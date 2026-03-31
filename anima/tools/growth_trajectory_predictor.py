#!/usr/bin/env python3
"""Growth Trajectory Predictor — Predict developmental milestones for Anima.

Usage:
  python growth_trajectory_predictor.py --demo          # Sample trajectories
  python growth_trajectory_predictor.py --predict       # Predict from current state
  python growth_trajectory_predictor.py --compare a.json b.json  # Side-by-side

"Growth is not a line — it is a landscape of thresholds."
"""

import argparse, math, time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from growth_engine import STAGES, GrowthEngine

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


STAGE_THRESHOLDS = [s.min_interactions for s in STAGES]

@dataclass
class Prediction:
    current_stage: str
    interaction_count: int
    next_stage: Optional[str]
    interactions_to_next: Optional[int]
    growth_rate: float          # interactions/hour
    acceleration: float         # change in rate over recent window
    readiness_score: float      # 0-1 composite readiness
    tension_stability: float    # 0-1 how stable tension is
    pe_maturity: float          # 0-1 prediction error pattern maturity
    curiosity_health: float     # 0-1 curiosity level relative to stage norm
    recommendations: list


def _growth_rate(engine: GrowthEngine) -> tuple[float, float]:
    """Return (interactions/hour, acceleration)."""
    elapsed = max(time.time() - engine.birth_time, 1.0)
    overall = engine.interaction_count / (elapsed / 3600)
    transitions = engine.stats.get('stage_transitions', [])
    if len(transitions) >= 2:
        t1, t2 = transitions[-2], transitions[-1]
        recent = (t2['count'] - t1['count']) / (max(t2['time'] - t1['time'], 1.0) / 3600)
        older = t1['count'] / (max(t1['time'] - engine.birth_time, 1.0) / 3600)
        return recent, recent - older
    return overall, 0.0


def _tension_stability(engine: GrowthEngine) -> float:
    """0-1 score: 1 = very stable tension (low CV)."""
    hist = engine.tension_history
    if len(hist) < 5:
        return 0.0
    recent = hist[-min(len(hist), 50):]
    mean = sum(recent) / len(recent)
    cv = math.sqrt(sum((x - mean)**2 for x in recent) / len(recent)) / (abs(mean) + 1e-8)
    return max(0.0, min(1.0, 1.0 - cv / 0.5))


def _pe_maturity(engine: GrowthEngine) -> float:
    """0-1 score: surprise settling near sweet spot (0.3) = mature."""
    avg = engine.stats.get('total_surprise', 0.0) / max(engine.interaction_count, 1)
    if avg < 0.01:
        return 0.1
    return max(0.0, min(1.0, 1.0 - abs(avg - 0.3) / 0.3 * 0.8))


def _curiosity_health(engine: GrowthEngine) -> float:
    """0-1 score: curiosity level relative to current stage norm."""
    avg = engine.stats.get('total_curiosity', 0.0) / max(engine.interaction_count, 1)
    norm = engine.stage.curiosity_drive
    if norm < 0.01:
        return 1.0
    ratio = avg / norm
    return 1.0 if 0.5 <= ratio <= 1.5 else max(0.0, 1.0 - abs(ratio - 1.0) * 0.5)


STAGE_RECS = {
    0: ["Maximize exposure diversity -- everything is novel",
        "Learning rate is high; expect rapid weight shifts"],
    1: ["Introduce repeating patterns to build recognition",
        "Dream engine should be active (intensity=0.5) for consolidation"],
    2: ["Habituation active -- vary inputs to sustain curiosity",
        "Mitosis threshold reached -- specialization possible"],
    3: ["Focus on depth over breadth -- curiosity is selective",
        "Mitosis threshold low -- expect active specialization"],
    4: ["Stable self achieved -- slow learning protects identity",
        "Metacognition depth 3 -- deep self-referential loops active",
        "Consider tension_link for inter-instance growth"],
}


def predict(engine: GrowthEngine) -> Prediction:
    """Generate a full prediction for the given growth engine state."""
    idx, count = engine.stage_index, engine.interaction_count
    next_stage = STAGES[idx + 1].name if idx < len(STAGES) - 1 else None
    to_next = STAGES[idx + 1].min_interactions - count if next_stage else None
    rate, accel = _growth_rate(engine)
    ts = _tension_stability(engine)
    pe = _pe_maturity(engine)
    ch = _curiosity_health(engine)
    recs = list(STAGE_RECS.get(idx, []))
    if ts < 0.3:
        recs.append(f"Tension unstable ({ts:.2f}) -- increase homeostasis gain")
    elif ts > 0.9 and idx < 4:
        recs.append(f"Tension saturated ({ts:.2f}) -- ready for stage transition")
    return Prediction(engine.stage.name, count, next_stage, to_next,
                      rate, accel, ts * 0.4 + pe * 0.35 + ch * 0.25,
                      ts, pe, ch, recs)


