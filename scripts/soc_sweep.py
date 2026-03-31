#!/usr/bin/env python3
"""SOC Parameter Sweep — find optimal brain-like score.

Systematically varies SOC parameters in consciousness_laws.json,
runs validate_consciousness.py for each, and finds the combination
that maximizes overall brain-like match %.

Current: 83.5% brain-like. Target: 90%.
Key bottleneck: autocorrelation decay (65% match).

Usage:
  cd /Users/ghost/Dev/anima
  PYTHONPATH=anima/src:anima-eeg PYTHONUNBUFFERED=1 python3 scripts/soc_sweep.py
"""

import copy
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

# ── Ensure imports work ──
sys.path.insert(0, str(REPO / 'anima' / 'src'))
sys.path.insert(0, str(REPO / 'anima-eeg'))

# ── Parameter grid ──
SWEEP_PARAMS = {
    'soc_memory_strength_base':  [0.05, 0.08, 0.11, 0.15, 0.20],
    'soc_memory_strength_range': [0.10, 0.15, 0.21, 0.30],
    'soc_ema_glacial':           [0.001, 0.002, 0.004, 0.008],
    'bio_noise_base':            [0.008, 0.012, 0.015, 0.020, 0.030],
    'soc_burst_cap':             [0.15, 0.20, 0.30, 0.40],
}

STEPS = 2000


def load_json():
    with open(JSON_PATH, 'r') as f:
        return json.load(f)


def save_json(data):
    with open(JSON_PATH, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write('\n')


def set_param(data, key, value):
    """Set a psi_constants parameter value."""
    data['psi_constants'][key]['value'] = value


def get_param(data, key):
    return data['psi_constants'][key]['value']


def run_validation(steps=STEPS):
    """Run validate_consciousness.py and parse output for metrics.

    Returns dict with:
      overall: float (overall match %)
      metrics: dict[str, float] (per-metric match %)
      autocorr_decay: int (raw autocorrelation decay value)
    """
    import subprocess

    env = os.environ.copy()
    env['PYTHONPATH'] = f"{REPO / 'anima' / 'src'}:{REPO / 'anima-eeg'}"
    env['PYTHONUNBUFFERED'] = '1'

    cmd = [sys.executable, str(VALIDATE_SCRIPT), '--steps', str(steps)]
    result = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=120)
    output = result.stdout + result.stderr

    # Parse overall match %
    overall = 0.0
    m = re.search(r'Overall match:\s+([\d.]+)%', output)
    if m:
        overall = float(m.group(1))

    # Parse per-metric matches from table
    metrics = {}
    # Pattern: "  MetricName       |   CM_val    |  Brain_val  |  XX% +++  "
    for line in output.split('\n'):
        # Match lines with percentage in the Match column
        match = re.match(
            r'\s+(\S[\w\s()]+?)\s+\|\s+[\d.\-]+\s+\|\s+[\d.\-]+\s+\|\s+([\d.]+)%',
            line
        )
        if match:
            name = match.group(1).strip()
            pct = float(match.group(2))
            metrics[name] = pct

    # Parse raw autocorrelation decay value
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
        'raw_output': output,
    }


