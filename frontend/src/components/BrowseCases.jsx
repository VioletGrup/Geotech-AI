import React, { useEffect, useState } from "react";
import { api } from "../api.js";

const COLS = [
  ["pile_id", "pile"], ["pile_type", "type"], ["diameter", "dia (m)"],
  ["length", "len (m)"], ["qc", "qc (kPa)"], ["soil_type", "soil"], ["max_load", "load (kN)"],
];
const NUMERIC = new Set(["diameter", "length", "qc", "max_load"]);

export default function BrowseCases() {
  const [rows, setRows] = useState([]);
  const [qc, setQc] = useState("");
  const [soil, setSoil] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);

  async function loadAll() {
    setBusy(true); setErr(null);
    try { const r = await api.listCases(200); setRows(r.results || []); }
    catch (e) { setErr(e.message); }
    finally { setBusy(false); }
  }

  async function filter() {
    if (!qc && !soil) return loadAll();
    setBusy(true); setErr(null);
    try { const r = await api.query({ qc, soil_type: soil }); setRows(r.results || []); }
    catch (e) { setErr(e.message); }
    finally { setBusy(false); }
  }

  useEffect(() => { loadAll(); }, []);

  return (
    <>
      <div className="panel">
        <h3>filter</h3>
        <div className="grid">
          <div className="numeric">
            <label>qc near (kPa) — ±2000 band</label>
            <input type="number" step="any" value={qc} onChange={(e) => setQc(e.target.value)} placeholder="e.g. 5000" />
          </div>
          <div>
            <label>soil type</label>
            <input value={soil} onChange={(e) => setSoil(e.target.value)} placeholder="e.g. clay" />
          </div>
        </div>
        <div className="row">
          <button className="btn" disabled={busy} onClick={filter}>{busy ? "Loading…" : "Apply filter"}</button>
          <button className="btn ghost" disabled={busy} onClick={() => { setQc(""); setSoil(""); loadAll(); }}>Show all</button>
          <span style={{ color: "var(--muted)", fontSize: 12, fontFamily: "var(--mono)" }}>{rows.length} cases</span>
        </div>
        {err && <div className="note err">{err}</div>}
      </div>
      <div className="panel">
        {rows.length === 0 && !busy ? (
          <p style={{ color: "var(--muted)", margin: 0 }}>No cases yet. Add piles with load tests under "Add data".</p>
        ) : (
          <table>
            <thead>
              <tr>{COLS.map(([k, h]) => <th key={k} style={NUMERIC.has(k) ? { textAlign: "right" } : null}>{h}</th>)}</tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={r.pile_id ?? i}>
                  {COLS.map(([k]) => {
                    const v = r[k];
                    if (k === "soil_type") return <td key={k}>{v ? <span className="tag">{v}</span> : "—"}</td>;
                    if (NUMERIC.has(k)) return <td key={k} className="num">{v == null ? "—" : Number(v).toLocaleString()}</td>;
                    return <td key={k}>{v ?? "—"}</td>;
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}