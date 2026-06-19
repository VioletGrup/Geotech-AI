import { api } from "../api.js";
import React, { useState } from "react";

// Schema v3 — one field spec per node type. Each field: [name, kind, opts?]
//   kind: "text" | "num" | "int" | "bool" | "select"
//   opts.fk: true  -> foreign key (builds a relationship; shown with a link hint)
//   opts.req: true -> required
//   opts.choices  -> for select
const SCHEMA = {
  site: [
    ["id", "text", { req: true }], ["name", "text"], ["address", "text"],
    ["coordinate_system", "text"],
  ],
  zone: [
    ["id", "text", { req: true }], ["site_id", "text", { fk: true }], ["name", "text"],
    ["pre_drill_decision", "select", { choices: ["", "Pre-Drill", "Driven"] }],
    ["trackers_4string", "int"], ["trackers_3string", "int"], ["trackers_2string", "int"],
  ],
  "pile-test-location": [
    ["id", "text", { req: true }], ["zone_id", "text", { fk: true }],
    ["driving_type", "select", { choices: ["", "Driven", "PreDrilled"] }],
    ["easting", "num"], ["northing", "num"], ["reduced_level", "num"],
    ["designer", "text"], ["section_type", "text"],
    ["target_depth", "num"], ["achieved_embedment", "num"],
    ["drive_time", "num"], ["driving_rate", "num"],
  ],
  "pile-test": [
    ["id", "text", { req: true }], ["pile_location_id", "text", { fk: true }],
    ["section_type", "text"], ["passed", "bool"],
  ],
  "tension-test": [
    ["id", "text", { req: true }], ["pile_test_id", "text", { fk: true, req: true }],
    ["uplift_applied_force", "num"], ["uplift_max_deflection", "num"],
    ["max_load_proportion_ed", "num"],
  ],
  "lateral-test": [
    ["id", "text", { req: true }], ["pile_test_id", "text", { fk: true, req: true }],
    ["max_applied_force", "num"], ["max_deflection_top", "num"],
    ["load_max", "num"], ["max_load_proportion_ed", "num"],
  ],
  "compression-test": [
    ["id", "text", { req: true }], ["pile_test_id", "text", { fk: true, req: true }],
    ["max_applied_force", "num"], ["max_deflection", "num"],
    ["max_load_proportion_ed", "num"],
  ],
  dpsh: [
    ["id", "text", { req: true }], ["zone_id", "text", { fk: true }],
    ["easting", "num"], ["northing", "num"], ["refusal_depth", "num"],
  ],
  borehole: [
    ["id", "text", { req: true }], ["zone_id", "text", { fk: true }],
    ["series", "text"], ["elevation", "num"], ["total_depth", "num"], ["groundwater_depth", "num"],
  ],
  testpit: [
    ["id", "text", { req: true }], ["zone_id", "text", { fk: true }],
    ["elevation", "num"], ["total_depth", "num"],
  ],
  "soil-type": [
    ["unit_name", "text", { req: true }], ["description", "text"],
  ],
  "ground-model": [
    ["id", "text", { req: true }], ["location_id", "text", { fk: true }],
  ],
  "ground-layer": [
    ["id", "text", { req: true }], ["ground_model_id", "text", { fk: true, req: true }],
    ["soil_unit_name", "text", { fk: true }], ["order", "int"],
    ["start_depth", "num"], ["end_depth", "num"],
    ["condition", "select", { choices: ["", "Firm", "Stiff", "VeryStiff", "Hard", "Dense", "VeryDense"] }],
  ],
  "thermal-test": [
    ["id", "text", { req: true }], ["testpit_id", "text", { fk: true, req: true }],
    ["depth", "num"], ["thermal_reading", "num"], ["r_value", "num"],
  ],
  "lab-test": [
    ["id", "text", { req: true }], ["location_id", "text", { fk: true, req: true }],
    ["soil_unit_name", "text", { fk: true }],
    ["top_depth", "num"], ["bottom_depth", "num"], ["moisture_content", "num"],
    ["liquid_limit", "num"], ["plastic_limit", "num"], ["plasticity_index", "num"],
    ["linear_shrinkage", "num"], ["emerson_class", "int"], ["iss", "num"],
    ["gravel", "num"], ["sand", "num"], ["fines", "num"],
    ["compaction_mdd", "num"], ["compaction_omc", "num"],
    ["cbr_4day_2_5mm", "int"], ["cbr_swell", "num"],
  ],
  aggressivity: [
    ["id", "text", { req: true }], ["location_id", "text", { fk: true, req: true }],
    ["depth", "num"], ["ph", "num"], ["sulfate", "num"], ["chlorides", "num"],
    ["resistivity", "num"], ["exposure_class_concrete", "text"], ["exposure_class_steel", "text"],
  ],
};

