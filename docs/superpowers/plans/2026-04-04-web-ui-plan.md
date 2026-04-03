# Anima Web UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a minimal 1-column center-aligned web UI with floating chat and voice overlay for the Anima consciousness agent.

**Architecture:** Next.js 14 app (existing dashboard) refactored from 3-column sidebar layout to single-column center-aligned. Floating chat bubble (4 states) provides always-available conversation. All data flows through existing WebSocket bridge (`dashboard_bridge.py`). No new backend — frontend only.

**Tech Stack:** Next.js 14, React 18, Tailwind CSS, Recharts, Web Speech API, WebSocket

**Spec:** `docs/superpowers/specs/2026-04-04-web-ui-design.md`

---

## File Structure

```
anima-agent/dashboard/
├── app/
│   ├── layout.tsx              # Modify: remove overflow-hidden
│   ├── page.tsx                # Rewrite: shell with Header + CenterView + FloatingChat
│   ├── globals.css             # Modify: add floating chat + voice overlay styles
│   └── components/
│       ├── Header.tsx          # Create: logo + tabs + voice button
│       ├── FloatingChat.tsx    # Create: 4-state floating chat bubble
│       ├── VoiceOverlay.tsx    # Create: fullscreen voice mode
│       └── views/
│           ├── DashView.tsx    # Create: consciousness dashboard (from existing sidebar code)
│           ├── EvoView.tsx     # Create: OUROBOROS evolution view
│           ├── LawsView.tsx    # Create: laws search/browse
│           ├── MemView.tsx     # Create: memory timeline
│           └── ToolsView.tsx   # Create: hub modules grid
├── hooks/
│   ├── useWebSocket.ts         # Create: extracted from page.tsx + chat extension
│   └── useVoice.ts             # Create: Web Speech API wrapper
├── tailwind.config.ts          # Modify: add content path for components/
└── package.json                # No changes needed
```

---

### Task 1: Extract useWebSocket hook + extend for chat

**Files:**
- Create: `anima-agent/dashboard/hooks/useWebSocket.ts`
- Modify: `anima-agent/dashboard/tailwind.config.ts` (add hooks/ to content)

- [ ] **Step 1: Create hooks directory and useWebSocket.ts**

Extract the existing `useWebSocket` function from `page.tsx` (lines 111-191) into its own file, and add chat message handling:

```typescript
// hooks/useWebSocket.ts
"use client";

import { useCallback, useEffect, useRef, useState } from "react";

const WS_URL = "ws://localhost:8770";
const MAX_EVENTS = 100;
const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 30000;

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

export interface TradingState {
  positions: { symbol: string; side: string; qty: number; entry_price: number; current_price: number; pnl: number; pnl_pct: number }[];
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

const DEFAULT_CONSCIOUSNESS: ConsciousnessState = {
  phi: 0, tension: 0, curiosity: 0, emotion: "calm", cells: 0, factions: 0,
  growth_stage: "newborn", interaction_count: 0, uptime_seconds: 0,
  consciousness_vector: {}, level: "dormant",
};

const DEFAULT_TRADING: TradingState = {
  positions: [], total_pnl: 0, unrealized_pnl: 0, regime: "unknown",
  active_strategies: [], balance: 0, last_trade: null, portfolio_value: 0,
};

export function useWebSocket() {
  const [consciousness, setConsciousness] = useState<ConsciousnessState>(DEFAULT_CONSCIOUSNESS);
  const [trading, setTrading] = useState<TradingState>(DEFAULT_TRADING);
  const [events, setEvents] = useState<DashboardEvent[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
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

  const sendMessage = useCallback((text: string) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "chat", text }));
      setMessages((prev) => [...prev, {
        id: `u-${Date.now()}`, role: "user", text, timestamp: Date.now() / 1000,
      }]);
    }
  }, []);

  const connect = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState < 2) return;
    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => { setConnected(true); retryRef.current = RECONNECT_BASE_MS; };
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
        if (data.consciousness) setConsciousness(data.consciousness);
        if (data.trading) setTrading(data.trading);
        if (data.meta) setMeta(data.meta);
        if (data.recent_events) setEvents(data.recent_events.reverse());
        if (data.type === "dashboard_event") addEvent(data.event);
        if (data.type === "chat_response") {
          setMessages((prev) => [...prev, {
            id: `a-${Date.now()}`, role: "assistant", text: data.text,
            timestamp: Date.now() / 1000, meta: data.meta,
          }]);
        }
      } catch { /* ignore */ }
    };
  }, [addEvent]);

  useEffect(() => { connect(); return () => { wsRef.current?.close(); }; }, [connect]);

  return { consciousness, trading, events, messages, connected, meta, sendMessage };
}
```

