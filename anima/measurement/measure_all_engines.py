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


import torch.nn.functional as F

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10



def rust_phi(states_tensor):
    """Rust PhiCalculator from tensor [n_cells, dim]."""
    h = states_tensor.abs().float() if states_tensor.is_complex() else states_tensor.float()
    states = h.detach().cpu().numpy().astype(np.float32)
    if states.shape[0] < 2:
        return 0.0
    phi, _ = phi_rs.compute_phi(states, 16)
    return phi


def granger_from_states(h):
    """Granger causality proxy from hidden states tensor [nc, dim]."""
    nc = h.shape[0]
    if nc < 2:
        return 0.0
    hr = h.abs().float() if h.is_complex() else h.float()
    total = 0.0
    n_samples = min(50, nc * nc)
    for _ in range(n_samples):
        i, j = np.random.randint(0, nc), np.random.randint(0, nc)
        if i == j:
            continue
        total += abs(F.cosine_similarity(hr[i:i+1], hr[j:j+1]).item())
    return total * nc * nc / max(n_samples, 1)


def quick_iq_from_states(eng, nc, dim, steps=10):
    """IQ proxy: run extra steps, measure memory retention + logic."""
    memory_score = 0
    logic_score = 0
    h_before = extract_states(eng, nc)
    if h_before is None:
        return 60  # baseline

    # Memory: run steps, check how much state changes
    for _ in range(steps):
        try:
            eng.step()
        except Exception:
            break
    h_after = extract_states(eng, nc)
    if h_after is None:
        return 60

    hr_b = h_before.abs().float() if h_before.is_complex() else h_before.float()
    hr_a = h_after.abs().float() if h_after.is_complex() else h_after.float()

    # Memory retention: similarity between before/after
    for i in range(min(5, nc)):
        sim = F.cosine_similarity(hr_b[i:i+1], hr_a[i:i+1]).item()
        if sim > 0.1:
            memory_score += 1

    # Logic: coherence across cells
    for i in range(min(5, nc - 1)):
        sim = F.cosine_similarity(hr_a[i:i+1], hr_a[i+1:i+2]).item()
        if sim > 0.05:
            logic_score += 1

    raw = (memory_score / 5 * 0.5 + logic_score / 5 * 0.5)
    iq = 100 + 15 * (raw - 0.5) / 0.15
    return round(max(40, min(160, iq)))


def measure_hive_from_cls(engine_cls, nc, dim, steps):
    """Hive: run 2 engines, connect, measure Φ/IQ delta."""
    try:
        eng_a = engine_cls(nc, dim)
    except TypeError:
        try:
            eng_a = engine_cls(nc=nc, dim=dim)
        except TypeError:
            eng_a = engine_cls(nc, dim=dim)
    try:
        eng_b = engine_cls(nc, dim)
    except TypeError:
        try:
            eng_b = engine_cls(nc=nc, dim=dim)
        except TypeError:
            eng_b = engine_cls(nc, dim=dim)

    # Solo run
    for _ in range(steps):
        try:
            eng_a.step()
            eng_b.step()
        except Exception:
            break

    h_a = extract_states(eng_a, nc)
    if h_a is None:
        return {'phi_delta': 0, 'iq_delta': 0}
    solo_phi = rust_phi(h_a)
    solo_iq = quick_iq_from_states(eng_a, nc, dim, 5)

    # Connect: blend states between a and b
    h_b = extract_states(eng_b, nc)
    if h_b is not None:
        hr_a = h_a.abs().float() if h_a.is_complex() else h_a.float()
        hr_b = h_b.abs().float() if h_b.is_complex() else h_b.float()
        blended = 0.8 * hr_a + 0.2 * hr_b
        # Write back blended states
        _write_states(eng_a, blended, nc)
        for _ in range(50):
            try:
                eng_a.step()
            except Exception:
                break

    h_hive = extract_states(eng_a, nc)
    if h_hive is None:
        return {'phi_delta': 0, 'iq_delta': 0}
    hive_phi = rust_phi(h_hive)
    hive_iq = quick_iq_from_states(eng_a, nc, dim, 5)

    phi_d = (hive_phi - solo_phi) / max(solo_phi, 1e-8) * 100
    return {
        'phi_delta': round(phi_d, 1),
        'iq_delta': hive_iq - solo_iq,
    }


def _write_states(eng, h, nc):
    """Try to write blended states back to engine."""
    for attr in ['pos', 'state', 'states', 'hidden', 'hiddens', 'h']:
        if hasattr(eng, attr):
            val = getattr(eng, attr)
            if isinstance(val, torch.Tensor) and val.dim() == 2 and val.shape[0] == nc:
                with torch.no_grad():
                    setattr(eng, attr, h[:val.shape[0], :val.shape[1]])
                return
    # Try pos component
    if hasattr(eng, 'pos'):
        val = eng.pos
        if isinstance(val, torch.Tensor) and val.shape[0] == nc:
            with torch.no_grad():
                eng.pos = h[:val.shape[0], :val.shape[1]]


