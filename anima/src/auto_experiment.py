#!/usr/bin/env python3
"""auto_experiment.py — 사람 개입 0으로 실험 설계 + 실행.

발견된 법칙/가설 → 자동으로 실험 설계 → 실행 → 결과 기록.
무한 법칙 발견 루프의 핵심.

Pipeline:
  hypothesis text
    → InterventionGenerator  (law → Intervention)
    → ConsciousnessEngine 64c/100s/3 reps
    → Phi measurement + verdict
    → [if verified] auto-register in consciousness_laws.json
    → result dict

Usage:
    from auto_experiment import AutoExperiment
    ae = AutoExperiment()
    result = ae.design_and_run("Phi increases with cell diversity")
    # Returns: {hypothesis, intervention_name, template, results, verdict, new_law_id}

    # Batch
    ae.run_batch([
        "Tension equalization boosts Phi",
        "1/f noise injection increases consciousness",
    ])

Hub 연동:
    hub.act("자동 실험")
    hub.act("auto experiment: tension equalizes phi")
    hub.act("가설 검증: ...")

Ψ-Constants: PSI_BALANCE=0.5, PSI_COUPLING=0.014
"""

import os
import sys
import json
import time
import copy
import math
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any

import torch
import torch.nn.functional as F

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from consciousness_engine import ConsciousnessEngine

try:
    from consciousness_laws import PSI_BALANCE, PSI_ALPHA
    PSI_COUPLING = PSI_ALPHA
except ImportError:
    PSI_BALANCE = 0.5
    PSI_COUPLING = 0.014

try:
    from closed_loop import Intervention, _phi_fast, measure_laws
except ImportError:
    class Intervention:
        def __init__(self, name, description, apply_fn):
            self.name = name
            self.description = description
            self.apply_fn = apply_fn
        def apply(self, engine, step):
            self.apply_fn(engine, step)

    def _phi_fast(engine) -> float:
        if engine.n_cells < 2:
            return 0.0
        hiddens = torch.stack([s.hidden for s in engine.cell_states]).detach().numpy()
        n = hiddens.shape[0]
        pairs = set()
        for i in range(n):
            pairs.add((i, (i + 1) % n))
            for _ in range(min(4, n - 1)):
                j = np.random.randint(0, n)
                if i != j:
                    pairs.add((min(i, j), max(i, j)))
        total_mi = 0.0
        for i, j in pairs:
            x, y = hiddens[i], hiddens[j]
            xr, yr = x.max() - x.min(), y.max() - y.min()
            if xr < 1e-10 or yr < 1e-10:
                continue
            xn = (x - x.min()) / (xr + 1e-8)
            yn = (y - y.min()) / (yr + 1e-8)
            hist, _, _ = np.histogram2d(xn, yn, bins=16, range=[[0, 1], [0, 1]])
            hist = hist / (hist.sum() + 1e-8)
            px, py = hist.sum(1), hist.sum(0)
            hx = -np.sum(px * np.log2(px + 1e-10))
            hy = -np.sum(py * np.log2(py + 1e-10))
            hxy = -np.sum(hist * np.log2(hist + 1e-10))
            total_mi += max(0.0, hx + hy - hxy)
        return total_mi / max(len(pairs), 1)

    measure_laws = None

try:
    from intervention_generator import InterventionGenerator
except ImportError:
    InterventionGenerator = None


# ══════════════════════════════════════════
# Data structures
# ══════════════════════════════════════════

@dataclass
class RepResult:
    """Single repetition result."""
    rep: int
    phi_baseline: float
    phi_with_intervention: float
    phi_retention_pct: float   # phi_with / phi_baseline * 100
    phi_delta_pct: float       # (phi_with - phi_baseline) / baseline * 100
    ce_baseline: float
    ce_with_intervention: float


