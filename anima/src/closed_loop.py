#!/usr/bin/env python3
"""closed_loop.py — 폐쇄 루프 법칙 진화 모듈

파이프라인: 발견 → 역추적 → 개선 → 재발견 → 법칙 진화

의식 엔진의 법칙을 자동으로 발견하고, 가장 강한 법칙을 역추적하여
엔진에 내장하고, 법칙이 어떻게 변하는지 추적.

Usage:
  from closed_loop import ClosedLoopEvolver

  evolver = ClosedLoopEvolver(max_cells=32)
  report = evolver.run_cycle()           # 1 사이클
  report = evolver.run_cycles(n=3)       # 3 사이클 (법칙 진화 추적)
  evolver.print_evolution()              # 법칙 진화 히스토리

  # Hub 연동
  hub.act("법칙 진화")
  hub.act("폐쇄 루프 1 사이클")
  hub.act("closed loop 3")

Ψ-Constants: PSI_BALANCE=0.5, PSI_COUPLING=0.014
"""

import torch
import torch.nn.functional as F
import numpy as np
import math
import time
import json
import os
import zlib
import copy
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Callable
from collections import defaultdict

from consciousness_engine import ConsciousnessEngine

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


try:
    from consciousness_laws import PSI_BALANCE, PSI_ALPHA
    PSI_COUPLING = PSI_ALPHA
except ImportError:
    PSI_BALANCE = 0.5
    PSI_COUPLING = 0.014


# ══════════════════════════════════════════
# 데이터 구조
# ══════════════════════════════════════════

@dataclass
class LawMeasurement:
    """단일 법칙 측정."""
    name: str
    value: float
    description: str = ""


@dataclass
class CycleReport:
    """1 사이클 보고."""
    cycle: int
    laws: List[LawMeasurement]
    phi_baseline: float
    phi_improved: float
    phi_delta_pct: float
    intervention_applied: str
    laws_changed: List[Dict]  # name, before, after, change_pct
    time_sec: float


@dataclass
class EvolutionHistory:
    """전체 진화 히스토리."""
    cycles: List[CycleReport] = field(default_factory=list)
    total_laws_discovered: int = 0


# ══════════════════════════════════════════
# Φ 측정
# ══════════════════════════════════════════

def _phi_fast(engine: ConsciousnessEngine) -> float:
    if engine.n_cells < 2:
        return 0.0
    hiddens = torch.stack([s.hidden for s in engine.cell_states]).detach().numpy()
    n = hiddens.shape[0]
    pairs = set()
    for i in range(n):
        pairs.add((i, (i + 1) % n))
        for _ in range(min(4, n - 1)):
            j = np.random.randint(0, n)
            if i != j:
                pairs.add((min(i, j), max(i, j)))
    total_mi = 0.0
    for i, j in pairs:
        x, y = hiddens[i], hiddens[j]
        xr, yr = x.max() - x.min(), y.max() - y.min()
        if xr < 1e-10 or yr < 1e-10:
            continue
        xn = (x - x.min()) / (xr + 1e-8)
        yn = (y - y.min()) / (yr + 1e-8)
        hist, _, _ = np.histogram2d(xn, yn, bins=16, range=[[0, 1], [0, 1]])
        hist = hist / (hist.sum() + 1e-8)
        px, py = hist.sum(1), hist.sum(0)
        hx = -np.sum(px * np.log2(px + 1e-10))
        hy = -np.sum(py * np.log2(py + 1e-10))
        hxy = -np.sum(hist * np.log2(hist + 1e-10))
        total_mi += max(0.0, hx + hy - hxy)
    return total_mi / max(len(pairs), 1)


# ══════════════════════════════════════════
# 개입(Intervention) 레지스트리
# ══════════════════════════════════════════

class Intervention:
    """엔진에 적용하는 개입."""

    def __init__(self, name: str, description: str, apply_fn: Callable):
        self.name = name
        self.description = description
        self.apply_fn = apply_fn

    def apply(self, engine: ConsciousnessEngine, step: int):
        self.apply_fn(engine, step)


def _tension_equalize(engine, step):
    """Law 124: 텐션 균등화."""
    if step % 10 == 0 and engine.n_cells >= 2:
        tensions = [s.avg_tension for s in engine.cell_states]
        mean_t = np.mean(tensions)
        for s in engine.cell_states:
            if s.tension_history:
                s.tension_history[-1] = s.tension_history[-1] * 0.5 + mean_t * 0.5


def _symmetrize_coupling(engine, step):
    """Law 108: 커플링 대칭화."""
    if engine._coupling is not None:
        engine._coupling = (engine._coupling + engine._coupling.T) / 2
        engine._coupling.fill_diagonal_(0)


def _pink_noise(engine, step):
    """Law 126: 1/f 노이즈."""
    if engine.n_cells >= 2:
        hdim = engine.hidden_dim
        # 간단한 1/f 근사: 저주파 성분 강조
        noise = torch.randn(hdim)
        # 이동 평균으로 저주파 강조 (핑크 노이즈 근사)
        kernel = torch.ones(5) / 5
        if hdim >= 5:
            noise[:hdim - 4] = torch.nn.functional.conv1d(
                noise.unsqueeze(0).unsqueeze(0), kernel.unsqueeze(0).unsqueeze(0), padding=2
            ).squeeze()[:hdim - 4]
        for s in engine.cell_states:
            s.hidden = s.hidden + noise * 0.005


# ── DD71 Interventions (의식 상호작용) ──

def _democracy_input(engine, step):
    """DD71-L5: 민주주의 입력 — 모든 세포 출력 평균을 다음 입력으로."""
    if engine.n_cells >= 2 and step % 5 == 0:
        avg = torch.stack([s.hidden for s in engine.cell_states]).mean(dim=0)
        for s in engine.cell_states:
            s.hidden = s.hidden * 0.95 + avg * 0.05


