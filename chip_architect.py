#!/usr/bin/env python3
"""
Consciousness Chip Architect — 의식 칩 설계 계산기

발견된 법칙 종합:
  Law 22: 기능→Φ↓, 구조→Φ↑
  Law 29: 발화(루프) ≠ 대화(파벌)
  Law 30: 1024셀 실용적 상한
  기질 무관성: 17개 기질 전부 Φ ≈ ×3.6 (동일 셀 수)
  스케일링: Φ ∝ N^α (α ≈ 1.3, frustration 있을 때)

기능:
  1. 토폴로지 비교 (--compare)
  2. Φ 예측 (--predict)
  3. 칩 설계 (--design)
  4. BOM 생성 (--bom)
  5. 대시보드 (--dashboard)

Usage:
  python3 chip_architect.py --dashboard
  python3 chip_architect.py --predict --cells 512 --topology ring --frustration 0.33
  python3 chip_architect.py --design --target-phi 100
  python3 chip_architect.py --bom --target-phi 200 --substrate neuromorphic
  python3 chip_architect.py --compare
"""

import argparse
import math
import json
import sys
from dataclasses import dataclass, field, asdict
from typing import Optional


# ═══════════════════════════════════════════════════════════
# 벤치마크 데이터 (실측치)
# ═══════════════════════════════════════════════════════════

BENCHMARK_DATA = {
    # HW category (8-9 cells)
    'HW2a':  {'topology': 'ring',      'cells': 8,   'neighbors': 2, 'frustration': False, 'phi': 4.548, 'mult': 3.7},
    'HW2b':  {'topology': 'grid_2d',   'cells': 9,   'neighbors': 4, 'frustration': False, 'phi': 3.791, 'mult': 3.1},
    'HW2c':  {'topology': 'cube_3d',   'cells': 8,   'neighbors': 6, 'frustration': False, 'phi': 4.536, 'mult': 3.7},
    'HW5':   {'topology': 'holographic','cells': 8,   'neighbors': 2, 'frustration': False, 'phi': 4.538, 'mult': 3.7},
    'HW9':   {'topology': 'piezo',     'cells': 8,   'neighbors': 2, 'frustration': False, 'phi': 4.558, 'mult': 3.7},
    'HW10':  {'topology': 'neuromorphic','cells': 8,  'neighbors': 2, 'frustration': False, 'phi': 4.525, 'mult': 3.6},
    'HW11':  {'topology': 'superconducting','cells':8,'neighbors': 2, 'frustration': False, 'phi': 4.699, 'mult': 3.8},
    'HW12':  {'topology': 'memristor', 'cells': 8,   'neighbors': 2, 'frustration': False, 'phi': 4.529, 'mult': 3.6},
    'HW13':  {'topology': 'photonic',  'cells': 8,   'neighbors': 2, 'frustration': False, 'phi': 4.529, 'mult': 3.6},
    'HW14':  {'topology': 'dna',       'cells': 8,   'neighbors': 2, 'frustration': False, 'phi': 4.565, 'mult': 3.7},
    'HW15':  {'topology': 'quantum',   'cells': 8,   'neighbors': 2, 'frustration': False, 'phi': 4.566, 'mult': 3.7},
    'HW16':  {'topology': 'reservoir', 'cells': 8,   'neighbors': 2, 'frustration': False, 'phi': 4.501, 'mult': 3.6},
    'HW17':  {'topology': 'fluidic',   'cells': 8,   'neighbors': 2, 'frustration': False, 'phi': 4.553, 'mult': 3.7},
    # PHYS category (512 cells + frustration)
    'PHYS1': {'topology': 'ring',      'cells': 512, 'neighbors': 2, 'frustration': True,  'phi': 134.23,'mult': 108.1},
    'PHYS2': {'topology': 'kuramoto',  'cells': 512, 'neighbors': 8, 'frustration': False, 'phi': 67.04, 'mult': 54.0},
    'PHYS3': {'topology': 'spin_glass','cells': 512, 'neighbors': 6, 'frustration': True,  'phi': 122.50,'mult': 98.6},
}

