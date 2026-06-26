import React, { useState, useEffect, useCallback, useRef } from "react";
import { api } from "../api.js";

// natural sort comparator: "1.10" > "1.9", "10.1" > "2.1"
function natCmp(a, b) {
  const re = /(\d+|\D+)/g;
  const pa = String(a).match(re) || [];
  const pb = String(b).match(re) || [];
  for (let i = 0; i < Math.max(pa.length, pb.length); i++) {
    if (i >= pa.length) return -1;
    if (i >= pb.length) return 1;
    const na = Number(pa[i]), nb = Number(pb[i]);
    if (!isNaN(na) && !isNaN(nb)) { if (na !== nb) return na - nb; }
    else { if (pa[i] !== pb[i]) return pa[i] < pb[i] ? -1 : 1; }
  }
  return 0;
}


// ── shared helpers ────────────────────────────────────────────────────────────
function StatPill({ label, value, color = "accent" }) {
  if (!value) return null;
  return (
    <span style={{
      display:"inline-flex",alignItems:"center",gap:4,
      padding:"2px 8px",borderRadius:10,fontSize:12,
      background:`var(--bg-${color})`,color:`var(--text-${color})`,
      border:`1px solid var(--border-${color})`,
    }}>{label}: <strong>{value}</strong></span>
  );
}

function DecisionBadge({ decision }) {
  if (!decision) return <span style={{fontSize:12,color:"var(--text-muted)",fontStyle:"italic"}}>undecided</span>;
  const color = decision === "Pre-Drill" ? "warning" : "success";
  return (
    <span style={{
      fontSize:12,padding:"2px 8px",borderRadius:10,fontWeight:500,
      background:`var(--bg-${color})`,color:`var(--text-${color})`,
      border:`1px solid var(--border-${color})`,
    }}>{decision}</span>
  );
}

