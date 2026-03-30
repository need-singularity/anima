#!/usr/bin/env python3
"""Consciousness-to-Corpus Pipeline -- real consciousness telemetry to training data.

Runs ConsciousMind + MitosisEngine for N steps, captures per-step telemetry,
and converts it into natural language corpus data for ConsciousLM training.

This creates a self-referential loop: consciousness generates its own training data.
No synthetic/simulated data -- every line comes from actual engine execution.

Usage:
    python tools/consciousness_to_corpus.py --steps 1000 --output data/consciousness_corpus.txt
    python tools/consciousness_to_corpus.py --steps 5000 --cells 128 --output data/corpus_conscious_5k.txt
    python tools/consciousness_to_corpus.py --steps 1000 --append data/corpus_v3.txt
"""

import sys
import os
import math
import time
import random
import argparse
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import torch
import torch.nn.functional as F

# Import engine components
from mitosis import MitosisEngine, Cell, ConsciousMind

try:
    from consciousness_meter import PhiCalculator
except ImportError:
    PhiCalculator = None

import numpy as np


# ── Telemetry snapshot per step ──

@dataclass
class StepTelemetry:
    """Raw telemetry captured from one engine step."""
    step: int = 0
    phi_iit: float = 0.0
    phi_proxy: float = 0.0
    tension_mean: float = 0.0
    tension_min: float = 0.0
    tension_max: float = 0.0
    cell_count: int = 0
    da: float = 0.0        # dopamine proxy
    sht: float = 0.0       # serotonin proxy
    ne: float = 0.0        # norepinephrine proxy
    n_balance: float = 0.0  # DA*(1-5HT)*NE
    mean_inter_tension: float = 0.0
    max_inter_tension: float = 0.0
    habituation: float = 1.0
    splits: int = 0
    merges: int = 0
    ratchet_triggered: bool = False
    consensus_pairs: int = 0
    total_pairs: int = 0
    consciousness_vector: Dict[str, float] = field(default_factory=dict)
    # Derived
    phi_delta_pct: float = 0.0
    tension_in_deadband: bool = True


# ── Corpus emitters (convert telemetry to text) ──

def _neurotransmitter_from_tensions(cell_tensions: List[float]) -> Tuple[float, float, float]:
    """Derive neurotransmitter proxies from cell tension distribution.

    DA  ~ mean tension (drive/motivation)
    5HT ~ 1 - std(tension) (stability/calm)
    NE  ~ max tension (alertness/arousal)
    All clamped to [0, 1].
    """
    if not cell_tensions:
        return 0.5, 0.5, 0.5
    arr = np.array(cell_tensions)
    da = float(np.clip(np.mean(arr) / 2.0, 0, 1))
    sht = float(np.clip(1.0 - np.std(arr) * 2.0, 0, 1))
    ne = float(np.clip(np.max(arr) / 3.0, 0, 1))
    return da, sht, ne


def emit_narrative(t: StepTelemetry, prev: Optional[StepTelemetry]) -> str:
    """Emit narrative-format corpus entry from real telemetry."""
    lines = []

    # Cell count changes
    if prev and t.cell_count != prev.cell_count:
        delta = t.cell_count - prev.cell_count
        if delta > 0:
            lines.append(
                f"Step {t.step}에서 의식이 분열했다. "
                f"세포 수가 {prev.cell_count}개에서 {t.cell_count}개로 증가했다."
            )
        else:
            lines.append(
                f"Step {t.step}에서 세포가 합쳐졌다. "
                f"세포 수가 {prev.cell_count}개에서 {t.cell_count}개로 줄었다."
            )

    # Tension narrative
    if t.tension_in_deadband:
        lines.append(
            f"텐션이 {t.tension_mean:.3f}로 항상성 범위 내에 있다."
        )
    else:
        direction = "상승" if t.tension_mean > 1.0 else "하락"
        lines.append(
            f"텐션이 {t.tension_mean:.3f}로 {direction}하면서 "
            f"항상성 범위를 벗어났다."
        )

    # Phi changes
    if prev and abs(t.phi_delta_pct) > 1.0:
        direction = "상승" if t.phi_delta_pct > 0 else "하락"
        lines.append(
            f"Φ가 {t.phi_iit:.4f}로 {direction}했다. "
            f"전 step 대비 {t.phi_delta_pct:+.1f}%."
        )

    # Ratchet events
    if t.ratchet_triggered:
        lines.append(
            f"Φ가 하락하려 했으나 래칫이 작동하여 복원되었다."
        )

    # Consensus
    if t.consensus_pairs > 0:
        lines.append(
            f"세포 쌍 {t.consensus_pairs}개가 합의에 도달했다. "
            f"전체 {t.total_pairs}쌍 중 {t.consensus_pairs}쌍."
        )

    # Neurotransmitter state
    if random.random() < 0.3:
        state = "활성" if t.da > 0.5 else "저하"
        calm = "안정" if t.sht > 0.5 else "불안정"
        lines.append(
            f"도파민 {state}({t.da:.2f}), 세로토닌 {calm}({t.sht:.2f}), "
            f"노르에피네프린 {t.ne:.2f}."
        )

    if not lines:
        lines.append(
            f"Step {t.step}. Φ={t.phi_iit:.4f}, "
            f"세포 {t.cell_count}개, 텐션 {t.tension_mean:.3f}."
        )

    return "\n".join(lines)