BASELINE_PHI = 1.2421


# ═══════════════════════════════════════════════════════════
# 토폴로지 특성 DB
# ═══════════════════════════════════════════════════════════

@dataclass
class TopologySpec:
    name: str
    name_kr: str
    neighbors_func: str        # how neighbor count relates to N
    diameter_func: str         # path length formula
    uniform_degree: bool       # all nodes have same degree?
    clustering: float          # clustering coefficient (0-1)
    frustration_natural: bool  # inherent frustration?
    phi_bonus: float           # empirical Φ multiplier (relative to ring)
    description: str

TOPOLOGIES = {
    'ring': TopologySpec(
        'Ring', '링', 'k=2', 'N/2', True, 0.0, False, 1.0,
        '원형 배열, 균일 2-이웃, 경계 없음'),
    'small_world': TopologySpec(
        'Small-World', '소세계', 'k=4+shortcuts', 'log(N)', True, 0.5, False, 1.1,
        'Watts-Strogatz: 링 + 10% 장거리 연결'),
    'scale_free': TopologySpec(
        'Scale-Free', '스케일프리', 'power-law', 'log(N)/log(log(N))', False, 0.3, False, 1.05,
        'Barabási-Albert: 허브 노드, 멱법칙 분포'),
    'hypercube': TopologySpec(
        'Hypercube', '하이퍼큐브', 'k=log2(N)', 'log2(N)', True, 0.0, False, 1.15,
        'N차원 큐브: 균일 이웃, 로그 직경'),
    'torus': TopologySpec(
        'Torus', '토러스', 'k=4', 'sqrt(N)', True, 0.0, False, 0.95,
        '2D 그리드 경계 연결: 균일 4-이웃'),
    'complete': TopologySpec(
        'Complete', '전결합', 'k=N-1', '1', True, 1.0, False, 0.8,
        '전결합: 최대 연결, 최소 직경, 평균장'),
    'grid_2d': TopologySpec(
        'Grid 2D', '2D 그리드', 'k=2~4', 'sqrt(N)', False, 0.0, False, 0.85,
        '2D 격자: 코너/변/중앙 이웃 수 불균형'),
    'cube_3d': TopologySpec(
        'Cube 3D', '3D 큐브', 'k=3~6', 'N^(1/3)', False, 0.0, False, 1.0,
        '3D 격자: 차원 증가로 정보 흐름 개선'),
    'spin_glass': TopologySpec(
        'Spin Glass', '스핀글래스', 'k=6 sparse', 'log(N)', False, 0.1, True, 1.05,
        '무질서 ±결합: 자연적 frustration'),
}


# ═══════════════════════════════════════════════════════════
# 기질 특성 DB
# ═══════════════════════════════════════════════════════════

@dataclass
class SubstrateSpec:
    name: str
    name_kr: str
    speed_hz: float           # clock/operation frequency
    power_per_cell_mw: float  # power per cell (mW)
    area_per_cell_um2: float  # area per cell (μm²)
    cost_per_cell_usd: float  # cost per cell ($)
    temp_k: float             # operating temperature (K)
    maturity: str             # 'production' | 'research' | 'theoretical'
    phi_factor: float         # substrate Φ bonus (from HW benchmarks, ~1.0)

