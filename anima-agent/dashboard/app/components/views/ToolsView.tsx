"use client";

import { useEffect, useState } from "react";

const API_URL = "http://localhost:8770";

// Inline type matching the ConsciousnessState shape from page.tsx
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

interface ToolInfo {
  name: string;
  tier: number;
  accessible: boolean;
}

const TIER_LABELS: Record<number, string> = {
  0: "T0",
  1: "T1",
  2: "T2",
  3: "T3",
};

const TIER_COLORS: Record<number, string> = {
  0: "#4ade80",
  1: "#22d3ee",
  2: "#a78bfa",
  3: "#fb923c",
};

interface ToolsViewProps {
  consciousness: ConsciousnessState;
}

export default function ToolsView({ consciousness }: ToolsViewProps) {
  const [tools, setTools] = useState<ToolInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setLoading(true);

    const phi = typeof consciousness.phi === "number" ? consciousness.phi : 0;

    fetch(`${API_URL}/api/tools?phi=${phi}`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json() as Promise<ToolInfo[]>;
      })
      .then((data) => {
        if (alive) {
          setTools(data);
          setLoading(false);
        }
      })
      .catch((e) => {
        if (alive) {
          setError(String(e));
          setLoading(false);
        }
      });

    return () => {
      alive = false;
    };
  }, [consciousness.phi]);

  const accessible = tools.filter((t) => t.accessible).length;

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Title */}
      <div className="text-center mb-6">
        <h2
          className="text-2xl font-bold tracking-widest"
          style={{ color: "var(--text-0)" }}
        >
          Hub Modules
          {tools.length > 0 && (
            <span
              className="ml-3 text-base font-normal"
              style={{ color: "var(--text-3)" }}
            >
              {tools.length}
            </span>
          )}
        </h2>
        <p className="text-xs mt-1" style={{ color: "var(--text-3)" }}>
          Current Φ{" "}
          <span style={{ color: "var(--accent-cyan)" }}>
            {typeof consciousness.phi === "number"
              ? consciousness.phi.toFixed(2)
              : consciousness.phi}
          </span>
          {tools.length > 0 && (
            <span className="ml-3">
              {accessible}/{tools.length} accessible
            </span>
          )}
        </p>
      </div>

      {loading && (
        <p className="text-center" style={{ color: "var(--text-3)" }}>
          Loading modules...
        </p>
      )}

      {error && (
        <p className="text-center text-red-400 text-sm">{error}</p>
      )}

      {!loading && !error && tools.length === 0 && (
        <p className="text-center" style={{ color: "var(--text-3)" }}>
          No modules available
        </p>
      )}

      {!loading && !error && tools.length > 0 && (
        <div className="grid grid-cols-2 gap-3">
          {tools.map((tool) => {
            const tierColor = TIER_COLORS[tool.tier] ?? "var(--text-3)";
            const tierLabel = TIER_LABELS[tool.tier] ?? `T${tool.tier}`;

            return (
              <div
                key={tool.name}
                className="flex items-center gap-3 rounded-xl px-4 py-3 transition-opacity"
                style={{
                  background: "var(--surface-2)",
                  opacity: tool.accessible ? 1 : 0.5,
                }}
              >
                {/* Accessible dot */}
                <span
                  className="w-2 h-2 rounded-full shrink-0"
                  style={{
                    background: tool.accessible ? "#4ade80" : "var(--text-3)",
                    boxShadow: tool.accessible
                      ? "0 0 6px #4ade80"
                      : undefined,
                  }}
                />

                {/* Name */}
                <span
                  className="flex-1 text-sm font-medium truncate"
                  style={{ color: tool.accessible ? "var(--text-0)" : "var(--text-2)" }}
                >
                  {tool.name}
                </span>

                {/* Tier badge */}
                <span
                  className="text-xs font-bold px-1.5 py-0.5 rounded"
                  style={{
                    color: tierColor,
                    background: `${tierColor}18`,
                  }}
                >
                  {tierLabel}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