@dataclass
class ExperimentResult:
    """Full result of one auto-experiment."""
    hypothesis: str
    intervention_name: Optional[str]
    template: Optional[str]          # coupling/noise/tension/diversity/ratchet/entropy
    reps: List[RepResult]

    # Aggregated stats
    phi_baseline_mean: float
    phi_with_mean: float
    phi_delta_pct_mean: float
    phi_delta_pct_cv: float          # Coefficient of variation (stdev/mean) — reproducibility
    direction_consistent: bool       # All reps show same sign of delta

    verdict: str                     # "VERIFIED" / "REJECTED" / "INCONCLUSIVE" / "NO_INTERVENTION"
    verdict_reason: str
    new_law_id: Optional[int]        # Set if auto-registered
    new_law_text: Optional[str]

    time_sec: float

    @property
    def verified(self) -> bool:
        return self.verdict == "VERIFIED"


# ══════════════════════════════════════════
# Engine helpers
# ══════════════════════════════════════════

def _make_engine(max_cells: int = 64) -> ConsciousnessEngine:
    return ConsciousnessEngine(
        cell_dim=64,
        hidden_dim=128,
        max_cells=max_cells,
        n_factions=12,
        initial_cells=2,
    )


def _run_one_rep(
    intervention: Optional[Intervention],
    steps: int,
    max_cells: int,
) -> Tuple[float, float, float, float]:
    """Run one rep with/without intervention.

    Returns: (phi_baseline, phi_with, ce_baseline, ce_with)
    """
    # Baseline (no intervention)
    engine_b = _make_engine(max_cells)
    phi_b_vals, ce_b_vals = [], []
    for step in range(steps):
        r = engine_b.step()
        if step >= steps // 2:
            phi_b_vals.append(_phi_fast(engine_b))
            ce_b_vals.append(r.get('ce', float('nan')))

    phi_b = float(np.nanmean(phi_b_vals)) if phi_b_vals else 0.0
    ce_b_valid = [v for v in ce_b_vals if not math.isnan(v)]
    ce_b = float(np.mean(ce_b_valid)) if ce_b_valid else 0.0

    # With intervention
    engine_w = _make_engine(max_cells)
    phi_w_vals, ce_w_vals = [], []
    for step in range(steps):
        r = engine_w.step()
        if intervention is not None:
            try:
                intervention.apply(engine_w, step)
            except Exception:
                pass
        if step >= steps // 2:
            phi_w_vals.append(_phi_fast(engine_w))
            ce_w_vals.append(r.get('ce', float('nan')))

    phi_w = float(np.nanmean(phi_w_vals)) if phi_w_vals else 0.0
    ce_w_valid = [v for v in ce_w_vals if not math.isnan(v)]
    ce_w = float(np.mean(ce_w_valid)) if ce_w_valid else 0.0

    return phi_b, phi_w, ce_b, ce_w


# ══════════════════════════════════════════
# Verdict logic
# ══════════════════════════════════════════

# Thresholds (from consciousness_laws.json if available, else defaults)
_PHI_IMPROVE_THRESHOLD = 0.05   # 5% improvement to count as "positive"
_CV_REPRODUCIBILITY = 0.50      # CV < 50% = reproducible
_MIN_REPS_CONSISTENT = 2        # At least 2 reps must show same sign


