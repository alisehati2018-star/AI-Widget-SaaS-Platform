"""Normalise store payloads into the canonical catalogue document (M3: REQ-M3-010).

Each connector (OpenCart / WooCommerce / REST) emits its own shape; this maps
them onto the explicit catalogue mapping (Appendix A.2) so the index sees one
consistent document regardless of source.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CanonicalProduct:
    tenant_id: str
    product_id: str
    title: str
    description: str = ""
    brand: str | None = None
    categories: list[str] = field(default_factory=list)
    attributes: dict[str, Any] = field(default_factory=dict)
    price: float | None = None
    in_stock: bool = True
    popularity: float | None = None
    updated_at: str | None = None  # ISO-8601

    def to_doc(self) -> dict:
        doc = {
            "tenant_id": self.tenant_id,
            "product_id": self.product_id,
            "title": self.title,
            "description": self.description,
            "brand": self.brand,
            "categories": self.categories,
            "attributes": self.attributes,
            "price": self.price,
            "in_stock": self.in_stock,
            "updated_at": self.updated_at,
        }
        if self.popularity is not None:
            # rank_feature must be strictly positive.
            doc["popularity"] = max(self.popularity, 1e-6)
        return {k: v for k, v in doc.items() if v is not None}

    def embedding_text(self) -> str:
        """Build the text that gets embedded into the dense vector.

        Brand and categories MUST be embedded with the product (not only stored
        as BM25 keyword fields) so the semantic leg can match a shopper who
        searches by brand, category, or a key attribute — even with a synonym or
        a different spelling. Order: title → brand → categories → salient
        attributes → description.
        """
        parts: list[str] = []
        if self.title:
            parts.append(self.title.strip())
        if self.brand:
            parts.append(f"برند: {self.brand}")
        if self.categories:
            cats = "، ".join(str(c).strip() for c in self.categories if str(c).strip())
            if cats:
                parts.append(f"دسته‌بندی: {cats}")
        if self.attributes:
            attr_bits: list[str] = []
            for name, value in self.attributes.items():
                if value is None or value == "" or value == []:
                    continue
                if isinstance(value, (list, tuple)):
                    value = "، ".join(str(v) for v in value if str(v).strip())
                attr_bits.append(f"{name}: {value}")
            if attr_bits:
                parts.append("ویژگی‌ها: " + " | ".join(attr_bits))
        if self.description:
            parts.append(self.description.strip())
        return "\n".join(p for p in parts if p)


def _coerce_categories(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(c) for c in raw]
    return [str(raw)]


def normalize_product(tenant_id: str, source: str, raw: dict) -> CanonicalProduct:
    """Map a raw connector payload to a CanonicalProduct.

    Supports the OpenCart, WooCommerce, and generic REST field shapes. Unknown
    sources fall through to the REST/canonical shape.
    """
    src = source.lower()
    if src == "opencart":
        return CanonicalProduct(
            tenant_id=tenant_id,
            product_id=str(raw.get("product_id") or raw.get("id")),
            title=str(raw.get("name") or raw.get("title") or ""),
            description=str(raw.get("description") or ""),
            brand=raw.get("manufacturer") or raw.get("brand"),
            categories=_coerce_categories(raw.get("categories")),
            attributes=raw.get("attributes") or {},
            price=_as_float(raw.get("price")),
            in_stock=_as_bool(raw.get("quantity"), raw.get("in_stock")),
            updated_at=raw.get("date_modified") or raw.get("updated_at"),
        )
    if src in ("woo", "woocommerce"):
        return CanonicalProduct(
            tenant_id=tenant_id,
            product_id=str(raw.get("id")),
            title=str(raw.get("name") or ""),
            description=str(raw.get("description") or raw.get("short_description") or ""),
            brand=_woo_brand(raw),
            categories=[
                c.get("name", "") for c in raw.get("categories", []) if isinstance(c, dict)
            ],
            attributes={
                str(a.get("name")): a.get("options")
                for a in raw.get("attributes", [])
                if isinstance(a, dict) and a.get("name")
            },
            price=_as_float(raw.get("price")),
            in_stock=(raw.get("stock_status", "instock") == "instock"),
            updated_at=raw.get("date_modified_gmt") or raw.get("date_modified"),
        )
    # generic REST / canonical
    return CanonicalProduct(
        tenant_id=tenant_id,
        product_id=str(raw.get("product_id") or raw.get("id")),
        title=str(raw.get("title") or raw.get("name") or ""),
        description=str(raw.get("description") or ""),
        brand=raw.get("brand"),
        categories=_coerce_categories(raw.get("categories")),
        attributes=raw.get("attributes") or {},
        price=_as_float(raw.get("price")),
        in_stock=bool(raw.get("in_stock", True)),
        updated_at=raw.get("updated_at"),
    )


def _as_float(v: Any) -> float | None:
    try:
        return float(v) if v is not None and v != "" else None
    except (TypeError, ValueError):
        return None


def _as_bool(quantity: Any, in_stock_flag: Any) -> bool:
    if in_stock_flag is not None:
        return bool(in_stock_flag)
    try:
        return float(quantity) > 0
    except (TypeError, ValueError):
        return True


def _woo_brand(raw: dict) -> str | None:
    brands = raw.get("brands")
    if isinstance(brands, list) and brands and isinstance(brands[0], dict):
        return brands[0].get("name")
    return raw.get("brand")
