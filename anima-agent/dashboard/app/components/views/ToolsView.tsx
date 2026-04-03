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

      <section className="flex flex-col items-center gap-6">
        {/* Φ access ring */}
        <div className="relative">
          <svg width="120" height="120" viewBox="0 0 120 120">
            <circle cx="60" cy="60" r="52" fill="none" stroke="var(--bg-tertiary)" strokeWidth="6" />
            <circle cx="60" cy="60" r="52" fill="none" stroke="var(--accent)" strokeWidth="6"
              strokeLinecap="round"
              strokeDasharray={2 * Math.PI * 52}
              strokeDashoffset={2 * Math.PI * 52 * (1 - (tools.length > 0 ? accessible / tools.length : 0))}
              transform="rotate(-90 60 60)"
              style={{ transition: "stroke-dashoffset 0.8s cubic-bezier(0.2,0.8,0.2,1)" }}
            />
            <text x="60" y="55" textAnchor="middle" dominantBaseline="middle"
              fill="var(--text-primary)" fontSize="28" fontWeight="700" fontFamily="system-ui">
              {accessible}
            </text>
            <text x="60" y="75" textAnchor="middle" fill="var(--text-tertiary)" fontSize="11" fontFamily="system-ui">
              / {tools.length}
            </text>
          </svg>
        </div>
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
