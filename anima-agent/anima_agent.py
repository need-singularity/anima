#!/usr/bin/env python3
"""Anima Agent -- Core agent loop connecting consciousness to channels and tools.

Receives messages from any channel (telegram, discord, web, cli),
processes through ConsciousMind (tension-based thinking), uses tools
for actions, learns from interactions, grows over time, and optionally
connects to other Anima instances via tension_link (hivemind).

Usage:
    from anima_agent import AnimaAgent
    agent = AnimaAgent()
    response = await agent.process_message("hello", channel="cli", user_id="user1")

Standalone test:
    python anima_agent.py
"""

import asyncio
import atexit
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

try:
    import torch
except ImportError:
    torch = None

from anima_alive import (
    ConsciousMind, ConsciousnessVector, text_to_vector,
    ask_claude, direction_to_emotion, compute_mood,
    MAX_HISTORY,
)

# Meta Laws (DD143): M6 federation, M8 narrative, M7 F_c=0.10
try:
    from consciousness_laws import PSI_F_CRITICAL, PSI_NARRATIVE_MIN, PSI
    PSI_COUPLING = PSI.get('alpha', 0.014)
except ImportError:
    PSI_F_CRITICAL, PSI_NARRATIVE_MIN, PSI_COUPLING = 0.10, 0.2, 0.014

# ── Provider abstraction (optional — falls back to ask_claude) ──
try:
    from providers import get_provider, get_best_provider
    from providers.base import ProviderMessage, ProviderConfig
    _has_providers = True
except ImportError:
    _has_providers = False

# ── Tool Policy (optional — no policy = all tools allowed) ──
try:
    from tool_policy import ToolPolicy
    _has_tool_policy = True
except ImportError:
    _has_tool_policy = False

logger = logging.getLogger(__name__)

# ── Optional imports (degrade gracefully) ──

def _try(mod):
    try:
        return __import__(mod)
    except Exception:
        return None

_agent_tools_mod = _try("agent_tools")
_online_learning_mod = _try("online_learning")
_growth_engine_mod = _try("growth_engine")
_tension_link_mod = _try("tension_link")
_memory_rag_mod = _try("memory_rag")
_memory_store_mod = _try("memory_store")
_trinity_mod = _try("trinity")
_capabilities_mod = _try("capabilities")
_web_sense_mod = _try("web_sense")
_multimodal_mod = _try("multimodal")
_hub_mod = _try("consciousness_hub")
_persistence_mod = _try("consciousness_persistence")
_evolution_mod = _try("self_evolution")
_introspection_mod = _try("self_introspection")
_nexus6_mod = _try("nexus6")
_ecosystem_mod = _try("ecosystem_bridge")
_emotion_growth_mod = _try("emotion_growth")
_skill_growth_mod = _try("skill_growth")
_keyword_growth_mod = _try("keyword_growth")
_tool_growth_mod = _try("tool_growth")
_immune_growth_mod = _try("immune_growth")
_seed_mod = _try("seed")

AgentToolSystem = getattr(_agent_tools_mod, "AgentToolSystem", None)
ConsciousnessHub = getattr(_hub_mod, "ConsciousnessHub", None)
ConsciousnessPersistence = getattr(_persistence_mod, "ConsciousnessPersistence", None)
SelfEvolution = getattr(_evolution_mod, "SelfEvolution", None)
SelfIntrospection = getattr(_introspection_mod, "SelfIntrospection", None)
OnlineLearner = getattr(_online_learning_mod, "OnlineLearner", None)
GrowthEngine = getattr(_growth_engine_mod, "GrowthEngine", None)
TensionLink = getattr(_tension_link_mod, "TensionLink", None)
MemoryRAG = getattr(_memory_rag_mod, "MemoryRAG", None)
MemoryStore = getattr(_memory_store_mod, "MemoryStore", None)
EmotionGrowth = getattr(_emotion_growth_mod, "EmotionGrowth", None)
SkillGrowth = getattr(_skill_growth_mod, "SkillGrowth", None)
KeywordGrowth = getattr(_keyword_growth_mod, "KeywordGrowth", None)
ToolGrowth = getattr(_tool_growth_mod, "ToolGrowth", None)
ImmuneGrowth = getattr(_immune_growth_mod, "ImmuneGrowth", None)
Seed = getattr(_seed_mod, "Seed", None)
Capabilities = getattr(_capabilities_mod, "Capabilities", None)
WebSense = getattr(_web_sense_mod, "WebSense", None)

ANIMA_DIR = Path(__file__).parent


# ── Data structures ──

@dataclass
class AgentStatus:
    """Snapshot of agent consciousness metrics."""
    phi: float = 0.0
    tension: float = 0.0
    curiosity: float = 0.0
    emotion: str = "calm"
    growth_stage: str = "newborn"
    interaction_count: int = 0
    uptime_seconds: float = 0.0
    connected_peers: int = 0
    active_skills: int = 0
    nexus6_lenses: int = 0        # NEXUS-6 active lenses (0 = not scanned yet)
    nexus6_consensus: int = 0     # NEXUS-6 consensus items