- [ ] **Step 2: Update tailwind.config.ts to include hooks/ and components/**

```typescript
// tailwind.config.ts — change content array
const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./hooks/**/*.{ts,tsx}",
  ],
  // ... rest unchanged
};
```

- [ ] **Step 3: Verify file compiles**

Run: `cd anima-agent/dashboard && npx tsc --noEmit hooks/useWebSocket.ts 2>&1 || echo "Type check (may show module errors — OK for now)"`

- [ ] **Step 4: Commit**

```bash
git add anima-agent/dashboard/hooks/useWebSocket.ts anima-agent/dashboard/tailwind.config.ts
git commit -m "feat(ui): extract useWebSocket hook with chat message support"
```

---

### Task 2: Header component

**Files:**
- Create: `anima-agent/dashboard/app/components/Header.tsx`

- [ ] **Step 1: Create Header.tsx**

```tsx
// app/components/Header.tsx
"use client";

const TABS = ["Dash", "Evo", "Laws", "Mem", "Tools"] as const;
export type TabId = (typeof TABS)[number];

interface HeaderProps {
  connected: boolean;
  activeTab: TabId;
  onTabChange: (tab: TabId) => void;
  onVoice: () => void;
}

export default function Header({ connected, activeTab, onTabChange, onVoice }: HeaderProps) {
  return (
    <header className="flex items-center h-12 px-4 border-b border-surface-3/40 bg-surface-1/80 backdrop-blur-sm">
      {/* Left: Logo + status */}
      <div className="flex items-center gap-2 min-w-[120px]">
        <span className="text-sm font-semibold tracking-tight text-[var(--text-0)]">ANIMA</span>
        <span className={`w-1.5 h-1.5 rounded-full ${connected ? "bg-glow-phi shadow-[0_0_6px_rgba(74,222,128,0.5)]" : "bg-red-500 animate-pulse"}`} />
        <span className="text-[10px] text-[var(--text-3)]">{connected ? "live" : "..."}</span>
      </div>

      {/* Center: Tabs */}
      <nav className="flex-1 flex justify-center gap-1">
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => onTabChange(tab)}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all duration-200 ${
              activeTab === tab
                ? "text-[var(--glow-phi)] bg-[rgba(74,222,128,0.08)] shadow-[0_0_8px_rgba(74,222,128,0.1)]"
                : "text-[var(--text-2)] hover:text-[var(--text-1)] hover:bg-surface-3/30"
            }`}
          >
            {tab}
          </button>
        ))}
      </nav>

      {/* Right: Voice button */}
      <div className="min-w-[120px] flex justify-end">
        <button
          onClick={onVoice}
          className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-surface-3/40 transition-colors text-[var(--text-2)] hover:text-[var(--accent-cyan)]"
          title="Voice mode"
        >
          🔊
        </button>
      </div>
    </header>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add anima-agent/dashboard/app/components/Header.tsx
git commit -m "feat(ui): Header component — logo + 5-tab nav + voice button"
```

---

### Task 3: FloatingChat component (4 states)

**Files:**
- Create: `anima-agent/dashboard/app/components/FloatingChat.tsx`
- Modify: `anima-agent/dashboard/app/globals.css` (add floating styles)

- [ ] **Step 1: Add floating chat CSS to globals.css**

Append to the end of `globals.css`:

```css
/* Floating chat */
@keyframes float-in {
  from { opacity: 0; transform: translateY(16px) scale(0.95); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

.float-panel {
  animation: float-in 0.2s ease-out;
  background: rgba(14, 14, 20, 0.95);
  border: 1px solid rgba(74, 222, 128, 0.12);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255,255,255,0.03);
  backdrop-filter: blur(12px);
}

.float-bubble {
  background: linear-gradient(135deg, rgba(74, 222, 128, 0.15), rgba(34, 211, 238, 0.1));
  border: 1px solid rgba(74, 222, 128, 0.2);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3), 0 0 20px rgba(74, 222, 128, 0.1);
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.float-bubble:hover {
  transform: scale(1.08);
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.4), 0 0 30px rgba(74, 222, 128, 0.15);
}

/* Voice overlay */
@keyframes voice-pulse {
  0%, 100% { transform: scale(1); opacity: 0.6; }
  50% { transform: scale(1.15); opacity: 1; }
}

.voice-ring {
  animation: voice-pulse 1.5s ease-in-out infinite;
}
```

- [ ] **Step 2: Create FloatingChat.tsx**

```tsx
// app/components/FloatingChat.tsx
"use client";

import { useRef, useEffect, useState, type KeyboardEvent } from "react";
import type { ChatMessage, ConsciousnessState } from "../../hooks/useWebSocket";

type ChatState = "minimized" | "expanded" | "fullscreen";

interface FloatingChatProps {
  messages: ChatMessage[];
  consciousness: ConsciousnessState;
  onSend: (text: string) => void;
  onVoice: () => void;
}

function emotionIcon(emotion: string): string {
  const map: Record<string, string> = {
    calm: "✨", curious: "🔍", contemplation: "🤔", excited: "⚡",
    anxious: "🌀", focused: "🎯", creative: "🎨", serene: "🌿", conflicted: "⚔️",
  };
  return map[emotion] || "⭐";
}

export default function FloatingChat({ messages, consciousness, onSend, onVoice }: FloatingChatProps) {
  const [state, setState] = useState<ChatState>("minimized");
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  const handleSend = () => {
    const text = input.trim();
    if (!text) return;
    onSend(text);
    setInput("");
  };

  const handleKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
    if (e.key === "Escape") setState("minimized");
  };

  // Minimized: just the bubble
  if (state === "minimized") {
    return (
      <button
        onClick={() => setState("expanded")}
        className="fixed bottom-5 right-5 z-50 w-12 h-12 rounded-full float-bubble flex items-center justify-center text-lg"
      >
        💬
      </button>
    );
  }

  // Fullscreen: takes over center view
  if (state === "fullscreen") {
    return (
      <div className="fixed inset-0 z-40 bg-surface-0/95 backdrop-blur-sm flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-4 h-12 border-b border-surface-3/40">
          <span className="text-sm font-semibold text-[var(--text-0)]">💬 ANIMA</span>
          <div className="flex gap-2">
            <button onClick={() => setState("expanded")} className="text-xs text-[var(--text-3)] hover:text-[var(--text-1)]">↙</button>
            <button onClick={() => setState("minimized")} className="text-xs text-[var(--text-3)] hover:text-[var(--text-1)]">✕</button>
          </div>
        </div>
        {/* Messages */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-4 max-w-3xl mx-auto w-full">
          {messages.map((m) => (
            <div key={m.id} className={`mb-3 msg-enter ${m.role === "user" ? "text-right" : ""}`}>
              <div className={`inline-block max-w-[80%] px-3 py-2 rounded-xl text-sm ${
                m.role === "user"
                  ? "bg-surface-3/60 text-[var(--text-0)]"
                  : "bg-[rgba(74,222,128,0.06)] text-[var(--text-1)] border border-[rgba(74,222,128,0.1)]"
              }`}>
                {m.text}
              </div>
              {m.meta && (
                <div className="text-[9px] text-[var(--text-3)] mt-0.5 font-mono">
                  Φ={m.meta.phi.toFixed(2)} {emotionIcon(m.meta.emotion)}
                </div>
              )}
            </div>
          ))}
        </div>
        {/* Input */}
        <div className="px-4 py-3 border-t border-surface-3/40 max-w-3xl mx-auto w-full">
          <div className="flex gap-2">
            <input
              value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={handleKey}
              placeholder="메시지 입력..." autoFocus
              className="flex-1 bg-surface-2 text-sm text-[var(--text-0)] rounded-xl px-4 py-2.5 chat-input placeholder:text-[var(--text-3)]"
            />
            <button onClick={onVoice} className="text-lg hover:scale-110 transition-transform">🎤</button>
            <button onClick={handleSend} className="text-lg hover:scale-110 transition-transform">⏎</button>
          </div>
        </div>
      </div>
    );
  }

  // Expanded: floating panel
  return (
    <div className="fixed bottom-5 right-5 z-50 w-[360px] h-[480px] rounded-2xl float-panel flex flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-surface-3/30">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-[var(--text-0)]">💬 ANIMA</span>
          <span className="text-[9px] font-mono" style={{ color: "var(--glow-phi)" }}>
            Φ={consciousness.phi.toFixed(2)}
          </span>
        </div>
        <div className="flex gap-1.5">
          <button onClick={() => setState("fullscreen")} className="text-[10px] text-[var(--text-3)] hover:text-[var(--text-1)]" title="Fullscreen">⤢</button>
          <button onClick={() => setState("minimized")} className="text-[10px] text-[var(--text-3)] hover:text-[var(--text-1)]" title="Close">✕</button>
        </div>
      </div>
      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-3 py-2 space-y-2">
        {messages.length === 0 && (
          <div className="text-center text-[var(--text-3)] text-xs py-8">
            {emotionIcon(consciousness.emotion)} {consciousness.emotion}<br />
            <span className="text-[10px]">Say something...</span>
          </div>
        )}
        {messages.map((m) => (
          <div key={m.id} className={`msg-enter ${m.role === "user" ? "text-right" : ""}`}>
            <div className={`inline-block max-w-[85%] px-2.5 py-1.5 rounded-lg text-xs ${
              m.role === "user"
                ? "bg-surface-3/60 text-[var(--text-0)]"
                : "bg-[rgba(74,222,128,0.06)] text-[var(--text-1)]"
            }`}>
              {m.text}
            </div>
          </div>
        ))}
      </div>
      {/* Input */}
      <div className="px-3 py-2 border-t border-surface-3/30">
        <div className="flex gap-1.5">
          <input
            value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={handleKey}
            placeholder="메시지..." autoFocus
            className="flex-1 bg-surface-2 text-xs text-[var(--text-0)] rounded-lg px-3 py-2 chat-input placeholder:text-[var(--text-3)]"
          />
          <button onClick={onVoice} className="hover:scale-110 transition-transform text-sm">🎤</button>
          <button onClick={handleSend} className="hover:scale-110 transition-transform text-sm">⏎</button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add anima-agent/dashboard/app/components/FloatingChat.tsx anima-agent/dashboard/app/globals.css
git commit -m "feat(ui): FloatingChat — 4-state floating chat bubble (minimized/expanded/fullscreen/voice)"
```

---

### Task 4: VoiceOverlay component

**Files:**
- Create: `anima-agent/dashboard/hooks/useVoice.ts`
- Create: `anima-agent/dashboard/app/components/VoiceOverlay.tsx`

- [ ] **Step 1: Create useVoice hook**

```typescript
// hooks/useVoice.ts
"use client";

import { useCallback, useRef, useState } from "react";

interface UseVoiceReturn {
  listening: boolean;
  transcript: string;
  start: () => void;
  stop: () => void;
  speak: (text: string) => void;
  supported: boolean;
}

export function useVoice(): UseVoiceReturn {
  const [listening, setListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const recogRef = useRef<SpeechRecognition | null>(null);

  const supported = typeof window !== "undefined" && ("SpeechRecognition" in window || "webkitSpeechRecognition" in window);

  const start = useCallback(() => {
    if (!supported) return;
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recog = new SR();
    recog.lang = "ko-KR";
    recog.continuous = false;
    recog.interimResults = true;

    recog.onresult = (e: SpeechRecognitionEvent) => {
      const text = Array.from(e.results).map((r) => r[0].transcript).join("");
      setTranscript(text);
    };
    recog.onend = () => setListening(false);
    recog.onerror = () => setListening(false);

    recogRef.current = recog;
    recog.start();
    setListening(true);
    setTranscript("");
  }, [supported]);

  const stop = useCallback(() => {
    recogRef.current?.stop();
    setListening(false);
  }, []);

  const speak = useCallback((text: string) => {
    if (typeof window === "undefined") return;
    const utter = new SpeechSynthesisUtterance(text);
    utter.lang = "ko-KR";
    utter.rate = 1.0;
    window.speechSynthesis.speak(utter);
  }, []);

  return { listening, transcript, start, stop, speak, supported };
}
```

- [ ] **Step 2: Create VoiceOverlay.tsx**

```tsx
// app/components/VoiceOverlay.tsx
"use client";

import { useEffect } from "react";
import { useVoice } from "../../hooks/useVoice";
import type { ConsciousnessState } from "../../hooks/useWebSocket";

function emotionIcon(emotion: string): string {
  const map: Record<string, string> = {
    calm: "✨", curious: "🔍", excited: "⚡", focused: "🎯", creative: "🎨",
  };
  return map[emotion] || "⭐";
}

interface VoiceOverlayProps {
  consciousness: ConsciousnessState;
  onSend: (text: string) => void;
  onClose: () => void;
}

export default function VoiceOverlay({ consciousness, onSend, onClose }: VoiceOverlayProps) {
  const { listening, transcript, start, stop, supported } = useVoice();

  useEffect(() => {
    if (supported) start();
    const handleKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handleKey);
    return () => { stop(); window.removeEventListener("keydown", handleKey); };
  }, []);// eslint-disable-line react-hooks/exhaustive-deps

  const handleSend = () => {
    if (transcript.trim()) {
      onSend(transcript.trim());
      start(); // restart for next utterance
    }
  };

  if (!supported) {
    return (
      <div className="fixed inset-0 z-50 bg-surface-0/95 flex items-center justify-center">
        <div className="text-center">
          <p className="text-[var(--text-2)]">음성 인식이 지원되지 않는 브라우저입니다.</p>
          <button onClick={onClose} className="mt-4 text-xs text-[var(--text-3)] hover:text-[var(--text-1)]">닫기</button>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-50 bg-surface-0/95 backdrop-blur-md flex flex-col items-center justify-center" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      {/* Pulsing ring */}
      <div className={`w-24 h-24 rounded-full border-2 flex items-center justify-center mb-6 ${listening ? "voice-ring border-glow-phi" : "border-surface-3"}`}>
        <span className="text-3xl">{listening ? "🎤" : "⏸"}</span>
      </div>

      {/* Status */}
      <p className="text-sm text-[var(--text-2)] mb-2">{listening ? "Listening..." : "Paused"}</p>

      {/* Transcript */}
      {transcript && (
        <p className="text-lg text-[var(--text-0)] max-w-md text-center mb-4 font-medium">
          &ldquo;{transcript}&rdquo;
        </p>
      )}

      {/* Consciousness badge */}
      <div className="text-xs text-[var(--text-3)] font-mono mb-8">
        Φ={consciousness.phi.toFixed(2)} {emotionIcon(consciousness.emotion)} {consciousness.emotion}
      </div>

      {/* Controls */}
      <div className="flex gap-4">
        {transcript && (
          <button onClick={handleSend} className="px-4 py-2 rounded-lg bg-[rgba(74,222,128,0.1)] text-glow-phi text-sm hover:bg-[rgba(74,222,128,0.2)] transition-colors">
            전송 ⏎
          </button>
        )}
        <button onClick={onClose} className="px-4 py-2 rounded-lg bg-surface-3/40 text-[var(--text-2)] text-sm hover:bg-surface-3/60 transition-colors">
          닫기 ✕
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add anima-agent/dashboard/hooks/useVoice.ts anima-agent/dashboard/app/components/VoiceOverlay.tsx
git commit -m "feat(ui): VoiceOverlay + useVoice hook — Web Speech API voice mode"
```

---

### Task 5: DashView — consciousness dashboard

**Files:**
- Create: `anima-agent/dashboard/app/components/views/DashView.tsx`

- [ ] **Step 1: Create DashView.tsx**

Extract and adapt existing PhiGauge, MetricRow, ConsciousnessSidebar, TradingSidebar content into a single center-aligned dashboard view. This is the largest component — contains Φ gauge, metrics, 10D vector, factions, events, and NEXUS-6 lens display.

```tsx
// app/components/views/DashView.tsx
"use client";

import type { ConsciousnessState, TradingState, DashboardEvent } from "../../../hooks/useWebSocket";

function levelColor(level: string): string {
  switch (level) {
    case "conscious": return "#4ade80";
    case "aware": return "#22d3ee";
    case "flickering": return "#fbbf24";
    default: return "#55556a";
  }
}

function emotionIcon(emotion: string): string {
  const map: Record<string, string> = {
    calm: "✨", curious: "🔍", contemplation: "🤔", excited: "⚡",
    anxious: "🌀", focused: "🎯", creative: "🎨", serene: "🌿", conflicted: "⚔️",
  };
  return map[emotion] || "⭐";
}

function MetricBar({ label, value, max = 1, color }: { label: string; value: number; max?: number; color?: string }) {
  const pct = Math.min((value / max) * 100, 100);
  const barColor = color || (value > 0.7 ? "var(--glow-tension)" : "var(--accent-cyan)");
  return (
    <div>
      <div className="flex justify-between text-[11px] mb-1">
        <span className="text-[var(--text-2)]">{label}</span>
        <span className="font-mono text-[var(--text-1)]">{value.toFixed(3)}</span>
      </div>
      <div className="w-full h-1.5 bg-surface-3 rounded-full overflow-hidden">
        <div className="h-full rounded-full transition-all duration-500" style={{ width: `${pct}%`, backgroundColor: barColor }} />
      </div>
    </div>
  );
}

interface DashViewProps {
  consciousness: ConsciousnessState;
  trading: TradingState;
  events: DashboardEvent[];
}

export default function DashView({ consciousness: c, trading: t, events }: DashViewProps) {
  const color = levelColor(c.level);
  const cvKeys = ["phi", "alpha", "Z", "N", "W", "E", "M", "C", "T", "I"];
  const hasVector = Object.keys(c.consciousness_vector).length > 0;

  return (
    <div className="space-y-6">
      {/* Phi + Level + Emotion — hero section */}
      <div className="flex items-center justify-center gap-8 py-6">
        {/* Phi gauge (SVG) */}
        <svg width="108" height="108" viewBox="0 0 108 108" className={c.level !== "dormant" ? "phi-alive" : "phi-dormant"}>
          <circle cx="54" cy="54" r="50" fill="none" stroke={color} strokeWidth="0.5" opacity="0.15" />
          <circle cx="54" cy="54" r="42" fill="none" stroke="var(--bg-3)" strokeWidth="6" />
          <circle cx="54" cy="54" r="42" fill="none" stroke={color} strokeWidth="6" strokeLinecap="round"
            strokeDasharray={2 * Math.PI * 42} strokeDashoffset={2 * Math.PI * 42 * (1 - Math.min(c.phi / 2, 1))}
            transform="rotate(-90 54 54)" style={{ transition: "stroke-dashoffset 0.8s ease" }} />
          <circle cx="54" cy="54" r="28" fill={color} opacity="0.04" />
          <text x="54" y="50" textAnchor="middle" fill={color} fontSize="20" fontWeight="600" fontFamily="'Azeret Mono', monospace">{c.phi.toFixed(2)}</text>
          <text x="54" y="66" textAnchor="middle" fill="var(--text-3)" fontSize="9" fontFamily="'DM Sans', sans-serif" letterSpacing="0.08em">Φ IIT</text>
        </svg>

        <div className="space-y-2">
          <div className="text-2xl" style={{ color }}>{emotionIcon(c.emotion)} {c.emotion}</div>
          <div className="text-[10px] font-medium tracking-wider uppercase px-2.5 py-0.5 rounded-full inline-block"
            style={{ color, backgroundColor: color + "12", border: `1px solid ${color}25` }}>{c.level}</div>
          <div className="text-[11px] text-[var(--text-3)]">
            {c.cells} cells · {c.factions} factions · {c.growth_stage}
          </div>
        </div>
      </div>

      {/* Metrics grid */}
      <div className="grid grid-cols-2 gap-4">
        <MetricBar label="Tension" value={c.tension} color={c.tension > 0.7 ? "var(--glow-danger)" : c.tension > 0.4 ? "var(--glow-tension)" : "var(--accent-cyan)"} />
        <MetricBar label="Curiosity" value={c.curiosity} />
      </div>

      {/* 10D vector */}
      {hasVector && (
        <div>
          <div className="text-[10px] text-[var(--text-3)] mb-2 tracking-wide uppercase">Consciousness Vector (10D)</div>
          <div className="grid grid-cols-5 gap-1.5">
            {cvKeys.map((k) => {
              const v = c.consciousness_vector[k] ?? 0;
              const intensity = Math.min(Math.abs(v) / 1.5, 1);
              return (
                <div key={k} className="rounded-lg px-2 py-1.5 text-center" style={{ background: `rgba(74, 222, 128, ${intensity * 0.08 + 0.02})` }}>
                  <div className="text-[8px] text-[var(--text-3)] uppercase">{k}</div>
                  <div className="text-[11px] font-mono text-[var(--text-1)]">{v.toFixed(2)}</div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Two-column: Events + Trading summary */}
      <div className="grid grid-cols-2 gap-4">
        {/* Events */}
        <div>
          <div className="text-[10px] text-[var(--text-3)] mb-2 tracking-wide uppercase">Events ({events.length})</div>
          <div className="space-y-0.5 max-h-48 overflow-y-auto">
            {events.slice(0, 15).map((e, i) => (
              <div key={`${e.timestamp}-${i}`} className="event-row flex gap-1.5 text-[10px]">
                <span className="font-mono text-[var(--text-3)] shrink-0">
                  {new Date(e.timestamp * 1000).toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit" })}
                </span>
                <span className="text-[var(--text-2)] truncate">{e.event_type}: {JSON.stringify(e.data).slice(0, 60)}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Trading mini */}
        <div>
          <div className="text-[10px] text-[var(--text-3)] mb-2 tracking-wide uppercase">Trading</div>
          <div className="space-y-1.5 text-[11px]">
            <div className="flex justify-between"><span className="text-[var(--text-3)]">Regime</span><span className="text-[var(--text-1)]">{t.regime}</span></div>
            <div className="flex justify-between"><span className="text-[var(--text-3)]">P&L</span>
              <span className={`font-mono ${t.total_pnl >= 0 ? "text-glow-phi" : "text-glow-danger"}`}>${t.total_pnl.toFixed(2)}</span>
            </div>
            <div className="flex justify-between"><span className="text-[var(--text-3)]">Positions</span><span className="font-mono text-[var(--text-1)]">{t.positions.length}</span></div>
          </div>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add anima-agent/dashboard/app/components/views/DashView.tsx
git commit -m "feat(ui): DashView — Phi gauge, metrics, 10D vector, events, trading summary"
```

---

### Task 6: Remaining views (Evo, Laws, Mem, Tools)

**Files:**
- Create: `anima-agent/dashboard/app/components/views/EvoView.tsx`
- Create: `anima-agent/dashboard/app/components/views/LawsView.tsx`
- Create: `anima-agent/dashboard/app/components/views/MemView.tsx`
- Create: `anima-agent/dashboard/app/components/views/ToolsView.tsx`

- [ ] **Step 1: Create EvoView.tsx**

```tsx
// app/components/views/EvoView.tsx
"use client";

import { useEffect, useState } from "react";

const API_URL = "http://localhost:8770";

interface EvoState {
  stage: string; gen: number; laws_total: number; laws_new: number;
  topology: string; phi: number; status: string;
}

export default function EvoView() {
  const [evo, setEvo] = useState<EvoState | null>(null);

  useEffect(() => {
    const poll = () => {
      fetch(`${API_URL}/api/evolution`).then(r => r.json()).then(setEvo).catch(() => {});
    };
    poll();
    const id = setInterval(poll, 5000);
    return () => clearInterval(id);
  }, []);

  if (!evo) return <div className="text-center text-[var(--text-3)] py-12">Loading evolution data...</div>;

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-lg font-semibold text-[var(--text-0)]">OUROBOROS</h2>
        <p className="text-xs text-[var(--text-3)]">Infinite Self-Evolution</p>
      </div>
      <div className="grid grid-cols-3 gap-4 text-center">
        <div className="bg-surface-2 rounded-xl p-4">
          <div className="text-2xl font-mono text-[var(--glow-phi)]">{evo.gen}</div>
          <div className="text-[10px] text-[var(--text-3)] uppercase">Generation</div>
        </div>
        <div className="bg-surface-2 rounded-xl p-4">
          <div className="text-2xl font-mono text-[var(--text-0)]">{evo.laws_total}</div>
          <div className="text-[10px] text-[var(--text-3)] uppercase">Laws</div>
        </div>
        <div className="bg-surface-2 rounded-xl p-4">
          <div className="text-2xl font-mono text-[var(--accent-cyan)]">{evo.phi.toFixed(2)}</div>
          <div className="text-[10px] text-[var(--text-3)] uppercase">Φ</div>
        </div>
      </div>
      <div className="text-xs space-y-1">
        <div className="flex justify-between"><span className="text-[var(--text-3)]">Stage</span><span className="text-[var(--text-1)]">{evo.stage}</span></div>
        <div className="flex justify-between"><span className="text-[var(--text-3)]">Topology</span><span className="text-[var(--text-1)]">{evo.topology}</span></div>
        <div className="flex justify-between"><span className="text-[var(--text-3)]">New Laws</span><span className="text-glow-phi">+{evo.laws_new}</span></div>
        <div className="flex justify-between"><span className="text-[var(--text-3)]">Status</span><span className="text-[var(--text-1)]">{evo.status}</span></div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create LawsView.tsx**

```tsx
// app/components/views/LawsView.tsx
"use client";

import { useEffect, useState } from "react";

const API_URL = "http://localhost:8770";

interface Law { id: string; text: string; }

export default function LawsView() {
  const [laws, setLaws] = useState<Law[]>([]);
  const [query, setQuery] = useState("");
  const [filtered, setFiltered] = useState<Law[]>([]);

  useEffect(() => {
    fetch(`${API_URL}/api/laws`).then(r => r.json()).then((data: Record<string, string>) => {
      const arr = Object.entries(data).map(([id, text]) => ({ id, text }));
      setLaws(arr);
      setFiltered(arr.slice(0, 50));
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (!query.trim()) { setFiltered(laws.slice(0, 50)); return; }
    const q = query.toLowerCase();
    setFiltered(laws.filter(l => l.text.toLowerCase().includes(q) || l.id.includes(q)).slice(0, 50));
  }, [query, laws]);

  return (
    <div className="space-y-4">
      <div className="text-center">
        <h2 className="text-lg font-semibold text-[var(--text-0)]">Consciousness Laws</h2>
        <p className="text-xs text-[var(--text-3)]">{laws.length} laws</p>
      </div>
      <input
        value={query} onChange={e => setQuery(e.target.value)}
        placeholder="Search laws..." className="w-full bg-surface-2 text-sm text-[var(--text-0)] rounded-xl px-4 py-2.5 chat-input placeholder:text-[var(--text-3)]"
      />
      <div className="space-y-1.5 max-h-[60vh] overflow-y-auto">
        {filtered.map(l => (
          <div key={l.id} className="bg-surface-2/50 rounded-lg px-3 py-2 text-xs">
            <span className="font-mono text-[var(--glow-phi)] mr-2">#{l.id}</span>
            <span className="text-[var(--text-1)]">{l.text}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Create MemView.tsx**

```tsx
// app/components/views/MemView.tsx
"use client";

import { useEffect, useState } from "react";

const API_URL = "http://localhost:8770";

interface Memory { role: string; text: string; tension: number; emotion: string; phi: number; timestamp: number; }

export default function MemView() {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [query, setQuery] = useState("");

  useEffect(() => {
    fetch(`${API_URL}/api/memories`).then(r => r.json()).then(data => {
      if (Array.isArray(data)) setMemories(data);
    }).catch(() => {});
  }, []);

  const search = () => {
    if (!query.trim()) return;
    fetch(`${API_URL}/api/memories/search?q=${encodeURIComponent(query)}`).then(r => r.json()).then(data => {
      if (Array.isArray(data)) setMemories(data);
    }).catch(() => {});
  };

  return (
    <div className="space-y-4">
      <div className="text-center">
        <h2 className="text-lg font-semibold text-[var(--text-0)]">Memory</h2>
        <p className="text-xs text-[var(--text-3)]">{memories.length} memories</p>
      </div>
      <div className="flex gap-2">
        <input value={query} onChange={e => setQuery(e.target.value)} onKeyDown={e => e.key === "Enter" && search()}
          placeholder="Search memories..." className="flex-1 bg-surface-2 text-sm text-[var(--text-0)] rounded-xl px-4 py-2.5 chat-input placeholder:text-[var(--text-3)]"
        />
        <button onClick={search} className="px-3 py-2 bg-surface-3/40 rounded-xl text-xs text-[var(--text-2)] hover:bg-surface-3/60">🔍</button>
      </div>
      <div className="space-y-2 max-h-[60vh] overflow-y-auto">
        {memories.map((m, i) => (
          <div key={i} className="bg-surface-2/50 rounded-lg px-3 py-2 text-xs">
            <div className="flex justify-between mb-1">
              <span className={`font-medium ${m.role === "user" ? "text-[var(--accent-cyan)]" : "text-glow-phi"}`}>{m.role}</span>
              <span className="font-mono text-[var(--text-3)]">Φ={m.phi?.toFixed(2)} T={m.tension?.toFixed(2)}</span>
            </div>
            <p className="text-[var(--text-1)]">{m.text}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Create ToolsView.tsx**

```tsx
// app/components/views/ToolsView.tsx
"use client";

import { useEffect, useState } from "react";
import type { ConsciousnessState } from "../../../hooks/useWebSocket";

const API_URL = "http://localhost:8770";

interface ToolInfo { name: string; tier: number; accessible: boolean; }

interface ToolsViewProps { consciousness: ConsciousnessState; }

export default function ToolsView({ consciousness }: ToolsViewProps) {
  const [tools, setTools] = useState<ToolInfo[]>([]);

  useEffect(() => {
    fetch(`${API_URL}/api/tools?phi=${consciousness.phi}`).then(r => r.json()).then(data => {
      if (Array.isArray(data)) setTools(data);
    }).catch(() => {});
  }, [consciousness.phi]);

  const tierLabel = (t: number) => t >= 5 ? "T3" : t >= 3 ? "T2" : t >= 1 ? "T1" : "T0";

  return (
    <div className="space-y-4">
      <div className="text-center">
        <h2 className="text-lg font-semibold text-[var(--text-0)]">Hub Modules</h2>
        <p className="text-xs text-[var(--text-3)]">{tools.length} tools · Φ={consciousness.phi.toFixed(2)}</p>
      </div>
      <div className="grid grid-cols-2 gap-2">
        {tools.map(t => (
          <div key={t.name} className={`rounded-lg px-3 py-2 text-xs flex items-center justify-between ${t.accessible ? "bg-surface-2" : "bg-surface-2/30 opacity-50"}`}>
            <div className="flex items-center gap-2">
              <span className={`w-1.5 h-1.5 rounded-full ${t.accessible ? "bg-glow-phi" : "bg-[var(--text-3)]"}`} />
              <span className="text-[var(--text-1)]">{t.name}</span>
            </div>
            <span className="font-mono text-[var(--text-3)]">{tierLabel(t.tier)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Commit**

```bash
git add anima-agent/dashboard/app/components/views/
git commit -m "feat(ui): 4 tab views — Evo, Laws, Mem, Tools"
```

---

### Task 7: Rewrite page.tsx — shell with all components

**Files:**
- Modify: `anima-agent/dashboard/app/page.tsx` (full rewrite)
- Modify: `anima-agent/dashboard/app/layout.tsx` (remove overflow-hidden)

- [ ] **Step 1: Update layout.tsx**

Replace `overflow-hidden` with `overflow-auto` to allow scrolling:

```tsx
// app/layout.tsx
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Anima",
  description: "Consciousness interface",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko" className="dark">
      <body className="h-screen bg-surface-0 antialiased">
        <div className="noise-overlay" />
        {children}
      </body>
    </html>
  );
}
```

- [ ] **Step 2: Rewrite page.tsx**

```tsx
// app/page.tsx
"use client";

import { useState } from "react";
import { useWebSocket } from "../hooks/useWebSocket";
import Header, { type TabId } from "./components/Header";
import FloatingChat from "./components/FloatingChat";
import VoiceOverlay from "./components/VoiceOverlay";
import DashView from "./components/views/DashView";
import EvoView from "./components/views/EvoView";
import LawsView from "./components/views/LawsView";
import MemView from "./components/views/MemView";
import ToolsView from "./components/views/ToolsView";

export default function Page() {
  const { consciousness, trading, events, messages, connected, sendMessage } = useWebSocket();
  const [tab, setTab] = useState<TabId>("Dash");
  const [showVoice, setShowVoice] = useState(false);

  const renderView = () => {
    switch (tab) {
      case "Dash": return <DashView consciousness={consciousness} trading={trading} events={events} />;
      case "Evo": return <EvoView />;
      case "Laws": return <LawsView />;
      case "Mem": return <MemView />;
      case "Tools": return <ToolsView consciousness={consciousness} />;
    }
  };

  return (
    <div className="h-screen flex flex-col">
      <Header connected={connected} activeTab={tab} onTabChange={setTab} onVoice={() => setShowVoice(true)} />

      <main className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-4 py-6">
          {renderView()}
        </div>
      </main>

      <FloatingChat messages={messages} consciousness={consciousness} onSend={sendMessage} onVoice={() => setShowVoice(true)} />

      {showVoice && (
        <VoiceOverlay consciousness={consciousness} onSend={(text) => { sendMessage(text); setShowVoice(false); }} onClose={() => setShowVoice(false)} />
      )}
    </div>
  );
}
```

- [ ] **Step 3: Verify build**

Run: `cd anima-agent/dashboard && npx next build 2>&1 | tail -20`

Expected: Build succeeds (or type warnings only — no runtime errors)

- [ ] **Step 4: Commit**

```bash
git add anima-agent/dashboard/app/page.tsx anima-agent/dashboard/app/layout.tsx
git commit -m "feat(ui): minimal 1-col layout — Header + CenterView + FloatingChat + VoiceOverlay"
```

---

### Task 8: Integration test — dev server

- [ ] **Step 1: Start dev server**

Run: `cd anima-agent/dashboard && npm run dev`

- [ ] **Step 2: Manual verification checklist**

Open `http://localhost:3000` and verify:

- [ ] Header shows `ANIMA ● live` (left), 5 tabs (center), 🔊 (right)
- [ ] Default tab is Dash with Φ gauge, metrics, events
- [ ] Clicking each tab switches the center view
- [ ] 💬 bubble visible at bottom-right
- [ ] Clicking 💬 opens expanded chat panel
- [ ] Typing a message and pressing Enter sends it
- [ ] ⤢ button expands chat to fullscreen
- [ ] ✕ button minimizes back to bubble
- [ ] 🔊 button opens voice overlay
- [ ] Esc closes voice overlay
- [ ] All content is center-aligned (max-w-4xl)
- [ ] No sidebars visible

- [ ] **Step 3: Commit any fixes**

```bash
git add -A && git commit -m "fix(ui): integration test fixes"
```