// ── delete confirmation dialog ────────────────────────────────────────────────
function DeleteDialog({ site, busy, onConfirm, onCancel }) {
  const [typed, setTyped] = useState("");
  const match = typed === site.site_id;
  return (
    <div style={{position:"fixed",inset:0,zIndex:200,background:"rgba(0,0,0,0.6)",
      display:"flex",alignItems:"center",justifyContent:"center",padding:24}}>
      <div style={{background:"var(--surface-2)",borderRadius:14,padding:"28px 28px 24px",
        maxWidth:440,width:"100%",border:"1px solid var(--border-danger)"}}>
        <div style={{display:"flex",gap:12,alignItems:"flex-start",marginBottom:16}}>
          <i className="ti ti-alert-triangle" style={{fontSize:28,color:"var(--text-danger)",flexShrink:0}} aria-hidden/>
          <div>
            <p style={{margin:"0 0 6px",fontWeight:500,fontSize:16}}>Delete {site.name || site.site_id}?</p>
            <p style={{margin:0,fontSize:13,color:"var(--text-secondary)",lineHeight:1.6}}>
              Permanently removes this site and all data that belongs exclusively to it.
              SoilType nodes and shared ground models are preserved.<br/><br/>
              <strong style={{color:"var(--text-danger)"}}>This cannot be undone.</strong>
            </p>
          </div>
        </div>
        <label style={{fontSize:13,color:"var(--text-secondary)",display:"block",marginBottom:6}}>
          Type <strong style={{color:"var(--text-primary)"}}>{site.site_id}</strong> to confirm:
        </label>
        <input autoFocus value={typed} onChange={e=>setTyped(e.target.value)}
          onKeyDown={e=>e.key==="Enter"&&match&&!busy&&onConfirm()}
          style={{width:"100%",padding:"8px 12px",borderRadius:8,fontSize:13,
            border:`1px solid ${match?"var(--border-danger)":"var(--border-strong)"}`,
            background:"var(--surface-1)",color:"var(--text-primary)",boxSizing:"border-box"}}
          placeholder={site.site_id}/>
        <div style={{display:"flex",gap:10,justifyContent:"flex-end",marginTop:16}}>
          <button className="btn ghost" onClick={onCancel} disabled={busy}>Cancel</button>
          <button disabled={!match||busy} onClick={onConfirm}
            style={{padding:"8px 20px",borderRadius:8,border:"none",
              cursor:match?"pointer":"not-allowed",fontWeight:500,fontSize:13,
              background:match?"var(--text-danger)":"var(--border-strong)",color:"#fff"}}>
            {busy?<><i className="ti ti-loader-2" style={{animation:"spin 1s linear infinite"}} aria-hidden/> Deleting…</>
                 :<><i className="ti ti-trash" aria-hidden/> Delete permanently</>}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── zone decision panel ───────────────────────────────────────────────────────
function ZonePanel({ site, onClose }) {
  const [zones,   setZones]   = useState([]);
  const [pending, setPending] = useState({});
  const [loading, setLoading] = useState(true);
  const [saving,  setSaving]  = useState(false);
  const [filter,  setFilter]  = useState("all");
  const [history, setHistory] = useState([]);

  useEffect(() => {
    api.listZones(site.site_id).then(z => { setZones([...z].sort((a,b)=>natCmp(a.zone_id,b.zone_id))); setLoading(false); });
  }, [site.site_id]);

  const displayed = zones.map(z => ({
    ...z,
    decision: z.zone_id in pending ? pending[z.zone_id] : z.decision,
    isDirty:  z.zone_id in pending && pending[z.zone_id] !== z.decision,
  }));

  const nPre   = displayed.filter(z => z.decision === "Pre-Drill").length;
  const nDriv  = displayed.filter(z => z.decision === "Driven").length;
  const nUnd   = displayed.filter(z => !z.decision).length;
  const nDirty = Object.entries(pending).filter(([id, dec]) => {
    const z = zones.find(z => z.zone_id === id);
    return z && z.decision !== dec;
  }).length;

  function stage(zoneId, decision) {
    const z = zones.find(z => z.zone_id === zoneId);
    if (!z) return;
    if (decision === z.decision) {
      setPending(p => { const n = {...p}; delete n[zoneId]; return n; });
    } else {
      setPending(p => ({...p, [zoneId]: decision}));
    }
  }

  function stageAll(decision) {
    const patch = {};
    zones.forEach(z => { if (z.decision !== decision) patch[z.zone_id] = decision; });
    setPending(p => ({...p, ...patch}));
  }

  function discardAll() { setPending({}); }

  async function save() {
    const dirty = Object.entries(pending).filter(([id, dec]) => {
      const z = zones.find(z => z.zone_id === id);
      return z && z.decision !== dec;
    });
    if (!dirty.length) return;
    setSaving(true);
    const undoRecord = dirty.map(([id, to]) => ({
      zone_id: id,
      from: zones.find(z => z.zone_id === id)?.decision ?? null,
      to,
    }));
    try {
      await Promise.all(dirty.map(([id, dec]) =>
        api.setZoneDecision(site.site_id, id, dec)
      ));
      setZones(zs => zs.map(z =>
        z.zone_id in pending ? {...z, decision: pending[z.zone_id]} : z
      ));
      setPending({});
      setHistory(h => [...h, undoRecord]);
    } catch(e) { console.error("Save failed", e); }
    finally { setSaving(false); }
  }

  async function undo() {
    if (!history.length) return;
    setSaving(true);
    const last = history[history.length - 1];
    try {
      await Promise.all(last.map(({zone_id, from}) =>
        api.setZoneDecision(site.site_id, zone_id, from)
      ));
      setZones(zs => zs.map(z => {
        const rev = last.find(r => r.zone_id === z.zone_id);
        return rev ? {...z, decision: rev.from} : z;
      }));
      setHistory(h => h.slice(0, -1));
      setPending({});
    } catch(e) { console.error("Undo failed", e); }
    finally { setSaving(false); }
  }

  const filtered = displayed.filter(z => {
    if (filter === "undecided") return !z.decision;
    if (filter === "predrill")  return z.decision === "Pre-Drill";
    if (filter === "driven")    return z.decision === "Driven";
    if (filter === "unsaved")   return z.isDirty;
    return true;
  });

  return (
    <div style={{position:"fixed",inset:0,zIndex:150,background:"rgba(0,0,0,0.6)",
      display:"flex",alignItems:"stretch",justifyContent:"flex-end"}}>
      <div style={{width:"min(680px,100vw)",background:"var(--surface-2)",
        display:"flex",flexDirection:"column",
        boxShadow:"-4px 0 32px rgba(0,0,0,.5)",overflow:"hidden",
        borderLeft:"1px solid var(--border-strong)"}}>

        {/* header */}
        <div style={{padding:"16px 20px 12px",borderBottom:"1px solid var(--border)"}}>
          <div style={{display:"flex",alignItems:"center",gap:10,marginBottom:10}}>
            <div style={{flex:1}}>
              <div style={{fontWeight:600,fontSize:16,color:"var(--text-primary)"}}>{site.name}</div>
              <div style={{fontSize:12,color:"var(--text-secondary)"}}>Pre-drill / driven decisions per zone</div>
            </div>
            <button onClick={onClose}
              onMouseOver={e=>e.currentTarget.style.background="rgba(248,113,113,0.18)"}
              onMouseOut={e=>e.currentTarget.style.background="rgba(255,255,255,0.08)"}
              style={{background:"rgba(255,255,255,0.08)",border:"1px solid var(--border-strong)",
                borderRadius:8,cursor:"pointer",color:"var(--text-primary)",
                padding:"5px 9px",fontSize:17,lineHeight:1}}>×</button>
          </div>

          {/* counts */}
          <div style={{display:"flex",gap:6,flexWrap:"wrap",marginBottom:12}}>
            <StatPill label="Pre-Drill" value={nPre} color="warning"/>
            <StatPill label="Driven" value={nDriv} color="success"/>
            {nUnd > 0 && <StatPill label="Undecided" value={nUnd} color="danger"/>}
            {nDirty > 0 && (
              <span style={{fontSize:12,padding:"2px 8px",borderRadius:10,fontWeight:500,
                background:"rgba(139,92,246,0.15)",color:"#a78bfa",
                border:"1px solid rgba(139,92,246,0.3)"}}>
                {nDirty} unsaved
              </span>
            )}
          </div>

          {/* save / undo / bulk actions */}
          <div style={{display:"flex",gap:8,flexWrap:"wrap",alignItems:"center"}}>
            <button disabled={nDirty===0||saving} onClick={save}
              style={{padding:"6px 16px",borderRadius:8,border:"none",
                cursor:nDirty>0?"pointer":"not-allowed",fontWeight:600,fontSize:13,
                background:nDirty>0?"var(--pcl-gold)":"var(--border-strong)",
                color:nDirty>0?"#050608":"var(--text-muted)",transition:"background .12s"}}>
              {saving ? "Saving…" : `Save${nDirty > 0 ? ` (${nDirty})` : ""}`}
            </button>
            <button disabled={history.length===0||saving} onClick={undo}
              style={{padding:"6px 14px",borderRadius:8,fontSize:13,cursor:"pointer",
                background:"rgba(255,255,255,0.06)",border:"1px solid var(--border-strong)",
                color:history.length?"var(--text-primary)":"var(--text-muted)",fontWeight:500}}>
              ↩ Undo{history.length > 0 ? ` (${history[history.length-1].length})` : ""}
            </button>
            {nDirty > 0 && (
              <button onClick={discardAll}
                style={{padding:"5px 12px",borderRadius:8,fontSize:12,cursor:"pointer",
                  background:"none",border:"1px solid var(--border)",color:"var(--text-muted)"}}>
                Discard
              </button>
            )}
            <div style={{flex:1}}/>
            <button className="btn ghost" style={{fontSize:12,padding:"4px 10px"}}
              onClick={() => stageAll("Pre-Drill")}>All Pre-Drill</button>
            <button className="btn ghost" style={{fontSize:12,padding:"4px 10px"}}
              onClick={() => stageAll("Driven")}>All Driven</button>
          </div>
        </div>

        {/* filter bar */}
        <div style={{padding:"8px 20px",borderBottom:"1px solid var(--border)",display:"flex",gap:6,flexWrap:"wrap"}}>
          {[["all","All"],["undecided","Undecided"],["predrill","Pre-Drill"],
            ["driven","Driven"],["unsaved","Unsaved"]].map(([v,l]) => (
            <button key={v} onClick={() => setFilter(v)}
              style={{fontSize:12,padding:"3px 10px",borderRadius:10,
                border:"1px solid var(--border)",cursor:"pointer",
                background:filter===v?"var(--text-accent)":"var(--surface-1)",
                color:filter===v?"#000":"var(--text-secondary)"}}>
              {l}{v==="unsaved"&&nDirty>0?` (${nDirty})`:""}
            </button>
          ))}
        </div>

        {/* zone list */}
        <div style={{flex:1,overflowY:"auto",padding:"8px 12px"}}>
          {loading && (
            <div style={{color:"var(--text-muted)",textAlign:"center",padding:32,fontSize:13}}>
              Loading zones…
            </div>
          )}
          {filtered.map(z => (
            <div key={z.zone_id} style={{display:"flex",alignItems:"center",gap:10,
              padding:"8px 10px",borderRadius:8,marginBottom:4,
              background:z.isDirty?"rgba(139,92,246,0.07)":"var(--surface-1)",
              border:`1px solid ${z.isDirty?"rgba(139,92,246,0.25)":"var(--border)"}`,
              transition:"background .12s,border-color .12s"}}>
              <div style={{flex:1,minWidth:0}}>
                <span style={{fontSize:13,fontWeight:500,color:"var(--text-primary)"}}>{z.zone_id}</span>
                {z.isDirty && <span style={{fontSize:11,color:"#a78bfa",marginLeft:8}}>unsaved</span>}
              </div>
              <span style={{fontSize:12,minWidth:72,textAlign:"right",fontWeight:z.decision?500:400,
                fontStyle:!z.decision?"italic":"normal",
                color:z.decision==="Pre-Drill"?"var(--text-warning)":
                      z.decision==="Driven"?"var(--text-success)":"var(--text-muted)"}}>
                {z.decision || "undecided"}
              </span>
              <div style={{display:"flex",gap:4,flexShrink:0}}>
                {["Pre-Drill","Driven"].map(opt => (
                  <button key={opt} onClick={() => stage(z.zone_id, z.decision===opt?null:opt)}
                    style={{fontSize:11,padding:"3px 8px",borderRadius:6,border:"none",cursor:"pointer",
                      background:z.decision===opt
                        ?(opt==="Pre-Drill"?"#BA7517":"#1D9E75"):"var(--border-strong)",
                      color:z.decision===opt?"#fff":"var(--text-secondary)",
                      transition:"background .1s"}}>
                    {opt}
                  </button>
                ))}
                {z.decision && (
                  <button onClick={() => stage(z.zone_id, null)}
                    style={{fontSize:11,padding:"3px 7px",borderRadius:6,border:"none",
                      cursor:"pointer",background:"var(--border)",color:"var(--text-muted)"}}>
                    ×
                  </button>
                )}
              </div>
            </div>
          ))}
          {!loading && filtered.length===0 && (
            <div style={{color:"var(--text-muted)",fontSize:13,textAlign:"center",padding:24}}>
              No zones match this filter.
            </div>
          )}
        </div>

        {/* sticky footer save bar */}
        {nDirty > 0 && (
          <div style={{padding:"12px 20px",borderTop:"1px solid var(--border-strong)",
            background:"rgba(139,92,246,0.08)",display:"flex",alignItems:"center",gap:10}}>
            <span style={{flex:1,fontSize:13,color:"#a78bfa"}}>
              {nDirty} unsaved change{nDirty!==1?"s":""} — click Save to apply
            </span>
            <button onClick={discardAll}
              style={{fontSize:12,padding:"5px 12px",borderRadius:7,cursor:"pointer",
                background:"none",border:"1px solid var(--border)",color:"var(--text-muted)"}}>
              Discard
            </button>
            <button onClick={save} disabled={saving}
              style={{fontSize:13,padding:"6px 20px",borderRadius:7,border:"none",cursor:"pointer",
                background:"var(--pcl-gold)",color:"#050608",fontWeight:600}}>
              {saving ? "Saving…" : "Save changes"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}


// ── completed site quick-create form ─────────────────────────────────────────
function CompletedSiteForm({ onDone, onBack, onCancel }) {
  const [id,   setId]   = useState("");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [err,  setErr]  = useState(null);
  async function submit() {
    if (!id.trim()) { setErr("Site ID is required"); return; }
    setBusy(true); setErr(null);
    try {
      await api.addNode("site", { id:id.trim(), name:name.trim()||id.trim(), status:"completed" });
      onDone();
    } catch(e) { setErr(e.message); setBusy(false); }
  }
  return (
    <div style={{background:"var(--surface-2)",borderRadius:14,padding:"28px 28px 24px",
      maxWidth:420,width:"100%",border:"1px solid var(--border)"}}>
      <div style={{display:"flex",alignItems:"center",gap:10,marginBottom:20}}>
        <button onClick={onBack} style={{background:"none",border:"none",cursor:"pointer",color:"var(--text-muted)",fontSize:18}}>←</button>
        <span style={{fontWeight:500,fontSize:15,flex:1}}>Add completed site</span>
        <button onClick={onCancel} style={{background:"none",border:"none",cursor:"pointer",color:"var(--text-muted)",fontSize:18}}>×</button>
      </div>
      <p style={{fontSize:13,color:"var(--text-secondary)",margin:"0 0 16px",lineHeight:1.6}}>
        Create the site node. Upload its data and set zone decisions afterwards.
      </p>
      <div style={{display:"flex",flexDirection:"column",gap:12,marginBottom:16}}>
        <div>
          <label style={{fontSize:12,color:"var(--text-secondary)",display:"block",marginBottom:4}}>
            Site ID <span style={{color:"var(--text-danger)"}}>*</span>
          </label>
          <input value={id} onChange={e=>setId(e.target.value)} placeholder="e.g. SITE-MARYVALE"
            style={{width:"100%",padding:"8px 12px",borderRadius:8,fontSize:13,
              border:"1px solid var(--border-strong)",background:"var(--surface-1)",
              color:"var(--text-primary)",boxSizing:"border-box"}}/>
        </div>
        <div>
          <label style={{fontSize:12,color:"var(--text-secondary)",display:"block",marginBottom:4}}>Site name</label>
          <input value={name} onChange={e=>setName(e.target.value)} placeholder="e.g. Maryvale Solar Farm"
            style={{width:"100%",padding:"8px 12px",borderRadius:8,fontSize:13,
              border:"1px solid var(--border-strong)",background:"var(--surface-1)",
              color:"var(--text-primary)",boxSizing:"border-box"}}/>
        </div>
      </div>
      {err && <div style={{fontSize:12,color:"var(--text-danger)",marginBottom:12}}>{err}</div>}
      <div style={{display:"flex",gap:10,justifyContent:"flex-end"}}>
        <button className="btn ghost" onClick={onCancel}>Cancel</button>
        <button className="btn" disabled={busy||!id.trim()} onClick={submit}>
          {busy?"Creating…":"Create site"}
        </button>
      </div>
    </div>
  );
}

// ── add site dialog (type picker) ─────────────────────────────────────────────
function AddSiteDialog({ onDone, onCancel, onGoIngest }) {
  const [siteType, setSiteType] = useState(null);
  if (!siteType) return (
    <div style={{position:"fixed",inset:0,zIndex:200,background:"rgba(0,0,0,0.6)",
      display:"flex",alignItems:"center",justifyContent:"center",padding:24}}>
      <div style={{background:"var(--surface-2)",borderRadius:14,padding:"28px 28px 24px",
        maxWidth:480,width:"100%",border:"1px solid var(--border)"}}>
        <div style={{display:"flex",alignItems:"center",gap:10,marginBottom:20}}>
          <span style={{fontWeight:500,fontSize:16,flex:1}}>Add a site</span>
          <button onClick={onCancel} style={{background:"none",border:"none",cursor:"pointer",
            color:"var(--text-muted)",fontSize:18}}>×</button>
        </div>
        <div style={{display:"flex",flexDirection:"column",gap:12}}>
          <button onClick={()=>onGoIngest("new")} style={{padding:"16px 20px",borderRadius:10,textAlign:"left",cursor:"pointer",
            border:"2px solid var(--border-accent)",background:"var(--bg-accent)"}}>
            <div style={{fontWeight:500,fontSize:14,color:"var(--text-accent)",marginBottom:4}}>✦ New site — predict decisions</div>
            <div style={{fontSize:12,color:"var(--text-accent)",opacity:.8,lineHeight:1.5}}>
              Piling hasn't happened yet. Upload geotech data and the tool will predict pre-drill vs driven.
            </div>
          </button>
          <button onClick={()=>setSiteType("completed")} style={{padding:"16px 20px",borderRadius:10,textAlign:"left",cursor:"pointer",
            border:"2px solid var(--border-strong)",background:"var(--surface-1)"}}>
            <div style={{fontWeight:500,fontSize:14,color:"var(--text-primary)",marginBottom:4}}>✓ Completed site</div>
            <div style={{fontSize:12,color:"var(--text-secondary)",lineHeight:1.5}}>
              Piling is done. Decisions are known. Adds to historical database for future predictions.
            </div>
          </button>
        </div>
      </div>
    </div>
  );
  return (
    <div style={{position:"fixed",inset:0,zIndex:200,background:"rgba(0,0,0,0.6)",
      display:"flex",alignItems:"center",justifyContent:"center",padding:24}}>
      <CompletedSiteForm onDone={onDone} onBack={()=>setSiteType(null)} onCancel={onCancel}/>
    </div>
  );
}

// ── site card ─────────────────────────────────────────────────────────────────
function SiteCard({ site, onDelete, onZones, onGoIngest }) {
  const isNew       = site.status === "new";
  const isCompleted = site.status === "completed";
  return (
    <div style={{border:`1px solid ${isNew?"var(--border-accent)":"var(--border)"}`,
      borderRadius:12,padding:"16px 18px",
      background:isNew?"var(--bg-accent)":"var(--surface-1)"}}>
      <div style={{display:"flex",alignItems:"flex-start",gap:12}}>
        <div style={{flex:1,minWidth:0}}>
          <div style={{display:"flex",alignItems:"center",gap:8,marginBottom:6,flexWrap:"wrap"}}>
            <span style={{fontWeight:500,fontSize:15,
              color:isNew?"var(--text-accent)":"var(--text-primary)"}}>
              {site.name || site.site_id}
            </span>
            <code style={{fontSize:11,padding:"1px 6px",borderRadius:4,
              background:"var(--surface-0)",color:"var(--text-muted)",border:"1px solid var(--border)"}}>
              {site.site_id}
            </code>
            {isNew && (
              <span style={{fontSize:11,padding:"2px 8px",borderRadius:10,fontWeight:500,
                background:"var(--bg-accent)",color:"var(--text-accent)",border:"1px solid var(--border-accent)"}}>
                ✦ New — predictions pending
              </span>
            )}
            {isCompleted && (
              <span style={{fontSize:11,padding:"2px 8px",borderRadius:10,fontWeight:500,
                background:"var(--bg-success)",color:"var(--text-success)",border:"1px solid var(--border-success)"}}>
                ✓ Completed
              </span>
            )}
          </div>
          <div style={{display:"flex",gap:6,flexWrap:"wrap"}}>
            <StatPill label="zones" value={site.zones}/>
            <StatPill label="piles" value={site.pile_locations}/>
            <StatPill label="DPSH" value={site.dpsh_probes}/>
            <StatPill label="boreholes" value={site.boreholes}/>
            <StatPill label="test pits" value={site.test_pits}/>
          </div>
        </div>
        <div style={{display:"flex",gap:6,flexShrink:0,flexWrap:"wrap",justifyContent:"flex-end"}}>
          {isNew && (
            <button className="btn" style={{fontSize:12,padding:"6px 12px"}}
              onClick={()=>onGoIngest(site.site_id)}>
              ✦ Get predictions
            </button>
          )}
          {site.zones > 0 && (
            <button className="btn ghost" style={{fontSize:12,padding:"6px 12px"}}
              onClick={()=>onZones(site)}>
              ⊞ Zone decisions
            </button>
          )}
          <button onClick={()=>onDelete(site)}
            style={{padding:"6px 12px",borderRadius:8,border:"1px solid var(--border-danger)",
              background:"transparent",color:"var(--text-danger)",cursor:"pointer",
              fontSize:12,display:"flex",alignItems:"center",gap:5}}>
            ✕ Remove
          </button>
        </div>
      </div>
    </div>
  );
}


export default function ManageSites({ onNavigate }) {
  const [sites,   setSites]   = useState([]);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);
  const [delSite, setDelSite] = useState(null);
  const [busyDel, setBusyDel] = useState(false);
  const [zoneSite,setZoneSite]= useState(null);
  const [addOpen, setAddOpen] = useState(false);
  const [doneMsg, setDoneMsg] = useState(null);

  const load = useCallback(async()=>{
    setLoading(true); setError(null);
    try { setSites(await api.listSites()); }
    catch(e){ setError(e.message); }
    finally { setLoading(false); }
  },[]);

  useEffect(()=>{ load(); },[load]);

  async function handleDelete(){
    if(!delSite) return;
    setBusyDel(true);
    try{
      const r = await api.deleteSite(delSite.site_id);
      setDoneMsg(`${delSite.site_id} deleted.`);
      setDelSite(null);
      await load();
    } catch(e){ setError(e.message); setDelSite(null); }
    finally{ setBusyDel(false); }
  }

  const newSites = sites.filter(s=>s.status==="new");
  const compSites = sites.filter(s=>s.status==="completed");
  const otherSites = sites.filter(s=>!s.status||(!["new","completed"].includes(s.status)));

  return (
    <div style={{maxWidth:800,margin:"0 auto",paddingBottom:40,position:"relative"}}>

      {delSite && <DeleteDialog site={delSite} busy={busyDel}
        onConfirm={handleDelete} onCancel={()=>setDelSite(null)}/>}
      {zoneSite && <ZonePanel site={zoneSite} onClose={()=>setZoneSite(null)}/>}
      {addOpen  && <AddSiteDialog
        onDone={()=>{ setAddOpen(false); load(); }}
        onCancel={()=>setAddOpen(false)}
        onGoIngest={(type)=>{ setAddOpen(false); onNavigate&&onNavigate("ingest",{siteType:type}); }}
      />}

      {/* header */}
      <div style={{display:"flex",alignItems:"center",gap:10,marginBottom:24}}>
        <div style={{flex:1}}>
          <h3 style={{margin:0,fontSize:18}}>Sites</h3>
          <p style={{margin:0,fontSize:13,color:"var(--text-secondary)"}}>
            Manage historical and new project sites.
          </p>
        </div>
        <button className="btn ghost" onClick={load} disabled={loading}>
          <i className={`ti ti-refresh${loading?" ti-spin":""}`} aria-hidden/> Refresh
        </button>
        <button className="btn" onClick={()=>setAddOpen(true)}>
          <i className="ti ti-plus" aria-hidden/> Add site
        </button>
      </div>

      {doneMsg&&(
        <div style={{display:"flex",alignItems:"center",gap:10,marginBottom:16,
          padding:"10px 16px",background:"var(--bg-success)",border:"1px solid var(--border-success)",
          borderRadius:10,color:"var(--text-success)",fontSize:13}}>
          <i className="ti ti-circle-check" aria-hidden/> {doneMsg}
          <button onClick={()=>setDoneMsg(null)} style={{marginLeft:"auto",background:"none",
            border:"none",cursor:"pointer",color:"inherit"}}>×</button>
        </div>
      )}

      {error&&(
        <div style={{padding:"10px 14px",background:"var(--bg-danger)",border:"1px solid var(--border-danger)",
          borderRadius:8,color:"var(--text-danger)",fontSize:13,marginBottom:16}}>
          <i className="ti ti-alert-circle" aria-hidden/> {error}
        </div>
      )}

      {loading&&!sites.length&&(
        <div style={{color:"var(--text-muted)",padding:48,textAlign:"center"}}>
          <i className="ti ti-loader-2" style={{fontSize:28,animation:"spin 1s linear infinite"}} aria-hidden/>
        </div>
      )}

      {!loading&&!sites.length&&!error&&(
        <div style={{padding:"48px 24px",textAlign:"center",color:"var(--text-muted)"}}>
          <i className="ti ti-database-off" style={{fontSize:40,marginBottom:12,display:"block"}} aria-hidden/>
          <p style={{margin:"0 0 16px",fontSize:14}}>No sites in the graph yet.</p>
          <button className="btn" onClick={()=>setAddOpen(true)}>
            <i className="ti ti-plus" aria-hidden/> Add your first site
          </button>
        </div>
      )}

      {/* new sites — prediction targets */}
      {newSites.length>0&&(
        <section style={{marginBottom:28}}>
          <div style={{fontSize:12,fontWeight:500,color:"var(--text-accent)",
            textTransform:"uppercase",letterSpacing:".06em",marginBottom:10}}>
            <i className="ti ti-sparkles" aria-hidden style={{marginRight:6}}/>
            New sites — awaiting prediction
          </div>
          <div style={{display:"flex",flexDirection:"column",gap:10}}>
            {newSites.map(s=>(
              <SiteCard key={s.site_id} site={s}
                onDelete={setDelSite} onZones={setZoneSite}
                onGoIngest={type=>onNavigate&&onNavigate("ingest",{siteType:type,siteId:s.site_id})}/>
            ))}
          </div>
        </section>
      )}

      {/* completed sites — training data */}
      {compSites.length>0&&(
        <section style={{marginBottom:28}}>
          <div style={{fontSize:12,fontWeight:500,color:"var(--text-muted)",
            textTransform:"uppercase",letterSpacing:".06em",marginBottom:10}}>
            <i className="ti ti-circle-check" aria-hidden style={{marginRight:6}}/>
            Completed sites — historical data
          </div>
          <div style={{display:"flex",flexDirection:"column",gap:10}}>
            {compSites.map(s=>(
              <SiteCard key={s.site_id} site={s}
                onDelete={setDelSite} onZones={setZoneSite}
                onGoIngest={()=>{}}/>
            ))}
          </div>
        </section>
      )}

      {/* sites without status */}
      {otherSites.length>0&&(
        <section style={{marginBottom:28}}>
          <div style={{fontSize:12,fontWeight:500,color:"var(--text-muted)",
            textTransform:"uppercase",letterSpacing:".06em",marginBottom:10}}>
            Other sites
          </div>
          <div style={{display:"flex",flexDirection:"column",gap:10}}>
            {otherSites.map(s=>(
              <SiteCard key={s.site_id} site={s}
                onDelete={setDelSite} onZones={setZoneSite}
                onGoIngest={()=>{}}/>
            ))}
          </div>
        </section>
      )}

      <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
    </div>
  );
}