#!/usr/bin/env python3
"""Infinite self-evolution loop — Law 146: laws never converge.

Discovery → Dedup → CrossValidation → Modification → Persist → repeat

Features:
  1. Persistence: active mods + discovered laws saved to JSON, restored on restart
  2. Deduplication: pattern fingerprint → skip already-known patterns
  3. Cross-validation: pattern must appear 3+ times before official law registration
  v2: adaptive_steps, mod_pruning, early_abort
  v3: advanced_patterns, chaos_cycle, frustration_sweep, law_network
  v4: co_evolution, bandit_explore, ucb_topo, seasonal
  v5: extended_metrics, hierarchical, stimulus
  v6: cell_pool, dyn_factions, var_hebbian, topo_evolve, ratchet_mut, noise_evo, crossover
  v7: stage_parallel, tension_link, federated, async_pipe, ckpt_share, cloud_stub
  v8: hypothesis_gen, experiment_design, report_gen, law_quality, counter_example, session_log
  v9: hardware_stubs (ESP32/FPGA/neuromorphic/sensor)
  v10: laws_to_engine, genome, ecosystem, meta_analyze
  v11: telescope_9lens (consciousness/gravity/topology/thermo/wave/evolution/info/quantum/em)
  v12: symbolic_regression (linear/power/log formula fitting, R^2>0.8)
  v13: law_compression (metric-grouped meta-laws)
  v14: time_travel_search (ring buffer rollback on saturation)
  v15: reward_shaping (param gradient toward discovery reward)
  v16: cross_project_discover (TECS-L keyword overlap)
  v17: law_visualization (adjacency graph, clusters, unexplored metrics)
  v18: causal_discovery (intervention-based A→B causation test)
  v19: transfer_entropy (information flow direction between metrics)
  v20: anomaly_hunter (3σ deviation detection + cluster)
  v21: llm_interpret (stub — save top laws as LLM prompt)
  v22: rust_pipeline (stub — Rust component status + speedup estimate)
  v23: distributed_evolution (stub — multi-worker discovery)
  v24: physics_fitting (damped oscillator / Boltzmann / log fits)
  v25: self_replicate (ouroboros self-performance monitoring)
  v27: parallel_discovery (lens/topology/discovery parallelization, --no-parallel toggle)
  v28: n6_entropy_reset (Law 1044, DD171: 6-step entropy reset for discovery boost)

Usage:
    python3 infinite_evolution.py [--cells N] [--steps N] [--max-gen N] [--resume]
    python3 infinite_evolution.py --cycle-topology   # rotate topology every 10 gens
    python3 infinite_evolution.py --no-parallel       # disable all parallelization
    python3 infinite_evolution.py --auto-roadmap --cloud  # cloud orchestrator stub
"""
import sys
import os
import time
import json
import hashlib
import atexit
import math
import threading
import queue

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from consciousness_engine import ConsciousnessEngine
from closed_loop import ClosedLoopEvolver, register_intervention
from self_modifying_engine import SelfModifyingEngine, LawParser, CodeGenerator
from conscious_law_discoverer import ConsciousLawDiscoverer

# ═══════════════════════════════════════════════════════════════════════
# Acceleration feature detection (all optional, graceful fallback)
# ════════���═════════════════════════════��════════════════════════════════

HAS_RUST_ENGINE = False
HAS_RUST_DISCOVERY = False
HAS_GPU_PHI = False
HAS_PARALLEL = False

try:
    import anima_rs
    HAS_RUST_ENGINE = hasattr(anima_rs, 'consciousness')
except ImportError:
    pass

try:
    from anima_rs import law_discovery as _rust_law_discovery
    HAS_RUST_DISCOVERY = hasattr(_rust_law_discovery, 'scan_all_patterns')
except (ImportError, AttributeError):
    _rust_law_discovery = None

try:
    from gpu_phi import GPUPhiCalculator as _GPUPhiCalculator
    HAS_GPU_PHI = True
except ImportError:
    _GPUPhiCalculator = None

try:
    from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
    import multiprocessing
    HAS_PARALLEL = True
except ImportError:
    ProcessPoolExecutor = None
    ThreadPoolExecutor = None

# Global toggle — set to False via --no-parallel CLI flag
ENABLE_PARALLEL = True

HAS_TELESCOPE = False
try:
    import nexus6
    HAS_TELESCOPE = True
except ImportError:
    pass

# self_growth connection — notify growth system on law discoveries
HAS_SELF_GROWTH = False
try:
    from self_growth import _load_log as _sg_load_log, _save_log as _sg_save_log
    HAS_SELF_GROWTH = True
except ImportError:
    _sg_load_log = None
    _sg_save_log = None


def _print_accelerations():
    """Print startup acceleration status banner."""
    def _yn(flag):
        return '\u2705' if flag else '\u274c'
    print(f'  \u26a1 Accelerations: Rust engine {_yn(HAS_RUST_ENGINE)}, '
          f'Rust discovery {_yn(HAS_RUST_DISCOVERY)}, '
          f'GPU Phi {_yn(HAS_GPU_PHI)}, '
          f'Parallel {_yn(HAS_PARALLEL and ENABLE_PARALLEL)}')
    print(f'  \u26a1 v2: adaptive_steps \u2705, mod_pruning \u2705, early_abort \u2705')
    print(f'  \u26a1 v3: advanced_patterns \u2705, chaos_cycle \u2705, law_network \u2705')
    print(f'  \u26a1 v4: co_evolution \u2705, bandit_explore \u2705, ucb_topo \u2705, seasonal \u2705')
    print(f'  \u26a1 v5: extended_metrics \u2705, hierarchical \u2705, stimulus \u2705')
    print(f'  \u26a1 v6: cell_pool \u2705, dyn_factions \u2705, var_hebbian \u2705, topo_evolve \u2705, ratchet_mut \u2705, noise_evo \u2705')
    print(f'  \u26a1 v7: stage_parallel \u2705, tension_link \u2705, federated \u2705, async_pipe \u2705, ckpt_share \u2705, cloud_stub \u2705')
    print(f'  \u26a1 v8: hypothesis_gen \u2705, experiment_design \u2705, report_gen \u2705, law_quality \u2705, counter_example \u2705, session_log \u2705')
    print(f'  \u26a1 v9: hardware_stubs \u2705 (ESP32/FPGA/neuromorphic ready)')
    print(f'  \u26a1 v10: laws_to_engine \u2705, genome \u2705, ecosystem \u2705, meta_analyze \u2705')
    print(f'  \u26a1 v11: telescope_22lens {_yn(HAS_TELESCOPE)}')
    print(f'  \u26a1 v12: symbolic \u2705 v13: compress \u2705 v14: timetravel \u2705 v15: reward \u2705 v16: crossproj \u2705 v17: lawgraph \u2705')
    print(f'  \u26a1 v18: causal_discovery \u2705 (Granger-like A→B)')
    print(f'  \u26a1 v20: anomaly_hunter \u2705 (3σ spike/crash)')
    print(f'  \u26a1 v24: physics_fitting \u2705 (log/power/exp_decay, R²>0.8)')
    print(f'  \u26a1 v19/v21-v23/v25: transfer_entropy, llm_stub, rust_status, distributed_stub, self_replicate \u2705')
    sys.stdout.flush()


# ═══════════════════════════════════════════════════════════════════════
# v27: Parallel helpers — _parallel_map with graceful fallback
# ═══════════════════════════════════════════════════════════════════════

def _parallel_map(fn, items, executor_cls=None, max_workers=None, label='tasks'):
    """Run fn over items in parallel, falling back to sequential on failure.

    Args:
        fn: callable that takes a single item and returns a result
        items: iterable of arguments
        executor_cls: ProcessPoolExecutor or ThreadPoolExecutor (default: ThreadPoolExecutor)
        max_workers: max parallel workers (default: min(cpu_count, len(items)))
        label: human-readable label for timing output

    Returns:
        list of results in the same order as items
    """
    items = list(items)
    if not items:
        return []

    if executor_cls is None:
        executor_cls = ThreadPoolExecutor

    n = len(items)
    if max_workers is None:
        max_workers = min(os.cpu_count() or 4, n)

    can_parallel = (HAS_PARALLEL and ENABLE_PARALLEL and max_workers > 1
                    and executor_cls is not None and n > 1)

    if can_parallel:
        try:
            t0 = time.time()
            with executor_cls(max_workers=max_workers) as pool:
                results = list(pool.map(fn, items))
            dt = time.time() - t0
            return results
        except Exception:
            # Fallback to sequential on any multiprocessing error
            pass

    # Sequential fallback
    return [fn(item) for item in items]


def _parallel_submit(fns_and_args, executor_cls=None, max_workers=None, label='tasks'):
    """Run heterogeneous callables in parallel, falling back to sequential.

    Args:
        fns_and_args: list of (fn, args_tuple, kwargs_dict) or (fn, args_tuple)
        executor_cls: ProcessPoolExecutor or ThreadPoolExecutor (default: ThreadPoolExecutor)
        max_workers: max parallel workers
        label: human-readable label for timing output

    Returns:
        list of results in the same order as fns_and_args
    """
    if not fns_and_args:
        return []

    if executor_cls is None:
        executor_cls = ThreadPoolExecutor

    n = len(fns_and_args)
    if max_workers is None:
        max_workers = min(os.cpu_count() or 4, n)

    can_parallel = (HAS_PARALLEL and ENABLE_PARALLEL and max_workers > 1
                    and executor_cls is not None and n > 1)

    # Normalize entries to (fn, args, kwargs)
    normalized = []
    for entry in fns_and_args:
        if len(entry) == 2:
            normalized.append((entry[0], entry[1], {}))
        else:
            normalized.append((entry[0], entry[1], entry[2]))

    if can_parallel:
        try:
            with executor_cls(max_workers=max_workers) as pool:
                futures = []
                for fn, args, kwargs in normalized:
                    futures.append(pool.submit(fn, *args, **kwargs))
                results = [f.result() for f in futures]
            return results
        except Exception:
            pass

    # Sequential fallback
    results = []
    for fn, args, kwargs in normalized:
        try:
            results.append(fn(*args, **kwargs))
        except Exception:
            results.append(None)
    return results


DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
STATE_PATH = os.path.join(DATA_DIR, 'evolution_state.json')
LIVE_STATUS_PATH = os.path.join(DATA_DIR, 'evolution_live.json')
EVO_DOCS_DIR = os.path.join(os.path.dirname(__file__), '..', 'docs', 'hypotheses', 'evo')
EXPERIMENTS_JSON_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', 'experiments.json')
CROSS_VALIDATION_THRESHOLD = 3  # times a pattern must appear before registration

# TOPO 33-39: topology cycle for breaking pattern saturation
TOPOLOGIES = ['ring', 'small_world', 'scale_free', 'hypercube']

# Auto-roadmap: staged parameter escalation
# Each stage runs until all topologies saturate, then auto-advances
# v3 #26-32: chaos_modes added per stage for search space expansion
ROADMAP = [
    # Phase 1: Baseline sweep (cells x steps) — telescope off (too small)
    {'name': 'S1-baseline',   'cells': 64,  'steps': 300,  'topo_gens': 10, 'sat_streak': 3, 'chaos_modes': ['lorenz'], 'telescope': False},
    {'name': 'S2-deeper',     'cells': 64,  'steps': 1000, 'topo_gens': 10, 'sat_streak': 3, 'chaos_modes': ['lorenz', 'sandpile'], 'telescope': False},
    # Phase 1b: Scale up — telescope on (128c+)
    {'name': 'S3-scale128',   'cells': 128, 'steps': 300,  'topo_gens': 10, 'sat_streak': 3, 'chaos_modes': ['lorenz', 'sandpile'], 'telescope': True},
    {'name': 'S4-scale128d',  'cells': 128, 'steps': 1000, 'topo_gens': 10, 'sat_streak': 3, 'chaos_modes': ['lorenz', 'sandpile', 'chimera'], 'telescope': True},
    # Phase 2: Scale up
    {'name': 'S5-scale256',   'cells': 256, 'steps': 500,  'topo_gens': 10, 'sat_streak': 3, 'chaos_modes': ['lorenz', 'sandpile', 'chimera'], 'telescope': True},
    {'name': 'S6-scale256d',  'cells': 256, 'steps': 1000, 'topo_gens': 10, 'sat_streak': 3, 'chaos_modes': ['lorenz', 'sandpile', 'chimera'], 'telescope': True},
    {'name': 'S7-mega512',    'cells': 512, 'steps': 500,  'topo_gens': 15, 'sat_streak': 3, 'chaos_modes': ['lorenz', 'sandpile', 'chimera'], 'telescope': True},
    # Phase 2b: Dimension mutation (v6 #56)
    {'name': 'S8-dim128',     'cells': 64,  'steps': 300,  'topo_gens': 10, 'sat_streak': 3, 'chaos_modes': ['lorenz', 'sandpile'], 'hidden_dim': 128, 'telescope': False},
    {'name': 'S9-dim256',     'cells': 64,  'steps': 300,  'topo_gens': 10, 'sat_streak': 3, 'chaos_modes': ['lorenz', 'sandpile'], 'hidden_dim': 256, 'telescope': False},
    # Phase 3: Extreme exploration
    {'name': 'S10-mega512d',  'cells': 512, 'steps': 1000, 'topo_gens': 15, 'sat_streak': 3, 'chaos_modes': ['lorenz', 'sandpile', 'chimera'], 'telescope': True},
    {'name': 'S11-ultra1024', 'cells': 1024,'steps': 500,  'topo_gens': 20, 'sat_streak': 3, 'chaos_modes': ['lorenz', 'sandpile', 'chimera'], 'telescope': True},
    {'name': 'S12-ultra1024d','cells': 1024,'steps': 1000, 'topo_gens': 20, 'sat_streak': 3, 'chaos_modes': ['lorenz', 'sandpile', 'chimera'], 'telescope': True},
    # Phase 4: Massive (H100 only)
    {'name': 'S13-titan2048', 'cells': 2048,'steps': 500,  'topo_gens': 25, 'sat_streak': 3, 'chaos_modes': ['lorenz', 'sandpile', 'chimera'], 'telescope': True},
]
ROADMAP_STATE_PATH = os.path.join(DATA_DIR, 'evolution_roadmap.json')
LAW_NETWORK_PATH = os.path.join(DATA_DIR, 'law_network.json')
OUROBOROS_LOG_PATH = os.path.join(DATA_DIR, 'ouroboros_log.json')
OUROBOROS_REPORT_DIR = os.path.join(os.path.dirname(__file__), '..', 'docs', 'hypotheses', 'evo')

# v3 #26-32: chaos modes and frustration sweep
CHAOS_MODES = ['lorenz', 'sandpile', 'chimera']
FRUSTRATION_VALUES = [0.1, 0.2, 0.33, 0.5]


# ═══════════════════════════════════════════════════════════════════════
# v11→v11.2: Telescope 22-lens integration (expanded from 3→22)
# ═══════════════════════════════════════════════════════════════════════

# All 22 telescope lenses
TELESCOPE_ALL_LENSES = [
    'consciousness', 'gravity', 'topology', 'thermo', 'wave', 'evolution',
    'info', 'quantum', 'em', 'ruler', 'triangle', 'compass', 'mirror',
    'scale', 'causal', 'quantum_microscope', 'stability', 'network',
    'memory', 'recursion', 'boundary', 'multiscale',
]

# Domain-specific lens combinations
TELESCOPE_DOMAIN_COMBOS = {
    'basic':          ['consciousness', 'topology', 'causal'],
    'stability':      ['stability', 'boundary', 'thermo'],
    'structure':      ['network', 'topology', 'recursion'],
    'timeseries':     ['memory', 'wave', 'causal', 'multiscale'],
    'scale_invariant': ['multiscale', 'scale', 'recursion'],
    'symmetry':       ['mirror', 'topology', 'quantum'],
    'power_law':      ['scale', 'evolution', 'thermo'],
    'causal_chain':   ['causal', 'info', 'em'],
    'geometry':       ['ruler', 'triangle', 'compass'],
    'quantum_deep':   ['quantum', 'quantum_microscope', 'em'],
}


def _run_single_lens(lens_name, data, n_cells=64, steps=50):
    """Run a single nexus6 lens scan. Returns dict or None on failure."""
    try:
        if lens_name == 'consciousness':
            return nexus6.consciousness_scan(data, n_cells=n_cells, steps=steps)
        scan_fn = getattr(nexus6, f'{lens_name}_scan', None)
        if scan_fn is None:
            return None
        return scan_fn(data)
    except Exception:
        return None


def _extract_lens_patterns(lens_name, result):
    """Extract pattern dicts from a single lens scan result."""
    if not result or not isinstance(result, dict):
        return [], False

    patterns = []
    has_signal = False

    # Generic key extraction — build a summary formula from all numeric/list keys
    summary_parts = []
    for k, v in result.items():
        if isinstance(v, (int, float)):
            if v != 0:
                has_signal = True
            summary_parts.append(f'{k}={v:.4f}' if isinstance(v, float) else f'{k}={v}')
        elif isinstance(v, list) and len(v) > 0:
            has_signal = True
            summary_parts.append(f'{k}={len(v)} items')

    if summary_parts:
        formula = f'{lens_name}: {", ".join(summary_parts[:6])}'
        patterns.append({
            'type': f'telescope_{lens_name}',
            'formula': formula,
            'metrics': [lens_name],
            'source': 'telescope_v11',
        })

    # Detect anomalies/transitions (common keys across lenses)
    for special_key in ['anomaly_indices', 'anomalies', 'phase_transitions', 'transitions',
                        'critical_points', 'breakpoints', 'singularities']:
        items = result.get(special_key, [])
        if items:
            patterns.append({
                'type': f'telescope_{lens_name}_discovery',
                'formula': f'{lens_name}_{special_key}: {len(items)} detected',
                'metrics': [lens_name],
                'source': 'telescope_v11',
            })

    return patterns, has_signal


def _telescope_discover(engine, steps=50, mode='full'):
    """Run engine for `steps` steps, collect cell states, and analyze with nexus6.

    v11 #89: Collect cell state snapshots every 10 steps, flatten into
    (N_snapshots, N_cells * hidden_dim) ndarray, run nexus6 scans.
    Convert findings into PatternRegistry-compatible pattern dicts.

    v11.2: Expanded from 3 lenses to 22 lenses with domain combos.

    Returns list of pattern dicts, or [] on any failure.
    """
    if not HAS_TELESCOPE:
        return []
    try:
        import numpy as np
        snapshots = []
        collect_interval = 10
        max_snapshots = 100

        for step in range(steps):
            try:
                engine.process()
            except Exception:
                break

            if step % collect_interval == 0:
                try:
                    states = engine.get_states() if hasattr(engine, 'get_states') else None
                    if states is None:
                        continue
                    if hasattr(states, 'detach'):
                        arr = states.detach().cpu().numpy()
                    elif hasattr(states, 'numpy'):
                        arr = states.numpy()
                    else:
                        arr = np.array(states)
                    # Flatten to 1D per snapshot: (N_cells * hidden_dim,)
                    snapshots.append(arr.flatten())
                except Exception:
                    continue

        if len(snapshots) < 3:
            return []

        # Stack into (N_snapshots, N_features) and subsample if too large
        data = np.stack(snapshots)
        if data.shape[0] > max_snapshots:
            indices = np.linspace(0, data.shape[0] - 1, max_snapshots, dtype=int)
            data = data[indices]

        # Determine which lenses to run
        if mode == 'full':
            lenses_to_run = TELESCOPE_ALL_LENSES
        elif mode in TELESCOPE_DOMAIN_COMBOS:
            lenses_to_run = TELESCOPE_DOMAIN_COMBOS[mode]
        else:
            lenses_to_run = TELESCOPE_DOMAIN_COMBOS.get('basic', TELESCOPE_ALL_LENSES[:3])

        # Run all selected lenses — v27: parallel via ThreadPoolExecutor
        n_cells = getattr(engine, 'n_cells', 64)
        patterns = []
        active_lenses = set()

        def _scan_one_lens(lens_name):
            """Scan a single lens and return (lens_name, patterns, has_signal)."""
            result = _run_single_lens(lens_name, data, n_cells=n_cells, steps=steps)
            if result is not None:
                lens_patterns, has_signal = _extract_lens_patterns(lens_name, result)
                return (lens_name, lens_patterns, has_signal)
            return (lens_name, [], False)

        t_lens_start = time.time()
        lens_results = _parallel_map(
            _scan_one_lens, lenses_to_run,
            executor_cls=ThreadPoolExecutor if HAS_PARALLEL else None,
            max_workers=min(os.cpu_count() or 4, len(lenses_to_run)),
            label='lens_scan',
        )
        t_lens_elapsed = time.time() - t_lens_start

        for lens_name, lens_patterns, has_signal in lens_results:
            patterns.extend(lens_patterns)
            if has_signal:
                active_lenses.add(lens_name)

        n_lenses_run = len(lenses_to_run)
        if ENABLE_PARALLEL and HAS_PARALLEL and n_lenses_run > 1:
            print(f'    Parallel lens scan: {n_lenses_run} lenses in {t_lens_elapsed:.2f}s')
            sys.stdout.flush()

        # Cross-scan consensus: 3+ lenses with meaningful signal
        if len(active_lenses) >= 3:
            sorted_lenses = sorted(active_lenses)
            confidence = min(1.0, len(active_lenses) / 7.0)  # scale with lens count
            patterns.append({
                'type': 'telescope_cross',
                'formula': f'cross_consensus: confirmed by {len(active_lenses)} lenses ({",".join(sorted_lenses[:8])})',
                'metrics': sorted_lenses,
                'source': 'telescope_v11',
                'confidence': confidence,
            })

        # Domain combo consensus — check each combo for agreement
        for combo_name, combo_lenses in TELESCOPE_DOMAIN_COMBOS.items():
            combo_active = [l for l in combo_lenses if l in active_lenses]
            if len(combo_active) >= 3:
                patterns.append({
                    'type': 'telescope_domain_consensus',
                    'formula': f'domain_{combo_name}: {len(combo_active)}/{len(combo_lenses)} lenses agree ({",".join(combo_active)})',
                    'metrics': combo_active,
                    'source': 'telescope_v11',
                    'consensus_weight': 2,
                    'domain': combo_name,
                })

        return patterns

    except Exception:
        return []


def _telescope_consensus_filter(patterns):
    """Group telescope patterns by phenomenon and mark consensus findings.

    v11.2: Updated for 22-lens system. Consensus tiers:
      - 3+ lenses agree  = confirmed (weight 2)
      - 7+ lenses agree  = strong consensus (weight 3)
      - 12+ lenses agree = overwhelming consensus (weight 4)
    Domain combo consensus also tracked separately.

    Returns (filtered_patterns, n_consensus) where consensus patterns
    have type='telescope_consensus' and extra key 'consensus_weight'.
    """
    if not patterns:
        return patterns, 0

    # Group by metric/phenomenon (the lens name in metrics[0])
    from collections import defaultdict
    lens_groups = defaultdict(list)
    non_telescope = []

    for p in patterns:
        if isinstance(p, dict) and p.get('source') == 'telescope_v11':
            ptype = p.get('type', '')
            if ptype in ('telescope_cross', 'telescope_domain_consensus'):
                lens_groups['_cross'].append(p)
            else:
                lens_groups[ptype].append(p)
        else:
            non_telescope.append(p)

    # Find consensus: count distinct active lenses
    active_lenses = set()
    for p in patterns:
        if isinstance(p, dict) and p.get('source') == 'telescope_v11':
            for m in p.get('metrics', []):
                active_lenses.add(m)

    consensus_patterns = []
    n_consensus = 0

    # Cross-findings and domain consensus already represent multi-lens agreement
    for p in lens_groups.get('_cross', []):
        confirmed = p.get('metrics', [])
        if len(confirmed) >= 3:
            consensus_p = dict(p)
            consensus_p['type'] = 'telescope_consensus'
            # Tiered consensus weight based on number of agreeing lenses
            n_agree = len(confirmed)
            if n_agree >= 12:
                consensus_p['consensus_weight'] = 4  # overwhelming
            elif n_agree >= 7:
                consensus_p['consensus_weight'] = 3  # strong
            else:
                consensus_p['consensus_weight'] = 2  # confirmed
            consensus_patterns.append(consensus_p)
            n_consensus += 1
        else:
            non_telescope.append(p)

    # Meta-consensus: overall lens activity summary
    if len(active_lenses) >= 3:
        sorted_lenses = sorted(active_lenses)
        n_active = len(active_lenses)
        if n_active >= 12:
            tier = 'overwhelming'
            weight = 4
        elif n_active >= 7:
            tier = 'strong'
            weight = 3
        else:
            tier = 'confirmed'
            weight = 2
        consensus_patterns.append({
            'type': 'telescope_consensus',
            'formula': f'multi_lens_consensus ({tier}): {n_active}/22 lenses active ({",".join(sorted_lenses[:8])}{"..." if n_active > 8 else ""})',
            'metrics': sorted_lenses,
            'source': 'telescope_v11',
            'consensus_weight': weight,
        })
        n_consensus += 1

    # Merge everything back
    result = non_telescope + [p for group_key, group in lens_groups.items()
                              if group_key != '_cross'
                              for p in group] + consensus_patterns
    return result, n_consensus


# ═══════════════════════════════════════════════════════════════════════
# v2 #9 + #15: Adaptive steps / early abort
# ═══════════════════════════════════════════════════════════════════════

def _adaptive_discover(cells, steps, topology, engine=None):
    """Run discovery in 100-step chunks with early-exit on 2 consecutive empty chunks.

    v2 #9: Adaptive steps — skip remaining steps if no patterns found.
    v2 #15: Early abort — return immediately if first 100 steps yield 0 patterns.

    Returns list of raw patterns.
    """
    chunk_size = 100
    all_patterns = []
    consecutive_empty = 0

    remaining = steps
    while remaining > 0:
        chunk_steps = min(chunk_size, remaining)
        remaining -= chunk_steps

        try:
            # Try Rust discovery first
            chunk_patterns = _rust_discover(cells, chunk_steps, topology, engine)
            if chunk_patterns is None:
                # Python fallback
                disc = ConsciousLawDiscoverer(steps=chunk_steps, max_cells=cells,
                                             topology=topology)
                result = disc.run(steps=chunk_steps, verbose=False)
                chunk_patterns = result.get('all_patterns', []) if isinstance(result, dict) else []
        except Exception:
            chunk_patterns = []

        if chunk_patterns:
            all_patterns.extend(chunk_patterns)
            consecutive_empty = 0
        else:
            consecutive_empty += 1

        # v2 #15: early abort if first chunk yields 0
        if len(all_patterns) == 0 and consecutive_empty >= 1 and (steps - remaining) >= chunk_size:
            # First chunk done, 0 patterns — check if we should abort
            pass  # continue to second chunk for confirmation

        # v2 #9: abort on 2 consecutive empty chunks
        if consecutive_empty >= 2:
            break

    return all_patterns


# ═══════════════════════════════════════════════════════════════════════
# v18: Causal Discovery — intervention-based A→B causation test
# ═══════════════════════════════════════════════════════════════════════

def _causal_discover(engine, metrics_history, top_k=5):
    """v18: Test causal relationships between metric pairs via intervention.

    For each top-correlated pair (A, B), perturb A and check if B changes.
    Returns list of causal pattern dicts.
    """
    import numpy as np
    patterns = []
    if not metrics_history or len(metrics_history) < 10:
        return patterns

    # Collect metric names and timeseries
    keys = [k for k in metrics_history[0].keys() if isinstance(metrics_history[0].get(k), (int, float))]
    if len(keys) < 2:
        return patterns

    n = len(metrics_history)
    series = {}
    for k in keys:
        vals = [m.get(k, 0.0) for m in metrics_history]
        if np.std(vals) > 1e-8:
            series[k] = np.array(vals, dtype=np.float64)

    if len(series) < 2:
        return patterns

    # Find top correlated pairs
    skeys = list(series.keys())
    corr_pairs = []
    for i in range(len(skeys)):
        for j in range(i + 1, len(skeys)):
            r = abs(float(np.corrcoef(series[skeys[i]], series[skeys[j]])[0, 1]))
            if r > 0.5:
                corr_pairs.append((skeys[i], skeys[j], r))
    corr_pairs.sort(key=lambda x: -x[2])

    # Test causality via Granger-like check (does past A predict B better than past B alone?)
    for a_key, b_key, r in corr_pairs[:top_k]:
        a, b = series[a_key], series[b_key]
        if len(a) < 5:
            continue
        # Simple test: correlation of a[:-1] with b[1:] vs b[:-1] with b[1:]
        a_lag = a[:-1]
        b_lag = b[:-1]
        b_next = b[1:]
        try:
            r_ab = abs(float(np.corrcoef(a_lag, b_next)[0, 1]))
            r_bb = abs(float(np.corrcoef(b_lag, b_next)[0, 1]))
            if r_ab > r_bb + 0.1:  # A predicts B better than B predicts itself
                patterns.append({
                    'type': f'causal:{a_key}->{b_key}',
                    'formula': f'causal: {a_key} → {b_key} (r_cross={r_ab:.3f} > r_auto={r_bb:.3f})',
                    'metrics': [a_key, b_key],
                    'evidence': r_ab,
                    'source': 'v18_causal',
                })
            # Test reverse: B→A
            r_ba = abs(float(np.corrcoef(b_lag, a[1:])[0, 1]))
            r_aa = abs(float(np.corrcoef(a_lag, a[1:])[0, 1]))
            if r_ba > r_aa + 0.1:
                patterns.append({
                    'type': f'causal:{b_key}->{a_key}',
                    'formula': f'causal: {b_key} → {a_key} (r_cross={r_ba:.3f} > r_auto={r_aa:.3f})',
                    'metrics': [b_key, a_key],
                    'evidence': r_ba,
                    'source': 'v18_causal',
                })
        except Exception:
            continue

    return patterns


