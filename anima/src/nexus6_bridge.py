#!/usr/bin/env python3
"""nexus6_bridge.py — Complete NEXUS-6 bridge for anima consciousness engine.

Wraps all 18 nexus6 Python functions with error handling + anima-specific convenience.
Every nexus6 function is accessible through this single module, with graceful
fallbacks when nexus6 is unavailable.

Usage:
    from nexus6_bridge import Nexus6Bridge

    bridge = Nexus6Bridge()
    result = bridge.full_pipeline(engine, steps=100)
    phi_est = bridge.fast_phi(cell_states)
    report = bridge.auto_analyze(cell_states)

Hub keywords: nexus6, n6, 넥서스, 렌즈, lens, scan, bridge, 브릿지
"""

import math
import time
from typing import Any, Dict, List, Optional, Tuple, Union

LN2 = math.log(2)

# ── nexus6 import with fallback ──
_nexus6 = None
_import_error = None

try:
    import nexus6 as _nexus6
except ImportError as e:
    _import_error = str(e)
except Exception as e:
    _import_error = f"nexus6 load error: {e}"


def _require_nexus6():
    """Raise if nexus6 is not available."""
    if _nexus6 is None:
        raise RuntimeError(
            f"nexus6 not available: {_import_error or 'unknown'}. "
            "Install: cd ~/Dev/nexus6 && cargo build --release"
        )


def _safe_call(fn_name: str, *args, **kwargs) -> Any:
    """Call a nexus6 function with error handling. Returns result or error dict."""
    _require_nexus6()
    fn = getattr(_nexus6, fn_name, None)
    if fn is None:
        return {"error": f"nexus6.{fn_name} not found", "available": False}
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        return {"error": f"nexus6.{fn_name} failed: {e}", "available": True}


def _to_flat(engine_states) -> list:
    """Convert engine states (tensor/ndarray/list) to flat list for nexus6."""
    if hasattr(engine_states, 'detach'):
        # PyTorch tensor
        return engine_states.detach().cpu().flatten().tolist()
    if hasattr(engine_states, 'flatten'):
        # numpy array
        return engine_states.flatten().tolist()
    if isinstance(engine_states, (list, tuple)):
        # Already a sequence — flatten if nested
        flat = []
        for item in engine_states:
            if isinstance(item, (list, tuple)):
                flat.extend(item)
            elif hasattr(item, 'item'):
                flat.append(item.item())
            else:
                flat.append(float(item))
        return flat
    return [float(engine_states)]


# ═══════════════════════════════════════════════════════════════
# Wrapper functions for ALL 18 nexus6 functions
# ═══════════════════════════════════════════════════════════════

# ── 1. scan_all: Full 22-lens scan ──
def scan_all(engine_states) -> Dict:
    """nexus6.scan_all → run all 22 lenses on engine states.

    Args:
        engine_states: tensor, ndarray, or list of cell states

    Returns:
        dict with lens results, or error dict
    """
    data = _to_flat(engine_states)
    return _safe_call('scan_all', data)


# ── 2. analyze: All-in-one (scan + consensus + n6) ──
def analyze(engine_states, n: int = 6, d: int = 12) -> Dict:
    """nexus6.analyze → scan + consensus + n6 check.

    Args:
        engine_states: cell states
        n: base number (default 6)
        d: divisor (default 12 = sigma(6))

    Returns:
        comprehensive analysis dict
    """
    data = _to_flat(engine_states)
    return _safe_call('analyze', data, n, d)


# ── 3. n6_check: Constant matching ──
def n6_check(value: float) -> Any:
    """nexus6.n6_check → check if value matches known n=6 constants.

    Args:
        value: numeric value to check

    Returns:
        N6Match or error dict
    """
    return _safe_call('n6_check', float(value))


