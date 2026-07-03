"""Pilot store simulator — a tiny local "shop" for integration pilots (Phase 7).

Emulates BOTH store backends Vitrin pulls from, with a small Persian catalogue:

* WooCommerce REST:  GET /wp-json/wc/v3/products
  (consumer_key/consumer_secret as query params over HTTP, paging,
  `modified_after` + `dates_are_gmt` filtering — same contract as real Woo)
* OpenCart ACIP module export:  GET /index.php?route=extension/module/acip/export
  (X-Acip-Token header, `since` wall-clock filter, `page`/`limit`, `more` flag)

Also exposes POST /touch/{id} to bump a product's modified time — edit a
product "in the store" and watch the next reconciliation pick it up.

Usage:
    PYTHONPATH=packages:services python scripts/pilot_store.py --port 9099
    # credentials the simulator accepts:
    #   Woo:      consumer key  ck_pilot   secret  cs_pilot
    #   OpenCart: export token  pilot-token

Windows PowerShell:
    $env:PYTHONPATH = "packages;services"
    python scripts/pilot_store.py --port 9099
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime

import uvicorn
from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse

WOO_CK, WOO_CS = "ck_pilot", "cs_pilot"
OC_TOKEN = "pilot-token"

_BASE = "2026-06-0{d}T0{h}:00:00"

# One catalogue, two projections (Woo shape / OpenCart shape).
PRODUCTS: list[dict] = [
    {"id": 1, "name": "گوشی موبایل سامسونگ گلکسی A55", "brand": "سامسونگ",
     "cats": ["موبایل"], "price": "18500000", "stock": True, "m": _BASE.format(d=1, h=1)},
    {"id": 2, "name": "گوشی موبایل شیائومی ردمی نوت 13", "brand": "شیائومی",
     "cats": ["موبایل"], "price": "12900000", "stock": True, "m": _BASE.format(d=1, h=2)},
    {"id": 3, "name": "لپ تاپ ایسوس ویووبوک 15", "brand": "ایسوس",
     "cats": ["لپ‌تاپ"], "price": "38500000", "stock": True, "m": _BASE.format(d=2, h=1)},
    {"id": 4, "name": "کفش ورزشی نایکی ایرمکس", "brand": "نایکی",
     "cats": ["کفش"], "price": "5200000", "stock": True, "m": _BASE.format(d=2, h=2)},
    {"id": 5, "name": "هدفون بی سیم سونی WH-1000XM5", "brand": "سونی",
     "cats": ["صوتی"], "price": "21500000", "stock": False, "m": _BASE.format(d=3, h=1)},
    {"id": 6, "name": "تلویزیون هوشمند ال جی 55 اینچ", "brand": "ال جی",
     "cats": ["تلویزیون"], "price": "42800000", "stock": True, "m": _BASE.format(d=3, h=2)},
    {"id": 7, "name": "ساعت هوشمند اپل واچ SE", "brand": "اپل",
     "cats": ["ساعت هوشمند"], "price": "16900000", "stock": True, "m": _BASE.format(d=4, h=1)},
    {"id": 8, "name": "ماشین اصلاح فیلیپس سری 5000", "brand": "فیلیپس",
     "cats": ["لوازم شخصی"], "price": "4300000", "stock": True, "m": _BASE.format(d=4, h=2)},
]

app = FastAPI(title="Vitrin pilot store", docs_url=None, redoc_url=None)


def _woo_shape(p: dict) -> dict:
    return {
        "id": p["id"],
        "name": p["name"],
        "description": f"{p['name']} — کالای نمونهٔ فروشگاه pilot",
        "brands": [{"name": p["brand"]}],
        "categories": [{"name": c} for c in p["cats"]],
        "attributes": [],
        "price": p["price"],
        "stock_status": "instock" if p["stock"] else "outofstock",
        "date_modified_gmt": p["m"],
    }


def _oc_shape(p: dict) -> dict:
    return {
        "product_id": p["id"],
        "name": p["name"],
        "description": f"{p['name']} — کالای نمونهٔ فروشگاه pilot",
        "manufacturer": p["brand"],
        "categories": p["cats"],
        "attributes": {},
        "price": float(p["price"]),
        "quantity": 5 if p["stock"] else 0,
        "date_modified": p["m"].replace("T", " "),
    }


@app.get("/wp-json/wc/v3/products")
async def woo_products(request: Request):
    q = request.query_params
    if q.get("consumer_key") != WOO_CK or q.get("consumer_secret") != WOO_CS:
        return JSONResponse({"code": "woocommerce_rest_cannot_view"}, status_code=401)
    per_page = max(1, min(100, int(q.get("per_page", "10"))))
    page = max(1, int(q.get("page", "1")))
    since = q.get("modified_after")
    items = sorted(PRODUCTS, key=lambda p: p["m"])
    if since:
        bare = since.replace("Z", "").split("+")[0]
        items = [p for p in items if p["m"] > bare]
    window = items[(page - 1) * per_page : (page - 1) * per_page + per_page]
    return [_woo_shape(p) for p in window]


@app.get("/index.php")
async def opencart_router(request: Request, x_acip_token: str | None = Header(default=None)):
    q = request.query_params
    if q.get("route") != "extension/module/acip/export":
        return JSONResponse({"error": "unknown_route"}, status_code=404)
    if x_acip_token != OC_TOKEN:
        return JSONResponse({"error": "forbidden"}, status_code=403)
    limit = max(1, min(500, int(q.get("limit", "100"))))
    page = max(1, int(q.get("page", "1")))
    since = q.get("since")
    items = sorted(PRODUCTS, key=lambda p: p["m"])
    if since:
        items = [p for p in items if p["m"].replace("T", " ") > since]
    window = items[(page - 1) * limit : (page - 1) * limit + limit]
    more = len(items) > page * limit
    return {"products": [_oc_shape(p) for p in window], "more": more, "page": page}


@app.post("/touch/{product_id}")
async def touch(product_id: int):
    """Simulate editing a product in the store admin (bumps date_modified)."""
    for p in PRODUCTS:
        if p["id"] == product_id:
            p["m"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S")
            return {"touched": product_id, "date_modified": p["m"]}
    return JSONResponse({"error": "not_found"}, status_code=404)


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "products": len(PRODUCTS)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=9099)
    args = parser.parse_args()
    print(f"pilot store on http://127.0.0.1:{args.port}")
    print(f"  Woo:      ck={WOO_CK} cs={WOO_CS}")
    print(f"  OpenCart: token={OC_TOKEN}")
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
