"""
routes_ingest.py — PDF → template pipeline.

POST /ingest/extract   accepts multiple PDFs, runs extraction + LLM mapping,
                       returns the populated template as JSON (one key per sheet).

GET  /ingest/template  returns the blank template xlsx for download.

POST /ingest/import    accepts the final template xlsx and bulk-writes every
                       sheet to the graph via the existing /nodes bulk endpoints.
"""
from __future__ import annotations
import io, json, os, re, traceback
from typing import List

import openpyxl
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.ingestion.pdf_extractor import extract_pdf, tables_as_text
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/ingest", tags=["ingest"])

# ── LLM call (same env vars as agent.py, direct HTTP — no agent-framework) ───

def _llm_extract(prompt: str) -> str:
    """Call whichever LLM is configured and return the raw text response.
    Retries once on 429 with a 65-second wait (Groq resets per minute)."""
    import requests, time

    groq_key = os.getenv("GROQ_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if groq_key:
        url     = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}
        model   = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    elif gemini_key:
        url     = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
        headers = {"Authorization": f"Bearer {gemini_key}", "Content-Type": "application/json"}
        model   = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    elif openai_key:
        url     = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"}
        model   = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    else:
        raise RuntimeError("No LLM API key configured (GROQ_API_KEY / GEMINI_API_KEY / OPENAI_API_KEY)")

    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": 4096,
    }

    for attempt in range(3):
        r = requests.post(url, headers=headers, json=body, timeout=90)
        if r.status_code == 429:
            wait = 65 if attempt == 0 else 120
            logger.warning("Rate limited by LLM API — waiting %ds before retry %d", wait, attempt + 1)
            time.sleep(wait)
            continue
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

    raise RuntimeError("LLM API rate limit exceeded after retries. Try again in a few minutes.")


def _parse_json(raw: str) -> dict | list:
    """Strip markdown fences, extract the first JSON object/array, then parse."""
    # strip code fences
    raw = re.sub(r"```json|```", "", raw).strip()
    # find the first { or [ and the matching last } or ]
    start = next((i for i, c in enumerate(raw) if c in "{["), None)
    if start is None:
        raise ValueError("No JSON object found in LLM response")
    # find the last matching closer
    closer = "}" if raw[start] == "{" else "]"
    end = raw.rfind(closer)
    if end == -1:
        raise ValueError("Unterminated JSON in LLM response")
    raw = raw[start:end+1]
    # replace single-quoted keys/values (common Llama quirk)
    # only do this when standard parse fails
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # attempt light repair: trailing commas before } or ]
        repaired = re.sub(r",\s*([}\]])", r"\1", raw)
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            # last resort: replace Python-style None/True/False
            repaired = repaired.replace("None", "null").replace("True", "true").replace("False", "false")
            return json.loads(repaired)


# ── Schema definition (mirrors Example_Input.xlsx sheets) ────────────────────

