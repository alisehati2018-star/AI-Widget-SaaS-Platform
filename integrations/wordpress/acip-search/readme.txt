=== ACIP — Smart Search & Assistant ===
Contributors: acip
Tags: search, woocommerce, ai, assistant, persian, elasticsearch
Requires at least: 6.0
Tested up to: 6.7
Requires PHP: 7.4
Stable tag: 1.0.0
License: GPLv2 or later
License URI: https://www.gnu.org/licenses/gpl-2.0.html

Replace WooCommerce native search with ACIP hybrid Persian search, embed the
grounded AI shopping assistant, and keep your catalogue synced to ACIP.

== Description ==

ACIP turns WooCommerce search into a hybrid (keyword + semantic) Persian search
engine and adds a grounded AI shopping assistant that answers only from your own
catalogue. The plugin:

* Injects the single-line ACIP widget loader on every storefront page.
* Optionally replaces the native shop search with ACIP-ranked results.
* Syncs product create / update / delete to ACIP in real time — including brand,
  categories, and attributes, which are indexed *with* each product.
* Offers a one-click bulk import to build the initial index.

== Installation ==

1. Upload the `acip-search` folder to `/wp-content/plugins/`, or install the zip
   via **Plugins → Add New → Upload Plugin**.
2. Activate the plugin.
3. Go to **WooCommerce → ACIP Search** and enter:
   * **ACIP API URL** (e.g. `https://api.acip.example`)
   * **Widget API Key** — a *widget*-scoped key from your ACIP dashboard.
   * **Sync API Key** — a *sync*-scoped key from your ACIP dashboard.
4. Enable the plugin, choose whether to replace native search, and **Save**.
5. Click **Bulk import now** for the initial catalogue index.

== Frequently Asked Questions ==

= Is the widget key safe to expose? =
Yes. The widget key is least-privilege (search + chat only) and tenant-scoped.
The sync key ingests the catalogue and is only ever used server-side.

= Does it require Elasticsearch on my server? =
No. ACIP runs the search/AI stack; the plugin only talks to the ACIP API.

== Changelog ==

= 1.0.0 =
* Initial release: hybrid search, assistant widget, real-time + bulk sync.
