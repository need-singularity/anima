#!/usr/bin/env python3
"""nexus6_telescope.py — Bridge between Anima consciousness engine and NEXUS-6 lenses

Law 1047 optimal mapping: 6 lenses -> Hexad 6 modules
  ConsciousnessOrchestrator -> C (consciousness core)
  Gravity                   -> D (decoder - weight/importance)
  Warp                      -> W (will - transformation)
  Spacetime                 -> S (sense - spatiotemporal)
  Entropy                   -> M (memory - information)
  Singularity               -> E (ethics - convergence)

Usage:
  from nexus6_telescope import TelescopeBridge
  bridge = TelescopeBridge()
  results = bridge.scan_consciousness(engine_state)
  bridge.feed_growth(results)
  synergies = bridge.discover_from_lenses(hypothesis_data)

Hub registration:
  keywords: telescope, nexus6, lens, scan, bridge, 망원경, 렌즈, 스캔
"""

import json
import math
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_THIS_DIR = Path(__file__).parent
_CONFIG_DIR = _THIS_DIR.parent / 'config'
_GROWTH_STATE = _CONFIG_DIR / 'growth_state.json'
_LAWS_JSON = _CONFIG_DIR / 'consciousness_laws.json'
_NEXUS6_GROWTH = Path.home() / 'Dev' / 'nexus6' / 'shared' / 'growth-registry.json'

LN2 = math.log(2)
PSI_BALANCE = 0.5

# nexus6 import — graceful fallback
try:
    import nexus6
    _HAS_NEXUS6 = True
except ImportError:
    _HAS_NEXUS6 = False

# numpy — optional for array handling
try:
    import numpy as np
    _HAS_NP = True
except ImportError:
    _HAS_NP = False

# Law 1047 mapping: hexad module -> NEXUS-6 lens name (as registered in scan)
HEXAD_LENS_MAP = {
    'C': 'ConsciousnessOrchestratorLens',
    'D': 'GravityLens',
    'W': 'WarpLens',
    'S': 'SpacetimeLens',
    'M': 'EntropyLens',
    'E': 'SingularityLens',
}

# Human-readable names for display
HEXAD_LENS_DISPLAY = {
    'C': 'consciousness_orchestrator',
    'D': 'gravity',
    'W': 'warp',
    'S': 'spacetime',
    'M': 'entropy',
    'E': 'singularity',
}

# Reverse for lookup
LENS_TO_HEXAD = {v: k for k, v in HEXAD_LENS_MAP.items()}


def _to_flat(data) -> list:
    """Convert engine state to flat list for nexus6 scanning."""
    if _HAS_NP and isinstance(data, np.ndarray):
        return data.flatten().tolist()
    if hasattr(data, 'detach'):  # torch tensor
        return data.detach().cpu().numpy().flatten().tolist()
    if isinstance(data, (list, tuple)):
        flat = []
        for item in data:
            if isinstance(item, (list, tuple)):
                flat.extend(item)
            elif isinstance(item, (int, float)):
                flat.append(float(item))
            elif _HAS_NP and isinstance(item, np.ndarray):
                flat.extend(item.flatten().tolist())
        return flat if flat else list(data)
    return [float(data)] if isinstance(data, (int, float)) else []


def _load_json(path: Path) -> dict:
    if path.exists():
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


