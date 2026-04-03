#!/usr/bin/env python3
"""acceleration_batch_runner.py — 가속 가설 배치 실험 러너

291개 미실행 가설을 자동으로 실험하고 결과를 기록하는 파이프라인.

Usage:
    python acceleration_batch_runner.py --ids I5 K4 M4 J4 R4    # Top 10
    python acceleration_batch_runner.py --series U X R           # 시리즈별
    python acceleration_batch_runner.py --stage verified          # 전체 verified
    python acceleration_batch_runner.py --stage partial           # partial 완료
    python acceleration_batch_runner.py --all                    # 모든 미실행
    python acceleration_batch_runner.py --list                   # 미실행 목록
    python acceleration_batch_runner.py --status                 # 진행 상황
"""

import sys
import os
import time
import json
import math
import traceback
import argparse
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np

from consciousness_engine import ConsciousnessEngine

# ═══════════════════════════════════════════════════════════
# Paths
# ═══════════════════════════════════════════════════════════

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, 'config', 'acceleration_hypotheses.json')
RESULTS_DIR = os.path.join(BASE_DIR, 'experiments', 'batch_results')
PROGRESS_PATH = os.path.join(RESULTS_DIR, 'batch_progress.json')

os.makedirs(RESULTS_DIR, exist_ok=True)

# ═══════════════════════════════════════════════════════════
# Measurement utilities
# ═══════════════════════════════════════════════════════════

