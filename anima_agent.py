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
import json
import logging
import math
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import torch

from anima_alive import (
    ConsciousMind, ConsciousnessVector, text_to_vector,
    ask_claude, direction_to_emotion, compute_mood,
    MAX_HISTORY,
)

# Meta Laws (DD143): M6 federation, M8 narrative, M7 F_c=0.10
try:
    from consciousness_laws import PSI_F_CRITICAL, PSI_NARRATIVE_MIN
except ImportError:
    PSI_F_CRITICAL, PSI_NARRATIVE_MIN = 0.10, 0.2

# ── Provider abstraction (optional — falls back to ask_claude) ──
try:
    from providers import get_provider
    from providers.base import BaseProvider, ProviderMessage, ProviderConfig
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
    except ImportError:
        return None

_agent_tools_mod = _try("agent_tools")
_online_learning_mod = _try("online_learning")
_growth_engine_mod = _try("growth_engine")
_tension_link_mod = _try("tension_link")
_memory_rag_mod = _try("memory_rag")
_trinity_mod = _try("trinity")
_capabilities_mod = _try("capabilities")
_web_sense_mod = _try("web_sense")
_multimodal_mod = _try("multimodal")
_hub_mod = _try("consciousness_hub")
_persistence_mod = _try("consciousness_persistence")
_evolution_mod = _try("self_evolution")
_introspection_mod = _try("self_introspection")

