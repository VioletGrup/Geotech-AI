import React, { useRef, useEffect, useState } from "react";
import { api } from "../api.js";

const EXAMPLES = [
  "Is zone ZONE-1.1 pre-drill or driven, and what's in it?",
  "Which pile tests failed in zone ZONE-13.1?",
  "Show DPSH probes that refused at 0.5 m or shallower.",
  "What's the ground profile at borehole BH02?",
  "Which piles fell short of their target embedment?",
];

export default function Copilot() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const streamRef = useRef(null);

  useEffect(() => {
    streamRef.current?.scrollTo({ top: streamRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, busy]);

  async function send(text) {
    const q = (text ?? input).trim();
    if (!q || busy) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", text: q }]);
    setBusy(true);
    try {
      const res = await api.chat(q);
      setMessages((m) => [...m, { role: "bot", text: res.reply }]);
    } catch (e) {
      setMessages((m) => [...m, { role: "bot", text: `⚠ ${e.message}`, err: true }]);
    } finally { setBusy(false); }
  }

  function onKey(e) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
  }

  return (
    <div className="chat">
      <div className="stream" ref={streamRef}>
        {messages.length === 0 ? (
          <div className="empty">
            <p>Ask the advisor about pile drilling, pile refusal, test pass/fail, DPSH refusal depths, or ground profiles.</p>
            <div className="examples">
              {EXAMPLES.map((ex) => <button key={ex} onClick={() => send(ex)}>{ex}</button>)}
            </div>
          </div>
        ) : (
          messages.map((m, i) => (
            <div key={i} className={`msg ${m.role}`}>{m.text}</div>
          ))
        )}
        {busy && <div className="msg bot thinking">Consulting the graph…</div>}
      </div>
      <div className="composer">
        <textarea value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={onKey}
          placeholder="Ask about a pile, soil profile, or expected capacity… (Enter to send)" />
        <button className="btn" disabled={busy || !input.trim()} onClick={() => send()}>Send</button>
      </div>
    </div>
  );
}