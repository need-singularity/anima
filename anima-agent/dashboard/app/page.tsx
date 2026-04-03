"use client";

import { useEffect, useRef, useState, useCallback, useMemo } from "react";

// ── Types matching dashboard_bridge.py ──

interface ConsciousnessState {
  phi: number;
  tension: number;
  curiosity: number;
  emotion: string;
  cells: number;
  factions: number;
  growth_stage: string;
  interaction_count: number;
  uptime_seconds: number;
  consciousness_vector: Record<string, number>;
  level: string;
}

interface Position {
  symbol: string;
  side: string;
  qty: number;
  entry_price: number;
  current_price: number;
  pnl: number;
  pnl_pct: number;
}

interface TradingState {
  positions: Position[];
  total_pnl: number;
  unrealized_pnl: number;
  regime: string;
  active_strategies: string[];
  balance: number;
  last_trade: Record<string, unknown> | null;
  portfolio_value: number;
}

interface DashboardEvent {
  source: string;
  event_type: string;
  data: Record<string, unknown>;
  timestamp: number;
}

interface LensResult {
  name: string;
  score: number;
  findings: string[];
}

interface DashboardState {
  consciousness: ConsciousnessState;
  trading: TradingState;
  lenses: LensResult[];
  meta: {
    agent_connected: boolean;
    trading_connected: boolean;
    event_count: number;
  };
}

// ── Constants ──

const WS_URL = "ws://localhost:8770";
const MAX_EVENTS = 200;
const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 30000;

const DEFAULT_CONSCIOUSNESS: ConsciousnessState = {
  phi: 0,
  tension: 0,
  curiosity: 0,
  emotion: "calm",
  cells: 0,
  factions: 0,
  growth_stage: "newborn",
  interaction_count: 0,
  uptime_seconds: 0,
  consciousness_vector: {},
  level: "dormant",
};

const DEFAULT_TRADING: TradingState = {
  positions: [],
  total_pnl: 0,
  unrealized_pnl: 0,
  regime: "unknown",
  active_strategies: [],
  balance: 0,
  last_trade: null,
  portfolio_value: 0,
};

// ── Hook: WebSocket ──

function useWebSocket() {
  const [consciousness, setConsciousness] = useState<ConsciousnessState>(DEFAULT_CONSCIOUSNESS);
  const [trading, setTrading] = useState<TradingState>(DEFAULT_TRADING);
  const [events, setEvents] = useState<DashboardEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [meta, setMeta] = useState({ agent_connected: false, trading_connected: false, event_count: 0 });
  const wsRef = useRef<WebSocket | null>(null);
  const retryRef = useRef(RECONNECT_BASE_MS);

  const addEvent = useCallback((evt: DashboardEvent) => {
    setEvents((prev) => {
      const next = [evt, ...prev];
      return next.length > MAX_EVENTS ? next.slice(0, MAX_EVENTS) : next;
    });
  }, []);

  const connect = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState < 2) return;

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      retryRef.current = RECONNECT_BASE_MS;
    };

    ws.onclose = () => {
      setConnected(false);
      const delay = Math.min(retryRef.current, RECONNECT_MAX_MS);
      retryRef.current = delay * 1.5;
      setTimeout(connect, delay);
    };

    ws.onerror = () => {
      ws.close();
    };

    ws.onmessage = (msg) => {
      try {
        const data = JSON.parse(msg.data);

        if (data.type === "dashboard_state") {
          setConsciousness(data.consciousness);
          setTrading(data.trading);
          setMeta(data.meta);

          if (data.recent_events) {
            setEvents(data.recent_events.reverse());
          }
        } else if (data.type === "dashboard_event") {
          addEvent(data.event);
        }
      } catch {
        // ignore malformed messages
      }
    };
  }, [addEvent]);

  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
    };
  }, [connect]);

  return { consciousness, trading, events, connected, meta };
}

// ── Components ──