SCHEMA = {
    "site": {
        "columns": ["id","name","address","coordinate_system"],
        "required": ["id"],
        "desc": "One row per project site.",
    },
    "zone": {
        "columns": ["id","site_id","name","pile_drilling",
                    "trackers_4_string","trackers_3_string","trackers_2_string"],
        "required": ["id","site_id"],
        "desc": "Zones / blocks / PCUs within the site. pile_drilling = Pre-Drill | Driven | None (leave None for new sites).",
    },
    "dpsh": {
        "columns": ["id","zone_id","easting","northing","refusal_depth"],
        "required": ["id"],
        "desc": "DPSH probe refusal depths (m). zone_id filled later from map.",
    },
    "borehole": {
        "columns": ["id","zone_id","ground_model_id","series","elevation",
                    "total_depth","groundwater_depth"],
        "required": ["id"],
        "desc": "Boreholes. series = BH or SS-BH.",
    },
    "testpit": {
        "columns": ["id","zone_id","ground_model_id","elevation","total_depth"],
        "required": ["id"],
        "desc": "Trial / test pits.",
    },
    "soil-type": {
        "columns": ["unit_no","origin","unit_name","description"],
        "required": ["unit_no"],
        "desc": "Soil / material vocabulary. unit_no must be unique globally (e.g. 1, 2A, 4D).",
    },
    "ground-model": {
        "columns": ["id"],
        "required": ["id"],
        "desc": "One ground model per borehole or test pit.",
    },
    "ground-layer": {
        "columns": ["id","ground_model_id","soil_unit_no","start_depth","end_depth"],
        "required": ["id","ground_model_id","start_depth","end_depth"],
        "desc": "Depth bands within a ground model. One row per (layer, soil type) pair.",
    },
    "thermal-test": {
        "columns": ["id","test_pit_id","depth","thermal_reading","r_value"],
        "required": ["id","test_pit_id","depth","thermal_reading","r_value"],
        "desc": "In-situ thermal resistivity tests.",
    },
    "lab-test": {
        "columns": ["id","location_id","soil_unit_no","top_depth","bottom_depth",
                    "moisture_content","liquid_limit","plastic_limit","plasticity_index",
                    "linear_shrinkage","emerson_class","iss","gravel","sand","fines",
                    "compaction_mdd","compaction_omc","cbr_4day_2_5mm","cbr_swell"],
        "required": ["id","location_id"],
        "desc": "Laboratory test results linked to a borehole or test pit.",
    },
    "aggressivity": {
        "columns": ["id","location_id","depth","ph","sulfate","chlorides",
                    "resistivity","exposure_class_concrete","exposure_class_steel"],
        "required": ["id","location_id"],
        "desc": "Soil aggressivity / corrosivity tests.",
    },
    "pile-test-location": {
        "columns": ["id","zone_id","driving_type","easting","northing","reduced_level",
                    "designer","section_type","target_depth","achieved_embedment",
                    "drive_time","driving_rate"],
        "required": ["id"],
        "desc": "Pile locations with install data. driving_type = Driven | PreDrilled.",
    },
    "pile-test": {
        "columns": ["id","pile_location_id","section_type","passed"],
        "required": ["id","pile_location_id"],
        "desc": "Pile test container. passed = true | false | undecided.",
    },
    "tension-test": {
        "columns": ["id","pile_test_id","uplift_applied_force",
                    "uplift_max_deflection","max_load_proportion_ed"],
        "required": ["id","pile_test_id"],
        "desc": "Tension / uplift sub-test.",
    },
    "lateral-test": {
        "columns": ["id","pile_test_id","max_applied_force","max_deflection_top",
                    "max_deflection_bottom","load_max","max_load_proportion_ed"],
        "required": ["id","pile_test_id"],
        "desc": "Lateral sub-test.",
    },
    "compression-test": {
        "columns": ["id","pile_test_id","max_applied_force",
                    "max_deflection","max_load_proportion_ed"],
        "required": ["id","pile_test_id"],
        "desc": "Compression sub-test.",
    },
}

SCHEMA_SUMMARY = "\n".join(
    f"  {name}: {', '.join(s['columns'])}  [{s['desc']}]"
    for name, s in SCHEMA.items()
)


# ── Extraction prompt builder ─────────────────────────────────────────────────

def _extraction_prompt(pdf_label: str, content: str) -> str:
    return f"""You are a geotechnical data extractor. Extract ALL data from the document below 
into the given JSON schema. Return ONLY a valid JSON object (no markdown, no explanation).

SCHEMA (sheet name → array of row objects):
{SCHEMA_SUMMARY}

Rules:
- Include only sheets where you find data. Empty sheets → omit.
- Use null for missing values, never invent values.
- IDs: use the label from the document exactly (e.g. BH01, TP03, PLT-004A).
- zone_id: set to null — zones are assigned separately from a site map.
- For soil-type, use the unit number from a geological profile table (1, 2A, 2B … 4D).
- For ground-layer, emit one row per (layer depth range × soil unit).
- For pile tests, emit one pile-test row per pile location, then sub-test rows.
- passed: true if max_load_proportion_ed ≥ 200, false otherwise, null if not tested.
- Numbers: strip units (store 1.65 not "1.65 m"), convert <10 to null.
- Do not include rows that are entirely null.

DOCUMENT: {pdf_label}
---
{content}
---

Return JSON object mapping sheet names to arrays of row objects.
"""