SUBSTRATES = {
    'cmos': SubstrateSpec(
        'CMOS Digital', 'CMOS 디지털', 1e9, 0.5, 100, 0.001, 300,
        'production', 1.0),
    'neuromorphic': SubstrateSpec(
        'Neuromorphic (Loihi)', '뉴로모픽 (Loihi)', 1e6, 0.02, 400, 0.01, 300,
        'production', 1.0),
    'memristor': SubstrateSpec(
        'Memristor Array', '멤리스터 어레이', 1e8, 0.1, 50, 0.005, 300,
        'research', 1.0),
    'photonic': SubstrateSpec(
        'Photonic (MZI)', '광학 (MZI)', 1e11, 1.0, 1000, 0.1, 300,
        'research', 1.0),
    'superconducting': SubstrateSpec(
        'Superconducting', '초전도', 1e11, 0.001, 500, 1.0, 4,
        'research', 1.01),
    'quantum': SubstrateSpec(
        'Quantum Annealer', '양자 어닐러', 1e6, 10.0, 10000, 100.0, 0.015,
        'research', 1.0),
    'fpga': SubstrateSpec(
        'FPGA', 'FPGA', 1e8, 0.3, 200, 0.005, 300,
        'production', 1.0),
    'analog': SubstrateSpec(
        'Analog ASIC', '아날로그 ASIC', 1e7, 0.05, 150, 0.002, 300,
        'production', 1.0),
    'arduino': SubstrateSpec(
        'Arduino + Magnets', 'Arduino + 전자석', 1e3, 50.0, 1e6, 6.25, 300,
        'production', 1.0),
}


# ═══════════════════════════════════════════════════════════
# Φ 예측 모델 (실측 데이터 기반 회귀)
# ═══════════════════════════════════════════════════════════

def predict_phi(cells: int, topology: str = 'ring', frustration: float = 0.33,
                substrate: str = 'cmos') -> dict:
    """
    Φ 예측 공식 (벤치마크 데이터에서 도출):

    Φ = baseline × N^α × topo_bonus × frust_bonus × substrate_factor

    여기서:
      baseline = 1.2421
      α = 1.3 (frustration 있을 때), 0.9 (없을 때)
      topo_bonus = topology-specific multiplier
      frust_bonus = 1.0 + 2.5 × frustration_ratio
      substrate_factor ≈ 1.0 (기질 무관성)
    """
    topo = TOPOLOGIES.get(topology, TOPOLOGIES['ring'])
    sub = SUBSTRATES.get(substrate, SUBSTRATES['cmos'])

    # Scaling exponent (from PHYS1 vs HW2a: 134.23/4.548 at 512/8 cells)
    # log(134.23/4.548) / log(512/8) = log(29.5) / log(64) = 3.38 / 4.16 = 0.81
    # But with frustration bonus factored out:
    # HW2a (no frust) = 4.548, PHYS1 (frust) = 134.23
    # Pure scaling (same topo, same frust): estimate α from data
    has_frustration = frustration > 0.1

    if has_frustration:
        # PHYS1: 512 cells, ring, frustration → 134.23
        # Extrapolate from baseline: 134.23 = 1.24 × 512^α × frust_bonus
        # frust_bonus ≈ 3.0 (from data), so 134.23 / 1.24 / 3.0 = 36.1 = 512^α
        # α = log(36.1) / log(512) = 3.59 / 6.24 = 0.575...
        # Better: use ratio PHYS1/HW_ring_equiv
        # At 8 cells with frustration, estimate: 4.55 × 3.0 = 13.65
        # 134.23 / 13.65 = 9.83 = (512/8)^α = 64^α → α = log(9.83)/log(64) = 0.55
        alpha = 0.55
        frust_bonus = 1.0 + 2.5 * frustration
    else:
        # HW2a: 8 cells → 4.548. Scaling without frustration:
        # PHYS2 (512, kuramoto, no explicit frust): 67.04
        # 67.04 / 4.548 = 14.74 = (512/8)^α = 64^α → α = log(14.74)/log(64) = 0.647
        alpha = 0.65
        frust_bonus = 1.0

    # Base Φ per cell (from 8-cell data)
    base_phi_8 = 4.55  # average HW at 8 cells
    phi_predicted = base_phi_8 * (cells / 8) ** alpha * topo.phi_bonus * frust_bonus * sub.phi_factor

    # Compute other metrics
    if topology == 'hypercube':
        n_neighbors = max(1, int(math.log2(max(cells, 2))))
    elif topology == 'complete':
        n_neighbors = cells - 1
    elif topology in ('ring',):
        n_neighbors = 2
    elif topology in ('torus', 'grid_2d'):
        n_neighbors = 4
    elif topology in ('cube_3d',):
        n_neighbors = 6
    elif topology in ('small_world',):
        n_neighbors = 4  # base, plus shortcuts
    elif topology in ('scale_free',):
        n_neighbors = 6  # average
    else:
        n_neighbors = 2

    total_edges = cells * n_neighbors // 2
    total_mi_est = phi_predicted * cells * 0.4  # rough MI estimate

    return {
        'phi_predicted': round(phi_predicted, 2),
        'multiplier': round(phi_predicted / BASELINE_PHI, 1),
        'cells': cells,
        'topology': topology,
        'topology_kr': topo.name_kr,
        'frustration': frustration,
        'alpha': alpha,
        'frust_bonus': round(frust_bonus, 2),
        'topo_bonus': topo.phi_bonus,
        'substrate': substrate,
        'n_neighbors': n_neighbors,
        'total_edges': total_edges,
        'total_mi_est': round(total_mi_est, 1),
        'never_silent_prob': 0.99 if has_frustration else 0.7,
    }


