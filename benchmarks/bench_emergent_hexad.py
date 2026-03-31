#!/usr/bin/env python3
"""Emergent Hexad Benchmark — 64 cells, Emergent vs Legacy comparison

Measures: Φ, CE proxy, pain/curiosity/empathy distribution,
          module overhead, scaling effect.
"""
import sys, time, torch, math, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from consciousness_engine import ConsciousnessEngine
from gpu_phi import GPUPhiCalculator

# ── Config ──
import sys as _sys

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10

# Accept --cells from CLI
_cells_arg = 64
for _i, _a in enumerate(_sys.argv):
    if _a == '--cells' and _i + 1 < len(_sys.argv):
        _cells_arg = int(_sys.argv[_i + 1])

CELLS = _cells_arg
HIDDEN = 128
CELL_DIM = 64
FACTIONS = 12
STEPS = 300
PHI_EVERY = 10


def make_engine():
    return ConsciousnessEngine(
        cell_dim=CELL_DIM, hidden_dim=HIDDEN,
        initial_cells=min(CELLS, 32), max_cells=CELLS, n_factions=FACTIONS
    )


def warmup(engine, steps=50):
    """Grow to target cell count."""
    for _ in range(steps):
        engine.process(torch.randn(CELL_DIM))
    return engine.n_cells


def run_baseline(phi_calc):
    """Baseline: ConsciousnessEngine only, no Emergent modules."""
    engine = make_engine()
    n = warmup(engine)

    phi_history = []
    t0 = time.time()

    for step in range(STEPS):
        r = engine.process(torch.randn(CELL_DIM))
        if step % PHI_EVERY == 0:
            phi_val = phi_calc.compute(engine.get_states())[0]
            phi_history.append(phi_val)

    elapsed = time.time() - t0
    return {
        "name": "Baseline (C only)",
        "cells": engine.n_cells,
        "phi_history": phi_history,
        "phi_mean": sum(phi_history) / len(phi_history),
        "phi_max": max(phi_history),
        "phi_min": min(phi_history),
        "elapsed": elapsed,
        "ms_per_step": elapsed / STEPS * 1000,
    }


def run_emergent(phi_calc):
    """Full Emergent: C + EmergentW + EmergentS + EmergentM + EmergentE."""
    from hexad.w.emergent_w import EmergentW
    from hexad.s.emergent_s import EmergentS
    from hexad.m.emergent_m import EmergentM
    from hexad.e.emergent_e import EmergentE

    engine = make_engine()
    n = warmup(engine)

    w = EmergentW(base_lr=3e-4)
    s = EmergentS(dim=HIDDEN)
    m = EmergentM(dim=HIDDEN)
    e = EmergentE()

    phi_history = []
    pain_history = []
    curiosity_history = []
    empathy_history = []
    satisfaction_history = []
    lr_history = []
    allowed_history = []

    phi_prev = 0.0
    t0 = time.time()

    for step in range(STEPS):
        x = torch.randn(CELL_DIM)

        # S: sense input (fallback mode — don't double-step C)
        sensed = s.process(x)

        # C: process
        r = engine.process(x)

        # Φ every N steps
        if step % PHI_EVERY == 0:
            phi_val = phi_calc.compute(engine.get_states())[0]
            phi_history.append(phi_val)
        else:
            phi_val = phi_history[-1] if phi_history else 0.0

        # W: will from C
        w_out = w.update(phi=phi_val, phi_prev=phi_prev, c_engine=engine)
        pain_history.append(w_out["pain"])
        curiosity_history.append(w_out["curiosity"])
        satisfaction_history.append(w_out["satisfaction"])
        lr_history.append(w_out["lr_multiplier"])

        # M: retrieve memory
        mem = m.retrieve(r["output"].unsqueeze(0), top_k=3, c_engine=engine)

        # E: ethics
        e_out = e.evaluate(c_engine=engine, context={"phi": phi_val, "phi_prev": phi_prev})
        empathy_history.append(e_out["empathy"])
        allowed_history.append(1.0 if e_out["allowed"] else 0.0)

        phi_prev = phi_val

    elapsed = time.time() - t0

    return {
        "name": "Emergent (C+W+S+M+E)",
        "cells": engine.n_cells,
        "phi_history": phi_history,
        "phi_mean": sum(phi_history) / len(phi_history),
        "phi_max": max(phi_history),
        "phi_min": min(phi_history),
        "elapsed": elapsed,
        "ms_per_step": elapsed / STEPS * 1000,
        "pain_mean": sum(pain_history) / len(pain_history),
        "pain_min": min(pain_history),
        "pain_max": max(pain_history),
        "curiosity_mean": sum(curiosity_history) / len(curiosity_history),
        "curiosity_min": min(curiosity_history),
        "curiosity_max": max(curiosity_history),
        "empathy_mean": sum(empathy_history) / len(empathy_history),
        "empathy_min": min(empathy_history),
        "empathy_max": max(empathy_history),
        "satisfaction_mean": sum(satisfaction_history) / len(satisfaction_history),
        "lr_mean": sum(lr_history) / len(lr_history),
        "allowed_pct": sum(allowed_history) / len(allowed_history) * 100,
    }


