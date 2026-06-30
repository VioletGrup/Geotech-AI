import React, { useState, useRef, useEffect } from "react";
import { api } from "../api.js";

const SHEET_ORDER = [
  "site","zone","dpsh","borehole","testpit","soil-type","ground-model",
  "ground-layer","thermal-test","lab-test","aggressivity",
  "pile-test-location","pile-test","tension-test","lateral-test","compression-test",
];

// ── helpers ───────────────────────────────────────────────────────────────────
function Badge({ n, color = "accent" }) {
  return (
    <span style={{ background:`var(--bg-${color})`,color:`var(--text-${color})`,
      border:`1px solid var(--border-${color})`,borderRadius:12,
      padding:"1px 8px",fontSize:12,fontWeight:500 }}>{n}</span>
  );
}

function FileDropZone({ onFiles, accept, multiple, label, sub, disabled }) {
  const [drag, setDrag] = useState(false);
  const ref = useRef();
  const handle = (files) => {
    if (disabled) return;
    const arr = Array.from(files).filter(f =>
      accept.split(",").some(ext => f.name.toLowerCase().endsWith(ext.trim()))
    );
    if (arr.length) onFiles(arr);
  };
  return (
    <div onClick={() => !disabled && ref.current.click()}
      onDragOver={e => { e.preventDefault(); if (!disabled) setDrag(true); }}
      onDragLeave={() => setDrag(false)}
      onDrop={e => { e.preventDefault(); setDrag(false); handle(e.dataTransfer.files); }}
      style={{ border:`2px dashed var(--border${drag?"-accent":"-strong"})`,borderRadius:12,
        padding:"32px 24px",textAlign:"center",
        background:drag?"var(--bg-accent)":"var(--surface-1)",
        cursor:disabled?"not-allowed":"pointer",opacity:disabled?0.5:1,transition:"all .15s" }}>
      <i className="ti ti-upload" style={{fontSize:28,color:"var(--text-secondary)"}} aria-hidden />
      <p style={{margin:"8px 0 4px",color:"var(--text-primary)",fontWeight:500}}>{label}</p>
      {sub && <p style={{margin:0,fontSize:13,color:"var(--text-secondary)"}}>{sub}</p>}
      <input ref={ref} type="file" accept={accept} multiple={multiple}
        style={{display:"none"}} onChange={e => handle(e.target.files)} />
    </div>
  );
}

function PreviewTable({ rows }) {
  if (!rows?.length) return null;
  const cols = Object.keys(rows[0]);
  return (
    <div style={{overflowX:"auto",marginTop:8}}>
      <table style={{width:"100%",borderCollapse:"collapse",fontSize:12}}>
        <thead>
          <tr>{cols.map(c => (
            <th key={c} style={{background:"var(--surface-0)",borderBottom:"1px solid var(--border)",
              padding:"4px 8px",textAlign:"left",whiteSpace:"nowrap",
              color:"var(--text-secondary)",fontWeight:500}}>{c}</th>
          ))}</tr>
        </thead>
        <tbody>{rows.slice(0,8).map((r,i) => (
          <tr key={i} style={{borderBottom:"1px solid var(--border)"}}>
            {cols.map(c => (
              <td key={c} style={{padding:"3px 8px",
                color:r[c]==null?"var(--text-muted)":"var(--text-primary)",
                fontStyle:r[c]==null?"italic":"normal"}}>
                {r[c]==null?"—":String(r[c])}
              </td>
            ))}
          </tr>
        ))}
        {rows.length > 8 && (
          <tr><td colSpan={cols.length}
            style={{padding:"3px 8px",color:"var(--text-muted)",fontSize:11}}>
            … {rows.length-8} more rows
          </td></tr>
        )}
        </tbody>
      </table>
    </div>
  );
}