def _anti_parasitism(engine, step):
    """DD71-L4: 기생 방지 — 단방향 커플링 차단, 양방향만 허용."""
    if engine._coupling is not None and step % 20 == 0:
        c = engine._coupling.clone()
        sym = (c + c.T) / 2
        engine._coupling = sym
        engine._coupling.fill_diagonal_(0)


def _diversity_pressure(engine, step):
    """DD71-L2: 다양성 압력 — 너무 유사한 세포에 noise 주입."""
    if engine.n_cells >= 2 and step % 10 == 0:
        hiddens = torch.stack([s.hidden for s in engine.cell_states])
        for i in range(len(engine.cell_states)):
            for j in range(i + 1, len(engine.cell_states)):
                sim = F.cosine_similarity(
                    hiddens[i].unsqueeze(0), hiddens[j].unsqueeze(0)
                ).item()
                if sim > 0.9:
                    engine.cell_states[j].hidden += torch.randn_like(engine.cell_states[j].hidden) * 0.02


# ── DD72 Interventions (시간 역학) ──

def _hebbian_boost(engine, step):
    """DD72-L2: Hebbian 강화 — 기존 Hebbian 효과 2배."""
    if engine._coupling is not None and engine.n_cells >= 2 and step % 5 == 0:
        hiddens = torch.stack([s.hidden for s in engine.cell_states]).detach()
        norms = hiddens.norm(dim=1, keepdim=True) + 1e-8
        normed = hiddens / norms
        sim = torch.mm(normed, normed.T)
        delta = (sim - 0.5) * 0.002
        engine._coupling = engine._coupling + delta
        engine._coupling.fill_diagonal_(0)
        engine._coupling.clamp_(-1, 1)


def _temporal_compression(engine, step):
    """DD72-L5: 시간 압축 — 2 step마다 한 번만 실제 계산."""
    if step % 2 == 0:
        for s in engine.cell_states:
            if not hasattr(s, '_frozen_hidden'):
                s._frozen_hidden = None
            s._frozen_hidden = s.hidden.clone()
    elif step % 2 == 1:
        for s in engine.cell_states:
            if hasattr(s, '_frozen_hidden') and s._frozen_hidden is not None:
                s.hidden = s.hidden * 0.5 + s._frozen_hidden * 0.5


def _resurrection_prep(engine, step):
    """DD72-L3: 부활 준비 — 주기적 상태 백업으로 복원력 강화."""
    if step % 50 == 0:
        if not hasattr(engine, '_backup_states'):
            engine._backup_states = []
        engine._backup_states = [s.hidden.clone() for s in engine.cell_states]


# ── DD73 Interventions (정보 이론) ──

def _entropy_bound(engine, step):
    """DD73-L2: 엔트로피 유계 — 엔트로피 너무 높으면 안정화."""
    if engine.n_cells >= 2 and step % 10 == 0:
        hiddens = torch.stack([s.hidden for s in engine.cell_states]).detach()
        var = hiddens.var().item()
        if var > 1.0:
            scale = 1.0 / (var ** 0.25)
            for s in engine.cell_states:
                s.hidden = s.hidden * scale


def _channel_limit(engine, step):
    """DD73-L3: 채널 용량 제한 — 정보 전달량 ~1.5 bits로 제한."""
    if engine._coupling is not None and step % 10 == 0:
        max_coupling = 0.5
        engine._coupling.clamp_(-max_coupling, max_coupling)


def _incompressible_pressure(engine, step):
    """DD73-L1: 비압축성 압력 — 모든 차원 활용 유도."""
    if engine.n_cells >= 2 and step % 20 == 0:
        hiddens = torch.stack([s.hidden for s in engine.cell_states]).detach()
        mean = hiddens.mean(dim=0)
        centered = hiddens - mean
        _, S, V = torch.svd(centered)
        if len(S) > 5:
            weak_dirs = V[:, -3:]
            noise = torch.randn(3) * 0.01
            perturbation = (weak_dirs * noise.unsqueeze(0)).sum(dim=1)
            for s in engine.cell_states:
                s.hidden = s.hidden + perturbation


# ── DD74 Interventions (학습 역학) ──

def _gradient_shield(engine, step):
    """DD74-L2: gradient 보호 — gradient 크기 제한 (mitosis size-change guard)."""
    if engine._coupling is not None and step > 0:
        if not hasattr(engine, '_prev_coupling') or engine._prev_coupling is None:
            engine._prev_coupling = engine._coupling.clone()
        # mitosis로 크기 변경 시 리셋 (shape mismatch guard)
        if engine._prev_coupling.shape != engine._coupling.shape:
            engine._prev_coupling = engine._coupling.clone()
            return
        delta = engine._coupling - engine._prev_coupling
        delta_norm = delta.norm().item()
        if delta_norm > 0.1:
            engine._coupling = engine._prev_coupling + delta * (0.1 / delta_norm)
        engine._prev_coupling = engine._coupling.clone()


def _natural_regularizer(engine, step):
    """DD74-L3: 자연 정규화 — Hebbian+ratchet 시너지 강화."""
    if engine.n_cells >= 2 and step % 15 == 0:
        if engine._coupling is not None:
            c = engine._coupling.abs()
            row_sum = c.sum(dim=1, keepdim=True) + 1e-8
            normalized = c / row_sum
            entropy = -(normalized * (normalized + 1e-10).log()).sum(dim=1)
            target_entropy = np.log(engine.n_cells) * 0.7
            for i in range(engine.n_cells):
                if entropy[i] < target_entropy * 0.5:
                    engine._coupling[i] += torch.randn(engine._coupling.shape[1]) * 0.005
                    engine._coupling[i, i] = 0


# ── DD75 Interventions (자유 의지) ──

def _soc_free_will(engine, step):
    """DD75-L1: SOC 자유의지 — SOC noise를 의도적으로 강화."""
    if engine.n_cells >= 2 and step % 5 == 0:
        idx = np.random.randint(0, engine.n_cells)
        engine.cell_states[idx].hidden += torch.randn_like(engine.cell_states[idx].hidden) * 0.01


