<?php
/**
 * ACIP API client (WordPress) — search, product sync, bulk import via the
 * WordPress HTTP API. Configured from the plugin settings.
 *
 * @package ACIP
 */

if (!defined('ABSPATH')) {
    exit;
}

class ACIP_Client {
    private $api_url;
    private $widget_key;
    private $sync_key;

    public function __construct($options) {
        $this->api_url    = isset($options['api_url']) ? rtrim($options['api_url'], '/') : '';
        $this->widget_key = isset($options['widget_key']) ? $options['widget_key'] : '';
        $this->sync_key   = isset($options['sync_key']) ? $options['sync_key'] : '';
    }

    /** Hybrid search; returns the result rows (empty on any failure). */
    public function search($query, $size = 24, $filters = array()) {
        $resp = $this->post('/v1/search', $this->widget_key, array(
            'query'   => $query,
            'size'    => (int) $size,
            'filters' => (object) $filters,
        ));
        return isset($resp['results']) ? $resp['results'] : array();
    }

    /** Upsert/delete a single product via the sync webhook. */
    public function sync_product($product, $event = 'upsert') {
        return $this->post('/v1/sync/webhook?source=woocommerce', $this->sync_key, array(
            'event'   => $event,
            'product' => $product,
        ));
    }

    /** Bulk import a list of normalised products. */
    public function bulk_import($products) {
        return $this->post('/v1/sync/bulk', $this->sync_key, array(
            'source'   => 'woocommerce',
            'products' => array_values($products),
        ));
    }

    private function post($path, $key, $payload) {
        if (!$this->api_url || !$key) {
            return array();
        }
        $resp = wp_remote_post($this->api_url . $path, array(
            'headers' => array(
                'Content-Type' => 'application/json',
                'x-api-key'    => $key,
            ),
            'body'    => wp_json_encode($payload),
            'timeout' => 5,
        ));
        if (is_wp_error($resp)) {
            return array();
        }
        $data = json_decode(wp_remote_retrieve_body($resp), true);
        return is_array($data) ? $data : array();
    }
}