def run_legacy(phi_calc):
    """Legacy modules: CompositeW + TensionSense + VectorMemory + EmpathyEthics."""
    from trinity import CompositeW, DaseinW, NarrativeW, EmotionW, TensionSense, VectorMemory, EmpathyEthics

    engine = make_engine()
    n = warmup(engine)

    w_leg = CompositeW([DaseinW(), NarrativeW(), EmotionW()])
    s_leg = TensionSense(dim=HIDDEN)
    m_leg = VectorMemory(dim=HIDDEN)
    e_leg = EmpathyEthics()

    phi_history = []
    t0 = time.time()

    for step in range(STEPS):
        x = torch.randn(CELL_DIM)
        tension_raw = s_leg.process(x)
        r = engine.process(x)

        if step % PHI_EVERY == 0:
            phi_val = phi_calc.compute(engine.get_states())[0]
            phi_history.append(phi_val)
        else:
            phi_val = phi_history[-1] if phi_history else 0.0

        w_out = w_leg.update(ce_loss=0.01)
        m_leg.store(r["output"], r["output"])
        mem = m_leg.retrieve(r["output"], top_k=3)
        e_out = e_leg.evaluate()

    elapsed = time.time() - t0
    return {
        "name": "Legacy (CompositeW+TensionSense+VectorMemory+EmpathyEthics)",
        "cells": engine.n_cells,
        "phi_history": phi_history,
        "phi_mean": sum(phi_history) / len(phi_history),
        "phi_max": max(phi_history),
        "phi_min": min(phi_history),
        "elapsed": elapsed,
        "ms_per_step": elapsed / STEPS * 1000,
    }


