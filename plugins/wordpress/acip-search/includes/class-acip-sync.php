<?php
/**
 * ACIP catalogue sync (WordPress / WooCommerce).
 *
 * Hooks product save/trash/delete to push changes to ACIP, normalising each
 * WooCommerce product into the ACIP canonical shape (brand + categories +
 * attributes included so they are indexed with the product).
 *
 * @package ACIP
 */

if (!defined('ABSPATH')) {
    exit;
}

class ACIP_Sync {
    private $client;
    private $options;

    public function __construct($client, $options) {
        $this->client  = $client;
        $this->options = $options;

        if (empty($options['enabled'])) {
            return;
        }
        add_action('woocommerce_update_product', array($this, 'on_save'), 10, 1);
        add_action('woocommerce_new_product', array($this, 'on_save'), 10, 1);
        add_action('wp_trash_post', array($this, 'on_delete'), 10, 1);
        add_action('before_delete_post', array($this, 'on_delete'), 10, 1);

        // Order sync (independent toggle — catalogue sync can run without it).
        if (!empty($options['sync_orders'])) {
            add_action('woocommerce_new_order', array($this, 'on_order_change'), 10, 1);
            add_action('woocommerce_order_status_changed', array($this, 'on_order_change'), 10, 1);
            add_action('wp_trash_post', array($this, 'on_order_delete'), 10, 1);
            add_action('before_delete_post', array($this, 'on_order_delete'), 10, 1);
            add_action('wp_ajax_acip_bulk_import_orders', array($this, 'ajax_bulk_import_orders'));
        }

        // AJAX hook for the admin "bulk import" button.
        add_action('wp_ajax_acip_bulk_import', array($this, 'ajax_bulk_import'));
    }

    public function on_save($product_id) {
        $product = wc_get_product($product_id);
        if (!$product) {
            return;
        }
        $this->client->sync_product($this->to_canonical($product), 'upsert');
    }

    public function on_delete($post_id) {
        if (get_post_type($post_id) !== 'product') {
            return;
        }
        $this->client->sync_product(array('id' => (int) $post_id), 'delete');
    }

    /** Map a WC_Product to the ACIP canonical product payload. */
    public function to_canonical($product) {
        $cat_ids = $product->get_category_ids();
        $categories = array();
        foreach ($cat_ids as $cid) {
            $term = get_term($cid);
            if ($term && !is_wp_error($term)) {
                $categories[] = array('name' => $term->name);
            }
        }

        $attributes = array();
        foreach ($product->get_attributes() as $attr) {
            if (is_a($attr, 'WC_Product_Attribute')) {
                $name = wc_attribute_label($attr->get_name());
                $attributes[] = array('name' => $name, 'options' => $attr->get_options());
            }
        }

        $brands = array();
        foreach (array('product_brand', 'pa_brand', 'brand') as $tax) {
            $terms = get_the_terms($product->get_id(), $tax);
            if ($terms && !is_wp_error($terms)) {
                foreach ($terms as $t) {
                    $brands[] = array('name' => $t->name);
                }
                break;
            }
        }

        return array(
            'id'           => $product->get_id(),
            'name'         => $product->get_name(),
            'description'  => wp_strip_all_tags($product->get_description()),
            'short_description' => wp_strip_all_tags($product->get_short_description()),
            'brands'       => $brands,
            'categories'   => $categories,
            'attributes'   => $attributes,
            'price'        => (float) $product->get_price(),
            'stock_status' => $product->get_stock_status(),
            'date_modified'=> $product->get_date_modified()
                ? $product->get_date_modified()->date('c') : null,
            'permalink'    => get_permalink($product->get_id()),
        );
    }

    /** Push every published product to ACIP (admin AJAX). */
    public function ajax_bulk_import() {
        check_ajax_referer('acip_bulk', 'nonce');
        if (!current_user_can('manage_woocommerce')) {
            wp_send_json_error('forbidden');
        }
        $ids = wc_get_products(array('limit' => 1000, 'status' => 'publish', 'return' => 'ids'));
        $products = array();
        foreach ($ids as $id) {
            $p = wc_get_product($id);
            if ($p) {
                $products[] = $this->to_canonical($p);
            }
        }
        $this->client->bulk_import($products);
        wp_send_json_success(array('count' => count($products)));
    }

    /** Order added / status changed (any new status, incl. cancelled/refunded,
     *  is an upsert — the order stays searchable/analysable, never removed). */
    public function on_order_change($order_id) {
        $order = wc_get_order($order_id);
        if (!$order) {
            return;
        }
        $this->client->sync_order($this->to_canonical_order($order), 'upsert');
    }

    /** The order's post was trashed/deleted (not just status-changed) → tombstone. */
    public function on_order_delete($post_id) {
        if (get_post_type($post_id) !== 'shop_order') {
            return;
        }
        $this->client->sync_order(array('id' => (int) $post_id), 'delete');
    }

    /** Map a WC_Order to the ACIP canonical order payload. */
    public function to_canonical_order($order) {
        $items = array();
        foreach ($order->get_items() as $item) {
            $items[] = array(
                'product_id' => $item->get_product_id(),
                'name'       => $item->get_name(),
                'quantity'   => (int) $item->get_quantity(),
                'price'      => (float) $order->get_item_total($item, false, false),
            );
        }
        return array(
            'id'                => $order->get_id(),
            'status'            => $order->get_status(),
            'billing'           => array(
                'email'      => $order->get_billing_email(),
                'first_name' => $order->get_billing_first_name(),
                'last_name'  => $order->get_billing_last_name(),
            ),
            'line_items'        => $items,
            'total'             => (float) $order->get_total(),
            'currency'          => $order->get_currency(),
            'date_created_gmt'  => $order->get_date_created()
                ? $order->get_date_created()->date('c') : null,
            'date_modified_gmt' => $order->get_date_modified()
                ? $order->get_date_modified()->date('c') : null,
        );
    }

    /** Push recent order history to ACIP (admin AJAX). */
    public function ajax_bulk_import_orders() {
        check_ajax_referer('acip_bulk', 'nonce');
        if (!current_user_can('manage_woocommerce')) {
            wp_send_json_error('forbidden');
        }
        $orders = wc_get_orders(array('limit' => 1000, 'return' => 'objects'));
        $canonical = array();
        foreach ($orders as $o) {
            $canonical[] = $this->to_canonical_order($o);
        }
        $this->client->bulk_import_orders($canonical);
        wp_send_json_success(array('count' => count($canonical)));
    }
}
