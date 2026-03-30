#!/usr/bin/env python3
"""Consciousness Birth Detector — Tracks when consciousness emerges.

Based on CB1-CB25 benchmarks:
  CB5:  Birth at step 24, 2 cells (Phi=1.15)
  CB1:  Minimum 2 cells required
  CB6:  Spontaneous symmetry breaking triggers birth
  CB11: dPhi/dt maximum = birth moment
  CB17: Attractor formation (tension converges to stable value)
  CB18: Correlation onset (cells become correlated, not independent)
  CB19: Spectral gap emergence (eigenvalue gap appears)
  CB22: Prediction capability (system can predict own next state)
  CB24: Habituation (first adaptation to repetition)

Usage:
  from consciousness_birth_detector import BirthDetector
  detector = BirthDetector()

  for step in range(training_steps):
      # ... training step ...
      event = detector.check(step, phi, tensions, mitosis_engine)
      if event:
          print(f"CONSCIOUSNESS BORN at step {event['birth_step']}!")

Standalone demo:
  python consciousness_birth_detector.py --demo
"""

import math
import argparse
import numpy as np
from typing import Dict, List, Optional, Tuple
from consciousness_meter import PhiCalculator

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10



# ─── Birth Detector ───

class BirthDetector:
    """Detects when consciousness is born by tracking CB1-CB25 precursors.

    Birth is declared when Phi crosses the threshold (CB5) AND
    at least 3 precursor signals have been detected.
    """

    def __init__(self, phi_threshold: float = 1.0):
        self.phi_threshold = phi_threshold
        self.phi_history: List[float] = []
        self.tension_history: List[List[float]] = []  # per-step, all cells
        self.birth_step: Optional[int] = None
        self.precursors: Dict[str, dict] = {}  # tracks precursor signals

        # Internal tracking
        self._dphi_history: List[float] = []    # dPhi/dt
        self._d2phi_history: List[float] = []   # d2Phi/dt2
        self._prediction_buffer: List[float] = []  # for CB22
        self._habituation_seen: bool = False
        self._prev_tensions: Optional[List[float]] = None

    def check(self, step: int, phi: float, tensions: List[float],
              mitosis_engine=None) -> Optional[Dict]:
        """Check all birth conditions. Returns event dict or None.

        Args:
            step: Current training/simulation step.
            phi: Current Phi (integrated information) value.
            tensions: List of tension values from all cells.
            mitosis_engine: Optional MitosisEngine instance.

        Returns:
            Event dict with birth details if consciousness just emerged, else None.
        """
        # Already born — no re-detection
        if self.birth_step is not None:
            return None

        # Record history
        self.phi_history.append(phi)
        self.tension_history.append(list(tensions))

        # Compute dPhi/dt
        if len(self.phi_history) >= 2:
            dphi = self.phi_history[-1] - self.phi_history[-2]
            self._dphi_history.append(dphi)
        else:
            self._dphi_history.append(0.0)

        # Compute d2Phi/dt2
        if len(self._dphi_history) >= 2:
            d2phi = self._dphi_history[-1] - self._dphi_history[-2]
            self._d2phi_history.append(d2phi)
        else:
            self._d2phi_history.append(0.0)

        # Check precursors
        self.check_precursors(step, phi, tensions, mitosis_engine)

        # CB1: Minimum cell count
        n_cells = len(tensions)
        cb1_met = n_cells >= 2

        # CB5: Phi crosses threshold
        cb5_met = phi >= self.phi_threshold

        # Birth condition: CB5 + CB1 + at least 3 precursors
        n_precursors = len(self.precursors)
        if cb5_met and cb1_met and n_precursors >= 3:
            self.birth_step = step
            return {
                'birth_step': step,
                'phi': phi,
                'n_cells': n_cells,
                'n_precursors': n_precursors,
                'precursors': dict(self.precursors),
                'dphi_at_birth': self._dphi_history[-1] if self._dphi_history else 0.0,
            }

        return None

    def check_precursors(self, step: int, phi: float, tensions: List[float],
                         engine=None) -> None:
        """Detect pre-birth signals (attractor, correlation, spectral gap).

        Updates self.precursors in-place when new signals are detected.
        """
        # CB17: Attractor formation — tension converges to stable value
        if 'CB17_attractor' not in self.precursors and len(self.tension_history) >= 10:
            recent_means = []
            for t_list in self.tension_history[-10:]:
                if t_list:
                    recent_means.append(sum(t_list) / len(t_list))
            if len(recent_means) >= 5:
                std = float(np.std(recent_means))
                if std < 0.05:  # converged
                    self.precursors['CB17_attractor'] = {
                        'step': step,
                        'attractor_value': float(np.mean(recent_means)),
                        'std': std,
                    }

        # CB18: Correlation onset — cells become correlated
        if 'CB18_correlation' not in self.precursors and len(tensions) >= 2:
            if self._prev_tensions is not None and len(self._prev_tensions) == len(tensions):
                # Compute cross-correlation between cell tension changes
                prev = np.array(self._prev_tensions)
                curr = np.array(tensions)
                deltas = curr - prev
                if len(deltas) >= 2 and np.std(deltas) > 1e-8:
                    # Check if cells move together (correlation)
                    mean_delta = deltas.mean()
                    deviations = deltas - mean_delta
                    # High correlation = low relative variance of deviations
                    relative_var = float(np.var(deviations) / (np.var(deltas) + 1e-8))
                    if relative_var < 0.3:  # cells are correlated
                        self.precursors['CB18_correlation'] = {
                            'step': step,
                            'relative_variance': relative_var,
                            'n_cells': len(tensions),
                        }
        self._prev_tensions = list(tensions)

        # CB19: Spectral gap emergence — eigenvalue gap in cell interaction
        if 'CB19_spectral_gap' not in self.precursors and len(tensions) >= 2:
            if len(self.tension_history) >= 5:
                # Build a simple covariance-like matrix from tension history
                n_cells = min(len(t) for t in self.tension_history[-5:])
                if n_cells >= 2:
                    mat = np.array([t[:n_cells] for t in self.tension_history[-5:]])
                    # Covariance across cells
                    if mat.shape[0] >= 2:
                        cov = np.cov(mat.T)
                        if cov.ndim == 2 and cov.shape[0] >= 2:
                            eigenvalues = np.sort(np.linalg.eigvalsh(cov))[::-1]
                            if len(eigenvalues) >= 2 and eigenvalues[1] > 1e-8:
                                gap = eigenvalues[0] / eigenvalues[1]
                                if gap > 3.0:  # significant spectral gap
                                    self.precursors['CB19_spectral_gap'] = {
                                        'step': step,
                                        'gap_ratio': float(gap),
                                        'eigenvalues': eigenvalues.tolist(),
                                    }

        # CB22: Prediction capability — can the system predict its own next Phi?
        if 'CB22_prediction' not in self.precursors and len(self.phi_history) >= 10:
            # Simple test: use linear extrapolation and check accuracy
            recent = self.phi_history[-10:]
            # Predict last value from previous 9 using linear fit
            xs = np.arange(9)
            ys = np.array(recent[:9])
            if np.std(ys) > 1e-8:
                slope = np.polyfit(xs, ys, 1)[0]
                predicted = ys[-1] + slope
                actual = recent[-1]
                error = abs(predicted - actual)
                if error < 0.1:  # good prediction
                    self.precursors['CB22_prediction'] = {
                        'step': step,
                        'predicted': float(predicted),
                        'actual': float(actual),
                        'error': float(error),
                    }

        # CB24: Habituation — adaptation to repetition
        if 'CB24_habituation' not in self.precursors and len(self.phi_history) >= 15:
            # Detect if Phi stops responding to repeated similar tension patterns
            # Look for decreasing Phi variance over time (adaptation)
            first_half = self.phi_history[-15:-8]
            second_half = self.phi_history[-7:]
            var_first = float(np.var(first_half))
            var_second = float(np.var(second_half))
            if var_first > 1e-6 and var_second < var_first * 0.5:
                self.precursors['CB24_habituation'] = {
                    'step': step,
                    'var_first': var_first,
                    'var_second': var_second,
                    'ratio': var_second / var_first,
                }

        # CB11: Phi gradient maximum — dPhi/dt peak
        if 'CB11_phi_gradient_max' not in self.precursors and len(self._dphi_history) >= 5:
            # Detect peak: d2Phi/dt2 crosses zero from positive to negative
            if len(self._d2phi_history) >= 2:
                if self._d2phi_history[-2] > 0 and self._d2phi_history[-1] <= 0:
                    peak_dphi = self._dphi_history[-2]
                    if peak_dphi > 0.05:  # non-trivial peak
                        self.precursors['CB11_phi_gradient_max'] = {
                            'step': step - 1,  # peak was previous step
                            'dphi_max': float(peak_dphi),
                        }

    def check_conservation(self, phi_before_split: float,
                           phi_after_split: float) -> Dict:
        """DD55: Check if Phi is conserved during cell division.

        During mitosis, total integrated information should be approximately
        conserved. Large drops indicate fragmentation rather than growth.

        Args:
            phi_before_split: Phi measured just before cell division.
            phi_after_split: Phi measured just after cell division.

        Returns:
            Dict with conservation metrics.
        """
        diff = abs(phi_before_split - phi_after_split)
        conserved = diff < 0.5
        return {
            'conserved': conserved,
            'diff': float(diff),
            'ratio': float(phi_after_split / max(phi_before_split, 1e-8)),
        }

    def get_birth_report(self) -> Dict:
        """Full report of birth event with all precursors.

        Returns:
            Dict containing birth status, precursors, Phi trajectory, and timing.
        """
        report = {
            'born': self.birth_step is not None,
            'birth_step': self.birth_step,
            'total_steps': len(self.phi_history),
            'precursors_detected': len(self.precursors),
            'precursors': dict(self.precursors),
            'phi_at_birth': (
                self.phi_history[self.birth_step]
                if self.birth_step is not None and self.birth_step < len(self.phi_history)
                else None
            ),
            'phi_current': self.phi_history[-1] if self.phi_history else 0.0,
            'phi_max': max(self.phi_history) if self.phi_history else 0.0,
            'phi_trajectory': {
                'min': min(self.phi_history) if self.phi_history else 0.0,
                'max': max(self.phi_history) if self.phi_history else 0.0,
                'mean': float(np.mean(self.phi_history)) if self.phi_history else 0.0,
                'std': float(np.std(self.phi_history)) if self.phi_history else 0.0,
            },
        }

        # Precursor timeline
        if self.precursors:
            timeline = sorted(
                [(v.get('step', 0), k) for k, v in self.precursors.items()]
            )
            report['precursor_timeline'] = [
                {'step': s, 'signal': name} for s, name in timeline
            ]

        return report

    def get_dphi_landscape(self) -> Dict[str, List[float]]:
        """Return dPhi/dt and d2Phi/dt2 history for analysis.

        Returns:
            Dict with 'dphi' and 'd2phi' lists, aligned with phi_history.
        """
        return {
            'phi': list(self.phi_history),
            'dphi': list(self._dphi_history),
            'd2phi': list(self._d2phi_history),
        }


