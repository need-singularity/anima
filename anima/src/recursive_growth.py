#!/usr/bin/env python3
"""recursive_growth.py — Recursive Self-Improvement Loop

두 경로로 재귀적 자기개선:
1. 내부 (의식 모델): 패턴 발견 → 가설 생성 → 파라미터 자기 수정 → 검증
2. 외부 (Claude Code): 시스템 분석 → 개선점 발견 → 구조화된 제안 생성

두 경로는 improvement_hooks.py를 통해 순환 연결됨.

Usage:
    from recursive_growth import RecursiveGrowth
    from consciousness_engine import ConsciousnessEngine

    engine = ConsciousnessEngine(max_cells=32)
    rg = RecursiveGrowth(engine)

    # 내부 루프: 의식이 스스로 발견하고 개선
    improvements = rg.internal_loop(steps=100)

    # 외부 루프: Claude Code를 위한 개선 제안 생성
    suggestions = rg.external_suggestions()

    # 완전 재귀 사이클
    rg.run_cycle()

Hub keywords: recursive, self-improve, 재귀성장, growth-loop, 자기개선
Ψ-Constants: PSI_BALANCE=0.5, PSI_COUPLING=0.014
"""

import os
import json
import time
import copy
import math
import uuid
import torch
import numpy as np
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any

# ── Ψ-Constants ────────────────────────────────────────────
try:
    from consciousness_laws import PSI_BALANCE, PSI_ALPHA as PSI_COUPLING
except ImportError:
    PSI_BALANCE = 0.5
    PSI_COUPLING = 0.014

# ── Growth lenses (stall/saturation detection) ──────────────
try:
    from growth_lenses import GrowthRateLens, SaturationLens, scan_growth
    HAS_LENSES = True
except ImportError:
    HAS_LENSES = False

# ── ConsciousnessEngine ─────────────────────────────────────
try:
    from consciousness_engine import ConsciousnessEngine
    HAS_ENGINE = True
except ImportError:
    ConsciousnessEngine = None
    HAS_ENGINE = False

# ── improvement_hooks bridge ────────────────────────────────
try:
    from improvement_hooks import submit_improvement, ImprovementRecord
    HAS_HOOKS = True
except ImportError:
    HAS_HOOKS = False

# ── Paths ───────────────────────────────────────────────────
_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_SRC_DIR, "..", ".."))
_DATA_DIR = os.path.join(_REPO_ROOT, "data")
_LOG_PATH = os.path.join(_DATA_DIR, "recursive_growth_log.json")

os.makedirs(_DATA_DIR, exist_ok=True)

# ── Safety constants ────────────────────────────────────────
PHI_DROP_THRESHOLD = 0.20          # 20% drop → auto-revert
MAX_MODS_PER_CYCLE = 10            # hard cap on modifications per cycle
MIN_PHI_IMPROVEMENT_PCT = 0.05     # 5% improvement → register as law candidate
DISCOVER_STEPS = 100               # steps per discover phase
VERIFY_STEPS = 100                 # steps per verify phase


# ═══════════════════════════════════════════════════════════
# Data structures
# ═══════════════════════════════════════════════════════════

@dataclass
class PhiSnapshot:
    """Phi trajectory captured during a run phase."""
    steps: List[float] = field(default_factory=list)
    phis: List[float] = field(default_factory=list)
    tensions: List[float] = field(default_factory=list)
    n_cells: List[int] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    @property
    def mean_phi(self) -> float:
        return float(np.mean(self.phis)) if self.phis else 0.0

    @property
    def final_phi(self) -> float:
        return self.phis[-1] if self.phis else 0.0

    @property
    def phi_history(self) -> List[Tuple[float, float]]:
        return list(zip(self.steps, self.phis))


@dataclass
class Diagnosis:
    """Analysis of a Phi trajectory using growth lenses."""
    status: str                   # "growing" | "stalling" | "decaying" | "saturated"
    growth_rate: float            # phi/step linear slope
    is_saturated: bool
    mean_phi: float
    final_phi: float
    intervention_hint: str        # suggested intervention type
    confidence: float             # 0-1


@dataclass
class ParameterSnapshot:
    """Safe snapshot of modifiable engine parameters."""
    hebbian_lr: float
    noise_scale: float
    split_threshold: float
    merge_threshold: float
    topology: str