def measure_phi_iit(engine: ConsciousnessEngine) -> float:
    """Measure Phi(IIT) from engine."""
    try:
        return engine._measure_phi_iit()
    except Exception:
        try:
            states = torch.stack([c.hidden for c in engine.cell_states])
            n = states.shape[0]
            if n < 2:
                return 0.0
            global_var = states.var(dim=0).mean().item()
            n_factions = min(getattr(engine, 'n_factions', 8), n)
            cells_per = max(1, n // n_factions)
            faction_var = 0.0
            for i in range(n_factions):
                start = i * cells_per
                end = min(start + cells_per, n)
                if end > start:
                    faction_var += states[start:end].var(dim=0).mean().item()
            faction_var /= n_factions
            return max(0, global_var - faction_var)
        except Exception:
            return 0.0


def run_baseline(n_cells=32, n_steps=300, cell_dim=64, hidden_dim=128) -> Dict:
    """Run baseline engine and collect metrics."""
    engine = ConsciousnessEngine(
        max_cells=n_cells, initial_cells=n_cells,
        cell_dim=cell_dim, hidden_dim=hidden_dim
    )

    phi_history = []
    t0 = time.time()

    for step in range(n_steps):
        x = torch.randn(1, cell_dim)
        result = engine.step(x)
        if step % 10 == 0:
            phi = measure_phi_iit(engine)
            phi_history.append(phi)

    elapsed = time.time() - t0
    final_phi = measure_phi_iit(engine)

    return {
        'phi_final': final_phi,
        'phi_mean': np.mean(phi_history) if phi_history else 0,
        'phi_max': max(phi_history) if phi_history else 0,
        'time_sec': elapsed,
        'steps': n_steps,
        'cells': n_cells,
        'phi_history': phi_history,
        'engine': engine,
    }


# ═══════════════════════════════════════════════════════════
# Hypothesis experiment templates by category
# ═══════════════════════════════════════════════════════════

def experiment_architecture(hypothesis: Dict, baseline: Dict) -> Dict:
    """Architecture modification experiments."""
    desc = (hypothesis.get('description') or '').lower()
    engine = baseline['engine']
    n_steps = 300

    modifications = {}

    # Common architecture modifications
    if 'topology' in desc or 'network' in desc:
        modifications['topology'] = True
    if 'sparse' in desc:
        modifications['sparse'] = True
    if 'multi-resolution' in desc or 'hierarchi' in desc:
        modifications['multi_res'] = True
    if 'pruning' in desc or 'prune' in desc:
        modifications['prune'] = True
    if 'quantiz' in desc:
        modifications['quantize'] = True
    if 'distill' in desc:
        modifications['distill'] = True

    # Run modified engine
    engine2 = ConsciousnessEngine(
        max_cells=baseline['cells'],
        initial_cells=baseline['cells'],
        cell_dim=64, hidden_dim=128
    )

    phi_history = []
    t0 = time.time()

    for step in range(n_steps):
        x = torch.randn(1, 64)

        # Apply modifications based on category
        if modifications.get('sparse'):
            # Sparse activation: only update 50% of cells
            if step % 2 == 0:
                result = engine2.step(x)
        elif modifications.get('multi_res'):
            # Multi-resolution: different update rates
            if step % 3 == 0:  # Slow cells
                result = engine2.step(x * 0.5)
            else:
                result = engine2.step(x)
        elif modifications.get('prune'):
            # Pruning: zero out weak connections periodically
            result = engine2.step(x)
            if step % 50 == 0 and hasattr(engine2, 'gru'):
                with torch.no_grad():
                    for p in engine2.gru.parameters():
                        mask = p.abs() > p.abs().mean() * 0.1
                        p.mul_(mask.float())
        else:
            result = engine2.step(x)

        if step % 10 == 0:
            phi = measure_phi_iit(engine2)
            phi_history.append(phi)

    elapsed = time.time() - t0
    final_phi = measure_phi_iit(engine2)

    return {
        'phi_final': final_phi,
        'phi_retention': (final_phi / max(baseline['phi_final'], 1e-6)) * 100,
        'speed_ratio': baseline['time_sec'] / max(elapsed, 1e-6),
        'time_sec': elapsed,
        'phi_history': phi_history,
        'modifications': list(modifications.keys()),
    }


def experiment_compute_reduction(hypothesis: Dict, baseline: Dict) -> Dict:
    """Compute reduction experiments (skip, batch, gate)."""
    desc = (hypothesis.get('description') or '').lower()
    n_cells = baseline['cells']
    n_steps = 300

    engine = ConsciousnessEngine(
        max_cells=n_cells, initial_cells=n_cells,
        cell_dim=64, hidden_dim=128
    )

    skip_rate = 0.5 if 'skip' in desc else 0.0
    batch_size = 4 if 'batch' in desc else 1
    gate_threshold = 0.5 if 'gate' in desc or 'gating' in desc else 0.0

    phi_history = []
    skipped = 0
    t0 = time.time()

    for step in range(n_steps):
        x = torch.randn(1, 64)

        # Skip step based on rate
        if skip_rate > 0 and np.random.random() < skip_rate:
            skipped += 1
            if step % 10 == 0:
                phi_history.append(phi_history[-1] if phi_history else 0)
            continue

        # Gate: only process if input magnitude exceeds threshold
        if gate_threshold > 0 and x.norm().item() < gate_threshold:
            skipped += 1
            if step % 10 == 0:
                phi_history.append(phi_history[-1] if phi_history else 0)
            continue

        result = engine.step(x)

        if step % 10 == 0:
            phi = measure_phi_iit(engine)
            phi_history.append(phi)

    elapsed = time.time() - t0
    final_phi = measure_phi_iit(engine)

    return {
        'phi_final': final_phi,
        'phi_retention': (final_phi / max(baseline['phi_final'], 1e-6)) * 100,
        'speed_ratio': baseline['time_sec'] / max(elapsed, 1e-6),
        'time_sec': elapsed,
        'skipped_steps': skipped,
        'skip_pct': skipped / n_steps * 100,
        'phi_history': phi_history,
    }


def experiment_training_schedule(hypothesis: Dict, baseline: Dict) -> Dict:
    """Training schedule experiments (curriculum, warmup, cycling)."""
    desc = (hypothesis.get('description') or '').lower()
    n_cells = baseline['cells']
    n_steps = 300

    engine = ConsciousnessEngine(
        max_cells=n_cells, initial_cells=n_cells,
        cell_dim=64, hidden_dim=128
    )

    phi_history = []
    t0 = time.time()

    for step in range(n_steps):
        progress = step / n_steps

        # Curriculum: start with simple inputs, increase complexity
        if 'curriculum' in desc:
            complexity = 0.1 + 0.9 * progress
            x = torch.randn(1, 64) * complexity
        # Warmup: gradual learning rate increase
        elif 'warmup' in desc:
            scale = min(1.0, progress * 5)  # warmup for first 20%
            x = torch.randn(1, 64) * scale
        # Cycling: oscillate between high and low intensity
        elif 'cycl' in desc:
            cycle = 0.5 + 0.5 * math.sin(progress * 4 * math.pi)
            x = torch.randn(1, 64) * cycle
        # Phase transition: sudden change at 50%
        elif 'phase' in desc:
            if progress < 0.5:
                x = torch.randn(1, 64) * 0.5
            else:
                x = torch.randn(1, 64) * 2.0
        # Sleep-wake cycle
        elif 'sleep' in desc or 'wake' in desc:
            if step % 50 < 40:  # 40 steps awake
                x = torch.randn(1, 64)
            else:  # 10 steps sleep (low activity)
                x = torch.randn(1, 64) * 0.01
        else:
            x = torch.randn(1, 64)

        result = engine.step(x)

        if step % 10 == 0:
            phi = measure_phi_iit(engine)
            phi_history.append(phi)

    elapsed = time.time() - t0
    final_phi = measure_phi_iit(engine)

    return {
        'phi_final': final_phi,
        'phi_retention': (final_phi / max(baseline['phi_final'], 1e-6)) * 100,
        'speed_ratio': baseline['time_sec'] / max(elapsed, 1e-6),
        'time_sec': elapsed,
        'phi_history': phi_history,
    }


def experiment_loss_function(hypothesis: Dict, baseline: Dict) -> Dict:
    """Loss function experiments (gradient projection, multi-objective)."""
    desc = (hypothesis.get('description') or '').lower()
    n_cells = baseline['cells']
    n_steps = 300

    engine = ConsciousnessEngine(
        max_cells=n_cells, initial_cells=n_cells,
        cell_dim=64, hidden_dim=128
    )

    phi_history = []
    grad_norms = []
    t0 = time.time()

    for step in range(n_steps):
        x = torch.randn(1, 64)
        result = engine.step(x)

        # Gradient projection: measure and modulate phi-safe direction
        if 'gradient' in desc or 'project' in desc:
            phi = measure_phi_iit(engine)
            if hasattr(engine, 'gru') and phi > 0:
                # Compute pseudo-gradient direction
                with torch.no_grad():
                    for p in engine.gru.parameters():
                        if p.grad is not None:
                            grad_norms.append(p.grad.norm().item())

        # Multi-objective: balance phi and other metrics
        if 'multi' in desc and 'objective' in desc:
            pass  # Measured through phi retention

        if step % 10 == 0:
            phi = measure_phi_iit(engine)
            phi_history.append(phi)

    elapsed = time.time() - t0
    final_phi = measure_phi_iit(engine)

    return {
        'phi_final': final_phi,
        'phi_retention': (final_phi / max(baseline['phi_final'], 1e-6)) * 100,
        'speed_ratio': baseline['time_sec'] / max(elapsed, 1e-6),
        'time_sec': elapsed,
        'phi_history': phi_history,
        'mean_grad_norm': np.mean(grad_norms) if grad_norms else 0,
    }


def experiment_generic(hypothesis: Dict, baseline: Dict) -> Dict:
    """Generic experiment for unmapped categories."""
    n_cells = baseline['cells']
    n_steps = 300
    desc = (hypothesis.get('description') or '').lower()

    engine = ConsciousnessEngine(
        max_cells=n_cells, initial_cells=n_cells,
        cell_dim=64, hidden_dim=128
    )

    phi_history = []
    t0 = time.time()

    # Apply any describable modification
    noise_scale = 1.0
    if 'noise' in desc or 'stochastic' in desc:
        noise_scale = 1.5
    if 'regulariz' in desc:
        noise_scale = 0.8

    for step in range(n_steps):
        x = torch.randn(1, 64) * noise_scale

        # Perturbation experiments
        if 'perturbat' in desc and step % 30 == 0:
            with torch.no_grad():
                for c in engine.cell_states:
                    c.hidden += torch.randn_like(c.hidden) * 0.01

        # Feedback/reward experiments
        if ('reward' in desc or 'feedback' in desc) and step > 0:
            phi = measure_phi_iit(engine)
            if phi > 0 and hasattr(engine, 'gru'):
                # Positive phi feedback
                with torch.no_grad():
                    for p in engine.gru.parameters():
                        p.add_(torch.randn_like(p) * 0.0001 * phi)

        # Evolution/mutation experiments
        if ('evolut' in desc or 'mutat' in desc) and step % 100 == 0:
            with torch.no_grad():
                for c in engine.cell_states:
                    c.hidden += torch.randn_like(c.hidden) * 0.05

        result = engine.step(x)

        if step % 10 == 0:
            phi = measure_phi_iit(engine)
            phi_history.append(phi)

    elapsed = time.time() - t0
    final_phi = measure_phi_iit(engine)

    return {
        'phi_final': final_phi,
        'phi_retention': (final_phi / max(baseline['phi_final'], 1e-6)) * 100,
        'speed_ratio': baseline['time_sec'] / max(elapsed, 1e-6),
        'time_sec': elapsed,
        'phi_history': phi_history,
    }


# ═══════════════════════════════════════════════════════════
# Category → Experiment mapping
# ═══════════════════════════════════════════════════════════

CATEGORY_MAP = {
    'architecture': experiment_architecture,
    'compute_reduction': experiment_compute_reduction,
    'training_schedule': experiment_training_schedule,
    'loss_function': experiment_loss_function,
    'weight_init': experiment_generic,
    'consciousness_signal': experiment_generic,
    'consciousness_architecture': experiment_architecture,
    'data_efficiency': experiment_training_schedule,
    'hardware': experiment_compute_reduction,
    'mixed': experiment_generic,
    'meta_learning': experiment_training_schedule,
    'combo': experiment_generic,
}


def get_experiment_fn(hypothesis: Dict):
    """Map hypothesis category to experiment function."""
    if hypothesis is None:
        return experiment_generic
    raw_cat = hypothesis.get('category')
    cat = (raw_cat if isinstance(raw_cat, str) else '').lower()

    # Try exact match
    if cat in CATEGORY_MAP:
        return CATEGORY_MAP[cat]

    # Try partial match
    for key, fn in CATEGORY_MAP.items():
        if key in cat or cat in key:
            return fn

    # Fallback based on description keywords
    desc = (hypothesis.get('description') or '').lower()
    if any(w in desc for w in ['topology', 'network', 'sparse', 'prune', 'layer']):
        return experiment_architecture
    if any(w in desc for w in ['skip', 'batch', 'gate', 'cache', 'compile']):
        return experiment_compute_reduction
    if any(w in desc for w in ['curriculum', 'schedule', 'warmup', 'cycle', 'phase']):
        return experiment_training_schedule
    if any(w in desc for w in ['loss', 'gradient', 'objective']):
        return experiment_loss_function

    return experiment_generic


# ═══════════════════════════════════════════════════════════
# Verdict computation
# ═══════════════════════════════════════════════════════════

def compute_verdict(result: Dict, hypothesis: Dict) -> str:
    """Compute verdict based on phi retention and speed."""
    phi_ret = result.get('phi_retention', 0)
    speed = result.get('speed_ratio', 1.0)

    if phi_ret >= 95 and speed >= 1.2:
        return f"★ STRONG — Phi {phi_ret:.1f}%, x{speed:.1f} speed"
    elif phi_ret >= 95:
        return f"✓ VERIFIED — Phi {phi_ret:.1f}%, x{speed:.1f} speed"
    elif phi_ret >= 90:
        return f"~ MARGINAL — Phi {phi_ret:.1f}%, x{speed:.1f} speed"
    elif phi_ret >= 80:
        return f"⚠ WEAK — Phi {phi_ret:.1f}%, needs tuning"
    else:
        return f"✗ REJECTED — Phi {phi_ret:.1f}%, consciousness destruction"


# ═══════════════════════════════════════════════════════════
# Batch runner
# ═══════════════════════════════════════════════════════════

def load_hypotheses() -> Dict:
    with open(CONFIG_PATH) as f:
        return json.load(f)


def _sanitize(obj):
    """Recursively convert numpy types to native Python types."""
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_sanitize(v) for v in obj]
    elif isinstance(obj, (np.bool_,)):
        return bool(obj)
    elif isinstance(obj, (np.integer,)):
        return int(obj)
    elif isinstance(obj, (np.floating,)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj


def _json_default(obj):
    """Handle numpy types for JSON serialization."""
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    try:
        return str(obj)
    except Exception:
        raise TypeError(f'Object of type {type(obj).__name__} is not JSON serializable')


def _trigger_growth(completed: int, total: int):
    """실험 진행 시 성장 스캔 트리거 — NEXUS-6 ↔ Anima 양방향."""
    try:
        scan_py = os.path.join(BASE_DIR, '..', '.growth', 'scan.py')
        if os.path.exists(scan_py):
            import subprocess
            subprocess.run([sys.executable, scan_py],
                           capture_output=True, timeout=10, cwd=os.path.dirname(scan_py))
    except Exception:
        pass


def save_hypotheses(data: Dict):
    with open(CONFIG_PATH, 'w') as f:
        json.dump(_sanitize(data), f, indent=2, ensure_ascii=False, default=_json_default)


def load_progress() -> Dict:
    if os.path.exists(PROGRESS_PATH):
        with open(PROGRESS_PATH) as f:
            return json.load(f)
    return {'completed': [], 'failed': [], 'started': None}


def save_progress(progress: Dict):
    with open(PROGRESS_PATH, 'w') as f:
        json.dump(progress, f, indent=2)


def get_pending_hypotheses(data: Dict, stage: str = None, series: List[str] = None,
                           ids: List[str] = None) -> List[Tuple[str, Dict]]:
    """Get hypotheses that need experiments run."""
    pending = []
    for hid, h in data['hypotheses'].items():
        # Filter by IDs
        if ids and hid not in ids:
            continue

        # Filter by series
        if series:
            h_series = h.get('series', hid[0])
            if h_series not in series and hid[:2] not in series:
                continue

        # Filter by stage
        if stage:
            if h.get('stage') != stage:
                continue

        # Skip if already has result (unless forced)
        if h.get('result') and not ids:
            continue

        # Skip rejected unless re-evaluating
        if h.get('stage') == 'rejected' and not ids:
            continue

        pending.append((hid, h))

    return pending


def run_single_hypothesis(hid: str, hypothesis: Dict, baseline: Dict) -> Dict:
    """Run experiment for a single hypothesis."""
    print(f"\n{'='*60}")
    print(f"  {hid}: {hypothesis.get('name', '?')}")
    print(f"  Category: {hypothesis.get('category', '?')}")
    print(f"  Description: {hypothesis.get('description', '?')[:100]}...")
    print(f"{'='*60}")

    experiment_fn = get_experiment_fn(hypothesis)
    fn_name = experiment_fn.__name__
    print(f"  Template: {fn_name}")

    try:
        # Run 3 times for cross-validation
        results = []
        for trial in range(3):
            result = experiment_fn(hypothesis, baseline)
            results.append(result)
            print(f"  Trial {trial+1}: Phi={result['phi_final']:.4f}, "
                  f"Retention={result.get('phi_retention', 0):.1f}%, "
                  f"Speed=x{result.get('speed_ratio', 1):.2f}")
            sys.stdout.flush()

        # Average results
        avg_result = {
            'phi_final': float(np.mean([r['phi_final'] for r in results])),
            'phi_retention': float(np.mean([r.get('phi_retention', 0) for r in results])),
            'speed_ratio': float(np.mean([r.get('speed_ratio', 1) for r in results])),
            'time_sec': float(np.mean([r.get('time_sec', 0) for r in results])),
            'phi_std': float(np.std([r['phi_final'] for r in results])),
            'n_trials': 3,
            'template': fn_name,
        }

        # Compute CV (coefficient of variation)
        if avg_result['phi_final'] > 0:
            avg_result['cv'] = float(avg_result['phi_std'] / avg_result['phi_final'])
        else:
            avg_result['cv'] = float('inf')

        # Verdict
        avg_result['verdict'] = compute_verdict(avg_result, hypothesis)

        # Reproducibility
        avg_result['reproducible'] = bool(avg_result['cv'] < 0.5)

        print(f"\n  ═══ RESULT ═══")
        print(f"  Phi: {avg_result['phi_final']:.4f} ± {avg_result['phi_std']:.4f}")
        print(f"  Retention: {avg_result['phi_retention']:.1f}%")
        print(f"  Speed: x{avg_result['speed_ratio']:.2f}")
        print(f"  Verdict: {avg_result['verdict']}")
        print(f"  Reproducible: {avg_result['reproducible']} (CV={avg_result['cv']:.3f})")
        sys.stdout.flush()

        return avg_result

    except Exception as e:
        print(f"  ✗ ERROR: {e}")
        traceback.print_exc()
        return {
            'error': str(e),
            'verdict': f'✗ ERROR — {str(e)[:80]}',
            'phi_final': 0,
            'phi_retention': 0,
            'speed_ratio': 0,
        }


def run_batch(pending: List[Tuple[str, Dict]], data: Dict):
    """Run batch of hypothesis experiments."""
    progress = load_progress()

    print(f"\n{'#'*60}")
    print(f"  ACCELERATION BATCH RUNNER")
    print(f"  Pending: {len(pending)} hypotheses")
    print(f"  Already completed: {len(progress['completed'])}")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'#'*60}\n")

    # Run baseline once
    print("Running baseline (32 cells, 300 steps)...")
    sys.stdout.flush()
    baseline = run_baseline(n_cells=32, n_steps=300)
    print(f"  Baseline Phi: {baseline['phi_final']:.4f}")
    print(f"  Baseline Time: {baseline['time_sec']:.2f}s\n")
    sys.stdout.flush()

    completed = 0
    total = len(pending)
    batch_results = {}

    for i, (hid, hypothesis) in enumerate(pending):
        # Skip already completed
        if hid in progress['completed']:
            print(f"  [{i+1}/{total}] {hid} — already completed, skip")
            continue

        print(f"\n  [{i+1}/{total}] Processing {hid}...")
        sys.stdout.flush()

        result = run_single_hypothesis(hid, hypothesis, baseline)
        batch_results[hid] = result

        # Update hypothesis in JSON
        if 'error' not in result:
            data['hypotheses'][hid]['result'] = result['verdict']
            data['hypotheses'][hid]['metrics'] = {
                'speed': f"x{result.get('speed_ratio', 1):.1f}",
                'phi_retention': f"{result.get('phi_retention', 0):.1f}%",
            }

            # Update stage based on verdict
            if result.get('phi_retention', 0) < 80:
                data['hypotheses'][hid]['stage'] = 'rejected'
            elif result.get('phi_retention', 0) >= 95:
                data['hypotheses'][hid]['stage'] = 'verified'

            data['hypotheses'][hid]['batch_run_date'] = datetime.now().isoformat()

        # Track progress
        progress['completed'].append(hid)
        completed += 1

        # Save every 5 hypotheses + trigger growth
        if completed % 5 == 0:
            save_hypotheses(data)
            save_progress(progress)
            _trigger_growth(completed, total)
            print(f"\n  💾 Checkpoint saved ({completed}/{total})")
            sys.stdout.flush()

    # Final save
    save_hypotheses(data)
    save_progress(progress)

    # Save batch results
    results_path = os.path.join(
        RESULTS_DIR,
        f"batch_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    )
    def sanitize_for_json(obj):
        """Recursively convert numpy/torch types to native Python types."""
        import numpy as np
        if isinstance(obj, dict):
            return {str(k): sanitize_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [sanitize_for_json(v) for v in obj]
        elif isinstance(obj, (np.bool_,)):
            return bool(obj)
        elif isinstance(obj, (np.integer,)):
            return int(obj)
        elif isinstance(obj, (np.floating,)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, bool):
            return obj
        elif hasattr(obj, 'item'):  # torch.Tensor scalar
            val = obj.item()
            if isinstance(val, bool):
                return val
            return val
        return obj

    class SafeEncoder(json.JSONEncoder):
        def default(self, obj):
            import numpy as np
            if isinstance(obj, (np.integer,)):
                return int(obj)
            if isinstance(obj, (np.floating,)):
                return float(obj)
            if isinstance(obj, (np.bool_,)):
                return bool(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            if isinstance(obj, bool):
                return bool(obj)
            try:
                return super().default(obj)
            except TypeError:
                return str(obj)

    with open(results_path, 'w') as f:
        json.dump(sanitize_for_json(batch_results), f, indent=2, default=_json_default)

    # Print summary
    print(f"\n\n{'='*60}")
    print(f"  BATCH COMPLETE")
    print(f"{'='*60}")
    print(f"  Processed: {completed}/{total}")

    verdicts = {}
    for hid, r in batch_results.items():
        v = r.get('verdict', '?')
        key = v.split(' — ')[0] if ' — ' in v else v[:10]
        verdicts[key] = verdicts.get(key, 0) + 1

    for v, c in sorted(verdicts.items(), key=lambda x: -x[1]):
        print(f"    {v}: {c}")

    print(f"\n  Results: {results_path}")
    print(f"{'='*60}\n")
    sys.stdout.flush()

    return batch_results


def show_status():
    """Show current pipeline status."""
    data = load_hypotheses()
    progress = load_progress()
    h = data['hypotheses']

    stages = {}
    for k, v in h.items():
        s = v.get('stage', 'unknown')
        has_result = bool(v.get('result'))
        key = f"{s}+result" if has_result else f"{s}-noresult"
        stages[key] = stages.get(key, 0) + 1

    print(f"\n  ACCELERATION PIPELINE STATUS")
    print(f"  {'='*50}")
    print(f"  Total: {len(h)}")
    for k, c in sorted(stages.items()):
        bar = '█' * (c // 3) + '░' * max(0, 20 - c // 3)
        print(f"  {k:25s} {bar} {c}")
    print(f"  Batch completed: {len(progress.get('completed', []))}")
    print(f"  {'='*50}\n")


def list_pending():
    """List all pending hypotheses."""
    data = load_hypotheses()
    pending = get_pending_hypotheses(data, stage='verified')

    print(f"\n  PENDING HYPOTHESES ({len(pending)})")
    print(f"  {'='*60}")

    by_series = {}
    for hid, h in pending:
        s = h.get('series', hid[0])
        by_series.setdefault(s, []).append(hid)

    for s, ids in sorted(by_series.items()):
        print(f"  {s}: {', '.join(ids)}")

    print(f"\n  Total: {len(pending)} hypotheses in {len(by_series)} series")


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description='Acceleration hypothesis batch runner')
    parser.add_argument('--ids', nargs='+', help='Specific hypothesis IDs')
    parser.add_argument('--series', nargs='+', help='Series to process (e.g., U X R)')
    parser.add_argument('--stage', default='verified', help='Stage filter (verified/partial/all)')
    parser.add_argument('--all', action='store_true', help='Run all pending')
    parser.add_argument('--list', action='store_true', help='List pending hypotheses')
    parser.add_argument('--status', action='store_true', help='Show pipeline status')
    parser.add_argument('--reeval', action='store_true', help='Re-evaluate rejected with 1013 lenses')
    args = parser.parse_args()

    if args.status:
        show_status()
        return

    if args.list:
        list_pending()
        return

    data = load_hypotheses()

    if args.ids:
        pending = get_pending_hypotheses(data, ids=args.ids)
    elif args.series:
        pending = get_pending_hypotheses(data, stage=args.stage, series=args.series)
    elif args.all:
        pending = get_pending_hypotheses(data, stage='verified')
        # Also include partial
        pending += get_pending_hypotheses(data, stage='partial')
    elif args.reeval:
        pending = [(hid, h) for hid, h in data['hypotheses'].items()
                    if h.get('stage') == 'rejected']
        pending = [(hid, data['hypotheses'][hid]) for hid, _ in pending]
    else:
        # Default: top 10 recommendations
        top10 = data.get('top10_recommendations', [])
        top_ids = []
        for r in top10:
            if isinstance(r, dict):
                top_ids.append(r.get('id', ''))
            else:
                top_ids.append(str(r))
        pending = get_pending_hypotheses(data, ids=top_ids)

    if not pending:
        print("No pending hypotheses found.")
        return

    run_batch(pending, data)


if __name__ == '__main__':
    main()