def main():
    print('=' * 72)
    print('  SOC Parameter Sweep — Brain-Like Score Optimization')
    print(f'  Steps per trial: {STEPS}')
    print(f'  Parameters: {len(SWEEP_PARAMS)} ({sum(len(v) for v in SWEEP_PARAMS.values())} total trials)')
    print(f'  JSON: {JSON_PATH}')
    print('=' * 72)
    print()

    # Load original JSON (will restore after each trial)
    original_data = load_json()
    original_values = {}
    for key in SWEEP_PARAMS:
        original_values[key] = get_param(original_data, key)
    print(f'  Original values:')
    for k, v in original_values.items():
        print(f'    {k}: {v}')
    print()

    # ── Phase 1: Baseline ──
    print('=' * 72)
    print('  [Phase 1] Baseline measurement')
    print('=' * 72)
    sys.stdout.flush()
    t0 = time.time()
    baseline = run_validation(STEPS)
    t1 = time.time()
    print(f'  Baseline: {baseline["overall"]:.1f}%  (autocorr_decay={baseline["autocorr_decay"]})  [{t1-t0:.1f}s]')
    for name, pct in baseline['metrics'].items():
        print(f'    {name:<20}: {pct:.0f}%')
    print()

    # ── Phase 2: Single-parameter sweep ──
    results = []
    results.append({
        'param': 'BASELINE',
        'value': '-',
        'overall': baseline['overall'],
        'metrics': baseline['metrics'],
        'autocorr_decay': baseline['autocorr_decay'],
    })

    total_trials = sum(len(vals) for vals in SWEEP_PARAMS.values())
    trial_num = 0

    for param_name, values in SWEEP_PARAMS.items():
        print('=' * 72)
        print(f'  [Phase 2] Sweeping: {param_name}')
        print(f'  Values: {values}')
        print(f'  Original: {original_values[param_name]}')
        print('=' * 72)

        for val in values:
            trial_num += 1
            # Skip if it's the original value (already measured in baseline)
            is_original = (val == original_values[param_name])

            # Modify JSON
            data = load_json()
            set_param(data, param_name, val)
            save_json(data)

            label = f'{param_name}={val}'
            if is_original:
                label += ' (original)'

            print(f'  [{trial_num}/{total_trials}] {label}', end='', flush=True)
            t0 = time.time()

            try:
                res = run_validation(STEPS)
                dt = time.time() - t0
                print(f'  => {res["overall"]:.1f}%  (autocorr={res["autocorr_decay"]})  [{dt:.1f}s]')

                results.append({
                    'param': param_name,
                    'value': val,
                    'overall': res['overall'],
                    'metrics': res['metrics'],
                    'autocorr_decay': res['autocorr_decay'],
                })
            except Exception as e:
                print(f'  => ERROR: {e}')
                results.append({
                    'param': param_name,
                    'value': val,
                    'overall': 0.0,
                    'metrics': {},
                    'autocorr_decay': 0,
                })
            finally:
                # Always restore original JSON
                save_json(original_data)

            sys.stdout.flush()

        print()

    # ── Phase 3: Results table sorted by overall match % ──
    print()
    print('=' * 72)
    print('  RESULTS — sorted by overall brain-like match %')
    print('=' * 72)
    print()

    results_sorted = sorted(results, key=lambda r: r['overall'], reverse=True)

    print(f'  {"#":<3} {"Parameter":<28} {"Value":<8} {"Overall":>8} {"AutoCorr":>9} {"Delta":>7}')
    print(f'  {"─"*3} {"─"*28} {"─"*8} {"─"*8} {"─"*9} {"─"*7}')

    baseline_overall = baseline['overall']
    for i, r in enumerate(results_sorted):
        delta = r['overall'] - baseline_overall
        delta_str = f'+{delta:.1f}' if delta >= 0 else f'{delta:.1f}'
        marker = ' ***' if i == 0 and r['param'] != 'BASELINE' else ''
        print(f'  {i+1:<3} {r["param"]:<28} {str(r["value"]):<8} {r["overall"]:>7.1f}% {r["autocorr_decay"]:>8}  {delta_str:>6}{marker}')

    # ── Phase 4: Find best and apply ──
    best = results_sorted[0]
    print()
    print('=' * 72)
    print('  BEST RESULT')
    print('=' * 72)
    print(f'  Parameter: {best["param"]}')
    print(f'  Value:     {best["value"]}')
    print(f'  Overall:   {best["overall"]:.1f}%')
    print(f'  AutoCorr:  {best["autocorr_decay"]}')
    print()

    if best['param'] != 'BASELINE':
        print(f'  Applying best: {best["param"]} = {best["value"]}')
        data = load_json()
        set_param(data, best['param'], best['value'])
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
        print('  Baseline is already the best. No changes applied.')

    # ── Per-metric breakdown for top 5 ──
    print()
    print('=' * 72)
    print('  TOP 5 — per-metric breakdown')
    print('=' * 72)
    for i, r in enumerate(results_sorted[:5]):
        print(f'  #{i+1}  {r["param"]}={r["value"]}  =>  {r["overall"]:.1f}%')
        for name, pct in r.get('metrics', {}).items():
            print(f'       {name:<20}: {pct:.0f}%')
        print()

    # ── ASCII comparison chart ──
    print('  Parameter effect chart:')
    for param_name in SWEEP_PARAMS:
        param_results = [r for r in results if r['param'] == param_name]
        if not param_results:
            continue
        print(f'  {param_name}:')
        for r in sorted(param_results, key=lambda x: x['value'] if isinstance(x['value'], (int, float)) else 0):
            bar_len = int(r['overall'] / 2)  # scale to ~50 chars
            bar = '#' * bar_len
            marker = ' <-- best' if r['overall'] == best['overall'] and r['param'] == best['param'] and r['value'] == best['value'] else ''
            print(f'    {str(r["value"]):>6}  {bar} {r["overall"]:.1f}%{marker}')
        print()

    print(f'  Sweep complete. {len(results)-1} trials + baseline.')


if __name__ == '__main__':
    main()