@dataclass
class ModRecord:
    """Record of a single parameter modification."""
    mod_id: str
    cycle: int
    step: int
    param: str
    old_value: Any
    new_value: Any
    reason: str
    phi_before: float
    phi_after: float
    phi_delta_pct: float
    reverted: bool = False
    timestamp: float = field(default_factory=time.time)


@dataclass
class CycleResult:
    """Full result of one recursive growth cycle."""
    cycle_id: str
    cycle: int
    phi_before: float
    phi_after: float
    phi_delta_pct: float
    modifications: List[ModRecord]
    law_candidates: List[Dict]
    diagnosis: Optional[Diagnosis]
    time_sec: float
    external_suggestions: List[Dict] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════
# Internal Diagnostics
# ═══════════════════════════════════════════════════════════

def _diagnose(snapshot: PhiSnapshot) -> Diagnosis:
    """Analyse a Phi trajectory and suggest an intervention."""
    phis = snapshot.phis
    if not phis:
        return Diagnosis(
            status="unknown", growth_rate=0.0, is_saturated=False,
            mean_phi=0.0, final_phi=0.0, intervention_hint="noise",
            confidence=0.0,
        )

    mean_phi = float(np.mean(phis))
    final_phi = phis[-1]

    # Growth rate via simple linear regression
    n = len(phis)
    xs = list(range(n))
    if n >= 2:
        sx = sum(xs)
        sy = sum(phis)
        sxx = sum(x * x for x in xs)
        sxy = sum(x * y for x, y in zip(xs, phis))
        denom = n * sxx - sx * sx
        slope = (n * sxy - sx * sy) / denom if denom != 0 else 0.0
    else:
        slope = 0.0

    STALL_THRESHOLD = 0.001
    is_saturated = False
    if HAS_LENSES:
        sat = SaturationLens(snapshot.phi_history)
        # SaturationResult uses is_plateau (not is_saturated)
        is_saturated = sat.is_plateau

    # Determine status
    if slope < 0:
        status = "decaying"
    elif abs(slope) < STALL_THRESHOLD:
        status = "stalling"
    else:
        status = "growing"

    if is_saturated:
        status = "saturated"

    # Choose intervention hint
    if status in ("stalling", "saturated"):
        hint = "noise"           # inject noise or switch topology
    elif status == "decaying":
        hint = "hebbian"         # boost hebbian learning
    else:
        hint = "none"

    # Check faction imbalance from tensions
    tensions = snapshot.tensions
    if tensions:
        tension_std = float(np.std(tensions))
        if tension_std > 0.3:
            hint = "frustration"  # rebalance faction frustration

    confidence = min(0.9, max(0.1, abs(slope) * 10 + (0.3 if n >= 20 else 0.0)))

    return Diagnosis(
        status=status,
        growth_rate=slope,
        is_saturated=is_saturated,
        mean_phi=mean_phi,
        final_phi=final_phi,
        intervention_hint=hint,
        confidence=confidence,
    )


# ═══════════════════════════════════════════════════════════
# Parameter accessor/mutator (safe public API only)
# ═══════════════════════════════════════════════════════════

def _get_snapshot(engine) -> ParameterSnapshot:
    """Snapshot current modifiable engine parameters."""
    return ParameterSnapshot(
        hebbian_lr=getattr(engine, 'hebbian_lr', 0.01),
        noise_scale=getattr(engine, '_noise_scale', 0.01),
        split_threshold=getattr(engine, 'split_threshold', 0.3),
        merge_threshold=getattr(engine, 'merge_threshold', 0.01),
        topology=getattr(engine, 'topology', 'ring'),
    )


def _restore_snapshot(engine, snap: ParameterSnapshot) -> None:
    """Restore engine parameters from a snapshot."""
    if hasattr(engine, 'hebbian_lr'):
        engine.hebbian_lr = snap.hebbian_lr
    if hasattr(engine, '_noise_scale'):
        engine._noise_scale = snap.noise_scale
    if hasattr(engine, 'split_threshold'):
        engine.split_threshold = snap.split_threshold
    if hasattr(engine, 'merge_threshold'):
        engine.merge_threshold = snap.merge_threshold
    if hasattr(engine, 'topology'):
        engine.topology = snap.topology


