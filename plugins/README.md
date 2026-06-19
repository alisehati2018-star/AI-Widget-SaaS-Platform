# Store plugins (M8 — Phase 1 subset)

Phase 1 ships the **pilot subset** of M8: connectors that (a) replace the
store's native search with ACIP `/v1/search` and (b) post change webhooks to
`/v1/sync/webhook`. The full embeddable widget, white-label, and citation cards
are Phase 2 (M8 full).

| Plugin | Platform | Phase-1 responsibility |
|---|---|---|
| `opencart/` | OpenCart | Replace native search; product/inventory change webhooks (REQ-M8-002, REQ-M3-007) |
| `woocommerce/` | WordPress / WooCommerce | Replace native search; product/order webhooks (REQ-M8-003, REQ-M3-008) |

Both call the ACIP API with a tenant-scoped `x-api-key` (widget scope for
search; sync scope for webhooks). These are integration scaffolds intended to be
packaged for their platforms during pilot onboarding; they are not exercised by
the Python test suite.
