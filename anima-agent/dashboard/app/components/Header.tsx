"use client";

export type TabId = "Dash" | "Evo" | "Laws" | "Mem" | "Tools";

const TABS: TabId[] = ["Dash", "Evo", "Laws", "Mem", "Tools"];

interface HeaderProps {
  connected: boolean;
  activeTab: TabId;
  onTabChange: (tab: TabId) => void;
  onVoice: () => void;
}

export default function Header({
  connected,
  activeTab,
  onTabChange,
  onVoice,
}: HeaderProps) {
  return (
    <header className="h-12 px-4 border-b border-surface-3/40 bg-surface-1/80 backdrop-blur-sm flex items-center justify-between">
      {/* Left: Logo + connection status */}
      <div className="flex items-center gap-2 min-w-[80px]">
        <span className="text-sm font-semibold tracking-widest text-[var(--text-0)]">
          ANIMA
        </span>
        <div className="flex items-center gap-1.5">
          {connected ? (
            <span
              className="w-1.5 h-1.5 rounded-full bg-glow-phi"
              style={{ boxShadow: "0 0 6px var(--glow-phi)" }}
            />
          ) : (
            <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse" />
          )}
          <span className="text-xs text-[var(--text-3)]">
            {connected ? "live" : "..."}
          </span>
        </div>
      </div>

      {/* Center: Tab navigation */}
      <nav className="flex items-center gap-1">
        {TABS.map((tab) => {
          const isActive = tab === activeTab;
          return (
            <button
              key={tab}
              onClick={() => onTabChange(tab)}
              className={[
                "px-3 py-1 rounded text-xs font-medium transition-colors",
                isActive
                  ? "text-glow-phi bg-glow-phi/10"
                  : "text-[var(--text-2)] hover:text-[var(--text-1)] hover:bg-surface-3/30",
              ].join(" ")}
            >
              {tab}
            </button>
          );
        })}
      </nav>

      {/* Right: Voice mode button */}
      <div className="flex items-center justify-end min-w-[80px]">
        <button
          onClick={onVoice}
          aria-label="Voice mode"
          className="w-8 h-8 flex items-center justify-center rounded-full text-base text-[var(--text-2)] hover:text-[var(--text-0)] hover:bg-surface-3/40 transition-colors"
        >
          🔊
        </button>
      </div>
    </header>
  );
}
