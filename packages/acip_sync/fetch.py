"""Store-side pull clients for delta reconciliation (M3: REQ-M3-002/012, Phase 7).

Webhook push (the fast path) can lose events; these fetchers let the periodic
reconciliation PULL everything changed since the watermark straight from the
store, so the index converges even if every webhook is lost.

Two real store backends:

* **WooCommerce** — the standard REST API (`/wp-json/wc/v3/products`) with the
  read-only consumer key/secret the owner creates in WooCommerce → Settings →
  Advanced → REST API. Over HTTPS credentials go as basic auth; over plain HTTP
  (local pilots) WooCommerce only accepts them as query parameters.
* **OpenCart 3** — the ACIP module's own catalog export endpoint
  (`index.php?route=extension/module/acip/export`), protected by the export
  token the admin sets in the module and mirrors into the Vitrin dashboard.

Both yield RAW platform payloads; `normalize_product` maps them to the
canonical document downstream.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from urllib.parse import urlsplit

import httpx
from acip_core.logging import get_logger

log = get_logger("sync.fetch")

PAGE_SIZE = 100
_TIMEOUT = 15.0


def _base(store_url: str) -> str:
    return store_url.rstrip("/")


async def fetch_woo_changed(
    store_url: str,
    consumer_key: str,
    consumer_secret: str,
    since: str | None = None,
    *,
    page_size: int = PAGE_SIZE,
    client: httpx.AsyncClient | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Yield WooCommerce products modified since the watermark (paged)."""
    own_client = client is None
    http = client or httpx.AsyncClient(timeout=_TIMEOUT)
    try:
        page = 1
        while True:
            params: dict[str, Any] = {
                "per_page": page_size,
                "page": page,
                "orderby": "modified",
                "order": "asc",
                "status": "publish",
            }
            if since:
                # The watermark comes from `date_modified_gmt`; tell Woo to
                # compare in GMT too, or site-timezone offsets skip products.
                params["modified_after"] = since
                params["dates_are_gmt"] = "true"
            auth = None
            if urlsplit(store_url).scheme == "https":
                auth = (consumer_key, consumer_secret)
            else:
                # WooCommerce only accepts key/secret as query params over HTTP.
                params["consumer_key"] = consumer_key
                params["consumer_secret"] = consumer_secret
            resp = await http.get(
                f"{_base(store_url)}/wp-json/wc/v3/products", params=params, auth=auth
            )
            resp.raise_for_status()
            products = resp.json()
            if not isinstance(products, list):
                raise ValueError("unexpected WooCommerce products payload")
            for raw in products:
                yield raw
            if len(products) < page_size:
                return
            page += 1
    finally:
        if own_client:
            await http.aclose()


async def fetch_opencart_changed(
    store_url: str,
    export_token: str,
    since: str | None = None,
    *,
    page_size: int = PAGE_SIZE,
    client: httpx.AsyncClient | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Yield OpenCart products from the ACIP module's export endpoint (paged)."""
    own_client = client is None
    http = client or httpx.AsyncClient(timeout=_TIMEOUT)
    try:
        page = 1
        while True:
            params: dict[str, Any] = {
                "route": "extension/module/acip/export",
                "limit": page_size,
                "page": page,
            }
            if since:
                # OpenCart's date_modified is store-local wall-clock time; send
                # the watermark's bare digits back (no offset) so PHP does not
                # shift it into another timezone and skip fresh products.
                params["since"] = since.replace("T", " ").split("+")[0].split(".")[0]
            resp = await http.get(
                f"{_base(store_url)}/index.php",
                params=params,
                headers={"X-Acip-Token": export_token},
            )
            resp.raise_for_status()
            body = resp.json()
            products = body.get("products", [])
            for raw in products:
                yield raw
            if not body.get("more"):
                return
            page += 1
    finally:
        if own_client:
            await http.aclose()


def fetch_changed_since(
    source: str,
    settings: dict[str, Any],
    since: str | None,
    *,
    client: httpx.AsyncClient | None = None,
) -> AsyncIterator[dict[str, Any]] | None:
    """Build the pull iterator for a tenant's connected store.

    Returns ``None`` when the tenant hasn't configured pull credentials for
    this source (custom REST integrations push; there is nothing to pull).
    """
    store_url = str(settings.get("store_url") or "").strip()
    src = source.lower()
    if not store_url:
        return None
    if src in ("woo", "woocommerce"):
        ck = str(settings.get("woo_consumer_key") or "").strip()
        cs = str(settings.get("woo_consumer_secret") or "").strip()
        if not ck or not cs:
            return None
        return fetch_woo_changed(store_url, ck, cs, since, client=client)
    if src == "opencart":
        token = str(settings.get("oc_export_token") or "").strip()
        if not token:
            return None
        return fetch_opencart_changed(store_url, token, since, client=client)
    return None
