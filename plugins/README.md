# ACIP store plugins (M8 — full CMS-native modules)

Production-ready, CMS-native modules that connect a merchant's storefront to
ACIP: hybrid search, the grounded assistant widget, and catalogue **and order**
sync to Elasticsearch — all authenticated with the tenant's own ACIP API keys
(the same keys and plan/credit quota used everywhere else on the platform).

| Folder | Platform | Type |
|---|---|---|
| [`opencart3/`](opencart3/) | OpenCart 3.x | Module + OCMOD (admin settings, test-connection, event-registered product **and order** sync + widget injection, bulk import, optional search override, `en-gb` + `fa` admin languages) |
| [`wordpress/acip-search/`](wordpress/acip-search/) | WordPress / WooCommerce (latest) | Plugin (settings page with test-connection, enqueued assets, real-time + bulk product **and order** sync, widget injection, search replacement, clean uninstall, `fa_IR` translation) |

Both follow their platform's real packaging conventions end to end — OpenCart's
`admin/`, `catalog/`, `system/` tree and language files; WordPress's
`includes/`, `assets/`, `languages/`, `uninstall.php`, and directory-listing
guards — so each can be uploaded and installed as-is on a fresh store, then
configured entirely from that store's own admin panel.

## Authentication & security

Every call from a module to ACIP is authenticated with a tenant-scoped API key
generated from **Dashboard → API Keys** (`/dashboard/keys`) — the same screen
that issues every other ACIP key, so usage is metered and billed against the
tenant's own plan/credit quota, exactly as with any other integration:

- **widget key** — least privilege: storefront search + chat only. Safe to ship
  to the browser (it cannot sync, import, or delete anything).
- **sync key** — catalogue + order ingest (webhook + bulk). Server-side only;
  never exposed to the storefront.

On top of key-scoped auth, every webhook call is **HMAC-signed** (SHA-256, a
per-tenant secret set in the module) and verified server-side before any data
is written, and every response uses the platform's stable
`{"error": {"code", "message", "request_id"}}` envelope. See
**[`docs/api-reference-fa.md`](../docs/api-reference-fa.md)** for the complete
API contract (auth, all endpoints, product **and order** payload shapes, error
codes) and **[`docs/integrations-fa.md`](../docs/integrations-fa.md)** for the
step-by-step install/connect walkthrough.

The single-line widget embed both modules inject:

```html
<script src="https://api.acip.example/widget/v1.js"
        data-acip-key="acip_widget_xxx"
        data-acip-base="https://api.acip.example" async></script>
```
