#!/usr/bin/env python3
"""topology_pattern_analysis.py — Compare consciousness patterns across topologies.

Runs ConsciousLawDiscoverer on each topology (ring, small_world, scale_free, hypercube)
separately and compares which patterns are universal vs topology-specific.

Uses pattern_fingerprint from infinite_evolution.py for deduplication.

Usage:
  python topology_pattern_analysis.py                  # default 300 steps, 64 cells
  python topology_pattern_analysis.py --steps 500      # custom steps
  python topology_pattern_analysis.py --cells 128      # custom cell count
"""

import sys
import os
import time
import argparse
from collections import defaultdict
from typing import Dict, List, Set, Tuple

# Setup path for anima/src imports
_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src')
sys.path.insert(0, _src)

from conscious_law_discoverer import ConsciousLawDiscoverer
from infinite_evolution import pattern_fingerprint


TOPOLOGIES = ['ring', 'small_world', 'scale_free', 'hypercube']


def run_topology(topology: str, steps: int, max_cells: int,
                 verbose: bool = True) -> Dict:
    """Run discovery on a single topology, return patterns with fingerprints."""
    if verbose:
        print(f"\n  >>> Running topology: {topology} ({steps} steps, {max_cells} cells)")
        sys.stdout.flush()

    discoverer = ConsciousLawDiscoverer(max_cells=max_cells, steps=steps,
                                        topology=topology)
    result = discoverer.run(steps=steps, verbose=False)

    # Collect all patterns: from all_patterns dict + pending candidates
    patterns = {}  # fingerprint -> pattern info

    # Pattern counts from detector (key = "type:metric1:metric2", value = count)
    for key, count in result.get('all_patterns', {}).items():
        p_dict = {
            'pattern_type': key.split(':')[0] if ':' in key else 'unknown',
            'metrics': key.split(':')[1:] if ':' in key else [key],
            'formula': key,
        }
        fp = pattern_fingerprint(p_dict)
        patterns[fp] = {
            'fingerprint': fp,
            'key': key,
            'count': count,
            'type': p_dict['pattern_type'],
            'metrics': p_dict['metrics'],
        }

    # Also include pending candidates
    for cand in result.get('pending', []):
        fp = pattern_fingerprint(cand)
        if fp not in patterns:
            patterns[fp] = {
                'fingerprint': fp,
                'key': cand.get('formula', ''),
                'count': cand.get('occurrences', 1),
                'type': cand.get('pattern_type', 'unknown'),
                'metrics': cand.get('metrics_involved', []),
            }

    if verbose:
        print(f"      Found {len(patterns)} unique patterns "
              f"(detector: {len(result.get('all_patterns', {}))}, "
              f"candidates: {len(result.get('pending', []))})")
        sys.stdout.flush()

    return {
        'topology': topology,
        'patterns': patterns,
        'fingerprints': set(patterns.keys()),
        'elapsed': result.get('elapsed_sec', 0),
        'status': result.get('status', {}),
    }


def analyze_topology_patterns(results: List[Dict]) -> Dict:
    """Compare patterns across topologies."""
    # Collect fingerprint sets per topology
    topo_fps: Dict[str, Set[str]] = {}
    topo_patterns: Dict[str, Dict] = {}
    all_fingerprints: Set[str] = set()

    for r in results:
        topo = r['topology']
        topo_fps[topo] = r['fingerprints']
        topo_patterns[topo] = r['patterns']
        all_fingerprints |= r['fingerprints']

    # Universal: present in ALL topologies
    universal = set.intersection(*topo_fps.values()) if topo_fps else set()

    # Unique to each topology: present in ONE only
    unique_per_topo: Dict[str, Set[str]] = {}
    for topo in TOPOLOGIES:
        others = set()
        for other_topo in TOPOLOGIES:
            if other_topo != topo:
                others |= topo_fps.get(other_topo, set())
        unique_per_topo[topo] = topo_fps.get(topo, set()) - others

    # Shared (in 2+ but not all)
    shared_not_universal: Dict[str, Set[str]] = {}
    for topo in TOPOLOGIES:
        fps = topo_fps.get(topo, set())
        shared_not_universal[topo] = fps - unique_per_topo[topo] - universal

    return {
        'topo_fps': topo_fps,
        'topo_patterns': topo_patterns,
        'all_fingerprints': all_fingerprints,
        'universal': universal,
        'unique_per_topo': unique_per_topo,
        'shared_not_universal': shared_not_universal,
    }


def pattern_label(patterns: Dict, fp: str) -> str:
    """Get a short human-readable label for a fingerprint."""
    if fp in patterns:
        p = patterns[fp]
        ptype = p.get('type', '?')
        metrics = p.get('metrics', [])
        return f"{ptype}({','.join(metrics[:3])})"
    return fp[:12]