# ── Merge results from multiple PDFs ─────────────────────────────────────────

def _merge(results: list[dict]) -> dict:
    merged: dict[str, list] = {k: [] for k in SCHEMA}
    seen: dict[str, set] = {k: set() for k in SCHEMA}
    for r in results:
        for sheet, rows in r.items():
            if sheet not in merged or not isinstance(rows, list):
                continue
            id_col = "unit_no" if sheet == "soil-type" else "id"
            for row in rows:
                if not isinstance(row, dict):
                    continue
                key = str(row.get(id_col, ""))
                if key and key in seen[sheet]:
                    continue  # deduplicate by id
                if key:
                    seen[sheet].add(key)
                merged[sheet].append(row)
    return {k: v for k, v in merged.items() if v}


# ── Build xlsx from merged data ───────────────────────────────────────────────

def _build_xlsx(data: dict) -> bytes:
    from openpyxl.styles import Font, PatternFill, Alignment

    HFONT  = Font(bold=True, color="FFFFFF", name="Arial", size=10)
    HFILL  = PatternFill("solid", start_color="2F6F77")
    RFILL  = PatternFill("solid", start_color="FFE0E0")   # required
    RFONT  = Font(bold=True, color="CC0000", name="Arial", size=10)
    FKFILL = PatternFill("solid", start_color="FFF3CC")   # foreign key
    FKFONT = Font(bold=True, color="7A5200", name="Arial", size=10)
    NULL_FILL = PatternFill("solid", start_color="F5F5F5")

    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    for sheet_name, schema in SCHEMA.items():
        ws = wb.create_sheet(sheet_name)
        cols = schema["columns"]
        req  = set(schema.get("required", []))
        fk_cols = {c for c in cols if c.endswith("_id")}

        ws.append(cols)
        for ci, col in enumerate(cols, 1):
            cell = ws.cell(1, ci)
            if col in req:
                cell.font = RFONT; cell.fill = RFILL
            elif col in fk_cols:
                cell.font = FKFONT; cell.fill = FKFILL
            else:
                cell.font = HFONT; cell.fill = HFILL
            cell.alignment = Alignment(horizontal="center")

        rows = data.get(sheet_name, [])
        for row in rows:
            ws.append([row.get(c) for c in cols])

        # grey out null cells so they're visually distinct from blanks
        for r in ws.iter_rows(min_row=2):
            for c in r:
                if c.value is None:
                    c.fill = NULL_FILL

        # auto-width
        for col in ws.columns:
            w = max((len(str(c.value)) if c.value is not None else 0) for c in col) + 2
            ws.column_dimensions[col[0].column_letter].width = max(w, 12)

        ws.freeze_panes = "A2"

        # legend in top-right
        legend_col = len(cols) + 2
        legend = [
            ("■ RED header", "CC0000", "Required field"),
            ("■ ORANGE header", "7A5200", "Foreign key (links to another sheet)"),
            ("■ TEAL header", "2F6F77", "Optional field"),
            ("■ Grey cell", "888888", "No data extracted — fill manually"),
        ]
        for i, (label, color, note) in enumerate(legend, 1):
            ws.cell(i, legend_col).value = f"{label}: {note}"
            ws.cell(i, legend_col).font = Font(color=color, italic=True, size=9, name="Arial")

    return io.BytesIO(b"").getvalue().__class__(wb.save(io.BytesIO()) or b"") or _save(wb)


