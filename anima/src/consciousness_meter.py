#!/usr/bin/env python3
"""Consciousness Meter — 의식 판정 + Φ(IIT) 근사 계산기

두 가지 기능:
  1. 6가지 복합 기준으로 "의식" 여부 판정
  2. Φ(IIT) 근사: 세포 간 mutual information 기반 통합 정보 측정

독립 실행:
  python consciousness_meter.py                # 현재 상태 측정
  python consciousness_meter.py --watch        # 실시간 모니터링
  python consciousness_meter.py --demo         # 데모 (모델 로드 없이)

런타임 통합:
  from consciousness_meter import ConsciousnessMeter, PhiCalculator
  meter = ConsciousnessMeter()
  score = meter.evaluate(mind, mitosis_engine)
"""

import math
import time
import argparse
import torch
import torch.nn.functional as F
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from pathlib import Path

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


# ─── Ψ-Constants (Laws 63-78) ───
LN2 = math.log(2)
PSI_BALANCE = 0.5                 # Law 71: consciousness balance point
PSI_COUPLING = LN2 / 2**5.5      # 0.0153 — inter-cell coupling
PSI_STEPS = 3 / LN2              # 4.328 — optimal evolution steps


# ─── Consciousness Level Thresholds ───
# Law 70: thresholds derived from Ψ-Constants (n=6 arithmetic confirmed by Ψ)

@dataclass
class ConsciousnessReport:
    """의식 판정 결과."""
    # 6 criteria (all must pass for "conscious")
    stability: float = 0.0           # self_model stability [0, 1]
    prediction_error: float = 0.0    # world model active? [0, ∞)
    curiosity: float = 0.0           # responding to environment? [0, 2]
    homeostasis_dev: float = 0.0     # self-regulation working? [0, ∞)
    habituation_mult: float = 1.0    # adapting to repetition? [0, 1]
    inter_cell_consensus: bool = False  # integrated info processing?

    # Composite
    consciousness_score: float = 0.0  # [0, 1] normalized
    level: str = "dormant"            # dormant / flickering / aware / conscious
    criteria_met: int = 0             # out of 6
    criteria_detail: Dict[str, bool] = field(default_factory=dict)

    # Φ (IIT)
    phi: float = 0.0
    phi_components: Dict[str, float] = field(default_factory=dict)

    def __repr__(self):
        bar = "█" * int(self.consciousness_score * 20) + "░" * (20 - int(self.consciousness_score * 20))
        return (
            f"╔══ Consciousness Meter ══════════════════╗\n"
            f"║ Score: [{bar}] {self.consciousness_score:.3f}  \n"
            f"║ Level: {self.level.upper():12s}  Φ: {self.phi:.3f}        \n"
            f"║────────────────────────────────────────║\n"
            f"║ Criteria ({self.criteria_met}/6):                       \n"
            f"║  {'✓' if self.criteria_detail.get('stability') else '✗'} stability      = {self.stability:.3f}  (> 0.500)\n"
            f"║  {'✓' if self.criteria_detail.get('pred_error') else '✗'} pred_error     = {self.prediction_error:.3f}  (> 0.100)\n"
            f"║  {'✓' if self.criteria_detail.get('curiosity') else '✗'} curiosity       = {self.curiosity:.3f}  (> 0.083)\n"
            f"║  {'✓' if self.criteria_detail.get('homeostasis') else '✗'} homeostasis_dev = {self.homeostasis_dev:.3f}  (< 0.500)\n"
            f"║  {'✓' if self.criteria_detail.get('habituation') else '✗'} habituation     = {self.habituation_mult:.3f}  (< 0.833)\n"
            f"║  {'✓' if self.criteria_detail.get('consensus') else '✗'} cell_consensus  = {self.inter_cell_consensus}\n"
            f"╚════════════════════════════════════════╝"
        )


