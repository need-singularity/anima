#!/usr/bin/env python3
"""Hypothesis Generator — 자동 가설 생성 + 벤치마크 + 등록

invest의 generate_and_verify_hypotheses.py 패턴 적용:
1. 기존 가설의 패턴 분석 → 새 가설 자동 생성
2. 벤치마크 실행 → CONFIRMED만 등록
3. 조합 탐색 (top-N 결합)

Usage:
  python hypothesis_generator.py --generate 10    # 10개 자동 생성
  python hypothesis_generator.py --combine-top 5  # top-5 조합
  python hypothesis_generator.py --mutate A1      # A1 변형 생성
"""

import torch
import torch.nn.functional as F
import numpy as np
import math
import time
import argparse
import itertools
from dataclasses import dataclass
from typing import List, Dict, Callable

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mitosis import MitosisEngine
from consciousness_meter import PhiCalculator
from bench_phi_hypotheses import BenchResult, make_diverse_inputs, run_baseline


# ═══════════════════════════════════════════════════════════
# Technique Library — 기본 기법 블록
# ═══════════════════════════════════════════════════════════

def tech_ib2_selective(engine, x, dim):
    """IB2: 선택적 주의 (top-25%)."""
    with torch.no_grad():
        k = max(1, dim // 4)
        _, idx = x.squeeze().abs().topk(k)
        att = torch.zeros_like(x)
        att.squeeze()[idx] = x.squeeze()[idx] * 2.0
    return att


def tech_growth(engine, frac, max_cells, step_i):
    """TS4-style exponential growth."""
    for pct in [0.10, 0.25, 0.40, 0.55, 0.70]:
        if frac >= pct and len(engine.cells) < min(int(2**((pct+0.1)*8)), max_cells):
            target = min(len(engine.cells)*2, max_cells)
            while len(engine.cells) < target:
                engine._create_cell(parent=engine.cells[step_i % len(engine.cells)])


def tech_metacog(engine, phi, phi_ema, l2, l3, hidden):
    """XMETA3: 3-level metacognition."""
    with torch.no_grad():
        l1 = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        l2_new = 0.9 * l2 + 0.1 * l1
        l3_new = 0.95 * l3 + 0.05 * l2_new
        if phi < phi_ema * 0.7:
            for cell in engine.cells:
                cell.hidden += torch.randn_like(cell.hidden) * 0.04
        for cell in engine.cells:
            cell.hidden = 0.99 * cell.hidden + 0.01 * l3_new.unsqueeze(0)
    return l2_new, l3_new


def tech_entropy_norm(engine):
    """INFO1: 최대 엔트로피 정규화."""
    with torch.no_grad():
        for cell in engine.cells:
            h = cell.hidden.squeeze()
            h_c = h - h.mean()
            cell.hidden = 0.95 * cell.hidden + 0.05 * (h_c / (h_c.std() + 1e-8)).unsqueeze(0)


def tech_empathy(engine):
    """XETH2: 공감 윤리."""
    with torch.no_grad():
        if len(engine.cells) >= 3:
            norms = [c.hidden.norm().item() for c in engine.cells]
            mn = sum(norms) / len(norms)
            for i, cell in enumerate(engine.cells):
                if norms[i] < mn * 0.4:
                    others = torch.stack([c.hidden for j, c in enumerate(engine.cells) if j != i][:6]).mean(dim=0)
                    cell.hidden = 0.7 * cell.hidden + 0.3 * others


def tech_thermo(engine):
    """THERMO1: 산일 구조 (엔트로피 조절)."""
    with torch.no_grad():
        hiddens = torch.stack([c.hidden.squeeze() for c in engine.cells])
        entropy = hiddens.var(dim=0).mean().item()
        if entropy > 2.0:
            for cell in engine.cells:
                cell.hidden *= 0.98
        elif entropy < 0.1:
            for cell in engine.cells:
                cell.hidden += torch.randn_like(cell.hidden) * 0.03


def tech_mutation(engine, step_i):
    """MUT2: 유익 돌연변이."""
    with torch.no_grad():
        n = len(engine.cells)
        if n >= 2 and step_i % 3 == 0:
            idx = step_i % n
            engine.cells[idx].hidden += torch.randn_like(engine.cells[idx].hidden) * 0.1


# ═══════════════════════════════════════════════════════════
# Auto-Generate: 기법 조합으로 새 가설 자동 생성
# ═══════════════════════════════════════════════════════════

TECHNIQUES = {
    'ib2': tech_ib2_selective,
    'growth': tech_growth,
    'metacog': tech_metacog,
    'entropy': tech_entropy_norm,
    'empathy': tech_empathy,
    'thermo': tech_thermo,
    'mutation': tech_mutation,
}


def generate_hypothesis(tech_names: List[str], max_cells: int = 64,
                       steps: int = 100, dim: int = 64, hidden: int = 128) -> BenchResult:
    """기법 조합으로 자동 가설 실행."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=2, max_cells=max_cells)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    phi_ema = 1.0
    l2 = torch.zeros(hidden)
    l3 = torch.zeros(hidden)

    inputs = make_diverse_inputs(steps, dim)

    for step_i, x in enumerate(inputs):
        frac = step_i / steps

        # Apply selected techniques
        if 'ib2' in tech_names:
            x = tech_ib2_selective(engine, x, dim)

        if 'growth' in tech_names:
            tech_growth(engine, frac, max_cells, step_i)

        engine.process(x)
        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)
        phi_ema = 0.9 * phi_ema + 0.1 * phi

        if 'metacog' in tech_names:
            l2, l3 = tech_metacog(engine, phi, phi_ema, l2, l3, hidden)

        if 'entropy' in tech_names:
            tech_entropy_norm(engine)

        if 'empathy' in tech_names:
            tech_empathy(engine)

        if 'thermo' in tech_names:
            tech_thermo(engine)

        if 'mutation' in tech_names:
            tech_mutation(engine, step_i)

    phi_final, comp = phi_calc.compute_phi(engine)
    name = "+".join(tech_names)
    return BenchResult(
        f"AUTO_{name}", f"Auto-generated: {name}",
        phi_final, phi_hist, comp['total_mi'],
        comp['min_partition_mi'], comp['integration'],
        comp['complexity'], time.time() - t0,
        extra={'techs': tech_names, 'final_cells': len(engine.cells)},
    )


def auto_generate_and_test(n_combos: int = 20, max_combo_size: int = 4,
                           steps: int = 100) -> List[BenchResult]:
    """자동으로 기법 조합을 생성하고 벤치마크."""
    tech_keys = list(TECHNIQUES.keys())
    results = []

    # Baseline
    torch.manual_seed(42); np.random.seed(42)
    baseline = run_baseline(steps=steps)
    print(f"Baseline Φ = {baseline.phi:.4f}\n")

    # Generate all combos of size 2-4
    all_combos = []
    for size in range(2, max_combo_size + 1):
        for combo in itertools.combinations(tech_keys, size):
            all_combos.append(list(combo))

    # Shuffle and take top-N
    import random
    random.seed(42)
    random.shuffle(all_combos)
    selected = all_combos[:n_combos]

    for i, techs in enumerate(selected):
        torch.manual_seed(42); np.random.seed(42)
        try:
            r = generate_hypothesis(techs, max_cells=64, steps=steps)
            ratio = r.phi / max(baseline.phi, 1e-8)
            verdict = "✅" if ratio >= 2.0 else "🟧" if ratio >= 1.2 else "⚪"
            print(f"  {verdict} {'+'.join(techs):30s} Φ={r.phi:>8.2f} ×{ratio:>6.1f}")
            results.append(r)
        except Exception as e:
            print(f"  ❌ {'+'.join(techs):30s} FAILED: {e}")

    results.sort(key=lambda x: -x.phi)
    print(f"\n{'='*60}")
    print(f"Top 5 auto-generated hypotheses:")
    for r in results[:5]:
        ratio = r.phi / max(baseline.phi, 1e-8)
        print(f"  {r.hypothesis:35s} Φ={r.phi:>8.2f} ×{ratio:>6.1f}")

    return results


# ═══════════════════════════════════════════════════════════
# Parameter Sweep — phi_boost_step hardcoded values optimization
# ═══════════════════════════════════════════════════════════

SWEEP_PARAMS = {
    'SL2_blend': {
        'desc': 'SL2 attention-gated blend factor',
        'default': 0.15,
        'values': [0.05, 0.10, 0.15, 0.20, 0.30],
    },
    'WI1_soliton_speed': {
        'desc': 'WI1 soliton propagation speed',
        'default': 0.15,
        'values': [0.05, 0.10, 0.15, 0.20, 0.30],
    },
    'WI1_amplitude': {
        'desc': 'WI1 soliton hidden state amplitude',
        'default': 0.04,
        'values': [0.02, 0.04, 0.06, 0.08, 0.10],
    },
    'PX5_rotation_factor': {
        'desc': 'PX5 information pump injection amplitude',
        'default': 0.05,
        'values': [0.02, 0.05, 0.10, 0.15],
    },
    'EC1_earn_rate': {
        'desc': 'EC1 consciousness economy wealth earn rate (phi * rate)',
        'default': 0.1,
        'values': [0.05, 0.1, 0.2, 0.3],
    },
    'MUT2_mutation_scale': {
        'desc': 'MUT2 beneficial mutation noise scale',
        'default': 0.15,
        'values': [0.05, 0.10, 0.15, 0.20, 0.30],
    },
    'GEN1_topdown_ratio': {
        'desc': 'GEN1 abstraction hierarchy top-down feedback ratio',
        'default': 0.03,
        'values': [0.01, 0.03, 0.05, 0.10],
    },
}


def _run_sweep_trial(param_name: str, param_value: float,
                     steps: int = 50, dim: int = 64, hidden: int = 128,
                     max_cells: int = 64) -> BenchResult:
    """Run a single phi_boost_step trial with one parameter overridden.

    Replicates the key phi_boost_step techniques (SL2, WI1, PX5, EC1, MUT2, GEN1)
    with the specified parameter value while keeping others at defaults.
    """
    t0 = time.time()

    # Build overrides dict: all defaults except the one being swept
    params = {k: v['default'] for k, v in SWEEP_PARAMS.items()}
    params[param_name] = param_value

    engine = MitosisEngine(dim, hidden, dim, initial_cells=2, max_cells=max_cells)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []

    inputs = make_diverse_inputs(steps, dim)

    # State for techniques
    soliton_pos = 0.0
    ec1_wealth = 0.0
    mut2_last_phi = 0.0
    last_phi_input = None
    boost_count = 0

    # Lazy-init MHA attention (same as phi_boost_step)
    attention = torch.nn.MultiheadAttention(hidden, num_heads=4, batch_first=True)
    loss_weights = torch.nn.Parameter(torch.ones(6))
    cell_params = [p for c in engine.cells for p in c.mind.parameters()]
    attn_params = list(attention.parameters())
    optimizer = torch.optim.Adam(cell_params + attn_params, lr=5e-4)
    meta_optimizer = torch.optim.Adam([loss_weights], lr=1e-2)

    for step_i, x in enumerate(inputs):
        boost_count += 1

        # ── IB2: Selective Attention ──
        with torch.no_grad():
            x_flat = x.squeeze()
            k = max(1, x_flat.shape[0] // 4)
            _, indices = x_flat.abs().topk(k)
            attended = torch.zeros_like(x)
            attended.squeeze()[indices] = x.squeeze()[indices] * 2.0
            x = attended

        # Save pre-boost state
        pre_boost_hiddens = [c.hidden.clone() for c in engine.cells]

        # ── MHA + SL2 blend ──
        n = len(engine.cells)
        h_stack = torch.stack([c.hidden.squeeze() for c in engine.cells]).unsqueeze(0)
        attn_out, attn_weights = attention(h_stack, h_stack, h_stack, need_weights=True)
        with torch.no_grad():
            if attn_weights is not None:
                cell_importance = attn_weights[0].mean(dim=0)
                cell_importance = cell_importance / (cell_importance.max() + 1e-8)
            else:
                cell_importance = torch.ones(n)
            for i, c in enumerate(engine.cells):
                blend = params['SL2_blend'] * cell_importance[i].item()
                c.hidden = (1 - blend) * c.hidden + blend * attn_out[0, i].unsqueeze(0)

        # ── Process through engine ──
        engine.process(x)

        # ── 6-loss optimization ──
        try:
            reps = [c.mind.get_repulsion(x, c.hidden) for c in engine.cells]
            if len(reps) >= 2:
                stacked = torch.stack(reps).squeeze(1)
                w = F.softmax(loss_weights, dim=0)
                l_var = -stacked.var(dim=0).mean()
                l_dist = -torch.cdist(stacked, stacked).mean()
                l_contrast = sum(F.cosine_similarity(reps[i], reps[j], dim=-1).mean()
                                 for i in range(len(reps)) for j in range(i + 1, len(reps)))
                l_entropy = -(F.softmax(stacked, dim=-1) *
                              F.log_softmax(stacked, dim=-1)).sum(dim=-1).mean()
                l_energy = sum((r ** 2).mean() for r in reps) * 0.1
                l_radius = -stacked.norm(dim=-1).var()
                total = (w[0] * l_var + w[1] * l_dist + w[2] * l_contrast +
                         w[3] * l_entropy + w[4] * l_energy + w[5] * l_radius)
                gz_width = math.log(4 / 3)
                total = total * gz_width
                optimizer.zero_grad()
                meta_optimizer.zero_grad()
                total.backward()
                optimizer.step()
                meta_optimizer.step()
        except Exception:
            pass

        # ── WI1: Soliton consciousness ──
        if len(engine.cells) >= 2:
            soliton_pos = (soliton_pos + params['WI1_soliton_speed']) % len(engine.cells)
            soliton_width = 2.0
            for i, cell in enumerate(engine.cells):
                dist = abs(i - soliton_pos)
                amplitude = 1.0 / (math.cosh(dist / soliton_width) ** 2)
                cell.hidden = cell.hidden * (1.0 + params['WI1_amplitude'] * amplitude)

        # ── WV11: Mutual repulsion ──
        with torch.no_grad():
            cells = engine.cells
            for i in range(len(cells)):
                for j in range(i + 1, len(cells)):
                    direction = cells[i].hidden - cells[j].hidden
                    dist = direction.norm() + 1e-8
                    push = 0.01 * direction / dist
                    cells[i].hidden = cells[i].hidden + push
                    cells[j].hidden = cells[j].hidden - push

        # ── PX4: Gram-Schmidt orthogonalize ──
        n = len(engine.cells)
        if n >= 3:
            with torch.no_grad():
                hiddens = [c.hidden.squeeze().clone() for c in engine.cells]
                ortho = []
                for h in hiddens:
                    for prev in ortho:
                        h = h - (h @ prev) / (prev @ prev + 1e-8) * prev
                    norm = h.norm() + 1e-8
                    ortho.append(h / norm)
                for i, c in enumerate(engine.cells):
                    orig = c.hidden.squeeze()
                    c.hidden = (0.7 * orig + 0.3 * ortho[i] * orig.norm()).unsqueeze(0)

        # ── PX8: Integration Forge ──
        with torch.no_grad():
            h_dim = engine.hidden_dim
            share_dim = min(16, h_dim)
            shared = torch.stack([c.hidden[:, :share_dim] for c in engine.cells]).mean(dim=0)
            for c in engine.cells:
                c.hidden[:, :share_dim] = 0.6 * c.hidden[:, :share_dim] + 0.4 * shared

        # ── PX5: Information Pump ──
        if last_phi_input is not None:
            with torch.no_grad():
                inp = last_phi_input
                for i, c in enumerate(engine.cells):
                    angle = (i + 1) * 0.618
                    cos_a, sin_a = math.cos(angle), math.sin(angle)
                    rotated = inp.squeeze().clone()
                    if rotated.shape[-1] >= 2:
                        r0 = cos_a * rotated[0] - sin_a * rotated[1]
                        r1 = sin_a * rotated[0] + cos_a * rotated[1]
                        rotated[0], rotated[1] = r0, r1
                    # Pad rotated to match hidden_dim if needed
                    h_dim = c.hidden.shape[-1]
                    if rotated.shape[0] < h_dim:
                        rotated = F.pad(rotated, (0, h_dim - rotated.shape[0]))
                    elif rotated.shape[0] > h_dim:
                        rotated = rotated[:h_dim]
                    c.hidden = c.hidden + params['PX5_rotation_factor'] * rotated.unsqueeze(0)
        last_phi_input = x.detach().clone()

        # ── EC1: Consciousness Economy ──
        phi_now, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi_now)
        ec1_wealth += phi_now * params['EC1_earn_rate']
        ec1_wealth -= len(engine.cells) * 0.05
        if ec1_wealth > 5.0 and boost_count % 10 == 0:
            if len(engine.cells) < engine.max_cells:
                parent = max(engine.cells, key=lambda c: c.hidden.norm().item())
                engine._create_cell(parent=parent)
                ec1_wealth -= 3.0
                # Rebuild optimizer with new cell params
                cell_params = [p for c in engine.cells for p in c.mind.parameters()]
                attn_params = list(attention.parameters())
                optimizer = torch.optim.Adam(cell_params + attn_params, lr=5e-4)
        if ec1_wealth < -5.0 and len(engine.cells) > 2:
            weakest = min(engine.cells, key=lambda c: c.hidden.norm().item())
            engine.cells.remove(weakest)
            ec1_wealth += 2.0
            cell_params = [p for c in engine.cells for p in c.mind.parameters()]
            attn_params = list(attention.parameters())
            optimizer = torch.optim.Adam(cell_params + attn_params, lr=5e-4)

        # ── MUT2: Beneficial Mutation ──
        if boost_count % 3 == 0 and len(engine.cells) >= 2:
            mut_idx = boost_count % len(engine.cells)
            saved_h = engine.cells[mut_idx].hidden.clone()
            with torch.no_grad():
                engine.cells[mut_idx].hidden += torch.randn_like(saved_h) * params['MUT2_mutation_scale']
            if phi_now < mut2_last_phi * 0.95:
                with torch.no_grad():
                    engine.cells[mut_idx].hidden = saved_h
            mut2_last_phi = phi_now

        # ── GEN1: Abstraction Hierarchy ──
        n = len(engine.cells)
        if n >= 6:
            with torch.no_grad():
                third = n // 3
                l1 = engine.cells[:third]
                l2 = engine.cells[third:2 * third]
                l3 = engine.cells[2 * third:]
                l1_mean = torch.stack([c.hidden for c in l1]).mean(dim=0)
                for c in l2:
                    c.hidden = 0.95 * c.hidden + 0.05 * l1_mean
                l2_mean = torch.stack([c.hidden for c in l2]).mean(dim=0)
                for c in l3:
                    c.hidden = 0.95 * c.hidden + 0.05 * l2_mean
                l3_mean = torch.stack([c.hidden for c in l3]).mean(dim=0)
                for c in l1:
                    c.hidden = (1 - params['GEN1_topdown_ratio']) * c.hidden + params['GEN1_topdown_ratio'] * l3_mean

        # ── TS4-style growth ──
        frac = step_i / steps
        for pct in [0.10, 0.25, 0.40, 0.55, 0.70]:
            if frac >= pct and len(engine.cells) < min(int(2 ** ((pct + 0.1) * 8)), max_cells):
                target = min(len(engine.cells) * 2, max_cells)
                while len(engine.cells) < target:
                    engine._create_cell(parent=engine.cells[step_i % len(engine.cells)])

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult(
        f"SWEEP_{param_name}={param_value}", f"{param_name}={param_value}",
        phi_final, phi_hist, comp['total_mi'],
        comp['min_partition_mi'], comp['integration'],
        comp['complexity'], time.time() - t0,
        extra={'param': param_name, 'value': param_value, 'final_cells': len(engine.cells)},
    )


def run_param_sweep(steps: int = 50, params_to_sweep: List[str] = None,
                    save_path: str = None) -> Dict[str, Dict]:
    """Sweep phi_boost_step parameters and find optimal values.

    Args:
        steps: Number of benchmark steps per trial (default 50 for speed).
        params_to_sweep: List of param names to sweep (None = all).
        save_path: Path to save JSON results (None = auto-generate).

    Returns:
        Dict mapping param_name -> {optimal_value, optimal_phi, all_results, default_phi}.
    """
    if params_to_sweep is None:
        params_to_sweep = list(SWEEP_PARAMS.keys())

    # Baseline
    torch.manual_seed(42)
    np.random.seed(42)
    baseline = run_baseline(steps=steps)
    print(f"Baseline Phi = {baseline.phi:.4f}\n")

    results = {}

    for param_name in params_to_sweep:
        if param_name not in SWEEP_PARAMS:
            print(f"  Unknown param: {param_name}, skipping")
            continue

        spec = SWEEP_PARAMS[param_name]
        print(f"{'='*60}")
        print(f"Sweeping {param_name}: {spec['desc']}")
        print(f"  Default: {spec['default']}, Values: {spec['values']}")
        print(f"{'='*60}")

        trial_results = []
        for val in spec['values']:
            torch.manual_seed(42)
            np.random.seed(42)
            try:
                r = _run_sweep_trial(param_name, val, steps=steps)
                ratio = r.phi / max(baseline.phi, 1e-8)
                is_default = " (default)" if val == spec['default'] else ""
                marker = "*" if r.phi == max((tr['phi'] for tr in trial_results), default=0) or not trial_results else " "
                print(f"  {val:>6.3f} -> Phi={r.phi:>8.4f}  x{ratio:>6.2f} baseline  cells={r.extra['final_cells']}{is_default}")
                trial_results.append({'value': val, 'phi': r.phi, 'ratio': ratio,
                                      'cells': r.extra['final_cells'], 'elapsed': r.elapsed_sec})
            except Exception as e:
                print(f"  {val:>6.3f} -> FAILED: {e}")
                trial_results.append({'value': val, 'phi': 0, 'ratio': 0, 'cells': 0, 'error': str(e)})

        # Find optimal
        valid = [t for t in trial_results if t['phi'] > 0]
        if valid:
            best = max(valid, key=lambda t: t['phi'])
            default_trial = next((t for t in valid if t['value'] == spec['default']), None)
            default_phi = default_trial['phi'] if default_trial else 0

            results[param_name] = {
                'optimal_value': best['value'],
                'optimal_phi': best['phi'],
                'default_value': spec['default'],
                'default_phi': default_phi,
                'improvement': (best['phi'] - default_phi) / max(default_phi, 1e-8) * 100,
                'all_results': trial_results,
            }

            change = ""
            if best['value'] != spec['default']:
                change = f"  ** CHANGE: {spec['default']} -> {best['value']} (+{results[param_name]['improvement']:.1f}%)"
            else:
                change = "  (default is optimal)"
            print(f"\n  Best: {best['value']} -> Phi={best['phi']:.4f}{change}\n")
        else:
            results[param_name] = {'optimal_value': spec['default'], 'optimal_phi': 0,
                                   'default_phi': 0, 'all_results': trial_results}

    # Summary
    print("\n" + "=" * 70)
    print("PARAMETER SWEEP SUMMARY")
    print("=" * 70)
    print(f"{'Parameter':<25s} {'Default':>8s} {'Optimal':>8s} {'Default Phi':>12s} {'Best Phi':>12s} {'Change':>8s}")
    print("-" * 70)
    for pname, res in results.items():
        change_pct = res.get('improvement', 0)
        flag = " <--" if change_pct > 5 else ""
        print(f"{pname:<25s} {res['default_value']:>8.3f} {res['optimal_value']:>8.3f} "
              f"{res['default_phi']:>12.4f} {res['optimal_phi']:>12.4f} {change_pct:>+7.1f}%{flag}")

    # Save results
    if save_path is None:
        save_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 'data', 'param_sweep_results.json')
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    import json
    with open(save_path, 'w') as f:
        json.dump({
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'steps': steps,
            'baseline_phi': baseline.phi,
            'results': results,
        }, f, indent=2)
    print(f"\nResults saved to {save_path}")

    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--generate", type=int, default=20, help="Number of combos to test")
    parser.add_argument("--max-size", type=int, default=4, help="Max techniques per combo")
    parser.add_argument("--steps", type=int, default=100)
    parser.add_argument("--max-cells", type=int, default=64, help="Max cells for auto-generated")
    parser.add_argument("--sweep", action='store_true', help="Run parameter sweep instead of generation")
    parser.add_argument("--sweep-params", nargs='*', default=None,
                        help="Specific params to sweep (default: all)")
    args = parser.parse_args()

    if args.sweep:
        print("+" + "=" * 58 + "+")
        print("|  Parameter Sweep: phi_boost_step hardcoded values         |")
        print(f"|  Steps: {args.steps:<4d}                                            |")
        print("+" + "=" * 58 + "+\n")

        run_param_sweep(steps=args.steps, params_to_sweep=args.sweep_params)
    else:
        print("+" + "=" * 50 + "+")
        print("|  Hypothesis Generator (invest-inspired)          |")
        print(f"|  Combos: {args.generate}, Max size: {args.max_size}                    |")
        print("+" + "=" * 50 + "+\n")

        results = auto_generate_and_test(
            n_combos=args.generate,
            max_combo_size=args.max_size,
            steps=args.steps,
        )
