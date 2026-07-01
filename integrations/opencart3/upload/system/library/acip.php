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

    /**
     * Connectivity check for the admin "Test connection" button. Hits the
     * public, unauthenticated /healthz probe (no api key required) so it only
     * verifies the API URL is reachable, then reports whether the widget/sync
     * keys are at least present.
     */
    public function ping() {
        if (!$this->api_url) {
            return array('ok' => false, 'error' => 'missing_api_url');
        }
        $ch = curl_init(rtrim($this->api_url, '/') . '/healthz');
        curl_setopt_array($ch, array(
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_TIMEOUT        => 5,
        ));
        $body = curl_exec($ch);
        $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $err  = curl_error($ch);
        curl_close($ch);
        return array(
            'ok'          => ($code === 200),
            'http_status' => $code,
            'error'       => $err ?: null,
            'has_widget_key' => (bool) $this->widget_key,
            'has_sync_key'   => (bool) $this->sync_key,
        );
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
