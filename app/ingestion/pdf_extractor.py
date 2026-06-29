"""
pdf_extractor.py — algorithmic PDF table extraction layer (v2).

Two stages:
  1. EXTRACT  — pdfplumber finds all tables and captures surrounding context
                (page number, lines of text above the table that likely
                contain the table title, and the column headers).
  2. CLASSIFY — lightweight heuristics identify what kind of data each table
                likely contains before the LLM sees it, so the LLM prompt
                can be targeted rather than generic.

The LLM mapping layer lives in routes_ingest.py and calls into this module.
"""
from __future__ import annotations
import io, re
from dataclasses import dataclass, field
from typing import Optional
import pdfplumber


# ── data structures ───────────────────────────────────────────────────────────

@dataclass
class ExtractedTable:
    """One table extracted from a PDF page with surrounding context."""
    page:        int
    table_index: int            # nth table on this page (1-based)
    title:       Optional[str]  # best-guess title from text above the table
    headers:     list[str]      # first data row treated as headers
    rows:        list[list[str]]# data rows (excluding header)
    raw_text_above: str         # raw text above table on this page (for context)
    table_type:  Optional[str]  # heuristic classification (see _classify)

    def as_text(self, max_chars: int = 4000) -> str:
        """
        Render as labelled text block for the LLM prompt.
        Hard cap at max_chars to stay within Groq token limits.
        If the table is truncated, a note is appended.
        """
        parts = []
        if self.title:
            parts.append(f"Table title: {self.title}")
        parts.append(f"[Page {self.page}, Table {self.table_index}]")
        parts.append(" | ".join(str(h) for h in self.headers))

        char_count = sum(len(p) for p in parts)
        rows_included = 0

        for row in self.rows:
            line = " | ".join(str(c) for c in row)
            if char_count + len(line) + 1 > max_chars:
                break
            parts.append(line)
            char_count += len(line) + 1
            rows_included += 1

        skipped = len(self.rows) - rows_included
        if skipped > 0:
            parts.append(
                f"[TABLE TRUNCATED: {skipped} of {len(self.rows)} rows omitted "
                f"to fit token limit. Extract from the rows shown only.]"
            )
        return "\n".join(parts)

    def column_count(self) -> int:
        return len(self.headers)

    def row_count(self) -> int:
        return len(self.rows)


# ── title extraction ──────────────────────────────────────────────────────────

_TABLE_TITLE_PATTERNS = [
    # "Table 5 Laboratory Test Results Summary"
    re.compile(r'(?:^|\n)(Table\s+\d+[A-Za-z]?[\s\.:–-]+.{5,80})', re.IGNORECASE),
    # "5.1 In-Situ Testing"
    re.compile(r'(?:^|\n)(\d+(?:\.\d+)*\s+[A-Z][A-Za-z\s/()-]{5,60})', re.MULTILINE),
    # bold-ish standalone line (short, title-case, ends without period)
    re.compile(r'(?:^|\n)([A-Z][A-Za-z\s/()-]{8,60})(?:\n|$)'),
]

def _extract_title(text_above: str) -> Optional[str]:
    """
    Pull the most likely table title from the text immediately above the table.
    Prefers 'Table N …' patterns, falls back to short standalone lines.
    """
    if not text_above:
        return None
    # Try patterns in priority order
    for pattern in _TABLE_TITLE_PATTERNS:
        m = pattern.search(text_above)
        if m:
            candidate = m.group(1).strip()
            # reject very short or very generic strings
            if len(candidate) > 8 and candidate.lower() not in (
                "contents", "appendix", "section", "figure", "summary"
            ):
                return candidate
    return None


# ── heuristic table classifier ────────────────────────────────────────────────

# Keyword sets for each table type (matched against lowercased headers + title)
_TABLE_SIGNATURES: dict[str, list[str]] = {
    "soil_profile": [
        "unit no", "unit_no", "origin", "unit name", "description",
        "soil type", "material", "geology",
    ],
    "ground_model": [
        "model", "from", "to", "mbgl", "depth", "layer", "thickness",
        "unit", "borehole", "trial pit",
    ],
    "borehole_summary": [
        "borehole", "bh", "easting", "northing", "elevation", "rl",
        "depth", "groundwater", "water table", "series",
    ],
    "testpit_summary": [
        "trial pit", "test pit", "tp", "easting", "northing", "depth",
        "elevation",
    ],
    "laboratory_test": [
        "liquid limit", "plastic limit", "plasticity index", "moisture",
        "ll", "pl", "pi", "gravel", "sand", "fines", "psd", "emerson",
        "cbr", "mdd", "omc", "atterberg", "shrinkage", "compaction",
    ],
    "thermal_test": [
        "thermal", "resistivity", "r-value", "r value", "w/mk", "km/w",
        "thermal reading", "trt", "ert",
    ],
    "aggressivity": [
        "ph", "sulfate", "chloride", "resistivity", "exposure",
        "aggressiv", "corrosiv", "concrete pile", "steel pile",
    ],
    "pile_test": [
        "pile", "plt", "section", "tension", "lateral", "compression",
        "uplift", "applied force", "deflection", "ed", "embedment",
        "driving", "drive time", "driving rate", "target depth",
    ],
    "dpsh": [
        "dpsh", "dynamic probe", "refusal", "probe", "penetration",
        "blow count", "n value",
    ],
    "spт": [
        "spt", "standard penetration", "n value", "blow count",
        "n60", "corrected",
    ],
}

