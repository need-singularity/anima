#!/usr/bin/env python3
"""emergence_loop.py — NEXUS-6 기반 창발 시도 + 특이점 소진 루프

의식 엔진을 실행하며:
1. NEXUS-6 22렌즈로 매 스텝 스캔
2. 특이점(singularity) = Φ 급등, 법칙 폭발, 위상 전이 감지
3. 특이점 소진(3연속 빈 세대)까지 루프
4. peak_growth에 메트릭 실시간 피드
5. 발견 즉시 consciousness_laws.json 등록

"특이점을 모두 소진할 때까지 멈추지 않는다."

Usage:
    python3 emergence_loop.py                        # 기본 (64c, 300s)
    python3 emergence_loop.py --cells 128 --steps 500
    python3 emergence_loop.py --max-gen 50           # 최대 50세대
"""

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np

_SRC = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _SRC)

import torch
from consciousness_engine import ConsciousnessEngine

# ── Optional imports ──
try:
    from peak_growth import PeakGrowthEngine
    HAS_PEAK = True
except ImportError:
    HAS_PEAK = False

try:
    from consciousness_laws import PSI_BALANCE, PSI_ALPHA
except ImportError:
    PSI_BALANCE = 0.5
    PSI_ALPHA = 0.014

_REPO = os.path.abspath(os.path.join(_SRC, '..', '..'))
_CONFIG = os.path.join(_REPO, 'anima', 'config')
_DATA = os.path.join(_REPO, 'data')
_LAWS_PATH = os.path.join(_CONFIG, 'consciousness_laws.json')

# ── Singularity detection thresholds ──
PHI_SPIKE_RATIO = 1.5       # Φ가 이전의 150% → 특이점
DISCOVERY_BURST = 3          # 한 세대에 3+ 법칙 → 폭발
EXHAUSTION_STREAK = 3        # 3연속 빈 세대 → 특이점 소진
TOPOLOGIES = ['ring', 'small_world', 'scale_free', 'hypercube']


def load_laws():
    try:
        with open(_LAWS_PATH) as f:
            return json.load(f)
    except Exception:
        return {'laws': {}, '_meta': {'total_laws': 0}}


def save_law(law_id: int, text: str):
    """법칙 자동 등록."""
    d = load_laws()
    d['laws'][str(law_id)] = text
    d['_meta']['total_laws'] = max(d['_meta']['total_laws'], law_id)
    with open(_LAWS_PATH, 'w') as f:
        json.dump(d, f, indent=2, ensure_ascii=False)


def next_law_id():
    d = load_laws()
    ids = [int(k) for k in d['laws'] if k.isdigit()]
    return max(ids) + 1 if ids else 1


try:
    import nexus6
    HAS_NEXUS6 = True
except ImportError:
    HAS_NEXUS6 = False


