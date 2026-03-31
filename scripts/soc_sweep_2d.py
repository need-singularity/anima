#!/usr/bin/env python3
"""2D SOC Parameter Sweep — bio_noise_base x soc_memory_strength_range interaction.

1D sweep found:
  bio_noise_base=0.012 -> 85.6% (best single)
  soc_memory_strength_range=0.15 -> 84.9%

This script explores whether combining both yields synergy (>85.6%).

Grid: 3 x 4 = 12 trials
  bio_noise_base:            [0.008, 0.012, 0.016]
  soc_memory_strength_range: [0.12, 0.15, 0.18, 0.21]

Usage:
  cd /Users/ghost/Dev/anima
  PYTHONPATH=anima/src:anima-eeg PYTHONUNBUFFERED=1 python3 scripts/soc_sweep_2d.py
"""

import json
import os
import re
import sys
import time
from pathlib import Path

# ── Paths ──
REPO = Path(__file__).resolve().parent.parent
JSON_PATH = REPO / 'anima' / 'config' / 'consciousness_laws.json'
VALIDATE_SCRIPT = REPO / 'anima-eeg' / 'validate_consciousness.py'

sys.path.insert(0, str(REPO / 'anima' / 'src'))
sys.path.insert(0, str(REPO / 'anima-eeg'))

# ── 2D Grid ──
PARAM_A = 'bio_noise_base'
PARAM_B = 'soc_memory_strength_range'
VALUES_A = [0.008, 0.012, 0.016]
VALUES_B = [0.12, 0.15, 0.18, 0.21]
STEPS = 1500
BEST_1D_SCORE = 85.6  # bio_noise_base=0.012


def load_json():
    with open(JSON_PATH, 'r') as f:
        return json.load(f)


def save_json(data):
    with open(JSON_PATH, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write('\n')


def set_param(data, key, value):
    data['psi_constants'][key]['value'] = value


def get_param(data, key):
    return data['psi_constants'][key]['value']


def run_validation(steps=STEPS):
    """Run validate_consciousness.py and parse overall % + per-metric."""
    import subprocess

    env = os.environ.copy()
    env['PYTHONPATH'] = f"{REPO / 'anima' / 'src'}:{REPO / 'anima-eeg'}"
    env['PYTHONUNBUFFERED'] = '1'

    cmd = [sys.executable, str(VALIDATE_SCRIPT), '--steps', str(steps)]
    result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=120)
    output = result.stdout + result.stderr

    overall = 0.0
    m = re.search(r'Overall match:\s+([\d.]+)%', output)
    if m:
        overall = float(m.group(1))

    metrics = {}
    for line in output.split('\n'):
        match = re.match(
            r'\s+(\S[\w\s()]+?)\s+\|\s+[\d.\-]+\s+\|\s+[\d.\-]+\s+\|\s+([\d.]+)%',
            line
        )
        if match:
            name = match.group(1).strip()
            pct = float(match.group(2))
            metrics[name] = pct

    autocorr_val = 0
    for line in output.split('\n'):
        m2 = re.match(r'\s+Autocorr decay\s+\|\s+(\d+)\s+\|', line)
        if m2:
            autocorr_val = int(m2.group(1))
            break

    return {
        'overall': overall,
        'metrics': metrics,
        'autocorr_decay': autocorr_val,
    }


