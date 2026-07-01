# ACIP — OpenCart 3.x Module

Replaces OpenCart's native catalogue search with ACIP hybrid Persian search,
embeds the grounded shopping assistant widget, and keeps the catalogue synced to
ACIP via the admin event system.

## What it does
- **Admin settings page** (Extensions → Modules → *ACIP — Smart Search & Assistant*):
  API URL, widget key, sync key, toggles for search replacement and widget injection.
- **Test connection** button — verifies the API URL is reachable before saving,
  using the posted (not-yet-saved) values.
- **One-click bulk import** of the active catalogue (initial index build).
- **Event-driven sync** — product add / edit / delete are pushed to
  `/v1/sync/webhook` (brand + categories + attributes included, so they are
  indexed *with* the product, not just as separate keyword filters).
- **Single-line widget** injected on every storefront page via the OC3 event
  table (`catalog/view/common/footer/after`) — no core template edits.
- **Optional search override** (OCMOD) — prepends ACIP-ranked product ids ahead
  of native search results when "Replace native search" is enabled.
- **Bilingual admin UI** — English (`en-gb`) and Persian (`fa`) language packs.

## Install
1. **Admin → Extensions → Installer** and upload this folder zipped as
   `acip_search.ocmod.zip` (the `upload/` tree + `install.xml`), **or** copy the
   contents of `upload/` into your OpenCart root and upload `install.xml` under
   **Extensions → Modifications**.
2. **Extensions → Modifications → Refresh** to apply the OCMOD.
3. **Extensions → Modules → ACIP → Install** — this registers the footer
   widget-injection event and the product add/edit/delete sync events
   automatically (OC3 event table, no manual wiring needed).
4. **Edit** the module:
   - **ACIP API URL** — e.g. `https://api.acip.example` (use **Test connection**
     to confirm it's reachable before saving).
   - **Widget API Key** — a *widget*-scoped key from your ACIP dashboard.
   - **Sync API Key** — a *sync*-scoped key from your ACIP dashboard.
   - Enable **Status**, choose whether to replace native search / inject the widget.
5. Click **Bulk import catalogue now** for the initial index.
6. **Uninstalling** the module automatically removes all four registered events
   (product edit/add/delete + footer injection) — no leftover hooks.

## Files
```
upload/
  admin/
    controller/extension/module/acip.php        # settings, test-connection, events, bulk import
    model/extension/module/acip.php               # product → ACIP canonical shape
    view/template/extension/module/acip.twig      # settings page UI
    language/en-gb/extension/module/acip.php      # English admin strings
    language/fa/extension/module/acip.php         # Persian admin strings
  catalog/
    controller/extension/module/acip.php          # widget injection + search proxy
  system/
    library/acip.php                              # API client (search/sync/bulk/ping)
install.xml                                        # OCMOD: optional native-search override
```

This mirrors OpenCart's own `admin/`, `catalog/`, `system/` tree exactly, so the
`upload/` folder can be copied straight into an OpenCart 3.x installation root.

## Keys & isolation
The widget key is storefront-safe (least privilege: search + chat only). The
sync key ingests the catalogue and must stay server-side (admin settings only).
Both are tenant-scoped — a store can only ever read/write its own data.