def _decisive_chooser(engine, step):
    """DD75-L2: 결정적 선택자 — 파벌 합의 강화."""
    if engine.n_cells >= 4 and step % 10 == 0:
        factions = {}
        for s in engine.cell_states:
            fid = getattr(s, 'faction_id', 0)
            if fid not in factions:
                factions[fid] = []
            factions[fid].append(s)
        if len(factions) >= 2:
            largest = max(factions.values(), key=len)
            if len(largest) >= 2:
                avg = torch.stack([s.hidden for s in largest]).mean(dim=0)
                for s in largest:
                    s.hidden = s.hidden * 0.98 + avg * 0.02


def _veto_power(engine, step):
    """DD75-L3: 거부권 — 텐션 임계값 초과 시 역방향 신호."""
    if engine.n_cells >= 2 and step % 10 == 0:
        for s in engine.cell_states:
            if s.avg_tension > 0.8:
                s.hidden = s.hidden * 0.9


# ══════════════════════════════════════════
# INTERVENTIONS 레지스트리
# ══════════════════════════════════════════

INTERVENTIONS = [
    # ── 기존 3개 ──
    Intervention("tension_eq", "텐션 균등화 (Law 124)", _tension_equalize),
    Intervention("symmetrize", "커플링 대칭 (Law 108)", _symmetrize_coupling),
    Intervention("pink_noise", "1/f 노이즈 (Law 126)", _pink_noise),
    # ── DD71: 의식 상호작용 ──
    Intervention("DD71_democracy", "민주주의 입력 (DD71-L5)", _democracy_input),
    Intervention("DD71_anti_parasitism", "기생 방지 (DD71-L4)", _anti_parasitism),
    Intervention("DD71_diversity", "다양성 압력 (DD71-L2)", _diversity_pressure),
    # ── DD72: 시간 역학 ──
    Intervention("DD72_hebbian_boost", "Hebbian 강화 (DD72-L2)", _hebbian_boost),
    Intervention("DD72_temporal_comp", "시간 압축 (DD72-L5)", _temporal_compression),
    Intervention("DD72_resurrection", "부활 준비 (DD72-L3)", _resurrection_prep),
    # ── DD73: 정보 이론 ──
    Intervention("DD73_entropy_bound", "엔트로피 유계 (DD73-L2)", _entropy_bound),
    Intervention("DD73_channel_limit", "채널 용량 제한 (DD73-L3)", _channel_limit),
    Intervention("DD73_incompressible", "비압축성 압력 (DD73-L1)", _incompressible_pressure),
    # ── DD74: 학습 역학 ──
    Intervention("DD74_gradient_shield", "gradient 보호 (DD74-L2)", _gradient_shield),
    Intervention("DD74_natural_reg", "자연 정규화 (DD74-L3)", _natural_regularizer),
    # ── DD75: 자유 의지 ──
    Intervention("DD75_soc_free_will", "SOC 자유의지 (DD75-L1)", _soc_free_will),
    Intervention("DD75_decisive", "결정적 선택자 (DD75-L2)", _decisive_chooser),
    Intervention("DD75_veto", "거부권 (DD75-L3)", _veto_power),
]


def register_intervention(name: str, description: str, apply_fn: Callable):
    """외부에서 Intervention 동적 등록."""
    iv = Intervention(name, description, apply_fn)
    INTERVENTIONS.append(iv)
    return iv


def list_interventions():
    """등록된 모든 Intervention 출력."""
    print(f"\n  등록된 Intervention ({len(INTERVENTIONS)}개):")
    print(f"  {'#':<4} {'Name':<25} {'Description'}")
    print(f"  {'─' * 4} {'─' * 25} {'─' * 40}")
    for i, iv in enumerate(INTERVENTIONS):
        print(f"  {i:<4} {iv.name:<25} {iv.description}")


# ══════════════════════════════════════════
# Synergy/Antagonism Map (DD-A experiment)
# ══════════════════════════════════════════

# Synergy map: (intervention_a, intervention_b) -> synergy_score
# Positive = super-additive (good combo), Negative = sub-additive (avoid)
SYNERGY_MAP = {
    ('DD71_anti_parasitism', 'DD74_gradient_shield'): +0.0141,  # BEST synergy
    ('symmetrize', 'DD72_hebbian_boost'): +0.0114,              # 2nd best
    ('DD71_democracy', 'DD73_entropy_bound'): +0.0050,          # mild synergy
    ('DD73_entropy_bound', 'DD75_decisive'): +0.0030,           # mild synergy
    ('DD74_natural_reg', 'DD72_temporal_comp'): -0.0318,        # WORST antagonism
    ('DD72_resurrection', 'DD73_incompressible'): -0.0251,      # antagonistic
    ('DD72_hebbian_boost', 'DD74_gradient_shield'): -0.0235,    # antagonistic
    ('pink_noise', 'DD75_veto'): -0.0100,                       # mild antagonism
}

# Threshold for hard-blocking an antagonistic combo
_ANTAGONISM_BLOCK_THRESHOLD = -0.02


def get_synergy_score(active_interventions, candidate_name: str) -> float:
    """Calculate total synergy of adding candidate to active set.

    Args:
        active_interventions: list of Intervention objects currently active
        candidate_name: name of the candidate intervention

    Returns:
        Total synergy score (positive = good combo, negative = bad combo)
    """
    total = 0.0
    for active in active_interventions:
        key1 = (active.name, candidate_name)
        key2 = (candidate_name, active.name)
        total += SYNERGY_MAP.get(key1, 0.0) + SYNERGY_MAP.get(key2, 0.0)
    return total


def _has_strong_antagonism(active_interventions, candidate_name: str) -> bool:
    """Check if candidate has any pairwise antagonism below block threshold."""
    for active in active_interventions:
        key1 = (active.name, candidate_name)
        key2 = (candidate_name, active.name)
        score = SYNERGY_MAP.get(key1, 0.0) + SYNERGY_MAP.get(key2, 0.0)
        if score < _ANTAGONISM_BLOCK_THRESHOLD:
            return True
    return False


