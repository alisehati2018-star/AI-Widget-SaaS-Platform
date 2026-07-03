"""Server-side PDF invoices with proper Persian shaping (Phase 10).

Uses fpdf2 + uharfbuzz (text shaping) with any installed Persian-capable TTF —
searched in order: ``INVOICE_FONT_PATH`` → Vazirmatn → common Linux fonts →
Windows fonts. When no font (or fpdf2) is available the caller degrades to the
printable HTML invoice instead of failing the request.
"""

from __future__ import annotations

import os
from pathlib import Path

_FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/vazirmatn/Vazirmatn-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSerif.ttf",
    "C:/Windows/Fonts/Vazirmatn-Regular.ttf",
    "C:/Windows/Fonts/tahoma.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
)


def find_font(configured: str = "") -> str | None:
    for candidate in (configured or os.environ.get("INVOICE_FONT_PATH", ""), *_FONT_CANDIDATES):
        if candidate and Path(candidate).is_file():
            return candidate
    return None


def render_invoice_pdf(
    *,
    number: int,
    store: str,
    date: str,
    description: str,
    amount: str,
    currency: str,
    status_fa: str,
    font_path: str | None = None,
) -> bytes | None:
    """Render the invoice as PDF bytes, or None when PDF support is missing."""
    font = font_path or find_font()
    if font is None:
        return None
    try:
        from fpdf import FPDF
        from fpdf.enums import TextDirection
    except ImportError:
        return None

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    pdf.add_font("fa", "", font)
    pdf.set_text_shaping(use_shaping_engine=True, direction=TextDirection.RTL, language="fa")

    pdf.set_font("fa", size=16)
    pdf.cell(0, 12, f"فاکتور شمارهٔ {number}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("fa", size=10)
    pdf.cell(0, 8, f"{status_fa} · {date}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 8, f"فروشگاه: {store}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    # Two-column table, right-aligned (RTL): شرح | مبلغ
    col_desc, col_amount = 130, 60
    pdf.set_font("fa", size=11)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(col_amount, 10, "مبلغ", border=1, align="C", fill=True)
    pdf.cell(col_desc, 10, "شرح", border=1, align="C", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.cell(col_amount, 10, f"{amount} {currency}", border=1, align="C")
    pdf.cell(col_desc, 10, description, border=1, align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("fa", size=12)
    pdf.cell(col_amount, 10, f"{amount} {currency}", border=1, align="C")
    pdf.cell(col_desc, 10, "جمع کل", border=1, align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(8)
    pdf.set_font("fa", size=9)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(0, 6, "این فاکتور توسط پلتفرم ویترین صادر شده است.", align="C")

    return bytes(pdf.output())
