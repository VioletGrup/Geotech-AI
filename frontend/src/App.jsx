import { useEffect, useState } from "react";
import { api } from "./api.js";
import AddNodes from "./components/AddNodes.jsx";
import BrowseCases from "./components/BrowseCases.jsx";
import Copilot from "./components/Copilot.jsx";

const VIEWS = [
  { id: "add", label: "Add data", el: AddNodes, blurb: "Create piles, CPT tests, soil layers and load tests — singly or in bulk." },
  { id: "browse", label: "Browse cases", el: BrowseCases, blurb: "Logged pile load tests from previous projects." },
  { id: "copilot", label: "Copilot", el: Copilot, blurb: "Ask the graph-backed advisor to predict capacity or find analog cases." },
];

export default function App() {
  const [view, setView] = useState("add");
  const [status, setStatus] = useState("wait");
  const [base, setBase] = useState("");

  useEffect(() => {
    api.health()
      .then(async () => { setStatus("ok"); setBase(await api.base()); })
      .catch(async () => { setStatus("down"); setBase(await api.base()); });
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