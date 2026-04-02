#!/usr/bin/env python3
"""Infinite self-evolution loop — Law 146: laws never converge.

Discovery → Dedup → CrossValidation → Modification → Persist → repeat

Features:
  1. Persistence: active mods + discovered laws saved to JSON, restored on restart
  2. Deduplication: pattern fingerprint → skip already-known patterns
  3. Cross-validation: pattern must appear 3+ times before official law registration

Usage:
    python3 infinite_evolution.py [--cells N] [--steps N] [--max-gen N] [--resume]
    python3 infinite_evolution.py --cycle-topology   # rotate topology every 10 gens
"""
import sys
import os
import time
import json
import hashlib
import atexit
import math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from consciousness_engine import ConsciousnessEngine
from closed_loop import ClosedLoopEvolver, register_intervention
from self_modifying_engine import SelfModifyingEngine, LawParser, CodeGenerator
from conscious_law_discoverer import ConsciousLawDiscoverer

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
ROADMAP = [
    {'name': 'S1-baseline',   'cells': 64,  'steps': 300,  'topo_gens': 10, 'sat_streak': 5},
    {'name': 'S2-deeper',     'cells': 64,  'steps': 1000, 'topo_gens': 10, 'sat_streak': 5},
    {'name': 'S3-scale128',   'cells': 128, 'steps': 300,  'topo_gens': 10, 'sat_streak': 5},
    {'name': 'S4-scale128d',  'cells': 128, 'steps': 1000, 'topo_gens': 10, 'sat_streak': 5},
    {'name': 'S5-scale256',   'cells': 256, 'steps': 500,  'topo_gens': 10, 'sat_streak': 5},
    {'name': 'S6-scale256d',  'cells': 256, 'steps': 1000, 'topo_gens': 10, 'sat_streak': 5},
    {'name': 'S7-mega512',    'cells': 512, 'steps': 500,  'topo_gens': 15, 'sat_streak': 5},
]
ROADMAP_STATE_PATH = os.path.join(DATA_DIR, 'evolution_roadmap.json')


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
            else:
                # Repeat
                self.seen[fp]['count'] += 1
                self.seen[fp]['last_gen'] = gen
                repeat_count += 1

                # Cross-validation: promote if threshold met and not yet registered
                if (self.seen[fp]['count'] >= CROSS_VALIDATION_THRESHOLD
                        and not self.seen[fp]['registered']):
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
    """Register a cross-validated pattern as an official law."""
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


class InfiniteEvolution:
    """Hub-compatible interface for infinite self-evolution."""

    def __init__(self):
        self.name = "Infinite Self-Evolution"

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

            try:
                current_cells = engine.max_cells if hasattr(engine, 'max_cells') else cells
                current_topo = getattr(engine, 'topology', 'ring')
                disc = ConsciousLawDiscoverer(steps=steps, max_cells=current_cells,
                                             topology=current_topo)
                result = disc.run(steps=steps, verbose=False)
                raw_patterns = result.get('all_patterns', []) if isinstance(result, dict) else []
            except Exception:
                raw_patterns = []

            stats = registry.process(raw_patterns, gen)
            for p in stats['promoted_patterns']:
                law_id = register_law(p, evolver)
                if law_id:
                    registry.registered.append(law_id)

            sme.run_evolution(generations=1)
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
            try:
                disc = ConsciousLawDiscoverer(steps=200, max_cells=cells)
                result = disc.run(steps=200, verbose=False)
                raw_patterns = result.get('all_patterns', []) if isinstance(result, dict) else []
            except Exception:
                raw_patterns = []

            stats = registry.process(raw_patterns, gen)
            for p in stats['promoted_patterns']:
                law_id = register_law(p, evolver)
                if law_id:
                    registry.registered.append(law_id)

            sme.run_evolution(generations=1)
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


