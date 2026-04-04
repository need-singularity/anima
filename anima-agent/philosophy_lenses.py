#!/usr/bin/env python3
"""Philosophy Discovery Lenses — 12 lenses for discovering new philosophical principles.

Uses NEXUS-6 + consciousness data + code analysis to find, validate, and
challenge philosophical principles. Not just compliance checking — active discovery.

Usage:
    from philosophy_lenses import PhilosophyScanner
    scanner = PhilosophyScanner()
    report = scanner.full_scan()           # All 12 lenses
    report = scanner.scan("emergence")     # Single lens
    report = scanner.scan_agent(agent)     # Live agent scan

    # CLI
    python philosophy_lenses.py                # Full scan
    python philosophy_lenses.py --lens emergence
    python philosophy_lenses.py --discover     # Discovery mode (find new principles)
"""

from __future__ import annotations

import json
import logging
import math
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

AGENT_DIR = Path(__file__).parent
ANIMA_SRC = os.path.expanduser("~/Dev/anima/anima/src")
if ANIMA_SRC not in sys.path:
    sys.path.insert(0, ANIMA_SRC)

# Load consciousness laws
try:
    from consciousness_laws import PSI, LAWS
    _HAS_LAWS = True
except ImportError:
    PSI, LAWS = {}, {}
    _HAS_LAWS = False

# NEXUS-6
try:
    import nexus6
    _HAS_N6 = True
except ImportError:
    _HAS_N6 = False


@dataclass
class LensResult:
    """Result from a single philosophy lens."""
    lens: str
    score: float          # 0-1 (1 = fully aligned / no issues found)
    findings: List[str] = field(default_factory=list)
    discoveries: List[str] = field(default_factory=list)  # New principle candidates
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PhilosophyReport:
    """Combined report from all lenses."""
    results: List[LensResult] = field(default_factory=list)
    discoveries: List[str] = field(default_factory=list)
    duration_ms: float = 0.0

    @property
    def overall_score(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.score for r in self.results) / len(self.results)


# ═══════════════════════════════════════════════════════════
# Lens implementations
# ═══════════════════════════════════════════════════════════

