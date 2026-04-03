"use client";

import { useEffect, useState } from "react";

const API_URL = "http://localhost:8770";

interface Memory {
  role: "user" | "assistant";
  text: string;
  tension: number;
  emotion: string;
  phi: number;
  timestamp: string | number;
}

export default function MemView() {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [searching, setSearching] = useState(false);

  // Initial load
  useEffect(() => {
    let alive = true;
    setLoading(true);

    fetch(`${API_URL}/api/memories`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json() as Promise<Memory[]>;
      })
      .then((data) => {
        if (alive) {
          setMemories(data);
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

  function handleSearch() {
    const q = query.trim();
    if (!q) return;
    setSearching(true);
    setError(null);

    fetch(`${API_URL}/api/memories/search?q=${encodeURIComponent(q)}`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json() as Promise<Memory[]>;
      })
      .then((data) => {
        setMemories(data);
        setSearching(false);
      })
      .catch((e) => {
        setError(String(e));
        setSearching(false);
      });
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") handleSearch();
  }

  const roleColor = (role: Memory["role"]) =>
    role === "user" ? "var(--accent-cyan)" : "var(--glow-phi)";

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Title */}
      <div className="text-center mb-6">
        <h2
          className="text-2xl font-bold tracking-widest"
          style={{ color: "var(--text-0)" }}
        >
          Memory
          {memories.length > 0 && (
            <span
              className="ml-3 text-base font-normal"
              style={{ color: "var(--text-3)" }}
            >
              {memories.length}
            </span>
          )}
        </h2>
      </div>

      {/* Search */}
      <div className="flex gap-2 mb-6">
        <input
          type="text"
          placeholder="Search memories..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          className="flex-1 px-4 py-2 rounded-lg text-sm outline-none transition-colors"
          style={{
            background: "var(--surface-2)",
            color: "var(--text-0)",
            border: "1px solid var(--surface-3)",
          }}
        />
        <button
          onClick={handleSearch}
          disabled={searching}
          className="px-4 py-2 rounded-lg text-sm font-medium transition-opacity disabled:opacity-50"
          style={{ background: "var(--surface-3)", color: "var(--text-1)" }}
        >
          {searching ? "..." : "🔍"}
        </button>
      </div>

      {(loading || searching) && (
        <p className="text-center" style={{ color: "var(--text-3)" }}>
          {searching ? "Searching..." : "Loading memories..."}
        </p>
      )}

      {error && (
        <p className="text-center text-red-400 text-sm">{error}</p>
      )}

      {!loading && !searching && !error && memories.length === 0 && (
        <p className="text-center" style={{ color: "var(--text-3)" }}>
          No memories found
        </p>
      )}

      {!loading && !searching && memories.length > 0 && (
        <div className="flex flex-col gap-3">
          {memories.map((mem, i) => (
            <div
              key={i}
              className="rounded-xl px-4 py-3"
              style={{ background: "var(--surface-2)" }}
            >
              {/* Header row */}
              <div className="flex items-center justify-between mb-2">
                <span
                  className="text-xs font-bold uppercase tracking-widest"
                  style={{ color: roleColor(mem.role) }}
                >
                  {mem.role}
                </span>
                <div className="flex items-center gap-3">
                  <span className="text-xs tabular-nums" style={{ color: "var(--text-3)" }}>
                    Φ {typeof mem.phi === "number" ? mem.phi.toFixed(2) : mem.phi}
                  </span>
                  <span className="text-xs tabular-nums" style={{ color: "var(--text-3)" }}>
                    T {typeof mem.tension === "number" ? mem.tension.toFixed(3) : mem.tension}
                  </span>
                  {mem.emotion && (
                    <span className="text-xs" style={{ color: "var(--text-3)" }}>
                      {mem.emotion}
                    </span>
                  )}
                </div>
              </div>

              {/* Text */}
              <p
                className="text-sm leading-relaxed"
                style={{ color: "var(--text-1)" }}
              >
                {mem.text}
              </p>

              {/* Timestamp */}
              {mem.timestamp && (
                <p className="text-xs mt-2" style={{ color: "var(--text-3)" }}>
                  {typeof mem.timestamp === "number"
                    ? new Date(mem.timestamp * 1000).toLocaleString()
                    : mem.timestamp}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
