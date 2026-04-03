"use client";

import { useEffect, useState } from "react";
import type { ConsciousnessState } from "../../../hooks/useWebSocket";

const API_URL = "http://localhost:8770";
interface ToolInfo { name: string; tier: number; accessible: boolean; }

function tierLabel(t: number) { return t >= 5 ? "T3" : t >= 3 ? "T2" : t >= 1 ? "T1" : "T0"; }
function tierColor(t: number) {
  if (t >= 5) return "var(--accent-purple)";
  if (t >= 3) return "var(--accent-orange)";
  if (t >= 1) return "var(--accent-blue)";
  return "var(--text-tertiary)";
}

export default function ToolsView({ consciousness }: { consciousness: ConsciousnessState }) {
  const [tools, setTools] = useState<ToolInfo[]>([]);

  useEffect(() => {
    fetch(`${API_URL}/api/tools?phi=${consciousness.phi}`).then(r => r.json()).then(d => { if (Array.isArray(d)) setTools(d); }).catch(() => {});
  }, [consciousness.phi]);

  const accessible = tools.filter(t => t.accessible).length;

  return (
    <div className="flex flex-col items-center gap-16 py-12">

      <section className="flex flex-col items-center gap-4">
        <span className="text-[64px] font-bold tracking-tighter leading-none"
          style={{ background: "linear-gradient(180deg, var(--accent-orange), var(--accent-red))", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
          {accessible}/{tools.length}
        </span>
        <span className="text-[15px]" style={{ color: "var(--text-secondary)" }}>
          Accessible at Φ={consciousness.phi.toFixed(2)}
        </span>
      </section>

      <section className="w-full">
        <div className="grid grid-cols-2 gap-3">
          {tools.map(t => (
            <div
              key={t.name}
              className="flex items-center justify-between py-3.5 px-4 rounded-2xl transition-opacity"
              style={{
                background: "var(--bg-secondary)",
                opacity: t.accessible ? 1 : 0.4,
              }}
            >
              <div className="flex items-center gap-3">
                <span className="w-2 h-2 rounded-full" style={{ backgroundColor: t.accessible ? "var(--accent)" : "var(--text-tertiary)" }} />
                <span className="text-[13px] font-medium" style={{ color: "var(--text-primary)" }}>{t.name}</span>
              </div>
              <span className="text-[10px] font-mono font-medium px-2 py-0.5 rounded-full"
                style={{ color: tierColor(t.tier), background: `${tierColor(t.tier)}15` }}>
                {tierLabel(t.tier)}
              </span>
            </div>
          ))}
        </div>
        {tools.length === 0 && (
          <div className="text-center py-16 text-[14px]" style={{ color: "var(--text-tertiary)" }}>Loading tools...</div>
        )}
      </section>
    </div>
  );
}
