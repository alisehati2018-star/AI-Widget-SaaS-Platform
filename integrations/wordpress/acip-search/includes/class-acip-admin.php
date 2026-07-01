<?php
/**
 * ACIP settings screen (WordPress admin).
 *
 * Registers a settings page under WooCommerce → ACIP with the API URL, widget
 * key, sync key, and toggles, plus a "Test connection" check and a one-click
 * bulk import button. Assets are enqueued (not inlined) per WP coding
 * standards, and only load on this plugin's own settings screen.
 *
 * @package ACIP
 */

if (!defined('ABSPATH')) {
    exit;
}

class ACIP_Admin {
    /** @var string Hook suffix returned by add_submenu_page(), used to scope asset loading. */
    private $hook_suffix = '';

    public function __construct() {
        add_action('admin_menu', array($this, 'menu'));
        add_action('admin_init', array($this, 'register'));
        add_action('admin_enqueue_scripts', array($this, 'enqueue_assets'));
        add_action('wp_ajax_acip_test_connection', array($this, 'ajax_test_connection'));
    }

    public function menu() {
        $this->hook_suffix = add_submenu_page(
            'woocommerce',
            __('ACIP Search', 'acip-search'),
            __('ACIP Search', 'acip-search'),
            'manage_woocommerce',
            'acip-search',
            array($this, 'render')
        );
    }

    public function register() {
        register_setting('acip_settings_group', 'acip_settings', array(
            'sanitize_callback' => array($this, 'sanitize'),
        ));
    }

    public function sanitize($input) {
        return array(
            'enabled'        => empty($input['enabled']) ? 0 : 1,
            'api_url'        => esc_url_raw(isset($input['api_url']) ? $input['api_url'] : ''),
            'widget_key'     => sanitize_text_field(isset($input['widget_key']) ? $input['widget_key'] : ''),
            'sync_key'       => sanitize_text_field(isset($input['sync_key']) ? $input['sync_key'] : ''),
            'replace_search' => empty($input['replace_search']) ? 0 : 1,
        );
    }

    /** Enqueue the settings-page CSS/JS only on our own admin screen. */
    public function enqueue_assets($hook) {
        if ($hook !== $this->hook_suffix) {
            return;
        }
        wp_enqueue_style('acip-admin', ACIP_PLUGIN_URL . 'assets/css/admin.css', array(), ACIP_VERSION);
        wp_enqueue_script('acip-admin', ACIP_PLUGIN_URL . 'assets/js/admin.js', array(), ACIP_VERSION, true);
        wp_localize_script('acip-admin', 'acipAdmin', array(
            'ajaxUrl' => admin_url('admin-ajax.php'),
            'nonce'   => wp_create_nonce('acip_bulk'),
            'i18n'    => array(
                'working'  => __('Working…', 'acip-search'),
                'imported' => __('Imported %d products.', 'acip-search'),
                'failed'   => __('Failed. Check your keys and try again.', 'acip-search'),
            ),
        ));
    }

    /** AJAX: verify the configured (posted, not-yet-saved) API URL is reachable. */
    public function ajax_test_connection() {
        check_ajax_referer('acip_test_connection', 'nonce');
        if (!current_user_can('manage_woocommerce')) {
            wp_send_json_error(array('message' => __('Forbidden.', 'acip-search')), 403);
        }
        $options = array(
            'api_url'    => isset($_POST['api_url']) ? esc_url_raw(wp_unslash($_POST['api_url'])) : '',
            'widget_key' => isset($_POST['widget_key']) ? sanitize_text_field(wp_unslash($_POST['widget_key'])) : '',
            'sync_key'   => isset($_POST['sync_key']) ? sanitize_text_field(wp_unslash($_POST['sync_key'])) : '',
        );
        $client = new ACIP_Client($options);
        $result = $client->ping();
        $result['message'] = $result['ok']
            ? __('Connected — the API is reachable.', 'acip-search')
            : __('Could not reach the ACIP API. Check the URL and try again.', 'acip-search');
        wp_send_json_success($result);
    }

    public function render() {
        $o = wp_parse_args(get_option('acip_settings', array()), array(
            'enabled' => 0, 'api_url' => '', 'widget_key' => '', 'sync_key' => '', 'replace_search' => 1,
        ));
        $test_nonce = wp_create_nonce('acip_test_connection');
        ?>
        <div class="wrap acip-settings-page">
            <h1><?php esc_html_e('ACIP — Smart Search & Assistant', 'acip-search'); ?></h1>
            <form method="post" action="options.php">
                <?php settings_fields('acip_settings_group'); ?>
                <table class="form-table" role="presentation">
                    <tr><th><?php esc_html_e('Enabled', 'acip-search'); ?></th>
                        <td><label><input type="checkbox" name="acip_settings[enabled]" value="1"
                            <?php checked($o['enabled'], 1); ?>> <?php esc_html_e('Activate ACIP', 'acip-search'); ?></label></td></tr>
                    <tr><th><?php esc_html_e('ACIP API URL', 'acip-search'); ?></th>
                        <td>
                            <input type="url" class="regular-text" id="acip-api-url" name="acip_settings[api_url]"
                                value="<?php echo esc_attr($o['api_url']); ?>" placeholder="https://api.acip.example">
                            <button type="button" class="button" id="acip-test"
                                data-nonce="<?php echo esc_attr($test_nonce); ?>">
                                <?php esc_html_e('Test connection', 'acip-search'); ?></button>
                            <p id="acip-test-result"></p>
                        </td></tr>
                    <tr><th><?php esc_html_e('Widget API Key', 'acip-search'); ?></th>
                        <td><input type="text" class="regular-text" id="acip-widget-key" name="acip_settings[widget_key]"
                            value="<?php echo esc_attr($o['widget_key']); ?>">
                            <p class="description"><?php esc_html_e('Storefront search + chat (least privilege).', 'acip-search'); ?></p></td></tr>
                    <tr><th><?php esc_html_e('Sync API Key', 'acip-search'); ?></th>
                        <td><input type="text" class="regular-text" id="acip-sync-key" name="acip_settings[sync_key]"
                            value="<?php echo esc_attr($o['sync_key']); ?>">
                            <p class="description"><?php esc_html_e('Catalogue ingest. Keep server-side.', 'acip-search'); ?></p></td></tr>
                    <tr><th><?php esc_html_e('Replace native search', 'acip-search'); ?></th>
                        <td><label><input type="checkbox" name="acip_settings[replace_search]" value="1"
                            <?php checked($o['replace_search'], 1); ?>> <?php esc_html_e('Use ACIP results on the shop search page', 'acip-search'); ?></label></td></tr>
                </table>
                <?php submit_button(); ?>
            </form>

            <hr>
            <h2><?php esc_html_e('Initial catalogue import', 'acip-search'); ?></h2>
            <p><?php esc_html_e('Push every published product to ACIP to build the index.', 'acip-search'); ?></p>
            <button class="button button-secondary" id="acip-bulk"><?php esc_html_e('Bulk import now', 'acip-search'); ?></button>
            <span id="acip-bulk-result"></span>
        </div>
        <?php
    }
}