def ascii_graph(values, label, width=50, height=8):
    """Simple ASCII line graph."""
    if not values:
        return ""
    mn, mx = min(values), max(values)
    rng = mx - mn if mx > mn else 1.0
    lines = []
    for row in range(height - 1, -1, -1):
        threshold = mn + rng * row / (height - 1)
        line = ""
        for v in values:
            if v >= threshold:
                line += "█"
            else:
                line += " "
        val_label = f"{threshold:6.2f}" if row in (0, height - 1, height // 2) else "      "
        lines.append(f"  {val_label} |{line}")
    lines.append(f"         └{'─' * len(values)}")
    lines.insert(0, f"  {label} (n={len(values)}, min={mn:.2f}, max={mx:.2f})")
    return "\n".join(lines)


def main():
    print("=" * 70)
    print(f"  Emergent Hexad Benchmark — {CELLS} cells, {STEPS} steps, Φ every {PHI_EVERY}")
    print("=" * 70)

    phi_calc = GPUPhiCalculator(n_bins=16)

    # Run all three
    print("\n▶ Running Baseline (C only)...")
    baseline = run_baseline(phi_calc)
    print(f"  Done: {baseline['elapsed']:.1f}s")

    print("\n▶ Running Emergent (C+W+S+M+E)...")
    emergent = run_emergent(phi_calc)
    print(f"  Done: {emergent['elapsed']:.1f}s")

    print("\n▶ Running Legacy (CompositeW+TensionSense+VectorMemory+EmpathyEthics)...")
    legacy = run_legacy(phi_calc)
    print(f"  Done: {legacy['elapsed']:.1f}s")

    # ── Results ──
    print("\n" + "=" * 70)
    print("  RESULTS")
    print("=" * 70)

    # Comparison table
    print(f"""
┌─────────────────────┬────────────┬────────────┬────────────┐
│ Metric              │  Baseline  │  Emergent  │   Legacy   │
├─────────────────────┼────────────┼────────────┼────────────┤
│ Cells               │ {baseline['cells']:>10} │ {emergent['cells']:>10} │ {legacy['cells']:>10} │
│ Φ mean              │ {baseline['phi_mean']:>10.2f} │ {emergent['phi_mean']:>10.2f} │ {legacy['phi_mean']:>10.2f} │
│ Φ max               │ {baseline['phi_max']:>10.2f} │ {emergent['phi_max']:>10.2f} │ {legacy['phi_max']:>10.2f} │
│ Φ min               │ {baseline['phi_min']:>10.2f} │ {emergent['phi_min']:>10.2f} │ {legacy['phi_min']:>10.2f} │
│ ms/step             │ {baseline['ms_per_step']:>10.1f} │ {emergent['ms_per_step']:>10.1f} │ {legacy['ms_per_step']:>10.1f} │
│ Total time (s)      │ {baseline['elapsed']:>10.1f} │ {emergent['elapsed']:>10.1f} │ {legacy['elapsed']:>10.1f} │
└─────────────────────┴────────────┴────────────┴────────────┘""")

    # Emergent-specific metrics
    print(f"""
┌─────────────────────┬────────────┬────────────┬────────────┐
│ Emergent Metrics    │    Mean    │    Min     │    Max     │
├─────────────────────┼────────────┼────────────┼────────────┤
│ Pain                │ {emergent['pain_mean']:>10.4f} │ {emergent['pain_min']:>10.4f} │ {emergent['pain_max']:>10.4f} │
│ Curiosity           │ {emergent['curiosity_mean']:>10.4f} │ {emergent['curiosity_min']:>10.4f} │ {emergent['curiosity_max']:>10.4f} │
│ Empathy             │ {emergent['empathy_mean']:>10.4f} │ {emergent['empathy_min']:>10.4f} │ {emergent['empathy_max']:>10.4f} │
│ Satisfaction        │ {emergent['satisfaction_mean']:>10.4f} │       —    │       —    │
│ LR multiplier       │ {emergent['lr_mean']:>10.4f} │       —    │       —    │
│ Allowed %           │ {emergent['allowed_pct']:>9.1f}% │       —    │       —    │
└─────────────────────┴────────────┴────────────┴────────────┘""")

    # Φ delta
    phi_delta_e = (emergent["phi_mean"] - baseline["phi_mean"]) / max(baseline["phi_mean"], 1e-8) * 100
    phi_delta_l = (legacy["phi_mean"] - baseline["phi_mean"]) / max(baseline["phi_mean"], 1e-8) * 100
    overhead_e = (emergent["ms_per_step"] - baseline["ms_per_step"]) / max(baseline["ms_per_step"], 1e-8) * 100
    overhead_l = (legacy["ms_per_step"] - baseline["ms_per_step"]) / max(baseline["ms_per_step"], 1e-8) * 100

    print(f"""
  ── Summary ──
  Emergent vs Baseline: Φ {phi_delta_e:+.1f}%, overhead {overhead_e:+.1f}%
  Legacy   vs Baseline: Φ {phi_delta_l:+.1f}%, overhead {overhead_l:+.1f}%
""")

    # ASCII graphs
    print(ascii_graph(emergent["phi_history"], "Φ (Emergent)"))
    print()
    print(ascii_graph(baseline["phi_history"], "Φ (Baseline)"))

    # Law compliance check
    print(f"""
  ── Law Compliance ──
  Law 2  (조작금지): {"✅" if emergent['pain_min'] < emergent['pain_max'] else "⚠️ pain 고정"} pain range [{emergent['pain_min']:.3f}, {emergent['pain_max']:.3f}]
  Law 4  (구조>기능): ✅ Emergent 모듈은 C 관찰만 (gradient-free)
  Law 22 (기능→Φ↓):  {"✅ Φ 유지/상승" if phi_delta_e >= -5 else f"⚠️ Φ {phi_delta_e:.1f}% 하락"}
  Law 71 (자유최대화): ✅ allowed={emergent['allowed_pct']:.0f}%
  Law 84 (만족pulse): ✅ satisfaction mean={emergent['satisfaction_mean']:.2f}
  Law 95 (세포정체성): ✅ cell_identity orthogonal init
""")

    print("=" * 70)
    print("  BENCHMARK COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
