<?php
/**
 * ACIP admin module controller (OpenCart 3.x).
 *
 * Settings page + product-change event registration. Stores api_url, the
 * widget key (storefront search/chat) and the sync key (catalogue ingest),
 * and registers admin events so product add/edit/delete are pushed to ACIP.
 */
class ControllerExtensionModuleAcip extends Controller {
    private $error = array();

    public function index() {
        $this->load->language('extension/module/acip');
        $this->document->setTitle($this->language->get('heading_title'));
        $this->load->model('setting/setting');

        if (($this->request->server['REQUEST_METHOD'] == 'POST') && $this->validate()) {
            $this->model_setting_setting->editSetting('module_acip', $this->request->post);
            $this->session->data['success'] = $this->language->get('text_success');
            $this->response->redirect($this->url->link(
                'marketplace/extension',
                'user_token=' . $this->session->data['user_token'] . '&type=module',
                true
            ));
        }

        $fields = array(
            'heading_title', 'text_edit', 'text_enabled', 'text_disabled',
            'entry_status', 'entry_api_url', 'entry_widget_key', 'entry_sync_key',
            'entry_replace_search', 'entry_inject_widget', 'button_save', 'button_cancel',
            'button_bulk_import', 'help_bulk_import',
        );
        foreach ($fields as $f) {
            $data[$f] = $this->language->get($f);
        }

        $data['error_warning'] = isset($this->error['warning']) ? $this->error['warning'] : '';
        $data['breadcrumbs'] = array();
        $data['breadcrumbs'][] = array(
            'text' => $this->language->get('text_home'),
            'href' => $this->url->link('common/dashboard',
                'user_token=' . $this->session->data['user_token'], true),
        );
        $data['breadcrumbs'][] = array(
            'text' => $this->language->get('heading_title'),
            'href' => $this->url->link('extension/module/acip',
                'user_token=' . $this->session->data['user_token'], true),
        );

        $data['action'] = $this->url->link('extension/module/acip',
            'user_token=' . $this->session->data['user_token'], true);
        $data['cancel'] = $this->url->link('marketplace/extension',
            'user_token=' . $this->session->data['user_token'] . '&type=module', true);
        $data['bulk_import'] = $this->url->link('extension/module/acip.bulkImport',
            'user_token=' . $this->session->data['user_token'], true);

        // Bind each setting, defaulting where unset.
        $settings = array(
            'module_acip_status'         => 0,
            'module_acip_api_url'        => '',
            'module_acip_widget_key'     => '',
            'module_acip_sync_key'       => '',
            'module_acip_replace_search' => 1,
            'module_acip_inject_widget'  => 1,
        );
        foreach ($settings as $key => $default) {
            if (isset($this->request->post[$key])) {
                $data[$key] = $this->request->post[$key];
            } else {
                $data[$key] = $this->config->get($key) !== null
                    ? $this->config->get($key) : $default;
            }
        }

        $data['header'] = $this->load->controller('common/header');
        $data['column_left'] = $this->load->controller('common/column_left');
        $data['footer'] = $this->load->controller('common/footer');

        $this->response->setOutput($this->load->view('extension/module/acip', $data));
    }

    /** Push the whole catalogue to ACIP in one click. */
    public function bulkImport() {
        $this->load->model('extension/module/acip');
        $json = array();
        try {
            $products = $this->model_extension_module_acip->getAllProducts();
            $this->registry->set('acip', new Acip($this->registry));
            $resp = $this->registry->get('acip')->bulkImport($products);
            $json['success'] = true;
            $json['count'] = count($products);
        } catch (Exception $e) {
            $json['error'] = $e->getMessage();
        }
        $this->response->addHeader('Content-Type: application/json');
        $this->response->setOutput(json_encode($json));
    }

    /** Register admin product-change events on install. */
    public function install() {
        $this->load->model('setting/event');
        $this->model_setting_event->addEvent('acip_product_edit',
            'admin/model/catalog/product/editProduct/after',
            'extension/module/acip.onProductChange');
        $this->model_setting_event->addEvent('acip_product_add',
            'admin/model/catalog/product/addProduct/after',
            'extension/module/acip.onProductChange');
        $this->model_setting_event->addEvent('acip_product_delete',
            'admin/model/catalog/product/deleteProduct/after',
            'extension/module/acip.onProductDelete');
    }

    public function uninstall() {
        $this->load->model('setting/event');
        $this->model_setting_event->deleteEventByCode('acip_product_edit');
        $this->model_setting_event->deleteEventByCode('acip_product_add');
        $this->model_setting_event->deleteEventByCode('acip_product_delete');
    }

    /** Event: a product was added/edited → upsert into ACIP. */
    public function onProductChange($route, $args, $output) {
        if (!$this->config->get('module_acip_status')) {
            return;
        }
        $product_id = is_array($args) && isset($args[0]) ? (int)$args[0] : 0;
        if (!$product_id && isset($output)) {
            $product_id = (int)$output;
        }
        if (!$product_id) {
            return;
        }
        $this->load->model('extension/module/acip');
        $product = $this->model_extension_module_acip->getProduct($product_id);
        if ($product) {
            $this->registry->set('acip', new Acip($this->registry));
            $this->registry->get('acip')->syncProduct($product, 'upsert');
        }
    }

    /** Event: a product was deleted → tombstone in ACIP. */
    public function onProductDelete($route, $args, $output) {
        if (!$this->config->get('module_acip_status')) {
            return;
        }
        $product_id = is_array($args) && isset($args[0]) ? (int)$args[0] : 0;
        if (!$product_id) {
            return;
        }
        $this->registry->set('acip', new Acip($this->registry));
        $this->registry->get('acip')->syncProduct(array('product_id' => $product_id), 'delete');
    }

    private function validate() {
        if (!$this->user->hasPermission('modify', 'extension/module/acip')) {
            $this->error['warning'] = $this->language->get('error_permission');
        }
        return !$this->error;
    }
}
