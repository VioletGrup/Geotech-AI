
import { api, NODE_ENDPOINTS } from "../api.js";
import React, { useEffect, useState } from "react";

const FORMS = {
  pile: [["id", "text"], ["diameter", "num"], ["length", "num"], ["type", "text"]],
  cpt: [["id", "text"], ["depth", "num"], ["qc", "num"], ["fs", "num"]],
  soil: [["id", "text"], ["soil_type", "text"]],
  "load-test": [["id", "text"], ["pile_id", "text"], ["max_load", "num"]],
};
const ADDERS = {
  pile: api.addPile, cpt: api.addCpt, soil: api.addSoil, "load-test": api.addLoadTest,
};
const LINKS = {
  "pile-soil": [["pile_id", "text"], ["soil_id", "text"], api.linkPileSoil],
  "cpt-soil": [["cpt_id", "text"], ["soil_id", "text"], api.linkCptSoil],
};

function coerce(fields, values) {
  const out = {};
  for (const [name, kind] of fields) {
    out[name] = kind === "num" ? parseFloat(values[name]) : values[name];
  }
  return out;
}

export default function AddNodes() {
  const [tab, setTab] = useState("pile");
  const [mode, setMode] = useState("single");
  const [values, setValues] = useState({});
  const [bulk, setBulk] = useState("");
  const [msg, setMsg] = useState(null);
  const [busy, setBusy] = useState(false);

  const isLink = tab.includes("-soil");
  const fields = isLink ? LINKS[tab].slice(0, 2) : FORMS[tab];

  async function submitSingle() {
    setBusy(true); setMsg(null);
    try {
      const fn = isLink ? LINKS[tab][2] : ADDERS[tab];
      const res = await fn(coerce(fields, values));
      setMsg({ ok: true, text: res.message || "Created." });
      setValues({});
    } catch (e) {
      setMsg({ ok: false, text: e.message });
    } finally { setBusy(false); }
  }

  async function submitBulk() {
    setBusy(true); setMsg(null);
    let rows;
    try {
      rows = JSON.parse(bulk);
      if (!Array.isArray(rows)) throw new Error("Expected a JSON array.");
    } catch (e) {
      setMsg({ ok: false, text: `Parse error: ${e.message}` });
      setBusy(false); return;
    }
    const fn = NODE_ENDPOINTS[tab];
    let ok = 0; const errors = [];
    for (let i = 0; i < rows.length; i++) {
      try { await fn(coerce(FORMS[tab], rows[i])); ok++; }
      catch (e) { errors.push(`row ${i + 1}: ${e.message}`); }
    }
    setMsg({
      ok: errors.length === 0,
      text: `${ok}/${rows.length} created.` + (errors.length ? "\n" + errors.join("\n") : ""),
    });
    setBusy(false);
  }

  const placeholder = JSON.stringify(
    tab === "pile" ? [{ id: "P-001", diameter: 0.3, length: 6, type: "driven" }]
    : tab === "cpt" ? [{ id: "C-001", depth: 8, qc: 5000, fs: 60 }]
    : tab === "soil" ? [{ id: "S-001", soil_type: "clay" }]
    : [{ id: "LT-001", pile_id: "P-001", max_load: 220 }], null, 2
  );

  return (
    <>
      <div className="tabs">
        {["pile", "cpt", "soil", "load-test", "pile-soil", "cpt-soil"].map((t) => (
          <button key={t} className={t === tab ? "active" : ""}
            onClick={() => { setTab(t); setValues({}); setMsg(null); if (t.includes("-soil")) setMode("single"); }}>
            {t}
          </button>
        ))}
      </div>
      {!isLink && (
        <div className="tabs">
          <button className={mode === "single" ? "active" : ""} onClick={() => setMode("single")}>one</button>
          <button className={mode === "bulk" ? "active" : ""} onClick={() => setMode("bulk")}>many</button>
        </div>
      )}
      <div className="panel">
        {mode === "single" || isLink ? (
          <>
            <h3>{isLink ? `link ${tab}` : `new ${tab}`}</h3>
            <div className="grid">
              {fields.map(([name, kind]) => (
                <div key={name} className={kind === "num" ? "numeric" : ""}>
                  <label>{name}</label>
                  <input type={kind === "num" ? "number" : "text"} step="any"
                    value={values[name] ?? ""}
                    onChange={(e) => setValues({ ...values, [name]: e.target.value })} />
                </div>
              ))}
            </div>
            <div className="row">
              <button className="btn" disabled={busy} onClick={submitSingle}>
                {busy ? "Saving…" : isLink ? "Create link" : "Create"}
              </button>
            </div>
          </>
        ) : (
          <>
            <h3>bulk {tab} — paste JSON array</h3>
            <textarea value={bulk} onChange={(e) => setBulk(e.target.value)} placeholder={placeholder} />
            <div className="row">
              <button className="btn" disabled={busy || !bulk.trim()} onClick={submitBulk}>
                {busy ? "Importing…" : "Import all"}
              </button>
              <button className="btn ghost" onClick={() => setBulk(placeholder)}>Insert example</button>
            </div>
          </>
        )}
        {msg && <div className={`note ${msg.ok ? "ok" : "err"}`}>{msg.text}</div>}
      </div>
    </>
  );
}