def extract_states(eng, nc):
    """Extract hidden states tensor from engine."""
    for attr in ['pos', 'state', 'states', 'hidden', 'hiddens', 'h',
                  'uv_state', 'boundary', 'info', 'fiber', 'voice',
                  'expression', 'features']:
        if hasattr(eng, attr):
            val = getattr(eng, attr)
            if isinstance(val, torch.Tensor) and val.dim() == 2 and val.shape[0] == nc:
                return val

    parts = []
    for attr in ['pos', 'vel', 'phase', 'amplitude', 'charge', 'spin',
                  'momentum', 'energy', 'activation',
                  # physics: wavefunction, fields, order parameters
                  'psi_re', 'psi_im', 'delta_re', 'delta_im',
                  'N1', 'N2', 'radius', 'displacement',
                  # emergent: reaction-diffusion, sandpile, excitable media
                  'u', 'v', 'w', 'heights', 'temp', 'velocity',
                  'omega', 'theta', 'genome', 'constructor', 'fitness',
                  # geometric: hyperbolic, symplectic, fiber bundle, calabi-yau
                  'z', 'q', 'p', 'fiber', 'base_angle',
                  'z_re', 'z_im',
                  # extreme: holographic, neuromorphic, consciousness field
                  'boundary', 'V', 'phi', 'pi',
                  # evolution/music: host/symbiont, pitch, epigenome
                  'host_state', 'symbiont_state', 'hybrid_state', 'vigor',
                  'pitch', 'pitch_class', 'voice', 'deviation', 'motion',
                  'epigenome', 'histone', 'epi_memory']:
        if hasattr(eng, attr):
            val = getattr(eng, attr)
            if isinstance(val, torch.Tensor):
                if val.dim() == 1 and val.shape[0] == nc:
                    parts.append(val.unsqueeze(1))
                elif val.dim() == 2 and val.shape[0] == nc:
                    parts.append(val)
                elif val.dim() >= 3 and val.shape[0] == nc:
                    # Flatten higher dims (e.g., CalabiYau z_re [nc, 3, d])
                    parts.append(val.reshape(nc, -1))
    if parts:
        return torch.cat(parts, dim=1)
    return None


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

    h = extract_states(eng, nc)
    if h is None:
        return 0.0, None, eng, time.time() - t0

    phi = rust_phi(h)
    return phi, h, eng, time.time() - t0


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

    mode = 'quick' if args.quick else 'full'
    print(f"═══ 전체 도메인 엔진 측정 ({NC}c, {STEPS} steps, {mode}) ═══\n")

    if args.quick:
        print(f"{'Domain':<12} {'Engine':<35} {'Φ(IIT)':>8} {'Time':>6}")
        print('─' * 70)
    else:
        print(f"{'Domain':<10} {'Engine':<30} {'Φ(IIT)':>8} {'Grangr':>8} {'IQ':>4} {'Hive_Φ':>8} {'Hive_IQ':>8} {'Time':>6}")
        print('─' * 95)

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
                phi, h, eng, elapsed = run_engine(cls, NC, DIM, STEPS)

                result = {
                    'domain': domain, 'engine': eng_name,
                    'phi': round(phi, 4), 'cells': NC, 'steps': STEPS,
                    'granger': 0, 'iq': 60, 'hive_phi_delta': 0, 'hive_iq_delta': 0,
                    'time': round(elapsed, 1),
                }

                if h is not None and not args.quick:
                    # Granger
                    result['granger'] = round(granger_from_states(h), 1)
                    # IQ
                    result['iq'] = quick_iq_from_states(eng, NC, DIM, 10)
                    # Hive
                    hive = measure_hive_from_cls(cls, NC, DIM, STEPS)
                    result['hive_phi_delta'] = hive['phi_delta']
                    result['hive_iq_delta'] = hive['iq_delta']

                if args.quick:
                    status = f"{phi:>8.3f}" if h is not None else "  NODATA"
                    print(f"{domain:<12} {eng_name:<35} {status} {elapsed:>5.1f}s")
                else:
                    if h is not None:
                        print(f"{domain:<10} {eng_name:<30} {phi:>8.3f} {result['granger']:>8.0f} {result['iq']:>4} {result['hive_phi_delta']:>+7.1f}% {result['hive_iq_delta']:>+7} {elapsed:>5.1f}s")
                    else:
                        print(f"{domain:<10} {eng_name:<30}   NODATA {'—':>8} {'—':>4} {'—':>8} {'—':>8} {elapsed:>5.1f}s")

                all_results.append(result)
                total_engines += 1
            except Exception as e:
                print(f"{domain:<12} {eng_name:<35}    ERROR: {str(e)[:40]}")
                total_failed += 1

        sys.stdout.flush()

    # Sort by Φ descending
    all_results.sort(key=lambda x: x['phi'], reverse=True)

    print(f"\n{'─' * 95}")
    print(f"측정 완료: {total_engines} engines, {total_failed} failed\n")

    if all_results:
        print("═══ TOP 20 by Φ(IIT) ═══")
        header = f"{'#':>3} {'Engine':<35} {'Domain':<10} {'Φ(IIT)':>8}"
        if not args.quick:
            header += f" {'Grangr':>8} {'IQ':>4} {'Hive_Φ':>8} {'Hive_IQ':>8}"
        print(header)
        print('─' * (len(header) + 5))
        for i, r in enumerate(all_results[:20], 1):
            line = f"{i:>3} {r['engine']:<35} {r['domain']:<10} {r['phi']:>8.3f}"
            if not args.quick:
                line += f" {r['granger']:>8.0f} {r['iq']:>4} {r['hive_phi_delta']:>+7.1f}% {r['hive_iq_delta']:>+7}"
            print(line)

    Path('data').mkdir(exist_ok=True)
    out = f'data/measure_all_engines_{NC}c.json'
    Path(out).write_text(json.dumps(all_results, indent=2))
    print(f"\n[saved] {len(all_results)} engines → {out}")


if __name__ == '__main__':
    main()