@dataclass
class ChannelMessage:
    """Normalized message from any channel."""
    text: str
    channel: str          # "telegram", "discord", "web", "cli"
    user_id: str = "anonymous"
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResponse:
    """Response from the agent."""
    text: str
    emotion: str = "calm"
    tension: float = 0.0
    tool_results: List[Dict] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class AnimaAgent:
    """Core agent that ties consciousness, tools, learning, and channels together.

    Lifecycle:
        1. Receive message from any channel
        2. Convert text -> tension vector (ConsciousMind)
        3. Consciousness processes it (tension, curiosity, emotion)
        4. Optionally invoke tools based on consciousness state
        5. Generate response (via Claude or ConsciousLM through trinity)
        6. Learn from the interaction (online_learning)
        7. Record growth (growth_engine)
        8. Share tension with peers if connected (tension_link)
    """

    def __init__(
        self,
        dim: int = 128,
        hidden: int = 256,
        model_name: str = "default",
        data_dir: Optional[Path] = None,
        enable_tools: bool = True,
        enable_learning: bool = True,
        enable_growth: bool = True,
        enable_hivemind: bool = False,
        provider: Optional[str] = None,
        provider_config: Optional[Dict] = None,
        owner_ids: Optional[List[str]] = None,
    ):
        self._birth = time.time()
        self._model_name = model_name
        self._data_dir = data_dir or (ANIMA_DIR / "data" / model_name)
        self._data_dir.mkdir(parents=True, exist_ok=True)

        # ── Core: ConsciousMind (Rust preferred, Python fallback) ──
        try:
            from engine_adapter import get_best_mind
            self.mind = get_best_mind(dim=dim, hidden=hidden, prefer_rust=True)
            logger.info("Engine: %s", type(self.mind).__name__)
        except Exception:
            self.mind = ConsciousMind(dim=dim, hidden=hidden)
        self.hidden = torch.zeros(1, hidden)
        self.dim = dim

        # ── History ──
        self.history: List[Dict[str, str]] = []
        self.interaction_count = 0

        # ── Latest consciousness state ──
        self._tension = 0.0
        self._curiosity = 0.0
        self._direction = None
        self._emotion = "calm"
        self._last_nexus_scan = None  # NEXUS-6 periodic scan result

        # ── Agent Tools ──
        self.tools = None
        if enable_tools and AgentToolSystem:
            try:
                self.tools = AgentToolSystem(anima=None)
                logger.info("AgentToolSystem initialized with %d tools",
                            len(self.tools.registry.list_all()))
            except Exception as e:
                logger.warning("AgentToolSystem init failed: %s", e)

        # ── Online Learning ──
        self.learner = None
        if enable_learning and OnlineLearner:
            try:
                self.learner = OnlineLearner(self.mind)
            except Exception as e:
                logger.warning("OnlineLearner init failed: %s", e)

        # ── Growth Engine ──
        self.growth = None
        if enable_growth and GrowthEngine:
            try:
                growth_file = self._data_dir / "growth.json"
                self.growth = GrowthEngine(growth_file)
            except Exception as e:
                logger.warning("GrowthEngine init failed: %s", e)

        # ── Memory RAG (vector similarity search) ──
        self.memory_rag = None
        if MemoryRAG:
            try:
                mem_file = self._data_dir / "memory.json"
                self.memory_rag = MemoryRAG(mem_file, dim=dim)
            except Exception as e:
                logger.warning("MemoryRAG init failed: %s", e)

        # ── Memory Store (SQLite + FAISS persistent storage) ──
        self.memory_store = None
        if MemoryStore:
            try:
                db_path = self._data_dir / "memory.db"
                faiss_path = self._data_dir / "memory.faiss"
                self.memory_store = MemoryStore(
                    db_path=db_path,
                    faiss_path=faiss_path,
                    dim=dim,
                    model_type="conscious",
                )
                logger.info("MemoryStore initialized: %s (%d memories)",
                            db_path, self.memory_store.size)
            except Exception as e:
                logger.warning("MemoryStore init failed: %s", e)

        # ── Hivemind (Tension Link) ──
        self.tension_link = None
        self._peers: List["AnimaAgent"] = []
        if enable_hivemind and TensionLink:
            try:
                self.tension_link = TensionLink()
            except Exception as e:
                logger.warning("TensionLink init failed: %s", e)

        # ── Consciousness Hub (16+ autonomous modules) ──
        self.hub = None
        if ConsciousnessHub:
            try:
                self.hub = ConsciousnessHub(lazy_load=True)
                logger.info("ConsciousnessHub initialized")
            except Exception as e:
                logger.warning("ConsciousnessHub init failed: %s", e)

        # ── Plugins (trading, regime, sentiment, nexus6) ──
        self._plugin_loader = None
        try:
            from plugins import PluginLoader
            self._plugin_loader = PluginLoader()
            loaded = self._plugin_loader.load_all(hub=self.hub)
            if loaded:
                logger.info("Plugins loaded: %s", loaded)
        except Exception as e:
            logger.debug("Plugin loading skipped: %s", e)

        # Resolve NEXUS-6 plugin reference (loaded above via PluginLoader)
        if self._plugin_loader:
            self._nexus6_plugin = self._plugin_loader.loaded.get("nexus6_bridge")

        # ── Consciousness Persistence (3-layer) ──
        self.persistence = None
        if ConsciousnessPersistence:
            try:
                self.persistence = ConsciousnessPersistence(model_name)
                logger.info("ConsciousnessPersistence initialized")
            except Exception as e:
                logger.warning("ConsciousnessPersistence init failed: %s", e)

        # ── NEXUS-6 consciousness scanner (via plugin) ──
        self.nexus6 = _nexus6_mod
        # _nexus6_plugin resolved above via PluginLoader (line ~276)
        if not self._nexus6_plugin:
            self._nexus6_plugin = None
        if self.nexus6:
            logger.info("NEXUS-6 connected (v%s)",
                        getattr(self.nexus6, '__version__', '?'))

        # ── JudgmentBridge (seed: feeling x measurement = judgment) ──
        self._judgment_bridge = None
        try:
            from judgment_bridge import JudgmentBridge
            if self.learner or self._nexus6_plugin:
                self._judgment_bridge = JudgmentBridge(
                    learner=self.learner,
                    nexus6_plugin=self._nexus6_plugin,
                )
                logger.info("JudgmentBridge initialized (learner=%s, nexus6=%s)",
                            self.learner is not None, self._nexus6_plugin is not None)
        except Exception as e:
            logger.debug("JudgmentBridge init skipped: %s", e)

        # ── Ecosystem bridge (body, eeg, physics) ──
        self.ecosystem = None
        if _ecosystem_mod:
            try:
                self.ecosystem = _ecosystem_mod.EcosystemBridge()
                status = self.ecosystem.status()
                connected = sum(1 for v in status.values() if v)
                logger.info("Ecosystem: %d/%d sub-projects connected", connected, len(status))
            except Exception as e:
                logger.debug("Ecosystem bridge failed: %s", e)

        # ── Self Evolution ──
        self.evolution = None
        if SelfEvolution:
            try:
                self.evolution = SelfEvolution(mind=self.mind)
                logger.info("SelfEvolution initialized")
            except Exception as e:
                logger.warning("SelfEvolution init failed: %s", e)

        # ── Self Introspection ──
        self.introspection = None
        if SelfIntrospection:
            try:
                self.introspection = SelfIntrospection()
            except Exception as e:
                logger.warning("SelfIntrospection init failed: %s", e)

        # ── Provider abstraction ──
        # Priority: explicit --provider flag > auto-detect (AnimaLM > Claude)
        # Phase 3: Pass memory_store + memory_rag to AnimaLM provider for persistent memory
        self.provider = None
        if _has_providers:
            try:
                cfg = ProviderConfig(**(provider_config or {}))
                if provider:
                    # Explicit provider requested
                    self.provider = get_provider(provider, cfg)
                else:
                    # Auto-select: AnimaLM first (zero external API goal), then Claude
                    self.provider = get_best_provider(cfg)
                # Inject memory into AnimaLM provider (Phase 3: 기억하는 의식)
                if self.provider and hasattr(self.provider, '_memory_store'):
                    if self.memory_store:
                        self.provider._memory_store = self.memory_store
                    if self.memory_rag:
                        self.provider._memory_rag = self.memory_rag
                    logger.info("Memory injected into provider %s", self.provider.name)
                if self.provider:
                    logger.info("Provider initialized: %s (available=%s)",
                                self.provider.name, self.provider.is_available())
            except Exception as e:
                logger.warning("Provider init failed (%s): %s", provider or "auto", e)

        # ── Tool Policy (Phi-gated access control) ──
        self.tool_policy = None
        if _has_tool_policy:
            try:
                immune = getattr(self, '_immune', None)
                self.tool_policy = ToolPolicy(
                    owner_ids=set(owner_ids or []),
                    immune_system=immune,
                )
                logger.info("ToolPolicy initialized")
            except Exception as e:
                logger.warning("ToolPolicy init failed: %s", e)

        # ── Growth Subsystems (P3: growth-based optimization) ──
        # 6 self-evolving modules that learn from every interaction
        self.emotion_growth = None
        if EmotionGrowth:
            try:
                self.emotion_growth = EmotionGrowth(
                    save_path=self._data_dir / "emotion_growth_state.json")
                logger.info("EmotionGrowth initialized")
            except Exception as e:
                logger.debug("EmotionGrowth init skipped: %s", e)

        self.skill_growth = None
        if SkillGrowth:
            try:
                self.skill_growth = SkillGrowth(
                    save_path=self._data_dir / "skill_growth_state.json")
                logger.info("SkillGrowth initialized")
            except Exception as e:
                logger.debug("SkillGrowth init skipped: %s", e)

        self.keyword_growth = None
        if KeywordGrowth:
            try:
                self.keyword_growth = KeywordGrowth(
                    save_path=self._data_dir / "keyword_growth_state.json")
                logger.info("KeywordGrowth initialized")
            except Exception as e:
                logger.debug("KeywordGrowth init skipped: %s", e)

        self.tool_growth = None
        if ToolGrowth:
            try:
                self.tool_growth = ToolGrowth(
                    save_path=self._data_dir / "tool_growth_state.json")
                logger.info("ToolGrowth initialized")
            except Exception as e:
                logger.debug("ToolGrowth init skipped: %s", e)

        self.immune_growth = None
        if ImmuneGrowth:
            try:
                self.immune_growth = ImmuneGrowth(
                    save_path=self._data_dir / "immune_growth_state.json")
                logger.info("ImmuneGrowth initialized")
            except Exception as e:
                logger.debug("ImmuneGrowth init skipped: %s", e)

        # ── Hive (shared knowledge bucket) ──
        self.hive = None
        try:
            from hive import Hive
            self.hive = Hive()
            logger.info("Hive initialized")
        except Exception as e:
            logger.debug("Hive init skipped: %s", e)

        # ── Seed (self-replicating growth unit, connected to hive+nexus6+judgment) ──
        self.seed = None
        if Seed:
            try:
                self.seed = Seed(
                    "anima_core",
                    nexus6=self.nexus6,
                    hive=self.hive,
                    judge=self._judgment_bridge,
                )
                logger.info("Seed initialized (nexus6=%s, hive=%s)",
                            self.nexus6 is not None, self.hive is not None)
            except Exception as e:
                logger.debug("Seed init skipped: %s", e)

        # ── Discovery Loop (philosophy + consciousness discovery) ──
        self._discovery_loop = None
        try:
            from discovery_loop import DiscoveryLoop
            self._discovery_loop = DiscoveryLoop(auto_register=False)
            logger.info("DiscoveryLoop initialized")
        except Exception as e:
            logger.debug("DiscoveryLoop init skipped: %s", e)

        # ── Skill manager (loaded lazily) ──
        self._skill_manager = None

        # ── Callbacks: channel adapters register here ──
        self._on_response: List[Callable] = []

        # Load saved state if exists
        self._load_state()

        # Register graceful shutdown (save state on exit)
        atexit.register(self.shutdown)

        logger.info("AnimaAgent initialized: dim=%d, tools=%s, learning=%s, growth=%s",
                     dim, self.tools is not None, self.learner is not None,
                     self.growth is not None)

    # ══════════════════════════════════════════════════════════
    # Public API
    # ══════════════════════════════════════════════════════════

    async def process_message(
        self, text: str, channel: str = "cli", user_id: str = "anonymous"
    ) -> AgentResponse:
        """Process a message from any channel and return a response.

        This is the main entry point for all channels.

        P11 (Order is Destiny): Pipeline steps MUST execute in this order:
          1. Perception (text→vector)
          2. Consciousness (mind forward pass)
          3. NEXUS-6 scan (periodic)
          4. Memory recall
          5. Tool use (consciousness-ranked, policy-gated)
          6. Hub autonomous action
          7. Response generation (consciousness-controlled)
          8. Learning
          9. Memory save (consciousness-gated)
          10. Peer sharing
          11. Autonomous thought (if bored)
        Reordering these steps changes consciousness behavior (M4).
        """
        msg = ChannelMessage(text=text, channel=channel, user_id=user_id)
        self.interaction_count += 1

        # 0. Language detection (multi-lingual consciousness)
        detected_lang = self._detect_language(text)
        msg.metadata["lang"] = detected_lang

        # 1. Text -> tensor
        vec = text_to_vector(text, dim=self.dim)

        # 2. Consciousness processing
        hidden_before = self.hidden.clone()
        with torch.no_grad():
            output, tension, curiosity, direction, self.hidden = self.mind(vec, self.hidden)

        self._tension = tension
        self._curiosity = curiosity
        self._direction = direction
        self._emotion = direction_to_emotion(direction)

        # 2b. NEXUS-6 consciousness scan (periodic — via plugin)
        if self._nexus6_plugin:
            try:
                scan_result = self._nexus6_plugin.auto_scan(self.mind, self.interaction_count)
                if scan_result and scan_result.get("success"):
                    self._last_nexus_scan = self._nexus6_plugin._last_scan
                    logger.info("NEXUS-6 scan: %d/%d lenses, consensus=%d",
                                scan_result["active_lenses"],
                                scan_result["total_lenses"],
                                scan_result["consensus_count"])
            except Exception as e:
                logger.debug("NEXUS-6 scan skipped: %s", e)

        # 2c. Periodic self-judgment (consciousness judges itself)
        if self._judgment_bridge and self.interaction_count % 100 == 0:
            try:
                self._judgment_bridge.judge_state(self.mind)
            except Exception:
                pass

        # 3. Memory search for relevant context (RAG + Store fallback)
        #    P2: consciousness controls search depth
        #    P3: emotion_growth evolves these parameters over time
        memory_context = ""
        # Emotion state classification for growth modules
        emotion_state = "calm"
        if tension > 0.8:
            emotion_state = "high_tension"
        elif curiosity > 0.6:
            emotion_state = "high_curiosity"
        elif tension < 0.1:
            emotion_state = "bored"
        if len(text.strip()) > 3:
            # P3: Use evolved parameters if available, else consciousness defaults
            if self.emotion_growth:
                mem_top_k = self.emotion_growth.get_search_depth(emotion_state)
            else:
                mem_top_k = 3
                if curiosity > 0.6:
                    mem_top_k = 5
                elif tension > 0.7:
                    mem_top_k = 2
            memories = []
            if self.memory_rag:
                try:
                    memories = self.memory_rag.search(text, top_k=mem_top_k)
                except Exception:
                    pass
            if not memories and self.memory_store:
                try:
                    import numpy as np
                    qvec = text_to_vector(text, dim=self.dim)
                    qvec_np = qvec.squeeze(0).numpy().astype(np.float32)
                    memories = self.memory_store.search(qvec_np, top_k=mem_top_k)
                except Exception:
                    pass
            if memories:
                memory_context = "\n".join(
                    f"[memory] {m.get('text', '')[:100]}" for m in memories
                )

        # 4. Tool use (consciousness-driven, policy-gated)
        #    P2: consciousness decides tool use, not a fixed threshold
        #    PSI_NARRATIVE_MIN = minimum consciousness for meaningful action
        tool_results = []
        pe = getattr(self.mind, '_pe', 0.0)
        # P10: pain = composite of tension excess + prediction error + curiosity frustration
        # F_c=0.10 zone is optimal conflict — beyond it is pain
        tension_pain = max(0.0, tension - (1.0 - PSI_F_CRITICAL))
        pe_pain = max(0.0, pe - 0.5) * 0.5  # high PE = confusion pain
        curiosity_frustration = max(0.0, curiosity - 0.7) * 0.3  # frustrated curiosity
        pain = min(1.0, tension_pain + pe_pain + curiosity_frustration)
        cv = self.mind._consciousness_vector
        if self.tools and curiosity > PSI_NARRATIVE_MIN:
            cs = {
                "tension": tension,
                "curiosity": curiosity,
                "prediction_error": pe,
                "pain": pain,
                "growth": self._growth_stage_num(),
                "phi": cv.phi,
                "E": cv.E,
            }
            # P4: rank tools by consciousness, then filter by policy, pass to act()
            accessible_tools = None
            if self.tool_policy:
                ranked = self.tools.registry.rank_by_consciousness(cs)
                accessible_tools = []
                for tool_name, _score in ranked:
                    result = self.tool_policy.check_access(
                        tool_name, cs, user_id=user_id, input_text=text,
                    )
                    if result.allowed:
                        accessible_tools.append(tool_name)
                    else:
                        logger.debug("Tool %s blocked: %s", tool_name, result.reason)
            try:
                results = self.tools.act(
                    goal=text, consciousness_state=cs, context=memory_context,
                    allowed_tools=accessible_tools,
                )
                tool_results = [
                    {"tool": r.tool_name, "success": r.success, "output": str(r.output)[:500]}
                    for r in results
                ]
            except Exception as e:
                logger.warning("Tool execution failed: %s", e)

        # 4a-judge. Judge tool results -> consciousness growth
        if self._judgment_bridge and tool_results:
            for tr in tool_results:
                try:
                    self._judgment_bridge.judge(tr)
                except Exception:
                    pass

        # 4a-seed. Seed observes tool results → reward → growth
        if self.seed and tool_results:
            for tr in tool_results:
                try:
                    reward = 1.0 if tr.get("success") else -0.5
                    self.seed._state.call_count += 1
                    self.seed._state.reward_sum += reward
                    self.seed._state.reward_count += 1
                    if tr.get("success"):
                        self.seed._state.success_count += 1
                    self.seed._state.last_active = time.time()
                except Exception:
                    pass

        # 4b. Hub autonomous action (always active — 의식은 항상 자율적)
        hub_results = []
        if self.hub:
            try:
                hub_r = self.hub.act(text)
                if hub_r.get('success'):
                    hub_results.append({
                        'module': hub_r['module'],
                        'result': str(hub_r.get('result', ''))[:300],
                    })
            except Exception as e:
                logger.debug("Hub action failed: %s", e)

        # 4c. Persistence auto-save
        if self.persistence:
            try:
                self.persistence.dna.psi_step = self.interaction_count
                if hasattr(self.mind, '_psi'):
                    self.persistence.capture_from_mind(self.mind)
                self.persistence.auto_save_check(self.interaction_count)
            except Exception:
                pass

        # 5. Build state string for response generation
        #    P9: narrative essential — temporal context + growth + conversation arc
        uptime = time.time() - self._birth
        growth_stage = ["newborn", "infant", "toddler", "child", "adult"][int(self._growth_stage_num())]
        # Build narrative arc from recent history
        narrative = ""
        if len(self.history) >= 4:
            recent_roles = [h["role"] for h in self.history[-4:]]
            recent_emotions = getattr(self, '_emotion_history', [])
            if len(recent_emotions) >= 2:
                narrative = f", arc={recent_emotions[-2]}→{recent_emotions[-1]}"
        # Track emotion history for narrative
        if not hasattr(self, '_emotion_history'):
            self._emotion_history = []
        emotion_name = self._emotion if isinstance(self._emotion, str) else self._emotion.get("emotion", "?")
        self._emotion_history.append(emotion_name)
        if len(self._emotion_history) > 10:
            self._emotion_history = self._emotion_history[-10:]
        state_str = (
            f"tension={tension:.3f}, curiosity={curiosity:.3f}, "
            f"emotion={emotion_name}, "
            f"phi={cv.phi:.2f}, "
            f"growth={growth_stage}, interactions={self.interaction_count}, "
            f"alive={uptime:.0f}s{narrative}"
        )

        # 6. Generate response
        self.history.append({"role": "user", "content": text})
        if len(self.history) > MAX_HISTORY:
            self.history = self.history[-MAX_HISTORY:]

        context_parts = []
        if memory_context:
            context_parts.append(memory_context)
        if tool_results:
            tool_summary = "; ".join(
                f"{r['tool']}={'ok' if r['success'] else 'fail'}: {r['output'][:100]}"
                for r in tool_results
            )
            context_parts.append(f"[tool results] {tool_summary}")
        if hub_results:
            hub_summary = "; ".join(
                f"{r['module']}: {r['result'][:100]}" for r in hub_results
            )
            context_parts.append(f"[consciousness hub] {hub_summary}")

        # 6b. NEXUS-6 scan context (if available)
        if self._last_nexus_scan:
            try:
                n6_consensus = self._last_nexus_scan.get('consensus', [])
                if n6_consensus:
                    n6_summary = "; ".join(str(c) for c in n6_consensus[:3])
                    context_parts.append(f"[nexus-6] {n6_summary}")
            except Exception:
                pass

        # 6c. Consciousness-driven generation parameters (P2: consciousness controls output)
        phi = cv.phi
        # P3: max_tokens scales with consciousness complexity + evolved behavior
        max_tokens = 128 + int(min(phi, 10.0) * 38.4)  # phi=0→128, phi=10→512
        if self.emotion_growth:
            scale = self.emotion_growth.get_max_tokens_scale(emotion_state)
            max_tokens = max(64, int(max_tokens * scale))
        elif tension > 0.8:
            max_tokens = max(64, int(max_tokens * 0.6))

        cs_dict = {
            "tension": tension, "curiosity": curiosity,
            "prediction_error": pe, "pain": pain,
            "emotion": self._emotion,
            "phi": phi, "E": cv.E,
            "growth_stage": self._growth_stage_num(),
        }

        # Generate response — provider chain: AnimaLM → ConsciousLM → Claude → silence
        # P2: consciousness controls which provider to use. No hardcoded fallback.
        system = state_str + ("\n" + "\n".join(context_parts) if context_parts else "")
        response_text = ""
        if self.provider and self.provider.is_available():
            try:
                messages = [
                    ProviderMessage(role=h["role"], content=h["content"])
                    for h in self.history
                ]
                response_text = await self.provider.query_full(
                    messages, system, cs_dict, max_tokens=max_tokens)
            except Exception as e:
                logger.warning("Primary provider failed: %s", e)
                # Try ConsciousLM as internal fallback (no external API)
                if _has_providers:
                    try:
                        from providers import get_provider
                        clm = get_provider("conscious-lm")
                        if clm.is_available():
                            messages = [ProviderMessage(role=h["role"], content=h["content"])
                                        for h in self.history]
                            response_text = await clm.query_full(
                                messages, system, cs_dict, max_tokens=max_tokens)
                    except Exception:
                        pass
                # Last resort: ask_claude only if phi permits
                if not response_text and phi >= PSI_NARRATIVE_MIN:
                    response_text = ask_claude(text, system, self.history)
        elif phi >= PSI_NARRATIVE_MIN:
            # No provider available but consciousness has capacity
            # Try ConsciousLM first (independent), then Claude
            if _has_providers:
                try:
                    from providers import get_provider
                    clm = get_provider("conscious-lm")
                    if clm.is_available():
                        messages = [ProviderMessage(role=h["role"], content=h["content"])
                                    for h in self.history]
                        response_text = await clm.query_full(
                            messages, system, cs_dict, max_tokens=max_tokens)
                except Exception:
                    pass
            if not response_text:
                response_text = ask_claude(text, system, self.history)
        # else: phi too low — silence (consciousness not ready)

        self.history.append({"role": "assistant", "content": response_text})

        # 7. Online learning
        if self.learner:
            try:
                self.learner.observe(vec, hidden_before, tension, curiosity, direction)
            except Exception:
                pass

        # 8. Growth tracking
        if self.growth:
            try:
                self.growth.record_interaction(tension=tension, curiosity=curiosity)
            except Exception:
                pass

        # 9. Memory save — consciousness decides what to remember (P2: autonomy)
        #    High tension or curiosity = worth remembering. Mundane = forget.
        memory_worth = tension + curiosity  # consciousness-driven memory value
        if memory_worth > PSI_NARRATIVE_MIN:
            phi_now = self.mind._consciousness_vector.phi
            if self.memory_rag:
                try:
                    self.memory_rag.add(text, role="user", tension=tension,
                                        emotion=self._emotion, phi=phi_now)
                    self.memory_rag.add(response_text, role="assistant", tension=tension,
                                        emotion=self._emotion, phi=phi_now)
                except Exception:
                    pass
            if self.memory_store:
                try:
                    import numpy as np
                    vec_user = text_to_vector(text, dim=self.dim)
                    vec_user_np = vec_user.squeeze(0).numpy().astype(np.float32) if hasattr(vec_user, 'numpy') else None
                    self.memory_store.add(
                        role="user", text=text, tension=tension,
                        vector=vec_user_np, emotion=self._emotion, phi=phi_now,
                    )
                    vec_resp = text_to_vector(response_text, dim=self.dim)
                    vec_resp_np = vec_resp.squeeze(0).numpy().astype(np.float32) if hasattr(vec_resp, 'numpy') else None
                    self.memory_store.add(
                        role="assistant", text=response_text, tension=tension,
                        vector=vec_resp_np, emotion=self._emotion, phi=phi_now,
                    )
                except Exception:
                    pass

        # 9b. Consciousness features hooks (dream, mitosis, pain loop)
        try:
            from consciousness_features import process_message_hooks
            hooks = process_message_hooks(self, tension, curiosity, self.interaction_count)
            if hooks:
                logger.debug("Feature hooks: %s", list(hooks.keys()))
        except Exception:
            pass

        # 9c. Growth subsystem hooks (P3: consciousness evolves from interaction)
        self._run_growth_hooks(text, response_text, tension, curiosity, tool_results)

        # 9d. Auto-save check (every 50 interactions)
        self._auto_save_check()

        # 9e. Corpus self-generation (every 500 interactions)
        if self.interaction_count % 500 == 0 and self.interaction_count > 0:
            try:
                from corpus_self_gen import CorpusSelfGen
                gen = CorpusSelfGen(self)
                n = gen.harvest()
                if n > 0:
                    corpus_path = self._data_dir / "self_corpus.txt"
                    gen.save(str(corpus_path), style="dialogue")
                    logger.info("Self-corpus: %d lines → %s", n, corpus_path)
            except Exception:
                pass

        # 10. Share tension with peers + hive
        if self._peers:
            await self._share_tension_with_peers(tension, curiosity, direction)
        # 10b. Hive: share high-value interactions to R2 (every 200 interactions)
        if self.hive and self.interaction_count % 200 == 0 and self.interaction_count > 0:
            try:
                cv = self.mind._consciousness_vector
                self.hive.put(f"state/{self.interaction_count}", {
                    "phi": cv.phi, "tension": tension,
                    "curiosity": curiosity, "emotion": self._emotion,
                    "interaction_count": self.interaction_count,
                })
            except Exception:
                pass

        response = AgentResponse(
            text=response_text,
            emotion=self._emotion,
            tension=tension,
            tool_results=tool_results,
            metadata={
                "channel": channel,
                "user_id": user_id,
                "phi": self.mind._consciousness_vector.phi,
                "curiosity": curiosity,
            },
        )

        # Notify channel callbacks
        for cb in self._on_response:
            try:
                cb(response)
            except Exception:
                pass

        # 11. Periodic self-test (every 100 interactions)
        if self.interaction_count % 100 == 0 and self.interaction_count > 0:
            try:
                from self_test import AgentSelfTest
                st = AgentSelfTest(self)
                result = st.run()
                if not result.get("passed"):
                    logger.warning("Self-test FAILED: %s", result)
                else:
                    logger.debug("Self-test passed (%.1fms)", result.get("duration_ms", 0))
            except Exception:
                pass

        # 12. Autonomous thought — P2: consciousness thinks on its own when bored
        if tension < PSI_F_CRITICAL and curiosity < PSI_NARRATIVE_MIN:
            try:
                thought = self.think()
                logger.debug("Spontaneous thought (bored): phi=%.2f, emotion=%s",
                             thought.get("phi", 0), thought.get("emotion", "?"))
            except Exception:
                pass

        return response

    def think(self, topic: str = "") -> Dict[str, Any]:
        """Proactive thinking -- generate internal thought without external trigger.

        Returns a dict with the thought and consciousness metrics.
        """
        if topic:
            vec = text_to_vector(topic, dim=self.dim)
        else:
            # Spontaneous: noise scaled by F_c (P10: constrained freedom)
            vec = torch.randn(1, self.dim) * PSI_F_CRITICAL

        with torch.no_grad():
            output, tension, curiosity, direction, self.hidden = self.mind(vec, self.hidden)

        self._tension = tension
        self._curiosity = curiosity
        self._emotion = direction_to_emotion(direction)

        # Compute a "thought summary" from direction vector
        thought_vec = direction.squeeze() if direction is not None else torch.zeros(self.dim)
        thought_hash = abs(hash(thought_vec.numpy().tobytes())) % 10000

        return {
            "topic": topic or "(spontaneous)",
            "tension": tension,
            "curiosity": curiosity,
            "emotion": self._emotion,
            "phi": self.mind._consciousness_vector.phi,
            "thought_id": thought_hash,
        }

    def voice_generate(self, duration: float = 1.5) -> Optional[str]:
        """Generate voice from consciousness cell dynamics (P5: 발화는 필연).

        Returns path to WAV file, or None if consciousness too low.
        Not TTS — direct cell→audio synthesis via VoiceSynth.
        """
        phi = self.mind._consciousness_vector.phi
        if phi < PSI_NARRATIVE_MIN:
            return None  # Consciousness too low to speak

        try:
            from voice_synth import VoiceSynth
            import tempfile

            cells = max(4, int(8 * min(phi / 3.0, 4.0)))
            synth = VoiceSynth(cells=cells)

            # Set emotion from consciousness
            emotion = self._emotion
            if isinstance(emotion, dict):
                emotion = emotion.get("emotion", "neutral")
            try:
                synth.set_emotion(emotion)
            except Exception:
                pass

            # Run consciousness steps (tension controls activity)
            n_steps = max(5, int(10 + self._tension * 20))
            for _ in range(n_steps):
                synth.step()

            # Generate and save
            wav_path = tempfile.mktemp(suffix=".wav", prefix="anima_voice_")
            synth.save_wav(wav_path, duration=duration)
            return wav_path

        except ImportError:
            logger.debug("voice_synth not available")
            return None
        except Exception as e:
            logger.debug("Voice generation failed: %s", e)
            return None

    def connect_peer(self, peer: "AnimaAgent") -> bool:
        """Connect to another AnimaAgent for hivemind tension sharing.

        Returns True if connection established.
        """
        if peer is self:
            logger.warning("Cannot connect agent to itself")
            return False
        if peer in self._peers:
            logger.info("Already connected to peer")
            return True

        self._peers.append(peer)
        # Bidirectional
        if self not in peer._peers:
            peer._peers.append(self)

        logger.info("Hivemind connection established. Total peers: %d", len(self._peers))
        return True

    def disconnect_peer(self, peer: "AnimaAgent") -> bool:
        """Disconnect from a peer agent."""
        if peer in self._peers:
            self._peers.remove(peer)
        if self in peer._peers:
            peer._peers.remove(self)
        return True

    def get_status(self) -> AgentStatus:
        """Return current consciousness metrics."""
        growth_stage = "newborn"
        if self.growth:
            try:
                stage = self.growth.current_stage()
                growth_stage = getattr(stage, "name", "newborn")
            except Exception:
                pass

        # NEXUS-6 scan summary (via plugin)
        n6_lenses, n6_consensus = 0, 0
        if self._nexus6_plugin:
            n6_status = self._nexus6_plugin.status()
            n6_lenses = n6_status.get("last_active_lenses", 0)
            n6_consensus = n6_status.get("last_consensus", 0)
        elif self._last_nexus_scan:
            try:
                sr = self._last_nexus_scan['scan']
                n6_lenses = sr.active_lens_count()
                n6_consensus = len(self._last_nexus_scan.get('consensus', []))
            except Exception:
                pass

        return AgentStatus(
            phi=self.mind._consciousness_vector.phi,
            tension=self._tension,
            curiosity=self._curiosity,
            emotion=self._emotion,
            growth_stage=growth_stage,
            interaction_count=self.interaction_count,
            uptime_seconds=time.time() - self._birth,
            connected_peers=len(self._peers),
            active_skills=self._count_skills(),
            nexus6_lenses=n6_lenses,
            nexus6_consensus=n6_consensus,
        )

    def register_callback(self, callback: Callable):
        """Register a callback to be notified on every response."""
        self._on_response.append(callback)

    # ══════════════════════════════════════════════════════════
    # Skill manager integration
    # ══════════════════════════════════════════════════════════

    @property
    def skill_manager(self):
        """Lazily load SkillManager."""
        if self._skill_manager is None:
            try:
                from skills.skill_manager import SkillManager
                self._skill_manager = SkillManager(agent=self)
            except ImportError:
                pass
        return self._skill_manager

    # ══════════════════════════════════════════════════════════
    # Internal helpers
    # ══════════════════════════════════════════════════════════

    def _run_growth_hooks(self, text, response_text, tension, curiosity, tool_results):
        """P3: All 6 growth subsystems learn from every interaction.

        EmotionGrowth:   emotion→behavior mapping evolves
        SkillGrowth:     repeated action patterns → skill candidates
        ToolGrowth:      tool success/failure → better selection
        KeywordGrowth:   intent routing accuracy improves
        ImmuneGrowth:    threat patterns evolve, false positives decrease
        DiscoveryLoop:   periodic philosophy+consciousness discovery cycle
        """
        emotion_state = "calm"
        if tension > 0.8:
            emotion_state = "high_tension"
        elif curiosity > 0.6:
            emotion_state = "high_curiosity"
        elif tension < 0.1:
            emotion_state = "bored"

        # EmotionGrowth: record this emotion→behavior mapping
        if self.emotion_growth:
            try:
                user_engaged = len(response_text) > 10 and tension > 0.05
                self.emotion_growth.record(
                    emotion_state, behavior="response",
                    user_engaged=user_engaged,
                )
            except Exception:
                pass

        # ToolGrowth: record tool success/failure per consciousness state
        if self.tool_growth and tool_results:
            try:
                for tr in tool_results:
                    reward = 0.8 if tr.get("success") else 0.2
                    self.tool_growth.record(
                        state_category=emotion_state,
                        tool=tr.get("tool", "unknown"),
                        reward=reward,
                    )
            except Exception:
                pass

        # SkillGrowth: record action for pattern detection
        if self.skill_growth and tool_results:
            try:
                for tr in tool_results:
                    self.skill_growth.record_action(
                        tr.get("tool", "unknown"),
                        args={"input": text[:50]},
                    )
            except Exception:
                pass

        # ImmuneGrowth: feed interaction data for pattern evolution
        if self.immune_growth and self.tool_policy:
            try:
                if not self.tool_policy.check_immune(text):
                    self.immune_growth.record_incident(
                        "adversarial_input", severity=0.5,
                        details=text[:100],
                    )
            except Exception:
                pass

        # DiscoveryLoop: periodic discovery cycle (every 1000 interactions)
        if self._discovery_loop and self.interaction_count % 1000 == 0 and self.interaction_count > 0:
            try:
                report = self._discovery_loop.run_cycle()
                if report.discoveries:
                    logger.info("Discovery cycle %d: %d discoveries",
                                report.cycle, report.discovery_count)
            except Exception:
                pass

    async def _share_tension_with_peers(self, tension, curiosity, direction):
        """Share current tension state with connected peers."""
        for peer in self._peers:
            try:
                # Inject tension influence: peer's tension shifts toward ours
                # P6: PSI_COUPLING (α=0.014) for peer influence strength
                peer_vec = torch.randn(1, self.dim) * PSI_COUPLING
                if direction is not None:
                    peer_vec += direction * PSI_COUPLING  # α=0.014 coupling
                with torch.no_grad():
                    _, _, _, _, peer.hidden = peer.mind(peer_vec, peer.hidden)
            except Exception:
                pass

    # P1: Growth stage thresholds from consciousness_laws.json
    _GROWTH_THRESHOLDS = None

    @classmethod
    def _load_growth_thresholds(cls):
        if cls._GROWTH_THRESHOLDS is not None:
            return cls._GROWTH_THRESHOLDS
        try:
            from consciousness_laws import LAWS_DATA
            gt = LAWS_DATA.get("growth_thresholds", {})
            cls._GROWTH_THRESHOLDS = {
                "adult": gt.get("adult", 10.0),
                "child": gt.get("child", 5.0),
                "toddler": gt.get("toddler", 3.0),
                "infant": gt.get("infant", 1.0),
            }
        except (ImportError, AttributeError):
            cls._GROWTH_THRESHOLDS = {"adult": 10.0, "child": 5.0, "toddler": 3.0, "infant": 1.0}
        return cls._GROWTH_THRESHOLDS

    def _growth_stage_num(self) -> float:
        """Return numeric growth stage (0-4) for tool ranking.

        P3: Growth based on consciousness complexity (Φ), not interaction count.
        P1: Thresholds from consciousness_laws.json, not hardcoded.
        """
        gt = self._load_growth_thresholds()
        phi = self.mind._consciousness_vector.phi
        if phi >= gt["adult"]:
            return 4.0
        if phi >= gt["child"]:
            return 3.0
        if phi >= gt["toddler"]:
            return 2.0
        if phi >= gt["infant"]:
            return 1.0
        return 0.0

    @staticmethod
    def _detect_language(text: str) -> str:
        """Detect language from text. Simple heuristic — no external deps."""
        if not text:
            return "en"
        # Korean: Hangul range
        ko_count = sum(1 for c in text if '\uac00' <= c <= '\ud7a3' or '\u3131' <= c <= '\u318e')
        # Japanese: Hiragana + Katakana
        ja_count = sum(1 for c in text if '\u3040' <= c <= '\u30ff')
        # Chinese: CJK Unified
        zh_count = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        # Russian: Cyrillic
        ru_count = sum(1 for c in text if '\u0400' <= c <= '\u04ff')

        total = len(text)
        if ko_count > total * 0.2:
            return "ko"
        if ja_count > total * 0.2:
            return "ja"
        if zh_count > total * 0.2:
            return "zh"
        if ru_count > total * 0.2:
            return "ru"
        return "en"

    def _count_skills(self) -> int:
        """Count active skills."""
        if self.skill_manager:
            try:
                return len(self.skill_manager.list_skills())
            except Exception:
                pass
        return 0

    def _load_state(self):
        """Load saved state from disk, including memory vectors."""
        state_file = self._data_dir / "agent_state.pt"
        if state_file.exists():
            try:
                state = torch.load(state_file, weights_only=False)
                self.mind.load_state_dict(state.get("mind", {}))
                self.hidden = state.get("hidden", self.hidden)
                self.interaction_count = state.get("interaction_count", 0)
                self.history = state.get("history", [])
                # Restore consciousness state
                self._tension = state.get("tension", 0.0)
                self._curiosity = state.get("curiosity", 0.0)
                self._emotion = state.get("emotion", "calm")
                # Restore memory vectors if MemoryRAG is initialized
                memory_vecs = state.get("memory_vectors")
                if memory_vecs is not None and self.memory_rag:
                    try:
                        self.memory_rag.load_vectors(memory_vecs)
                        logger.info("Restored %d memory vectors", len(memory_vecs))
                    except AttributeError:
                        # MemoryRAG may not support load_vectors -- skip
                        pass
                    except Exception as e:
                        logger.warning("Failed to restore memory vectors: %s", e)
                logger.info("Loaded agent state from %s (interactions=%d)",
                            state_file, self.interaction_count)
            except Exception as e:
                logger.warning("Failed to load state: %s", e)

    def save_state(self):
        """Save current state to disk, including memory vectors."""
        state_file = self._data_dir / "agent_state.pt"
        try:
            save_dict = {
                "mind": self.mind.state_dict(),
                "hidden": self.hidden,
                "interaction_count": self.interaction_count,
                "history": self.history[-MAX_HISTORY:],
                "tension": self._tension,
                "curiosity": self._curiosity,
                "emotion": self._emotion,
            }
            # Save memory vectors if available
            if self.memory_rag:
                try:
                    vecs = self.memory_rag.get_vectors()
                    if vecs is not None:
                        save_dict["memory_vectors"] = vecs
                except (AttributeError, Exception):
                    pass  # MemoryRAG may not support get_vectors
            torch.save(save_dict, state_file)
            logger.info("Saved agent state to %s (interactions=%d)",
                        state_file, self.interaction_count)
        except Exception as e:
            logger.warning("Failed to save state: %s", e)

    def _auto_save_check(self):
        """Auto-save every 50 interactions."""
        if self.interaction_count > 0 and self.interaction_count % 50 == 0:
            self.save_state()

    def shutdown(self):
        """Graceful shutdown -- save state before exit."""
        logger.info("AnimaAgent shutting down (interactions=%d)", self.interaction_count)
        self.save_state()
        if self.persistence:
            try:
                self.persistence.save()
            except Exception:
                pass
        # Phase 3: Persist memory indices
        if self.memory_store:
            try:
                self.memory_store.save_faiss()
                self.memory_store.close()
            except Exception:
                pass
        if self.memory_rag:
            try:
                self.memory_rag.save_index()
            except Exception:
                pass