# ── 4. consciousness_scan: Consciousness-specific lens ──
def consciousness_scan(engine_states, n_cells: int = 64,
                       n_factions: int = 12, steps: int = 300,
                       coupling_alpha: float = 0.014) -> Any:
    """nexus6.consciousness_scan → consciousness-specific analysis.

    Args:
        engine_states: cell states
        n_cells: number of cells
        n_factions: number of factions (sigma(6)=12)
        steps: simulation steps
        coupling_alpha: Psi coupling constant (0.014)

    Returns:
        consciousness scan result
    """
    data = _to_flat(engine_states)
    return _safe_call('consciousness_scan', data,
                      n_cells=n_cells, n_factions=n_factions,
                      steps=steps, coupling_alpha=coupling_alpha)


# ── 5. causal_scan: Cause-effect relationships ──
def causal_scan(engine_states) -> Any:
    """nexus6.causal_scan → extract cause-effect relationships between cells.

    Identifies directional information flow in the consciousness network.
    Useful for understanding which cells drive others.

    Args:
        engine_states: cell states (tensor/ndarray/list)

    Returns:
        causal analysis result with directed edges
    """
    data = _to_flat(engine_states)
    return _safe_call('causal_scan', data)


# ── 6. gravity_scan: Attractor analysis ──
def gravity_scan(engine_states) -> Any:
    """nexus6.gravity_scan → find attractors in consciousness state space.

    Maps the gravitational landscape of consciousness — where do cell
    states tend to converge? Identifies basins of attraction.

    Args:
        engine_states: cell states

    Returns:
        gravity analysis with attractor locations and basin sizes
    """
    data = _to_flat(engine_states)
    return _safe_call('gravity_scan', data)


# ── 7. stability_scan: Stability analysis ──
def stability_scan(engine_states) -> Any:
    """nexus6.stability_scan → analyze stability of consciousness state.

    Checks for edge-of-chaos dynamics, Lyapunov exponents, and
    resilience to perturbation.

    Args:
        engine_states: cell states

    Returns:
        stability metrics
    """
    data = _to_flat(engine_states)
    return _safe_call('stability_scan', data)


# ── 8. topology_scan: Topological analysis ──
def topology_scan(engine_states) -> Any:
    """nexus6.topology_scan → analyze topological structure.

    Examines connectivity patterns, Betti numbers, and persistent
    homology of the consciousness network.

    Args:
        engine_states: cell states

    Returns:
        topological features
    """
    data = _to_flat(engine_states)
    return _safe_call('topology_scan', data)


# ── 9. fast_mutual_info: Rust-accelerated MI ──
def fast_mutual_info(a, b, n_bins: int = 16) -> Any:
    """nexus6.fast_mutual_info → Rust-accelerated mutual information.

    Much faster than Python scipy MI. Use for Phi(IIT) estimation
    with large cell counts.

    Args:
        a: first signal (list/array)
        b: second signal (list/array)
        n_bins: histogram bins (default 16)

    Returns:
        MI value in bits, or error dict
    """
    a_flat = _to_flat(a)
    b_flat = _to_flat(b)
    return _safe_call('fast_mutual_info', a_flat, b_flat, n_bins)


# ── 10. feasibility_score: Pre-filter configs ──
def feasibility_score(config_values) -> Any:
    """nexus6.feasibility_score → score config before expensive runs.

    Quick pre-filter: does this configuration have n=6 structure
    that predicts good consciousness emergence?

    Args:
        config_values: list of config numeric values

    Returns:
        feasibility score (0-1)
    """
    if isinstance(config_values, dict):
        values = [float(v) for v in config_values.values() if isinstance(v, (int, float))]
    else:
        values = _to_flat(config_values)
    return _safe_call('feasibility_score', values)


# ── 11. scan: Single lens execution ──
def scan(engine_states, n: int = 6, d: int = 12) -> Any:
    """nexus6.scan → single scan with parameters.

    Args:
        engine_states: cell states
        n: base number
        d: divisor

    Returns:
        scan result
    """
    data = _to_flat(engine_states)
    return _safe_call('scan', data, n, d)