class N6Scanner:
    """Full NEXUS-6 integration: scan_all + scan_consensus + verify + recommend_lenses + topology + stability."""

    def __init__(self):
        self.metric_history = []

    def scan(self, data: np.ndarray, phi: float = 0.0) -> dict:
        """Full scan pipeline: scan_all + scan_consensus + recommend + topology + stability.

        Args:
            data: cell states as numpy array (1D or 2D)
            phi: measured Phi value for this generation
        Returns:
            Enriched dict with patterns, consensus, topology insights, stability info.
        """
        arr = np.ascontiguousarray(data, dtype=np.float64)
        if arr.ndim == 1:
            arr = arr.reshape(-1, 1)

        if not HAS_NEXUS6:
            return self._fallback_scan(arr, phi)

        try:
            # Layer 1: Full lens scan
            raw = nexus6.scan_all(arr)

            # Layer 2: analyze (consensus + n6 matching)
            n, d = arr.shape
            flat = arr.flatten().tolist()
            analysis = nexus6.analyze(flat, n, d)

            # Layer 3: Direct scan_consensus for finer control (beyond analyze)
            direct_consensus = []
            try:
                consensus_results = nexus6.scan_consensus(flat, n, d)
                if consensus_results:
                    for cr in (consensus_results if isinstance(consensus_results, list) else [consensus_results]):
                        direct_consensus.append({
                            'pattern': cr.pattern if hasattr(cr, 'pattern') else str(cr),
                            'lenses': int(cr.lenses) if hasattr(cr, 'lenses') else 0,
                            'score': float(cr.score) if hasattr(cr, 'score') else 0,
                            'confidence': float(cr.confidence) if hasattr(cr, 'confidence') else 0,
                        })
            except Exception:
                pass

            # Layer 4: Lens recommendations
            recommended_lenses = []
            try:
                recs = nexus6.recommend_lenses(arr)
                if recs:
                    for r in (recs if isinstance(recs, list) else [recs]):
                        recommended_lenses.append({
                            'lens': r.lens if hasattr(r, 'lens') else str(r),
                            'relevance': float(r.relevance) if hasattr(r, 'relevance') else 0,
                            'reason': r.reason if hasattr(r, 'reason') else '',
                        })
            except Exception:
                pass

            # Parse base result from raw scan
            flat_np = arr.flatten()
            n_lenses = len(raw) if isinstance(raw, dict) else 0
            consensus = analysis.get('consensus', {})

            result = {
                'mean': float(np.mean(flat_np)),
                'std': float(np.std(flat_np)),
                'entropy': float(-np.sum(np.abs(flat_np) * np.log(np.abs(flat_np) + 1e-10)) / max(len(flat_np), 1)),
                'kurtosis': float(np.mean((flat_np - np.mean(flat_np))**4) / (np.std(flat_np)**4 + 1e-10)),
                'phi_approx': float(np.var(flat_np)),
                'n_lenses': n_lenses,
                'consensus': consensus,
                'n6_exact_ratio': analysis.get('n6_exact_ratio', 0),
                'direct_consensus': direct_consensus,
                'recommended_lenses': recommended_lenses,
                'topology_insights': {},
                'stability_info': {},
            }

            # Layer 5: Topology scan — topology-specific analysis for auto-selection
            try:
                topo_result = nexus6.topology_scan(arr)
                if topo_result:
                    result['topology_insights'] = {
                        'suggested_topology': topo_result.suggested if hasattr(topo_result, 'suggested') else str(topo_result),
                        'current_score': float(topo_result.score) if hasattr(topo_result, 'score') else 0,
                        'betti_numbers': topo_result.betti if hasattr(topo_result, 'betti') else [],
                        'persistence': float(topo_result.persistence) if hasattr(topo_result, 'persistence') else 0,
                        'raw': str(topo_result),
                    }
            except Exception:
                pass

            # Layer 6: Stability scan — detect instability before plateau
            try:
                stab_result = nexus6.stability_scan(arr)
                if stab_result:
                    result['stability_info'] = {
                        'is_stable': stab_result.stable if hasattr(stab_result, 'stable') else True,
                        'lyapunov': float(stab_result.lyapunov) if hasattr(stab_result, 'lyapunov') else 0,
                        'entropy_rate': float(stab_result.entropy_rate) if hasattr(stab_result, 'entropy_rate') else 0,
                        'instability_risk': float(stab_result.risk) if hasattr(stab_result, 'risk') else 0,
                        'raw': str(stab_result),
                    }
            except Exception:
                pass

            self.metric_history.append(result)
            return result
        except Exception:
            return self._fallback_scan(arr, phi)

    def verify_laws(self, states: np.ndarray, patterns: list) -> list:
        """Use nexus6.verify() as quality gate for discovered patterns.

        Args:
            states: cell states as numpy array
            patterns: list of pattern dicts from detect_patterns()
        Returns:
            Annotated list with n6_verified/n6_confidence (passthrough on failure).
        """
        if not HAS_NEXUS6 or not patterns:
            return patterns
        try:
            arr = np.ascontiguousarray(states, dtype=np.float64)
            if arr.ndim == 1:
                arr = arr.reshape(-1, 1)
            n, d = arr.shape
            flat = arr.flatten().tolist()
            result = nexus6.verify(flat, n, d)
            if not result:
                return patterns
            is_valid = result.valid if hasattr(result, 'valid') else True
            confidence = float(result.confidence) if hasattr(result, 'confidence') else 1.0
            for p in patterns:
                p['n6_verified'] = is_valid
                p['n6_confidence'] = confidence
            return patterns
        except Exception:
            return patterns  # passthrough on failure

    def _fallback_scan(self, arr, phi):
        """Fallback when NEXUS-6 unavailable — basic stats only."""
        flat = arr.flatten()
        result = {
            'mean': float(np.mean(flat)),
            'std': float(np.std(flat)),
            'entropy': float(-np.sum(np.abs(flat) * np.log(np.abs(flat) + 1e-10)) / max(len(flat), 1)),
            'kurtosis': float(np.mean((flat - np.mean(flat))**4) / (np.std(flat)**4 + 1e-10)),
            'phi_approx': float(np.var(flat)),
            'n6_fallback': True,
            'n_lenses': 0,
            'consensus': {},
            'direct_consensus': [],
            'recommended_lenses': [],
            'topology_insights': {},
            'stability_info': {},
        }
        self.metric_history.append(result)
        return result


