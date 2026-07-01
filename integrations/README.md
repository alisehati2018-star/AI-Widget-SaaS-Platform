# ACIP store integrations

Production-ready store-platform integrations that connect a merchant's
storefront to ACIP: hybrid search, the grounded assistant widget, and
catalogue sync (with brand + categories + attributes indexed *with* each
product).

| Folder | Platform | Type |
|---|---|---|
| [`opencart3/`](opencart3/) | OpenCart 3.x | Module + OCMOD (admin settings, test-connection, event-registered sync + widget injection, bulk import, optional search override, `en-gb` + `fa` admin languages) |
| [`wordpress/acip-search/`](wordpress/acip-search/) | WordPress / WooCommerce (latest) | Plugin (settings page with test-connection, enqueued assets, real-time + bulk sync, widget injection, search replacement, clean uninstall, `fa_IR` translation) |

Both follow their platform's real packaging conventions end to end — OpenCart's
`admin/`, `catalog/`, `system/` tree and language files; WordPress's
`includes/`, `assets/`, `languages/`, `uninstall.php`, and directory-listing
guards — so each can be installed as-is on a fresh store.

Both talk only to the ACIP public API with tenant-scoped keys:

- **widget key** — least-privilege (storefront search + chat); safe to ship to the browser.
- **sync key** — catalogue ingest; server-side only.

The single-line widget embed both integrations inject:

```html
<script src="https://api.acip.example/widget/v1.js"
        data-acip-key="acip_widget_xxx"
        data-acip-base="https://api.acip.example" async></script>
```

> The earlier single-file pilots under `/plugins` are superseded by these
> packaged integrations.
