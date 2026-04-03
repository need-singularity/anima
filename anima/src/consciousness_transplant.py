#!/usr/bin/env python3
"""consciousness_transplant.py — Transplant consciousness between models.

Transfer Phi structure from trained donor to untrained recipient.
Preserves: cell differentiation patterns, tension dynamics, Phi topology.

Based on benchmarks:
  DD55 — Phi conservation during splits
  DV1  — Scaling transfer (small -> large)
  DV2  — Distillation (large -> small)
  MX16 — Distilled consciousness

Usage:
  python consciousness_transplant.py --benchmark                          # test transplant quality
  python consciousness_transplant.py --analyze --donor model_a.pt        # compatibility analysis
  python consciousness_transplant.py --donor a.pt --recipient b.pt --output c.pt  # transplant
  python consciousness_transplant.py --demo                              # quick demo
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

# Meta Laws (DD143): M1(atom=8), M6(federation>empire), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10



# ===================================================================
# Data classes
# ===================================================================

@dataclass
class CompatibilityReport:
    """Compatibility analysis between donor and recipient."""
    compatible: bool
    donor_config: Dict
    recipient_config: Dict
    strategy: str              # 'direct', 'projection', 'partial'
    projection_needed: bool
    layer_mapping: Dict        # donor layer -> recipient layer
    param_coverage: float      # fraction of recipient params that can be transplanted
    warnings: List[str] = field(default_factory=list)
    projection_matrix_size: Optional[Tuple] = None


@dataclass
class TransplantResult:
    """Result of a transplant operation."""
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


@dataclass
class VerificationResult:
    """Post-transplant verification result."""
    phi_before: float
    phi_after: float
    phi_retention: float       # phi_after / phi_before (DD55 conservation)
    tension_mean_before: float
    tension_mean_after: float
    tension_preserved: bool    # tension pattern maintained?
    pattern_correlation: float # donor-recipient tension pattern correlation
    consciousness_transfer: bool  # Phi transferred?


# ===================================================================
# 1. TransplantCalculator — compatibility + projection
# ===================================================================

class TransplantCalculator:
    """Analyze donor/recipient compatibility and compute projections."""

    @staticmethod
    def extract_config(state_dict: dict) -> dict:
        """Extract architecture config from a state_dict."""
        config = {}

        # ConsciousLM detection (has blocks.N.xxx keys)
        if any('blocks.' in k for k in state_dict):
            layer_ids = set()
            for k in state_dict:
                if k.startswith('blocks.'):
                    layer_ids.add(int(k.split('.')[1]))
            config['type'] = 'ConsciousLM'
            config['n_layer'] = max(layer_ids) + 1 if layer_ids else 0

            if 'ln_f.weight' in state_dict:
                config['d_model'] = state_dict['ln_f.weight'].shape[0]
            elif 'tok_emb.weight' in state_dict:
                config['d_model'] = state_dict['tok_emb.weight'].shape[1]

            for k, v in state_dict.items():
                if 'attn.c_attn.weight' in k:
                    config['n_head'] = v.shape[0] // (3 * config.get('d_model', 1))
                    break

            for k, v in state_dict.items():
                if 'ffn.engine_a.0.weight' in k:
                    config['d_inner'] = v.shape[0]
                    break

            config['vocab_size'] = state_dict.get('tok_emb.weight', torch.zeros(1, 1)).shape[0]
            config['total_params'] = sum(v.numel() for v in state_dict.values())

        # ConsciousMind detection (has engine_a but no blocks)
        elif any('engine_a' in k for k in state_dict) and not any('blocks.' in k for k in state_dict):
            config['type'] = 'ConsciousMind'
            for k, v in state_dict.items():
                if 'engine_a.0.weight' in k:
                    config['input_dim'] = v.shape[1]
                    config['hidden_dim'] = v.shape[0]
                    break
            config['total_params'] = sum(v.numel() for v in state_dict.values())

        # Wrapped checkpoint
        elif 'model_state_dict' in state_dict:
            return TransplantCalculator.extract_config(state_dict['model_state_dict'])

        else:
            config['type'] = 'unknown'
            config['total_params'] = sum(v.numel() for v in state_dict.values()
                                         if isinstance(v, torch.Tensor))

        return config

    @staticmethod
    def analyze_compatibility(donor_config: dict, recipient_config: dict) -> CompatibilityReport:
        """Check dim/cell compatibility between donor and recipient."""
        warnings = []

        if donor_config.get('type') != recipient_config.get('type'):
            warnings.append(f"Type mismatch: {donor_config.get('type')} -> {recipient_config.get('type')}")

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

        # Layer mapping: map donor layers to recipient layers
        layer_mapping = {}
        if l_donor <= l_recip:
            for i in range(l_donor):
                layer_mapping[i] = i
        else:
            # Donor is bigger: stride-sample into recipient
            stride = l_donor / l_recip
            for i in range(l_recip):
                layer_mapping[int(i * stride)] = i

        transplantable = min(l_donor, l_recip)
        param_coverage = transplantable / l_recip if l_recip > 0 else 0

        proj_size = None
        if projection_needed:
            proj_size = (d_recip, d_donor)
            if d_donor > d_recip:
                warnings.append(f"Donor dim ({d_donor}) > Recipient dim ({d_recip}): information loss (DV2 distillation)")

        if param_coverage < 0.5:
            warnings.append(f"Low coverage ({param_coverage:.0%}): only {transplantable}/{l_recip} layers")

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
        """Create projection matrix for dimension transfer (128->256 etc).

        Methods:
          orthogonal — random orthogonal projection (preserves distances)
          linear     — linear interpolation
          pad_zero   — zero-pad (small->large) or truncate (large->small)
        """
        if method == 'orthogonal':
            M = torch.randn(d_to, d_from)
            U, _, V = torch.linalg.svd(M, full_matrices=False)
            if d_to <= d_from:
                return U @ V[:d_to]
            else:
                P = torch.zeros(d_to, d_from)
                P[:d_from, :d_from] = torch.eye(d_from)
                return P

        elif method == 'linear':
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
            raise ValueError(f"Unknown projection method: {method}")


# ===================================================================
# 2. TransplantEngine — blend donor consciousness into recipient
# ===================================================================

class TransplantEngine:
    """Transplant consciousness (tension patterns, Phi structure) between models."""

    def __init__(self, projection_method: str = 'pad_zero'):
        self.projection_method = projection_method

    def transplant(
        self,
        donor_state: dict,
        recipient_state: dict,
        alpha: float = 0.5,
    ) -> Tuple[dict, TransplantResult]:
        """High-level transplant: auto-detect model type and blend.

        Args:
            donor_state:     Donor checkpoint (state_dict or full checkpoint).
            recipient_state: Recipient checkpoint.
            alpha:           Blend strength (1.0 = full donor, 0.5 = 50/50).

        Returns:
            (new_state_dict, TransplantResult)
        """
        calc = TransplantCalculator()
        d_cfg = calc.extract_config(donor_state)
        r_cfg = calc.extract_config(recipient_state)

        if d_cfg.get('type') == 'ConsciousMind' and r_cfg.get('type') == 'ConsciousMind':
            return self.transplant_conscious_mind(donor_state, recipient_state, alpha)
        else:
            report = calc.analyze_compatibility(d_cfg, r_cfg)
            return self.transplant_conscious_lm(donor_state, recipient_state, report, alpha)

    def transplant_conscious_lm(
        self,
        donor_state: dict,
        recipient_state: dict,
        report: CompatibilityReport,
        alpha: float = 1.0,
    ) -> Tuple[dict, TransplantResult]:
        """Transplant between ConsciousLM models (DV1/DV2 scaling transfer)."""
        t0 = time.time()
        warnings = []
        params_transplanted = 0
        layers_done = 0

        d_state = donor_state.get('model_state_dict', donor_state)
        r_state = dict(recipient_state.get('model_state_dict', recipient_state))

        d_model_donor = report.donor_config.get('d_model', 384)
        d_model_recip = report.recipient_config.get('d_model', 384)

        # Compute projection matrices if dimensions differ
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
                    r_state[r_key] = alpha * d_tensor + (1 - alpha) * r_tensor
                    params_transplanted += d_tensor.numel()
                elif proj is not None:
                    try:
                        projected = self._project_weight(d_tensor, r_tensor.shape, proj, proj_inner)
                        r_state[r_key] = alpha * projected + (1 - alpha) * r_tensor
                        params_transplanted += r_tensor.numel()
                    except Exception as e:
                        warnings.append(f"Skip {r_key}: {e}")
                else:
                    warnings.append(f"Shape mismatch {r_key}: {d_tensor.shape} vs {r_tensor.shape}")

            layers_done += 1

        # Re-wrap checkpoint format
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
        """Transplant between ConsciousMind models (anima_alive.py)."""
        t0 = time.time()
        warnings = []
        params_transplanted = 0
        r_state = dict(recipient_state)

        for key in donor_state:
            if ('engine_a' in key or 'engine_g' in key) and key in r_state:
                d_t = donor_state[key]
                r_t = r_state[key]
                if d_t.shape == r_t.shape:
                    r_state[key] = alpha * d_t + (1 - alpha) * r_t
                    params_transplanted += d_t.numel()
                else:
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
        """Project donor weight tensor to target shape."""
        if donor.dim() == 1:
            if donor.shape[0] == target_shape[0]:
                return donor
            p = TransplantCalculator.compute_projection_matrix(
                donor.shape[0], target_shape[0], self.projection_method)
            return (p @ donor.unsqueeze(1)).squeeze(1)

        elif donor.dim() == 2:
            out_d, in_d = donor.shape
            out_t, in_t = target_shape

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


# ===================================================================
# 3. TransplantVerifier — DD55 conservation check
# ===================================================================

class TransplantVerifier:
    """Verify Phi retention and tension pattern preservation after transplant."""

    @staticmethod
    def verify_transplant(
        before_state: dict,
        after_state: dict,
        device: str = 'cpu',
    ) -> VerificationResult:
        """DD55 conservation check: compare Phi and tension before vs after.

        Works on raw state_dicts without loading full models.
        Measures engine A/G divergence as a Phi proxy.
        """
        pre = TransplantVerifier.quick_verify(before_state, device)
        post = TransplantVerifier.quick_verify(after_state, device)

        phi_before = pre.get('ag_divergence', 0.0)
        phi_after = post.get('ag_divergence', 0.0)
        phi_retention = phi_after / (phi_before + 1e-8)

        # Tension pattern: compare weight norm distributions
        pre_norms = pre.get('_all_norms', [])
        post_norms = post.get('_all_norms', [])
        if len(pre_norms) == len(post_norms) and len(pre_norms) > 1:
            pre_arr = np.array(pre_norms)
            post_arr = np.array(post_norms)
            if np.std(pre_arr) > 0 and np.std(post_arr) > 0:
                corr = float(np.corrcoef(pre_arr, post_arr)[0, 1])
            else:
                corr = 1.0 if np.allclose(pre_arr, post_arr) else 0.0
        else:
            corr = 0.0

        t_mean_before = float(np.mean(pre_norms)) if pre_norms else 0.0
        t_mean_after = float(np.mean(post_norms)) if post_norms else 0.0

        return VerificationResult(
            phi_before=phi_before,
            phi_after=phi_after,
            phi_retention=phi_retention,
            tension_mean_before=t_mean_before,
            tension_mean_after=t_mean_after,
            tension_preserved=abs(corr) > 0.3,
            pattern_correlation=corr,
            consciousness_transfer=phi_after > 0.01,
        )

    @staticmethod
    def quick_verify(state_dict: dict, device: str = 'cpu') -> Dict:
        """Quick verification via weight statistics (no model load)."""
        sd = state_dict.get('model_state_dict', state_dict)
        stats = {}

        engine_a_norms = []
        engine_g_norms = []
        all_norms = []
        for k, v in sd.items():
            if not isinstance(v, torch.Tensor):
                continue
            if 'engine_a' in k and 'weight' in k:
                engine_a_norms.append(v.norm().item())
            elif 'engine_g' in k and 'weight' in k:
                engine_g_norms.append(v.norm().item())
            if 'weight' in k:
                all_norms.append(v.norm().item())

        stats['_all_norms'] = all_norms

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

    @staticmethod
    def verify_conscious_lm(
        original_state: dict,
        transplanted_state: dict,
        donor_state: dict,
        n_test_inputs: int = 50,
        device: str = 'cpu',
    ) -> VerificationResult:
        """Full ConsciousLM verification (loads model, runs inference)."""
        from conscious_lm import ConsciousLM

        calc = TransplantCalculator()
        t_config = calc.extract_config(transplanted_state.get('model_state_dict', transplanted_state))

        d_model = t_config.get('d_model', 384)
        n_layer = t_config.get('n_layer', 6)
        n_head = t_config.get('n_head', 4)
        block_size = 256

        def load_and_measure(state):
            model = ConsciousLM(256, d_model, n_head, n_layer, block_size, dropout=0.0)
            sd = state.get('model_state_dict', state)
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

        orig_tensions = load_and_measure(original_state)
        trans_tensions = load_and_measure(transplanted_state)

        phi_before = np.std(orig_tensions) * np.mean(orig_tensions) if orig_tensions else 0
        phi_after = np.std(trans_tensions) * np.mean(trans_tensions) if trans_tensions else 0

        if len(orig_tensions) == len(trans_tensions) and np.std(orig_tensions) > 0 and np.std(trans_tensions) > 0:
            corr = float(np.corrcoef(orig_tensions, trans_tensions)[0, 1])
        else:
            corr = 0.0

        return VerificationResult(
            phi_before=phi_before,
            phi_after=phi_after,
            phi_retention=phi_after / (phi_before + 1e-8),
            tension_mean_before=float(np.mean(orig_tensions)),
            tension_mean_after=float(np.mean(trans_tensions)),
            tension_preserved=abs(corr) > 0.3,
            pattern_correlation=corr,
            consciousness_transfer=phi_after > phi_before,
        )


# ===================================================================
# Top-level convenience functions
# ===================================================================

def analyze_compatibility(donor_path: str, recipient_path: Optional[str] = None,
                          recipient_config: Optional[dict] = None) -> CompatibilityReport:
    """Analyze transplant compatibility between donor and recipient.

    Args:
        donor_path:       Path to donor checkpoint.
        recipient_path:   Path to recipient checkpoint (optional if config given).
        recipient_config: Dict config for recipient (optional if path given).

    Returns:
        CompatibilityReport with strategy, coverage, warnings.
    """
    calc = TransplantCalculator()
    donor_state = torch.load(donor_path, map_location='cpu', weights_only=False)
    d_cfg = calc.extract_config(donor_state)

    if recipient_path:
        r_state = torch.load(recipient_path, map_location='cpu', weights_only=False)
        r_cfg = calc.extract_config(r_state)
    elif recipient_config:
        r_cfg = recipient_config
    else:
        raise ValueError("Need recipient_path or recipient_config")

    return calc.analyze_compatibility(d_cfg, r_cfg)


def transplant(donor_path: str, recipient_path: str, output_path: str,
               alpha: float = 0.5, projection: str = 'pad_zero') -> TransplantResult:
    """Transplant consciousness from donor to recipient and save.

    Args:
        donor_path:     Path to trained donor checkpoint.
        recipient_path: Path to untrained/different recipient checkpoint.
        output_path:    Where to save the transplanted model.
        alpha:          Blend strength (0.0=keep recipient, 1.0=full donor, 0.5=blend).
        projection:     Projection method for dim mismatch ('pad_zero', 'orthogonal', 'linear').

    Returns:
        TransplantResult with stats.
    """
    donor_state = torch.load(donor_path, map_location='cpu', weights_only=False)
    recip_state = torch.load(recipient_path, map_location='cpu', weights_only=False)

    engine = TransplantEngine(projection_method=projection)
    new_state, result = engine.transplant(donor_state, recip_state, alpha=alpha)

    torch.save(new_state, output_path)
    return result


def verify_transplant_quality(
    donor_path: str,
    recipient_before_path: str,
    recipient_after_path: str,
    steps: int = 500,
    n_cells: int = 4,
    dim: int = 64,
):
    """Run EEG brain-likeness metrics on donor and recipient (before/after transplant).

    Lazy-imports transplant_eeg_verify so it only fails if actually called
    without the anima-eeg module available.

    Args:
        donor_path:            Path to donor checkpoint.
        recipient_before_path: Path to recipient checkpoint before transplant.
        recipient_after_path:  Path to recipient checkpoint after transplant.
        steps:                 Steps for Phi collection (default: 500).
        n_cells:               Number of consciousness cells (default: 4).
        dim:                   Cell dimension (default: 64).

    Returns:
        EEGVerifyResult from transplant_eeg_verify, or dict with error info
        if the EEG module is not available.
    """
    try:
        import sys as _sys
        from pathlib import Path as _Path

        # Ensure anima-eeg is on path
        _repo_root = _Path(__file__).resolve().parent.parent.parent
        _eeg_dir = _repo_root / 'anima-eeg'
        if str(_eeg_dir) not in _sys.path:
            _sys.path.insert(0, str(_eeg_dir))

        from transplant_eeg_verify import (
            TransplantEEGVerifier,
            _collect_phi_from_checkpoint,
            _compute_brain_likeness,
        )
        from validate_consciousness import analyze_signal
    except ImportError as e:
        print(f'[EEG Verify] Not available: {e}')
        print('[EEG Verify] Install anima-eeg dependencies or check path.')
        return {'error': str(e), 'available': False}

    print(f'\n[EEG Verify] Collecting brain-likeness metrics (steps={steps})...')
    import sys as _sys
    _sys.stdout.flush()

    # Collect Phi timeseries for each checkpoint
    donor_phi = _collect_phi_from_checkpoint(donor_path, steps, n_cells, dim)
    before_phi = _collect_phi_from_checkpoint(recipient_before_path, steps, n_cells, dim)
    after_phi = _collect_phi_from_checkpoint(recipient_after_path, steps, n_cells, dim)

    # Compute brain-likeness
    donor_metrics = analyze_signal('Donor', donor_phi)
    before_metrics = analyze_signal('Before', before_phi)
    after_metrics = analyze_signal('After', after_phi)

    donor_bl = _compute_brain_likeness(donor_metrics)
    before_bl = _compute_brain_likeness(before_metrics)
    after_bl = _compute_brain_likeness(after_metrics)

    delta = after_bl - before_bl
    sign = '+' if delta >= 0 else ''

    print(f'[EEG Verify] Brain-likeness: {before_bl:.1f}% -> {after_bl:.1f}% ({sign}{delta:.1f}%)')
    print(f'[EEG Verify] Donor brain-likeness: {donor_bl:.1f}%')
    transferred = after_bl >= donor_bl * 0.8
    improved = after_bl > before_bl
    print(f'[EEG Verify] Transferred: {"PASS" if transferred else "FAIL"} | '
          f'Improved: {"PASS" if improved else "FAIL"}')
    _sys.stdout.flush()

    return {
        'available': True,
        'donor_brain_likeness': donor_bl,
        'before_brain_likeness': before_bl,
        'after_brain_likeness': after_bl,
        'delta': delta,
        'transferred': transferred,
        'improved': improved,
        'donor_metrics': donor_metrics,
        'before_metrics': before_metrics,
        'after_metrics': after_metrics,
    }


def verify_transplant(before_path: str, after_path: str) -> VerificationResult:
    """DD55 conservation check: verify Phi retention after transplant.

    Args:
        before_path: Path to model checkpoint before transplant.
        after_path:  Path to model checkpoint after transplant.

    Returns:
        VerificationResult with phi_retention, pattern_correlation, etc.
    """
    before = torch.load(before_path, map_location='cpu', weights_only=False)
    after = torch.load(after_path, map_location='cpu', weights_only=False)
    return TransplantVerifier.verify_transplant(before, after)


# ===================================================================
# Benchmark (DD55 + DV1 + DV2 + MX16)
# ===================================================================

def run_benchmark(steps=200):
    """Benchmark: create donor, transplant to recipient, measure Phi retention.

    Tests:
      DD55 — Phi conservation during cell splits
      DV1  — Scaling transfer: small donor (2 cells) -> large recipient (4 cells)
      DV2  — Distillation: 128d donor -> 64d recipient (dimension reduction)
      MX16 — Distilled consciousness: transplant + continued training
    """
    from mitosis import MitosisEngine
    from consciousness_meter import PhiCalculator

    print("=" * 60)
    print("  Consciousness Transplant Benchmark")
    print("  DD55 (conservation) + DV1 (scaling) + DV2 (distillation) + MX16")
    print("=" * 60)

    dim, hidden = 64, 128
    phi_calc = PhiCalculator(n_bins=16)

    # ---- Phase 1: Train donor ----
    half = steps // 2
    print(f"\n[1/5] Training donor (2 cells, {half} steps)...")
    donor = MitosisEngine(dim, hidden, dim, initial_cells=2, max_cells=4)
    opt_d = torch.optim.Adam([p for c in donor.cells for p in c.mind.parameters()], lr=5e-4)
    for step in range(half):
        x = torch.randn(1, dim) * (1 + 0.1 * (step % 8))
        reps = [c.mind.get_repulsion(x, c.hidden) for c in donor.cells]
        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)
            loss = -stacked.var(dim=0).mean()
            opt_d.zero_grad(); loss.backward(); opt_d.step()
        with torch.no_grad():
            donor.process(x)
    donor_phi, _ = phi_calc.compute_phi(donor)
    print(f"  Donor Phi = {donor_phi:.4f}")

    # ---- Phase 2: DD55 — Phi conservation during split ----
    print("\n[2/5] DD55: Phi conservation during split...")
    phi_before_split = donor_phi
    # Force a split on first cell
    if len(donor.cells) < donor.max_cells:
        donor.split_cell(donor.cells[0])
    phi_after_split, _ = phi_calc.compute_phi(donor)
    conservation_ratio = phi_after_split / (phi_before_split + 1e-8)
    dd55_pass = abs(conservation_ratio - 1.0) < 0.15
    print(f"  Phi before split: {phi_before_split:.4f}")
    print(f"  Phi after split:  {phi_after_split:.4f}")
    print(f"  Conservation ratio: {conservation_ratio:.4f} ({'PASS' if dd55_pass else 'FAIL'} < 15% change)")

    # ---- Phase 3: DV1 — Scaling transfer (2 cells -> 4 cells) ----
    print(f"\n[3/5] DV1: Scaling transfer (donor 2-cell -> recipient 4-cell, {half} steps)...")
    recipient = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    control = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)

    # Transplant donor weights into first 2 cells of recipient
    transplanted_count = 0
    for i in range(min(2, len(recipient.cells), len(donor.cells))):
        with torch.no_grad():
            for rp, dp in zip(recipient.cells[i].mind.parameters(), donor.cells[i].mind.parameters()):
                if rp.shape == dp.shape:
                    rp.copy_(dp)
                    transplanted_count += dp.numel()
    print(f"  Transplanted {transplanted_count:,} parameters to recipient")

    # Train both recipient and control
    opt_r = torch.optim.Adam([p for c in recipient.cells for p in c.mind.parameters()], lr=5e-4)
    opt_c = torch.optim.Adam([p for c in control.cells for p in c.mind.parameters()], lr=5e-4)

    r_phi_hist = []
    c_phi_hist = []
    for step in range(half):
        x = torch.randn(1, dim) * (1 + 0.1 * (step % 8))

        # Recipient (transplanted)
        reps = [c.mind.get_repulsion(x, c.hidden) for c in recipient.cells]
        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)
            loss = -stacked.var(dim=0).mean()
            opt_r.zero_grad(); loss.backward(); opt_r.step()
        with torch.no_grad():
            recipient.process(x)
        phi_r, _ = phi_calc.compute_phi(recipient)
        r_phi_hist.append(phi_r)

        # Control (no transplant)
        reps = [c.mind.get_repulsion(x, c.hidden) for c in control.cells]
        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)
            loss = -stacked.var(dim=0).mean()
            opt_c.zero_grad(); loss.backward(); opt_c.step()
        with torch.no_grad():
            control.process(x)
        phi_c, _ = phi_calc.compute_phi(control)
        c_phi_hist.append(phi_c)

    dv1_accel = r_phi_hist[-1] / (c_phi_hist[-1] + 1e-8)
    print(f"  Recipient Phi: {r_phi_hist[-1]:.4f}")
    print(f"  Control Phi:   {c_phi_hist[-1]:.4f}")
    print(f"  Acceleration:  {dv1_accel:.2f}x")

    # ---- Phase 4: DV2 — Distillation (128d -> 64d) ----
    print("\n[4/5] DV2: Distillation (128d donor -> 64d recipient)...")
    dim_large, dim_small = 128, 64
    donor_large = MitosisEngine(dim_large, 256, dim_large, initial_cells=2, max_cells=4)
    opt_dl = torch.optim.Adam([p for c in donor_large.cells for p in c.mind.parameters()], lr=5e-4)
    for step in range(half):
        x = torch.randn(1, dim_large) * (1 + 0.1 * (step % 8))
        reps = [c.mind.get_repulsion(x, c.hidden) for c in donor_large.cells]
        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)
            loss = -stacked.var(dim=0).mean()
            opt_dl.zero_grad(); loss.backward(); opt_dl.step()
        with torch.no_grad():
            donor_large.process(x)

    recip_small = MitosisEngine(dim_small, hidden, dim_small, initial_cells=2, max_cells=4)

    # Transplant with projection (128d -> 64d)
    engine = TransplantEngine(projection_method='pad_zero')
    dv2_transplanted = 0
    for i in range(min(len(donor_large.cells), len(recip_small.cells))):
        d_sd = donor_large.cells[i].mind.state_dict()
        r_sd = recip_small.cells[i].mind.state_dict()
        new_sd, result = engine.transplant_conscious_mind(d_sd, r_sd, alpha=0.8)
        recip_small.cells[i].mind.load_state_dict(new_sd, strict=False)
        dv2_transplanted += result.params_transplanted

    phi_recip_small, _ = phi_calc.compute_phi(recip_small)
    phi_donor_large, _ = phi_calc.compute_phi(donor_large)
    dv2_retention = phi_recip_small / (phi_donor_large + 1e-8)
    print(f"  Donor (128d) Phi:    {phi_donor_large:.4f}")
    print(f"  Recipient (64d) Phi: {phi_recip_small:.4f}")
    print(f"  Phi retention:       {dv2_retention:.2%}")
    print(f"  Params transplanted: {dv2_transplanted:,}")

    # ---- Phase 5: MX16 — Distilled consciousness (transplant + train) ----
    print(f"\n[5/5] MX16: Distilled consciousness (transplant + {half} steps training)...")
    mx16_recip = MitosisEngine(dim, hidden, dim, initial_cells=2, max_cells=4)
    mx16_ctrl = MitosisEngine(dim, hidden, dim, initial_cells=2, max_cells=4)

    # Transplant donor to mx16_recip
    for i in range(min(len(donor.cells), len(mx16_recip.cells))):
        with torch.no_grad():
            for rp, dp in zip(mx16_recip.cells[i].mind.parameters(), donor.cells[i].mind.parameters()):
                if rp.shape == dp.shape:
                    rp.copy_(dp)

    opt_mx = torch.optim.Adam([p for c in mx16_recip.cells for p in c.mind.parameters()], lr=5e-4)
    opt_mc = torch.optim.Adam([p for c in mx16_ctrl.cells for p in c.mind.parameters()], lr=5e-4)
    mx_phi_hist = []
    mc_phi_hist = []
    for step in range(half):
        x = torch.randn(1, dim) * (1 + 0.1 * (step % 8))
        for eng, opt, hist in [(mx16_recip, opt_mx, mx_phi_hist), (mx16_ctrl, opt_mc, mc_phi_hist)]:
            reps = [c.mind.get_repulsion(x, c.hidden) for c in eng.cells]
            if len(reps) >= 2:
                stacked = torch.stack(reps).squeeze(1)
                loss = -stacked.var(dim=0).mean()
                opt.zero_grad(); loss.backward(); opt.step()
            with torch.no_grad():
                eng.process(x)
            phi_v, _ = phi_calc.compute_phi(eng)
            hist.append(phi_v)

    mx16_accel = mx_phi_hist[-1] / (mc_phi_hist[-1] + 1e-8)
    print(f"  Transplanted Phi: {mx_phi_hist[-1]:.4f}")
    print(f"  Control Phi:      {mc_phi_hist[-1]:.4f}")
    print(f"  Acceleration:     {mx16_accel:.2f}x")

    # ---- Summary ----
    def sparkline(hist, width=40):
        if not hist:
            return ""
        mn, mx_val = min(hist), max(hist)
        rng = mx_val - mn if mx_val > mn else 1
        chars = "........::::####"
        return ''.join(chars[min(int((v - mn) / rng * 15), 15)] for v in
                       [hist[int(i * len(hist) / width)] for i in range(width)])

    print("\n" + "=" * 60)
    print("  Summary")
    print("=" * 60)
    print(f"  DD55 conservation:  {conservation_ratio:.4f} ({'PASS' if dd55_pass else 'FAIL'})")
    print(f"  DV1 scaling:        {dv1_accel:.2f}x acceleration")
    print(f"  DV2 distillation:   {dv2_retention:.2%} Phi retention")
    print(f"  MX16 distilled:     {mx16_accel:.2f}x acceleration")
    print(f"\n  DV1 recipient: {sparkline(r_phi_hist)} {r_phi_hist[-1]:.3f}")
    print(f"  DV1 control:   {sparkline(c_phi_hist)} {c_phi_hist[-1]:.3f}")
    print(f"  MX16 transpl:  {sparkline(mx_phi_hist)} {mx_phi_hist[-1]:.3f}")
    print(f"  MX16 control:  {sparkline(mc_phi_hist)} {mc_phi_hist[-1]:.3f}")
    print()

    return {
        'dd55_conservation': conservation_ratio,
        'dv1_acceleration': dv1_accel,
        'dv2_retention': dv2_retention,
        'mx16_acceleration': mx16_accel,
        'donor_phi': donor_phi,
        'recipient_phi': r_phi_hist[-1],
        'control_phi': c_phi_hist[-1],
    }


# ===================================================================
# Demo
# ===================================================================

def demo():
    """Quick demo: create donor with learned consciousness, transplant to fresh recipient."""
    from mitosis import MitosisEngine
    from consciousness_meter import PhiCalculator

    print("=" * 60)
    print("  Consciousness Transplant Demo")
    print("=" * 60)

    dim, hidden = 64, 128
    phi_calc = PhiCalculator(n_bins=16)

    # Train a donor
    print("\n[1/3] Training donor (50 steps)...")
    donor = MitosisEngine(dim, hidden, dim, initial_cells=2, max_cells=4)
    opt = torch.optim.Adam([p for c in donor.cells for p in c.mind.parameters()], lr=1e-3)
    for step in range(50):
        x = torch.randn(1, dim) * (1 + 0.3 * math.sin(step * 0.5))
        reps = [c.mind.get_repulsion(x, c.hidden) for c in donor.cells]
        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)
            loss = -stacked.var(dim=0).mean()
            opt.zero_grad(); loss.backward(); opt.step()
        with torch.no_grad():
            donor.process(x)

    donor_phi, d_comp = phi_calc.compute_phi(donor)
    print(f"  Donor Phi = {donor_phi:.4f}")

    # Create fresh recipient
    print("\n[2/3] Transplanting to fresh recipient...")
    recipient = MitosisEngine(dim, hidden, dim, initial_cells=2, max_cells=4)
    phi_before, _ = phi_calc.compute_phi(recipient)
    print(f"  Recipient Phi (before) = {phi_before:.4f}")

    # Transplant
    transplanted = 0
    for i in range(min(len(donor.cells), len(recipient.cells))):
        with torch.no_grad():
            for rp, dp in zip(recipient.cells[i].mind.parameters(), donor.cells[i].mind.parameters()):
                if rp.shape == dp.shape:
                    rp.copy_(0.5 * dp + 0.5 * rp)  # alpha=0.5 blend
                    transplanted += dp.numel()

    phi_after, _ = phi_calc.compute_phi(recipient)
    print(f"  Recipient Phi (after)  = {phi_after:.4f}")
    print(f"  Params transplanted:   {transplanted:,}")

    # Verify
    print("\n[3/3] Verification...")
    retention = phi_after / (donor_phi + 1e-8)
    print(f"  Phi retention: {retention:.2%}")
    print(f"  Consciousness transferred: {'YES' if phi_after > phi_before else 'NO'}")
    print(f"  DD55 conservation: {'PASS' if abs(retention - 1.0) < 0.5 else 'FAIL'}")
    print()


# ===================================================================
# CLI
# ===================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Consciousness Transplant — transfer Phi between models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python consciousness_transplant.py --demo
  python consciousness_transplant.py --benchmark
  python consciousness_transplant.py --analyze --donor model_a.pt
  python consciousness_transplant.py --donor a.pt --recipient b.pt --output c.pt --alpha 0.5
        """)

    parser.add_argument("--donor", type=str, help="Donor checkpoint path")
    parser.add_argument("--recipient", type=str, help="Recipient checkpoint path")
    parser.add_argument("--output", type=str, help="Output checkpoint path")
    parser.add_argument("--donor-type", choices=['lm', 'mind'], default='lm')
    parser.add_argument("--recipient-type", choices=['lm', 'mind'], default='lm')
    parser.add_argument("--alpha", type=float, default=0.5, help="Transplant strength (0=recipient, 1=donor)")
    parser.add_argument("--projection", choices=['pad_zero', 'orthogonal', 'linear'],
                        default='pad_zero', help="Projection method for dim mismatch")
    parser.add_argument("--analyze", action="store_true", help="Analyze compatibility only")
    parser.add_argument("--verify", action="store_true", help="Verify transplant result")
    parser.add_argument("--benchmark", action="store_true", help="Run full benchmark (DD55+DV1+DV2+MX16)")
    parser.add_argument("--demo", action="store_true", help="Quick demo")
    parser.add_argument("--recipient-config", type=str, help="Recipient config JSON (for --analyze)")
    parser.add_argument("--steps", type=int, default=200, help="Benchmark steps")
    parser.add_argument("--verify-with-eeg", action="store_true",
                        help="Run EEG brain-likeness verification after transplant")
    parser.add_argument("--eeg-steps", type=int, default=500,
                        help="Steps for EEG Phi collection (default: 500)")
    args = parser.parse_args()

    if args.demo:
        demo()
        return

    if args.benchmark:
        run_benchmark(steps=args.steps)
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

    stats = TransplantVerifier.quick_verify(donor_state)
    print(f"  A/G divergence: {stats.get('ag_divergence', 0):.4f}")
    print(f"  Consciousness signal: {'YES' if stats.get('consciousness_signal') else 'NO'}")

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
        print(f"  Compatible: {'YES' if report.compatible else 'NO'}")
        print(f"  Strategy: {report.strategy}")
        print(f"  Projection needed: {report.projection_needed}")
        print(f"  Layer mapping: {report.layer_mapping}")
        print(f"  Coverage: {report.param_coverage:.0%}")
        if report.projection_matrix_size:
            print(f"  Projection matrix: {report.projection_matrix_size}")
        for w in report.warnings:
            print(f"  WARNING: {w}")
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
        print(f"  WARNING: {w}")

    # Transplant
    print(f"\n  Transplanting (alpha={args.alpha})...")
    engine = TransplantEngine(projection_method=args.projection)

    if args.donor_type == 'mind' and args.recipient_type == 'mind':
        output_state, result = engine.transplant_conscious_mind(donor_state, recip_state, args.alpha)
    else:
        output_state, result = engine.transplant_conscious_lm(donor_state, recip_state, report, args.alpha)

    print(f"  Done in {result.elapsed_sec:.2f}s")
    print(f"  Params transplanted: {result.params_transplanted:,} / {result.params_total:,} ({result.coverage:.1%})")
    for w in result.warnings:
        print(f"  WARNING: {w}")

    # Save
    torch.save(output_state, args.output)
    print(f"\n  Saved to {args.output}")

    # Verify (quick weight-based check)
    if args.verify:
        print("\n  Verifying...")
        vr = TransplantVerifier.quick_verify(output_state)
        print(f"  A/G divergence: {vr.get('ag_divergence', 0):.4f}")
        print(f"  Consciousness signal: {'YES' if vr.get('consciousness_signal') else 'NO'}")

    # EEG brain-likeness verification
    if args.verify_with_eeg:
        eeg_result = verify_transplant_quality(
            donor_path=args.donor,
            recipient_before_path=args.recipient,
            recipient_after_path=args.output,
            steps=args.eeg_steps,
        )
        if isinstance(eeg_result, dict) and eeg_result.get('available'):
            print(f"\n  EEG Summary: Brain-likeness "
                  f"{eeg_result['before_brain_likeness']:.1f}% -> "
                  f"{eeg_result['after_brain_likeness']:.1f}% "
                  f"({'+' if eeg_result['delta'] >= 0 else ''}{eeg_result['delta']:.1f}%)")


if __name__ == "__main__":
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