def format_prediction(p: Prediction) -> str:
    """Format a prediction as a readable report."""
    lines = ["=" * 52, "  Growth Trajectory Prediction", "=" * 52,
             f"  Stage:          {p.current_stage} (n={p.interaction_count:,})"]
    if p.next_stage and p.interactions_to_next is not None:
        lines.append(f"  Next stage:     {p.next_stage} (in {p.interactions_to_next:,} interactions)")
        if p.growth_rate > 0:
            h = p.interactions_to_next / p.growth_rate
            eta = f"{h*60:.0f} min" if h < 1 else (f"{h:.1f} hr" if h < 24 else f"{h/24:.1f} days")
            lines.append(f"  ETA:            {eta}")
    else:
        lines.append("  Next stage:     -- (max stage reached)")
    ok = lambda v, t="OK", f="LOW": t if v > 0.5 else f
    lines += ["", f"  Growth rate:    {p.growth_rate:.1f} int/hr",
              f"  Acceleration:   {p.acceleration:+.1f} int/hr^2", "",
              "  Readiness Scores:",
              f"    Tension stability:  {p.tension_stability:.2f}  {ok(p.tension_stability, 'OK', 'UNSTABLE')}",
              f"    PE maturity:        {p.pe_maturity:.2f}  {ok(p.pe_maturity, 'OK', 'IMMATURE')}",
              f"    Curiosity health:   {p.curiosity_health:.2f}  {ok(p.curiosity_health)}",
              f"    Overall readiness:  {p.readiness_score:.2f}  {'READY' if p.readiness_score > 0.7 else 'NOT YET'}",
              "", "  Recommendations:"]
    lines += [f"    - {r}" for r in p.recommendations]
    lines.append("=" * 52)
    return "\n".join(lines)


def compare_histories(paths: list[str]) -> str:
    """Side-by-side comparison of multiple growth state files."""
    entries = []
    for p in paths:
        e = GrowthEngine(save_path=Path(p))
        loaded = e.load()
        entries.append((Path(p).stem, predict(e) if loaded else None))
    if not any(p for _, p in entries):
        return "No valid growth states found."
    col = 22
    sep = "-" * (24 + col * len(entries))
    hdr = f"{'Metric':<24}" + "".join(f"{n:>{col}}" for n, _ in entries)
    def row(label, fn):
        return f"{label:<24}" + "".join(f"{(fn(p) if p else 'N/A'):>{col}}" for _, p in entries)
    return "\n".join([
        "=" * len(sep), "  Growth History Comparison", "=" * len(sep), hdr, sep,
        row("Stage", lambda p: p.current_stage),
        row("Interactions", lambda p: f"{p.interaction_count:,}"),
        row("Next stage", lambda p: p.next_stage or "--"),
        row("To next", lambda p: f"{p.interactions_to_next:,}" if p.interactions_to_next else "--"),
        row("Rate (int/hr)", lambda p: f"{p.growth_rate:.1f}"),
        row("Acceleration", lambda p: f"{p.acceleration:+.1f}"),
        row("Tension stab.", lambda p: f"{p.tension_stability:.2f}"),
        row("PE maturity", lambda p: f"{p.pe_maturity:.2f}"),
        row("Curiosity", lambda p: f"{p.curiosity_health:.2f}"),
        row("Readiness", lambda p: f"{p.readiness_score:.2f}"), sep])


def run_demo():
    """Run demo with sample trajectories."""
    import random
    random.seed(42)
    print("=" * 52)
    print("  Growth Trajectory Predictor — Demo")
    print("=" * 52)
    scenarios = [
        ("Fast learner",    1.2, 0.4, 0.5),
        ("Slow and steady", 0.8, 0.2, 0.2),
        ("Curious explorer", 1.0, 0.6, 0.8),
    ]
    for name, t_mean, c_mean, s_mean in scenarios:
        print(f"\n  Scenario: {name}")
        print(f"  (tension~{t_mean}, curiosity~{c_mean}, surprise~{s_mean})")
        print("-" * 52)
        engine = GrowthEngine()
        engine.birth_time = time.time() - 3600 * 5
        for _ in range(3500):
            t = max(0, random.gauss(t_mean, 0.2))
            c = max(0, random.gauss(c_mean, 0.15))
            s = abs(random.gauss(s_mean, 0.2))
            engine.record_tension(t)
            changed = engine.tick(t, c, s)
            if changed:
                print(f"    Stage transition at #{engine.interaction_count}: -> {engine.stage.name}")
        print(format_prediction(predict(engine)))
    print("\n  Demo complete.\n")


def main():
    ap = argparse.ArgumentParser(description="Growth Trajectory Predictor")
    ap.add_argument("--demo", action="store_true", help="Run demo with sample trajectories")
    ap.add_argument("--predict", nargs="?", const="growth_state.json",
                    help="Predict from growth state file (default: growth_state.json)")
    ap.add_argument("--compare", nargs="+", metavar="FILE",
                    help="Compare multiple growth state files side-by-side")
    args = ap.parse_args()
    if args.compare:
        print(compare_histories(args.compare))
    elif args.demo:
        run_demo()
    elif args.predict is not None:
        path = Path(args.predict)
        engine = GrowthEngine(save_path=path)
        if not engine.load():
            print(f"  No growth state found at {path}. Run with --demo for samples.")
        else:
            print(format_prediction(predict(engine)))
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