// ── loading overlay with progress bar ────────────────────────────────────────
function LoadingOverlay({ progress, onCancel }) {
  const { done=0, total=0, label="", rateLimited=false, currentFile="" } = progress;
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;

  return (
    <div style={{position:"fixed",inset:0,zIndex:300,background:"rgba(0,0,0,0.72)",
      display:"flex",alignItems:"center",justifyContent:"center",padding:24}}>
      <div style={{background:"var(--surface-2)",borderRadius:16,
        padding:"36px 40px 28px",maxWidth:500,width:"100%",
        border:"1px solid var(--border-strong)",
        boxShadow:"0 24px 64px rgba(0,0,0,.6)"}}>

        {/* spinner + title */}
        <div style={{display:"flex",alignItems:"center",gap:16,marginBottom:20}}>
          <i className="ti ti-loader-2"
            style={{fontSize:32,animation:"spin 1s linear infinite",
              color:rateLimited?"var(--text-warning)":"var(--text-accent)",flexShrink:0}} aria-hidden />
          <div>
            <div style={{fontWeight:600,fontSize:16,color:"var(--text-primary)"}}>
              {rateLimited ? "Rate limited — waiting…" : "Extracting data"}
            </div>
            <div style={{fontSize:12,color:"var(--text-secondary)",marginTop:2}}>
              {currentFile || "Analysing PDF tables and mapping to schema"}
            </div>
          </div>
        </div>

        {/* rate limit warning */}
        {rateLimited && (
          <div style={{padding:"8px 12px",background:"var(--bg-warning)",
            border:"1px solid var(--border-warning)",borderRadius:8,
            color:"var(--text-warning)",fontSize:12,marginBottom:16,lineHeight:1.5}}>
            The LLM API is rate limiting requests. The tool is waiting and will
            retry automatically — this may take up to 60 seconds per retry.
            You can cancel and try again later if needed.
          </div>
        )}

        {/* progress bar */}
        {total > 0 && (
          <div style={{marginBottom:16}}>
            <div style={{display:"flex",justifyContent:"space-between",
              fontSize:12,color:"var(--text-secondary)",marginBottom:6}}>
              <span>{label || "Processing…"}</span>
              <span style={{fontWeight:500,color:"var(--text-primary)"}}>
                {done} / {total} chunks
              </span>
            </div>
            <div style={{height:6,background:"var(--surface-0)",borderRadius:3,overflow:"hidden"}}>
              <div style={{
                height:"100%",borderRadius:3,
                background:rateLimited
                  ? "var(--text-warning)"
                  : "linear-gradient(90deg,var(--pcl-green),var(--pcl-gold))",
                width:`${pct}%`,
                transition:"width .4s ease",
              }}/>
            </div>
            <div style={{textAlign:"right",fontSize:11,color:"var(--text-muted)",marginTop:3}}>
              {pct}%
            </div>
          </div>
        )}

        {/* cancel */}
        <button onClick={onCancel}
          style={{width:"100%",padding:"9px",borderRadius:8,
            border:"1px solid var(--border-danger)",background:"transparent",
            color:"var(--text-danger)",cursor:"pointer",fontSize:13,fontWeight:500,
            transition:"background .12s"}}
          onMouseOver={e=>e.currentTarget.style.background="var(--bg-danger)"}
          onMouseOut={e=>e.currentTarget.style.background="transparent"}>
          × Cancel
        </button>
      </div>
      <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
    </div>
  );
}

