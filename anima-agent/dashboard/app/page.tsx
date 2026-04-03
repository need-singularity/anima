"use client";

import { useState, useEffect } from "react";
import { useWebSocket } from "../hooks/useWebSocket";
import Header, { type TabId } from "./components/Header";
import FloatingChat from "./components/FloatingChat";
import VoiceOverlay from "./components/VoiceOverlay";
import DashView from "./components/views/DashView";
import EvoView from "./components/views/EvoView";
import LawsView from "./components/views/LawsView";
import MemView from "./components/views/MemView";
import ToolsView from "./components/views/ToolsView";

export default function Page() {
  const { consciousness, trading, events, messages, connected, sendMessage } =
    useWebSocket();
  const [tab, setTab] = useState<TabId>("Dash");
  const [showVoice, setShowVoice] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // Cmd+K or Ctrl+K → toggle chat
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setChatOpen(prev => !prev);
      }
      // 1-5 → switch tabs
      if (!e.metaKey && !e.ctrlKey && !e.altKey) {
        const tabMap: Record<string, typeof tab> = { "1": "Dash", "2": "Evo", "3": "Laws", "4": "Mem", "5": "Tools" };
        const target = document.activeElement?.tagName;
        if (target !== "INPUT" && target !== "TEXTAREA" && tabMap[e.key]) {
          setTab(tabMap[e.key]);
        }
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  const renderView = () => {
    switch (tab) {
      case "Dash":
        return (
          <DashView
            consciousness={consciousness}
            trading={trading}
            events={events}
          />
        );
      case "Evo":
        return <EvoView />;
      case "Laws":
        return <LawsView />;
      case "Mem":
        return <MemView />;
      case "Tools":
        return <ToolsView consciousness={consciousness} />;
    }
  };

  return (
    <div className="h-screen flex flex-col">
      <Header
        connected={connected}
        activeTab={tab}
        onTabChange={setTab}
        onVoice={() => setShowVoice(true)}
        phi={consciousness.phi}
      />

      <main className="flex-1 overflow-y-auto" style={{ background: "var(--bg-primary)" }}>
        <div className="max-w-3xl mx-auto px-6 py-10" key={tab} style={{ animation: "section-in 0.4s cubic-bezier(0.2,0.8,0.2,1)" }}>
          {renderView()}
        </div>
      </main>

      <FloatingChat
        messages={messages}
        consciousness={consciousness}
        onSend={sendMessage}
        onVoice={() => setShowVoice(true)}
        forceOpen={chatOpen}
        onStateChange={(s) => setChatOpen(s !== "minimized")}
      />

      {showVoice && (
        <VoiceOverlay
          consciousness={consciousness}
          onSend={(text) => {
            sendMessage(text);
            setShowVoice(false);
          }}
          onClose={() => setShowVoice(false)}
        />
      )}
    </div>
  );
}
