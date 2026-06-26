import React, { useEffect, useState } from "react";
import AddNodes from "./components/AddNodes.jsx";
import Copilot from "./components/Copilot.jsx";
import ManageSites from "./components/manageSites.jsx";
import Ingest from "./components/ingest.jsx";

const VIEWS = [
  { id: "ingest", label: "New site", el: Ingest, blurb: "Upload PDFs → extract data → review → import to graph." },
  { id: "manage", label: "Manage sites", el: ManageSites, blurb: "View sites in the graph and permanently remove projects and their data." },
  { id: "copilot", label: "Copilot", el: Copilot, blurb: "Ask the graph-backed advisor about pre-drill decisions, refusal, test results and ground profiles." },
];

export default function App() {
  const [view, setView] = useState("manage");
  const [status, setStatus] = useState("wait");
  const [base, setBase] = useState("");

  useEffect(() => {
    import("./api.js").then(({ api }) => {
      api.health()
        .then(async () => { setStatus("ok"); setBase(await api.base()); })
        .catch(async () => { setStatus("down"); setBase(await api.base()); });
    });
  }, []);

  const active = VIEWS.find((v) => v.id === view);
  const View = active.el;

  return (
    <div className="layout">
      <aside className="rail">
        <div className="brand">
          <h1>Geotech AI</h1>
          <div className="sub">solar pile · graph advisor</div>
        </div>
        <nav className="nav">
          {VIEWS.map((v, i) => (
            <button key={v.id} className={v.id === view ? "active" : ""} onClick={() => setView(v.id)}>
              <span className="idx">{String(i + 1).padStart(2, "0")}</span>
              {v.label}
            </button>
          ))}
        </nav>
        <div className="status">
          <span className={`dot ${status}`} />
          {status === "ok" ? "api connected" : status === "down" ? "api unreachable" : "checking…"}
          {base && <div style={{ marginTop: 4, opacity: 0.7 }}>{base.replace("http://", "")}</div>}
        </div>
      </aside>
      <main className="content">
        <div className="head">
          <h2>{active.label}</h2>
          <p>{active.blurb}</p>
        </div>
        <View />
      </main>
    </div>
  );
}