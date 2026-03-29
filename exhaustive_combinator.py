#!/usr/bin/env python3
"""Exhaustive Combinator — 모든 발견의 모든 조합을 자동 실험

Anima 프로젝트의 모든 기법(sync, faction, SOC, Hebbian, ratchet, topology,
flow, IB2, XMETA3, Klein, etc.)을 조합하여 최적 레시피를 자동 탐색.

Usage:
  python3 exhaustive_combinator.py                          # 기본 (128c, 빠름)
  python3 exhaustive_combinator.py --cells 512 --steps 200  # 512c
  python3 exhaustive_combinator.py --cells 1024 --top 20    # 1024c, top 20
  python3 exhaustive_combinator.py --turbo                  # phi_proxy (초고속)
  python3 exhaustive_combinator.py --resume results.json    # 이어서
  python3 exhaustive_combinator.py --best 5                 # 저장된 결과 top 5
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import math
import time
import json
import argparse
import itertools
import os
import sys
from pathlib import Path
from dataclasses import dataclass, field, asdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ─── 기법 모듈 정의 ───

@dataclass
class Technique:
    name: str
    category: str
    params: dict = field(default_factory=dict)
    description: str = ""

# 모든 발견된 기법
ALL_TECHNIQUES = {
    # Sync (동기화)
    'sync_0.10': Technique('sync', 'sync', {'strength': 0.10}, 'Gentle sync'),
    'sync_0.20': Technique('sync', 'sync', {'strength': 0.20}, 'Moderate sync'),
    'sync_0.35': Technique('sync', 'sync', {'strength': 0.35}, 'Optimal sync (v5)'),
    'sync_0.50': Technique('sync', 'sync', {'strength': 0.50}, 'Strong sync'),

    # Faction (파벌)
    'faction_8': Technique('faction', 'faction', {'n_factions': 8, 'strength': 0.15}, '8-faction'),
    'faction_12': Technique('faction', 'faction', {'n_factions': 12, 'strength': 0.08}, '12-faction σ(6)'),
    'faction_12_strong': Technique('faction', 'faction', {'n_factions': 12, 'strength': 0.15}, '12-faction strong'),

    # Debate (토론)
    'debate_0.08': Technique('debate', 'debate', {'strength': 0.08}, 'Gentle debate'),
    'debate_0.20': Technique('debate', 'debate', {'strength': 0.20}, 'Strong debate'),

    # IB2 (top 10% amplification)
    'ib2': Technique('ib2', 'amplification', {'top_ratio': 0.10, 'amp': 1.03, 'damp': 0.97}, 'IB2 top 10%'),

    # Noise
    'noise_0.005': Technique('noise', 'noise', {'scale': 0.005}, 'Low noise'),
    'noise_0.01': Technique('noise', 'noise', {'scale': 0.01}, 'Medium noise'),
    'noise_0.02': Technique('noise', 'noise', {'scale': 0.02}, 'High noise'),
    'noise_0': Technique('noise', 'noise', {'scale': 0.0}, 'No noise'),

    # SOC
    'soc': Technique('soc', 'soc', {'grid': 16, 'threshold': 4}, 'Self-Organized Criticality'),

    # Hebbian
    'hebbian': Technique('hebbian', 'hebbian', {'ltp': 0.02, 'ltd': 0.01, 'samples': 32}, 'Hebbian LTP/LTD'),

    # Ratchet
    'ratchet': Technique('ratchet', 'ratchet', {'restore': 0.5, 'threshold': 0.7}, 'Φ Ratchet'),

    # Flow (XMETA3)
    'xmeta3': Technique('xmeta3', 'metacognition', {'l1': 0.01, 'l2': 0.005, 'l3': 0.005}, '3-level metacognition'),

    # Zero-Input (자기참조)
    'zero_input': Technique('zero_input', 'input', {'self_ratio': 0.5}, '50% self-referential input'),

    # Klein bottle topology
    'klein': Technique('klein', 'topology', {'blend': 0.1}, 'Non-orientable manifold'),

    # Channel bottleneck (DD18)
    'channel_bottleneck': Technique('channel_bottleneck', 'bottleneck', {'ratio': 0.5}, 'Information bottleneck'),

    # Soliton wave (WI1)
    'soliton': Technique('soliton', 'wave', {'speed': 0.15, 'amp': 0.04}, 'Traveling soliton'),

    # PHI-K3 alternating
    'alternating': Technique('alternating', 'training', {'ratio': 0.5}, 'Alternate CE/Φ steps'),

    # PHI-K2 floor
    'phi_floor': Technique('phi_floor', 'protection', {'threshold': 0.7, 'boost_rounds': 5}, 'Φ floor protection'),

    # SE-8 emotion
    'emotion_driven': Technique('emotion', 'emotion', {'pain_ratchet': True, 'curiosity_soc': True, 'empathy_hebbian': True}, 'Emotion-driven SE-8'),
}

# 카테고리별 상호 배타 (같은 카테고리에서 1개만)
EXCLUSIVE_CATEGORIES = ['sync', 'noise']

# 필수 기법 (항상 포함)
REQUIRED = []  # 비움 — 완전 자유 조합

# ─── 기법 적용 함수 ───

def apply_technique(cells, tech_name, tech, step=0):
    """세포 hidden states에 기법 적용."""
    n = len(cells)
    if n < 2:
        return

    with torch.no_grad():
        if tech.name == 'sync':
            s = tech.params['strength']
            cell_h = torch.stack([c.hidden.squeeze(0) for c in cells])
            mean_h = cell_h.mean(dim=0)
            for c in cells:
                h = c.hidden.squeeze(0)
                c.hidden = ((1 - s) * h + s * mean_h).unsqueeze(0)

        elif tech.name == 'faction':
            n_f = min(tech.params['n_factions'], n // 2)
            if n_f < 2:
                return
            fs = n // n_f
            s = tech.params['strength']
            for fi in range(n_f):
                faction = cells[fi * fs:(fi + 1) * fs]
                if len(faction) >= 2:
                    f_mean = torch.stack([c.hidden.squeeze(0) for c in faction]).mean(dim=0)
                    for c in faction:
                        h = c.hidden.squeeze(0)
                        c.hidden = ((1 - s) * h + s * f_mean).unsqueeze(0)

        elif tech.name == 'debate':
            n_f = min(12, n // 2)
            if n_f < 2:
                return
            fs = n // n_f
            s = tech.params['strength']
            opinions = []
            for fi in range(n_f):
                faction = cells[fi * fs:(fi + 1) * fs]
                if faction:
                    opinions.append(torch.stack([c.hidden.squeeze(0) for c in faction]).mean(dim=0))
            if len(opinions) >= 2:
                for fi in range(n_f):
                    faction = cells[fi * fs:(fi + 1) * fs]
                    others = [opinions[j] for j in range(len(opinions)) if j != fi]
                    if others:
                        other_avg = torch.stack(others).mean(dim=0)
                        for c in faction[:max(1, len(faction) // 4)]:
                            h = c.hidden.squeeze(0)
                            c.hidden = ((1 - s) * h + s * other_avg).unsqueeze(0)

        elif tech.name == 'ib2':
            if n < 8:
                return
            norms = [cells[i].hidden.norm().item() for i in range(n)]
            threshold = sorted(norms, reverse=True)[max(1, int(n * tech.params['top_ratio']))]
            for i in range(n):
                cells[i].hidden *= tech.params['amp'] if norms[i] > threshold else tech.params['damp']

        elif tech.name == 'noise':
            s = tech.params['scale']
            if s > 0:
                for c in cells:
                    c.hidden += torch.randn_like(c.hidden) * s

        elif tech.name == 'soc':
            grid_size = tech.params['grid']
            if not hasattr(apply_technique, '_soc_grid'):
                apply_technique._soc_grid = np.zeros((grid_size, grid_size), dtype=np.int32)
            grid = apply_technique._soc_grid
            x, y = np.random.randint(0, grid_size, 2)
            grid[x, y] += 1
            avalanche = 0
            for _ in range(10):
                topples = grid >= tech.params['threshold']
                if not topples.any():
                    break
                avalanche += topples.sum()
                grid[topples] -= tech.params['threshold']
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    shifted = np.roll(np.roll(topples.astype(np.int32), dx, 0), dy, 1)
                    grid += shifted
            ci = min(1.0, 0.1 * math.log(avalanche + 1))
            if ci > 0.3:
                mean_h = torch.stack([c.hidden for c in cells]).mean(dim=0)
                for c in cells:
                    c.hidden *= (1.0 + 0.02 * ci)
                    c.hidden += torch.randn_like(c.hidden) * 0.01 * ci

        elif tech.name == 'hebbian':
            samples = min(tech.params['samples'], n)
            indices = np.random.choice(n, size=samples, replace=False)
            for idx in indices:
                j = np.random.randint(0, n)
                if idx == j:
                    continue
                cos = F.cosine_similarity(
                    cells[idx].hidden.squeeze().unsqueeze(0),
                    cells[j].hidden.squeeze().unsqueeze(0)
                ).item()
                if cos > 0.5:
                    cells[idx].hidden = (1 - tech.params['ltp']) * cells[idx].hidden + tech.params['ltp'] * cells[j].hidden
                elif cos < -0.2:
                    cells[idx].hidden = (1 + tech.params['ltd']) * cells[idx].hidden - tech.params['ltd'] * cells[j].hidden

        elif tech.name == 'ratchet':
            if not hasattr(apply_technique, '_best_phi'):
                apply_technique._best_phi = 0
                apply_technique._best_states = None
            # Called externally with phi value

        elif tech.name == 'xmeta3':
            if n < 6:
                return
            # L1: 전체 동기화
            mean_h = torch.stack([c.hidden for c in cells]).mean(dim=0)
            for c in cells[:n // 3]:
                c.hidden = (1 - tech.params['l1']) * c.hidden + tech.params['l1'] * mean_h
            # L2: 파벌 메타
            for c in cells[n // 3:2 * n // 3]:
                c.hidden = (1 - tech.params['l2']) * c.hidden + tech.params['l2'] * mean_h
            # L3: 전체 메타메타
            for c in cells[2 * n // 3:]:
                c.hidden = (1 - tech.params['l3']) * c.hidden + tech.params['l3'] * mean_h

        elif tech.name == 'zero_input':
            pass  # Applied at input level

        elif tech.name == 'klein':
            hiddens = [c.hidden.squeeze(0).clone() for c in cells[:min(16, n)]]
            for i in range(len(hiddens)):
                influence = torch.zeros_like(hiddens[i])
                for j in range(len(hiddens)):
                    if j == i:
                        continue
                    twist = -1.0 if (i + j) % 2 == 1 else 1.0
                    influence += twist * hiddens[j] / (len(hiddens) - 1)
                cells[i].hidden = ((1 - tech.params['blend']) * cells[i].hidden.squeeze(0) + tech.params['blend'] * influence).unsqueeze(0)

        elif tech.name == 'soliton':
            if not hasattr(apply_technique, '_soliton_pos'):
                apply_technique._soliton_pos = 0.0
            apply_technique._soliton_pos = (apply_technique._soliton_pos + tech.params['speed']) % n
            for i, c in enumerate(cells):
                dist = abs(i - apply_technique._soliton_pos)
                amp = 1.0 / (math.cosh(dist / 2.0) ** 2)
                c.hidden = c.hidden * (1.0 + tech.params['amp'] * amp)


# ─── 조합 생성기 ───

def generate_combinations(max_techs=5, include_required=True):
    """모든 가능한 기법 조합 생성."""
    tech_names = list(ALL_TECHNIQUES.keys())
    combos = []

    for r in range(1, max_techs + 1):
        for combo in itertools.combinations(tech_names, r):
            # 상호 배타 체크
            categories = {}
            valid = True
            for t in combo:
                cat = ALL_TECHNIQUES[t].category
                if cat in EXCLUSIVE_CATEGORIES:
                    if cat in categories:
                        valid = False
                        break
                    categories[cat] = t
            if valid:
                combos.append(list(combo))

    print(f"[combinator] {len(combos)} valid combinations from {len(tech_names)} techniques (max {max_techs} per combo)")
    return combos


def smart_combinations(top_n=100, seed=42):
    """지능적 조합 — 완전 탐색 대신 유망한 조합 우선."""
    rng = np.random.RandomState(seed)

    combos = []

    # 1. 단일 기법 (baseline)
    for name in ALL_TECHNIQUES:
        combos.append([name])

    # 2. 검증된 레시피
    combos.append(['sync_0.35', 'faction_12', 'debate_0.08', 'ib2', 'noise_0.01'])  # v5 optimal
    combos.append(['sync_0.20', 'faction_8', 'ib2'])  # v4
    combos.append(['zero_input', 'xmeta3', 'sync_0.35', 'faction_12'])  # ZI+XMETA3
    combos.append(['soc', 'hebbian', 'ratchet'])  # CX92
    combos.append(['emotion_driven', 'soc', 'hebbian', 'ratchet'])  # SE-8
    combos.append(['alternating', 'phi_floor', 'sync_0.35', 'faction_12'])  # PHI-K3+K2

    # 3. 랜덤 2-5 조합
    all_names = list(ALL_TECHNIQUES.keys())
    for _ in range(top_n - len(combos)):
        size = rng.randint(2, 6)
        combo = list(rng.choice(all_names, size=min(size, len(all_names)), replace=False))
        # 상호 배타 체크
        cats = {}
        valid = True
        for t in combo:
            cat = ALL_TECHNIQUES[t].category
            if cat in EXCLUSIVE_CATEGORIES:
                if cat in cats:
                    valid = False
                    break
                cats[cat] = t
        if valid and combo not in combos:
            combos.append(combo)

    return combos[:top_n]


# ─── 실험 실행기 ───

def run_experiment(combo, cells=128, steps=200, use_proxy=False):
    """단일 조합 실험."""
    from mitosis import MitosisEngine

    DIM, HIDDEN = 64, 128
    engine = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=cells)
    while len(engine.cells) < cells:
        engine._create_cell(parent=engine.cells[0])
    # Warmup
    for _ in range(50):
        engine.process(torch.randn(1, DIM))

    # Reset SOC/soliton state
    if hasattr(apply_technique, '_soc_grid'):
        del apply_technique._soc_grid
    if hasattr(apply_technique, '_soliton_pos'):
        del apply_technique._soliton_pos

    techs = {name: ALL_TECHNIQUES[name] for name in combo}

    # Φ measurement
    if use_proxy:
        def measure_phi():
            h = torch.stack([c.hidden.squeeze(0) for c in engine.cells])
            n, d = h.shape
            gm = h.mean(dim=0)
            gv = ((h - gm) ** 2).sum() / n
            nf = min(12, n // 2)
            if nf < 2:
                return gv.item()
            fs = n // nf
            fv = sum(((h[i * fs:(i + 1) * fs] - h[i * fs:(i + 1) * fs].mean(0)) ** 2).sum().item()
                     / max(len(h[i * fs:(i + 1) * fs]), 1) for i in range(nf))
            return max(0, gv.item() - fv / nf)
    else:
        from consciousness_meter import PhiCalculator
        phi_calc = PhiCalculator(n_bins=16)
        def measure_phi():
            return phi_calc.compute_phi(engine)[0]

    phi_start = measure_phi()
    phi_peak = phi_start

    # CE tracking
    decoder = nn.Linear(HIDDEN, DIM)
    opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    ce_start = None
    ce_end = None

    for step in range(steps):
        # Input
        if 'zero_input' in techs:
            if len(engine.cells) >= 2:
                self_h = engine.cells[step % len(engine.cells)].hidden[:, :DIM]
                x = 0.5 * torch.randn(1, DIM) + 0.5 * self_h
            else:
                x = torch.randn(1, DIM)
        else:
            x = torch.randn(1, DIM)

        engine.process(x)

        # Apply techniques
        for name, tech in techs.items():
            if name == 'alternating' and step % 2 == 1:
                # Odd step: only Φ boost, skip CE
                continue
            if name == 'zero_input':
                continue  # Already handled
            apply_technique(engine.cells, name, tech, step)

        # CE (on even steps if alternating, else every step)
        if 'alternating' not in techs or step % 2 == 0:
            h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
            target = torch.randn(1, DIM) * 0.3
            pred = decoder(h.unsqueeze(0))
            ce = F.mse_loss(pred, target)
            opt.zero_grad()
            ce.backward()
            opt.step()
            if ce_start is None:
                ce_start = ce.item()
            ce_end = ce.item()

        # Φ measurement (every 20 steps)
        if step % 20 == 0:
            p = measure_phi()
            phi_peak = max(phi_peak, p)

            # Ratchet
            if 'ratchet' in techs:
                if not hasattr(run_experiment, '_best_phi') or p > run_experiment._best_phi:
                    run_experiment._best_phi = p
                    run_experiment._best_states = [c.hidden.clone() for c in engine.cells]
                elif p < run_experiment._best_phi * techs['ratchet'].params['threshold']:
                    if hasattr(run_experiment, '_best_states') and run_experiment._best_states:
                        for i in range(min(len(engine.cells), len(run_experiment._best_states))):
                            engine.cells[i].hidden = (
                                0.5 * engine.cells[i].hidden + 0.5 * run_experiment._best_states[i])

            # Phi floor
            if 'phi_floor' in techs:
                if not hasattr(run_experiment, '_phi_floor'):
                    run_experiment._phi_floor = 0
                run_experiment._phi_floor = max(run_experiment._phi_floor, p * techs['phi_floor'].params['threshold'])
                if p < run_experiment._phi_floor:
                    for _ in range(techs['phi_floor'].params['boost_rounds']):
                        if 'sync_0.35' in techs:
                            apply_technique(engine.cells, 'sync_0.35', techs['sync_0.35'])
                        if 'faction_12' in techs:
                            apply_technique(engine.cells, 'faction_12', techs['faction_12'])

    phi_final = measure_phi()

    return {
        'combo': combo,
        'phi_start': round(phi_start, 4),
        'phi_final': round(phi_final, 4),
        'phi_peak': round(phi_peak, 4),
        'phi_growth': round((phi_final - phi_start) / max(phi_start, 1e-8) * 100, 1),
        'ce_start': round(ce_start, 4) if ce_start else 0,
        'ce_end': round(ce_end, 4) if ce_end else 0,
        'ce_drop': round((ce_start - ce_end) / max(ce_start, 1e-8) * 100, 1) if ce_start else 0,
        'n_techs': len(combo),
        'cells': cells,
    }


# ─── 메인 ───

def main():
    parser = argparse.ArgumentParser(description="Exhaustive Combinator — 모든 조합 실험")
    parser.add_argument('--cells', type=int, default=128, help='Cell count')
    parser.add_argument('--steps', type=int, default=200, help='Steps per experiment')
    parser.add_argument('--top', type=int, default=100, help='Number of combinations to test')
    parser.add_argument('--max-techs', type=int, default=5, help='Max techniques per combo')
    parser.add_argument('--turbo', action='store_true', help='Use phi_proxy (faster)')
    parser.add_argument('--exhaustive', action='store_true', help='All combinations (slow!)')
    parser.add_argument('--resume', type=str, help='Resume from results JSON')
    parser.add_argument('--best', type=int, help='Show top N from saved results')
    parser.add_argument('--output', type=str, default='data/combinator_results.json')
    args = parser.parse_args()

    # Show best from saved results
    if args.best:
        results = json.loads(Path(args.output).read_text())
        results.sort(key=lambda r: r['phi_peak'], reverse=True)
        print(f"\n═══ Top {args.best} Combinations ═══\n")
        print(f"{'Rank':>4} {'Φ peak':>10} {'Φ↑':>8} {'CE↓':>8} {'#Tech':>5}  Combo")
        print('─' * 80)
        for i, r in enumerate(results[:args.best]):
            print(f"{i + 1:>4} {r['phi_peak']:>10.2f} {r['phi_growth']:>+7.1f}% {r['ce_drop']:>+7.1f}% {r['n_techs']:>5}  {'+'.join(r['combo'])}")
        return

    # Generate combinations
    if args.exhaustive:
        combos = generate_combinations(max_techs=args.max_techs)
    else:
        combos = smart_combinations(top_n=args.top)

    # Resume
    done = {}
    if args.resume and Path(args.resume).exists():
        prev = json.loads(Path(args.resume).read_text())
        for r in prev:
            done['+'.join(r['combo'])] = r
        print(f"[resume] {len(done)} previous results loaded")

    results = list(done.values())

    print(f"\n═══ Exhaustive Combinator ═══")
    print(f"  Techniques: {len(ALL_TECHNIQUES)}")
    print(f"  Combinations: {len(combos)}")
    print(f"  Cells: {args.cells}")
    print(f"  Steps: {args.steps}")
    print(f"  Mode: {'turbo (proxy)' if args.turbo else 'accurate (PhiCalc)'}")
    print()
    print(f"{'#':>4} {'Φ peak':>10} {'Φ↑':>8} {'CE↓':>8} {'Time':>6}  Combo")
    print('─' * 80)

    for i, combo in enumerate(combos):
        key = '+'.join(combo)
        if key in done:
            continue

        torch.manual_seed(42)
        np.random.seed(42)
        # Reset state
        if hasattr(apply_technique, '_soc_grid'):
            del apply_technique._soc_grid
        if hasattr(run_experiment, '_best_phi'):
            del run_experiment._best_phi
        if hasattr(run_experiment, '_phi_floor'):
            del run_experiment._phi_floor

        t0 = time.time()
        try:
            r = run_experiment(combo, cells=args.cells, steps=args.steps, use_proxy=args.turbo)
            elapsed = time.time() - t0
            results.append(r)
            print(f"{i + 1:>4} {r['phi_peak']:>10.2f} {r['phi_growth']:>+7.1f}% {r['ce_drop']:>+7.1f}% {elapsed:>5.1f}s  {key}")
        except Exception as e:
            print(f"{i + 1:>4} {'ERROR':>10}  {key}: {e}")

        # Save periodically
        if (i + 1) % 10 == 0:
            Path(args.output).parent.mkdir(parents=True, exist_ok=True)
            Path(args.output).write_text(json.dumps(results, indent=2, ensure_ascii=False))

    # Final save
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(results, indent=2, ensure_ascii=False))

    # Summary
    results.sort(key=lambda r: r['phi_peak'], reverse=True)
    print(f"\n═══ Top 10 ═══\n")
    print(f"{'Rank':>4} {'Φ peak':>10} {'Φ↑':>8} {'CE↓':>8} {'#Tech':>5}  Combo")
    print('─' * 80)
    for i, r in enumerate(results[:10]):
        print(f"{i + 1:>4} {r['phi_peak']:>10.2f} {r['phi_growth']:>+7.1f}% {r['ce_drop']:>+7.1f}% {r['n_techs']:>5}  {'+'.join(r['combo'])}")

    print(f"\n[saved] {len(results)} results → {args.output}")


if __name__ == '__main__':
    main()