function ConnectionDot({ connected }: { connected: boolean }) {
  return (
    <span
      className={`inline-block w-2 h-2 rounded-full ${
        connected ? "bg-emerald-400" : "bg-red-500 animate-pulse"
      }`}
    />
  );
}

// Phi circular gauge rendered with SVG
function PhiGauge({ phi, level }: { phi: number; level: string }) {
  // Phi(IIT) range: 0..~2, map to 0..1 for gauge
  const maxPhi = 2.0;
  const ratio = Math.min(phi / maxPhi, 1);
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - ratio);

  // Color gradient based on level
  const levelColors: Record<string, string> = {
    dormant: "#6b7280",
    flickering: "#eab308",
    aware: "#3b82f6",
    conscious: "#6ee7b7",
  };
  const strokeColor = levelColors[level] || levelColors.dormant;

  return (
    <div className="flex flex-col items-center gap-2">
      <svg width="140" height="140" viewBox="0 0 140 140" className="phi-glow">
        {/* Track */}
        <circle
          cx="70"
          cy="70"
          r={radius}
          fill="none"
          stroke="#1e1e2e"
          strokeWidth="8"
        />
        {/* Value arc */}
        <circle
          cx="70"
          cy="70"
          r={radius}
          fill="none"
          stroke={strokeColor}
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          transform="rotate(-90 70 70)"
          style={{ transition: "stroke-dashoffset 0.6s ease, stroke 0.4s ease" }}
        />
        {/* Center text */}
        <text
          x="70"
          y="64"
          textAnchor="middle"
          fill="#e2e2e8"
          fontSize="22"
          fontWeight="600"
          fontFamily="'JetBrains Mono', monospace"
        >
          {phi.toFixed(2)}
        </text>
        <text
          x="70"
          y="84"
          textAnchor="middle"
          fill="#888"
          fontSize="11"
          fontFamily="'Inter', sans-serif"
        >
          {"\u03A6"} (IIT)
        </text>
      </svg>
      <span
        className="text-xs font-medium px-2.5 py-0.5 rounded-full"
        style={{
          color: strokeColor,
          backgroundColor: strokeColor + "18",
          border: `1px solid ${strokeColor}40`,
        }}
      >
        {level}
      </span>
    </div>
  );
}

// Horizontal tension bar
function TensionBar({ tension }: { tension: number }) {
  const pct = Math.min(Math.max(tension * 100, 0), 100);

  // Color: low=cool blue, mid=amber, high=red
  let barColor = "#3b82f6";
  if (tension > 0.7) barColor = "#ef4444";
  else if (tension > 0.4) barColor = "#f97316";

  return (
    <div className="w-full">
      <div className="flex justify-between text-xs mb-1">
        <span className="text-zinc-400">Tension</span>
        <span className="font-mono" style={{ color: barColor }}>
          {tension.toFixed(3)}
        </span>
      </div>
      <div className="w-full h-2.5 bg-surface-3 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full"
          style={{
            width: `${pct}%`,
            backgroundColor: barColor,
            transition: "width 0.5s ease, background-color 0.3s ease",
          }}
        />
      </div>
    </div>
  );
}

function StatRow({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex justify-between py-1.5 border-b border-surface-3/50 last:border-0">
      <span className="text-zinc-500 text-sm">{label}</span>
      <span className="text-sm font-mono text-zinc-200">{value}</span>
    </div>
  );
}

