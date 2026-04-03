"use client";

import { useState } from "react";
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
      />

      <main className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-4 py-6">{renderView()}</div>
      </main>

      <FloatingChat
        messages={messages}
        consciousness={consciousness}
        onSend={sendMessage}
        onVoice={() => setShowVoice(true)}
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
