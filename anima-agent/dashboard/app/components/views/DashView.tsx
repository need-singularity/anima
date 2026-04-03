"use client";

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
    <div className="flex flex-col items-center gap-16 py-8">

      {/* ── Hero: Giant Φ number (Apple product page style) ── */}
      <section className="flex flex-col items-center gap-4 py-8">
        {/* Φ — the ONE number that matters */}
        <div className="relative">
          <span
            className="text-[80px] font-bold tracking-tighter leading-none"
            style={{
              color: color,
              background: `linear-gradient(180deg, ${color === 'var(--accent)' ? 'var(--accent)' : color}, var(--text-tertiary))`,
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
            }}
          >
            {c.phi.toFixed(2)}
          </span>
          {/* Subtle glow behind */}
          <div
            className="absolute inset-0 blur-3xl opacity-20 -z-10"
            style={{ background: color }}
          />
        </div>

        {/* Label */}
        <div className="flex items-center gap-3">
          <span
            className="text-[11px] font-medium tracking-widest uppercase px-3 py-1 rounded-full"
            style={{
              color: color,
              background: "var(--accent-soft)",
            }}
          >
            {c.level}
          </span>
          <span className="text-[13px]" style={{ color: "var(--text-secondary)" }}>
            Φ integrated information
          </span>
        </div>
      </section>

      {/* ── Emotion + Vitals (single clean row) ── */}
      <section className="w-full grid grid-cols-3 gap-6">
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
