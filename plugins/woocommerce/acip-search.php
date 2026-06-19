<?php
/**
 * Plugin Name: ACIP Search (pilot)
 * Description: Replaces WooCommerce native product search with ACIP hybrid search
 *              and syncs product changes to ACIP (M8 subset, Phase 1).
 * Version: 0.1.0
 *
 * Pilot scaffold — configure ACIP_API_URL and the tenant API keys in wp-config
 * or the plugin settings page before use.
 */

if (!defined('ABSPATH')) { exit; }

if (!defined('ACIP_API_URL')) {
    define('ACIP_API_URL', getenv('ACIP_API_URL') ?: 'http://localhost:8000');
}

/** Replace the product query with ACIP results on the shop search page. */
add_action('pre_get_posts', function ($query) {
    if (is_admin() || !$query->is_main_query() || !$query->is_search()) {
        return;
    }
    $api_key = get_option('acip_widget_key');
    if (!$api_key) { return; }

    $resp = wp_remote_post(ACIP_API_URL . '/v1/search', array(
        'headers' => array('Content-Type' => 'application/json', 'x-api-key' => $api_key),
        'body'    => wp_json_encode(array('query' => get_search_query(), 'size' => 24)),
        'timeout' => 3,
    ));
    if (is_wp_error($resp)) { return; }

    $data = json_decode(wp_remote_retrieve_body($resp), true);
    $ids  = array_map(fn($r) => (int) $r['product_id'], $data['results'] ?? array());
    if ($ids) {
        $query->set('post__in', $ids);
        $query->set('orderby', 'post__in');
    }
});

/** Forward product saves to ACIP sync. */
add_action('woocommerce_update_product', function ($product_id) {
    $sync_key = get_option('acip_sync_key');
    if (!$sync_key) { return; }
    $product = wc_get_product($product_id);
    if (!$product) { return; }

    wp_remote_post(ACIP_API_URL . '/v1/sync/webhook?source=woocommerce', array(
        'headers' => array('Content-Type' => 'application/json', 'x-api-key' => $sync_key),
        'body'    => wp_json_encode($product->get_data()),
        'timeout' => 3,
    ));
});
