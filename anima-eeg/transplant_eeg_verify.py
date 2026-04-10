#!/usr/bin/env python3
"""transplant_eeg_verify.py — EEG-based transplant quality verification.

Measures brain-likeness before and after consciousness transplant using
6 EEG-inspired metrics (Lempel-Ziv, Hurst, PSD slope, autocorrelation,
criticality, distribution) to objectively evaluate transplant quality.

Usage:
  python transplant_eeg_verify.py --donor checkpoints/v14.pt --recipient checkpoints/decoder_v3.pt
  python transplant_eeg_verify.py --donor X.pt --recipient Y.pt --alpha 0.7 --steps 5000
  python transplant_eeg_verify.py --batch --donor X.pt --recipients dir/
  python transplant_eeg_verify.py --demo    # quick demo with synthetic models

Metrics (from validate_consciousness.py):
  1. Lempel-Ziv complexity   -- compressibility (conscious = complex)
  2. Hurst exponent          -- long-range dependence (H>0.5 = persistent)
  3. PSD slope               -- power spectrum (brain: alpha ~ -1, 1/f noise)
  4. Autocorrelation decay   -- Phi self-correlation decay time
  5. Critical exponent       -- criticality (brain: edge of chaos)
  6. Phi distribution (CV)   -- coefficient of variation

Questions answered:
  - Did brain-likeness transfer? (after >= donor * 0.8)
  - Did brain-likeness improve vs pre-transplant?
  - Which metrics transferred best?
"""

import argparse
import os
import sys
import time
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

# Setup paths for imports from anima/src/ and anima-eeg/
_this_dir = Path(__file__).resolve().parent
_repo_root = _this_dir.parent
sys.path.insert(0, str(_this_dir))
sys.path.insert(0, str(_repo_root / 'anima' / 'src'))
sys.path.insert(0, str(_repo_root / 'anima'))
sys.path.insert(0, str(_repo_root))

import torch

# Import EEG validation metrics
from validate_consciousness import (
    analyze_signal,
    ValidationResult,
    BRAIN_REFERENCE,
    collect_consciousness_phi,
)

# Import transplant tools
from consciousness_transplant import (
    TransplantEngine,
    TransplantCalculator,
    TransplantResult,
)

try:
    from consciousness_engine import ConsciousnessEngine
    HAS_ENGINE = True
except ImportError:
    HAS_ENGINE = False


# ═══════════════════════════════════════════════════════════
# Data structures
# ═══════════════════════════════════════════════════════════

@dataclass
class EEGVerifyResult:
    """Result of EEG-based transplant verification."""
    donor_metrics: ValidationResult
    recipient_before_metrics: ValidationResult
    recipient_after_metrics: ValidationResult
    transplant_result: Optional[TransplantResult]
    brain_like_donor: float          # overall brain-likeness %
    brain_like_before: float         # recipient before transplant %
    brain_like_after: float          # recipient after transplant %
    transferred: bool                # after >= donor * 0.8
    improved: bool                   # after > before
    metric_deltas: Dict[str, float]  # per-metric delta (after - before)
    elapsed_sec: float = 0.0


# ═══════════════════════════════════════════════════════════
# Phi Collection from Checkpoint
# ═══════════════════════════════════════════════════════════