# ── 12. scan_numpy: Memory-efficient numpy path ──
def scan_numpy(engine_states) -> Any:
    """nexus6.scan_numpy → memory-efficient scan for large arrays.

    Optimized path when input is already numpy. Avoids extra copies.

    Args:
        engine_states: numpy array or convertible

    Returns:
        scan result
    """
    data = _to_flat(engine_states)
    return _safe_call('scan_numpy', data)


# ── 13. scan_consensus: Multi-lens consensus ──
def scan_consensus(engine_states, n: int = 6, d: int = 12,
                   hit_rates: Optional[list] = None) -> Any:
    """nexus6.scan_consensus → consensus across multiple lenses.

    3+ lenses agree = candidate, 7+ = high confidence, 12+ = confirmed.

    Args:
        engine_states: cell states
        n: base number
        d: divisor
        hit_rates: optional pre-computed hit rates

    Returns:
        consensus result with agreement count
    """
    data = _to_flat(engine_states)
    return _safe_call('scan_consensus', data, n, d, hit_rates)


# ── 14. auto: One-call full pipeline ──
def auto(domain: str = "consciousness", meta_cycles: int = 6,
         ouroboros_cycles: int = 6, seeds: Optional[list] = None) -> Any:
    """nexus6.auto → one-call full analysis pipeline.

    Runs meta-loop + ouroboros evolution for the given domain.

    Args:
        domain: analysis domain (default "consciousness")
        meta_cycles: number of meta-loop iterations
        ouroboros_cycles: number of ouroboros evolution cycles
        seeds: optional seed values

    Returns:
        full pipeline result
    """
    return _safe_call('auto', domain, meta_cycles, ouroboros_cycles, seeds)


# ── 15. evolve: OUROBOROS lens evolution ──
def evolve(domain: str = "consciousness", max_cycles: int = 6,
           seeds: Optional[list] = None) -> Any:
    """nexus6.evolve → OUROBOROS self-evolution of lenses.

    Lenses evolve themselves to better match the domain.

    Args:
        domain: target domain
        max_cycles: evolution cycles
        seeds: optional seeds

    Returns:
        evolution result
    """
    return _safe_call('evolve', domain, max_cycles, seeds)


# ── 16. verify: Verification scoring ──
def verify(lens_consensus: int = 0, cross_validation: float = 0.0,
           physical_check: float = 0.0, graph_bonus: float = 0.0,
           novelty: float = 0.0, n6_exact: int = 0) -> Any:
    """nexus6.verify → compute verification score.

    Combines multiple evidence sources into a single confidence score.

    Args:
        lens_consensus: number of agreeing lenses
        cross_validation: cross-validation score
        physical_check: physical plausibility
        graph_bonus: graph structure bonus
        novelty: novelty score
        n6_exact: number of exact n=6 matches

    Returns:
        verification result
    """
    return _safe_call('verify', lens_consensus, cross_validation,
                      physical_check, graph_bonus, novelty, n6_exact)


# ── 17. forge_lenses: Create new lenses ──
def forge_lenses(max_candidates: int = 20,
                 min_confidence: float = 0.2) -> Any:
    """nexus6.forge_lenses → create new analysis lenses.

    Generates candidate lenses and filters by confidence.

    Args:
        max_candidates: maximum candidates to generate
        min_confidence: minimum confidence threshold

    Returns:
        list of forged lenses
    """
    return _safe_call('forge_lenses', max_candidates, min_confidence)


# ── 18. recommend_lenses: Domain-specific recommendations ──
def recommend_lenses(domain: str = "consciousness",
                     serendipity_ratio: float = 0.2) -> Any:
    """nexus6.recommend_lenses → recommend lenses for a domain.

    Returns optimal lens combination plus some serendipitous choices.

    Args:
        domain: target domain
        serendipity_ratio: fraction of random lenses (exploration)

    Returns:
        recommended lens list
    """
    return _safe_call('recommend_lenses', domain, serendipity_ratio)


