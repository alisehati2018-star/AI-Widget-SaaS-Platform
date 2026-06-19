# ACIP Embeddable Widget (M8)

A lightweight, framework-free widget (`acip-widget.ts`) that a store page embeds
to replace native search and host the grounded assistant. It calls the public
API (`/v1/search`, `/v1/chat`) with a **shopper-widget (least-privilege)** key
and supports **white-label** branding (logo + colours) — presentation-only, it
never weakens tenant isolation (REQ-M8-001/004/005).

## Embed

```html
<div id="acip-widget"></div>
<script type="module">
  import { mountAcipWidget } from "/widget/acip-widget.js";
  mountAcipWidget(document.getElementById("acip-widget"), {
    apiBase: "https://store.example.com",
    apiKey: "acip_...",        // shopper-widget key (issued via /admin/tenants)
    primaryColor: "#1A7A4B",
    logoUrl: "/logo.png",
  });
</script>
```

The widget renders a search box (hybrid results) and an assistant panel with
citation cards from the answer's evidence. Store-platform packaging (OpenCart
module / WooCommerce plugin) lives under `plugins/`.

> Runtime validation (embedding in a real store page, white-label render) is
> deferred to the Validation & Acceptance phase — see
> `reports/deferred-validation.md` (DV-109).
