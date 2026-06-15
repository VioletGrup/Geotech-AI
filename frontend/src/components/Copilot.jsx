import { useRef, useState, useEffect } from "react";
import { api } from "../api.js";

const EXAMPLES = [
  "Predict capacity for a 0.3 m × 6 m driven pile in clay, qc 5000.",
  "Find logged cases in sand with qc around 8000.",
  "What's the expected load for a 0.4 m × 8 m pile, and which past cases support it?",
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
            <p>Ask the advisor to predict pile capacity or surface analog cases.</p>
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