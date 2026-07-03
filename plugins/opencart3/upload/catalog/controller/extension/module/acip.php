<?php
/**
 * ACIP storefront controller (OpenCart 3.x).
 *
 * Registered on the `catalog/view/common/footer/before` event to inject the
 * single-line ACIP widget loader on every storefront page, and exposes a JSON
 * search endpoint the (OCMOD-patched) search page can call. Also handles the
 * order-sync events: OpenCart routes every order mutation — storefront
 * checkout, the admin "Add History" button, 3rd-party payment callbacks —
 * through `catalog/model/checkout/order.php`, so hooking it here (rather than
 * on an admin-side model) reaches every order regardless of which side
 * changed it.
 */
class ControllerExtensionModuleAcip extends Controller {

    /** Event: inject the widget loader script before the footer renders. */
    public function injectWidget(&$route, &$args, &$output) {
        if (!$this->config->get('module_acip_status')
            || !$this->config->get('module_acip_inject_widget')) {
            return;
        }
        $api_url = rtrim($this->config->get('module_acip_api_url'), '/');
        $key     = $this->config->get('module_acip_widget_key');
        if (!$api_url || !$key) {
            return;
        }
        $snippet = '<script src="' . htmlspecialchars($api_url) . '/widget/v1.js"'
            . ' data-acip-key="' . htmlspecialchars($key) . '"'
            . ' data-acip-base="' . htmlspecialchars($api_url) . '" async></script>';
        // Inject right before </body>.
        if (strpos($output, '</body>') !== false) {
            $output = str_replace('</body>', $snippet . "\n</body>", $output);
        } else {
            $output .= $snippet;
        }
    }

    /**
     * Paged catalogue export for Vitrin delta reconciliation (pull path).
     *
     * GET index.php?route=extension/module/acip/export&since=...&page=N&limit=100
     * Header: X-Acip-Token: <module export token>
     *
     * Returns {"products": [...], "more": bool, "page": N}. Products modified
     * since the watermark (all products when `since` is omitted), oldest first,
     * in the same canonical shape the webhook/bulk paths send.
     */
    public function export() {
        $this->response->addHeader('Content-Type: application/json');

        $configured = (string)$this->config->get('module_acip_export_token');
        $provided = isset($this->request->server['HTTP_X_ACIP_TOKEN'])
            ? (string)$this->request->server['HTTP_X_ACIP_TOKEN'] : '';
        if (!$this->config->get('module_acip_status')
            || $configured === '' || !hash_equals($configured, $provided)) {
            $this->response->addHeader('HTTP/1.1 403 Forbidden');
            $this->response->setOutput(json_encode(array('error' => 'forbidden')));
            return;
        }

        $limit = isset($this->request->get['limit'])
            ? max(1, min(500, (int)$this->request->get['limit'])) : 100;
        $page = isset($this->request->get['page'])
            ? max(1, (int)$this->request->get['page']) : 1;
        $since = isset($this->request->get['since'])
            ? date('Y-m-d H:i:s', strtotime($this->request->get['since'])) : null;

        $sql = "SELECT p.product_id FROM " . DB_PREFIX . "product p WHERE p.status = '1'";
        if ($since) {
            $sql .= " AND p.date_modified > '" . $this->db->escape($since) . "'";
        }
        $sql .= " ORDER BY p.date_modified ASC, p.product_id ASC"
              . " LIMIT " . (int)(($page - 1) * $limit) . ", " . (int)($limit + 1);
        $rows = $this->db->query($sql)->rows;

        $more = count($rows) > $limit;
        $rows = array_slice($rows, 0, $limit);
        $products = array();
        foreach ($rows as $r) {
            $p = $this->exportProduct((int)$r['product_id']);
            if ($p) {
                $products[] = $p;
            }
        }
        $this->response->setOutput(json_encode(array(
            'products' => $products,
            'more'     => $more,
            'page'     => $page,
        )));
    }

