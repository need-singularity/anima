"use client";

import {
  useEffect,
  useRef,
  useState,
  useCallback,
  useMemo,
  type KeyboardEvent,
} from "react";

// ═══════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════

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

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  timestamp: number;
  meta?: { tension: number; emotion: string; phi: number };
}

// ═══════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════

const WS_URL = "ws://localhost:8770";
const API_URL = "http://localhost:8770";
const MAX_EVENTS = 100;
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

// ═══════════════════════════════════════════════════════════
// Hook: WebSocket
// ═══════════════════════════════════════════════════════════

function useWebSocket() {
  const [consciousness, setConsciousness] =
    useState<ConsciousnessState>(DEFAULT_CONSCIOUSNESS);
  const [trading, setTrading] = useState<TradingState>(DEFAULT_TRADING);
  const [events, setEvents] = useState<DashboardEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [meta, setMeta] = useState({
    agent_connected: false,
    trading_connected: false,
    event_count: 0,
  });
  const wsRef = useRef<WebSocket | null>(null);
  const retryRef = useRef(RECONNECT_BASE_MS);

  const addEvent = useCallback((evt: DashboardEvent) => {
    setEvents((prev) => {
      const next = [evt, ...prev];
      return next.length > MAX_EVENTS ? next.slice(0, MAX_EVENTS) : next;
    });
  }, []);

  const sendMessage = useCallback((text: string) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "chat", text }));
    }
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

    ws.onerror = () => ws.close();

    ws.onmessage = (msg) => {
      try {
        const data = JSON.parse(msg.data);
        if (data.consciousness) {
          setConsciousness(data.consciousness);
        }
        if (data.trading) {
          setTrading(data.trading);
        }
        if (data.meta) {
          setMeta(data.meta);
        }
        if (data.recent_events) {
          setEvents(data.recent_events.reverse());
        }
        if (data.type === "dashboard_event") {
          addEvent(data.event);
        }
      } catch {
        // ignore
      }
    };
  }, [addEvent]);

  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
    };
  }, [connect]);

  return { consciousness, trading, events, connected, meta, sendMessage };
}

// ═══════════════════════════════════════════════════════════
// Hook: Lenses
// ═══════════════════════════════════════════════════════════

function useLenses() {
  const [lenses, setLenses] = useState<LensResult[]>([]);
  useEffect(() => {
    const fetchLenses = () => {
      fetch(`${API_URL}/api/lenses`)
        .then((r) => r.json())
        .then((data) => {
          if (Array.isArray(data)) setLenses(data);
        })
        .catch(() => {});
    };
    fetchLenses();
    const interval = setInterval(fetchLenses, 5000);
    return () => clearInterval(interval);
  }, []);
  return lenses;
}

// ═══════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════