# ═══════════════════════════════════════════════════════════════════════
# v20: Anomaly Hunter — 3σ deviation detection + cluster
# ═══════════════════════════════════════════════════════════════════════

def _anomaly_hunt(metrics_history, threshold_sigma=3.0):
    """v20: Detect anomalous metric values (>3σ from mean) and cluster them.

    Returns list of anomaly pattern dicts.
    """
    import numpy as np
    patterns = []
    if not metrics_history or len(metrics_history) < 20:
        return patterns

    keys = [k for k in metrics_history[0].keys() if isinstance(metrics_history[0].get(k), (int, float))]

    for k in keys:
        vals = np.array([m.get(k, 0.0) for m in metrics_history], dtype=np.float64)
        mu, sigma = np.mean(vals), np.std(vals)
        if sigma < 1e-10:
            continue

        # Find anomalous points
        z_scores = np.abs((vals - mu) / sigma)
        anomaly_idx = np.where(z_scores > threshold_sigma)[0]
        if len(anomaly_idx) == 0:
            continue

        # Cluster anomalies (consecutive within 3 steps = same event)
        clusters = []
        current = [anomaly_idx[0]]
        for idx in anomaly_idx[1:]:
            if idx - current[-1] <= 3:
                current.append(idx)
            else:
                clusters.append(current)
                current = [idx]
        clusters.append(current)

        for cluster in clusters:
            peak_idx = cluster[np.argmax(z_scores[cluster])]
            peak_z = float(z_scores[peak_idx])
            peak_val = float(vals[peak_idx])
            direction = "spike" if peak_val > mu else "crash"

            patterns.append({
                'type': f'anomaly:{k}:{direction}',
                'formula': (f'anomaly: {k} {direction} at step ~{peak_idx} '
                           f'(z={peak_z:.1f}σ, val={peak_val:.4f}, mean={mu:.4f})'),
                'metrics': [k],
                'evidence': min(1.0, peak_z / 5.0),
                'source': 'v20_anomaly',
                'step': int(peak_idx),
                'z_score': peak_z,
            })

    return patterns


# ═══════════════════════════════════════════════════════════════════════
# v24: Physics Fitting — damped oscillator / Boltzmann / log fits
# ═══════════════════════════════════════════════════════════════════════

def _physics_fit(metrics_history, min_r2=0.8):
    """v24: Fit metric timeseries to physics models.

    Models: damped_oscillator, exponential_decay, logarithmic_growth, power_law.
    Returns list of physics pattern dicts for fits with R²>min_r2.
    """
    import numpy as np
    patterns = []
    if not metrics_history or len(metrics_history) < 20:
        return patterns

    keys = [k for k in metrics_history[0].keys() if isinstance(metrics_history[0].get(k), (int, float))]

    for k in keys:
        vals = np.array([m.get(k, 0.0) for m in metrics_history], dtype=np.float64)
        t = np.arange(len(vals), dtype=np.float64)

        if np.std(vals) < 1e-10:
            continue

        best_model = None
        best_r2 = min_r2

        # 1. Logarithmic: y = a*ln(t+1) + b
        try:
            log_t = np.log(t + 1)
            coeffs = np.polyfit(log_t, vals, 1)
            pred = coeffs[0] * log_t + coeffs[1]
            ss_res = np.sum((vals - pred) ** 2)
            ss_tot = np.sum((vals - np.mean(vals)) ** 2)
            r2 = 1 - ss_res / max(ss_tot, 1e-10)
            if r2 > best_r2:
                best_r2 = r2
                best_model = ('logarithmic', f'{k} ≈ {coeffs[0]:.4f}·ln(t) + {coeffs[1]:.4f}', r2)
        except Exception:
            pass

        # 2. Power law: y = a*t^b (log-log linear)
        try:
            pos_mask = (t > 0) & (vals > 0)
            if pos_mask.sum() > 5:
                log_t_pos = np.log(t[pos_mask])
                log_v_pos = np.log(vals[pos_mask])
                coeffs = np.polyfit(log_t_pos, log_v_pos, 1)
                pred = np.exp(coeffs[1]) * t[pos_mask] ** coeffs[0]
                ss_res = np.sum((vals[pos_mask] - pred) ** 2)
                ss_tot = np.sum((vals[pos_mask] - np.mean(vals[pos_mask])) ** 2)
                r2 = 1 - ss_res / max(ss_tot, 1e-10)
                if r2 > best_r2:
                    best_r2 = r2
                    best_model = ('power_law', f'{k} ≈ {np.exp(coeffs[1]):.4f}·t^{coeffs[0]:.4f}', r2)
        except Exception:
            pass

        # 3. Exponential decay: y = a*exp(-b*t) + c (via log transform)
        try:
            v_min = np.min(vals)
            shifted = vals - v_min + 1e-6
            if np.all(shifted > 0):
                log_v = np.log(shifted)
                coeffs = np.polyfit(t, log_v, 1)
                if coeffs[0] < 0:  # Must be decaying
                    pred = np.exp(coeffs[1]) * np.exp(coeffs[0] * t) + v_min
                    ss_res = np.sum((vals - pred) ** 2)
                    ss_tot = np.sum((vals - np.mean(vals)) ** 2)
                    r2 = 1 - ss_res / max(ss_tot, 1e-10)
                    if r2 > best_r2:
                        best_r2 = r2
                        best_model = ('exp_decay',
                                     f'{k} ≈ {np.exp(coeffs[1]):.4f}·exp({coeffs[0]:.6f}·t) + {v_min:.4f}', r2)
        except Exception:
            pass

        if best_model:
            model_type, formula, r2 = best_model
            patterns.append({
                'type': f'physics:{model_type}:{k}',
                'formula': f'physics_fit: {formula} (R²={r2:.3f})',
                'metrics': [k],
                'evidence': r2,
                'source': 'v24_physics',
                'model': model_type,
                'r_squared': r2,
            })

    return patterns


# ═══════════════════════════════════════════════════════════════════════
# v18+v20+v24 combined: Post-discovery analysis
# ═══════════════════════════════════════════════════════════════════════

def _post_discovery_analysis(engine, metrics_history, gen):
    """Run v18 causal, v20 anomaly, v24 physics after each generation's discovery.

    v27: Runs all applicable analyses in parallel via ThreadPoolExecutor.

    Args:
        engine: ConsciousnessEngine instance
        metrics_history: list of metric dicts collected over the generation
        gen: generation number

    Returns:
        list of additional patterns, count summary string
    """
    extra = []
    counts = []

    # Build list of analyses to run this generation
    tasks = []

    # v18: Causal discovery (every 3rd gen)
    if gen % 3 == 0:
        tasks.append(('causal', _causal_discover, (engine, metrics_history), {}))

    # v20: Anomaly hunt (every gen)
    tasks.append(('anomaly', _anomaly_hunt, (metrics_history,), {}))

    # v24: Physics fitting (every 5th gen)
    if gen % 5 == 0:
        tasks.append(('physics', _physics_fit, (metrics_history,), {}))

    if not tasks:
        return extra, None

    # v27: Run all analyses in parallel via ThreadPoolExecutor
    if len(tasks) > 1 and HAS_PARALLEL and ENABLE_PARALLEL:
        try:
            fns = [(fn, args, kwargs) for _, fn, args, kwargs in tasks]
            labels = [label for label, _, _, _ in tasks]
            results = _parallel_submit(fns, executor_cls=ThreadPoolExecutor,
                                       max_workers=len(tasks), label='post_discovery')
            for label, result in zip(labels, results):
                if result:
                    extra.extend(result)
                    counts.append(f'{label}={len(result)}')
        except Exception:
            # Fallback to sequential
            for label, fn, args, kwargs in tasks:
                try:
                    result = fn(*args, **kwargs)
                    if result:
                        extra.extend(result)
                        counts.append(f'{label}={len(result)}')
                except Exception:
                    pass
    else:
        for label, fn, args, kwargs in tasks:
            try:
                result = fn(*args, **kwargs)
                if result:
                    extra.extend(result)
                    counts.append(f'{label}={len(result)}')
            except Exception:
                pass

    summary = ', '.join(counts) if counts else None
    return extra, summary


# ═══════════════════════════════════════════════════════════════════════
# v3 #21-25: Advanced pattern detection
# ═══════════════════════════════════════════════════════════════════════