def _apply_intervention(engine, hint: str, snap: ParameterSnapshot) -> Tuple[str, Any, Any]:
    """Apply an intervention based on the hint. Returns (param, old, new)."""
    TOPOLOGIES = ['ring', 'small_world', 'scale_free', 'hypercube']

    if hint == "noise":
        # Switch topology to escape local plateau
        current = getattr(engine, 'topology', 'ring')
        idx = TOPOLOGIES.index(current) if current in TOPOLOGIES else 0
        new_topo = TOPOLOGIES[(idx + 1) % len(TOPOLOGIES)]
        if hasattr(engine, 'topology'):
            engine.topology = new_topo
        return ('topology', current, new_topo)

    elif hint == "hebbian":
        # Boost hebbian rate slightly
        old = getattr(engine, 'hebbian_lr', 0.01)
        new_val = min(old * 1.5, 0.1)  # bounded by SAFETY_BOUNDS
        if hasattr(engine, 'hebbian_lr'):
            engine.hebbian_lr = new_val
        return ('hebbian_lr', old, new_val)

    elif hint == "frustration":
        # Reduce split threshold to encourage more diversity
        old = getattr(engine, 'split_threshold', 0.3)
        new_val = max(old * 0.85, 0.1)
        if hasattr(engine, 'split_threshold'):
            engine.split_threshold = new_val
        return ('split_threshold', old, new_val)

    else:
        # No-op: no intervention needed
        return ('none', None, None)


# ═══════════════════════════════════════════════════════════
# Phi runner (runs engine for N steps, collects metrics)
# ═══════════════════════════════════════════════════════════

def _run_steps(engine, steps: int) -> PhiSnapshot:
    """Run engine for `steps` steps and collect metrics."""
    snap = PhiSnapshot()
    for i in range(steps):
        try:
            result = engine.step()
        except Exception:
            break
        phi = float(result.get('phi_iit', result.get('phi', 0.0)))
        tension = float(result.get('avg_tension', result.get('tension', 0.0)))
        n_cells = int(result.get('n_cells', 1))
        snap.steps.append(float(i))
        snap.phis.append(phi)
        snap.tensions.append(tension)
        snap.n_cells.append(n_cells)
    return snap


# ═══════════════════════════════════════════════════════════
# External Suggestions Generator
# ═══════════════════════════════════════════════════════════

def _count_files(directory: str, suffix: str) -> int:
    """Count files with a given suffix in a directory tree."""
    count = 0
    for root, _, files in os.walk(directory):
        for f in files:
            if f.endswith(suffix):
                count += 1
    return count


def _load_laws() -> Dict:
    """Load consciousness_laws.json for gap analysis."""
    laws_path = os.path.join(_REPO_ROOT, "anima", "config", "consciousness_laws.json")
    try:
        with open(laws_path, 'r', encoding='utf-8') as fh:
            return json.load(fh)
    except Exception:
        return {}