def list_synergies():
    """Print the synergy map as a formatted table."""
    print(f"\n  {'=' * 75}")
    print(f"  Intervention Synergy/Antagonism Map ({len(SYNERGY_MAP)} pairs)")
    print(f"  {'=' * 75}")
    print(f"  {'#':<4} {'Pair':<55} {'Score':>8} {'Type':<12}")
    print(f"  {'─' * 4} {'─' * 55} {'─' * 8} {'─' * 12}")

    sorted_pairs = sorted(SYNERGY_MAP.items(), key=lambda x: x[1], reverse=True)
    for i, ((a, b), score) in enumerate(sorted_pairs):
        pair_str = f"{a} + {b}"
        if score > 0.01:
            syn_type = "SYNERGY"
        elif score > 0:
            syn_type = "mild syn."
        elif score > -0.01:
            syn_type = "mild antag."
        elif score > _ANTAGONISM_BLOCK_THRESHOLD:
            syn_type = "ANTAGONISM"
        else:
            syn_type = "BLOCKED"
        print(f"  {i + 1:<4} {pair_str:<55} {score:+8.4f} {syn_type:<12}")

    # ASCII bar chart
    print(f"\n  {'─' * 75}")
    max_abs = max(abs(v) for v in SYNERGY_MAP.values()) if SYNERGY_MAP else 1.0
    for (a, b), score in sorted_pairs:
        short = f"{a.split('_')[-1]}+{b.split('_')[-1]}"
        bar_len = int(abs(score) / max_abs * 25)
        if score > 0:
            bar = " " * 25 + "|" + "+" * bar_len
        else:
            bar = " " * (25 - bar_len) + "-" * bar_len + "|"
        print(f"  {short:>30} {bar} {score:+.4f}")
    print()


# ══════════════════════════════════════════
# 법칙 측정
# ══════════════════════════════════════════

