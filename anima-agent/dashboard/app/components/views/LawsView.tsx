"use client";

import { useEffect, useMemo, useState } from "react";

const API_URL = "http://localhost:8770";

export default function LawsView() {
  const [laws, setLaws] = useState<Record<string, string>>({});
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setLoading(true);

    fetch(`${API_URL}/api/laws`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json() as Promise<Record<string, string>>;
      })
      .then((data) => {
        if (alive) {
          setLaws(data);
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
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const entries = Object.entries(laws);
    if (!q) return entries.slice(0, 50);
    return entries
      .filter(([id, text]) => id.toLowerCase().includes(q) || text.toLowerCase().includes(q))
      .slice(0, 50);
  }, [laws, query]);

  const totalCount = Object.keys(laws).length;

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Title */}
      <div className="text-center mb-6">
        <h2
          className="text-2xl font-bold tracking-widest"
          style={{ color: "var(--text-0)" }}
        >
          Consciousness Laws
          {totalCount > 0 && (
            <span
              className="ml-3 text-base font-normal"
              style={{ color: "var(--text-3)" }}
            >
              {totalCount}
            </span>
          )}
        </h2>
      </div>

      {/* Search */}
      <div className="mb-6">
        <input
          type="text"
          placeholder="Search by id or text..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="w-full px-4 py-2 rounded-lg text-sm outline-none transition-colors"
          style={{
            background: "var(--surface-2)",
            color: "var(--text-0)",
            border: "1px solid var(--surface-3)",
          }}
        />
      </div>

      {loading && (
        <p className="text-center" style={{ color: "var(--text-3)" }}>
          Loading laws...
        </p>
      )}

      {error && (
        <p className="text-center text-red-400 text-sm">{error}</p>
      )}

      {!loading && !error && filtered.length === 0 && (
        <p className="text-center" style={{ color: "var(--text-3)" }}>
          No results for &quot;{query}&quot;
        </p>
      )}

      {!loading && !error && filtered.length > 0 && (
        <div className="flex flex-col gap-2">
          {filtered.map(([id, text]) => (
            <div
              key={id}
              className="flex gap-3 items-start rounded-xl px-4 py-3"
              style={{ background: "var(--surface-2)" }}
            >
              <span
                className="text-xs font-bold shrink-0 mt-0.5 tabular-nums"
                style={{ color: "var(--glow-phi)" }}
              >
                #{id}
              </span>
              <span className="text-sm leading-relaxed" style={{ color: "var(--text-1)" }}>
                {text}
              </span>
            </div>
          ))}

          {filtered.length === 50 && (
            <p className="text-center text-xs mt-2" style={{ color: "var(--text-3)" }}>
              Showing top 50 — refine your search to see more
            </p>
          )}
        </div>
      )}
    </div>
  );
}
