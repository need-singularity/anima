#!/usr/bin/env python3
"""measure_all_engines.py — 전체 엔진 통합 측정 (Rust PhiCalculator)

모든 bench_*_engines.py + bench_v8_*.py 엔진을 Rust PhiCalculator로 측정.
각 엔진 클래스의 hidden states를 추출 → phi_rs.compute_phi() 호출.

Usage:
  python3 measure_all_engines.py                    # 256c 전체
  python3 measure_all_engines.py --cells 1024       # 1024c
  python3 measure_all_engines.py --cells 512 --quick  # Φ만 (IQ/Hive 생략)
  python3 measure_all_engines.py --only physics thermo  # 특정 도메인만
"""

import torch
import numpy as np
import time
import json
import sys
import os
import argparse
import importlib
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ['OMP_NUM_THREADS'] = '1'

import phi_rs

DIM, HIDDEN = 64, 128


def rust_phi(states_tensor):
    """Rust PhiCalculator from tensor [n_cells, dim]."""
    h = states_tensor.abs().float() if states_tensor.is_complex() else states_tensor.float()
    states = h.detach().cpu().numpy().astype(np.float32)
    if states.shape[0] < 2:
        return 0.0
    phi, _ = phi_rs.compute_phi(states, 16)
    return phi


def run_engine(engine_cls, nc, dim, steps):
    """Run an engine class and return (phi, hidden_states_tensor, time)."""
    t0 = time.time()
    try:
        eng = engine_cls(nc, dim)
    except TypeError:
        try:
            eng = engine_cls(nc=nc, dim=dim)
        except TypeError:
            eng = engine_cls(nc, dim=dim)

    for _ in range(steps):
        try:
            eng.step()
        except Exception:
            break

    # Extract hidden states — try common patterns
    h = None
    for attr in ['pos', 'state', 'states', 'hidden', 'hiddens', 'h']:
        if hasattr(eng, attr):
            val = getattr(eng, attr)
            if isinstance(val, torch.Tensor) and val.dim() == 2 and val.shape[0] == nc:
                h = val
                break

    if h is None:
        # Try combining pos+vel or state components
        parts = []
        for attr in ['pos', 'vel', 'phase', 'amplitude', 'charge', 'spin',
                      'momentum', 'energy', 'activation']:
            if hasattr(eng, attr):
                val = getattr(eng, attr)
                if isinstance(val, torch.Tensor):
                    if val.dim() == 1 and val.shape[0] == nc:
                        parts.append(val.unsqueeze(1))
                    elif val.dim() == 2 and val.shape[0] == nc:
                        parts.append(val)
        if parts:
            h = torch.cat(parts, dim=1)

    if h is None:
        return 0.0, None, time.time() - t0

    phi = rust_phi(h)
    return phi, h, time.time() - t0


# ═══ Engine Registry ═══