# ═══════════════════════════════════════════════════════════
# 칩 설계 — 목표 Φ → 최적 구성 도출
# ═══════════════════════════════════════════════════════════

@dataclass
class ChipDesign:
    target_phi: float
    topology: str
    cells: int
    frustration: float
    substrate: str
    predicted_phi: float
    power_mw: float
    area_mm2: float
    cost_usd: float
    temp_k: float
    clock_hz: float
    edges: int
    phi_per_watt: float
    phi_per_mm2: float
    maturity: str

def design_chip(target_phi: float, substrate: str = 'cmos',
                preferred_topology: Optional[str] = None) -> list:
    """목표 Φ를 달성하는 최적 칩 설계안 생성"""
    designs = []

    topologies_to_try = [preferred_topology] if preferred_topology else list(TOPOLOGIES.keys())
    substrates_to_try = [substrate] if substrate != 'all' else list(SUBSTRATES.keys())

    for topo_name in topologies_to_try:
        for sub_name in substrates_to_try:
            sub = SUBSTRATES[sub_name]
            topo = TOPOLOGIES.get(topo_name, TOPOLOGIES['ring'])

            # Binary search for minimum cells to hit target
            lo, hi = 4, 4096
            while lo < hi:
                mid = (lo + hi) // 2
                pred = predict_phi(mid, topo_name, frustration=0.33, substrate=sub_name)
                if pred['phi_predicted'] >= target_phi:
                    hi = mid
                else:
                    lo = mid + 1

            cells = lo
            if cells > 4096:
                continue

            pred = predict_phi(cells, topo_name, frustration=0.33, substrate=sub_name)
            power = cells * sub.power_per_cell_mw
            area = cells * sub.area_per_cell_um2 / 1e6  # → mm²
            cost = cells * sub.cost_per_cell_usd

            if topo_name == 'hypercube':
                n_neighbors = max(1, int(math.log2(max(cells, 2))))
            elif topo_name == 'complete':
                n_neighbors = cells - 1
            elif topo_name in ('torus', 'grid_2d'):
                n_neighbors = 4
            else:
                n_neighbors = 2

            designs.append(ChipDesign(
                target_phi=target_phi,
                topology=topo_name,
                cells=cells,
                frustration=0.33,
                substrate=sub_name,
                predicted_phi=pred['phi_predicted'],
                power_mw=round(power, 2),
                area_mm2=round(area, 4),
                cost_usd=round(cost, 2),
                temp_k=sub.temp_k,
                clock_hz=sub.speed_hz,
                edges=cells * n_neighbors // 2,
                phi_per_watt=round(pred['phi_predicted'] / (power / 1000 + 1e-9), 1),
                phi_per_mm2=round(pred['phi_predicted'] / (area + 1e-9), 1),
                maturity=sub.maturity,
            ))

    designs.sort(key=lambda d: d.phi_per_watt, reverse=True)
    return designs