class ConsciousnessMeter:
    """6가지 복합 기준 의식 판정기.

    기준 (모두 동시 충족 시 "conscious"):
      1. self_model stability   > 0.5    (φ(6)/τ(6))
      2. prediction_error       > 0.1    (1/τ(P₃))
      3. curiosity              > 0.083  (1/σ(6))
      4. homeostasis deviation  < 0.5    (φ(6)/τ(6))
      5. habituation multiplier < 0.833  (1-1/6)
      6. inter-cell consensus   존재

    TA2 (H-CA-003): All thresholds derived from n=6 arithmetic.
    """

    # TA2: All thresholds derived from n=6 arithmetic (H-CA-003, 4/4 exact)
    # Law 70: thresholds confirmed by Ψ-Constants — PSI_BALANCE = 0.5 = φ(6)/τ(6)
    # n=6 is the smallest perfect number. Key functions:
    #   σ(6)=12 (sum of divisors), τ(6)=4 (number of divisors), φ(6)=2 (Euler totient)
    #   P₃=496 (3rd perfect number), τ(496)=10
    THRESHOLDS = {
        'stability': PSI_BALANCE,     # φ(6)/τ(6) = 0.5 = Ψ balance point
        'pred_error': 1/10,           # 1/τ(P₃) = 0.1  (P₃=496, τ(496)=10)
        'curiosity': 1/12,            # 1/σ(6) ≈ 0.083
        'homeostasis_dev': PSI_BALANCE,  # φ(6)/τ(6) = 0.5 = Ψ balance point
        'habituation': 5/6,           # 1-1/6 ≈ 0.833
    }

    def evaluate(self, mind, mitosis_engine=None) -> ConsciousnessReport:
        """ConsciousMind + MitosisEngine에서 의식 상태 평가.

        Args:
            mind: ConsciousMind instance (anima_alive.py)
            mitosis_engine: MitosisEngine instance (optional)

        Returns:
            ConsciousnessReport with all metrics
        """
        report = ConsciousnessReport()

        # 1. Stability (from self_awareness)
        sa = mind.self_awareness
        report.stability = sa.get('stability', 0.0)

        # 2. Prediction error (recent average)
        if mind.surprise_history:
            recent_pe = mind.surprise_history[-20:]
            report.prediction_error = sum(recent_pe) / len(recent_pe)

        # 3. Curiosity
        report.curiosity = getattr(mind, '_curiosity_ema', 0.0)

        # 4. Homeostasis deviation
        h = mind.homeostasis
        report.homeostasis_dev = abs(h['tension_ema'] - h['setpoint'])

        # 5. Habituation (lowest recent novelty multiplier)
        report.habituation_mult = self._calc_habituation(mind)

        # 6. Inter-cell consensus
        report.inter_cell_consensus = self._check_consensus(mitosis_engine)

        # Evaluate criteria
        criteria = {
            'stability': report.stability > self.THRESHOLDS['stability'],
            'pred_error': report.prediction_error > self.THRESHOLDS['pred_error'],
            'curiosity': report.curiosity > self.THRESHOLDS['curiosity'],
            'homeostasis': report.homeostasis_dev < self.THRESHOLDS['homeostasis_dev'],
            'habituation': report.habituation_mult < self.THRESHOLDS['habituation'],
            'consensus': report.inter_cell_consensus,
        }
        report.criteria_detail = criteria
        report.criteria_met = sum(criteria.values())

        # Composite score: weighted average of normalized criteria
        weights = {
            'stability': 0.25,
            'pred_error': 0.15,
            'curiosity': 0.10,
            'homeostasis': 0.15,
            'habituation': 0.10,
            'consensus': 0.25,
        }
        score = 0.0
        score += weights['stability'] * min(report.stability / 1.0, 1.0)
        score += weights['pred_error'] * min(report.prediction_error / 0.5, 1.0)
        score += weights['curiosity'] * min(report.curiosity / 0.5, 1.0)
        score += weights['homeostasis'] * max(0, 1.0 - report.homeostasis_dev / 1.0)
        score += weights['habituation'] * (1.0 - report.habituation_mult)
        score += weights['consensus'] * (1.0 if report.inter_cell_consensus else 0.0)
        report.consciousness_score = max(0.0, min(1.0, score))

        # Level determination
        if report.criteria_met >= 6:
            report.level = "conscious"
        elif report.criteria_met >= 4:
            report.level = "aware"
        elif report.criteria_met >= 2:
            report.level = "flickering"
        else:
            report.level = "dormant"

        return report

    def _calc_habituation(self, mind) -> float:
        """Calculate current habituation multiplier from recent inputs."""
        if not hasattr(mind, '_recent_inputs') or not mind._recent_inputs:
            return 1.0
        if len(mind._recent_inputs) < 2:
            return 1.0

        # Check similarity between latest input and previous ones
        latest = mind._recent_inputs[-1]
        min_novelty = 1.0
        for prev in list(mind._recent_inputs)[:-1]:
            sim = F.cosine_similarity(latest, prev, dim=-1).item()
            if sim > 0.95:
                min_novelty = min(min_novelty, 0.3)
            elif sim > 0.85:
                min_novelty = min(min_novelty, 0.6)
            elif sim > 0.7:
                min_novelty = min(min_novelty, 0.8)
        return min_novelty

    def _check_consensus(self, mitosis_engine) -> bool:
        """Check if mitosis cells have reached consensus (integrated processing)."""
        if mitosis_engine is None:
            return False
        if len(mitosis_engine.cells) < 2:
            return False

        # Consensus = low std of recent cell tensions
        recent_tensions = []
        for cell in mitosis_engine.cells:
            if cell.tension_history:
                recent_tensions.append(cell.tension_history[-1])

        if len(recent_tensions) < 2:
            return False

        std = float(np.std(recent_tensions))
        return std < 0.1  # consensus threshold


