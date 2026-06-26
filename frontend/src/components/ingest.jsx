import React, { useState, useRef } from "react";
import { api } from "../api.js";

// ── tiny helpers ──────────────────────────────────────────────────────────────
const SHEET_ORDER = [
  "site","zone","dpsh","borehole","testpit","soil-type","ground-model",
  "ground-layer","thermal-test","lab-test","aggressivity",
  "pile-test-location","pile-test","tension-test","lateral-test","compression-test",
];

function Badge({ n, color = "accent" }) {
  return (
    <span style={{
      background: `var(--bg-${color})`, color: `var(--text-${color})`,
      border: `1px solid var(--border-${color})`,
      borderRadius: 12, padding: "1px 8px", fontSize: 12, fontWeight: 500,
    }}>{n}</span>
  );
}

function FileDropZone({ onFiles, accept, multiple, label, sub }) {
  const [drag, setDrag] = useState(false);
  const ref = useRef();
  const handle = (files) => {
    const arr = Array.from(files).filter(f =>
      accept.split(",").some(ext => f.name.toLowerCase().endsWith(ext.trim()))
    );
    if (arr.length) onFiles(arr);
  };
  return (
    <div
      onClick={() => ref.current.click()}
      onDragOver={e => { e.preventDefault(); setDrag(true); }}
      onDragLeave={() => setDrag(false)}
      onDrop={e => { e.preventDefault(); setDrag(false); handle(e.dataTransfer.files); }}
      style={{
        border: `2px dashed var(--border${drag ? "-accent" : "-strong"})`,
        borderRadius: 12, padding: "32px 24px", textAlign: "center",
        background: drag ? "var(--bg-accent)" : "var(--surface-1)",
        cursor: "pointer", transition: "all .15s",
      }}
    >
      <i className="ti ti-upload" style={{ fontSize: 28, color: "var(--text-secondary)" }} aria-hidden />
      <p style={{ margin: "8px 0 4px", color: "var(--text-primary)", fontWeight: 500 }}>{label}</p>
      <p style={{ margin: 0, fontSize: 13, color: "var(--text-secondary)" }}>{sub}</p>
      <input ref={ref} type="file" accept={accept} multiple={multiple}
        style={{ display: "none" }} onChange={e => handle(e.target.files)} />
    </div>
  );
}