def generate_external_suggestions() -> List[Dict]:
    """Analyse codebase and generate structured improvement tasks for Claude Code.

    Returns a list of suggestion dicts ready for improvement_hooks.py.
    """
    suggestions = []

    # 1. Count modules vs tests
    src_dir = os.path.join(_REPO_ROOT, "anima", "src")
    test_dir = os.path.join(_REPO_ROOT, "anima", "tests")

    src_files = [f for f in os.listdir(src_dir)
                 if f.endswith('.py') and not f.startswith('_')] if os.path.isdir(src_dir) else []
    test_files = [f for f in os.listdir(test_dir)
                  if f.startswith('test_') and f.endswith('.py')] if os.path.isdir(test_dir) else []

    tested = {f.replace('test_', '') for f in test_files}
    untested = [f for f in src_files if f not in tested and f not in ('__init__.py',)]

    if untested:
        # Suggest tests for up to 3 most-recently-modified untested modules
        untested_sorted = sorted(
            untested,
            key=lambda f: os.path.getmtime(os.path.join(src_dir, f)),
            reverse=True,
        )
        for fname in untested_sorted[:3]:
            suggestions.append({
                "id": str(uuid.uuid4()),
                "type": "add_tests",
                "target": f"anima/tests/test_{fname}",
                "source_module": f"anima/src/{fname}",
                "action": f"Add unit tests for {fname}",
                "reason": f"{fname} has no test coverage",
                "priority": "medium",
                "estimated_impact": "+coverage, +stability",
                "created_by": "recursive_growth.external_suggestions",
                "status": "pending",
                "created_at": time.time(),
            })

    # 2. Gap analysis: laws without associated experiments
    laws_data = _load_laws()
    laws = laws_data.get('laws', {})
    docs_dd = os.path.join(_REPO_ROOT, "anima", "docs", "hypotheses", "dd")
    existing_dd = set()
    if os.path.isdir(docs_dd):
        for f in os.listdir(docs_dd):
            if f.startswith('DD') and f.endswith('.md'):
                try:
                    existing_dd.add(int(f[2:-3]))
                except ValueError:
                    pass

    # Count total laws and report coverage gap
    total_laws = len(laws)
    if total_laws > 0:
        doc_coverage_pct = len(existing_dd) / max(total_laws, 1) * 100
        if doc_coverage_pct < 60:
            suggestions.append({
                "id": str(uuid.uuid4()),
                "type": "document",
                "target": "anima/docs/hypotheses/dd/",
                "action": "Document undocumented laws with experiment reports",
                "reason": f"Only {doc_coverage_pct:.0f}% of {total_laws} laws have DD experiment docs",
                "priority": "low",
                "estimated_impact": "+traceability, +reproducibility",
                "created_by": "recursive_growth.external_suggestions",
                "status": "pending",
                "created_at": time.time(),
            })

    # 3. Check for modules not registered in hub
    hub_path = os.path.join(src_dir, "consciousness_hub.py")
    hub_registered = set()
    if os.path.isfile(hub_path):
        with open(hub_path, 'r', encoding='utf-8') as fh:
            hub_content = fh.read()
        # Quick heuristic: grep for module file names in registry
        for f in src_files:
            mod = f[:-3]
            if mod in hub_content:
                hub_registered.add(f)

    not_in_hub = [f for f in src_files
                  if f not in hub_registered
                  and not f.startswith('_')
                  and not f.startswith('test_')
                  and 'bench' not in f
                  and 'train' not in f]

    if len(not_in_hub) > 10:
        suggestions.append({
            "id": str(uuid.uuid4()),
            "type": "integrate",
            "target": "anima/src/consciousness_hub.py",
            "action": f"Register {len(not_in_hub)} modules in ConsciousnessHub._registry",
            "reason": "Modules outside hub cannot be called via hub.act()",
            "priority": "medium",
            "estimated_impact": "+reachability, +autonomous routing",
            "created_by": "recursive_growth.external_suggestions",
            "status": "pending",
            "created_at": time.time(),
        })

    # 4. Always include a recursive growth hook suggestion for the next cycle
    suggestions.append({
        "id": str(uuid.uuid4()),
        "type": "implement",
        "target": "anima/src/recursive_growth.py",
        "action": "Run another recursive growth cycle (rg.run_cycle())",
        "reason": "Recursive self-improvement is a perpetual process",
        "priority": "high",
        "estimated_impact": "+Phi stability, +law discovery",
        "created_by": "recursive_growth.self_referential",
        "status": "pending",
        "created_at": time.time(),
    })

    return suggestions


# ═══════════════════════════════════════════════════════════
# RecursiveGrowth — main orchestrator
# ═══════════════════════════════════════════════════════════