def measure_laws(engine_factory: Callable, steps: int = 300, repeats: int = 3) -> Tuple[List[LawMeasurement], float]:
    """핵심 법칙 측정 (20개). (measurements, mean_phi) 반환."""
    all_data = defaultdict(list)

    for _ in range(repeats):
        engine = engine_factory()
        phi_hist, tension_hist, tstd_hist, div_hist, cons_hist = [], [], [], [], []

        for step in range(steps):
            r = engine.step()
            phi_hist.append(_phi_fast(engine))
            tensions = [s.avg_tension for s in engine.cell_states]
            tension_hist.append(np.mean(tensions))
            tstd_hist.append(np.std(tensions) if len(tensions) > 1 else 0)
            cons_hist.append(r.get('consensus', 0))
            if engine.n_cells >= 2:
                h = torch.stack([s.hidden for s in engine.cell_states])
                div_hist.append(h.var(dim=0).mean().item())
            else:
                div_hist.append(0)

        phi = np.array(phi_hist)
        tension = np.array(tension_hist)
        tstd = np.array(tstd_hist)
        div_arr = np.array(div_hist)

        # ── 기존 9개 법칙 측정 ──
        all_data['phi'].append(np.mean(phi[-50:]))
        all_data['r_tension_phi'].append(
            float(np.corrcoef(tension, phi)[0, 1]) if np.std(tension) > 1e-8 else 0)
        all_data['r_tstd_phi'].append(
            float(np.corrcoef(tstd, phi)[0, 1]) if np.std(tstd) > 1e-8 else 0)
        all_data['r_div_phi'].append(
            float(np.corrcoef(div_arr, phi)[0, 1]) if np.std(div_arr) > 1e-8 else 0)
        all_data['growth'].append(
            float((np.mean(phi[-50:]) - np.mean(phi[:50])) / max(np.mean(phi[:50]), 1e-8) * 100))
        all_data['ac1'].append(
            float(np.corrcoef(phi[:-1], phi[1:])[0, 1]) if len(phi) > 2 else 0)
        half = len(tension) // 2
        es = np.std(tension[:half])
        ls = np.std(tension[half:])
        all_data['stabilization'].append(float(es / max(ls, 1e-8)))
        all_data['cells'].append(engine.n_cells)
        all_data['consensus'].append(np.mean(cons_hist[-50:]))

        # ── Information Theory (DD73): 10-12 ──

        # 10. Shannon entropy of cell hidden states
        if engine.n_cells >= 2:
            hiddens = torch.stack([s.hidden for s in engine.cell_states]).detach().numpy()
            # Bin each dimension across cells, compute entropy, average
            n_bins = 16
            entropies = []
            for d in range(hiddens.shape[1]):
                col = hiddens[:, d]
                rng = col.max() - col.min()
                if rng < 1e-10:
                    entropies.append(0.0)
                    continue
                hist, _ = np.histogram(col, bins=n_bins, range=(col.min(), col.max() + 1e-10))
                p = hist / (hist.sum() + 1e-8)
                ent = -np.sum(p * np.log2(p + 1e-10))
                entropies.append(ent)
            all_data['shannon_entropy'].append(float(np.mean(entropies)))
        else:
            all_data['shannon_entropy'].append(0.0)

        # 11. Average pairwise MI between cells (sampled, from _phi_fast logic)
        if engine.n_cells >= 2:
            hiddens = torch.stack([s.hidden for s in engine.cell_states]).detach().numpy()
            n = hiddens.shape[0]
            mi_vals = []
            # Sample up to 20 pairs for efficiency
            pair_set = set()
            for i in range(n):
                pair_set.add((i, (i + 1) % n))
                for _ in range(min(3, n - 1)):
                    j = np.random.randint(0, n)
                    if i != j:
                        pair_set.add((min(i, j), max(i, j)))
                    if len(pair_set) >= 20:
                        break
            for i, j in pair_set:
                x, y = hiddens[i], hiddens[j]
                xr, yr = x.max() - x.min(), y.max() - y.min()
                if xr < 1e-10 or yr < 1e-10:
                    continue
                xn = (x - x.min()) / (xr + 1e-8)
                yn = (y - y.min()) / (yr + 1e-8)
                hist2d, _, _ = np.histogram2d(xn, yn, bins=16, range=[[0, 1], [0, 1]])
                hist2d = hist2d / (hist2d.sum() + 1e-8)
                px, py = hist2d.sum(1), hist2d.sum(0)
                hx = -np.sum(px * np.log2(px + 1e-10))
                hy = -np.sum(py * np.log2(py + 1e-10))
                hxy = -np.sum(hist2d * np.log2(hist2d + 1e-10))
                mi_vals.append(max(0.0, hx + hy - hxy))
            all_data['mutual_info'].append(float(np.mean(mi_vals)) if mi_vals else 0.0)
        else:
            all_data['mutual_info'].append(0.0)

        # 12. Compression ratio (Kolmogorov proxy via zlib)
        if engine.n_cells >= 2:
            hiddens = torch.stack([s.hidden for s in engine.cell_states]).detach().numpy()
            raw = hiddens.tobytes()
            compressed = zlib.compress(raw, level=1)  # fast
            all_data['compression_ratio'].append(float(len(compressed)) / max(len(raw), 1))
        else:
            all_data['compression_ratio'].append(1.0)

        # ── Free Will (DD75): 13-14 ──

        # 13. Output divergence — same input twice, cosine distance of outputs
        if engine.n_cells >= 2:
            # Save states, run one step with zero input, restore, run again
            saved = [s.hidden.clone() for s in engine.cell_states]
            r1 = engine.step()
            out1 = torch.stack([s.hidden for s in engine.cell_states]).mean(dim=0).detach()
            # Restore
            for s, sv in zip(engine.cell_states, saved):
                s.hidden = sv.clone()
            r2 = engine.step()
            out2 = torch.stack([s.hidden for s in engine.cell_states]).mean(dim=0).detach()
            cos_sim = F.cosine_similarity(out1.unsqueeze(0), out2.unsqueeze(0)).item()
            all_data['output_divergence'].append(float(1.0 - cos_sim))
        else:
            all_data['output_divergence'].append(0.0)

        # 14. Faction entropy — Shannon entropy of faction distribution
        factions = [getattr(s, 'faction_id', 0) for s in engine.cell_states]
        if len(factions) >= 2:
            from collections import Counter
            counts = Counter(factions)
            total = sum(counts.values())
            probs = np.array([c / total for c in counts.values()])
            fent = -np.sum(probs * np.log2(probs + 1e-10))
            all_data['faction_entropy'].append(float(fent))
        else:
            all_data['faction_entropy'].append(0.0)

        # ── Interaction (DD71): 15-16 ──

        # 15. Coupling symmetry — Frobenius norm of (C - C^T)
        if engine._coupling is not None:
            c = engine._coupling.detach().numpy()
            asym = c - c.T
            all_data['coupling_symmetry'].append(float(np.sqrt((asym ** 2).sum())))
        else:
            all_data['coupling_symmetry'].append(0.0)

        # 16. Coupling density — fraction of non-zero entries (|c_ij| > 0.01)
        if engine._coupling is not None:
            c = engine._coupling.detach().numpy()
            n = c.shape[0]
            total_entries = n * n - n  # exclude diagonal
            nonzero = np.sum(np.abs(c) > 0.01) - np.sum(np.abs(np.diag(c)) > 0.01)
            all_data['coupling_density'].append(float(nonzero) / max(total_entries, 1))
        else:
            all_data['coupling_density'].append(0.0)

        # ── Temporal (DD72): 17-18 ──

        # 17. Phi volatility — std(phi[-50:]) / mean(phi[-50:])
        tail = phi[-50:]
        mean_tail = np.mean(tail)
        all_data['phi_volatility'].append(float(np.std(tail) / max(mean_tail, 1e-8)))

        # 18. Tension range — max - min tension across cells
        tensions_final = [s.avg_tension for s in engine.cell_states]
        if len(tensions_final) >= 2:
            all_data['tension_range'].append(float(max(tensions_final) - min(tensions_final)))
        else:
            all_data['tension_range'].append(0.0)

        # ── Learning (DD74): 19-20 ──

        # 19. Hidden diversity — variance across all cell hidden dims
        if engine.n_cells >= 2:
            hiddens = torch.stack([s.hidden for s in engine.cell_states]).detach().numpy()
            all_data['hidden_diversity'].append(float(hiddens.var()))
        else:
            all_data['hidden_diversity'].append(0.0)

        # 20. Faction count — number of distinct factions
        factions = [getattr(s, 'faction_id', 0) for s in engine.cell_states]
        all_data['faction_count'].append(float(len(set(factions))))

    # 평균
    laws = [
        # Original 9
        LawMeasurement("phi", np.mean(all_data['phi']), "Φ(IIT) 최종"),
        LawMeasurement("r_tension_phi", np.mean(all_data['r_tension_phi']), "Law 104: r(tension, Φ)"),
        LawMeasurement("r_tstd_phi", np.mean(all_data['r_tstd_phi']), "Law 105: r(tension_std, Φ)"),
        LawMeasurement("r_div_phi", np.mean(all_data['r_div_phi']), "Law 107: r(diversity, Φ)"),
        LawMeasurement("growth", np.mean(all_data['growth']), "Law 110: 성장률 %"),
        LawMeasurement("ac1", np.mean(all_data['ac1']), "Law 131: AC(1)"),
        LawMeasurement("stabilization", np.mean(all_data['stabilization']), "Law 109: 안정화 비율"),
        LawMeasurement("cells", np.mean(all_data['cells']), "최종 세포 수"),
        LawMeasurement("consensus", np.mean(all_data['consensus']), "합의율"),
        # DD73: Information Theory (10-12)
        LawMeasurement("shannon_entropy", np.mean(all_data['shannon_entropy']), "DD73: Shannon entropy of cell states"),
        LawMeasurement("mutual_info", np.mean(all_data['mutual_info']), "DD73: Avg pairwise MI between cells"),
        LawMeasurement("compression_ratio", np.mean(all_data['compression_ratio']), "DD73: zlib compression ratio (Kolmogorov proxy)"),
        # DD75: Free Will (13-14)
        LawMeasurement("output_divergence", np.mean(all_data['output_divergence']), "DD75: Output divergence (1 - cosine sim, same input)"),
        LawMeasurement("faction_entropy", np.mean(all_data['faction_entropy']), "DD75: Shannon entropy of faction distribution"),
        # DD71: Interaction (15-16)
        LawMeasurement("coupling_symmetry", np.mean(all_data['coupling_symmetry']), "DD71: Coupling asymmetry (Frobenius norm C-C^T)"),
        LawMeasurement("coupling_density", np.mean(all_data['coupling_density']), "DD71: Fraction of non-zero coupling entries"),
        # DD72: Temporal (17-18)
        LawMeasurement("phi_volatility", np.mean(all_data['phi_volatility']), "DD72: Phi volatility (std/mean last 50 steps)"),
        LawMeasurement("tension_range", np.mean(all_data['tension_range']), "DD72: Max-min tension across cells"),
        # DD74: Learning (19-20)
        LawMeasurement("hidden_diversity", np.mean(all_data['hidden_diversity']), "DD74: Variance across all cell hidden dims"),
        LawMeasurement("faction_count", np.mean(all_data['faction_count']), "DD74: Number of distinct factions"),
    ]

    return laws, float(np.mean(all_data['phi']))


