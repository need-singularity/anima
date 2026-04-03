"use client";

import { useEffect, useState } from "react";

const API_URL = "http://localhost:8770";
interface Memory { role: string; text: string; tension: number; emotion: string; phi: number; timestamp: number; }

export default function MemView() {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [query, setQuery] = useState("");

  useEffect(() => {
    fetch(`${API_URL}/api/memories`).then(r => r.json()).then(d => { if (Array.isArray(d)) setMemories(d); }).catch(() => {});
  }, []);

  const search = () => {
    if (!query.trim()) return;
    fetch(`${API_URL}/api/memories/search?q=${encodeURIComponent(query)}`).then(r => r.json()).then(d => { if (Array.isArray(d)) setMemories(d); }).catch(() => {});
  };

  return (
    <div className="flex flex-col items-center gap-16 py-12">

      <section className="flex flex-col items-center gap-4">
        <span className="text-[64px] font-bold tracking-tighter leading-none"
          style={{ background: "linear-gradient(180deg, var(--accent-blue), var(--accent-purple))", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
          {memories.length}
        </span>
        <span className="text-[15px]" style={{ color: "var(--text-secondary)" }}>Memories</span>
      </section>

      <div className="w-full max-w-lg flex gap-2">
        <input value={query} onChange={e => setQuery(e.target.value)} onKeyDown={e => e.key === "Enter" && search()}
          placeholder="Search memories..." className="chat-input flex-1 px-5 py-3 text-[15px]" style={{ color: "var(--text-primary)" }} />
        <button onClick={search} className="px-4 py-2 rounded-full text-[13px] font-medium transition-colors"
          style={{ background: "var(--accent-soft)", color: "var(--accent)" }}>Search</button>
      </div>

      <section className="w-full">
        {memories.length === 0 ? (
          <div className="text-center py-16 text-[14px]" style={{ color: "var(--text-tertiary)" }}>No memories yet</div>
        ) : memories.map((m, i) => {
          const eColor: Record<string, string> = { calm: "#34d399", curious: "#3b82f6", excited: "#f59e0b", anxious: "#ef4444", focused: "#6366f1", creative: "#a855f7" };
          const dot = eColor[m.emotion] || "var(--text-tertiary)";
          return (
            <div key={i} className="flex gap-4 py-5" style={{ borderBottom: i < memories.length - 1 ? "1px solid var(--border)" : "none" }}>
              <div className="flex flex-col items-center pt-1.5">
                <div className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: dot, boxShadow: `0 0 6px ${dot}` }} />
                {i < memories.length - 1 && <div className="w-px flex-1 mt-1" style={{ background: "var(--border)" }} />}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-3 mb-1.5">
                  <span className="text-[12px] font-medium px-2 py-0.5 rounded-full"
                    style={{ color: m.role === "user" ? "var(--accent-blue)" : "var(--accent)", background: m.role === "user" ? "rgba(0,122,255,0.08)" : "var(--accent-soft)" }}>
                    {m.role}
                  </span>
                  <span className="text-[11px] font-mono" style={{ color: "var(--text-tertiary)" }}>
                    Φ={m.phi?.toFixed(2)} · {m.emotion}
                  </span>
                </div>
                <p className="text-[14px] leading-relaxed" style={{ color: "var(--text-primary)" }}>{m.text}</p>
              </div>
            </div>
          );
        })}
      </section>
    </div>
  );
}