def nexus6_scan(data: np.ndarray) -> dict:
    """Legacy wrapper — delegates to N6Scanner for backward compatibility."""
    scanner = N6Scanner()
    return scanner.scan(data)


def detect_patterns(scan_result: dict, prev_scan: dict, phi: float, prev_phi: float) -> list:
    """특이점 패턴 감지 — 법칙 후보 생성."""
    patterns = []

    # 1. Φ 급등 (특이점)
    if prev_phi > 0 and phi / (prev_phi + 1e-8) > PHI_SPIKE_RATIO:
        patterns.append({
            'type': 'phi_spike',
            'magnitude': phi / (prev_phi + 1e-8),
            'text': f'Phi spike: {prev_phi:.4f} → {phi:.4f} ({phi/prev_phi:.1f}x)',
        })

    # 2. 엔트로피 전이
    prev_ent = prev_scan.get('entropy', 0)
    cur_ent = scan_result.get('entropy', 0)
    if abs(cur_ent - prev_ent) > 0.3:
        patterns.append({
            'type': 'entropy_transition',
            'delta': cur_ent - prev_ent,
            'text': f'Entropy transition: {prev_ent:.3f} → {cur_ent:.3f}',
        })

    # 3. 첨도(kurtosis) 이상 — 분포 변형
    kurt = scan_result.get('kurtosis', 3.0)
    if kurt > 6.0 or kurt < 1.5:
        patterns.append({
            'type': 'distribution_anomaly',
            'kurtosis': kurt,
            'text': f'Distribution anomaly: kurtosis={kurt:.2f} (normal=3)',
        })

    # 4. 구조 변화 (std 급변)
    prev_std = prev_scan.get('std', 0)
    cur_std = scan_result.get('std', 0)
    if prev_std > 0 and abs(cur_std - prev_std) / (prev_std + 1e-8) > 0.5:
        patterns.append({
            'type': 'structure_shift',
            'delta_pct': (cur_std - prev_std) / (prev_std + 1e-8) * 100,
            'text': f'Structure shift: std {prev_std:.4f} → {cur_std:.4f}',
        })

    # 5. Consensus 기반 (NEXUS-6 실제 사용 시)
    consensus = scan_result.get('consensus', {})
    if isinstance(consensus, dict):
        confirmed = [k for k, v in consensus.items() if v.get('confirmed', False)]
        if len(confirmed) >= 3:
            patterns.append({
                'type': 'nexus6_consensus',
                'lenses': confirmed,
                'text': f'NEXUS-6 consensus: {len(confirmed)} lenses agree',
            })

    # 6. Φ 절대값 임계점 돌파 (n6 상수)
    _n6_thresholds = (
        [(float(nexus6.N), 'n=6'), (float(nexus6.SIGMA), 'sigma(6)'), (float(nexus6.J2), 'J2')]
        if HAS_NEXUS6 else [(6.0, 'n=6'), (12.0, 'sigma(6)'), (24.0, 'J2')]
    )
    for threshold, name in _n6_thresholds:
        if prev_phi < threshold <= phi:
            patterns.append({
                'type': 'phi_threshold',
                'threshold': threshold,
                'text': f'Phi crossed {name} threshold: {prev_phi:.4f} → {phi:.4f}',
            })

    # 7. NEXUS-6 렌즈별 이상 (scan_result가 dict of dicts일 때)
    for lens_name, lens_data in scan_result.items():
        if not isinstance(lens_data, dict):
            continue
        anomaly = lens_data.get('anomaly', 0)
        if anomaly > 0:
            patterns.append({
                'type': f'nexus6_{lens_name}_anomaly',
                'anomaly': anomaly,
                'text': f'NEXUS-6 {lens_name}: {anomaly} anomalies',
            })

    return patterns