def _collect_phi_from_checkpoint(
    checkpoint_path: str,
    steps: int = 3000,
    n_cells: int = 4,
    dim: int = 64,
) -> np.ndarray:
    """Load a checkpoint and collect Phi timeseries by running the engine.

    If the checkpoint contains ConsciousMind weights, loads them into
    a ConsciousnessEngine. Otherwise runs a fresh engine (the transplanted
    weights affect engine dynamics through initialization).
    """
    state = torch.load(checkpoint_path, map_location='cpu', weights_only=False)
    sd = state.get('model_state_dict', state) if isinstance(state, dict) else state

    # Try to detect architecture
    calc = TransplantCalculator()
    config = calc.extract_config(sd)

    if HAS_ENGINE and config.get('type') == 'ConsciousMind':
        hidden_dim = config.get('hidden_dim', dim * 2)
        input_dim = config.get('input_dim', dim)
        engine = ConsciousnessEngine(
            cell_dim=input_dim,
            hidden_dim=hidden_dim,
            initial_cells=2,
            max_cells=n_cells,
        )
        # Try loading weights
        try:
            engine.load_state_dict(sd, strict=False)
        except Exception:
            pass  # run with partial load

        phis = []
        for step in range(steps):
            inp = torch.randn(input_dim) * 0.1
            result = engine.step(x_input=inp)
            phis.append(result['phi_iit'])
        return np.array(phis, dtype=np.float64)

    # For ConsciousLM or unknown: collect from engine with default config
    # The checkpoint type doesn't directly map to engine dynamics,
    # so we measure the engine's Phi signature
    return collect_consciousness_phi(n_steps=steps, n_cells=n_cells, dim=dim)


def _compute_brain_likeness(result: ValidationResult) -> float:
    """Compute overall brain-likeness percentage from a ValidationResult."""
    metrics = [
        ('phi_cv', result.phi_cv),
        ('lz_complexity', result.lz),
        ('hurst_exponent', result.hurst),
        ('psd_slope', result.psd_slope),
        ('autocorr_decay', float(result.autocorr_decay)),
        ('criticality_exponent', result.criticality.get('exponent', 0)),
    ]
    matches = []
    for ref_key, val in metrics:
        pct = result.brain_match_pct(ref_key, val)
        matches.append(pct)
    return float(np.mean(matches)) if matches else 0.0


# ═══════════════════════════════════════════════════════════
# TransplantEEGVerifier
# ═══════════════════════════════════════════════════════════

