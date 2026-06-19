<?php
/**
 * ACIP — OpenCart search integration (M8 subset, Phase 1).
 *
 * Replaces native catalogue search with ACIP hybrid search (/v1/search) and
 * forwards product change events to /v1/sync/webhook. Drop into an OpenCart
 * module; wire ACIP_API_URL and ACIP_API_KEY from the store admin settings.
 *
 * This is a pilot scaffold, not a packaged extension.
 */

if (!defined('ACIP_API_URL')) {
    define('ACIP_API_URL', getenv('ACIP_API_URL') ?: 'http://localhost:8000');
}

/** Run an ACIP search and return decoded results. */
function acip_search($query, $apiKey, $filters = array(), $size = 20) {
    $ch = curl_init(ACIP_API_URL . '/v1/search');
    $payload = json_encode(array('query' => $query, 'filters' => $filters, 'size' => $size));
    curl_setopt_array($ch, array(
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_POST           => true,
        CURLOPT_POSTFIELDS     => $payload,
        CURLOPT_HTTPHEADER     => array('Content-Type: application/json', 'x-api-key: ' . $apiKey),
        CURLOPT_TIMEOUT        => 3,
    ));
    $body = curl_exec($ch);
    curl_close($ch);
    return $body ? json_decode($body, true) : array('results' => array());
}

/** Forward a product upsert/delete to ACIP sync. */
function acip_sync_product($product, $event, $apiKey) {
    $ch = curl_init(ACIP_API_URL . '/v1/sync/webhook?source=opencart');
    $payload = json_encode(array('event' => $event, 'product' => $product));
    curl_setopt_array($ch, array(
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_POST           => true,
        CURLOPT_POSTFIELDS     => $payload,
        CURLOPT_HTTPHEADER     => array('Content-Type: application/json', 'x-api-key: ' . $apiKey),
        CURLOPT_TIMEOUT        => 3,
    ));
    curl_exec($ch);
    curl_close($ch);
}
