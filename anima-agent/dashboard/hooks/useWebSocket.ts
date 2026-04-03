"use client";

import { useEffect, useRef, useState, useCallback } from "react";

// ═══════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════

const WS_URL = "ws://localhost:8770";
const MAX_EVENTS = 100;
const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 30000;

// ═══════════════════════════════════════════════════════════
// Interfaces
// ═══════════════════════════════════════════════════════════

export interface ConsciousnessState {
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

export interface Position {
  symbol: string;
  side: string;
  qty: number;
  entry_price: number;
  current_price: number;
  pnl: number;
  pnl_pct: number;
}

export interface TradingState {
  positions: Position[];
  total_pnl: number;
  unrealized_pnl: number;
  regime: string;
  active_strategies: string[];
  balance: number;
  last_trade: Record<string, unknown> | null;
  portfolio_value: number;
}

export interface DashboardEvent {
  source: string;
  event_type: string;
  data: Record<string, unknown>;
  timestamp: number;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  timestamp: number;
  meta?: { tension: number; emotion: string; phi: number };
}

// ═══════════════════════════════════════════════════════════
// Defaults
// ═══════════════════════════════════════════════════════════

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
// Hook: useWebSocket
// ═══════════════════════════════════════════════════════════

export function useWebSocket() {
  const [consciousness, setConsciousness] =
    useState<ConsciousnessState>(DEFAULT_CONSCIOUSNESS);
  const [trading, setTrading] = useState<TradingState>(DEFAULT_TRADING);
  const [events, setEvents] = useState<DashboardEvent[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
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
      // Add user message to local state immediately
      const userMsg: ChatMessage = {
        id: `user-${Date.now()}-${Math.random().toString(36).slice(2)}`,
        role: "user",
        text,
        timestamp: Date.now(),
      };
      setMessages((prev) => [...prev, userMsg]);
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
        if (data.type === "chat_response") {
          const assistantMsg: ChatMessage = {
            id: `assistant-${Date.now()}-${Math.random().toString(36).slice(2)}`,
            role: "assistant",
            text: data.text ?? "",
            timestamp: Date.now(),
            meta: data.meta,
          };
          setMessages((prev) => [...prev, assistantMsg]);
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

  return {
    consciousness,
    trading,
    events,
    messages,
    connected,
    meta,
    sendMessage,
  };
}
