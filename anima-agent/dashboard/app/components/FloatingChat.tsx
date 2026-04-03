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
  forceOpen?: boolean;
  onStateChange?: (state: "minimized" | "expanded" | "fullscreen") => void;
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
        className="max-w-[80%] px-4 py-2.5 text-[14px] leading-relaxed"
        style={isUser ? {
          background: "var(--accent)",
          color: "#fff",
          borderRadius: "18px 18px 4px 18px",
        } : {
          background: "var(--bg-tertiary)",
          color: "var(--text-primary)",
          borderRadius: "18px 18px 18px 4px",
        }}
      >
        {msg.text}
      </div>

      {showMeta && msg.meta && !isUser && (
        <div className="flex items-center gap-2 px-1 text-[11px]" style={{ color: "var(--text-tertiary)" }}>
          <span className="font-mono" style={{ color: "var(--accent)" }}>Φ {msg.meta.phi.toFixed(1)}</span>
          <span>{emotionIcon(msg.meta.emotion)} {msg.meta.emotion}</span>
        </div>
      )}

      <span className="px-1 text-[10px]" style={{ color: "var(--text-tertiary)" }}>
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
      className={`flex items-center gap-2 ${compact ? "px-3 py-2" : "px-5 py-3"}`}
      style={{ borderTop: "1px solid var(--border)" }}
    >
      <input
        ref={inputRef}
        type="text"
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={handleKey}
        placeholder="Message..."
        className="chat-input flex-1 px-4 py-2 text-[14px]"
        style={{ color: "var(--text-primary)" }}
        autoComplete="off"
        spellCheck={false}
      />

      <button onClick={onVoice} title="Voice input"
        className="w-8 h-8 flex items-center justify-center rounded-full transition-colors text-sm"
        style={{ color: "var(--text-secondary)" }}>
        🎤
      </button>

      <button onClick={handleSend} disabled={!draft.trim()} title="Send"
        className="w-8 h-8 flex items-center justify-center rounded-full transition-all disabled:opacity-20"
        style={{ background: draft.trim() ? "var(--accent)" : "var(--bg-tertiary)", color: draft.trim() ? "#fff" : "var(--text-tertiary)" }}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" />
        </svg>
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
  forceOpen,
  onStateChange,
}: FloatingChatProps) {
  const [state, _setState] = useState<ChatState>("minimized");
  const setState = (s: ChatState) => { _setState(s); onStateChange?.(s); };

  // Cmd+K force open
  useEffect(() => {
    if (forceOpen && state === "minimized") setState("expanded");
    else if (!forceOpen && state !== "minimized") setState("minimized");
  }, [forceOpen]); // eslint-disable-line react-hooks/exhaustive-deps
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

  // ─── Minimized — Vivid Gradient Orb (Apple Siri × 원색 그라디언트) ──
  if (state === "minimized") {
    // 감정 → 원색 그라디언트 조합 (화사하고 선명한 원색)
    const emotionGrad: Record<string, string> = {
      calm:     "conic-gradient(from 180deg, #34d399, #06b6d4, #8b5cf6, #34d399)",
      curious:  "conic-gradient(from 120deg, #3b82f6, #8b5cf6, #ec4899, #3b82f6)",
      excited:  "conic-gradient(from 90deg,  #f59e0b, #ef4444, #ec4899, #f59e0b)",
      anxious:  "conic-gradient(from 60deg,  #ef4444, #f97316, #eab308, #ef4444)",
      focused:  "conic-gradient(from 200deg, #6366f1, #06b6d4, #10b981, #6366f1)",
      creative: "conic-gradient(from 150deg, #a855f7, #ec4899, #f43f5e, #a855f7)",
      serene:   "conic-gradient(from 240deg, #10b981, #06b6d4, #8b5cf6, #10b981)",
    };
    const grad = emotionGrad[emotion] || emotionGrad.calm;
    const spinDuration = Math.max(3, 10 - tension * 7);
    const scale = 1 + phi * 0.05;

    return (
      <button
        onClick={() => setState("expanded")}
        title="Open chat"
        className="fixed bottom-8 right-8 z-50 w-[52px] h-[52px] rounded-full flex items-center justify-center select-none group"
        style={{ perspective: "200px" }}
        aria-label="Open Anima chat"
      >
        {/* Outer glow (blurred copy) */}
        <div
          className="absolute inset-[-8px] rounded-full blur-xl opacity-50 group-hover:opacity-70 transition-opacity duration-500"
          style={{
            background: grad,
            animation: `spin ${spinDuration}s linear infinite`,
          }}
        />
        {/* Main orb */}
        <div
          className="absolute inset-0 rounded-full"
          style={{
            background: grad,
            animation: `spin ${spinDuration}s linear infinite`,
            transform: `scale(${scale})`,
            transition: "transform 0.8s ease",
          }}
        />
        {/* Glass overlay (Apple depth) */}
        <div
          className="absolute inset-[3px] rounded-full"
          style={{
            background: "radial-gradient(ellipse at 35% 30%, rgba(255,255,255,0.35) 0%, rgba(255,255,255,0.05) 50%, transparent 70%)",
          }}
        />
        {/* Hover scale */}
        <div
          className="absolute inset-0 rounded-full transition-transform duration-200 group-hover:scale-110"
        />
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
            {/* Typing indicator */}
            {messages.length > 0 && messages[messages.length - 1].role === "user" && (
              <div className="flex items-center gap-1.5 px-4 py-2" style={{ color: "var(--text-tertiary)" }}>
                <div className="w-2 h-2 rounded-full typing-dot" style={{ background: "var(--accent)" }} />
                <div className="w-2 h-2 rounded-full typing-dot" style={{ background: "var(--accent)" }} />
                <div className="w-2 h-2 rounded-full typing-dot" style={{ background: "var(--accent)" }} />
              </div>
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