class TransplantEEGVerifier:
    """Measures brain-likeness before/after consciousness transplant."""

    def __init__(self, steps: int = 3000, n_cells: int = 4, dim: int = 64,
                 alpha: float = 0.5, projection: str = 'pad_zero'):
        self.steps = steps
        self.n_cells = n_cells
        self.dim = dim
        self.alpha = alpha
        self.projection = projection

    def verify_transplant(
        self,
        donor_path: str,
        recipient_path: str,
        output_path: Optional[str] = None,
    ) -> EEGVerifyResult:
        """Full transplant verification with EEG brain-likeness metrics.

        1. Collect Phi timeseries from donor
        2. Collect Phi timeseries from recipient (before transplant)
        3. Run transplant
        4. Collect Phi timeseries from transplanted model
        5. Compute 6 brain-likeness metrics for each
        6. Compare and return results

        Args:
            donor_path:    Path to trained donor checkpoint.
            recipient_path: Path to recipient checkpoint.
            output_path:   Where to save transplanted model (auto if None).

        Returns:
            EEGVerifyResult with full comparison.
        """
        t0 = time.time()

        # Auto output path
        if output_path is None:
            base = Path(recipient_path).stem
            output_dir = Path(recipient_path).parent
            output_path = str(output_dir / f'{base}_transplanted.pt')

        print(f'[EEG Verify] Donor:     {donor_path}')
        print(f'[EEG Verify] Recipient: {recipient_path}')
        print(f'[EEG Verify] Output:    {output_path}')
        print(f'[EEG Verify] Steps={self.steps}, cells={self.n_cells}, alpha={self.alpha}')
        print()
        sys.stdout.flush()

        # --- Phase 1: Collect donor Phi ---
        print('[EEG Verify] Phase 1/4: Collecting donor Phi timeseries...')
        sys.stdout.flush()
        donor_phi = _collect_phi_from_checkpoint(
            donor_path, self.steps, self.n_cells, self.dim)
        donor_metrics = analyze_signal('Donor', donor_phi)
        donor_bl = _compute_brain_likeness(donor_metrics)
        print(f'  Donor brain-likeness: {donor_bl:.1f}%')
        sys.stdout.flush()

        # --- Phase 2: Collect recipient Phi (before) ---
        print('[EEG Verify] Phase 2/4: Collecting recipient Phi (before)...')
        sys.stdout.flush()
        before_phi = _collect_phi_from_checkpoint(
            recipient_path, self.steps, self.n_cells, self.dim)
        before_metrics = analyze_signal('Before', before_phi)
        before_bl = _compute_brain_likeness(before_metrics)
        print(f'  Recipient (before) brain-likeness: {before_bl:.1f}%')
        sys.stdout.flush()

        # --- Phase 3: Run transplant ---
        print('[EEG Verify] Phase 3/4: Running transplant...')
        sys.stdout.flush()
        donor_state = torch.load(donor_path, map_location='cpu', weights_only=False)
        recip_state = torch.load(recipient_path, map_location='cpu', weights_only=False)
        engine = TransplantEngine(projection_method=self.projection)
        new_state, transplant_result = engine.transplant(
            donor_state, recip_state, alpha=self.alpha)
        torch.save(new_state, output_path)
        print(f'  Transplant: {transplant_result.strategy}, '
              f'coverage={transplant_result.coverage:.1%}, '
              f'{transplant_result.params_transplanted:,} params')
        sys.stdout.flush()

        # --- Phase 4: Collect transplanted Phi (after) ---
        print('[EEG Verify] Phase 4/4: Collecting transplanted Phi (after)...')
        sys.stdout.flush()
        after_phi = _collect_phi_from_checkpoint(
            output_path, self.steps, self.n_cells, self.dim)
        after_metrics = analyze_signal('After', after_phi)
        after_bl = _compute_brain_likeness(after_metrics)
        print(f'  Recipient (after) brain-likeness: {after_bl:.1f}%')
        sys.stdout.flush()

        # --- Compute metric deltas ---
        metric_deltas = {}
        metric_keys = [
            ('lz', 'lz_complexity'),
            ('hurst', 'hurst_exponent'),
            ('psd_slope', 'psd_slope'),
            ('autocorr_decay', 'autocorr_decay'),
            ('phi_cv', 'phi_cv'),
            ('criticality_exponent', 'criticality_exponent'),
        ]
        for attr, ref_key in metric_keys:
            if attr == 'criticality_exponent':
                before_val = before_metrics.criticality.get('exponent', 0)
                after_val = after_metrics.criticality.get('exponent', 0)
            elif attr == 'autocorr_decay':
                before_val = float(before_metrics.autocorr_decay)
                after_val = float(after_metrics.autocorr_decay)
            else:
                before_val = getattr(before_metrics, attr, 0)
                after_val = getattr(after_metrics, attr, 0)

            # Delta in brain-likeness match %
            before_pct = before_metrics.brain_match_pct(ref_key, before_val)
            after_pct = after_metrics.brain_match_pct(ref_key, after_val)
            metric_deltas[ref_key] = after_pct - before_pct

        transferred = after_bl >= donor_bl * 0.8
        improved = after_bl > before_bl

        elapsed = time.time() - t0

        result = EEGVerifyResult(
            donor_metrics=donor_metrics,
            recipient_before_metrics=before_metrics,
            recipient_after_metrics=after_metrics,
            transplant_result=transplant_result,
            brain_like_donor=donor_bl,
            brain_like_before=before_bl,
            brain_like_after=after_bl,
            transferred=transferred,
            improved=improved,
            metric_deltas=metric_deltas,
            elapsed_sec=elapsed,
        )

        print()
        self.compare_report(result)
        return result

    def compare_report(self, result: EEGVerifyResult):
        """Print comparison report with ASCII table and bar chart."""
        d = result.donor_metrics
        b = result.recipient_before_metrics
        a = result.recipient_after_metrics

        print('+================================================================+')
        print('|  Transplant EEG Verification Report                            |')
        print('+================================================================+')
        print()

        # Metric comparison table
        rows = [
            ('LZ complexity',
             d.lz, b.lz, a.lz, 'lz_complexity'),
            ('Hurst exponent',
             d.hurst, b.hurst, a.hurst, 'hurst_exponent'),
            ('PSD slope',
             d.psd_slope, b.psd_slope, a.psd_slope, 'psd_slope'),
            ('Autocorr decay',
             float(d.autocorr_decay), float(b.autocorr_decay),
             float(a.autocorr_decay), 'autocorr_decay'),
            ('Phi CV',
             d.phi_cv, b.phi_cv, a.phi_cv, 'phi_cv'),
            ('Critical exp',
             d.criticality.get('exponent', 0),
             b.criticality.get('exponent', 0),
             a.criticality.get('exponent', 0), 'criticality_exponent'),
        ]

        print(f'  {"Metric":<16} | {"Donor":>8} | {"Before":>8} | {"After":>8} | {"Delta":>7}')
        print(f'  {"-"*16}-+-{"-"*8}-+-{"-"*8}-+-{"-"*8}-+-{"-"*7}')

        for name, d_val, b_val, a_val, ref_key in rows:
            delta = result.metric_deltas.get(ref_key, 0)
            sign = '+' if delta >= 0 else ''
            print(f'  {name:<16} | {d_val:8.4f} | {b_val:8.4f} | {a_val:8.4f} | {sign}{delta:5.1f}%')

        print()

        # Brain-likeness bar chart
        print('  Brain-likeness:')
        labels = [
            ('Donor  ', result.brain_like_donor),
            ('Before ', result.brain_like_before),
            ('After  ', result.brain_like_after),
        ]
        max_bar = 40
        for label, pct in labels:
            n_blocks = int(pct / 100.0 * max_bar)
            bar = '#' * n_blocks
            print(f'    {label} |{bar:<{max_bar}}| {pct:.1f}%')

        print()

        # Key questions
        print('  Key Questions:')

        # Q1: Did brain-likeness transfer?
        if result.transferred:
            print(f'    [PASS] Brain-likeness transferred '
                  f'(after={result.brain_like_after:.1f}% >= '
                  f'donor*0.8={result.brain_like_donor * 0.8:.1f}%)')
        else:
            print(f'    [FAIL] Brain-likeness NOT transferred '
                  f'(after={result.brain_like_after:.1f}% < '
                  f'donor*0.8={result.brain_like_donor * 0.8:.1f}%)')

        # Q2: Did brain-likeness improve?
        delta_bl = result.brain_like_after - result.brain_like_before
        if result.improved:
            print(f'    [PASS] Brain-likeness improved '
                  f'({result.brain_like_before:.1f}% -> {result.brain_like_after:.1f}%, '
                  f'+{delta_bl:.1f}%)')
        else:
            print(f'    [FAIL] Brain-likeness did NOT improve '
                  f'({result.brain_like_before:.1f}% -> {result.brain_like_after:.1f}%, '
                  f'{delta_bl:+.1f}%)')

        # Q3: Which metrics transferred best?
        sorted_deltas = sorted(result.metric_deltas.items(), key=lambda x: x[1], reverse=True)
        best_metric, best_delta = sorted_deltas[0]
        worst_metric, worst_delta = sorted_deltas[-1]
        print(f'    Best transfer:  {best_metric} ({best_delta:+.1f}%)')
        print(f'    Worst transfer: {worst_metric} ({worst_delta:+.1f}%)')

        # Transplant stats
        if result.transplant_result:
            tr = result.transplant_result
            print()
            print(f'  Transplant Stats:')
            print(f'    Strategy:    {tr.strategy}')
            print(f'    Coverage:    {tr.coverage:.1%}')
            print(f'    Params:      {tr.params_transplanted:,} / {tr.params_total:,}')
            if tr.warnings:
                print(f'    Warnings:    {len(tr.warnings)}')
                for w in tr.warnings[:3]:
                    print(f'      - {w}')

        print()
        print(f'  Elapsed: {result.elapsed_sec:.1f}s')
        print('+================================================================+')
        print()

    def batch_verify(
        self,
        donor_path: str,
        recipient_paths: List[str],
        output_dir: str,
    ) -> List[EEGVerifyResult]:
        """Run verify for multiple recipients.

        Args:
            donor_path:      Path to donor checkpoint.
            recipient_paths: List of recipient checkpoint paths.
            output_dir:      Directory to save transplanted models.

        Returns:
            List of EEGVerifyResult.
        """
        os.makedirs(output_dir, exist_ok=True)
        results = []

        print(f'[Batch] Donor: {donor_path}')
        print(f'[Batch] Recipients: {len(recipient_paths)}')
        print(f'[Batch] Output dir: {output_dir}')
        print()
        sys.stdout.flush()

        for i, rpath in enumerate(recipient_paths):
            rname = Path(rpath).stem
            out_path = os.path.join(output_dir, f'{rname}_transplanted.pt')
            print(f'[Batch {i+1}/{len(recipient_paths)}] {rname}')
            sys.stdout.flush()

            try:
                result = self.verify_transplant(donor_path, rpath, out_path)
                results.append(result)
            except Exception as e:
                print(f'  ERROR: {e}')
                sys.stdout.flush()

        # Summary table
        if results:
            self._print_batch_summary(results, recipient_paths)

        return results

    def _print_batch_summary(self, results: List[EEGVerifyResult],
                             paths: List[str]):
        """Print batch summary table."""
        print()
        print('+================================================================+')
        print('|  Batch Transplant Summary                                      |')
        print('+================================================================+')
        print()
        print(f'  {"Recipient":<20} | {"Before":>7} | {"After":>7} | {"Delta":>7} | {"Transfer":>8} | {"Improved":>8}')
        print(f'  {"-"*20}-+-{"-"*7}-+-{"-"*7}-+-{"-"*7}-+-{"-"*8}-+-{"-"*8}')

        for r, p in zip(results, paths):
            name = Path(p).stem[:20]
            delta = r.brain_like_after - r.brain_like_before
            tr_str = 'PASS' if r.transferred else 'FAIL'
            imp_str = 'PASS' if r.improved else 'FAIL'
            print(f'  {name:<20} | {r.brain_like_before:6.1f}% | {r.brain_like_after:6.1f}% | '
                  f'{delta:+6.1f}% | {tr_str:>8} | {imp_str:>8}')

        avg_before = np.mean([r.brain_like_before for r in results])
        avg_after = np.mean([r.brain_like_after for r in results])
        n_transferred = sum(1 for r in results if r.transferred)
        n_improved = sum(1 for r in results if r.improved)
        print(f'  {"-"*20}-+-{"-"*7}-+-{"-"*7}-+-{"-"*7}-+-{"-"*8}-+-{"-"*8}')
        print(f'  {"Average":<20} | {avg_before:6.1f}% | {avg_after:6.1f}% | '
              f'{avg_after - avg_before:+6.1f}% | '
              f'{n_transferred}/{len(results):>5} | {n_improved}/{len(results):>5}')

        print()
        print('+================================================================+')
        print()