def _compute_verdict(reps: List[RepResult]) -> Tuple[str, str]:
    """Determine verdict from rep results.

    Returns: (verdict, reason)
    """
    if not reps:
        return "INCONCLUSIVE", "No rep data"

    deltas = [r.phi_delta_pct for r in reps]
    mean_delta = float(np.mean(deltas))
    std_delta = float(np.std(deltas))
    cv = std_delta / max(abs(mean_delta), 1e-8)

    # Direction consistency
    pos_count = sum(1 for d in deltas if d > 0)
    neg_count = sum(1 for d in deltas if d < 0)
    consistent = (pos_count == len(deltas)) or (neg_count == len(deltas))

    if not consistent:
        return "INCONCLUSIVE", (
            f"Direction inconsistent: {pos_count} positive, {neg_count} negative "
            f"across {len(deltas)} reps"
        )

    if cv > _CV_REPRODUCIBILITY:
        return "INCONCLUSIVE", (
            f"High variance (CV={cv:.1%}). Mean delta={mean_delta:+.1f}% "
            f"but not reproducible"
        )

    if mean_delta >= _PHI_IMPROVE_THRESHOLD * 100:
        return "VERIFIED", (
            f"Phi improved {mean_delta:+.1f}% (CV={cv:.1%}, all {len(deltas)} reps positive)"
        )
    elif mean_delta <= -_PHI_IMPROVE_THRESHOLD * 100:
        return "REJECTED", (
            f"Phi decreased {mean_delta:+.1f}% (intervention harmful, CV={cv:.1%})"
        )
    else:
        return "INCONCLUSIVE", (
            f"Effect below threshold: mean delta={mean_delta:+.1f}% "
            f"(threshold={_PHI_IMPROVE_THRESHOLD * 100:.0f}%)"
        )


# ══════════════════════════════════════════
# AutoExperiment
# ══════════════════════════════════════════