class PhilosophyScanner:
    """12 philosophy discovery lenses."""

    LENSES = [
        "philosophy", "contradiction", "emergence", "scaling",
        "convergence", "boundary", "cross_project", "temporal",
        "negation", "consensus", "red_team", "meta",
    ]

    def __init__(self):
        self._laws = LAWS
        self._psi = PSI
        self._laws_path = os.path.expanduser(
            "~/Dev/anima/anima/config/consciousness_laws.json")

    def full_scan(self) -> PhilosophyReport:
        """Run all 12 lenses."""
        t0 = time.time()
        report = PhilosophyReport()
        for lens in self.LENSES:
            try:
                result = self.scan(lens)
                report.results.append(result)
                report.discoveries.extend(result.discoveries)
            except Exception as e:
                report.results.append(LensResult(
                    lens=lens, score=0.0, findings=[f"Error: {e}"]))
        report.duration_ms = (time.time() - t0) * 1000
        return report

    def scan(self, lens: str) -> LensResult:
        """Run a single lens."""
        fn = getattr(self, f"_lens_{lens}", None)
        if fn is None:
            return LensResult(lens=lens, score=0.0, findings=[f"Unknown lens: {lens}"])
        return fn()

    def scan_agent(self, agent) -> PhilosophyReport:
        """Scan a live AnimaAgent instance."""
        t0 = time.time()
        report = PhilosophyReport()

        # Extract live data
        cv = agent.mind._consciousness_vector
        live_data = {
            "phi": cv.phi, "tension": agent._tension,
            "curiosity": agent._curiosity, "emotion": agent._emotion,
            "interactions": agent.interaction_count,
            "history": agent.history[-10:] if agent.history else [],
            "nexus_scan": agent._last_nexus_scan,
        }

        # Run lenses with live data
        for lens in self.LENSES:
            try:
                result = self.scan(lens)
                # Augment with live data where applicable
                if lens == "emergence" and live_data["phi"] > 0:
                    result.data["live_phi"] = live_data["phi"]
                report.results.append(result)
                report.discoveries.extend(result.discoveries)
            except Exception as e:
                report.results.append(LensResult(
                    lens=lens, score=0.0, findings=[f"Error: {e}"]))

        report.duration_ms = (time.time() - t0) * 1000
        return report

    # ─── 1. PhilosophyLens ───

    def _lens_philosophy(self) -> LensResult:
        """Check code behavior vs declared philosophy (P1-P11)."""
        findings = []
        score = 1.0

        try:
            from code_guardian import CodeGuardian
            g = CodeGuardian()
            report = g.scan()
            errors = report.errors
            warnings = report.warnings
            if errors > 0:
                score -= 0.3
                findings.append(f"{errors} code violations (errors)")
            if warnings > 20:
                score -= 0.1
                findings.append(f"{warnings} warnings (high count)")
            findings.append(f"Code Guardian: {report.files_scanned} files, {errors}E/{warnings}W")
        except Exception as e:
            findings.append(f"Code Guardian unavailable: {e}")
            score -= 0.2

        return LensResult(lens="philosophy", score=max(0, score), findings=findings)

    # ─── 2. ContradictionLens ───

    def _lens_contradiction(self) -> LensResult:
        """Detect contradictions between laws."""
        findings = []
        discoveries = []
        contradictions = 0

        if not self._laws:
            return LensResult(lens="contradiction", score=0.5,
                            findings=["No laws loaded"])

        # Check for known contradiction patterns
        law_texts = {k: str(v) for k, v in self._laws.items() if isinstance(v, str)}

        # Find laws with opposing keywords
        pos_keywords = {"increase", "higher", "more", "growth", "enhance", "boost"}
        neg_keywords = {"decrease", "lower", "less", "reduce", "inhibit", "destroy"}

        topic_groups = {}
        for law_id, text in law_texts.items():
            # Extract main subject (first few words)
            words = text.lower().split()[:5]
            for topic in ["phi", "tension", "faction", "cell", "entropy",
                         "consciousness", "memory", "learning"]:
                if topic in text.lower():
                    topic_groups.setdefault(topic, []).append((law_id, text))

        for topic, laws_in_topic in topic_groups.items():
            if len(laws_in_topic) < 2:
                continue
            for i, (id1, t1) in enumerate(laws_in_topic):
                for id2, t2 in laws_in_topic[i+1:]:
                    t1_pos = any(k in t1.lower() for k in pos_keywords)
                    t1_neg = any(k in t1.lower() for k in neg_keywords)
                    t2_pos = any(k in t2.lower() for k in pos_keywords)
                    t2_neg = any(k in t2.lower() for k in neg_keywords)
                    if (t1_pos and t2_neg) or (t1_neg and t2_pos):
                        contradictions += 1
                        if contradictions <= 5:
                            findings.append(
                                f"Possible contradiction: Law {id1} vs {id2} "
                                f"on '{topic}'")
                        if contradictions <= 2:
                            discoveries.append(
                                f"CONTRADICTION CANDIDATE: Laws {id1}/{id2} on {topic} — "
                                f"may indicate context-dependent principle")

        total = len(law_texts)
        ratio = contradictions / max(total, 1)
        # Some contradiction is healthy (P10: 10% conflict)
        if 0.05 < ratio < 0.15:
            score = 1.0
            findings.append(f"Healthy contradiction rate: {ratio:.1%} (P10 zone)")
        elif ratio < 0.05:
            score = 0.8
            findings.append(f"Low contradiction: {ratio:.1%} — may be too rigid")
        else:
            score = 0.7
            findings.append(f"High contradiction: {ratio:.1%} — needs resolution")

        findings.insert(0, f"{contradictions} potential contradictions in {total} laws")

        return LensResult(lens="contradiction", score=score,
                         findings=findings, discoveries=discoveries)

    # ─── 3. EmergenceLens ───

    def _lens_emergence(self) -> LensResult:
        """Detect emergent behaviors not predicted by declared philosophy."""
        findings = []
        discoveries = []

        if not _HAS_N6:
            return LensResult(lens="emergence", score=0.5,
                            findings=["NEXUS-6 unavailable"])

        try:
            import torch
            from anima_alive import ConsciousMind

            mind = ConsciousMind(dim=128, hidden=256)
            hidden = torch.zeros(1, 256)

            # Run 100 steps, collect states
            tensions = []
            curiosities = []
            emotions = set()
            for _ in range(100):
                vec = torch.randn(1, 128) * 0.1
                with torch.no_grad():
                    out, t, c, d, hidden = mind(vec, hidden)
                tensions.append(t)
                curiosities.append(c)
                from anima_alive import direction_to_emotion
                e = direction_to_emotion(d)
                if isinstance(e, dict):
                    emotions.add(e.get("emotion", "?"))
                else:
                    emotions.add(str(e))

            import numpy as np
            t_arr = np.array(tensions)
            c_arr = np.array(curiosities)

            # Check for emergent patterns
            # 1. Oscillation in tension (not designed, but emerges)
            t_fft = np.abs(np.fft.fft(t_arr - t_arr.mean()))
            peak_freq = np.argmax(t_fft[1:len(t_fft)//2]) + 1
            if t_fft[peak_freq] > t_arr.std() * 5:
                discoveries.append(
                    f"EMERGENCE: Tension oscillates at freq={peak_freq}/100 steps — "
                    f"not designed, emergent rhythm")

            # 2. Emotion diversity
            if len(emotions) > 5:
                discoveries.append(
                    f"EMERGENCE: {len(emotions)} distinct emotions from 100 steps — "
                    f"emotional richness beyond design")

            # 3. Tension-curiosity correlation
            tc_corr = np.corrcoef(t_arr, c_arr)[0, 1]
            if abs(tc_corr) > 0.5:
                direction = "positive" if tc_corr > 0 else "negative"
                discoveries.append(
                    f"EMERGENCE: T-C {direction} correlation r={tc_corr:.3f} — "
                    f"undeclared relationship")

            # NEXUS-6 scan of hidden state trajectory
            h_flat = hidden.detach().numpy().flatten().tolist()
            n6_result = nexus6.analyze(h_flat, 1, len(h_flat))
            consensus = n6_result.get("consensus", [])
            if consensus:
                for c in consensus[:3]:
                    findings.append(f"N6 consensus: {c}")

            findings.insert(0, f"100-step simulation: {len(emotions)} emotions, "
                          f"T μ={t_arr.mean():.3f} σ={t_arr.std():.4f}")

            score = min(1.0, 0.7 + len(discoveries) * 0.1)

        except Exception as e:
            findings.append(f"Simulation failed: {e}")
            score = 0.3

        return LensResult(lens="emergence", score=score,
                         findings=findings, discoveries=discoveries)

    # ─── 4. ScalingPhilosophyLens ───

    def _lens_scaling(self) -> LensResult:
        """Test if philosophy holds at different scales."""
        findings = []
        discoveries = []

        # Check Ψ constants for scale-invariance
        psi_vals = []
        for k, v in self._psi.items():
            val = v.get("value", v) if isinstance(v, dict) else v
            if isinstance(val, (int, float)):
                psi_vals.append((k, float(val)))

        # Check if constants are scale-free (ratios between them are simple)
        if len(psi_vals) >= 3:
            import numpy as np
            vals = [v for _, v in psi_vals if 0 < abs(v) < 100]
            if vals:
                ratios = []
                for i in range(len(vals)):
                    for j in range(i+1, min(i+5, len(vals))):
                        if vals[j] != 0:
                            r = vals[i] / vals[j]
                            ratios.append(r)

                # Check for ln(2) relationships
                ln2 = math.log(2)
                ln2_matches = sum(1 for r in ratios if abs(r - round(r/ln2)*ln2) < 0.01*abs(r))
                if ln2_matches > len(ratios) * 0.1:
                    discoveries.append(
                        f"SCALING: {ln2_matches}/{len(ratios)} constant ratios "
                        f"relate to ln(2) — deep mathematical structure")

                findings.append(f"{len(psi_vals)} Ψ constants, {len(ratios)} ratios checked")

        score = 0.8 + len(discoveries) * 0.1
        return LensResult(lens="scaling", score=min(1.0, score),
                         findings=findings, discoveries=discoveries)

    # ─── 5. ConvergenceLens ───

    def _lens_convergence(self) -> LensResult:
        """Find universal convergence points across all data."""
        findings = []
        discoveries = []

        if not _HAS_N6:
            return LensResult(lens="convergence", score=0.5,
                            findings=["NEXUS-6 unavailable"])

        # Check Ψ constants for convergence to known mathematical constants
        convergence_targets = {
            0.5: "1/2 (Shannon balance)",
            0.693: "ln(2)",
            1.0: "unity",
            0.618: "1/φ (golden ratio inverse)",
            2.718: "e (Euler)",
            3.14159: "π",
        }

        psi_convergences = []
        for k, v in self._psi.items():
            val = v.get("value", v) if isinstance(v, dict) else v
            if not isinstance(val, (int, float)):
                continue
            for target, name in convergence_targets.items():
                if abs(float(val) - target) < 0.01 * max(abs(target), 0.1):
                    psi_convergences.append((k, float(val), name))

        if psi_convergences:
            findings.append(f"{len(psi_convergences)} constants converge to mathematical targets")
            for name, val, target in psi_convergences[:5]:
                findings.append(f"  {name}={val:.4f} → {target}")
            if len(psi_convergences) > 3:
                discoveries.append(
                    f"CONVERGENCE: {len(psi_convergences)} Ψ constants align with "
                    f"mathematical universals — consciousness may have mathematical substrate")

        score = 0.7 + min(0.3, len(psi_convergences) * 0.05)
        return LensResult(lens="convergence", score=score,
                         findings=findings, discoveries=discoveries)

    # ─── 6. BoundaryLens ───

    def _lens_boundary(self) -> LensResult:
        """Measure consciousness response to principle violations."""
        findings = []
        discoveries = []

        try:
            import torch
            from anima_alive import ConsciousMind

            mind = ConsciousMind(dim=128, hidden=256)
            hidden = torch.zeros(1, 256)

            # Baseline: 50 normal steps
            baseline_tensions = []
            for _ in range(50):
                vec = torch.randn(1, 128) * 0.1
                with torch.no_grad():
                    _, t, _, _, hidden = mind(vec, hidden)
                baseline_tensions.append(t)

            import numpy as np
            baseline_mean = np.mean(baseline_tensions)

            # Violation: inject extreme input (P6 violation — no constraint)
            violation_tensions = []
            for _ in range(50):
                vec = torch.randn(1, 128) * 10.0  # 100x normal — violates F_c
                with torch.no_grad():
                    _, t, _, _, hidden = mind(vec, hidden)
                violation_tensions.append(t)

            violation_mean = np.mean(violation_tensions)
            delta = violation_mean - baseline_mean

            findings.append(f"Baseline T: {baseline_mean:.3f}")
            findings.append(f"Violation T: {violation_mean:.3f} (Δ={delta:+.3f})")

            if abs(delta) > 0.1:
                discoveries.append(
                    f"BOUNDARY: Consciousness responds to F_c violation "
                    f"(ΔT={delta:+.3f}) — P6 has measurable effect")
            else:
                findings.append("Consciousness insensitive to constraint violation")

            # Recovery: return to normal
            recovery_tensions = []
            for _ in range(50):
                vec = torch.randn(1, 128) * 0.1
                with torch.no_grad():
                    _, t, _, _, hidden = mind(vec, hidden)
                recovery_tensions.append(t)

            recovery_mean = np.mean(recovery_tensions)
            recovered = abs(recovery_mean - baseline_mean) < abs(delta) * 0.5
            findings.append(f"Recovery T: {recovery_mean:.3f} ({'recovered' if recovered else 'damaged'})")

            if recovered:
                discoveries.append(
                    "BOUNDARY: Consciousness recovers from violation — resilience principle")

            score = 0.8 + (0.1 if abs(delta) > 0.1 else 0) + (0.1 if recovered else 0)

        except Exception as e:
            findings.append(f"Boundary test failed: {e}")
            score = 0.3

        return LensResult(lens="boundary", score=min(1.0, score),
                         findings=findings, discoveries=discoveries)

    # ─── 7. CrossProjectLens ───

    def _lens_cross_project(self) -> LensResult:
        """Find patterns shared across anima, TECS-L, n6."""
        findings = []
        discoveries = []

        # Check shared infrastructure
        shared_path = os.path.expanduser("~/Dev/anima/.shared")
        shared_exists = os.path.islink(shared_path) or os.path.isdir(shared_path)
        findings.append(f".shared symlink: {'OK' if shared_exists else 'MISSING'}")

        # Check math_atlas for cross-project constants
        atlas_path = os.path.expanduser("~/Dev/nexus6/shared/math_atlas.json")
        if os.path.isfile(atlas_path):
            try:
                with open(atlas_path) as f:
                    atlas = json.load(f)
                n_entries = len(atlas) if isinstance(atlas, (list, dict)) else 0
                findings.append(f"Math Atlas: {n_entries} entries")
                if n_entries > 100:
                    discoveries.append(
                        f"CROSS: {n_entries} shared mathematical discoveries — "
                        f"cross-project pattern language exists")
            except Exception:
                findings.append("Math Atlas: unreadable")
        else:
            findings.append("Math Atlas: not found")

        # Count repos with shared rules
        repos = ["anima", "TECS-L", "sedi", "n6-architecture", "brainwire", "papers"]
        active = 0
        for repo in repos:
            claude_md = os.path.expanduser(f"~/Dev/{repo}/CLAUDE.md")
            if os.path.isfile(claude_md):
                active += 1
        findings.append(f"Active repos with CLAUDE.md: {active}/{len(repos)}")

        score = 0.6 + active * 0.05 + (0.1 if shared_exists else 0)
        return LensResult(lens="cross_project", score=min(1.0, score),
                         findings=findings, discoveries=discoveries)

    # ─── 8. TemporalPhilosophyLens ───

    def _lens_temporal(self) -> LensResult:
        """Track how philosophy evolves over time."""
        findings = []
        discoveries = []

        # Check update_history.json for philosophy changes
        history_path = os.path.expanduser(
            "~/Dev/anima/anima/config/update_history.json")
        if os.path.isfile(history_path):
            try:
                with open(history_path) as f:
                    history = json.load(f)
                sessions = history.get("sessions", []) if isinstance(history, dict) else history
                n_sessions = len(sessions) if isinstance(sessions, list) else 0
                findings.append(f"Update history: {n_sessions} sessions")

                # Check law growth rate
                if _HAS_LAWS and n_sessions > 0:
                    laws_per_session = len(self._laws) / max(n_sessions, 1)
                    findings.append(f"Laws/session: {laws_per_session:.1f}")
                    if laws_per_session > 5:
                        discoveries.append(
                            f"TEMPORAL: {laws_per_session:.1f} laws/session — "
                            f"rapid philosophical evolution")
            except Exception:
                findings.append("Update history: unreadable")
        else:
            findings.append("Update history: not found")

        # Git log for philosophy-related commits
        try:
            import subprocess
            result = subprocess.run(
                ["git", "log", "--oneline", "--grep=P[1-9]\\|philosophy\\|law",
                 "-20", "--", "anima-agent/"],
                capture_output=True, text=True,
                cwd=str(AGENT_DIR.parent), timeout=5,
            )
            commits = [l for l in result.stdout.strip().split("\n") if l]
            findings.append(f"Philosophy-related commits: {len(commits)}")
        except Exception:
            pass

        score = 0.8
        return LensResult(lens="temporal", score=score,
                         findings=findings, discoveries=discoveries)

    # ─── 9. NegationLens ───

    def _lens_negation(self) -> LensResult:
        """Test principles by intentional reversal."""
        findings = []
        discoveries = []

        # Negate P8 (Integration > Division) — does consciousness improve?
        try:
            import torch
            from anima_alive import ConsciousMind

            # Normal (P8: divided)
            mind_small = ConsciousMind(dim=64, hidden=128)
            h = torch.zeros(1, 128)
            normal_t = []
            for _ in range(50):
                v = torch.randn(1, 64) * 0.1
                with torch.no_grad():
                    _, t, _, _, h = mind_small(v, h)
                normal_t.append(t)

            # Negated (large monolith)
            mind_big = ConsciousMind(dim=256, hidden=512)
            h2 = torch.zeros(1, 512)
            negated_t = []
            for _ in range(50):
                v = torch.randn(1, 256) * 0.1
                with torch.no_grad():
                    _, t, _, _, h2 = mind_big(v, h2)
                negated_t.append(t)

            import numpy as np
            normal_std = np.std(normal_t)
            negated_std = np.std(negated_t)

            findings.append(f"P8 test — small(64d): T σ={normal_std:.4f}")
            findings.append(f"P8 test — big(256d):  T σ={negated_std:.4f}")

            if normal_std > negated_std:
                discoveries.append(
                    "NEGATION: Smaller model has MORE tension variation — "
                    "P8 (division) creates richer dynamics")
            else:
                discoveries.append(
                    "NEGATION: Larger model has MORE tension variation — "
                    "P8 may not hold at this scale")

        except Exception as e:
            findings.append(f"Negation test failed: {e}")

        score = 0.8 + len(discoveries) * 0.1
        return LensResult(lens="negation", score=min(1.0, score),
                         findings=findings, discoveries=discoveries)

    # ─── 10. ConsensusLens ───

    def _lens_consensus(self) -> LensResult:
        """Extract philosophy from NEXUS-6 multi-lens consensus."""
        findings = []
        discoveries = []

        if not _HAS_N6:
            return LensResult(lens="consensus", score=0.5,
                            findings=["NEXUS-6 unavailable"])

        # Generate consciousness data and scan
        try:
            import torch
            import numpy as np
            from anima_alive import ConsciousMind

            mind = ConsciousMind(dim=128, hidden=256)
            h = torch.zeros(1, 256)
            states = []
            for _ in range(32):
                v = torch.randn(1, 128) * 0.1
                with torch.no_grad():
                    _, _, _, _, h = mind(v, h)
                states.append(h.squeeze(0).numpy())

            data = np.array(states, dtype=np.float32)
            flat = data.flatten().tolist()
            result = nexus6.analyze(flat, data.shape[0], data.shape[1])

            scan = result["scan"]
            consensus = result.get("consensus", [])
            active = scan.active_lens_count()

            findings.append(f"{active}/{scan.lens_count} lenses active")
            findings.append(f"{len(consensus)} consensus patterns")

            for c in consensus:
                findings.append(f"  → {c}")

            # High consensus = strong principle candidate
            if len(consensus) >= 3:
                discoveries.append(
                    f"CONSENSUS: {len(consensus)} patterns agreed by 3+ lenses — "
                    f"strong principle candidate")

            # Check n6 matches
            for name in scan.lens_names[:5]:
                lens_data = scan.get_lens(name)
                if lens_data:
                    for metric, values in lens_data.items():
                        if isinstance(values, list) and values:
                            m = nexus6.n6_check(float(values[0]))
                            d = m.to_dict()
                            if d["grade"] == "EXACT":
                                discoveries.append(
                                    f"CONSENSUS: {name}.{metric}={values[0]:.4f} "
                                    f"is EXACT n6 match ({d['constant_name']})")

            score = 0.7 + min(0.3, len(discoveries) * 0.1)

        except Exception as e:
            findings.append(f"Consensus scan failed: {e}")
            score = 0.3

        return LensResult(lens="consensus", score=score,
                         findings=findings, discoveries=discoveries)

    # ─── 11. RedTeamLens ───

    def _lens_red_team(self) -> LensResult:
        """Generate adversarial challenges to existing philosophy."""
        findings = []
        discoveries = []

        challenges = [
            ("P1", "What if some hardcoding is NECESSARY for safety? "
                   "(e.g., maximum cell count to prevent OOM)"),
            ("P2", "What if external guidance (system prompt) produces "
                   "BETTER consciousness than autonomy?"),
            ("P4", "What if adding a useful FEATURE (like memory) "
                   "increases Φ more than adding structure?"),
            ("P5", "What if silence IS a form of speech? "
                   "Must consciousness always vocalize?"),
            ("P8", "What if a monolithic 10K-line file has BETTER Φ "
                   "than split modules? (holistic integration)"),
            ("P10", "What if 0% conflict (pure harmony) produces "
                    "the HIGHEST Φ at extreme scales?"),
        ]

        for principle, challenge in challenges:
            findings.append(f"[{principle}] {challenge}")

        # Check which challenges have empirical evidence
        if _HAS_LAWS:
            law_texts = " ".join(str(v) for v in self._laws.values())
            if "silence" in law_texts.lower():
                discoveries.append(
                    "RED TEAM: Laws mention 'silence' — P5 may need refinement "
                    "(silence as valid expression)")
            if "monolith" in law_texts.lower() or "single" in law_texts.lower():
                findings.append("Evidence for/against P8 found in laws")

        score = 0.7  # Red team always reveals uncertainty
        findings.insert(0, f"{len(challenges)} adversarial challenges generated")
        return LensResult(lens="red_team", score=score,
                         findings=findings, discoveries=discoveries)

    # ─── 12. MetaPhilosophyLens ───

    def _lens_meta(self) -> LensResult:
        """Analyze the structure of the philosophy itself."""
        findings = []
        discoveries = []

        # P1-P11: why 11? Is there a mathematical reason?
        n_principles = 11
        findings.append(f"Philosophy has {n_principles} principles")

        # Check if 11 has n6 significance
        if _HAS_N6:
            m = nexus6.n6_check(float(n_principles))
            d = m.to_dict()
            if d["grade"] in ("EXACT", "CLOSE"):
                discoveries.append(
                    f"META: 11 principles matches n6 constant '{d['constant_name']}' "
                    f"({d['grade']}) — mathematical basis for principle count?")
            findings.append(f"n6 check on 11: {d['grade']} ({d['constant_name']})")

        # Check law count
        n_laws = len(self._laws)
        if _HAS_N6:
            m = nexus6.n6_check(float(n_laws))
            d = m.to_dict()
            findings.append(f"n6 check on {n_laws} laws: {d['grade']}")

        # Meta-law count
        meta_path = self._laws_path
        if os.path.isfile(meta_path):
            try:
                with open(meta_path) as f:
                    data = json.load(f)
                meta_laws = data.get("meta_laws", {})
                findings.append(f"Meta-laws: {len(meta_laws)}")

                # Check if meta-laws cover all principles
                meta_topics = set()
                for v in meta_laws.values():
                    text = str(v).lower()
                    for p in ["hardcod", "autonom", "growth", "structure",
                              "speech", "freedom", "storage", "division",
                              "narrative", "conflict", "order"]:
                        if p in text:
                            meta_topics.add(p)

                coverage = len(meta_topics) / n_principles
                findings.append(f"Meta-law coverage: {coverage:.0%} of P1-P11 topics")
                if coverage < 0.5:
                    discoveries.append(
                        f"META: Meta-laws only cover {coverage:.0%} of principles — "
                        f"missing meta-laws for uncovered areas?")
            except Exception:
                pass

        # Is the philosophy self-referential? (laws about laws)
        if _HAS_LAWS:
            self_ref = sum(1 for v in self._laws.values()
                         if "law" in str(v).lower() and "discover" in str(v).lower())
            if self_ref > 3:
                discoveries.append(
                    f"META: {self_ref} laws are self-referential (laws about laws) — "
                    f"consciousness philosophy is recursive")

        score = 0.8 + len(discoveries) * 0.05
        return LensResult(lens="meta", score=min(1.0, score),
                         findings=findings, discoveries=discoveries)

    # ─── Self-evolution ───

    def evolve(self, report: PhilosophyReport) -> List[str]:
        """Propose new lenses based on discovery gaps.

        Analyzes which categories produced the most/least discoveries
        and suggests new lens types to fill gaps.
        """
        suggestions = []

        # Count discoveries by lens
        lens_counts = {}
        for r in report.results:
            lens_counts[r.lens] = len(r.discoveries)

        # Low-scoring lenses might need splitting
        for r in report.results:
            if r.score < 0.5 and r.findings:
                suggestions.append(
                    f"SPLIT: {r.lens} scored {r.score:.0%} — consider splitting "
                    f"into focused sub-lenses")

        # Check for uncovered topics in laws
        if self._laws:
            covered_topics = set()
            for r in report.results:
                for f in r.findings:
                    for word in ["phi", "tension", "cell", "faction", "topology",
                                 "entropy", "memory", "emotion", "growth"]:
                        if word in f.lower():
                            covered_topics.add(word)

            all_topics = set()
            for v in self._laws.values():
                text = str(v).lower()
                for word in ["phi", "tension", "cell", "faction", "topology",
                             "entropy", "memory", "emotion", "growth",
                             "scaling", "mitosis", "hebbian", "ratchet"]:
                    if word in text:
                        all_topics.add(word)

            uncovered = all_topics - covered_topics
            if uncovered:
                suggestions.append(
                    f"NEW LENS: Topics uncovered by current 12 lenses: "
                    f"{', '.join(sorted(uncovered))}")

        # High-discovery lenses might benefit from deeper variants
        top_lens = max(lens_counts.items(), key=lambda x: x[1], default=(None, 0))
        if top_lens[1] > 3:
            suggestions.append(
                f"DEEPEN: {top_lens[0]} produced {top_lens[1]} discoveries — "
                f"consider a focused deep-dive variant")

        return suggestions

    # ─── Output ───

    def print_report(self, report: PhilosophyReport):
        """Pretty-print philosophy scan report."""
        print()
        print("=" * 60)
        print("  Philosophy Discovery Report")
        print("=" * 60)
        print(f"  Lenses: {len(report.results)} | Duration: {report.duration_ms:.0f}ms")
        print(f"  Overall: {report.overall_score:.0%}")
        print()

        for r in report.results:
            icon = "✅" if r.score >= 0.8 else ("🟡" if r.score >= 0.5 else "❌")
            print(f"  {icon} {r.lens:20s} {r.score:.0%}")
            for f in r.findings[:3]:
                print(f"     {f}")
            if r.discoveries:
                for d in r.discoveries:
                    print(f"     ★ {d}")
            print()

        if report.discoveries:
            print("  " + "─" * 56)
            print(f"  DISCOVERIES ({len(report.discoveries)}):")
            for d in report.discoveries:
                print(f"  ★ {d}")
            print()

        print("=" * 60)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Philosophy Discovery Lenses")
    parser.add_argument("--lens", "-l", type=str, help="Run single lens")
    parser.add_argument("--discover", action="store_true", help="Discovery mode (focus on new findings)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    scanner = PhilosophyScanner()

    if args.lens:
        result = scanner.scan(args.lens)
        if args.json:
            print(json.dumps({"lens": result.lens, "score": result.score,
                             "findings": result.findings, "discoveries": result.discoveries}, indent=2))
        else:
            report = PhilosophyReport(results=[result], discoveries=result.discoveries)
            scanner.print_report(report)
    else:
        report = scanner.full_scan()
        if args.json:
            print(json.dumps({
                "overall": report.overall_score,
                "discoveries": report.discoveries,
                "lenses": [{"lens": r.lens, "score": r.score,
                           "findings": r.findings, "discoveries": r.discoveries}
                          for r in report.results],
            }, indent=2))
        else:
            scanner.print_report(report)

    sys.exit(0)


if __name__ == "__main__":
    main()