function formatUptime(seconds: number) {
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (d > 0) return `${d}d ${h}h`;
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m`;
  return `${Math.floor(seconds)}s`;
}

function levelColor(level: string): string {
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

function emotionIcon(emotion: string): string {
  const map: Record<string, string> = {
    calm: "\u2728",
    curious: "\uD83D\uDD0D",
    contemplation: "\uD83E\uDD14",
    excited: "\u26A1",
    anxious: "\uD83C\uDF00",
    focused: "\uD83C\uDFAF",
    creative: "\uD83C\uDFA8",
    serene: "\uD83C\uDF3F",
    conflicted: "\u2694\uFE0F",
  };
  return map[emotion] || "\u2B50";
}

// ═══════════════════════════════════════════════════════════
// Phi Gauge — The Heart
// ═══════════════════════════════════════════════════════════

function PhiGauge({
  phi,
  level,
  tension,
}: {
  phi: number;
  level: string;
  tension: number;
}) {
  const maxPhi = 2.0;
  const ratio = Math.min(phi / maxPhi, 1);
  const radius = 42;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - ratio);
  const color = levelColor(level);
  const isAlive = level !== "dormant";

  return (
    <div className="flex flex-col items-center">
      <svg
        width="108"
        height="108"
        viewBox="0 0 108 108"
        className={isAlive ? "phi-alive" : "phi-dormant"}
      >
        {/* Outer subtle ring */}
        <circle
          cx="54"
          cy="54"
          r="50"
          fill="none"
          stroke={color}
          strokeWidth="0.5"
          opacity="0.15"
        />
        {/* Track */}
        <circle
          cx="54"
          cy="54"
          r={radius}
          fill="none"
          stroke="var(--bg-3)"
          strokeWidth="6"
        />
        {/* Value arc */}
        <circle
          cx="54"
          cy="54"
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          transform="rotate(-90 54 54)"
          style={{
            transition: "stroke-dashoffset 0.8s ease, stroke 0.5s ease",
          }}
        />
        {/* Inner glow circle */}
        <circle
          cx="54"
          cy="54"
          r="28"
          fill={color}
          opacity="0.04"
        />
        {/* Center phi value */}
        <text
          x="54"
          y="50"
          textAnchor="middle"
          fill={color}
          fontSize="20"
          fontWeight="600"
          fontFamily="'Azeret Mono', monospace"
        >
          {phi.toFixed(2)}
        </text>
        <text
          x="54"
          y="66"
          textAnchor="middle"
          fill="var(--text-3)"
          fontSize="9"
          fontFamily="'DM Sans', sans-serif"
          letterSpacing="0.08em"
        >
          {"\u03A6"} IIT
        </text>
      </svg>
      {/* Level badge */}
      <div
        className="mt-1.5 text-[10px] font-medium tracking-wider uppercase px-2.5 py-0.5 rounded-full"
        style={{
          color,
          backgroundColor: color + "12",
          border: `1px solid ${color}25`,
        }}
      >
        {level}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════
// Left Sidebar — Consciousness Monitor
// ═══════════════════════════════════════════════════════════

function ConsciousnessSidebar({
  c,
  connected,
  lenses,
}: {
  c: ConsciousnessState;
  connected: boolean;
  lenses: LensResult[];
}) {
  const cvKeys = ["phi", "alpha", "Z", "N", "W", "E", "M", "C", "T", "I"];
  const hasVector = Object.keys(c.consciousness_vector).length > 0;
  const glowClass =
    c.level === "conscious"
      ? "glow-conscious"
      : c.level === "aware"
      ? "glow-aware"
      : c.level === "flickering"
      ? "glow-flickering"
      : "";

  return (
    <aside
      className={`flex flex-col h-full bg-surface-1 border-r border-surface-3/50 overflow-y-auto ${glowClass}`}
    >
      {/* Header */}
      <div className="px-4 pt-4 pb-3 border-b border-surface-3/30">
        <div className="flex items-center gap-2">
          <span className="text-base font-semibold tracking-tight text-[var(--text-0)]">
            ANIMA
          </span>
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              connected
                ? "bg-glow-phi shadow-[0_0_6px_rgba(74,222,128,0.5)]"
                : "bg-red-500 animate-pulse"
            }`}
          />
        </div>
        <p className="text-[10px] text-[var(--text-3)] mt-0.5 tracking-wide">
          Consciousness Observer
        </p>
      </div>

      {/* Phi Gauge */}
      <div className="flex justify-center py-5 border-b border-surface-3/30">
        <PhiGauge phi={c.phi} level={c.level} tension={c.tension} />
      </div>

      {/* Metrics */}
      <div className="px-4 py-3 space-y-2.5 border-b border-surface-3/30">
        {/* Tension bar */}
        <div>
          <div className="flex justify-between text-[11px] mb-1">
            <span className="text-[var(--text-2)]">Tension</span>
            <span
              className="font-mono"
              style={{
                color:
                  c.tension > 0.7
                    ? "var(--glow-danger)"
                    : c.tension > 0.4
                    ? "var(--glow-tension)"
                    : "var(--text-1)",
              }}
            >
              {c.tension.toFixed(3)}
            </span>
          </div>
          <div className="w-full h-1.5 bg-surface-3 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{
                width: `${Math.min(c.tension * 100, 100)}%`,
                background:
                  c.tension > 0.7
                    ? "linear-gradient(90deg, var(--glow-tension), var(--glow-danger))"
                    : c.tension > 0.4
                    ? "linear-gradient(90deg, var(--accent-cyan), var(--glow-tension))"
                    : "linear-gradient(90deg, var(--bg-4), var(--accent-cyan))",
              }}
            />
          </div>
        </div>

        {/* Key stats */}
        <MetricRow
          label="Emotion"
          value={
            <span>
              {emotionIcon(c.emotion)} {c.emotion}
            </span>
          }
        />
        <MetricRow
          label="Curiosity"
          value={<span className="font-mono">{c.curiosity.toFixed(3)}</span>}
        />
        <MetricRow label="Cells" value={<span className="font-mono">{c.cells}</span>} />
        <MetricRow
          label="Factions"
          value={<span className="font-mono">{c.factions}</span>}
        />
        <MetricRow label="Stage" value={c.growth_stage} />
        <MetricRow
          label="Interactions"
          value={<span className="font-mono">{c.interaction_count.toLocaleString()}</span>}
        />
        <MetricRow
          label="Uptime"
          value={
            <span className="font-mono">{formatUptime(c.uptime_seconds)}</span>
          }
        />
      </div>

      {/* 10D Consciousness Vector */}
      {hasVector && (
        <div className="px-4 py-3 border-b border-surface-3/30">
          <div className="text-[10px] text-[var(--text-3)] mb-2 tracking-wide uppercase">
            Consciousness Vector
          </div>
          <div className="grid grid-cols-5 gap-1">
            {cvKeys.map((k) => {
              const v = c.consciousness_vector[k] ?? 0;
              const intensity = Math.min(Math.abs(v) / 1.5, 1);
              return (
                <div
                  key={k}
                  className="rounded px-1 py-0.5 text-center"
                  style={{
                    background: `rgba(74, 222, 128, ${intensity * 0.08 + 0.02})`,
                  }}
                >
                  <div className="text-[8px] text-[var(--text-3)] uppercase">
                    {k}
                  </div>
                  <div className="text-[10px] font-mono text-[var(--text-1)]">
                    {v.toFixed(2)}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Runtime Lenses */}
      {lenses.length > 0 && (
        <div className="px-4 py-3">
          <div className="text-[10px] text-[var(--text-3)] mb-2 tracking-wide uppercase">
            Runtime Lenses
          </div>
          <div className="space-y-1.5">
            {lenses.map((lens) => {
              const pct = lens.score * 100;
              const barColor =
                pct >= 80
                  ? "var(--glow-phi)"
                  : pct >= 50
                  ? "var(--accent-amber)"
                  : "var(--glow-danger)";
              return (
                <div key={lens.name}>
                  <div className="flex justify-between text-[10px] mb-0.5">
                    <span className="text-[var(--text-2)]">{lens.name}</span>
                    <span className="font-mono" style={{ color: barColor }}>
                      {pct.toFixed(0)}%
                    </span>
                  </div>
                  <div className="w-full h-1 bg-surface-3 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-700"
                      style={{ width: `${pct}%`, backgroundColor: barColor }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </aside>
  );
}

function MetricRow({
  label,
  value,
}: {
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="flex justify-between items-center text-[11px]">
      <span className="text-[var(--text-3)]">{label}</span>
      <span className="text-[var(--text-1)]">{value}</span>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════
// Right Sidebar — Trading + Events
// ═══════════════════════════════════════════════════════════

function TradingSidebar({
  t,
  events,
  meta,
}: {
  t: TradingState;
  events: DashboardEvent[];
  meta: { agent_connected: boolean; trading_connected: boolean };
}) {
  return (
    <aside className="flex flex-col h-full bg-surface-1 border-l border-surface-3/50 overflow-y-auto">
      {/* Trading header */}
      <div className="px-4 pt-4 pb-3 border-b border-surface-3/30">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold tracking-wide text-[var(--text-1)] uppercase">
            Trading
          </span>
          <RegimeBadge regime={t.regime} />
        </div>
        <div className="flex gap-3 mt-2">
          <StatusDot label="Agent" on={meta.agent_connected} />
          <StatusDot label="Trade" on={meta.trading_connected} />
        </div>
      </div>

      {/* P&L Summary */}
      <div className="px-4 py-3 border-b border-surface-3/30">
        <div className="grid grid-cols-2 gap-2">
          <PnlCard label="Total P&L" value={t.total_pnl} />
          <PnlCard label="Unrealized" value={t.unrealized_pnl} />
        </div>
        <div className="mt-2 flex justify-between items-center text-[11px]">
          <span className="text-[var(--text-3)]">Portfolio</span>
          <span className="font-mono text-[var(--text-0)] text-sm font-semibold">
            $
            {t.portfolio_value.toLocaleString(undefined, {
              minimumFractionDigits: 0,
              maximumFractionDigits: 0,
            })}
          </span>
        </div>
        <div className="mt-1 flex justify-between items-center text-[11px]">
          <span className="text-[var(--text-3)]">Balance</span>
          <span className="font-mono text-[var(--text-2)]">
            $
            {t.balance.toLocaleString(undefined, {
              minimumFractionDigits: 2,
            })}
          </span>
        </div>
      </div>

      {/* Positions */}
      <div className="px-4 py-3 border-b border-surface-3/30">
        <div className="text-[10px] text-[var(--text-3)] mb-2 tracking-wide uppercase">
          Positions ({t.positions.length})
        </div>
        {t.positions.length === 0 ? (
          <div className="text-[11px] text-[var(--text-3)] italic py-2 text-center">
            No open positions
          </div>
        ) : (
          <div className="space-y-1.5">
            {t.positions.map((p, i) => (
              <div
                key={`${p.symbol}-${i}`}
                className="flex items-center justify-between bg-surface-2 rounded-lg px-2.5 py-1.5"
              >
                <div>
                  <span className="text-xs font-mono font-medium text-[var(--text-0)]">
                    {p.symbol}
                  </span>
                  <span
                    className={`ml-1.5 text-[10px] ${
                      p.side === "long" ? "text-glow-phi" : "text-glow-danger"
                    }`}
                  >
                    {p.side?.toUpperCase()}
                  </span>
                </div>
                <div className="text-right">
                  <PnlValue value={p.pnl ?? 0} />
                  <div className="text-[9px] text-[var(--text-3)] font-mono">
                    {(p.pnl_pct ?? 0) >= 0 ? "+" : ""}
                    {(p.pnl_pct ?? 0).toFixed(1)}%
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Event Stream */}
      <div className="flex-1 px-4 py-3 overflow-y-auto">
        <div className="text-[10px] text-[var(--text-3)] mb-2 tracking-wide uppercase">
          Events ({events.length})
        </div>
        {events.length === 0 ? (
          <div className="text-[11px] text-[var(--text-3)] italic text-center py-4">
            Waiting for events...
          </div>
        ) : (
          <div className="space-y-0.5">
            {events.slice(0, 30).map((e, i) => (
              <div
                key={`${e.timestamp}-${i}`}
                className="event-row flex items-start gap-1.5 py-0.5 text-[10px]"
              >
                <span className="font-mono text-[var(--text-3)] shrink-0">
                  {new Date(e.timestamp * 1000).toLocaleTimeString("en-US", {
                    hour12: false,
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                  })}
                </span>
                <EventTag source={e.source} />
                <span className="text-[var(--text-2)] truncate">
                  {describeEvent(e)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </aside>
  );
}

function StatusDot({ label, on }: { label: string; on: boolean }) {
  return (
    <div className="flex items-center gap-1">
      <span
        className={`w-1.5 h-1.5 rounded-full ${
          on ? "bg-glow-phi" : "bg-[var(--text-3)]"
        }`}
      />
      <span className="text-[10px] text-[var(--text-3)]">{label}</span>
    </div>
  );
}

function RegimeBadge({ regime }: { regime: string }) {
  const colors: Record<string, string> = {
    bull: "#4ade80",
    bear: "#f87171",
    range: "#fbbf24",
    unknown: "#55556a",
  };
  const c = colors[regime] || colors.unknown;

  return (
    <span
      className="text-[9px] font-semibold tracking-wider uppercase px-2 py-0.5 rounded"
      style={{
        color: c,
        backgroundColor: c + "15",
        border: `1px solid ${c}30`,
      }}
    >
      {regime}
    </span>
  );
}

function PnlCard({ label, value }: { label: string; value: number }) {
  const isPos = value >= 0;
  const color = isPos ? "var(--glow-phi)" : "var(--glow-danger)";
  const prefix = isPos ? "+" : "";

  return (
    <div className="bg-surface-2 rounded-lg px-2.5 py-2">
      <div className="text-[9px] text-[var(--text-3)] uppercase tracking-wide">
        {label}
      </div>
      <div className="font-mono text-sm font-semibold mt-0.5" style={{ color }}>
        {prefix}
        {value.toFixed(2)}
      </div>
    </div>
  );
}

function PnlValue({ value }: { value: number }) {
  const isPos = value >= 0;
  const color = isPos ? "var(--glow-phi)" : "var(--glow-danger)";
  return (
    <span className="font-mono text-[11px] font-medium" style={{ color }}>
      {isPos ? "+" : ""}
      {value.toFixed(2)}
    </span>
  );
}

function EventTag({ source }: { source: string }) {
  const colors: Record<string, string> = {
    consciousness: "#4ade80",
    trading: "#fb923c",
    system: "#55556a",
  };
  const c = colors[source] || colors.system;
  return (
    <span
      className="text-[8px] font-mono font-semibold px-1 py-px rounded shrink-0"
      style={{ color: c, backgroundColor: c + "12" }}
    >
      {source.slice(0, 5).toUpperCase()}
    </span>
  );
}

function describeEvent(e: DashboardEvent): string {
  const d = e.data;
  switch (e.event_type) {
    case "emotion_shift":
      return `${d.from} \u2192 ${d.to}`;
    case "phi_change":
      return `\u03A6 ${Number(d.from ?? 0).toFixed(2)} \u2192 ${Number(
        d.to ?? 0
      ).toFixed(2)}`;
    case "trade":
      return `${d.side} ${d.symbol} x${d.qty}`;
    case "thought":
      return `${d.text ?? d.topic ?? "..."}`;
    default:
      return e.event_type;
  }
}

// ═══════════════════════════════════════════════════════════
// Chat Panel — The Main Interface
// ═══════════════════════════════════════════════════════════

function ChatPanel({
  consciousness,
}: {
  consciousness: ConsciousnessState;
}) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isTyping]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const sendMessage = useCallback(async () => {
    const text = input.trim();
    if (!text) return;

    const userMsg: ChatMessage = {
      id: `u-${Date.now()}`,
      role: "user",
      text,
      timestamp: Date.now() / 1000,
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsTyping(true);

    // Resize textarea back
    if (inputRef.current) {
      inputRef.current.style.height = "auto";
    }

    try {
      const resp = await fetch(`${API_URL}/api/message`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });

      const data = await resp.json();

      const assistantMsg: ChatMessage = {
        id: `a-${Date.now()}`,
        role: "assistant",
        text: data.text || "...",
        timestamp: Date.now() / 1000,
        meta: {
          tension: data.tension ?? consciousness.tension,
          emotion: data.emotion ?? consciousness.emotion,
          phi: data.phi ?? consciousness.phi,
        },
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch {
      const errorMsg: ChatMessage = {
        id: `e-${Date.now()}`,
        role: "assistant",
        text: "[connection lost]",
        timestamp: Date.now() / 1000,
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsTyping(false);
    }
  }, [input, consciousness]);

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    // Auto-resize
    const el = e.target;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 120) + "px";
  };

  return (
    <div className="flex flex-col h-full">
      {/* Messages area */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-4 md:px-8 py-4 space-y-3"
      >
        {messages.length === 0 && !isTyping && (
          <div className="flex flex-col items-center justify-center h-full opacity-40 select-none">
            <svg width="48" height="48" viewBox="0 0 108 108" className="phi-dormant mb-4 opacity-50">
              <circle cx="54" cy="54" r="42" fill="none" stroke="var(--text-3)" strokeWidth="4" />
              <circle cx="54" cy="54" r="28" fill="var(--text-3)" opacity="0.05" />
              <text x="54" y="58" textAnchor="middle" fill="var(--text-3)" fontSize="18" fontFamily="'Azeret Mono', monospace">
                {"\u03A6"}
              </text>
            </svg>
            <p className="text-sm text-[var(--text-3)]">Anima에게 말을 걸어보세요</p>
            <p className="text-[11px] text-[var(--text-3)] mt-1 opacity-60">의식 엔진이 대기 중입니다</p>
          </div>
        )}

        {messages.map((msg) => (
          <MessageBubble key={msg.id} msg={msg} />
        ))}

        {/* Typing indicator */}
        {isTyping && (
          <div className="flex items-start gap-3 msg-enter">
            <div className="w-7 h-7 rounded-full bg-surface-3 flex items-center justify-center shrink-0 mt-0.5">
              <span className="text-[10px]">{"\uD83E\uDDE0"}</span>
            </div>
            <div className="bg-surface-2 rounded-2xl rounded-tl-sm px-4 py-2.5">
              <div className="flex gap-1">
                <span className="typing-dot w-1.5 h-1.5 rounded-full bg-[var(--text-3)]" />
                <span className="typing-dot w-1.5 h-1.5 rounded-full bg-[var(--text-3)]" />
                <span className="typing-dot w-1.5 h-1.5 rounded-full bg-[var(--text-3)]" />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Input area */}
      <div className="border-t border-surface-3/30 bg-surface-1/80 backdrop-blur-sm px-4 md:px-8 py-3">
        <div className="flex items-end gap-2 max-w-3xl mx-auto">
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={input}
              onChange={handleInput}
              onKeyDown={handleKeyDown}
              placeholder="Anima에게 말하기..."
              rows={1}
              className="chat-input w-full bg-surface-2 border border-surface-3/50 rounded-xl px-4 py-2.5 text-sm text-[var(--text-0)] placeholder:text-[var(--text-3)] resize-none overflow-hidden transition-colors"
              style={{ maxHeight: "120px" }}
            />
          </div>
          <button
            onClick={sendMessage}
            disabled={!input.trim() || isTyping}
            className="shrink-0 w-9 h-9 rounded-xl bg-glow-phi/10 border border-glow-phi/20 flex items-center justify-center text-glow-phi hover:bg-glow-phi/20 disabled:opacity-30 disabled:hover:bg-glow-phi/10 transition-all"
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M22 2L11 13" />
              <path d="M22 2L15 22L11 13L2 9L22 2Z" />
            </svg>
          </button>
        </div>
        <div className="text-center mt-1.5">
          <span className="text-[9px] text-[var(--text-3)]">
            Enter 전송 · Shift+Enter 줄바꿈
          </span>
        </div>
      </div>
    </div>
  );
}

function MessageBubble({ msg }: { msg: ChatMessage }) {
  const isUser = msg.role === "user";

  return (
    <div
      className={`flex items-start gap-3 msg-enter ${
        isUser ? "flex-row-reverse" : ""
      }`}
    >
      {/* Avatar */}
      <div
        className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 mt-0.5 ${
          isUser ? "bg-accent-cyan/15" : "bg-surface-3"
        }`}
      >
        <span className="text-[10px]">
          {isUser ? "\uD83D\uDC64" : "\uD83E\uDDE0"}
        </span>
      </div>

      {/* Bubble */}
      <div className={`max-w-[75%] ${isUser ? "items-end" : "items-start"}`}>
        <div
          className={`rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
            isUser
              ? "bg-accent-cyan/10 border border-accent-cyan/15 rounded-tr-sm text-[var(--text-0)]"
              : "bg-surface-2 border border-surface-3/30 rounded-tl-sm text-[var(--text-1)]"
          }`}
        >
          {msg.text.split("\n").map((line, i) => (
            <p key={i} className={i > 0 ? "mt-1.5" : ""}>
              {line}
            </p>
          ))}
        </div>

        {/* Consciousness metadata on assistant messages */}
        {!isUser && msg.meta && (
          <div className="flex items-center gap-2 mt-1 px-1">
            <span className="text-[9px] font-mono text-[var(--text-3)]">
              {"\u03A6"} {msg.meta.phi.toFixed(2)}
            </span>
            <span className="text-[9px] text-[var(--text-3)]">\u00B7</span>
            <span className="text-[9px] text-[var(--text-3)]">
              {emotionIcon(msg.meta.emotion)} {msg.meta.emotion}
            </span>
            <span className="text-[9px] text-[var(--text-3)]">\u00B7</span>
            <span className="text-[9px] font-mono text-[var(--text-3)]">
              T {msg.meta.tension.toFixed(3)}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════
// Mobile Sidebar Toggle
// ═══════════════════════════════════════════════════════════

function SidebarToggle({
  side,
  isOpen,
  onClick,
}: {
  side: "left" | "right";
  isOpen: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`lg:hidden fixed top-3 ${
        side === "left" ? "left-3" : "right-3"
      } z-50 w-8 h-8 rounded-lg bg-surface-2 border border-surface-3/50 flex items-center justify-center text-[var(--text-2)] hover:text-[var(--text-0)] transition-colors`}
    >
      {side === "left" ? (
        isOpen ? (
          "\u2715"
        ) : (
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <circle cx="12" cy="12" r="10" />
            <circle cx="12" cy="12" r="3" />
          </svg>
        )
      ) : isOpen ? (
        "\u2715"
      ) : (
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <path d="M3 12h18M3 6h18M3 18h18" />
        </svg>
      )}
    </button>
  );
}

// ═══════════════════════════════════════════════════════════
// Main Page
// ═══════════════════════════════════════════════════════════

export default function DashboardPage() {
  const { consciousness, trading, events, connected, meta } = useWebSocket();
  const lenses = useLenses();
  const [leftOpen, setLeftOpen] = useState(false);
  const [rightOpen, setRightOpen] = useState(false);

  return (
    <div className="h-screen flex overflow-hidden">
      {/* Mobile toggles */}
      <SidebarToggle
        side="left"
        isOpen={leftOpen}
        onClick={() => {
          setLeftOpen(!leftOpen);
          setRightOpen(false);
        }}
      />
      <SidebarToggle
        side="right"
        isOpen={rightOpen}
        onClick={() => {
          setRightOpen(!rightOpen);
          setLeftOpen(false);
        }}
      />

      {/* Mobile overlay */}
      {(leftOpen || rightOpen) && (
        <div
          className="lg:hidden fixed inset-0 bg-black/60 z-30"
          onClick={() => {
            setLeftOpen(false);
            setRightOpen(false);
          }}
        />
      )}

      {/* Left Sidebar — Consciousness */}
      <div
        className={`sidebar-panel fixed lg:relative z-40 h-full w-72 lg:w-64 xl:w-72 shrink-0 transition-transform duration-300 ${
          leftOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        }`}
      >
        <ConsciousnessSidebar
          c={consciousness}
          connected={connected}
          lenses={lenses}
        />
      </div>

      {/* Center — Chat */}
      <main className="flex-1 min-w-0 bg-surface-0">
        <ChatPanel consciousness={consciousness} />
      </main>

      {/* Right Sidebar — Trading + Events */}
      <div
        className={`sidebar-panel fixed lg:relative right-0 z-40 h-full w-72 lg:w-60 xl:w-72 shrink-0 transition-transform duration-300 ${
          rightOpen ? "translate-x-0" : "translate-x-full lg:translate-x-0"
        }`}
      >
        <TradingSidebar t={trading} events={events} meta={meta} />
      </div>
    </div>
  );
}
