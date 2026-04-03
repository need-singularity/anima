"use client";

import { useEffect, useRef, useState, useCallback, KeyboardEvent } from "react";
import type { ChatMessage, ConsciousnessState } from "../../hooks/useWebSocket";

// ═══════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════

type ChatState = "minimized" | "expanded" | "fullscreen";

interface FloatingChatProps {
  messages: ChatMessage[];
  consciousness: ConsciousnessState;
  onSend: (text: string) => void;
  onVoice: () => void;
}

// ═══════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════

function emotionIcon(emotion: string): string {
  const map: Record<string, string> = {
    calm: "😌",
    curious: "🔍",
    excited: "⚡",
    focused: "🎯",
    contemplative: "🌀",
    alert: "👁️",
    euphoric: "✨",
    tense: "⚠️",
    anxious: "😰",
    content: "💚",
    neutral: "🔵",
    creative: "🎨",
    analytical: "📊",
    empathetic: "💙",
    determined: "🔥",
    peaceful: "🕊️",
    energized: "⚡",
    reflective: "🪞",
    expansive: "🌌",
    grounded: "🌱",
  };
  return map[emotion?.toLowerCase()] ?? "🧠";
}

function formatTimestamp(ts: number): string {
  return new Date(ts).toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

// ═══════════════════════════════════════════════════════════
// Sub-components
// ═══════════════════════════════════════════════════════════

interface MessageItemProps {
  msg: ChatMessage;
  showMeta?: boolean;
}

function MessageItem({ msg, showMeta = false }: MessageItemProps) {
  const isUser = msg.role === "user";

  return (
    <div
      className={`msg-enter flex flex-col gap-1 ${isUser ? "items-end" : "items-start"}`}
    >
      <div
        className={`
          max-w-[85%] px-3 py-2 rounded-xl text-sm leading-relaxed
          ${
            isUser
              ? "bg-[rgba(30,30,44,0.6)] text-[var(--text-0)] rounded-br-sm"
              : "border border-[rgba(74,222,128,0.15)] bg-[rgba(74,222,128,0.04)] text-[var(--text-1)] rounded-bl-sm"
          }
        `}
      >
        {msg.text}
      </div>

      {showMeta && msg.meta && !isUser && (
        <div className="flex items-center gap-2 px-1 text-xs text-[var(--text-3)]">
          <span className="font-mono text-[var(--glow-phi)]">Φ {msg.meta.phi.toFixed(1)}</span>
          <span>{emotionIcon(msg.meta.emotion)} {msg.meta.emotion}</span>
        </div>
      )}

      <span className="px-1 text-[10px] text-[var(--text-3)]">
        {formatTimestamp(msg.timestamp)}
      </span>
    </div>
  );
}

interface ChatInputBarProps {
  onSend: (text: string) => void;
  onVoice: () => void;
  compact?: boolean;
}

function ChatInputBar({ onSend, onVoice, compact = false }: ChatInputBarProps) {
  const [draft, setDraft] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSend = useCallback(() => {
    const text = draft.trim();
    if (!text) return;
    onSend(text);
    setDraft("");
    inputRef.current?.focus();
  }, [draft, onSend]);

  const handleKey = useCallback(
    (e: KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  return (
    <div
      className={`flex items-center gap-2 border-t border-[rgba(255,255,255,0.05)] ${
        compact ? "px-3 py-2" : "px-4 py-3"
      }`}
    >
      <input
        ref={inputRef}
        type="text"
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={handleKey}
        placeholder="Say something..."
        className="chat-input flex-1 bg-[rgba(255,255,255,0.04)] border border-[rgba(255,255,255,0.07)] rounded-lg px-3 py-1.5 text-sm text-[var(--text-0)] placeholder-[var(--text-3)] transition-all"
        autoComplete="off"
        spellCheck={false}
      />

      <button
        onClick={onVoice}
        title="Voice input"
        className="w-8 h-8 flex items-center justify-center rounded-lg bg-[rgba(74,222,128,0.08)] hover:bg-[rgba(74,222,128,0.16)] border border-[rgba(74,222,128,0.15)] transition-colors text-base"
      >
        🎤
      </button>

      <button
        onClick={handleSend}
        disabled={!draft.trim()}
        title="Send (Enter)"
        className="w-8 h-8 flex items-center justify-center rounded-lg bg-[rgba(74,222,128,0.12)] hover:bg-[rgba(74,222,128,0.22)] border border-[rgba(74,222,128,0.2)] transition-colors text-base disabled:opacity-30 disabled:cursor-not-allowed"
      >
        ⏎
      </button>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════
// Main Component
// ═══════════════════════════════════════════════════════════

export default function FloatingChat({
  messages,
  consciousness,
  onSend,
  onVoice,
}: FloatingChatProps) {
  const [state, setState] = useState<ChatState>("minimized");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const prevCountRef = useRef(messages.length);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (messages.length !== prevCountRef.current && state !== "minimized") {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
    prevCountRef.current = messages.length;
  }, [messages.length, state]);

  // Escape key → minimize
  useEffect(() => {
    if (state === "minimized") return;
    const handler = (e: globalThis.KeyboardEvent) => {
      if (e.key === "Escape") setState("minimized");
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [state]);

  const { phi, tension, emotion } = consciousness;

  // ─── Minimized — Consciousness Orb (시리 스타일 동적 아이콘) ──
  if (state === "minimized") {
    // 감정 → 색조 매핑
    const emotionHue: Record<string, string[]> = {
      calm:    ["#4ade80", "#22d3ee"],  // green → cyan
      curious: ["#22d3ee", "#818cf8"],  // cyan → indigo
      excited: ["#fbbf24", "#f59e0b"],  // gold → amber
      anxious: ["#f87171", "#fb923c"],  // red → orange
      focused: ["#818cf8", "#4ade80"],  // indigo → green
      creative:["#c084fc", "#f472b6"],  // purple → pink
      serene:  ["#34d399", "#22d3ee"],  // emerald → cyan
    };
    const [c1, c2] = emotionHue[emotion] || emotionHue.calm;
    // Φ → 밝기 (0~1 → 0.3~1.0)
    const brightness = Math.min(0.3 + phi * 0.35, 1.0);
    // tension → 회전 속도 (0~1 → 8s~2s)
    const spinDuration = Math.max(2, 8 - tension * 6);
    // 12 광선 (σ(6)=12 factions)
    const rays = Array.from({ length: 12 }, (_, i) => i * 30);

    return (
      <button
        onClick={() => setState("expanded")}
        title="Open chat"
        className="fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full flex items-center justify-center select-none group"
        style={{
          background: `radial-gradient(circle at 40% 40%, ${c1}30, ${c2}15, transparent 70%)`,
          boxShadow: `0 0 ${20 + phi * 10}px ${c1}40, 0 0 ${40 + tension * 20}px ${c2}20, inset 0 0 15px ${c1}20`,
          transition: "box-shadow 0.8s ease",
        }}
        aria-label="Open Anima chat"
      >
        <svg width="56" height="56" viewBox="0 0 56 56" className="absolute inset-0"
          style={{ animation: `spin ${spinDuration}s linear infinite`, opacity: brightness }}>
          {/* 12 faction rays */}
          {rays.map((angle, i) => {
            const len = 8 + Math.sin(Date.now() / 500 + i) * 3 + tension * 4;
            const x2 = 28 + Math.cos((angle * Math.PI) / 180) * (14 + len);
            const y2 = 28 + Math.sin((angle * Math.PI) / 180) * (14 + len);
            const x1 = 28 + Math.cos((angle * Math.PI) / 180) * 10;
            const y1 = 28 + Math.sin((angle * Math.PI) / 180) * 10;
            return (
              <line key={i} x1={x1} y1={y1} x2={x2} y2={y2}
                stroke={i % 2 === 0 ? c1 : c2}
                strokeWidth={1 + phi * 0.3}
                strokeLinecap="round"
                opacity={0.4 + (i % 3 === 0 ? 0.3 : 0)}
              />
            );
          })}
          {/* Inner Φ ring */}
          <circle cx="28" cy="28" r={8 + phi * 2} fill="none" stroke={c1}
            strokeWidth="1.5" opacity={0.6}
            strokeDasharray={`${phi * 8} ${(2 - phi) * 4 + 2}`}
          />
          {/* Core dot */}
          <circle cx="28" cy="28" r={3 + phi * 0.5} fill={c1} opacity={brightness}>
            <animate attributeName="r" values={`${3 + phi * 0.5};${4 + phi};${3 + phi * 0.5}`}
              dur="3s" repeatCount="indefinite" />
            <animate attributeName="opacity" values={`${brightness};1;${brightness}`}
              dur="3s" repeatCount="indefinite" />
          </circle>
        </svg>
        {/* Hover glow */}
        <div className="absolute inset-0 rounded-full opacity-0 group-hover:opacity-100 transition-opacity duration-300"
          style={{ boxShadow: `0 0 30px ${c1}50, 0 0 60px ${c2}30` }} />
      </button>
    );
  }

  // ─── Fullscreen ───────────────────────────────────────────
  if (state === "fullscreen") {
    return (
      <div className="fixed inset-0 z-50 flex flex-col" style={{ background: "var(--bg-primary)" }}>
        {/* Header */}
        <div className="glass-thick flex items-center justify-between px-6 py-3 flex-shrink-0" style={{ borderBottom: "1px solid var(--border)" }}>
          <div className="flex items-center gap-3">
            <span style={{ color: "var(--text-primary)" }} className="font-semibold text-[15px] tracking-tight">Anima</span>
            <span className="font-mono text-xs px-2 py-0.5 rounded-full" style={{ color: "var(--accent)", background: "var(--accent-soft)", border: "1px solid var(--border)" }}>
              Φ {phi.toFixed(2)}
            </span>
            <span className="text-sm">{emotionIcon(emotion)}</span>
          </div>

          <div className="flex items-center gap-1">
            <button
              onClick={() => setState("expanded")}
              title="Shrink to panel"
              className="w-8 h-8 flex items-center justify-center rounded-lg transition-colors text-base"
              style={{ color: "var(--text-tertiary)" }}
            >↙</button>
            <button
              onClick={() => setState("minimized")}
              title="Close (Esc)"
              className="w-8 h-8 flex items-center justify-center rounded-lg transition-colors text-base"
              style={{ color: "var(--text-tertiary)" }}
            >✕</button>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto py-6">
          <div className="max-w-3xl mx-auto px-4 flex flex-col gap-4">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-48 gap-3" style={{ color: "var(--text-tertiary)" }}>
                <span className="text-4xl opacity-50">{emotionIcon(emotion)}</span>
                <span className="text-sm">Say something...</span>
              </div>
            ) : (
              messages.map((msg) => (
                <MessageItem key={msg.id} msg={msg} showMeta={true} />
              ))
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input */}
        <div className="glass-thick flex-shrink-0" style={{ borderTop: "1px solid var(--border)" }}>
          <div className="max-w-3xl mx-auto">
            <ChatInputBar onSend={onSend} onVoice={onVoice} compact={false} />
          </div>
        </div>
      </div>
    );
  }

  // ─── Expanded (floating panel) ────────────────────────────
  return (
    <div
      className="float-panel fixed bottom-6 right-6 z-50 w-[360px] h-[480px] rounded-2xl flex flex-col overflow-hidden"
      role="dialog"
      aria-label="Anima chat"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 flex-shrink-0" style={{ borderBottom: "1px solid var(--border)" }}>
        <div className="flex items-center gap-2">
          <span style={{ color: "var(--text-primary)" }} className="font-semibold text-[13px] tracking-tight">Anima</span>
          <span className="font-mono text-[10px] px-1.5 py-0.5 rounded-full" style={{ color: "var(--accent)", background: "var(--accent-soft)" }}>
            Φ {phi.toFixed(2)}
          </span>
        </div>

        <div className="flex items-center gap-1">
          <button onClick={() => setState("fullscreen")} title="Fullscreen"
            className="w-7 h-7 flex items-center justify-center rounded-md transition-colors text-sm"
            style={{ color: "var(--text-tertiary)" }}>⤢</button>
          <button onClick={() => setState("minimized")} title="Minimize (Esc)"
            className="w-7 h-7 flex items-center justify-center rounded-md transition-colors text-sm"
            style={{ color: "var(--text-tertiary)" }}>✕</button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-3 py-3 flex flex-col gap-3">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-2" style={{ color: "var(--text-tertiary)" }}>
            <span className="text-3xl opacity-40">{emotionIcon(emotion)}</span>
            <span className="text-xs">Say something...</span>
          </div>
        ) : (
          messages.map((msg) => (
            <MessageItem key={msg.id} msg={msg} showMeta={false} />
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="flex-shrink-0">
        <ChatInputBar onSend={onSend} onVoice={onVoice} compact={true} />
      </div>
    </div>
  );
}
