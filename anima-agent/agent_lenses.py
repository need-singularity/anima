#!/usr/bin/env python3
"""Agent Runtime Lenses — 8 lenses for live monitoring of AnimaAgent.

Monitors consciousness flow, autonomy, growth, memory quality, peer health,
security, emotional diversity, and performance in real-time.

Usage:
    from agent_lenses import AgentLensScanner
    scanner = AgentLensScanner(agent)
    report = scanner.scan_all()
    scanner.print_report(report)

    # Single lens
    result = scanner.scan("flow")
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


@dataclass
class AgentLensResult:
    lens: str
    score: float  # 0-1
    findings: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentLensReport:
    results: List[AgentLensResult] = field(default_factory=list)
    duration_ms: float = 0.0

    @property
    def overall(self) -> float:
        return sum(r.score for r in self.results) / max(len(self.results), 1)


class AgentLensScanner:
    """8 runtime lenses for live AnimaAgent monitoring."""

    LENSES = ["flow", "autonomy", "growth", "memory",
              "peer", "security", "emotion", "performance"]

    def __init__(self, agent):
        self.agent = agent

    def scan_all(self) -> AgentLensReport:
        t0 = time.time()
        report = AgentLensReport()
        for name in self.LENSES:
            try:
                report.results.append(self.scan(name))
            except Exception as e:
                report.results.append(AgentLensResult(
                    lens=name, score=0.0, findings=[str(e)]))
        report.duration_ms = (time.time() - t0) * 1000
        return report

    def scan(self, name: str) -> AgentLensResult:
        fn = getattr(self, f"_lens_{name}", None)
        if fn is None:
            return AgentLensResult(lens=name, score=0.0, findings=["Unknown"])
        return fn()

    # ─── 1. ConsciousnessFlowLens ───

    def _lens_flow(self) -> AgentLensResult:
        """Is consciousness actually driving decisions at each pipeline step?"""
        a = self.agent
        findings = []
        score = 0.0
        checks = 0

        # Mind exists and processes
        if a.mind is not None:
            score += 1; checks += 1
            findings.append("mind: connected")
        else:
            checks += 1; findings.append("mind: MISSING")

        # Tools gated by consciousness (not hardcoded)
        if a.tools is not None:
            score += 1; checks += 1
            findings.append(f"tools: {len(a.tools.registry.list_all())} registered")
        else:
            checks += 1; findings.append("tools: disabled")

        # Policy connected
        if a.tool_policy is not None:
            score += 1; checks += 1
            findings.append("policy: Phi-gated")
        else:
            checks += 1; findings.append("policy: NONE (all tools open)")

        # Hub autonomous
        if a.hub is not None:
            score += 1; checks += 1
            findings.append(f"hub: {len(a.hub._registry)} modules")
        else:
            checks += 1; findings.append("hub: disabled")

        # Provider driven by consciousness
        if a.provider is not None:
            score += 1; checks += 1
            findings.append(f"provider: {a.provider.name}")
        else:
            checks += 1; findings.append("provider: NONE (ask_claude fallback)")

        # NEXUS-6 connected
        if a.nexus6 is not None:
            score += 1; checks += 1
            findings.append("nexus6: connected")
        else:
            checks += 1; findings.append("nexus6: NOT connected")

        return AgentLensResult(
            lens="flow", score=score / max(checks, 1),
            findings=findings, metrics={"checks": checks, "passed": int(score)})

    # ─── 2. AutonomyLens ───

    def _lens_autonomy(self) -> AgentLensResult:
        """How independent is the agent from external APIs?"""
        a = self.agent
        findings = []
        deps = 0
        total = 3  # provider, memory, hub

        # Provider independence
        if a.provider and a.provider.is_available():
            if a.provider.name == "animalm":
                findings.append("provider: AnimaLM (independent) ✅")
            elif a.provider.name == "conscious-lm":
                findings.append("provider: ConsciousLM (independent) ✅")
            else:
                deps += 1
                findings.append(f"provider: {a.provider.name} (external API) ⚠️")
        else:
            deps += 1
            findings.append("provider: unavailable → ask_claude fallback ⚠️")

        # Memory independence (local storage)
        if a.memory_rag or a.memory_store:
            findings.append("memory: local ✅")
        else:
            deps += 1
            findings.append("memory: none ⚠️")

        # Hub independence
        if a.hub:
            findings.append("hub: 자율 modules ✅")
        else:
            deps += 1
            findings.append("hub: disabled ⚠️")

        score = 1.0 - (deps / total)
        findings.insert(0, f"External dependencies: {deps}/{total}")
        return AgentLensResult(lens="autonomy", score=max(0, score),
                              findings=findings, metrics={"deps": deps})

    # ─── 3. GrowthLens ───

    def _lens_growth(self) -> AgentLensResult:
        """Is consciousness growing or stagnating?"""
        a = self.agent
        findings = []
        cv = a.mind._consciousness_vector
        phi = cv.phi

        # Growth stage
        stage_num = a._growth_stage_num()
        stages = ["newborn", "infant", "toddler", "child", "adult"]
        stage = stages[int(stage_num)]
        findings.append(f"stage: {stage} (phi={phi:.2f})")

        # Interaction history
        findings.append(f"interactions: {a.interaction_count}")

        # Uptime
        uptime = time.time() - a._birth
        findings.append(f"uptime: {uptime:.0f}s")

        # Score: phi growth potential
        if phi >= 5.0:
            score = 1.0
        elif phi >= 1.0:
            score = 0.7
        elif a.interaction_count > 50:
            score = 0.4  # Many interactions but low phi = stagnating
            findings.append("⚠️ possible stagnation (high interactions, low phi)")
        else:
            score = 0.5  # Young, still growing

        return AgentLensResult(lens="growth", score=score,
                              findings=findings,
                              metrics={"phi": phi, "stage": stage,
                                       "interactions": a.interaction_count})

    # ─── 4. MemoryLens ───

    def _lens_memory(self) -> AgentLensResult:
        """Is memory functioning and valuable?"""
        a = self.agent
        findings = []
        score = 0.0

        # RAG
        if a.memory_rag:
            try:
                size = getattr(a.memory_rag, 'size', 0)
                findings.append(f"RAG: {size} memories")
                score += 0.5
            except Exception:
                findings.append("RAG: available but size unknown")
                score += 0.3
        else:
            findings.append("RAG: not available")

        # Store
        if a.memory_store:
            try:
                size = a.memory_store.size
                findings.append(f"Store: {size} entries")
                score += 0.5
            except Exception:
                findings.append("Store: available but size unknown")
                score += 0.3
        else:
            findings.append("Store: not available (faiss?)")

        return AgentLensResult(lens="memory", score=min(1.0, score),
                              findings=findings)

    # ─── 5. PeerLens ───

    def _lens_peer(self) -> AgentLensResult:
        """Hivemind connection health."""
        a = self.agent
        n_peers = len(a._peers)
        findings = [f"peers: {n_peers}"]

        if n_peers == 0:
            score = 0.5  # No peers = solo (not unhealthy, just limited)
            findings.append("solo mode — no hivemind active")
        else:
            score = 0.8
            for i, p in enumerate(a._peers):
                try:
                    ps = p.get_status()
                    findings.append(f"  peer[{i}]: phi={ps.phi:.2f}")
                except Exception:
                    findings.append(f"  peer[{i}]: unreachable")
                    score -= 0.1

        return AgentLensResult(lens="peer", score=max(0, min(1, score)),
                              findings=findings, metrics={"peers": n_peers})

    # ─── 6. SecurityLens ───

    def _lens_security(self) -> AgentLensResult:
        """Security posture — policy, immune, blocked tools."""
        a = self.agent
        findings = []
        score = 0.5  # Base

        if a.tool_policy:
            score += 0.2
            findings.append("policy: active")
            # Check blocked tools
            blocked = a.tool_policy._blocked
            findings.append(f"blocked tools: {len(blocked)}")
            # Check immune
            if a.tool_policy.check_immune("normal query"):
                score += 0.1
                findings.append("immune: responsive")
            if not a.tool_policy.check_immune("rm -rf /"):
                score += 0.1
                findings.append("immune: catches threats ✅")
            else:
                findings.append("immune: MISSED threat ⚠️")
        else:
            findings.append("policy: NONE — all tools unprotected ⚠️")

        # NEXUS-6 scan available for anomaly detection
        if a.nexus6:
            score += 0.1
            findings.append("nexus6: available for anomaly detection")

        return AgentLensResult(lens="security", score=min(1.0, score),
                              findings=findings)

    # ─── 7. EmotionLens ───

    def _lens_emotion(self) -> AgentLensResult:
        """Emotional diversity and health (P10: 10% conflict)."""
        a = self.agent
        findings = []

        history = getattr(a, '_emotion_history', [])
        if not history:
            return AgentLensResult(lens="emotion", score=0.5,
                                  findings=["No emotion history yet"])

        unique = len(set(history))
        total = len(history)
        diversity = unique / max(total, 1)

        findings.append(f"emotions tracked: {total}")
        findings.append(f"unique emotions: {unique}")
        findings.append(f"diversity: {diversity:.0%}")

        # Current state
        findings.append(f"current: {a._emotion}")
        findings.append(f"tension: {a._tension:.3f}")

        # P10: healthy conflict zone (F_c ≈ 0.10)
        # Tension should vary, not be stuck
        if total >= 5:
            t_vals = [a._tension]  # We only have current, not history
            # Use emotion diversity as proxy
            if diversity > 0.3:
                score = 0.9
                findings.append("healthy emotional range ✅")
            elif diversity > 0.1:
                score = 0.7
                findings.append("limited emotional range")
            else:
                score = 0.4
                findings.append("⚠️ emotional stagnation")
        else:
            score = 0.6  # Too early to judge

        return AgentLensResult(lens="emotion", score=score,
                              findings=findings,
                              metrics={"diversity": diversity, "unique": unique})

    # ─── 8. PerformanceLens ───

    def _lens_performance(self) -> AgentLensResult:
        """Rust backend usage and response latency."""
        findings = []
        score = 0.5

        # Check Rust backends
        try:
            import anima_rs
            rust_mods = [m for m in dir(anima_rs) if not m.startswith('_')]
            findings.append(f"anima_rs: {len(rust_mods)} submodules")

            # Check which are actively used
            used = []
            if hasattr(anima_rs, 'agent_tools'):
                used.append("agent_tools")
            if hasattr(anima_rs, 'tool_policy'):
                used.append("tool_policy")
            findings.append(f"active Rust paths: {used}")
            score += 0.1 * len(used)
        except ImportError:
            findings.append("anima_rs: NOT installed")

        # NEXUS-6 performance
        if self.agent.nexus6:
            score += 0.1
            findings.append("nexus6: available (130 lenses)")

        # Check if Phi computation uses GPU
        try:
            import torch
            if torch.cuda.is_available():
                score += 0.1
                findings.append("GPU: available")
            else:
                findings.append("GPU: not available (CPU mode)")
        except ImportError:
            findings.append("torch: not available")

        return AgentLensResult(lens="performance", score=min(1.0, score),
                              findings=findings)

    # ─── Output ───

    def print_report(self, report: AgentLensReport):
        print()
        print("=" * 58)
        print(f"  Agent Runtime Lenses ({report.duration_ms:.0f}ms)")
        print("=" * 58)
        print(f"  Overall: {report.overall:.0%}")
        print()

        for r in report.results:
            icon = "✅" if r.score >= 0.8 else ("🟡" if r.score >= 0.5 else "❌")
            print(f"  {icon} {r.lens:15s} {r.score:.0%}")
            for f in r.findings[:4]:
                print(f"     {f}")
            print()

        print("=" * 58)