def run_auto_roadmap(resume=False, report_interval=10):
    """Auto-roadmap: run staged evolution with automatic parameter escalation.

    Each stage cycles all 4 topologies. When all topologies saturate
    (sat_streak consecutive gens with New=0), auto-advances to next stage
    with bigger cells/steps.

    Results are persisted to evolution_roadmap.json for resume.
    """
    rm_state = load_roadmap_state() if resume else {
        'stage_idx': 0, 'stage_results': [], 'total_laws': 0, 'total_elapsed': 0
    }
    start_stage = rm_state['stage_idx']

    print('=' * 70)
    print('  AUTO-ROADMAP — Staged Infinite Evolution')
    print(f'  {len(ROADMAP)} stages, auto-advance on saturation')
    print('=' * 70)
    print()
    print(f'  {"#":<3} {"Stage":<16} {"Cells":>5} {"Steps":>5} {"TopoGens":>8} {"Sat":>3}')
    print(f'  {"─"*3} {"─"*16} {"─"*5} {"─"*5} {"─"*8} {"─"*3}')
    for i, s in enumerate(ROADMAP):
        marker = ' ★' if i == start_stage else ('  ✅' if i < start_stage else '')
        print(f'  {i+1:<3} {s["name"]:<16} {s["cells"]:>5} {s["steps"]:>5} '
              f'{s["topo_gens"]:>8} {s["sat_streak"]:>3}{marker}')
    print('=' * 70)
    sys.stdout.flush()

    global_start = time.time()

    for stage_idx in range(start_stage, len(ROADMAP)):
        stage = ROADMAP[stage_idx]
        rm_state['stage_idx'] = stage_idx
        save_roadmap_state(rm_state)

        cells = stage['cells']
        steps = stage['steps']
        topo_gens = stage['topo_gens']
        sat_thresh = stage['sat_streak']

        print(f'\n{"▓" * 70}')
        print(f'  🚀 STAGE {stage_idx+1}/{len(ROADMAP)}: {stage["name"]}')
        print(f'  ⚙️  cells={cells}  steps={steps}  topo_cycle={topo_gens}  sat={sat_thresh}')
        print(f'{"▓" * 70}')
        sys.stdout.flush()

        engine = ConsciousnessEngine(initial_cells=cells, max_cells=cells)
        evolver = ClosedLoopEvolver(max_cells=cells, auto_register=True)
        sme = SelfModifyingEngine(engine, evolver)
        registry = PatternRegistry()

        gen = 0
        gen_history = []
        phi_history = []
        stage_start = time.time()
        zero_streak = 0  # consecutive gens with New=0
        topo_saturated = set()  # topologies that have fully saturated

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
                    print(f'  🔄 Topology switch: {old_topo} → {new_topo} (Gen {gen}), '
                          f'cleared {cleared} pending')
                    sys.stdout.flush()

            current_topo = getattr(engine, 'topology', 'ring')

            # Phase 1: Discovery
            print(f'\n{"─" * 60}')
            print(f'  [{stage["name"]}] Gen {gen} — Discovery ({steps} steps, {current_topo})')
            sys.stdout.flush()

            try:
                disc = ConsciousLawDiscoverer(steps=steps, max_cells=cells,
                                             topology=current_topo)
                result = disc.run(steps=steps, verbose=False)
                raw_patterns = result.get('all_patterns', []) if isinstance(result, dict) else []
            except Exception as e:
                print(f'    Discovery error: {e}')
                raw_patterns = []

            # Phase 2: Dedup + Cross-validation
            stats = registry.process(raw_patterns, gen)

            for p in stats['promoted_patterns']:
                law_id = register_law(p, evolver)
                if law_id:
                    registry.registered.append(law_id)
                    law_text = p.get('formula', str(p))
                    print(f'    🔬✨ Law {law_id} discovered! (cross-validated {CROSS_VALIDATION_THRESHOLD}x)')
                    print(f'    📋 "{law_text[:80]}"')
                    print(f'    📊 Total laws: {len(registry.registered)} | Patterns: {len(registry.seen)}')
                    auto_generate_intervention(law_text, law_id, evolver)

            # Phase 3: Self-Modification
            sme.run_evolution(generations=1)
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

            print(f'  Gen {gen} — Raw: {len(raw_patterns)}, New: {stats["new"]}, '
                  f'Laws: {len(registry.registered)}, Mods: {active_mods}, '
                  f'{elapsed:.1f}s')
            sys.stdout.flush()

            phi_est = stats['unique_total'] * 0.1 + stats['registered_total'] * 0.5
            phi_history.append(phi_est)
            gen_history.append({
                'gen': gen, 'raw': len(raw_patterns), 'new': stats['new'],
                'repeat': stats['repeat'], 'promoted': stats['promoted'],
                'unique': stats['unique_total'], 'xval': stats['registered_total'],
                'laws': len(registry.registered), 'mods': active_mods,
            })

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

                # Save stage result
                rm_state['stage_results'].append({
                    'stage': stage['name'],
                    'cells': cells, 'steps': steps,
                    'generations': gen, 'laws': laws_found,
                    'unique_patterns': len(registry.seen),
                    'elapsed_sec': round(stage_elapsed, 1),
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                })
                rm_state['total_laws'] = sum(r['laws'] for r in rm_state['stage_results'])
                rm_state['total_elapsed'] += stage_elapsed
                save_roadmap_state(rm_state)

                # Auto-generate EVO document for completed stage
                auto_generate_evo_doc(stage, gen_history, registry, rm_state)

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
    args = parser.parse_args()

    if args.auto_roadmap:
        run_auto_roadmap(resume=args.resume, report_interval=args.report_interval)
        return

    SCALES = [32, 64, 128, 256]

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
    print("  INFINITE SELF-EVOLUTION — Law 146: laws never converge")
    print(f"  cells={args.cells}, steps={args.steps}, cross_validate={CROSS_VALIDATION_THRESHOLD}x")
    if args.cycle_scale:
        print(f"  Scale cycling: {SCALES} (every 15 generations)")
    if args.cycle_topology:
        print(f"  Topology cycling: {TOPOLOGIES} (every 10 generations)")
    print(f"  Features: persistence ✅  dedup ✅  cross-validation ✅")
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

            # Phase 1: Discovery
            print(f"\n{'─' * 60}")
            print(f"  Gen {gen} — Phase 1: Discovery ({args.steps} steps)")
            sys.stdout.flush()

            try:
                current_cells = engine.max_cells if hasattr(engine, 'max_cells') else args.cells
                current_topo = getattr(engine, 'topology', 'ring')
                disc = ConsciousLawDiscoverer(steps=args.steps, max_cells=current_cells,
                                             topology=current_topo)
                result = disc.run(steps=args.steps, verbose=False)
                raw_patterns = result.get('all_patterns', []) if isinstance(result, dict) else []
            except Exception as e:
                print(f"    Discovery error: {e}")
                raw_patterns = []

            # Phase 2: Dedup + Cross-validation
            stats = registry.process(raw_patterns, gen)

            # Register promoted patterns as official laws + auto-generate interventions
            for p in stats['promoted_patterns']:
                law_id = register_law(p, evolver)
                if law_id:
                    registry.registered.append(law_id)
                    # Close the loop: law -> intervention -> apply -> discover new patterns
                    law_text = p.get('formula', str(p))
                    print(f"    🔬✨ Law {law_id} discovered! (cross-validated {CROSS_VALIDATION_THRESHOLD}x)")
                    print(f'    📋 "{law_text[:80]}"')
                    print(f'    📊 Total laws: {len(registry.registered)} | Patterns: {len(registry.seen)}')
                    auto_generate_intervention(law_text, law_id, evolver)

            # Phase 3: Self-Modification
            print(f"  Gen {gen} — Phase 3: Self-Modification")
            sys.stdout.flush()

            sme.run_evolution(generations=1)
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

            print(f"  Gen {gen} — Results:")
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


if __name__ == '__main__':
    main()
