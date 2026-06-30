<?php
/**
 * ACIP API client for OpenCart 3.x.
 *
 * Thin cURL wrapper around the ACIP public API: hybrid search, product sync
 * webhooks, and bulk import. Configured from the admin module settings
 * (api_url, widget_key, sync_key).
 */
class Acip {
    private $api_url;
    private $widget_key;
    private $sync_key;

    public function __construct($registry) {
        $config = $registry->get('config');
        $this->api_url    = rtrim($config->get('module_acip_api_url'), '/');
        $this->widget_key = $config->get('module_acip_widget_key');
        $this->sync_key   = $config->get('module_acip_sync_key');
    }

    /** Run a hybrid search; returns the decoded result array. */
    public function search($query, $size = 24, $filters = array()) {
        $resp = $this->call('/v1/search', $this->widget_key, array(
            'query'   => $query,
            'size'    => (int)$size,
            'filters' => (object)$filters,
        ));
        return isset($resp['results']) ? $resp['results'] : array();
    }

    /** Forward a single product upsert/delete to the sync webhook. */
    public function syncProduct($product, $event = 'upsert') {
        return $this->call('/v1/sync/webhook?source=opencart', $this->sync_key, array(
            'event'   => $event,
            'product' => $product,
        ));
    }

    /** Bulk import a list of normalised products (initial backfill). */
    public function bulkImport($products) {
        return $this->call('/v1/sync/bulk', $this->sync_key, array(
            'source'   => 'opencart',
            'products' => array_values($products),
        ));
    }

    private function call($path, $key, $payload) {
        if (!$this->api_url || !$key) {
            return array();
        }
        $ch = curl_init($this->api_url . $path);
        curl_setopt_array($ch, array(
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_POST           => true,
            CURLOPT_POSTFIELDS     => json_encode($payload),
            CURLOPT_HTTPHEADER     => array(
                'Content-Type: application/json',
                'x-api-key: ' . $key,
            ),
            CURLOPT_TIMEOUT        => 5,
        ));
        $body = curl_exec($ch);
        curl_close($ch);
        return $body ? json_decode($body, true) : array();
    }
}