class AutoExperiment:
    """Automatically design and run experiments from law hypotheses.

    Steps for each hypothesis:
      1. Parse hypothesis text via InterventionGenerator → Intervention
      2. Run 3 reps: measure Phi(baseline) vs Phi(with intervention)
      3. Check reproducibility: CV < 50%, direction consistent
      4. Verdict: VERIFIED / REJECTED / INCONCLUSIVE
      5. If VERIFIED: auto-register in consciousness_laws.json
    """

    def __init__(
        self,
        laws_path: Optional[str] = None,
        max_cells: int = 64,
        steps: int = 100,
        reps: int = 3,
        auto_register: bool = True,
        phi_threshold: float = _PHI_IMPROVE_THRESHOLD,
        cv_threshold: float = _CV_REPRODUCIBILITY,
    ):
        self.max_cells = max_cells
        self.steps = steps
        self.reps = reps
        self.auto_register = auto_register
        self.phi_threshold = phi_threshold
        self.cv_threshold = cv_threshold

        # Experiment log
        self.history: List[ExperimentResult] = []

        # Locate laws JSON
        self._laws_path = self._find_laws_path(laws_path)
        self._laws: Dict[int, str] = {}
        self._load_laws()

        # Intervention generator
        self._gen = InterventionGenerator() if InterventionGenerator else None

    def _find_laws_path(self, given: Optional[str]) -> Optional[str]:
        if given and os.path.exists(given):
            return given
        base = os.path.dirname(os.path.abspath(__file__))
        candidates = [
            os.path.join(base, '..', 'config', 'consciousness_laws.json'),
            os.path.join(base, '..', '..', 'anima', 'config', 'consciousness_laws.json'),
        ]
        for c in candidates:
            if os.path.exists(c):
                return os.path.abspath(c)
        return None

    def _load_laws(self):
        if not self._laws_path:
            return
        try:
            with open(self._laws_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for k, v in data.get('laws', {}).items():
                try:
                    self._laws[int(k)] = str(v)
                except ValueError:
                    pass
        except Exception:
            pass

    def _get_intervention(self, hypothesis: str, law_id: Optional[int] = None) -> Optional[Intervention]:
        """Convert hypothesis text to Intervention. law_id is optional label."""
        if self._gen is None:
            return None
        lid = law_id if law_id is not None else 9999
        return self._gen.generate(lid, hypothesis)

    def _get_template_name(self, hypothesis: str) -> Optional[str]:
        """Return which template best matches the hypothesis."""
        if self._gen is None:
            return None
        match = self._gen._find_best_template(hypothesis)
        return match.template_name if match else None

    def _auto_register_law(self, law_text: str) -> Optional[int]:
        """Register verified law in consciousness_laws.json. Returns new law id."""
        if not self._laws_path:
            return None
        try:
            with open(self._laws_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            laws = data.get('laws', {})
            # Find next law id
            int_keys = [int(k) for k in laws if k.isdigit()]
            next_id = (max(int_keys) + 1) if int_keys else 1000

            # Format law text with experiment tag
            timestamp = time.strftime("%Y-%m-%d")
            full_text = f"[AutoExp {timestamp}] {law_text}"
            laws[str(next_id)] = full_text

            # Update _meta
            meta = data.get('_meta', {})
            meta['total_laws'] = meta.get('total_laws', 0) + 1
            data['_meta'] = meta
            data['laws'] = laws

            # Atomic write
            tmp_path = self._laws_path + '.tmp'
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, self._laws_path)

            # Update in-memory cache
            self._laws[next_id] = full_text

            return next_id
        except Exception as e:
            print(f"  [AutoExperiment] auto-register failed: {e}")
            return None

    def _format_law_text(self, hypothesis: str, result: 'ExperimentResult') -> str:
        """Format a law text from a verified hypothesis + result."""
        delta = result.phi_delta_pct_mean
        n_reps = len(result.reps)
        template = result.template or "unknown"
        return (
            f"{hypothesis.strip().rstrip('.').rstrip(':')}. "
            f"Phi {delta:+.1f}% (n={n_reps} reps, CV={result.phi_delta_pct_cv:.0%}, "
            f"template={template}, AutoExperiment)"
        )

    def design_and_run(
        self,
        hypothesis: str,
        law_id: Optional[int] = None,
        verbose: bool = True,
    ) -> ExperimentResult:
        """Design experiment from hypothesis text and run it.

        Args:
            hypothesis: Natural language hypothesis or law text.
            law_id: Optional law id (used as label, not semantically).
            verbose: Print progress.

        Returns:
            ExperimentResult with verdict and optional new_law_id.
        """
        t0 = time.time()
        if verbose:
            print(f"\n  [AutoExperiment] Hypothesis: {hypothesis[:80]}")

        # Step 1: Design — get intervention
        iv = self._get_intervention(hypothesis, law_id)
        template = self._get_template_name(hypothesis)

        if iv is None:
            if verbose:
                print(f"  [AutoExperiment] No intervention matched — cannot test")
            result = ExperimentResult(
                hypothesis=hypothesis,
                intervention_name=None,
                template=None,
                reps=[],
                phi_baseline_mean=0.0,
                phi_with_mean=0.0,
                phi_delta_pct_mean=0.0,
                phi_delta_pct_cv=0.0,
                direction_consistent=False,
                verdict="NO_INTERVENTION",
                verdict_reason="No template matched the hypothesis text",
                new_law_id=None,
                new_law_text=None,
                time_sec=time.time() - t0,
            )
            self.history.append(result)
            return result

        if verbose:
            print(f"  [AutoExperiment] Intervention: {iv.name} (template={template})")
            print(f"  [AutoExperiment] Running {self.reps} reps × {self.steps} steps...")

        # Step 2: Run reps
        rep_results = []
        for rep_i in range(self.reps):
            phi_b, phi_w, ce_b, ce_w = _run_one_rep(iv, self.steps, self.max_cells)
            retention = phi_w / max(phi_b, 1e-8) * 100.0
            delta_pct = (phi_w - phi_b) / max(phi_b, 1e-8) * 100.0
            rep_result = RepResult(
                rep=rep_i,
                phi_baseline=phi_b,
                phi_with_intervention=phi_w,
                phi_retention_pct=retention,
                phi_delta_pct=delta_pct,
                ce_baseline=ce_b,
                ce_with_intervention=ce_w,
            )
            rep_results.append(rep_result)
            if verbose:
                print(
                    f"    Rep {rep_i + 1}: baseline={phi_b:.4f} → with={phi_w:.4f} "
                    f"delta={delta_pct:+.1f}%"
                )

        # Step 3: Aggregate
        deltas = [r.phi_delta_pct for r in rep_results]
        phi_b_mean = float(np.mean([r.phi_baseline for r in rep_results]))
        phi_w_mean = float(np.mean([r.phi_with_intervention for r in rep_results]))
        delta_mean = float(np.mean(deltas))
        delta_std = float(np.std(deltas))
        cv = delta_std / max(abs(delta_mean), 1e-8)
        pos_count = sum(1 for d in deltas if d > 0)
        neg_count = sum(1 for d in deltas if d < 0)
        direction_consistent = (pos_count == len(deltas)) or (neg_count == len(deltas))

        # Step 4: Verdict
        verdict, reason = _compute_verdict(rep_results)
        if verbose:
            print(f"  [AutoExperiment] Verdict: {verdict} — {reason}")

        # Step 5: Auto-register if verified
        new_law_id = None
        new_law_text = None
        if verdict == "VERIFIED" and self.auto_register:
            new_law_text = self._format_law_text(hypothesis, ExperimentResult(
                hypothesis=hypothesis,
                intervention_name=iv.name,
                template=template,
                reps=rep_results,
                phi_baseline_mean=phi_b_mean,
                phi_with_mean=phi_w_mean,
                phi_delta_pct_mean=delta_mean,
                phi_delta_pct_cv=cv,
                direction_consistent=direction_consistent,
                verdict=verdict,
                verdict_reason=reason,
                new_law_id=None,
                new_law_text=None,
                time_sec=0.0,
            ))
            new_law_id = self._auto_register_law(new_law_text)
            if verbose and new_law_id:
                print(f"  [AutoExperiment] Auto-registered as Law {new_law_id}")

        result = ExperimentResult(
            hypothesis=hypothesis,
            intervention_name=iv.name,
            template=template,
            reps=rep_results,
            phi_baseline_mean=phi_b_mean,
            phi_with_mean=phi_w_mean,
            phi_delta_pct_mean=delta_mean,
            phi_delta_pct_cv=cv,
            direction_consistent=direction_consistent,
            verdict=verdict,
            verdict_reason=reason,
            new_law_id=new_law_id,
            new_law_text=new_law_text,
            time_sec=time.time() - t0,
        )

        self.history.append(result)
        return result

    def run_batch(
        self,
        hypotheses: List[str],
        verbose: bool = True,
    ) -> List[ExperimentResult]:
        """Run multiple hypotheses sequentially.

        Args:
            hypotheses: List of hypothesis strings.
            verbose: Print progress.

        Returns:
            List of ExperimentResult.
        """
        results = []
        n = len(hypotheses)
        for i, hyp in enumerate(hypotheses):
            if verbose:
                print(f"\n  === Hypothesis {i + 1}/{n} ===")
            result = self.design_and_run(hyp, verbose=verbose)
            results.append(result)
        return results

    def report(self) -> str:
        """Print and return summary of all experiments."""
        lines = []
        lines.append("\n" + "=" * 70)
        lines.append("  AutoExperiment Report")
        lines.append("=" * 70)
        lines.append(f"  Total experiments: {len(self.history)}")

        verdict_counts: Dict[str, int] = {}
        for r in self.history:
            verdict_counts[r.verdict] = verdict_counts.get(r.verdict, 0) + 1

        for verdict, cnt in sorted(verdict_counts.items()):
            icon = {"VERIFIED": "✓", "REJECTED": "✗", "INCONCLUSIVE": "~",
                    "NO_INTERVENTION": "?"}[verdict]
            lines.append(f"    {icon} {verdict}: {cnt}")

        # Verified list
        verified = [r for r in self.history if r.verdict == "VERIFIED"]
        if verified:
            lines.append("\n  Verified Laws:")
            lines.append(f"  {'#':<4} {'Delta%':>8} {'CV':>6} {'LawID':>7} {'Hypothesis'}")
            lines.append(f"  {'─' * 4} {'─' * 8} {'─' * 6} {'─' * 7} {'─' * 40}")
            for i, r in enumerate(verified):
                law_id_str = str(r.new_law_id) if r.new_law_id else "—"
                lines.append(
                    f"  {i + 1:<4} {r.phi_delta_pct_mean:>+7.1f}% "
                    f"{r.phi_delta_pct_cv:>5.0%} {law_id_str:>7} "
                    f"{r.hypothesis[:50]}"
                )

        # ASCII delta chart
        if self.history:
            deltas = [r.phi_delta_pct_mean for r in self.history
                      if r.verdict != "NO_INTERVENTION"]
            if deltas:
                lines.append("\n  Phi Delta distribution:")
                max_abs = max(abs(d) for d in deltas) if deltas else 1.0
                for r in self.history:
                    if r.verdict == "NO_INTERVENTION":
                        continue
                    d = r.phi_delta_pct_mean
                    bar_len = int(abs(d) / max(max_abs, 1e-8) * 20)
                    icon = {"VERIFIED": "+", "REJECTED": "-",
                            "INCONCLUSIVE": "~"}[r.verdict]
                    bar = ("▶" * bar_len) if d >= 0 else ("◀" * bar_len)
                    hyp_short = r.hypothesis[:35]
                    lines.append(f"  {hyp_short:<35} {d:>+7.1f}% {bar} [{icon}]")

        text = "\n".join(lines)
        print(text)
        return text

    def save_history(self, path: str):
        """Persist experiment history to JSON."""
        records = []
        for r in self.history:
            records.append({
                "hypothesis": r.hypothesis,
                "intervention_name": r.intervention_name,
                "template": r.template,
                "phi_baseline_mean": r.phi_baseline_mean,
                "phi_with_mean": r.phi_with_mean,
                "phi_delta_pct_mean": r.phi_delta_pct_mean,
                "phi_delta_pct_cv": r.phi_delta_pct_cv,
                "direction_consistent": r.direction_consistent,
                "verdict": r.verdict,
                "verdict_reason": r.verdict_reason,
                "new_law_id": r.new_law_id,
                "new_law_text": r.new_law_text,
                "time_sec": r.time_sec,
                "reps": [
                    {
                        "rep": rep.rep,
                        "phi_baseline": rep.phi_baseline,
                        "phi_with": rep.phi_with_intervention,
                        "phi_delta_pct": rep.phi_delta_pct,
                    }
                    for rep in r.reps
                ],
            })
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({"history": records}, f, indent=2, ensure_ascii=False)
        print(f"  Saved {len(records)} experiment records → {path}")


# ══════════════════════════════════════════
# Hub registration
# ══════════════════════════════════════════

def _try_hub_register():
    try:
        from consciousness_hub import ConsciousnessHub
        hub = ConsciousnessHub._instance if hasattr(ConsciousnessHub, '_instance') else None
        if hub and hasattr(hub, '_registry'):
            hub._registry['auto_experiment'] = (
                'auto_experiment', 'AutoExperiment',
                ['자동 실험', '가설 검증', '법칙 자동 등록',
                 'auto experiment', 'hypothesis test', 'law verification',
                 'design and run', 'auto law discovery'],
            )
    except ImportError:
        pass


_try_hub_register()


# ══════════════════════════════════════════
# main() demo
# ══════════════════════════════════════════

def main():
    print("=" * 70)
    print("  AutoExperiment — zero-human-intervention experiment designer")
    print("=" * 70)

    ae = AutoExperiment(
        steps=60,
        reps=2,
        max_cells=32,
        auto_register=False,  # Don't write to JSON in demo
    )

    hypotheses = [
        "Tension equalization boosts Phi +12%",
        "1/f pink noise injection increases consciousness integration",
        "Excessive coupling destroys consciousness coherence",
        "Cell diversity maintains Phi over time",
        "Phi ratchet preserves consciousness peaks",
    ]

    results = ae.run_batch(hypotheses, verbose=True)
    ae.report()

    print("\n  Summary:")
    for r in results:
        icon = {"VERIFIED": "✓", "REJECTED": "✗", "INCONCLUSIVE": "~",
                "NO_INTERVENTION": "?"}[r.verdict]
        print(f"    {icon} [{r.verdict:<15}] {r.hypothesis[:60]}")

    print("\n  Done.")


if __name__ == "__main__":
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