// ── main ─────────────────────────────────────────────────────────────────────
export default function Ingest({ initSiteType }) {
  const [siteType, setSiteType] = useState(initSiteType || null);
  const [pdfs,     setPdfs]     = useState([]);
  const [busy,     setBusy]     = useState(false);
  const [progress, setProgress] = useState({ done:0, total:0, label:"", rateLimited:false, currentFile:"" });
  const [error,    setError]    = useState(null);
  const [preview,  setPreview]  = useState(null);
  const [open,     setOpen]     = useState({});
  const [xlFile,   setXlFile]   = useState(null);
  const [result,   setResult]   = useState(null);
  const jobIdRef   = useRef(null);
  const cancelledRef = useRef(false);

  useEffect(() => { if (initSiteType) setSiteType(initSiteType); }, [initSiteType]);

  const stage = preview ? (result ? 3 : 2) : 1;

  // ── cancel ────────────────────────────────────────────────────────────────
  async function cancel() {
    cancelledRef.current = true;
    if (jobIdRef.current) {
      const base = await api.base();
      fetch(`${base}/ingest/extract/${jobIdRef.current}`, { method:"DELETE" }).catch(()=>{});
      jobIdRef.current = null;
    }
    setBusy(false);
    setProgress({ done:0, total:0, label:"", rateLimited:false, currentFile:"" });
  }

  // ── stage 1: SSE extraction ───────────────────────────────────────────────
  async function runExtract() {
    setBusy(true); setError(null); cancelledRef.current = false;
    setProgress({ done:0, total:0, label:"Uploading…", rateLimited:false, currentFile:"" });

    const jobId = crypto.randomUUID();
    jobIdRef.current = jobId;

    const base = await api.base();
    const form = new FormData();
    pdfs.forEach(f => form.append("files", f));
    if (siteType) form.append("site_type", siteType);

    try {
      const resp = await fetch(`${base}/ingest/extract/${jobId}`, { method:"POST", body:form });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail?.message || err.detail || resp.statusText);
      }

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        if (cancelledRef.current) { reader.cancel(); break; }

        buf += decoder.decode(value, { stream: true });
        const messages = buf.split("\n\n");
        buf = messages.pop(); // last may be incomplete

        for (const msg of messages) {
          if (!msg.trim()) continue;
          const eventLine = msg.match(/^event:\s*(.+)/m);
          const dataLine  = msg.match(/^data:\s*(.+)/ms);
          if (!eventLine || !dataLine) continue;

          const event = eventLine[1].trim();
          let data;
          try { data = JSON.parse(dataLine[1].trim()); } catch { continue; }

          if (cancelledRef.current) break;

          switch (event) {
            case "start":
              setProgress(p => ({...p, total:data.total_chunks, label:"Starting…"}));
              break;
            case "chunk_start":
              setProgress(p => ({...p,
                done:data.done, total:data.total,
                label:data.label, currentFile:data.file,
                rateLimited:false,
              }));
              break;
            case "chunk_done":
              setProgress(p => ({...p, done:data.done, total:data.total, rateLimited:false}));
              break;
            case "rate_limit":
              setProgress(p => ({...p, rateLimited:true, label:data.message}));
              break;
            case "info":
              // informational (e.g. appendix detected) — show as a dim note, not an error
              setError(prev => prev ? `${prev}\nℹ ${data.message}` : `ℹ ${data.message}`);
              break;
            case "warning":
              setError(prev => prev ? `${prev}\n⚠ ${data.message}` : `⚠ ${data.message}`);
              break;
            case "done":
              setPreview({ data:data.data, summary:data.summary, errors:data.errors||[] });
              setBusy(false);
              setProgress({ done:0, total:0, label:"", rateLimited:false, currentFile:"" });
              break;
            case "error":
              setError(data.message + (data.errors?.length ? `\n${data.errors.join("\n")}` : ""));
              setBusy(false);
              setProgress({ done:0, total:0, label:"", rateLimited:false, currentFile:"" });
              break;
            case "cancelled":
              setBusy(false);
              setProgress({ done:0, total:0, label:"", rateLimited:false, currentFile:"" });
              break;
          }
        }
      }
    } catch(e) {
      if (!cancelledRef.current) setError(e.message);
      setBusy(false);
      setProgress({ done:0, total:0, label:"", rateLimited:false, currentFile:"" });
    }

    jobIdRef.current = null;
  }

  // ── download prefilled xlsx (blocking — no progress needed) ───────────────
  async function downloadPrefilled() {
    setBusy(true); setError(null);
    setProgress({ done:0, total:0, label:"Building spreadsheet…", rateLimited:false, currentFile:"" });
    try {
      const form = new FormData();
      pdfs.forEach(f => form.append("files", f));
      if (siteType) form.append("site_type", siteType);
      const base = await api.base();
      // reuse SSE extract with a temp job but just collect data
      const r = await fetch(`${base}/ingest/download-prefilled`, { method:"POST", body:form });
      if (!r.ok) throw new Error(r.statusText);
      const blob = await r.blob();
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob); a.download = "geotech_extracted.xlsx"; a.click();
    } catch(e) { setError(e.message); }
    finally { setBusy(false); setProgress({ done:0, total:0, label:"", rateLimited:false, currentFile:"" }); }
  }

  async function downloadBlank() {
    const r = await fetch(`${await api.base()}/ingest/template`);
    const blob = await r.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob); a.download = "geotech_input_template.xlsx"; a.click();
  }

  // ── import final xlsx ─────────────────────────────────────────────────────
  async function runImport() {
    if (!xlFile) return;
    setBusy(true); setError(null);
    setProgress({ done:0, total:0, label:"Importing to graph…", rateLimited:false, currentFile:"" });
    try {
      const form = new FormData(); form.append("file", xlFile);
      const r = await fetch(`${await api.base()}/ingest/import`, { method:"POST", body:form });
      if (!r.ok) throw new Error((await r.json().catch(()=>({}))).detail || r.statusText);
      setResult(await r.json());
    } catch(e) { setError(e.message); }
    finally { setBusy(false); setProgress({ done:0, total:0, label:"", rateLimited:false, currentFile:"" }); }
  }

  function reset() {
    setPdfs([]); setPreview(null); setXlFile(null);
    setResult(null); setError(null); setSiteType(null);
    setProgress({ done:0, total:0, label:"", rateLimited:false, currentFile:"" });
  }

  const totalRows = preview ? Object.values(preview.summary||{}).reduce((a,b)=>a+b,0) : 0;

  return (
    <div style={{maxWidth:860,margin:"0 auto",paddingBottom:40}}>

      {busy && <LoadingOverlay progress={progress} onCancel={cancel} />}

      {/* site type picker */}
      {!siteType && !preview && !result && (
        <div style={{marginBottom:24}}>
          <p style={{fontWeight:500,margin:"0 0 12px",fontSize:15}}>What kind of site is this?</p>
          <div style={{display:"flex",gap:12,flexWrap:"wrap"}}>
            <button onClick={() => setSiteType("new")} style={{
              flex:1,minWidth:220,padding:"16px 20px",borderRadius:10,textAlign:"left",cursor:"pointer",
              border:"2px solid var(--border-accent)",background:"var(--bg-accent)"}}>
              <div style={{fontWeight:500,fontSize:14,color:"var(--text-accent)",marginBottom:4}}>
                ✦ New site
              </div>
              <div style={{fontSize:12,color:"var(--text-accent)",opacity:.8,lineHeight:1.5}}>
                Piling hasn't happened yet. Upload geotech data to predict pre-drill vs driven per zone.
              </div>
            </button>
            <button onClick={() => setSiteType("completed")} style={{
              flex:1,minWidth:220,padding:"16px 20px",borderRadius:10,textAlign:"left",cursor:"pointer",
              border:"2px solid var(--border-strong)",background:"var(--surface-1)"}}>
              <div style={{fontWeight:500,fontSize:14,color:"var(--text-primary)",marginBottom:4}}>
                ✓ Completed site
              </div>
              <div style={{fontSize:12,color:"var(--text-secondary)",lineHeight:1.5}}>
                Piling is done. Decisions are known. Adds to the historical database for predictions.
              </div>
            </button>
          </div>
        </div>
      )}

      {siteType && !preview && !result && (
        <div style={{display:"flex",alignItems:"center",gap:10,marginBottom:20,
          padding:"8px 14px",background:"var(--surface-1)",borderRadius:8,border:"1px solid var(--border)"}}>
          <span style={{fontSize:13,color:"var(--text-secondary)"}}>Adding as:</span>
          <span style={{fontSize:13,fontWeight:500,color:"var(--text-primary)"}}>
            {siteType==="new" ? "New site (predict decisions)" : "Completed site (historical)"}
          </span>
          <button onClick={() => setSiteType(null)}
            style={{marginLeft:6,background:"none",border:"none",cursor:"pointer",
              color:"var(--text-muted)",fontSize:12}}>change</button>
        </div>
      )}

      {/* step progress bar */}
      {siteType && (
        <div style={{display:"flex",gap:0,marginBottom:28,borderRadius:8,overflow:"hidden"}}>
          {[["1","Upload PDFs"],["2","Review & download"],["3","Import to graph"]].map(([n,label],i) => (
            <div key={n} style={{flex:1,padding:"10px 16px",fontSize:13,
              fontWeight:stage>=i+1?500:400,
              background:stage>i+1?"var(--bg-success)":stage===i+1?"var(--bg-accent)":"var(--surface-1)",
              color:stage>=i+1?(stage>i+1?"var(--text-success)":"var(--text-accent)"):"var(--text-muted)",
              borderRight:i<2?"1px solid var(--border)":"none",
              display:"flex",alignItems:"center",gap:8}}>
              <span style={{width:22,height:22,borderRadius:"50%",display:"flex",
                alignItems:"center",justifyContent:"center",fontSize:11,fontWeight:600,
                background:stage>i+1?"var(--bg-success)":stage===i+1?"var(--text-accent)":"var(--border-strong)",
                color:stage===i+1?"#fff":"inherit"}}>
                {stage>i+1?"✓":n}
              </span>
              {label}
            </div>
          ))}
        </div>
      )}

      {/* ── stage 1 ── */}
      {stage===1 && siteType && (
        <div style={{display:"flex",flexDirection:"column",gap:20}}>
          <FileDropZone accept=".pdf" multiple disabled={busy}
            label="Drop your PDFs here or click to browse"
            sub="PLT reports, GIR, GFR — upload as many as you have"
            onFiles={fs => setPdfs(prev => {
              const names = new Set(prev.map(f => f.name));
              return [...prev, ...fs.filter(f => !names.has(f.name))];
            })} />

          {pdfs.length > 0 && (
            <div style={{display:"flex",flexDirection:"column",gap:6}}>
              {pdfs.map((f,i) => (
                <div key={f.name} style={{display:"flex",alignItems:"center",gap:10,
                  padding:"8px 12px",background:"var(--surface-1)",borderRadius:8,
                  border:"1px solid var(--border)"}}>
                  <i className="ti ti-file-type-pdf"
                    style={{color:"var(--text-danger)",fontSize:18}} aria-hidden />
                  <span style={{flex:1,fontSize:13}}>{f.name}</span>
                  <span style={{fontSize:12,color:"var(--text-muted)"}}>
                    {(f.size/1024).toFixed(0)} KB
                  </span>
                  <button onClick={() => setPdfs(p => p.filter((_,j) => j!==i))}
                    style={{background:"none",border:"none",cursor:"pointer",
                      color:"var(--text-muted)",fontSize:16}}>×</button>
                </div>
              ))}
            </div>
          )}

          {error && (
            <div style={{padding:"10px 14px",background:"var(--bg-danger)",
              border:"1px solid var(--border-danger)",borderRadius:8,
              color:"var(--text-danger)",fontSize:13,whiteSpace:"pre-wrap"}}>
              {error}
            </div>
          )}

          <div style={{display:"flex",gap:10,flexWrap:"wrap"}}>
            <button className="btn" disabled={pdfs.length===0||busy} onClick={runExtract}>
              ✦ Extract data
            </button>
            <button className="btn ghost" onClick={downloadBlank}>
              ↓ Blank template
            </button>
          </div>
          <p style={{fontSize:12,color:"var(--text-muted)",margin:0}}>
            No PDFs? Download the blank template, fill manually, then upload in step 3.
          </p>
        </div>
      )}

      {/* ── stage 2 ── */}
      {stage===2 && preview && (
        <div style={{display:"flex",flexDirection:"column",gap:20}}>
          <div style={{display:"flex",alignItems:"center",gap:12,flexWrap:"wrap"}}>
            <span style={{fontWeight:500}}>
              Extracted from {pdfs.length} PDF{pdfs.length!==1?"s":""}
            </span>
            <Badge n={`${totalRows} rows across ${Object.keys(preview.data).length} sheets`} />
            {preview.errors?.length > 0 &&
              <Badge n={`${preview.errors.length} warnings`} color="warning" />}
          </div>

          {preview.errors?.length > 0 && (
            <div style={{padding:"10px 14px",background:"var(--bg-warning)",
              border:"1px solid var(--border-warning)",borderRadius:8,
              fontSize:12,color:"var(--text-warning)",whiteSpace:"pre-wrap"}}>
              {preview.errors.join("\n")}
            </div>
          )}

          {SHEET_ORDER.filter(s => preview.data[s]?.length).map(sheet => (
            <div key={sheet} style={{border:"1px solid var(--border)",borderRadius:10}}>
              <div onClick={() => setOpen(o => ({...o,[sheet]:!o[sheet]}))}
                style={{display:"flex",alignItems:"center",gap:10,padding:"10px 14px",
                  cursor:"pointer",userSelect:"none"}}>
                <span style={{fontSize:12,color:"var(--text-muted)"}}>{open[sheet]?"▲":"▼"}</span>
                <span style={{fontWeight:500,flex:1,fontSize:14}}>{sheet}</span>
                <Badge n={preview.data[sheet].length} />
              </div>
              {open[sheet] && (
                <div style={{padding:"0 14px 14px"}}>
                  <PreviewTable rows={preview.data[sheet]} />
                </div>
              )}
            </div>
          ))}

          <div style={{display:"flex",gap:10,flexWrap:"wrap",paddingTop:8}}>
            <button className="btn" onClick={downloadPrefilled} disabled={busy}>
              ↓ {busy?"Preparing…":"Download pre-filled spreadsheet"}
            </button>
            <button className="btn ghost"
              onClick={() => { setPreview(null); setError(null); }}>
              ← Back
            </button>
          </div>

          <div style={{padding:"12px 16px",background:"var(--surface-1)",
            border:"1px solid var(--border)",borderRadius:10,fontSize:13}}>
            <p style={{margin:"0 0 6px",fontWeight:500}}>Next steps</p>
            <ol style={{margin:0,paddingLeft:18,color:"var(--text-secondary)",lineHeight:1.8}}>
              <li>Download the pre-filled spreadsheet</li>
              <li>Fill in grey cells and assign zone IDs from your site map</li>
              {siteType==="completed"
                ? <li>Make sure zone decisions (Pre-Drill / Driven) are filled in</li>
                : <li>Leave zone decisions blank — the tool will predict them</li>}
              <li>Upload the completed file below to import to the graph</li>
            </ol>
          </div>

          <hr style={{border:"none",borderTop:"1px solid var(--border)",margin:"4px 0"}} />
          <p style={{fontWeight:500,margin:"0 0 8px"}}>Upload completed spreadsheet to import</p>
          <FileDropZone accept=".xlsx" multiple={false} disabled={busy}
            label="Drop your completed .xlsx here"
            sub="The file you downloaded and edited"
            onFiles={([f]) => setXlFile(f)} />
          {xlFile && (
            <div style={{display:"flex",alignItems:"center",gap:10,padding:"8px 12px",
              background:"var(--surface-1)",borderRadius:8,border:"1px solid var(--border)"}}>
              <i className="ti ti-file-spreadsheet"
                style={{color:"var(--text-success)",fontSize:18}} aria-hidden />
              <span style={{flex:1,fontSize:13}}>{xlFile.name}</span>
              <button className="btn" disabled={busy} onClick={runImport}>
                → Import to graph
              </button>
            </div>
          )}
          {error && (
            <div style={{padding:"10px 14px",background:"var(--bg-danger)",
              border:"1px solid var(--border-danger)",borderRadius:8,
              color:"var(--text-danger)",fontSize:13}}>{error}</div>
          )}
        </div>
      )}

      {/* ── stage 3 ── */}
      {stage===3 && result && (
        <div style={{display:"flex",flexDirection:"column",gap:16}}>
          <div style={{padding:"16px 20px",background:"var(--bg-success)",
            border:"1px solid var(--border-success)",borderRadius:10,
            color:"var(--text-success)",fontWeight:500}}>
            ✓ Import complete
            {siteType==="new" && (
              <span style={{fontWeight:400,fontSize:13,marginLeft:8}}>
                — zone decisions can be set from the Sites page
              </span>
            )}
          </div>
          {Object.entries(result.imported||{}).map(([sheet,r]) => (
            <div key={sheet} style={{display:"flex",alignItems:"center",gap:10,
              padding:"8px 14px",background:"var(--surface-1)",
              border:"1px solid var(--border)",borderRadius:8}}>
              <span style={{flex:1,fontSize:13,fontWeight:500}}>{sheet}</span>
              {r.error
                ? <Badge n={`Error: ${r.error}`} color="danger" />
                : <Badge n={`${r.saved??"?"} saved`} color="success" />}
              {r.errors?.length > 0 &&
                <Badge n={`${r.errors.length} skipped`} color="warning" />}
            </div>
          ))}
          <button className="btn ghost" style={{marginTop:8}} onClick={reset}>
            + Add another site
          </button>
        </div>
      )}

    </div>
  );
}