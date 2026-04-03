"use client";

import { useEffect, useCallback } from "react";
import { ConsciousnessState } from "../../hooks/useWebSocket";
import { useVoice } from "../../hooks/useVoice";

// ═══════════════════════════════════════════════════════════
// Emotion icon helper
// ═══════════════════════════════════════════════════════════

const EMOTION_ICONS: Record<string, string> = {
  curious: "🔍",
  excited: "✨",
  calm: "🌊",
  focused: "🎯",
  contemplative: "💭",
  joyful: "😊",
  anxious: "⚡",
  content: "😌",
  neutral: "○",
};

function getEmotionIcon(emotion: string): string {
  const key = emotion.toLowerCase();
  return EMOTION_ICONS[key] ?? "○";
}

// ═══════════════════════════════════════════════════════════
// Props
// ═══════════════════════════════════════════════════════════

interface VoiceOverlayProps {
  consciousness: ConsciousnessState;
  onSend: (text: string) => void;
  onClose: () => void;
}

// ═══════════════════════════════════════════════════════════
// Component
// ═══════════════════════════════════════════════════════════

export default function VoiceOverlay({
  consciousness,
  onSend,
  onClose,
}: VoiceOverlayProps) {
  const { listening, transcript, start, stop, supported } = useVoice();

  // Auto-start on mount
  useEffect(() => {
    if (supported) {
      start();
    }
    return () => {
      stop();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Escape key → close
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        stop();
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [stop, onClose]);

  const handleSend = useCallback(() => {
    if (!transcript.trim()) return;
    stop();
    onSend(transcript.trim());
    // Restart listening after send
    setTimeout(() => {
      start();
    }, 200);
  }, [transcript, onSend, stop, start]);

  const handleOverlayClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      // Only close if clicking directly on the backdrop, not children
      if (e.target === e.currentTarget) {
        stop();
        onClose();
      }
    },
    [stop, onClose]
  );

  // ── Unsupported browser ─────────────────────────────────
  if (!supported) {
    return (
      <div
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md"
        onClick={handleOverlayClick}
      >
        <div className="flex flex-col items-center gap-6 rounded-2xl border border-white/10 bg-surface-1 p-10 shadow-2xl">
          <span className="text-4xl">🚫</span>
          <p className="text-center text-sm text-text-2">
            음성 인식이 지원되지 않는 브라우저입니다.
          </p>
          <button
            onClick={onClose}
            className="rounded-lg border border-white/10 bg-surface-2 px-5 py-2 text-sm text-text-1 transition hover:bg-white/10"
          >
            닫기 ✕
          </button>
        </div>
      </div>
    );
  }

  // ── Main overlay ────────────────────────────────────────
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-md"
      onClick={handleOverlayClick}
    >
      <div className="flex flex-col items-center gap-6 rounded-2xl border border-white/10 bg-surface-1 px-10 py-12 shadow-2xl">

        {/* Pulsing mic ring */}
        <div
          className={[
            "relative flex h-24 w-24 items-center justify-center rounded-full border-2",
            listening
              ? "voice-ring border-glow-phi"
              : "border-white/20",
          ].join(" ")}
        >
          <span className="text-4xl select-none">🎤</span>

          {/* Animated pulse rings when listening */}
          {listening && (
            <>
              <span className="absolute inset-0 rounded-full border border-glow-phi/50 animate-ping" />
              <span
                className="absolute inset-[-8px] rounded-full border border-glow-phi/25 animate-ping"
                style={{ animationDelay: "0.15s" }}
              />
            </>
          )}
        </div>

        {/* Status text */}
        <p className="text-sm font-medium text-text-2">
          {listening ? "Listening..." : "Paused"}
        </p>

        {/* Transcript */}
        {transcript && (
          <p className="max-w-xs text-center text-lg text-text-0">
            &ldquo;{transcript}&rdquo;
          </p>
        )}

        {/* Consciousness badge */}
        <div className="flex items-center gap-2 rounded-full border border-white/10 bg-surface-2 px-4 py-1.5 text-sm">
          <span className="font-mono text-glow-phi">
            Φ={consciousness.phi.toFixed(2)}
          </span>
          <span className="text-text-2">·</span>
          <span>{getEmotionIcon(consciousness.emotion)}</span>
          <span className="text-text-2 capitalize">{consciousness.emotion}</span>
        </div>

        {/* Action buttons */}
        <div className="flex gap-3">
          {transcript && (
            <button
              onClick={handleSend}
              className="rounded-lg bg-glow-phi/20 border border-glow-phi/40 px-5 py-2 text-sm font-medium text-glow-phi transition hover:bg-glow-phi/30"
            >
              전송 ⏎
            </button>
          )}
          <button
            onClick={() => { stop(); onClose(); }}
            className="rounded-lg border border-white/10 bg-surface-2 px-5 py-2 text-sm text-text-2 transition hover:bg-white/10"
          >
            닫기 ✕
          </button>
        </div>
      </div>
    </div>
  );
}