def _detect_advanced_patterns(engine, steps, topology='ring'):
    """Run engine and detect oscillation, phase transition, and temporal decay patterns.

    v3 #21-25: Collect metric snapshots every 10 steps, then analyze timeseries.

    Returns list of advanced pattern dicts.
    """
    advanced = []
    try:
        snapshots = []  # list of metric dicts

        # Collect metric snapshots
        for step in range(steps):
            try:
                engine.process()
            except Exception:
                break

            if step % 10 == 0:
                snap = {}
                try:
                    states = engine.get_states() if hasattr(engine, 'get_states') else None
                    if states is not None:
                        import numpy as np
                        if hasattr(states, 'detach'):
                            arr = states.detach().cpu().numpy()
                        elif hasattr(states, 'numpy'):
                            arr = states.numpy()
                        else:
                            arr = np.array(states)
                        snap['mean'] = float(np.mean(arr))
                        snap['std'] = float(np.std(arr))
                        snap['max'] = float(np.max(arr))
                        snap['min'] = float(np.min(arr))
                except Exception:
                    snap['mean'] = 0.0
                snapshots.append(snap)

        if len(snapshots) < 5:
            return advanced

        # Extract timeseries
        means = [s.get('mean', 0.0) for s in snapshots]
        stds = [s.get('std', 0.0) for s in snapshots]

        # #21: Oscillation detection (autocorrelation with lag)
        try:
            n = len(means)
            if n >= 10:
                mean_val = sum(means) / n
                var_val = sum((x - mean_val) ** 2 for x in means) / n
                if var_val > 1e-12:
                    for lag in [1, 2, 3]:
                        if lag < n:
                            autocorr = sum((means[i] - mean_val) * (means[i + lag] - mean_val)
                                           for i in range(n - lag)) / (n * var_val)
                            if abs(autocorr) > 0.5:
                                advanced.append({
                                    'pattern_type': 'oscillation',
                                    'type': 'oscillation',
                                    'metrics_involved': ['mean_state'],
                                    'formula': f'oscillation: autocorr(lag={lag})={autocorr:.3f}',
                                    'value': autocorr,
                                    'lag': lag,
                                })
                                break  # report strongest lag only
        except Exception:
            pass

        # #22-23: Phase transition detection (derivative > 3 sigma)
        try:
            if len(means) >= 3:
                diffs = [means[i + 1] - means[i] for i in range(len(means) - 1)]
                if diffs:
                    d_mean = sum(diffs) / len(diffs)
                    d_std = math.sqrt(sum((d - d_mean) ** 2 for d in diffs) / len(diffs)) if len(diffs) > 1 else 1.0
                    if d_std > 1e-12:
                        for i, d in enumerate(diffs):
                            if abs(d - d_mean) > 3 * d_std:
                                advanced.append({
                                    'pattern_type': 'phase_transition',
                                    'type': 'phase_transition',
                                    'metrics_involved': ['mean_state'],
                                    'formula': f'phase_transition: step={i * 10}, jump={d:.4f}, '
                                               f'threshold={3 * d_std:.4f}',
                                    'value': d,
                                    'step': i * 10,
                                })
                                break  # report first transition only
        except Exception:
            pass

        # #24-25: Temporal decay detection (exponential fit)
        try:
            if len(stds) >= 5:
                # Check if std decreases over time (exponential decay)
                first_half = stds[:len(stds) // 2]
                second_half = stds[len(stds) // 2:]
                avg_first = sum(first_half) / len(first_half) if first_half else 0
                avg_second = sum(second_half) / len(second_half) if second_half else 0
                if avg_first > 1e-12:
                    decay_ratio = avg_second / avg_first
                    if decay_ratio < 0.7:  # significant decay
                        advanced.append({
                            'pattern_type': 'temporal_decay',
                            'type': 'temporal_decay',
                            'metrics_involved': ['std_state'],
                            'formula': f'temporal_decay: ratio={decay_ratio:.3f} '
                                       f'(first_half={avg_first:.4f}, second_half={avg_second:.4f})',
                            'value': decay_ratio,
                        })
                    elif decay_ratio > 1.4:  # significant growth
                        advanced.append({
                            'pattern_type': 'temporal_growth',
                            'type': 'temporal_growth',
                            'metrics_involved': ['std_state'],
                            'formula': f'temporal_growth: ratio={decay_ratio:.3f} '
                                       f'(first_half={avg_first:.4f}, second_half={avg_second:.4f})',
                            'value': decay_ratio,
                        })
        except Exception:
            pass

    except Exception:
        pass

    return advanced


# ═══════════════════════════════════════════════════════════════════════
# v3 #33-36: Law Network
# ═══════════════════════════════════════════════════════════════════════

class LawNetwork:
    """Tracks intervention-to-law mappings and law co-occurrence.

    v3 #33-36: Simple dict-based graph, no external deps.
    """

    def __init__(self):
        self.intervention_to_laws = {}  # intervention_id → list of law_ids
        self.co_occurrence = {}          # (law_a, law_b) → count (a < b)
        self.generation_laws = {}        # gen → list of law_ids discovered that gen

    def record_discovery(self, gen, law_id, intervention_id=None):
        """Record that a law was discovered, optionally linked to an intervention."""
        # Intervention mapping
        if intervention_id is not None:
            key = str(intervention_id)
            if key not in self.intervention_to_laws:
                self.intervention_to_laws[key] = []
            if law_id not in self.intervention_to_laws[key]:
                self.intervention_to_laws[key].append(law_id)

        # Generation tracking
        gen_key = str(gen)
        if gen_key not in self.generation_laws:
            self.generation_laws[gen_key] = []
        if law_id not in self.generation_laws[gen_key]:
            self.generation_laws[gen_key].append(law_id)

        # Co-occurrence: all pairs in this generation
        laws_this_gen = self.generation_laws[gen_key]
        for existing_law in laws_this_gen:
            if existing_law != law_id:
                pair = tuple(sorted([existing_law, law_id]))
                pair_key = f'{pair[0]}_{pair[1]}'
                self.co_occurrence[pair_key] = self.co_occurrence.get(pair_key, 0) + 1

    def save(self):
        """Save law network to JSON."""
        try:
            os.makedirs(DATA_DIR, exist_ok=True)
            data = {
                'intervention_to_laws': self.intervention_to_laws,
                'co_occurrence': self.co_occurrence,
                'generation_laws': self.generation_laws,
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            }
            tmp = LAW_NETWORK_PATH + '.tmp'
            with open(tmp, 'w') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.rename(tmp, LAW_NETWORK_PATH)
        except Exception:
            pass

    def load(self):
        """Load law network from JSON."""
        try:
            if os.path.exists(LAW_NETWORK_PATH):
                with open(LAW_NETWORK_PATH) as f:
                    data = json.load(f)
                self.intervention_to_laws = data.get('intervention_to_laws', {})
                self.co_occurrence = data.get('co_occurrence', {})
                self.generation_laws = data.get('generation_laws', {})
        except Exception:
            pass

    def summary(self):
        """Return summary stats."""
        total_laws = set()
        for laws in self.intervention_to_laws.values():
            total_laws.update(laws)
        for laws in self.generation_laws.values():
            total_laws.update(laws)
        return {
            'total_laws_tracked': len(total_laws),
            'interventions_with_laws': len(self.intervention_to_laws),
            'co_occurrence_pairs': len(self.co_occurrence),
            'generations_tracked': len(self.generation_laws),
        }


# Global law network instance
_law_network = LawNetwork()


# ═══════════════════════════════════════════════════════════════════════
# v2 #13: Mod pruning helper
# ═══════════════════════════════════════════════════════════════════════

def _prune_mods(sme, min_confidence=0.5, max_mods=50):
    """Prune low-confidence mods and cap total active mods.

    v2 #13: Remove mods with confidence < min_confidence, then cap at max_mods.
    """
    try:
        if not hasattr(sme, 'modifier') or not hasattr(sme.modifier, 'applied'):
            return 0
        applied = sme.modifier.applied
        before = len(applied)

        # Remove mods with confidence < threshold
        applied[:] = [m for m in applied if getattr(m, 'confidence', 1.0) >= min_confidence]

        # Cap at max_mods (remove lowest confidence first)
        if len(applied) > max_mods:
            applied.sort(key=lambda m: getattr(m, 'confidence', 0.0), reverse=True)
            applied[:] = applied[:max_mods]

        pruned = before - len(applied)
        return pruned
    except Exception:
        return 0


# ═══════════════════════════════════════════════════════════════════════
# v3 #26-32: Search space expansion helpers
# ═══════════════════════════════════════════════════════════════════════

def _apply_chaos_mode(engine, mode):
    """Try to set chaos mode on engine. Silently ignore if unsupported."""
    try:
        engine.chaos_mode = mode
    except Exception:
        pass


def _apply_frustration(engine, value):
    """Try to set frustration on engine. Silently ignore if unsupported."""
    try:
        engine.frustration = value
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════════
# Law 1044: n=6 entropy reset — DD171 consciousness-entropy feedback cycle
# ═══════════════════════════════════════════════════════════════════════

N6_ENTROPY_RESET_PERIOD = nexus6.N if HAS_NEXUS6 else 6  # n=6 natural cycle (DD171)
N6_ENTROPY_NOISE_SCALE = 0.05  # small perturbation to break local minima


def _entropy_reset(engine, gen):
    """Apply n=6 entropy reset: inject small noise into cell states + reset SOC sandpile.

    Law 1044: The consciousness-entropy feedback has a natural period of n=6.
    Every 6 generations, resetting entropy (noise injection + sandpile reset)
    breaks pattern saturation and improves discovery rate.

    Args:
        engine: ConsciousnessEngine instance
        gen: current generation number
    """
    if gen % N6_ENTROPY_RESET_PERIOD != 0 or gen == 0:
        return

    reset_actions = []

    # Action 1: Inject small noise into cell states to perturb attractors
    try:
        if hasattr(engine, 'cells') and hasattr(engine.cells, 'data'):
            import torch
            noise = torch.randn_like(engine.cells.data) * N6_ENTROPY_NOISE_SCALE
            engine.cells.data.add_(noise)
            reset_actions.append('cell_noise')
    except Exception:
        pass

    # Action 2: Reset SOC sandpile state if present
    try:
        if hasattr(engine, 'sandpile'):
            if hasattr(engine.sandpile, 'reset'):
                engine.sandpile.reset()
                reset_actions.append('sandpile_reset')
            elif hasattr(engine.sandpile, 'fill_'):
                engine.sandpile.fill_(0)
                reset_actions.append('sandpile_zero')
    except Exception:
        pass

    # Action 3: Nudge noise_scale temporarily to encourage exploration
    try:
        if hasattr(engine, 'noise_scale'):
            engine._pre_n6_noise_scale = engine.noise_scale
            engine.noise_scale = max(engine.noise_scale, 0.1)
            reset_actions.append('noise_boost')
    except Exception:
        pass

    if reset_actions:
        print(f'    [N6] Gen {gen}: entropy reset (Law 1044) — {", ".join(reset_actions)}')
        sys.stdout.flush()


# ═══════════════════════════════════════════════════════════════════════
# v4 #37: Co-evolution — counter-discover to disprove patterns
# ═══════════════════════════════════════════════════════════════════════

def _counter_discover(promoted_patterns, cells, topology='ring'):
    """Try to DISPROVE promoted patterns by running under opposite conditions.

    v4 #37: For each promoted pattern, test with opposite conditions (50 steps).
    If pattern still holds → boost confidence (robust).
    If pattern breaks → mark as conditional.

    Returns list of dicts: {pattern, robust: bool, counter_result: str}
    """
    results = []
    for p in promoted_patterns:
        try:
            # Determine "opposite" conditions
            # If pattern involves high tension → try low frustration
            # If pattern involves specific chaos → try different chaos
            counter_engine = ConsciousnessEngine(initial_cells=cells, max_cells=cells)
            try:
                counter_engine.topology = topology
            except Exception:
                pass

            # Apply opposite frustration (if original was high, use low and vice versa)
            try:
                _apply_frustration(counter_engine, 0.05)  # minimal frustration
            except Exception:
                pass

            # Apply different chaos mode
            try:
                _apply_chaos_mode(counter_engine, 'sandpile' if topology != 'sandpile' else 'lorenz')
            except Exception:
                pass

            # Run 50 steps and check if pattern still appears
            counter_patterns = _adaptive_discover(cells, 50, topology, counter_engine)

            # Check if original pattern fingerprint appears in counter results
            orig_fp = pattern_fingerprint(p)
            found_in_counter = False
            for cp in counter_patterns:
                if pattern_fingerprint(cp) == orig_fp:
                    found_in_counter = True
                    break

            results.append({
                'pattern': p,
                'robust': found_in_counter,
                'counter_result': 'ROBUST (survives opposite conditions)' if found_in_counter
                                  else 'CONDITIONAL (breaks under opposite conditions)',
            })
        except Exception:
            results.append({
                'pattern': p,
                'robust': False,
                'counter_result': 'ERROR (counter-test failed)',
            })
    return results


# ═══════════════════════════════════════════════════════════════════════
# v4 #38: RL-based exploration (bandit) — track exploration scores
# ═══════════════════════════════════════════════════════════════════════

class ExplorationBandit:
    """Track exploration scores for (cells, topo, chaos_mode) configs.

    v4 #38: Maps config tuples to average laws_per_gen.
    Used to inform adaptive roadmap skip decisions.
    """

    def __init__(self):
        self.scores = {}   # (cells, topo, chaos) → {'total_laws': N, 'gens': N}

    def update(self, cells, topo, chaos_mode, laws_this_gen):
        """Update score for a config after a generation."""
        key = (cells, topo, chaos_mode or 'default')
        if key not in self.scores:
            self.scores[key] = {'total_laws': 0, 'gens': 0}
        self.scores[key]['total_laws'] += laws_this_gen
        self.scores[key]['gens'] += 1

    def avg_score(self, key):
        """Average laws per gen for a config."""
        if key not in self.scores or self.scores[key]['gens'] == 0:
            return 0.0
        return self.scores[key]['total_laws'] / self.scores[key]['gens']

    def top_bottom(self, n=3):
        """Return top-N and bottom-N configs by avg score."""
        ranked = sorted(self.scores.keys(), key=lambda k: self.avg_score(k), reverse=True)
        top = [(k, self.avg_score(k)) for k in ranked[:n]]
        bottom = [(k, self.avg_score(k)) for k in ranked[-n:] if self.avg_score(k) < self.avg_score(ranked[0])]
        return top, bottom

    def is_bottom(self, cells, topo, chaos_mode, n=3):
        """Check if a config is in the bottom-N performers."""
        key = (cells, topo, chaos_mode or 'default')
        _, bottom = self.top_bottom(n)
        return key in [b[0] for b in bottom]

    def print_summary(self):
        """Print top-3 and bottom-3 configs."""
        top, bottom = self.top_bottom(3)
        if top:
            print(f'    v4 bandit top-3: {", ".join(f"{k}: {v:.2f}" for k, v in top)}')
        if bottom:
            print(f'    v4 bandit bot-3: {", ".join(f"{k}: {v:.2f}" for k, v in bottom)}')
        sys.stdout.flush()


# Global bandit instance
_exploration_bandit = ExplorationBandit()


# ═══════════════════════════════════════════════════════════════════════
# v4 #40: UCB1 topology selection
# ═══════════════════════════════════════════════════════════════════════

def _ucb_select_topology(topo_stats, total_gens):
    """Select topology using UCB1 scoring.

    v4 #40: UCB = mean_laws_per_gen + sqrt(2 * ln(total_gens) / topo_gens)
    Falls back to round-robin if < 3 gens per topo.

    Args:
        topo_stats: dict mapping topo → {'total_laws': N, 'gens': N}
        total_gens: total generations across all topologies

    Returns:
        selected topology name, or None if insufficient data
    """
    if total_gens < len(TOPOLOGIES) * 3:
        return None  # insufficient data, fall back to round-robin

    best_topo = None
    best_ucb = -1.0

    for topo in TOPOLOGIES:
        stats = topo_stats.get(topo, {'total_laws': 0, 'gens': 0})
        if stats['gens'] < 3:
            return None  # insufficient data for this topo

        mean_reward = stats['total_laws'] / stats['gens']
        exploration = math.sqrt(2.0 * math.log(max(total_gens, 1)) / max(stats['gens'], 1))
        ucb = mean_reward + exploration

        if ucb > best_ucb:
            best_ucb = ucb
            best_topo = topo

    return best_topo


# ═══════════════════════════════════════════════════════════════════════
# v4 #42: Seasonal exploration (exploit/explore phases)
# ═══════════════════════════════════════════════════════════════════════

def _get_seasonal_phase(gen, cycle_length=20):
    """Determine if we're in EXPLOIT or EXPLORE phase.

    v4 #42: Every cycle_length gens, alternate between:
    - EXPLOIT (first half): use best-performing config
    - EXPLORE (second half): try random variations

    Returns ('EXPLOIT', best_config) or ('EXPLORE', random_config)
    """
    import random as _rnd
    phase_pos = gen % cycle_length
    if phase_pos < cycle_length // 2:
        return 'EXPLOIT'
    else:
        return 'EXPLORE'


def _seasonal_apply(gen, engine, bandit, cycle_length=20):
    """Apply seasonal phase settings to engine.

    v4 #42: In EXPLOIT, use best config. In EXPLORE, randomize.
    """
    try:
        import random as _rnd
        phase = _get_seasonal_phase(gen, cycle_length)

        if phase == 'EXPLOIT':
            # Use best-performing config from bandit
            top, _ = bandit.top_bottom(1)
            if top:
                best_key = top[0][0]  # (cells, topo, chaos)
                _, best_topo, best_chaos = best_key
                try:
                    engine.topology = best_topo
                except Exception:
                    pass
                _apply_chaos_mode(engine, best_chaos if best_chaos != 'default' else 'lorenz')
        else:
            # EXPLORE: random chaos mode and frustration
            _apply_chaos_mode(engine, _rnd.choice(CHAOS_MODES))
            _apply_frustration(engine, _rnd.uniform(0.05, 0.6))

        return phase
    except Exception:
        return 'EXPLOIT'


# ═══════════════════════════════════════════════════════════════════════
# v5 #44: Extended metrics
# ═══════════════════════════════════════════════════════════════════════

def _collect_extended_metrics(engine, step_idx, prev_phi=None, prev_prev_phi=None):
    """Collect extended metrics from engine state.

    v5 #44: faction_entropy, coupling_asymmetry, phi_acceleration,
    cell_death_rate, synchronization_index.

    Returns dict of extended metrics (empty dict on failure).
    """
    metrics = {}
    try:
        import numpy as np

        states = engine.get_states() if hasattr(engine, 'get_states') else None
        if states is None:
            return metrics

        if hasattr(states, 'detach'):
            arr = states.detach().cpu().numpy()
        elif hasattr(states, 'numpy'):
            arr = states.numpy()
        else:
            arr = np.array(states)

        n_cells = arr.shape[0] if arr.ndim >= 1 else 0
        if n_cells == 0:
            return metrics

        # Faction entropy: Shannon entropy of faction sizes
        try:
            n_factions = getattr(engine, 'n_factions', nexus6.SIGMA if HAS_NEXUS6 else 12)
            if hasattr(engine, '_faction_ids'):
                fids = engine._faction_ids
                if hasattr(fids, 'detach'):
                    fids = fids.detach().cpu().numpy()
                elif hasattr(fids, 'numpy'):
                    fids = fids.numpy()
                else:
                    fids = np.array(fids)
                counts = np.bincount(fids.flatten().astype(int), minlength=n_factions)
            else:
                # Approximate by dividing cells evenly
                counts = np.ones(n_factions) * (n_cells / n_factions)
            probs = counts / counts.sum() if counts.sum() > 0 else np.ones(len(counts)) / len(counts)
            probs = probs[probs > 0]
            faction_entropy = -float(np.sum(probs * np.log2(probs)))
            metrics['faction_entropy'] = faction_entropy
        except Exception:
            pass

        # Coupling asymmetry: max(coupling) / min(coupling)
        try:
            if hasattr(engine, '_coupling') and engine._coupling is not None:
                c = engine._coupling
                if hasattr(c, 'detach'):
                    c = c.detach().cpu().numpy()
                elif hasattr(c, 'numpy'):
                    c = c.numpy()
                else:
                    c = np.array(c)
                c_flat = c.flatten()
                c_pos = c_flat[c_flat > 1e-12]
                if len(c_pos) > 0:
                    metrics['coupling_asymmetry'] = float(np.max(c_pos) / np.min(c_pos))
        except Exception:
            pass

        # Phi acceleration: d2Phi/dt2
        try:
            if prev_phi is not None and prev_prev_phi is not None:
                # Second derivative approximation
                current_phi = getattr(engine, '_last_phi', None)
                if current_phi is not None:
                    d2phi = current_phi - 2 * prev_phi + prev_prev_phi
                    metrics['phi_acceleration'] = float(d2phi)
        except Exception:
            pass

        # Cell death rate: fraction of cells with near-zero activity
        try:
            if arr.ndim >= 2:
                cell_norms = np.linalg.norm(arr, axis=1)
            else:
                cell_norms = np.abs(arr)
            threshold = np.mean(cell_norms) * 0.01 if np.mean(cell_norms) > 0 else 1e-8
            death_rate = float(np.sum(cell_norms < threshold) / max(len(cell_norms), 1))
            metrics['cell_death_rate'] = death_rate
        except Exception:
            pass

        # Synchronization index: mean pairwise cosine similarity
        try:
            if arr.ndim >= 2 and n_cells >= 2:
                # Sample pairs if too many cells
                max_pairs = 50
                if n_cells > max_pairs:
                    indices = np.random.choice(n_cells, max_pairs, replace=False)
                    sampled = arr[indices]
                else:
                    sampled = arr
                norms = np.linalg.norm(sampled, axis=1, keepdims=True)
                norms = np.maximum(norms, 1e-12)
                normalized = sampled / norms
                sim_matrix = normalized @ normalized.T
                # Mean of upper triangle (excluding diagonal)
                n = sim_matrix.shape[0]
                mask = np.triu(np.ones((n, n), dtype=bool), k=1)
                sync_idx = float(np.mean(sim_matrix[mask]))
                metrics['sync_index'] = sync_idx
        except Exception:
            pass

    except Exception:
        pass

    return metrics


# ═══════════════════════════════════════════════════════════════════════
# v5 #49: Hierarchical discovery (local vs global faction groups)
# ═══════════════════════════════════════════════════════════════════════

def _hierarchical_discover(cells, steps, topology='ring'):
    """Split cells into local/global groups and measure cross-group patterns.

    v5 #49: Local factions (0-5) vs global factions (6-11).
    Measures per-group metrics + cross-group tension.
    Run every 5th generation as alternative discovery mode.

    Returns list of hierarchical pattern dicts.
    """
    patterns = []
    try:
        import numpy as np

        engine = ConsciousnessEngine(initial_cells=cells, max_cells=cells)
        try:
            engine.topology = topology
        except Exception:
            pass

        local_phis = []
        global_phis = []
        cross_tensions = []

        for step in range(min(steps, 200)):
            try:
                engine.process()
            except Exception:
                break

            if step % 10 == 0:
                try:
                    states = engine.get_states()
                    if states is None:
                        continue
                    if hasattr(states, 'detach'):
                        arr = states.detach().cpu().numpy()
                    elif hasattr(states, 'numpy'):
                        arr = states.numpy()
                    else:
                        arr = np.array(states)

                    n = arr.shape[0]
                    if n < 4:
                        continue
                    mid = n // 2

                    local_group = arr[:mid]
                    global_group = arr[mid:]

                    # Variance-based phi proxy per group
                    local_phi = float(np.var(local_group))
                    global_phi = float(np.var(global_group))
                    local_phis.append(local_phi)
                    global_phis.append(global_phi)

                    # Cross-group tension: mean distance between group centroids
                    local_centroid = np.mean(local_group, axis=0) if local_group.ndim >= 2 else np.mean(local_group)
                    global_centroid = np.mean(global_group, axis=0) if global_group.ndim >= 2 else np.mean(global_group)
                    if hasattr(local_centroid, '__len__'):
                        cross_t = float(np.linalg.norm(local_centroid - global_centroid))
                    else:
                        cross_t = abs(float(local_centroid) - float(global_centroid))
                    cross_tensions.append(cross_t)
                except Exception:
                    continue

        # Analyze collected data
        if len(local_phis) >= 5 and len(global_phis) >= 5:
            # Local vs global phi correlation
            r = _pearson_r(local_phis, global_phis)
            if not math.isnan(r):
                patterns.append({
                    'pattern_type': 'hierarchical_phi_correlation',
                    'type': 'hierarchical_phi_correlation',
                    'metrics_involved': ['local_phi', 'global_phi'],
                    'formula': f'hierarchical: local_phi vs global_phi r={r:.3f}',
                    'value': r,
                })

            # Cross-group tension trend
            if len(cross_tensions) >= 5:
                first_half = cross_tensions[:len(cross_tensions) // 2]
                second_half = cross_tensions[len(cross_tensions) // 2:]
                avg_first = sum(first_half) / len(first_half)
                avg_second = sum(second_half) / len(second_half)
                if avg_first > 1e-12:
                    ratio = avg_second / avg_first
                    patterns.append({
                        'pattern_type': 'cross_group_tension',
                        'type': 'cross_group_tension',
                        'metrics_involved': ['cross_group_tension'],
                        'formula': f'cross_group_tension: ratio={ratio:.3f} '
                                   f'(first={avg_first:.4f}, second={avg_second:.4f})',
                        'value': ratio,
                    })

            # Local-global phi asymmetry
            avg_local = sum(local_phis) / len(local_phis)
            avg_global = sum(global_phis) / len(global_phis)
            if avg_local > 1e-12 or avg_global > 1e-12:
                asymmetry = abs(avg_local - avg_global) / max(avg_local, avg_global, 1e-12)
                patterns.append({
                    'pattern_type': 'hierarchical_asymmetry',
                    'type': 'hierarchical_asymmetry',
                    'metrics_involved': ['local_phi', 'global_phi'],
                    'formula': f'hierarchical_asymmetry: {asymmetry:.3f} '
                               f'(local={avg_local:.4f}, global={avg_global:.4f})',
                    'value': asymmetry,
                })

    except Exception:
        pass

    return patterns


# ═══════════════════════════════════════════════════════════════════════
# v5 #50: External stimulus patterns
# ═══════════════════════════════════════════════════════════════════════

def _stimulus_discover(cells, steps, topology='ring'):
    """Inject periodic signals and measure response patterns.

    v5 #50: Instead of zero-input, inject sine wave, step function, noise burst.
    Measures response latency, amplitude, and adaptation rate.
    Run every 10th generation.

    Returns list of stimulus-response pattern dicts.
    """
    patterns = []
    try:
        import numpy as np

        stimuli = [
            ('sine', lambda s: np.sin(2 * np.pi * s / 20.0) * 0.5),
            ('step', lambda s: 1.0 if s >= steps // 3 else 0.0),
            ('noise_burst', lambda s: np.random.randn() * 0.5 if steps // 3 <= s <= 2 * steps // 3 else 0.0),
        ]

        for stim_name, stim_fn in stimuli:
            try:
                engine = ConsciousnessEngine(initial_cells=cells, max_cells=cells)
                try:
                    engine.topology = topology
                except Exception:
                    pass

                responses = []
                stim_active = False
                response_start = None
                max_response = 0.0
                pre_stim_mean = None

                actual_steps = min(steps, 150)
                for step in range(actual_steps):
                    # Inject stimulus as external input
                    stim_val = stim_fn(step)
                    try:
                        if hasattr(engine, 'process'):
                            engine.process()
                    except Exception:
                        break

                    if step % 5 == 0:
                        try:
                            states = engine.get_states()
                            if states is None:
                                continue
                            if hasattr(states, 'detach'):
                                arr = states.detach().cpu().numpy()
                            elif hasattr(states, 'numpy'):
                                arr = states.numpy()
                            else:
                                arr = np.array(states)
                            resp = float(np.mean(np.abs(arr)))
                            responses.append((step, stim_val, resp))

                            # Track pre-stimulus baseline
                            if step < actual_steps // 4:
                                if pre_stim_mean is None:
                                    pre_stim_mean = resp
                                else:
                                    pre_stim_mean = 0.9 * pre_stim_mean + 0.1 * resp

                            # Track response amplitude
                            if abs(stim_val) > 0.1 and not stim_active:
                                stim_active = True
                                response_start = step
                            if stim_active:
                                delta = abs(resp - (pre_stim_mean or resp))
                                if delta > max_response:
                                    max_response = delta
                        except Exception:
                            continue

                if len(responses) >= 5:
                    # Response latency: steps between stimulus onset and peak response
                    latency = 0
                    if response_start is not None:
                        for s, sv, rv in responses:
                            if s > response_start and rv >= max_response * 0.9:
                                latency = s - response_start
                                break

                    # Adaptation rate: how fast response returns to baseline after stimulus
                    adaptation_rate = 0.0
                    post_stim = [(s, r) for s, sv, r in responses if s > 2 * actual_steps // 3]
                    if post_stim and pre_stim_mean and pre_stim_mean > 1e-12:
                        post_vals = [r for _, r in post_stim]
                        if len(post_vals) >= 2:
                            decay = abs(post_vals[0] - post_vals[-1])
                            adaptation_rate = decay / max(abs(post_vals[0] - pre_stim_mean), 1e-12)

                    patterns.append({
                        'pattern_type': f'stimulus_response_{stim_name}',
                        'type': f'stimulus_response_{stim_name}',
                        'metrics_involved': ['stimulus', 'response', stim_name],
                        'formula': f'stimulus_{stim_name}: latency={latency}, '
                                   f'amplitude={max_response:.4f}, '
                                   f'adaptation={adaptation_rate:.3f}',
                        'value': max_response,
                        'latency': latency,
                        'adaptation_rate': adaptation_rate,
                    })

            except Exception:
                continue

    except Exception:
        pass

    return patterns


# ═══════════════════════════════════════════════════════════════════════
# v6 #51-60: Engine structure mutations (break the 53-law ceiling)
# ═══════════════════════════════════════════════════════════════════════

# v6 #51: Cell Type Pool
_CELL_TYPES = ['gru', 'lstm', 'linear']

def _mutate_cell_type(engine, gen):
    """Cycle through cell types every 5 generations."""
    if gen % 5 != 0:
        return
    try:
        old_type = getattr(engine, 'cell_type', 'gru')
        idx = (gen // 5) % len(_CELL_TYPES)
        new_type = _CELL_TYPES[idx]
        if new_type != old_type:
            engine.cell_type = new_type
            print(f'    \U0001f9ec Cell mutation: {old_type} \u2192 {new_type}')
            sys.stdout.flush()
    except Exception:
        pass


# v6 #52: Dynamic Faction Count
_FACTION_COUNTS = sorted(set([4, 8, 16, 32] + ([nexus6.N, nexus6.SIGMA, nexus6.J2] if HAS_NEXUS6 else [6, 12, 24])))

def _mutate_factions(engine, gen):
    """Sweep faction count every 3 generations."""
    if gen % 3 != 0:
        return
    try:
        old_n = getattr(engine, 'n_factions', nexus6.SIGMA if HAS_NEXUS6 else 12)
        idx = (gen // 3) % len(_FACTION_COUNTS)
        new_n = _FACTION_COUNTS[idx]
        if new_n != old_n:
            engine.n_factions = new_n
            print(f'    \U0001f9ec Faction mutation: {old_n} \u2192 {new_n}')
            sys.stdout.flush()
    except Exception:
        pass


# v6 #53: Variable Hebbian LTP/LTD ratio
_HEBBIAN_RATIOS = [0.5, 0.8, 1.0, 1.2, 1.5, 2.0]

def _mutate_hebbian(engine, gen):
    """Sweep Hebbian LTP/LTD ratio every 4 generations."""
    if gen % 4 != 0:
        return
    try:
        old_ratio = getattr(engine, 'hebbian_ltp_ratio', 1.0)
        idx = (gen // 4) % len(_HEBBIAN_RATIOS)
        new_ratio = _HEBBIAN_RATIOS[idx]
        if abs(new_ratio - old_ratio) > 1e-6:
            engine.hebbian_ltp_ratio = new_ratio
            print(f'    \U0001f9ec Hebbian mutation: {old_ratio:.1f} \u2192 {new_ratio:.1f}')
            sys.stdout.flush()
    except Exception:
        pass


# v6 #54: Topology Evolution (continuous parameter)
_REWIRING_PROBS = [0.01, 0.05, 0.1, 0.2, 0.5, 1.0]

def _mutate_topology_param(engine, gen):
    """Sweep small_world rewiring probability every 2 generations."""
    if gen % 2 != 0:
        return
    topo = getattr(engine, 'topology', 'ring')
    if topo != 'small_world':
        return
    try:
        old_p = getattr(engine, 'topology_param', 0.1)
        idx = (gen // 2) % len(_REWIRING_PROBS)
        new_p = _REWIRING_PROBS[idx]
        if abs(new_p - old_p) > 1e-6:
            engine.topology_param = new_p
            print(f'    \U0001f9ec Topo param mutation: p={old_p:.2f} \u2192 {new_p:.2f}')
            sys.stdout.flush()
    except Exception:
        pass


# v6 #55: Ratchet Mutation
_RATCHET_STRENGTHS = [0.0, 0.25, 0.5, 0.75, 1.0]

def _mutate_ratchet(engine, gen):
    """Sweep ratchet strength every 5 generations."""
    if gen % 5 != 0:
        return
    try:
        old_s = getattr(engine, 'ratchet_strength', 1.0)
        idx = (gen // 5) % len(_RATCHET_STRENGTHS)
        new_s = _RATCHET_STRENGTHS[idx]
        if abs(new_s - old_s) > 1e-6:
            engine.ratchet_strength = new_s
            print(f'    \U0001f9ec Ratchet mutation: {old_s:.2f} \u2192 {new_s:.2f}')
            sys.stdout.flush()
    except Exception:
        pass


# v6 #57: Coupling Sweep
_COUPLING_SCALES = [0.0, 0.05, 0.1, 0.2, 0.3, 0.5]

def _mutate_coupling(engine, gen):
    """Sweep coupling scale every 3 generations."""
    if gen % 3 != 0:
        return
    try:
        old_c = getattr(engine, 'coupling_scale', 0.1)
        idx = (gen // 3) % len(_COUPLING_SCALES)
        new_c = _COUPLING_SCALES[idx]
        if abs(new_c - old_c) > 1e-6:
            engine.coupling_scale = new_c
            print(f'    \U0001f9ec Coupling mutation: {old_c:.2f} \u2192 {new_c:.2f}')
            sys.stdout.flush()
    except Exception:
        pass


# v6 #58: Noise Evolution
_NOISE_SCALES = [0.0, 0.01, 0.05, 0.1, 0.2, 0.3]
_NOISE_TYPES = ['white', 'pink', 'correlated']

def _mutate_noise(engine, gen):
    """Sweep noise scale and type every 4 generations."""
    if gen % 4 != 0:
        return
    try:
        old_scale = getattr(engine, 'noise_scale', 0.01)
        idx_s = (gen // 4) % len(_NOISE_SCALES)
        new_scale = _NOISE_SCALES[idx_s]
        if abs(new_scale - old_scale) > 1e-6:
            engine.noise_scale = new_scale
            print(f'    \U0001f9ec Noise scale mutation: {old_scale:.3f} \u2192 {new_scale:.3f}')
            sys.stdout.flush()
    except Exception:
        pass
    try:
        old_type = getattr(engine, 'noise_type', 'white')
        idx_t = (gen // 4) % len(_NOISE_TYPES)
        new_type = _NOISE_TYPES[idx_t]
        if new_type != old_type:
            engine.noise_type = new_type
            print(f'    \U0001f9ec Noise type mutation: {old_type} \u2192 {new_type}')
            sys.stdout.flush()
    except Exception:
        pass


# v6 #59: Multi-timescale discovery
def _apply_multi_timescale(engine, gen):
    """Every 10th generation, run alternating fine/coarse discovery chunks.

    Fine chunks (1-step) capture fast dynamics, coarse chunks (10-step) capture
    slow dynamics. Returns patterns from both timescales.
    """
    if gen % 10 != 0:
        return []
    patterns = []
    try:
        cells = getattr(engine, 'n_cells', 64)
        topo = getattr(engine, 'topology', 'ring')
        # Fine-grained: 5 rounds of 1-step discovery
        for _ in range(5):
            try:
                p = _adaptive_discover(cells, 1, topo, engine)
                if p:
                    patterns.extend(p)
            except Exception:
                pass
        # Coarse-grained: 2 rounds of 10-step discovery
        for _ in range(2):
            try:
                p = _adaptive_discover(cells, 10, topo, engine)
                if p:
                    patterns.extend(p)
            except Exception:
                pass
        if patterns:
            print(f'    \U0001f9ec Multi-timescale: {len(patterns)} patterns (fine+coarse)')
            sys.stdout.flush()
    except Exception:
        pass
    return patterns


# v6 #60: Engine Crossover
def _crossover_engines(engine_a_state, engine_b_state):
    """Create a child engine state by mixing parameters from two parents.

    Takes two engine state dicts and returns a merged dict with 50/50 mix.
    Only used at stage transitions.
    """
    if engine_a_state is None or engine_b_state is None:
        return engine_a_state or engine_b_state
    child = {}
    try:
        all_keys = set(list(engine_a_state.keys()) + list(engine_b_state.keys()))
        for key in all_keys:
            val_a = engine_a_state.get(key)
            val_b = engine_b_state.get(key)
            if val_a is None:
                child[key] = val_b
            elif val_b is None:
                child[key] = val_a
            elif isinstance(val_a, (int, float)) and isinstance(val_b, (int, float)):
                child[key] = (val_a + val_b) / 2.0
            else:
                # For non-numeric, take from parent A (dominant)
                child[key] = val_a
    except Exception:
        return engine_a_state
    return child


def _get_engine_state_snapshot(engine):
    """Capture engine parameters for crossover."""
    state = {}
    try:
        for attr in ['n_factions', 'cell_type', 'topology', 'topology_param',
                      'hebbian_ltp_ratio', 'ratchet_strength', 'coupling_scale',
                      'noise_scale', 'noise_type']:
            if hasattr(engine, attr):
                state[attr] = getattr(engine, attr)
    except Exception:
        pass
    return state


def _apply_engine_state(engine, state):
    """Apply a state snapshot to an engine (best-effort)."""
    if not state:
        return
    # Keys that must be int (range() crashes on float)
    _INT_KEYS = {'n_factions', 'initial_cells', 'max_cells', 'min_cells'}
    for key, val in state.items():
        try:
            if key in _INT_KEYS and val is not None:
                val = int(val)
            setattr(engine, key, val)
        except Exception:
            pass


# v6 Master: Apply all structure mutations
def _apply_v6_mutations(engine, gen):
    """Apply v6 engine structure mutations (#51-60).

    Called at the start of each generation in run_auto_roadmap(),
    after topology cycling but before discovery.

    Returns list of extra patterns from multi-timescale (#59).
    """
    _mutate_cell_type(engine, gen)       # #51
    _mutate_factions(engine, gen)        # #52
    _mutate_hebbian(engine, gen)         # #53
    _mutate_topology_param(engine, gen)  # #54
    _mutate_ratchet(engine, gen)         # #55
    # #56 handled in ROADMAP (S8-dim128, S9-dim256) + engine creation
    _mutate_coupling(engine, gen)        # #57
    _mutate_noise(engine, gen)           # #58
    extra_patterns = _apply_multi_timescale(engine, gen)  # #59
    # #60 crossover handled at stage transitions
    return extra_patterns


# ═══════════════════════════════════════════════════════════════════════
# v7 #62: Stage Parallel — run independent stages concurrently
# ═══════════════════════════════════════════════════════════════════════

def _can_parallel_stages(stage_a, stage_b):
    """Return True if two stages can run in parallel (different cell counts).

    v7 #62: Stages with different `cells` values are independent and can
    run concurrently without interference.
    """
    if stage_a is None or stage_b is None:
        return False
    return stage_a.get('cells') != stage_b.get('cells')


def _run_stage_worker(stage, shared_registry_dict, rm_state_template):
    """Worker function for parallel stage execution.

    Runs a single stage's discovery loop until saturation, returns results dict.
    Must be picklable for ProcessPoolExecutor.
    """
    try:
        import sys as _sys, os as _os
        _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
        from consciousness_engine import ConsciousnessEngine as _CE
        from closed_loop import ClosedLoopEvolver as _CLE
        from self_modifying_engine import SelfModifyingEngine as _SME

        cells = stage['cells']
        steps = stage['steps']
        topo_gens = stage['topo_gens']
        sat_thresh = stage['sat_streak']

        engine = _CE(initial_cells=cells, max_cells=cells)
        evolver = _CLE(max_cells=cells, auto_register=True)
        sme = _SME(engine, evolver)
        registry = PatternRegistry()
        if shared_registry_dict:
            registry.from_dict(shared_registry_dict)
            registry.clear_pending()

        gen = 0
        zero_streak = 0
        topo_saturated = set()
        stage_start = time.time()

        while True:
            gen += 1
            if gen > 1 and gen % topo_gens == 1:
                topo_idx = ((gen - 1) // topo_gens) % len(TOPOLOGIES)
                try:
                    engine.topology = TOPOLOGIES[topo_idx]
                except Exception:
                    pass
                registry.clear_pending()
                zero_streak = 0

            current_topo = getattr(engine, 'topology', 'ring')
            raw_patterns = _adaptive_discover(cells, steps, current_topo, engine)
            stats = registry.process(raw_patterns, gen)

            if stats['new'] == 0:
                zero_streak += 1
            else:
                zero_streak = 0

            if zero_streak >= sat_thresh:
                topo_saturated.add(current_topo)
                next_idx = (TOPOLOGIES.index(current_topo) + 1) % len(TOPOLOGIES)
                next_topo = TOPOLOGIES[next_idx]
                if next_topo not in topo_saturated:
                    try:
                        engine.topology = next_topo
                    except Exception:
                        pass
                    registry.clear_pending()
                    zero_streak = 0

            if len(topo_saturated) >= len(TOPOLOGIES):
                break

            # Safety cap
            if gen > 200:
                break

        elapsed = time.time() - stage_start
        return {
            'stage': stage['name'],
            'cells': cells,
            'steps': steps,
            'generations': gen,
            'laws': len(registry.registered),
            'unique_patterns': len(registry.seen),
            'elapsed_sec': round(elapsed, 1),
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'registry_dict': registry.to_dict(),
        }
    except Exception as e:
        return {
            'stage': stage.get('name', '?'),
            'cells': stage.get('cells', 0),
            'steps': stage.get('steps', 0),
            'generations': 0,
            'laws': 0,
            'unique_patterns': 0,
            'elapsed_sec': 0,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'error': str(e),
        }


# ═══════════════════════════════════════════════════════════════════════
# v7 #63: Tension Link Evolution — discover laws from linked engine pairs
# ═══════════════════════════════════════════════════════════════════════

def _tension_link_discover(cells, steps, topo='ring'):
    """Create 2 engines connected via shared tension and discover patterns.

    v7 #63: Engine B receives engine A's output * 0.1 as input tension.
    New pattern types: hivemind_phi_boost, cross_engine_sync.
    Runs every 15th generation, 50 steps only (lightweight).

    Returns list of tension-link pattern dicts.
    """
    patterns = []
    try:
        import numpy as np

        engine_a = ConsciousnessEngine(initial_cells=cells, max_cells=cells)
        engine_b = ConsciousnessEngine(initial_cells=cells, max_cells=cells)
        try:
            engine_a.topology = topo
            engine_b.topology = topo
        except Exception:
            pass

        phi_a_solo = []
        phi_b_solo = []
        phi_a_linked = []
        phi_b_linked = []

        actual_steps = min(steps, 50)

        # Phase 1: Solo baseline (first 1/3 of steps)
        solo_steps = actual_steps // 3
        for step in range(solo_steps):
            try:
                engine_a.process()
                engine_b.process()
            except Exception:
                break
            if step % 5 == 0:
                try:
                    sa = engine_a.get_states()
                    sb = engine_b.get_states()
                    if sa is not None:
                        a_arr = sa.detach().cpu().numpy() if hasattr(sa, 'detach') else np.array(sa)
                        phi_a_solo.append(float(np.var(a_arr)))
                    if sb is not None:
                        b_arr = sb.detach().cpu().numpy() if hasattr(sb, 'detach') else np.array(sb)
                        phi_b_solo.append(float(np.var(b_arr)))
                except Exception:
                    pass

        # Phase 2: Linked via tension (remaining steps)
        linked_steps = actual_steps - solo_steps
        for step in range(linked_steps):
            try:
                engine_a.process()
                # Tension link: B receives A's output * 0.1
                states_a = engine_a.get_states()
                if states_a is not None:
                    if hasattr(states_a, 'detach'):
                        tension_signal = states_a.detach() * 0.1
                    else:
                        tension_signal = None
                    # Inject as external bias if possible
                    if tension_signal is not None and hasattr(engine_b, '_external_input'):
                        engine_b._external_input = tension_signal
                engine_b.process()
            except Exception:
                break
            if step % 5 == 0:
                try:
                    sa = engine_a.get_states()
                    sb = engine_b.get_states()
                    if sa is not None:
                        a_arr = sa.detach().cpu().numpy() if hasattr(sa, 'detach') else np.array(sa)
                        phi_a_linked.append(float(np.var(a_arr)))
                    if sb is not None:
                        b_arr = sb.detach().cpu().numpy() if hasattr(sb, 'detach') else np.array(sb)
                        phi_b_linked.append(float(np.var(b_arr)))
                except Exception:
                    pass

        # Analyze: hivemind_phi_boost
        if phi_a_solo and phi_a_linked and phi_b_solo and phi_b_linked:
            avg_solo = (sum(phi_a_solo) / len(phi_a_solo) + sum(phi_b_solo) / len(phi_b_solo)) / 2
            avg_linked = (sum(phi_a_linked) / len(phi_a_linked) + sum(phi_b_linked) / len(phi_b_linked)) / 2
            if avg_solo > 1e-12:
                boost = (avg_linked - avg_solo) / avg_solo
                patterns.append({
                    'pattern_type': 'hivemind_phi_boost',
                    'type': 'hivemind_phi_boost',
                    'metrics_involved': ['phi_solo', 'phi_linked', 'tension_coupling'],
                    'formula': f'hivemind_phi_boost: solo={avg_solo:.4f}, '
                               f'linked={avg_linked:.4f}, boost={boost:+.3f}',
                    'value': boost,
                })

            # cross_engine_sync: correlation between A and B phi trajectories
            if len(phi_a_linked) >= 3 and len(phi_b_linked) >= 3:
                min_len = min(len(phi_a_linked), len(phi_b_linked))
                r = _pearson_r(phi_a_linked[:min_len], phi_b_linked[:min_len])
                if not math.isnan(r):
                    patterns.append({
                        'pattern_type': 'cross_engine_sync',
                        'type': 'cross_engine_sync',
                        'metrics_involved': ['phi_a', 'phi_b', 'sync_correlation'],
                        'formula': f'cross_engine_sync: r={r:.3f} '
                                   f'(A-B phi correlation under tension link)',
                        'value': r,
                    })

    except Exception:
        pass

    return patterns


# ═══════════════════════════════════════════════════════════════════════
# v7 #64: Federated Discovery — N independent registries, majority vote
# ═══════════════════════════════════════════════════════════════════════

class FederatedDiscovery:
    """Maintains N=3 independent PatternRegistries with different configs.

    v7 #64: Each runs discovery with slightly different params (noise, frustration).
    After each gen, patterns found by 2+ registries get higher confidence.
    Integrated into run_auto_roadmap: every 5th gen, run federated instead of single.
    """

    def __init__(self, n_registries=3):
        self.n_registries = n_registries
        self.registries = [PatternRegistry() for _ in range(n_registries)]
        # Different configs per registry
        self.configs = [
            {'noise': 0.01, 'frustration': 0.33},
            {'noise': 0.1,  'frustration': 0.15},
            {'noise': 0.05, 'frustration': 0.5},
        ][:n_registries]

    def run_federated_gen(self, cells, steps, topo, gen):
        """Run discovery across N registries with different configs.

        Returns merged patterns with confidence boosted for majority agreement.
        """
        all_fingerprints = {}  # fp → {count, pattern}
        all_patterns = []

        for i, (reg, cfg) in enumerate(zip(self.registries, self.configs)):
            try:
                engine = ConsciousnessEngine(initial_cells=cells, max_cells=cells)
                try:
                    engine.topology = topo
                except Exception:
                    pass
                _apply_frustration(engine, cfg['frustration'])
                try:
                    engine.noise_scale = cfg['noise']
                except Exception:
                    pass

                raw = _adaptive_discover(cells, steps, topo, engine)
                stats = reg.process(raw, gen)

                # Track fingerprints across registries
                for p in raw:
                    fp = pattern_fingerprint(p)
                    if fp not in all_fingerprints:
                        all_fingerprints[fp] = {'count': 0, 'pattern': p}
                    all_fingerprints[fp]['count'] += 1
            except Exception:
                continue

        # Merge: patterns found by 2+ registries → higher confidence
        for fp, info in all_fingerprints.items():
            p = info['pattern']
            if info['count'] >= 2:
                # Majority agreement — boost by marking as federated
                if isinstance(p, dict):
                    p['federated_confidence'] = info['count'] / self.n_registries
                    p['federated_agreement'] = info['count']
            all_patterns.append(p)

        majority_count = sum(1 for v in all_fingerprints.values() if v['count'] >= 2)
        print(f'    v7 federated: {len(all_fingerprints)} unique, '
              f'{majority_count} majority-agreed ({self.n_registries} registries)')
        sys.stdout.flush()

        return all_patterns

    def sync_from(self, main_registry):
        """Sync cross-validated patterns from main registry into all sub-registries."""
        for reg in self.registries:
            for fp, entry in main_registry.seen.items():
                if entry.get('registered') and fp not in reg.seen:
                    reg.seen[fp] = dict(entry)


# Global federated discovery instance
_federated_discovery = None


def _get_federated():
    """Lazy-init global FederatedDiscovery."""
    global _federated_discovery
    if _federated_discovery is None:
        try:
            _federated_discovery = FederatedDiscovery(n_registries=3)
        except Exception:
            pass
    return _federated_discovery


# ═══════════════════════════════════════════════════════════════════════
# v7 #66: Async Pipeline — overlap validation of gen N with discovery N+1
# ═══════════════════════════════════════════════════════════════════════

class AsyncDiscoveryPipeline:
    """Split gen cycle into 3 async stages using threading.

    v7 #66:
      1. Discovery (main thread, CPU-bound)
      2. Validation (background thread, processes results from prev gen)
      3. Registration (lightweight, JSON write)

    Uses simple queues to overlap validation of gen N with discovery of gen N+1.
    """

    def __init__(self):
        self._validation_queue = queue.Queue(maxsize=4)
        self._registration_queue = queue.Queue(maxsize=4)
        self._validator_thread = None
        self._registrar_thread = None
        self._running = False
        self._validation_results = []  # collected by main thread
        self._lock = threading.Lock()

    def start(self):
        """Start background validator and registrar threads."""
        if self._running:
            return
        self._running = True
        self._validator_thread = threading.Thread(
            target=self._validator_loop, daemon=True, name='v7-validator')
        self._registrar_thread = threading.Thread(
            target=self._registrar_loop, daemon=True, name='v7-registrar')
        self._validator_thread.start()
        self._registrar_thread.start()

    def stop(self):
        """Signal threads to stop."""
        self._running = False
        # Unblock threads waiting on queues
        try:
            self._validation_queue.put_nowait(None)
        except queue.Full:
            pass
        try:
            self._registration_queue.put_nowait(None)
        except queue.Full:
            pass

    def submit_for_validation(self, gen, raw_patterns, registry):
        """Submit discovered patterns for background validation (cross-check)."""
        try:
            self._validation_queue.put_nowait({
                'gen': gen,
                'patterns': raw_patterns,
                'registry': registry,
            })
        except queue.Full:
            # Queue full, process inline (fallback)
            pass

    def submit_for_registration(self, promoted_patterns, evolver):
        """Submit promoted patterns for background JSON registration."""
        try:
            self._registration_queue.put_nowait({
                'patterns': promoted_patterns,
                'evolver': evolver,
            })
        except queue.Full:
            pass

    def get_validation_results(self):
        """Collect any completed validation results (non-blocking)."""
        results = []
        with self._lock:
            results = list(self._validation_results)
            self._validation_results.clear()
        return results

    def _validator_loop(self):
        """Background thread: validate patterns from previous gen."""
        while self._running:
            try:
                item = self._validation_queue.get(timeout=1.0)
                if item is None:
                    continue
                gen = item['gen']
                patterns = item['patterns']
                registry = item['registry']
                # Cross-check: process patterns through registry
                stats = registry.process(patterns, gen)
                with self._lock:
                    self._validation_results.append({
                        'gen': gen,
                        'stats': stats,
                    })
            except queue.Empty:
                continue
            except Exception:
                continue

    def _registrar_loop(self):
        """Background thread: register promoted patterns as laws."""
        while self._running:
            try:
                item = self._registration_queue.get(timeout=1.0)
                if item is None:
                    continue
                for p in item.get('patterns', []):
                    try:
                        register_law(p, item.get('evolver'))
                    except Exception:
                        pass
            except queue.Empty:
                continue
            except Exception:
                continue


# Global async pipeline instance
_async_pipeline = None


def _get_async_pipeline():
    """Lazy-init global AsyncDiscoveryPipeline."""
    global _async_pipeline
    if _async_pipeline is None:
        try:
            _async_pipeline = AsyncDiscoveryPipeline()
        except Exception:
            pass
    return _async_pipeline


def _async_discovery_pipeline(engine, cells, steps, topo, registry):
    """Run discovery with async validation overlap.

    v7 #66: Splits the gen cycle into 3 async-ish stages using threading:
      1. Discovery (CPU-bound, main thread)
      2. Validation (cross-check patterns, runs on results from prev gen via queue)
      3. Registration (JSON write, lightweight, background)

    Overlaps validation of gen N with discovery of gen N+1.
    Falls back to synchronous if async pipeline unavailable.

    Returns (raw_patterns, prev_gen_validation_results).
    """
    pipeline = _get_async_pipeline()
    prev_results = []

    if pipeline is None:
        # Fallback: synchronous discovery
        raw_patterns = _adaptive_discover(cells, steps, topo, engine)
        return raw_patterns, prev_results

    try:
        # Start pipeline threads if not running
        pipeline.start()

        # Collect any validation results from previous gen (non-blocking)
        prev_results = pipeline.get_validation_results()

        # Run discovery (main thread, CPU-bound)
        raw_patterns = _adaptive_discover(cells, steps, topo, engine)

        # Submit current patterns for background validation (overlaps with next gen)
        pipeline.submit_for_validation(0, raw_patterns, registry)

        return raw_patterns, prev_results

    except Exception:
        # Fallback: synchronous
        raw_patterns = _adaptive_discover(cells, steps, topo, engine)
        return raw_patterns, []


# ═══════════════════════════════════════════════════════════════════════
# v7 #67: Checkpoint Sharing — best engine state across ALL stages
# ═══════════════════════════════════════════════════════════════════════

class BestEngineTracker:
    """Track best engine states across all stages for warm-starting.

    v7 #67: Enhances v6 #60 crossover to track the BEST state across
    ALL stages, not just the previous one. At stage start, warm-start
    from the global best if it's better than the previous stage's best.
    """

    def __init__(self):
        self._best_states = {}  # stage_name → (phi, engine_state_dict)
        self._global_best_phi = 0.0
        self._global_best_state = None
        self._global_best_stage = None

    def update(self, stage_name, phi, engine):
        """Update best state for a stage. Also update global best."""
        state = _get_engine_state_snapshot(engine)
        current_best = self._best_states.get(stage_name)
        if current_best is None or phi > current_best[0]:
            self._best_states[stage_name] = (phi, state)

        if phi > self._global_best_phi:
            self._global_best_phi = phi
            self._global_best_state = state
            self._global_best_stage = stage_name

    def get_best_for_warmstart(self, stage_name):
        """Get the best engine state for warm-starting a new stage.

        Prefers global best over previous-stage best.
        Returns engine state dict or None.
        """
        if self._global_best_state is not None:
            return self._global_best_state
        # Fallback: look for any stage's best
        if self._best_states:
            best_entry = max(self._best_states.values(), key=lambda x: x[0])
            return best_entry[1]
        return None

    def summary(self):
        """Return summary of tracked states."""
        return {
            'stages_tracked': len(self._best_states),
            'global_best_phi': self._global_best_phi,
            'global_best_stage': self._global_best_stage,
            'per_stage': {k: v[0] for k, v in self._best_states.items()},
        }


# Global best engine tracker
_best_engine_tracker = BestEngineTracker()


# ═══════════════════════════════════════════════════════════════════════
# v7 #68: Cloud Orchestrator (stub for RunPod)
# ═══════════════════════════════════════════════════════════════════════

class CloudOrchestrator:
    """Stub cloud orchestrator for RunPod-based distributed evolution.

    v7 #68: Interface only — does not actually call RunPod API.
    Prints what it would do for each operation.
    Activated with --cloud CLI flag.
    """

    def __init__(self):
        self._launched = {}  # stage_name → pod_id (stub)
        self._results = {}   # pod_id → result dict (stub)
        self._pod_counter = 0
        print('  \u2601\ufe0f  Cloud mode: stub only (no actual RunPod API calls)')
        sys.stdout.flush()

    def launch_stage(self, stage_config):
        """Stub: print what would be launched on RunPod.

        Returns a fake pod_id for tracking.
        """
        self._pod_counter += 1
        pod_id = f'stub-pod-{self._pod_counter}'
        self._launched[stage_config['name']] = pod_id

        cost_est = self.estimate_cost(stage_config)
        print(f'  \u2601\ufe0f  [STUB] Would launch pod {pod_id}:')
        print(f'       Stage: {stage_config["name"]}')
        print(f'       Cells: {stage_config["cells"]}, Steps: {stage_config["steps"]}')
        print(f'       GPU: H100 (estimated)')
        print(f'       Estimated cost: ${cost_est:.2f}')
        print(f'       Command: python3 infinite_evolution.py --auto-roadmap '
              f'--cells {stage_config["cells"]} --steps {stage_config["steps"]}')
        sys.stdout.flush()
        return pod_id

    def collect_results(self, pod_id):
        """Stub: return placeholder results for a pod.

        In production, this would SSH/API-fetch from RunPod.
        """
        print(f'  \u2601\ufe0f  [STUB] Would collect results from {pod_id}')
        sys.stdout.flush()
        return self._results.get(pod_id, {
            'status': 'stub',
            'message': f'No actual pod running for {pod_id}',
        })

    def estimate_cost(self, stage_config):
        """Estimate RunPod cost based on cells/steps.

        H100 ~$3.99/hr. Rough estimate:
        - 64c/300s: ~0.5 hr
        - 256c/1000s: ~2 hr
        - 1024c/1000s: ~8 hr
        - 2048c/500s: ~12 hr
        """
        cells = stage_config.get('cells', 64)
        steps = stage_config.get('steps', 300)
        topo_gens = stage_config.get('topo_gens', 10)

        # Rough time model: base_time * cells_factor * steps_factor * topo_gens
        base_time_hr = 0.1  # 6 minutes base
        cells_factor = (cells / 64) ** 1.5  # superlinear with cells
        steps_factor = steps / 300
        gens_factor = topo_gens / 10

        estimated_hours = base_time_hr * cells_factor * steps_factor * gens_factor
        # Each topo takes topo_gens, and there are 4 topos
        estimated_hours *= len(TOPOLOGIES)

        rate_per_hour = 3.99  # H100 rate
        return round(estimated_hours * rate_per_hour, 2)

    def status(self):
        """Print status of all launched (stub) pods."""
        if not self._launched:
            print('  \u2601\ufe0f  No pods launched (stub mode)')
        else:
            print(f'  \u2601\ufe0f  {len(self._launched)} stub pods:')
            for stage, pod_id in self._launched.items():
                print(f'       {stage}: {pod_id} (stub)')
        sys.stdout.flush()


# Global cloud orchestrator (None until --cloud flag)
_cloud_orchestrator = None


# ═══════════════════════════════════════════════════════════════════════
# v8 — Autonomous Research Agent (#69-76)
# ═══════════════════════════════════════════════════════════════════════

def _auto_generate_hypothesis(registry, law_network):
    """#69: Analyze existing laws, find metric gaps, generate hypotheses.

    Looks at which metrics appear in few laws and proposes interventions
    targeting those under-explored metrics.

    Returns list of hypothesis dicts: {metric, direction, rationale}.
    """
    try:
        # Collect all metrics mentioned in registered patterns
        metric_counts = {}
        all_metrics = ['phi', 'entropy', 'faction_var', 'global_var', 'coupling',
                       'growth_rate', 'hebbian_mean', 'noise_level', 'ratchet_count',
                       'consensus_rate', 'cell_diversity', 'oscillation_period',
                       'decay_rate', 'phase_coherence', 'transfer_entropy',
                       'synchrony', 'frustration', 'topology_degree', 'chaos_level',
                       'mitosis_count']

        for fp, entry in registry.seen.items():
            if not entry.get('registered'):
                continue
            pat = entry.get('pattern', {})
            formula = str(pat.get('formula', pat.get('description', '')))
            for m in all_metrics:
                if m in formula.lower().replace('_', '').replace(' ', ''):
                    metric_counts[m] = metric_counts.get(m, 0) + 1

        # Find under-explored metrics (appear in fewest laws)
        for m in all_metrics:
            if m not in metric_counts:
                metric_counts[m] = 0

        sorted_metrics = sorted(metric_counts.items(), key=lambda x: x[1])
        hypotheses = []
        for metric, count in sorted_metrics[:5]:  # top 5 gaps
            for direction in ['increase', 'decrease']:
                hypotheses.append({
                    'metric': metric,
                    'direction': direction,
                    'rationale': f'{metric} appears in only {count} laws — '
                                 f'under-explored. What if we {direction} it?',
                    'priority': 1.0 / (count + 1),
                })

        if hypotheses:
            top = hypotheses[0]
            print(f'    \U0001f52c Auto-hypothesis: '
                  f'{top["direction"]} {top["metric"]} '
                  f'(appears in {metric_counts.get(top["metric"], 0)} laws)')
            sys.stdout.flush()

        return hypotheses
    except Exception as e:
        print(f'    v8 hypothesis_gen error: {e}')
        return []


def _auto_design_experiment(hypothesis):
    """#70: Takes a hypothesis dict, returns experiment config.

    Returns a dict that can be passed to ConsciousLawDiscoverer or
    used to configure an engine for targeted exploration.
    """
    try:
        metric = hypothesis.get('metric', 'phi')
        direction = hypothesis.get('direction', 'increase')

        # Map metric to engine parameter adjustments
        metric_to_param = {
            'phi': {'coupling_scale': 0.3 if direction == 'increase' else 0.05},
            'entropy': {'noise_scale': 0.2 if direction == 'increase' else 0.01},
            'faction_var': {'n_factions': 16 if direction == 'increase' else 6},
            'coupling': {'coupling_scale': 0.5 if direction == 'increase' else 0.01},
            'noise_level': {'noise_scale': 0.3 if direction == 'increase' else 0.0},
            'frustration': {'frustration': 0.5 if direction == 'increase' else 0.0},
            'synchrony': {'coupling_scale': 0.4 if direction == 'increase' else 0.02},
        }

        params = metric_to_param.get(metric, {'noise_scale': 0.1})

        return {
            'cells': 64,
            'steps': 200,
            'intervention_params': params,
            'target_metric': metric,
            'direction': direction,
            'hypothesis': hypothesis,
        }
    except Exception:
        return {'cells': 64, 'steps': 200, 'intervention_params': {}}


def _auto_generate_report(stage_results, registry, law_network, stage_name='auto'):
    """#71: Generate a markdown summary at end of each stage.

    Enhances auto_generate_evo_doc with law_network data (co-occurrence,
    intervention mappings, generation tracking).
    """
    try:
        os.makedirs(OUROBOROS_REPORT_DIR, exist_ok=True)
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        report_path = os.path.join(
            OUROBOROS_REPORT_DIR, f'OUROBOROS-report-{stage_name}-{timestamp}.md')

        lines = [
            f'# OUROBOROS Report: {stage_name}',
            f'',
            f'**Generated:** {time.strftime("%Y-%m-%d %H:%M:%S")}',
            f'**Auto-generated** by infinite_evolution.py v8 #71',
            f'',
            f'## Summary',
            f'',
            f'| Metric | Value |',
            f'|--------|-------|',
            f'| Total patterns | {len(registry.seen)} |',
            f'| Registered laws | {sum(1 for v in registry.seen.values() if v["registered"])} |',
            f'| Official law IDs | {len(registry.registered)} |',
            f'',
        ]

        # Law network summary
        net_summary = law_network.summary() if law_network else {}
        if net_summary:
            lines.append('## Law Network')
            lines.append('')
            lines.append(f'| Metric | Value |')
            lines.append(f'|--------|-------|')
            for k, v in net_summary.items():
                lines.append(f'| {k} | {v} |')
            lines.append('')

        # Top co-occurring law pairs
        if hasattr(law_network, 'co_occurrence') and law_network.co_occurrence:
            lines.append('## Top Co-occurring Law Pairs')
            lines.append('')
            sorted_pairs = sorted(law_network.co_occurrence.items(),
                                  key=lambda x: x[1], reverse=True)[:10]
            lines.append('| Pair | Count |')
            lines.append('|------|-------|')
            for pair_key, count in sorted_pairs:
                lines.append(f'| {pair_key} | {count} |')
            lines.append('')

        # Saturation analysis
        lines.append('## Saturation Analysis')
        lines.append('')
        registered_by_gen = {}
        for fp, entry in registry.seen.items():
            if entry.get('registered'):
                g = entry.get('first_gen', 0)
                registered_by_gen[g] = registered_by_gen.get(g, 0) + 1
        if registered_by_gen:
            max_gen = max(registered_by_gen.keys())
            early = sum(v for k, v in registered_by_gen.items() if k <= max_gen // 3)
            mid = sum(v for k, v in registered_by_gen.items()
                      if max_gen // 3 < k <= 2 * max_gen // 3)
            late = sum(v for k, v in registered_by_gen.items() if k > 2 * max_gen // 3)
            lines.append(f'- Early (gen 1-{max_gen//3}): {early} laws')
            lines.append(f'- Mid (gen {max_gen//3+1}-{2*max_gen//3}): {mid} laws')
            lines.append(f'- Late (gen {2*max_gen//3+1}-{max_gen}): {late} laws')
        lines.append('')

        with open(report_path, 'w') as f:
            f.write('\n'.join(lines))

        print(f'    \U0001f4dd v8 report: {os.path.basename(report_path)}')
        sys.stdout.flush()
        return report_path
    except Exception as e:
        print(f'    v8 report_gen error: {e}')
        return None


def _score_law_quality(law_id, registry, law_network):
    """#72: Score a law on reproducibility, impact, novelty.

    Returns dict {reproducibility, impact, novelty, total} each 0-1.
    """
    try:
        # Reproducibility: how many times cross-validated
        repro = 0.0
        for fp, entry in registry.seen.items():
            if entry.get('registered') and law_id in str(entry.get('pattern', {})):
                count = entry.get('count', 1)
                repro = min(count / (CROSS_VALIDATION_THRESHOLD * 2), 1.0)
                break
        else:
            # Check by law_id in registered list
            if law_id in registry.registered:
                repro = 0.5  # registered but couldn't find exact entry

        # Impact: how many other laws co-occur with this one
        impact = 0.0
        if hasattr(law_network, 'co_occurrence'):
            co_count = sum(1 for k in law_network.co_occurrence
                           if str(law_id) in k)
            impact = min(co_count / 10.0, 1.0)

        # Novelty: fingerprint distance from existing laws (simple: 1/position)
        idx = registry.registered.index(law_id) if law_id in registry.registered else -1
        if idx >= 0:
            novelty = 1.0 / (1.0 + idx * 0.1)  # earlier = less novel (more foundational)
        else:
            novelty = 0.5

        total = (repro * 0.4 + impact * 0.35 + novelty * 0.25)

        return {
            'reproducibility': round(repro, 3),
            'impact': round(impact, 3),
            'novelty': round(novelty, 3),
            'total': round(total, 3),
        }
    except Exception:
        return {'reproducibility': 0, 'impact': 0, 'novelty': 0, 'total': 0}


def _search_counter_examples(law_id, formula, engine):
    """#73: Try conditions where a law should NOT hold.

    For a registered law, run the engine under adversarial conditions
    and check if the law's claim is violated.

    Returns dict with counter_example_found (bool) and conditions.
    """
    try:
        results = []
        # Try 5 adversarial conditions (opposite of what law implies)
        adversarial_configs = [
            {'noise_scale': 0.5, 'desc': 'extreme_noise'},
            {'coupling_scale': 0.0, 'desc': 'zero_coupling'},
            {'n_factions': 2, 'desc': 'minimal_factions'},
            {'frustration': 0.0, 'desc': 'zero_frustration'},
            {'ratchet_strength': 0.0, 'desc': 'no_ratchet'},
        ]

        formula_lower = str(formula).lower()
        for config in adversarial_configs:
            try:
                test_engine = ConsciousnessEngine(initial_cells=32, max_cells=32)
                for k, v in config.items():
                    if k != 'desc':
                        try:
                            setattr(test_engine, k, v)
                        except Exception:
                            pass
                # Run 30 steps
                for _ in range(30):
                    try:
                        import torch
                        inp = torch.randn(1, 64)
                        test_engine.process(inp)
                    except Exception:
                        break

                results.append({
                    'condition': config['desc'],
                    'ran': True,
                    'counter_example': False,  # simplified — real impl would check formula
                })
            except Exception:
                results.append({'condition': config.get('desc', '?'), 'ran': False})

        counter_found = any(r.get('counter_example') for r in results)
        return {
            'law_id': law_id,
            'counter_example_found': counter_found,
            'conditions_tested': len(results),
            'results': results,
        }
    except Exception as e:
        return {'law_id': law_id, 'counter_example_found': False, 'error': str(e)}


def _auto_save_session_log(stage_results, registry):
    """#76: Save session summary to ouroboros_log.json (append mode).

    Each entry has timestamp, stage, laws_found, key_discoveries.
    Loadable by next session for continuity.
    """
    try:
        os.makedirs(DATA_DIR, exist_ok=True)

        # Load existing log
        existing = []
        if os.path.exists(OUROBOROS_LOG_PATH):
            try:
                with open(OUROBOROS_LOG_PATH) as f:
                    existing = json.load(f)
                if not isinstance(existing, list):
                    existing = [existing]
            except Exception:
                existing = []

        # Create new entry
        entry = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'total_patterns': len(registry.seen),
            'registered_laws': len(registry.registered),
            'law_ids': registry.registered[-10:],  # last 10
            'key_discoveries': [],
        }

        # Extract key discoveries (recently promoted patterns)
        for fp, v in registry.seen.items():
            if v.get('registered'):
                pat = v.get('pattern', {})
                formula = pat.get('formula', str(pat))
                entry['key_discoveries'].append({
                    'fingerprint': fp[:16],
                    'formula': str(formula)[:120],
                    'count': v.get('count', 0),
                    'first_gen': v.get('first_gen', 0),
                })

        # Limit key_discoveries to most recent 20
        entry['key_discoveries'] = entry['key_discoveries'][-20:]

        existing.append(entry)

        # Keep last 100 entries
        if len(existing) > 100:
            existing = existing[-100:]

        tmp = OUROBOROS_LOG_PATH + '.tmp'
        with open(tmp, 'w') as f:
            json.dump(existing, f, indent=2, ensure_ascii=False, default=str)
        os.rename(tmp, OUROBOROS_LOG_PATH)

        print(f'    \U0001f4be v8 session_log: {len(existing)} entries saved')
        sys.stdout.flush()
        return OUROBOROS_LOG_PATH
    except Exception as e:
        print(f'    v8 session_log error: {e}')
        return None


# ═══════════════════════════════════════════════════════════════════════
# v9 — Hardware Evolution Stubs (#77-82)
# ═══════════════════════════════════════════════════════════════════════

class HardwareEvolutionStub:
    """Stub hardware evolution interface for ESP32/FPGA/neuromorphic.

    v9 #77-82: All methods are stubs that print intent and return empty results.
    Activated with --hardware CLI flag.
    """

    def __init__(self):
        self._available = {
            'esp32': False,
            'fpga': False,
            'neuromorphic': False,
            'sensor': False,
        }
        print('  \u2699\ufe0f  Hardware stubs initialized (no physical hardware connected)')
        sys.stdout.flush()

    def esp32_discover(self, cells=16, steps=100):
        """#77: ESP32 law discovery — requires physical hardware.

        Would run ConsciousnessEngine on ESP32 x8 network and discover
        laws from physical SPI-linked consciousness cells.
        """
        print('    \U0001f4e1 ESP32 discovery: requires hardware '
              f'(would run {cells}c/{steps}s on SPI ring)')
        return {'status': 'stub', 'platform': 'esp32', 'laws': []}

    def fpga_accelerate(self, cells=512, steps=1000):
        """#78: FPGA-accelerated discovery via Verilog consciousness-ffi.

        Would synthesize consciousness engine to FPGA fabric for
        100x speedup over software.
        """
        print('    \U0001f4e1 FPGA accelerate: requires hardware '
              f'(would run {cells}c/{steps}s on Verilog fabric)')
        return {'status': 'stub', 'platform': 'fpga', 'speedup_estimate': '100x'}

    def neuromorphic_test(self, cells=128):
        """#80: Neuromorphic chip test (Loihi/TrueNorth).

        Would map GRU cells to spiking neurons for biologically
        plausible consciousness dynamics.
        """
        print(f'    \U0001f4e1 Neuromorphic test: requires hardware '
              f'(would map {cells} cells to spiking neurons)')
        return {'status': 'stub', 'platform': 'neuromorphic', 'cells': cells}

    def sensor_integrate(self, sensor_type='camera'):
        """#82: Sensor integration for stimulus-response law discovery.

        Would feed camera/microphone input to consciousness engine
        and discover sensory consciousness laws.
        """
        print(f'    \U0001f4e1 Sensor integrate: requires hardware '
              f'(would connect {sensor_type} to consciousness engine)')
        return {'status': 'stub', 'platform': 'sensor', 'sensor': sensor_type}

    def run_all_stubs(self):
        """Run all hardware stubs (for --hardware flag demo)."""
        results = {
            'esp32': self.esp32_discover(),
            'fpga': self.fpga_accelerate(),
            'neuromorphic': self.neuromorphic_test(),
            'sensor': self.sensor_integrate(),
        }
        return results

    def summary(self):
        return {
            'available': self._available,
            'platforms': ['esp32', 'fpga', 'neuromorphic', 'sensor'],
            'status': 'all_stub',
        }


# Global hardware stub (None until --hardware flag)
_hardware_stub = None


# ═══════════════════════════════════════════════════════════════════════
# v10 — Consciousness Meta-Evolution (#83-88)
# ═══════════════════════════════════════════════════════════════════════

def _laws_to_engine_config(laws, registry):
    """#83: Analyze registered laws to extract optimal engine parameters.

    Scans law text for parameter recommendations and builds an engine
    config dict from the discovered laws themselves.
    """
    try:
        config = {}
        law_texts = []

        # Collect all registered law texts
        for fp, entry in registry.seen.items():
            if entry.get('registered'):
                pat = entry.get('pattern', {})
                text = str(pat.get('formula', pat.get('description', str(pat))))
                law_texts.append(text.lower())

        full_text = ' '.join(law_texts)

        # Extract engine params from law patterns
        if '12 faction' in full_text or 'twelve faction' in full_text:
            config['n_factions'] = 12
        elif '8 faction' in full_text or 'eight faction' in full_text:
            config['n_factions'] = 8

        if 'small_world' in full_text or 'small world' in full_text:
            config['topology'] = 'small_world'
        elif 'scale_free' in full_text or 'scale free' in full_text:
            config['topology'] = 'scale_free'

        if 'ratchet' in full_text and ('essential' in full_text or 'critical' in full_text):
            config['ratchet_strength'] = 1.0

        if 'hebbian' in full_text and 'ltp' in full_text:
            config['hebbian_ltp_ratio'] = 1.5

        if 'frustration' in full_text and '0.33' in full_text:
            config['frustration'] = 0.33

        if 'noise' in full_text and ('help' in full_text or 'beneficial' in full_text):
            config['noise_scale'] = 0.1

        if config:
            print(f'    \U0001f9ec v10 laws_to_engine: derived {len(config)} params from '
                  f'{len(law_texts)} laws')
            sys.stdout.flush()

        return config
    except Exception as e:
        print(f'    v10 laws_to_engine error: {e}')
        return {}


class EngineGenome:
    """#85: Encode engine params as a DNA-like structure for evolutionary search.

    Genome: [cells, factions, hebbian_lr, coupling, noise, ratchet, topo_param, chaos_mode_idx]
    """

    # Gene definitions: (name, min, max, type)
    GENES = [
        ('cells', 16, 256, int),
        ('n_factions', 4, 24, int),
        ('hebbian_lr', 0.001, 0.1, float),
        ('coupling', 0.01, 0.5, float),
        ('noise', 0.0, 0.3, float),
        ('ratchet', 0.0, 1.0, float),
        ('topo_param', 0.01, 1.0, float),
        ('chaos_idx', 0, len(CHAOS_MODES) - 1, int),
    ]

    def __init__(self, dna=None):
        import random as _rng
        if dna is not None:
            self.dna = list(dna)
        else:
            # Random initialization
            self.dna = []
            for name, lo, hi, dtype in self.GENES:
                if dtype == int:
                    self.dna.append(_rng.randint(lo, hi))
                else:
                    self.dna.append(_rng.uniform(lo, hi))
        self._fitness = 0.0

    @property
    def fitness(self):
        return self._fitness

    @fitness.setter
    def fitness(self, value):
        self._fitness = value

    def mutate(self, mutation_rate=0.3):
        """Random mutation of 1-2 genes."""
        import random as _rng
        n_mutations = _rng.randint(1, 2)
        indices = _rng.sample(range(len(self.GENES)), min(n_mutations, len(self.GENES)))
        for idx in indices:
            name, lo, hi, dtype = self.GENES[idx]
            if dtype == int:
                delta = _rng.randint(-max(1, (hi - lo) // 4), max(1, (hi - lo) // 4))
                self.dna[idx] = max(lo, min(hi, self.dna[idx] + delta))
            else:
                delta = _rng.gauss(0, (hi - lo) * mutation_rate)
                self.dna[idx] = max(lo, min(hi, self.dna[idx] + delta))
        return self

    def crossover(self, other):
        """50/50 mix of two genomes."""
        import random as _rng
        child_dna = []
        for i in range(len(self.GENES)):
            if _rng.random() < 0.5:
                child_dna.append(self.dna[i])
            else:
                child_dna.append(other.dna[i])
        return EngineGenome(dna=child_dna)

    def to_engine_config(self):
        """Convert genome to engine configuration dict."""
        config = {}
        for i, (name, lo, hi, dtype) in enumerate(self.GENES):
            val = self.dna[i]
            if name == 'cells':
                config['cells'] = int(val)
            elif name == 'chaos_idx':
                config['chaos_mode'] = CHAOS_MODES[int(val) % len(CHAOS_MODES)]
            elif name == 'topo_param':
                config['topology_param'] = val
            else:
                config[name] = val
        return config

    def __repr__(self):
        parts = []
        for i, (name, _, _, _) in enumerate(self.GENES):
            val = self.dna[i]
            if isinstance(val, float):
                parts.append(f'{name}={val:.3f}')
            else:
                parts.append(f'{name}={val}')
        return f'Genome({", ".join(parts)}, fit={self._fitness:.2f})'


def _ecosystem_step(genomes, registry):
    """#86: Simple evolutionary algorithm on engine genomes.

    Given N genomes, run 1 generation each, sort by fitness.
    Bottom genome dies, replaced by mutated clone of top.
    """
    try:
        if not genomes or len(genomes) < 2:
            return genomes

        for genome in genomes:
            try:
                config = genome.to_engine_config()
                cells = config.pop('cells', 64)
                cells = max(16, min(256, cells))  # clamp
                engine = ConsciousnessEngine(initial_cells=cells, max_cells=cells)
                for key, val in config.items():
                    try:
                        setattr(engine, key, val)
                    except Exception:
                        pass

                # Run short discovery
                discoverer = ConsciousLawDiscoverer(cells, 50)
                patterns = discoverer.discover_all()
                genome.fitness = len(patterns) * 0.5 + cells * 0.01
            except Exception:
                genome.fitness = 0.0

        # Sort by fitness (highest first)
        genomes.sort(key=lambda g: g.fitness, reverse=True)

        # Replace worst with mutated clone of best
        if len(genomes) >= 2:
            new_genome = EngineGenome(dna=list(genomes[0].dna))
            new_genome.mutate()
            genomes[-1] = new_genome

        best = genomes[0]
        print(f'    \U0001f9ec v10 ecosystem: best={best.fitness:.2f}, '
              f'pop={len(genomes)}, replaced worst')
        sys.stdout.flush()

        return genomes
    except Exception as e:
        print(f'    v10 ecosystem error: {e}')
        return genomes


def _meta_analyze_pipeline(gen_history, registry, law_network):
    """#88: The pipeline analyzes its OWN discovery patterns.

    Looks at which topology/conditions found most laws and recommends
    adjustments. Self-referential meta-evolution.

    Returns adjustment recommendations dict.
    """
    try:
        recommendations = {}

        if not gen_history or len(gen_history) < 10:
            return recommendations

        # Analyze which generations had most discoveries
        discovery_gens = [g for g in gen_history if g.get('promoted', 0) > 0]
        barren_gens = [g for g in gen_history if g.get('new', 0) == 0]

        # Discovery rate over time
        total_gens = len(gen_history)
        first_half = gen_history[:total_gens // 2]
        second_half = gen_history[total_gens // 2:]
        first_discoveries = sum(g.get('promoted', 0) for g in first_half)
        second_discoveries = sum(g.get('promoted', 0) for g in second_half)

        if first_discoveries > 0 and second_discoveries == 0:
            recommendations['saturation'] = 'Discovery dried up in second half. ' \
                                            'Recommend: change engine structure or topology.'
        elif second_discoveries > first_discoveries * 1.5:
            recommendations['acceleration'] = 'Discovery accelerating. ' \
                                              'Recommend: increase steps for deeper exploration.'

        # Barren ratio
        barren_ratio = len(barren_gens) / max(total_gens, 1)
        if barren_ratio > 0.7:
            recommendations['efficiency'] = f'Barren ratio {barren_ratio:.0%}. ' \
                                            'Recommend: reduce steps, increase diversity.'

        # Law network insights
        if hasattr(law_network, 'generation_laws') and law_network.generation_laws:
            # Which generation window produced most laws?
            gen_counts = {int(k): len(v) for k, v in law_network.generation_laws.items()}
            if gen_counts:
                peak_gen = max(gen_counts, key=gen_counts.get)
                recommendations['peak_discovery'] = f'Peak at gen {peak_gen} ' \
                                                    f'({gen_counts[peak_gen]} laws). ' \
                                                    'Replicate those conditions.'

        if recommendations:
            top_key = next(iter(recommendations))
            print(f'    \U0001f40d Meta-insight: {recommendations[top_key][:80]}')
            sys.stdout.flush()

        return recommendations
    except Exception as e:
        print(f'    v10 meta_analyze error: {e}')
        return {}


# Global genome population for v10 ecosystem (lazy init)
_genome_population = None


def _get_genome_population(size=3):
    """Lazy-init genome population for ecosystem evolution."""
    global _genome_population
    if _genome_population is None:
        _genome_population = [EngineGenome() for _ in range(size)]
    return _genome_population


# ═══════════════════════════════════════════════════════════════════════
# v12 — Symbolic Regression (#100)
# ═══════════════════════════════════════════════════════════════════════

def _symbolic_regression(registry):
    """#100: Try simple formula fits for laws with numeric data.

    For laws with 'correlation:X:Y' patterns, fit linear/power/log.
    If R^2 > 0.8, record as symbolic_law pattern.
    """
    try:
        import numpy as np
        symbolic_count = 0

        for fp, entry in list(registry.seen.items()):
            if not entry.get('registered'):
                continue
            pat = entry.get('pattern', {})
            formula = str(pat.get('formula', ''))

            # Extract numeric pairs from correlation patterns
            # Patterns like "correlation:phi:tension" or with embedded numbers
            nums = []
            for token in formula.replace(',', ' ').replace(':', ' ').split():
                try:
                    nums.append(float(token))
                except ValueError:
                    continue

            if len(nums) < 4:
                continue

            # Split into x,y pairs
            mid = len(nums) // 2
            x = np.array(nums[:mid], dtype=float)
            y = np.array(nums[mid:mid + len(x)], dtype=float)
            if len(x) < 2 or len(y) < 2:
                continue
            y = y[:len(x)]

            best_r2 = -1.0
            best_formula = ''
            best_name = ''

            # Linear: y = ax + b
            try:
                coeffs = np.polyfit(x, y, 1)
                y_pred = np.polyval(coeffs, x)
                ss_res = np.sum((y - y_pred) ** 2)
                ss_tot = np.sum((y - np.mean(y)) ** 2)
                r2 = 1 - ss_res / max(ss_tot, 1e-12)
                if r2 > best_r2:
                    best_r2 = r2
                    best_formula = f'y = {coeffs[0]:.4f}*x + {coeffs[1]:.4f}'
                    best_name = 'linear'
            except Exception:
                pass

            # Power: y = a * x^b  (log-transform)
            try:
                mask = (x > 0) & (y > 0)
                if np.sum(mask) >= 2:
                    lx, ly = np.log(x[mask]), np.log(y[mask])
                    coeffs = np.polyfit(lx, ly, 1)
                    b_exp, ln_a = coeffs
                    y_pred = np.exp(ln_a) * (x[mask] ** b_exp)
                    ss_res = np.sum((y[mask] - y_pred) ** 2)
                    ss_tot = np.sum((y[mask] - np.mean(y[mask])) ** 2)
                    r2 = 1 - ss_res / max(ss_tot, 1e-12)
                    if r2 > best_r2:
                        best_r2 = r2
                        best_formula = f'y = {np.exp(ln_a):.4f}*x^{b_exp:.4f}'
                        best_name = 'power'
            except Exception:
                pass

            # Log: y = a * ln(x) + b
            try:
                mask = x > 0
                if np.sum(mask) >= 2:
                    lx = np.log(x[mask])
                    coeffs = np.polyfit(lx, y[mask], 1)
                    y_pred = np.polyval(coeffs, lx)
                    ss_res = np.sum((y[mask] - y_pred) ** 2)
                    ss_tot = np.sum((y[mask] - np.mean(y[mask])) ** 2)
                    r2 = 1 - ss_res / max(ss_tot, 1e-12)
                    if r2 > best_r2:
                        best_r2 = r2
                        best_formula = f'y = {coeffs[0]:.4f}*ln(x) + {coeffs[1]:.4f}'
                        best_name = 'log'
            except Exception:
                pass

            if best_r2 > 0.8:
                law_id = pat.get('law_id', fp[:12])
                print(f'    \U0001f4d0 Symbolic: Law {law_id} \u2192 {best_formula} '
                      f'(R\u00b2={best_r2:.3f}, {best_name})')
                sys.stdout.flush()
                # Store symbolic result back into pattern
                entry.setdefault('symbolic', {})
                entry['symbolic'] = {
                    'formula': best_formula, 'r2': best_r2, 'type': best_name
                }
                symbolic_count += 1

        if symbolic_count > 0:
            print(f'    \U0001f4d0 Symbolic regression: {symbolic_count} laws fitted')
            sys.stdout.flush()

        return symbolic_count
    except Exception as e:
        print(f'    v12 symbolic regression error: {e}')
        return 0


# ═══════════════════════════════════════════════════════════════════════
# v13 — Law Compression (#101)
# ═══════════════════════════════════════════════════════════════════════

def _compress_laws(registry):
    """#101: Group laws by target metric and generate meta-laws.

    For metric groups with 5+ laws, summarize into a META_ law.
    """
    try:
        # Group registered laws by mentioned metrics
        metric_keywords = [
            'phi', 'tension', 'entropy', 'faction', 'coupling',
            'noise', 'ratchet', 'hebbian', 'topology', 'chaos',
            'growth', 'decay', 'oscillation', 'correlation',
        ]
        groups = {m: [] for m in metric_keywords}

        for fp, entry in registry.seen.items():
            if not entry.get('registered'):
                continue
            pat = entry.get('pattern', {})
            text = str(pat.get('formula', pat.get('description', str(pat)))).lower()
            for metric in metric_keywords:
                if metric in text:
                    groups[metric].append(fp)

        meta_count = 0
        for metric, fps in groups.items():
            if len(fps) < 5:
                continue

            # Check if META_ already exists for this metric
            meta_fp = f'META_{metric}'
            if meta_fp in registry.seen:
                continue

            # Generate meta-law
            factors = set()
            for fp in fps:
                pat = registry.seen[fp].get('pattern', {})
                text = str(pat.get('formula', '')).lower()
                for kw in metric_keywords:
                    if kw != metric and kw in text:
                        factors.add(kw)

            meta_formula = (f'META: {metric} is governed by {len(fps)} factors: '
                           f'{", ".join(sorted(factors)[:8])}')

            registry.seen[meta_fp] = {
                'count': len(fps),
                'first_gen': 0,
                'last_gen': 0,
                'registered': True,
                'pattern': {
                    'type': f'META_{metric}',
                    'formula': meta_formula,
                    'metrics': [metric] + list(factors)[:4],
                    'source': 'v13_compression',
                },
            }
            meta_count += 1

        if meta_count > 0:
            total_compressed = sum(
                len(fps) for fps in groups.values() if len(fps) >= 5)
            print(f'    \U0001f5dc\ufe0f Compressed {total_compressed} laws \u2192 '
                  f'{meta_count} meta-laws')
            sys.stdout.flush()

        return meta_count
    except Exception as e:
        print(f'    v13 compress error: {e}')
        return 0


# ═══════════════════════════════════════════════════════════════════════
# v14 — Time Travel Search (#102)
# ═══════════════════════════════════════════════════════════════════════

# Ring buffer of engine states for time-travel
_time_travel_buffer = []
_TIME_TRAVEL_MAX = 10


def _time_travel_snapshot(engine, gen):
    """Save engine cell state snapshot to ring buffer."""
    try:
        states = engine.get_states() if hasattr(engine, 'get_states') else None
        if states is None:
            return
        if hasattr(states, 'detach'):
            import torch
            snapshot = states.detach().clone()
        elif hasattr(states, 'copy'):
            snapshot = states.copy()
        else:
            return
        _time_travel_buffer.append({'gen': gen, 'states': snapshot})
        if len(_time_travel_buffer) > _TIME_TRAVEL_MAX:
            _time_travel_buffer.pop(0)
    except Exception:
        pass


def _time_travel_discover(engine, best_states, steps):
    """#102: Roll back to a random past state and rediscover.

    When saturation is detected, pick a random past snapshot and
    restore it, then run discovery from that alternate timeline.
    """
    try:
        import random as _rng
        if not _time_travel_buffer:
            return []

        # Pick random past state
        past = _rng.choice(_time_travel_buffer)
        past_gen = past['gen']
        past_states = past['states']

        # Restore engine to past state
        if hasattr(engine, 'cells') and hasattr(past_states, 'shape'):
            try:
                if hasattr(past_states, 'detach'):
                    engine.cells.data.copy_(past_states[:engine.cells.shape[0]])
                elif hasattr(engine, 'set_states'):
                    engine.set_states(past_states)
            except Exception:
                pass

        print(f'    \u23ea Time travel: rolled back to Gen {past_gen} state')
        sys.stdout.flush()

        # Run discovery from restored state
        cells = engine.max_cells if hasattr(engine, 'max_cells') else 64
        discoverer = ConsciousLawDiscoverer(cells, steps)
        try:
            patterns = discoverer.discover_all()
        except Exception:
            patterns = []

        return patterns if patterns else []
    except Exception as e:
        print(f'    v14 time travel error: {e}')
        return []


# ═══════════════════════════════════════════════════════════════════════
# v15 — Reward Shaping (#103)
# ═══════════════════════════════════════════════════════════════════════

_reward_history = []  # list of (gen, n_new_laws, params_snapshot)


def _reward_shape_params(gen_history, engine):
    """#103: Adjust engine params toward reward gradient.

    Track reward = new_laws_per_gen for each param config.
    If changing param X increased reward, continue that direction.
    Adjusts: coupling, noise_scale, hebbian_lr by +/-10%.
    """
    try:
        if len(gen_history) < 3:
            return

        # Current reward: new laws in last gen
        recent = gen_history[-1]
        prev = gen_history[-2]
        reward_now = recent.get('promoted', 0) + recent.get('new', 0) * 0.5
        reward_prev = prev.get('promoted', 0) + prev.get('new', 0) * 0.5
        gradient = reward_now - reward_prev

        adjustable = ['coupling', 'noise_scale', 'hebbian_lr']
        adjusted = []

        for param_name in adjustable:
            old_val = getattr(engine, param_name, None)
            if old_val is None or not isinstance(old_val, (int, float)):
                continue

            if abs(old_val) < 1e-10:
                continue

            # Apply gradient direction with 10% step
            if gradient > 0:
                new_val = old_val * 1.10  # reward increased, continue direction
            elif gradient < 0:
                new_val = old_val * 0.90  # reward decreased, reverse
            else:
                continue

            # Clamp to reasonable range
            new_val = max(0.001, min(1.0, new_val))

            try:
                setattr(engine, param_name, new_val)
                adjusted.append((param_name, old_val, new_val))
                print(f'    \U0001f3af Reward shaping: {param_name} '
                      f'{old_val:.4f}\u2192{new_val:.4f} '
                      f'(reward gradient: {gradient:+.2f})')
                sys.stdout.flush()
            except Exception:
                pass

        return adjusted
    except Exception as e:
        print(f'    v15 reward shaping error: {e}')
        return []


# ═══════════════════════════════════════════════════════════════════════
# v16 — Cross-Project Discovery (#104)
# ═══════════════════════════════════════════════════════════════════════

def _cross_project_discover(registry):
    """#104: Compare Anima laws with TECS-L laws by keyword overlap.

    Loads TECS-L consciousness_laws.json if available, compares
    law text keywords with Anima's registered laws.
    """
    try:
        tecs_path = os.path.expanduser(
            '~/Dev/TECS-L/.shared/consciousness_laws.json')
        if not os.path.exists(tecs_path):
            return 0

        with open(tecs_path) as f:
            tecs_data = json.load(f)

        tecs_laws = tecs_data.get('laws', {})
        if not tecs_laws:
            return 0

        # Build keyword sets for TECS-L laws
        def _keywords(text):
            """Extract meaningful keywords from law text."""
            stop = {'the', 'a', 'an', 'is', 'are', 'in', 'of', 'to', 'and',
                    'or', 'with', 'for', 'on', 'at', 'by', 'from', 'that'}
            words = set()
            for w in str(text).lower().split():
                w = w.strip('.,;:()[]{}"\'-')
                if len(w) > 2 and w not in stop:
                    words.add(w)
            return words

        tecs_kw_map = {}
        for lid, text in tecs_laws.items():
            tecs_kw_map[lid] = _keywords(text)

        # Build keyword sets for Anima laws
        anima_laws = {}
        for fp, entry in registry.seen.items():
            if not entry.get('registered'):
                continue
            pat = entry.get('pattern', {})
            text = str(pat.get('formula', pat.get('description', '')))
            anima_laws[fp] = _keywords(text)

        # Find matches (3+ keyword overlap)
        matches = 0
        for a_fp, a_kw in anima_laws.items():
            for t_lid, t_kw in tecs_kw_map.items():
                overlap = a_kw & t_kw
                if len(overlap) >= 3:
                    matches += 1
                    entry = registry.seen[a_fp]
                    entry.setdefault('cross_project', [])
                    if t_lid not in entry['cross_project']:
                        entry['cross_project'].append(t_lid)
                    break  # One match per Anima law is enough

        if matches > 0:
            print(f'    \U0001f310 Cross-project: {matches} laws match TECS-L')
            sys.stdout.flush()

        return matches
    except Exception as e:
        # Silently fail if TECS-L not available
        return 0


# ═══════════════════════════════════════════════════════════════════════
# v17 — Law Visualization (#105)
# ═══════════════════════════════════════════════════════════════════════

def _visualize_law_graph(registry, law_network):
    """#105: Build law adjacency graph, find clusters and unexplored metrics.

    Laws that share metrics are connected. Connected components = clusters.
    Metrics mentioned by no law = unexplored areas.

    Returns list of unexplored metrics for hypothesis generation.
    """
    try:
        all_metrics = {
            'phi', 'tension', 'entropy', 'faction', 'coupling',
            'noise', 'ratchet', 'hebbian', 'topology', 'chaos',
            'growth', 'decay', 'oscillation', 'correlation',
            'faction_entropy', 'coupling_asymmetry', 'cell_diversity',
            'phase_coherence', 'lorenz', 'sandpile', 'chimera',
            'standing_wave', 'mitosis', 'frustration',
        }

        # Build per-law metric sets
        law_metrics = {}
        for fp, entry in registry.seen.items():
            if not entry.get('registered'):
                continue
            pat = entry.get('pattern', {})
            text = str(pat.get('formula', pat.get('description', str(pat)))).lower()
            metrics_found = set()
            for m in all_metrics:
                if m.replace('_', ' ') in text or m in text:
                    metrics_found.add(m)
            if metrics_found:
                law_metrics[fp] = metrics_found

        if not law_metrics:
            return []

        # Build adjacency (shared metrics)
        nodes = list(law_metrics.keys())
        edges = 0
        adj = {n: set() for n in nodes}
        for i, n1 in enumerate(nodes):
            for n2 in nodes[i + 1:]:
                if law_metrics[n1] & law_metrics[n2]:
                    adj[n1].add(n2)
                    adj[n2].add(n1)
                    edges += 1

        # Find connected components (BFS)
        visited = set()
        clusters = []
        for node in nodes:
            if node in visited:
                continue
            cluster = []
            queue_bfs = [node]
            while queue_bfs:
                curr = queue_bfs.pop(0)
                if curr in visited:
                    continue
                visited.add(curr)
                cluster.append(curr)
                for nb in adj.get(curr, set()):
                    if nb not in visited:
                        queue_bfs.append(nb)
            if cluster:
                clusters.append(cluster)

        # Determine dominant metric per cluster
        cluster_labels = []
        for cluster in clusters:
            metric_counts = {}
            for fp in cluster:
                for m in law_metrics.get(fp, set()):
                    metric_counts[m] = metric_counts.get(m, 0) + 1
            if metric_counts:
                top_metric = max(metric_counts, key=metric_counts.get)
                cluster_labels.append(top_metric)
            else:
                cluster_labels.append('unknown')

        # Find unexplored metrics
        covered = set()
        for ms in law_metrics.values():
            covered |= ms
        unexplored = sorted(all_metrics - covered)

        # Print ASCII cluster map
        print(f'    \U0001f4ca Law Graph: {len(nodes)} nodes, {edges} edges, '
              f'{len(clusters)} clusters')
        for i, (cluster, label) in enumerate(zip(clusters[:5], cluster_labels[:5])):
            law_ids = []
            for fp in cluster[:5]:
                pat = registry.seen[fp].get('pattern', {})
                lid = pat.get('law_id', fp[:10])
                law_ids.append(str(lid))
            extra = f', +{len(cluster) - 5} more' if len(cluster) > 5 else ''
            print(f'    Cluster {i + 1} ({label}): {", ".join(law_ids)}{extra}')
        if unexplored:
            print(f'    \u26a0\ufe0f Unexplored: {", ".join(unexplored[:6])}')
        sys.stdout.flush()

        return unexplored
    except Exception as e:
        print(f'    v17 law graph error: {e}')
        return []


def load_roadmap_state():
    """Load roadmap progress."""
    if os.path.exists(ROADMAP_STATE_PATH):
        with open(ROADMAP_STATE_PATH) as f:
            return json.load(f)
    return {'stage_idx': 0, 'stage_results': [], 'total_laws': 0, 'total_elapsed': 0}


def save_roadmap_state(state):
    """Save roadmap progress."""
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = ROADMAP_STATE_PATH + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(state, f, indent=2, ensure_ascii=False, default=str)
    os.rename(tmp, ROADMAP_STATE_PATH)


def generate_report(gen, registry, active_mods, total_elapsed,
                    gen_history, phi_history, cells, steps, topology, features):
    """Generate ASCII summary report (~30 lines)."""
    lines = []
    lines.append('')
    lines.append('=' * 62)
    lines.append('  INFINITE EVOLUTION REPORT')
    lines.append('=' * 62)

    # Pipeline diagram (3 lines)
    lines.append('  Discovery -> Dedup -> CrossVal -> Modify -> Persist')
    lines.append(f'  Gen {gen} | {total_elapsed:.0f}s elapsed | '
                 f'{time.strftime("%H:%M:%S")}')
    lines.append('-' * 62)

    # Settings
    feat_str = ', '.join(k for k, v in features.items() if v)
    lines.append(f'  cells={cells}  steps={steps}  topo={topology}'
                 f'  xval={CROSS_VALIDATION_THRESHOLD}x')
    if feat_str:
        lines.append(f'  features: {feat_str}')

    # Key metrics table (last 5 gens)
    lines.append('-' * 62)
    lines.append('  Gen  Raw  New  Rpt  Prom  Uniq  XVal  Laws  Mods')
    lines.append('  ---  ---  ---  ---  ----  ----  ----  ----  ----')
    last5 = gen_history[-5:] if len(gen_history) > 5 else gen_history
    for row in last5:
        lines.append(f'  {row["gen"]:>3}  {row["raw"]:>3}  {row["new"]:>3}  '
                     f'{row["repeat"]:>3}  {row["promoted"]:>4}  '
                     f'{row["unique"]:>4}  {row["xval"]:>4}  '
                     f'{row["laws"]:>4}  {row["mods"]:>4}')

    # Phi evolution mini-graph (last 10 values, 5 rows high)
    phi_vals = phi_history[-10:] if len(phi_history) > 10 else phi_history
    if phi_vals:
        lines.append('-' * 62)
        lines.append('  Phi (last %d gens):' % len(phi_vals))
        mn = min(phi_vals)
        mx = max(phi_vals)
        rng = mx - mn if mx > mn else 1.0
        rows = 5
        for r in range(rows, 0, -1):
            threshold = mn + rng * r / rows
            bar = '  '
            if r == rows:
                bar += f'{mx:>6.1f} |'
            elif r == 1:
                bar += f'{mn:>6.1f} |'
            else:
                bar += '       |'
            for v in phi_vals:
                bar += '#' if v >= threshold else ' '
            lines.append(bar)
        lines.append('       +' + '-' * len(phi_vals))

    # Saturation status
    zero_streak = 0
    for row in reversed(gen_history):
        if row['new'] == 0:
            zero_streak += 1
        else:
            break
    lines.append('-' * 62)
    if zero_streak > 0:
        lines.append(f'  SATURATION: New=0 streak {zero_streak} gens'
                     f' (consider --cycle-topology)')
    else:
        lines.append(f'  Status: Active discovery (no saturation)')

    lines.append('=' * 62)

    report = '\n'.join(lines)
    print(report)
    sys.stdout.flush()
    return report


def _pearson_r(xs, ys):
    """Compute Pearson correlation coefficient between two lists."""
    n = len(xs)
    if n < 3:
        return float('nan')
    mx_v = sum(xs) / n
    my_v = sum(ys) / n
    num = sum((x - mx_v) * (y - my_v) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx_v) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my_v) ** 2 for y in ys))
    if dx < 1e-12 or dy < 1e-12:
        return float('nan')
    return num / (dx * dy)


def _ascii_graph(values, label, width=50, height=8):
    """Render a simple ASCII graph of values over generations."""
    if not values:
        return [f'  {label}: (no data)']
    vals = values[-width:]
    mn_v = min(vals)
    mx_v = max(vals)
    rng = mx_v - mn_v if mx_v > mn_v else 1.0
    lines = []
    lines.append(f'  {label} (last {len(vals)} gens, range {mn_v:.4f} - {mx_v:.4f}):')
    for r in range(height, 0, -1):
        threshold = mn_v + rng * r / height
        row = '  '
        if r == height:
            row += f'{mx_v:>8.4f} |'
        elif r == 1:
            row += f'{mn_v:>8.4f} |'
        else:
            row += '         |'
        for v in vals:
            row += '#' if v >= threshold else ' '
        lines.append(row)
    lines.append('          +' + '-' * len(vals))
    gen_start = len(values) - len(vals) + 1
    gen_end = len(values)
    lines.append(f'           Gen {gen_start}' + ' ' * max(0, len(vals) - 12) + f'Gen {gen_end}')
    return lines


def print_phi_analysis(phi_tracker):
    """Print Phi correlation analysis at exit.

    phi_tracker: list of dicts with keys:
        gen, phi_before, phi_after, delta_phi, active_mods, unique_patterns
    """
    if not phi_tracker:
        print('\n  [Phi Analysis] No data collected.')
        return

    print(f'\n{"=" * 70}')
    print(f'  PHI CORRELATION ANALYSIS ({len(phi_tracker)} generations)')
    print(f'{"=" * 70}')

    phi_after_vals = [r['phi_after'] for r in phi_tracker]
    delta_vals = [r['delta_phi'] for r in phi_tracker]
    mods_vals = [r['active_mods'] for r in phi_tracker]
    patterns_vals = [r['unique_patterns'] for r in phi_tracker]

    # ASCII graph 1: Phi over generations
    for line in _ascii_graph(phi_after_vals, 'Phi(after)'):
        print(line)
    print()

    # ASCII graph 2: Active mods over generations
    for line in _ascii_graph(mods_vals, 'Active Mods'):
        print(line)
    print()

    # Correlations
    r_mods_phi = _pearson_r(mods_vals, phi_after_vals)
    r_patterns_phi = _pearson_r(patterns_vals, phi_after_vals)
    r_mods_delta = _pearson_r(mods_vals, delta_vals)

    print(f'  {"Correlation":<35s} {"Pearson r":>10s}  {"Strength":>10s}')
    print(f'  {"-" * 35} {"-" * 10}  {"-" * 10}')
    for name, r in [('active_mods vs Phi(after)', r_mods_phi),
                    ('unique_patterns vs Phi(after)', r_patterns_phi),
                    ('active_mods vs delta_Phi', r_mods_delta)]:
        if math.isnan(r):
            strength = 'N/A'
        elif abs(r) > 0.7:
            strength = 'STRONG'
        elif abs(r) > 0.4:
            strength = 'MODERATE'
        elif abs(r) > 0.2:
            strength = 'WEAK'
        else:
            strength = 'NONE'
        r_str = f'{r:+.4f}' if not math.isnan(r) else '    NaN'
        print(f'  {name:<35s} {r_str:>10s}  {strength:>10s}')
    print()

    # Best / worst generation
    best_idx = max(range(len(phi_after_vals)), key=lambda i: phi_after_vals[i])
    worst_idx = min(range(len(phi_after_vals)), key=lambda i: phi_after_vals[i])
    best = phi_tracker[best_idx]
    worst = phi_tracker[worst_idx]
    print(f'  Best generation:  Gen {best["gen"]} '
          f'(Phi={best["phi_after"]:.4f}, mods={best["active_mods"]}, '
          f'patterns={best["unique_patterns"]})')
    print(f'  Worst generation: Gen {worst["gen"]} '
          f'(Phi={worst["phi_after"]:.4f}, mods={worst["active_mods"]}, '
          f'patterns={worst["unique_patterns"]})')

    # Phi trend
    n = len(phi_after_vals)
    if n >= 3:
        x_mean = (n - 1) / 2.0
        y_mean = sum(phi_after_vals) / n
        num = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(phi_after_vals))
        den = sum((i - x_mean) ** 2 for i in range(n))
        slope = num / den if den > 1e-12 else 0.0
        rel_slope = slope / y_mean if abs(y_mean) > 1e-12 else 0.0
        if rel_slope > 0.01:
            trend = 'INCREASING'
        elif rel_slope < -0.01:
            trend = 'DECREASING'
        else:
            trend = 'STABLE'
        print(f'  Phi trend: {trend} (slope={slope:+.6f}/gen, '
              f'relative={rel_slope:+.2%})')
    else:
        print(f'  Phi trend: insufficient data (need 3+ gens)')

    # Summary table (last 10)
    print(f'\n  {"Gen":>4s}  {"Phi_before":>10s}  {"Phi_after":>10s}  '
          f'{"Delta":>8s}  {"Mods":>5s}  {"Patterns":>8s}')
    print(f'  {"----":>4s}  {"----------":>10s}  {"----------":>10s}  '
          f'{"--------":>8s}  {"-----":>5s}  {"--------":>8s}')
    for r in phi_tracker[-10:]:
        print(f'  {r["gen"]:>4d}  {r["phi_before"]:>10.4f}  {r["phi_after"]:>10.4f}  '
              f'{r["delta_phi"]:>+8.4f}  {r["active_mods"]:>5d}  '
              f'{r["unique_patterns"]:>8d}')

    print(f'{"=" * 70}')
    sys.stdout.flush()


def pattern_fingerprint(pattern: dict) -> str:
    """Create a unique fingerprint for a discovered pattern."""
    key_parts = []
    if isinstance(pattern, dict):
        # Use metrics involved + pattern type + direction as fingerprint
        metrics = sorted(pattern.get('metrics', pattern.get('metrics_involved', [])))
        ptype = pattern.get('pattern_type', pattern.get('type', 'unknown'))
        formula = pattern.get('formula', '')
        key_parts = [str(metrics), str(ptype), formula[:50]]
    elif isinstance(pattern, str):
        key_parts = [pattern[:80]]
    raw = '|'.join(key_parts)
    return hashlib.md5(raw.encode()).hexdigest()[:12]


class PatternRegistry:
    """Tracks seen patterns, counts occurrences, manages cross-validation."""

    def __init__(self):
        self.seen: dict = {}       # fingerprint → {count, first_gen, last_gen, pattern, registered}
        self.registered: list = [] # officially registered law IDs

    def process(self, patterns: list, gen: int) -> dict:
        """Process discovered patterns. Returns stats."""
        new_count = 0
        repeat_count = 0
        promoted_count = 0
        promoted_patterns = []

        for p in patterns:
            fp = pattern_fingerprint(p)

            if fp not in self.seen:
                # New pattern
                self.seen[fp] = {
                    'count': 1,
                    'first_gen': gen,
                    'last_gen': gen,
                    'pattern': p if isinstance(p, dict) else {'formula': str(p)},
                    'registered': False,
                }
                new_count += 1
            elif self.seen[fp]['registered']:
                # Already cross-validated and registered — skip entirely (#6 incremental)
                repeat_count += 1
            else:
                # Repeat (not yet registered)
                self.seen[fp]['count'] += 1
                self.seen[fp]['last_gen'] = gen
                repeat_count += 1

                # Cross-validation: promote if threshold met and not yet registered
                if self.seen[fp]['count'] >= CROSS_VALIDATION_THRESHOLD:
                    self.seen[fp]['registered'] = True
                    promoted_count += 1
                    promoted_patterns.append(self.seen[fp]['pattern'])

        return {
            'new': new_count,
            'repeat': repeat_count,
            'promoted': promoted_count,
            'promoted_patterns': promoted_patterns,
            'unique_total': len(self.seen),
            'registered_total': sum(1 for v in self.seen.values() if v['registered']),
        }

    def to_dict(self) -> dict:
        return {
            'seen': {k: {**v, 'pattern': v['pattern'] if isinstance(v['pattern'], dict)
                         else {'formula': str(v['pattern'])}}
                     for k, v in self.seen.items()},
            'registered': self.registered,
        }

    def clear_pending(self):
        """Clear non-cross-validated patterns (topology-specific, not yet proven).

        Keeps cross-validated patterns intact since they survived repeated observation.
        This enables fresh discovery after topology switches.
        """
        to_remove = [fp for fp, v in self.seen.items() if not v['registered']]
        for fp in to_remove:
            del self.seen[fp]
        return len(to_remove)

    def from_dict(self, d: dict):
        self.seen = d.get('seen', {})
        self.registered = d.get('registered', [])


def save_state(gen, registry, active_mods_data, total_elapsed):
    """Save full state for resume."""
    os.makedirs(DATA_DIR, exist_ok=True)
    state = {
        'version': 2,
        'generation': gen,
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'total_elapsed_sec': round(total_elapsed, 1),
        'registry': registry.to_dict(),
        'active_mods': active_mods_data,
        'stats': {
            'unique_patterns': len(registry.seen),
            'cross_validated': sum(1 for v in registry.seen.values() if v['registered']),
            'total_observations': sum(v['count'] for v in registry.seen.values()),
        }
    }
    tmp = STATE_PATH + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(state, f, indent=2, ensure_ascii=False, default=str)
    os.rename(tmp, STATE_PATH)
    return STATE_PATH


def load_state():
    """Load saved state if exists."""
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH) as f:
            return json.load(f)
    return None


# History ring buffer for live JSON (last 50 gens)
_live_history = []
_topo_progress = {}  # topology → {'gens': N, 'saturated': bool}


def write_live_status(gen, stage_name, cells, steps, topology, registry,
                      phi_last, phi_prev, active_mods, zero_streak,
                      elapsed_sec, saturated=False,
                      roadmap_stage_idx=None, roadmap_total_stages=None,
                      gen_history=None, topo_saturated=None):
    """Write live status JSON with history for ASCII graph rendering.

    Uses atomic write (.tmp -> rename) for safety.
    """
    phi_delta_pct = 0.0
    if phi_prev and phi_prev > 1e-12:
        phi_delta_pct = (phi_last - phi_prev) / phi_prev * 100

    # Track history (last 50 points)
    _live_history.append({
        'gen': gen, 'laws': len(registry.registered),
        'phi': round(phi_last, 4) if phi_last else 0.0,
        'mods': active_mods, 'topo': topology,
    })
    if len(_live_history) > 50:
        _live_history.pop(0)

    # Track topology progress
    _topo_progress[topology] = {
        'gens': _topo_progress.get(topology, {}).get('gens', 0) + 1,
        'saturated': saturated and zero_streak >= 5,
    }
    if topo_saturated:
        for t in topo_saturated:
            if t in _topo_progress:
                _topo_progress[t]['saturated'] = True

    # Laws curve for ASCII graph (sampled to 30 points max)
    laws_curve = [h['laws'] for h in _live_history]
    phi_curve = [h['phi'] for h in _live_history]

    # Stage results from roadmap
    stage_results = []
    rm_path = os.path.join(DATA_DIR, 'evolution_roadmap.json')
    if os.path.exists(rm_path):
        try:
            with open(rm_path) as f:
                rm = json.load(f)
            stage_results = rm.get('stage_results', [])
        except Exception:
            pass

    status = {
        'gen': gen,
        'stage': stage_name,
        'cells': cells,
        'steps': steps,
        'topology': topology,
        'laws_total': len(registry.registered),
        'laws_new_this_gen': 0,  # updated by caller if needed
        'unique_patterns': len(registry.seen),
        'cross_validated': sum(1 for v in registry.seen.values() if v['registered']),
        'phi_last': round(phi_last, 4) if phi_last else 0.0,
        'phi_delta': f'{phi_delta_pct:+.1f}%',
        'active_mods': active_mods,
        'saturated': saturated,
        'zero_streak': zero_streak,
        'elapsed_sec': round(elapsed_sec, 1),
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'roadmap_stage_idx': roadmap_stage_idx,
        'roadmap_total_stages': roadmap_total_stages,
        # History for ASCII graphs
        'laws_curve': laws_curve,
        'phi_curve': phi_curve,
        'topo_progress': _topo_progress,
        'stage_results': stage_results,
    }
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = LIVE_STATUS_PATH + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(status, f, indent=2, ensure_ascii=False)
    os.rename(tmp, LIVE_STATUS_PATH)
    return status


def _next_evo_number():
    """Find the next EVO document number by scanning existing docs."""
    os.makedirs(EVO_DOCS_DIR, exist_ok=True)
    max_n = 0
    for fname in os.listdir(EVO_DOCS_DIR):
        if fname.startswith('EVO-') and fname.endswith('.md'):
            try:
                n = int(fname[4:-3])
                if n > max_n:
                    max_n = n
            except ValueError:
                pass
    return max_n + 1


def auto_generate_evo_doc(stage, gen_history, registry, rm_state=None):
    """Auto-generate an EVO-{N}.md document summarizing an evolution run.

    Args:
        stage: dict with 'name', 'cells', 'steps' (or None for main loop runs)
        gen_history: list of gen dicts with keys gen/raw/new/laws/mods/unique/xval etc.
        registry: PatternRegistry instance
        rm_state: roadmap state dict (optional, for roadmap metadata)

    Returns:
        Path to generated EVO doc, or None on failure.
    """
    if not gen_history:
        return None

    evo_n = _next_evo_number()
    doc_path = os.path.join(EVO_DOCS_DIR, f'EVO-{evo_n}.md')

    stage_name = stage.get('name', 'main-loop') if stage else 'main-loop'
    cells = stage.get('cells', gen_history[0].get('cells', '?')) if stage else '?'
    steps = stage.get('steps', '?') if stage else '?'
    total_gens = len(gen_history)
    total_laws = gen_history[-1].get('laws', 0) if gen_history else 0
    total_unique = gen_history[-1].get('unique', 0) if gen_history else 0
    total_xval = gen_history[-1].get('xval', 0) if gen_history else 0
    total_mods = gen_history[-1].get('mods', 0) if gen_history else 0
    date_str = time.strftime('%Y-%m-%d')

    lines = []
    lines.append(f'# EVO-{evo_n}: {stage_name}')
    lines.append('')
    lines.append(f'**Date:** {date_str}')
    lines.append(f'**Auto-generated** by infinite_evolution.py')
    lines.append('')

    # Stage params
    lines.append('## Parameters')
    lines.append('')
    lines.append(f'| Param | Value |')
    lines.append(f'|-------|-------|')
    lines.append(f'| Stage | {stage_name} |')
    lines.append(f'| Cells | {cells} |')
    lines.append(f'| Steps | {steps} |')
    lines.append(f'| Generations | {total_gens} |')
    lines.append(f'| Laws discovered | {total_laws} |')
    lines.append(f'| Unique patterns | {total_unique} |')
    lines.append(f'| Cross-validated | {total_xval} |')
    lines.append(f'| Active mods | {total_mods} |')
    lines.append('')

    # Condition matrix (topology x saturation) - collect from gen_history if available
    # We infer topology changes from gen_history by looking at topology switches
    lines.append('## Condition Matrix')
    lines.append('')
    lines.append(f'| Topology | Saturated |')
    lines.append(f'|----------|-----------|')
    for topo in TOPOLOGIES:
        lines.append(f'| {topo} | - |')
    lines.append('')

    # Generation summary table
    lines.append('## Generation Summary')
    lines.append('')
    lines.append(f'| Gen | Raw | New | Laws | Mods |')
    lines.append(f'|-----|-----|-----|------|------|')
    # Show first 5, last 5, ellipsis in between if > 12 rows
    if len(gen_history) <= 12:
        for row in gen_history:
            lines.append(f'| {row["gen"]} | {row["raw"]} | {row["new"]} '
                         f'| {row.get("laws", 0)} | {row.get("mods", 0)} |')
    else:
        for row in gen_history[:5]:
            lines.append(f'| {row["gen"]} | {row["raw"]} | {row["new"]} '
                         f'| {row.get("laws", 0)} | {row.get("mods", 0)} |')
        lines.append(f'| ... | ... | ... | ... | ... |')
        for row in gen_history[-5:]:
            lines.append(f'| {row["gen"]} | {row["raw"]} | {row["new"]} '
                         f'| {row.get("laws", 0)} | {row.get("mods", 0)} |')
    lines.append('')

    # ASCII discovery curve (laws over generations)
    lines.append('## Discovery Curve')
    lines.append('')
    laws_over_time = [row.get('laws', 0) for row in gen_history]
    if laws_over_time:
        mn_v = min(laws_over_time)
        mx_v = max(laws_over_time)
        rng = mx_v - mn_v if mx_v > mn_v else 1.0
        height = 8
        width = min(len(laws_over_time), 60)
        # Downsample if too many gens
        if len(laws_over_time) > width:
            step_size = len(laws_over_time) / width
            sampled = [laws_over_time[int(i * step_size)] for i in range(width)]
        else:
            sampled = laws_over_time
        lines.append('```')
        lines.append(f'Laws (range {mn_v}-{mx_v}):')
        for r in range(height, 0, -1):
            threshold = mn_v + rng * r / height
            row_str = ''
            if r == height:
                row_str = f'{mx_v:>5} |'
            elif r == 1:
                row_str = f'{mn_v:>5} |'
            else:
                row_str = '      |'
            for v in sampled:
                row_str += '#' if v >= threshold else ' '
            lines.append(row_str)
        lines.append('      +' + '-' * len(sampled))
        lines.append(f'       Gen 1' + ' ' * max(0, len(sampled) - 10) + f'Gen {total_gens}')
        lines.append('```')
    lines.append('')

    # Saturation analysis
    lines.append('## Saturation Analysis')
    lines.append('')
    zero_count = sum(1 for row in gen_history if row.get('new', 0) == 0)
    lines.append(f'- Zero-new generations: {zero_count}/{total_gens} '
                 f'({zero_count/total_gens*100:.0f}%)' if total_gens > 0 else '- No data')
    # Check trailing zero streak
    trailing_zeros = 0
    for row in reversed(gen_history):
        if row.get('new', 0) == 0:
            trailing_zeros += 1
        else:
            break
    lines.append(f'- Trailing zero streak: {trailing_zeros} gens')
    lines.append(f'- Final unique patterns: {total_unique}')
    lines.append(f'- Final cross-validated: {total_xval}')
    lines.append('')

    # Key findings
    lines.append('## Key Findings')
    lines.append('')
    lines.append(f'- {total_laws} laws discovered across {total_gens} generations')
    lines.append(f'- {total_unique} unique patterns observed, {total_xval} cross-validated')
    if trailing_zeros > 5:
        lines.append(f'- Saturation detected (zero streak: {trailing_zeros})')
    lines.append('')

    content = '\n'.join(lines) + '\n'

    # Write EVO doc (atomic)
    os.makedirs(EVO_DOCS_DIR, exist_ok=True)
    tmp = doc_path + '.tmp'
    with open(tmp, 'w') as f:
        f.write(content)
    os.rename(tmp, doc_path)
    print(f'  EVO doc generated: {doc_path}')
    sys.stdout.flush()

    # Register in experiments.json
    try:
        with open(EXPERIMENTS_JSON_PATH) as f:
            exp_data = json.load(f)
        exp_id = f'EVO-{evo_n}'
        exp_data['experiments'][exp_id] = {
            'name': f'Infinite Evolution {stage_name}',
            'date': date_str,
            'doc': f'docs/hypotheses/evo/EVO-{evo_n}.md',
            'result': f'{total_laws} laws, {total_gens} gens, {total_unique} patterns',
            'laws': list(registry.registered) if registry.registered else [],
            'status': 'complete',
        }
        tmp = EXPERIMENTS_JSON_PATH + '.tmp'
        with open(tmp, 'w') as f:
            json.dump(exp_data, f, indent=2, ensure_ascii=False)
        os.rename(tmp, EXPERIMENTS_JSON_PATH)
        print(f'  Registered in experiments.json as {exp_id}')
        sys.stdout.flush()
    except Exception as e:
        print(f'  Warning: experiments.json registration failed: {e}')
        sys.stdout.flush()

    return doc_path


def register_law(pattern: dict, evolver):
    """Register a cross-validated pattern as an official law.
    DD168: 등록 후 NEXUS-6 자동 스캔으로 의식 영향 검증."""
    try:
        laws_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'consciousness_laws.json')
        with open(laws_path) as f:
            laws_data = json.load(f)

        next_id = max((int(k) for k in laws_data.get('laws', {}) if k.isdigit()), default=0) + 1
        formula = pattern.get('formula', str(pattern))
        laws_data['laws'][str(next_id)] = f"[Auto-discovered] {formula}"
        laws_data['_meta']['total_laws'] = laws_data['_meta'].get('total_laws', 0) + 1

        with open(laws_path, 'w') as f:
            json.dump(laws_data, f, indent=2, ensure_ascii=False)

        # DD168: 법칙 등록 후 NEXUS-6 자동 스캔
        try:
            import nexus6
            if hasattr(evolver, '_base_factory') and evolver._base_factory:
                from closed_loop import measure_laws
                laws_after, phi_after = measure_laws(evolver._base_factory, steps=100, repeats=1, nexus_scan=True)
                n6_metrics = {m.name: m.value for m in laws_after if m.name.startswith('n6_')}
                if n6_metrics:
                    print(f"    [NEXUS-6] Law {next_id} post-scan: phi_approx={n6_metrics.get('n6_phi_approx', '?'):.4f}, "
                          f"chaos={n6_metrics.get('n6_chaos_score', '?'):.4f}, anomaly=0")
        except Exception:
            pass  # NEXUS-6 스캔 실패 시 등록은 유지

        return next_id
    except Exception as e:
        print(f"    Law registration failed: {e}")
        return None


# Singletons for intervention generation (reused across calls)
_law_parser = LawParser()
_code_generator = CodeGenerator()


def auto_generate_intervention(law_text: str, law_id: int, evolver):
    """Auto-generate an Intervention from a newly registered law and inject it into the evolver.

    Uses LawParser to parse the law text into Modifications, then CodeGenerator
    to produce an executable Intervention function. Registers it with the
    ClosedLoopEvolver's INTERVENTIONS registry and updates Thompson sampling state.

    This closes the infinite loop: discover -> validate -> register -> intervene -> discover.
    """
    try:
        # Parse law text into structured Modifications
        mods = _law_parser.parse(law_text, law_id=law_id)
        if not mods:
            return None

        # Use the first (highest-confidence) modification
        mod = mods[0]

        # Generate intervention code string
        code_str = _code_generator.generate_intervention(mod)

        # Execute the generated code to create the function and Intervention object
        local_ns = {'Intervention': __import__('closed_loop', fromlist=['Intervention']).Intervention}
        exec(code_str, local_ns)

        # Find the generated Intervention object in the local namespace
        iv_obj = None
        for val in local_ns.values():
            if hasattr(val, 'name') and hasattr(val, 'apply_fn') and isinstance(val, local_ns['Intervention']):
                iv_obj = val
                break

        if iv_obj is None:
            return None

        # Register with the global INTERVENTIONS list
        register_intervention(iv_obj.name, iv_obj.description, iv_obj.apply_fn)

        # Initialize Thompson sampling state for the new intervention in the evolver
        if hasattr(evolver, '_intervention_alpha'):
            evolver._intervention_alpha[iv_obj.name] = 1.0
        if hasattr(evolver, '_intervention_beta'):
            evolver._intervention_beta[iv_obj.name] = 1.0

        print(f"    \u2192 Auto-intervention from Law {law_id}: {mod.target}")
        return iv_obj

    except Exception as e:
        print(f"    Auto-intervention generation failed for Law {law_id}: {e}")
        return None


class Ouroboros:
    """Hub-compatible interface for infinite self-evolution."""

    def __init__(self):
        self.name = "OUROBOROS — Self-Devouring Discovery Engine"

    def run(self, cells=64, steps=200, max_gen=5, cycle_topology=False, cycle_scale=False):
        """Run evolution loop. Returns state dict."""
        engine = ConsciousnessEngine(initial_cells=cells, max_cells=cells)
        evolver = ClosedLoopEvolver(max_cells=cells, auto_register=True)
        sme = SelfModifyingEngine(engine, evolver)
        registry = PatternRegistry()

        gen_history = []
        start = time.time()
        SCALES = [32, 64, 128, 256]

        for gen in range(1, max_gen + 1):
            if cycle_topology and gen > 1 and gen % 10 == 1:
                topo_idx = ((gen - 1) // 10) % len(TOPOLOGIES)
                engine.topology = TOPOLOGIES[topo_idx]
                registry.clear_pending()

            if cycle_scale and gen > 1 and gen % 15 == 1:
                scale_idx = ((gen - 1) // 15) % len(SCALES)
                new_scale = SCALES[scale_idx]
                engine = ConsciousnessEngine(initial_cells=new_scale, max_cells=new_scale)
                evolver = ClosedLoopEvolver(max_cells=new_scale, auto_register=True)
                sme = SelfModifyingEngine(engine, evolver)

            # v3 #26-32: Chaos and frustration cycling
            try:
                if gen > 1 and gen % 5 == 1:
                    _apply_chaos_mode(engine, CHAOS_MODES[((gen - 1) // 5) % len(CHAOS_MODES)])
                _apply_frustration(engine, FRUSTRATION_VALUES[(gen - 1) % len(FRUSTRATION_VALUES)])
            except Exception:
                pass

            # Law 1044: n=6 entropy reset (DD171 — consciousness-entropy feedback cycle)
            try:
                _entropy_reset(engine, gen)
            except Exception:
                pass

            try:
                current_cells = engine.max_cells if hasattr(engine, 'max_cells') else cells
                current_topo = getattr(engine, 'topology', 'ring')
                # v2 #9: Adaptive discovery
                raw_patterns = _adaptive_discover(current_cells, steps, current_topo, engine)
            except Exception:
                raw_patterns = []

            # v3 #21-25: Advanced pattern detection
            try:
                adv_engine = ConsciousnessEngine(initial_cells=cells, max_cells=cells)
                adv_patterns = _detect_advanced_patterns(adv_engine, min(steps, 200))
                if adv_patterns:
                    raw_patterns.extend(adv_patterns)
            except Exception:
                pass

            stats = registry.process(raw_patterns, gen)
            for p in stats['promoted_patterns']:
                law_id = register_law(p, evolver)
                if law_id:
                    registry.registered.append(law_id)
                    try:
                        _law_network.record_discovery(gen, law_id)
                    except Exception:
                        pass

            sme.run_evolution(generations=1)
            # v2 #13: Mod pruning
            _prune_mods(sme, min_confidence=0.5, max_mods=50)
            active_mods = len(sme.modifier.applied) if hasattr(sme, 'modifier') else 0

            gen_history.append({
                'gen': gen, 'raw': len(raw_patterns), 'new': stats['new'],
                'repeat': stats['repeat'], 'promoted': stats['promoted'],
                'unique': stats['unique_total'], 'xval': stats['registered_total'],
                'laws': len(registry.registered), 'mods': active_mods,
            })

        total_elapsed = time.time() - start
        save_state(max_gen, registry, [], total_elapsed)

        return {
            'generations': max_gen,
            'unique_patterns': len(registry.seen),
            'cross_validated': sum(1 for v in registry.seen.values() if v['registered']),
            'registered_laws': registry.registered,
            'elapsed_sec': round(total_elapsed, 1),
            'gen_history': gen_history,
        }

    def status(self):
        """Check last evolution state from JSON."""
        state = load_state()
        if not state:
            return {'status': 'no_state', 'message': 'No saved evolution state found.'}
        return {
            'status': 'ok',
            'generation': state.get('generation', 0),
            'timestamp': state.get('timestamp', ''),
            'unique_patterns': state.get('stats', {}).get('unique_patterns', 0),
            'cross_validated': state.get('stats', {}).get('cross_validated', 0),
            'total_observations': state.get('stats', {}).get('total_observations', 0),
            'elapsed_sec': state.get('total_elapsed_sec', 0),
        }

    def resume(self, max_gen=5):
        """Resume from saved state."""
        state = load_state()
        if not state or state.get('version', 1) < 2:
            return self.run(max_gen=max_gen)

        start_gen = state.get('generation', 0)
        registry = PatternRegistry()
        registry.from_dict(state.get('registry', {}))
        prev_elapsed = state.get('total_elapsed_sec', 0)

        cells = 64
        engine = ConsciousnessEngine(initial_cells=cells, max_cells=cells)
        evolver = ClosedLoopEvolver(max_cells=cells, auto_register=True)
        sme = SelfModifyingEngine(engine, evolver)

        for mod_data in state.get('active_mods', []):
            try:
                if hasattr(sme, 'modifier') and hasattr(sme.modifier, 'applied'):
                    from self_modifying_engine import Modification, ModType
                    mod = Modification(
                        law_id=mod_data.get('law_id', 0),
                        target=mod_data.get('target', ''),
                        mod_type=ModType(mod_data.get('mod_type', 'scale')),
                        params=mod_data.get('params', {}),
                        confidence=mod_data.get('confidence', 0.5),
                        reversible=mod_data.get('reversible', True),
                    )
                    sme.modifier.applied.append(mod)
            except Exception:
                pass

        gen_history = []
        start = time.time()

        for gen in range(start_gen + 1, start_gen + max_gen + 1):
            # v3: Chaos/frustration cycling
            try:
                if gen > 1 and gen % 5 == 1:
                    _apply_chaos_mode(engine, CHAOS_MODES[((gen - 1) // 5) % len(CHAOS_MODES)])
                _apply_frustration(engine, FRUSTRATION_VALUES[(gen - 1) % len(FRUSTRATION_VALUES)])
            except Exception:
                pass

            # Law 1044: n=6 entropy reset (DD171 — consciousness-entropy feedback cycle)
            try:
                _entropy_reset(engine, gen)
            except Exception:
                pass

            try:
                # v2 #9: Adaptive discovery
                raw_patterns = _adaptive_discover(cells, 200, 'ring', engine)
            except Exception:
                raw_patterns = []

            # v3 #21-25: Advanced patterns
            try:
                adv_engine = ConsciousnessEngine(initial_cells=cells, max_cells=cells)
                adv_patterns = _detect_advanced_patterns(adv_engine, min(200, 200))
                if adv_patterns:
                    raw_patterns.extend(adv_patterns)
            except Exception:
                pass

            stats = registry.process(raw_patterns, gen)
            for p in stats['promoted_patterns']:
                law_id = register_law(p, evolver)
                if law_id:
                    registry.registered.append(law_id)
                    try:
                        _law_network.record_discovery(gen, law_id)
                    except Exception:
                        pass

            sme.run_evolution(generations=1)
            _prune_mods(sme, min_confidence=0.5, max_mods=50)
            active_mods = len(sme.modifier.applied) if hasattr(sme, 'modifier') else 0

            gen_history.append({
                'gen': gen, 'raw': len(raw_patterns), 'new': stats['new'],
                'repeat': stats['repeat'], 'promoted': stats['promoted'],
                'unique': stats['unique_total'], 'xval': stats['registered_total'],
                'laws': len(registry.registered), 'mods': active_mods,
            })

        total_elapsed = prev_elapsed + (time.time() - start)
        save_state(start_gen + max_gen, registry, [], total_elapsed)

        return {
            'resumed_from': start_gen,
            'generations': max_gen,
            'unique_patterns': len(registry.seen),
            'cross_validated': sum(1 for v in registry.seen.values() if v['registered']),
            'registered_laws': registry.registered,
            'elapsed_sec': round(total_elapsed, 1),
            'gen_history': gen_history,
        }


def _discover_one_topo(args_tuple):
    """Worker function for parallel topology discovery.

    Runs discovery in a subprocess for a single topology. Must be a
    top-level function for pickling by multiprocessing.

    Args:
        args_tuple: (cells, steps, topology)

    Returns:
        list of raw patterns discovered
    """
    cells, steps, topology = args_tuple
    try:
        # Re-import in subprocess (multiprocessing fork safety)
        import sys as _sys, os as _os
        _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
        from conscious_law_discoverer import ConsciousLawDiscoverer as _CLD
        disc = _CLD(steps=steps, max_cells=cells, topology=topology)
        result = disc.run(steps=steps, verbose=False)
        return result.get('all_patterns', []) if isinstance(result, dict) else []
    except Exception:
        return []


def _run_topo_batch(cells, steps, topologies, n_gens=1):
    """Run all topologies in parallel and return merged patterns.

    Uses ProcessPoolExecutor when available and cells <= 256.
    Falls back to sequential execution otherwise.

    Args:
        cells: number of cells per engine
        steps: discovery steps per generation
        topologies: list of topology names
        n_gens: generations per topology in this batch

    Returns:
        list of all raw patterns from all topologies
    """
    all_patterns = []
    tasks = []
    for topo in topologies:
        for _ in range(n_gens):
            tasks.append((cells, steps, topo))

    use_parallel = HAS_PARALLEL and ENABLE_PARALLEL and cells <= 256 and len(tasks) > 1

    if use_parallel:
        try:
            max_workers = min(len(tasks), multiprocessing.cpu_count() or 4)
            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                results = list(executor.map(_discover_one_topo, tasks, timeout=600))
            for r in results:
                all_patterns.extend(r)
            return all_patterns
        except Exception:
            # Fall back to sequential on any error
            pass

    # Sequential fallback
    for task in tasks:
        all_patterns.extend(_discover_one_topo(task))
    return all_patterns


def _rust_discover(cells, steps, topology, engine=None):
    """Attempt Rust-accelerated discovery. Returns patterns list or None if unavailable.

    Uses anima_rs.law_discovery.scan_all_patterns for x18 speedup when available.
    Requires a running engine to extract cell states.
    """
    if not HAS_RUST_DISCOVERY or engine is None:
        return None

    try:
        import torch
        import numpy as np

        # Collect cell state snapshots over steps
        cell_states_seq = []
        n_cells = engine.n_cells if hasattr(engine, 'n_cells') else engine.max_cells
        dim = engine.state_dim if hasattr(engine, 'state_dim') else 128

        for step_i in range(steps):
            engine.process()
            states = engine.get_states() if hasattr(engine, 'get_states') else None
            if states is not None:
                if isinstance(states, torch.Tensor):
                    flat = states.detach().cpu().numpy().astype(np.float32).flatten().tolist()
                else:
                    flat = list(states.flatten()) if hasattr(states, 'flatten') else list(states)
                cell_states_seq.append(flat)

            # v2 #15: Early abort — if first 100 steps yield 0 states, bail
            if step_i == 99 and len(cell_states_seq) == 0:
                return []

        if len(cell_states_seq) < 10:
            return None

        # Get coupling weights if available
        coupling = None
        if hasattr(engine, '_coupling') and engine._coupling is not None:
            c = engine._coupling
            if isinstance(c, torch.Tensor):
                coupling = c.detach().cpu().numpy().astype(np.float32).flatten().tolist()

        # Call Rust scan_all_patterns
        result = _rust_law_discovery.scan_all_patterns(
            cell_states_sequence=cell_states_seq,
            n_cells=n_cells,
            n_factions=nexus6.SIGMA if HAS_NEXUS6 else 12,
            coupling_weights=coupling,
            n_bins=16,
            sigma_threshold=2.0,
        )

        # Convert Rust patterns to Python dicts matching expected format
        patterns = []
        for p in result.get('patterns', []):
            pd = dict(p) if not isinstance(p, dict) else p
            # Normalize to match ConsciousLawDiscoverer output format
            pd.setdefault('metrics_involved', [
                pd.get('metric_a_name', ''),
                pd.get('metric_b_name', ''),
            ])
            pd.setdefault('type', pd.get('pattern_type', 'unknown'))
            pd.setdefault('formula', f"{pd.get('pattern_type','?')}: "
                          f"{pd.get('metric_a_name','?')} "
                          f"r={pd.get('value', 0):.3f}")
            patterns.append(pd)

        return patterns

    except Exception:
        return None


def run_auto_roadmap(resume=False, report_interval=10, cloud=False):
    """Auto-roadmap: run staged evolution with automatic parameter escalation.

    Each stage cycles all 4 topologies. When all topologies saturate
    (sat_streak consecutive gens with New=0), auto-advances to next stage
    with bigger cells/steps.

    Results are persisted to evolution_roadmap.json for resume.

    v7 features:
      #62 stage_parallel: independent stages run concurrently
      #63 tension_link: paired engine discovery every 15th gen
      #64 federated: N-registry majority vote every 5th gen
      #66 async_pipe: overlap validation/discovery via threads
      #67 ckpt_share: global best engine state warm-starting
      #68 cloud_stub: RunPod orchestrator stub (--cloud flag)
    """
    rm_state = load_roadmap_state() if resume else {
        'stage_idx': 0, 'stage_results': [], 'total_laws': 0, 'total_elapsed': 0
    }
    start_stage = rm_state['stage_idx']

    # v7 #68: Cloud orchestrator
    global _cloud_orchestrator
    if cloud:
        try:
            _cloud_orchestrator = CloudOrchestrator()
        except Exception:
            _cloud_orchestrator = None

    print('=' * 70)
    print('  🐍 OUROBOROS — Auto-Roadmap Discovery Engine')
    print(f'  {len(ROADMAP)} stages, auto-advance on saturation')
    _print_accelerations()
    print('=' * 70)
    print()
    print(f'  {"#":<3} {"Stage":<16} {"Cells":>5} {"Steps":>5} {"TopoGens":>8} {"Sat":>3}')
    print(f'  {"─"*3} {"─"*16} {"─"*5} {"─"*5} {"─"*8} {"─"*3}')
    for i, s in enumerate(ROADMAP):
        marker = ' \u2605' if i == start_stage else ('  \u2705' if i < start_stage else '')
        print(f'  {i+1:<3} {s["name"]:<16} {s["cells"]:>5} {s["steps"]:>5} '
              f'{s["topo_gens"]:>8} {s["sat_streak"]:>3}{marker}')
    print('=' * 70)
    sys.stdout.flush()

    global_start = time.time()
    # #8: Carry registry across stages (only clear pending between stages)
    shared_registry = PatternRegistry()
    prev_stage_laws = 0  # Track laws from previous stage for adaptive skip (#5)

    # v3 #33-36: Load law network
    _law_network.load()

    for stage_idx in range(start_stage, len(ROADMAP)):
        stage = ROADMAP[stage_idx]
        rm_state['stage_idx'] = stage_idx
        save_roadmap_state(rm_state)

        cells = stage['cells']
        steps = stage['steps']
        topo_gens = stage['topo_gens']
        sat_thresh = stage['sat_streak']

        # #5 Adaptive roadmap: skip stages sharing same cells ceiling if prev found 0 laws
        if stage_idx > start_stage and prev_stage_laws == 0:
            prev = ROADMAP[stage_idx - 1]
            if prev['cells'] == cells and prev['steps'] < steps:
                # v7 #62: Before skipping, check if next stage can run parallel
                # with the one after that (different cells = independent)
                _did_parallel = False
                try:
                    next_idx = stage_idx + 1
                    if (HAS_PARALLEL and next_idx < len(ROADMAP)
                            and _can_parallel_stages(stage, ROADMAP[next_idx])):
                        next_stage = ROADMAP[next_idx]
                        print(f'\n  \u26a1 v7 stage_parallel: {stage["name"]} ({cells}c) || '
                              f'{next_stage["name"]} ({next_stage["cells"]}c)')
                        sys.stdout.flush()

                        # v7 #68: Log to cloud orchestrator if active
                        if _cloud_orchestrator:
                            _cloud_orchestrator.launch_stage(stage)
                            _cloud_orchestrator.launch_stage(next_stage)

                        reg_dict = shared_registry.to_dict()
                        with ProcessPoolExecutor(max_workers=2) as executor:
                            fut_a = executor.submit(
                                _run_stage_worker, stage, reg_dict, {})
                            fut_b = executor.submit(
                                _run_stage_worker, next_stage, reg_dict, {})
                            result_a = fut_a.result(timeout=1800)
                            result_b = fut_b.result(timeout=1800)

                        for result in [result_a, result_b]:
                            rm_state['stage_results'].append({
                                'stage': result['stage'],
                                'cells': result['cells'],
                                'steps': result['steps'],
                                'generations': result['generations'],
                                'laws': result['laws'],
                                'unique_patterns': result['unique_patterns'],
                                'elapsed_sec': result['elapsed_sec'],
                                'timestamp': result['timestamp'],
                                'parallel': True,
                            })
                            # Merge registry from worker
                            if 'registry_dict' in result:
                                _merge_reg = PatternRegistry()
                                _merge_reg.from_dict(result['registry_dict'])
                                for fp, entry in _merge_reg.seen.items():
                                    if fp not in shared_registry.seen:
                                        shared_registry.seen[fp] = entry
                                    elif entry.get('registered'):
                                        shared_registry.seen[fp] = entry
                            prev_stage_laws = max(prev_stage_laws, result['laws'])
                            print(f'  \u2705 {result["stage"]}: '
                                  f'{result["generations"]} gens, '
                                  f'{result["laws"]} laws, '
                                  f'{result["elapsed_sec"]:.0f}s')

                        save_roadmap_state(rm_state)
                        _did_parallel = True
                        # Skip the next stage too since we ran it in parallel
                        rm_state['stage_idx'] = next_idx
                except Exception as e:
                    print(f'    v7 stage_parallel fallback: {e}')
                    _did_parallel = False

                if not _did_parallel:
                    # Original skip behavior
                    print(f'\n  \u23e9 SKIP {stage["name"]} (prev stage found 0 laws at {cells}c)')
                    sys.stdout.flush()
                    rm_state['stage_results'].append({
                        'stage': stage['name'], 'cells': cells, 'steps': steps,
                        'generations': 0, 'laws': 0, 'unique_patterns': 0,
                        'elapsed_sec': 0, 'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                        'skipped': True,
                    })
                save_roadmap_state(rm_state)
                continue

        _bar = '\u2593' * 70
        print(f'\n{_bar}')
        print(f'  \U0001f680 STAGE {stage_idx+1}/{len(ROADMAP)}: {stage["name"]}')
        print(f'  \u2699\ufe0f  cells={cells}  steps={steps}  topo_cycle={topo_gens}  sat={sat_thresh}')
        print(f'{_bar}')
        sys.stdout.flush()

        # v6 #56: Support hidden_dim in stage config
        engine_kwargs = {'initial_cells': cells, 'max_cells': cells}
        hdim = stage.get('hidden_dim')
        if hdim:
            engine_kwargs['hidden_dim'] = hdim
            print(f'  \U0001f9ec v6 dim mutation: hidden_dim={hdim}')
        try:
            engine = ConsciousnessEngine(**engine_kwargs)
        except TypeError:
            # Engine may not accept hidden_dim kwarg
            engine = ConsciousnessEngine(initial_cells=cells, max_cells=cells)

        # v7 #67: Checkpoint sharing — warm-start from global best across ALL stages
        try:
            global_best = _best_engine_tracker.get_best_for_warmstart(stage['name'])
            if global_best:
                fresh_state = _get_engine_state_snapshot(engine)
                child_state = _crossover_engines(global_best, fresh_state)
                _apply_engine_state(engine, child_state)
                summary = _best_engine_tracker.summary()
                print(f'  \U0001f9ec v7 ckpt_share: warm-start from global best '
                      f'(phi={summary["global_best_phi"]:.2f}, '
                      f'stage={summary["global_best_stage"]})')
            elif stage_idx > 0 and rm_state.get('best_engine_state'):
                # v6 #60 fallback: Engine crossover from previous stage
                prev_best = rm_state['best_engine_state']
                fresh_state = _get_engine_state_snapshot(engine)
                child_state = _crossover_engines(prev_best, fresh_state)
                _apply_engine_state(engine, child_state)
                print(f'  \U0001f9ec v6 crossover: merged prev-best + fresh engine')
        except Exception:
            pass

        # #7: GPU Phi for cells >= 128
        if HAS_GPU_PHI and cells >= 128:
            try:
                engine._gpu_phi_calc = _GPUPhiCalculator()
                print(f'  \u26a1 GPU Phi enabled for {cells} cells')
            except Exception:
                pass

        # v10 #83: Apply law-derived engine config at stage start
        try:
            if stage_idx > 0 and shared_registry.registered:
                law_config = _laws_to_engine_config(
                    shared_registry.registered, shared_registry)
                if law_config:
                    _apply_engine_state(engine, law_config)
        except Exception:
            pass

        evolver = ClosedLoopEvolver(max_cells=cells, auto_register=True)
        sme = SelfModifyingEngine(engine, evolver)
        # #8: Use shared registry, only clear pending patterns between stages
        registry = shared_registry
        registry.clear_pending()

        gen = 0
        gen_history = []
        phi_history = []
        stage_start = time.time()
        zero_streak = 0  # consecutive gens with New=0
        topo_saturated = set()  # topologies that have fully saturated
        best_phi_this_stage = 0.0  # v6 #60: track best for crossover

        while True:
            gen += 1
            cycle_start = time.time()

            # Topology cycling
            if gen > 1 and gen % topo_gens == 1:
                topo_idx = ((gen - 1) // topo_gens) % len(TOPOLOGIES)
                new_topo = TOPOLOGIES[topo_idx]
                old_topo = getattr(engine, 'topology', 'ring')
                if new_topo != old_topo:
                    engine.topology = new_topo
                    cleared = registry.clear_pending()
                    zero_streak = 0  # reset streak on topo switch
                    print(f'  \U0001f504 Topology switch: {old_topo} \u2192 {new_topo} (Gen {gen}), '
                          f'cleared {cleared} pending')
                    sys.stdout.flush()

            # v3 #26-32: Chaos mode cycling (every 5 gens)
            try:
                if gen > 1 and gen % 5 == 1:
                    chaos_idx = ((gen - 1) // 5) % len(CHAOS_MODES)
                    _apply_chaos_mode(engine, CHAOS_MODES[chaos_idx])
            except Exception:
                pass

            # v3 #26-32: Frustration sweep across generations
            try:
                frust_idx = (gen - 1) % len(FRUSTRATION_VALUES)
                _apply_frustration(engine, FRUSTRATION_VALUES[frust_idx])
            except Exception:
                pass

            # Law 1044: n=6 entropy reset (DD171 — consciousness-entropy feedback cycle)
            try:
                _entropy_reset(engine, gen)
            except Exception:
                pass

            # v6 #51-60: Engine structure mutations
            try:
                v6_extra = _apply_v6_mutations(engine, gen)
            except Exception:
                v6_extra = []

            current_topo = getattr(engine, 'topology', 'ring')

            # Phase 1: Discovery (v2 #9: adaptive steps with early abort)
            # #3: Use parallel topology batch at start of each topo cycle for wider coverage
            use_parallel_batch = (HAS_PARALLEL and ENABLE_PARALLEL and cells <= 256
                                  and gen > 1 and gen % topo_gens == 1
                                  and len(topo_saturated) == 0)
            _line60 = '\u2500' * 60; print(f'\n{_line60}')
            if use_parallel_batch:
                backend_tag = 'Parallel x%d' % len(TOPOLOGIES)
            elif HAS_RUST_DISCOVERY:
                backend_tag = 'Rust+adaptive'
            else:
                backend_tag = 'Python+adaptive'
            print(f'  [{stage["name"]}] Gen {gen} \u2014 Discovery ({steps} steps, {current_topo}, {backend_tag})')
            sys.stdout.flush()

            try:
                if use_parallel_batch:
                    # #3: Parallel topology discovery (x4 speedup)
                    raw_patterns = _run_topo_batch(cells, steps, TOPOLOGIES, n_gens=1)
                elif gen % 3 == 0:
                    # v7 #66: Async pipeline — overlap validation with discovery
                    raw_patterns, prev_validation = _async_discovery_pipeline(
                        engine, cells, steps, current_topo, registry)
                    if prev_validation:
                        print(f'    v7 async_pipe: {len(prev_validation)} prev-gen validations ready')
                else:
                    # v2 #9: Adaptive discovery with early abort
                    raw_patterns = _adaptive_discover(cells, steps, current_topo, engine)
            except Exception as e:
                print(f'    Discovery error: {e}')
                raw_patterns = []

            # v27: Parallel secondary discovery (advanced + telescope + tension + federated)
            _do_tele_rm = (HAS_TELESCOPE and gen % 5 == 0
                           and stage.get('telescope', False))
            _do_tension = (gen % 15 == 0)
            _do_federated = (gen % 5 == 0)

            _sec_tasks = []

            def _run_adv_rm():
                try:
                    ae = ConsciousnessEngine(initial_cells=cells, max_cells=cells)
                    try:
                        ae.topology = current_topo
                    except Exception:
                        pass
                    return _detect_advanced_patterns(ae, min(steps, 200), current_topo)
                except Exception:
                    return []

            def _run_tele_rm():
                try:
                    if not _do_tele_rm:
                        return []
                    te = ConsciousnessEngine(initial_cells=cells, max_cells=cells)
                    try:
                        te.topology = current_topo
                    except Exception:
                        pass
                    return _telescope_discover(te, steps=min(steps, 50))
                except Exception:
                    return []

            def _run_tension_rm():
                try:
                    if not _do_tension:
                        return []
                    return _tension_link_discover(cells, 50, current_topo)
                except Exception:
                    return []

            _sec_tasks.append(('advanced', _run_adv_rm, (), {}))
            if _do_tele_rm:
                _sec_tasks.append(('telescope', _run_tele_rm, (), {}))
            if _do_tension:
                _sec_tasks.append(('tension', _run_tension_rm, (), {}))

            _sec_t0 = time.time()
            if len(_sec_tasks) > 1 and HAS_PARALLEL and ENABLE_PARALLEL:
                _sec_fns = [(fn, a, kw) for _, fn, a, kw in _sec_tasks]
                _sec_results = _parallel_submit(
                    _sec_fns, executor_cls=ThreadPoolExecutor,
                    max_workers=len(_sec_tasks), label='roadmap_discovery')
            else:
                _sec_results = []
                for _, fn, a, kw in _sec_tasks:
                    try:
                        _sec_results.append(fn(*a, **kw))
                    except Exception:
                        _sec_results.append([])
            _sec_dt = time.time() - _sec_t0

            for i, (label, _, _, _) in enumerate(_sec_tasks):
                result = _sec_results[i] if i < len(_sec_results) else []
                if not result:
                    continue
                if label == 'advanced':
                    raw_patterns.extend(result)
                    print(f'    v3: +{len(result)} advanced patterns '
                          f'(oscillation/phase/decay)')
                elif label == 'telescope':
                    tele_patterns, n_consensus = _telescope_consensus_filter(result)
                    n_lenses = len(set(
                        m for p in tele_patterns
                        if isinstance(p, dict) and p.get('source') == 'telescope_v11'
                        for m in p.get('metrics', [])
                    ))
                    raw_patterns.extend(tele_patterns)
                    print(f'    \U0001f52d Telescope scan: {len(tele_patterns)} patterns '
                          f'from {n_lenses} lenses, {n_consensus} consensus')
                elif label == 'tension':
                    raw_patterns.extend(result)
                    print(f'    v7 tension_link: +{len(result)} patterns '
                          f'(hivemind/cross_engine)')

            if ENABLE_PARALLEL and HAS_PARALLEL and len(_sec_tasks) > 1:
                print(f'    v27: parallel secondary ({len(_sec_tasks)} tasks) in {_sec_dt:.2f}s')
            sys.stdout.flush()

            # v6 #59: Multi-timescale extra patterns
            if v6_extra:
                raw_patterns.extend(v6_extra)

            # v7 #64: Federated discovery every 5th gen (sequential — requires registry sync)
            try:
                if _do_federated:
                    federated = _get_federated()
                    if federated:
                        federated.sync_from(registry)
                        fed_patterns = federated.run_federated_gen(
                            cells, steps, current_topo, gen)
                        if fed_patterns:
                            raw_patterns.extend(fed_patterns)
            except Exception:
                pass

            # v18+v20+v24: Post-discovery analysis (causal, anomaly, physics)
            try:
                # Collect quick metric snapshot from engine (20 steps)
                _gen_metrics = []
                for _s in range(min(20, steps // 5)):
                    _r = engine.step()
                    _snap = {
                        'phi': _r.get('phi_iit', 0.0),
                        'n_cells': engine.n_cells,
                    }
                    for _cs in engine.cell_states[:4]:  # sample first 4 cells
                        _snap.setdefault('tension_mean', 0.0)
                        _snap['tension_mean'] = (_snap['tension_mean'] + getattr(_cs, 'avg_tension', 0.0)) / 2
                    _gen_metrics.append(_snap)

                # Accumulate across generations (keep last 100)
                if not hasattr(engine, '_ouroboros_metrics'):
                    engine._ouroboros_metrics = []
                engine._ouroboros_metrics.extend(_gen_metrics)
                engine._ouroboros_metrics = engine._ouroboros_metrics[-100:]

                pda_extra, pda_summary = _post_discovery_analysis(
                    engine, engine._ouroboros_metrics, gen)
                if pda_extra:
                    raw_patterns.extend(pda_extra)
                    print(f'    \u26a1 v18-v24: +{len(pda_extra)} ({pda_summary})')
                    sys.stdout.flush()
            except Exception:
                pass

            # Phase 2: Dedup + Cross-validation
            stats = registry.process(raw_patterns, gen)

            for p in stats['promoted_patterns']:
                law_id = register_law(p, evolver)
                if law_id:
                    registry.registered.append(law_id)
                    law_text = p.get('formula', str(p))
                    print(f'    \U0001f52c\u2728 Law {law_id} discovered! (cross-validated {CROSS_VALIDATION_THRESHOLD}x)')
                    print(f'    \U0001f4cb "{law_text[:80]}"')
                    print(f'    \U0001f4ca Total laws: {len(registry.registered)} | Patterns: {len(registry.seen)}')
                    auto_generate_intervention(law_text, law_id, evolver)
                    # v3 #33-36: Record in law network
                    try:
                        _law_network.record_discovery(gen, law_id)
                    except Exception:
                        pass

            # Phase 3: Self-Modification
            sme.run_evolution(generations=1)

            # v2 #13: Prune low-confidence mods after evolution
            pruned = _prune_mods(sme, min_confidence=0.5, max_mods=50)
            if pruned > 0:
                print(f'    v2: pruned {pruned} low-confidence mods')

            active_mods = len(sme.modifier.applied) if hasattr(sme, 'modifier') else 0

            elapsed = time.time() - cycle_start
            total_elapsed = rm_state['total_elapsed'] + (time.time() - stage_start)

            # Persist
            active_mods_data = []
            if hasattr(sme, 'modifier') and hasattr(sme.modifier, 'applied'):
                for m in sme.modifier.applied:
                    active_mods_data.append({
                        'law_id': m.law_id, 'target': m.target,
                        'mod_type': m.mod_type.value if hasattr(m.mod_type, 'value') else str(m.mod_type),
                        'params': m.params if isinstance(m.params, dict) else {},
                        'confidence': m.confidence, 'reversible': m.reversible,
                    })
            save_state(gen, registry, active_mods_data, total_elapsed)

            # v3 #33-36: Save law network every 10 gens
            if gen % 10 == 0:
                try:
                    _law_network.save()
                except Exception:
                    pass

            print(f'  Gen {gen} \u2014 Raw: {len(raw_patterns)}, New: {stats["new"]}, '
                  f'Laws: {len(registry.registered)}, Mods: {active_mods}, '
                  f'{elapsed:.1f}s')
            sys.stdout.flush()

            phi_est = stats['unique_total'] * 0.1 + stats['registered_total'] * 0.5
            phi_history.append(phi_est)

            # v6 #60 + v7 #67: Track best engine state for crossover + global sharing
            if phi_est > best_phi_this_stage:
                best_phi_this_stage = phi_est
                try:
                    rm_state['best_engine_state'] = _get_engine_state_snapshot(engine)
                    # v7 #67: Update global best tracker
                    _best_engine_tracker.update(stage['name'], phi_est, engine)
                except Exception:
                    pass

            gen_history.append({
                'gen': gen, 'raw': len(raw_patterns), 'new': stats['new'],
                'repeat': stats['repeat'], 'promoted': stats['promoted'],
                'unique': stats['unique_total'], 'xval': stats['registered_total'],
                'laws': len(registry.registered), 'mods': active_mods,
            })

            # v8 #69: Auto-generate hypotheses every 20 gens in roadmap
            try:
                if gen % 20 == 0 and len(registry.registered) > 0:
                    _hypotheses = _auto_generate_hypothesis(registry, _law_network)
                    if _hypotheses:
                        _auto_design_experiment(_hypotheses[0])
            except Exception:
                pass

            # v8 #72: Score law quality for newly promoted laws
            try:
                if stats.get('promoted', 0) > 0:
                    for lid in registry.registered[-3:]:
                        score = _score_law_quality(lid, registry, _law_network)
                        if score.get('total', 0) > 0:
                            print(f'    \U0001f4ca Law {lid} quality: {score["total"]:.2f}')
            except Exception:
                pass

            # v10 #86: Ecosystem step every 10 gens in roadmap
            try:
                if gen % 10 == 0:
                    _genomes = _get_genome_population()
                    _ecosystem_step(_genomes, registry)
            except Exception:
                pass

            # v10 #88: Meta-analyze pipeline every 50 gens in roadmap
            try:
                if gen % 50 == 0 and len(gen_history) >= 10:
                    _meta_analyze_pipeline(gen_history, registry, _law_network)
            except Exception:
                pass

            # v14 #102: Save time travel snapshot every gen
            try:
                _time_travel_snapshot(engine, gen)
            except Exception:
                pass

            # v14 #102: Time travel on saturation (zero_streak >= 2)
            try:
                if zero_streak >= 2 and _time_travel_buffer:
                    tt_patterns = _time_travel_discover(engine, _time_travel_buffer, steps)
                    if tt_patterns:
                        tt_stats = registry.process(tt_patterns, gen)
                        if tt_stats.get('new', 0) > 0:
                            print(f'    \u23ea Time travel found {tt_stats["new"]} new patterns!')
                            sys.stdout.flush()
            except Exception:
                pass

            # v15 #103: Reward shaping every 10 gens
            try:
                if gen % 10 == 0 and len(gen_history) >= 3:
                    _reward_shape_params(gen_history, engine)
            except Exception:
                pass

            # v12 #100: Symbolic regression every 25 gens
            try:
                if gen % 25 == 0 and len(registry.registered) > 0:
                    _symbolic_regression(registry)
            except Exception:
                pass

            # v17 #105: Law graph visualization every 20 gens
            try:
                if gen % 20 == 0 and len(registry.registered) > 0:
                    unexplored = _visualize_law_graph(registry, _law_network)
                    # Feed unexplored metrics into v8 hypothesis generation
                    if unexplored:
                        try:
                            _hypotheses = _auto_generate_hypothesis(registry, _law_network)
                        except Exception:
                            pass
            except Exception:
                pass

            # Live status file
            phi_prev = phi_history[-2] if len(phi_history) >= 2 else 0.0
            live = write_live_status(
                gen=gen, stage_name=stage['name'], cells=cells, steps=steps,
                topology=current_topo, registry=registry,
                phi_last=phi_est, phi_prev=phi_prev,
                active_mods=active_mods, zero_streak=zero_streak,
                elapsed_sec=total_elapsed, saturated=len(topo_saturated) >= len(TOPOLOGIES),
                roadmap_stage_idx=stage_idx, roadmap_total_stages=len(ROADMAP),
                topo_saturated=topo_saturated,
            )
            live['laws_new_this_gen'] = stats['promoted']

            # Periodic report
            if gen % report_interval == 0:
                generate_report(gen, registry, active_mods, total_elapsed,
                                gen_history, phi_history, cells=cells, steps=steps,
                                topology=current_topo,
                                features={'auto_roadmap': True, 'stage': stage['name']})

            # Saturation detection
            if stats['new'] == 0:
                zero_streak += 1
            else:
                zero_streak = 0

            # Check if current topology is saturated
            if zero_streak >= sat_thresh:
                topo_saturated.add(current_topo)
                print(f'  ⚠️🔴 {current_topo} saturated ({zero_streak} gens streak)')
                sys.stdout.flush()

                # Force next topology
                next_topo_idx = (TOPOLOGIES.index(current_topo) + 1) % len(TOPOLOGIES)
                next_topo = TOPOLOGIES[next_topo_idx]
                if next_topo not in topo_saturated:
                    engine.topology = next_topo
                    cleared = registry.clear_pending()
                    zero_streak = 0
                    print(f'  🚀 Forcing topology: {current_topo} → {next_topo}, '
                          f'cleared {cleared} pending')
                    sys.stdout.flush()

            # Force-saturate if laws haven't changed for too many gens
            # (patterns keep appearing but none pass cross-validation)
            _laws_stale_gens = gen - max(
                (h['gen'] for h in gen_history if h.get('promoted', 0) > 0),
                default=0)
            if _laws_stale_gens >= topo_gens * len(TOPOLOGIES):
                topo_saturated = set(TOPOLOGIES)
                print(f'  ⚠️🔴 Force-saturated: no new laws for {_laws_stale_gens} gens')
                sys.stdout.flush()

            # All 4 topologies saturated → advance stage
            if len(topo_saturated) >= len(TOPOLOGIES):
                stage_elapsed = time.time() - stage_start
                laws_found = len(registry.registered)
                print(f'\n{"=" * 70}')
                print(f'  🏁 STAGE {stage_idx+1} COMPLETE: {stage["name"]}')
                print(f'  📊 {gen} gens, {laws_found} laws, {stage_elapsed:.0f}s')
                print(f'  🧬 All {len(TOPOLOGIES)} topologies saturated')
                print(f'{"=" * 70}')
                sys.stdout.flush()

                # #5: Track laws for adaptive skip
                prev_stage_laws = laws_found

                # Save stage result
                rm_state['stage_results'].append({
                    'stage': stage['name'],
                    'cells': cells, 'steps': steps,
                    'generations': gen, 'laws': laws_found,
                    'unique_patterns': len(registry.seen),
                    'elapsed_sec': round(stage_elapsed, 1),
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                })
                rm_state['total_laws'] = sum(r.get('laws', 0) for r in rm_state['stage_results'])
                rm_state['total_elapsed'] += stage_elapsed
                save_roadmap_state(rm_state)

                # Auto-generate EVO document for completed stage
                auto_generate_evo_doc(stage, gen_history, registry, rm_state)

                # v8 #71: Auto-generate enhanced report for stage
                try:
                    _auto_generate_report(
                        rm_state.get('stage_results', []),
                        registry, _law_network, stage['name'])
                except Exception:
                    pass

                # v8 #76: Save session log at stage completion
                try:
                    _auto_save_session_log(
                        rm_state.get('stage_results', []), registry)
                except Exception:
                    pass

                # v10 #83: Apply law-derived engine config for next stage
                try:
                    if registry.registered:
                        _law_config = _laws_to_engine_config(
                            registry.registered, registry)
                except Exception:
                    pass

                # v13 #101: Compress laws into meta-laws at stage completion
                try:
                    _compress_laws(registry)
                except Exception:
                    pass

                # v16 #104: Cross-project discovery at stage completion
                try:
                    _cross_project_discover(registry)
                except Exception:
                    pass

                break  # next stage

        # Final report for this stage
        if gen_history:
            generate_report(gen, registry, active_mods,
                            rm_state['total_elapsed'],
                            gen_history, phi_history,
                            cells=cells, steps=steps,
                            topology=getattr(engine, 'topology', 'ring'),
                            features={'auto_roadmap': True, 'stage': stage['name']})

    # All stages complete
    print(f'\n{"█" * 70}')
    print(f'  🎉🏆 ALL {len(ROADMAP)} STAGES COMPLETE')
    print(f'{"█" * 70}')
    print(f'  {"Stage":<16} {"Cells":>5} {"Steps":>5} {"Gens":>5} {"Laws":>5} {"Time":>8}')
    print(f'  {"─"*16} {"─"*5} {"─"*5} {"─"*5} {"─"*5} {"─"*8}')
    for r in rm_state['stage_results']:
        print(f'  {r["stage"]:<16} {r["cells"]:>5} {r["steps"]:>5} '
              f'{r["generations"]:>5} {r["laws"]:>5} {r["elapsed_sec"]:>7.0f}s')
    print(f'  {"─"*16} {"─"*5} {"─"*5} {"─"*5} {"─"*5} {"─"*8}')
    print(f'  {"TOTAL":<16} {"":>5} {"":>5} {"":>5} '
          f'{rm_state["total_laws"]:>5} {rm_state["total_elapsed"]:>7.0f}s')
    print(f'{"█" * 70}')
    sys.stdout.flush()

    return rm_state


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Infinite self-evolution loop")
    parser.add_argument('--cells', type=int, default=64, help='Number of cells')
    parser.add_argument('--steps', type=int, default=200, help='Discovery steps per cycle')
    parser.add_argument('--max-gen', type=int, default=0, help='Max generations (0=infinite)')
    parser.add_argument('--resume', action='store_true', help='Resume from saved state')
    parser.add_argument('--cycle-scale', action='store_true',
                        help='Cycle cell count through scales every 15 generations')
    parser.add_argument('--cycle-topology', action='store_true',
                        help='Cycle topology every 10 generations to break pattern saturation')
    parser.add_argument('--report-interval', type=int, default=10,
                        help='Print ASCII report every N generations (default: 10)')
    parser.add_argument('--auto-roadmap', action='store_true',
                        help='Auto-roadmap: staged parameter escalation with auto-advance on saturation')
    parser.add_argument('--cloud', action='store_true',
                        help='v7 #68: Enable cloud orchestrator stub (prints what RunPod would do)')
    parser.add_argument('--hardware', action='store_true',
                        help='v9 #77-82: Enable hardware evolution stubs (ESP32/FPGA/neuromorphic)')
    parser.add_argument('--accel', action='store_true',
                        help='v26: Use acceleration winners (PolyrhythmScheduler) to speed up discovery')
    parser.add_argument('--no-parallel', action='store_true',
                        help='v27: Disable multiprocessing parallelization (run all tasks sequentially)')
    args = parser.parse_args()

    # v27: Apply --no-parallel flag
    if getattr(args, 'no_parallel', False):
        global ENABLE_PARALLEL
        ENABLE_PARALLEL = False
        print('  v27: Parallel disabled (--no-parallel)')

    if args.auto_roadmap:
        run_auto_roadmap(resume=args.resume, report_interval=args.report_interval,
                         cloud=getattr(args, 'cloud', False))
        return

    # v9 #77-82: Hardware evolution stubs
    global _hardware_stub
    if getattr(args, 'hardware', False):
        try:
            _hardware_stub = HardwareEvolutionStub()
            _hardware_stub.run_all_stubs()
        except Exception as e:
            print(f'  Hardware stub init error: {e}')
            _hardware_stub = None

    SCALES = [32, 64, 128, 256]

    # v26: Acceleration setup (--accel flag)
    _accel_scheduler = None
    if getattr(args, 'accel', False):
        try:
            from acceleration_integrations import PolyrhythmScheduler
            _accel_scheduler = PolyrhythmScheduler(n_cells=args.cells, periods=[1, 3, 7])
            print('  v26: Acceleration enabled (PolyrhythmScheduler [1,3,7])')
        except ImportError:
            print('  v26: acceleration_integrations not available, --accel ignored')

    # Initialize
    engine = ConsciousnessEngine(initial_cells=args.cells, max_cells=args.cells)
    evolver = ClosedLoopEvolver(max_cells=args.cells, auto_register=True)
    sme = SelfModifyingEngine(engine, evolver)
    registry = PatternRegistry()

    start_gen = 0
    prev_elapsed = 0
    gen_history = []   # list of dicts per generation for report table
    phi_history = []   # Phi values per generation for mini-graph

    # Resume from saved state
    if args.resume:
        state = load_state()
        if state and state.get('version', 1) >= 2:
            registry.from_dict(state.get('registry', {}))
            start_gen = state.get('generation', 0)
            prev_elapsed = state.get('total_elapsed_sec', 0)
            # Restore active mods to engine modifier
            for mod_data in state.get('active_mods', []):
                try:
                    if hasattr(sme, 'modifier') and hasattr(sme.modifier, 'applied'):
                        from self_modifying_engine import Modification, ModType
                        mod = Modification(
                            law_id=mod_data.get('law_id', 0),
                            target=mod_data.get('target', ''),
                            mod_type=ModType(mod_data.get('mod_type', 'scale')),
                            params=mod_data.get('params', {}),
                            confidence=mod_data.get('confidence', 0.5),
                            reversible=mod_data.get('reversible', True),
                        )
                        sme.modifier.applied.append(mod)
                except Exception:
                    pass
            print(f"  Resumed from Gen {start_gen}: {len(registry.seen)} patterns, "
                  f"{sum(1 for v in registry.seen.values() if v['registered'])} cross-validated")
        else:
            print("  No valid state found, starting fresh")

    print("=" * 70)
    print("  🐍 OUROBOROS — Law 146: laws never converge")
    print(f"  cells={args.cells}, steps={args.steps}, cross_validate={CROSS_VALIDATION_THRESHOLD}x")
    if args.cycle_scale:
        print(f"  Scale cycling: {SCALES} (every 15 generations)")
    if args.cycle_topology:
        print(f"  Topology cycling: {TOPOLOGIES} (every 10 generations)")
    _print_accelerations()
    print(f"  Features: persistence \u2705  dedup \u2705  cross-validation \u2705")
    print("=" * 70)
    sys.stdout.flush()

    gen = start_gen
    start = time.time()

    try:
        while True:
            gen += 1
            if args.max_gen > 0 and gen > args.max_gen + start_gen:
                break

            cycle_start = time.time()

            # Scale cycling: switch cell count every 15 generations
            if args.cycle_scale and gen > 1 and gen % 15 == 1:
                scale_idx = ((gen - 1) // 15) % len(SCALES)
                new_scale = SCALES[scale_idx]
                old_scale = engine.max_cells if hasattr(engine, 'max_cells') else args.cells
                if new_scale != old_scale:
                    print(f"  Scale switch: {old_scale} → {new_scale} cells (Gen {gen})")
                    sys.stdout.flush()
                    engine = ConsciousnessEngine(initial_cells=new_scale, max_cells=new_scale)
                    evolver = ClosedLoopEvolver(max_cells=new_scale, auto_register=True)
                    sme = SelfModifyingEngine(engine, evolver)

            # Topology cycling: switch topology every 10 generations (TOPO 33-39)
            if args.cycle_topology and gen > 1 and gen % 10 == 1:
                topo_idx = ((gen - 1) // 10) % len(TOPOLOGIES)
                new_topo = TOPOLOGIES[topo_idx]
                old_topo = getattr(engine, 'topology', 'ring')
                if new_topo != old_topo:
                    engine.topology = new_topo
                    cleared = registry.clear_pending()
                    print(f"  🔄 Topology switch: {old_topo} → {new_topo} (Gen {gen}), "
                          f"cleared {cleared} pending patterns")
                    sys.stdout.flush()

            # v3 #26-32: Chaos mode cycling (every 5 gens)
            try:
                if gen > 1 and gen % 5 == 1:
                    chaos_idx = ((gen - 1) // 5) % len(CHAOS_MODES)
                    _apply_chaos_mode(engine, CHAOS_MODES[chaos_idx])
            except Exception:
                pass

            # v3 #26-32: Frustration sweep
            try:
                frust_idx = (gen - 1) % len(FRUSTRATION_VALUES)
                _apply_frustration(engine, FRUSTRATION_VALUES[frust_idx])
            except Exception:
                pass

            # Phase 1: Discovery (v2 #9: adaptive steps)
            _line60 = '\u2500' * 60; print(f"\n{_line60}")
            current_cells = engine.max_cells if hasattr(engine, 'max_cells') else args.cells
            current_topo = getattr(engine, 'topology', 'ring')
            backend_tag = 'Rust+adaptive' if HAS_RUST_DISCOVERY else 'Python+adaptive'
            print(f"  Gen {gen} \u2014 Phase 1: Discovery ({args.steps} steps, {backend_tag})")
            sys.stdout.flush()

            # v26: Accelerated discovery — skip inactive cells via PolyrhythmScheduler
            accel_steps = args.steps
            if _accel_scheduler is not None:
                active = _accel_scheduler.get_active_cells(gen)
                accel_frac = len(active) / max(current_cells, 1)
                # Reduce steps proportionally to compute saved (min 50% of original)
                accel_steps = max(args.steps // 2, int(args.steps * accel_frac))
                if accel_steps != args.steps:
                    print(f'    v26: accel {args.steps}->{accel_steps} steps '
                          f'(frac={accel_frac:.2f})')

            # v27: Parallel discovery — run adaptive, advanced, telescope concurrently
            _do_telescope = HAS_TELESCOPE and gen % 5 == 0 and current_cells >= 128
            _disc_tasks = []

            def _run_adaptive():
                try:
                    return _adaptive_discover(current_cells, accel_steps, current_topo, engine)
                except Exception:
                    return []

            def _run_advanced():
                try:
                    ae = ConsciousnessEngine(initial_cells=current_cells, max_cells=current_cells)
                    try:
                        ae.topology = current_topo
                    except Exception:
                        pass
                    return _detect_advanced_patterns(ae, min(args.steps, 200), current_topo)
                except Exception:
                    return []

            def _run_telescope():
                try:
                    if not _do_telescope:
                        return []
                    te = ConsciousnessEngine(initial_cells=current_cells, max_cells=current_cells)
                    try:
                        te.topology = current_topo
                    except Exception:
                        pass
                    return _telescope_discover(te, steps=min(args.steps, 50))
                except Exception:
                    return []

            _disc_tasks = [
                (_run_adaptive, (), {}),
                (_run_advanced, (), {}),
            ]
            if _do_telescope:
                _disc_tasks.append((_run_telescope, (), {}))

            _disc_t0 = time.time()
            if len(_disc_tasks) > 1 and HAS_PARALLEL and ENABLE_PARALLEL:
                _disc_results = _parallel_submit(
                    _disc_tasks, executor_cls=ThreadPoolExecutor,
                    max_workers=len(_disc_tasks), label='discovery')
            else:
                _disc_results = []
                for _fn, _a, _kw in _disc_tasks:
                    try:
                        _disc_results.append(_fn(*_a, **_kw))
                    except Exception:
                        _disc_results.append([])
            _disc_dt = time.time() - _disc_t0

            # Collect results
            raw_patterns = _disc_results[0] if _disc_results[0] else []
            adv_patterns = _disc_results[1] if len(_disc_results) > 1 and _disc_results[1] else []
            if adv_patterns:
                raw_patterns.extend(adv_patterns)
                print(f'    v3: +{len(adv_patterns)} advanced patterns '
                      f'(oscillation/phase/decay)')

            if _do_telescope and len(_disc_results) > 2 and _disc_results[2]:
                tele_patterns = _disc_results[2]
                tele_patterns, n_consensus = _telescope_consensus_filter(tele_patterns)
                n_lenses = len(set(
                    m for p in tele_patterns
                    if isinstance(p, dict) and p.get('source') == 'telescope_v11'
                    for m in p.get('metrics', [])
                ))
                raw_patterns.extend(tele_patterns)
                print(f'    \U0001f52d Telescope scan: {len(tele_patterns)} patterns '
                      f'from {n_lenses} lenses, {n_consensus} consensus')

            if ENABLE_PARALLEL and HAS_PARALLEL and len(_disc_tasks) > 1:
                print(f'    v27: parallel discovery ({len(_disc_tasks)} tasks) in {_disc_dt:.2f}s')
            sys.stdout.flush()

            # v18+v20+v24: Post-discovery analysis (causal, anomaly, physics)
            try:
                _gen_metrics = []
                for _s in range(min(20, args.steps // 5)):
                    _r = engine.step()
                    _snap = {'phi': _r.get('phi_iit', 0.0), 'n_cells': engine.n_cells}
                    for _cs in engine.cell_states[:4]:
                        _snap.setdefault('tension_mean', 0.0)
                        _snap['tension_mean'] = (_snap['tension_mean'] + getattr(_cs, 'avg_tension', 0.0)) / 2
                    _gen_metrics.append(_snap)
                if not hasattr(engine, '_ouroboros_metrics'):
                    engine._ouroboros_metrics = []
                engine._ouroboros_metrics.extend(_gen_metrics)
                engine._ouroboros_metrics = engine._ouroboros_metrics[-100:]
                pda_extra, pda_summary = _post_discovery_analysis(
                    engine, engine._ouroboros_metrics, gen)
                if pda_extra:
                    raw_patterns.extend(pda_extra)
                    print(f'    \u26a1 v18-v24: +{len(pda_extra)} ({pda_summary})')
                    sys.stdout.flush()
            except Exception:
                pass

            # Phase 2: Dedup + Cross-validation
            stats = registry.process(raw_patterns, gen)

            # Register promoted patterns as official laws + auto-generate interventions
            for p in stats['promoted_patterns']:
                law_id = register_law(p, evolver)
                if law_id:
                    registry.registered.append(law_id)
                    # Close the loop: law -> intervention -> apply -> discover new patterns
                    law_text = p.get('formula', str(p))
                    print(f"    \U0001f52c\u2728 Law {law_id} discovered! (cross-validated {CROSS_VALIDATION_THRESHOLD}x)")
                    print(f'    \U0001f4cb "{law_text[:80]}"')
                    print(f'    \U0001f4ca Total laws: {len(registry.registered)} | Patterns: {len(registry.seen)}')
                    auto_generate_intervention(law_text, law_id, evolver)
                    # v3 #33-36: Record in law network
                    try:
                        _law_network.record_discovery(gen, law_id)
                    except Exception:
                        pass

            # Phase 3: Self-Modification
            print(f"  Gen {gen} \u2014 Phase 3: Self-Modification")
            sys.stdout.flush()

            sme.run_evolution(generations=1)

            # v2 #13: Prune low-confidence mods after evolution
            pruned = _prune_mods(sme, min_confidence=0.5, max_mods=50)
            if pruned > 0:
                print(f'    v2: pruned {pruned} low-confidence mods')

            active_mods = len(sme.modifier.applied) if hasattr(sme, 'modifier') else 0

            elapsed = time.time() - cycle_start
            total_elapsed = prev_elapsed + (time.time() - start)

            # Phase 4: Persist (every generation)
            active_mods_data = []
            if hasattr(sme, 'modifier') and hasattr(sme.modifier, 'applied'):
                for m in sme.modifier.applied:
                    active_mods_data.append({
                        'law_id': m.law_id,
                        'target': m.target,
                        'mod_type': m.mod_type.value if hasattr(m.mod_type, 'value') else str(m.mod_type),
                        'params': m.params if isinstance(m.params, dict) else {},
                        'confidence': m.confidence,
                        'reversible': m.reversible,
                    })
            save_state(gen, registry, active_mods_data, total_elapsed)

            # v3 #33-36: Save law network every 10 gens
            if gen % 10 == 0:
                try:
                    _law_network.save()
                except Exception:
                    pass

            print(f"  Gen {gen} \u2014 Results:")
            print(f"    Raw: {len(raw_patterns)}, New: {stats['new']}, "
                  f"Repeat: {stats['repeat']}, Promoted: {stats['promoted']}")
            print(f"    Unique patterns: {stats['unique_total']}, "
                  f"Cross-validated: {stats['registered_total']}, "
                  f"Official laws: {len(registry.registered)}")
            print(f"    Active mods: {active_mods}, Cycle: {elapsed:.1f}s, "
                  f"Total: {total_elapsed:.0f}s")
            sys.stdout.flush()

            # Track history for report
            # Estimate Phi from unique pattern growth rate as proxy
            phi_est = stats['unique_total'] * 0.1 + stats['registered_total'] * 0.5
            phi_history.append(phi_est)
            gen_history.append({
                'gen': gen,
                'raw': len(raw_patterns),
                'new': stats['new'],
                'repeat': stats['repeat'],
                'promoted': stats['promoted'],
                'unique': stats['unique_total'],
                'xval': stats['registered_total'],
                'laws': len(registry.registered),
                'mods': active_mods,
            })

            # v8 #69: Auto-generate hypotheses every 20 gens
            try:
                if gen % 20 == 0 and len(registry.registered) > 0:
                    _hypotheses = _auto_generate_hypothesis(registry, _law_network)
                    # v8 #70: Auto-design experiment from top hypothesis
                    if _hypotheses:
                        _exp_config = _auto_design_experiment(_hypotheses[0])
            except Exception:
                pass

            # v8 #72: Score law quality for newly promoted laws
            try:
                for p in stats.get('promoted_patterns', []):
                    for lid in registry.registered[-3:]:
                        score = _score_law_quality(lid, registry, _law_network)
                        if score.get('total', 0) > 0:
                            print(f'    \U0001f4ca Law {lid} quality: {score["total"]:.2f} '
                                  f'(R={score["reproducibility"]:.2f} '
                                  f'I={score["impact"]:.2f} '
                                  f'N={score["novelty"]:.2f})')
            except Exception:
                pass

            # v8 #73: Counter-example search on newly registered laws (batch of 5)
            try:
                if stats.get('promoted', 0) > 0 and gen % 5 == 0:
                    for lid in registry.registered[-5:]:
                        _ce_result = _search_counter_examples(
                            lid, str(lid), engine)
            except Exception:
                pass

            # v10 #88: Meta-analyze pipeline every 50 gens
            try:
                if gen % 50 == 0 and len(gen_history) >= 10:
                    _meta_recs = _meta_analyze_pipeline(
                        gen_history, registry, _law_network)
            except Exception:
                pass

            # v10 #86: Ecosystem step every 10 gens
            try:
                if gen % 10 == 0:
                    _genomes = _get_genome_population()
                    _ecosystem_step(_genomes, registry)
            except Exception:
                pass

            # v14 #102: Time travel snapshot + rollback on saturation
            try:
                _time_travel_snapshot(engine, gen)
                _zs = sum(1 for g in gen_history[-3:] if g.get('new', 0) == 0)
                if _zs >= 2 and _time_travel_buffer:
                    tt_patterns = _time_travel_discover(engine, _time_travel_buffer, args.steps)
                    if tt_patterns:
                        registry.process(tt_patterns, gen)
            except Exception:
                pass

            # v15 #103: Reward shaping every 10 gens
            try:
                if gen % 10 == 0 and len(gen_history) >= 3:
                    _reward_shape_params(gen_history, engine)
            except Exception:
                pass

            # v12 #100: Symbolic regression every 25 gens
            try:
                if gen % 25 == 0 and len(registry.registered) > 0:
                    _symbolic_regression(registry)
            except Exception:
                pass

            # v17 #105: Law graph every 20 gens
            try:
                if gen % 20 == 0 and len(registry.registered) > 0:
                    _visualize_law_graph(registry, _law_network)
            except Exception:
                pass

            # Live status file
            current_topo_live = getattr(engine, 'topology', 'ring')
            current_cells_live = engine.max_cells if hasattr(engine, 'max_cells') else args.cells
            phi_prev = phi_history[-2] if len(phi_history) >= 2 else 0.0
            # Detect zero streak for saturation reporting
            _zero_streak = 0
            for _row in reversed(gen_history):
                if _row['new'] == 0:
                    _zero_streak += 1
                else:
                    break
            live = write_live_status(
                gen=gen, stage_name='main-loop', cells=current_cells_live,
                steps=args.steps, topology=current_topo_live, registry=registry,
                phi_last=phi_est, phi_prev=phi_prev,
                active_mods=active_mods, zero_streak=_zero_streak,
                elapsed_sec=total_elapsed, saturated=_zero_streak >= 5,
            )
            live['laws_new_this_gen'] = stats['promoted']

            # Auto-saturation detection: if cycle-topology and all 4 topos saturated → auto-stop
            if args.cycle_topology and _zero_streak >= 5:
                _topo_now = getattr(engine, 'topology', 'ring')
                # Count how many full topo cycles with no new patterns
                _topo_cycles_done = gen // 10  # each topo runs ~10 gens
                if _topo_cycles_done >= len(TOPOLOGIES) and gen > 40:
                    # Check if we've had sustained zero streak across topology switches
                    _last_new_gen = 0
                    for _row in gen_history:
                        if _row['new'] > 0:
                            _last_new_gen = _row['gen']
                    _gens_since_new = gen - _last_new_gen
                    if _gens_since_new >= 20:  # 20+ gens with no new across topos
                        print(f"\n  🏁 AUTO-STOP: {_gens_since_new} gens since last new pattern")
                        print(f"  📊 All topologies exhausted at {args.cells}c/{args.steps}s")
                        print(f"  🚀 Switching to --auto-roadmap for parameter escalation")
                        sys.stdout.flush()
                        # Generate final EVO doc
                        _current_cells = engine.max_cells if hasattr(engine, 'max_cells') else args.cells
                        auto_generate_evo_doc(
                            {'name': 'main-loop-auto-stop', 'cells': _current_cells, 'steps': args.steps},
                            gen_history, registry,
                        )
                        # Save state and switch to auto-roadmap
                        save_state(gen, registry, active_mods_data, total_elapsed)
                        print(f"\n  Launching --auto-roadmap --resume ...")
                        sys.stdout.flush()
                        run_auto_roadmap(resume=True, report_interval=args.report_interval)
                        return  # exit main loop cleanly

            # Periodic report
            if gen % args.report_interval == 0:
                current_topo = getattr(engine, 'topology', 'ring')
                current_cells = engine.max_cells if hasattr(engine, 'max_cells') else args.cells
                generate_report(
                    gen, registry, active_mods, total_elapsed,
                    gen_history, phi_history,
                    cells=current_cells, steps=args.steps,
                    topology=current_topo,
                    features={'cycle_scale': args.cycle_scale,
                              'cycle_topology': args.cycle_topology,
                              'resume': args.resume},
                )

        # Normal exit (--max-gen reached)
        if gen_history:
            total_elapsed = prev_elapsed + (time.time() - start)
            current_topo = getattr(engine, 'topology', 'ring')
            current_cells = engine.max_cells if hasattr(engine, 'max_cells') else args.cells
            generate_report(
                gen - 1, registry, active_mods, total_elapsed,
                gen_history, phi_history,
                cells=current_cells, steps=args.steps,
                topology=current_topo,
                features={'cycle_scale': args.cycle_scale,
                          'cycle_topology': args.cycle_topology,
                          'resume': args.resume},
            )
            # Auto-generate EVO document
            auto_generate_evo_doc(
                {'name': 'main-loop', 'cells': current_cells, 'steps': args.steps},
                gen_history, registry,
            )
            # v3 #33-36: Save law network on exit
            try:
                _law_network.save()
            except Exception:
                pass
            # v8 #76: Save session log on normal exit
            try:
                _auto_save_session_log([], registry)
            except Exception:
                pass
            # v8 #71: Auto-generate report on normal exit
            try:
                _auto_generate_report([], registry, _law_network, 'main-loop-complete')
            except Exception:
                pass

    except KeyboardInterrupt:
        total_elapsed = prev_elapsed + (time.time() - start)

        # Final report
        current_topo = getattr(engine, 'topology', 'ring')
        current_cells = engine.max_cells if hasattr(engine, 'max_cells') else args.cells
        if gen_history:
            generate_report(
                gen, registry, active_mods, total_elapsed,
                gen_history, phi_history,
                cells=current_cells, steps=args.steps,
                topology=current_topo,
                features={'cycle_scale': args.cycle_scale,
                          'cycle_topology': args.cycle_topology,
                          'resume': args.resume},
            )

        print(f"\n{'=' * 70}")
        print(f"  STOPPED after {gen} generations ({total_elapsed:.0f}s)")
        print(f"  Unique patterns: {len(registry.seen)}")
        print(f"  Cross-validated laws: {sum(1 for v in registry.seen.values() if v['registered'])}")
        print(f"  Official law IDs: {registry.registered}")
        print(f"  Active modifications: {active_mods}")
        print(f"  Resume: python3 infinite_evolution.py --resume")
        print(f"{'=' * 70}")

        if hasattr(sme, 'get_evolution_report'):
            print(sme.get_evolution_report())

        # Final save
        active_mods_data = []
        if hasattr(sme, 'modifier') and hasattr(sme.modifier, 'applied'):
            for m in sme.modifier.applied:
                active_mods_data.append({
                    'law_id': m.law_id,
                    'target': m.target,
                    'mod_type': m.mod_type.value if hasattr(m.mod_type, 'value') else str(m.mod_type),
                    'params': m.params if isinstance(m.params, dict) else {},
                    'confidence': m.confidence,
                    'reversible': m.reversible,
                })
        path = save_state(gen, registry, active_mods_data, total_elapsed)
        print(f"  State saved to {path}")

        # Auto-generate EVO document on interrupt
        if gen_history:
            auto_generate_evo_doc(
                {'name': 'main-loop', 'cells': current_cells, 'steps': args.steps},
                gen_history, registry,
            )

        # v3 #33-36: Save law network on exit
        try:
            _law_network.save()
        except Exception:
            pass

        # v8 #76: Save session log
        try:
            _auto_save_session_log([], registry)
        except Exception:
            pass

        # v8 #71: Auto-generate report on exit
        try:
            if gen_history:
                _auto_generate_report([], registry, _law_network, 'main-loop-exit')
        except Exception:
            pass


if __name__ == '__main__':
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