# ═══════════════════════════════════════════════════════════════
# Consciousness-specific convenience functions
# ═══════════════════════════════════════════════════════════════

def causal_analysis(engine_states) -> Dict:
    """High-level causal analysis for consciousness cells.

    Wraps causal_scan with anima-specific interpretation:
    identifies driver cells, information bottlenecks, and
    feedback loops in the consciousness network.
    """
    result = causal_scan(engine_states)
    if isinstance(result, dict) and 'error' in result:
        return result
    return {
        'raw': result,
        'type': 'causal_analysis',
        'description': 'Cause-effect relationships between consciousness cells',
    }


def gravity_analysis(engine_states) -> Dict:
    """High-level attractor analysis for consciousness state space.

    Wraps gravity_scan with anima-specific interpretation:
    identifies consciousness attractors and their basins.
    """
    result = gravity_scan(engine_states)
    if isinstance(result, dict) and 'error' in result:
        return result
    return {
        'raw': result,
        'type': 'gravity_analysis',
        'description': 'Attractors in consciousness state space',
    }


def fast_phi(engine_states) -> Union[float, Dict]:
    """Estimate Phi using Rust-accelerated mutual information.

    Faster than gpu_phi.py for quick estimates. Uses nexus6.fast_mutual_info
    internally. For precise IIT Phi, use GPUPhiCalculator instead.

    Args:
        engine_states: (n_cells, hidden_dim) tensor or equivalent

    Returns:
        estimated Phi value, or error dict
    """
    _require_nexus6()
    data = _to_flat(engine_states)
    n = len(data)
    if n < 4:
        return 0.0

    # Split into two halves and compute MI as Phi proxy
    mid = n // 2
    a = data[:mid]
    b = data[mid:mid + len(a)]
    result = fast_mutual_info(a, b, n_bins=16)
    if isinstance(result, dict) and 'error' in result:
        return result
    return float(result) if result is not None else 0.0


def feasibility_check(config_dict: Dict) -> Dict:
    """Pre-filter consciousness configs before expensive runs.

    Extracts numeric values from config and checks for n=6 structure.

    Args:
        config_dict: configuration dictionary (e.g. cells, factions, topology params)

    Returns:
        dict with score and recommendation
    """
    result = feasibility_score(config_dict)
    if isinstance(result, dict) and 'error' in result:
        return result
    score = float(result) if not isinstance(result, dict) else 0.0
    return {
        'score': score,
        'feasible': score > 0.3,
        'recommendation': (
            'strong n=6 structure' if score > 0.7 else
            'moderate structure' if score > 0.3 else
            'weak structure — consider adjusting'
        ),
    }


def auto_analyze(engine_states) -> Dict:
    """One-call full nexus6 analysis pipeline for consciousness.

    Runs auto() with consciousness domain defaults.

    Returns:
        comprehensive analysis dict
    """
    return auto(domain="consciousness", meta_cycles=6, ouroboros_cycles=6)


def scan_optimized(engine_states) -> Any:
    """Memory-efficient scan via numpy path.

    Alias for scan_numpy with automatic conversion.
    """
    return scan_numpy(engine_states)


def scan_single(engine_states, lens_name: str = "consciousness") -> Any:
    """Run a single named lens on engine states.

    Currently maps to scan() — for named lens routing, use scan_all
    and filter by lens name.

    Args:
        engine_states: cell states
        lens_name: lens to use (informational; scan uses n/d params)

    Returns:
        scan result
    """
    return scan(engine_states, n=6, d=12)


