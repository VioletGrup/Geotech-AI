import React, { useRef, useEffect, useState } from "react";
import { api } from "../api.js";

export default function Copilot() {
  const [messages, setMessages] = useState([]);
  const [input,    setInput]    = useState("");
  const [busy,     setBusy]     = useState(false);
  const bottomRef = useRef(null);
  const textareaRef = useRef(null);

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
      setMessages(m => [...m, { role: "bot", text: res.reply }]);
    } catch(e) {
      setMessages(m => [...m, { role: "bot", text: `Error: ${e.message}`, err: true }]);
    } finally { setBusy(false); }
  }

  function onKey(e) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
  }

  function formatTime() {
    return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  return (
    <div style={{display:"flex",flexDirection:"column",height:"calc(100vh - 120px)"}}>

      {/* message list */}
      <div style={{flex:1,overflowY:"auto",padding:"16px 20px",
        display:"flex",flexDirection:"column",gap:4}}>

        {messages.length === 0 && (
          <div style={{margin:"auto",textAlign:"center",color:"var(--text-muted)",fontSize:13}}>
            <div style={{fontSize:32,marginBottom:12}}>⛏</div>
            Ask about zones, piles, DPSH refusal, ground profiles, or pile test results.
          </div>
        )}

        {messages.map((m, i) => {
          const isUser = m.role === "user";
          return (
            <div key={i} style={{display:"flex",flexDirection:"column",
              alignItems:isUser?"flex-end":"flex-start",marginBottom:2}}>
              {/* bubble */}
              <div style={{
                maxWidth:"72%",
                padding:"10px 14px",
                borderRadius:isUser?"18px 18px 4px 18px":"18px 18px 18px 4px",
                background:isUser
                  ? "var(--pcl-gold)"
                  : m.err ? "var(--bg-danger)" : "var(--surface-2)",
                color:isUser
                  ? "#050608"
                  : m.err ? "var(--text-danger)" : "var(--text-primary)",
                border:isUser
                  ? "none"
                  : `1px solid ${m.err?"var(--border-danger)":"var(--border-strong)"}`,
                fontSize:13,
                lineHeight:1.6,
                whiteSpace:"pre-wrap",
                wordBreak:"break-word",
              }}>
                {m.text}
              </div>
            </div>
          );
        })}

        {/* typing indicator */}
        {busy && (
          <div style={{display:"flex",alignItems:"flex-start",marginBottom:2}}>
            <div style={{padding:"10px 16px",borderRadius:"18px 18px 18px 4px",
              background:"var(--surface-2)",border:"1px solid var(--border-strong)",
              display:"flex",gap:5,alignItems:"center"}}>
              {[0,1,2].map(i=>(
                <span key={i} style={{width:6,height:6,borderRadius:"50%",
                  background:"var(--text-muted)",display:"inline-block",
                  animation:`bounce 1.2s ease-in-out ${i*0.2}s infinite`}}/>
              ))}
            </div>
          </div>
        )}

        <div ref={bottomRef}/>
      </div>

      {/* composer */}
      <div style={{borderTop:"1px solid var(--border)",padding:"12px 16px",
        background:"var(--surface-1)",display:"flex",gap:10,alignItems:"flex-end"}}>
        <textarea
          ref={textareaRef}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={onKey}
          placeholder="Message the advisor…"
          rows={1}
          style={{flex:1,minHeight:40,maxHeight:140,resize:"none",
            background:"var(--surface-2)",border:"1px solid var(--border-strong)",
            borderRadius:20,color:"var(--text-primary)",padding:"10px 16px",
            fontSize:13,fontFamily:"inherit",lineHeight:1.5,outline:"none",
            transition:"border-color .12s",}}
          onFocus={e=>e.target.style.borderColor="var(--border-accent)"}
          onBlur={e=>e.target.style.borderColor="var(--border-strong)"}
        />
        <button
          disabled={busy || !input.trim()}
          onClick={() => send()}
          style={{width:40,height:40,borderRadius:"50%",border:"none",cursor:"pointer",
            background:input.trim()&&!busy?"var(--pcl-gold)":"var(--border-strong)",
            color:input.trim()&&!busy?"#050608":"var(--text-muted)",
            display:"flex",alignItems:"center",justifyContent:"center",
            flexShrink:0,fontSize:18,transition:"background .12s,color .12s"}}>
          ▶
        </button>
      </div>

      <style>{`
        @keyframes bounce {
          0%,80%,100% { transform: translateY(0); opacity:.4; }
          40%          { transform: translateY(-5px); opacity:1; }
        }
      `}</style>
    </div>
  );
}