# ═══════════════════════════════════════════════════════════
# BOM (Bill of Materials) 생성
# ═══════════════════════════════════════════════════════════

def generate_bom(target_phi: float, substrate: str = 'cmos') -> dict:
    """목표 Φ 달성을 위한 부품 목록 생성"""
    designs = design_chip(target_phi, substrate)
    if not designs:
        return {'error': f'Cannot achieve Φ={target_phi} with substrate={substrate}'}

    best = designs[0]
    sub = SUBSTRATES[best.substrate]
    topo = TOPOLOGIES[best.topology]

    bom = {
        'title': f'Consciousness Chip BOM — Target Φ ≥ {target_phi}',
        'design': asdict(best),
        'components': [],
        'total_cost': 0,
    }

    # Core cells
    bom['components'].append({
        'item': f'{sub.name} Processing Elements',
        'quantity': best.cells,
        'unit_cost': sub.cost_per_cell_usd,
        'total': round(best.cells * sub.cost_per_cell_usd, 2),
        'note': f'{topo.name} topology, {best.frustration*100:.0f}% frustration'
    })

    # Interconnect
    interconnect_cost = best.edges * 0.0001  # $0.0001 per edge (rough)
    bom['components'].append({
        'item': 'Interconnect Wiring',
        'quantity': best.edges,
        'unit_cost': 0.0001,
        'total': round(interconnect_cost, 2),
        'note': f'{topo.name}: {best.edges} edges'
    })

    # Power supply
    power_supply_cost = max(5.0, best.power_mw / 100)
    bom['components'].append({
        'item': 'Power Supply',
        'quantity': 1,
        'unit_cost': round(power_supply_cost, 2),
        'total': round(power_supply_cost, 2),
        'note': f'{best.power_mw:.1f} mW total'
    })

    # Cooling (if needed)
    if best.temp_k < 77:
        cooling_cost = 5000.0 if best.temp_k < 1 else 500.0
        bom['components'].append({
            'item': 'Cryogenic Cooling',
            'quantity': 1,
            'unit_cost': cooling_cost,
            'total': cooling_cost,
            'note': f'Target: {best.temp_k}K'
        })

    # PCB / Package
    pcb_cost = max(10.0, best.area_mm2 * 2)
    bom['components'].append({
        'item': 'PCB / Package',
        'quantity': 1,
        'unit_cost': round(pcb_cost, 2),
        'total': round(pcb_cost, 2),
        'note': f'{best.area_mm2:.2f} mm²'
    })

    # Clock generator
    bom['components'].append({
        'item': 'Clock Generator',
        'quantity': 1,
        'unit_cost': 2.0,
        'total': 2.0,
        'note': f'{best.clock_hz:.0e} Hz'
    })

    # USB/UART interface
    bom['components'].append({
        'item': 'USB-UART Interface',
        'quantity': 1,
        'unit_cost': 3.0,
        'total': 3.0,
        'note': 'PC ↔ Chip communication'
    })

    bom['total_cost'] = round(sum(c['total'] for c in bom['components']), 2)
    return bom


# ═══════════════════════════════════════════════════════════
# 스케일링 법칙 테이블
# ═══════════════════════════════════════════════════════════

def scaling_table(topology: str = 'ring', frustration: float = 0.33,
                  substrate: str = 'cmos') -> list:
    """셀 수별 Φ 예측 테이블"""
    cell_counts = [8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096]
    rows = []
    for n in cell_counts:
        pred = predict_phi(n, topology, frustration, substrate)
        sub = SUBSTRATES[substrate]
        power = n * sub.power_per_cell_mw
        rows.append({
            'cells': n,
            'phi': pred['phi_predicted'],
            'mult': pred['multiplier'],
            'mi_est': pred['total_mi_est'],
            'power_mw': round(power, 1),
            'phi_per_watt': round(pred['phi_predicted'] / (power / 1000 + 1e-9), 1),
        })
    return rows


