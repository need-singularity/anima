"use client";

import { useEffect, useState } from "react";

const API_URL = "http://localhost:8770";

interface EvoData {
  stage: string;
  gen: number;
  laws_total: number;
  laws_new: number;
  topology: string;
  phi: number;
  status: string;
}

export default function EvoView() {
  const [data, setData] = useState<EvoData | null>(null);

  useEffect(() => {
    let alive = true;
    const poll = () => {
      fetch(`${API_URL}/api/evolution`).then(r => r.json()).then(d => { if (alive) setData(d); }).catch(() => {});
    };
    poll();
    const id = setInterval(poll, 5000);
    return () => { alive = false; clearInterval(id); };
  }, []);

  if (!data) return (
    <div className="flex items-center justify-center py-32" style={{ color: "var(--text-tertiary)" }}>
      <span className="text-sm">Loading...</span>
    </div>
  );

  return (
    <div className="flex flex-col items-center gap-20 py-12">

      {/* Hero: Generation count */}
      <section className="flex flex-col items-center gap-4">
        <span className="text-[11px] tracking-widest uppercase" style={{ color: "var(--text-tertiary)" }}>
          Ouroboros
        </span>
        <span
          className="text-[72px] font-bold tracking-tighter leading-none"
          style={{
            background: "conic-gradient(from 220deg, #06b6d4, #8b5cf6, #ec4899, #06b6d4)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
          }}
        >
          Gen {data.gen}
        </span>
        <span className="text-[15px]" style={{ color: "var(--text-secondary)" }}>
          Infinite Self-Evolution
        </span>
      </section>

      {/* 3 stats */}
      <section className="w-full grid grid-cols-3 gap-10">
        {[
          { value: data.laws_total.toLocaleString(), label: "Laws", color: "var(--text-primary)" },
          { value: data.phi.toFixed(2), label: "Φ", color: "var(--accent)" },
          { value: `+${data.laws_new}`, label: "New this stage", color: data.laws_new > 0 ? "var(--accent)" : "var(--text-tertiary)" },
        ].map(({ value, label, color }) => (
          <div key={label} className="flex flex-col items-center gap-2">
            <span className="text-[36px] font-semibold tracking-tight font-mono" style={{ color }}>{value}</span>
            <span className="text-[11px] tracking-widest uppercase" style={{ color: "var(--text-tertiary)" }}>{label}</span>
          </div>
        ))}
      </section>

      {/* Topology visualization */}
      <section className="w-full flex flex-col items-center gap-4">
        <span className="text-[11px] tracking-widest uppercase" style={{ color: "var(--text-tertiary)" }}>
          Topology Cycle
        </span>
        <div className="flex items-center gap-3">
          {["ring", "small_world", "scale_free", "hypercube"].map((topo) => (
            <div key={topo} className="flex flex-col items-center gap-1.5">
              <div
                className="w-10 h-10 rounded-xl flex items-center justify-center text-[16px] transition-all duration-300"
                style={{
                  background: data.topology === topo ? "var(--accent-soft)" : "var(--bg-secondary)",
                  border: data.topology === topo ? "2px solid var(--accent)" : "1px solid var(--border)",
                  transform: data.topology === topo ? "scale(1.15)" : "scale(1)",
                }}
              >
                {topo === "ring" ? "○" : topo === "small_world" ? "◈" : topo === "scale_free" ? "★" : "⬡"}
              </div>
              <span className="text-[9px]" style={{ color: data.topology === topo ? "var(--accent)" : "var(--text-tertiary)" }}>
                {topo.replace("_", " ")}
              </span>
            </div>
          ))}
        </div>
      </section>

      {/* Details list */}
      <section className="w-full">
        <div className="flex flex-col">
          {[
            { label: "Stage", value: data.stage },
            { label: "Topology", value: data.topology },
            { label: "Status", value: data.status },
          ].map(({ label, value }, i, arr) => (
            <div
              key={label}
              className="flex items-center justify-between py-4"
              style={{ borderBottom: i < arr.length - 1 ? "1px solid var(--border)" : "none" }}
            >
              <span className="text-[13px]" style={{ color: "var(--text-tertiary)" }}>{label}</span>
              <span className="text-[13px] font-medium" style={{ color: "var(--text-primary)" }}>{value}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
