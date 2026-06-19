"""Operator/admin API surface (blueprint §12). Contract skeleton only.

  /admin/tenants    -> M11/M9, Phase 2-3
  /admin/analytics  -> M9/M10, Phase 2
  /admin/synonyms   -> M2/M9, Phase 1-2
The admin plane is auth-separated from tenant APIs (§9.2); enforcement is M11.
"""

from __future__ import annotations

from acip_core.errors import not_implemented
from fastapi import APIRouter

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/tenants")
async def create_tenant():
    return not_implemented("Tenant management (/admin/tenants, M11)")


@router.get("/analytics")
async def analytics():
    return not_implemented("Analytics (/admin/analytics, M9/M10)")


@router.get("/synonyms")
async def synonyms():
    return not_implemented("Synonym management (/admin/synonyms, M2/M9)")
