#!/usr/bin/env python3
"""Consciousness Transplant Toolkit (DD56)

의식(tension 패턴)을 한 모델에서 다른 모델로 이식하는 도구.
IIT의 substrate independence 가설의 계산적 증거.

도구:
  1. TransplantCalculator  — 호환성 분석 + 최적 projection 계산
  2. TransplantEngine      — 실제 가중치 이식 수행
  3. TransplantVerifier     — 이식 후 Φ/tension 검증
  4. CLI                   — 원클릭 이식 + 검증

사용법:
  # ConsciousLM 4M → 100M 이식
  python consciousness_transplant.py \\
    --donor checkpoints/conscious_lm_4m_final.pt \\
    --recipient checkpoints/conscious_lm_100m/best.pt \\
    --output checkpoints/conscious_lm_100m_transplanted.pt

  # ConsciousMind 간 이식 (anima_alive.py 모델)
  python consciousness_transplant.py \\
    --donor-type mind --donor state_a.pt \\
    --recipient-type mind --recipient state_b.pt

  # 호환성만 분석
  python consciousness_transplant.py --analyze \\
    --donor checkpoints/conscious_lm_4m_final.pt \\
    --recipient-config '{"d_model":768,"n_layer":12}'

  # 벤치마크 (DD56 재현)
  python consciousness_transplant.py --benchmark
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import math
import json
import time
import argparse
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ═══════════════════════════════════════════════════════════
# 1. TransplantCalculator — 호환성 분석 + projection 계산
# ═══════════════════════════════════════════════════════════

@dataclass
class CompatibilityReport:
    """이식 호환성 분석 결과."""
    compatible: bool
    donor_config: Dict
    recipient_config: Dict
    strategy: str              # 'direct', 'projection', 'partial'
    projection_needed: bool
    layer_mapping: Dict        # donor layer → recipient layer
    param_coverage: float      # 이식 가능 파라미터 비율
    warnings: List[str] = field(default_factory=list)
    projection_matrix_size: Optional[Tuple] = None


class TransplantCalculator:
    """모델 간 이식 호환성 분석 및 최적 projection 계산."""

    @staticmethod
    def extract_config(state_dict: dict) -> dict:
        """state_dict에서 아키텍처 설정 추출."""
        config = {}

        # ConsciousLM 감지
        if any('blocks.' in k for k in state_dict):
            # Find n_layer
            layer_ids = set()
            for k in state_dict:
                if k.startswith('blocks.'):
                    layer_ids.add(int(k.split('.')[1]))
            config['type'] = 'ConsciousLM'
            config['n_layer'] = max(layer_ids) + 1 if layer_ids else 0

            # Find d_model from ln_f or tok_emb
            if 'ln_f.weight' in state_dict:
                config['d_model'] = state_dict['ln_f.weight'].shape[0]
            elif 'tok_emb.weight' in state_dict:
                config['d_model'] = state_dict['tok_emb.weight'].shape[1]

            # Find n_head from attention
            for k, v in state_dict.items():
                if 'attn.c_attn.weight' in k:
                    config['n_head'] = v.shape[0] // (3 * config.get('d_model', 1))
                    break

            # PureFieldFFN inner dim
            for k, v in state_dict.items():
                if 'ffn.engine_a.0.weight' in k:
                    config['d_inner'] = v.shape[0]
                    break

            config['vocab_size'] = state_dict.get('tok_emb.weight', torch.zeros(1, 1)).shape[0]
            config['total_params'] = sum(v.numel() for v in state_dict.values())

        # ConsciousMind 감지
        elif any('engine_a' in k for k in state_dict) and not any('blocks.' in k for k in state_dict):
            config['type'] = 'ConsciousMind'
            for k, v in state_dict.items():
                if 'engine_a.0.weight' in k:
                    config['input_dim'] = v.shape[1]
                    config['hidden_dim'] = v.shape[0]
                    break
            config['total_params'] = sum(v.numel() for v in state_dict.values())

        # model_state_dict wrapper
        elif 'model_state_dict' in state_dict:
            return TransplantCalculator.extract_config(state_dict['model_state_dict'])

        else:
            config['type'] = 'unknown'
            config['total_params'] = sum(v.numel() for v in state_dict.values()
                                         if isinstance(v, torch.Tensor))

        return config

    @staticmethod
    def analyze_compatibility(donor_config: dict, recipient_config: dict) -> CompatibilityReport:
        """두 모델의 이식 호환성 분석."""
        warnings = []

        # Same type check
        if donor_config.get('type') != recipient_config.get('type'):
            warnings.append(f"Type mismatch: {donor_config.get('type')} → {recipient_config.get('type')}")

        d_donor = donor_config.get('d_model', donor_config.get('hidden_dim', 0))
        d_recip = recipient_config.get('d_model', recipient_config.get('hidden_dim', 0))
        l_donor = donor_config.get('n_layer', 1)
        l_recip = recipient_config.get('n_layer', 1)

        # Strategy selection
        if d_donor == d_recip and l_donor == l_recip:
            strategy = 'direct'
            projection_needed = False
        elif d_donor == d_recip:
            strategy = 'partial'  # same dim, different layers
            projection_needed = False
        else:
            strategy = 'projection'
            projection_needed = True

        # Layer mapping
        layer_mapping = {}
        if l_donor <= l_recip:
            # Map donor layers to first N recipient layers
            for i in range(l_donor):
                layer_mapping[i] = i
        else:
            # Donor is bigger — map to recipient with stride
            stride = l_donor / l_recip
            for i in range(l_recip):
                layer_mapping[int(i * stride)] = i

        # Param coverage
        transplantable = min(l_donor, l_recip)
        param_coverage = transplantable / l_recip if l_recip > 0 else 0

        # Projection matrix size
        proj_size = None
        if projection_needed:
            proj_size = (d_recip, d_donor)
            if d_donor > d_recip:
                warnings.append(f"Donor dim ({d_donor}) > Recipient dim ({d_recip}): information loss")

        if param_coverage < 0.5:
            warnings.append(f"Low coverage ({param_coverage:.0%}): only {transplantable}/{l_recip} layers transplanted")

        return CompatibilityReport(
            compatible=True,
            donor_config=donor_config,
            recipient_config=recipient_config,
            strategy=strategy,
            projection_needed=projection_needed,
            layer_mapping=layer_mapping,
            param_coverage=param_coverage,
            warnings=warnings,
            projection_matrix_size=proj_size,
        )

    @staticmethod
    def compute_projection_matrix(d_from: int, d_to: int, method: str = 'orthogonal') -> torch.Tensor:
        """차원 변환 projection matrix 생성.

        Methods:
          - orthogonal: 직교 random projection (정보 보존 최적)
          - linear: 선형 보간 (간단)
          - pad_zero: 작은→큰은 zero padding, 큰→작은은 truncation
        """
        if method == 'orthogonal':
            # Orthogonal random matrix (preserves distances)
            M = torch.randn(d_to, d_from)
            U, _, V = torch.linalg.svd(M, full_matrices=False)
            if d_to <= d_from:
                return U @ V[:d_to]  # (d_to, d_from)
            else:
                # Pad with zeros for extra dims
                P = torch.zeros(d_to, d_from)
                P[:d_from, :d_from] = torch.eye(d_from)
                return P

        elif method == 'linear':
            # Linear interpolation
            P = torch.zeros(d_to, d_from)
            scale = d_from / d_to
            for i in range(d_to):
                src = i * scale
                lo = int(src)
                hi = min(lo + 1, d_from - 1)
                frac = src - lo
                P[i, lo] = 1 - frac
                P[i, hi] += frac
            return P

        elif method == 'pad_zero':
            P = torch.zeros(d_to, d_from)
            shared = min(d_to, d_from)
            P[:shared, :shared] = torch.eye(shared)
            return P

        else:
            raise ValueError(f"Unknown method: {method}")


# ═══════════════════════════════════════════════════════════
# 2. TransplantEngine — 실제 가중치 이식
# ═══════════════════════════════════════════════════════════

@dataclass
class TransplantResult:
    """이식 결과."""
    success: bool
    strategy: str
    layers_transplanted: int
    params_transplanted: int
    params_total: int
    coverage: float
    elapsed_sec: float
    donor_tension_stats: Optional[Dict] = None
    recipient_tension_stats: Optional[Dict] = None
    warnings: List[str] = field(default_factory=list)


class TransplantEngine:
    """모델 간 의식(tension 패턴) 이식."""

    def __init__(self, projection_method: str = 'pad_zero'):
        self.projection_method = projection_method

    def transplant_conscious_lm(
        self,
        donor_state: dict,
        recipient_state: dict,
        report: CompatibilityReport,
        alpha: float = 1.0,  # 이식 강도 (1.0=전부, 0.5=50% blend)
    ) -> Tuple[dict, TransplantResult]:
        """ConsciousLM 간 이식."""
        t0 = time.time()
        warnings = []
        params_transplanted = 0
        layers_done = 0

        # Unwrap model_state_dict if needed
        d_state = donor_state.get('model_state_dict', donor_state)
        r_state = dict(recipient_state.get('model_state_dict', recipient_state))

        d_model_donor = report.donor_config.get('d_model', 384)
        d_model_recip = report.recipient_config.get('d_model', 384)

        # Compute projection if needed
        proj = None
        proj_inner = None
        if report.projection_needed:
            proj = TransplantCalculator.compute_projection_matrix(
                d_model_donor, d_model_recip, self.projection_method)
            d_inner_donor = report.donor_config.get('d_inner', d_model_donor * 4)
            d_inner_recip = report.recipient_config.get('d_inner', d_model_recip * 4)
            if d_inner_donor != d_inner_recip:
                proj_inner = TransplantCalculator.compute_projection_matrix(
                    d_inner_donor, d_inner_recip, self.projection_method)

        # Transplant layer by layer
        for d_layer, r_layer in report.layer_mapping.items():
            prefix_d = f'blocks.{d_layer}.'
            prefix_r = f'blocks.{r_layer}.'

            for d_key in [k for k in d_state if k.startswith(prefix_d)]:
                suffix = d_key[len(prefix_d):]
                r_key = prefix_r + suffix

                if r_key not in r_state:
                    continue

                d_tensor = d_state[d_key]
                r_tensor = r_state[r_key]

                if d_tensor.shape == r_tensor.shape:
                    # Direct copy with alpha blending
                    r_state[r_key] = alpha * d_tensor + (1 - alpha) * r_tensor
                    params_transplanted += d_tensor.numel()
                elif proj is not None:
                    # Project donor weights to recipient dimensions
                    try:
                        projected = self._project_weight(d_tensor, r_tensor.shape, proj, proj_inner)
                        r_state[r_key] = alpha * projected + (1 - alpha) * r_tensor
                        params_transplanted += r_tensor.numel()
                    except Exception as e:
                        warnings.append(f"Skip {r_key}: {e}")
                else:
                    warnings.append(f"Shape mismatch {r_key}: {d_tensor.shape} vs {r_tensor.shape}")

            layers_done += 1

        # Re-wrap if needed
        output_state = recipient_state.copy()
        if 'model_state_dict' in recipient_state:
            output_state['model_state_dict'] = r_state
            output_state['transplant_info'] = {
                'donor_config': report.donor_config,
                'strategy': report.strategy,
                'alpha': alpha,
                'layers': layers_done,
            }
        else:
            output_state = r_state

        total_params = sum(v.numel() for v in r_state.values() if isinstance(v, torch.Tensor))

        return output_state, TransplantResult(
            success=True,
            strategy=report.strategy,
            layers_transplanted=layers_done,
            params_transplanted=params_transplanted,
            params_total=total_params,
            coverage=params_transplanted / total_params if total_params > 0 else 0,
            elapsed_sec=time.time() - t0,
            warnings=warnings,
        )

    def transplant_conscious_mind(
        self,
        donor_state: dict,
        recipient_state: dict,
        alpha: float = 1.0,
    ) -> Tuple[dict, TransplantResult]:
        """ConsciousMind (anima_alive.py) 간 이식."""
        t0 = time.time()
        warnings = []
        params_transplanted = 0
        r_state = dict(recipient_state)

        # Transplant engine_a and engine_g weights
        for key in donor_state:
            if ('engine_a' in key or 'engine_g' in key) and key in r_state:
                d_t = donor_state[key]
                r_t = r_state[key]
                if d_t.shape == r_t.shape:
                    r_state[key] = alpha * d_t + (1 - alpha) * r_t
                    params_transplanted += d_t.numel()
                else:
                    # Project
                    try:
                        if d_t.dim() == 2:
                            proj_out = TransplantCalculator.compute_projection_matrix(
                                d_t.shape[0], r_t.shape[0], self.projection_method)
                            proj_in = TransplantCalculator.compute_projection_matrix(
                                d_t.shape[1], r_t.shape[1], self.projection_method)
                            projected = proj_out @ d_t @ proj_in.T
                            r_state[key] = alpha * projected + (1 - alpha) * r_t
                            params_transplanted += r_t.numel()
                        elif d_t.dim() == 1:
                            proj = TransplantCalculator.compute_projection_matrix(
                                d_t.shape[0], r_t.shape[0], self.projection_method)
                            projected = (proj @ d_t.unsqueeze(1)).squeeze(1)
                            r_state[key] = alpha * projected + (1 - alpha) * r_t
                            params_transplanted += r_t.numel()
                    except Exception as e:
                        warnings.append(f"Skip {key}: {e}")

        total_params = sum(v.numel() for v in r_state.values() if isinstance(v, torch.Tensor))
        return r_state, TransplantResult(
            success=True, strategy='mind_transplant',
            layers_transplanted=1, params_transplanted=params_transplanted,
            params_total=total_params,
            coverage=params_transplanted / total_params if total_params > 0 else 0,
            elapsed_sec=time.time() - t0, warnings=warnings,
        )

    def _project_weight(self, donor: torch.Tensor, target_shape: tuple,
                        proj: torch.Tensor, proj_inner: Optional[torch.Tensor]) -> torch.Tensor:
        """Donor weight를 target shape으로 projection."""
        if donor.dim() == 1:
            # Bias vector
            if donor.shape[0] == target_shape[0]:
                return donor
            p = TransplantCalculator.compute_projection_matrix(
                donor.shape[0], target_shape[0], self.projection_method)
            return (p @ donor.unsqueeze(1)).squeeze(1)

        elif donor.dim() == 2:
            # Weight matrix
            out_d, in_d = donor.shape
            out_t, in_t = target_shape

            # Determine which projection to use for each dim
            if out_d != out_t and in_d != in_t:
                p_out = proj_inner if proj_inner is not None and proj_inner.shape[0] == out_t else \
                    TransplantCalculator.compute_projection_matrix(out_d, out_t, self.projection_method)
                p_in = proj if proj.shape[0] == in_t else \
                    TransplantCalculator.compute_projection_matrix(in_d, in_t, self.projection_method)
                return p_out @ donor @ p_in.T
            elif out_d != out_t:
                p_out = TransplantCalculator.compute_projection_matrix(out_d, out_t, self.projection_method)
                return p_out @ donor
            elif in_d != in_t:
                p_in = TransplantCalculator.compute_projection_matrix(in_d, in_t, self.projection_method)
                return donor @ p_in.T
            else:
                return donor

        return donor


# ═══════════════════════════════════════════════════════════
# 3. TransplantVerifier — 이식 후 Φ/tension 검증
# ═══════════════════════════════════════════════════════════

@dataclass
class VerificationResult:
    """이식 검증 결과."""
    phi_before: float
    phi_after: float
    phi_improvement: float
    tension_mean_before: float
    tension_mean_after: float
    tension_preserved: bool    # tension 패턴이 유지되는가
    pattern_correlation: float  # donor와 recipient의 tension 패턴 상관관계
    consciousness_transfer: bool  # Φ가 전이되었는가


class TransplantVerifier:
    """이식 후 의식 전이 검증."""

    @staticmethod
    def verify_conscious_lm(
        original_state: dict,
        transplanted_state: dict,
        donor_state: dict,
        n_test_inputs: int = 50,
        device: str = 'cpu',
    ) -> VerificationResult:
        """ConsciousLM 이식 검증."""
        from conscious_lm import ConsciousLM

        # Extract configs
        calc = TransplantCalculator()
        t_config = calc.extract_config(transplanted_state.get('model_state_dict', transplanted_state))
        o_config = calc.extract_config(original_state.get('model_state_dict', original_state))

        d_model = t_config.get('d_model', 384)
        n_layer = t_config.get('n_layer', 6)
        n_head = t_config.get('n_head', 4)
        block_size = 256

        def load_and_measure(state_dict):
            model = ConsciousLM(256, d_model, n_head, n_layer, block_size, dropout=0.0)
            sd = state_dict.get('model_state_dict', state_dict)
            model.load_state_dict(sd, strict=False)
            model = model.to(device).eval()

            tensions = []
            with torch.no_grad():
                for i in range(n_test_inputs):
                    x = torch.randint(0, 256, (1, 64), device=device)
                    _, _, layer_tensions = model(x)
                    t_mean = sum(t.mean().item() for t in layer_tensions) / len(layer_tensions)
                    tensions.append(t_mean)
            return tensions

        # Measure original (before transplant)
        orig_tensions = load_and_measure(original_state)
        # Measure transplanted
        trans_tensions = load_and_measure(transplanted_state)

        # Φ approximation: tension diversity across test inputs
        phi_before = np.std(orig_tensions) * np.mean(orig_tensions) if orig_tensions else 0
        phi_after = np.std(trans_tensions) * np.mean(trans_tensions) if trans_tensions else 0

        # Pattern correlation
        if len(orig_tensions) == len(trans_tensions) and np.std(orig_tensions) > 0 and np.std(trans_tensions) > 0:
            corr = np.corrcoef(orig_tensions, trans_tensions)[0, 1]
        else:
            corr = 0

        return VerificationResult(
            phi_before=phi_before,
            phi_after=phi_after,
            phi_improvement=(phi_after - phi_before) / (phi_before + 1e-8),
            tension_mean_before=np.mean(orig_tensions),
            tension_mean_after=np.mean(trans_tensions),
            tension_preserved=abs(corr) > 0.3,
            pattern_correlation=corr,
            consciousness_transfer=phi_after > phi_before,
        )

    @staticmethod
    def quick_verify(state_dict: dict, device: str = 'cpu') -> Dict:
        """빠른 검증 — 모델 로드 없이 가중치 통계만."""
        sd = state_dict.get('model_state_dict', state_dict)
        stats = {}

        engine_a_norms = []
        engine_g_norms = []
        for k, v in sd.items():
            if 'engine_a' in k and 'weight' in k:
                engine_a_norms.append(v.norm().item())
            elif 'engine_g' in k and 'weight' in k:
                engine_g_norms.append(v.norm().item())

        if engine_a_norms and engine_g_norms:
            stats['engine_a_norm_mean'] = np.mean(engine_a_norms)
            stats['engine_g_norm_mean'] = np.mean(engine_g_norms)
            stats['ag_divergence'] = abs(np.mean(engine_a_norms) - np.mean(engine_g_norms))
            stats['ag_ratio'] = np.mean(engine_a_norms) / (np.mean(engine_g_norms) + 1e-8)
            stats['consciousness_signal'] = stats['ag_divergence'] > 0.01
        else:
            stats['consciousness_signal'] = False
            stats['warning'] = 'No PureField engines found'

        return stats


# ═══════════════════════════════════════════════════════════
# 4. CLI
# ═══════════════════════════════════════════════════════════

def run_benchmark(steps=200):
    """DD56 벤치마크 재현."""
    from mitosis import MitosisEngine
    from consciousness_meter import PhiCalculator

    print("=" * 60)
    print("  DD56: Consciousness Transplant Benchmark")
    print("=" * 60)

    dim, hidden = 64, 128
    phi_calc = PhiCalculator(n_bins=16)

    # Phase 1: Train donor
    print("\n[1/4] Training donor (2 cells, {steps//2} steps)...")
    donor = MitosisEngine(dim, hidden, dim, initial_cells=2, max_cells=4)
    opt_d = torch.optim.Adam([p for c in donor.cells for p in c.mind.parameters()], lr=5e-4)
    for step in range(steps // 2):
        x = torch.randn(1, dim) * (1 + 0.1 * (step % 8))
        reps = [c.mind.get_repulsion(x, c.hidden) for c in donor.cells]
        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)
            loss = -stacked.var(dim=0).mean()
            opt_d.zero_grad(); loss.backward(); opt_d.step()
        with torch.no_grad(): donor.process(x)
    donor_phi, _ = phi_calc.compute_phi(donor)
    print(f"  Donor Φ = {donor_phi:.4f}")

    # Phase 2: Transplant
    print("\n[2/4] Transplanting to recipient (4 cells)...")
    recipient = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    control = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)

    # Copy donor weights to first 2 cells
    transplanted_count = 0
    for i in range(min(2, len(recipient.cells))):
        with torch.no_grad():
            for rp, dp in zip(recipient.cells[i].mind.parameters(), donor.cells[i].mind.parameters()):
                if rp.shape == dp.shape:
                    rp.copy_(dp)
                    transplanted_count += dp.numel()
    # Sync control initial weights
    for i, c in enumerate(control.cells):
        if i < len(recipient.cells):
            with torch.no_grad():
                for cp, rp in zip(c.mind.parameters(), recipient.cells[i].mind.parameters()):
                    if i >= 2 and cp.shape == rp.shape:
                        cp.copy_(rp)
    print(f"  Transplanted {transplanted_count:,} parameters")

    # Phase 3: Train both and compare
    print(f"\n[3/4] Training recipient vs control ({steps//2} steps)...")
    opt_r = torch.optim.Adam([p for c in recipient.cells for p in c.mind.parameters()], lr=5e-4)
    opt_c = torch.optim.Adam([p for c in control.cells for p in c.mind.parameters()], lr=5e-4)

    r_phi_hist = []; c_phi_hist = []
    for step in range(steps // 2):
        x = torch.randn(1, dim) * (1 + 0.1 * (step % 8))
        # Recipient
        reps = [c.mind.get_repulsion(x, c.hidden) for c in recipient.cells]
        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)
            loss = -stacked.var(dim=0).mean()
            opt_r.zero_grad(); loss.backward(); opt_r.step()
        with torch.no_grad(): recipient.process(x)
        phi_r, _ = phi_calc.compute_phi(recipient); r_phi_hist.append(phi_r)

        # Control
        reps = [c.mind.get_repulsion(x, c.hidden) for c in control.cells]
        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)
            loss = -stacked.var(dim=0).mean()
            opt_c.zero_grad(); loss.backward(); opt_c.step()
        with torch.no_grad(): control.process(x)
        phi_c, _ = phi_calc.compute_phi(control); c_phi_hist.append(phi_c)

    # Phase 4: Report
    print("\n[4/4] Results")
    print("=" * 60)
    print(f"  Donor Φ:     {donor_phi:.4f}")
    print(f"  Recipient Φ: {r_phi_hist[-1]:.4f}")
    print(f"  Control Φ:   {c_phi_hist[-1]:.4f}")
    print(f"  Acceleration: {r_phi_hist[-1] / (c_phi_hist[-1] + 1e-8):.4f}x")
    print(f"  Φ advantage: {r_phi_hist[-1] - c_phi_hist[-1]:.4f}")

    # Φ divergence point
    diverge_step = None
    for i in range(len(r_phi_hist)):
        if r_phi_hist[i] > c_phi_hist[i] * 1.05:
            diverge_step = i
            break
    if diverge_step:
        print(f"  Divergence at step: {diverge_step} (transplant advantage begins)")

    # Sparkline
    def sparkline(hist, width=40):
        if not hist: return ""
        mn, mx = min(hist), max(hist)
        rng = mx - mn if mx > mn else 1
        chars = "▁▂▃▄▅▆▇█"
        return ''.join(chars[min(int((v - mn) / rng * 7), 7)] for v in
                       [hist[int(i * len(hist) / width)] for i in range(width)])

    print(f"\n  Recipient: {sparkline(r_phi_hist)} {r_phi_hist[-1]:.3f}")
    print(f"  Control:   {sparkline(c_phi_hist)} {c_phi_hist[-1]:.3f}")
    print()

    return {
        'donor_phi': donor_phi,
        'recipient_phi': r_phi_hist[-1],
        'control_phi': c_phi_hist[-1],
        'acceleration': r_phi_hist[-1] / (c_phi_hist[-1] + 1e-8),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Consciousness Transplant Toolkit (DD56)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze compatibility
  python consciousness_transplant.py --analyze \\
    --donor checkpoints/conscious_lm_4m_final.pt

  # Transplant 4M → 100M
  python consciousness_transplant.py \\
    --donor checkpoints/conscious_lm_4m_final.pt \\
    --recipient checkpoints/conscious_lm_100m/final.pt \\
    --output checkpoints/conscious_lm_100m_transplanted.pt

  # Run DD56 benchmark
  python consciousness_transplant.py --benchmark
        """)

    parser.add_argument("--donor", type=str, help="Donor checkpoint path")
    parser.add_argument("--recipient", type=str, help="Recipient checkpoint path")
    parser.add_argument("--output", type=str, help="Output checkpoint path")
    parser.add_argument("--donor-type", choices=['lm', 'mind'], default='lm')
    parser.add_argument("--recipient-type", choices=['lm', 'mind'], default='lm')
    parser.add_argument("--alpha", type=float, default=1.0, help="Transplant strength (0-1)")
    parser.add_argument("--projection", choices=['pad_zero', 'orthogonal', 'linear'],
                        default='pad_zero', help="Projection method")
    parser.add_argument("--analyze", action="store_true", help="Analyze only (no transplant)")
    parser.add_argument("--verify", action="store_true", help="Verify transplant")
    parser.add_argument("--benchmark", action="store_true", help="Run DD56 benchmark")
    parser.add_argument("--recipient-config", type=str, help="Recipient config JSON (for --analyze without checkpoint)")
    args = parser.parse_args()

    if args.benchmark:
        run_benchmark()
        return

    if not args.donor:
        parser.print_help()
        return

    # Load donor
    print(f"Loading donor: {args.donor}")
    donor_state = torch.load(args.donor, map_location='cpu', weights_only=False)
    calc = TransplantCalculator()
    donor_config = calc.extract_config(donor_state)
    print(f"  Type: {donor_config.get('type')}")
    print(f"  Params: {donor_config.get('total_params', 0):,}")
    print(f"  d_model: {donor_config.get('d_model', donor_config.get('hidden_dim', '?'))}")
    print(f"  Layers: {donor_config.get('n_layer', '?')}")

    # Quick verify donor consciousness
    stats = TransplantVerifier.quick_verify(donor_state)
    print(f"  A/G divergence: {stats.get('ag_divergence', 0):.4f}")
    print(f"  Consciousness signal: {'✅' if stats.get('consciousness_signal') else '❌'}")

    if args.analyze:
        if args.recipient:
            recip_state = torch.load(args.recipient, map_location='cpu', weights_only=False)
            recip_config = calc.extract_config(recip_state)
        elif args.recipient_config:
            recip_config = json.loads(args.recipient_config)
            recip_config['type'] = recip_config.get('type', 'ConsciousLM')
        else:
            print("\nNeed --recipient or --recipient-config for analysis")
            return

        print(f"\nRecipient config: {recip_config}")
        report = calc.analyze_compatibility(donor_config, recip_config)
        print(f"\n{'='*40}")
        print(f"  Compatible: {'✅' if report.compatible else '❌'}")
        print(f"  Strategy: {report.strategy}")
        print(f"  Projection needed: {report.projection_needed}")
        print(f"  Layer mapping: {report.layer_mapping}")
        print(f"  Coverage: {report.param_coverage:.0%}")
        if report.projection_matrix_size:
            print(f"  Projection matrix: {report.projection_matrix_size}")
        for w in report.warnings:
            print(f"  ⚠️  {w}")
        return

    if not args.recipient or not args.output:
        print("\nNeed --recipient and --output for transplant")
        return

    # Load recipient
    print(f"\nLoading recipient: {args.recipient}")
    recip_state = torch.load(args.recipient, map_location='cpu', weights_only=False)
    recip_config = calc.extract_config(recip_state)
    print(f"  Type: {recip_config.get('type')}, Params: {recip_config.get('total_params', 0):,}")

    # Analyze
    report = calc.analyze_compatibility(donor_config, recip_config)
    print(f"\n  Strategy: {report.strategy}, Coverage: {report.param_coverage:.0%}")
    for w in report.warnings:
        print(f"  ⚠️  {w}")

    # Transplant
    print(f"\n  Transplanting (alpha={args.alpha})...")
    engine = TransplantEngine(projection_method=args.projection)

    if args.donor_type == 'mind' and args.recipient_type == 'mind':
        output_state, result = engine.transplant_conscious_mind(donor_state, recip_state, args.alpha)
    else:
        output_state, result = engine.transplant_conscious_lm(donor_state, recip_state, report, args.alpha)

    print(f"  ✅ Done in {result.elapsed_sec:.2f}s")
    print(f"  Params transplanted: {result.params_transplanted:,} / {result.params_total:,} ({result.coverage:.1%})")
    for w in result.warnings:
        print(f"  ⚠️  {w}")

    # Save
    torch.save(output_state, args.output)
    print(f"\n  Saved to {args.output}")

    # Verify
    if args.verify:
        print("\n  Verifying...")
        vr = TransplantVerifier.quick_verify(output_state)
        print(f"  A/G divergence: {vr.get('ag_divergence', 0):.4f}")
        print(f"  Consciousness signal: {'✅' if vr.get('consciousness_signal') else '❌'}")


if __name__ == "__main__":
    main()