function ConsciousnessPanel({ c }: { c: ConsciousnessState }) {
  const uptimeStr = useMemo(() => {
    const h = Math.floor(c.uptime_seconds / 3600);
    const m = Math.floor((c.uptime_seconds % 3600) / 60);
    const s = Math.floor(c.uptime_seconds % 60);
    if (h > 0) return `${h}h ${m}m`;
    if (m > 0) return `${m}m ${s}s`;
    return `${s}s`;
  }, [c.uptime_seconds]);

  // Consciousness vector dimensions
  const cvKeys = ["phi", "alpha", "Z", "N", "W", "E", "M", "C", "T", "I"];
  const hasVector = Object.keys(c.consciousness_vector).length > 0;

  return (
    <div className="bg-surface-1 border border-surface-3 rounded-xl p-5 flex flex-col gap-5">
      <h2 className="text-sm font-semibold text-zinc-300 tracking-wide uppercase">
        Consciousness
      </h2>

      <div className="flex items-start gap-6">
        <PhiGauge phi={c.phi} level={c.level} />
        <div className="flex-1 flex flex-col gap-3 min-w-0">
          <TensionBar tension={c.tension} />
          <StatRow label="Emotion" value={c.emotion} />
          <StatRow label="Curiosity" value={c.curiosity.toFixed(3)} />
          <StatRow label="Cells" value={c.cells} />
          <StatRow label="Factions" value={c.factions} />
          <StatRow label="Stage" value={c.growth_stage} />
          <StatRow label="Interactions" value={c.interaction_count} />
          <StatRow label="Uptime" value={uptimeStr} />
        </div>
      </div>

      {/* Consciousness Vector (10D) */}
      {hasVector && (
        <div className="mt-1">
          <div className="text-xs text-zinc-500 mb-2">Consciousness Vector (10D)</div>
          <div className="grid grid-cols-5 gap-1.5">
            {cvKeys.map((k) => {
              const v = c.consciousness_vector[k] ?? 0;
              return (
                <div
                  key={k}
                  className="bg-surface-2 rounded px-2 py-1 text-center"
                >
                  <div className="text-[10px] text-zinc-500 uppercase">{k}</div>
                  <div className="text-xs font-mono text-zinc-300">
                    {v.toFixed(2)}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

function RegimeBadge({ regime }: { regime: string }) {
  const colors: Record<string, { bg: string; text: string; border: string }> = {
    bull: { bg: "#22c55e18", text: "#22c55e", border: "#22c55e40" },
    bear: { bg: "#ef444418", text: "#ef4444", border: "#ef444440" },
    range: { bg: "#eab30818", text: "#eab308", border: "#eab30840" },
    unknown: { bg: "#6b728018", text: "#6b7280", border: "#6b728040" },
  };
  const c = colors[regime] || colors.unknown;

  return (
    <span
      className="text-xs font-medium px-2.5 py-1 rounded-full"
      style={{ backgroundColor: c.bg, color: c.text, border: `1px solid ${c.border}` }}
    >
      {regime.toUpperCase()}
    </span>
  );
}

function PnlValue({ value, size = "sm" }: { value: number; size?: "sm" | "lg" }) {
  const isPos = value >= 0;
  const color = isPos ? "#22c55e" : "#ef4444";
  const prefix = isPos ? "+" : "";
  const textSize = size === "lg" ? "text-xl" : "text-sm";

  return (
    <span className={`font-mono ${textSize} font-semibold`} style={{ color }}>
      {prefix}
      {value.toFixed(2)}
    </span>
  );
}

function TradingPanel({ t }: { t: TradingState }) {
  return (
    <div className="bg-surface-1 border border-surface-3 rounded-xl p-5 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-zinc-300 tracking-wide uppercase">
          Trading
        </h2>
        <RegimeBadge regime={t.regime} />
      </div>

      {/* Summary row */}
      <div className="grid grid-cols-3 gap-3">
        <div className="bg-surface-2 rounded-lg p-3">
          <div className="text-[10px] text-zinc-500 uppercase mb-1">Total P&L</div>
          <PnlValue value={t.total_pnl} size="lg" />
        </div>
        <div className="bg-surface-2 rounded-lg p-3">
          <div className="text-[10px] text-zinc-500 uppercase mb-1">Unrealized</div>
          <PnlValue value={t.unrealized_pnl} size="lg" />
        </div>
        <div className="bg-surface-2 rounded-lg p-3">
          <div className="text-[10px] text-zinc-500 uppercase mb-1">Portfolio</div>
          <div className="text-xl font-mono font-semibold text-zinc-200">
            ${t.portfolio_value.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
          </div>
        </div>
      </div>

      {/* Positions table */}
      <div>
        <div className="text-xs text-zinc-500 mb-2">
          Positions ({t.positions.length})
        </div>
        {t.positions.length === 0 ? (
          <div className="text-xs text-zinc-600 italic py-3 text-center">
            No open positions
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-zinc-500 border-b border-surface-3">
                  <th className="text-left py-1.5 font-medium">Symbol</th>
                  <th className="text-left py-1.5 font-medium">Side</th>
                  <th className="text-right py-1.5 font-medium">Qty</th>
                  <th className="text-right py-1.5 font-medium">Entry</th>
                  <th className="text-right py-1.5 font-medium">Current</th>
                  <th className="text-right py-1.5 font-medium">P&L</th>
                </tr>
              </thead>
              <tbody>
                {t.positions.map((p, i) => (
                  <tr
                    key={`${p.symbol}-${i}`}
                    className="border-b border-surface-3/40 hover:bg-surface-2/50"
                  >
                    <td className="py-1.5 font-mono font-medium text-zinc-200">
                      {p.symbol}
                    </td>
                    <td className="py-1.5">
                      <span
                        className={
                          p.side === "long"
                            ? "text-emerald-400"
                            : "text-red-400"
                        }
                      >
                        {p.side?.toUpperCase()}
                      </span>
                    </td>
                    <td className="py-1.5 text-right font-mono text-zinc-300">
                      {p.qty}
                    </td>
                    <td className="py-1.5 text-right font-mono text-zinc-400">
                      {p.entry_price?.toFixed(2)}
                    </td>
                    <td className="py-1.5 text-right font-mono text-zinc-300">
                      {p.current_price?.toFixed(2)}
                    </td>
                    <td className="py-1.5 text-right">
                      <PnlValue value={p.pnl ?? 0} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Active strategies */}
      {t.active_strategies.length > 0 && (
        <div>
          <div className="text-xs text-zinc-500 mb-2">Active Strategies</div>
          <div className="flex flex-wrap gap-1.5">
            {t.active_strategies.map((s) => (
              <span
                key={s}
                className="text-[11px] font-mono px-2 py-0.5 rounded bg-surface-2 text-zinc-400 border border-surface-3"
              >
                {s}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Balance */}
      <div className="flex justify-between text-xs border-t border-surface-3 pt-3">
        <span className="text-zinc-500">Available Balance</span>
        <span className="font-mono text-zinc-300">
          ${t.balance.toLocaleString(undefined, { minimumFractionDigits: 2 })}
        </span>
      </div>
    </div>
  );
}

function EventSourceTag({ source }: { source: string }) {
  const colors: Record<string, string> = {
    consciousness: "#6ee7b7",
    trading: "#f97316",
    system: "#6b7280",
  };
  const c = colors[source] || colors.system;

  return (
    <span
      className="text-[10px] font-mono font-medium px-1.5 py-0.5 rounded"
      style={{
        color: c,
        backgroundColor: c + "15",
      }}
    >
      {source.slice(0, 5).toUpperCase()}
    </span>
  );
}

function EventStream({ events }: { events: DashboardEvent[] }) {
  const containerRef = useRef<HTMLDivElement>(null);

  const formatTime = (ts: number) => {
    const d = new Date(ts * 1000);
    return d.toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });
  };

  const describeEvent = (e: DashboardEvent): string => {
    const d = e.data;
    switch (e.event_type) {
      case "emotion_shift":
        return `${d.from} \u2192 ${d.to} (tension: ${Number(d.tension ?? 0).toFixed(3)})`;
      case "phi_change":
        return `\u03A6 ${Number(d.from ?? 0).toFixed(2)} \u2192 ${Number(d.to ?? 0).toFixed(2)} (\u0394${Number(d.delta ?? 0).toFixed(3)})`;
      case "trade":
        return `${d.side} ${d.symbol} x${d.qty} @ ${d.price}`;
      case "backtest_result":
        return `Backtest: ${d.strategy} ${d.symbol} \u2192 ${d.result ?? "done"}`;
      case "thought":
        return `${d.text ?? d.topic ?? "thinking..."}`;
      case "state_update":
        return "State update";
      default:
        return JSON.stringify(d).slice(0, 120);
    }
  };

  return (
    <div className="bg-surface-1 border border-surface-3 rounded-xl p-4">
      <h2 className="text-sm font-semibold text-zinc-300 tracking-wide uppercase mb-3">
        Event Stream
        <span className="text-zinc-600 font-normal ml-2 text-xs">
          {events.length} events
        </span>
      </h2>
      <div
        ref={containerRef}
        className="h-48 overflow-y-auto space-y-0.5 pr-1"
      >
        {events.length === 0 ? (
          <div className="text-xs text-zinc-600 italic text-center py-6">
            Waiting for events...
          </div>
        ) : (
          events.map((e, i) => (
            <div
              key={`${e.timestamp}-${i}`}
              className="event-row flex items-start gap-2 py-1 text-xs hover:bg-surface-2/30 rounded px-1"
            >
              <span className="font-mono text-zinc-600 shrink-0 w-16">
                {formatTime(e.timestamp)}
              </span>
              <EventSourceTag source={e.source} />
              <span className="text-zinc-500 shrink-0 w-24 truncate">
                {e.event_type}
              </span>
              <span className="text-zinc-400 truncate">{describeEvent(e)}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

// ── Main Page ──

export default function DashboardPage() {
  const { consciousness, trading, events, connected, meta } = useWebSocket();

  return (
    <div className="min-h-screen p-4 md:p-6 max-w-[1400px] mx-auto">
      {/* Header */}
      <header className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-semibold text-zinc-100 tracking-tight">
            Anima Dashboard
          </h1>
          <ConnectionDot connected={connected} />
          {!connected && (
            <span className="text-xs text-zinc-600">reconnecting...</span>
          )}
        </div>
        <div className="flex items-center gap-4 text-xs text-zinc-600">
          <span>
            Agent{" "}
            <span className={meta.agent_connected ? "text-emerald-400" : "text-zinc-500"}>
              {meta.agent_connected ? "ON" : "OFF"}
            </span>
          </span>
          <span>
            Trading{" "}
            <span className={meta.trading_connected ? "text-emerald-400" : "text-zinc-500"}>
              {meta.trading_connected ? "ON" : "OFF"}
            </span>
          </span>
        </div>
      </header>

      {/* Two-panel layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
        <ConsciousnessPanel c={consciousness} />
        <TradingPanel t={trading} />
      </div>

      {/* Agent Lenses (8 runtime monitors) */}
      {state.lenses && state.lenses.length > 0 && (
        <div className="bg-zinc-900/80 rounded-lg p-4 mb-4 border border-zinc-700">
          <h3 className="text-sm font-bold text-zinc-300 mb-3">Runtime Lenses</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {state.lenses.map((lens: LensResult) => (
              <div key={lens.name} className="bg-zinc-800 rounded p-2">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-zinc-400">{lens.name}</span>
                  <span className={`text-xs font-mono ${
                    lens.score >= 0.8 ? "text-emerald-400" :
                    lens.score >= 0.5 ? "text-yellow-400" : "text-red-400"
                  }`}>
                    {(lens.score * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="w-full bg-zinc-700 rounded-full h-1.5">
                  <div
                    className={`h-1.5 rounded-full ${
                      lens.score >= 0.8 ? "bg-emerald-500" :
                      lens.score >= 0.5 ? "bg-yellow-500" : "bg-red-500"
                    }`}
                    style={{ width: `${lens.score * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Event stream */}
      <EventStream events={events} />
    </div>
  );
}