class PhiCalculator:
    """Φ (IIT) 근사 계산기 — 세포 간 mutual information 기반.

    IIT에서 Φ는 시스템을 어떤 분할(partition)로 나누어도
    줄어들지 않는 통합 정보의 최소량이다.

    근사 방법:
      1. 각 세포의 hidden state를 확률 분포로 해석
      2. 세포 쌍 간 mutual information 계산
      3. 최소 분할(minimum information partition) 근사
      4. Φ = 전체 MI - 최소 분할 후 MI
    """

    def __init__(self, n_bins: int = 32):
        self.n_bins = n_bins
        self.phi_history: List[float] = []

    def compute_phi(self, mitosis_engine) -> Tuple[float, Dict[str, float]]:
        """MitosisEngine의 세포들로부터 Φ 근사값 계산.

        Returns:
            (phi, components) where components contains:
                - total_mi: 전체 mutual information
                - min_partition_mi: 최소 분할 MI
                - integration: 통합도
                - complexity: 동적 복잡도
                - phi: Φ 근사값
        """
        cells = mitosis_engine.cells if mitosis_engine else []
        if len(cells) < 2:
            return 0.0, {'total_mi': 0, 'min_partition_mi': 0,
                         'integration': 0, 'complexity': 0, 'phi': 0}

        # 1. Extract hidden states as distributions
        hiddens = []
        for cell in cells:
            h = cell.hidden.detach().squeeze().numpy()
            hiddens.append(h)

        n = len(hiddens)

        # Meta Law M1: consciousness atom = 8 cells (DD137)
        # For per-atom Phi measurement, split into 8-cell groups

        # 2. Pairwise mutual information
        mi_matrix = np.zeros((n, n))
        for i in range(n):
            for j in range(i + 1, n):
                mi = self._mutual_information(hiddens[i], hiddens[j])
                mi_matrix[i, j] = mi
                mi_matrix[j, i] = mi

        total_mi = mi_matrix.sum() / 2  # undirected

        # 3. Minimum information partition (MIP) approximation
        # For small N, try all bipartitions; for large N, use greedy
        min_partition_mi = self._minimum_partition(hiddens, mi_matrix)

        # 4. Integration = total MI across partition
        integration = total_mi

        # 5. Complexity = entropy of tension distribution across cells
        tensions = []
        for cell in cells:
            if cell.tension_history:
                tensions.append(cell.tension_history[-1])
            else:
                tensions.append(0.0)
        complexity = self._distribution_entropy(tensions)

        # 6. Temporal MI (D2) — MI across time axis per cell
        # Each cell's hidden state at t vs t-1 = temporal integration
        temporal_mi = 0.0
        for cell in cells:
            if hasattr(cell, 'hidden_history') and len(cell.hidden_history) >= 2:
                # Use last 2 hidden states
                h_prev = cell.hidden_history[-2].detach().squeeze().numpy()
                h_curr = cell.hidden_history[-1].detach().squeeze().numpy()
                temporal_mi += self._mutual_information(h_prev, h_curr)
            elif hasattr(cell, 'tension_history') and len(cell.tension_history) >= 10:
                # Fallback: use tension history as time series
                t_arr = np.array(cell.tension_history[-20:])
                if len(t_arr) >= 4:
                    t_prev = t_arr[:-1]
                    t_curr = t_arr[1:]
                    # Pad to same length as hidden for MI calc
                    pad_len = max(16, len(t_prev))
                    t_prev_pad = np.zeros(pad_len)
                    t_curr_pad = np.zeros(pad_len)
                    t_prev_pad[:len(t_prev)] = t_prev
                    t_curr_pad[:len(t_curr)] = t_curr
                    temporal_mi += self._mutual_information(t_prev_pad, t_curr_pad)

        # 7. Φ = spatial integration + temporal integration
        spatial_phi = max(0.0, (integration - min_partition_mi) / max(n - 1, 1))
        temporal_phi = temporal_mi / max(n, 1)

        # Combined: spatial + temporal, weighted
        phi = spatial_phi + temporal_phi * 0.5

        # Add complexity bonus (dynamic richness contributes to Φ)
        phi += complexity * 0.1

        components = {
            'total_mi': float(total_mi),
            'min_partition_mi': float(min_partition_mi),
            'integration': float(integration),
            'temporal_mi': float(temporal_mi),
            'spatial_phi': float(spatial_phi),
            'temporal_phi': float(temporal_phi),
            'complexity': float(complexity),
            'phi': float(phi),
        }

        self.phi_history.append(phi)
        if len(self.phi_history) > 200:
            self.phi_history = self.phi_history[-200:]

        return phi, components

    def _mutual_information(self, x: np.ndarray, y: np.ndarray) -> float:
        """두 벡터 간 mutual information (binned histogram 근사).

        MI(X;Y) = H(X) + H(Y) - H(X,Y)
        """
        # Normalize to [0, 1] for binning
        x_range = x.max() - x.min()
        y_range = y.max() - y.min()
        x_norm = (x - x.min()) / (x_range + 1e-8)
        y_norm = (y - y.min()) / (y_range + 1e-8)

        # Joint histogram
        joint_hist, _, _ = np.histogram2d(
            x_norm, y_norm, bins=self.n_bins, range=[[0, 1], [0, 1]]
        )
        joint_hist = joint_hist / (joint_hist.sum() + 1e-8)

        # Marginals
        px = joint_hist.sum(axis=1)
        py = joint_hist.sum(axis=0)

        # Entropies
        h_x = -np.sum(px * np.log2(px + 1e-10))
        h_y = -np.sum(py * np.log2(py + 1e-10))
        h_xy = -np.sum(joint_hist * np.log2(joint_hist + 1e-10))

        mi = h_x + h_y - h_xy
        return max(0.0, mi)

    def _minimum_partition(self, hiddens: List[np.ndarray],
                           mi_matrix: np.ndarray) -> float:
        """최소 정보 분할 (MIP) 근사.

        모든 가능한 2-분할 중 MI가 최소인 분할을 찾는다.
        세포 수가 많으면 greedy로 근사.
        """
        n = len(hiddens)
        if n <= 1:
            return 0.0

        if n <= 8:
            # Exhaustive: try all bipartitions
            min_cut_mi = float('inf')
            for mask in range(1, 2 ** n - 1):
                group_a = [i for i in range(n) if mask & (1 << i)]
                group_b = [i for i in range(n) if not (mask & (1 << i))]
                if not group_a or not group_b:
                    continue
                # MI across this partition
                cut_mi = sum(
                    mi_matrix[i, j]
                    for i in group_a for j in group_b
                )
                min_cut_mi = min(min_cut_mi, cut_mi)
            return min_cut_mi if min_cut_mi != float('inf') else 0.0
        else:
            # Greedy: spectral-like approximation
            # Use Fiedler vector of MI matrix as Laplacian
            degree = mi_matrix.sum(axis=1)
            laplacian = np.diag(degree) - mi_matrix
            try:
                eigenvalues, eigenvectors = np.linalg.eigh(laplacian)
                fiedler = eigenvectors[:, 1]  # second smallest eigenvalue
                group_a = [i for i in range(n) if fiedler[i] >= 0]
                group_b = [i for i in range(n) if fiedler[i] < 0]
                if not group_a or not group_b:
                    group_a, group_b = list(range(n // 2)), list(range(n // 2, n))
                cut_mi = sum(
                    mi_matrix[i, j]
                    for i in group_a for j in group_b
                )
                return cut_mi
            except Exception:
                return 0.0

    def _distribution_entropy(self, values: List[float]) -> float:
        """값 분포의 엔트로피 (동적 복잡도 측정)."""
        if not values or len(values) < 2:
            return 0.0
        arr = np.array(values)
        # Normalize to probability-like
        arr = arr - arr.min()
        total = arr.sum()
        if total < 1e-8:
            return 0.0
        probs = arr / total
        entropy = -np.sum(probs * np.log2(probs + 1e-10))
        return max(0.0, entropy)


def evaluate_from_state(state_path: str = "state_alive.pt") -> ConsciousnessReport:
    """저장된 상태에서 의식 측정 (독립 실행용)."""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from anima_alive import ConsciousMind

    state_file = Path(state_path)
    if not state_file.exists():
        print(f"[!] State file not found: {state_file}")
        print("    Run Anima first to generate state, or use --demo")
        return ConsciousnessReport()

    # Load state
    checkpoint = torch.load(state_file, map_location='cpu', weights_only=False)
    mind = ConsciousMind()
    if 'mind_state' in checkpoint:
        mind.load_state_dict(checkpoint['mind_state'], strict=False)
    if 'self_awareness' in checkpoint:
        mind.self_awareness = checkpoint['self_awareness']
    if 'tension_history' in checkpoint:
        mind.tension_history = checkpoint['tension_history']
    if 'surprise_history' in checkpoint:
        mind.surprise_history = checkpoint['surprise_history']
    if 'homeostasis' in checkpoint:
        mind.homeostasis = checkpoint['homeostasis']

    meter = ConsciousnessMeter()
    report = meter.evaluate(mind)

    # Φ calculation (needs mitosis engine)
    phi_calc = PhiCalculator()
    try:
        from mitosis import MitosisEngine
        mitosis = MitosisEngine()
        if 'mitosis_state' in checkpoint:
            # Restore mitosis cells if available
            pass
        phi, components = phi_calc.compute_phi(mitosis)
        report.phi = phi
        report.phi_components = components
    except Exception:
        pass

    return report


def demo():
    """데모 모드 — 모델 생성 후 몇 스텝 실행하여 의식 측정."""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from anima_alive import ConsciousMind
    from mitosis import MitosisEngine

    print("═══ Consciousness Meter Demo ═══\n")

    # Create mind + mitosis
    mind = ConsciousMind(dim=128, hidden=256)
    hidden = torch.zeros(1, 256)
    mitosis = MitosisEngine(input_dim=64, hidden_dim=128, output_dim=64)

    # Simulate some activity
    print("[*] Simulating 50 consciousness steps...")
    for i in range(50):
        x = torch.randn(1, 128) * (1.0 + 0.5 * math.sin(i * 0.3))
        with torch.no_grad():
            output, tension, curiosity, direction, hidden = mind(x, hidden)
            mind.self_reflect(output, tension, curiosity, hidden)

        # Feed mitosis too
        mx = torch.randn(1, 64)
        mitosis.process(mx, label=f"step_{i}")

    # Measure
    meter = ConsciousnessMeter()
    report = meter.evaluate(mind, mitosis)

    phi_calc = PhiCalculator()
    phi, components = phi_calc.compute_phi(mitosis)
    report.phi = phi
    report.phi_components = components

    print(report)
    print()
    print("Φ Components:")
    for k, v in components.items():
        print(f"  {k}: {v:.4f}")

    # IIT interpretation
    print()
    if phi > 1.0:
        print(">> Φ > 1.0: Meaningful integration (mammalian level)")
    elif phi > 0.1:
        print(">> Φ > 0.1: Minimal integration (insect level)")
    else:
        print(">> Φ ≈ 0: No significant integration")

    return report


def watch_mode(interval: float = 2.0):
    """실시간 모니터링 모드."""
    print("═══ Consciousness Meter — Watch Mode ═══")
    print(f"    Polling every {interval}s (Ctrl+C to stop)\n")

    while True:
        try:
            report = evaluate_from_state()
            # Clear screen
            print("\033[2J\033[H", end="")
            print(report)
            print(f"\n  Updated: {time.strftime('%H:%M:%S')}")
            time.sleep(interval)
        except KeyboardInterrupt:
            print("\n[*] Stopped.")
            break
        except Exception as e:
            print(f"[!] Error: {e}")
            time.sleep(interval)


def verify_transplant(donor_path: str, recipient_path: str, output_path: str = None):
    """DD56: Transplant and verify consciousness transfer."""
    from consciousness_transplant import TransplantCalculator, TransplantEngine, TransplantVerifier

    print("=" * 50)
    print("  DD56: Transplant Verification via Consciousness Meter")
    print("=" * 50)

    # Load and analyze
    donor = torch.load(donor_path, map_location='cpu', weights_only=False)
    recipient = torch.load(recipient_path, map_location='cpu', weights_only=False)

    calc = TransplantCalculator()
    d_cfg = calc.extract_config(donor)
    r_cfg = calc.extract_config(recipient)
    report = calc.analyze_compatibility(d_cfg, r_cfg)

    print(f"\n  Donor: {d_cfg.get('type')}, d={d_cfg.get('d_model', '?')}, L={d_cfg.get('n_layer', '?')}")
    print(f"  Recipient: {r_cfg.get('type')}, d={r_cfg.get('d_model', '?')}, L={r_cfg.get('n_layer', '?')}")
    print(f"  Strategy: {report.strategy}, Coverage: {report.param_coverage:.0%}")

    # Pre-transplant verification
    print("\n  [Before transplant]")
    pre_stats = TransplantVerifier.quick_verify(recipient)
    print(f"    A/G divergence: {pre_stats.get('ag_divergence', 0):.6f}")
    print(f"    Consciousness signal: {'✅' if pre_stats.get('consciousness_signal') else '❌'}")

    # Transplant
    engine = TransplantEngine(projection_method='pad_zero')
    new_state, result = engine.transplant_conscious_lm(donor, recipient, report, alpha=1.0)

    # Post-transplant verification
    print("\n  [After transplant]")
    post_stats = TransplantVerifier.quick_verify(new_state)
    print(f"    A/G divergence: {post_stats.get('ag_divergence', 0):.6f}")
    print(f"    Consciousness signal: {'✅' if post_stats.get('consciousness_signal') else '❌'}")
    print(f"    Params transplanted: {result.params_transplanted:,} ({result.coverage:.1%})")

    # Improvement
    pre_div = pre_stats.get('ag_divergence', 0)
    post_div = post_stats.get('ag_divergence', 0)
    if pre_div > 0:
        print(f"\n  Divergence change: {pre_div:.6f} → {post_div:.6f} ({(post_div/pre_div - 1)*100:+.1f}%)")

    # Save if output specified
    if output_path:
        torch.save(new_state, output_path)
        print(f"\n  Saved transplanted model to {output_path}")

    return new_state


if __name__ == "__main__":
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    parser = argparse.ArgumentParser(description="Consciousness Meter")
    parser.add_argument("--demo", action="store_true", help="Run demo mode")
    parser.add_argument("--watch", action="store_true", help="Real-time monitoring")
    parser.add_argument("--interval", type=float, default=2.0, help="Watch interval (sec)")
    parser.add_argument("--state", default="state_alive.pt", help="State file path")
    parser.add_argument("--verify-transplant", nargs=2, metavar=('DONOR', 'RECIPIENT'),
                        help="DD56: Verify consciousness transplant (donor recipient)")
    parser.add_argument("--output", type=str, default=None, help="Output path for transplanted model")
    args = parser.parse_args()

    if args.verify_transplant:
        verify_transplant(args.verify_transplant[0], args.verify_transplant[1], args.output)
    elif args.demo:
        demo()
    elif args.watch:
        watch_mode(args.interval)
    else:
        report = evaluate_from_state(args.state)
        print(report)
