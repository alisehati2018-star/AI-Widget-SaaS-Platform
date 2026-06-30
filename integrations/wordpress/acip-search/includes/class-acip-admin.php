<?php
/**
 * ACIP settings screen (WordPress admin).
 *
 * Registers a settings page under WooCommerce → ACIP with the API URL, widget
 * key, sync key, and toggles, plus a one-click bulk import button.
 *
 * @package ACIP
 */

if (!defined('ABSPATH')) {
    exit;
}

class ACIP_Admin {
    public function __construct() {
        add_action('admin_menu', array($this, 'menu'));
        add_action('admin_init', array($this, 'register'));
    }

    public function menu() {
        add_submenu_page(
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

    public function render() {
        $o = wp_parse_args(get_option('acip_settings', array()), array(
            'enabled' => 0, 'api_url' => '', 'widget_key' => '', 'sync_key' => '', 'replace_search' => 1,
        ));
        $nonce = wp_create_nonce('acip_bulk');
        ?>
        <div class="wrap">
            <h1><?php esc_html_e('ACIP — Smart Search & Assistant', 'acip-search'); ?></h1>
            <form method="post" action="options.php">
                <?php settings_fields('acip_settings_group'); ?>
                <table class="form-table" role="presentation">
                    <tr><th><?php esc_html_e('Enabled', 'acip-search'); ?></th>
                        <td><label><input type="checkbox" name="acip_settings[enabled]" value="1"
                            <?php checked($o['enabled'], 1); ?>> <?php esc_html_e('Activate ACIP', 'acip-search'); ?></label></td></tr>
                    <tr><th><?php esc_html_e('ACIP API URL', 'acip-search'); ?></th>
                        <td><input type="url" class="regular-text" name="acip_settings[api_url]"
                            value="<?php echo esc_attr($o['api_url']); ?>" placeholder="https://api.acip.example"></td></tr>
                    <tr><th><?php esc_html_e('Widget API Key', 'acip-search'); ?></th>
                        <td><input type="text" class="regular-text" name="acip_settings[widget_key]"
                            value="<?php echo esc_attr($o['widget_key']); ?>">
                            <p class="description"><?php esc_html_e('Storefront search + chat (least privilege).', 'acip-search'); ?></p></td></tr>
                    <tr><th><?php esc_html_e('Sync API Key', 'acip-search'); ?></th>
                        <td><input type="text" class="regular-text" name="acip_settings[sync_key]"
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
            <script>
            document.getElementById('acip-bulk').addEventListener('click', function (e) {
                e.preventDefault();
                var out = document.getElementById('acip-bulk-result');
                out.textContent = ' …';
                var body = new URLSearchParams({ action: 'acip_bulk_import', nonce: '<?php echo esc_js($nonce); ?>' });
                fetch(ajaxurl, { method: 'POST', body: body })
                    .then(function (r) { return r.json(); })
                    .then(function (j) {
                        out.textContent = j.success ? ' Imported ' + j.data.count + ' products.' : ' Failed.';
                    });
            });
            </script>
        </div>
        <?php
    }
}