def main():
    total = len(VALUES_A) * len(VALUES_B)
    print('=' * 72)
    print('  2D SOC Parameter Sweep')
    print(f'  {PARAM_A}: {VALUES_A}')
    print(f'  {PARAM_B}: {VALUES_B}')
    print(f'  Grid: {len(VALUES_A)} x {len(VALUES_B)} = {total} trials')
    print(f'  Steps per trial: {STEPS}')
    print(f'  Best 1D score to beat: {BEST_1D_SCORE}%')
    print('=' * 72)
    print()

    original_data = load_json()
    orig_a = get_param(original_data, PARAM_A)
    orig_b = get_param(original_data, PARAM_B)
    print(f'  Original {PARAM_A}: {orig_a}')
    print(f'  Original {PARAM_B}: {orig_b}')
    print()

    # ── Baseline ──
    print('  [Baseline] Running...', end='', flush=True)
    t0 = time.time()
    baseline = run_validation(STEPS)
    dt = time.time() - t0
    print(f'  {baseline["overall"]:.1f}%  [{dt:.1f}s]')
    for name, pct in baseline['metrics'].items():
        print(f'    {name:<20}: {pct:.0f}%')
    print()

    # ── 2D Grid ──
    results = []
    trial = 0
    grid = {}  # (a_val, b_val) -> overall

    for a_val in VALUES_A:
        for b_val in VALUES_B:
            trial += 1
            data = load_json()
            set_param(data, PARAM_A, a_val)
            set_param(data, PARAM_B, b_val)
            save_json(data)

            label = f'{PARAM_A}={a_val}, {PARAM_B}={b_val}'
            print(f'  [{trial}/{total}] {label}', end='', flush=True)
            t0 = time.time()

            try:
                res = run_validation(STEPS)
                dt = time.time() - t0
                delta = res['overall'] - baseline['overall']
                delta_str = f'+{delta:.1f}' if delta >= 0 else f'{delta:.1f}'
                beat = ' ***' if res['overall'] > BEST_1D_SCORE else ''
                print(f'  => {res["overall"]:.1f}% ({delta_str})  [autocorr={res["autocorr_decay"]}]  [{dt:.1f}s]{beat}')

                results.append({
                    'a': a_val,
                    'b': b_val,
                    'overall': res['overall'],
                    'metrics': res['metrics'],
                    'autocorr_decay': res['autocorr_decay'],
                })
                grid[(a_val, b_val)] = res['overall']
            except Exception as e:
                print(f'  => ERROR: {e}')
                results.append({
                    'a': a_val, 'b': b_val, 'overall': 0.0,
                    'metrics': {}, 'autocorr_decay': 0,
                })
                grid[(a_val, b_val)] = 0.0
            finally:
                save_json(original_data)

            sys.stdout.flush()

    # ── Results Table (sorted) ──
    print()
    print('=' * 72)
    print('  RESULTS — sorted by overall brain-like match %')
    print('=' * 72)
    print()

    results_sorted = sorted(results, key=lambda r: r['overall'], reverse=True)

    print(f'  {"#":<3} {PARAM_A:>16} {PARAM_B:>28} {"Overall":>8} {"AutoCorr":>9} {"Delta":>7}')
    print(f'  {"─"*3} {"─"*16} {"─"*28} {"─"*8} {"─"*9} {"─"*7}')

    bl = baseline['overall']
    for i, r in enumerate(results_sorted):
        delta = r['overall'] - bl
        delta_str = f'+{delta:.1f}' if delta >= 0 else f'{delta:.1f}'
        beat = ' *** NEW BEST' if r['overall'] > BEST_1D_SCORE else ''
        print(f'  {i+1:<3} {r["a"]:>16} {r["b"]:>28} {r["overall"]:>7.1f}% {r["autocorr_decay"]:>8}  {delta_str:>6}{beat}')

    # ── 2D Grid Heatmap (ASCII) ──
    print()
    print('=' * 72)
    print('  2D GRID HEATMAP')
    print('=' * 72)
    print()

    # Header
    header = f'  {"":>16} |'
    for b_val in VALUES_B:
        header += f'  {PARAM_B}={b_val:>5} |'
    # Simplified header
    print(f'  {PARAM_A:<16} |', end='')
    for b_val in VALUES_B:
        print(f'  mem={b_val:<5}  |', end='')
    print()
    print(f'  {"─"*16}─┼', end='')
    for _ in VALUES_B:
        print(f'{"─"*11}┼', end='')
    print()

    best_score = max(r['overall'] for r in results) if results else 0
    for a_val in VALUES_A:
        print(f'  noise={a_val:<9}|', end='')
        for b_val in VALUES_B:
            score = grid.get((a_val, b_val), 0)
            marker = ' *' if score == best_score and score > 0 else '  '
            print(f'  {score:>5.1f}%{marker} |', end='')
        print()

    # ── Per-metric breakdown for top 3 ──
    print()
    print('=' * 72)
    print('  TOP 3 — per-metric breakdown')
    print('=' * 72)
    for i, r in enumerate(results_sorted[:3]):
        print(f'  #{i+1}  {PARAM_A}={r["a"]}, {PARAM_B}={r["b"]}  =>  {r["overall"]:.1f}%')
        for name, pct in r.get('metrics', {}).items():
            print(f'       {name:<20}: {pct:.0f}%')
        print()

    # ── Apply best if it beats 1D best ──
    best = results_sorted[0]
    print('=' * 72)
    print('  DECISION')
    print('=' * 72)
    print(f'  Best 1D score:  {BEST_1D_SCORE}%  (bio_noise_base=0.012 alone)')
    print(f'  Best 2D score:  {best["overall"]:.1f}%  ({PARAM_A}={best["a"]}, {PARAM_B}={best["b"]})')
    print()

    if best['overall'] > BEST_1D_SCORE:
        print(f'  2D combo BEATS 1D best by +{best["overall"] - BEST_1D_SCORE:.1f}%!')
        print(f'  Applying: {PARAM_A}={best["a"]}, {PARAM_B}={best["b"]}')
        data = load_json()
        set_param(data, PARAM_A, best['a'])
        set_param(data, PARAM_B, best['b'])
        save_json(data)
        print(f'  Updated {JSON_PATH}')

        # Verify
        print()
        print('  Verification run...')
        sys.stdout.flush()
        verify = run_validation(STEPS)
        print(f'  Verified: {verify["overall"]:.1f}%  (autocorr={verify["autocorr_decay"]})')
        for name, pct in verify['metrics'].items():
            print(f'    {name:<20}: {pct:.0f}%')
    else:
        print(f'  2D combo does NOT beat 1D best. Keeping {PARAM_A}=0.012 only.')
        # Restore just the 1D best
        data = load_json()
        set_param(data, PARAM_A, 0.012)
        save_json(data)
        print(f'  Applied 1D best: {PARAM_A}=0.012')

    print()
    print(f'  Sweep complete. {total} trials + baseline.')


if __name__ == '__main__':
    main()