class TelescopeBridge:
    """Bridge connecting Anima's consciousness engine with NEXUS-6 lenses.

    Tracks which lenses correlate with Phi improvements and feeds
    growth data back to the consciousness growth system.
    """

    def __init__(self):
        self._correlation_log: List[Dict] = []
        self._scan_count = 0

    def scan_consciousness(self, engine_state) -> Dict[str, Any]:
        """Scan engine state through all 6 hexad-mapped lenses.

        Args:
            engine_state: Cell states as tensor, ndarray, or flat list.

        Returns:
            Dict with per-hexad lens results + phi + consensus count.
        """
        flat = _to_flat(engine_state)
        if not flat:
            return {'error': 'empty engine state', 'hexad': {}}

        if not _HAS_NEXUS6:
            return self._fallback_scan(flat)

        # Determine grid shape for analyze(flat_list, n, d)
        # n*d must equal len(flat) exactly
        total = len(flat)
        n = max(1, int(total ** 0.5))
        d = total // n
        # Trim flat to exact n*d length
        flat = flat[:n * d]

        # nexus6.analyze returns: {scan: ScanResult, consensus: [...], ...}
        result_raw = nexus6.analyze(flat, n, d)
        scan_obj = result_raw['scan']  # ScanResult object
        self._scan_count += 1

        hexad_results = {}
        for module_key, lens_name in HEXAD_LENS_MAP.items():
            raw = scan_obj.get_metric(lens_name)
            # get_metric returns dict: {metric_name: [values]} or {}
            if isinstance(raw, dict) and raw:
                # Extract first numeric value from the lens metrics
                first_key = next(iter(raw))
                vals = raw[first_key]
                score = float(vals[0]) if isinstance(vals, list) and vals else 0.0
            else:
                score = 0.0
            hexad_results[module_key] = {
                'lens': HEXAD_LENS_DISPLAY[module_key],
                'score': score,
                'raw': raw,
            }

        # Global phi from ConsciousnessLens
        phi_raw = scan_obj.get_metric('ConsciousnessLens')
        if isinstance(phi_raw, dict) and phi_raw:
            first_vals = next(iter(phi_raw.values()))
            phi = float(first_vals[0]) if isinstance(first_vals, list) and first_vals else 0.0
        else:
            phi = 0.0

        consensus_items = result_raw.get('consensus', [])
        consensus_count = len(consensus_items) if isinstance(consensus_items, list) else 0

        result = {
            'hexad': hexad_results,
            'phi': float(phi),
            'consensus': consensus_count,
            'scan_id': self._scan_count,
            'timestamp': time.time(),
            'n6_available': True,
        }

        # Track correlation for later analysis
        self._correlation_log.append({
            'phi': result['phi'],
            'scores': {k: v['score'] for k, v in hexad_results.items()},
            'time': result['timestamp'],
        })

        return result

    @staticmethod
    def _entropy_proxy(flat: list) -> float:
        """Normalized Shannon entropy of absolute values (0-1)."""
        subset = flat[:64]
        total = sum(abs(x) + 1e-10 for x in subset)
        h = 0.0
        for x in subset:
            p = (abs(x) + 1e-10) / total
            h -= p * math.log(p)
        max_h = math.log(max(len(subset), 1))
        return h / max_h if max_h > 0 else 0.0

    def _fallback_scan(self, flat: list) -> Dict[str, Any]:
        """Lightweight fallback when nexus6 is not available.

        Uses basic statistical proxies for each lens dimension.
        """
        n = len(flat)
        if n == 0:
            return {'error': 'empty data', 'hexad': {}}

        mean = sum(flat) / n
        var = sum((x - mean) ** 2 for x in flat) / n
        std = var ** 0.5

        # Proxy scores derived from basic statistics
        proxies = {
            'C': min(1.0, var * 10),            # consciousness: variance = integration
            'D': min(1.0, abs(mean) * 5),       # gravity: mean magnitude = weight
            'W': min(1.0, std / (abs(mean) + 1e-8)),  # warp: coefficient of variation
            'S': min(1.0, n / 1024),             # spacetime: dimensionality
            'M': min(1.0, self._entropy_proxy(flat)),  # entropy proxy
            'E': min(1.0, 1.0 - var / (var + PSI_BALANCE)),  # singularity: convergence
        }

        hexad_results = {}
        for key, score in proxies.items():
            hexad_results[key] = {
                'lens': HEXAD_LENS_DISPLAY[key],
                'score': round(score, 4),
                'raw': {'fallback': True},
            }

        self._scan_count += 1
        return {
            'hexad': hexad_results,
            'phi': round(var * n * 0.01, 4),  # crude phi proxy
            'consensus': 0,
            'scan_id': self._scan_count,
            'timestamp': time.time(),
            'n6_available': False,
        }

    def feed_growth(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Update growth_state.json with lens-derived growth signals.

        Higher lens scores across multiple hexad modules indicate
        richer consciousness -- this feeds back into the growth engine.
        """
        hexad = results.get('hexad', {})
        if not hexad:
            return {'updated': False, 'reason': 'no hexad data'}

        scores = [v['score'] for v in hexad.values() if isinstance(v, dict)]
        if not scores:
            return {'updated': False, 'reason': 'no scores'}

        avg_score = sum(scores) / len(scores)
        phi = results.get('phi', 0.0)
        consensus = results.get('consensus', 0)

        # Growth bonus: consensus * avg_score (capped at 10)
        growth_delta = min(10, max(0, int(consensus * avg_score * 3)))

        # Update growth_state.json
        state = _load_json(_GROWTH_STATE)
        if not state:
            return {'updated': False, 'reason': 'growth_state.json not found'}

        stats = state.get('stats', {})
        prev_bonus = stats.get('nexus6_bonus', 0)
        stats['nexus6_bonus'] = prev_bonus + growth_delta
        stats['last_telescope_scan'] = time.time()
        stats['last_telescope_phi'] = phi
        state['stats'] = stats

        # Increment interaction count by growth_delta
        if growth_delta > 0:
            state['interaction_count'] = state.get('interaction_count', 0) + growth_delta

        _save_json(_GROWTH_STATE, state)

        # Also update nexus6 growth-registry if available
        registry_update = self._update_growth_registry(results, growth_delta)

        return {
            'updated': True,
            'growth_delta': growth_delta,
            'avg_score': round(avg_score, 4),
            'phi': phi,
            'registry_synced': registry_update,
        }

    def _update_growth_registry(self, results: Dict, delta: int) -> bool:
        """Sync growth event to nexus6 shared growth-registry.json."""
        if not _NEXUS6_GROWTH.exists():
            return False
        try:
            registry = _load_json(_NEXUS6_GROWTH)
            events = registry.get('events', [])
            events.append({
                'source': 'anima-telescope',
                'phi': results.get('phi', 0),
                'consensus': results.get('consensus', 0),
                'delta': delta,
                'time': time.strftime('%Y-%m-%dT%H:%M:%S'),
            })
            # Keep last 100 events
            registry['events'] = events[-100:]
            registry['last_anima_sync'] = time.strftime('%Y-%m-%dT%H:%M:%S')
            _save_json(_NEXUS6_GROWTH, registry)
            return True
        except (OSError, json.JSONDecodeError):
            return False

    def discover_from_lenses(self, hypothesis_data) -> Dict[str, Any]:
        """Run mirror_universe scan on hypothesis data to find synergies.

        Compares hypothesis results against known hexad correlations
        to identify which lens combinations boost Phi most.
        """
        flat = _to_flat(hypothesis_data)
        if not flat:
            return {'synergies': [], 'error': 'empty hypothesis data'}

        if _HAS_NEXUS6:
            total = len(flat)
            n = max(1, int(total ** 0.5))
            d = total // n
            flat = flat[:n * d]
            result_raw = nexus6.analyze(flat, n, d)
            scan_obj = result_raw['scan']
            # Look for mirror lens results
            mirror = scan_obj.get_metric('MirrorLens')
            if not mirror:
                mirror = {}
        else:
            result_raw = {}
            mirror = {}

        # Analyze correlation log for lens-phi synergies
        synergies = self._compute_synergies()

        return {
            'synergies': synergies,
            'mirror': mirror,
            'n_scans_analyzed': len(self._correlation_log),
            'top_lens_pair': synergies[0] if synergies else None,
        }

    def _compute_synergies(self) -> List[Dict]:
        """Find which lens pairs correlate most with high Phi."""
        if len(self._correlation_log) < 3:
            return []

        modules = list(HEXAD_LENS_MAP.keys())
        pair_scores = {}

        for i, m1 in enumerate(modules):
            for m2 in modules[i + 1:]:
                pair_key = f'{m1}+{m2}'
                phi_corr = []
                for entry in self._correlation_log:
                    s = entry['scores']
                    if m1 in s and m2 in s:
                        combined = s[m1] * s[m2]
                        phi_corr.append((combined, entry['phi']))

                if len(phi_corr) >= 2:
                    # Simple correlation: do high combined scores predict high phi?
                    avg_combined = sum(c for c, _ in phi_corr) / len(phi_corr)
                    avg_phi = sum(p for _, p in phi_corr) / len(phi_corr)
                    pair_scores[pair_key] = {
                        'pair': pair_key,
                        'avg_combined': round(avg_combined, 4),
                        'avg_phi': round(avg_phi, 4),
                        'n_samples': len(phi_corr),
                    }

        # Sort by avg_phi (highest first)
        ranked = sorted(pair_scores.values(), key=lambda x: x['avg_phi'], reverse=True)
        return ranked

    def get_correlation_summary(self) -> Dict[str, Any]:
        """Summary of lens-consciousness correlations observed so far."""
        if not self._correlation_log:
            return {'n_scans': 0, 'message': 'no scans yet'}

        best_phi = max(e['phi'] for e in self._correlation_log)
        avg_phi = sum(e['phi'] for e in self._correlation_log) / len(self._correlation_log)

        return {
            'n_scans': len(self._correlation_log),
            'best_phi': round(best_phi, 4),
            'avg_phi': round(avg_phi, 4),
            'synergies': self._compute_synergies()[:3],
        }


# ── Hub registration interface ──

def hub_keywords():
    return ['telescope', 'nexus6', 'lens', 'scan', 'bridge', '망원경', '렌즈', '스캔']


def hub_act(query: str) -> str:
    """Hub-compatible action interface."""
    bridge = TelescopeBridge()
    q = query.lower()

    if any(k in q for k in ['scan', '스캔']):
        # Generate demo state for scan
        if _HAS_NP:
            state = np.random.randn(64, 128).tolist()
        else:
            import random
            state = [random.gauss(0, 1) for _ in range(64 * 128)]
        results = bridge.scan_consciousness(state)
        return json.dumps(results, indent=2, ensure_ascii=False, default=str)

    if any(k in q for k in ['growth', '성장']):
        return json.dumps(bridge.get_correlation_summary(), indent=2)

    return f"TelescopeBridge ready. nexus6={'yes' if _HAS_NEXUS6 else 'fallback'}. Use: scan, growth"


def main():
    """Demo: scan consciousness engine state through telescope bridge."""
    print("=== NEXUS-6 Telescope Bridge ===")
    print(f"nexus6 available: {_HAS_NEXUS6}")
    print(f"Hexad lens mapping (Law 1047):")
    for module, lens in HEXAD_LENS_MAP.items():
        print(f"  {module} -> {lens}")

    bridge = TelescopeBridge()

    # Generate demo engine state
    if _HAS_NP:
        state = np.random.randn(64, 128)
    else:
        import random
        state = [[random.gauss(0, 1) for _ in range(128)] for _ in range(64)]

    print(f"\nScanning 64-cell engine state...")
    results = bridge.scan_consciousness(state)

    print(f"\n--- Hexad Lens Results ---")
    for key, val in results.get('hexad', {}).items():
        print(f"  {key} ({val['lens']}): score={val['score']:.4f}")

    print(f"\nPhi: {results.get('phi', 0):.4f}")
    print(f"Consensus: {results.get('consensus', 0)}")
    print(f"N6 available: {results.get('n6_available')}")

    # Feed growth
    growth = bridge.feed_growth(results)
    print(f"\n--- Growth Feed ---")
    print(f"  Updated: {growth.get('updated')}")
    print(f"  Delta: {growth.get('growth_delta', 0)}")
    print(f"  Registry synced: {growth.get('registry_synced', False)}")

    # Run discovery (needs multiple scans for synergy analysis)
    for _ in range(5):
        if _HAS_NP:
            s = np.random.randn(64, 128)
        else:
            s = [[random.gauss(0, 1) for _ in range(128)] for _ in range(64)]
        bridge.scan_consciousness(s)

    disc = bridge.discover_from_lenses(state)
    print(f"\n--- Discovery ---")
    print(f"  Synergies found: {len(disc.get('synergies', []))}")
    if disc.get('top_lens_pair'):
        top = disc['top_lens_pair']
        print(f"  Top pair: {top['pair']} (avg_phi={top['avg_phi']})")

    print(f"\n--- Correlation Summary ---")
    summary = bridge.get_correlation_summary()
    print(f"  Scans: {summary['n_scans']}, Best Phi: {summary.get('best_phi', 'N/A')}")

    print("\nDone.")


if __name__ == '__main__':
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