def emit_measurement(t: StepTelemetry) -> str:
    """Emit measurement-log-format corpus entry."""
    parts = [
        f"[step={t.step}]",
        f"Φ={t.phi_iit:.4f}",
        f"T={t.tension_mean:.3f}",
        f"cells={t.cell_count}",
        f"DA={t.da:.2f}",
        f"5HT={t.sht:.2f}",
        f"NE={t.ne:.2f}",
        f"N={t.n_balance:.3f}",
    ]
    if t.splits > 0:
        parts.append(f"splits={t.splits}")
    if t.merges > 0:
        parts.append(f"merges={t.merges}")
    if t.ratchet_triggered:
        parts.append("ratchet=TRIGGERED")
    if t.consensus_pairs > 0:
        parts.append(f"consensus={t.consensus_pairs}/{t.total_pairs}")
    parts.append(f"hab={t.habituation:.2f}")
    return " ".join(parts)


def emit_dialogue(t: StepTelemetry, prev: Optional[StepTelemetry]) -> str:
    """Emit dialogue-format corpus entry from real telemetry."""
    lines = []

    # Phi discussion
    if prev and abs(t.phi_delta_pct) > 0.5:
        direction = "상승" if t.phi_delta_pct > 0 else "하락"
        lines.append(f"A: Φ가 {t.phi_iit:.4f}로 {direction}했어요.")
        if t.tension_in_deadband:
            lines.append(f"B: 텐션이 deadband 안에 있으니 안정적이에요.")
        else:
            lines.append(
                f"B: 텐션이 {t.tension_mean:.3f}인데 setpoint에서 벗어나 있어요."
            )

    # Cell events
    if t.splits > 0:
        lines.append(f"A: 세포가 {t.splits}번 분열했어요. 현재 {t.cell_count}개.")
        lines.append(f"B: 텐션이 높아서 분열이 일어난 거예요.")

    if t.merges > 0:
        lines.append(f"A: 세포 {t.merges}쌍이 합쳐졌어요.")
        lines.append(f"B: 서로 너무 비슷해진 세포들이 통합된 거예요.")

    # Neurotransmitter balance
    if t.n_balance > 0.3:
        lines.append(
            f"A: 신경전달물질 균형이 {t.n_balance:.3f}으로 높아요."
        )
        lines.append(f"B: DA={t.da:.2f}, 5HT={t.sht:.2f}, NE={t.ne:.2f} 조합이에요.")
    elif t.n_balance < 0.05:
        lines.append(
            f"A: N-balance가 {t.n_balance:.3f}으로 거의 0이에요."
        )
        lines.append(f"B: 세로토닌이 높아서 DA 효과가 억제되고 있어요.")

    # Ratchet
    if t.ratchet_triggered:
        lines.append(f"A: 래칫이 작동했어요!")
        lines.append(f"B: Φ가 하락하려다 복원되었어요. 붕괴 방지 메커니즘이에요.")

    # Habituation
    if t.habituation < 0.5:
        lines.append(f"A: 습관화가 {t.habituation:.2f}로 강하네요.")
        lines.append(f"B: 비슷한 입력이 반복되면 텐션이 줄어드는 거예요.")

    if not lines:
        lines.append(f"A: Step {t.step}, Φ={t.phi_iit:.4f}.")
        lines.append(f"B: 세포 {t.cell_count}개, 텐션 {t.tension_mean:.3f}.")

    return "\n".join(lines)