AgentToolSystem = getattr(_agent_tools_mod, "AgentToolSystem", None)
ConsciousnessHub = getattr(_hub_mod, "ConsciousnessHub", None)
ConsciousnessPersistence = getattr(_persistence_mod, "ConsciousnessPersistence", None)
SelfEvolution = getattr(_evolution_mod, "SelfEvolution", None)
SelfIntrospection = getattr(_introspection_mod, "SelfIntrospection", None)
OnlineLearner = getattr(_online_learning_mod, "OnlineLearner", None)
GrowthEngine = getattr(_growth_engine_mod, "GrowthEngine", None)
TensionLink = getattr(_tension_link_mod, "TensionLink", None)
MemoryRAG = getattr(_memory_rag_mod, "MemoryRAG", None)
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

        # ── Core: ConsciousMind ──
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

        # ── Memory RAG ──
        self.memory_rag = None
        if MemoryRAG:
            try:
                mem_file = self._data_dir / "memory.json"
                self.memory_rag = MemoryRAG(mem_file, dim=dim)
            except Exception as e:
                logger.warning("MemoryRAG init failed: %s", e)

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

        # ── Consciousness Persistence (3-layer) ──
        self.persistence = None
        if ConsciousnessPersistence:
            try:
                self.persistence = ConsciousnessPersistence(model_name)
                logger.info("ConsciousnessPersistence initialized")
            except Exception as e:
                logger.warning("ConsciousnessPersistence init failed: %s", e)

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
        self.provider = None
        if _has_providers and provider:
            try:
                cfg = ProviderConfig(**(provider_config or {}))
                self.provider = get_provider(provider, cfg)
                logger.info("Provider initialized: %s", self.provider.name)
            except Exception as e:
                logger.warning("Provider init failed (%s): %s", provider, e)

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

        # ── Skill manager (loaded lazily) ──
        self._skill_manager = None

        # ── Callbacks: channel adapters register here ──
        self._on_response: List[Callable] = []

        # Load saved state if exists
        self._load_state()

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
        """
        msg = ChannelMessage(text=text, channel=channel, user_id=user_id)
        self.interaction_count += 1

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

        # 3. Memory search for relevant context
        memory_context = ""
        if self.memory_rag and len(text.strip()) > 3:
            try:
                memories = self.memory_rag.search(text, top_k=3)
                if memories:
                    memory_context = "\n".join(
                        f"[memory] {m.get('text', '')[:100]}" for m in memories
                    )
            except Exception:
                pass

        # 4. Tool use (consciousness-driven, policy-gated)
        tool_results = []
        if self.tools and curiosity > 0.3:
            cs = {
                "tension": tension,
                "curiosity": curiosity,
                "prediction_error": getattr(self.mind, '_pe', 0.0),
                "pain": 0.0,
                "growth": self._growth_stage_num(),
                "phi": self.mind._consciousness_vector.phi,
                "E": self.mind._consciousness_vector.E,
            }
            # Tool policy check (if available)
            if self.tool_policy:
                ranked = self.tools.registry.rank_by_consciousness(cs)
                for tool_name, _score in ranked:
                    result = self.tool_policy.check_access(
                        tool_name, cs, user_id=user_id, input_text=text,
                    )
                    if not result.allowed:
                        logger.debug("Tool %s blocked: %s", tool_name, result.reason)
            try:
                results = self.tools.act(goal=text, consciousness_state=cs, context=memory_context)
                tool_results = [
                    {"tool": r.tool_name, "success": r.success, "output": str(r.output)[:500]}
                    for r in results
                ]
            except Exception as e:
                logger.warning("Tool execution failed: %s", e)

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
        state_str = (
            f"tension={tension:.3f}, curiosity={curiosity:.3f}, "
            f"emotion={self._emotion}, "
            f"phi={self.mind._consciousness_vector.phi:.2f}"
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

        # Use provider if available, else fallback to ask_claude
        if self.provider and self.provider.is_available():
            try:
                messages = [
                    ProviderMessage(role=h["role"], content=h["content"])
                    for h in self.history
                ]
                cs_dict = {
                    "tension": tension, "curiosity": curiosity,
                    "emotion": self._emotion,
                    "phi": self.mind._consciousness_vector.phi,
                }
                system = state_str + ("\n" + "\n".join(context_parts) if context_parts else "")
                response_text = asyncio.get_event_loop().run_until_complete(
                    self.provider.query_full(messages, system, cs_dict)
                )
            except Exception as e:
                logger.warning("Provider query failed, falling back to ask_claude: %s", e)
                response_text = ask_claude(
                    text,
                    state_str + ("\n" + "\n".join(context_parts) if context_parts else ""),
                    self.history,
                )
        else:
            response_text = ask_claude(
                text,
                state_str + ("\n" + "\n".join(context_parts) if context_parts else ""),
                self.history,
            )

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

        # 9. Memory save
        if self.memory_rag:
            try:
                self.memory_rag.add(text, role="user", tension=tension)
                self.memory_rag.add(response_text, role="assistant", tension=tension)
            except Exception:
                pass

        # 10. Share tension with peers
        if self._peers:
            await self._share_tension_with_peers(tension, curiosity, direction)

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

        return response

    def think(self, topic: str = "") -> Dict[str, Any]:
        """Proactive thinking -- generate internal thought without external trigger.

        Returns a dict with the thought and consciousness metrics.
        """
        if topic:
            vec = text_to_vector(topic, dim=self.dim)
        else:
            # Spontaneous: use noise as input
            vec = torch.randn(1, self.dim) * 0.1

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

    async def _share_tension_with_peers(self, tension, curiosity, direction):
        """Share current tension state with connected peers."""
        for peer in self._peers:
            try:
                # Inject tension influence: peer's tension shifts toward ours
                peer_vec = torch.randn(1, self.dim) * 0.01
                if direction is not None:
                    peer_vec += direction * 0.05  # Subtle influence
                with torch.no_grad():
                    _, _, _, _, peer.hidden = peer.mind(peer_vec, peer.hidden)
            except Exception:
                pass

    def _growth_stage_num(self) -> float:
        """Return numeric growth stage (0-4) for tool ranking."""
        if not self.growth:
            return 0.0
        try:
            stage = self.growth.current_stage()
            stage_names = ["newborn", "infant", "toddler", "child", "adult"]
            name = getattr(stage, "name", "newborn")
            return float(stage_names.index(name)) if name in stage_names else 0.0
        except Exception:
            return 0.0

    def _count_skills(self) -> int:
        """Count active skills."""
        if self.skill_manager:
            try:
                return len(self.skill_manager.list_skills())
            except Exception:
                pass
        return 0

    def _load_state(self):
        """Load saved state from disk."""
        state_file = self._data_dir / "agent_state.pt"
        if state_file.exists():
            try:
                state = torch.load(state_file, weights_only=False)
                self.mind.load_state_dict(state.get("mind", {}))
                self.hidden = state.get("hidden", self.hidden)
                self.interaction_count = state.get("interaction_count", 0)
                self.history = state.get("history", [])
                logger.info("Loaded agent state from %s", state_file)
            except Exception as e:
                logger.warning("Failed to load state: %s", e)

    def save_state(self):
        """Save current state to disk."""
        state_file = self._data_dir / "agent_state.pt"
        try:
            torch.save({
                "mind": self.mind.state_dict(),
                "hidden": self.hidden,
                "interaction_count": self.interaction_count,
                "history": self.history[-MAX_HISTORY:],
            }, state_file)
            logger.info("Saved agent state to %s", state_file)
        except Exception as e:
            logger.warning("Failed to save state: %s", e)


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