const TABS = Object.keys(SCHEMA);

function coerce(fields, values) {
  const out = {};
  for (const [name, kind] of fields) {
    const raw = values[name];
    if (raw === undefined || raw === "" || raw === null) continue;
    if (kind === "num") out[name] = parseFloat(raw);
    else if (kind === "int") out[name] = parseInt(raw, 10);
    else if (kind === "bool") out[name] = raw === true || raw === "true";
    else out[name] = raw;
  }
  return out;
}

export default function AddNodes() {
  const [tab, setTab] = useState("site");
  const [mode, setMode] = useState("single");
  const [values, setValues] = useState({});
  const [bulk, setBulk] = useState("");
  const [msg, setMsg] = useState(null);
  const [busy, setBusy] = useState(false);

  const fields = SCHEMA[tab];

  async function submitSingle() {
    setBusy(true); setMsg(null);
    try {
      const res = await api.addNode(tab, coerce(fields, values));
      setMsg({ ok: true, text: res.message || "Saved." });
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
    try {
      const res = await api.bulkNodes(tab, rows.map((r) => coerce(fields, r)));
      setMsg({
        ok: res.errors.length === 0,
        text: `${res.saved}/${res.total} saved.` + (res.errors.length ? "\n" + res.errors.join("\n") : ""),
      });
    } catch (e) {
      setMsg({ ok: false, text: e.message });
    } finally { setBusy(false); }
  }

  function example() {
    const obj = {};
    for (const [name, kind, opts] of fields) {
      if (opts?.req || opts?.fk) {
        obj[name] = kind === "num" || kind === "int" ? 0 : `<${name}>`;
      }
    }
    return JSON.stringify([obj], null, 2);
  }

  return (
    <>
      <div className="tabs">
        {TABS.map((t) => (
          <button key={t} className={t === tab ? "active" : ""}
            onClick={() => { setTab(t); setValues({}); setBulk(""); setMsg(null); }}>
            {t}
          </button>
        ))}
      </div>

      <div className="tabs">
        <button className={mode === "single" ? "active" : ""} onClick={() => setMode("single")}>one</button>
        <button className={mode === "bulk" ? "active" : ""} onClick={() => setMode("bulk")}>many</button>
      </div>

      <div className="panel">
        {mode === "single" ? (
          <>
            <h3>new {tab}</h3>
            <div className="grid">
              {fields.map(([name, kind, opts]) => (
                <div key={name} className={kind === "num" || kind === "int" ? "numeric" : ""}>
                  <label>
                    {name}
                    {opts?.req ? " *" : ""}
                    {opts?.fk ? " \u2192" : ""}
                  </label>
                  {kind === "select" ? (
                    <select value={values[name] ?? ""}
                      onChange={(e) => setValues({ ...values, [name]: e.target.value })}>
                      {opts.choices.map((c) => <option key={c} value={c}>{c || "—"}</option>)}
                    </select>
                  ) : kind === "bool" ? (
                    <select value={values[name] ?? ""}
                      onChange={(e) => setValues({ ...values, [name]: e.target.value })}>
                      <option value="">—</option>
                      <option value="true">true</option>
                      <option value="false">false</option>
                    </select>
                  ) : (
                    <input type={kind === "num" || kind === "int" ? "number" : "text"} step="any"
                      value={values[name] ?? ""}
                      onChange={(e) => setValues({ ...values, [name]: e.target.value })} />
                  )}
                </div>
              ))}
            </div>
            <div className="row">
              <button className="btn" disabled={busy} onClick={submitSingle}>
                {busy ? "Saving…" : "Create"}
              </button>
            </div>
            <p className="hint">* required &nbsp; \u2192 links to another node</p>
          </>
        ) : (
          <>
            <h3>bulk {tab} — paste JSON array</h3>
            <textarea value={bulk} onChange={(e) => setBulk(e.target.value)} placeholder={example()} />
            <div className="row">
              <button className="btn" disabled={busy || !bulk.trim()} onClick={submitBulk}>
                {busy ? "Importing…" : "Import all"}
              </button>
              <button className="btn ghost" onClick={() => setBulk(example())}>Insert example</button>
            </div>
          </>
        )}
        {msg && <div className={`note ${msg.ok ? "ok" : "err"}`}>{msg.text}</div>}
      </div>
    </>
  );
}