    /** Canonical payload for one product (same shape as the admin model). */
    private function exportProduct($product_id) {
        $lang = (int)$this->config->get('config_language_id');
        $row = $this->db->query(
            "SELECT p.product_id, p.model, p.sku, p.price, p.quantity,
                    pd.name, pd.description, m.name AS manufacturer, p.date_modified
             FROM " . DB_PREFIX . "product p
             LEFT JOIN " . DB_PREFIX . "product_description pd
                    ON (p.product_id = pd.product_id)
             LEFT JOIN " . DB_PREFIX . "manufacturer m
                    ON (p.manufacturer_id = m.manufacturer_id)
             WHERE p.product_id = '" . (int)$product_id . "'
               AND pd.language_id = '" . $lang . "'"
        )->row;
        if (!$row) {
            return null;
        }
        $cats = $this->db->query(
            "SELECT cd.name FROM " . DB_PREFIX . "product_to_category pc
             JOIN " . DB_PREFIX . "category_description cd
               ON (pc.category_id = cd.category_id)
             WHERE pc.product_id = '" . (int)$product_id . "'
               AND cd.language_id = '" . $lang . "'"
        )->rows;
        $attr_rows = $this->db->query(
            "SELECT ad.name, pa.text FROM " . DB_PREFIX . "product_attribute pa
             JOIN " . DB_PREFIX . "attribute_description ad
               ON (pa.attribute_id = ad.attribute_id)
             WHERE pa.product_id = '" . (int)$product_id . "'
               AND ad.language_id = '" . $lang . "'"
        )->rows;
        $attrs = array();
        foreach ($attr_rows as $a) {
            $attrs[$a['name']] = $a['text'];
        }
        return array(
            'product_id'    => (int)$row['product_id'],
            'name'          => $row['name'],
            'description'   => trim(strip_tags(html_entity_decode(
                                 $row['description'], ENT_QUOTES, 'UTF-8'))),
            'manufacturer'  => $row['manufacturer'],
            'categories'    => array_map(function ($c) { return $c['name']; }, $cats),
            'attributes'    => $attrs,
            'price'         => (float)$row['price'],
            'quantity'      => (int)$row['quantity'],
            'date_modified' => $row['date_modified'],
        );
    }

    /** Event: `addOrderHistory` fired — a new order's initial status was set,
     *  or an existing order's status changed (from checkout, the admin "Add
     *  History" button, or a payment callback). Always an upsert: cancelled/
     *  refunded is a status value, not a removal (`onOrderDelete` handles
     *  actual deletion). */
    public function onOrderChange($route, $args, $output) {
        if (!$this->config->get('module_acip_status')
            || !$this->config->get('module_acip_sync_orders')) {
            return;
        }
        $order_id = is_array($args) && isset($args[0]) ? (int)$args[0] : 0;
        if (!$order_id) {
            return;
        }
        $order = $this->exportOrder($order_id);
        if ($order) {
            $this->registry->set('acip', new Acip($this->registry));
            $this->registry->get('acip')->syncOrder($order, 'upsert');
        }
    }

    /** Event: `deleteOrder` fired — the order record itself was removed. */
    public function onOrderDelete($route, $args, $output) {
        if (!$this->config->get('module_acip_status')
            || !$this->config->get('module_acip_sync_orders')) {
            return;
        }
        $order_id = is_array($args) && isset($args[0]) ? (int)$args[0] : 0;
        if (!$order_id) {
            return;
        }
        $this->registry->set('acip', new Acip($this->registry));
        $this->registry->get('acip')->syncOrder(array('order_id' => $order_id), 'delete');
    }

    /** Canonical payload for one order (same shape as the admin model). */
    private function exportOrder($order_id) {
        $row = $this->db->query(
            "SELECT order_id, firstname, lastname, email, total, currency_code,
                    order_status_id, date_added, date_modified
             FROM " . DB_PREFIX . "order WHERE order_id = '" . (int)$order_id . "'"
        )->row;
        if (!$row) {
            return null;
        }
        $status = $this->db->query(
            "SELECT name FROM " . DB_PREFIX . "order_status
             WHERE order_status_id = '" . (int)$row['order_status_id'] . "'
               AND language_id = '" . (int)$this->config->get('config_language_id') . "'"
        )->row;
        $items = $this->db->query(
            "SELECT product_id, name, quantity, price FROM " . DB_PREFIX . "order_product
             WHERE order_id = '" . (int)$order_id . "'"
        )->rows;
        return array(
            'order_id'      => (int)$row['order_id'],
            'firstname'     => $row['firstname'],
            'lastname'      => $row['lastname'],
            'email'         => $row['email'],
            'total'         => (float)$row['total'],
            'currency_code' => $row['currency_code'],
            'order_status'  => $status ? $status['name'] : '',
            'date_added'    => $row['date_added'],
            'date_modified' => $row['date_modified'],
            'products'      => array_map(function ($r) {
                return array(
                    'product_id' => (int)$r['product_id'],
                    'name'       => $r['name'],
                    'quantity'   => (int)$r['quantity'],
                    'price'      => (float)$r['price'],
                );
            }, $items),
        );
    }

    /** JSON search proxy used by the OCMOD search override. */
    public function search() {
        $json = array('results' => array());
        if ($this->config->get('module_acip_status')
            && $this->config->get('module_acip_replace_search')) {
            $query = isset($this->request->get['search']) ? $this->request->get['search'] : '';
            if ($query !== '') {
                $this->registry->set('acip', new Acip($this->registry));
                $json['results'] = $this->registry->get('acip')->search($query);
            }
        }
        $this->response->addHeader('Content-Type: application/json');
        $this->response->setOutput(json_encode($json));
    }
}