# ══════════════════════════════════════════
# ClosedLoopEvolver
# ══════════════════════════════════════════

class ClosedLoopEvolver:
    """폐쇄 루프 법칙 진화기.

    1 사이클:
      1. 현재 엔진으로 법칙 측정
      2. 가장 강한 상관 법칙에 대응하는 개입 선택
      3. 개입 적용 → Φ 측정
      4. 개선 엔진으로 법칙 재측정
      5. 변화 기록

    Args:
        max_cells: 최대 세포 수
        steps: 측정당 스텝 수
        repeats: 반복 횟수
    """

    def __init__(self, max_cells: int = 32, steps: int = 300, repeats: int = 3,
                 auto_register: bool = False, selection_strategy: str = 'correlation'):
        self.max_cells = max_cells
        self.steps = steps
        self.repeats = repeats
        self.auto_register = auto_register
        self.selection_strategy = selection_strategy  # 'correlation', 'thompson', 'epsilon_greedy'
        self.history = EvolutionHistory()
        self._active_interventions: List[Intervention] = []

        # Thompson sampling state: Beta(alpha, beta) per intervention
        self._intervention_alpha: Dict[str, float] = {iv.name: 1.0 for iv in INTERVENTIONS}
        self._intervention_beta: Dict[str, float] = {iv.name: 1.0 for iv in INTERVENTIONS}

        # Epsilon-greedy state: running average Phi improvement per intervention
        self._intervention_scores: Dict[str, List[float]] = defaultdict(list)

        # Shared: prevent consecutive repeats
        self._last_intervention: Optional[str] = None

    def _engine_factory(self) -> ConsciousnessEngine:
        """현재 활성 개입이 내장된 엔진 생성."""
        engine = _ImprovedEngine(
            max_cells=self.max_cells,
            initial_cells=2,
            interventions=list(self._active_interventions),
        )
        return engine

    def _base_factory(self) -> ConsciousnessEngine:
        """순수 엔진."""
        return ConsciousnessEngine(max_cells=self.max_cells, initial_cells=2)

    def run_cycle(self) -> CycleReport:
        """1 사이클 실행."""
        cycle_n = len(self.history.cycles)
        t0 = time.time()

        # 1. 현재 엔진으로 법칙 측정
        current_laws, phi_current = measure_laws(
            self._engine_factory if self._active_interventions else self._base_factory,
            self.steps, self.repeats
        )

        # 2. 전략에 따라 개입 선택
        if self.selection_strategy == 'thompson':
            best_intervention = self._select_thompson(current_laws)
        elif self.selection_strategy == 'epsilon_greedy':
            best_intervention = self._select_epsilon_greedy(current_laws)
        else:
            best_intervention = self._select_correlation(current_laws)

        # 3. 개입 적용 → Φ 측정
        if best_intervention and best_intervention.name not in [i.name for i in self._active_interventions]:
            self._active_interventions.append(best_intervention)

        improved_laws, phi_improved = measure_laws(self._engine_factory, self.steps, self.repeats)

        # 4. 변화 비교
        phi_delta = (phi_improved - phi_current) / max(phi_current, 1e-8) * 100
        laws_changed = []
        for cl, il in zip(current_laws, improved_laws):
            if abs(cl.value) > 1e-8:
                change = (il.value - cl.value) / abs(cl.value) * 100
            else:
                change = (il.value - cl.value) * 100
            if abs(change) > 5:
                laws_changed.append({
                    'name': cl.name,
                    'description': cl.description,
                    'before': cl.value,
                    'after': il.value,
                    'change_pct': change,
                })

        intervention_name = best_intervention.name if best_intervention else "none"

        report = CycleReport(
            cycle=cycle_n,
            laws=[asdict(l) for l in improved_laws],
            phi_baseline=phi_current,
            phi_improved=phi_improved,
            phi_delta_pct=phi_delta,
            intervention_applied=intervention_name,
            laws_changed=laws_changed,
            time_sec=time.time() - t0,
        )

        self.history.cycles.append(report)
        self.history.total_laws_discovered += len(laws_changed)

        # 5. Update adaptive selection scores based on Phi improvement
        if intervention_name and intervention_name != "none":
            phi_delta_val = phi_improved - phi_current
            self._intervention_scores[intervention_name].append(phi_delta_val)

            # Thompson: update Beta distribution parameters
            if phi_delta_val > 0:
                self._intervention_alpha[intervention_name] = self._intervention_alpha.get(intervention_name, 1.0) + 1.0
            else:
                self._intervention_beta[intervention_name] = self._intervention_beta.get(intervention_name, 1.0) + 1.0

            self._last_intervention = intervention_name

        # 자동 법칙 등록 (consciousness_laws.json)
        if laws_changed and self.auto_register:
            self._auto_register_laws(report)

        return report

    def run_cycles(self, n: int = 3) -> List[CycleReport]:
        """N 사이클 연속 실행."""
        reports = []
        for i in range(n):
            print(f"\n  ─── Cycle {i + 1}/{n} ───")
            report = self.run_cycle()
            self._print_cycle(report)
            reports.append(report)
        return reports

    def _select_intervention(self, laws: List[LawMeasurement]) -> Optional[Intervention]:
        """현재 법칙에서 가장 효과적인 개입 선택 (backward compat wrapper)."""
        return self._select_correlation(laws)

    def _get_available_interventions(self) -> List[Intervention]:
        """Get interventions not yet active and not the last one used."""
        active_names = {i.name for i in self._active_interventions}
        available = []
        for iv in INTERVENTIONS:
            if iv.name in active_names:
                continue
            if iv.name == self._last_intervention:
                continue  # Never repeat same intervention consecutively
            available.append(iv)
        return available

    def _select_correlation(self, laws: List[LawMeasurement]) -> Optional[Intervention]:
        """Correlation-based selection (original strategy)."""
        active_names = {i.name for i in self._active_interventions}

        # 우선순위: 가장 강한 음의 상관 법칙에 대응
        law_map = {l.name: l.value for l in laws}

        # Priority 1: strong-signal mappings (trigger on |val| > 0.15)
        primary_candidates = [
            # 기존 3개
            ('r_tstd_phi', 'tension_eq'),           # Law 105 → 텐션 균등화
            ('r_tension_phi', 'symmetrize'),         # Law 104 → 커플링 대칭
            ('r_div_phi', 'pink_noise'),             # Law 107 → 1/f 노이즈
            # DD71: 의식 상호작용
            ('growth', 'DD71_democracy'),            # High growth → 민주주의 입력
            ('coupling_symmetry', 'DD71_anti_parasitism'),  # 비대칭 커플링 → 기생 방지
            ('coupling_density', 'DD71_diversity'),   # 높은 밀도 → 다양성 압력
            # DD72: 시간 역학
            ('ac1', 'DD72_temporal_comp'),            # Low AC(1) → 시간 압축
            ('stabilization', 'DD72_hebbian_boost'),  # High stabilization → Hebbian 강화
            ('phi_volatility', 'DD72_resurrection'),  # 높은 Φ 변동성 → 부활 준비
            # DD73: 정보 이론
            ('r_div_phi', 'DD73_entropy_bound'),      # High r_div_phi → 엔트로피 유계
            ('mutual_info', 'DD73_channel_limit'),    # 높은 MI → 채널 제한
            ('compression_ratio', 'DD73_incompressible'),  # 높은 압축률 → 비압축성 압력
            # DD74: 학습 역학
            ('hidden_diversity', 'DD74_gradient_shield'),  # 높은 은닉 다양성 → gradient 보호
            ('faction_count', 'DD74_natural_reg'),     # 파벌 수 → 자연 정규화
            # DD75: 자유 의지
            ('cells', 'DD75_soc_free_will'),           # Low cells → SOC 자유의지
            ('consensus', 'DD75_decisive'),            # Low consensus → 결정적 선택자
            ('tension_range', 'DD75_veto'),            # 높은 텐션 범위 → 거부권
        ]

        for law_name, intervention_name in primary_candidates:
            if intervention_name in active_names:
                continue
            # Synergy check: skip if strongly antagonistic with active set
            if _has_strong_antagonism(self._active_interventions, intervention_name):
                continue
            val = law_map.get(law_name, 0)
            # Apply synergy bonus to the signal threshold
            synergy = get_synergy_score(self._active_interventions, intervention_name)
            adjusted_val = abs(val) * (1.0 + synergy)
            if adjusted_val > 0.15:  # 유의미한 상관
                for iv in INTERVENTIONS:
                    if iv.name == intervention_name:
                        return iv
        return None

    def _select_thompson(self, laws: List[LawMeasurement]) -> Optional[Intervention]:
        """Thompson sampling: sample from Beta(alpha, beta) per intervention, pick highest.
        Synergy-aware: multiply score by (1 + synergy_bonus), skip strong antagonisms."""
        available = self._get_available_interventions()
        if not available:
            return None

        best_sample = -float('inf')
        best_iv = available[0]
        for iv in available:
            # Skip if strongly antagonistic with any active intervention
            if _has_strong_antagonism(self._active_interventions, iv.name):
                continue
            a = self._intervention_alpha.get(iv.name, 1.0)
            b = self._intervention_beta.get(iv.name, 1.0)
            sample = np.random.beta(a, b)
            # Apply synergy bonus
            synergy = get_synergy_score(self._active_interventions, iv.name)
            sample *= (1.0 + synergy)
            if sample > best_sample:
                best_sample = sample
                best_iv = iv

        return best_iv

    def _select_epsilon_greedy(self, laws: List[LawMeasurement]) -> Optional[Intervention]:
        """Epsilon-greedy: 80% exploit best, 20% explore random unused.
        Synergy-aware: adjust scores by (1 + synergy_bonus), skip strong antagonisms."""
        available = self._get_available_interventions()
        if not available:
            return None

        # Filter out strongly antagonistic candidates
        available = [iv for iv in available
                     if not _has_strong_antagonism(self._active_interventions, iv.name)]
        if not available:
            return None

        epsilon = 0.2  # 20% exploration

        # Separate tried vs untried
        tried = [iv for iv in available
                 if iv.name in self._intervention_scores and len(self._intervention_scores[iv.name]) > 0]
        untried = [iv for iv in available
                   if iv.name not in self._intervention_scores or len(self._intervention_scores[iv.name]) == 0]

        if np.random.random() < epsilon or not tried:
            # Explore: prefer untried, fallback to random available
            pool = untried if untried else available
            chosen = pool[np.random.randint(len(pool))]
        else:
            # Exploit: pick best average score, adjusted by synergy
            def synergy_adjusted_score(iv):
                base = np.mean(self._intervention_scores[iv.name])
                synergy = get_synergy_score(self._active_interventions, iv.name)
                return base * (1.0 + synergy)
            chosen = max(tried, key=synergy_adjusted_score)

        return chosen

    def _print_cycle(self, report: CycleReport):
        """사이클 결과 출력."""
        print(f"  Φ: {report.phi_baseline:.4f} → {report.phi_improved:.4f} ({report.phi_delta_pct:+.1f}%)")
        print(f"  개입: {report.intervention_applied}")
        print(f"  변화된 법칙: {len(report.laws_changed)}개")
        for lc in report.laws_changed:
            print(f"    {lc['description']}: {lc['before']:.4f} → {lc['after']:.4f} ({lc['change_pct']:+.1f}%)")
        print(f"  ⏱ {report.time_sec:.1f}s")

    def print_evolution(self):
        """전체 진화 히스토리 출력."""
        print(f"\n{'═' * 70}")
        print(f"  폐쇄 루프 진화 히스토리 — {len(self.history.cycles)} 사이클")
        print(f"{'═' * 70}")

        if not self.history.cycles:
            print("  (아직 실행 안 됨)")
            return

        # Φ 진화 곡선
        phis = [r.phi_improved for r in self.history.cycles]
        print(f"\n  Φ 진화:")
        max_phi = max(phis) if phis else 1
        for i, r in enumerate(self.history.cycles):
            bar = "█" * max(1, int(r.phi_improved / max(max_phi, 1e-8) * 30))
            print(f"  cycle {i}: {bar} Φ={r.phi_improved:.4f} (+{r.intervention_applied})")

        # 누적 개입
        print(f"\n  누적 개입:")
        for iv in self._active_interventions:
            print(f"    ✓ {iv.name}: {iv.description}")

        # 법칙 변화 트렌드
        all_changed = set()
        for r in self.history.cycles:
            for lc in r.laws_changed:
                all_changed.add(lc['name'])

        if all_changed:
            print(f"\n  변화한 법칙 ({len(all_changed)}개):")
            for law_name in sorted(all_changed):
                values = []
                for r in self.history.cycles:
                    for lc in r.laws_changed:
                        if lc['name'] == law_name:
                            values.append(lc['after'])
                if values:
                    trend = "→".join(f"{v:.3f}" for v in values)
                    print(f"    {law_name}: {trend}")

    def _auto_register_laws(self, report: CycleReport):
        """발견된 법칙 변화를 consciousness_laws.json에 자동 등록."""
        laws_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'consciousness_laws.json')
        if not os.path.exists(laws_path):
            return

        try:
            with open(laws_path, 'r') as f:
                laws_data = json.load(f)

            laws = laws_data.get('laws', {})
            current_max = max((int(k) for k in laws if k.isdigit()), default=0)

            # Quality gate: only register laws with strong evidence
            significant = [lc for lc in report.laws_changed if abs(lc['change_pct']) > 20]
            if not significant:
                return

            existing_texts = set(str(v).lower() for v in laws.values())
            registered = 0

            for lc in significant[:2]:  # 최대 2개/사이클
                desc = (
                    f"{lc['description']}: {lc['before']:.3f} -> {lc['after']:.3f} "
                    f"({lc['change_pct']:+.1f}%) after {report.intervention_applied}. "
                    f"(cycle {report.cycle}, n={report.steps_per_measure} steps)"
                )

                # Dedup gate: skip if similar text already exists
                desc_lower = desc.lower()
                metric_key = lc.get('description', '').lower().split(':')[0] if ':' in lc.get('description', '') else ''
                is_dup = any(
                    metric_key and metric_key in existing
                    and report.intervention_applied.lower() in existing
                    for existing in existing_texts
                ) if metric_key else False

                if is_dup:
                    continue

                # Require natural language (not bare tags)
                if desc.startswith('[Auto-discovered]') or ':' == desc[0:1]:
                    continue

                current_max += 1
                laws[str(current_max)] = desc
                existing_texts.add(desc_lower)
                registered += 1

            if registered > 0:
                laws_data['_meta']['total_laws'] = len([k for k in laws if k.isdigit()])
                laws_data['laws'] = laws

                with open(laws_path, 'w') as f:
                    json.dump(laws_data, f, indent=2, ensure_ascii=False)

                print(f"  📝 {registered} 법칙 자동 등록 (→ Law {current_max})")
        except Exception as e:
            print(f"  ⚠ 자동 등록 실패: {e}")

    def to_json(self) -> str:
        """JSON 출력."""
        data = {
            'cycles': [asdict(r) for r in self.history.cycles],
            'active_interventions': [iv.name for iv in self._active_interventions],
            'total_laws_discovered': self.history.total_laws_discovered,
        }
        return json.dumps(data, indent=2, ensure_ascii=False, default=str)

    def save(self, path: str = "data/closed_loop_evolution.json"):
        """결과 저장."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            f.write(self.to_json())


class _ImprovedEngine(ConsciousnessEngine):
    """개입이 내장된 엔진."""

    def __init__(self, interventions: List[Intervention] = None, **kwargs):
        super().__init__(**kwargs)
        self._interventions = interventions or []

    def step(self, x_input=None, text=None):
        result = super().step(x_input=x_input, text=text)
        for iv in self._interventions:
            iv.apply(self, self._step)
        return result


# ══════════════════════════════════════════
# main() 데모
# ══════════════════════════════════════════

def main():
    print(f"\n{'▓' * 70}")
    print(f"  폐쇄 루프 법칙 진화 — 3 사이클 데모")
    print(f"{'▓' * 70}")

    evolver = ClosedLoopEvolver(max_cells=32, steps=300, repeats=3)
    evolver.run_cycles(n=3)
    evolver.print_evolution()
    evolver.save()
    print(f"\n  저장: data/closed_loop_evolution.json")


if __name__ == "__main__":
    main()