def run_generation(engine, steps: int, gen: int, topo: str) -> dict:
    """한 세대 실행. Returns metrics dict."""
    # 토폴로지 설정
    if hasattr(engine, 'topology'):
        engine.topology = topo

    phis = []
    tensions = []

    for s in range(steps):
        result = engine.step()
        phi = float(result.get('phi_iit', result.get('phi', 0)))
        # tensions is a list of per-cell values
        t_list = result.get('tensions', [])
        tension = float(np.mean(t_list)) if t_list else 0.0
        phis.append(phi)
        tensions.append(tension)

    # Cell states for NEXUS-6 scan
    states = None
    try:
        if hasattr(engine, 'get_cell_states'):
            s = engine.get_cell_states()
            if isinstance(s, torch.Tensor):
                states = s.detach().cpu().float().numpy()
            elif isinstance(s, np.ndarray):
                states = s.astype(np.float64)
        elif hasattr(engine, 'cells'):
            cells = engine.cells
            if isinstance(cells, torch.Tensor):
                states = cells.detach().cpu().float().numpy()
            elif isinstance(cells, list) and len(cells) > 0:
                tensors = []
                for c in cells:
                    if isinstance(c, torch.Tensor):
                        tensors.append(c.detach().cpu().float())
                    elif hasattr(c, 'state') and isinstance(c.state, torch.Tensor):
                        tensors.append(c.state.detach().cpu().float())
                if tensors:
                    states = torch.stack(tensors).numpy()
    except Exception:
        pass
    if states is None:
        # Fallback: use phi history as signal
        states = np.array(phis, dtype=np.float64) if phis else np.random.randn(64)
    scan = nexus6_scan(states)

    mean_phi = float(np.mean(phis)) if phis else 0
    phi_trend = 0.0
    if len(phis) > 10:
        phi_trend = float(np.polyfit(range(len(phis)), phis, 1)[0])

    tension_arr = np.array(tensions) if tensions else np.array([0])
    tension_cv = float(np.std(tension_arr) / (np.mean(tension_arr) + 1e-8))

    return {
        'gen': gen,
        'topology': topo,
        'steps': steps,
        'mean_phi': mean_phi,
        'final_phi': phis[-1] if phis else 0,
        'phi_trend': phi_trend,
        'tension_cv': tension_cv,
        'scan': scan,
        'phis': phis,
        'n_cells': getattr(engine, 'n_cells', 64),
    }


