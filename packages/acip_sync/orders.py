"""Normalise store order payloads into the canonical order document.

Sibling of `normalize.py` for products: each connector (OpenCart / WooCommerce
/ generic REST) emits its own order shape; this maps them onto the explicit
order mapping (`acip_search.order_mapping`) so the orders index sees one
consistent document regardless of source.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class OrderItem:
    product_id: str
    title: str = ""
    quantity: int = 1
    price: float | None = None

    def to_doc(self) -> dict:
        doc = {
            "product_id": self.product_id,
            "title": self.title,
            "quantity": self.quantity,
            "price": self.price,
        }
        return {k: v for k, v in doc.items() if v is not None}


@dataclass
class CanonicalOrder:
    tenant_id: str
    order_id: str
    status: str = ""
    customer_email: str | None = None
    customer_name: str | None = None
    items: list[OrderItem] = field(default_factory=list)
    total: float | None = None
    currency: str | None = None
    created_at: str | None = None
    updated_at: str | None = None  # ISO-8601

    def to_doc(self) -> dict:
        doc = {
            "tenant_id": self.tenant_id,
            "order_id": self.order_id,
            "status": self.status,
            "customer_email": self.customer_email,
            "customer_name": self.customer_name,
            "items": [i.to_doc() for i in self.items],
            "total": self.total,
            "currency": self.currency,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        return {k: v for k, v in doc.items() if v is not None and v != []}


def _coerce_items(
    raw: list, *, id_key: str, title_key: str, qty_key: str, price_key: str
) -> list[OrderItem]:
    items: list[OrderItem] = []
    for row in raw or []:
        if not isinstance(row, dict):
            continue
        items.append(
            OrderItem(
                product_id=str(row.get(id_key) or ""),
                title=str(row.get(title_key) or ""),
                quantity=int(_as_float(row.get(qty_key)) or 1),
                price=_as_float(row.get(price_key)),
            )
        )
    return items


def normalize_order(tenant_id: str, source: str, raw: dict) -> CanonicalOrder:
    """Map a raw connector payload to a CanonicalOrder.

    Supports the OpenCart, WooCommerce, and generic REST order field shapes.
    """
    src = source.lower()
    if src == "opencart":
        name = " ".join(
            p for p in (raw.get("firstname"), raw.get("lastname")) if p
        ).strip() or None
        return CanonicalOrder(
            tenant_id=tenant_id,
            order_id=str(raw.get("order_id") or raw.get("id") or ""),
            status=str(raw.get("order_status") or raw.get("status") or ""),
            customer_email=raw.get("email"),
            customer_name=name,
            items=_coerce_items(
                raw.get("products") or [],
                id_key="product_id",
                title_key="name",
                qty_key="quantity",
                price_key="price",
            ),
            total=_as_float(raw.get("total")),
            currency=raw.get("currency_code") or raw.get("currency"),
            created_at=raw.get("date_added"),
            updated_at=raw.get("date_modified") or raw.get("date_added"),
        )
    if src in ("woo", "woocommerce"):
        billing = raw.get("billing") or {}
        name = " ".join(
            p for p in (billing.get("first_name"), billing.get("last_name")) if p
        ).strip() or None
        return CanonicalOrder(
            tenant_id=tenant_id,
            order_id=str(raw.get("id") or ""),
            status=str(raw.get("status") or ""),
            customer_email=billing.get("email"),
            customer_name=name,
            items=_coerce_items(
                raw.get("line_items") or [],
                id_key="product_id",
                title_key="name",
                qty_key="quantity",
                price_key="price",
            ),
            total=_as_float(raw.get("total")),
            currency=raw.get("currency"),
            created_at=raw.get("date_created_gmt") or raw.get("date_created"),
            updated_at=raw.get("date_modified_gmt") or raw.get("date_modified"),
        )
    # generic REST / canonical
    return CanonicalOrder(
        tenant_id=tenant_id,
        order_id=str(raw.get("order_id") or raw.get("id") or ""),
        status=str(raw.get("status") or ""),
        customer_email=raw.get("customer_email") or raw.get("email"),
        customer_name=raw.get("customer_name"),
        items=_coerce_items(
            raw.get("items") or [],
            id_key="product_id",
            title_key="title",
            qty_key="quantity",
            price_key="price",
        ),
        total=_as_float(raw.get("total")),
        currency=raw.get("currency"),
        created_at=raw.get("created_at"),
        updated_at=raw.get("updated_at") or raw.get("created_at"),
    )


def _as_float(v: Any) -> float | None:
    try:
        return float(v) if v is not None and v != "" else None
    except (TypeError, ValueError):
        return None


def parse_order_event(source: str, payload: dict) -> tuple[str, str, dict]:
    """Extract (event_type, order_id, raw_order) from a raw order webhook body.

    Every connector (OpenCart, WooCommerce, generic REST) wraps its push the
    same way — ``{"event": "upsert"|"delete", "order": {...}}`` — mirroring the
    product webhook envelope, so parsing is source-agnostic.
    """
    event = str(payload.get("event", "upsert")).lower()
    etype = "delete" if "delete" in event else "upsert"
    order = payload.get("order", payload)
    order_id = str(order.get("order_id") or order.get("id") or "")
    return etype, order_id, order
