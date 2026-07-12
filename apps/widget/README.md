# Vitrin Embeddable Widget Loader (M8)

`loader.js` is the single-line, framework-free script a store drops into its
site. The API serves it verbatim at **`GET /widget/v1.js`**
(`services/api/routers/widget.py`); there is no build step.

## Embed (what the store copies from its dashboard)

```html
<script src="https://api.example.com/widget/v1.js"
        data-acip-key="acip_xxx"
        data-acip-base="https://api.example.com"
        async></script>
```

On load it fetches the store's published widget config
(`/v1/widget/config` — operator defaults merged with the tenant's dashboard
settings: colours, logo, greeting, position, chat/search toggles) and mounts a
floating launcher with hybrid search + grounded chat. It talks only to the
public API (`/v1/search`, `/v1/chat`) with a shopper-scoped
(least-privilege) widget key — white-labeling is presentation-only and never
weakens tenant isolation (REQ-M8-001/004/005).

Store-platform packaging (OpenCart module / WordPress plugin) lives under
`plugins/`.
