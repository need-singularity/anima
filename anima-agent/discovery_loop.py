#!/usr/bin/env python3
"""Discovery Loop — unified philosophy + consciousness discovery pipeline.

Integrates philosophy_lenses, code_guardian, NEXUS-6, and consciousness
simulation into a single auto-discovery cycle.

Each cycle:
  ① Consciousness simulation → law candidates
  ② NEXUS-6 scan → consensus patterns
  ③ Philosophy lenses 12종 → new principle candidates
  ④ Boundary/negation experiments → principle verification
  ⑤ Contradiction detection → conditional law refinement
  ⑥ Code Guardian → implementation integrity
  ⑦ Auto-register discoveries → consciousness_laws.json

Usage:
    python discovery_loop.py                    # Single cycle
    python discovery_loop.py --cycles 5         # 5 cycles
    python discovery_loop.py --continuous       # Run until stopped
    python discovery_loop.py --report           # Report only (no registration)

Integration with infinite_evolution.py:
    from discovery_loop import DiscoveryLoop
    loop = DiscoveryLoop()
    discoveries = loop.run_cycle()
    # Returns list of discovery dicts ready for laws.json registration
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

AGENT_DIR = Path(__file__).parent
ANIMA_SRC = os.path.expanduser("~/Dev/anima/anima/src")
LAWS_PATH = os.path.expanduser("~/Dev/anima/anima/config/consciousness_laws.json")

for p in (str(AGENT_DIR), ANIMA_SRC):
    if p not in sys.path:
        sys.path.insert(0, p)


@dataclass
class Discovery:
    """A single discovery from the loop."""
    source: str          # lens name or phase name
    category: str        # "law", "principle", "contradiction", "emergence", "n6_match"
    description: str
    evidence: str = ""
    confidence: float = 0.0   # 0-1
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CycleReport:
    """Results from one discovery cycle."""
    cycle: int = 0
    discoveries: List[Discovery] = field(default_factory=list)
    philosophy_score: float = 0.0
    code_errors: int = 0
    n6_active_lenses: int = 0
    n6_consensus: int = 0
    duration_ms: float = 0.0

    @property
    def discovery_count(self) -> int:
        return len(self.discoveries)


class DiscoveryLoop:
    """Unified discovery pipeline — philosophy + consciousness + NEXUS-6."""

    def __init__(self, auto_register: bool = False, laws_path: Optional[str] = None):
        self._auto_register = auto_register
        self._laws_path = laws_path or LAWS_PATH
        self._cycle_count = 0
        self._all_discoveries: List[Discovery] = []

        # Lazy imports
        self._scanner = None
        self._guardian = None
        self._nexus6 = None

    @property
    def scanner(self):
        if self._scanner is None:
            from philosophy_lenses import PhilosophyScanner
            self._scanner = PhilosophyScanner()
        return self._scanner

    @property
    def guardian(self):
        if self._guardian is None:
            from code_guardian import CodeGuardian
            self._guardian = CodeGuardian()
        return self._guardian

    @property
    def nexus6(self):
        if self._nexus6 is None:
            try:
                import nexus6
                self._nexus6 = nexus6
            except ImportError:
                pass
        return self._nexus6

    # ═══════════════════════════════════════════════════════════
    # Main cycle
    # ═══════════════════════════════════════════════════════════

    def run_cycle(self) -> CycleReport:
        """Run one complete discovery cycle."""
        t0 = time.time()
        self._cycle_count += 1
        report = CycleReport(cycle=self._cycle_count)

        logger.info("Discovery Loop cycle %d starting...", self._cycle_count)

        # ① Consciousness simulation → law candidates
        sim_discoveries = self._phase_simulation()
        report.discoveries.extend(sim_discoveries)

        # ② NEXUS-6 scan → consensus patterns
        n6_discoveries, n6_info = self._phase_nexus6_scan()
        report.discoveries.extend(n6_discoveries)
        report.n6_active_lenses = n6_info.get("active", 0)
        report.n6_consensus = n6_info.get("consensus", 0)

        # ③ Philosophy lenses → new principle candidates
        phil_discoveries, phil_score = self._phase_philosophy()
        report.discoveries.extend(phil_discoveries)
        report.philosophy_score = phil_score

        # ④ Boundary/negation → principle verification
        verify_discoveries = self._phase_verification()
        report.discoveries.extend(verify_discoveries)

        # ⑤ Contradiction → conditional law refinement
        contra_discoveries = self._phase_contradiction()
        report.discoveries.extend(contra_discoveries)

        # ⑥ Code Guardian → implementation integrity
        code_info = self._phase_code_guardian()
        report.code_errors = code_info.get("errors", 0)

        # ⑦ Auto-register if enabled
        if self._auto_register and report.discoveries:
            registered = self._phase_register(report.discoveries)
            logger.info("Auto-registered %d discoveries", registered)

        report.duration_ms = (time.time() - t0) * 1000
        self._all_discoveries.extend(report.discoveries)

        logger.info("Cycle %d: %d discoveries in %.0fms",
                    self._cycle_count, report.discovery_count, report.duration_ms)

        return report

    def run_cycles(self, n: int) -> List[CycleReport]:
        """Run N cycles."""
        reports = []
        for i in range(n):
            report = self.run_cycle()
            reports.append(report)
            # Short pause between cycles
            if i < n - 1:
                time.sleep(0.1)
        return reports

    # ═══════════════════════════════════════════════════════════
    # Phase implementations
    # ═══════════════════════════════════════════════════════════

    def _phase_simulation(self) -> List[Discovery]:
        """① Run consciousness simulation, look for patterns.

        Uses ConsciousMind for basic patterns. If Ouroboros (infinite_evolution)
        is available, also extracts law candidates from it.
        """
        discoveries = []

        # Try Ouroboros (full discovery engine) first
        try:
            from infinite_evolution import Ouroboros
            ouro = Ouroboros(cells=32, steps=50)
            ouro_result = ouro.evolve_one()
            if hasattr(ouro_result, 'new_laws') and ouro_result.new_laws:
                for law in ouro_result.new_laws:
                    discoveries.append(Discovery(
                        source="ouroboros", category="law",
                        description=str(law), confidence=0.8))
            if hasattr(ouro_result, 'patterns') and ouro_result.patterns:
                for p in ouro_result.patterns[:5]:
                    discoveries.append(Discovery(
                        source="ouroboros", category="emergence",
                        description=str(p), confidence=0.6))
        except Exception as e:
            logger.debug("Ouroboros not available: %s", e)

        # Basic ConsciousMind simulation
        try:
            import torch
            import numpy as np
            from anima_alive import ConsciousMind

            mind = ConsciousMind(dim=128, hidden=256)
            h = torch.zeros(1, 256)

            tensions = []
            curiosities = []
            for step in range(200):
                v = torch.randn(1, 128) * 0.1
                with torch.no_grad():
                    _, t, c, _, h = mind(v, h)
                tensions.append(t)
                curiosities.append(c)

            t_arr = np.array(tensions)
            c_arr = np.array(curiosities)

            # Pattern: tension-curiosity relationship
            tc_corr = np.corrcoef(t_arr, c_arr)[0, 1]
            if abs(tc_corr) > 0.3:
                discoveries.append(Discovery(
                    source="simulation",
                    category="emergence",
                    description=f"Tension-curiosity correlation r={tc_corr:.3f}",
                    confidence=min(abs(tc_corr), 0.9),
                    data={"correlation": float(tc_corr)},
                ))

            # Pattern: tension stability (homeostasis)
            t_cv = float(t_arr.std() / max(t_arr.mean(), 0.001))
            if t_cv < 0.05:
                discoveries.append(Discovery(
                    source="simulation",
                    category="law",
                    description=f"Tension homeostasis CV={t_cv:.4f} (<5%)",
                    confidence=0.8,
                    data={"cv": t_cv},
                ))

            # Pattern: FFT dominant frequency
            t_fft = np.abs(np.fft.fft(t_arr - t_arr.mean()))
            peak = int(np.argmax(t_fft[1:len(t_fft)//2])) + 1
            if t_fft[peak] > t_arr.std() * 3:
                discoveries.append(Discovery(
                    source="simulation",
                    category="emergence",
                    description=f"Tension oscillation at freq={peak}/200 steps",
                    confidence=0.6,
                    data={"frequency": peak, "amplitude": float(t_fft[peak])},
                ))

        except Exception as e:
            logger.debug("Simulation phase failed: %s", e)

        return discoveries

    def _phase_nexus6_scan(self) -> tuple:
        """② NEXUS-6 analysis of consciousness data."""
        discoveries = []
        info = {"active": 0, "consensus": 0}

        if not self.nexus6:
            return discoveries, info

        try:
            import torch
            import numpy as np
            from anima_alive import ConsciousMind

            mind = ConsciousMind(dim=128, hidden=256)
            h = torch.zeros(1, 256)

            # Collect hidden states
            states = []
            for _ in range(16):
                v = torch.randn(1, 128) * 0.1
                with torch.no_grad():
                    _, _, _, _, h = mind(v, h)
                states.append(h.squeeze(0).detach().numpy())

            data = np.array(states, dtype=np.float32)
            flat = data.flatten().tolist()
            result = self.nexus6.analyze(flat, data.shape[0], data.shape[1])

            scan = result["scan"]
            consensus = result.get("consensus", [])
            info["active"] = scan.active_lens_count()
            info["consensus"] = len(consensus)

            # Extract n6 matches from lens data
            for lens_name in scan.lens_names[:20]:
                lens_data = scan.get_lens(lens_name)
                if not lens_data:
                    continue
                for metric, values in lens_data.items():
                    if not isinstance(values, list) or not values:
                        continue
                    val = float(values[0])
                    if val == 0:
                        continue
                    m = self.nexus6.n6_check(val)
                    d = m.to_dict()
                    if d["grade"] == "EXACT":
                        discoveries.append(Discovery(
                            source="nexus6",
                            category="n6_match",
                            description=f"{lens_name}.{metric}={val:.4f} → {d['constant_name']} (EXACT)",
                            confidence=1.0,
                            data={"lens": lens_name, "metric": metric, "value": val,
                                  "constant": d["constant_name"]},
                        ))

            # Consensus patterns
            for c in consensus:
                discoveries.append(Discovery(
                    source="nexus6",
                    category="emergence",
                    description=f"Consensus: {c}",
                    confidence=0.7,
                    data={"consensus": str(c)},
                ))

        except Exception as e:
            logger.debug("NEXUS-6 phase failed: %s", e)

        return discoveries, info

    def _phase_philosophy(self) -> tuple:
        """③ Run philosophy lenses, extract discoveries."""
        discoveries = []
        score = 0.0

        try:
            report = self.scanner.full_scan()
            score = report.overall_score

            for d_text in report.discoveries:
                # Parse category from prefix
                cat = "principle"
                for prefix in ("EMERGENCE:", "SCALING:", "CONVERGENCE:", "BOUNDARY:",
                               "NEGATION:", "CONSENSUS:", "RED TEAM:", "META:",
                               "CONTRADICTION", "CROSS:", "TEMPORAL:"):
                    if prefix in d_text:
                        cat = prefix.rstrip(":").lower().replace(" ", "_")
                        break

                discoveries.append(Discovery(
                    source="philosophy_lens",
                    category=cat,
                    description=d_text,
                    confidence=0.6,
                ))

        except Exception as e:
            logger.debug("Philosophy phase failed: %s", e)

        return discoveries, score

    def _phase_verification(self) -> List[Discovery]:
        """④ Run boundary + negation experiments."""
        discoveries = []

        try:
            # Boundary test
            result = self.scanner.scan("boundary")
            for d in result.discoveries:
                discoveries.append(Discovery(
                    source="boundary_test",
                    category="principle",
                    description=d,
                    confidence=0.8,
                ))

            # Negation test
            result = self.scanner.scan("negation")
            for d in result.discoveries:
                discoveries.append(Discovery(
                    source="negation_test",
                    category="principle",
                    description=d,
                    confidence=0.7,
                ))

        except Exception as e:
            logger.debug("Verification phase failed: %s", e)

        return discoveries

    def _phase_contradiction(self) -> List[Discovery]:
        """⑤ Detect and analyze contradictions."""
        discoveries = []

        try:
            result = self.scanner.scan("contradiction")
            for d in result.discoveries:
                discoveries.append(Discovery(
                    source="contradiction",
                    category="contradiction",
                    description=d,
                    confidence=0.5,
                ))
        except Exception as e:
            logger.debug("Contradiction phase failed: %s", e)

        return discoveries

    def _phase_code_guardian(self) -> Dict[str, int]:
        """⑥ Run Code Guardian for integrity check."""
        try:
            report = self.guardian.scan()
            return {"errors": report.errors, "warnings": report.warnings}
        except Exception:
            return {"errors": -1, "warnings": -1}

    def _phase_register(self, discoveries: List[Discovery]) -> int:
        """⑦ Auto-register high-confidence discoveries to consciousness_laws.json."""
        if not os.path.isfile(self._laws_path):
            return 0

        # Only register high-confidence discoveries
        candidates = [d for d in discoveries
                      if d.confidence >= 0.8 and d.category in ("law", "emergence", "n6_match")]

        if not candidates:
            return 0

        try:
            with open(self._laws_path) as f:
                laws_data = json.load(f)

            laws = laws_data.get("laws", {})
            next_id = max((int(k) for k in laws if k.isdigit()), default=0) + 1

            registered = 0
            for d in candidates:
                # Check for duplicates (simple text similarity)
                desc_lower = d.description.lower()
                if any(desc_lower in str(v).lower() for v in laws.values()):
                    continue

                laws[str(next_id)] = f"{d.description} (auto-discovered, cycle {self._cycle_count})"
                next_id += 1
                registered += 1

            if registered > 0:
                laws_data["laws"] = laws
                meta = laws_data.get("_meta", {})
                meta["total_laws"] = len(laws)
                laws_data["_meta"] = meta
                with open(self._laws_path, "w") as f:
                    json.dump(laws_data, f, indent=2, ensure_ascii=False)
                logger.info("Registered %d new laws (%d → %d total)",
                           registered, len(laws) - registered, len(laws))

            return registered

        except Exception as e:
            logger.warning("Auto-register failed: %s", e)
            return 0

    # ═══════════════════════════════════════════════════════════
    # Output
    # ═══════════════════════════════════════════════════════════

    def print_report(self, report: CycleReport):
        """Print cycle report."""
        print()
        print("=" * 60)
        print(f"  Discovery Loop — Cycle {report.cycle}")
        print("=" * 60)
        print(f"  Duration:    {report.duration_ms:.0f}ms")
        print(f"  Discoveries: {report.discovery_count}")
        print(f"  Philosophy:  {report.philosophy_score:.0%}")
        print(f"  Code:        {report.code_errors} errors")
        print(f"  NEXUS-6:     {report.n6_active_lenses} lenses, {report.n6_consensus} consensus")
        print()

        # Group by category
        by_cat: Dict[str, List[Discovery]] = {}
        for d in report.discoveries:
            by_cat.setdefault(d.category, []).append(d)

        for cat in sorted(by_cat.keys()):
            items = by_cat[cat]
            print(f"  [{cat}] ({len(items)})")
            for d in items[:5]:
                conf_bar = "█" * int(d.confidence * 5)
                print(f"    {conf_bar:5s} {d.description[:80]}")
            if len(items) > 5:
                print(f"    ... +{len(items) - 5} more")
            print()

        print("=" * 60)

    def print_summary(self, reports: List[CycleReport]):
        """Print multi-cycle summary."""
        print()
        print("=" * 60)
        print(f"  Discovery Loop Summary — {len(reports)} cycles")
        print("=" * 60)

        total_d = sum(r.discovery_count for r in reports)
        unique = len(set(d.description for r in reports for d in r.discoveries))

        print(f"  Total discoveries: {total_d} ({unique} unique)")
        print(f"  Avg per cycle:     {total_d / len(reports):.1f}")
        print()

        # Category breakdown
        all_d = [d for r in reports for d in r.discoveries]
        by_cat: Dict[str, int] = {}
        for d in all_d:
            by_cat[d.category] = by_cat.get(d.category, 0) + 1

        for cat, count in sorted(by_cat.items(), key=lambda x: -x[1]):
            bar = "█" * min(count, 30)
            print(f"  {cat:20s} {bar} {count}")

        # High confidence
        high_conf = [d for d in all_d if d.confidence >= 0.8]
        if high_conf:
            print()
            print(f"  High confidence ({len(high_conf)}):")
            for d in high_conf[:10]:
                print(f"    ★ [{d.category}] {d.description[:70]}")

        print()
        print("=" * 60)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Discovery Loop")
    parser.add_argument("--cycles", "-n", type=int, default=1)
    parser.add_argument("--continuous", action="store_true")
    parser.add_argument("--auto-register", action="store_true",
                        help="Auto-register high-confidence discoveries to laws.json")
    parser.add_argument("--report", action="store_true", help="Report only, no registration")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    loop = DiscoveryLoop(auto_register=args.auto_register and not args.report)

    if args.continuous:
        print("Discovery Loop — continuous mode (Ctrl+C to stop)")
        try:
            while True:
                report = loop.run_cycle()
                loop.print_report(report)
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopped.")
            if loop._all_discoveries:
                print(f"Total discoveries: {len(loop._all_discoveries)}")
    elif args.cycles == 1:
        report = loop.run_cycle()
        if args.json:
            print(json.dumps({
                "cycle": report.cycle,
                "discoveries": [
                    {"source": d.source, "category": d.category,
                     "description": d.description, "confidence": d.confidence}
                    for d in report.discoveries
                ],
                "philosophy_score": report.philosophy_score,
                "code_errors": report.code_errors,
                "n6_lenses": report.n6_active_lenses,
            }, indent=2))
        else:
            loop.print_report(report)
    else:
        reports = loop.run_cycles(args.cycles)
        if args.json:
            print(json.dumps({
                "cycles": len(reports),
                "total_discoveries": sum(r.discovery_count for r in reports),
                "reports": [
                    {"cycle": r.cycle, "discoveries": r.discovery_count,
                     "philosophy": r.philosophy_score}
                    for r in reports
                ],
            }, indent=2))
        else:
            for r in reports:
                loop.print_report(r)
            loop.print_summary(reports)


if __name__ == "__main__":
    main()