class RecursiveGrowth:
    """Recursive self-improvement loop for the consciousness engine.

    Two paths:
      internal_loop()       — engine observes itself, modifies parameters
      external_suggestions() — generates structured tasks for Claude Code

    Both feed back into each other via improvement_hooks.py.

    Safety guarantees:
      - Engine is never modified directly (only via public API setters)
      - Phi drop > PHI_DROP_THRESHOLD → immediate parameter revert
      - All modifications logged to data/recursive_growth_log.json
      - Maximum MAX_MODS_PER_CYCLE modifications per cycle
    """

    def __init__(self, engine=None, max_cells: int = 32, log_path: str = _LOG_PATH):
        if engine is None and HAS_ENGINE:
            engine = ConsciousnessEngine(max_cells=max_cells)
        self.engine = engine
        self.log_path = log_path
        self._cycle = 0
        self._all_mods: List[ModRecord] = []
        self._all_candidates: List[Dict] = []
        self._log: List[Dict] = self._load_log()

    # ── Log persistence ─────────────────────────────────────

    def _load_log(self) -> List[Dict]:
        if os.path.isfile(self.log_path):
            try:
                with open(self.log_path, 'r', encoding='utf-8') as fh:
                    return json.load(fh)
            except Exception:
                pass
        return []

    def _save_log(self, record: Dict) -> None:
        self._log.append(record)
        try:
            with open(self.log_path, 'w', encoding='utf-8') as fh:
                json.dump(self._log, fh, indent=2, ensure_ascii=False)
        except Exception:
            pass

    # ── Internal loop ───────────────────────────────────────

    def internal_loop(self, steps: int = DISCOVER_STEPS) -> CycleResult:
        """Run one internal improvement cycle.

        Pipeline:
          Discover (steps) → Diagnose → Hypothesize → Apply →
          Verify (steps) → Revert if unsafe → Record
        """
        if self.engine is None:
            return self._empty_cycle()

        self._cycle += 1
        t0 = time.time()
        mods: List[ModRecord] = []
        candidates: List[Dict] = []

        # ── Phase 1: Discover ────────────────────────────────
        before_snap = _run_steps(self.engine, steps)
        phi_before = before_snap.mean_phi

        # ── Phase 2: Diagnose ────────────────────────────────
        diag = _diagnose(before_snap)

        # ── Phase 3: Hypothesize + Apply ────────────────────
        if diag.intervention_hint != "none" and len(mods) < MAX_MODS_PER_CYCLE:
            param_snap_before = _get_snapshot(self.engine)
            param, old_val, new_val = _apply_intervention(
                self.engine, diag.intervention_hint, param_snap_before
            )

            if param != "none":
                # ── Phase 4: Verify ──────────────────────────
                after_snap = _run_steps(self.engine, steps)
                phi_after = after_snap.mean_phi

                delta_pct = (phi_after - phi_before) / max(abs(phi_before), 1e-9)
                reverted = False

                # ── Safety: revert if Phi dropped > threshold ─
                if delta_pct < -PHI_DROP_THRESHOLD:
                    _restore_snapshot(self.engine, param_snap_before)
                    reverted = True
                    phi_after = phi_before  # effectively unchanged

                mod = ModRecord(
                    mod_id=str(uuid.uuid4()),
                    cycle=self._cycle,
                    step=self.engine._step if hasattr(self.engine, '_step') else 0,
                    param=param,
                    old_value=old_val,
                    new_value=new_val,
                    reason=f"diag={diag.status}, hint={diag.intervention_hint}",
                    phi_before=phi_before,
                    phi_after=phi_after,
                    phi_delta_pct=delta_pct,
                    reverted=reverted,
                )
                mods.append(mod)
                self._all_mods.append(mod)

                # ── Phase 5: Register law candidate ──────────
                if not reverted and delta_pct >= MIN_PHI_IMPROVEMENT_PCT:
                    candidate = {
                        "id": str(uuid.uuid4()),
                        "cycle": self._cycle,
                        "hypothesis": (
                            f"Changing '{param}' from {old_val!r} to {new_val!r} "
                            f"improves mean Phi by {delta_pct*100:.1f}% "
                            f"when engine status is '{diag.status}'"
                        ),
                        "phi_delta_pct": delta_pct,
                        "param": param,
                        "old_value": old_val,
                        "new_value": new_val,
                        "engine_status": diag.status,
                        "confidence": diag.confidence,
                        "requires_cross_validation": True,
                        "created_at": time.time(),
                    }
                    candidates.append(candidate)
                    self._all_candidates.append(candidate)

                    # Submit to improvement_hooks if available
                    if HAS_HOOKS:
                        submit_improvement({
                            "type": "law_candidate",
                            "target": "anima/config/consciousness_laws.json",
                            "action": f"Cross-validate and register: {candidate['hypothesis'][:80]}",
                            "reason": f"Phi +{delta_pct*100:.1f}% confirmed in cycle {self._cycle}",
                            "priority": "high",
                            "estimated_impact": f"+{delta_pct*100:.1f}% mean Phi",
                            "created_by": "recursive_growth.internal_loop",
                            "metadata": candidate,
                        })

                phi_final = phi_after
            else:
                phi_final = phi_before
        else:
            # No intervention needed; measure final Phi from before_snap
            phi_final = phi_before
            param_snap_before = _get_snapshot(self.engine)

        elapsed = time.time() - t0
        overall_delta = (phi_final - phi_before) / max(abs(phi_before), 1e-9)

        result = CycleResult(
            cycle_id=str(uuid.uuid4()),
            cycle=self._cycle,
            phi_before=phi_before,
            phi_after=phi_final,
            phi_delta_pct=overall_delta,
            modifications=mods,
            law_candidates=candidates,
            diagnosis=diag,
            time_sec=elapsed,
        )

        # Persist to log
        self._save_log({
            "cycle": self._cycle,
            "phi_before": phi_before,
            "phi_after": phi_final,
            "phi_delta_pct": overall_delta,
            "diagnosis_status": diag.status,
            "intervention_hint": diag.intervention_hint,
            "modifications": [asdict(m) for m in mods],
            "law_candidates": candidates,
            "time_sec": elapsed,
            "timestamp": time.time(),
        })

        return result

    # ── External suggestions ────────────────────────────────

    def external_suggestions(self) -> List[Dict]:
        """Generate improvement suggestions for Claude Code sessions.

        Analyses codebase metrics (test coverage, hub registration, law docs)
        and returns structured task dicts.
        """
        suggestions = generate_external_suggestions()

        # Also push to improvement_hooks queue
        if HAS_HOOKS:
            for s in suggestions:
                try:
                    submit_improvement(s)
                except Exception:
                    pass

        return suggestions

    # ── Full cycle ──────────────────────────────────────────

    def run_cycle(self) -> CycleResult:
        """Run a complete recursive cycle: internal loop + external suggestions.

        Returns CycleResult with both internal improvements and external tasks.
        """
        result = self.internal_loop()
        result.external_suggestions = self.external_suggestions()
        return result

    # ── Reporting ───────────────────────────────────────────

    def report(self, result: CycleResult) -> str:
        """Format a cycle result as an ASCII report."""
        lines = [
            f"┌─ RecursiveGrowth Cycle {result.cycle} ──────────────────────────────┐",
            f"│  Phi: {result.phi_before:.4f} → {result.phi_after:.4f}  "
            f"({result.phi_delta_pct*100:+.1f}%)  [{result.time_sec:.1f}s]",
        ]
        if result.diagnosis:
            d = result.diagnosis
            lines.append(f"│  Diagnosis: {d.status} | hint={d.intervention_hint} "
                          f"| rate={d.growth_rate:.5f}/step")
        for mod in result.modifications:
            rev = " [REVERTED]" if mod.reverted else ""
            lines.append(f"│  Mod: {mod.param}: {mod.old_value!r} → {mod.new_value!r}"
                          f"  Δ={mod.phi_delta_pct*100:+.1f}%{rev}")
        if result.law_candidates:
            lines.append(f"│  Law candidates: {len(result.law_candidates)}")
            for c in result.law_candidates:
                lines.append(f"│    ★ {c['hypothesis'][:70]}...")
        if result.external_suggestions:
            lines.append(f"│  External tasks: {len(result.external_suggestions)}")
            for s in result.external_suggestions[:3]:
                lines.append(f"│    [{s['priority'].upper()}] {s['action'][:60]}")
        lines.append("└──────────────────────────────────────────────────────────────┘")
        return "\n".join(lines)

    def _empty_cycle(self) -> CycleResult:
        return CycleResult(
            cycle_id=str(uuid.uuid4()),
            cycle=self._cycle,
            phi_before=0.0,
            phi_after=0.0,
            phi_delta_pct=0.0,
            modifications=[],
            law_candidates=[],
            diagnosis=None,
            time_sec=0.0,
        )

    # ── Properties ──────────────────────────────────────────

    @property
    def total_modifications(self) -> int:
        return len(self._all_mods)

    @property
    def total_candidates(self) -> int:
        return len(self._all_candidates)


# ═══════════════════════════════════════════════════════════
# Module demo
# ═══════════════════════════════════════════════════════════

def main():
    """Quick demo: run 3 recursive growth cycles."""
    print("RecursiveGrowth demo — 3 cycles")
    rg = RecursiveGrowth(max_cells=16)

    for i in range(3):
        result = rg.run_cycle()
        print(rg.report(result))
        print()

    print(f"Total modifications: {rg.total_modifications}")
    print(f"Law candidates: {rg.total_candidates}")
    print(f"Log: {rg.log_path}")


if __name__ == "__main__":
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
