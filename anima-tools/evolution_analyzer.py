#!/usr/bin/env python3
"""
Evolution State Analyzer — standalone tool for evolution_state.json analysis.

Generates statistics, ASCII graphs, and comparison reports from
infinite_evolution.py's saved state files.

Usage:
    python3 evolution_analyzer.py                        # analyze default
    python3 evolution_analyzer.py --file path.json       # specific file
    python3 evolution_analyzer.py --compare a.json b.json
"""

import argparse
import json
import os
import sys
from collections import defaultdict

DEFAULT_PATH = os.path.join(
    os.path.dirname(__file__), '..', 'data', 'evolution_state.json'
)


def load_state(path: str) -> dict:
    """Load and validate an evolution_state.json file."""
    path = os.path.abspath(path)
    if not os.path.exists(path):
        print(f"Error: File not found: {path}")
        sys.exit(1)
    with open(path) as f:
        data = json.load(f)
    if 'registry' not in data or 'seen' not in data.get('registry', {}):
        print(f"Error: Invalid evolution_state format in {path}")
        sys.exit(1)
    return data


def format_duration(seconds: float) -> str:
    """Format seconds into human-readable duration."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        m, s = divmod(seconds, 60)
        return f"{int(m)}m {int(s)}s"
    else:
        h, rem = divmod(seconds, 3600)
        m, s = divmod(rem, 60)
        return f"{int(h)}h {int(m)}m {int(s)}s"


def analyze(data: dict) -> dict:
    """Extract all statistics from state data."""
    gen = data.get('generation', 0)
    elapsed = data.get('total_elapsed_sec', 0)
    seen = data.get('registry', {}).get('seen', {})
    registered_ids = data.get('registry', {}).get('registered', [])
    active_mods = data.get('active_mods', [])
    stats = data.get('stats', {})

    unique = len(seen)
    cross_validated = sum(1 for v in seen.values() if v.get('registered'))
    pending = unique - cross_validated
    total_obs = sum(v.get('count', 0) for v in seen.values())
    hit_rate = (cross_validated / unique * 100) if unique > 0 else 0
    avg_per_gen = (elapsed / gen) if gen > 0 else 0

    # Top patterns by occurrence
    patterns_sorted = sorted(
        seen.items(),
        key=lambda kv: kv[1].get('count', 0),
        reverse=True
    )

    # Discovery timeline: group by first_gen
    discovery_by_gen = defaultdict(int)
    for fp, v in seen.items():
        fg = v.get('first_gen', 1)
        discovery_by_gen[fg] += 1

    # Cross-validation timeline: group by when patterns got registered
    # A pattern is promoted when count >= threshold. Approximate the gen
    # it was promoted at: first_gen + (threshold - 1) since it needs
    # threshold observations. But we don't know exact gen, so use
    # last_gen for registered patterns as a rough proxy (they keep counting).
    # Better: for cross-validated patterns, promotion happened around
    # first_gen + 2 (since threshold is typically 3).
    promotion_by_gen = defaultdict(int)
    for fp, v in seen.items():
        if v.get('registered'):
            # Best estimate: promoted at first_gen + 2 (threshold=3)
            fg = v.get('first_gen', 1)
            count = v.get('count', 0)
            # If first seen at gen 1 and count=45 for gen=45, promoted at gen 3
            promo_gen = min(fg + 2, gen)
            promotion_by_gen[promo_gen] += 1

    return {
        'generation': gen,
        'elapsed': elapsed,
        'avg_per_gen': avg_per_gen,
        'unique': unique,
        'cross_validated': cross_validated,
        'pending': pending,
        'total_observations': total_obs,
        'hit_rate': hit_rate,
        'registered_law_ids': registered_ids,
        'active_mods': active_mods,
        'top_patterns': patterns_sorted[:15],
        'discovery_by_gen': dict(sorted(discovery_by_gen.items())),
        'promotion_by_gen': dict(sorted(promotion_by_gen.items())),
        'timestamp': data.get('timestamp', 'unknown'),
        'version': data.get('version', 1),
    }


def ascii_bar(value: int, max_value: int, width: int = 40) -> str:
    """Create an ASCII bar of proportional width."""
    if max_value <= 0:
        return ''
    bar_len = max(1, int(value / max_value * width))
    return '\u2588' * bar_len


def render_report(info: dict, file_path: str = '') -> str:
    """Render full ASCII report."""
    lines = []

    # Header
    lines.append('')
    lines.append('\u2550' * 55)
    lines.append('  Evolution State Analysis')
    lines.append('\u2550' * 55)
    if file_path:
        lines.append(f'  File: {os.path.basename(file_path)}')
    lines.append(f'  Timestamp: {info["timestamp"]}')
    lines.append(f'  Version: {info["version"]}')
    lines.append('')

    # Summary
    gen = info['generation']
    lines.append(f'  Generation: {gen} | '
                 f'Elapsed: {format_duration(info["elapsed"])} | '
                 f'Avg: {info["avg_per_gen"]:.1f}s/gen')
    lines.append('')

    # Pattern stats
    lines.append('  Patterns:')
    lines.append(f'    Unique: {info["unique"]} | '
                 f'Cross-validated: {info["cross_validated"]} | '
                 f'Pending: {info["pending"]}')
    lines.append(f'    Hit rate: {info["hit_rate"]:.0f}% '
                 f'(cross-validated / unique)')
    lines.append(f'    Total observations: {info["total_observations"]}')
    lines.append('')

    # Top patterns
    lines.append('  Top patterns by occurrence:')
    for i, (fp, v) in enumerate(info['top_patterns'][:10], 1):
        formula = v.get('pattern', {}).get('formula', fp[:20])
        count = v.get('count', 0)
        fg = v.get('first_gen', '?')
        lg = v.get('last_gen', '?')
        status = 'XV' if v.get('registered') else '  '
        lines.append(f'    {i:>2}. [{status}] {formula:<45} '
                     f'{count:>3}x (Gen {fg}-{lg})')
    lines.append('')

    # Active modifications
    mods = info['active_mods']
    lines.append(f'  Active modifications: {len(mods)}')
    if mods:
        for m in mods:
            law_id = m.get('law_id', '?')
            target = m.get('target', '?')
            mod_type = m.get('mod_type', '?')
            conf = m.get('confidence', 0)
            lines.append(f'    Law {law_id:<4} -> {target:<8} '
                         f'type={mod_type:<12} conf={conf:.1f}')
    lines.append('')

    # Registered law IDs
    law_ids = info['registered_law_ids']
    if law_ids:
        lines.append(f'  Registered law IDs: {len(law_ids)}')
        # Show in compact form
        chunks = []
        for i in range(0, len(law_ids), 15):
            chunk = law_ids[i:i+15]
            chunks.append('    ' + ', '.join(str(x) for x in chunk))
        for c in chunks:
            lines.append(c)
        lines.append('')

    # Discovery timeline graph
    disc = info['discovery_by_gen']
    if disc:
        lines.append('  Pattern discovery timeline:')
        max_disc = max(disc.values()) if disc else 1
        # Show up to 20 generations
        gens_to_show = sorted(disc.keys())[:20]
        label_w = len(str(max_disc))
        for g in gens_to_show:
            n = disc[g]
            bar = ascii_bar(n, max_disc, 30)
            lines.append(f'  {n:>{label_w}}|{bar}  Gen {g} ({n} new)')
        lines.append(f'  {" " * label_w}+{"-" * 32} Gen')
        lines.append('')

    # Cross-validation timeline graph
    prom = info['promotion_by_gen']
    if prom:
        lines.append('  Cross-validation timeline:')
        max_prom = max(prom.values()) if prom else 1
        gens_to_show = sorted(prom.keys())[:20]
        label_w = len(str(max_prom))
        for g in gens_to_show:
            n = prom[g]
            bar = ascii_bar(n, max_prom, 30)
            lines.append(f'  {n:>{label_w}}|{bar}  Gen {g} ({n} promoted)')
        lines.append(f'  {" " * label_w}+{"-" * 32} Gen')
        lines.append('')

    # Pattern type breakdown
    type_counts = defaultdict(int)
    seen = {}
    for fp, v in info['top_patterns']:
        formula = v.get('pattern', {}).get('formula', '')
        ptype = formula.split(':')[0] if ':' in formula else 'unknown'
        type_counts[ptype] += 1
    # Get all patterns from the original data (top_patterns is limited)
    # Just show what we have
    if type_counts:
        lines.append('  Pattern types (in top patterns):')
        max_tc = max(type_counts.values()) if type_counts else 1
        for ptype, count in sorted(type_counts.items(),
                                   key=lambda x: -x[1]):
            bar = ascii_bar(count, max_tc, 20)
            lines.append(f'    {ptype:<15} {count:>3} {bar}')
        lines.append('')

    lines.append('\u2550' * 55)
    return '\n'.join(lines)


def render_comparison(info_a: dict, info_b: dict,
                      path_a: str, path_b: str) -> str:
    """Render side-by-side comparison of two states."""
    lines = []
    name_a = os.path.basename(path_a)
    name_b = os.path.basename(path_b)

    lines.append('')
    lines.append('\u2550' * 65)
    lines.append('  Evolution State Comparison')
    lines.append('\u2550' * 65)
    lines.append('')

    # Header row
    w = 20
    lines.append(f'  {"Metric":<25} {name_a:>{w}} {name_b:>{w}}  Delta')
    lines.append(f'  {"-"*25} {"-"*w} {"-"*w}  {"-"*10}')

    def row(label, va, vb, fmt='d'):
        if fmt == 'd':
            sa = f'{va:>{w}d}'
            sb = f'{vb:>{w}d}'
            delta = vb - va
            sd = f'{delta:+d}' if delta != 0 else '='
        elif fmt == 'f1':
            sa = f'{va:>{w}.1f}'
            sb = f'{vb:>{w}.1f}'
            delta = vb - va
            sd = f'{delta:+.1f}' if abs(delta) > 0.05 else '='
        elif fmt == 'pct':
            sa = f'{va:>{w}.0f}%'
            sb = f'{vb:>{w}.0f}%'
            delta = vb - va
            sd = f'{delta:+.0f}%' if abs(delta) > 0.5 else '='
        elif fmt == 's':
            sa = f'{va:>{w}}'
            sb = f'{vb:>{w}}'
            sd = ''
        else:
            sa = f'{va:>{w}}'
            sb = f'{vb:>{w}}'
            sd = ''
        lines.append(f'  {label:<25} {sa} {sb}  {sd}')

    row('Generation', info_a['generation'], info_b['generation'])
    row('Elapsed (s)', info_a['elapsed'], info_b['elapsed'], 'f1')
    row('Avg s/gen', info_a['avg_per_gen'], info_b['avg_per_gen'], 'f1')
    row('Unique patterns', info_a['unique'], info_b['unique'])
    row('Cross-validated', info_a['cross_validated'], info_b['cross_validated'])
    row('Pending', info_a['pending'], info_b['pending'])
    row('Hit rate', info_a['hit_rate'], info_b['hit_rate'], 'pct')
    row('Total observations', info_a['total_observations'],
        info_b['total_observations'])
    row('Active mods', len(info_a['active_mods']),
        len(info_b['active_mods']))
    row('Registered laws', len(info_a['registered_law_ids']),
        len(info_b['registered_law_ids']))

    lines.append('')

    # New patterns in B that are not in A (by formula)
    formulas_a = set()
    for fp, v in info_a['top_patterns']:
        formulas_a.add(v.get('pattern', {}).get('formula', ''))
    new_in_b = []
    for fp, v in info_b['top_patterns']:
        f = v.get('pattern', {}).get('formula', '')
        if f and f not in formulas_a:
            new_in_b.append(f)

    if new_in_b:
        lines.append(f'  New patterns in {name_b} (not in {name_a}):')
        for f in new_in_b[:10]:
            lines.append(f'    + {f}')
        lines.append('')

    lines.append('\u2550' * 65)
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='Evolution State Analyzer — '
                    'statistics and ASCII graphs for evolution_state.json'
    )
    parser.add_argument('--file', '-f', type=str, default=None,
                        help='Path to evolution_state.json '
                             '(default: anima/data/evolution_state.json)')
    parser.add_argument('--compare', '-c', nargs=2, metavar=('FILE1', 'FILE2'),
                        help='Compare two state files side-by-side')
    parser.add_argument('--json', action='store_true',
                        help='Output raw analysis as JSON')
    args = parser.parse_args()

    if args.compare:
        path_a, path_b = args.compare
        data_a = load_state(path_a)
        data_b = load_state(path_b)
        info_a = analyze(data_a)
        info_b = analyze(data_b)

        if args.json:
            print(json.dumps({'a': info_a, 'b': info_b},
                             indent=2, default=str))
        else:
            print(render_comparison(info_a, info_b, path_a, path_b))
    else:
        path = args.file or DEFAULT_PATH
        data = load_state(path)
        info = analyze(data)

        if args.json:
            # Convert tuples for JSON serialization
            info['top_patterns'] = [
                {'fingerprint': fp, **v}
                for fp, v in info['top_patterns']
            ]
            print(json.dumps(info, indent=2, default=str))
        else:
            print(render_report(info, file_path=path))


if __name__ == '__main__':
    main()
