# ACIP — OpenCart 3.x Module

Replaces OpenCart's native catalogue search with ACIP hybrid Persian search,
embeds the grounded shopping assistant widget, and keeps the catalogue synced to
ACIP via the admin event system.

## What it does
- **Admin settings page** (Extensions → Modules → *ACIP — Smart Search & Assistant*):
  API URL, widget key, sync key, toggles for search replacement and widget injection.
- **One-click bulk import** of the active catalogue (initial index build).
- **Event-driven sync** — product add / edit / delete are pushed to
  `/v1/sync/webhook` (brand + categories + attributes included).
- **Single-line widget** injected on every storefront page via an OCMOD that
  registers the footer event (no core template edits).

## Install
1. **Admin → Extensions → Installer** and upload this folder zipped as
   `acip_search.ocmod.zip` (the `upload/` tree + `install.xml`), **or** copy the
   contents of `upload/` into your OpenCart root and upload `install.xml` under
   **Extensions → Modifications**.
2. **Extensions → Modifications → Refresh** to apply the OCMOD.
3. **Extensions → Modules → ACIP → Install**, then **Edit**:
   - **ACIP API URL** — e.g. `https://api.acip.example`
   - **Widget API Key** — a *widget*-scoped key from your ACIP dashboard.
   - **Sync API Key** — a *sync*-scoped key from your ACIP dashboard.
   - Enable **Status**, choose whether to replace native search / inject the widget.
4. Click **Bulk import catalogue now** for the initial index.

## Files
```
upload/
  admin/controller/extension/module/acip.php   # settings + events + bulk import
  admin/model/extension/module/acip.php         # product → ACIP canonical shape
  admin/view/template/extension/module/acip.twig
  admin/language/en-gb/extension/module/acip.php
  catalog/controller/extension/module/acip.php  # widget injection + search proxy
  system/library/acip.php                       # API client (search/sync/bulk)
install.xml                                      # OCMOD: footer event + search hook
```

## Keys & isolation
The widget key is storefront-safe (least privilege: search + chat only). The
sync key ingests the catalogue and must stay server-side (admin settings only).
Both are tenant-scoped — a store can only ever read/write its own data.
