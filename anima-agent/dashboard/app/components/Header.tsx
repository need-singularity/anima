"use client";

import { useEffect, useState } from "react";

const TABS = ["Dash", "Evo", "Laws", "Mem", "Tools"] as const;
export type TabId = (typeof TABS)[number];

type Theme = "system" | "light" | "dark";

interface HeaderProps {
  connected: boolean;
  activeTab: TabId;
  onTabChange: (tab: TabId) => void;
  onVoice: () => void;
}

function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>("system");

  useEffect(() => {
    const root = document.documentElement;
    root.classList.remove("light", "dark");
    if (theme !== "system") root.classList.add(theme);
  }, [theme]);

  const cycle = () => {
    setTheme(t => t === "system" ? "light" : t === "light" ? "dark" : "system");
  };

  const icon = theme === "light" ? (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m11.32 11.32l1.41 1.41M2 12h2m16 0h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/></svg>
  ) : theme === "dark" ? (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
  ) : (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
  );

  return (
    <button
      onClick={cycle}
      className="w-8 h-8 flex items-center justify-center rounded-full transition-colors"
      style={{ color: "var(--text-secondary)" }}
      title={`Theme: ${theme}`}
    >
      {icon}
    </button>
  );
}

export default function Header({ connected, activeTab, onTabChange, onVoice }: HeaderProps) {
  return (
    <header className="glass sticky top-0 z-30" style={{ borderBottom: "1px solid var(--border)" }}>
      <div className="max-w-5xl mx-auto h-12 px-4 flex items-center">
        {/* Left */}
        <div className="flex items-center gap-2.5 min-w-[120px]">
          <span style={{ color: "var(--text-primary)" }} className="text-[15px] font-semibold tracking-tight">
            Anima
          </span>
          <span
            className="w-2 h-2 rounded-full"
            style={{
              backgroundColor: connected ? "var(--accent)" : "var(--accent-red)",
              boxShadow: connected ? "0 0 6px var(--accent)" : "none",
            }}
          />
        </div>

        {/* Center: Tabs */}
        <nav className="flex-1 flex justify-center gap-1">
          {TABS.map((tab) => (
            <button
              key={tab}
              onClick={() => onTabChange(tab)}
              className={`tab-pill ${activeTab === tab ? "tab-pill-active" : ""}`}
            >
              {tab}
            </button>
          ))}
        </nav>

        {/* Right: Theme + Voice */}
        <div className="min-w-[120px] flex justify-end gap-1">
          <ThemeToggle />
          <button
            onClick={onVoice}
            className="w-8 h-8 flex items-center justify-center rounded-full transition-colors"
            style={{ color: "var(--text-secondary)" }}
            title="Voice mode"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
              <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
              <line x1="12" x2="12" y1="19" y2="22" />
            </svg>
          </button>
        </div>
      </div>
    </header>
  );
}