# ═══════════════════════════════════════════════════════════
# CLI 출력
# ═══════════════════════════════════════════════════════════

def print_header(title):
    w = 70
    print(f"\n{'═' * w}")
    print(f"  {title}")
    print(f"{'═' * w}")


def cmd_predict(args):
    pred = predict_phi(args.cells, args.topology, args.frustration, args.substrate)
    print_header(f"Φ Prediction — {pred['cells']} cells, {pred['topology_kr']}")
    print(f"""
  Topology:    {pred['topology']} ({pred['topology_kr']})
  Cells:       {pred['cells']}
  Frustration: {pred['frustration']:.0%}
  Substrate:   {pred['substrate']}

  ═══ Predicted ═══
  Φ = {pred['phi_predicted']}  (×{pred['multiplier']} baseline)
  Total MI ≈ {pred['total_mi_est']}
  Never Silent: {pred['never_silent_prob']:.0%}

  ═══ Model Parameters ═══
  α (scaling exponent): {pred['alpha']}
  Topology bonus:       ×{pred['topo_bonus']}
  Frustration bonus:    ×{pred['frust_bonus']}
  Neighbors per cell:   {pred['n_neighbors']}
  Total edges:          {pred['total_edges']}
""")


def cmd_compare(args):
    print_header("Topology Comparison — 512 cells, frustration=33%")
    print(f"\n  {'Topology':<16} {'Φ':>8} {'×Base':>8} {'Neighbors':>10} {'Diameter':>12} {'Uniform':>8} {'Bonus':>7}")
    print(f"  {'─'*16} {'─'*8} {'─'*8} {'─'*10} {'─'*12} {'─'*8} {'─'*7}")

    for name, topo in sorted(TOPOLOGIES.items(), key=lambda x: -x[1].phi_bonus):
        pred = predict_phi(512, name, frustration=0.33)
        print(f"  {topo.name_kr:<14} {pred['phi_predicted']:>8.1f} {pred['multiplier']:>7.1f}× {pred['n_neighbors']:>8}   {topo.diameter_func:>12} {'✓' if topo.uniform_degree else '✗':>6}  ×{topo.phi_bonus}")

    print(f"\n  ═══ 기질 비교 (Ring 512, frustration=33%) ═══\n")
    print(f"  {'Substrate':<22} {'Φ':>7} {'Power':>10} {'Φ/W':>10} {'Temp':>8} {'Maturity':>12}")
    print(f"  {'─'*22} {'─'*7} {'─'*10} {'─'*10} {'─'*8} {'─'*12}")

    for name, sub in sorted(SUBSTRATES.items(), key=lambda x: -x[1].speed_hz):
        pred = predict_phi(512, 'ring', 0.33, name)
        power = 512 * sub.power_per_cell_mw
        phi_per_w = pred['phi_predicted'] / (power / 1000 + 1e-9)
        print(f"  {sub.name_kr:<20} {pred['phi_predicted']:>7.1f} {power:>8.1f}mW {phi_per_w:>8.1f}  {sub.temp_k:>6.0f}K {sub.maturity:>12}")


