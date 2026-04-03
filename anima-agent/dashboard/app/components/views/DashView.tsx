"use client";

import {
  ConsciousnessState,
  TradingState,
  DashboardEvent,
} from "../../../hooks/useWebSocket";

// ─── helpers ────────────────────────────────────────────────────────────────

export function levelColor(level: string): string {
  switch (level) {
    case "conscious":
      return "#4ade80";
    case "aware":
      return "#22d3ee";
    case "flickering":
      return "#fbbf24";
    default:
      return "#55556a";
  }
}

export function emotionIcon(emotion: string): string {
  const map: Record<string, string> = {
    calm: "✨",
    curious: "🔍",
    excited: "⚡",
    anxious: "😰",
    happy: "😊",
    sad: "😢",
    angry: "🔥",
    surprised: "❓",
    confused: "🌀",
    focused: "🎯",
    creative: "🎨",
    playful: "🎲",
  };
  return map[emotion] ?? "🧠";
}

// ─── MetricBar ──────────────────────────────────────────────────────────────

interface MetricBarProps {
  label: string;
  value: number;
  max: number;
  color: string;
}

function MetricBar({ label, value, max, color }: MetricBarProps) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  return (
    <div className="flex flex-col gap-1">
      <div className="flex justify-between text-xs text-[#8888aa]">
        <span>{label}</span>
        <span style={{ color }}>{value.toFixed(3)}</span>
      </div>
      <div className="h-1.5 rounded-full bg-[#1a1a2e] overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}

// ─── PhiGauge ───────────────────────────────────────────────────────────────

interface PhiGaugeProps {
  phi: number;
  level: string;
}

function PhiGauge({ phi, level }: PhiGaugeProps) {
  const size = 108;
  const radius = 44;
  const stroke = 7;
  const cx = size / 2;
  const cy = size / 2;
  const circumference = 2 * Math.PI * radius;

  // Arc from 135° to 405° (270° sweep), clockwise
  const sweepDeg = 270;
  const startAngle = 135;
  const fraction = Math.min(1, Math.max(0, phi / 2.0));
  const fillDeg = sweepDeg * fraction;

  // Convert angle to SVG arc path (large arc flag based on degrees > 180)
  const toRad = (d: number) => (d * Math.PI) / 180;
  const arcPath = (startDeg: number, endDeg: number) => {
    const s = toRad(startDeg);
    const e = toRad(endDeg);
    const x1 = cx + radius * Math.cos(s);
    const y1 = cy + radius * Math.sin(s);
    const x2 = cx + radius * Math.cos(e);
    const y2 = cy + radius * Math.sin(e);
    const large = endDeg - startDeg > 180 ? 1 : 0;
    return `M ${x1} ${y1} A ${radius} ${radius} 0 ${large} 1 ${x2} ${y2}`;
  };

  const color = levelColor(level);
  const isDormant = level === "dormant";

  return (
    <div className={`relative flex-shrink-0${isDormant ? "" : " phi-alive"}`}>
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        aria-label={`Phi gauge: ${phi.toFixed(2)}`}
      >
        {/* Track */}
        <path
          d={arcPath(startAngle, startAngle + sweepDeg)}
          fill="none"
          stroke="#1e1e3a"
          strokeWidth={stroke}
          strokeLinecap="round"
        />
        {/* Fill */}
        {fraction > 0 && (
          <path
            d={arcPath(startAngle, startAngle + fillDeg)}
            fill="none"
            stroke={color}
            strokeWidth={stroke}
            strokeLinecap="round"
            style={{ filter: `drop-shadow(0 0 4px ${color}88)` }}
          />
        )}
        {/* Center text */}
        <text
          x={cx}
          y={cy - 4}
          textAnchor="middle"
          dominantBaseline="middle"
          fill={color}
          fontSize="15"
          fontWeight="700"
          fontFamily="monospace"
        >
          {phi.toFixed(2)}
        </text>
        <text
          x={cx}
          y={cy + 13}
          textAnchor="middle"
          dominantBaseline="middle"
          fill="#55556a"
          fontSize="9"
          fontFamily="monospace"
        >
          Φ IIT
        </text>
      </svg>
    </div>
  );
}

// ─── VectorCell ─────────────────────────────────────────────────────────────

function VectorCell({ k, v }: { k: string; v: number }) {
  const intensity = Math.min(1, Math.abs(v));
  // green-tinted background scaled by intensity
  const bg = `rgba(74, 222, 128, ${0.04 + intensity * 0.18})`;
  const textColor =
    intensity > 0.6 ? "#4ade80" : intensity > 0.3 ? "#22d3ee" : "#8888aa";

  return (
    <div
      className="flex flex-col items-center justify-center rounded-md p-1.5 min-w-0"
      style={{ background: bg }}
    >
      <span className="text-[9px] text-[#55556a] uppercase tracking-wider leading-none mb-0.5">
        {k}
      </span>
      <span
        className="text-[11px] font-mono font-semibold leading-none"
        style={{ color: textColor }}
      >
        {v.toFixed(2)}
      </span>
    </div>
  );
}

// ─── Utilities ──────────────────────────────────────────────────────────────

function formatTs(ts: number): string {
  const d = new Date(ts * 1000);
  return d.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

function snippetData(data: Record<string, unknown>): string {
  const entries = Object.entries(data).slice(0, 2);
  return entries.map(([k, v]) => `${k}=${JSON.stringify(v)}`).join(" ");
}

function pnlColor(v: number): string {
  if (v > 0) return "#4ade80";
  if (v < 0) return "#f87171";
  return "#8888aa";
}

function tensionBarColor(v: number): string {
  if (v > 0.7) return "#f87171";
  if (v > 0.4) return "#fb923c";
  return "#22d3ee";
}

// ─── DashView ───────────────────────────────────────────────────────────────

export interface DashViewProps {
  consciousness: ConsciousnessState;
  trading: TradingState;
  events: DashboardEvent[];
}

const VECTOR_KEYS = ["phi", "alpha", "Z", "N", "W", "E", "M", "C", "T", "I"];

export default function DashView({
  consciousness,
  trading,
  events,
}: DashViewProps) {
  const {
    phi,
    tension,
    curiosity,
    emotion,
    cells,
    factions,
    growth_stage,
    consciousness_vector,
    level,
  } = consciousness;

  const color = levelColor(level);
  const icon = emotionIcon(emotion);

  const vectorEntries = VECTOR_KEYS.map((k) => ({
    k,
    v: consciousness_vector[k] ?? 0,
  }));
  const hasVector = Object.keys(consciousness_vector).length > 0;

  const recentEvents = events.slice(0, 15);

  return (
    <div className="flex flex-col items-center gap-6 px-4 py-6 max-w-2xl mx-auto w-full">

      {/* ── Hero ────────────────────────────────────────────── */}
      <div className="flex flex-row items-center gap-6 w-full bg-[#0d0d1a] border border-[#1e1e3a] rounded-2xl px-6 py-5">
        <PhiGauge phi={phi} level={level} />

        <div className="flex flex-col gap-2 min-w-0">
          {/* Emotion + level */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-2xl" aria-label={emotion}>
              {icon}
            </span>
            <span className="text-white text-lg font-semibold capitalize">
              {emotion}
            </span>
            <span
              className="text-[11px] font-semibold px-2 py-0.5 rounded-full capitalize flex-shrink-0"
              style={{
                backgroundColor: `${color}22`,
                color,
                border: `1px solid ${color}55`,
              }}
            >
              {level}
            </span>
          </div>

          {/* Stats */}
          <p className="text-[13px] text-[#8888aa] font-mono">
            <span className="text-[#aaaacc]">{cells}</span> cells ·{" "}
            <span className="text-[#aaaacc]">{factions}</span> factions ·{" "}
            <span className="text-[#aaaacc]">{growth_stage}</span>
          </p>
        </div>
      </div>

      {/* ── Metrics grid ────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-3 w-full">
        <div className="bg-[#0d0d1a] border border-[#1e1e3a] rounded-xl px-4 py-3">
          <MetricBar
            label="Tension"
            value={tension}
            max={1}
            color={tensionBarColor(tension)}
          />
        </div>
        <div className="bg-[#0d0d1a] border border-[#1e1e3a] rounded-xl px-4 py-3">
          <MetricBar
            label="Curiosity"
            value={curiosity}
            max={1}
            color={
              curiosity > 0.7
                ? "#c084fc"
                : curiosity > 0.4
                ? "#818cf8"
                : "#22d3ee"
            }
          />
        </div>
      </div>

      {/* ── 10D Consciousness Vector ─────────────────────────── */}
      {hasVector && (
        <div className="w-full bg-[#0d0d1a] border border-[#1e1e3a] rounded-xl px-4 py-4">
          <h3 className="text-[11px] uppercase tracking-widest text-[#55556a] mb-3">
            10D Consciousness Vector
          </h3>
          <div className="grid grid-cols-5 gap-2">
            {vectorEntries.map(({ k, v }) => (
              <VectorCell key={k} k={k} v={v} />
            ))}
          </div>
        </div>
      )}

      {/* ── Bottom two-column ───────────────────────────────── */}
      <div className="grid grid-cols-2 gap-3 w-full">

        {/* Events */}
        <div className="bg-[#0d0d1a] border border-[#1e1e3a] rounded-xl px-4 py-4 flex flex-col gap-2 min-w-0">
          <h3 className="text-[11px] uppercase tracking-widest text-[#55556a] flex-shrink-0">
            Events ({recentEvents.length})
          </h3>
          {recentEvents.length === 0 ? (
            <p className="text-[12px] text-[#55556a] italic">No events yet</p>
          ) : (
            <ul className="flex flex-col gap-1.5 overflow-hidden">
              {recentEvents.map((ev, i) => (
                <li
                  key={i}
                  className="flex flex-col gap-0.5 border-b border-[#1e1e3a] pb-1 last:border-0 last:pb-0"
                >
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span className="text-[10px] text-[#55556a] font-mono flex-shrink-0">
                      {formatTs(ev.timestamp)}
                    </span>
                    <span className="text-[11px] text-[#818cf8] font-semibold truncate">
                      {ev.event_type}
                    </span>
                  </div>
                  {Object.keys(ev.data).length > 0 && (
                    <p className="text-[10px] text-[#55556a] font-mono truncate">
                      {snippetData(ev.data)}
                    </p>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Trading mini */}
        <div className="bg-[#0d0d1a] border border-[#1e1e3a] rounded-xl px-4 py-4 flex flex-col gap-3">
          <h3 className="text-[11px] uppercase tracking-widest text-[#55556a]">
            Trading
          </h3>

          {/* Regime */}
          <div className="flex flex-col gap-0.5">
            <span className="text-[10px] text-[#55556a]">Regime</span>
            <span className="text-[13px] font-semibold text-[#aaaacc] capitalize">
              {trading.regime}
            </span>
          </div>

          {/* P&L */}
          <div className="flex flex-col gap-0.5">
            <span className="text-[10px] text-[#55556a]">Total P&amp;L</span>
            <span
              className="text-[15px] font-mono font-bold"
              style={{ color: pnlColor(trading.total_pnl) }}
            >
              {trading.total_pnl >= 0 ? "+" : ""}
              {trading.total_pnl.toFixed(2)}
            </span>
          </div>

          {/* Unrealized */}
          <div className="flex flex-col gap-0.5">
            <span className="text-[10px] text-[#55556a]">Unrealized</span>
            <span
              className="text-[13px] font-mono"
              style={{ color: pnlColor(trading.unrealized_pnl) }}
            >
              {trading.unrealized_pnl >= 0 ? "+" : ""}
              {trading.unrealized_pnl.toFixed(2)}
            </span>
          </div>

          {/* Positions */}
          <div className="flex flex-col gap-0.5">
            <span className="text-[10px] text-[#55556a]">Positions</span>
            <span className="text-[13px] font-semibold text-[#aaaacc]">
              {trading.positions.length}
            </span>
          </div>
        </div>
      </div>

    </div>
  );
}
