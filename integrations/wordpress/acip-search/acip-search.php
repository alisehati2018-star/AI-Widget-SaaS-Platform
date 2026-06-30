<?php
/**
 * Plugin Name:       ACIP — Smart Search & Assistant
 * Plugin URI:        https://acip.example
 * Description:        Replaces WooCommerce native product search with ACIP hybrid Persian search, embeds the grounded AI shopping assistant, and keeps your catalogue synced to ACIP.
 * Version:           1.0.0
 * Requires at least: 6.0
 * Requires PHP:      7.4
 * Author:            ACIP
 * License:           GPL-2.0-or-later
 * License URI:       https://www.gnu.org/licenses/gpl-2.0.html
 * Text Domain:       acip-search
 * WC requires at least: 6.0
 *
 * @package ACIP
 */

if (!defined('ABSPATH')) {
    exit;
}

define('ACIP_VERSION', '1.0.0');
define('ACIP_PLUGIN_FILE', __FILE__);
define('ACIP_PLUGIN_DIR', plugin_dir_path(__FILE__));

require_once ACIP_PLUGIN_DIR . 'includes/class-acip-client.php';
require_once ACIP_PLUGIN_DIR . 'includes/class-acip-admin.php';
require_once ACIP_PLUGIN_DIR . 'includes/class-acip-sync.php';

/**
 * Boot the plugin once all plugins are loaded (so WooCommerce is available).
 */
function acip_bootstrap() {
    $options = get_option('acip_settings', array());
    $client  = new ACIP_Client($options);

    new ACIP_Admin();
    new ACIP_Sync($client, $options);

    // Inject the single-line widget loader in the site footer.
    add_action('wp_footer', function () use ($options) {
        if (empty($options['enabled']) || empty($options['api_url']) || empty($options['widget_key'])) {
            return;
        }
        $api_url = esc_url(rtrim($options['api_url'], '/'));
        printf(
            '<script src="%1$s/widget/v1.js" data-acip-key="%2$s" data-acip-base="%1$s" async></script>' . "\n",
            $api_url,
            esc_attr($options['widget_key'])
        );
    });

    // Replace the storefront search results with ACIP-ranked product ids.
    if (!empty($options['replace_search'])) {
        add_action('pre_get_posts', function ($query) use ($client) {
            if (is_admin() || !$query->is_main_query() || !$query->is_search()) {
                return;
            }
            $term = get_search_query();
            if (!$term) {
                return;
            }
            $results = $client->search($term, 24);
            $ids = array();
            foreach ($results as $r) {
                if (!empty($r['product_id'])) {
                    $ids[] = (int) $r['product_id'];
                }
            }
            if ($ids) {
                $query->set('post_type', 'product');
                $query->set('post__in', $ids);
                $query->set('orderby', 'post__in');
            }
        });
    }
}
add_action('plugins_loaded', 'acip_bootstrap');

/**
 * On activation, flag a full sync to run on the next admin load.
 */
register_activation_hook(__FILE__, function () {
    add_option('acip_settings', array(
        'enabled'        => 0,
        'api_url'        => '',
        'widget_key'     => '',
        'sync_key'       => '',
        'replace_search' => 1,
    ));
});
