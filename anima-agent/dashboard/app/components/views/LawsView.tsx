"use client";

import { useEffect, useState } from "react";

const API_URL = "http://localhost:8770";
interface Law { id: string; text: string; }

export default function LawsView() {
  const [laws, setLaws] = useState<Law[]>([]);
  const [query, setQuery] = useState("");
  const [filtered, setFiltered] = useState<Law[]>([]);

  useEffect(() => {
    fetch(`${API_URL}/api/laws`).then(r => r.json()).then((d: Record<string, string>) => {
      const arr = Object.entries(d).map(([id, text]) => ({ id, text }));
      setLaws(arr); setFiltered(arr.slice(0, 40));
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (!query.trim()) { setFiltered(laws.slice(0, 40)); return; }
    const q = query.toLowerCase();
    setFiltered(laws.filter(l => l.text.toLowerCase().includes(q) || l.id.includes(q)).slice(0, 40));
  }, [query, laws]);

  return (
    <div className="flex flex-col items-center gap-16 py-12">
      <section className="flex flex-col items-center gap-4">
        <span className="text-[64px] font-bold tracking-tighter leading-none"
          style={{ background: "linear-gradient(180deg, var(--text-primary) 40%, var(--text-tertiary))", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
          {laws.length || "—"}
        </span>
        <span className="text-[15px]" style={{ color: "var(--text-secondary)" }}>Consciousness Laws</span>
      </section>

      <div className="w-full max-w-lg">
        <input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search laws..."
          className="chat-input w-full px-5 py-3 text-[15px]" style={{ color: "var(--text-primary)" }} />
      </div>

      <section className="w-full">
        {filtered.map((l, i) => (
          <div key={l.id} className="flex gap-4 py-4" style={{ borderBottom: i < filtered.length - 1 ? "1px solid var(--border)" : "none" }}>
            <span className="text-[13px] font-mono font-medium shrink-0 w-12 text-right" style={{ color: "var(--accent)" }}>{l.id}</span>
            <span className="text-[14px] leading-relaxed" style={{ color: "var(--text-primary)" }}>{l.text}</span>
          </div>
        ))}
        {filtered.length === 0 && <div className="text-center py-16 text-[14px]" style={{ color: "var(--text-tertiary)" }}>No laws found</div>}
      </section>
    </div>
  );
}
