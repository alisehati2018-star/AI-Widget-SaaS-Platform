<?php
/**
 * Uninstall handler — runs only when the plugin is deleted from the Plugins
 * screen (never on simple deactivation), and only removes ACIP's own data.
 *
 * @package ACIP
 */

if (!defined('WP_UNINSTALL_PLUGIN')) {
    exit;
}

delete_option('acip_settings');

// Multisite: also clear the option on every site in the network.
if (is_multisite()) {
    $site_ids = get_sites(array('fields' => 'ids'));
    foreach ($site_ids as $site_id) {
        switch_to_blog($site_id);
        delete_option('acip_settings');
        restore_current_blog();
    }
}
