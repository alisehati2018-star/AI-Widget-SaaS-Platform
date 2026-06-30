<?php
/**
 * ACIP storefront controller (OpenCart 3.x).
 *
 * Registered on the `catalog/view/common/footer/before` event to inject the
 * single-line ACIP widget loader on every storefront page, and exposes a JSON
 * search endpoint the (OCMOD-patched) search page can call.
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
