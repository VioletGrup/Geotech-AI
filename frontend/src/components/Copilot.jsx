import React, { useRef, useEffect, useState } from "react";
import { api } from "../api.js";

// ── confidence bar ────────────────────────────────────────────────────────────
function ConfidenceBar({ value }) {
  if (value == null) return null;
  const color = value >= 80 ? "#1D9E75"
              : value >= 50 ? "#f2c300"
              :               "#f87171";
  const label = value >= 80 ? "High" : value >= 50 ? "Medium" : "Low";
  return (
    <div style={{ marginTop: 8, display: "flex", alignItems: "center", gap: 8 }}>
      <div style={{ flex: 1, height: 4, background: "rgba(255,255,255,0.1)", borderRadius: 2, overflow: "hidden" }}>
        <div style={{
          height: "100%", width: `${value}%`, borderRadius: 2,
          background: color, transition: "width .6s ease",
        }}/>
      </div>
      <span style={{ fontSize: 11, color, minWidth: 64, fontWeight: 500 }}>
        {label} ({value}%)
      </span>
    </div>
  );
}

// ── reasoning toggle ──────────────────────────────────────────────────────────
function ReasoningToggle({ text }) {
  const [open, setOpen] = useState(false);
  if (!text) return null;

  // Split into level 1 (summary sentence) and level 2 (detail block)
  const parts = text.split("\n\n");
  const summary = parts[0] || "";
  const detail  = parts.slice(1).join("\n\n").trim();

  // Colour based on confidence % in the text
  const scoreMatch = text.match(/(\d+)%/);
  const score = scoreMatch ? parseInt(scoreMatch[1]) : null;
  const scoreColor = !score  ? "rgba(255,255,255,0.5)"
                   : score >= 90 ? "#34d399"
                   : score >= 75 ? "#86efac"
                   : score >= 60 ? "#fbbf24"
                   :               "#f87171";

  return (
    <div style={{ marginTop: 8 }}>
      {/* Level 1 — always visible summary */}
      <div style={{
        fontSize: 12, color: "rgba(255,255,255,0.6)",
        lineHeight: 1.6, marginBottom: 6,
        paddingLeft: 10,
        borderLeft: `2px solid ${scoreColor}`,
      }}>
        {summary}
      </div>

      {/* Level 2 — detailed breakdown, collapsible */}
      {detail && (
        <>
          <button
            onClick={() => setOpen(o => !o)}
            style={{
              background: "none", border: "none", cursor: "pointer", padding: 0,
              display: "flex", alignItems: "center", gap: 5,
              color: "rgba(255,255,255,0.35)", fontSize: 11,
            }}
          >
            <span style={{
              display: "inline-block", transition: "transform .2s",
              transform: open ? "rotate(180deg)" : "rotate(0deg)", lineHeight: 1,
            }}>▾</span>
            {open ? "Hide scoring detail" : "Show scoring detail"}
          </button>

          {open && (
            <div style={{
              marginTop: 6, padding: "10px 12px",
              background: "rgba(0,0,0,0.3)", borderRadius: 8,
              borderLeft: "2px solid rgba(242,195,0,0.2)",
            }}>
              {detail.split("\n").map((line, i) => {
                const isBullet  = line.startsWith("•");
                const isHeader  = line.startsWith("Confidence:") ||
                                  line.startsWith("Tools called") ||
                                  line.startsWith("Data returned") ||
                                  line.startsWith("Scoring breakdown");
                const isEmpty   = line.trim() === "";
                return (
                  <div key={i} style={{
                    fontSize: 11,
                    color: isHeader  ? "rgba(255,255,255,0.8)"
                         : isBullet ? "rgba(255,255,255,0.6)"
                         :             "rgba(255,255,255,0.45)",
                    fontWeight: isHeader ? 500 : 400,
                    marginBottom: isEmpty ? 4 : 1,
                    paddingLeft: isBullet ? 4 : 0,
                    lineHeight: 1.7,
                  }}>
                    {isEmpty ? " " : line}
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ── message bubble ────────────────────────────────────────────────────────────
function Bubble({ m }) {
  const isUser = m.role === "user";
  if (isUser) {
    return (
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 6 }}>
        <div style={{
          maxWidth: "72%", padding: "10px 14px",
          borderRadius: "18px 18px 4px 18px",
          background: "var(--pcl-gold)", color: "#050608",
          fontSize: 13, lineHeight: 1.6, wordBreak: "break-word",
        }}>
          {m.text}
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", justifyContent: "flex-start", marginBottom: 6 }}>
      <div style={{
        maxWidth: "76%", padding: "10px 14px",
        borderRadius: "18px 18px 18px 4px",
        background: m.err ? "var(--bg-danger)" : "var(--surface-2)",
        border: `1px solid ${m.err ? "var(--border-danger)" : "var(--border-strong)"}`,
        fontSize: 13, lineHeight: 1.6, color: m.err ? "var(--text-danger)" : "var(--text-primary)",
        wordBreak: "break-word",
      }}>
        <div style={{ whiteSpace: "pre-wrap" }}>{m.text}</div>
        {!m.err && (
          <>
            <ConfidenceBar value={m.confidence} />
            <ReasoningToggle text={m.reasoning} />
          </>
        )}
      </div>
    </div>
  );
}

// ── typing indicator ──────────────────────────────────────────────────────────
function Typing() {
  return (
    <div style={{ display: "flex", justifyContent: "flex-start", marginBottom: 6 }}>
      <div style={{
        padding: "10px 16px", borderRadius: "18px 18px 18px 4px",
        background: "var(--surface-2)", border: "1px solid var(--border-strong)",
        display: "flex", gap: 5, alignItems: "center",
      }}>
        {[0, 1, 2].map(i => (
          <span key={i} style={{
            width: 6, height: 6, borderRadius: "50%",
            background: "var(--text-muted)", display: "inline-block",
            animation: `bounce 1.2s ease-in-out ${i * 0.2}s infinite`,
          }}/>
        ))}
      </div>
    </div>
  );
}

// ── main ──────────────────────────────────────────────────────────────────────
export default function Copilot() {
  const [messages, setMessages] = useState([]);
  const [input,    setInput]    = useState("");
  const [busy,     setBusy]     = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  async function send(text) {
    const q = (text ?? input).trim();
    if (!q || busy) return;
    setInput("");
    setMessages(m => [...m, { role: "user", text: q }]);
    setBusy(true);
    try {
      const res = await api.chat(q);
      setMessages(m => [...m, {
        role:       "bot",
        text:       res.reply,
        confidence: res.confidence,
        reasoning:  res.reasoning,
      }]);
    } catch(e) {
      setMessages(m => [...m, { role: "bot", text: `Error: ${e.message}`, err: true }]);
    } finally { setBusy(false); }
  }

  function onKey(e) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "calc(100vh - 120px)" }}>

      {/* message list */}
      <div style={{
        flex: 1, overflowY: "auto", padding: "16px 20px",
        display: "flex", flexDirection: "column",
      }}>
        {messages.length === 0 && (
          <div style={{ margin: "auto", textAlign: "center", color: "var(--text-muted)", fontSize: 13 }}>
            <div style={{ fontSize: 32, marginBottom: 12 }}>⛏</div>
            Ask about zones, piles, DPSH refusal, ground profiles, or pile test results.
          </div>
        )}
        {messages.map((m, i) => <Bubble key={i} m={m} />)}
        {busy && <Typing />}
        <div ref={bottomRef} />
      </div>

      {/* composer */}
      <div style={{
        borderTop: "1px solid var(--border)", padding: "12px 16px",
        background: "var(--surface-1)", display: "flex", gap: 10, alignItems: "flex-end",
      }}>
        <textarea
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={onKey}
          placeholder="Message the advisor…"
          rows={1}
          style={{
            flex: 1, minHeight: 40, maxHeight: 140, resize: "none",
            background: "var(--surface-2)", border: "1px solid var(--border-strong)",
            borderRadius: 20, color: "var(--text-primary)", padding: "10px 16px",
            fontSize: 13, fontFamily: "inherit", lineHeight: 1.5, outline: "none",
          }}
          onFocus={e => e.target.style.borderColor = "var(--border-accent)"}
          onBlur={e  => e.target.style.borderColor = "var(--border-strong)"}
        />
        <button
          disabled={busy || !input.trim()}
          onClick={() => send()}
          style={{
            width: 40, height: 40, borderRadius: "50%", border: "none",
            cursor: "pointer", flexShrink: 0, fontSize: 18,
            background: input.trim() && !busy ? "var(--pcl-gold)" : "var(--border-strong)",
            color:      input.trim() && !busy ? "#050608" : "var(--text-muted)",
            display: "flex", alignItems: "center", justifyContent: "center",
            transition: "background .12s, color .12s",
          }}
        >▶</button>
      </div>

      <style>{`
        @keyframes bounce {
          0%,80%,100% { transform:translateY(0); opacity:.4; }
          40%          { transform:translateY(-5px); opacity:1; }
        }
      `}</style>
    </div>
  );
}