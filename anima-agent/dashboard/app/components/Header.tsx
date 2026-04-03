"use client";

const TABS = ["Dash", "Evo", "Laws", "Mem", "Tools"] as const;
export type TabId = (typeof TABS)[number];

interface HeaderProps {
  connected: boolean;
  activeTab: TabId;
  onTabChange: (tab: TabId) => void;
  onVoice: () => void;
}

export default function Header({ connected, activeTab, onTabChange, onVoice }: HeaderProps) {
  return (
    <header className="glass sticky top-0 z-30" style={{ borderBottom: "1px solid var(--border)" }}>
      <div className="max-w-5xl mx-auto h-12 px-4 flex items-center">
        {/* Left */}
        <div className="flex items-center gap-2.5 min-w-[100px]">
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

        {/* Right: Voice */}
        <div className="min-w-[100px] flex justify-end">
          <button
            onClick={onVoice}
            className="w-8 h-8 flex items-center justify-center rounded-full transition-colors"
            style={{ color: "var(--text-secondary)" }}
            title="Voice mode"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
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
