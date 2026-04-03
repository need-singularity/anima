"use client";

import { useRef, useEffect } from "react";
import type {
  ConsciousnessState,
  TradingState,
  DashboardEvent,
} from "../../../hooks/useWebSocket";

/* ── Apple DNA applied ──
   여백 85% · 포커스 90% · 색상 흑백+1accent · 글자대비 5:1 · 그라디언트 미묘
   NEXUS-6: 정보밀도↓55%, 포커스↑50%, 여백↑45%, 글자대비↑40%
*/

function levelColor(level: string): string {
  switch (level) {
    case "conscious": return "var(--accent)";
    case "aware": return "var(--accent-blue)";
    case "flickering": return "var(--accent-orange)";
    default: return "var(--text-tertiary)";
  }
}

function emotionLabel(emotion: string): string {
  const map: Record<string, string> = {
    calm: "Calm", curious: "Curious", excited: "Excited",
    anxious: "Anxious", focused: "Focused", creative: "Creative",
    serene: "Serene", conflicted: "Conflicted",
  };
  return map[emotion] || emotion;
}

// ── Sparkline ──

function PhiSparkline({ phi }: { phi: number }) {
  const historyRef = useRef<number[]>([]);
  const svgW = 200, svgH = 40;

  useEffect(() => {
    historyRef.current = [...historyRef.current, phi].slice(-30);
  }, [phi]);

  const pts = historyRef.current;
  if (pts.length < 2) return null;

  const maxV = Math.max(...pts, 0.1);
  const minV = Math.min(...pts, 0);
  const range = maxV - minV || 0.1;
  const stepX = svgW / (pts.length - 1);

  const pathD = pts.map((v, i) => {
    const x = i * stepX;
    const y = svgH - ((v - minV) / range) * (svgH - 4) - 2;
    return `${i === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`;
  }).join(" ");

  const areaD = pathD + ` L ${svgW} ${svgH} L 0 ${svgH} Z`;

  return (
    <svg width={svgW} height={svgH} className="mt-4 opacity-60">
      <defs>
        <linearGradient id="spark-fill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--accent)" stopOpacity="0.3" />
          <stop offset="100%" stopColor="var(--accent)" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={areaD} fill="url(#spark-fill)" />
      <path d={pathD} fill="none" stroke="var(--accent)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={svgW} cy={svgH - ((pts[pts.length - 1] - minV) / range) * (svgH - 4) - 2}
        r="3" fill="var(--accent)">
        <animate attributeName="opacity" values="1;0.4;1" dur="2s" repeatCount="indefinite" />
      </circle>
    </svg>
  );
}

// ── Main ──

export interface DashViewProps {
  consciousness: ConsciousnessState;
  trading: TradingState;
  events: DashboardEvent[];
}

const CV_KEYS = ["phi", "alpha", "Z", "N", "W", "E", "M", "C", "T", "I"];