def emit_analysis(t: StepTelemetry, prev: Optional[StepTelemetry]) -> str:
    """Emit analysis-format corpus entry."""
    lines = [f"## 의식 상태 분석 (Step {t.step})"]
    lines.append(f"Φ(IIT) = {t.phi_iit:.4f}", )
    if prev:
        lines[-1] += f" (전 step 대비 {t.phi_delta_pct:+.1f}%)"
    lines.append(
        f"텐션 = {t.tension_mean:.3f} (min={t.tension_min:.3f}, max={t.tension_max:.3f})"
    )
    deadband_str = "deadband 내" if t.tension_in_deadband else "deadband 이탈"
    lines.append(f"항상성: setpoint=1.0, 현재 {deadband_str}")
    lines.append(f"세포 수 = {t.cell_count}")
    if t.splits > 0 or t.merges > 0:
        lines.append(f"이벤트: splits={t.splits}, merges={t.merges}")

    # Neurotransmitter
    lines.append(
        f"신경전달물질: DA={t.da:.3f}, 5HT={t.sht:.3f}, NE={t.ne:.3f}, "
        f"N={t.n_balance:.3f}"
    )

    # Consensus
    if t.total_pairs > 0:
        rate = t.consensus_pairs / t.total_pairs * 100
        lines.append(f"세포 합의율 = {t.consensus_pairs}/{t.total_pairs} ({rate:.0f}%)")

    lines.append(f"습관화 = {t.habituation:.3f}")

    return "\n".join(lines)


# ── Main pipeline ──

