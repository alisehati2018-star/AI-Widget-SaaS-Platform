<?php
// Heading
$_['heading_title']       = 'ACIP — Smart Search & Assistant';

// Text
$_['text_extension']      = 'Extensions';
$_['text_success']        = 'Success: You have modified ACIP settings!';
$_['text_edit']           = 'Edit ACIP Settings';
$_['text_enabled']        = 'Enabled';
$_['text_disabled']       = 'Disabled';
$_['text_home']           = 'Home';

// Entry
$_['entry_status']        = 'Status';
$_['entry_api_url']       = 'ACIP API URL';
$_['entry_widget_key']    = 'Widget API Key (storefront search + chat)';
$_['entry_sync_key']      = 'Sync API Key (catalogue ingest)';
$_['entry_replace_search']= 'Replace native search';
$_['entry_export_token']  = 'Export token (delta sync)';
$_['help_export_token']   = 'Any long random string. Paste the SAME value into the Vitrin dashboard (Settings > Connect store) so the platform can pull changed products periodically.';
$_['entry_inject_widget'] = 'Inject widget on storefront';
$_['entry_sync_orders']   = 'Sync orders to ACIP';
$_['help_sync_orders']    = 'Indexes every order (and status change) into Elasticsearch so it can be looked up and analysed — uses the same Sync API Key as the catalogue.';

// Buttons / help
$_['button_save']         = 'Save';
$_['button_cancel']       = 'Cancel';
$_['button_bulk_import']  = 'Bulk import catalogue now';
$_['help_bulk_import']    = 'Pushes every active product to ACIP for the initial index build.';
$_['button_bulk_import_orders'] = 'Bulk import order history now';
$_['help_bulk_import_orders']   = 'Pushes recent orders to ACIP for the initial order index build.';
$_['button_test_connection'] = 'Test connection';
$_['text_test_success']   = 'Connected — the API is reachable.';
$_['text_test_failed']    = 'Could not reach the ACIP API. Check the URL and try again.';

// Error
$_['error_permission']    = 'Warning: You do not have permission to modify ACIP settings!';