function PreviewTable({ sheet, rows }) {
  if (!rows || rows.length === 0) return null;
  const cols = Object.keys(rows[0]);
  return (
    <div style={{ overflowX: "auto", marginTop: 8 }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
        <thead>
          <tr>{cols.map(c => (
            <th key={c} style={{
              background: "var(--surface-0)", borderBottom: "1px solid var(--border)",
              padding: "4px 8px", textAlign: "left", whiteSpace: "nowrap",
              color: "var(--text-secondary)", fontWeight: 500,
            }}>{c}</th>
          ))}</tr>
        </thead>
        <tbody>{rows.slice(0, 8).map((r, i) => (
          <tr key={i} style={{ borderBottom: "1px solid var(--border)" }}>
            {cols.map(c => (
              <td key={c} style={{
                padding: "3px 8px", color: r[c] == null ? "var(--text-muted)" : "var(--text-primary)",
                fontStyle: r[c] == null ? "italic" : "normal",
              }}>{r[c] == null ? "—" : String(r[c])}</td>
            ))}
          </tr>
        ))}
        {rows.length > 8 && (
          <tr><td colSpan={cols.length} style={{ padding: "3px 8px", color: "var(--text-muted)", fontSize: 11 }}>
            … {rows.length - 8} more rows
          </td></tr>
        )}
        </tbody>
      </table>
    </div>
  );
}

// ── main component ────────────────────────────────────────────────────────────
export default function Ingest() {
  // stage 1
  const [pdfs,    setPdfs]    = useState([]);
  const [busy,    setBusy]    = useState(false);
  const [error,   setError]   = useState(null);
  // stage 2
  const [preview, setPreview] = useState(null);  // {data, summary, errors}
  const [open,    setOpen]    = useState({});
  // stage 3
  const [xlFile,  setXlFile]  = useState(null);
  const [result,  setResult]  = useState(null);

  const stage = preview ? (result ? 3 : 2) : 1;

  // ── stage 1: extract ───────────────────────────────────────────────────────
  async function runExtract() {
    setBusy(true); setError(null);
    try {
      const form = new FormData();
      pdfs.forEach(f => form.append("files", f));
      const r = await fetch(`${await api.base()}/ingest/extract`, { method: "POST", body: form });
      if (!r.ok) {
        const err = await r.json().catch(() => ({}));
        throw new Error(err.detail?.message || err.detail || r.statusText);
      }
      const json = await r.json();
      setPreview(json);
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  }

  // ── stage 1→2: download pre-filled xlsx ───────────────────────────────────
  async function downloadPrefilled() {
    setBusy(true); setError(null);
    try {
      const form = new FormData();
      pdfs.forEach(f => form.append("files", f));
      const r = await fetch(`${await api.base()}/ingest/download-prefilled`, { method: "POST", body: form });
      if (!r.ok) throw new Error(r.statusText);
      const blob = await r.blob();
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement("a");
      a.href = url; a.download = "geotech_extracted.xlsx"; a.click();
      URL.revokeObjectURL(url);
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  }

  async function downloadBlank() {
    const r = await fetch(`${await api.base()}/ingest/template`);
    const blob = await r.blob();
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a"); a.href = url;
    a.download = "geotech_input_template.xlsx"; a.click();
    URL.revokeObjectURL(url);
  }

  // ── stage 3: import final xlsx ─────────────────────────────────────────────
  async function runImport() {
    if (!xlFile) return;
    setBusy(true); setError(null);
    try {
      const form = new FormData();
      form.append("file", xlFile);
      const r = await fetch(`${await api.base()}/ingest/import`, { method: "POST", body: form });
      if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText);
      setResult(await r.json());
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  }

  const totalExtracted = preview
    ? Object.values(preview.summary || {}).reduce((a, b) => a + b, 0)
    : 0;

  // ── render ─────────────────────────────────────────────────────────────────
  return (
    <div style={{ maxWidth: 860, margin: "0 auto", paddingBottom: 40 }}>

      {/* progress bar */}
      <div style={{ display: "flex", gap: 0, marginBottom: 28, borderRadius: 8, overflow: "hidden" }}>
        {[["1","Upload PDFs"],["2","Review & download"],["3","Import to graph"]].map(([n, label], i) => (
          <div key={n} style={{
            flex: 1, padding: "10px 16px", fontSize: 13, fontWeight: stage >= i+1 ? 500 : 400,
            background: stage > i+1 ? "var(--bg-success)" : stage === i+1 ? "var(--bg-accent)" : "var(--surface-1)",
            color: stage >= i+1 ? (stage > i+1 ? "var(--text-success)" : "var(--text-accent)") : "var(--text-muted)",
            borderRight: i < 2 ? "1px solid var(--border)" : "none",
            display: "flex", alignItems: "center", gap: 8,
          }}>
            <span style={{
              width: 22, height: 22, borderRadius: "50%", display: "flex",
              alignItems: "center", justifyContent: "center", fontSize: 11, fontWeight: 600,
              background: stage > i+1 ? "var(--bg-success)" : stage === i+1 ? "var(--text-accent)" : "var(--border-strong)",
              color: stage === i+1 ? "#fff" : "inherit",
            }}>
              {stage > i+1 ? <i className="ti ti-check" style={{ fontSize: 12 }} /> : n}
            </span>
            {label}
          </div>
        ))}
      </div>

      {/* ── stage 1 ── */}
      {stage === 1 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <FileDropZone
            accept=".pdf" multiple label="Drop your PDFs here or click to browse"
            onFiles={fs => setPdfs(prev => {
              const names = new Set(prev.map(f => f.name));
              return [...prev, ...fs.filter(f => !names.has(f.name))];
            })}
          />

          {pdfs.length > 0 && (
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {pdfs.map((f, i) => (
                <div key={f.name} style={{
                  display: "flex", alignItems: "center", gap: 10, padding: "8px 12px",
                  background: "var(--surface-1)", borderRadius: 8, border: "1px solid var(--border)",
                }}>
                  <i className="ti ti-file-type-pdf" style={{ color: "var(--text-danger)", fontSize: 18 }} aria-hidden />
                  <span style={{ flex: 1, fontSize: 13, color: "var(--text-primary)" }}>{f.name}</span>
                  <span style={{ fontSize: 12, color: "var(--text-muted)" }}>{(f.size/1024).toFixed(0)} KB</span>
                  <button onClick={() => setPdfs(prev => prev.filter((_,j) => j!==i))}
                    style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-muted)", padding: 4 }}>
                    <i className="ti ti-x" aria-hidden />
                  </button>
                </div>
              ))}
            </div>
          )}

          {error && (
            <div style={{ padding: "10px 14px", background: "var(--bg-danger)", border: "1px solid var(--border-danger)",
              borderRadius: 8, color: "var(--text-danger)", fontSize: 13 }}>
              <i className="ti ti-alert-circle" aria-hidden /> {error}
            </div>
          )}

          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <button className="btn" disabled={pdfs.length === 0 || busy} onClick={runExtract}
              style={{ minWidth: 180 }}>
              {busy ? <><i className="ti ti-loader-2" style={{ animation: "spin 1s linear infinite" }} aria-hidden /> Extracting…</>
                    : <><i className="ti ti-wand" aria-hidden /> Extract data</>}
            </button>
            <button className="btn ghost" onClick={downloadBlank}>
              <i className="ti ti-download" aria-hidden /> Blank template
            </button>
          </div>
        </div>
      )}

      {/* ── stage 2 ── */}
      {stage === 2 && preview && (
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
            <span style={{ fontWeight: 500 }}>Extracted from {pdfs.length} PDF{pdfs.length!==1?"s":""}</span>
            <Badge n={`${totalExtracted} rows across ${Object.keys(preview.data).length} sheets`} />
            {preview.errors?.length > 0 && (
              <Badge n={`${preview.errors.length} warning${preview.errors.length!==1?"s":""}`} color="warning" />
            )}
          </div>

          {preview.errors?.length > 0 && (
            <div style={{ padding: "10px 14px", background: "var(--bg-warning)",
              border: "1px solid var(--border-warning)", borderRadius: 8, fontSize: 12, color: "var(--text-warning)" }}>
              {preview.errors.map((e,i) => <div key={i}>{e}</div>)}
            </div>
          )}

          {/* sheet previews */}
          {SHEET_ORDER.filter(s => preview.data[s]?.length).map(sheet => (
            <div key={sheet} style={{ border: "1px solid var(--border)", borderRadius: 10 }}>
              <div
                onClick={() => setOpen(o => ({ ...o, [sheet]: !o[sheet] }))}
                style={{ display: "flex", alignItems: "center", gap: 10, padding: "10px 14px",
                  cursor: "pointer", userSelect: "none" }}>
                <i className={`ti ti-chevron-${open[sheet]?"up":"down"}`} style={{ fontSize: 14 }} aria-hidden />
                <span style={{ fontWeight: 500, flex: 1, fontSize: 14 }}>{sheet}</span>
                <Badge n={preview.data[sheet].length} />
              </div>
              {open[sheet] && (
                <div style={{ padding: "0 14px 14px" }}>
                  <PreviewTable sheet={sheet} rows={preview.data[sheet]} />
                </div>
              )}
            </div>
          ))}

          {/* actions */}
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", paddingTop: 8 }}>
            <button className="btn" onClick={downloadPrefilled} disabled={busy}>
              <i className="ti ti-download" aria-hidden />
              {busy ? "Preparing…" : "Download pre-filled spreadsheet"}
            </button>
            <button className="btn ghost" onClick={() => { setPreview(null); setError(null); }}>
              <i className="ti ti-arrow-left" aria-hidden /> Back
            </button>
          </div>

          <div style={{ padding: "12px 16px", background: "var(--surface-1)",
            border: "1px solid var(--border)", borderRadius: 10, fontSize: 13 }}>
            <p style={{ margin: "0 0 6px", fontWeight: 500 }}>Next steps</p>
            <ol style={{ margin: 0, paddingLeft: 18, color: "var(--text-secondary)", lineHeight: 1.8 }}>
              <li>Download the pre-filled spreadsheet above</li>
              <li>Open it and fill in any cells marked grey (no data found) or flagged with comments</li>
              <li>Assign zone IDs to boreholes and test pits once you have the site map</li>
              <li>Upload the completed file below to import everything to the graph</li>
            </ol>
          </div>

          <hr style={{ border: "none", borderTop: "1px solid var(--border)", margin: "4px 0" }} />

          <p style={{ fontWeight: 500, margin: "0 0 8px" }}>
            Upload completed spreadsheet to import
          </p>
          <FileDropZone
            accept=".xlsx" multiple={false}
            label="Drop your completed .xlsx here"
            sub="The file you downloaded and edited"
            onFiles={([f]) => setXlFile(f)}
          />
          {xlFile && (
            <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 12px",
              background: "var(--surface-1)", borderRadius: 8, border: "1px solid var(--border)" }}>
              <i className="ti ti-file-spreadsheet" style={{ color: "var(--text-success)", fontSize: 18 }} aria-hidden />
              <span style={{ flex: 1, fontSize: 13 }}>{xlFile.name}</span>
              <button className="btn" disabled={busy} onClick={runImport}>
                {busy ? "Importing…" : <><i className="ti ti-database-import" aria-hidden /> Import to graph</>}
              </button>
            </div>
          )}
          {error && (
            <div style={{ padding: "10px 14px", background: "var(--bg-danger)",
              border: "1px solid var(--border-danger)", borderRadius: 8,
              color: "var(--text-danger)", fontSize: 13 }}>
              <i className="ti ti-alert-circle" aria-hidden /> {error}
            </div>
          )}
        </div>
      )}

      {/* ── stage 3 ── */}
      {stage === 3 && result && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={{ padding: "16px 20px", background: "var(--bg-success)",
            border: "1px solid var(--border-success)", borderRadius: 10,
            color: "var(--text-success)", fontWeight: 500 }}>
            <i className="ti ti-circle-check" aria-hidden /> Import complete
          </div>

          {Object.entries(result.imported || {}).map(([sheet, r]) => (
            <div key={sheet} style={{ display: "flex", alignItems: "center", gap: 10,
              padding: "8px 14px", background: "var(--surface-1)",
              border: "1px solid var(--border)", borderRadius: 8 }}>
              <span style={{ flex: 1, fontSize: 13, fontWeight: 500 }}>{sheet}</span>
              {r.error
                ? <Badge n={`Error: ${r.error}`} color="danger" />
                : <Badge n={`${r.saved ?? "?"} saved`} color="success" />}
              {r.errors?.length > 0 && (
                <Badge n={`${r.errors.length} skipped`} color="warning" />
              )}
            </div>
          ))}

          <button className="btn ghost" style={{ marginTop: 8 }}
            onClick={() => { setPdfs([]); setPreview(null); setXlFile(null); setResult(null); setError(null); }}>
            <i className="ti ti-plus" aria-hidden /> Import another project
          </button>
        </div>
      )}

    </div>
  );
}