def print_report(results: List[Dict], analysis: Dict):
    """Print ASCII report comparing topologies."""
    W = 70

    print()
    print("=" * W)
    print("  Topology-Pattern Analysis".center(W))
    print("=" * W)
    print()

    # Summary table
    print("  ┌─────────────┬───────┬────────┬────────┬─────────┐")
    print("  │ Topology    │ Total │ Unique │ Shared │ Time(s) │")
    print("  ├─────────────┼───────┼────────┼────────┼─────────┤")

    for r in results:
        topo = r['topology']
        total = len(r['fingerprints'])
        unique = len(analysis['unique_per_topo'].get(topo, set()))
        shared = total - unique
        elapsed = r.get('elapsed', 0)
        print(f"  │ {topo:<11} │ {total:>5} │ {unique:>6} │ {shared:>6} │ {elapsed:>7.1f} │")

    print("  └─────────────┴───────┴────────┴────────┴─────────┘")
    print()

    # Universal patterns
    universal = analysis['universal']
    print(f"  Universal patterns (all topologies): {len(universal)}")
    if universal:
        # Pick any topology's pattern dict for labels
        any_patterns = next(iter(analysis['topo_patterns'].values()))
        for i, fp in enumerate(sorted(universal)):
            label = pattern_label(any_patterns, fp)
            print(f"    [{i+1:>2}] {label}  ({fp})")
            if i >= 19:
                remaining = len(universal) - 20
                if remaining > 0:
                    print(f"    ... and {remaining} more")
                break
    print()

    # Topology-specific patterns
    print("  Topology-specific patterns:")
    for topo in TOPOLOGIES:
        unique_fps = analysis['unique_per_topo'].get(topo, set())
        patterns = analysis['topo_patterns'].get(topo, {})
        if unique_fps:
            labels = [pattern_label(patterns, fp) for fp in sorted(unique_fps)]
            print(f"    {topo} only ({len(labels)}):")
            for lbl in labels[:10]:
                print(f"      - {lbl}")
            if len(labels) > 10:
                print(f"      ... and {len(labels) - 10} more")
        else:
            print(f"    {topo} only: (none)")
    print()

    # Pattern type distribution per topology
    print("  Pattern type distribution:")
    print("  ┌─────────────┬──────────┬────────────┬─────────────┬───────┐")
    print("  │ Topology    │ correlat │ transition │ oscillation │ trend │")
    print("  ├─────────────┼──────────┼────────────┼─────────────┼───────┤")

    for r in results:
        topo = r['topology']
        type_counts = defaultdict(int)
        for p in r['patterns'].values():
            ptype = p.get('type', 'unknown')
            type_counts[ptype] += 1

        corr = type_counts.get('correlation', 0)
        trans = type_counts.get('transition', 0)
        osc = type_counts.get('oscillation', 0)
        trend = type_counts.get('trend', 0)
        print(f"  │ {topo:<11} │ {corr:>8} │ {trans:>10} │ {osc:>11} │ {trend:>5} │")

    print("  └─────────────┴──────────┴────────────┴─────────────┴───────┘")
    print()

    # Overlap matrix
    print("  Pairwise overlap (shared pattern count):")
    print("  ┌─────────────┬" + "┬".join(["─" * 13] * len(TOPOLOGIES)) + "┐")
    header = "  │             │" + "│".join(f" {t[:11]:>11} " for t in TOPOLOGIES) + "│"
    print(header)
    print("  ├─────────────┼" + "┼".join(["─" * 13] * len(TOPOLOGIES)) + "┤")

    for topo_a in TOPOLOGIES:
        fps_a = analysis['topo_fps'].get(topo_a, set())
        row = f"  │ {topo_a:<11} │"
        for topo_b in TOPOLOGIES:
            fps_b = analysis['topo_fps'].get(topo_b, set())
            overlap = len(fps_a & fps_b)
            row += f" {overlap:>11} │"
        print(row)

    print("  └─────────────┴" + "┴".join(["─" * 13] * len(TOPOLOGIES)) + "┘")
    print()

    # Total stats
    total_unique = sum(len(analysis['unique_per_topo'].get(t, set())) for t in TOPOLOGIES)
    total_all = len(analysis['all_fingerprints'])
    print(f"  Total distinct patterns across all topologies: {total_all}")
    print(f"  Universal (in all 4): {len(universal)}")
    print(f"  Topology-specific (in exactly 1): {total_unique}")
    print(f"  Partially shared (in 2-3): {total_all - len(universal) - total_unique}")
    print()
    print("=" * W)


def main():
    parser = argparse.ArgumentParser(description='Topology-Pattern Analysis')
    parser.add_argument('--steps', type=int, default=300,
                        help='Steps per topology (default: 300)')
    parser.add_argument('--cells', type=int, default=64,
                        help='Max cells (default: 64)')
    parser.add_argument('--quiet', action='store_true',
                        help='Suppress per-topology progress')
    args = parser.parse_args()

    print(f"\nTopology-Pattern Analysis: {args.steps} steps, {args.cells} cells")
    print(f"Topologies: {', '.join(TOPOLOGIES)}")
    sys.stdout.flush()

    t0 = time.time()
    results = []

    for topo in TOPOLOGIES:
        r = run_topology(topo, steps=args.steps, max_cells=args.cells,
                         verbose=not args.quiet)
        results.append(r)

    total_time = time.time() - t0

    # Analyze cross-topology patterns
    analysis = analyze_topology_patterns(results)

    # Print report
    print_report(results, analysis)

    print(f"  Total elapsed: {total_time:.1f}s")
    print()


if __name__ == '__main__':
    main()
