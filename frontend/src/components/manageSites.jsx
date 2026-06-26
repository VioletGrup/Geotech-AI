import React, { useState, useEffect, useCallback } from "react";
import { api } from "../api.js";

function StatPill({ label, value, color = "accent" }) {
  if (!value) return null;
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 4,
      padding: "2px 8px", borderRadius: 10, fontSize: 12,
      background: `var(--bg-${color})`, color: `var(--text-${color})`,
      border: `1px solid var(--border-${color})`,
    }}>
      {label}: <strong>{value}</strong>
    </span>
  );
}

function ConfirmDialog({ site, onConfirm, onCancel, busy }) {
  const [typed, setTyped] = useState("");
  const match = typed === site.site_id;
  return (
    // faux-modal: full-height overlay div so it doesn't use position:fixed
    <div style={{
      position: "absolute", inset: 0, zIndex: 100,
      background: "rgba(0,0,0,0.55)",
      display: "flex", alignItems: "center", justifyContent: "center",
      padding: 24,
    }}>
      <div style={{
        background: "var(--surface-2)", borderRadius: 14,
        padding: "28px 28px 24px", maxWidth: 440, width: "100%",
        border: "1px solid var(--border-danger)", boxShadow: "0 8px 32px rgba(0,0,0,.3)",
      }}>
        <div style={{ display: "flex", alignItems: "flex-start", gap: 12, marginBottom: 16 }}>
          <i className="ti ti-alert-triangle"
            style={{ fontSize: 28, color: "var(--text-danger)", flexShrink: 0 }} aria-hidden />
          <div>
            <p style={{ margin: "0 0 6px", fontWeight: 500, fontSize: 16 }}>
              Delete {site.name || site.site_id}?
            </p>
            <p style={{ margin: 0, fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.6 }}>
              This will permanently delete the site and all data that belongs exclusively to it —
              zones, pile tests, boreholes, test pits, DPSH probes, lab tests and ground models.
              <br /><br />
              <strong style={{ color: "var(--text-primary)" }}>
                SoilType nodes and any ground models shared with other sites will be preserved.
              </strong>
              <br /><br />
              <span style={{ color: "var(--text-danger)", fontWeight: 500 }}>
                This cannot be undone.
              </span>
            </p>
          </div>
        </div>

        <div style={{ marginBottom: 20 }}>
          <div style={{
            display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 12,
            padding: "8px 12px", background: "var(--bg-danger)",
            borderRadius: 8, fontSize: 12,
          }}>
            <StatPill label="zones" value={site.zones} color="danger" />
            <StatPill label="piles" value={site.pile_locations} color="danger" />
            <StatPill label="DPSH" value={site.dpsh_probes} color="danger" />
            <StatPill label="boreholes" value={site.boreholes} color="danger" />
            <StatPill label="test pits" value={site.test_pits} color="danger" />
          </div>

          <label style={{ fontSize: 13, color: "var(--text-secondary)", display: "block", marginBottom: 6 }}>
            Type <strong style={{ color: "var(--text-primary)" }}>{site.site_id}</strong> to confirm:
          </label>
          <input
            autoFocus
            value={typed}
            onChange={e => setTyped(e.target.value)}
            onKeyDown={e => e.key === "Enter" && match && !busy && onConfirm()}
            style={{
              width: "100%", padding: "8px 12px", borderRadius: 8, fontSize: 13,
              border: `1px solid ${match ? "var(--border-danger)" : "var(--border-strong)"}`,
              background: "var(--surface-1)", color: "var(--text-primary)",
              outline: match ? "2px solid var(--border-danger)" : "none",
              boxSizing: "border-box",
            }}
            placeholder={site.site_id}
          />
        </div>

        <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
          <button className="btn ghost" onClick={onCancel} disabled={busy}>
            Cancel
          </button>
          <button
            disabled={!match || busy}
            onClick={onConfirm}
            style={{
              padding: "8px 20px", borderRadius: 8, border: "none", cursor: match ? "pointer" : "not-allowed",
              background: match ? "var(--text-danger)" : "var(--border-strong)",
              color: "#fff", fontWeight: 500, fontSize: 13,
              opacity: busy ? 0.7 : 1,
            }}
          >
            {busy
              ? <><i className="ti ti-loader-2" style={{ animation: "spin 1s linear infinite" }} aria-hidden /> Deleting…</>
              : <><i className="ti ti-trash" aria-hidden /> Delete permanently</>}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function ManageSites() {
  const [sites,   setSites]   = useState([]);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);
  const [confirm, setConfirm] = useState(null);   // site object being confirmed
  const [busy,    setBusy]    = useState(false);
  const [done,    setDone]    = useState(null);   // {site_id, deleted}

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const rows = await api.listSites();
      setSites(Array.isArray(rows) ? rows : []);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function handleDelete() {
    if (!confirm) return;
    setBusy(true);
    try {
      const result = await api.deleteSite(confirm.site_id);
      setDone({ site_id: confirm.site_id, deleted: result.deleted });
      setConfirm(null);
      await load();
    } catch (e) { setError(e.message); setConfirm(null); }
    finally { setBusy(false); }
  }

  const total = {
    zones: sites.reduce((a, s) => a + (s.zones || 0), 0),
    pile_locations: sites.reduce((a, s) => a + (s.pile_locations || 0), 0),
    dpsh_probes: sites.reduce((a, s) => a + (s.dpsh_probes || 0), 0),
  };

  return (
    // position:relative so the confirm overlay anchors to this container
    <div style={{ maxWidth: 760, margin: "0 auto", position: "relative" }}>

      {confirm && (
        <ConfirmDialog
          site={confirm}
          busy={busy}
          onConfirm={handleDelete}
          onCancel={() => setConfirm(null)}
        />
      )}

      {/* done banner */}
      {done && (
        <div style={{
          display: "flex", alignItems: "center", gap: 10, marginBottom: 20,
          padding: "12px 16px", background: "var(--bg-success)",
          border: "1px solid var(--border-success)", borderRadius: 10,
          color: "var(--text-success)",
        }}>
          <i className="ti ti-circle-check" aria-hidden />
          <span style={{ flex: 1, fontSize: 13 }}>
            <strong>{done.site_id}</strong> deleted — {
              Object.entries(done.deleted)
                .filter(([,v]) => v > 0)
                .map(([k, v]) => `${v} ${k}`)
                .join(", ")
            } removed.
          </span>
          <button onClick={() => setDone(null)} style={{ background: "none", border: "none", cursor: "pointer", color: "inherit" }}>
            <i className="ti ti-x" aria-hidden />
          </button>
        </div>
      )}

      {/* header row */}
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 20 }}>
        <h3 style={{ margin: 0, flex: 1 }}>Sites in graph</h3>
        <button className="btn ghost" onClick={load} disabled={loading}>
          <i className={`ti ti-refresh${loading ? " ti-spin" : ""}`} aria-hidden /> Refresh
        </button>
      </div>

      {/* summary */}
      {sites.length > 0 && (
        <div style={{
          display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 20,
          padding: "10px 14px", background: "var(--surface-1)",
          border: "1px solid var(--border)", borderRadius: 10,
        }}>
          <StatPill label="sites" value={sites.length} />
          <StatPill label="zones" value={total.zones} />
          <StatPill label="pile locations" value={total.pile_locations} />
          <StatPill label="DPSH probes" value={total.dpsh_probes} />
        </div>
      )}

      {error && (
        <div style={{ padding: "10px 14px", background: "var(--bg-danger)",
          border: "1px solid var(--border-danger)", borderRadius: 8,
          color: "var(--text-danger)", fontSize: 13, marginBottom: 16 }}>
          <i className="ti ti-alert-circle" aria-hidden /> {error}
        </div>
      )}

      {loading && !sites.length && (
        <div style={{ color: "var(--text-muted)", padding: 32, textAlign: "center" }}>
          <i className="ti ti-loader-2" style={{ animation: "spin 1s linear infinite", fontSize: 24 }} aria-hidden />
        </div>
      )}

      {!loading && sites.length === 0 && !error && (
        <div style={{ color: "var(--text-muted)", padding: 32, textAlign: "center", fontSize: 14 }}>
          No sites in the graph yet. Upload a project to get started.
        </div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {sites.map(site => (
          <div key={site.site_id} style={{
            border: "1px solid var(--border)", borderRadius: 12,
            padding: "16px 18px",
            background: "var(--surface-1)",
          }}>
            <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
              <div style={{ flex: 1 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                  <span style={{ fontWeight: 500, fontSize: 15 }}>{site.name || site.site_id}</span>
                  <code style={{
                    fontSize: 11, padding: "1px 6px", borderRadius: 4,
                    background: "var(--surface-0)", color: "var(--text-muted)",
                    border: "1px solid var(--border)",
                  }}>{site.site_id}</code>
                </div>
                <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                  <StatPill label="zones" value={site.zones} />
                  <StatPill label="pile locations" value={site.pile_locations} />
                  <StatPill label="DPSH" value={site.dpsh_probes} />
                  <StatPill label="boreholes" value={site.boreholes} />
                  <StatPill label="test pits" value={site.test_pits} />
                </div>
              </div>

              <button
                onClick={() => { setDone(null); setConfirm(site); }}
                title="Remove this site and all its data"
                style={{
                  padding: "7px 14px", borderRadius: 8, border: "1px solid var(--border-danger)",
                  background: "transparent", color: "var(--text-danger)",
                  cursor: "pointer", fontSize: 13, display: "flex", alignItems: "center", gap: 6,
                  flexShrink: 0,
                }}
              >
                <i className="ti ti-trash" aria-hidden /> Remove
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}