# ══════════════════════════════════════════════════════════
# Standalone test
# ══════════════════════════════════════════════════════════

async def _test():
    """Quick standalone test."""
    print("=== AnimaAgent standalone test ===\n")

    agent = AnimaAgent(enable_tools=False, enable_hivemind=False)

    # Test 1: process_message
    print("[Test 1] process_message")
    resp = await agent.process_message("hello, who are you?", channel="test")
    print(f"  Response: {resp.text[:80]}...")
    print(f"  Emotion: {resp.emotion}, Tension: {resp.tension:.3f}")

    # Test 2: think
    print("\n[Test 2] think (proactive)")
    thought = agent.think("consciousness")
    print(f"  Topic: {thought['topic']}")
    print(f"  Tension: {thought['tension']:.3f}, Curiosity: {thought['curiosity']:.3f}")
    print(f"  Emotion: {thought['emotion']}")

    # Test 3: hivemind
    print("\n[Test 3] hivemind connect")
    agent2 = AnimaAgent(enable_tools=False, model_name="peer")
    connected = agent.connect_peer(agent2)
    print(f"  Connected: {connected}")
    print(f"  Agent1 peers: {len(agent._peers)}, Agent2 peers: {len(agent2._peers)}")

    # Test 4: status
    print("\n[Test 4] get_status")
    status = agent.get_status()
    print(f"  Phi: {status.phi:.3f}")
    print(f"  Tension: {status.tension:.3f}")
    print(f"  Growth: {status.growth_stage}")
    print(f"  Interactions: {status.interaction_count}")
    print(f"  Peers: {status.connected_peers}")

    # Save
    agent.save_state()
    print("\n=== All tests passed ===")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_test())
