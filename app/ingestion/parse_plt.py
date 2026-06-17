"""Parse the Kleinfelder PLT report PDF into Pile records.

Extracts the structured summary tables that carry per-pile data with coordinates:
  - Table 5-2 Refusal Piles            -> refusal=True
  - Table 6-x Failure to Achieve Load  -> refusal=False, but flagged as a failure

Each row shares the column shape:
  BH ID | Easting | Northing | Reduced Level (mAHD) | Designer | Section Type
        | Target Depth (m) | Achieved Embedment (m)

Returns Pile dicts matching the /nodes/pile/upsert schema. Full per-pile result
pages (compression/tension/lateral curves) are NOT parsed here — those are the
LoadTest extraction, a separate pass once the per-page format is confirmed.

Usage:
    from app.ingestion.parse_plt import parse_plt_piles
    piles = parse_plt_piles("/path/PLT_Report.pdf")
"""
import re

import pdfplumber

# first token of each header cell -> normalised field
_HEADERS = {
    "bh": "id",                       # "BH ID"
    "easting": "easting",
    "northing": "northing",
    "reduced": "reduced_level",       # "Reduced\nLevels\n(mAHD)"
    "designer": "designer",
    "section": "section_type",        # "Section\nType"
    "target": "target_depth",         # "Target\nDepth (m)"
    "achieved": "achieved_embedment",  # "Achieved\nEmbedment (m)"
}
_PILE_ID = re.compile(r"^PLT\d{3}", re.I)
_FLOAT_FIELDS = {"easting", "northing", "reduced_level", "target_depth", "achieved_embedment"}


def _map_header(row: list) -> dict | None:
    """Return {col_index: field} if this row is the pile-table header, else None."""
    mapping = {}
    for idx, cell in enumerate(row):
        if not cell:
            continue
        key = str(cell).strip().lower().split()[0]
        if key in _HEADERS:
            mapping[idx] = _HEADERS[key]
    return mapping if "id" in mapping.values() and "easting" in mapping.values() else None


def _to_float(v):
    try:
        return float(str(v).replace(",", "").strip())
    except (ValueError, AttributeError):
        return None


def parse_plt_piles(path: str, *, pages=None) -> list[dict]:
    """Parse pile summary tables. `pages` is a 1-based iterable to limit the scan
    (the summary tables cluster in one section; scanning all 554 pages is slow)."""
    piles, seen = [], set()
    with pdfplumber.open(path) as pdf:
        total = len(pdf.pages)
        targets = pages if pages is not None else range(1, total + 1)
        for pageno in targets:
            if pageno < 1 or pageno > total:
                continue
            page = pdf.pages[pageno - 1]
            for table in page.extract_tables():
                if not table or len(table) < 2:
                    continue
                header = _map_header(table[0])
                if not header:
                    continue
                page_text = (page.extract_text() or "").lower()
                is_refusal = "refusal" in page_text
                is_failure = "failure to achieve" in page_text

                for row in table[1:]:
                    rec = {}
                    for idx, field in header.items():
                        if idx < len(row) and row[idx] not in (None, ""):
                            val = str(row[idx]).replace("\n", " ").strip()
                            rec[field] = _to_float(val) if field in _FLOAT_FIELDS else val
                    pid = rec.get("id", "")
                    if not _PILE_ID.match(pid) or pid in seen:
                        continue
                    seen.add(pid)
                    if is_refusal:
                        rec["refusal"] = True
                        if rec.get("achieved_embedment") is not None:
                            rec["refusal_depth"] = rec["achieved_embedment"]
                    elif is_failure:
                        rec["refusal"] = False
                    rec["_source_page"] = pageno
                    piles.append(rec)
    return piles


def discover_pile_table_pages(path: str, window=range(40, 60)) -> list[int]:
    """Find pages whose text mentions the pile summary tables (1-based)."""
    found = []
    with pdfplumber.open(path) as pdf:
        total = len(pdf.pages)
        for pageno in window:
            if 1 <= pageno <= total:
                txt = (pdf.pages[pageno - 1].extract_text() or "").lower()
                if "refusal piles" in txt or "failure to achieve" in txt:
                    found.append(pageno)
    return found


if __name__ == "__main__":
    import json, sys
    path = sys.argv[1]
    pages = discover_pile_table_pages(path)
    print(f"pile-table pages: {pages}")
    rows = parse_plt_piles(path, pages=pages)
    print(f"{len(rows)} piles parsed from summary tables")
    refusals = [r for r in rows if r.get("refusal") is True]
    print(f"  refusal piles: {len(refusals)}")
    print(json.dumps(rows[:4], indent=2))