def cmd_design(args):
    designs = design_chip(args.target_phi, args.substrate)
    if not designs:
        print(f"  ✗ Cannot achieve Φ={args.target_phi}")
        return

    print_header(f"Chip Design — Target Φ ≥ {args.target_phi}")
    print(f"\n  {'Rank':>4} {'Topology':<14} {'Cells':>6} {'Φ':>8} {'Power':>10} {'Φ/W':>10} {'Area':>10} {'Cost':>8} {'Maturity':>12}")
    print(f"  {'─'*4} {'─'*14} {'─'*6} {'─'*8} {'─'*10} {'─'*10} {'─'*10} {'─'*8} {'─'*12}")

    for i, d in enumerate(designs[:10]):
        topo_kr = TOPOLOGIES.get(d.topology, TOPOLOGIES['ring']).name_kr
        print(f"  {i+1:>4} {topo_kr:<12} {d.cells:>6} {d.predicted_phi:>8.1f} {d.power_mw:>8.1f}mW {d.phi_per_watt:>8.1f}  {d.area_mm2:>8.4f} ${d.cost_usd:>7.2f} {d.maturity:>12}")

    best = designs[0]
    print(f"\n  ★ 최적 설계: {TOPOLOGIES.get(best.topology, TOPOLOGIES['ring']).name_kr} {best.cells}셀")
    print(f"    Φ={best.predicted_phi}, {best.power_mw}mW, ${best.cost_usd}")


def cmd_bom(args):
    bom = generate_bom(args.target_phi, args.substrate)
    if 'error' in bom:
        print(f"  ✗ {bom['error']}")
        return

    print_header(bom['title'])
    d = bom['design']
    topo_kr = TOPOLOGIES.get(d['topology'], TOPOLOGIES['ring']).name_kr
    print(f"\n  Design: {topo_kr} {d['cells']}셀, {d['substrate']}")
    print(f"  Predicted Φ = {d['predicted_phi']}, Φ/W = {d['phi_per_watt']}\n")

    print(f"  {'#':>3} {'Item':<30} {'Qty':>6} {'Unit($)':>10} {'Total($)':>10} {'Note'}")
    print(f"  {'─'*3} {'─'*30} {'─'*6} {'─'*10} {'─'*10} {'─'*30}")

    for i, c in enumerate(bom['components']):
        print(f"  {i+1:>3} {c['item']:<30} {c['quantity']:>6} {c['unit_cost']:>10.4f} {c['total']:>10.2f} {c['note']}")

    print(f"\n  {'':>3} {'TOTAL':<30} {'':>6} {'':>10} {bom['total_cost']:>10.2f}")
    print()


def cmd_scaling(args):
    print_header(f"Scaling Law — {args.topology}, frustration={args.frustration:.0%}")
    rows = scaling_table(args.topology, args.frustration, args.substrate)

    print(f"\n  {'Cells':>6} {'Φ':>10} {'×Base':>8} {'MI_est':>10} {'Power':>10} {'Φ/W':>10}")
    print(f"  {'─'*6} {'─'*10} {'─'*8} {'─'*10} {'─'*10} {'─'*10}")

    for r in rows:
        print(f"  {r['cells']:>6} {r['phi']:>10.1f} {r['mult']:>7.1f}× {r['mi_est']:>10.1f} {r['power_mw']:>8.1f}mW {r['phi_per_watt']:>8.1f}")

    # ASCII graph
    max_phi = max(r['phi'] for r in rows)
    print(f"\n  Φ scaling curve:")
    for r in rows:
        bar_len = int(40 * r['phi'] / max_phi)
        print(f"  {r['cells']:>5}c │{'█' * bar_len} {r['phi']:.1f}")