def _save(wb) -> bytes:
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/extract")
async def extract_pdfs(files: List[UploadFile] = File(...)):
    """
    Accept one or more PDFs. For each:
      1. Extract text + tables with pdfplumber.
      2. Send to LLM with the schema prompt.
      3. Parse JSON response.
    Merge all results, return as JSON (sheet → rows).
    """
    if not files:
        raise HTTPException(400, "No files uploaded")

    results, errors = [], []
    for f in files:
        if not f.filename.lower().endswith(".pdf"):
            errors.append(f"{f.filename}: not a PDF, skipped")
            continue
    for f in files:
        if not f.filename.lower().endswith(".pdf"):
            errors.append(f"{f.filename}: not a PDF, skipped")
            continue
        try:
            data      = await f.read()
            extracted = extract_pdf(data)

            # Split into chunks of ~8 pages so we stay under token limits.
            # Each chunk is sent as a separate LLM call; results are merged.
            pages     = extracted["pages"]
            CHUNK     = 8
            chunks    = [pages[i:i+CHUNK] for i in range(0, max(1, len(pages)), CHUNK)]

            file_result: dict = {}
            for ci, chunk in enumerate(chunks):
                content = tables_as_text(chunk)
                if not content.strip():
                    content = "\n\n".join(p["text"] for p in chunk if p.get("text"))
                content = content[:10000]
                if not content.strip():
                    continue
                label  = f"{f.filename} (pages {chunk[0]['page']}–{chunk[-1]['page']})"
                prompt = _extraction_prompt(label, content)
                try:
                    raw    = _llm_extract(prompt)
                    parsed = _parse_json(raw)
                    if isinstance(parsed, dict):
                        # merge chunk into file_result
                        for sheet, rows in parsed.items():
                            if isinstance(rows, list):
                                file_result.setdefault(sheet, []).extend(rows)
                except Exception as chunk_err:
                    errors.append(f"{label}: {chunk_err}")

            if file_result:
                results.append(file_result)
        except Exception as e:
            logger.warning("Error processing %s: %s", f.filename, e)
            errors.append(f"{f.filename}: {e}")

    if not results:
        raise HTTPException(422, detail={"message": "No data could be extracted", "errors": errors})

    merged = _merge(results)
    # count rows per sheet
    summary = {k: len(v) for k, v in merged.items()}
    return {"data": merged, "summary": summary, "errors": errors}


@router.get("/template")
def download_template():
    """Return the blank Example_Input template xlsx."""
    blank = _build_xlsx({})
    return StreamingResponse(
        io.BytesIO(blank),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="geotech_input_template.xlsx"'},
    )


@router.post("/download-prefilled")
async def download_prefilled(files: List[UploadFile] = File(...)):
    """Extract from PDFs and return a pre-filled xlsx for the user to edit."""
    resp = await extract_pdfs(files)
    xlsx = _build_xlsx(resp["data"])
    return StreamingResponse(
        io.BytesIO(xlsx),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="geotech_extracted.xlsx"'},
    )


@router.post("/import")
async def import_xlsx(file: UploadFile = File(...)):
    """
    Accept the final edited xlsx and bulk-write every sheet to the graph
    via the existing /nodes/{type}/bulk endpoints (internal call).
    """
    import httpx, os
    if not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(400, "Expected an .xlsx file")

    data    = await file.read()
    wb      = openpyxl.load_workbook(io.BytesIO(data), data_only=True)
    base    = os.getenv("INTERNAL_API_BASE", "http://localhost:8000")

    results = {}
    async with httpx.AsyncClient(base_url=base, timeout=60) as client:
        for sheet_name in wb.sheetnames:
            if sheet_name not in SCHEMA:
                continue
            ws   = wb[sheet_name]
            cols = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
            rows = []
            for row in ws.iter_rows(min_row=2, values_only=True):
                obj = {cols[i]: v for i, v in enumerate(row) if i < len(cols)}
                # skip rows where the id field is blank
                id_col = "unit_no" if sheet_name == "soil-type" else "id"
                if not obj.get(id_col):
                    continue
                # convert Excel booleans / strings
                for k, v in obj.items():
                    if isinstance(v, str) and v.lower() in ("true","false"):
                        obj[k] = v.lower() == "true"
                rows.append(obj)

            if not rows:
                continue

            try:
                r = await client.post(f"/nodes/{sheet_name}/bulk", json={"rows": rows})
                results[sheet_name] = r.json()
            except Exception as e:
                results[sheet_name] = {"error": str(e)}

    return {"imported": results}