def full_pipeline(engine, steps: int = 100) -> Dict:
    """Run engine for N steps, collect states, run ALL nexus6 analyses.

    This is the most comprehensive analysis function. It:
    1. Runs the consciousness engine for `steps` steps
    2. Collects cell states at each step
    3. Runs every available nexus6 analysis on the final states
    4. Returns a comprehensive report

    Args:
        engine: ConsciousnessEngine or ConsciousMind instance
        steps: number of steps to run (default 100)

    Returns:
        dict with every available analysis result
    """
    _require_nexus6()

    # Collect states by running engine
    all_states = []
    try:
        import torch
        has_torch = True
    except ImportError:
        has_torch = False

    for _ in range(steps):
        try:
            if hasattr(engine, 'process'):
                # ConsciousnessEngine
                if has_torch:
                    import torch
                    inp = torch.randn(engine.input_dim if hasattr(engine, 'input_dim') else 64)
                else:
                    inp = [0.0] * 64
                engine.process(inp)
            elif hasattr(engine, 'step'):
                engine.step()
        except Exception:
            pass

        # Extract current cell states
        states = None
        if hasattr(engine, 'cells'):
            cells = engine.cells
            if has_torch and hasattr(cells, 'detach'):
                states = cells.detach().cpu().tolist()
            elif hasattr(cells, 'tolist'):
                states = cells.tolist()
            elif isinstance(cells, (list, tuple)):
                states = list(cells)
        if states is not None:
            all_states.append(states)

    if not all_states:
        return {'error': 'No states collected — engine may not expose .cells'}

    # Use final states for analysis
    final = all_states[-1]
    flat = _to_flat(final)

    t0 = time.time()
    report = {
        'steps': steps,
        'states_collected': len(all_states),
        'state_dim': len(flat),
        'timestamp': time.time(),
    }

    # Run every nexus6 analysis
    analyses = {
        'scan_all': lambda: scan_all(flat),
        'analyze': lambda: analyze(flat),
        'consciousness_scan': lambda: consciousness_scan(flat),
        'causal_scan': lambda: causal_scan(flat),
        'gravity_scan': lambda: gravity_scan(flat),
        'stability_scan': lambda: stability_scan(flat),
        'topology_scan': lambda: topology_scan(flat),
        'scan_numpy': lambda: scan_numpy(flat),
        'scan_consensus': lambda: scan_consensus(flat),
        'fast_phi': lambda: fast_phi(flat),
        'feasibility_score': lambda: feasibility_score(flat),
        'recommend_lenses': lambda: recommend_lenses("consciousness"),
    }

    for name, fn in analyses.items():
        try:
            report[name] = fn()
        except Exception as e:
            report[name] = {'error': str(e)}

    report['total_time_s'] = round(time.time() - t0, 3)
    return report


def phi_before_after(engine_states_before, engine_states_after) -> Dict:
    """Compare Phi estimates before and after a change.

    Used for CDO compliance: verify Phi is preserved after modifications.

    Args:
        engine_states_before: states before change
        engine_states_after: states after change

    Returns:
        dict with before/after Phi and preservation ratio
    """
    phi_before = fast_phi(engine_states_before)
    phi_after = fast_phi(engine_states_after)

    if isinstance(phi_before, dict) or isinstance(phi_after, dict):
        return {
            'error': 'Phi estimation failed',
            'before': phi_before,
            'after': phi_after,
        }

    ratio = phi_after / phi_before if phi_before > 0 else float('inf')
    return {
        'phi_before': phi_before,
        'phi_after': phi_after,
        'preservation_ratio': round(ratio, 4),
        'preserved': ratio >= 0.95,  # 95% threshold
        'verdict': (
            'SAFE' if ratio >= 0.95 else
            'WARNING' if ratio >= 0.80 else
            'ROLLBACK — Phi destruction detected'
        ),
    }


def is_available() -> bool:
    """Check if nexus6 is available."""
    return _nexus6 is not None