def _classify_table(title: Optional[str], headers: list[str]) -> Optional[str]:
    """
    Return the best-guess table type based on title and header keywords.
    Returns None if confidence is too low (avoids wrong classification).
    """
    fingerprint = " ".join(
        filter(None, [title or ""] + headers)
    ).lower()

    scores: dict[str, int] = {}
    for ttype, keywords in _TABLE_SIGNATURES.items():
        hits = sum(1 for kw in keywords if kw in fingerprint)
        if hits >= 2:          # require at least 2 keyword hits
            scores[ttype] = hits

    if not scores:
        return None
    best = max(scores, key=scores.__getitem__)
    # require a meaningful margin over second place to avoid ambiguity
    sorted_scores = sorted(scores.values(), reverse=True)
    if len(sorted_scores) >= 2 and sorted_scores[0] - sorted_scores[1] < 2:
        return None   # too close to call
    return best


# ── main extraction function ──────────────────────────────────────────────────

def extract_pdf(data: bytes) -> dict:
    """
    Extract all tables from a PDF with context.
    Returns:
        {
          "pages": [{"page": int, "text": str, "tables": [...raw...]}],
          "extracted_tables": [ExtractedTable, ...],
          "all_text": str,
        }
    """
    pages_raw: list[dict] = []
    extracted: list[ExtractedTable] = []

    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            page_text = (page.extract_text() or "").strip()

            raw_tables = page.extract_tables()
            cleaned_tables: list[list[list[str]]] = []

            for raw_t in raw_tables:
                cleaned = []
                for row in raw_t:
                    cells = [
                        str(c).replace("\n", " ").strip() if c else ""
                        for c in row
                    ]
                    if any(cells):
                        cleaned.append(cells)
                if cleaned:
                    cleaned_tables.append(cleaned)

            # For each table on this page, extract context and classify
            for t_idx, table_rows in enumerate(cleaned_tables, 1):
                if len(table_rows) < 2:
                    continue   # skip single-row tables (likely stray lines)

                # Use text above this table as context for title detection.
                # Approximate: take the last 600 chars of page text before
                # where this table would appear.
                text_above = page_text[:600] if page_text else ""

                # First row = headers; strip empty trailing cells
                raw_headers = [c for c in table_rows[0] if c]
                if not raw_headers:
                    raw_headers = table_rows[0]   # keep even if empty

                data_rows = table_rows[1:]

                title    = _extract_title(text_above)
                t_type   = _classify_table(title, raw_headers)

                extracted.append(ExtractedTable(
                    page=page_num,
                    table_index=t_idx,
                    title=title,
                    headers=raw_headers,
                    rows=data_rows,
                    raw_text_above=text_above[:300],
                    table_type=t_type,
                ))

            if page_text or cleaned_tables:
                pages_raw.append({
                    "page":   page_num,
                    "text":   page_text[:3000],
                    "tables": cleaned_tables,
                })

    all_text = "\n\n".join(p["text"] for p in pages_raw if p["text"])
    return {
        "pages":            pages_raw,
        "extracted_tables": extracted,
        "all_text":         all_text,
    }


def tables_as_text(pages: list[dict]) -> str:
    """Legacy helper — renders raw page tables as text (used by old code)."""
    out = []
    for p in pages:
        for j, table in enumerate(p.get("tables", []), 1):
            header = " | ".join(table[0]) if table else ""
            rows   = "\n".join(" | ".join(r) for r in table[1:])
            out.append(f"[Page {p['page']} Table {j}]\n{header}\n{rows}")
    return "\n\n".join(out)


def get_tables_by_type(extracted: list[ExtractedTable],
                       table_type: str) -> list[ExtractedTable]:
    """Filter extracted tables by heuristic type."""
    return [t for t in extracted if t.table_type == table_type]


def get_unclassified_tables(extracted: list[ExtractedTable]) -> list[ExtractedTable]:
    """Tables the heuristic couldn't classify — passed to LLM as-is."""
    return [t for t in extracted if t.table_type is None]