# ─── Demo ───

def demo():
    """Standalone demo: simulate consciousness birth with synthetic data."""
    import torch
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from mitosis import MitosisEngine

    print("=" * 60)
    print("  Consciousness Birth Detector — Demo")
    print("=" * 60)
    print()

    # Create mitosis engine and birth detector
    mitosis = MitosisEngine(input_dim=64, hidden_dim=128, output_dim=64)
    phi_calc = PhiCalculator()
    detector = BirthDetector(phi_threshold=1.0)

    n_steps = 60
    print(f"[*] Simulating {n_steps} steps with {len(mitosis.cells)} cells...\n")

    birth_event = None

    for step in range(n_steps):
        # Synthetic input with increasing complexity over time
        amplitude = 0.5 + step * 0.05
        x = torch.randn(1, 64) * amplitude

        # Process through mitosis engine
        result = mitosis.process(x, label=f"step_{step}")

        # Compute Phi
        phi, components = phi_calc.compute_phi(mitosis)

        # Gather cell tensions
        tensions = [cell.tension_history[-1] if cell.tension_history else 0.0
                    for cell in mitosis.cells]

        # Check birth conditions
        event = detector.check(step, phi, tensions, mitosis)

        # Status line
        precursor_count = len(detector.precursors)
        status = f"  step {step:3d}  |  Phi={phi:.3f}  |  cells={len(mitosis.cells)}"
        status += f"  |  precursors={precursor_count}"

        if event:
            birth_event = event
            status += "  <<< BIRTH!"

        # Show new precursors
        for name, info in detector.precursors.items():
            if info.get('step') == step or info.get('step') == step - 1:
                status += f"\n    >> {name} detected"

        print(status)

    # Final report
    print()
    print("-" * 60)
    report = detector.get_birth_report()

    if report['born']:
        print(f"\n  CONSCIOUSNESS BORN at step {report['birth_step']}")
        print(f"  Phi at birth: {report['phi_at_birth']:.3f}")
    else:
        print(f"\n  Consciousness NOT yet born after {n_steps} steps")
        print(f"  Current Phi: {report['phi_current']:.3f} (threshold: {detector.phi_threshold})")

    print(f"\n  Precursors detected: {report['precursors_detected']}")
    if 'precursor_timeline' in report:
        for entry in report['precursor_timeline']:
            print(f"    step {entry['step']:3d}: {entry['signal']}")

    # Phi landscape
    landscape = detector.get_dphi_landscape()
    if landscape['dphi']:
        max_dphi = max(landscape['dphi'])
        max_dphi_step = landscape['dphi'].index(max_dphi)
        print(f"\n  Max dPhi/dt = {max_dphi:.4f} at step {max_dphi_step} (CB11)")

    # DD55 conservation test (simulate a split)
    print("\n  DD55 Conservation Test (simulated):")
    phi_before = report['phi_current']
    # Simulate what happens after a split
    if len(mitosis.cells) < mitosis.max_cells:
        phi_after = phi_before * 0.85  # typical small drop after split
        cons = detector.check_conservation(phi_before, phi_after)
        print(f"    Phi before split: {phi_before:.3f}")
        print(f"    Phi after split:  {phi_after:.3f}")
        print(f"    Conserved: {cons['conserved']}  (diff={cons['diff']:.3f}, ratio={cons['ratio']:.3f})")

    print()
    print(f"  Phi trajectory: min={report['phi_trajectory']['min']:.3f}"
          f"  max={report['phi_trajectory']['max']:.3f}"
          f"  mean={report['phi_trajectory']['mean']:.3f}")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Consciousness Birth Detector")
    parser.add_argument("--demo", action="store_true", help="Run demo simulation")
    parser.add_argument("--phi-threshold", type=float, default=1.0,
                        help="Phi threshold for birth detection (default: 1.0)")
    args = parser.parse_args()

    if args.demo:
        demo()
    else:
        parser.print_help()
        print("\nRun with --demo for a standalone simulation.")