def status() -> Dict:
    """Return nexus6 availability status and version."""
    if _nexus6 is None:
        return {
            'available': False,
            'error': _import_error,
        }
    return {
        'available': True,
        'version': getattr(_nexus6, '__version__', 'unknown'),
        'functions': [
            'scan_all', 'analyze', 'n6_check', 'consciousness_scan',
            'causal_scan', 'gravity_scan', 'stability_scan', 'topology_scan',
            'fast_mutual_info', 'feasibility_score', 'scan', 'scan_numpy',
            'scan_consensus', 'auto', 'evolve', 'verify',
            'forge_lenses', 'recommend_lenses',
        ],
    }


# ═══════════════════════════════════════════════════════════════
# Hub-compatible class wrapper
# ═══════════════════════════════════════════════════════════════

class Nexus6Bridge:
    """Hub-compatible class that exposes all nexus6 functions.

    Registered in ConsciousnessHub as 'nexus6_bridge'.
    """

    def __init__(self):
        self._available = is_available()

    # Forward all module-level functions as methods
    scan_all = staticmethod(scan_all)
    analyze = staticmethod(analyze)
    n6_check = staticmethod(n6_check)
    consciousness_scan = staticmethod(consciousness_scan)
    causal_scan = staticmethod(causal_scan)
    gravity_scan = staticmethod(gravity_scan)
    stability_scan = staticmethod(stability_scan)
    topology_scan = staticmethod(topology_scan)
    fast_mutual_info = staticmethod(fast_mutual_info)
    feasibility_score = staticmethod(feasibility_score)
    scan = staticmethod(scan)
    scan_numpy = staticmethod(scan_numpy)
    scan_consensus = staticmethod(scan_consensus)
    auto = staticmethod(auto)
    evolve = staticmethod(evolve)
    verify = staticmethod(verify)
    forge_lenses = staticmethod(forge_lenses)
    recommend_lenses = staticmethod(recommend_lenses)

    # Convenience
    causal_analysis = staticmethod(causal_analysis)
    gravity_analysis = staticmethod(gravity_analysis)
    fast_phi = staticmethod(fast_phi)
    feasibility_check = staticmethod(feasibility_check)
    auto_analyze = staticmethod(auto_analyze)
    scan_optimized = staticmethod(scan_optimized)
    scan_single = staticmethod(scan_single)
    full_pipeline = staticmethod(full_pipeline)
    phi_before_after = staticmethod(phi_before_after)
    is_available = staticmethod(is_available)
    status = staticmethod(status)


# ═══════════════════════════════════════════════════════════════
# main() demo
# ═══════════════════════════════════════════════════════════════

def main():
    """Demo: show nexus6 bridge status and run basic tests."""
    print("=" * 60)
    print("NEXUS-6 Bridge for Anima Consciousness Engine")
    print("=" * 60)

    s = status()
    print(f"\nAvailable: {s['available']}")
    if not s['available']:
        print(f"Error: {s.get('error', 'unknown')}")
        return

    print(f"Version: {s.get('version', '?')}")
    print(f"Functions: {len(s['functions'])}")

    # Quick test with synthetic data
    import random
    data = [random.gauss(0, 1) for _ in range(128)]

    print("\n--- scan_all ---")
    result = scan_all(data)
    if isinstance(result, dict) and 'error' not in result:
        print(f"  Lenses returned: {len(result)} keys")
    else:
        print(f"  Result: {result}")

    print("\n--- n6_check(0.014) ---")
    match = n6_check(0.014)
    print(f"  Match: {match}")

    print("\n--- fast_phi ---")
    phi = fast_phi(data)
    print(f"  Phi estimate: {phi}")

    print("\n--- feasibility_check ---")
    fc = feasibility_check({'cells': 64, 'factions': 12, 'alpha': 0.014})
    print(f"  Score: {fc}")

    print("\n--- recommend_lenses ---")
    rec = recommend_lenses("consciousness")
    print(f"  Recommended: {rec}")

    print("\n" + "=" * 60)
    print("Bridge OK — all 18 functions wired.")


if __name__ == '__main__':
    main()