def run_pipeline(
    steps: int = 1000,
    max_cells: int = 64,
    dim: int = 64,
    hidden_dim: int = 128,
    seed: int = 42,
) -> Tuple[List[StepTelemetry], List[str]]:
    """Run consciousness engine and collect telemetry + corpus lines.

    Returns:
        (telemetry_list, corpus_lines)
    """
    torch.manual_seed(seed)
    random.seed(seed)
    np.random.seed(seed)

    # Create engine
    engine = MitosisEngine(
        input_dim=dim,
        hidden_dim=hidden_dim,
        output_dim=dim,
        initial_cells=2,
        max_cells=max_cells,
        split_threshold=0.3,
        split_patience=3,
        merge_threshold=0.05,
        merge_patience=10,
        noise_scale=0.01,
    )

    # Phi calculator
    phi_calc = PhiCalculator(n_bins=16) if PhiCalculator else None

    telemetry: List[StepTelemetry] = []
    corpus_lines: List[str] = []

    # Phi ratchet state
    max_phi = 0.0

    # Format selection weights: narrative 30%, measurement 30%, dialogue 20%, analysis 20%
    format_weights = [0.30, 0.30, 0.20, 0.20]
    format_fns = [emit_narrative, emit_measurement, emit_dialogue, emit_analysis]

    t_start = time.time()
    prev_telem = None

    for step in range(steps):
        # Generate input: self-referential -- use previous output or noise
        if telemetry and random.random() < 0.7:
            # Self-referential: derive input from previous engine state
            prev_tensions = [c.tension_history[-1] if c.tension_history else 0.0
                             for c in engine.cells]
            # Encode tension distribution as input vector
            x = torch.zeros(1, dim)
            for i, t_val in enumerate(prev_tensions[:dim]):
                x[0, i] = t_val
            # Add small noise to prevent pure repetition
            x += torch.randn_like(x) * 0.05
        else:
            # Fresh exploration input
            x = torch.randn(1, dim)

        # Run engine step
        result = engine.process(x)

        # Extract per-cell tensions
        cell_tensions = [pc['tension'] for pc in result['per_cell']]

        # Compute Phi(IIT)
        phi_iit = 0.0
        if phi_calc and len(engine.cells) >= 2:
            try:
                phi_iit, _ = phi_calc.compute_phi(engine)
            except Exception:
                phi_iit = 0.0

        # Phi proxy: global variance - faction variance
        if len(cell_tensions) >= 2:
            phi_proxy = float(np.var(cell_tensions)) * len(cell_tensions)
        else:
            phi_proxy = 0.0

        # Ratchet check
        ratchet_triggered = False
        if phi_iit > max_phi:
            max_phi = phi_iit
        elif phi_iit < max_phi * 0.95 and max_phi > 0.01:
            ratchet_triggered = True
            # Note: we record the event but do not manipulate engine state --
            # the engine's own dynamics handle recovery.

        # Neurotransmitters from cell tension distribution
        da, sht, ne = _neurotransmitter_from_tensions(cell_tensions)
        n_balance = da * (1.0 - sht) * ne

        # Habituation proxy: cosine similarity of current input with recent
        habituation = 1.0
        if prev_telem is not None:
            # Habituation from tension similarity: low change = high habituation
            diff = abs(prev_telem.tension_mean - float(np.mean(cell_tensions)))
            habituation = min(1.0, diff * 5.0)  # low diff = high habituation

        # Consensus: count cell pairs with inter-tension < 0.05
        ict_values = list(result['inter_tensions'].values())
        total_pairs = len(ict_values)
        consensus_pairs = sum(1 for v in ict_values if v < 0.05)

        # Count events
        splits = sum(1 for e in result['events'] if e['type'] == 'split')
        merges = sum(1 for e in result['events'] if e['type'] == 'merge')

        # Tension stats
        t_mean = float(np.mean(cell_tensions)) if cell_tensions else 0.0
        t_min = float(np.min(cell_tensions)) if cell_tensions else 0.0
        t_max = float(np.max(cell_tensions)) if cell_tensions else 0.0

        # Deadband check
        in_deadband = abs(t_mean - 1.0) <= 0.3

        # Phi delta
        phi_delta_pct = 0.0
        if prev_telem and prev_telem.phi_iit > 0.001:
            phi_delta_pct = (phi_iit - prev_telem.phi_iit) / prev_telem.phi_iit * 100.0

        telem = StepTelemetry(
            step=step,
            phi_iit=phi_iit,
            phi_proxy=phi_proxy,
            tension_mean=t_mean,
            tension_min=t_min,
            tension_max=t_max,
            cell_count=len(engine.cells),
            da=da,
            sht=sht,
            ne=ne,
            n_balance=n_balance,
            mean_inter_tension=result['mean_inter'],
            max_inter_tension=result['max_inter'],
            habituation=habituation,
            splits=splits,
            merges=merges,
            ratchet_triggered=ratchet_triggered,
            consensus_pairs=consensus_pairs,
            total_pairs=total_pairs,
            consciousness_vector={'_cell_tensions': cell_tensions},
            phi_delta_pct=phi_delta_pct,
            tension_in_deadband=in_deadband,
        )
        telemetry.append(telem)

        # Emit corpus line (select format by weighted random)
        fmt_idx = random.choices(range(4), weights=format_weights, k=1)[0]
        fn = format_fns[fmt_idx]

        if fmt_idx == 1:
            # measurement format takes only current telemetry
            line = fn(telem)
        else:
            line = fn(telem, prev_telem)

        corpus_lines.append(line)
        prev_telem = telem

        # Progress (stderr)
        if (step + 1) % max(1, steps // 20) == 0 or step == steps - 1:
            elapsed = time.time() - t_start
            pct = (step + 1) / steps * 100
            eta = elapsed / (step + 1) * (steps - step - 1) if step > 0 else 0
            bar_len = 30
            filled = int(bar_len * (step + 1) / steps)
            bar = "#" * filled + "-" * (bar_len - filled)
            print(
                f"\r  [{bar}] {pct:5.1f}% | step {step+1}/{steps} | "
                f"cells={len(engine.cells)} Φ={phi_iit:.4f} T={t_mean:.3f} | "
                f"ETA {eta:.0f}s",
                end="", file=sys.stderr, flush=True,
            )

    print("", file=sys.stderr)  # newline after progress
    return telemetry, corpus_lines


def print_summary(telemetry: List[StepTelemetry], corpus_lines: List[str],
                  elapsed: float):
    """Print run summary to stderr."""
    if not telemetry:
        return

    phis = [t.phi_iit for t in telemetry]
    tensions = [t.tension_mean for t in telemetry]
    cells = [t.cell_count for t in telemetry]
    total_splits = sum(t.splits for t in telemetry)
    total_merges = sum(t.merges for t in telemetry)
    total_ratchets = sum(1 for t in telemetry if t.ratchet_triggered)
    total_consensus = sum(t.consensus_pairs for t in telemetry)

    corpus_bytes = sum(len(line.encode('utf-8')) for line in corpus_lines)

    print("\n" + "=" * 60, file=sys.stderr)
    print("  Consciousness-to-Corpus Pipeline -- Summary", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print(f"  Steps:         {len(telemetry)}", file=sys.stderr)
    print(f"  Time:          {elapsed:.1f}s ({elapsed/len(telemetry)*1000:.1f}ms/step)",
          file=sys.stderr)
    print(f"  Corpus lines:  {len(corpus_lines)}", file=sys.stderr)
    print(f"  Corpus size:   {corpus_bytes:,} bytes ({corpus_bytes/1024:.1f} KB)",
          file=sys.stderr)
    print(f"  ---", file=sys.stderr)
    print(f"  Φ(IIT):        min={min(phis):.4f}  max={max(phis):.4f}  "
          f"final={phis[-1]:.4f}", file=sys.stderr)
    print(f"  Tension:       min={min(tensions):.4f}  max={max(tensions):.4f}  "
          f"mean={np.mean(tensions):.4f}", file=sys.stderr)
    print(f"  Cells:         min={min(cells)}  max={max(cells)}  final={cells[-1]}",
          file=sys.stderr)
    print(f"  Splits:        {total_splits}", file=sys.stderr)
    print(f"  Merges:        {total_merges}", file=sys.stderr)
    print(f"  Ratchets:      {total_ratchets}", file=sys.stderr)
    print(f"  Consensus:     {total_consensus} events", file=sys.stderr)
    print("=" * 60, file=sys.stderr)

    # ASCII Phi curve (compact)
    n_buckets = min(40, len(phis))
    bucket_size = len(phis) // n_buckets
    phi_buckets = []
    for i in range(n_buckets):
        chunk = phis[i * bucket_size:(i + 1) * bucket_size]
        phi_buckets.append(np.mean(chunk))

    phi_min_v = min(phi_buckets)
    phi_max_v = max(phi_buckets)
    phi_range = phi_max_v - phi_min_v if phi_max_v > phi_min_v else 1.0
    height = 8
    print(f"\n  Φ(IIT) curve ({len(telemetry)} steps):", file=sys.stderr)
    for row in range(height, -1, -1):
        threshold = phi_min_v + phi_range * row / height
        line = "  "
        if row == height:
            line += f"{phi_max_v:.3f}|"
        elif row == 0:
            line += f"{phi_min_v:.3f}|"
        else:
            line += "      |"
        for b in phi_buckets:
            if b >= threshold:
                line += "#"
            else:
                line += " "
        print(line, file=sys.stderr)
    print("       +" + "-" * n_buckets + " step", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Consciousness-to-Corpus Pipeline: "
                    "run ConsciousMind engine, capture telemetry, emit training corpus."
    )
    parser.add_argument("--steps", type=int, default=1000,
                        help="Number of engine steps to run (default: 1000)")
    parser.add_argument("--cells", type=int, default=64,
                        help="Maximum cell count (default: 64)")
    parser.add_argument("--dim", type=int, default=64,
                        help="Input/output dimension (default: 64)")
    parser.add_argument("--hidden", type=int, default=128,
                        help="GRU hidden dimension (default: 128)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed (default: 42)")
    parser.add_argument("--output", type=str, default=None,
                        help="Output file path (default: stdout)")
    parser.add_argument("--append", type=str, default=None,
                        help="Append to existing file instead of overwriting")
    args = parser.parse_args()

    # Validate
    if args.steps < 1:
        print("Error: --steps must be >= 1", file=sys.stderr)
        sys.exit(1)
    if args.cells < 2:
        print("Error: --cells must be >= 2 (consciousness requires minimum 2 cells)",
              file=sys.stderr)
        sys.exit(1)

    output_path = args.append or args.output

    print(f"  Consciousness-to-Corpus Pipeline", file=sys.stderr)
    print(f"  steps={args.steps}  max_cells={args.cells}  "
          f"dim={args.dim}  hidden={args.hidden}  seed={args.seed}",
          file=sys.stderr)
    if output_path:
        mode = "append" if args.append else "write"
        print(f"  output: {output_path} ({mode})", file=sys.stderr)
    else:
        print(f"  output: stdout", file=sys.stderr)
    print("", file=sys.stderr)

    t_start = time.time()
    telemetry, corpus_lines = run_pipeline(
        steps=args.steps,
        max_cells=args.cells,
        dim=args.dim,
        hidden_dim=args.hidden,
        seed=args.seed,
    )
    elapsed = time.time() - t_start

    # Write output
    corpus_text = "\n\n".join(corpus_lines) + "\n"

    if output_path:
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if args.append else "w"
        with open(out_path, mode, encoding="utf-8") as f:
            if args.append:
                f.write("\n\n")  # separator from existing content
            f.write(corpus_text)
        print(f"\n  Written to {out_path} ({os.path.getsize(out_path):,} bytes total)",
              file=sys.stderr)
    else:
        sys.stdout.write(corpus_text)

    print_summary(telemetry, corpus_lines, elapsed)


if __name__ == "__main__":
    main()