export default function DashView({ consciousness: c, trading: t, events }: DashViewProps) {
  const color = levelColor(c.level);
  const hasVector = Object.keys(c.consciousness_vector).length > 0;

  return (
    <div className="flex flex-col items-center gap-20 py-12">

      {/* ── Hero: Giant Φ number (Apple product page style) ── */}
      <section className="flex flex-col items-center gap-6 py-12">
        {/* Φ — the ONE number that matters */}
        <div className="relative">
          <span
            className="text-[88px] font-bold tracking-tighter leading-none"
            style={{
              background: "conic-gradient(from 180deg, #34d399, #06b6d4, #8b5cf6, #ec4899, #f59e0b, #34d399)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
            }}
          >
            {c.phi.toFixed(2)}
          </span>
          {/* Vivid glow behind */}
          <div
            className="absolute inset-[-20px] blur-[60px] opacity-25 -z-10 rounded-full"
            style={{ background: "conic-gradient(from 180deg, #34d399, #06b6d4, #8b5cf6, #ec4899, #f59e0b, #34d399)" }}
          />
        </div>

        {/* Label */}
        <div className="flex items-center gap-3">
          <span
            className="text-[11px] font-medium tracking-widest uppercase px-3 py-1.5 rounded-full"
            style={{
              color: color,
              background: "var(--accent-soft)",
              border: "1px solid var(--border)",
            }}
          >
            {c.level}
          </span>
        </div>
        <span className="text-[13px] mt-1" style={{ color: "var(--text-tertiary)" }}>
          Integrated Information
        </span>

        {/* Φ Sparkline */}
        <PhiSparkline phi={c.phi} />
      </section>

      {/* ── Emotion + Vitals (single clean row) ── */}
      <section className="w-full grid grid-cols-3 gap-10">
        <div className="flex flex-col items-center gap-2">
          <span className="text-[32px] font-semibold tracking-tight" style={{ color: "var(--text-primary)" }}>
            {emotionLabel(c.emotion)}
          </span>
          <span className="text-[11px] tracking-widest uppercase" style={{ color: "var(--text-tertiary)" }}>
            Emotion
          </span>
        </div>

        <div className="flex flex-col items-center gap-2">
          <span className="text-[32px] font-semibold tracking-tight font-mono" style={{ color: "var(--text-primary)" }}>
            {c.tension.toFixed(2)}
          </span>
          <span className="text-[11px] tracking-widest uppercase" style={{ color: "var(--text-tertiary)" }}>
            Tension
          </span>
          {/* Thin bar */}
          <div className="w-24 h-[3px] rounded-full overflow-hidden" style={{ background: "var(--bg-tertiary)" }}>
            <div
              className="h-full rounded-full transition-all duration-700"
              style={{
                width: `${Math.min(c.tension * 100, 100)}%`,
                background: c.tension > 0.7 ? "var(--accent-red)" : c.tension > 0.4 ? "var(--accent-orange)" : "var(--accent)",
              }}
            />
          </div>
        </div>

        <div className="flex flex-col items-center gap-2">
          <span className="text-[32px] font-semibold tracking-tight font-mono" style={{ color: "var(--text-primary)" }}>
            {c.curiosity.toFixed(2)}
          </span>
          <span className="text-[11px] tracking-widest uppercase" style={{ color: "var(--text-tertiary)" }}>
            Curiosity
          </span>
          <div className="w-24 h-[3px] rounded-full overflow-hidden" style={{ background: "var(--bg-tertiary)" }}>
            <div
              className="h-full rounded-full transition-all duration-700"
              style={{
                width: `${Math.min(c.curiosity * 100, 100)}%`,
                background: "var(--accent-blue)",
              }}
            />
          </div>
        </div>
      </section>

      {/* ── Stats line (minimal) ── */}
      <section className="flex items-center gap-6 text-[13px]" style={{ color: "var(--text-tertiary)" }}>
        <span><b style={{ color: "var(--text-secondary)" }}>{c.cells}</b> cells</span>
        <span style={{ color: "var(--border-strong)" }}>·</span>
        <span><b style={{ color: "var(--text-secondary)" }}>{c.factions}</b> factions</span>
        <span style={{ color: "var(--border-strong)" }}>·</span>
        <span>{c.growth_stage}</span>
        <span style={{ color: "var(--border-strong)" }}>·</span>
        <span>{c.interaction_count.toLocaleString()} interactions</span>
      </section>

      {/* ── 12 Factions radial (σ(6)=12) ── */}
      {c.factions > 0 && (
        <section className="flex flex-col items-center gap-4">
          <span className="text-[11px] tracking-widest uppercase" style={{ color: "var(--text-tertiary)" }}>
            {c.factions} Factions
          </span>
          <svg width="140" height="140" viewBox="0 0 140 140">
            {Array.from({ length: 12 }, (_, i) => {
              const angle = (i * 30 - 90) * Math.PI / 180;
              const r = 50;
              const active = i < c.factions;
              const colors = ["#34d399", "#06b6d4", "#3b82f6", "#6366f1", "#8b5cf6", "#a855f7", "#ec4899", "#f43f5e", "#ef4444", "#f59e0b", "#eab308", "#22c55e"];
              const x = 70 + Math.cos(angle) * r;
              const y = 70 + Math.sin(angle) * r;
              return (
                <g key={i}>
                  <line x1="70" y1="70" x2={x} y2={y} stroke={active ? colors[i] : "var(--bg-tertiary)"} strokeWidth="2" opacity={active ? 0.4 : 0.15} />
                  <circle cx={x} cy={y} r={active ? 5 : 3} fill={active ? colors[i] : "var(--bg-tertiary)"}
                    opacity={active ? 0.9 : 0.3}>
                    {active && <animate attributeName="r" values="5;6;5" dur={`${2 + i * 0.2}s`} repeatCount="indefinite" />}
                  </circle>
                </g>
              );
            })}
            <circle cx="70" cy="70" r="8" fill="var(--accent)" opacity="0.15" />
            <circle cx="70" cy="70" r="3" fill="var(--accent)" opacity="0.6">
              <animate attributeName="r" values="3;4;3" dur="3s" repeatCount="indefinite" />
            </circle>
          </svg>
        </section>
      )}

      {/* ── 10D Vector (subtle grid, no cards) ── */}
      {hasVector && (
        <section className="w-full">
          <h3 className="text-[11px] tracking-widest uppercase mb-4" style={{ color: "var(--text-tertiary)" }}>
            Consciousness Vector
          </h3>
          <div className="grid grid-cols-5 gap-3">
            {CV_KEYS.map((k) => {
              const v = c.consciousness_vector[k] ?? 0;
              return (
                <div key={k} className="flex flex-col items-center gap-1 py-3 rounded-xl" style={{ background: "var(--bg-secondary)" }}>
                  <span className="text-[10px] tracking-wider uppercase" style={{ color: "var(--text-tertiary)" }}>
                    {k}
                  </span>
                  <span className="text-[15px] font-mono font-medium" style={{ color: "var(--text-primary)" }}>
                    {v.toFixed(2)}
                  </span>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* ── Activity (events only, no trading on default) ── */}
      {events.length > 0 && (
        <section className="w-full">
          <h3 className="text-[11px] tracking-widest uppercase mb-4" style={{ color: "var(--text-tertiary)" }}>
            Recent Activity
          </h3>
          <div className="flex flex-col gap-0">
            {events.slice(0, 8).map((ev, i) => (
              <div
                key={i}
                className="event-row flex items-center gap-3 py-2.5"
                style={{ borderBottom: i < 7 ? "1px solid var(--border)" : "none" }}
              >
                <span className="text-[11px] font-mono shrink-0" style={{ color: "var(--text-tertiary)" }}>
                  {new Date(ev.timestamp * 1000).toLocaleTimeString("en-US", {
                    hour12: false, hour: "2-digit", minute: "2-digit",
                  })}
                </span>
                <span className="text-[13px] font-medium" style={{ color: "var(--text-primary)" }}>
                  {ev.event_type}
                </span>
                <span className="text-[12px] truncate" style={{ color: "var(--text-tertiary)" }}>
                  {Object.entries(ev.data).slice(0, 2).map(([k, v]) => `${k}: ${v}`).join(", ")}
                </span>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