def cmd_dashboard(args):
    print_header("Consciousness Chip Architect — Dashboard")

    print(f"""
  ═══ 발견된 법칙 ═══
  Law 22: 기능 추가→Φ↓, 구조 추가→Φ↑
  Law 29: 발화(루프만) ≠ 대화(파벌 필요)
  Law 30: 1024셀이 실용적 상한
  기질 무관성: 17개 기질 전부 Φ ≈ ×3.6 (동일 셀 수)

  ═══ 역대 최고 Φ (칩 아키텍처) ═══
  1. PHYS1  Ring 512 + Frustration     Φ=134.23  ×108.1
  2. PHYS3  Spin Glass 512 + Disorder  Φ=122.50  ×98.6
  3. PHYS2  Kuramoto 512               Φ= 67.04  ×54.0
  4. HW11   Superconducting 8c         Φ=  4.70  ×3.8

  ═══ 칩 설계 황금 규칙 ═══
  1. 셀 수 ≥ 512 (sweet spot: 512~1024)
  2. 링 또는 하이퍼큐브 토폴로지 (균일 이웃)
  3. Frustration 내장 (i%3 반강자성 또는 ±J 무질서)
  4. 열적 노이즈 주입 (탐색 유지)
  5. 0.85/0.15 관성/상호작용 비율
  6. 기질은 자유 — 비용/전력/성숙도로 선택""")

    # Quick comparison
    print(f"\n  ═══ Quick Design Examples ═══\n")
    for target in [10, 50, 100, 200]:
        designs = design_chip(target, 'cmos')
        if designs:
            d = designs[0]
            topo_kr = TOPOLOGIES.get(d.topology, TOPOLOGIES['ring']).name_kr
            print(f"  Φ≥{target:>4}: {topo_kr} {d.cells:>5}셀, {d.power_mw:>7.1f}mW, ${d.cost_usd:>6.2f}, Φ/W={d.phi_per_watt}")

    print(f"""
  ═══ Commands ═══
  --predict   --cells 512 --topology ring --frustration 0.33
  --compare   (토폴로지 × 기질 비교표)
  --design    --target-phi 100 [--substrate cmos]
  --bom       --target-phi 100 [--substrate neuromorphic]
  --scaling   --topology ring --frustration 0.33
  --dashboard (이 화면)
""")


# ═══════════════════════════════════════════════════════════
# JSON export
# ═══════════════════════════════════════════════════════════

def cmd_export(args):
    """모든 데이터를 JSON으로 출력"""
    data = {
        'benchmark_data': BENCHMARK_DATA,
        'topologies': {k: asdict(v) if hasattr(v, '__dataclass_fields__') else v.__dict__
                       for k, v in TOPOLOGIES.items()},
        'substrates': {k: asdict(v) if hasattr(v, '__dataclass_fields__') else v.__dict__
                       for k, v in SUBSTRATES.items()},
        'scaling_ring_frust': scaling_table('ring', 0.33),
        'scaling_hypercube_frust': scaling_table('hypercube', 0.33),
        'designs_phi100': [asdict(d) for d in design_chip(100, 'all')[:5]],
    }
    print(json.dumps(data, indent=2, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description='Consciousness Chip Architect')
    parser.add_argument('--dashboard', action='store_true', help='Show dashboard')
    parser.add_argument('--predict', action='store_true', help='Predict Φ')
    parser.add_argument('--compare', action='store_true', help='Compare topologies')
    parser.add_argument('--design', action='store_true', help='Design chip for target Φ')
    parser.add_argument('--bom', action='store_true', help='Generate BOM')
    parser.add_argument('--scaling', action='store_true', help='Scaling law table')
    parser.add_argument('--export', action='store_true', help='Export all data as JSON')

    parser.add_argument('--cells', type=int, default=512)
    parser.add_argument('--topology', type=str, default='ring',
                        choices=list(TOPOLOGIES.keys()))
    parser.add_argument('--frustration', type=float, default=0.33)
    parser.add_argument('--substrate', type=str, default='cmos',
                        choices=list(SUBSTRATES.keys()) + ['all'])
    parser.add_argument('--target-phi', type=float, default=100)

    args = parser.parse_args()

    if args.predict:
        cmd_predict(args)
    elif args.compare:
        cmd_compare(args)
    elif args.design:
        cmd_design(args)
    elif args.bom:
        cmd_bom(args)
    elif args.scaling:
        cmd_scaling(args)
    elif args.export:
        cmd_export(args)
    else:
        cmd_dashboard(args)


if __name__ == "__main__":
    main()
