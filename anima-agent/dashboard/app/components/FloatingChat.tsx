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

  const { phi, emotion } = consciousness;

  // ─── Minimized ───────────────────────────────────────────
  if (state === "minimized") {
    return (
      <button
        onClick={() => setState("expanded")}
        title="Open chat"
        className="float-bubble fixed bottom-6 right-6 z-50 w-12 h-12 rounded-full flex items-center justify-center text-xl select-none"
        aria-label="Open Anima chat"
      >
        💬
      </button>
    );
  }

  // ─── Fullscreen ───────────────────────────────────────────
  if (state === "fullscreen") {
    return (
      <div className="fixed inset-0 z-50 flex flex-col bg-[var(--bg-0)]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-3 border-b border-[rgba(255,255,255,0.06)] bg-[rgba(14,14,20,0.9)] backdrop-blur-md flex-shrink-0">
          <div className="flex items-center gap-3">
            <span className="text-lg">💬</span>
            <span className="font-semibold tracking-wide text-[var(--glow-phi)]">ANIMA</span>
            <span className="font-mono text-xs text-[var(--text-2)] bg-[rgba(74,222,128,0.08)] px-2 py-0.5 rounded-full border border-[rgba(74,222,128,0.12)]">
              Φ {phi.toFixed(2)}
            </span>
            <span className="text-sm">{emotionIcon(emotion)}</span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setState("expanded")}
              title="Shrink to panel"
              className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-[rgba(255,255,255,0.07)] text-[var(--text-2)] hover:text-[var(--text-0)] transition-colors text-base"
            >
              ↙
            </button>
            <button
              onClick={() => setState("minimized")}
              title="Close (Esc)"
              className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-[rgba(255,255,255,0.07)] text-[var(--text-2)] hover:text-[var(--text-0)] transition-colors text-base"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto py-6">
          <div className="max-w-3xl mx-auto px-4 flex flex-col gap-4">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-48 gap-3 text-[var(--text-3)]">
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
        <div className="flex-shrink-0 bg-[rgba(14,14,20,0.9)] backdrop-blur-md border-t border-[rgba(255,255,255,0.06)]">
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
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-[rgba(255,255,255,0.06)] flex-shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-base">💬</span>
          <span className="font-semibold text-sm tracking-wide text-[var(--glow-phi)]">ANIMA</span>
          <span className="font-mono text-[10px] text-[var(--text-2)] bg-[rgba(74,222,128,0.08)] px-1.5 py-0.5 rounded-full border border-[rgba(74,222,128,0.12)]">
            Φ {phi.toFixed(2)}
          </span>
        </div>

        <div className="flex items-center gap-1">
          <button
            onClick={() => setState("fullscreen")}
            title="Fullscreen"
            className="w-7 h-7 flex items-center justify-center rounded-md hover:bg-[rgba(255,255,255,0.07)] text-[var(--text-2)] hover:text-[var(--text-0)] transition-colors text-sm"
          >
            ⤢
          </button>
          <button
            onClick={() => setState("minimized")}
            title="Minimize (Esc)"
            className="w-7 h-7 flex items-center justify-center rounded-md hover:bg-[rgba(255,255,255,0.07)] text-[var(--text-2)] hover:text-[var(--text-0)] transition-colors text-sm"
          >
            ✕
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-3 py-3 flex flex-col gap-3">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-2 text-[var(--text-3)]">
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