BENCH_FILES = {
    'physics': ('bench_physics_engines', [
        'PlasmaEngine', 'SuperconductorEngine', 'LaserEngine',
        'BlackHoleEngine', 'CrystalEngine', 'SuperfluidEngine',
    ]),
    'thermo': ('bench_thermo_engines', [
        'CarnotCycleEngine', 'MaxwellDemonEngine', 'DissipativeStructureEngine',
        'FreeEnergyPrincipleEngine', 'HeatDeathResistanceEngine', 'BoltzmannBrainEngine',
    ]),
    'emergent': ('bench_emergent_engines', [
        'ReactionDiffusionEngine', 'SandpileCascadeEngine', 'FlockingVortexEngine',
        'PercolationEngine', 'SynchronizationChimeraEngine', 'SelfReplicatingEngine',
        'PatternFormationEngine', 'ExcitableMediaEngine',
    ]),
    'geometric': ('bench_geometric_engines', [
        'HyperbolicEngine', 'FiberBundleEngine', 'RicciFlowEngine',
        'SymplecticEngine', 'CalabiYauEngine', 'KnotInvariantEngine',
    ]),
    'extreme': ('bench_extreme_engines', [
        'HolographicUniverseEngine', 'TopologicalInsulatorEngine', 'TimeCrystalEngine',
        'NeuromorphicSpikeEngine', 'MembraneComputingEngine', 'TensorNetworkEngine',
        'AnyonicBraidingEngine', 'ConsciousnessFieldEngine',
    ]),
    'evolution': ('bench_evolution_engines', [
        'CambrianExplosionEngine', 'SymbiogenesisEngine', 'EcosystemEngine',
        'ImmuneSystemEngine', 'MorphogenesisEngine', 'NeuralCrestEngine',
    ]),
    'music': ('bench_music_engines', [
        'PolyrhythmEngine', 'HarmonicSeriesEngine', 'CounterpointEngine',
        'JazzImprovisationEngine', 'GamelanEngine', 'DrumCircleEngine',
    ]),
    'evobio': ('bench_evobio_engines', [
        'MutationRateEngine', 'SpeciationEngine', 'HorizontalGeneTransferEngine',
        'EpigeneticsEngine', 'RedQueenEngine', 'PunctuatedEquilibriumEngine',
        'SexualSelectionEngine', 'KinSelectionEngine',
    ]),
    'network': ('bench_network_engines', [
        'ScaleFreeEngine', 'RichClubEngine', 'ModularNetworkEngine',
        'MultiplexEngine', 'TemporalNetworkEngine', 'AdaptiveNetworkEngine',
    ]),
    'new': ('bench_new_engines', [
        'GraphNeuralEngine', 'EnergyBasedEngine', 'CellularAutomatonEngine',
        'DiffusionEngine', 'SpinGlassEngine', 'FluidDynamicsEngine',
        'GeneticEngine', 'SwarmEngine',
    ]),
    'info': ('bench_info_engines', [
        'MaximumEntropyEngine', 'MinimumDescriptionLengthEngine',
        'PredictiveInformationEngine', 'InformationBottleneckEngine',
        'CausalEmergenceEngine', 'IntegratedInfoDecompositionEngine',
        'ChannelCapacityEngine', 'KolmogorovStructureEngine',
    ]),
    'social': ('bench_social_engines', [
        'PrisonerDilemmaEngine', 'VotingDynamicsEngine', 'MarketDynamicsEngine',
        'LanguageGameEngine', 'CulturalEvolutionEngine', 'StigmergyEngine',
    ]),
    'complexity': ('bench_complexity_engines', [
        'TuringMachineEngine', 'CellularAutomatonEngine', 'LambdaCalculusEngine',
        'GameOfLifeEngine', 'StrangeLoopEngine', 'GoedelIncompletenessEngine',
    ]),
    'algebra': ('bench_algebra_engines', []),  # function-based, handled separately
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cells', type=int, default=256)
    parser.add_argument('--steps', type=int, default=300)
    parser.add_argument('--quick', action='store_true', help='Φ only, skip IQ/Hive')
    parser.add_argument('--only', nargs='+', help='Domains to measure (e.g., physics thermo)')
    args = parser.parse_args()

    NC, STEPS = args.cells, args.steps
    domains = args.only if args.only else list(BENCH_FILES.keys())

    print(f"═══ 전체 도메인 엔진 측정 ({NC}c, {STEPS} steps) ═══\n")
    print(f"{'Domain':<12} {'Engine':<35} {'Φ(IIT)':>8} {'Time':>6}")
    print('─' * 70)

    all_results = []
    total_engines = 0
    total_failed = 0

    for domain in domains:
        if domain not in BENCH_FILES:
            print(f"  ⚠ Unknown domain: {domain}")
            continue

        module_name, engine_names = BENCH_FILES[domain]
        if not engine_names:
            continue

        try:
            mod = importlib.import_module(module_name)
        except ImportError as e:
            print(f"  ⚠ {domain}: import failed — {e}")
            continue

        for eng_name in engine_names:
            torch.manual_seed(42)
            np.random.seed(42)

            cls = getattr(mod, eng_name, None)
            if cls is None:
                print(f"  ⚠ {eng_name} not found in {module_name}")
                total_failed += 1
                continue

            try:
                phi, h, elapsed = run_engine(cls, NC, DIM, STEPS)
                status = f"{phi:>8.3f}" if h is not None else "  NODATA"
                print(f"{domain:<12} {eng_name:<35} {status} {elapsed:>5.1f}s")
                all_results.append({
                    'domain': domain,
                    'engine': eng_name,
                    'phi': round(phi, 4),
                    'cells': NC,
                    'steps': STEPS,
                    'time': round(elapsed, 1),
                })
                total_engines += 1
            except Exception as e:
                print(f"{domain:<12} {eng_name:<35}    ERROR: {str(e)[:40]}")
                total_failed += 1

        sys.stdout.flush()

    # Sort by Φ descending
    all_results.sort(key=lambda x: x['phi'], reverse=True)

    print(f"\n{'─' * 70}")
    print(f"측정 완료: {total_engines} engines, {total_failed} failed\n")

    if all_results:
        print("═══ TOP 20 by Φ(IIT) ═══")
        print(f"{'#':>3} {'Engine':<35} {'Domain':<12} {'Φ(IIT)':>8}")
        print('─' * 62)
        for i, r in enumerate(all_results[:20], 1):
            print(f"{i:>3} {r['engine']:<35} {r['domain']:<12} {r['phi']:>8.3f}")

    Path('data').mkdir(exist_ok=True)
    out = f'data/measure_all_engines_{NC}c.json'
    Path(out).write_text(json.dumps(all_results, indent=2))
    print(f"\n[saved] {len(all_results)} engines → {out}")


if __name__ == '__main__':
    main()
