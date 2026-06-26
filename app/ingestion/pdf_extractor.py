"""
pdf_extractor.py — black-box text extraction layer.

Pulls raw text and tables from every page of a PDF. The caller (routes_ingest)
sends those chunks to the LLM for schema mapping.  All the pdfplumber logic
lives here; the LLM mapping logic lives in routes_ingest.py.
"""
from __future__ import annotations
import io, re
import pdfplumber


def extract_pdf(data: bytes) -> dict:
    """Return {pages: [{page, text, tables}], all_text: str} for a PDF."""
    pages = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            text  = (page.extract_text() or "").strip()
            tables = []
            for t in page.extract_tables():
                # collapse multi-line merged cells; drop fully-blank rows
                cleaned = []
                for row in t:
                    cells = []
                    for c in row:
                        cells.append(str(c).replace("\n"," ").strip() if c else "")
                    if any(cells):
                        cleaned.append(cells)
                if cleaned:
                    tables.append(cleaned)
            if text or tables:
                pages.append({"page": i, "text": text[:3000], "tables": tables})

    all_text = "\n\n".join(p["text"] for p in pages if p["text"])
    return {"pages": pages, "all_text": all_text}


def tables_as_text(pages: list[dict]) -> str:
    """Render all extracted tables as labelled text blocks for the LLM prompt."""
    out = []
    for p in pages:
        for j, table in enumerate(p.get("tables", []), 1):
            header = " | ".join(table[0]) if table else ""
            rows   = "\n".join(" | ".join(r) for r in table[1:])
            out.append(f"[Page {p['page']} Table {j}]\n{header}\n{rows}")
    return "\n\n".join(out)