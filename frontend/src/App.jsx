import React, { useEffect, useState } from "react";
import Copilot from "./components/Copilot.jsx";
import ManageSites from "./components/manageSites.jsx";
import Ingest from "./components/ingest.jsx";

export default function App() {
  const [view,         setView]         = useState("manage");
  const [ingestProps,  setIngestProps]  = useState({});   // {siteId, siteType}
  const [chatMessages, setChatMessages] = useState([]);
  const [status,       setStatus]       = useState("wait");
  const [base,         setBase]         = useState("");

  useEffect(() => {
    import("./api.js").then(({ api }) => {
      api.health()
        .then(async () => { setStatus("ok");   setBase(await api.base()); })
        .catch(async () => { setStatus("down"); setBase(await api.base()); });
    });
  }, []);

  function goIngest(siteId, siteType) {
    setIngestProps({ siteId, siteType });
    setView("ingest");
  }

  const NAV = [
    { id: "manage",  label: "Sites" },
    { id: "copilot", label: "Copilot" },
  ];

  const BLURBS = {
    manage:  "Manage project sites and zone pre-drill / driven decisions.",
    copilot: "Ask the graph-backed advisor about pre-drill decisions, refusal, test results and ground profiles.",
  };

  return (
    <div className="layout">
      <aside className="rail">
        <div className="brand">
          <h1>Geotech AI</h1>
          <div className="sub">solar pile · graph advisor</div>
        </div>
        <nav className="nav">
          {NAV.map((v, i) => (
            <button key={v.id} className={v.id === view ? "active" : ""}
              onClick={() => setView(v.id)}>
              <span className="idx">{String(i + 1).padStart(2, "0")}</span>
              {v.label}
            </button>
          ))}
        </nav>
        <div className="status">
          <span className={`dot ${status}`} />
          {status === "ok" ? "api connected"
            : status === "down" ? "api unreachable"
            : "checking…"}
          {base && <div style={{ marginTop: 4, opacity: 0.7 }}>{base.replace("http://", "")}</div>}
        </div>
      </aside>

      <main className="content">
        <div className="head">
          <h2>{view === "ingest" ? "Upload data" : NAV.find(v => v.id === view)?.label}</h2>
          <p>{BLURBS[view]}</p>
        </div>

        {view === "manage"  && <ManageSites onGoIngest={goIngest} />}
        {view === "ingest"  && <Ingest {...ingestProps} onBack={() => setView("manage")} />}
        {view === "copilot" && <Copilot messages={chatMessages} setMessages={setChatMessages} />}
      </main>
    </div>
  );
}