#!/usr/bin/env python3
"""Backend file-size gate — mirrors apps/web/scripts/fe-qa/check-size.mjs.

Flags Python files under packages/, services/, eval/ and scripts/ that exceed
the line-count ceiling, so oversized modules get decomposed into cohesive
per-domain files (the pattern already applied to the admin/tenant/auth/billing
routers: a slim entrypoint + shared `*_common.py` helpers + focused siblings).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIMIT = 400
DIRS = ("packages", "services", "eval", "scripts")
EXCLUDE_DIRS = {"__pycache__", ".venv", "node_modules"}


def _files() -> list[Path]:
    found: list[Path] = []
    for d in DIRS:
        base = ROOT / d
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            if not any(part in EXCLUDE_DIRS for part in path.parts):
                found.append(path)
    return sorted(found)


def main() -> int:
    violations = 0
    for path in _files():
        lines = len(path.read_text(encoding="utf-8").splitlines())
        if lines > LIMIT:
            rel = path.relative_to(ROOT)
            print(f"✗ oversized: {rel} — {lines} lines (limit {LIMIT})")
            violations += 1
    print(f"\ncheck_backend_size: {violations} file(s) over {LIMIT} lines.")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