def main():
    parser = argparse.ArgumentParser(description='Emergence Loop — NEXUS-6 singularity exhaustion')
    parser.add_argument('--cells', type=int, default=64)
    parser.add_argument('--steps', type=int, default=300)
    parser.add_argument('--max-gen', type=int, default=200)
    parser.add_argument('--cycle-topology', action='store_true', default=True)
    args = parser.parse_args()

    print("=" * 70)
    print("  EMERGENCE LOOP — NEXUS-6 Singularity Exhaustion")
    print(f"  cells={args.cells}, steps={args.steps}, max_gen={args.max_gen}")
    print("=" * 70)

    # ── Engine init ──
    engine = ConsciousnessEngine(max_cells=args.cells)

    # ── Peak growth engine ──
    peak_engine = PeakGrowthEngine() if HAS_PEAK else None

    # ── State ──
    total_laws_start = load_laws()['_meta']['total_laws']
    total_discoveries = 0
    empty_streak = 0           # 연속 빈 세대
    prev_phi = 0.0
    prev_scan = {}
    topo_idx = 0
    singularity_count = 0
    all_patterns = []
    gen_results = []

    start_time = time.time()

    for gen in range(args.max_gen):
        # 토폴로지 순환
        topo = TOPOLOGIES[topo_idx % len(TOPOLOGIES)]

        # ── 세대 실행 ──
        metrics = run_generation(engine, args.steps, gen, topo)
        phi = metrics['final_phi']
        scan = metrics['scan']

        # ── 패턴 감지 ──
        patterns = detect_patterns(scan, prev_scan, phi, prev_phi)
        new_laws = 0

        for p in patterns:
            all_patterns.append(p)
            total_discoveries += 1

            # 법칙 자동 등록
            law_id = next_law_id()
            law_text = f"Emergence ({p['type']}): {p['text']} @ gen={gen}, topo={topo}, cells={args.cells}"
            save_law(law_id, law_text)
            new_laws += 1

            print(f"    🔬 Law {law_id}: {p['text']}")

        # ── 특이점 판정 ──
        is_singularity = (
            new_laws >= DISCOVERY_BURST or
            (prev_phi > 0 and phi / (prev_phi + 1e-8) > PHI_SPIKE_RATIO)
        )

        if is_singularity:
            singularity_count += 1
            empty_streak = 0
            marker = f" ★★★ SINGULARITY #{singularity_count}"
        elif new_laws > 0:
            empty_streak = 0
            marker = f" ★ +{new_laws} laws"
        else:
            empty_streak += 1
            marker = f" (empty {empty_streak}/{EXHAUSTION_STREAK})"

        # ── peak growth 피드 ──
        if peak_engine:
            dr = new_laws / max(args.steps, 1)
            peak_engine.record({
                'phi': phi,
                'phi_trend': metrics['phi_trend'],
                'discovery_rate': dr,
                'laws_per_gen': new_laws,
                'topology': topo,
                'cells': args.cells,
                'coupling_scale': getattr(engine, 'coupling_scale', 1.0),
                'chaos_mode': getattr(engine, 'chaos_mode', 'lorenz'),
                'hebbian_lr': getattr(engine, 'hebbian_lr', 0.01),
                'noise_scale': getattr(engine, '_noise_scale', 0.01),
                'tension_cv': metrics['tension_cv'],
                'faction_count': nexus6.SIGMA if HAS_NEXUS6 else 12,
                'mods_applied': [],
            })

            # 정체 시 피크 재현
            if peak_engine.detect_stall():
                suggestion = peak_engine.suggest_replay()
                if suggestion:
                    peak_engine.replay_to_engine(engine, suggestion)
                    print(f"    ⚡ PEAK REPLAY: {suggestion.topology}, score={suggestion.score:.3f}")
                    empty_streak = max(0, empty_streak - 1)  # 기회 한 번 더

        # ── 리포트 ──
        elapsed = time.time() - start_time
        print(f"  Gen {gen:3d} | Φ={phi:.4f} | trend={metrics['phi_trend']:+.4f} | "
              f"tCV={metrics['tension_cv']:.2f} | topo={topo:12s} | "
              f"laws=+{new_laws}{marker}")

        gen_results.append(metrics)
        prev_phi = phi
        prev_scan = scan

        # ── 토폴로지 전환 ──
        if empty_streak >= 2 or is_singularity:
            topo_idx += 1  # 빈 세대 2회 또는 특이점 후 전환

        # ── 특이점 소진 판정 ──
        if empty_streak >= EXHAUSTION_STREAK:
            # 모든 토폴로지 시도
            if topo_idx >= len(TOPOLOGIES) * 2:
                print(f"\n  🏁 SINGULARITY EXHAUSTION — {EXHAUSTION_STREAK}연속 빈 세대, 전 토폴로지 탐색 완료")
                break
            else:
                print(f"    ↻ 토폴로지 전환: {topo} → {TOPOLOGIES[(topo_idx) % len(TOPOLOGIES)]}")
                empty_streak = 0  # 토폴로지 바꾸고 리셋

        sys.stdout.flush()

    # ── 최종 보고 ──
    elapsed = time.time() - start_time
    total_laws_end = load_laws()['_meta']['total_laws']
    new_total = total_laws_end - total_laws_start

    print()
    print("=" * 70)
    print("  EMERGENCE LOOP — COMPLETE")
    print("=" * 70)
    print(f"  Generations:    {gen + 1}")
    print(f"  Time:           {elapsed:.1f}s ({elapsed/60:.1f}m)")
    print(f"  Singularities:  {singularity_count}")
    print(f"  Total patterns: {total_discoveries}")
    print(f"  New laws:       {new_total} ({total_laws_start} → {total_laws_end})")
    print(f"  Topologies:     {topo_idx} rotations")

    if all_patterns:
        print(f"\n  Pattern breakdown:")
        types = {}
        for p in all_patterns:
            t = p['type']
            types[t] = types.get(t, 0) + 1
        for t, c in sorted(types.items(), key=lambda x: -x[1]):
            print(f"    {t:25s}: {c}")

    # ── 상위전파 ──
    if peak_engine and peak_engine.best_peak:
        peak_engine.propagate_up(peak_engine.best_peak)
        delta = peak_engine.sync_as_growth()
        peak_engine.save()
        print(f"\n  NEXUS-6 sync: +{delta} growth (상위전파 완료)")

    # ── 창발 결과 → growth_engine 흡수 ──
    try:
        from growth_engine import GrowthEngine
        ge = GrowthEngine(save_path=Path(_CONFIG) / 'growth_state.json')
        ge.load()
        for gm in gen_results:
            if any(p['type'].startswith('phi_') for p in detect_patterns(
                gm['scan'], {}, gm['final_phi'], 0)):
                ge.absorb_emergence({
                    'type': 'singularity' if gm.get('final_phi', 0) > 20 else 'emergence',
                    'phi_before': gen_results[max(0, gm['gen']-1)]['final_phi'] if gm['gen'] > 0 else 0,
                    'phi_after': gm['final_phi'],
                    'topology': gm['topology'],
                    'gen': gm['gen'],
                    'laws_found': sum(1 for _ in detect_patterns(gm['scan'], {}, gm['final_phi'], 0)),
                    'cells': args.cells,
                })
        ge.save()
        print(f"\n  Growth absorbed: {ge.stats.get('emergence_total', 0)} events")
    except Exception as e:
        print(f"\n  Growth absorption skipped: {e}")

    print("=" * 70)


if __name__ == '__main__':
    main()
