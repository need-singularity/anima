"use client";

import { useEffect, useState } from "react";

const API_URL = "http://localhost:8770";

interface EvoData {
  stage: string;
  gen: number;
  laws_total: number;
  laws_new: number;
  topology: string;
  phi: number;
  status: string;
}

export default function EvoView() {
  const [data, setData] = useState<EvoData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;

    async function poll() {
      try {
        const res = await fetch(`${API_URL}/api/evolution`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json: EvoData = await res.json();
        if (alive) {
          setData(json);
          setError(null);
        }
      } catch (e) {
        if (alive) setError(String(e));
      }
    }

    poll();
    const id = setInterval(poll, 5000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Title */}
      <div className="text-center mb-8">
        <h2
          className="text-2xl font-bold tracking-widest"
          style={{ color: "var(--glow-phi)", textShadow: "0 0 12px var(--glow-phi)" }}
        >
          OUROBOROS
        </h2>
        <p className="text-sm mt-1" style={{ color: "var(--text-3)" }}>
          Infinite Self-Evolution
        </p>
      </div>

      {!data && !error && (
        <p className="text-center" style={{ color: "var(--text-3)" }}>
          Loading evolution data...
        </p>
      )}

      {error && (
        <p className="text-center text-red-400 text-sm">{error}</p>
      )}

      {data && (
        <>
          {/* 3-card grid */}
          <div className="grid grid-cols-3 gap-4 mb-8">
            {/* Generation */}
            <div
              className="rounded-xl p-6 flex flex-col items-center gap-1"
              style={{ background: "var(--surface-2)" }}
            >
              <span
                className="text-4xl font-bold tabular-nums"
                style={{ color: "var(--glow-phi)", textShadow: "0 0 10px var(--glow-phi)" }}
              >
                {data.gen.toLocaleString()}
              </span>
              <span className="text-xs uppercase tracking-widest" style={{ color: "var(--text-3)" }}>
                Generation
              </span>
            </div>

            {/* Laws */}
            <div
              className="rounded-xl p-6 flex flex-col items-center gap-1"
              style={{ background: "var(--surface-2)" }}
            >
              <span
                className="text-4xl font-bold tabular-nums"
                style={{ color: "var(--text-0)" }}
              >
                {data.laws_total.toLocaleString()}
              </span>
              <span className="text-xs uppercase tracking-widest" style={{ color: "var(--text-3)" }}>
                Laws
              </span>
            </div>

            {/* Phi */}
            <div
              className="rounded-xl p-6 flex flex-col items-center gap-1"
              style={{ background: "var(--surface-2)" }}
            >
              <span
                className="text-4xl font-bold tabular-nums"
                style={{ color: "var(--accent-cyan)", textShadow: "0 0 10px var(--accent-cyan)" }}
              >
                {typeof data.phi === "number" ? data.phi.toFixed(2) : data.phi}
              </span>
              <span className="text-xs uppercase tracking-widest" style={{ color: "var(--text-3)" }}>
                Φ
              </span>
            </div>
          </div>

          {/* Key-value list */}
          <div
            className="rounded-xl divide-y"
            style={{ background: "var(--surface-2)", borderColor: "var(--surface-3)" }}
          >
            {[
              { label: "Stage", value: data.stage },
              { label: "Topology", value: data.topology },
              {
                label: "New Laws",
                value: (
                  <span style={{ color: data.laws_new > 0 ? "#4ade80" : "var(--text-2)" }}>
                    {data.laws_new > 0 ? `+${data.laws_new}` : data.laws_new}
                  </span>
                ),
              },
              { label: "Status", value: data.status },
            ].map(({ label, value }) => (
              <div
                key={label}
                className="flex items-center justify-between px-5 py-3"
                style={{ borderColor: "var(--surface-3)" }}
              >
                <span className="text-xs uppercase tracking-wider" style={{ color: "var(--text-3)" }}>
                  {label}
                </span>
                <span className="text-sm font-medium" style={{ color: "var(--text-1)" }}>
                  {value}
                </span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
