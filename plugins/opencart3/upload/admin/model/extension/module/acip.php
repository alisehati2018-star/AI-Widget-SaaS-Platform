<?php
/**
 * ACIP admin model (OpenCart 3.x) — reads products into the ACIP canonical
 * shape (id, name, description, manufacturer/brand, categories, attributes,
 * price, quantity) for sync + bulk import.
 */
class ModelExtensionModuleAcip extends Model {

    /** Build the ACIP product payload for one product id. */
    public function getProduct($product_id) {
        $row = $this->db->query(
            "SELECT p.product_id, p.model, p.sku, p.price, p.quantity,
                    pd.name, pd.description, m.name AS manufacturer, p.date_modified
             FROM " . DB_PREFIX . "product p
             LEFT JOIN " . DB_PREFIX . "product_description pd
                    ON (p.product_id = pd.product_id)
             LEFT JOIN " . DB_PREFIX . "manufacturer m
                    ON (p.manufacturer_id = m.manufacturer_id)
             WHERE p.product_id = '" . (int)$product_id . "'
               AND pd.language_id = '" . (int)$this->config->get('config_language_id') . "'"
        )->row;

        if (!$row) {
            return null;
        }

        return array(
            'product_id'   => (int)$row['product_id'],
            'name'         => $row['name'],
            'description'  => trim(strip_tags(html_entity_decode(
                                $row['description'], ENT_QUOTES, 'UTF-8'))),
            'manufacturer' => $row['manufacturer'],
            'categories'   => $this->getCategories($product_id),
            'attributes'   => $this->getAttributes($product_id),
            'price'        => (float)$row['price'],
            'quantity'     => (int)$row['quantity'],
            'date_modified'=> $row['date_modified'],
        );
    }

    /** Every product (capped page-by-page) for the initial bulk import. */
    public function getAllProducts($limit = 1000) {
        $ids = $this->db->query(
            "SELECT product_id FROM " . DB_PREFIX . "product
             WHERE status = '1' ORDER BY product_id ASC LIMIT " . (int)$limit
        )->rows;
        $out = array();
        foreach ($ids as $r) {
            $p = $this->getProduct($r['product_id']);
            if ($p) {
                $out[] = $p;
            }
        }
        return $out;
    }

    /** Build the ACIP order payload for one order id. */
    public function getOrder($order_id) {
        $row = $this->db->query(
            "SELECT order_id, firstname, lastname, email, total, currency_code,
                    order_status_id, date_added, date_modified
             FROM " . DB_PREFIX . "order
             WHERE order_id = '" . (int)$order_id . "'"
        )->row;

        if (!$row) {
            return null;
        }

        $status = $this->db->query(
            "SELECT name FROM " . DB_PREFIX . "order_status
             WHERE order_status_id = '" . (int)$row['order_status_id'] . "'
               AND language_id = '" . (int)$this->config->get('config_language_id') . "'"
        )->row;

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
            'products'      => $this->getOrderProducts($order_id),
        );
    }

    /** Every order (capped) for the initial order-history backfill. */
    public function getAllOrders($limit = 1000) {
        $ids = $this->db->query(
            "SELECT order_id FROM " . DB_PREFIX . "order
             WHERE order_status_id > 0 ORDER BY order_id DESC LIMIT " . (int)$limit
        )->rows;
        $out = array();
        foreach ($ids as $r) {
            $o = $this->getOrder($r['order_id']);
            if ($o) {
                $out[] = $o;
            }
        }
        return $out;
    }

    private function getOrderProducts($order_id) {
        $rows = $this->db->query(
            "SELECT product_id, name, quantity, price FROM " . DB_PREFIX . "order_product
             WHERE order_id = '" . (int)$order_id . "'"
        )->rows;
        return array_map(function ($r) {
            return array(
                'product_id' => (int)$r['product_id'],
                'name'       => $r['name'],
                'quantity'   => (int)$r['quantity'],
                'price'      => (float)$r['price'],
            );
        }, $rows);
    }

    private function getCategories($product_id) {
        $rows = $this->db->query(
            "SELECT cd.name FROM " . DB_PREFIX . "product_to_category pc
             JOIN " . DB_PREFIX . "category_description cd
               ON (pc.category_id = cd.category_id)
             WHERE pc.product_id = '" . (int)$product_id . "'
               AND cd.language_id = '" . (int)$this->config->get('config_language_id') . "'"
        )->rows;
        return array_map(function ($r) { return $r['name']; }, $rows);
    }

    private function getAttributes($product_id) {
        $rows = $this->db->query(
            "SELECT ad.name, pa.text FROM " . DB_PREFIX . "product_attribute pa
             JOIN " . DB_PREFIX . "attribute_description ad
               ON (pa.attribute_id = ad.attribute_id)
             WHERE pa.product_id = '" . (int)$product_id . "'
               AND ad.language_id = '" . (int)$this->config->get('config_language_id') . "'"
        )->rows;
        $attrs = array();
        foreach ($rows as $r) {
            $attrs[$r['name']] = $r['text'];
        }
        return $attrs;
    }
}
