"use client";

import { useEffect } from "react";
import type { ConsciousnessState } from "../../hooks/useWebSocket";
import { useVoice } from "../../hooks/useVoice";

interface VoiceOverlayProps {
  consciousness: ConsciousnessState;
  onSend: (text: string) => void;
  onClose: () => void;
}

export default function VoiceOverlay({ consciousness, onSend, onClose }: VoiceOverlayProps) {
  const { listening, transcript, start, stop, supported } = useVoice();

  useEffect(() => {
    if (supported) start();
    const handleKey = (e: KeyboardEvent) => { if (e.key === "Escape") { stop(); onClose(); } };
    window.addEventListener("keydown", handleKey);
    return () => { stop(); window.removeEventListener("keydown", handleKey); };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSend = () => {
    if (transcript.trim()) { onSend(transcript.trim()); start(); }
  };

  if (!supported) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: "var(--bg-primary)" }}>
        <div className="text-center">
          <p className="text-[15px]" style={{ color: "var(--text-secondary)" }}>음성 인식이 지원되지 않는 브라우저입니다.</p>
          <button onClick={onClose} className="mt-6 text-[13px] font-medium px-5 py-2.5 rounded-full"
            style={{ background: "var(--bg-tertiary)", color: "var(--text-primary)" }}>닫기</button>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex flex-col items-center justify-center"
      style={{ background: "var(--bg-primary)" }}
      onClick={(e) => { if (e.target === e.currentTarget) { stop(); onClose(); } }}>

      {/* Animated rings */}
      <div className="relative w-32 h-32 mb-10">
        {/* Outer ring — conic gradient (matches orb) */}
        <div className={`absolute inset-0 rounded-full ${listening ? "voice-ring" : ""}`}
          style={{
            background: "conic-gradient(from 180deg, #34d399, #06b6d4, #8b5cf6, #34d399)",
            opacity: listening ? 0.3 : 0.1,
            animation: listening ? "spin 4s linear infinite, voice-pulse 1.5s ease-in-out infinite" : "none",
          }} />
        {/* Inner glass */}
        <div className="absolute inset-3 rounded-full flex items-center justify-center"
          style={{ background: "var(--bg-secondary)" }}>
          <span className="text-4xl">{listening ? "🎤" : "⏸"}</span>
        </div>
      </div>

      {/* Status */}
      <p className="text-[15px] mb-3" style={{ color: "var(--text-secondary)" }}>
        {listening ? "Listening..." : "Paused"}
      </p>

      {/* Transcript */}
      {transcript && (
        <p className="text-[22px] font-medium max-w-md text-center mb-6 leading-relaxed"
          style={{ color: "var(--text-primary)" }}>
          &ldquo;{transcript}&rdquo;
        </p>
      )}

      {/* Consciousness badge */}
      <div className="text-[12px] font-mono mb-12" style={{ color: "var(--text-tertiary)" }}>
        Φ={consciousness.phi.toFixed(2)} · {consciousness.emotion}
      </div>

      {/* Buttons */}
      <div className="flex gap-3">
        {transcript && (
          <button onClick={handleSend}
            className="px-6 py-2.5 rounded-full text-[14px] font-medium transition-all"
            style={{ background: "var(--accent)", color: "#fff" }}>
            전송
          </button>
        )}
        <button onClick={() => { stop(); onClose(); }}
          className="px-6 py-2.5 rounded-full text-[14px] font-medium transition-all"
          style={{ background: "var(--bg-tertiary)", color: "var(--text-primary)" }}>
          닫기
        </button>
      </div>
    </div>
  );
}