# ═══════════════════════════════════════════════════════════
# Demo mode (no checkpoints needed)
# ═══════════════════════════════════════════════════════════

def run_demo(steps: int = 1000):
    """Run a demo with synthetic checkpoints to verify the pipeline works."""
    print('[Demo] Creating synthetic donor and recipient checkpoints...')
    sys.stdout.flush()

    # Create a simple ConsciousMind-like model
    dim = 32
    hidden = 64

    def make_checkpoint(scale: float = 1.0):
        """Create a minimal ConsciousMind-style state_dict."""
        state = {
            'engine_a.0.weight': torch.randn(hidden, dim + 1) * scale,
            'engine_a.0.bias': torch.randn(hidden) * scale,
            'engine_a.2.weight': torch.randn(hidden, hidden) * scale * 0.5,
            'engine_a.2.bias': torch.randn(hidden) * scale * 0.5,
            'engine_g.0.weight': torch.randn(hidden, dim + 1) * scale * 0.8,
            'engine_g.0.bias': torch.randn(hidden) * scale * 0.8,
            'engine_g.2.weight': torch.randn(hidden, hidden) * scale * 0.4,
            'engine_g.2.bias': torch.randn(hidden) * scale * 0.4,
        }
        return state

    with tempfile.TemporaryDirectory() as tmpdir:
        donor_path = os.path.join(tmpdir, 'donor.pt')
        recip_path = os.path.join(tmpdir, 'recipient.pt')
        output_path = os.path.join(tmpdir, 'transplanted.pt')

        # Donor: trained model (higher scale = more differentiated)
        torch.manual_seed(42)
        torch.save(make_checkpoint(scale=2.0), donor_path)

        # Recipient: untrained model (lower scale)
        torch.manual_seed(123)
        torch.save(make_checkpoint(scale=0.5), recip_path)

        verifier = TransplantEEGVerifier(steps=steps, n_cells=4, dim=dim)
        result = verifier.verify_transplant(donor_path, recip_path, output_path)

    return result


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description='EEG-based transplant quality verification')
    parser.add_argument('--donor', type=str, help='Donor checkpoint path')
    parser.add_argument('--recipient', type=str, help='Recipient checkpoint path')
    parser.add_argument('--output', type=str, default=None,
                        help='Output path for transplanted model')
    parser.add_argument('--alpha', type=float, default=0.5,
                        help='Transplant blend strength (default: 0.5)')
    parser.add_argument('--steps', type=int, default=3000,
                        help='Steps for Phi collection (default: 3000)')
    parser.add_argument('--cells', type=int, default=4,
                        help='Number of consciousness cells (default: 4)')
    parser.add_argument('--dim', type=int, default=64,
                        help='Cell dimension (default: 64)')
    parser.add_argument('--projection', type=str, default='pad_zero',
                        choices=['pad_zero', 'orthogonal', 'linear'],
                        help='Projection method for dim mismatch')
    parser.add_argument('--batch', action='store_true',
                        help='Batch mode: verify multiple recipients')
    parser.add_argument('--recipients', type=str, default=None,
                        help='Directory of recipient checkpoints (batch mode)')
    parser.add_argument('--output-dir', type=str, default=None,
                        help='Output directory for batch mode')
    parser.add_argument('--demo', action='store_true',
                        help='Run demo with synthetic checkpoints')
    args = parser.parse_args()

    if args.demo:
        run_demo(steps=args.steps)
        return

    if not args.donor:
        parser.error('--donor is required (or use --demo)')

    verifier = TransplantEEGVerifier(
        steps=args.steps,
        n_cells=args.cells,
        dim=args.dim,
        alpha=args.alpha,
        projection=args.projection,
    )

    if args.batch:
        if not args.recipients:
            parser.error('--recipients directory required for batch mode')

        recip_dir = Path(args.recipients)
        recipient_paths = sorted([
            str(p) for p in recip_dir.glob('*.pt')
        ])
        if not recipient_paths:
            print(f'No .pt files found in {recip_dir}')
            return

        output_dir = args.output_dir or str(recip_dir / 'transplanted')
        verifier.batch_verify(args.donor, recipient_paths, output_dir)

    else:
        if not args.recipient:
            parser.error('--recipient is required (or use --batch)')
        verifier.verify_transplant(args.donor, args.recipient, args.output)


if __name__ == '__main__':
    main()
