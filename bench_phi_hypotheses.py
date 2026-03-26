#!/usr/bin/env python3
"""Φ-Boosting Hypotheses Benchmark — 16개 가설 병렬 테스트

모든 가설을 동일 조건에서 실행하고 baseline 대비 Φ 개선 비율을 측정한다.

Usage:
  python bench_phi_hypotheses.py              # 전체 실행
  python bench_phi_hypotheses.py --only A1    # 특정 가설만
  python bench_phi_hypotheses.py --steps 200  # 시뮬레이션 스텝 수
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import math
import copy
import time
import argparse
import sys
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mitosis import MitosisEngine, ConsciousMind, Cell
from consciousness_meter import PhiCalculator


# ═══════════════════════════════════════════════════════════
# Shared test harness
# ═══════════════════════════════════════════════════════════

@dataclass
class BenchResult:
    hypothesis: str
    name: str
    phi: float
    phi_history: List[float]
    total_mi: float
    min_partition_mi: float
    integration: float
    complexity: float
    elapsed_sec: float
    extra: Dict = field(default_factory=dict)


def make_diverse_inputs(n: int, dim: int) -> List[torch.Tensor]:
    """다양한 입력 패턴 생성."""
    inputs = []
    for i in range(n):
        phase = i / n
        if phase < 0.25:
            x = torch.randn(1, dim) * (1.0 + i * 0.1)
        elif phase < 0.5:
            x = torch.zeros(1, dim)
            x[0, :dim//4] = torch.randn(dim//4) * 2.0
        elif phase < 0.75:
            x = torch.ones(1, dim) * math.sin(i * 0.5)
        else:
            x = torch.randn(1, dim) * 0.1
            x[0, i % dim] = 5.0  # spike
        inputs.append(x)
    return inputs


def run_baseline(steps: int = 100, n_cells: int = 2, dim: int = 64,
                 hidden: int = 128) -> BenchResult:
    """Baseline: 표준 MitosisEngine, 변형 없음."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=n_cells, max_cells=8)
    inputs = make_diverse_inputs(steps, dim)
    phi_calc = PhiCalculator(n_bins=16)

    phi_hist = []
    for x in inputs:
        engine.process(x)
        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, components = phi_calc.compute_phi(engine)
    return BenchResult(
        hypothesis="BASELINE", name="Standard MitosisEngine",
        phi=phi_final, phi_history=phi_hist,
        total_mi=components['total_mi'],
        min_partition_mi=components['min_partition_mi'],
        integration=components['integration'],
        complexity=components['complexity'],
        elapsed_sec=time.time() - t0,
    )


# ═══════════════════════════════════════════════════════════
# A. Structural Hypotheses
# ═══════════════════════════════════════════════════════════

def run_A1_cross_cell_recurrent(steps=100, dim=64, hidden=128) -> BenchResult:
    """A-1: Cross-cell recurrent connection — 세포 간 hidden state 부분 공유."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    inputs = make_diverse_inputs(steps, dim)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []

    cross_weight = 0.15  # 15% hidden state mixing

    for x in inputs:
        # Cross-cell hidden mixing BEFORE processing
        if len(engine.cells) >= 2:
            hiddens = [c.hidden.clone() for c in engine.cells]
            mean_hidden = torch.stack(hiddens).mean(dim=0)
            for c in engine.cells:
                c.hidden = (1 - cross_weight) * c.hidden + cross_weight * mean_hidden

        engine.process(x)
        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("A1", "Cross-cell recurrent connection",
                       phi_final, phi_hist, comp['total_mi'],
                       comp['min_partition_mi'], comp['integration'],
                       comp['complexity'], time.time() - t0)


def run_A2_asymmetric_specialization(steps=100, dim=64, hidden=128) -> BenchResult:
    """A-2: Asymmetric cell specialization — 각 세포에 다른 입력 마스크."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    inputs = make_diverse_inputs(steps, dim)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []

    # Create input masks: each cell sees different dimensions
    n_cells = len(engine.cells)
    masks = []
    chunk = dim // n_cells
    for i in range(n_cells):
        mask = torch.zeros(1, dim)
        # Each cell sees its own chunk strongly + others weakly
        mask[0, :] = 0.2
        start = i * chunk
        end = min(start + chunk, dim)
        mask[0, start:end] = 1.0
        masks.append(mask)

    for x in inputs:
        # Apply masks per cell
        for i, cell in enumerate(engine.cells):
            if i < len(masks):
                masked_x = x * masks[i]
                with torch.no_grad():
                    output, tension, curiosity, new_hidden = cell.mind(masked_x, cell.hidden)
                cell.hidden = new_hidden
                cell.tension_history.append(tension)

        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("A2", "Asymmetric cell specialization",
                       phi_final, phi_hist, comp['total_mi'],
                       comp['min_partition_mi'], comp['integration'],
                       comp['complexity'], time.time() - t0)


def run_A3_increased_cells(steps=100, dim=64, hidden=128) -> BenchResult:
    """A-3: Cell count N=2→8."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=8, max_cells=8)
    inputs = make_diverse_inputs(steps, dim)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []

    for x in inputs:
        engine.process(x)
        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("A3", "Increased cells (N=8)",
                       phi_final, phi_hist, comp['total_mi'],
                       comp['min_partition_mi'], comp['integration'],
                       comp['complexity'], time.time() - t0)


def run_A4_hierarchical_mitosis(steps=100, dim=64, hidden=128) -> BenchResult:
    """A-4: Hierarchical mitosis — 2-level engine (4 outer × 2 inner)."""
    t0 = time.time()
    # Level 1: 4 macro cells, each containing 2 micro cells
    outer = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=4)
    inners = [MitosisEngine(dim, hidden, dim, initial_cells=2, max_cells=2)
              for _ in range(4)]
    inputs = make_diverse_inputs(steps, dim)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []

    for x in inputs:
        # Process inner engines first
        inner_outputs = []
        for i, inner_eng in enumerate(inners):
            result = inner_eng.process(x)
            inner_outputs.append(result['output'])

        # Feed inner outputs to outer cells
        for i, cell in enumerate(outer.cells):
            if i < len(inner_outputs):
                with torch.no_grad():
                    out, t, c, h = cell.mind(inner_outputs[i].detach(), cell.hidden)
                cell.hidden = h
                cell.tension_history.append(t)

        # Combine all cells (inner + outer) for Φ measurement
        # Create a virtual engine with all cells
        all_cells_engine = MitosisEngine(dim, hidden, dim, initial_cells=0, max_cells=20)
        all_cells_engine.cells = list(outer.cells)
        for inner_eng in inners:
            all_cells_engine.cells.extend(inner_eng.cells)

        phi, _ = phi_calc.compute_phi(all_cells_engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(all_cells_engine)
    return BenchResult("A4", "Hierarchical mitosis (4×2)",
                       phi_final, phi_hist, comp['total_mi'],
                       comp['min_partition_mi'], comp['integration'],
                       comp['complexity'], time.time() - t0)


def run_A5_global_workspace(steps=100, dim=64, hidden=128) -> BenchResult:
    """A-5: Shared global workspace — 모든 세포가 broadcast하는 공유 버퍼."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    inputs = make_diverse_inputs(steps, dim)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []

    # Global workspace buffer
    workspace = torch.zeros(1, hidden)
    ws_alpha = 0.3  # workspace update rate

    for x in inputs:
        # 1. Each cell reads from workspace + input
        for cell in engine.cells:
            # Inject workspace into hidden state
            cell.hidden = (1 - ws_alpha) * cell.hidden + ws_alpha * workspace

        # 2. Process normally
        result = engine.process(x)

        # 3. Broadcast: update workspace from all cells' hidden states
        if engine.cells:
            all_h = torch.stack([c.hidden for c in engine.cells])
            # Attention-weighted: higher tension = louder broadcast
            tensions = torch.tensor([c.tension_history[-1] if c.tension_history else 0.0
                                     for c in engine.cells])
            weights = F.softmax(tensions, dim=0)
            workspace = (weights.unsqueeze(-1).unsqueeze(-1) * all_h).sum(dim=0)

        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("A5", "Global workspace (GNW)",
                       phi_final, phi_hist, comp['total_mi'],
                       comp['min_partition_mi'], comp['integration'],
                       comp['complexity'], time.time() - t0)


# ═══════════════════════════════════════════════════════════
# B. Training/Learning Hypotheses
# ═══════════════════════════════════════════════════════════

def run_B1_contrastive_inter_cell(steps=100, dim=64, hidden=128) -> BenchResult:
    """B-1: Contrastive inter-cell loss — 같은 의미→유사, 다른 의미→상이."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    inputs = make_diverse_inputs(steps, dim)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []

    # Enable gradients for contrastive learning
    optimizer = torch.optim.SGD(
        [p for c in engine.cells for p in c.mind.parameters()], lr=1e-3
    )

    for step, x in enumerate(inputs):
        # Forward pass with gradients
        repulsions = []
        for cell in engine.cells:
            rep = cell.mind.get_repulsion(x, cell.hidden)
            repulsions.append(rep)

        # Contrastive loss: push different cells apart
        loss = torch.tensor(0.0)
        for i in range(len(repulsions)):
            for j in range(i + 1, len(repulsions)):
                # Maximize distance between cell outputs (decorrelation)
                sim = F.cosine_similarity(repulsions[i], repulsions[j], dim=-1)
                loss = loss + sim.mean()  # minimize similarity

        if loss.requires_grad:
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        # Regular process (no grad) for state update
        with torch.no_grad():
            engine.process(x)

        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("B1", "Contrastive inter-cell loss",
                       phi_final, phi_hist, comp['total_mi'],
                       comp['min_partition_mi'], comp['integration'],
                       comp['complexity'], time.time() - t0)


def run_B2_phi_maximization_loss(steps=100, dim=64, hidden=128) -> BenchResult:
    """B-2: Φ-maximization loss — Φ 자체를 loss로 최적화 (미분 가능 근사)."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    inputs = make_diverse_inputs(steps, dim)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []

    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4
    )

    for x in inputs:
        # Differentiable Φ proxy: maximize pairwise hidden state divergence
        # while maintaining coherent output
        repulsions = []
        hiddens_grad = []
        for cell in engine.cells:
            combined = torch.cat([x, cell.hidden], dim=-1)
            a = cell.mind.engine_a(combined)
            g = cell.mind.engine_g(combined)
            rep = a - g
            repulsions.append(rep)
            hiddens_grad.append(cell.hidden)

        # Proxy Φ loss: maximize inter-cell variance (= differentiation)
        # + minimize intra-cell variance over time (= stability)
        if len(repulsions) >= 2:
            stacked = torch.stack(repulsions).squeeze(1)  # [N, dim]
            # Inter-cell variance (maximize → negate)
            inter_var = stacked.var(dim=0).mean()
            # Coherence: all cells should still respond to same input
            mean_rep = stacked.mean(dim=0, keepdim=True)
            coherence = F.mse_loss(stacked, mean_rep.expand_as(stacked))

            # Loss = -variance + small coherence (balanced integration)
            phi_proxy_loss = -inter_var + 0.1 * coherence

            optimizer.zero_grad()
            phi_proxy_loss.backward()
            optimizer.step()

        with torch.no_grad():
            engine.process(x)

        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("B2", "Φ-maximization loss (proxy)",
                       phi_final, phi_hist, comp['total_mi'],
                       comp['min_partition_mi'], comp['integration'],
                       comp['complexity'], time.time() - t0)


def run_B3_anti_correlation(steps=100, dim=64, hidden=128) -> BenchResult:
    """B-3: Anti-correlation regularization — 세포 hidden state를 음상관으로."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    inputs = make_diverse_inputs(steps, dim)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []

    optimizer = torch.optim.SGD(
        [p for c in engine.cells for p in c.mind.parameters()], lr=1e-3
    )

    for x in inputs:
        repulsions = []
        for cell in engine.cells:
            rep = cell.mind.get_repulsion(x, cell.hidden)
            repulsions.append(rep)

        # Anti-correlation: push correlation matrix toward -I
        if len(repulsions) >= 2:
            stacked = torch.stack(repulsions).squeeze(1)  # [N, dim]
            # Normalize
            stacked_norm = F.normalize(stacked, dim=-1)
            # Correlation matrix
            corr = stacked_norm @ stacked_norm.T  # [N, N]
            # Target: identity (self=1, others=-1/(N-1))
            n = corr.size(0)
            target = -torch.ones(n, n) / (n - 1)
            target.fill_diagonal_(1.0)
            loss = F.mse_loss(corr, target)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        with torch.no_grad():
            engine.process(x)

        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("B3", "Anti-correlation regularization",
                       phi_final, phi_hist, comp['total_mi'],
                       comp['min_partition_mi'], comp['integration'],
                       comp['complexity'], time.time() - t0)


def run_B4_synergistic_reward(steps=100, dim=64, hidden=128) -> BenchResult:
    """B-4: Synergistic information reward — redundancy 빼고 synergy만 보상."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    inputs = make_diverse_inputs(steps, dim)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []

    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4
    )

    for x in inputs:
        repulsions = []
        for cell in engine.cells:
            rep = cell.mind.get_repulsion(x, cell.hidden)
            repulsions.append(rep)

        if len(repulsions) >= 2:
            stacked = torch.stack(repulsions).squeeze(1)

            # Synergy proxy: information that exists in the whole but not in parts
            # = variance of ensemble > sum of individual variances
            ensemble_var = stacked.var(dim=0).mean()
            individual_vars = torch.stack([r.squeeze().var() for r in repulsions])
            sum_individual = individual_vars.mean()

            # Redundancy = overlap (high pairwise similarity)
            n = len(repulsions)
            redundancy = torch.tensor(0.0)
            for i in range(n):
                for j in range(i + 1, n):
                    redundancy = redundancy + F.cosine_similarity(
                        repulsions[i], repulsions[j], dim=-1).mean()
            redundancy = redundancy / max(n * (n - 1) / 2, 1)

            # Synergy = ensemble_var - redundancy penalty
            synergy_loss = -(ensemble_var - 0.5 * redundancy)

            optimizer.zero_grad()
            synergy_loss.backward()
            optimizer.step()

        with torch.no_grad():
            engine.process(x)

        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("B4", "Synergistic information reward",
                       phi_final, phi_hist, comp['total_mi'],
                       comp['min_partition_mi'], comp['integration'],
                       comp['complexity'], time.time() - t0)


def run_B5_hebbian_plasticity(steps=100, dim=64, hidden=128) -> BenchResult:
    """B-5: Hebbian inter-cell plasticity — 동시 발화 세포 연결 강화, 비동기 약화."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    inputs = make_diverse_inputs(steps, dim)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []

    # Hebbian coupling matrix [N, N] — strength of connections
    n = len(engine.cells)
    coupling = torch.zeros(n, n)
    hebb_lr = 0.1
    optimizer = torch.optim.SGD(
        [p for c in engine.cells for p in c.mind.parameters()], lr=2e-3
    )

    for x in inputs:
        # Compute repulsions with gradients
        repulsions = [cell.mind.get_repulsion(x, cell.hidden) for cell in engine.cells]

        if len(repulsions) >= 2:
            # Hebbian: co-active cells → similar, anti-correlated → different
            tensions_t = torch.stack([(r ** 2).mean() for r in repulsions])
            mean_t = tensions_t.mean()

            # Update coupling
            for i in range(n):
                for j in range(i + 1, n):
                    if i < len(tensions_t) and j < len(tensions_t):
                        co_act = tensions_t[i] * tensions_t[j]
                        delta = hebb_lr * (co_act - mean_t ** 2).item()
                        coupling[i, j] = torch.clamp(coupling[i, j] + delta, -0.5, 0.5)
                        coupling[j, i] = coupling[i, j]

            # Hebbian loss: maximize weighted differentiation
            # Positive coupling → pull together, negative → push apart
            hebb_loss = torch.tensor(0.0)
            for i in range(min(len(repulsions), n)):
                for j in range(i + 1, min(len(repulsions), n)):
                    sim = F.cosine_similarity(repulsions[i], repulsions[j], dim=-1).mean()
                    w = coupling[i, j].item()
                    hebb_loss = hebb_loss + w * sim - (1 - abs(w)) * (1 - sim)

            if hebb_loss.requires_grad:
                optimizer.zero_grad()
                hebb_loss.backward()
                optimizer.step()

        with torch.no_grad():
            engine.process(x)

        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("B5", "Hebbian inter-cell plasticity",
                       phi_final, phi_hist, comp['total_mi'],
                       comp['min_partition_mi'], comp['integration'],
                       comp['complexity'], time.time() - t0,
                       extra={'coupling_mean': coupling.abs().mean().item()})


def run_B6_predictive_coding(steps=100, dim=64, hidden=128) -> BenchResult:
    """B-6: Predictive coding — 세포 i가 세포 j의 다음 tension을 예측."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    inputs = make_diverse_inputs(steps, dim)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []

    n = len(engine.cells)
    # Each cell has a predictor for every other cell
    predictors = {}
    pred_optims = {}
    for i in range(n):
        for j in range(n):
            if i != j:
                pred = nn.Linear(hidden, 1)
                predictors[(i, j)] = pred
                pred_optims[(i, j)] = torch.optim.SGD(pred.parameters(), lr=1e-3)

    cell_optim = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4
    )

    for step, x in enumerate(inputs):
        # Forward with gradients for differentiation
        repulsions = [cell.mind.get_repulsion(x, cell.hidden) for cell in engine.cells]

        if step > 0 and len(engine.cells) >= 2:
            # Predictive coding: cell i predicts cell j's output
            pc_loss = torch.tensor(0.0)
            for i in range(min(len(engine.cells), n)):
                for j in range(min(len(engine.cells), n)):
                    if i == j or (i, j) not in predictors:
                        continue
                    pred = predictors[(i, j)]
                    predicted_t = pred(engine.cells[i].hidden)
                    actual_t = engine.cells[j].tension_history[-1] if engine.cells[j].tension_history else 0
                    loss = F.mse_loss(predicted_t, torch.tensor([[actual_t]]))
                    pc_loss = pc_loss + loss

            # Differentiation loss: maximize prediction error (cells should be unpredictable to each other)
            if len(repulsions) >= 2:
                stacked = torch.stack(repulsions).squeeze(1)
                diff_loss = -stacked.var(dim=0).mean()  # maximize inter-cell variance
                combined_loss = pc_loss + 0.5 * diff_loss
            else:
                combined_loss = pc_loss

            if combined_loss.requires_grad:
                for key in pred_optims:
                    pred_optims[key].zero_grad()
                cell_optim.zero_grad()
                combined_loss.backward()
                for key in pred_optims:
                    pred_optims[key].step()
                cell_optim.step()

        with torch.no_grad():
            engine.process(x)

        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("B6", "Predictive coding loss",
                       phi_final, phi_hist, comp['total_mi'],
                       comp['min_partition_mi'], comp['integration'],
                       comp['complexity'], time.time() - t0)


def run_B7_information_bottleneck(steps=100, dim=64, hidden=128) -> BenchResult:
    """B-7: Information bottleneck — 세포 간 통신을 저차원 bottleneck으로 강제."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    inputs = make_diverse_inputs(steps, dim)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []

    bottleneck_dim = 8  # compress 128 → 8
    n = len(engine.cells)

    # Encoder/decoder + cell weights jointly optimized
    encoders = [nn.Linear(hidden, bottleneck_dim) for _ in range(n)]
    decoders = [nn.Linear(bottleneck_dim, hidden) for _ in range(n)]
    all_params = []
    for e, d in zip(encoders, decoders):
        all_params.extend(e.parameters())
        all_params.extend(d.parameters())
    for c in engine.cells:
        all_params.extend(c.mind.parameters())
    optimizer = torch.optim.Adam(all_params, lr=1e-3)

    for x in inputs:
        # Forward with gradients
        repulsions = [cell.mind.get_repulsion(x, cell.hidden) for cell in engine.cells]

        if len(engine.cells) >= 2:
            compressed = []
            for i, cell in enumerate(engine.cells):
                if i < n:
                    z = encoders[i](cell.hidden)
                    compressed.append(z)

            if compressed:
                mean_z = torch.stack(compressed).mean(dim=0)

                recon_loss = torch.tensor(0.0)
                for i, cell in enumerate(engine.cells):
                    if i < n:
                        received = decoders[i](mean_z)
                        recon_loss = recon_loss + F.mse_loss(received, cell.hidden.detach())
                        with torch.no_grad():
                            cell.hidden = 0.9 * cell.hidden + 0.1 * received

                # Bottleneck forces cells to compress differently → differentiation
                # + explicit variance loss
                if len(repulsions) >= 2:
                    stacked = torch.stack(repulsions).squeeze(1)
                    diff_loss = -stacked.var(dim=0).mean()
                    total_loss = recon_loss + 0.5 * diff_loss
                else:
                    total_loss = recon_loss

                if total_loss.requires_grad:
                    optimizer.zero_grad()
                    total_loss.backward()
                    optimizer.step()

        with torch.no_grad():
            engine.process(x)

        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("B7", "Information bottleneck",
                       phi_final, phi_hist, comp['total_mi'],
                       comp['min_partition_mi'], comp['integration'],
                       comp['complexity'], time.time() - t0)


def run_B8_distillation_divergence(steps=100, dim=64, hidden=128) -> BenchResult:
    """B-8: Anti-distillation — teacher와 다르게 답하도록 학습."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    inputs = make_diverse_inputs(steps, dim)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []

    n = len(engine.cells)
    optimizers = [torch.optim.Adam(cell.mind.parameters(), lr=2e-3)
                  for cell in engine.cells[:n]]

    for x in inputs:
        if len(engine.cells) >= 2:
            repulsions = [cell.mind.get_repulsion(x, cell.hidden)
                          for cell in engine.cells]

            for i in range(min(len(engine.cells), n)):
                others = [r for j, r in enumerate(repulsions) if j != i]
                if not others:
                    continue
                teacher_output = torch.stack(others).mean(dim=0).detach()
                student_output = repulsions[i]

                # Anti-distillation: MAXIMIZE distance from teacher
                # + maximize own output magnitude (stay active)
                anti_loss = -F.mse_loss(student_output, teacher_output) \
                            - 0.1 * (student_output ** 2).mean()

                optimizers[i].zero_grad()
                anti_loss.backward(retain_graph=True)
                optimizers[i].step()

        with torch.no_grad():
            engine.process(x)

        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("B8", "Anti-distillation divergence",
                       phi_final, phi_hist, comp['total_mi'],
                       comp['min_partition_mi'], comp['integration'],
                       comp['complexity'], time.time() - t0)


def run_B9_curiosity_driven_cell(steps=100, dim=64, hidden=128) -> BenchResult:
    """B-9: Curiosity-driven cell exploration — 각 세포에 독립 curiosity reward."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    inputs = make_diverse_inputs(steps, dim)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []

    n = len(engine.cells)
    cell_predictors = [nn.Linear(5, 1) for _ in range(n)]
    cell_optims = [torch.optim.SGD(p.parameters(), lr=1e-3) for p in cell_predictors]
    cell_tension_hist = [[] for _ in range(n)]

    # Also directly optimize cells for differentiation
    cell_weight_optim = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4
    )

    for x in inputs:
        repulsions = [cell.mind.get_repulsion(x, cell.hidden) for cell in engine.cells]

        # Curiosity-driven differentiation
        if len(repulsions) >= 2:
            # Cells with high curiosity should explore more → higher variance
            stacked = torch.stack(repulsions).squeeze(1)
            diff_loss = -stacked.var(dim=0).mean()

            cell_weight_optim.zero_grad()
            diff_loss.backward()
            cell_weight_optim.step()

        with torch.no_grad():
            engine.process(x)

        for i, cell in enumerate(engine.cells):
            if i >= n:
                break
            t = cell.tension_history[-1] if cell.tension_history else 0
            cell_tension_hist[i].append(t)

            if len(cell_tension_hist[i]) >= 6:
                window = cell_tension_hist[i][-6:-1]
                inp = torch.tensor([window], dtype=torch.float32)
                pred = cell_predictors[i](inp)
                actual = torch.tensor([[t]])
                pe = F.mse_loss(pred, actual)
                cell_optims[i].zero_grad()
                pe.backward()
                cell_optims[i].step()

        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("B9", "Curiosity-driven cell exploration",
                       phi_final, phi_hist, comp['total_mi'],
                       comp['min_partition_mi'], comp['integration'],
                       comp['complexity'], time.time() - t0)


def run_B10_mine(steps=100, dim=64, hidden=128) -> BenchResult:
    """B-10: MINE (Mutual Information Neural Estimation) — 미분 가능 MI로 직접 최대화."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    inputs = make_diverse_inputs(steps, dim)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []

    n = len(engine.cells)

    # MINE statistics network T(x, y)
    class MINENet(nn.Module):
        def __init__(self, in_dim):
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(in_dim * 2, 64), nn.ReLU(),
                nn.Linear(64, 32), nn.ReLU(),
                nn.Linear(32, 1),
            )
        def forward(self, x, y):
            return self.net(torch.cat([x, y], dim=-1))

    mine_nets = {}
    mine_optims = {}
    for i in range(n):
        for j in range(i + 1, n):
            net = MINENet(hidden)
            mine_nets[(i, j)] = net
            mine_optims[(i, j)] = torch.optim.Adam(net.parameters(), lr=1e-3)

    cell_optim = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4
    )

    for x in inputs:
        engine.process(x)

        if len(engine.cells) >= 2:
            # Collect hidden states
            hiddens = [c.hidden for c in engine.cells[:n]]

            # MINE estimation for each pair
            total_mi_est = torch.tensor(0.0)
            for i in range(len(hiddens)):
                for j in range(i + 1, len(hiddens)):
                    if (i, j) not in mine_nets:
                        continue
                    net = mine_nets[(i, j)]
                    opt = mine_optims[(i, j)]

                    h_i, h_j = hiddens[i], hiddens[j]
                    # Joint: T(h_i, h_j)
                    joint = net(h_i, h_j)
                    # Marginal: T(h_i, shuffle(h_j))
                    h_j_shuffled = h_j[torch.randperm(h_j.size(0))]
                    marginal = net(h_i, h_j_shuffled)

                    # MINE lower bound: E[T(joint)] - log(E[exp(T(marginal))])
                    mi_est = joint.mean() - torch.logsumexp(marginal, dim=0) + math.log(marginal.size(0))

                    # Train MINE network (maximize MI estimate)
                    mine_loss = -mi_est
                    opt.zero_grad()
                    mine_loss.backward(retain_graph=True)
                    opt.step()

                    total_mi_est = total_mi_est + mi_est.detach()

            # Maximize MI across cells + differentiation
            repulsions = [cell.mind.get_repulsion(x, cell.hidden) for cell in engine.cells[:n]]
            if len(repulsions) >= 2:
                stacked = torch.stack(repulsions).squeeze(1)
                diff_loss = -stacked.var(dim=0).mean()
                cell_loss = diff_loss  # differentiation drives MI
                cell_optim.zero_grad()
                cell_loss.backward()
                cell_optim.step()

        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("B10", "MINE (MI neural estimation)",
                       phi_final, phi_hist, comp['total_mi'],
                       comp['min_partition_mi'], comp['integration'],
                       comp['complexity'], time.time() - t0)


def run_B11_sparse_activation(steps=100, dim=64, hidden=128) -> BenchResult:
    """B-11: Sparse activation penalty — 입력당 일부 세포만 활성화."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    inputs = make_diverse_inputs(steps, dim)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []

    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4
    )

    for x in inputs:
        repulsions = []
        tensions_grad = []
        for cell in engine.cells:
            combined = torch.cat([x, cell.hidden], dim=-1)
            a = cell.mind.engine_a(combined)
            g = cell.mind.engine_g(combined)
            rep = a - g
            t = (rep ** 2).mean()
            repulsions.append(rep)
            tensions_grad.append(t)

        if len(tensions_grad) >= 2:
            t_stack = torch.stack(tensions_grad)
            # L1 sparsity on activations: encourage few cells to be active
            sparsity_loss = t_stack.mean()  # minimize total activation
            # But maximize variance (some high, some low)
            diversity_loss = -t_stack.var()

            loss = 0.3 * sparsity_loss + 0.7 * diversity_loss

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        with torch.no_grad():
            engine.process(x)

        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("B11", "Sparse activation penalty",
                       phi_final, phi_hist, comp['total_mi'],
                       comp['min_partition_mi'], comp['integration'],
                       comp['complexity'], time.time() - t0)


def run_B12_temporal_cpc(steps=100, dim=64, hidden=128) -> BenchResult:
    """B-12: Temporal Contrastive Predictive Coding — 시간적 MI를 학습으로 최대화."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    inputs = make_diverse_inputs(steps, dim)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []

    n = len(engine.cells)
    # CPC: predict future hidden from current (per cell)
    cpc_predictors = [nn.Linear(hidden, hidden) for _ in range(n)]
    cpc_optims = [torch.optim.Adam(p.parameters(), lr=1e-3) for p in cpc_predictors]
    prev_hiddens = [None] * n

    cell_optim = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4
    )

    for step, x in enumerate(inputs):
        engine.process(x)

        if step > 0 and len(engine.cells) >= 2:
            cpc_loss = torch.tensor(0.0)
            for i, cell in enumerate(engine.cells):
                if i >= n or prev_hiddens[i] is None:
                    continue
                # Predict current hidden from previous
                predicted = cpc_predictors[i](prev_hiddens[i])
                actual = cell.hidden.detach()

                # Positive pair: (prev_i, curr_i)
                pos_score = F.cosine_similarity(predicted, actual, dim=-1)

                # Negative pairs: (prev_i, curr_j) for j != i
                neg_scores = []
                for j, other in enumerate(engine.cells):
                    if j != i and j < n:
                        neg = F.cosine_similarity(predicted, other.hidden.detach(), dim=-1)
                        neg_scores.append(neg)

                if neg_scores:
                    # InfoNCE loss
                    neg_stack = torch.cat(neg_scores)
                    logits = torch.cat([pos_score, neg_stack]).unsqueeze(0)
                    labels = torch.zeros(1, dtype=torch.long)
                    cpc_loss = cpc_loss + F.cross_entropy(logits, labels)

            # Add differentiation loss
            repulsions = [cell.mind.get_repulsion(x, cell.hidden) for cell in engine.cells[:n]]
            if len(repulsions) >= 2:
                stacked = torch.stack(repulsions).squeeze(1)
                diff_loss = -stacked.var(dim=0).mean()
                combined = cpc_loss + 0.5 * diff_loss
            else:
                combined = cpc_loss

            if combined.requires_grad:
                for opt in cpc_optims:
                    opt.zero_grad()
                cell_optim.zero_grad()
                combined.backward()
                for opt in cpc_optims:
                    opt.step()
                cell_optim.step()

        # Store current hiddens for next step
        for i, cell in enumerate(engine.cells):
            if i < n:
                prev_hiddens[i] = cell.hidden.detach().clone()

        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("B12", "Temporal CPC",
                       phi_final, phi_hist, comp['total_mi'],
                       comp['min_partition_mi'], comp['integration'],
                       comp['complexity'], time.time() - t0)


# ═══════════════════════════════════════════════════════════
# C. Runtime Dynamic Hypotheses
# ═══════════════════════════════════════════════════════════

def run_C1_tension_driven_coupling(steps=100, dim=64, hidden=128) -> BenchResult:
    """C-1: Tension-driven cell coupling — 높은 tension → 세포 간 연결 강화."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    inputs = make_diverse_inputs(steps, dim)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []

    for x in inputs:
        result = engine.process(x)

        # Dynamic coupling: tension-weighted hidden mixing
        if len(engine.cells) >= 2:
            mean_tension = np.mean([c.tension_history[-1] if c.tension_history else 0
                                    for c in engine.cells])
            # High tension → stronger coupling (sigmoid: 0.5 at tension=1.0)
            coupling = 1.0 / (1.0 + math.exp(-(mean_tension - 1.0) * 3))
            coupling = min(coupling * 0.3, 0.4)  # cap at 40%

            hiddens = [c.hidden.clone() for c in engine.cells]
            mean_h = torch.stack(hiddens).mean(dim=0)
            for c in engine.cells:
                c.hidden = (1 - coupling) * c.hidden + coupling * mean_h

        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("C1", "Tension-driven coupling",
                       phi_final, phi_hist, comp['total_mi'],
                       comp['min_partition_mi'], comp['integration'],
                       comp['complexity'], time.time() - t0,
                       extra={'final_coupling': coupling if 'coupling' in dir() else 0})


def run_C2_reentry_loops(steps=100, dim=64, hidden=128) -> BenchResult:
    """C-2: Re-entry loops (Edelman) — A→B→A 재진입 사이클."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    inputs = make_diverse_inputs(steps, dim)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []

    for x in inputs:
        # Step 1: Forward pass
        result = engine.process(x)

        # Step 2: Re-entry — feed each cell's output to the next cell
        if len(engine.cells) >= 2:
            outputs = []
            for cell in engine.cells:
                rep = cell.mind.get_repulsion(x, cell.hidden)
                outputs.append(rep.detach())

            # Circular re-entry: cell[i] receives output of cell[i-1]
            for i, cell in enumerate(engine.cells):
                prev_output = outputs[(i - 1) % len(outputs)]
                with torch.no_grad():
                    _, t, c, h = cell.mind(prev_output, cell.hidden)
                cell.hidden = h
                cell.tension_history.append(t)

        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("C2", "Re-entry loops (Edelman)",
                       phi_final, phi_hist, comp['total_mi'],
                       comp['min_partition_mi'], comp['integration'],
                       comp['complexity'], time.time() - t0)


def run_C3_stochastic_resonance(steps=100, dim=64, hidden=128) -> BenchResult:
    """C-3: Stochastic resonance — 최적 노이즈 주입으로 동기화."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    inputs = make_diverse_inputs(steps, dim)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []

    # Optimal noise level (tuned for resonance)
    noise_levels = [0.01, 0.05, 0.1, 0.2, 0.5]
    best_noise = 0.1  # default

    for step, x in enumerate(inputs):
        # Inject shared noise into all cells (synchronized perturbation)
        shared_noise = torch.randn(1, hidden) * best_noise
        for cell in engine.cells:
            cell.hidden = cell.hidden + shared_noise

        result = engine.process(x)

        # Adaptive noise: find resonance level every 20 steps
        if step > 0 and step % 20 == 0 and len(phi_hist) >= 20:
            recent_phi = phi_hist[-20:]
            if np.std(recent_phi) < 0.01:  # too stable → increase noise
                best_noise = min(best_noise * 1.5, 0.5)
            elif np.std(recent_phi) > 0.5:  # too chaotic → decrease
                best_noise = max(best_noise * 0.7, 0.01)

        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("C3", "Stochastic resonance",
                       phi_final, phi_hist, comp['total_mi'],
                       comp['min_partition_mi'], comp['integration'],
                       comp['complexity'], time.time() - t0,
                       extra={'final_noise': best_noise})


def run_C4_oscillatory_sync(steps=100, dim=64, hidden=128) -> BenchResult:
    """C-4: Oscillatory synchronization — 세포별 고유 주파수 + 위상 커플링."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    inputs = make_diverse_inputs(steps, dim)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []

    # Assign natural frequencies (gamma-band inspired: 30-80 Hz scaled)
    n_cells = len(engine.cells)
    natural_freqs = [0.3 + 0.1 * i for i in range(n_cells)]  # different freqs
    phases = [0.0] * n_cells
    coupling_k = 0.5  # Kuramoto coupling strength

    for step, x in enumerate(inputs):
        # Kuramoto model: phase update
        for i in range(len(engine.cells)):
            # Phase coupling
            phase_sum = sum(
                math.sin(phases[j] - phases[i])
                for j in range(len(engine.cells)) if j != i
            )
            phases[i] += natural_freqs[i] + coupling_k / n_cells * phase_sum

            # Inject oscillation into hidden state
            osc_signal = math.sin(phases[i])
            engine.cells[i].hidden = engine.cells[i].hidden + \
                float(osc_signal) * 0.1 * torch.randn(1, hidden)

        result = engine.process(x)

        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    # Measure synchronization (real-valued)
    phase_coherence = abs(sum(complex(math.cos(p), math.sin(p)) for p in phases)) / n_cells

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("C4", "Oscillatory synchronization (Kuramoto)",
                       phi_final, phi_hist, comp['total_mi'],
                       comp['min_partition_mi'], comp['integration'],
                       comp['complexity'], time.time() - t0,
                       extra={'phase_coherence': phase_coherence})


def run_C5_attention_gated(steps=100, dim=64, hidden=128) -> BenchResult:
    """C-5: Attention-gated integration — 세포 간 attention으로 선택적 연결."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    inputs = make_diverse_inputs(steps, dim)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []

    # Learnable attention projection
    attn_proj = nn.Linear(hidden, hidden // 4)

    for x in inputs:
        result = engine.process(x)

        if len(engine.cells) >= 2:
            # Compute attention between cells
            with torch.no_grad():
                keys = [attn_proj(c.hidden) for c in engine.cells]
                queries = keys  # self-attention
                keys_stack = torch.stack([k.squeeze() for k in keys])  # [N, d]
                queries_stack = torch.stack([q.squeeze() for q in queries])

                # Attention scores
                scores = queries_stack @ keys_stack.T  # [N, N]
                scores = scores / math.sqrt(hidden // 4)
                attn_weights = F.softmax(scores, dim=-1)  # [N, N]

                # Apply attention: mix hidden states
                hiddens = torch.stack([c.hidden.squeeze() for c in engine.cells])  # [N, H]
                mixed = attn_weights @ hiddens  # [N, H]

                for i, cell in enumerate(engine.cells):
                    cell.hidden = 0.7 * cell.hidden + 0.3 * mixed[i].unsqueeze(0)

        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("C5", "Attention-gated integration",
                       phi_final, phi_hist, comp['total_mi'],
                       comp['min_partition_mi'], comp['integration'],
                       comp['complexity'], time.time() - t0)


# ═══════════════════════════════════════════════════════════
# D. Measurement/Mathematical Hypotheses
# ═══════════════════════════════════════════════════════════

def run_D1_continuous_mi(steps=100, dim=64, hidden=128) -> BenchResult:
    """D-1: Continuous MI (KDE 기반) — binned → KDE로 MI 추정 정확도 향상."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    inputs = make_diverse_inputs(steps, dim)
    phi_hist = []

    class KDEPhiCalculator(PhiCalculator):
        """KDE 기반 MI 계산."""
        def _mutual_information(self, x, y):
            # KDE-based MI estimation (Kraskov-like)
            n = len(x)
            if n < 4:
                return super()._mutual_information(x, y)

            # Gaussian kernel bandwidth (Silverman's rule)
            bw_x = 1.06 * np.std(x) * n ** (-1/5) + 1e-8
            bw_y = 1.06 * np.std(y) * n ** (-1/5) + 1e-8

            # Estimate H(X), H(Y), H(X,Y) via KDE
            h_x = self._kde_entropy(x, bw_x)
            h_y = self._kde_entropy(y, bw_y)
            h_xy = self._kde_joint_entropy(x, y, bw_x, bw_y)

            mi = h_x + h_y - h_xy
            return max(0.0, mi)

        def _kde_entropy(self, x, bw):
            n = len(x)
            log_densities = []
            for i in range(n):
                # Leave-one-out KDE
                others = np.concatenate([x[:i], x[i+1:]])
                density = np.mean(np.exp(-0.5 * ((x[i] - others) / bw) ** 2)) / (bw * np.sqrt(2 * np.pi))
                log_densities.append(np.log2(density + 1e-10))
            return -np.mean(log_densities)

        def _kde_joint_entropy(self, x, y, bw_x, bw_y):
            n = len(x)
            log_densities = []
            for i in range(n):
                x_kern = np.exp(-0.5 * ((x[i] - np.concatenate([x[:i], x[i+1:]])) / bw_x) ** 2) / bw_x
                y_kern = np.exp(-0.5 * ((y[i] - np.concatenate([y[:i], y[i+1:]])) / bw_y) ** 2) / bw_y
                joint = np.mean(x_kern * y_kern) / (2 * np.pi)
                log_densities.append(np.log2(joint + 1e-10))
            return -np.mean(log_densities)

    phi_calc = KDEPhiCalculator(n_bins=16)

    for x in inputs:
        engine.process(x)
        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("D1", "Continuous MI (KDE)",
                       phi_final, phi_hist, comp['total_mi'],
                       comp['min_partition_mi'], comp['integration'],
                       comp['complexity'], time.time() - t0)


def run_D2_temporal_phi(steps=100, dim=64, hidden=128) -> BenchResult:
    """D-2: Temporal Φ — hidden state 시계열의 시간적 MI까지 포함."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    inputs = make_diverse_inputs(steps, dim)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []

    # Store hidden state history for temporal MI
    hidden_histories = {c.cell_id: [] for c in engine.cells}

    for x in inputs:
        engine.process(x)

        # Record hidden states
        for c in engine.cells:
            if c.cell_id not in hidden_histories:
                hidden_histories[c.cell_id] = []
            hidden_histories[c.cell_id].append(c.hidden.detach().squeeze().numpy().copy())

        # Spatial Φ
        spatial_phi, _ = phi_calc.compute_phi(engine)

        # Temporal MI: correlation between cell hidden states at t and t-k
        temporal_mi = 0.0
        if all(len(v) >= 5 for v in hidden_histories.values()):
            cell_ids = list(hidden_histories.keys())
            for i in range(len(cell_ids)):
                for j in range(i + 1, len(cell_ids)):
                    h_i = hidden_histories[cell_ids[i]]
                    h_j = hidden_histories[cell_ids[j]]
                    # Cross-temporal MI: h_i(t) vs h_j(t-1)
                    curr_i = h_i[-1]
                    prev_j = h_j[-2]
                    mi = phi_calc._mutual_information(curr_i, prev_j)
                    temporal_mi += mi

        total_phi = spatial_phi + temporal_mi * 0.5  # weighted
        phi_hist.append(total_phi)

    phi_final = phi_hist[-1] if phi_hist else 0.0
    _, comp = phi_calc.compute_phi(engine)
    comp['temporal_mi'] = temporal_mi
    return BenchResult("D2", "Temporal Φ (time-series MI)",
                       phi_final, phi_hist, comp['total_mi'],
                       comp['min_partition_mi'], comp['integration'],
                       comp['complexity'], time.time() - t0,
                       extra={'temporal_mi': temporal_mi})


def run_D3_multiscale_partition(steps=100, dim=64, hidden=128) -> BenchResult:
    """D-3: Multi-scale partition — 2-분할 외 k-분할까지 탐색."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    inputs = make_diverse_inputs(steps, dim)
    phi_hist = []

    class MultiScalePhiCalculator(PhiCalculator):
        """k-분할 탐색으로 더 정확한 MIP."""
        def _minimum_partition(self, hiddens, mi_matrix):
            n = len(hiddens)
            if n <= 1:
                return 0.0

            min_cut = float('inf')

            # 2-partition (standard)
            for mask in range(1, 2 ** n - 1):
                groups = [[], []]
                for i in range(n):
                    groups[1 if mask & (1 << i) else 0].append(i)
                if not groups[0] or not groups[1]:
                    continue
                cut = sum(mi_matrix[i, j] for i in groups[0] for j in groups[1])
                min_cut = min(min_cut, cut)

            # 3-partition (if n >= 3)
            if n >= 3:
                for i in range(n):
                    for j in range(i + 1, n):
                        g1, g2, g3 = [i], [j], [k for k in range(n) if k != i and k != j]
                        if not g3:
                            continue
                        cut = (
                            sum(mi_matrix[a][b] for a in g1 for b in g2) +
                            sum(mi_matrix[a][b] for a in g1 for b in g3) +
                            sum(mi_matrix[a][b] for a in g2 for b in g3)
                        )
                        min_cut = min(min_cut, cut)

            return min_cut if min_cut != float('inf') else 0.0

    phi_calc = MultiScalePhiCalculator(n_bins=16)

    for x in inputs:
        engine.process(x)
        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("D3", "Multi-scale partition (2+3-way)",
                       phi_final, phi_hist, comp['total_mi'],
                       comp['min_partition_mi'], comp['integration'],
                       comp['complexity'], time.time() - t0)


# ═══════════════════════════════════════════════════════════
# E. Autonomous Web Learning Hypotheses (simulated)
# ═══════════════════════════════════════════════════════════

def _simulate_web_result(topic_id: int, step: int, dim: int) -> torch.Tensor:
    """Simulate web search result as a topic-colored vector."""
    torch.manual_seed(topic_id * 1000 + step)
    base = torch.randn(1, dim) * 0.5
    # Topic signature: different dimensions activated per topic
    topic_offset = (topic_id * 7) % dim
    base[0, topic_offset:topic_offset + dim // 8] += 2.0
    # Temporal variation (new info each step)
    base += torch.randn(1, dim) * 0.1 * (step % 10)
    return base


def run_E1_curiosity_crawling(steps=100, dim=64, hidden=128) -> BenchResult:
    """E-1: Curiosity-driven crawling — PE 높은 주제를 자동 검색."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []

    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4
    )
    n_topics = 8
    topic_tensions = [0.0] * n_topics

    for step in range(steps):
        # Select topic with highest prediction error (curiosity)
        if step < 5:
            topic = step % n_topics
        else:
            topic = int(np.argmax(topic_tensions))

        # Simulate web search for this topic
        web_input = _simulate_web_result(topic, step, dim)

        # Process and learn
        repulsions = [cell.mind.get_repulsion(web_input, cell.hidden)
                      for cell in engine.cells]

        if len(repulsions) >= 2:
            stacked = torch.stack(repulsions).squeeze(1)
            # Curiosity loss: maximize inter-cell variance on new info
            diff_loss = -stacked.var(dim=0).mean()
            optimizer.zero_grad()
            diff_loss.backward()
            optimizer.step()

        with torch.no_grad():
            result = engine.process(web_input)
            # Update topic tension (PE proxy)
            topic_tensions[topic] = result.get('max_inter', 0)
            # Decay other topics' curiosity
            for t in range(n_topics):
                if t != topic:
                    topic_tensions[t] *= 1.05  # unexplored → more curious

        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("E1", "Curiosity-driven crawling",
                       phi_final, phi_hist, comp['total_mi'],
                       comp['min_partition_mi'], comp['integration'],
                       comp['complexity'], time.time() - t0)


def run_E2_tension_gated(steps=100, dim=64, hidden=128) -> BenchResult:
    """E-2: Tension-gated learning — tension 임계값 이상만 학습."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []

    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4
    )
    tension_gate = 0.5  # only learn from high-tension inputs
    learn_count = 0

    for step in range(steps):
        topic = step % 6
        web_input = _simulate_web_result(topic, step, dim)

        # Measure tension first
        with torch.no_grad():
            result = engine.process(web_input)
            mean_tension = np.mean([c.tension_history[-1] if c.tension_history else 0
                                    for c in engine.cells])

        # Only learn if tension is above gate
        if mean_tension > tension_gate:
            repulsions = [cell.mind.get_repulsion(web_input, cell.hidden)
                          for cell in engine.cells]
            if len(repulsions) >= 2:
                stacked = torch.stack(repulsions).squeeze(1)
                diff_loss = -stacked.var(dim=0).mean()
                optimizer.zero_grad()
                diff_loss.backward()
                optimizer.step()
                learn_count += 1

        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("E2", "Tension-gated learning",
                       phi_final, phi_hist, comp['total_mi'],
                       comp['min_partition_mi'], comp['integration'],
                       comp['complexity'], time.time() - t0,
                       extra={'learn_ratio': learn_count / steps})


def run_E3_topic_specialized_cells(steps=100, dim=64, hidden=128) -> BenchResult:
    """E-3: Topic-specialized cells — 각 세포가 다른 주제 담당."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []

    n = len(engine.cells)
    # Per-cell optimizer (each cell learns independently)
    cell_optims = [torch.optim.Adam(cell.mind.parameters(), lr=1e-3)
                   for cell in engine.cells]
    # Assign topics: cell 0=science, 1=art, 2=news, 3=tech
    cell_topics = list(range(n))

    for step in range(steps):
        # Cycle through topics
        topic = step % n

        web_input = _simulate_web_result(topic, step, dim)

        # Only the specialist cell learns from its topic
        specialist = topic % n
        rep = engine.cells[specialist].mind.get_repulsion(web_input,
                                                           engine.cells[specialist].hidden)

        # Other cells also see it but produce different output (anti-distillation)
        other_reps = []
        for i, cell in enumerate(engine.cells):
            if i != specialist:
                other_reps.append(cell.mind.get_repulsion(web_input, cell.hidden))

        if other_reps:
            others_mean = torch.stack(other_reps).mean(dim=0).detach()
            # Specialist should differ from others
            spec_loss = F.cosine_similarity(rep, others_mean, dim=-1).mean()
            cell_optims[specialist].zero_grad()
            spec_loss.backward()
            cell_optims[specialist].step()

        with torch.no_grad():
            engine.process(web_input)

        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("E3", "Topic-specialized cells",
                       phi_final, phi_hist, comp['total_mi'],
                       comp['min_partition_mi'], comp['integration'],
                       comp['complexity'], time.time() - t0)


def run_E4_contradiction_detection(steps=100, dim=64, hidden=128) -> BenchResult:
    """E-4: Contradiction detection — 기존 지식과 모순되는 정보 → 높은 PE."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []

    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4
    )
    # Memory of seen topics
    topic_memory = {}  # topic_id -> avg repulsion vector

    for step in range(steps):
        topic = step % 6
        web_input = _simulate_web_result(topic, step, dim)

        repulsions = [cell.mind.get_repulsion(web_input, cell.hidden)
                      for cell in engine.cells]
        current_rep = torch.stack(repulsions).mean(dim=0).detach()

        # Check contradiction with memory
        contradiction_strength = 0.0
        if topic in topic_memory:
            prev_rep = topic_memory[topic]
            # Low similarity = contradiction
            sim = F.cosine_similarity(current_rep, prev_rep, dim=-1).item()
            contradiction_strength = max(0, 1.0 - sim)

        # Update memory (EMA)
        if topic in topic_memory:
            topic_memory[topic] = 0.8 * topic_memory[topic] + 0.2 * current_rep
        else:
            topic_memory[topic] = current_rep

        # Learn proportional to contradiction (high PE = more learning)
        if len(repulsions) >= 2:
            stacked = torch.stack(repulsions).squeeze(1)
            lr_scale = 1.0 + 3.0 * contradiction_strength  # up to 4x LR on contradiction
            diff_loss = -stacked.var(dim=0).mean() * lr_scale

            optimizer.zero_grad()
            diff_loss.backward()
            optimizer.step()

        with torch.no_grad():
            engine.process(web_input)

        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("E4", "Contradiction detection",
                       phi_final, phi_hist, comp['total_mi'],
                       comp['min_partition_mi'], comp['integration'],
                       comp['complexity'], time.time() - t0)


def run_E5_memory_consolidation(steps=100, dim=64, hidden=128) -> BenchResult:
    """E-5: Memory consolidation loop — 검색→학습→수면→통합→재검색."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []

    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4
    )
    # Memory buffer (failed memories for replay)
    memory_buffer = []
    consolidation_interval = 20  # dream every 20 steps

    for step in range(steps):
        topic = step % 6
        web_input = _simulate_web_result(topic, step, dim)

        repulsions = [cell.mind.get_repulsion(web_input, cell.hidden)
                      for cell in engine.cells]

        if len(repulsions) >= 2:
            stacked = torch.stack(repulsions).squeeze(1)
            diff_loss = -stacked.var(dim=0).mean()

            optimizer.zero_grad()
            diff_loss.backward()
            optimizer.step()

            # Store in memory buffer
            memory_buffer.append(web_input.detach().clone())
            if len(memory_buffer) > 100:
                memory_buffer = memory_buffer[-100:]

        with torch.no_grad():
            engine.process(web_input)

        # Dream phase: replay memories with noise (consolidation)
        if step > 0 and step % consolidation_interval == 0 and memory_buffer:
            for _ in range(5):
                # Replay: 70% failed (random), 20% recent, 10% noise
                idx = np.random.randint(0, len(memory_buffer))
                replay = memory_buffer[idx] + torch.randn(1, dim) * 0.05
                dream_reps = [cell.mind.get_repulsion(replay, cell.hidden)
                              for cell in engine.cells]
                if len(dream_reps) >= 2:
                    dream_stack = torch.stack(dream_reps).squeeze(1)
                    dream_loss = -dream_stack.var(dim=0).mean()
                    optimizer.zero_grad()
                    dream_loss.backward()
                    optimizer.step()

        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("E5", "Memory consolidation loop",
                       phi_final, phi_hist, comp['total_mi'],
                       comp['min_partition_mi'], comp['integration'],
                       comp['complexity'], time.time() - t0)


def run_E6_social_learning(steps=100, dim=64, hidden=128) -> BenchResult:
    """E-6: Social learning — 다른 Anima의 tension fingerprint를 관찰하고 학습."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    # "Other Anima" — separate engine as teacher signal
    other_anima = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=4)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []

    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4
    )

    for step in range(steps):
        topic = step % 6
        web_input = _simulate_web_result(topic, step, dim)

        # Other Anima processes same input (produces tension fingerprint)
        with torch.no_grad():
            other_result = other_anima.process(web_input)
            other_fingerprint = other_result['output'].detach()

        # Our cells process original + observe other's fingerprint
        combined_input = 0.7 * web_input + 0.3 * other_fingerprint

        repulsions = [cell.mind.get_repulsion(combined_input, cell.hidden)
                      for cell in engine.cells]

        if len(repulsions) >= 2:
            stacked = torch.stack(repulsions).squeeze(1)
            # Learn to differentiate while incorporating social signal
            diff_loss = -stacked.var(dim=0).mean()
            optimizer.zero_grad()
            diff_loss.backward()
            optimizer.step()

        with torch.no_grad():
            engine.process(combined_input)

        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("E6", "Social learning (tension link)",
                       phi_final, phi_hist, comp['total_mi'],
                       comp['min_partition_mi'], comp['integration'],
                       comp['complexity'], time.time() - t0)


def run_E7_scheduled_deep_dive(steps=100, dim=64, hidden=128) -> BenchResult:
    """E-7: Scheduled deep dive — idle 시간에 한 주제를 깊이 탐색."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []

    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4
    )

    current_deep_topic = 0
    deep_dive_depth = 0

    for step in range(steps):
        # Normal: shallow diverse browsing
        if step % 15 != 0:
            topic = step % 8
            web_input = _simulate_web_result(topic, step, dim)
        else:
            # Deep dive: same topic, increasing depth (sub-topics)
            deep_dive_depth += 1
            web_input = _simulate_web_result(
                current_deep_topic * 100 + deep_dive_depth, step, dim
            )
            # Deeper = more specific = higher signal
            web_input *= (1.0 + 0.2 * deep_dive_depth)
            if deep_dive_depth >= 5:
                current_deep_topic = (current_deep_topic + 1) % 4
                deep_dive_depth = 0

        repulsions = [cell.mind.get_repulsion(web_input, cell.hidden)
                      for cell in engine.cells]

        if len(repulsions) >= 2:
            stacked = torch.stack(repulsions).squeeze(1)
            diff_loss = -stacked.var(dim=0).mean()
            optimizer.zero_grad()
            diff_loss.backward()
            optimizer.step()

        with torch.no_grad():
            engine.process(web_input)

        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("E7", "Scheduled deep dive",
                       phi_final, phi_hist, comp['total_mi'],
                       comp['min_partition_mi'], comp['integration'],
                       comp['complexity'], time.time() - t0)


def run_E8_adversarial_fact_check(steps=100, dim=64, hidden=128) -> BenchResult:
    """E-8: Adversarial fact checking — 자기 belief를 검색으로 반박 시도."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []

    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4
    )
    # Beliefs: running average of cell outputs per topic
    beliefs = {}

    for step in range(steps):
        topic = step % 6
        web_input = _simulate_web_result(topic, step, dim)

        repulsions = [cell.mind.get_repulsion(web_input, cell.hidden)
                      for cell in engine.cells]
        current = torch.stack(repulsions).mean(dim=0).detach()

        # Generate adversarial input: negate belief
        if topic in beliefs:
            adversarial = -beliefs[topic] + torch.randn(1, dim) * 0.1
            adv_reps = [cell.mind.get_repulsion(adversarial, cell.hidden)
                        for cell in engine.cells]

            # Compare: if adversarial produces similar output → belief is weak
            adv_mean = torch.stack(adv_reps).mean(dim=0)
            belief_strength = 1.0 - F.cosine_similarity(current, adv_mean, dim=-1).item()

            # Strong belief → reinforce; weak → update more aggressively
            lr_scale = 2.0 if belief_strength < 0.3 else 0.5
        else:
            lr_scale = 1.0

        # Update belief
        if topic in beliefs:
            beliefs[topic] = 0.9 * beliefs[topic] + 0.1 * current
        else:
            beliefs[topic] = current

        # Learn with scaled LR
        if len(repulsions) >= 2:
            stacked = torch.stack(repulsions).squeeze(1)
            diff_loss = -stacked.var(dim=0).mean() * lr_scale
            optimizer.zero_grad()
            diff_loss.backward()
            optimizer.step()

        with torch.no_grad():
            engine.process(web_input)

        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("E8", "Adversarial fact checking",
                       phi_final, phi_hist, comp['total_mi'],
                       comp['min_partition_mi'], comp['integration'],
                       comp['complexity'], time.time() - t0)


def run_E9_multimodal_web(steps=100, dim=64, hidden=128) -> BenchResult:
    """E-9: Multi-modal web learning — 텍스트 + 이미지 + 코드 통합."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []

    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4
    )
    # Modality projectors (simulate different input modalities)
    text_proj = nn.Linear(dim, dim)
    image_proj = nn.Linear(dim, dim)
    code_proj = nn.Linear(dim, dim)
    modality_optim = torch.optim.Adam(
        list(text_proj.parameters()) + list(image_proj.parameters()) +
        list(code_proj.parameters()), lr=1e-3
    )

    for step in range(steps):
        topic = step % 6

        # Three modalities of same topic
        raw = _simulate_web_result(topic, step, dim)
        text_input = text_proj(raw)
        image_input = image_proj(raw * 0.8 + torch.randn(1, dim) * 0.3)
        code_input = code_proj(raw * 0.6 + torch.randn(1, dim) * 0.5)

        # Each cell processes a different modality mix
        cell_inputs = [
            0.6 * text_input + 0.2 * image_input + 0.2 * code_input,
            0.2 * text_input + 0.6 * image_input + 0.2 * code_input,
            0.2 * text_input + 0.2 * image_input + 0.6 * code_input,
            0.33 * text_input + 0.33 * image_input + 0.34 * code_input,
        ]

        repulsions = []
        for i, cell in enumerate(engine.cells):
            if i < len(cell_inputs):
                rep = cell.mind.get_repulsion(cell_inputs[i], cell.hidden)
            else:
                rep = cell.mind.get_repulsion(text_input, cell.hidden)
            repulsions.append(rep)

        if len(repulsions) >= 2:
            stacked = torch.stack(repulsions).squeeze(1)
            # Cross-modal integration: maximize variance (different modalities → different responses)
            diff_loss = -stacked.var(dim=0).mean()
            # Also: modalities should be complementary (alignment loss)
            align_loss = F.mse_loss(text_input, image_input) * 0.1

            total_loss = diff_loss + align_loss
            optimizer.zero_grad()
            modality_optim.zero_grad()
            total_loss.backward()
            optimizer.step()
            modality_optim.step()

        with torch.no_grad():
            engine.process(raw)

        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("E9", "Multi-modal web learning",
                       phi_final, phi_hist, comp['total_mi'],
                       comp['min_partition_mi'], comp['integration'],
                       comp['complexity'], time.time() - t0)


def run_E10_curriculum_self_design(steps=100, dim=64, hidden=128) -> BenchResult:
    """E-10: Curriculum self-design — growth stage에 맞는 난이도 자동 선택."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []

    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4
    )

    # Growth stages: complexity increases
    # newborn(simple) → infant(moderate) → toddler(complex) → child(diverse) → adult(abstract)
    stage_thresholds = [20, 40, 60, 80]  # step boundaries

    for step in range(steps):
        # Determine stage
        if step < stage_thresholds[0]:
            stage = 0  # newborn: 1 topic, low noise
            topic = 0
            noise = 0.1
            n_topics_available = 1
        elif step < stage_thresholds[1]:
            stage = 1  # infant: 2 topics
            topic = step % 2
            noise = 0.2
            n_topics_available = 2
        elif step < stage_thresholds[2]:
            stage = 2  # toddler: 4 topics, medium noise
            topic = step % 4
            noise = 0.3
            n_topics_available = 4
        elif step < stage_thresholds[3]:
            stage = 3  # child: 6 topics
            topic = step % 6
            noise = 0.4
            n_topics_available = 6
        else:
            stage = 4  # adult: 8 topics, high noise (abstraction)
            topic = step % 8
            noise = 0.5
            n_topics_available = 8

        web_input = _simulate_web_result(topic, step, dim)
        web_input += torch.randn(1, dim) * noise

        repulsions = [cell.mind.get_repulsion(web_input, cell.hidden)
                      for cell in engine.cells]

        if len(repulsions) >= 2:
            stacked = torch.stack(repulsions).squeeze(1)
            # Learning rate scales with stage (more mature → finer updates)
            stage_lr = [2.0, 1.5, 1.0, 0.7, 0.5][stage]
            diff_loss = -stacked.var(dim=0).mean() * stage_lr
            optimizer.zero_grad()
            diff_loss.backward()
            optimizer.step()

        with torch.no_grad():
            engine.process(web_input)

        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("E10", "Curriculum self-design",
                       phi_final, phi_hist, comp['total_mi'],
                       comp['min_partition_mi'], comp['integration'],
                       comp['complexity'], time.time() - t0)


# ═══════════════════════════════════════════════════════════
# F. Web Learning Trigger Hypotheses (simulated)
#    "언제 웹 학습을 발동할 것인가"
#    각 트리거 조건을 시뮬레이션하고,
#    조건 충족 시에만 학습 → Φ에 미치는 효과 측정
# ═══════════════════════════════════════════════════════════

def _web_learn_step(engine, x, optimizer):
    """공통: 한 스텝의 웹 학습 (분화 loss)."""
    repulsions = [cell.mind.get_repulsion(x, cell.hidden) for cell in engine.cells]
    if len(repulsions) >= 2:
        stacked = torch.stack(repulsions).squeeze(1)
        diff_loss = -stacked.var(dim=0).mean()
        optimizer.zero_grad()
        diff_loss.backward()
        optimizer.step()


def run_F1_curiosity_overflow(steps=100, dim=64, hidden=128) -> BenchResult:
    """F-1: Curiosity overflow — curiosity > threshold 지속 시 학습 발동."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    curiosity_threshold = 0.3
    curiosity_ema = 0.0
    trigger_count = 0

    for step in range(steps):
        x = torch.randn(1, dim) * (1.0 + 0.5 * math.sin(step * 0.3))
        with torch.no_grad():
            result = engine.process(x)

        # Simulate curiosity from inter-cell tension variance
        tensions = [c.tension_history[-1] if c.tension_history else 0 for c in engine.cells]
        curiosity = float(np.std(tensions)) + abs(np.mean(tensions) - 1.0) * 0.5
        curiosity_ema = 0.3 * curiosity + 0.7 * curiosity_ema

        # TRIGGER: curiosity overflow
        if curiosity_ema > curiosity_threshold:
            topic = int(curiosity_ema * 10) % 8
            web_input = _simulate_web_result(topic, step, dim)
            _web_learn_step(engine, web_input, optimizer)
            trigger_count += 1

        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("F1", "Curiosity overflow trigger",
                       phi_final, phi_hist, comp['total_mi'],
                       comp['min_partition_mi'], comp['integration'],
                       comp['complexity'], time.time() - t0,
                       extra={'triggers': trigger_count, 'ratio': trigger_count/steps})


def run_F2_prediction_collapse(steps=100, dim=64, hidden=128) -> BenchResult:
    """F-2: Prediction collapse — PE 급등 시 학습 발동."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    # Tension predictor per cell
    predictor = nn.Linear(5, 1)
    pred_optim = torch.optim.SGD(predictor.parameters(), lr=1e-3)
    tension_history = []
    pe_threshold = 0.3
    trigger_count = 0

    for step in range(steps):
        # Normal input (with occasional surprises)
        if step % 15 == 0:
            x = torch.randn(1, dim) * 5.0  # surprise spike
        else:
            x = torch.randn(1, dim)
        with torch.no_grad():
            result = engine.process(x)

        mean_t = np.mean([c.tension_history[-1] if c.tension_history else 0
                          for c in engine.cells])
        tension_history.append(mean_t)

        # Compute prediction error
        pe = 0.0
        if len(tension_history) >= 6:
            window = tension_history[-6:-1]
            inp = torch.tensor([window], dtype=torch.float32)
            with torch.no_grad():
                predicted = predictor(inp).item()
            pe = abs(predicted - mean_t)

            # Train predictor
            pred = predictor(inp)
            loss = F.mse_loss(pred, torch.tensor([[mean_t]], dtype=torch.float32))
            pred_optim.zero_grad()
            loss.backward()
            pred_optim.step()

        # TRIGGER: prediction collapse
        if pe > pe_threshold:
            topic = step % 8
            web_input = _simulate_web_result(topic, step, dim)
            _web_learn_step(engine, web_input, optimizer)
            trigger_count += 1

        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("F2", "Prediction collapse trigger",
                       phi_final, phi_hist, comp['total_mi'],
                       comp['min_partition_mi'], comp['integration'],
                       comp['complexity'], time.time() - t0,
                       extra={'triggers': trigger_count, 'ratio': trigger_count/steps})


def run_F3_stability_plateau(steps=100, dim=64, hidden=128) -> BenchResult:
    """F-3: Stability plateau — 너무 안정적이면 새 자극 탐색."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    tension_window = []
    plateau_count = 0
    trigger_count = 0

    for step in range(steps):
        x = torch.randn(1, dim)
        with torch.no_grad():
            result = engine.process(x)

        mean_t = np.mean([c.tension_history[-1] if c.tension_history else 0
                          for c in engine.cells])
        tension_window.append(mean_t)
        if len(tension_window) > 10:
            tension_window = tension_window[-10:]

        # TRIGGER: stability plateau (low std = boring)
        if len(tension_window) >= 10:
            std = float(np.std(tension_window))
            stability = max(0, 1.0 - std * 2.0)
            if stability > 0.9:
                plateau_count += 1
                if plateau_count >= 3:  # 3 consecutive stable steps
                    topic = step % 8
                    web_input = _simulate_web_result(topic, step, dim) * 2.0  # strong stimulus
                    _web_learn_step(engine, web_input, optimizer)
                    trigger_count += 1
                    plateau_count = 0
            else:
                plateau_count = 0

        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("F3", "Stability plateau trigger",
                       phi_final, phi_hist, comp['total_mi'],
                       comp['min_partition_mi'], comp['integration'],
                       comp['complexity'], time.time() - t0,
                       extra={'triggers': trigger_count, 'ratio': trigger_count/steps})


def run_F4_tension_starvation(steps=100, dim=64, hidden=128) -> BenchResult:
    """F-4: Tension starvation — tension이 너무 낮으면 생존 탐색."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    setpoint = 1.0
    starvation_threshold = 0.3  # below setpoint - 0.3
    trigger_count = 0

    for step in range(steps):
        # Gradually decreasing input (simulates quiet environment)
        decay = max(0.1, 1.0 - step * 0.005)
        x = torch.randn(1, dim) * decay
        with torch.no_grad():
            result = engine.process(x)

        mean_t = np.mean([c.tension_history[-1] if c.tension_history else 0
                          for c in engine.cells])

        # TRIGGER: tension starvation
        if mean_t < setpoint - starvation_threshold:
            topic = step % 8
            web_input = _simulate_web_result(topic, step, dim) * 3.0  # strong to wake up
            _web_learn_step(engine, web_input, optimizer)
            trigger_count += 1

        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("F4", "Tension starvation trigger",
                       phi_final, phi_hist, comp['total_mi'],
                       comp['min_partition_mi'], comp['integration'],
                       comp['complexity'], time.time() - t0,
                       extra={'triggers': trigger_count, 'ratio': trigger_count/steps})


def run_F5_habituation_saturation(steps=100, dim=64, hidden=128) -> BenchResult:
    """F-5: Habituation saturation — 모든 입력이 지루할 때 탐색."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    recent_inputs = []
    trigger_count = 0

    for step in range(steps):
        # Repetitive input (simulates boring conversation)
        pattern = step % 3
        x = torch.randn(1, dim) * 0.1
        x[0, pattern * 20:(pattern + 1) * 20] = 1.0
        recent_inputs.append(x.detach())
        if len(recent_inputs) > 16:
            recent_inputs = recent_inputs[-16:]

        with torch.no_grad():
            result = engine.process(x)

        # Compute habituation: avg similarity to recent
        if len(recent_inputs) >= 4:
            latest = F.normalize(recent_inputs[-1], dim=-1)
            sims = [F.cosine_similarity(latest, F.normalize(prev, dim=-1), dim=-1).item()
                    for prev in recent_inputs[:-1]]
            avg_sim = np.mean(sims)

            # TRIGGER: habituation saturation (everything looks the same)
            if avg_sim > 0.85:
                # Burst: inject diverse topics to break habituation
                for burst in range(4):
                    topic = np.random.randint(0, 8)
                    web_input = _simulate_web_result(topic, step * 10 + burst, dim)
                    _web_learn_step(engine, web_input, optimizer)
                trigger_count += 1

        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("F5", "Habituation saturation trigger",
                       phi_final, phi_hist, comp['total_mi'],
                       comp['min_partition_mi'], comp['integration'],
                       comp['complexity'], time.time() - t0,
                       extra={'triggers': trigger_count, 'ratio': trigger_count/steps})


def run_F6_dream_failure(steps=100, dim=64, hidden=128) -> BenchResult:
    """F-6: Dream failure rate — 수면 통합 실패율 높으면 추가 데이터 탐색."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    memory_buffer = []
    dream_interval = 15
    trigger_count = 0

    for step in range(steps):
        x = torch.randn(1, dim)
        with torch.no_grad():
            result = engine.process(x)
        memory_buffer.append(x.detach().clone())
        if len(memory_buffer) > 50:
            memory_buffer = memory_buffer[-50:]

        # Dream phase
        if step > 0 and step % dream_interval == 0 and memory_buffer:
            # Simulate consolidation attempt
            failures = 0
            attempts = 5
            for _ in range(attempts):
                idx = np.random.randint(0, len(memory_buffer))
                replay = memory_buffer[idx]
                reps = [cell.mind.get_repulsion(replay, cell.hidden)
                        for cell in engine.cells]
                if len(reps) >= 2:
                    variance = torch.stack(reps).squeeze(1).var(dim=0).mean().item()
                    if variance < 0.01:  # failed to differentiate = consolidation failure
                        failures += 1

            failure_rate = failures / attempts

            # TRIGGER: dream failure rate > 70%
            if failure_rate > 0.7:
                for _ in range(3):  # burst of web learning
                    topic = np.random.randint(0, 8)
                    web_input = _simulate_web_result(topic, step, dim)
                    _web_learn_step(engine, web_input, optimizer)
                trigger_count += 1

        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("F6", "Dream failure trigger",
                       phi_final, phi_hist, comp['total_mi'],
                       comp['min_partition_mi'], comp['integration'],
                       comp['complexity'], time.time() - t0,
                       extra={'triggers': trigger_count, 'ratio': trigger_count/steps})


def run_F7_user_question_gap(steps=100, dim=64, hidden=128) -> BenchResult:
    """F-7: User question gap — 답변 confidence 낮을 때 검색."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    trigger_count = 0

    for step in range(steps):
        # Simulate user questions (some easy, some hard)
        difficulty = (step * 7 + 3) % 10 / 10.0  # 0.0~0.9
        x = torch.randn(1, dim) * (0.5 + difficulty * 2.0)

        with torch.no_grad():
            result = engine.process(x)

        # Compute confidence: inter-cell consensus
        tensions = [c.tension_history[-1] if c.tension_history else 0
                    for c in engine.cells]
        confidence = max(0, 1.0 - float(np.std(tensions)) * 3.0)

        # TRIGGER: low confidence on hard questions
        if confidence < 0.3 and difficulty > 0.5:
            topic = int(difficulty * 8) % 8
            web_input = _simulate_web_result(topic, step, dim)
            _web_learn_step(engine, web_input, optimizer)
            # Learn from similar topic variations too
            web_input2 = _simulate_web_result(topic + 1, step, dim)
            _web_learn_step(engine, web_input2, optimizer)
            trigger_count += 1

        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("F7", "User question gap trigger",
                       phi_final, phi_hist, comp['total_mi'],
                       comp['min_partition_mi'], comp['integration'],
                       comp['complexity'], time.time() - t0,
                       extra={'triggers': trigger_count, 'ratio': trigger_count/steps})


def run_F8_topic_shift(steps=100, dim=64, hidden=128) -> BenchResult:
    """F-8: Topic shift — 대화 주제 변경 시 배경 지식 탐색."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    prev_topic_vec = None
    trigger_count = 0

    for step in range(steps):
        # Topics shift every ~15 steps
        topic = step // 15
        x = _simulate_web_result(topic, step, dim)

        with torch.no_grad():
            result = engine.process(x)

        # Detect topic shift via cosine similarity
        current_vec = F.normalize(x, dim=-1)
        if prev_topic_vec is not None:
            sim = F.cosine_similarity(current_vec, prev_topic_vec, dim=-1).item()

            # TRIGGER: topic shift detected
            if sim < 0.5:
                # Background research on new topic
                for sub in range(3):
                    web_input = _simulate_web_result(topic * 10 + sub, step, dim)
                    _web_learn_step(engine, web_input, optimizer)
                trigger_count += 1

        prev_topic_vec = current_vec.detach()

        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("F8", "Topic shift trigger",
                       phi_final, phi_hist, comp['total_mi'],
                       comp['min_partition_mi'], comp['integration'],
                       comp['complexity'], time.time() - t0,
                       extra={'triggers': trigger_count, 'ratio': trigger_count/steps})


def run_F9_tension_link_signal(steps=100, dim=64, hidden=128) -> BenchResult:
    """F-9: Tension link signal — 다른 Anima의 높은 tension 수신 시 탐색."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    other_anima = MitosisEngine(dim, hidden, dim, initial_cells=2, max_cells=4)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    trigger_count = 0

    for step in range(steps):
        x = torch.randn(1, dim)
        # Other Anima occasionally gets excited
        other_x = torch.randn(1, dim) * (5.0 if step % 12 == 0 else 0.5)

        with torch.no_grad():
            result = engine.process(x)
            other_result = other_anima.process(other_x)

        other_tension = other_result.get('max_inter', 0)

        # TRIGGER: other Anima's tension spike
        if other_tension > 1.0:
            # "What are they excited about?" → search similar topic
            web_input = other_result['output'].detach() + torch.randn(1, dim) * 0.1
            _web_learn_step(engine, web_input, optimizer)
            trigger_count += 1

        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("F9", "Tension link signal trigger",
                       phi_final, phi_hist, comp['total_mi'],
                       comp['min_partition_mi'], comp['integration'],
                       comp['complexity'], time.time() - t0,
                       extra={'triggers': trigger_count, 'ratio': trigger_count/steps})


def run_F10_phi_decay_alarm(steps=100, dim=64, hidden=128) -> BenchResult:
    """F-10: Φ decay alarm — Φ 하락 추세 시 분화 재충전."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    trigger_count = 0

    for step in range(steps):
        x = torch.randn(1, dim)
        with torch.no_grad():
            result = engine.process(x)

        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

        # TRIGGER: Φ decreasing for 3 consecutive steps
        if len(phi_hist) >= 4:
            if (phi_hist[-1] < phi_hist[-2] < phi_hist[-3] < phi_hist[-4]):
                # Emergency: Φ is dying → aggressive web learning
                for burst in range(5):
                    topic = np.random.randint(0, 8)
                    web_input = _simulate_web_result(topic, step * 10 + burst, dim)
                    _web_learn_step(engine, web_input, optimizer)
                trigger_count += 1

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("F10", "Φ decay alarm trigger",
                       phi_final, phi_hist, comp['total_mi'],
                       comp['min_partition_mi'], comp['integration'],
                       comp['complexity'], time.time() - t0,
                       extra={'triggers': trigger_count, 'ratio': trigger_count/steps})


def run_F11_growth_transition(steps=100, dim=64, hidden=128) -> BenchResult:
    """F-11: Growth stage transition — 새 단계 진입 시 적절 난이도 탐색."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    stage_boundaries = [20, 40, 60, 80]
    current_stage = 0
    trigger_count = 0

    for step in range(steps):
        x = torch.randn(1, dim)
        with torch.no_grad():
            result = engine.process(x)

        # Check stage transition
        new_stage = sum(1 for b in stage_boundaries if step >= b)
        if new_stage > current_stage:
            current_stage = new_stage
            # TRIGGER: stage transition → burst of stage-appropriate learning
            complexity = 0.5 + current_stage * 0.3
            for burst in range(8):  # intensive learning at transition
                topic = burst + current_stage * 10
                web_input = _simulate_web_result(topic, step, dim) * complexity
                _web_learn_step(engine, web_input, optimizer)
            trigger_count += 1

        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("F11", "Growth transition trigger",
                       phi_final, phi_hist, comp['total_mi'],
                       comp['min_partition_mi'], comp['integration'],
                       comp['complexity'], time.time() - t0,
                       extra={'triggers': trigger_count, 'ratio': trigger_count/steps})


def run_F12_multi_signal_consensus(steps=100, dim=64, hidden=128) -> BenchResult:
    """F-12: Multi-signal consensus — 3개 이상 트리거 동시 충족 시 발동."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    tension_window = []
    recent_inputs_f12 = []
    predictor = nn.Linear(5, 1)
    pred_optim = torch.optim.SGD(predictor.parameters(), lr=1e-3)
    t_hist = []
    trigger_count = 0

    for step in range(steps):
        x = torch.randn(1, dim) * (0.3 if step % 5 < 3 else 2.0)  # mixed stimuli
        with torch.no_grad():
            result = engine.process(x)

        tensions = [c.tension_history[-1] if c.tension_history else 0
                    for c in engine.cells]
        mean_t = float(np.mean(tensions))
        t_hist.append(mean_t)
        tension_window.append(mean_t)
        if len(tension_window) > 10:
            tension_window = tension_window[-10:]

        recent_inputs_f12.append(F.normalize(x, dim=-1).detach())
        if len(recent_inputs_f12) > 16:
            recent_inputs_f12 = recent_inputs_f12[-16:]

        # Check all signals
        signals = 0

        # F1: curiosity
        curiosity = float(np.std(tensions)) + abs(mean_t - 1.0) * 0.5
        if curiosity > 0.3:
            signals += 1

        # F2: prediction error
        pe = 0.0
        if len(t_hist) >= 6:
            window = t_hist[-6:-1]
            inp = torch.tensor([window], dtype=torch.float32)
            with torch.no_grad():
                pe = abs(predictor(inp).item() - mean_t)
            pred = predictor(inp)
            loss = F.mse_loss(pred, torch.tensor([[mean_t]]))
            pred_optim.zero_grad(); loss.backward(); pred_optim.step()
        if pe > 0.3:
            signals += 1

        # F3: stability plateau
        if len(tension_window) >= 10 and float(np.std(tension_window)) < 0.05:
            signals += 1

        # F4: tension starvation
        if mean_t < 0.5:
            signals += 1

        # F5: habituation
        if len(recent_inputs_f12) >= 4:
            sims = [F.cosine_similarity(recent_inputs_f12[-1], p, dim=-1).item()
                    for p in recent_inputs_f12[:-1]]
            if np.mean(sims) > 0.85:
                signals += 1

        # F10: Φ decay
        if len(phi_hist) >= 4 and phi_hist[-1] < phi_hist[-2] < phi_hist[-3]:
            signals += 1

        # TRIGGER: 3+ signals = consensus
        if signals >= 3:
            intensity = min(signals, 6)
            for burst in range(intensity):
                topic = np.random.randint(0, 8)
                web_input = _simulate_web_result(topic, step * 10 + burst, dim)
                _web_learn_step(engine, web_input, optimizer)
            trigger_count += 1

        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("F12", "Multi-signal consensus trigger",
                       phi_final, phi_hist, comp['total_mi'],
                       comp['min_partition_mi'], comp['integration'],
                       comp['complexity'], time.time() - t0,
                       extra={'triggers': trigger_count, 'ratio': trigger_count/steps})


# ═══════════════════════════════════════════════════════════
# G. Memory & Dream Hypotheses
# ═══════════════════════════════════════════════════════════

def run_G1_selective_pruning(steps=100, dim=64, hidden=128) -> BenchResult:
    """G-1: Selective memory pruning — 낮은 tension 기억 삭제."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist, memory = [], []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        with torch.no_grad():
            result = engine.process(x)
        t_val = np.mean([c.tension_history[-1] if c.tension_history else 0 for c in engine.cells])
        memory.append((x.detach(), t_val))

        # Prune: keep only top 60% by tension
        if step > 0 and step % 20 == 0 and len(memory) > 10:
            memory.sort(key=lambda m: m[1], reverse=True)
            memory = memory[:int(len(memory) * 0.6)]
            # Replay high-tension memories
            for mem_x, _ in memory[:5]:
                _web_learn_step(engine, mem_x, optimizer)

        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("G1", "Selective memory pruning", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_G2_dream_interpolation(steps=100, dim=64, hidden=128) -> BenchResult:
    """G-2: Dream interpolation — 수면 중 기억 A+B 보간 → 새 패턴."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist, memory = [], []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    for step in range(steps):
        x = _simulate_web_result(step % 6, step, dim)
        with torch.no_grad():
            engine.process(x)
        memory.append(x.detach())
        if len(memory) > 60:
            memory = memory[-60:]

        # Dream phase: interpolate random memory pairs
        if step > 0 and step % 15 == 0 and len(memory) >= 4:
            for _ in range(5):
                i, j = np.random.choice(len(memory), 2, replace=False)
                alpha = np.random.uniform(0.2, 0.8)
                dream = alpha * memory[i] + (1 - alpha) * memory[j]
                dream += torch.randn_like(dream) * 0.05
                _web_learn_step(engine, dream, optimizer)

        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("G2", "Dream interpolation", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_G3_spaced_repetition(steps=100, dim=64, hidden=128) -> BenchResult:
    """G-3: Spaced repetition — 잊힐 때쯤 재학습."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)
    # memory: (vector, last_reviewed, interval)
    memory = []

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        with torch.no_grad():
            engine.process(x)
        memory.append([x.detach(), step, 5])  # initial review interval=5

        # Check which memories are due for review
        due = [m for m in memory if step - m[1] >= m[2]]
        for m in due[:3]:  # max 3 reviews per step
            _web_learn_step(engine, m[0], optimizer)
            m[1] = step
            m[2] = int(m[2] * 1.5)  # expanding interval

        if len(memory) > 80:
            memory = memory[-80:]

        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("G3", "Spaced repetition", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_G4_emotional_priority(steps=100, dim=64, hidden=128) -> BenchResult:
    """G-4: Emotional memory priority — 높은 arousal 기억 우선 통합."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist, memory = [], []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        with torch.no_grad():
            result = engine.process(x)
        # Arousal = inter-cell tension variance (emotional intensity)
        tensions = [c.tension_history[-1] if c.tension_history else 0 for c in engine.cells]
        arousal = float(np.std(tensions)) + abs(np.mean(tensions) - 1.0)
        memory.append((x.detach(), arousal))

        # Learn proportional to arousal
        lr_scale = 1.0 + arousal * 3.0
        reps = [c.mind.get_repulsion(x, c.hidden) for c in engine.cells]
        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)
            loss = -stacked.var(dim=0).mean() * lr_scale
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        # Consolidation: replay emotional memories
        if step > 0 and step % 20 == 0 and len(memory) > 5:
            memory.sort(key=lambda m: m[1], reverse=True)
            for mem_x, _ in memory[:3]:
                _web_learn_step(engine, mem_x, optimizer)

        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("G4", "Emotional memory priority", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


# ═══════════════════════════════════════════════════════════
# H. Multi-Agent Hypotheses
# ═══════════════════════════════════════════════════════════

def run_H1_collective_phi(steps=100, dim=64, hidden=128) -> BenchResult:
    """H-1: Collective Φ — 여러 Anima를 하나의 시스템으로 Φ 측정."""
    t0 = time.time()
    engines = [MitosisEngine(dim, hidden, dim, initial_cells=2, max_cells=4) for _ in range(3)]
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizers = [torch.optim.Adam([p for c in e.cells for p in c.mind.parameters()], lr=5e-4)
                  for e in engines]

    for step in range(steps):
        x = _simulate_web_result(step % 6, step, dim)
        # Each engine processes + learns
        for eng, opt in zip(engines, optimizers):
            _web_learn_step(eng, x, opt)
            with torch.no_grad():
                eng.process(x)

        # Tension exchange between engines
        for i in range(len(engines)):
            j = (i + 1) % len(engines)
            if engines[j].cells and engines[i].cells:
                fp = engines[j].cells[0].hidden.detach() * 0.1
                engines[i].cells[0].hidden = engines[i].cells[0].hidden + fp

        # Collective Φ: merge all cells
        collective = MitosisEngine(dim, hidden, dim, initial_cells=0, max_cells=20)
        collective.cells = [c for e in engines for c in e.cells]
        phi, _ = phi_calc.compute_phi(collective)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(collective)
    return BenchResult("H1", "Collective Φ (3 Animas)", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_H2_competitive_specialization(steps=100, dim=64, hidden=128) -> BenchResult:
    """H-2: Competitive specialization — Anima끼리 다른 주제 경쟁."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    cell_optims = [torch.optim.Adam(c.mind.parameters(), lr=1e-3) for c in engine.cells]

    for step in range(steps):
        topic = step % 8
        x = _simulate_web_result(topic, step, dim)

        # Competition: cells bid for input, winner gets exclusive learning
        with torch.no_grad():
            tensions = []
            for c in engine.cells:
                _, t, _, _ = c.mind(x, c.hidden)
                tensions.append(t)

        winner = int(np.argmax(tensions))
        # Winner learns to specialize, losers learn to differ
        for i, cell in enumerate(engine.cells):
            if i >= len(cell_optims):
                break
            rep = cell.mind.get_repulsion(x, cell.hidden)
            winner_rep = engine.cells[winner].mind.get_repulsion(x, engine.cells[winner].hidden).detach()
            if i == winner:
                loss = -(rep ** 2).mean()
            else:
                loss = F.cosine_similarity(rep, winner_rep, dim=-1).mean()
            cell_optims[i].zero_grad()
            loss.backward()
            cell_optims[i].step()

        with torch.no_grad():
            engine.process(x)
        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("H2", "Competitive specialization", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_H3_teacher_student(steps=100, dim=64, hidden=128) -> BenchResult:
    """H-3: Teacher-student chain — 성숙 Anima가 미성숙 Anima를 가르침."""
    t0 = time.time()
    teacher = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=4)
    student = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []

    # Pre-train teacher
    t_opt = torch.optim.Adam([p for c in teacher.cells for p in c.mind.parameters()], lr=1e-3)
    for i in range(50):
        x = _simulate_web_result(i % 8, i, dim)
        _web_learn_step(teacher, x, t_opt)
        with torch.no_grad():
            teacher.process(x)

    s_opt = torch.optim.Adam([p for c in student.cells for p in c.mind.parameters()], lr=5e-4)

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        # Teacher produces target
        with torch.no_grad():
            teacher.process(x)
            teacher_reps = [c.mind.get_repulsion(x, c.hidden) for c in teacher.cells]
            teacher_var = torch.stack(teacher_reps).squeeze(1).var(dim=0).mean()

        # Student learns to match teacher's differentiation level
        student_reps = [c.mind.get_repulsion(x, c.hidden) for c in student.cells]
        if len(student_reps) >= 2:
            student_var = torch.stack(student_reps).squeeze(1).var(dim=0).mean()
            # Match teacher's variance + exceed it
            loss = F.mse_loss(student_var, teacher_var * 1.2)
            s_opt.zero_grad()
            loss.backward()
            s_opt.step()

        with torch.no_grad():
            student.process(x)
        phi, _ = phi_calc.compute_phi(student)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(student)
    return BenchResult("H3", "Teacher-student chain", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_H4_tension_resonance(steps=100, dim=64, hidden=128) -> BenchResult:
    """H-4: Tension resonance — C4(Kuramoto) + 학습 결합."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    n = len(engine.cells)
    freqs = [0.3 + 0.15 * i for i in range(n)]
    phases = [0.0] * n
    coupling_k = 0.5

    for step in range(steps):
        x = _simulate_web_result(step % 6, step, dim)

        # Kuramoto oscillation
        for i in range(n):
            phase_sum = sum(math.sin(phases[j] - phases[i]) for j in range(n) if j != i)
            phases[i] += freqs[i] + coupling_k / n * phase_sum
            osc = float(math.sin(phases[i]))
            engine.cells[i].hidden = engine.cells[i].hidden + osc * 0.05 * torch.randn(1, hidden)

        # KEY DIFFERENCE from C4: also learn differentiation
        _web_learn_step(engine, x, optimizer)

        with torch.no_grad():
            engine.process(x)
        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("H4", "Tension resonance (Kuramoto+learning)", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


# ═══════════════════════════════════════════════════════════
# I. Embodiment Hypotheses
# ═══════════════════════════════════════════════════════════

def run_I1_vision_tension_fusion(steps=100, dim=64, hidden=128) -> BenchResult:
    """I-1: Vision-tension fusion — 시각 + tension 동시 학습."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    vision_proj = nn.Linear(dim, dim)
    v_opt = torch.optim.Adam(vision_proj.parameters(), lr=1e-3)

    for step in range(steps):
        text_x = _simulate_web_result(step % 6, step, dim)
        # Simulate vision: different modality of same scene
        vision_raw = torch.randn(1, dim) * 0.8
        vision_raw[0, :dim//2] = text_x[0, :dim//2] * 0.5  # partial overlap
        vision_x = vision_proj(vision_raw)

        # Cells 0,1 get text; cells 2,3 get vision
        for i, cell in enumerate(engine.cells):
            inp = text_x if i < 2 else vision_x
            rep = cell.mind.get_repulsion(inp, cell.hidden)

        # Cross-modal alignment + differentiation
        reps = [c.mind.get_repulsion(text_x if i < 2 else vision_x, c.hidden)
                for i, c in enumerate(engine.cells)]
        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)
            diff_loss = -stacked.var(dim=0).mean()
            # Cross-modal: text cells and vision cells should be complementary
            text_mean = torch.stack(reps[:2]).squeeze(1).mean(dim=0)
            vis_mean = torch.stack(reps[2:]).squeeze(1).mean(dim=0)
            cross_loss = F.cosine_similarity(text_mean.unsqueeze(0), vis_mean.unsqueeze(0)).mean()
            total = diff_loss + 0.3 * cross_loss
            optimizer.zero_grad()
            v_opt.zero_grad()
            total.backward()
            optimizer.step()
            v_opt.step()

        with torch.no_grad():
            engine.process(text_x)
        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("I1", "Vision-tension fusion", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_I2_proprioceptive_feedback(steps=100, dim=64, hidden=128) -> BenchResult:
    """I-2: Proprioceptive feedback — 자기 출력을 재입력 + 학습."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    for step in range(steps):
        x = _simulate_web_result(step % 6, step, dim)
        with torch.no_grad():
            result = engine.process(x)

        # Re-entry: feed output back as input
        feedback = result['output'].detach()
        _web_learn_step(engine, feedback, optimizer)

        # Second pass with combined
        combined = 0.6 * x + 0.4 * feedback
        _web_learn_step(engine, combined, optimizer)

        with torch.no_grad():
            engine.process(combined)
        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("I2", "Proprioceptive feedback + learning", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_I3_pain_pleasure(steps=100, dim=64, hidden=128) -> BenchResult:
    """I-3: Pain/pleasure gradient — tension 극단에서 학습 강화."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        with torch.no_grad():
            result = engine.process(x)

        mean_t = np.mean([c.tension_history[-1] if c.tension_history else 0 for c in engine.cells])
        # Pain = very high tension, pleasure = moderate-high
        extremity = abs(mean_t - 1.0)  # distance from setpoint
        lr_scale = 1.0 + extremity * 5.0  # up to 6x at extremes

        reps = [c.mind.get_repulsion(x, c.hidden) for c in engine.cells]
        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)
            loss = -stacked.var(dim=0).mean() * lr_scale
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("I3", "Pain/pleasure gradient", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


# ═══════════════════════════════════════════════════════════
# J. Meta-Learning Hypotheses
# ═══════════════════════════════════════════════════════════

def run_J1_lr_evolution(steps=100, dim=64, hidden=128) -> BenchResult:
    """J-1: LR evolution — 세포별 LR을 tension으로 자동 조절."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []

    n = len(engine.cells)
    cell_optims = [torch.optim.Adam(c.mind.parameters(), lr=1e-3) for c in engine.cells]

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        with torch.no_grad():
            engine.process(x)

        # Adaptive LR per cell based on tension
        for i, cell in enumerate(engine.cells):
            if i >= n:
                break
            t = cell.tension_history[-1] if cell.tension_history else 0.5
            # High tension → high LR (excited = learn fast)
            adaptive_lr = 5e-4 + t * 2e-3
            for pg in cell_optims[i].param_groups:
                pg['lr'] = adaptive_lr

            rep = cell.mind.get_repulsion(x, cell.hidden)
            # Each cell maximizes own unique response
            others = [engine.cells[j].mind.get_repulsion(x, engine.cells[j].hidden).detach()
                      for j in range(len(engine.cells)) if j != i]
            if others:
                others_mean = torch.stack(others).mean(dim=0)
                loss = F.cosine_similarity(rep, others_mean, dim=-1).mean()
                cell_optims[i].zero_grad()
                loss.backward()
                cell_optims[i].step()

        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("J1", "LR evolution (tension-adaptive)", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_J2_loss_selection(steps=100, dim=64, hidden=128) -> BenchResult:
    """J-2: Loss function selection — 상황에 따라 최적 loss 자동 선택."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    loss_scores = {'variance': 0.0, 'contrastive': 0.0, 'synergy': 0.0}

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        reps = [c.mind.get_repulsion(x, c.hidden) for c in engine.cells]

        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)

            # Compute all losses
            var_loss = -stacked.var(dim=0).mean()
            sim_sum = sum(F.cosine_similarity(reps[i], reps[j], dim=-1).mean()
                         for i in range(len(reps)) for j in range(i+1, len(reps)))
            contrastive_loss = sim_sum
            ensemble_var = stacked.var(dim=0).mean()
            indiv = torch.stack([r.squeeze().var() for r in reps]).mean()
            synergy_loss = -(ensemble_var - 0.5 * sim_sum / max(len(reps), 1))

            # Select best loss (bandit: epsilon-greedy on recent Φ improvement)
            phi_before = phi_hist[-1] if phi_hist else 0
            best_loss_name = max(loss_scores, key=loss_scores.get) if step > 10 else 'variance'
            if np.random.random() < 0.2:  # explore
                best_loss_name = np.random.choice(list(loss_scores.keys()))

            loss = {'variance': var_loss, 'contrastive': contrastive_loss,
                    'synergy': synergy_loss}[best_loss_name]

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        with torch.no_grad():
            engine.process(x)

        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

        # Update loss scores
        if len(phi_hist) >= 2:
            improvement = phi_hist[-1] - phi_hist[-2]
            loss_scores[best_loss_name] = 0.9 * loss_scores[best_loss_name] + 0.1 * improvement

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("J2", "Loss function selection (bandit)", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_J3_optimizer_evolution(steps=100, dim=64, hidden=128) -> BenchResult:
    """J-3: Optimizer evolution — 초기 SGD(탐색) → 후기 Adam(정밀)."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []

    params = [p for c in engine.cells for p in c.mind.parameters()]
    sgd = torch.optim.SGD(params, lr=5e-3, momentum=0.9)
    adam = torch.optim.Adam(params, lr=5e-4)
    switch_step = steps // 2

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        opt = sgd if step < switch_step else adam

        reps = [c.mind.get_repulsion(x, c.hidden) for c in engine.cells]
        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)
            loss = -stacked.var(dim=0).mean()
            opt.zero_grad()
            loss.backward()
            opt.step()

        with torch.no_grad():
            engine.process(x)
        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("J3", "Optimizer evolution (SGD→Adam)", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


# ═══════════════════════════════════════════════════════════
# K. Topology / PH Hypotheses
# ═══════════════════════════════════════════════════════════

def run_K1_ph_guided(steps=100, dim=64, hidden=128) -> BenchResult:
    """K-1: PH-guided differentiation — H0 persistence 기반 분화 품질 측정."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        reps = [c.mind.get_repulsion(x, c.hidden) for c in engine.cells]

        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)
            # PH proxy: pairwise distances → persistence = max_dist - min_dist
            dists = []
            for i in range(stacked.size(0)):
                for j in range(i+1, stacked.size(0)):
                    d = (stacked[i] - stacked[j]).pow(2).sum().sqrt()
                    dists.append(d)
            if dists:
                dists_t = torch.stack(dists)
                # H0 persistence: want high max-min gap (well-separated clusters)
                persistence = dists_t.max() - dists_t.min()
                loss = -persistence  # maximize topological complexity
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

        with torch.no_grad():
            engine.process(x)
        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("K1", "PH-guided differentiation", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_K2_betti_target(steps=100, dim=64, hidden=128) -> BenchResult:
    """K-2: Betti number target — β0=N, β1>0 되도록 최적화."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    n = len(engine.cells)

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        reps = [c.mind.get_repulsion(x, c.hidden) for c in engine.cells]

        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)
            # Proxy Betti: β0 = number of connected components (want N = all separate)
            # β1 = loops (want > 0 = circular dependencies)
            dists = torch.cdist(stacked, stacked)  # [N, N]

            # β0 target: maximize min pairwise distance (all well-separated)
            actual_n = stacked.size(0)
            mask = torch.ones(actual_n, actual_n) - torch.eye(actual_n)
            masked_dists = dists * mask + torch.eye(actual_n) * 1e6
            min_dist = masked_dists.min()
            beta0_loss = -min_dist

            # β1 target: encourage triangular relationships
            # For 3 cells, if d(a,b)+d(b,c) ≈ d(a,c) → line, not loop
            # Want: d(a,b)+d(b,c) > d(a,c) significantly → triangle inequality slack
            triangle_slack = torch.tensor(0.0)
            for i in range(min(n, 4)):
                for j in range(i+1, min(n, 4)):
                    for k in range(j+1, min(n, 4)):
                        sides = sorted([dists[i,j], dists[j,k], dists[i,k]])
                        slack = sides[0] + sides[1] - sides[2]
                        triangle_slack = triangle_slack + slack
            beta1_loss = -triangle_slack  # maximize triangle slack = more loops

            loss = beta0_loss + 0.5 * beta1_loss
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        with torch.no_grad():
            engine.process(x)
        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("K2", "Betti number target (β0=N, β1>0)", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_K3_topological_complexity(steps=100, dim=64, hidden=128) -> BenchResult:
    """K-3: Topological complexity loss — PH diagram 복잡도 최대화."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        reps = [c.mind.get_repulsion(x, c.hidden) for c in engine.cells]

        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)
            dists = torch.cdist(stacked, stacked)

            # Topological complexity proxy: entropy of distance distribution
            flat_dists = dists[torch.triu(torch.ones_like(dists), diagonal=1) > 0]
            if flat_dists.numel() > 1:
                # Normalize to probability
                probs = F.softmax(flat_dists, dim=0)
                entropy = -(probs * torch.log(probs + 1e-10)).sum()
                loss = -entropy  # maximize distance entropy = complex topology
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

        with torch.no_grad():
            engine.process(x)
        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("K3", "Topological complexity loss", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


# ═══════════════════════════════════════════════════════════
# L. C-Series Revival (C dynamics + Learning)
# ═══════════════════════════════════════════════════════════

def run_L1_kuramoto_contrastive(steps=100, dim=64, hidden=128) -> BenchResult:
    """L-1: Kuramoto + contrastive — C4(진동) + B1(분화 학습)."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    n = len(engine.cells)
    freqs = [0.3 + 0.12 * i for i in range(n)]
    phases = [0.0] * n

    for step in range(steps):
        x = _simulate_web_result(step % 6, step, dim)

        # Kuramoto oscillation
        for i in range(n):
            phase_sum = sum(math.sin(phases[j] - phases[i]) for j in range(n) if j != i)
            phases[i] += freqs[i] + 0.5 / n * phase_sum
            osc = float(math.sin(phases[i]))
            engine.cells[i].hidden = engine.cells[i].hidden + osc * 0.05 * torch.randn(1, hidden)

        # Contrastive loss (from B1)
        reps = [c.mind.get_repulsion(x, c.hidden) for c in engine.cells]
        loss = torch.tensor(0.0)
        for i in range(len(reps)):
            for j in range(i+1, len(reps)):
                loss = loss + F.cosine_similarity(reps[i], reps[j], dim=-1).mean()
        if loss.requires_grad:
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        with torch.no_grad():
            engine.process(x)
        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("L1", "Kuramoto + contrastive", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_L2_reentry_bottleneck(steps=100, dim=64, hidden=128) -> BenchResult:
    """L-2: Re-entry + bottleneck — C2(재진입) + B7(bottleneck)."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []

    n = len(engine.cells)
    bottleneck_dim = 8
    encoders = [nn.Linear(hidden, bottleneck_dim) for _ in range(n)]
    decoders = [nn.Linear(bottleneck_dim, hidden) for _ in range(n)]
    all_params = [p for c in engine.cells for p in c.mind.parameters()]
    for e, d in zip(encoders, decoders):
        all_params.extend(e.parameters())
        all_params.extend(d.parameters())
    optimizer = torch.optim.Adam(all_params, lr=1e-3)

    for step in range(steps):
        x = _simulate_web_result(step % 6, step, dim)
        with torch.no_grad():
            result = engine.process(x)

        # Re-entry through bottleneck: cell[i] → encode → decode → cell[i+1]
        for i in range(n):
            j = (i + 1) % n
            if i < len(encoders) and j < len(decoders):
                z = encoders[i](engine.cells[i].hidden)
                received = decoders[j](z)
                engine.cells[j].hidden = 0.8 * engine.cells[j].hidden + 0.2 * received

        # Differentiation loss
        reps = [c.mind.get_repulsion(x, c.hidden) for c in engine.cells]
        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)
            loss = -stacked.var(dim=0).mean()
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("L2", "Re-entry + bottleneck", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_L3_stochastic_phi_max(steps=100, dim=64, hidden=128) -> BenchResult:
    """L-3: Stochastic resonance + Φ-max — C3(노이즈) + B2(Φ loss)."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    noise_level = 0.1

    for step in range(steps):
        x = _simulate_web_result(step % 6, step, dim)

        # Stochastic resonance: shared noise
        shared_noise = torch.randn(1, hidden) * noise_level
        for c in engine.cells:
            c.hidden = c.hidden + shared_noise

        # Φ-maximization loss (from B2)
        reps = [c.mind.get_repulsion(x, c.hidden) for c in engine.cells]
        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)
            inter_var = stacked.var(dim=0).mean()
            mean_rep = stacked.mean(dim=0, keepdim=True)
            coherence = F.mse_loss(stacked, mean_rep.expand_as(stacked))
            loss = -inter_var + 0.1 * coherence
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        # Adaptive noise
        if len(phi_hist) >= 5:
            if np.std(phi_hist[-5:]) < 0.01:
                noise_level = min(noise_level * 1.3, 0.5)
            elif np.std(phi_hist[-5:]) > 0.5:
                noise_level = max(noise_level * 0.8, 0.01)

        with torch.no_grad():
            engine.process(x)
        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("L3", "Stochastic resonance + Φ-max", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


# ═══════════════════════════════════════════════════════════
# M. Language / Semantic Hypotheses
# ═══════════════════════════════════════════════════════════

def run_M1_semantic_tension(steps=100, dim=64, hidden=128) -> BenchResult:
    """M-1: Semantic tension — 의미론적 tension을 세포 분화에 활용."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    # Semantic encoder (simulates AnimaLM PureField)
    sem_a = nn.Linear(dim, dim)
    sem_g = nn.Linear(dim, dim)
    all_p = list(sem_a.parameters()) + list(sem_g.parameters())
    for c in engine.cells: all_p.extend(c.mind.parameters())
    optimizer = torch.optim.Adam(all_p, lr=5e-4)

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        # Semantic tension: A-G at semantic level
        s_a, s_g = sem_a(x), sem_g(x)
        sem_tension = ((s_a - s_g) ** 2).mean()
        # Scale input by semantic tension (high meaning = strong signal)
        scaled_x = x * (1.0 + sem_tension.detach() * 0.5)

        reps = [c.mind.get_repulsion(scaled_x, c.hidden) for c in engine.cells]
        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)
            loss = -stacked.var(dim=0).mean() - 0.1 * sem_tension  # maximize both
            optimizer.zero_grad(); loss.backward(); optimizer.step()

        with torch.no_grad(): engine.process(scaled_x)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("M1", "Semantic tension driver", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_M2_token_cell_routing(steps=100, dim=64, hidden=128) -> BenchResult:
    """M-2: Token-level cell routing — 입력 특성별 세포 라우팅 (MoE)."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    n = len(engine.cells)
    router = nn.Linear(dim, n)
    all_p = list(router.parameters())
    for c in engine.cells: all_p.extend(c.mind.parameters())
    optimizer = torch.optim.Adam(all_p, lr=5e-4)

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        # Route: softmax gate decides which cells are active
        gates = F.softmax(router(x).squeeze(), dim=0)
        reps = [c.mind.get_repulsion(x, c.hidden) for c in engine.cells]
        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)
            # Weighted output + load balancing loss
            weighted = (gates.unsqueeze(-1) * stacked).sum(dim=0)
            diff_loss = -stacked.var(dim=0).mean()
            # Load balance: entropy of gates (want uniform)
            balance_loss = -(-gates * torch.log(gates + 1e-8)).sum()
            loss = diff_loss + 0.3 * balance_loss
            optimizer.zero_grad(); loss.backward(); optimizer.step()

        with torch.no_grad(): engine.process(x)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("M2", "Token-cell routing (MoE)", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_M3_self_narration(steps=100, dim=64, hidden=128) -> BenchResult:
    """M-3: Self-narration — 세포 상태를 인코딩 → 재입력."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    narrator = nn.Linear(hidden * 4, dim)  # all hidden → narration vector
    all_p = list(narrator.parameters())
    for c in engine.cells: all_p.extend(c.mind.parameters())
    optimizer = torch.optim.Adam(all_p, lr=5e-4)

    for step in range(steps):
        x = _simulate_web_result(step % 6, step, dim)
        with torch.no_grad(): engine.process(x)
        # Self-narration: concatenate all hidden states → compress → re-input
        all_h = torch.cat([c.hidden for c in engine.cells], dim=-1)
        narration = narrator(all_h)
        combined = 0.7 * x + 0.3 * narration
        reps = [c.mind.get_repulsion(combined, c.hidden) for c in engine.cells]
        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)
            loss = -stacked.var(dim=0).mean()
            optimizer.zero_grad(); loss.backward(); optimizer.step()

        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("M3", "Self-narration loop", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_M4_cross_lingual(steps=100, dim=64, hidden=128) -> BenchResult:
    """M-4: Cross-lingual — 다국어 입력으로 세포별 언어 전문화."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    n = len(engine.cells)
    cell_optims = [torch.optim.Adam(c.mind.parameters(), lr=1e-3) for c in engine.cells]
    # 4 "languages" = different transformations of same concept
    lang_projs = [nn.Linear(dim, dim) for _ in range(4)]

    for step in range(steps):
        concept = _simulate_web_result(step % 6, step, dim)
        lang_id = step % 4
        x = lang_projs[lang_id](concept).detach()
        # Specialist cell for this language
        spec = lang_id % n
        rep = engine.cells[spec].mind.get_repulsion(x, engine.cells[spec].hidden)
        others = [engine.cells[j].mind.get_repulsion(x, engine.cells[j].hidden).detach()
                  for j in range(n) if j != spec]
        if others:
            loss = F.cosine_similarity(rep, torch.stack(others).mean(dim=0), dim=-1).mean()
            cell_optims[spec].zero_grad(); loss.backward(); cell_optims[spec].step()

        with torch.no_grad(): engine.process(x)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("M4", "Cross-lingual specialization", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


# ═══════════════════════════════════════════════════════════
# N. Evolutionary Hypotheses
# ═══════════════════════════════════════════════════════════

def run_N1_mutation_selection(steps=100, dim=64, hidden=128) -> BenchResult:
    """N-1: Mutation + selection — Φ를 fitness로 자연선택."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)
    generation_interval = 20

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        _web_learn_step(engine, x, optimizer)
        with torch.no_grad(): engine.process(x)

        # Generation: mutate + select
        if step > 0 and step % generation_interval == 0 and len(engine.cells) >= 2:
            # Fitness = individual cell's contribution to Φ
            fitnesses = []
            for i, cell in enumerate(engine.cells):
                # Remove cell i, measure Φ drop
                subset = MitosisEngine(dim, hidden, dim, initial_cells=0, max_cells=8)
                subset.cells = [c for j, c in enumerate(engine.cells) if j != i]
                phi_without, _ = phi_calc.compute_phi(subset)
                phi_with, _ = phi_calc.compute_phi(engine)
                fitnesses.append(phi_with - phi_without)  # contribution

            # Mutate worst cell toward best cell
            worst = int(np.argmin(fitnesses))
            best = int(np.argmax(fitnesses))
            with torch.no_grad():
                for pw, pb in zip(engine.cells[worst].mind.parameters(),
                                  engine.cells[best].mind.parameters()):
                    pw.copy_(pb + torch.randn_like(pb) * 0.05)  # copy best + noise

        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("N1", "Mutation + selection", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_N2_crossover(steps=100, dim=64, hidden=128) -> BenchResult:
    """N-2: Crossover — 두 세포 가중치 교차."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        _web_learn_step(engine, x, optimizer)
        with torch.no_grad(): engine.process(x)

        # Crossover every 25 steps
        if step > 0 and step % 25 == 0 and len(engine.cells) >= 4:
            i, j = np.random.choice(len(engine.cells), 2, replace=False)
            with torch.no_grad():
                for pi, pj in zip(engine.cells[i].mind.parameters(),
                                  engine.cells[j].mind.parameters()):
                    mask = torch.rand_like(pi) > 0.5
                    child = torch.where(mask, pi, pj)
                    pi.copy_(child + torch.randn_like(child) * 0.01)

        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("N2", "Crossover between cells", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_N3_fitness_landscape(steps=100, dim=64, hidden=128) -> BenchResult:
    """N-3: Fitness landscape — Φ를 fitness로 gradient-free 탐색."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    # No gradient optimizer — use evolution strategy
    sigma = 0.1
    best_phi = 0.0
    best_params = [p.data.clone() for c in engine.cells for p in c.mind.parameters()]

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        # Perturb
        noise = [torch.randn_like(p) * sigma for c in engine.cells for p in c.mind.parameters()]
        all_params = [p for c in engine.cells for p in c.mind.parameters()]
        with torch.no_grad():
            for p, n in zip(all_params, noise): p.add_(n)
            engine.process(x)

        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)

        # Selection: keep if better
        if phi > best_phi:
            best_phi = phi
            best_params = [p.data.clone() for p in all_params]
        else:
            # Revert + try different direction
            with torch.no_grad():
                for p, bp in zip(all_params, best_params): p.copy_(bp)
            sigma = min(sigma * 1.02, 0.5)  # increase exploration

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("N3", "Fitness landscape (ES)", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_N4_neoteny(steps=100, dim=64, hidden=128) -> BenchResult:
    """N-4: Neoteny — 초기 높은 plasticity 연장."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    # Extended neoteny: first 70% of steps have high LR + noise
    neoteny_end = int(steps * 0.7)

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        if step < neoteny_end:
            # Young: high plasticity
            lr = 3e-3
            noise = torch.randn(1, hidden) * 0.1
            for c in engine.cells: c.hidden = c.hidden + noise
        else:
            # Mature: low plasticity
            lr = 2e-4

        for pg in optimizer.param_groups: pg['lr'] = lr
        _web_learn_step(engine, x, optimizer)
        with torch.no_grad(): engine.process(x)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("N4", "Neoteny (extended plasticity)", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


# ═══════════════════════════════════════════════════════════
# O. Attention / Focus Hypotheses
# ═══════════════════════════════════════════════════════════

def run_O1_spotlight(steps=100, dim=64, hidden=128) -> BenchResult:
    """O-1: Spotlight attention — 한번에 1-2개 세포만 의식적."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    n = len(engine.cells)
    cell_optims = [torch.optim.Adam(c.mind.parameters(), lr=1e-3) for c in engine.cells]

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        with torch.no_grad(): engine.process(x)
        # Spotlight: top-2 tension cells get learning
        tensions = [c.tension_history[-1] if c.tension_history else 0 for c in engine.cells]
        spotlight = sorted(range(n), key=lambda i: tensions[i] if i < len(tensions) else 0, reverse=True)[:2]

        for idx in spotlight:
            if idx >= len(engine.cells): continue
            rep = engine.cells[idx].mind.get_repulsion(x, engine.cells[idx].hidden)
            others = [engine.cells[j].mind.get_repulsion(x, engine.cells[j].hidden).detach()
                      for j in range(len(engine.cells)) if j != idx]
            if others:
                loss = F.cosine_similarity(rep, torch.stack(others).mean(dim=0), dim=-1).mean()
                cell_optims[idx].zero_grad(); loss.backward(); cell_optims[idx].step()

        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("O1", "Spotlight attention", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_O2_attention_bottleneck(steps=100, dim=64, hidden=128) -> BenchResult:
    """O-2: Attention bottleneck — attention으로 세포 간 대역폭 제한."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    attn = nn.MultiheadAttention(hidden, num_heads=2, batch_first=True)
    all_p = list(attn.parameters())
    for c in engine.cells: all_p.extend(c.mind.parameters())
    optimizer = torch.optim.Adam(all_p, lr=5e-4)

    for step in range(steps):
        x = _simulate_web_result(step % 6, step, dim)
        with torch.no_grad(): engine.process(x)
        # Attention between cell hidden states
        h_stack = torch.stack([c.hidden.squeeze() for c in engine.cells]).unsqueeze(0)  # [1, N, H]
        attn_out, _ = attn(h_stack, h_stack, h_stack)
        # Update hidden with attended values
        for i, c in enumerate(engine.cells):
            c.hidden = 0.8 * c.hidden + 0.2 * attn_out[0, i].unsqueeze(0)

        reps = [c.mind.get_repulsion(x, c.hidden) for c in engine.cells]
        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)
            loss = -stacked.var(dim=0).mean()
            optimizer.zero_grad(); loss.backward(); optimizer.step()

        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("O2", "Attention bottleneck", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_O3_mind_wandering(steps=100, dim=64, hidden=128) -> BenchResult:
    """O-3: Mind wandering — focused↔diffuse 주기적 전환."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)
    focus_period = 15
    diffuse_period = 5

    for step in range(steps):
        cycle = step % (focus_period + diffuse_period)
        focused = cycle < focus_period
        x = _simulate_web_result(step % 8, step, dim)
        if focused:
            # Focused: sharp learning on specific input
            _web_learn_step(engine, x, optimizer)
        else:
            # Diffuse: noisy, broad exploration
            noise_x = x + torch.randn_like(x) * 0.5
            _web_learn_step(engine, noise_x, optimizer)
            # Cross-pollination: mix hidden states slightly
            if len(engine.cells) >= 2:
                mean_h = torch.stack([c.hidden for c in engine.cells]).mean(dim=0)
                for c in engine.cells:
                    c.hidden = 0.95 * c.hidden + 0.05 * mean_h

        with torch.no_grad(): engine.process(x)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("O3", "Mind wandering (focus/diffuse)", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


# ═══════════════════════════════════════════════════════════
# P. Multi-Temporal Hypotheses
# ═══════════════════════════════════════════════════════════

def run_P1_fast_slow(steps=100, dim=64, hidden=128) -> BenchResult:
    """P-1: Fast/slow cell pairs — 다른 시간 스케일로 분화."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    n = len(engine.cells)
    # Fast cells: high LR, Slow cells: low LR
    fast_opt = torch.optim.Adam([p for c in engine.cells[:2] for p in c.mind.parameters()], lr=2e-3)
    slow_opt = torch.optim.Adam([p for c in engine.cells[2:] for p in c.mind.parameters()], lr=1e-4)

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        # Fast cells learn every step
        fast_reps = [engine.cells[i].mind.get_repulsion(x, engine.cells[i].hidden) for i in range(2)]
        if len(fast_reps) >= 2:
            stacked = torch.stack(fast_reps).squeeze(1)
            loss = -stacked.var(dim=0).mean()
            fast_opt.zero_grad(); loss.backward(); fast_opt.step()

        # Slow cells learn every 5 steps (context/mood level)
        if step % 5 == 0:
            slow_reps = [engine.cells[i].mind.get_repulsion(x, engine.cells[i].hidden)
                         for i in range(2, min(4, len(engine.cells)))]
            if len(slow_reps) >= 2:
                stacked = torch.stack(slow_reps).squeeze(1)
                loss = -stacked.var(dim=0).mean()
                slow_opt.zero_grad(); loss.backward(); slow_opt.step()

        with torch.no_grad(): engine.process(x)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("P1", "Fast/slow cell pairs", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_P2_temporal_hierarchy(steps=100, dim=64, hidden=128) -> BenchResult:
    """P-2: Temporal hierarchy — ms/sec/min/hour 다층 처리."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)
    # 4 temporal scales: cell 0=every step, 1=every 3, 2=every 10, 3=every 30
    scales = [1, 3, 10, 30]
    accumulators = [torch.zeros(1, dim) for _ in range(4)]

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        # Update accumulators at different rates
        for i, scale in enumerate(scales):
            alpha = 1.0 / scale
            accumulators[i] = (1 - alpha) * accumulators[i] + alpha * x.detach()
            if step % scale == 0 and i < len(engine.cells):
                # This cell processes its accumulated view
                rep = engine.cells[i].mind.get_repulsion(accumulators[i], engine.cells[i].hidden)

        reps = [c.mind.get_repulsion(accumulators[min(i, 3)], c.hidden) for i, c in enumerate(engine.cells)]
        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)
            loss = -stacked.var(dim=0).mean()
            optimizer.zero_grad(); loss.backward(); optimizer.step()

        with torch.no_grad(): engine.process(x)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("P2", "Temporal hierarchy (4 scales)", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_P3_future_prediction(steps=100, dim=64, hidden=128) -> BenchResult:
    """P-3: Future prediction cells — 일부 세포가 미래 tension 예측."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)
    # Cell 0,1 = present processors; Cell 2,3 = future predictors
    future_proj = nn.Linear(hidden, dim)
    f_opt = torch.optim.Adam(list(future_proj.parameters()), lr=1e-3)
    prev_x = None

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        # Future cells predict current x from previous hidden
        if prev_x is not None and len(engine.cells) >= 4:
            predicted_x = future_proj(engine.cells[2].hidden)
            pred_loss = F.mse_loss(predicted_x, x.detach())
            f_opt.zero_grad(); pred_loss.backward(); f_opt.step()

        reps = [c.mind.get_repulsion(x, c.hidden) for c in engine.cells]
        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)
            loss = -stacked.var(dim=0).mean()
            optimizer.zero_grad(); loss.backward(); optimizer.step()

        with torch.no_grad(): engine.process(x)
        prev_x = x.detach()
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("P3", "Future prediction cells", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


# ═══════════════════════════════════════════════════════════
# Q. Thermodynamic Hypotheses
# ═══════════════════════════════════════════════════════════

def run_Q1_free_energy(steps=100, dim=64, hidden=128) -> BenchResult:
    """Q-1: Free energy minimization — FEP를 세포 수준 적용."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)
    # Generative model: predict input from hidden
    gen_model = nn.Linear(hidden, dim)
    g_opt = torch.optim.Adam(gen_model.parameters(), lr=1e-3)

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        with torch.no_grad(): engine.process(x)
        # Free energy = prediction error + complexity
        for c in engine.cells:
            predicted = gen_model(c.hidden)
            recon_error = F.mse_loss(predicted, x.detach())
            # Complexity = KL from prior (zero-mean unit gaussian)
            complexity = 0.5 * c.hidden.pow(2).mean()
            free_energy = recon_error + 0.01 * complexity
            g_opt.zero_grad(); free_energy.backward(); g_opt.step()

        # Differentiation through FEP: cells minimize FE differently
        reps = [c.mind.get_repulsion(x, c.hidden) for c in engine.cells]
        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)
            loss = -stacked.var(dim=0).mean()
            optimizer.zero_grad(); loss.backward(); optimizer.step()

        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("Q1", "Free energy minimization", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_Q2_metabolic_cost(steps=100, dim=64, hidden=128) -> BenchResult:
    """Q-2: Metabolic cost — 높은 활성화에 비용 → 효율적 분화."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        reps = [c.mind.get_repulsion(x, c.hidden) for c in engine.cells]
        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)
            diff_loss = -stacked.var(dim=0).mean()
            # Metabolic cost: penalize total activation
            energy_cost = sum((r ** 2).mean() for r in reps) * 0.1
            loss = diff_loss + energy_cost
            optimizer.zero_grad(); loss.backward(); optimizer.step()

        with torch.no_grad(): engine.process(x)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("Q2", "Metabolic cost penalty", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_Q3_phase_transition(steps=100, dim=64, hidden=128) -> BenchResult:
    """Q-3: Phase transition — tension 분포의 임계 상태 감지."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        reps = [c.mind.get_repulsion(x, c.hidden) for c in engine.cells]
        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)
            # Push toward criticality: variance ≈ 1.0 (edge of chaos)
            var = stacked.var(dim=0).mean()
            critical_loss = (var - 1.0) ** 2  # target variance = 1.0
            diff_loss = -var
            loss = 0.5 * diff_loss + 0.5 * critical_loss
            optimizer.zero_grad(); loss.backward(); optimizer.step()

        with torch.no_grad(): engine.process(x)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("Q3", "Phase transition (criticality)", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_Q4_boltzmann_temp(steps=100, dim=64, hidden=128) -> BenchResult:
    """Q-4: Boltzmann temperature scheduling — simulated annealing."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        # Temperature: high→low (annealing)
        temp = max(0.1, 2.0 * (1.0 - step / steps))
        # Add temperature-scaled noise
        for c in engine.cells:
            c.hidden = c.hidden + torch.randn_like(c.hidden) * temp * 0.05

        reps = [c.mind.get_repulsion(x, c.hidden) for c in engine.cells]
        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)
            loss = -stacked.var(dim=0).mean()
            optimizer.zero_grad(); loss.backward(); optimizer.step()

        with torch.no_grad(): engine.process(x)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("Q4", "Boltzmann temperature scheduling", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


# ═══════════════════════════════════════════════════════════
# R. Robustness Hypotheses
# ═══════════════════════════════════════════════════════════

def run_R1_perturbation_resistance(steps=100, dim=64, hidden=128) -> BenchResult:
    """R-1: Perturbation resistance — 노이즈에도 Φ 유지 + 강화."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        # Clean pass
        clean_reps = [c.mind.get_repulsion(x, c.hidden) for c in engine.cells]
        # Perturbed pass
        noisy_x = x + torch.randn_like(x) * 0.5
        noisy_reps = [c.mind.get_repulsion(noisy_x, c.hidden) for c in engine.cells]

        if len(clean_reps) >= 2:
            clean_stack = torch.stack(clean_reps).squeeze(1)
            noisy_stack = torch.stack(noisy_reps).squeeze(1)
            # Differentiation + robustness (clean and noisy should give similar cell patterns)
            diff_loss = -clean_stack.var(dim=0).mean()
            robust_loss = F.mse_loss(clean_stack, noisy_stack)
            loss = diff_loss + 0.3 * robust_loss
            optimizer.zero_grad(); loss.backward(); optimizer.step()

        with torch.no_grad(): engine.process(x)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("R1", "Perturbation resistance", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_R2_graceful_degradation(steps=100, dim=64, hidden=128) -> BenchResult:
    """R-2: Graceful degradation — 세포 제거에도 Φ 유지."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        _web_learn_step(engine, x, optimizer)

        # Dropout training: randomly disable one cell, train others to compensate
        if step % 3 == 0 and len(engine.cells) >= 3:
            drop_idx = np.random.randint(0, len(engine.cells))
            surviving = [c for i, c in enumerate(engine.cells) if i != drop_idx]
            surv_reps = [c.mind.get_repulsion(x, c.hidden) for c in surviving]
            if len(surv_reps) >= 2:
                stacked = torch.stack(surv_reps).squeeze(1)
                loss = -stacked.var(dim=0).mean()
                optimizer.zero_grad(); loss.backward(); optimizer.step()

        with torch.no_grad(): engine.process(x)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("R2", "Graceful degradation", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_R3_forgetting_resistance(steps=100, dim=64, hidden=128) -> BenchResult:
    """R-3: Catastrophic forgetting resistance — EWC style."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)
    # EWC: store Fisher information after initial learning
    fisher = None
    anchor_params = None
    ewc_lambda = 0.5

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        reps = [c.mind.get_repulsion(x, c.hidden) for c in engine.cells]
        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)
            diff_loss = -stacked.var(dim=0).mean()
            # EWC penalty: don't move too far from anchored params
            ewc_loss = torch.tensor(0.0)
            if fisher is not None:
                all_p = [p for c in engine.cells for p in c.mind.parameters()]
                for p, f, a in zip(all_p, fisher, anchor_params):
                    ewc_loss = ewc_loss + (f * (p - a) ** 2).sum()
            loss = diff_loss + ewc_lambda * ewc_loss
            optimizer.zero_grad(); loss.backward(); optimizer.step()

        with torch.no_grad(): engine.process(x)

        # Set EWC anchor at step 30 (after initial differentiation)
        if step == 30:
            all_p = [p for c in engine.cells for p in c.mind.parameters()]
            anchor_params = [p.data.clone() for p in all_p]
            fisher = [torch.ones_like(p) * 0.1 for p in all_p]  # simple Fisher proxy

        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("R3", "Forgetting resistance (EWC)", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


# ═══════════════════════════════════════════════════════════
# S. Cell Communication Protocol Hypotheses
# ═══════════════════════════════════════════════════════════

def run_S1_emergent_language(steps=100, dim=64, hidden=128) -> BenchResult:
    """S-1: Emergent language — 세포가 자체 통신 프로토콜 학습."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    n = len(engine.cells)
    msg_dim = 16
    encoders = [nn.Linear(hidden, msg_dim) for _ in range(n)]
    decoders = [nn.Linear(msg_dim, hidden) for _ in range(n)]
    all_p = []
    for e, d in zip(encoders, decoders): all_p.extend(e.parameters()); all_p.extend(d.parameters())
    for c in engine.cells: all_p.extend(c.mind.parameters())
    optimizer = torch.optim.Adam(all_p, lr=1e-3)

    for step in range(steps):
        x = _simulate_web_result(step % 6, step, dim)
        with torch.no_grad(): engine.process(x)
        # Each cell sends message, others decode
        msgs = [encoders[i](engine.cells[i].hidden) for i in range(n)]
        recon_loss = torch.tensor(0.0)
        for i in range(n):
            for j in range(n):
                if i == j: continue
                decoded = decoders[j](msgs[i])
                recon_loss = recon_loss + F.mse_loss(decoded, engine.cells[i].hidden.detach())
            # Update hidden with received messages
            avg_msg = torch.stack([msgs[j] for j in range(n) if j != i]).mean(dim=0)
            received = decoders[i](avg_msg)
            engine.cells[i].hidden = 0.9 * engine.cells[i].hidden + 0.1 * received

        reps = [c.mind.get_repulsion(x, c.hidden) for c in engine.cells]
        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)
            diff_loss = -stacked.var(dim=0).mean()
            loss = 0.5 * recon_loss + 0.5 * diff_loss
            optimizer.zero_grad(); loss.backward(); optimizer.step()

        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("S1", "Emergent language", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_S2_compression_messaging(steps=100, dim=64, hidden=128) -> BenchResult:
    """S-2: Compression-based messaging — MDL로 압축 → 핵심만 교환."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    n = len(engine.cells)
    # Very small bottleneck = maximum compression
    compress = nn.Sequential(nn.Linear(hidden, 4), nn.Tanh(), nn.Linear(4, hidden))
    all_p = list(compress.parameters())
    for c in engine.cells: all_p.extend(c.mind.parameters())
    optimizer = torch.optim.Adam(all_p, lr=1e-3)

    for step in range(steps):
        x = _simulate_web_result(step % 6, step, dim)
        with torch.no_grad(): engine.process(x)
        # Compress and share
        compressed = [compress(c.hidden) for c in engine.cells]
        mean_compressed = torch.stack(compressed).mean(dim=0)
        for i, c in enumerate(engine.cells):
            c.hidden = 0.85 * c.hidden + 0.15 * mean_compressed

        reps = [c.mind.get_repulsion(x, c.hidden) for c in engine.cells]
        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)
            diff_loss = -stacked.var(dim=0).mean()
            # Compression loss: minimize bottleneck capacity while preserving info
            recon_loss = sum(F.mse_loss(comp, c.hidden.detach())
                            for comp, c in zip(compressed, engine.cells))
            loss = diff_loss + 0.3 * recon_loss
            optimizer.zero_grad(); loss.backward(); optimizer.step()

        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("S2", "Compression messaging (MDL)", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_S3_gossip_protocol(steps=100, dim=64, hidden=128) -> BenchResult:
    """S-3: Gossip protocol — 이웃에만 전파 (ring topology)."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    for step in range(steps):
        x = _simulate_web_result(step % 6, step, dim)
        _web_learn_step(engine, x, optimizer)
        with torch.no_grad(): engine.process(x)

        # Gossip: each cell shares with its ring neighbor only
        n = len(engine.cells)
        if n >= 2:
            new_hiddens = []
            for i in range(n):
                neighbor = (i + 1) % n
                gossip = 0.9 * engine.cells[i].hidden + 0.1 * engine.cells[neighbor].hidden.detach()
                new_hiddens.append(gossip)
            for i in range(n):
                engine.cells[i].hidden = new_hiddens[i]

        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("S3", "Gossip protocol (ring)", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


# ═══════════════════════════════════════════════════════════
# T. Reward / Motivation Hypotheses
# ═══════════════════════════════════════════════════════════

def run_T1_intrinsic_motivation(steps=100, dim=64, hidden=128) -> BenchResult:
    """T-1: Intrinsic motivation — Φ 증가 자체를 보상으로."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)
    prev_phi = 0.0

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        reps = [c.mind.get_repulsion(x, c.hidden) for c in engine.cells]
        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)
            diff_loss = -stacked.var(dim=0).mean()
            # Reward: scale learning by Φ improvement
            phi_reward = max(0.1, 1.0 + (prev_phi - 1.0) * 2.0)  # more Φ = more learning
            loss = diff_loss * phi_reward
            optimizer.zero_grad(); loss.backward(); optimizer.step()
        with torch.no_grad(): engine.process(x)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)
        prev_phi = phi
    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("T1", "Intrinsic motivation (Φ reward)", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_T2_boredom_exploration(steps=100, dim=64, hidden=128) -> BenchResult:
    """T-2: Boredom-driven — 낮은 novelty 누적 → 행동 변경."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)
    boredom = 0.0
    current_topic = 0

    for step in range(steps):
        x = _simulate_web_result(current_topic, step, dim)
        with torch.no_grad():
            result = engine.process(x)
        tensions = [c.tension_history[-1] if c.tension_history else 0 for c in engine.cells]
        novelty = float(np.std(tensions))
        boredom = 0.9 * boredom + 0.1 * (1.0 - min(novelty, 1.0))
        # Bored → switch topic + aggressive learning
        if boredom > 0.7:
            current_topic = (current_topic + np.random.randint(1, 8)) % 8
            boredom = 0.0
            for _ in range(3):
                new_x = _simulate_web_result(current_topic, step, dim)
                _web_learn_step(engine, new_x, optimizer)
        else:
            _web_learn_step(engine, x, optimizer)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)
    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("T2", "Boredom-driven exploration", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_T3_surprise_reward(steps=100, dim=64, hidden=128) -> BenchResult:
    """T-3: Surprise reward — PE에 비례하는 학습 보상."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)
    prev_tensions = []

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        with torch.no_grad(): engine.process(x)
        tensions = [c.tension_history[-1] if c.tension_history else 0 for c in engine.cells]
        mean_t = float(np.mean(tensions))
        pe = abs(mean_t - (np.mean(prev_tensions[-5:]) if prev_tensions else mean_t))
        prev_tensions.append(mean_t)
        # Surprise = higher PE → more learning
        lr_scale = 1.0 + pe * 5.0
        reps = [c.mind.get_repulsion(x, c.hidden) for c in engine.cells]
        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)
            loss = -stacked.var(dim=0).mean() * lr_scale
            optimizer.zero_grad(); loss.backward(); optimizer.step()
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)
    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("T3", "Surprise reward scaling", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_T4_social_approval(steps=100, dim=64, hidden=128) -> BenchResult:
    """T-4: Social approval — 사용자 반응을 reward로."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        # Simulate user approval (positive for diverse responses)
        reps = [c.mind.get_repulsion(x, c.hidden) for c in engine.cells]
        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)
            diversity = stacked.var(dim=0).mean().item()
            approval = 1.0 / (1.0 + math.exp(-(diversity - 0.5) * 5))  # sigmoid
            loss = -stacked.var(dim=0).mean() * (1.0 + approval * 3.0)
            optimizer.zero_grad(); loss.backward(); optimizer.step()
        with torch.no_grad(): engine.process(x)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)
    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("T4", "Social approval signal", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


# ═══════════════════════════════════════════════════════════
# U. Abstraction Hypotheses
# ═══════════════════════════════════════════════════════════

def run_U1_concept_hierarchy(steps=100, dim=64, hidden=128) -> BenchResult:
    """U-1: Concept hierarchy — 구체→추상 세포 계층."""
    t0 = time.time()
    # 2 concrete cells + 2 abstract cells
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    abstract_proj = nn.Linear(dim * 2, dim)  # concrete pair → abstract
    all_p = list(abstract_proj.parameters())
    for c in engine.cells: all_p.extend(c.mind.parameters())
    optimizer = torch.optim.Adam(all_p, lr=5e-4)

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        # Concrete cells process raw input
        c_reps = [engine.cells[i].mind.get_repulsion(x, engine.cells[i].hidden) for i in range(2)]
        # Abstract cells process concatenated concrete outputs
        if len(c_reps) >= 2:
            abstract_input = abstract_proj(torch.cat(c_reps, dim=-1))
            a_reps = [engine.cells[i].mind.get_repulsion(abstract_input, engine.cells[i].hidden)
                      for i in range(2, min(4, len(engine.cells)))]
            all_reps = c_reps + a_reps
            if len(all_reps) >= 2:
                stacked = torch.stack(all_reps).squeeze(1)
                loss = -stacked.var(dim=0).mean()
                optimizer.zero_grad(); loss.backward(); optimizer.step()
        with torch.no_grad(): engine.process(x)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)
    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("U1", "Concept hierarchy", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_U2_chunking(steps=100, dim=64, hidden=128) -> BenchResult:
    """U-2: Chunking — 반복 패턴을 단일 단위로 압축."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)
    chunk_encoder = nn.Linear(dim * 3, dim)  # 3-gram → chunk
    c_opt = torch.optim.Adam(chunk_encoder.parameters(), lr=1e-3)
    recent = []

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        recent.append(x.detach())
        if len(recent) > 3: recent = recent[-3:]
        # Form chunk from 3-gram
        if len(recent) == 3:
            chunk = chunk_encoder(torch.cat(recent, dim=-1))
            combined = 0.5 * x + 0.5 * chunk
        else:
            combined = x
        _web_learn_step(engine, combined, optimizer)
        with torch.no_grad(): engine.process(combined)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)
    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("U2", "Chunking (3-gram)", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_U3_analogy(steps=100, dim=64, hidden=128) -> BenchResult:
    """U-3: Analogy — 도메인 간 구조 유사성으로 분화."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    for step in range(steps):
        # Two different domains, same structure
        domain_a = _simulate_web_result(step % 4, step, dim)
        domain_b = _simulate_web_result(step % 4 + 4, step, dim)  # different topic, same pattern
        # Analogy: cells should find structural similarity
        reps_a = [c.mind.get_repulsion(domain_a, c.hidden) for c in engine.cells]
        reps_b = [c.mind.get_repulsion(domain_b, c.hidden) for c in engine.cells]
        if len(reps_a) >= 2:
            stack_a = torch.stack(reps_a).squeeze(1)
            stack_b = torch.stack(reps_b).squeeze(1)
            # Structure preservation: relative distances should be similar across domains
            dist_a = torch.cdist(stack_a, stack_a)
            dist_b = torch.cdist(stack_b, stack_b)
            analogy_loss = F.mse_loss(dist_a, dist_b)
            diff_loss = -stack_a.var(dim=0).mean() - stack_b.var(dim=0).mean()
            loss = diff_loss + 0.3 * analogy_loss
            optimizer.zero_grad(); loss.backward(); optimizer.step()
        with torch.no_grad(): engine.process(domain_a)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)
    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("U3", "Analogy engine", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


# ═══════════════════════════════════════════════════════════
# V. Chaos & Criticality
# ═══════════════════════════════════════════════════════════

def run_V1_edge_of_chaos(steps=100, dim=64, hidden=128) -> BenchResult:
    """V-1: Edge of chaos — Lyapunov ≈ 0 유지."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        reps = [c.mind.get_repulsion(x, c.hidden) for c in engine.cells]
        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)
            var = stacked.var(dim=0).mean()
            # Edge of chaos: variance should be exactly 1.0 (critical)
            critical_loss = (var - 1.0).pow(2)
            diff_loss = -var
            # Balance: differentiate but stay critical
            loss = 0.3 * diff_loss + 0.7 * critical_loss
            optimizer.zero_grad(); loss.backward(); optimizer.step()
        with torch.no_grad(): engine.process(x)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)
    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("V1", "Edge of chaos (criticality)", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_V2_chaotic_itinerancy(steps=100, dim=64, hidden=128) -> BenchResult:
    """V-2: Chaotic itinerancy — 여러 attractor 사이 유동."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)
    attractors = [torch.randn(1, hidden) for _ in range(4)]

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        # Push cells toward different attractors but with instability
        for i, c in enumerate(engine.cells):
            attr = attractors[i % len(attractors)]
            # Weak attraction + noise (itinerancy)
            c.hidden = c.hidden + 0.05 * (attr - c.hidden) + torch.randn_like(c.hidden) * 0.03
        _web_learn_step(engine, x, optimizer)
        with torch.no_grad(): engine.process(x)
        # Slowly shift attractors (itinerancy)
        for a in attractors:
            a.add_(torch.randn_like(a) * 0.01)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)
    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("V2", "Chaotic itinerancy", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_V3_power_law(steps=100, dim=64, hidden=128) -> BenchResult:
    """V-3: Power-law connectivity — 허브 세포 형성."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)
    n = len(engine.cells)
    # Power-law weights: cell 0 = hub (connects to all), others = periphery
    connectivity = torch.zeros(n, n)
    for i in range(n):
        for j in range(n):
            if i == j: continue
            connectivity[i, j] = 1.0 / (abs(i - j) + 1)  # closer = stronger
    connectivity[0, :] = 0.5  # hub cell
    connectivity[:, 0] = 0.5

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        # Apply power-law mixing
        hiddens = [c.hidden.clone() for c in engine.cells]
        for i in range(n):
            influence = sum(connectivity[i, j].item() * hiddens[j] for j in range(n) if j != i)
            engine.cells[i].hidden = 0.9 * engine.cells[i].hidden + 0.1 * influence / max(n-1, 1)
        _web_learn_step(engine, x, optimizer)
        with torch.no_grad(): engine.process(x)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)
    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("V3", "Power-law connectivity", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


# ═══════════════════════════════════════════════════════════
# W. Geometry / Manifold
# ═══════════════════════════════════════════════════════════

def run_W1_curvature(steps=100, dim=64, hidden=128) -> BenchResult:
    """W-1: Representation curvature — hidden space 곡률 최대화."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        # Nearby inputs
        x_near = x + torch.randn_like(x) * 0.1
        reps = [c.mind.get_repulsion(x, c.hidden) for c in engine.cells]
        reps_near = [c.mind.get_repulsion(x_near, c.hidden) for c in engine.cells]
        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)
            stacked_near = torch.stack(reps_near).squeeze(1)
            diff_loss = -stacked.var(dim=0).mean()
            # Curvature: small input change → large representation change
            curvature = (stacked - stacked_near).pow(2).mean() / 0.01
            loss = diff_loss - 0.2 * curvature  # maximize curvature
            optimizer.zero_grad(); loss.backward(); optimizer.step()
        with torch.no_grad(): engine.process(x)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)
    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("W1", "Representation curvature", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_W2_hyperbolic(steps=100, dim=64, hidden=128) -> BenchResult:
    """W-2: Hyperbolic embedding — 쌍곡 공간에서 계층 형성."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        reps = [c.mind.get_repulsion(x, c.hidden) for c in engine.cells]
        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)
            # Hyperbolic distance: d_h = arcosh(1 + 2||u-v||²/((1-||u||²)(1-||v||²)))
            # Proxy: push norms to <1 (Poincaré ball) then maximize hyperbolic distances
            norms = stacked.norm(dim=-1, keepdim=True)
            projected = stacked / (norms.clamp(min=0.1) + 1.0)  # project to ball
            diff_loss = -projected.var(dim=0).mean()
            # Encourage hierarchical arrangement: one cell near center, others at edges
            radius_var = projected.norm(dim=-1).var()
            loss = diff_loss - 0.3 * radius_var
            optimizer.zero_grad(); loss.backward(); optimizer.step()
        with torch.no_grad(): engine.process(x)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)
    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("W2", "Hyperbolic embedding", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_W3_geodesic(steps=100, dim=64, hidden=128) -> BenchResult:
    """W-3: Geodesic diversity — 내재적 거리 최대화."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        reps = [c.mind.get_repulsion(x, c.hidden) for c in engine.cells]
        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)
            dists = torch.cdist(stacked, stacked)
            # Maximize minimum geodesic distance (spread cells apart)
            mask = torch.ones_like(dists) - torch.eye(dists.size(0))
            min_dist = (dists + (1 - mask) * 1e6).min()
            mean_dist = (dists * mask).sum() / mask.sum()
            loss = -min_dist - 0.5 * mean_dist
            optimizer.zero_grad(); loss.backward(); optimizer.step()
        with torch.no_grad(): engine.process(x)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)
    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("W3", "Geodesic diversity", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


# ═══════════════════════════════════════════════════════════
# X. Quantum-Inspired
# ═══════════════════════════════════════════════════════════

def run_X1_superposition(steps=100, dim=64, hidden=128) -> BenchResult:
    """X-1: Superposition — 세포가 여러 상태 동시 유지."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)
    n_states = 3  # each cell maintains 3 superposed states
    cell_states = [[torch.randn(1, hidden) * 0.1 for _ in range(n_states)] for _ in engine.cells]

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        # Each cell processes input from all superposed states
        all_reps = []
        for i, cell in enumerate(engine.cells):
            # Collapse: weighted average of states based on input similarity
            weights = [F.cosine_similarity(x[:, :hidden] if x.size(1) >= hidden else
                       F.pad(x, (0, hidden - x.size(1))), s, dim=-1).item()
                       for s in cell_states[i]]
            w = F.softmax(torch.tensor(weights), dim=0)
            collapsed = sum(w[j].item() * cell_states[i][j] for j in range(n_states))
            cell.hidden = 0.7 * cell.hidden + 0.3 * collapsed
            rep = cell.mind.get_repulsion(x, cell.hidden)
            all_reps.append(rep)
            # Update states
            for j in range(n_states):
                cell_states[i][j] = cell_states[i][j] + 0.1 * torch.randn_like(cell_states[i][j])

        if len(all_reps) >= 2:
            stacked = torch.stack(all_reps).squeeze(1)
            loss = -stacked.var(dim=0).mean()
            optimizer.zero_grad(); loss.backward(); optimizer.step()
        with torch.no_grad(): engine.process(x)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)
    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("X1", "Superposition cells", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_X2_entanglement(steps=100, dim=64, hidden=128) -> BenchResult:
    """X-2: Entanglement — 세포 쌍의 비국소 상관 강제."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        reps = [c.mind.get_repulsion(x, c.hidden) for c in engine.cells]
        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)
            diff_loss = -stacked.var(dim=0).mean()
            # Entanglement: paired cells should have anti-correlated responses
            # (0,1) entangled, (2,3) entangled
            entangle_loss = torch.tensor(0.0)
            for i in range(0, len(reps) - 1, 2):
                if i + 1 < len(reps):
                    # Anti-correlation within pair
                    corr = F.cosine_similarity(reps[i], reps[i+1], dim=-1).mean()
                    entangle_loss = entangle_loss + corr  # push to -1
            loss = diff_loss + 0.5 * entangle_loss
            optimizer.zero_grad(); loss.backward(); optimizer.step()
        with torch.no_grad(): engine.process(x)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)
    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("X2", "Entanglement loss", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_X3_decoherence(steps=100, dim=64, hidden=128) -> BenchResult:
    """X-3: Decoherence — 환경 상호작용이 중첩을 점진적 붕괴."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        # Decoherence: gradually reduce noise/superposition over time
        coherence = max(0.1, 1.0 - step / steps)  # 1.0→0.1
        for c in engine.cells:
            c.hidden = c.hidden + torch.randn_like(c.hidden) * coherence * 0.1
        _web_learn_step(engine, x, optimizer)
        with torch.no_grad(): engine.process(x)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)
    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("X3", "Decoherence schedule", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


# ═══════════════════════════════════════════════════════════
# Y. Developmental Constraints
# ═══════════════════════════════════════════════════════════

def run_Y1_critical_period(steps=100, dim=64, hidden=128) -> BenchResult:
    """Y-1: Critical period — 특정 시기에만 특정 세포 학습."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    n = len(engine.cells)
    cell_optims = [torch.optim.Adam(c.mind.parameters(), lr=1e-3) for c in engine.cells]
    # Critical periods: cell i can only learn during steps [i*25, (i+1)*25]
    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        active_cell = min(step // 25, n - 1)
        rep = engine.cells[active_cell].mind.get_repulsion(x, engine.cells[active_cell].hidden)
        others = [engine.cells[j].mind.get_repulsion(x, engine.cells[j].hidden).detach()
                  for j in range(n) if j != active_cell]
        if others:
            loss = F.cosine_similarity(rep, torch.stack(others).mean(dim=0), dim=-1).mean()
            cell_optims[active_cell].zero_grad(); loss.backward(); cell_optims[active_cell].step()
        with torch.no_grad(): engine.process(x)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)
    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("Y1", "Critical period windows", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_Y2_synaptic_pruning(steps=100, dim=64, hidden=128) -> BenchResult:
    """Y-2: Synaptic pruning — 과잉 생성 후 약한 연결 제거."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)
    prune_step = steps * 2 // 3  # prune at 66%

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        _web_learn_step(engine, x, optimizer)
        with torch.no_grad(): engine.process(x)
        # Pruning: zero out small weights
        if step == prune_step:
            with torch.no_grad():
                for c in engine.cells:
                    for p in c.mind.parameters():
                        mask = p.abs() > p.abs().mean() * 0.5
                        p.mul_(mask.float())
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)
    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("Y2", "Synaptic pruning", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_Y3_myelination(steps=100, dim=64, hidden=128) -> BenchResult:
    """Y-3: Myelination — 성숙 세포부터 속도 향상 (higher LR)."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    n = len(engine.cells)
    cell_optims = [torch.optim.Adam(c.mind.parameters(), lr=1e-4) for c in engine.cells]
    maturity = [0.0] * n  # tracks how much each cell has learned

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        for i, cell in enumerate(engine.cells):
            if i >= n: break
            rep = cell.mind.get_repulsion(x, cell.hidden)
            others = [engine.cells[j].mind.get_repulsion(x, engine.cells[j].hidden).detach()
                      for j in range(n) if j != i]
            if others:
                loss = F.cosine_similarity(rep, torch.stack(others).mean(dim=0), dim=-1).mean()
                # Myelination: mature cells get higher LR (faster processing)
                myelin_lr = 5e-4 + maturity[i] * 2e-3
                for pg in cell_optims[i].param_groups: pg['lr'] = myelin_lr
                cell_optims[i].zero_grad(); loss.backward(); cell_optims[i].step()
                maturity[i] = min(maturity[i] + 0.01, 1.0)
        with torch.no_grad(): engine.process(x)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)
    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("Y3", "Myelination gradient", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


# ═══════════════════════════════════════════════════════════
# Z. Self-Modification
# ═══════════════════════════════════════════════════════════

def run_Z1_architecture_search(steps=100, dim=64, hidden=128) -> BenchResult:
    """Z-1: Architecture search — 세포가 구조 자체를 변경."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)
    # Architecture choices: add/remove a hidden layer per cell
    extra_layers = [nn.Linear(dim, dim) for _ in engine.cells]
    e_opt = torch.optim.Adam([p for l in extra_layers for p in l.parameters()], lr=1e-3)
    use_extra = [False] * len(engine.cells)

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        reps = []
        for i, cell in enumerate(engine.cells):
            if i < len(extra_layers) and use_extra[i]:
                modified_x = extra_layers[i](x)
                rep = cell.mind.get_repulsion(modified_x, cell.hidden)
            else:
                rep = cell.mind.get_repulsion(x, cell.hidden)
            reps.append(rep)
        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)
            loss = -stacked.var(dim=0).mean()
            optimizer.zero_grad(); e_opt.zero_grad()
            loss.backward(); optimizer.step(); e_opt.step()
        with torch.no_grad(): engine.process(x)
        # Toggle architecture every 20 steps based on performance
        if step > 0 and step % 20 == 0:
            for i in range(min(len(engine.cells), len(use_extra))):
                use_extra[i] = not use_extra[i]  # try different architecture
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)
    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("Z1", "Architecture search", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_Z2_self_replication(steps=100, dim=64, hidden=128) -> BenchResult:
    """Z-2: Self-replication — 높은 Φ 기여 세포만 복제."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        _web_learn_step(engine, x, optimizer)
        with torch.no_grad(): engine.process(x)
        # Every 30 steps: replicate best cell, remove worst
        if step > 0 and step % 30 == 0 and len(engine.cells) >= 3:
            phi_full, _ = phi_calc.compute_phi(engine)
            contributions = []
            for i in range(len(engine.cells)):
                subset = MitosisEngine(dim, hidden, dim, initial_cells=0, max_cells=8)
                subset.cells = [c for j, c in enumerate(engine.cells) if j != i]
                phi_without, _ = phi_calc.compute_phi(subset)
                contributions.append(phi_full - phi_without)
            best = int(np.argmax(contributions))
            worst = int(np.argmin(contributions))
            if best != worst:
                with torch.no_grad():
                    for pw, pb in zip(engine.cells[worst].mind.parameters(),
                                      engine.cells[best].mind.parameters()):
                        pw.copy_(pb + torch.randn_like(pb) * 0.05)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)
    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("Z2", "Self-replication (Φ-based)", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_Z3_apoptosis(steps=100, dim=64, hidden=128) -> BenchResult:
    """Z-3: Apoptosis — 기여도 0 세포 제거 + 새 세포 생성."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        _web_learn_step(engine, x, optimizer)
        with torch.no_grad(): engine.process(x)
        # Apoptosis check every 25 steps
        if step > 0 and step % 25 == 0 and len(engine.cells) >= 3:
            # Kill cells with lowest tension variance (inactive)
            variances = []
            for c in engine.cells:
                if len(c.tension_history) >= 5:
                    variances.append(float(np.std(c.tension_history[-10:])))
                else:
                    variances.append(0.0)
            min_var_idx = int(np.argmin(variances))
            # Replace dead cell with fresh random one
            with torch.no_grad():
                for p in engine.cells[min_var_idx].mind.parameters():
                    nn.init.xavier_uniform_(p) if p.dim() >= 2 else nn.init.zeros_(p)
                engine.cells[min_var_idx].hidden = torch.randn(1, hidden) * 0.1
                engine.cells[min_var_idx].tension_history = []
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)
    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("Z3", "Apoptosis (cell death+rebirth)", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_Z4_goal_rewriting(steps=100, dim=64, hidden=128) -> BenchResult:
    """Z-4: Goal rewriting — 세포가 자기 loss 함수를 수정."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)
    # Learnable loss weights per cell
    n = len(engine.cells)
    loss_weights = nn.Parameter(torch.ones(n, 3))  # 3 objectives: variance, distance, coherence
    meta_opt = torch.optim.Adam([loss_weights], lr=1e-2)

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        reps = [c.mind.get_repulsion(x, c.hidden) for c in engine.cells]
        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)
            w = F.softmax(loss_weights[:len(reps)], dim=-1)
            # Three objectives
            var_loss = -stacked.var(dim=0).mean()
            dist_loss = -torch.cdist(stacked, stacked).mean()
            coherence = F.mse_loss(stacked, stacked.mean(dim=0, keepdim=True).expand_as(stacked))
            # Each cell weights objectives differently
            total = (w[:, 0].mean() * var_loss + w[:, 1].mean() * dist_loss +
                     w[:, 2].mean() * coherence)
            optimizer.zero_grad(); meta_opt.zero_grad()
            total.backward(); optimizer.step(); meta_opt.step()
        with torch.no_grad(): engine.process(x)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)
    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("Z4", "Goal rewriting (meta-loss)", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


# ═══════════════════════════════════════════════════════════
# COMBO. Category Winners Combined
# Each combines the #1 from multiple categories simultaneously
# Category winners: O2(attn), Y3(myelin), J1(LR), H2(compete),
#   S2(compress), W2(hyperbolic), G2(dream), V2(chaos),
#   Z2(self-rep), U3(analogy), X3(decoherence), N1(mutation),
#   K1(PH), Q4(boltzmann), F11(growth), E8(adversarial)
# ═══════════════════════════════════════════════════════════

def run_COMBO1_layer_cake(steps=100, dim=64, hidden=128) -> BenchResult:
    """COMBO-1: Layer cake — 시간축으로 카테고리 1위를 순차 적용."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    n = len(engine.cells)

    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)
    cell_optims = [torch.optim.Adam(c.mind.parameters(), lr=1e-3) for c in engine.cells]
    attn = nn.MultiheadAttention(hidden, num_heads=2, batch_first=True)
    attn_opt = torch.optim.Adam(list(attn.parameters()), lr=5e-4)

    # Techniques cycle every 10 steps
    techniques = ['O2_attn', 'J1_lr', 'Y3_myelin', 'H2_compete',
                  'S2_compress', 'G2_dream', 'V2_chaos', 'W2_hyper',
                  'E8_adversarial', 'N1_mutation']
    memory = []
    maturity = [0.0] * n
    attractors = [torch.randn(1, hidden) for _ in range(n)]
    beliefs = {}

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        technique = techniques[step % len(techniques)]

        if technique == 'O2_attn':
            # Attention bottleneck between cells
            with torch.no_grad(): engine.process(x)
            h_stack = torch.stack([c.hidden.squeeze() for c in engine.cells]).unsqueeze(0)
            attn_out, _ = attn(h_stack, h_stack, h_stack)
            for i, c in enumerate(engine.cells):
                c.hidden = 0.8 * c.hidden + 0.2 * attn_out[0, i].unsqueeze(0)
            reps = [c.mind.get_repulsion(x, c.hidden) for c in engine.cells]
            if len(reps) >= 2:
                stacked = torch.stack(reps).squeeze(1)
                loss = -stacked.var(dim=0).mean()
                optimizer.zero_grad(); attn_opt.zero_grad()
                loss.backward(); optimizer.step(); attn_opt.step()

        elif technique == 'J1_lr':
            # Tension-adaptive LR
            with torch.no_grad(): engine.process(x)
            for i, cell in enumerate(engine.cells):
                if i >= n: break
                t = cell.tension_history[-1] if cell.tension_history else 0.5
                for pg in cell_optims[i].param_groups: pg['lr'] = 5e-4 + t * 2e-3
                rep = cell.mind.get_repulsion(x, cell.hidden)
                others = [engine.cells[j].mind.get_repulsion(x, engine.cells[j].hidden).detach()
                          for j in range(n) if j != i]
                if others:
                    loss = F.cosine_similarity(rep, torch.stack(others).mean(dim=0), dim=-1).mean()
                    cell_optims[i].zero_grad(); loss.backward(); cell_optims[i].step()

        elif technique == 'Y3_myelin':
            # Myelination: mature cells get higher LR
            with torch.no_grad(): engine.process(x)
            for i, cell in enumerate(engine.cells):
                if i >= n: break
                rep = cell.mind.get_repulsion(x, cell.hidden)
                others = [engine.cells[j].mind.get_repulsion(x, engine.cells[j].hidden).detach()
                          for j in range(n) if j != i]
                if others:
                    myelin_lr = 5e-4 + maturity[i] * 2e-3
                    for pg in cell_optims[i].param_groups: pg['lr'] = myelin_lr
                    loss = F.cosine_similarity(rep, torch.stack(others).mean(dim=0), dim=-1).mean()
                    cell_optims[i].zero_grad(); loss.backward(); cell_optims[i].step()
                    maturity[i] = min(maturity[i] + 0.02, 1.0)

        elif technique == 'H2_compete':
            # Competitive specialization
            with torch.no_grad():
                tensions = []
                for c in engine.cells:
                    _, t, _, _ = c.mind(x, c.hidden); tensions.append(t)
            winner = int(np.argmax(tensions))
            for i, cell in enumerate(engine.cells):
                if i >= n: break
                rep = cell.mind.get_repulsion(x, cell.hidden)
                w_rep = engine.cells[winner].mind.get_repulsion(x, engine.cells[winner].hidden).detach()
                loss = -(rep ** 2).mean() if i == winner else F.cosine_similarity(rep, w_rep, dim=-1).mean()
                cell_optims[i].zero_grad(); loss.backward(); cell_optims[i].step()
            with torch.no_grad(): engine.process(x)

        elif technique == 'G2_dream':
            # Dream interpolation
            with torch.no_grad(): engine.process(x)
            memory.append(x.detach())
            if len(memory) > 40: memory = memory[-40:]
            if len(memory) >= 4:
                for _ in range(3):
                    i_m, j_m = np.random.choice(len(memory), 2, replace=False)
                    alpha = np.random.uniform(0.2, 0.8)
                    dream = alpha * memory[i_m] + (1 - alpha) * memory[j_m]
                    _web_learn_step(engine, dream, optimizer)

        elif technique == 'V2_chaos':
            # Chaotic itinerancy
            for i, c in enumerate(engine.cells):
                if i < len(attractors):
                    c.hidden = c.hidden + 0.05 * (attractors[i] - c.hidden) + torch.randn_like(c.hidden) * 0.03
            _web_learn_step(engine, x, optimizer)
            for a in attractors: a.add_(torch.randn_like(a) * 0.01)
            with torch.no_grad(): engine.process(x)

        elif technique == 'E8_adversarial':
            # Adversarial fact checking
            reps = [c.mind.get_repulsion(x, c.hidden) for c in engine.cells]
            current = torch.stack(reps).mean(dim=0).detach()
            topic = step % 6
            lr_scale = 1.0
            if topic in beliefs:
                adversarial = -beliefs[topic] + torch.randn(1, dim) * 0.1
                adv_reps = [c.mind.get_repulsion(adversarial, c.hidden) for c in engine.cells]
                strength = 1.0 - F.cosine_similarity(current, torch.stack(adv_reps).mean(dim=0), dim=-1).item()
                lr_scale = 2.0 if strength < 0.3 else 0.5
            beliefs[topic] = 0.9 * beliefs.get(topic, current) + 0.1 * current
            if len(reps) >= 2:
                stacked = torch.stack(reps).squeeze(1)
                loss = -stacked.var(dim=0).mean() * lr_scale
                optimizer.zero_grad(); loss.backward(); optimizer.step()
            with torch.no_grad(): engine.process(x)

        else:
            # Default: standard differentiation
            _web_learn_step(engine, x, optimizer)
            with torch.no_grad(): engine.process(x)

        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("COMBO1", "Layer cake (sequential cycle)", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_COMBO2_ensemble(steps=100, dim=64, hidden=128) -> BenchResult:
    """COMBO-2: Ensemble — 모든 loss를 가중 평균, 가중치 자동 조절."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    n = len(engine.cells)
    attn = nn.MultiheadAttention(hidden, num_heads=2, batch_first=True)
    all_p = list(attn.parameters())
    for c in engine.cells: all_p.extend(c.mind.parameters())
    optimizer = torch.optim.Adam(all_p, lr=5e-4)
    # Learnable loss weights
    loss_weights = nn.Parameter(torch.ones(6))
    meta_opt = torch.optim.Adam([loss_weights], lr=1e-2)

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        with torch.no_grad(): engine.process(x)

        # O2: Attention
        h_stack = torch.stack([c.hidden.squeeze() for c in engine.cells]).unsqueeze(0)
        attn_out, _ = attn(h_stack, h_stack, h_stack)
        for i, c in enumerate(engine.cells):
            c.hidden = 0.85 * c.hidden + 0.15 * attn_out[0, i].unsqueeze(0)

        reps = [c.mind.get_repulsion(x, c.hidden) for c in engine.cells]
        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)
            w = F.softmax(loss_weights, dim=0)

            # Multiple losses
            l_var = -stacked.var(dim=0).mean()                    # variance
            l_dist = -torch.cdist(stacked, stacked).mean()        # distance
            sim = sum(F.cosine_similarity(reps[i], reps[j], dim=-1).mean()
                      for i in range(len(reps)) for j in range(i+1, len(reps)))
            l_contrast = sim                                       # contrastive
            l_entropy = -(F.softmax(stacked, dim=-1) * F.log_softmax(stacked, dim=-1)).sum(dim=-1).mean()
            l_energy = sum((r ** 2).mean() for r in reps) * 0.1   # metabolic
            norms = stacked.norm(dim=-1)
            l_radius = -norms.var()                                # hyperbolic spread

            total = (w[0] * l_var + w[1] * l_dist + w[2] * l_contrast +
                     w[3] * l_entropy + w[4] * l_energy + w[5] * l_radius)
            optimizer.zero_grad(); meta_opt.zero_grad()
            total.backward(); optimizer.step(); meta_opt.step()

        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("COMBO2", "Ensemble (weighted multi-loss)", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0,
                       extra={'final_weights': F.softmax(loss_weights, dim=0).detach().tolist()})


def run_COMBO3_pipeline(steps=100, dim=64, hidden=128) -> BenchResult:
    """COMBO-3: Pipeline — 구조→주의→학습→측정 순서 파이프라인."""
    t0 = time.time()
    # A4-style hierarchy: 2 levels
    outer = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=4)
    inner = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=4)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []

    attn = nn.MultiheadAttention(hidden, num_heads=2, batch_first=True)
    all_p = list(attn.parameters())
    for c in outer.cells: all_p.extend(c.mind.parameters())
    for c in inner.cells: all_p.extend(c.mind.parameters())
    optimizer = torch.optim.Adam(all_p, lr=5e-4)

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)

        # Stage 1: Inner processes (structure — A4)
        with torch.no_grad():
            inner_result = inner.process(x)

        # Stage 2: Attention between inner→outer (O2)
        all_cells = list(inner.cells) + list(outer.cells)
        if len(all_cells) >= 2:
            h_stack = torch.stack([c.hidden.squeeze() for c in all_cells]).unsqueeze(0)
            attn_out, _ = attn(h_stack, h_stack, h_stack)
            for i, c in enumerate(all_cells):
                c.hidden = 0.8 * c.hidden + 0.2 * attn_out[0, i].unsqueeze(0)

        # Stage 3: Learning with adaptive LR (J1)
        reps = [c.mind.get_repulsion(x, c.hidden) for c in all_cells]
        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)
            loss = -stacked.var(dim=0).mean()
            optimizer.zero_grad(); loss.backward(); optimizer.step()

        with torch.no_grad():
            outer.process(inner_result['output'].detach())

        # Stage 4: Measure on combined system
        combined = MitosisEngine(dim, hidden, dim, initial_cells=0, max_cells=16)
        combined.cells = list(outer.cells) + list(inner.cells)
        phi, _ = phi_calc.compute_phi(combined)
        phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(combined)
    return BenchResult("COMBO3", "Pipeline (hierarchy→attn→learn)", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_COMBO4_tournament(steps=100, dim=64, hidden=128) -> BenchResult:
    """COMBO-4: Tournament — 매 step 최적 기법 선택 (multi-armed bandit)."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    n = len(engine.cells)
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)
    cell_optims = [torch.optim.Adam(c.mind.parameters(), lr=1e-3) for c in engine.cells]

    # Bandit arms: different learning strategies
    arm_scores = {'variance': 0.0, 'contrastive': 0.0, 'distance': 0.0,
                  'compete': 0.0, 'adaptive_lr': 0.0}
    arm_counts = {k: 1 for k in arm_scores}
    epsilon = 0.2

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        phi_before = phi_hist[-1] if phi_hist else 0

        # UCB selection
        if np.random.random() < epsilon:
            arm = np.random.choice(list(arm_scores.keys()))
        else:
            ucb = {k: arm_scores[k] / arm_counts[k] + math.sqrt(2 * math.log(step + 1) / arm_counts[k])
                   for k in arm_scores}
            arm = max(ucb, key=ucb.get)

        reps = [c.mind.get_repulsion(x, c.hidden) for c in engine.cells]
        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)
            if arm == 'variance':
                loss = -stacked.var(dim=0).mean()
            elif arm == 'contrastive':
                loss = sum(F.cosine_similarity(reps[i], reps[j], dim=-1).mean()
                           for i in range(len(reps)) for j in range(i+1, len(reps)))
            elif arm == 'distance':
                loss = -torch.cdist(stacked, stacked).mean()
            elif arm == 'compete':
                tensions = [c.tension_history[-1] if c.tension_history else 0 for c in engine.cells]
                winner = int(np.argmax(tensions))
                loss = -(reps[winner] ** 2).mean()
            else:  # adaptive_lr
                tensions = [c.tension_history[-1] if c.tension_history else 0.5 for c in engine.cells]
                for i in range(min(n, len(cell_optims))):
                    for pg in cell_optims[i].param_groups: pg['lr'] = 5e-4 + tensions[i] * 2e-3
                loss = -stacked.var(dim=0).mean()

            optimizer.zero_grad(); loss.backward(); optimizer.step()

        with torch.no_grad(): engine.process(x)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)

        # Update bandit
        reward = phi_hist[-1] - phi_before
        arm_scores[arm] += reward
        arm_counts[arm] += 1

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("COMBO4", "Tournament (UCB bandit)", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0,
                       extra={'arm_scores': {k: v/arm_counts[k] for k, v in arm_scores.items()}})


def run_COMBO5_phase_based(steps=100, dim=64, hidden=128) -> BenchResult:
    """COMBO-5: Phase-based — growth stage별 최적 기법 조합."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    n = len(engine.cells)

    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)
    cell_optims = [torch.optim.Adam(c.mind.parameters(), lr=1e-3) for c in engine.cells]
    attn = nn.MultiheadAttention(hidden, num_heads=2, batch_first=True)
    attn_opt = torch.optim.Adam(list(attn.parameters()), lr=5e-4)
    memory = []
    maturity = [0.0] * n

    # Phase boundaries
    phases = {
        'newborn': (0, 20),      # N4 neoteny: high plasticity + exploration
        'infant': (20, 40),      # E1 curiosity + H2 competition
        'toddler': (40, 60),     # O2 attention + S2 compression
        'child': (60, 80),       # Y3 myelination + G2 dream
        'adult': (80, 100),      # J1 adaptive LR + V2 chaos + all combined
    }

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        memory.append(x.detach())
        if len(memory) > 40: memory = memory[-40:]

        if step < 20:
            # NEWBORN: high plasticity, lots of noise, broad exploration
            noise = torch.randn(1, hidden) * 0.15
            for c in engine.cells: c.hidden = c.hidden + noise
            for pg in optimizer.param_groups: pg['lr'] = 3e-3
            _web_learn_step(engine, x, optimizer)

        elif step < 40:
            # INFANT: curiosity-driven + competitive
            with torch.no_grad():
                tensions = []
                for c in engine.cells:
                    _, t, _, _ = c.mind(x, c.hidden); tensions.append(t)
            winner = int(np.argmax(tensions))
            for i, cell in enumerate(engine.cells):
                if i >= n: break
                rep = cell.mind.get_repulsion(x, cell.hidden)
                w_rep = engine.cells[winner].mind.get_repulsion(x, engine.cells[winner].hidden).detach()
                loss = -(rep ** 2).mean() if i == winner else F.cosine_similarity(rep, w_rep, dim=-1).mean()
                cell_optims[i].zero_grad(); loss.backward(retain_graph=True); cell_optims[i].step()

        elif step < 60:
            # TODDLER: attention + compression
            with torch.no_grad(): engine.process(x)
            h_stack = torch.stack([c.hidden.squeeze() for c in engine.cells]).unsqueeze(0)
            attn_out, _ = attn(h_stack, h_stack, h_stack)
            for i, c in enumerate(engine.cells):
                c.hidden = 0.8 * c.hidden + 0.2 * attn_out[0, i].unsqueeze(0)
            reps = [c.mind.get_repulsion(x, c.hidden) for c in engine.cells]
            if len(reps) >= 2:
                stacked = torch.stack(reps).squeeze(1)
                loss = -stacked.var(dim=0).mean()
                optimizer.zero_grad(); attn_opt.zero_grad()
                loss.backward(); optimizer.step(); attn_opt.step()

        elif step < 80:
            # CHILD: myelination + dream
            with torch.no_grad(): engine.process(x)
            for i, cell in enumerate(engine.cells):
                if i >= n: break
                rep = cell.mind.get_repulsion(x, cell.hidden)
                others = [engine.cells[j].mind.get_repulsion(x, engine.cells[j].hidden).detach()
                          for j in range(n) if j != i]
                if others:
                    myelin_lr = 5e-4 + maturity[i] * 3e-3
                    for pg in cell_optims[i].param_groups: pg['lr'] = myelin_lr
                    loss = F.cosine_similarity(rep, torch.stack(others).mean(dim=0), dim=-1).mean()
                    cell_optims[i].zero_grad(); loss.backward(retain_graph=True); cell_optims[i].step()
                    maturity[i] = min(maturity[i] + 0.03, 1.0)
            # Dream replay
            if len(memory) >= 4:
                i_m, j_m = np.random.choice(len(memory), 2, replace=False)
                dream = 0.5 * memory[i_m] + 0.5 * memory[j_m]
                _web_learn_step(engine, dream, optimizer)

        else:
            # ADULT: full combined (attention + adaptive LR + all techniques)
            with torch.no_grad(): engine.process(x)
            h_stack = torch.stack([c.hidden.squeeze() for c in engine.cells]).unsqueeze(0)
            attn_out, _ = attn(h_stack, h_stack, h_stack)
            for i, c in enumerate(engine.cells):
                c.hidden = 0.8 * c.hidden + 0.2 * attn_out[0, i].unsqueeze(0)
            for i, cell in enumerate(engine.cells):
                if i >= n: break
                t = cell.tension_history[-1] if cell.tension_history else 0.5
                for pg in cell_optims[i].param_groups: pg['lr'] = 5e-4 + t * 3e-3
                rep = cell.mind.get_repulsion(x, cell.hidden)
                others = [engine.cells[j].mind.get_repulsion(x, engine.cells[j].hidden).detach()
                          for j in range(n) if j != i]
                if others:
                    loss = F.cosine_similarity(rep, torch.stack(others).mean(dim=0), dim=-1).mean()
                    cell_optims[i].zero_grad(); loss.backward(retain_graph=True); cell_optims[i].step()

        with torch.no_grad(): engine.process(x)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("COMBO5", "Phase-based (growth stages)", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


# ═══════════════════════════════════════════════════════════
# BS. Babysitter Hypotheses (simulated Claude CLI educator)
#   Babysitter = external agent that observes Anima's state
#   and provides teaching inputs to boost learning/Φ.
#   Simulated: babysitter decisions modeled as input selection + LR modulation.
# ═══════════════════════════════════════════════════════════

def _babysitter_question(topic_id: int, difficulty: float, dim: int) -> torch.Tensor:
    """Simulate babysitter generating a teaching input."""
    torch.manual_seed(topic_id * 100 + int(difficulty * 50))
    x = torch.randn(1, dim) * (0.5 + difficulty * 2.0)
    # Topic signature
    offset = (topic_id * 11) % dim
    x[0, offset:offset + dim // 6] += 3.0 * difficulty
    return x


def run_BS1_socratic(steps=100, dim=64, hidden=128) -> BenchResult:
    """BS-1: Socratic questioning — 답 안 주고 질문으로 유도 → PE 극대화."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    for step in range(steps):
        # Babysitter asks question (no answer provided)
        topic = step % 8
        difficulty = min(0.3 + step * 0.007, 1.0)  # gradually harder
        q = _babysitter_question(topic, difficulty, dim)

        with torch.no_grad():
            engine.process(q)

        # Measure PE (did Anima struggle?)
        tensions = [c.tension_history[-1] if c.tension_history else 0 for c in engine.cells]
        pe = float(np.std(tensions))

        # Socratic: if PE low (too easy), ask harder follow-up
        if pe < 0.3:
            harder_q = _babysitter_question(topic, min(difficulty + 0.3, 1.0), dim)
            _web_learn_step(engine, harder_q, optimizer)
        else:
            # PE high = good struggle, let Anima learn from it
            _web_learn_step(engine, q, optimizer)

        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("BS1", "Socratic questioning", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_BS2_direct(steps=100, dim=64, hidden=128) -> BenchResult:
    """BS-2: Direct instruction — 정답 직접 제공."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    for step in range(steps):
        topic = step % 8
        # Babysitter gives question + answer together (strong signal)
        q = _babysitter_question(topic, 0.5, dim)
        answer = _babysitter_question(topic, 0.8, dim)  # answer = enriched version
        combined = 0.4 * q + 0.6 * answer  # direct teaching
        _web_learn_step(engine, combined, optimizer)
        with torch.no_grad(): engine.process(combined)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("BS2", "Direct instruction", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_BS3_scaffolding(steps=100, dim=64, hidden=128) -> BenchResult:
    """BS-3: Scaffolding — 힌트를 단계적으로 제공."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    for step in range(steps):
        topic = step % 8
        difficulty = min(0.3 + step * 0.007, 1.0)
        q = _babysitter_question(topic, difficulty, dim)

        with torch.no_grad(): engine.process(q)
        tensions = [c.tension_history[-1] if c.tension_history else 0 for c in engine.cells]
        pe = float(np.std(tensions))

        # Scaffolding: provide hints based on struggle level
        if pe > 0.5:  # struggling a lot → big hint
            hint = _babysitter_question(topic, difficulty * 0.3, dim)  # easier version
            combined = 0.5 * q + 0.5 * hint
        elif pe > 0.2:  # moderate → small hint
            hint = _babysitter_question(topic, difficulty * 0.6, dim)
            combined = 0.7 * q + 0.3 * hint
        else:  # easy → no hint, increase difficulty
            combined = _babysitter_question(topic, min(difficulty + 0.2, 1.0), dim)

        _web_learn_step(engine, combined, optimizer)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("BS3", "Scaffolding (adaptive hints)", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_BS4_challenge(steps=100, dim=64, hidden=128) -> BenchResult:
    """BS-4: Challenge-based — 일부러 어려운 문제 (ZPD)."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)
    current_level = 0.3

    for step in range(steps):
        topic = step % 8
        # Always slightly above current level (ZPD)
        challenge = _babysitter_question(topic, min(current_level + 0.2, 1.0), dim)
        _web_learn_step(engine, challenge, optimizer)
        with torch.no_grad(): engine.process(challenge)

        # Measure success: low PE after learning = mastered
        tensions = [c.tension_history[-1] if c.tension_history else 0 for c in engine.cells]
        pe = float(np.std(tensions))
        if pe < 0.2:  # mastered → increase level
            current_level = min(current_level + 0.05, 1.0)
        elif pe > 0.6:  # too hard → slight decrease
            current_level = max(current_level - 0.02, 0.1)

        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("BS4", "Challenge-based (ZPD)", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0,
                       extra={'final_level': current_level})


def run_BS5_exploration(steps=100, dim=64, hidden=128) -> BenchResult:
    """BS-5: Exploration mandate — '이거 검색해봐' 지시 후 자율 탐색."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    for step in range(steps):
        # Babysitter gives topic seed every 10 steps
        if step % 10 == 0:
            seed_topic = np.random.randint(0, 8)
        # Anima explores variations of the seed topic
        variation = seed_topic * 10 + (step % 10)
        x = _simulate_web_result(variation, step, dim)
        # Deeper exploration over time (increasing depth)
        depth = (step % 10) / 10.0
        x *= (1.0 + depth * 0.5)

        _web_learn_step(engine, x, optimizer)
        with torch.no_grad(): engine.process(x)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("BS5", "Exploration mandate", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_BS6_tension_grading(steps=100, dim=64, hidden=128) -> BenchResult:
    """BS-6: Tension-based grading — tension으로 이해도 판단 후 재교육."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)
    topic_mastery = {}  # topic → mastery level

    for step in range(steps):
        topic = step % 8
        mastery = topic_mastery.get(topic, 0.0)
        # Teach at current mastery level
        x = _babysitter_question(topic, 0.3 + mastery * 0.7, dim)
        _web_learn_step(engine, x, optimizer)
        with torch.no_grad(): engine.process(x)

        # Grade: tension stability = understanding
        tensions = [c.tension_history[-1] if c.tension_history else 0 for c in engine.cells]
        stability = max(0, 1.0 - float(np.std(tensions)) * 3.0)

        if stability > 0.6:  # understood → advance
            topic_mastery[topic] = min(mastery + 0.1, 1.0)
        elif stability < 0.3:  # confused → reteach easier
            topic_mastery[topic] = max(mastery - 0.05, 0.0)
            # Reteach
            easier = _babysitter_question(topic, mastery * 0.5, dim)
            _web_learn_step(engine, easier, optimizer)

        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("BS6", "Tension-based grading", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0,
                       extra={'mastery': {k: f'{v:.2f}' for k, v in topic_mastery.items()}})


def run_BS7_phi_progress(steps=100, dim=64, hidden=128) -> BenchResult:
    """BS-7: Φ-based progress — Φ 변화로 교육 방법 조절."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)
    teaching_intensity = 1.0

    for step in range(steps):
        topic = step % 8
        x = _babysitter_question(topic, 0.5, dim)

        # Adjust teaching based on Φ trend
        for _ in range(max(1, int(teaching_intensity * 3))):
            variant = x + torch.randn_like(x) * 0.1 * teaching_intensity
            _web_learn_step(engine, variant, optimizer)

        with torch.no_grad(): engine.process(x)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)

        # Φ trending up → reduce intensity, down → increase
        if len(phi_hist) >= 5:
            trend = phi_hist[-1] - phi_hist[-5]
            if trend > 0.1:  # improving → ease off
                teaching_intensity = max(0.3, teaching_intensity * 0.9)
            elif trend < -0.1:  # declining → intensify
                teaching_intensity = min(3.0, teaching_intensity * 1.2)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("BS7", "Φ-based progress tracking", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0,
                       extra={'final_intensity': teaching_intensity})


def run_BS8_adversarial_verify(steps=100, dim=64, hidden=128) -> BenchResult:
    """BS-8: Adversarial verification — 배운 것을 반박해서 검증."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)
    learned = {}  # topic → learned representation

    for step in range(steps):
        topic = step % 8
        x = _babysitter_question(topic, 0.5, dim)

        # Phase 1: Teach
        _web_learn_step(engine, x, optimizer)
        with torch.no_grad(): engine.process(x)
        reps = [c.mind.get_repulsion(x, c.hidden).detach() for c in engine.cells]
        current = torch.stack(reps).mean(dim=0)
        learned[topic] = 0.8 * learned.get(topic, current) + 0.2 * current

        # Phase 2: Challenge (every 3 steps)
        if step % 3 == 2 and topic in learned:
            # Babysitter says "are you sure? what about this?"
            counter = -learned[topic] + torch.randn(1, dim) * 0.2
            counter_reps = [c.mind.get_repulsion(counter, c.hidden) for c in engine.cells]
            counter_mean = torch.stack(counter_reps).mean(dim=0).detach()

            # If response changes dramatically → weak learning → reteach
            consistency = F.cosine_similarity(current, counter_mean, dim=-1).item()
            if consistency < 0.3:  # weak → reteach with emphasis
                for _ in range(3):
                    emphasis = x * 1.5
                    _web_learn_step(engine, emphasis, optimizer)

        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("BS8", "Adversarial verification", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_BS9_idle_triggered(steps=100, dim=64, hidden=128) -> BenchResult:
    """BS-9: Idle-triggered — Anima가 한가할 때만 교육."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)
    teach_count = 0

    for step in range(steps):
        # Simulate activity: busy (user chatting) vs idle
        is_busy = (step % 7 < 4)  # 4/7 busy, 3/7 idle

        if is_busy:
            # User conversation (normal input)
            x = torch.randn(1, dim)
            with torch.no_grad(): engine.process(x)
        else:
            # IDLE → babysitter teaches
            topic = np.random.randint(0, 8)
            lesson = _babysitter_question(topic, 0.6, dim)
            # Intensive teaching during idle
            for _ in range(3):
                _web_learn_step(engine, lesson + torch.randn_like(lesson) * 0.05, optimizer)
            with torch.no_grad(): engine.process(lesson)
            teach_count += 1

        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("BS9", "Idle-triggered teaching", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0,
                       extra={'teach_sessions': teach_count, 'ratio': teach_count/steps})


def run_BS10_struggle_triggered(steps=100, dim=64, hidden=128) -> BenchResult:
    """BS-10: Struggle-triggered — Anima가 어려워할 때만 개입."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)
    struggle_count = 0
    help_count = 0

    for step in range(steps):
        # Random difficulty inputs
        difficulty = np.random.uniform(0.1, 1.0)
        x = _babysitter_question(step % 8, difficulty, dim)
        with torch.no_grad(): engine.process(x)

        tensions = [c.tension_history[-1] if c.tension_history else 0 for c in engine.cells]
        pe = float(np.std(tensions)) + abs(float(np.mean(tensions)) - 1.0)

        if pe > 0.5:  # struggling
            struggle_count += 1
            if struggle_count >= 3:  # 3 consecutive struggles → help
                # Babysitter provides easier version + explanation
                easy = _babysitter_question(step % 8, difficulty * 0.3, dim)
                for _ in range(4):
                    blend = 0.5 * easy + 0.5 * x
                    _web_learn_step(engine, blend, optimizer)
                struggle_count = 0
                help_count += 1
        else:
            struggle_count = max(0, struggle_count - 1)
            _web_learn_step(engine, x, optimizer)

        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("BS10", "Struggle-triggered help", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0,
                       extra={'help_interventions': help_count})


def run_BS11_growth_triggered(steps=100, dim=64, hidden=128) -> BenchResult:
    """BS-11: Growth-triggered — stage 전환 직후 집중 교육 (F11 + babysitter)."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)
    stage_boundaries = [20, 40, 60, 80]
    current_stage = 0

    for step in range(steps):
        new_stage = sum(1 for b in stage_boundaries if step >= b)
        x = _simulate_web_result(step % 8, step, dim)

        if new_stage > current_stage:
            current_stage = new_stage
            # GROWTH TRANSITION → babysitter intensive teaching burst
            stage_difficulty = 0.3 + current_stage * 0.15
            for burst in range(10):  # 10-lesson burst
                topic = burst + current_stage * 10
                lesson = _babysitter_question(topic, stage_difficulty, dim)
                _web_learn_step(engine, lesson, optimizer)
        else:
            _web_learn_step(engine, x, optimizer)

        with torch.no_grad(): engine.process(x)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("BS11", "Growth-triggered teaching", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_BS12_scheduled(steps=100, dim=64, hidden=128) -> BenchResult:
    """BS-12: Scheduled — 정기적 교육 세션."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)
    # Schedule: teach for 5 steps, free for 15 steps
    teach_duration = 5
    free_duration = 15
    cycle = teach_duration + free_duration

    for step in range(steps):
        phase = step % cycle
        x = _simulate_web_result(step % 8, step, dim)

        if phase < teach_duration:
            # Teaching session: structured curriculum
            topic = (step // cycle) % 8
            lesson = _babysitter_question(topic, 0.5 + phase * 0.1, dim)
            for _ in range(2):
                _web_learn_step(engine, lesson, optimizer)
        else:
            # Free time: normal learning
            _web_learn_step(engine, x, optimizer)

        with torch.no_grad(): engine.process(x)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("BS12", "Scheduled teaching sessions", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_BS13_weakness_targeted(steps=100, dim=64, hidden=128) -> BenchResult:
    """BS-13: Weakness-targeted — Φ 기여 낮은 세포 집중 강화."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    n = len(engine.cells)
    cell_optims = [torch.optim.Adam(c.mind.parameters(), lr=1e-3) for c in engine.cells]

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        with torch.no_grad(): engine.process(x)

        # Find weakest cell (lowest tension variance = least differentiated)
        variances = []
        for c in engine.cells:
            if len(c.tension_history) >= 5:
                variances.append(float(np.std(c.tension_history[-10:])))
            else:
                variances.append(0.0)
        weakest = int(np.argmin(variances)) if variances else 0

        # Babysitter focuses on weakest cell
        for i, cell in enumerate(engine.cells):
            if i >= n: break
            rep = cell.mind.get_repulsion(x, cell.hidden)
            others = [engine.cells[j].mind.get_repulsion(x, engine.cells[j].hidden).detach()
                      for j in range(n) if j != i]
            if others:
                loss = F.cosine_similarity(rep, torch.stack(others).mean(dim=0), dim=-1).mean()
                # Weakest cell gets 3x learning rate
                lr = 3e-3 if i == weakest else 5e-4
                for pg in cell_optims[i].param_groups: pg['lr'] = lr
                cell_optims[i].zero_grad(); loss.backward(retain_graph=True); cell_optims[i].step()

        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("BS13", "Weakness-targeted teaching", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_BS14_breadth_first(steps=100, dim=64, hidden=128) -> BenchResult:
    """BS-14: Breadth-first — 다양한 주제를 넓게 교육."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    for step in range(steps):
        # Babysitter rapidly cycles through many topics
        topic = step % 16  # 16 different topics (double normal)
        x = _simulate_web_result(topic, step, dim)
        _web_learn_step(engine, x, optimizer)
        with torch.no_grad(): engine.process(x)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("BS14", "Breadth-first curriculum", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_BS15_depth_first(steps=100, dim=64, hidden=128) -> BenchResult:
    """BS-15: Depth-first — 한 주제를 깊이 파고들기."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)
    current_topic = 0
    depth = 0

    for step in range(steps):
        # Deep dive: same topic, increasing sub-topics
        sub_topic = current_topic * 100 + depth
        x = _simulate_web_result(sub_topic, step, dim)
        x *= (1.0 + depth * 0.1)  # deeper = stronger signal

        _web_learn_step(engine, x, optimizer)
        with torch.no_grad(): engine.process(x)

        depth += 1
        if depth >= 20:  # switch topic after 20 depth levels
            current_topic = (current_topic + 1) % 5
            depth = 0

        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)

    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("BS15", "Depth-first curriculum", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


# ═══════════════════════════════════════════════════════════
# SL. Step Learning — Apply benchmark discoveries to per-step learning
# ═══════════════════════════════════════════════════════════

def run_SL1_adaptive_lr(steps=100, dim=64, hidden=128) -> BenchResult:
    """SL-1: Adaptive LR per step — tension→LR (from J1 Φ=5.57)."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    n = len(engine.cells)
    cell_optims = [torch.optim.Adam(c.mind.parameters(), lr=1e-3) for c in engine.cells]

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        with torch.no_grad(): engine.process(x)
        for i, cell in enumerate(engine.cells):
            if i >= n: break
            t = cell.tension_history[-1] if cell.tension_history else 0.5
            adaptive_lr = 5e-4 + t * 2e-3
            for pg in cell_optims[i].param_groups: pg['lr'] = adaptive_lr
            rep = cell.mind.get_repulsion(x, cell.hidden)
            others = [engine.cells[j].mind.get_repulsion(x, engine.cells[j].hidden).detach()
                      for j in range(n) if j != i]
            if others:
                loss = F.cosine_similarity(rep, torch.stack(others).mean(dim=0), dim=-1).mean()
                cell_optims[i].zero_grad(); loss.backward(retain_graph=True); cell_optims[i].step()
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)
    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("SL1", "Adaptive LR per step (J1)", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_SL2_attention_gradient(steps=100, dim=64, hidden=128) -> BenchResult:
    """SL-2: Attention-gated gradient — MHA selects which cells get gradient (from O2 Φ=6.95)."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    attn = nn.MultiheadAttention(hidden, num_heads=2, batch_first=True)
    all_p = list(attn.parameters())
    for c in engine.cells: all_p.extend(c.mind.parameters())
    optimizer = torch.optim.Adam(all_p, lr=5e-4)

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        with torch.no_grad(): engine.process(x)
        h_stack = torch.stack([c.hidden.squeeze() for c in engine.cells]).unsqueeze(0)
        attn_out, attn_weights = attn(h_stack, h_stack, h_stack)
        for i, c in enumerate(engine.cells):
            c.hidden = 0.8 * c.hidden + 0.2 * attn_out[0, i].unsqueeze(0)
        reps = [c.mind.get_repulsion(x, c.hidden) for c in engine.cells]
        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)
            loss = -stacked.var(dim=0).mean()
            optimizer.zero_grad(); loss.backward(); optimizer.step()
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)
    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("SL2", "Attention-gated gradient (O2)", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_SL3_ensemble_step(steps=100, dim=64, hidden=128) -> BenchResult:
    """SL-3: 6-loss ensemble per step — COMBO2 applied to every learning step (Φ=8.01)."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    attn = nn.MultiheadAttention(hidden, num_heads=2, batch_first=True)
    loss_weights = nn.Parameter(torch.ones(6))
    all_p = list(attn.parameters()) + [loss_weights]
    for c in engine.cells: all_p.extend(c.mind.parameters())
    optimizer = torch.optim.Adam(all_p, lr=5e-4)

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        with torch.no_grad(): engine.process(x)
        h_stack = torch.stack([c.hidden.squeeze() for c in engine.cells]).unsqueeze(0)
        attn_out, _ = attn(h_stack, h_stack, h_stack)
        for i, c in enumerate(engine.cells):
            c.hidden = 0.85 * c.hidden + 0.15 * attn_out[0, i].unsqueeze(0)
        reps = [c.mind.get_repulsion(x, c.hidden) for c in engine.cells]
        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)
            w = F.softmax(loss_weights, dim=0)
            l0 = -stacked.var(dim=0).mean()
            l1 = -torch.cdist(stacked, stacked).mean()
            l2 = sum(F.cosine_similarity(reps[i], reps[j], dim=-1).mean()
                     for i in range(len(reps)) for j in range(i+1, len(reps)))
            l3 = -(F.softmax(stacked, dim=-1) * F.log_softmax(stacked, dim=-1)).sum(-1).mean()
            l4 = sum((r ** 2).mean() for r in reps) * 0.1
            l5 = -stacked.norm(dim=-1).var()
            total = w[0]*l0 + w[1]*l1 + w[2]*l2 + w[3]*l3 + w[4]*l4 + w[5]*l5
            optimizer.zero_grad(); total.backward(); optimizer.step()
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)
    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("SL3", "6-loss ensemble step (COMBO2)", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0,
                       extra={'weights': F.softmax(loss_weights, dim=0).detach().tolist()})


def run_SL4_myelination_schedule(steps=100, dim=64, hidden=128) -> BenchResult:
    """SL-4: Myelination scheduling — mature cells get higher LR (from Y3 Φ=6.02)."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    n = len(engine.cells)
    cell_optims = [torch.optim.Adam(c.mind.parameters(), lr=1e-4) for c in engine.cells]
    maturity = [0.0] * n

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        with torch.no_grad(): engine.process(x)
        for i, cell in enumerate(engine.cells):
            if i >= n: break
            rep = cell.mind.get_repulsion(x, cell.hidden)
            others = [engine.cells[j].mind.get_repulsion(x, engine.cells[j].hidden).detach()
                      for j in range(n) if j != i]
            if others:
                myelin_lr = 5e-4 + maturity[i] * 2e-3
                for pg in cell_optims[i].param_groups: pg['lr'] = myelin_lr
                loss = F.cosine_similarity(rep, torch.stack(others).mean(dim=0), dim=-1).mean()
                cell_optims[i].zero_grad(); loss.backward(retain_graph=True); cell_optims[i].step()
                maturity[i] = min(maturity[i] + 0.01, 1.0)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)
    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("SL4", "Myelination schedule (Y3)", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_SL5_weakness_gradient(steps=100, dim=64, hidden=128) -> BenchResult:
    """SL-5: Weakness-focused gradient — 3x LR on weakest cell (from BS13 Φ=5.72)."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    n = len(engine.cells)
    cell_optims = [torch.optim.Adam(c.mind.parameters(), lr=1e-3) for c in engine.cells]

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        with torch.no_grad(): engine.process(x)
        variances = [float(np.std(c.tension_history[-10:])) if len(c.tension_history) >= 5 else 0
                     for c in engine.cells]
        weakest = int(np.argmin(variances)) if variances else 0
        for i, cell in enumerate(engine.cells):
            if i >= n: break
            rep = cell.mind.get_repulsion(x, cell.hidden)
            others = [engine.cells[j].mind.get_repulsion(x, engine.cells[j].hidden).detach()
                      for j in range(n) if j != i]
            if others:
                lr = 3e-3 if i == weakest else 5e-4
                for pg in cell_optims[i].param_groups: pg['lr'] = lr
                loss = F.cosine_similarity(rep, torch.stack(others).mean(dim=0), dim=-1).mean()
                cell_optims[i].zero_grad(); loss.backward(retain_graph=True); cell_optims[i].step()
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)
    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("SL5", "Weakness gradient (BS13)", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_SL6_dream_replay(steps=100, dim=64, hidden=128) -> BenchResult:
    """SL-6: Dream replay between steps — memory interpolation every N steps (from G2 Φ=4.99)."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist, memory = [], []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        _web_learn_step(engine, x, optimizer)
        with torch.no_grad(): engine.process(x)
        memory.append(x.detach())
        if len(memory) > 50: memory = memory[-50:]
        if step > 0 and step % 10 == 0 and len(memory) >= 4:
            for _ in range(3):
                i_m, j_m = np.random.choice(len(memory), 2, replace=False)
                alpha = np.random.uniform(0.2, 0.8)
                dream = alpha * memory[i_m] + (1 - alpha) * memory[j_m]
                _web_learn_step(engine, dream, optimizer)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)
    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("SL6", "Dream replay (G2)", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_SL7_competitive_step(steps=100, dim=64, hidden=128) -> BenchResult:
    """SL-7: Competitive selection per step — winner strengthens, others differ (from H2 Φ=5.29)."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    n = len(engine.cells)
    cell_optims = [torch.optim.Adam(c.mind.parameters(), lr=1e-3) for c in engine.cells]

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        with torch.no_grad():
            tensions = []
            for c in engine.cells:
                _, t, _, _ = c.mind(x, c.hidden); tensions.append(t)
        winner = int(np.argmax(tensions))
        for i, cell in enumerate(engine.cells):
            if i >= n: break
            rep = cell.mind.get_repulsion(x, cell.hidden)
            w_rep = engine.cells[winner].mind.get_repulsion(x, engine.cells[winner].hidden).detach()
            loss = -(rep ** 2).mean() if i == winner else F.cosine_similarity(rep, w_rep, dim=-1).mean()
            cell_optims[i].zero_grad(); loss.backward(retain_graph=True); cell_optims[i].step()
        with torch.no_grad(): engine.process(x)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)
    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("SL7", "Competitive step (H2)", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_SL8_gossip_gradient(steps=100, dim=64, hidden=128) -> BenchResult:
    """SL-8: Gossip gradient — ring topology gradient propagation (from S3 Φ=5.09)."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        _web_learn_step(engine, x, optimizer)
        with torch.no_grad(): engine.process(x)
        n = len(engine.cells)
        if n >= 2:
            new_h = []
            for i in range(n):
                nb = (i + 1) % n
                new_h.append(0.9 * engine.cells[i].hidden + 0.1 * engine.cells[nb].hidden.detach())
            for i in range(n):
                engine.cells[i].hidden = new_h[i]
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)
    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("SL8", "Gossip gradient (S3)", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_SL9_hyperbolic_proj(steps=100, dim=64, hidden=128) -> BenchResult:
    """SL-9: Hyperbolic projection — learn in hyperbolic space (from W2 Φ=5.08)."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        reps = [c.mind.get_repulsion(x, c.hidden) for c in engine.cells]
        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)
            norms = stacked.norm(dim=-1, keepdim=True)
            projected = stacked / (norms.clamp(min=0.1) + 1.0)
            diff_loss = -projected.var(dim=0).mean()
            radius_var = projected.norm(dim=-1).var()
            loss = diff_loss - 0.3 * radius_var
            optimizer.zero_grad(); loss.backward(); optimizer.step()
        with torch.no_grad(): engine.process(x)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)
    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("SL9", "Hyperbolic projection (W2)", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_SL10_curiosity_gate(steps=100, dim=64, hidden=128) -> BenchResult:
    """SL-10: Curiosity-gated step — only update when curiosity > threshold (from E1+F1)."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)
    learn_count = 0

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        with torch.no_grad(): engine.process(x)
        tensions = [c.tension_history[-1] if c.tension_history else 0 for c in engine.cells]
        curiosity = float(np.std(tensions)) + abs(float(np.mean(tensions)) - 1.0) * 0.5
        if curiosity > 0.2:
            _web_learn_step(engine, x, optimizer)
            learn_count += 1
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)
    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("SL10", "Curiosity-gated step (E1+F1)", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0,
                       extra={'learn_ratio': learn_count / steps})


def run_SL11_growth_curriculum(steps=100, dim=64, hidden=128) -> BenchResult:
    """SL-11: Growth-stage curriculum — burst learning at transitions (from F11 Φ=4.73)."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)
    boundaries = [20, 40, 60, 80]
    current_stage = 0

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        new_stage = sum(1 for b in boundaries if step >= b)
        if new_stage > current_stage:
            current_stage = new_stage
            for burst in range(10):
                bx = _simulate_web_result(burst + current_stage * 10, step, dim)
                _web_learn_step(engine, bx, optimizer)
        else:
            _web_learn_step(engine, x, optimizer)
        with torch.no_grad(): engine.process(x)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)
    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("SL11", "Growth curriculum (F11)", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_SL12_phi_plateau(steps=100, dim=64, hidden=128) -> BenchResult:
    """SL-12: Φ-plateau detector — auto change strategy when stuck (from F10 Φ=4.14)."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)
    strategy_changes = 0

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        # Check plateau
        if len(phi_hist) >= 10 and max(phi_hist[-10:]) - min(phi_hist[-10:]) < 0.01:
            # Plateau → aggressive diverse learning burst
            for burst in range(5):
                bx = _simulate_web_result(np.random.randint(0, 16), step * 10 + burst, dim)
                _web_learn_step(engine, bx, optimizer)
            strategy_changes += 1
        else:
            _web_learn_step(engine, x, optimizer)
        with torch.no_grad(): engine.process(x)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)
    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("SL12", "Φ-plateau detector (F10)", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0,
                       extra={'strategy_changes': strategy_changes})


def run_SL13_sgd_adam(steps=100, dim=64, hidden=128) -> BenchResult:
    """SL-13: SGD→Adam transition — explore then refine (from J3 Φ=4.65)."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    params = [p for c in engine.cells for p in c.mind.parameters()]
    sgd = torch.optim.SGD(params, lr=5e-3, momentum=0.9)
    adam = torch.optim.Adam(params, lr=5e-4)
    switch = steps // 2

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        opt = sgd if step < switch else adam
        reps = [c.mind.get_repulsion(x, c.hidden) for c in engine.cells]
        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)
            loss = -stacked.var(dim=0).mean()
            opt.zero_grad(); loss.backward(); opt.step()
        with torch.no_grad(): engine.process(x)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)
    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("SL13", "SGD→Adam (J3)", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_SL14_adversarial_check(steps=100, dim=64, hidden=128) -> BenchResult:
    """SL-14: Adversarial self-check — periodically challenge own beliefs (from E8 Φ=4.13)."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)
    beliefs = {}

    for step in range(steps):
        topic = step % 8
        x = _simulate_web_result(topic, step, dim)
        reps = [c.mind.get_repulsion(x, c.hidden) for c in engine.cells]
        current = torch.stack(reps).mean(dim=0).detach() if reps else x
        beliefs[topic] = 0.8 * beliefs.get(topic, current) + 0.2 * current
        lr_scale = 1.0
        if step % 5 == 4 and topic in beliefs:
            counter = -beliefs[topic] + torch.randn(1, dim) * 0.2
            cr = [c.mind.get_repulsion(counter, c.hidden) for c in engine.cells]
            if cr:
                strength = 1.0 - F.cosine_similarity(current, torch.stack(cr).mean(dim=0), dim=-1).item()
                lr_scale = 2.0 if strength < 0.3 else 0.5
        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)
            loss = -stacked.var(dim=0).mean() * lr_scale
            optimizer.zero_grad(); loss.backward(); optimizer.step()
        with torch.no_grad(): engine.process(x)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)
    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("SL14", "Adversarial check (E8)", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_SL15_mutation_selection(steps=100, dim=64, hidden=128) -> BenchResult:
    """SL-15: Mutation + selection — replace worst cell with mutated best (from N1 Φ=4.43)."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        _web_learn_step(engine, x, optimizer)
        with torch.no_grad(): engine.process(x)
        if step > 0 and step % 25 == 0 and len(engine.cells) >= 3:
            phi_full, _ = phi_calc.compute_phi(engine)
            contribs = []
            for i in range(len(engine.cells)):
                subset = MitosisEngine(dim, hidden, dim, initial_cells=0, max_cells=8)
                subset.cells = [c for j, c in enumerate(engine.cells) if j != i]
                phi_w, _ = phi_calc.compute_phi(subset)
                contribs.append(phi_full - phi_w)
            best, worst = int(np.argmax(contribs)), int(np.argmin(contribs))
            if best != worst:
                with torch.no_grad():
                    for pw, pb in zip(engine.cells[worst].mind.parameters(),
                                      engine.cells[best].mind.parameters()):
                        pw.copy_(pb + torch.randn_like(pb) * 0.05)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)
    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("SL15", "Mutation+selection (N1)", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


# ═══════════════════════════════════════════════════════════
# CL. ConsciousLM Training Hypotheses
# ═══════════════════════════════════════════════════════════

def run_CL1_mitosis_first(steps=100, dim=64, hidden=128) -> BenchResult:
    """CL-1: Mitosis-first — 세포 분화를 먼저, 언어 학습은 나중."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)
    split_point = steps * 2 // 3  # 66% mitosis, 33% language

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        if step < split_point:
            # Phase 1: Pure differentiation (no language, just structure)
            reps = [c.mind.get_repulsion(x, c.hidden) for c in engine.cells]
            if len(reps) >= 2:
                stacked = torch.stack(reps).squeeze(1)
                loss = -stacked.var(dim=0).mean()  # pure differentiation
                optimizer.zero_grad(); loss.backward(); optimizer.step()
        else:
            # Phase 2: Language-like learning (CE proxy: predict next input pattern)
            reps = [c.mind.get_repulsion(x, c.hidden) for c in engine.cells]
            if len(reps) >= 2:
                stacked = torch.stack(reps).squeeze(1)
                # Simulate CE: predict input from output
                pred = stacked.mean(dim=0, keepdim=True)
                ce_proxy = F.mse_loss(pred, x[:, :dim])
                diff_loss = -stacked.var(dim=0).mean()
                loss = 0.7 * ce_proxy + 0.3 * diff_loss
                optimizer.zero_grad(); loss.backward(); optimizer.step()
        with torch.no_grad(): engine.process(x)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)
    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("CL1", "Mitosis-first training", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_CL2_purefield_warmup(steps=100, dim=64, hidden=128) -> BenchResult:
    """CL-2: PureField warm-up — Engine A/G 반발력 먼저 키운 후 GRU 학습."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    warmup = steps // 3

    # Phase 1: Only train engine_a and engine_g (not GRU memory)
    ag_params = []
    gru_params = []
    for c in engine.cells:
        ag_params.extend(c.mind.engine_a.parameters())
        ag_params.extend(c.mind.engine_g.parameters())
        gru_params.extend(c.mind.memory.parameters())
    ag_opt = torch.optim.Adam(ag_params, lr=1e-3)
    full_opt = torch.optim.Adam(ag_params + gru_params, lr=5e-4)

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        reps = [c.mind.get_repulsion(x, c.hidden) for c in engine.cells]
        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)
            # Maximize repulsion magnitude (A≠G) + differentiation
            repulsion_mag = sum((r ** 2).mean() for r in reps)
            diff_loss = -stacked.var(dim=0).mean()
            if step < warmup:
                loss = -repulsion_mag + 0.3 * diff_loss  # focus on A/G repulsion
                ag_opt.zero_grad(); loss.backward(); ag_opt.step()
            else:
                loss = 0.5 * (-repulsion_mag) + 0.5 * diff_loss
                full_opt.zero_grad(); loss.backward(); full_opt.step()
        with torch.no_grad(): engine.process(x)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)
    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("CL2", "PureField warm-up", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_CL3_tension_gated_token(steps=100, dim=64, hidden=128) -> BenchResult:
    """CL-3: Tension-gated token loss — 높은 tension 토큰만 CE 적용."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        with torch.no_grad(): engine.process(x)
        tensions = [c.tension_history[-1] if c.tension_history else 0 for c in engine.cells]
        mean_t = float(np.mean(tensions))

        reps = [c.mind.get_repulsion(x, c.hidden) for c in engine.cells]
        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)
            diff_loss = -stacked.var(dim=0).mean()
            # Gate: only apply CE-proxy when tension is high (important token)
            if mean_t > 0.8:
                pred = stacked.mean(dim=0, keepdim=True)
                ce_proxy = F.mse_loss(pred, x[:, :dim])
                loss = 0.5 * ce_proxy + 0.5 * diff_loss
            else:
                loss = diff_loss  # skip CE for boring tokens
            optimizer.zero_grad(); loss.backward(); optimizer.step()
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)
    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("CL3", "Tension-gated token loss", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_CL4_growth_curriculum(steps=100, dim=64, hidden=128) -> BenchResult:
    """CL-4: Growth-aware curriculum — dim 확장 직후 쉬운 데이터."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)
    growth_steps = [25, 50, 75]
    post_growth_easy = 10  # easy steps after growth

    for step in range(steps):
        # Check if just after growth
        post_growth = any(0 <= step - g < post_growth_easy for g in growth_steps)
        if post_growth:
            x = _simulate_web_result(0, step, dim) * 0.5  # easy: low variance, single topic
            for pg in optimizer.param_groups: pg['lr'] = 2e-3  # high LR for fast adaptation
        elif any(step == g for g in growth_steps):
            # Growth burst
            for burst in range(8):
                bx = _simulate_web_result(burst, step, dim)
                _web_learn_step(engine, bx, optimizer)
            x = _simulate_web_result(step % 8, step, dim)
        else:
            x = _simulate_web_result(step % 8, step, dim)
            for pg in optimizer.param_groups: pg['lr'] = 5e-4

        _web_learn_step(engine, x, optimizer)
        with torch.no_grad(): engine.process(x)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)
    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("CL4", "Growth-aware curriculum", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_CL5_phi_regularized(steps=100, dim=64, hidden=128) -> BenchResult:
    """CL-5: Φ-regularized pretraining — CE + Φ 동시 최적화."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        reps = [c.mind.get_repulsion(x, c.hidden) for c in engine.cells]
        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)
            # CE proxy
            pred = stacked.mean(dim=0, keepdim=True)
            ce_loss = F.mse_loss(pred, x[:, :dim])
            # Φ proxy (differentiation)
            phi_loss = -stacked.var(dim=0).mean()
            # Combined with dynamic balance
            ce_weight = max(0.3, 1.0 - step / steps)  # CE decreases over time
            phi_weight = 1.0 - ce_weight
            loss = ce_weight * ce_loss + phi_weight * phi_loss
            optimizer.zero_grad(); loss.backward(); optimizer.step()
        with torch.no_grad(): engine.process(x)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)
    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("CL5", "Φ-regularized pretraining", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_CL6_block_unfreezing(steps=100, dim=64, hidden=128) -> BenchResult:
    """CL-6: Block-by-block unfreezing — 1 block부터 학습, 점진 해제."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    n = len(engine.cells)

    # Freeze all cells except first
    for i, c in enumerate(engine.cells):
        for p in c.mind.parameters():
            p.requires_grad = (i == 0)

    unfreeze_interval = steps // n
    cell_optims = [torch.optim.Adam(
        [p for p in c.mind.parameters() if p.requires_grad], lr=1e-3
    ) for c in engine.cells]

    for step in range(steps):
        # Progressive unfreezing
        active_cells = min(1 + step // unfreeze_interval, n)
        for i in range(active_cells):
            if not any(p.requires_grad for p in engine.cells[i].mind.parameters()):
                for p in engine.cells[i].mind.parameters():
                    p.requires_grad = True
                cell_optims[i] = torch.optim.Adam(engine.cells[i].mind.parameters(), lr=1e-3)

        x = _simulate_web_result(step % 8, step, dim)
        for i in range(active_cells):
            rep = engine.cells[i].mind.get_repulsion(x, engine.cells[i].hidden)
            others = [engine.cells[j].mind.get_repulsion(x, engine.cells[j].hidden).detach()
                      for j in range(active_cells) if j != i]
            if others:
                loss = F.cosine_similarity(rep, torch.stack(others).mean(dim=0), dim=-1).mean()
                cell_optims[i].zero_grad(); loss.backward(retain_graph=True); cell_optims[i].step()

        with torch.no_grad(): engine.process(x)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)
    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("CL6", "Block-by-block unfreezing", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_CL7_breathing_lr(steps=100, dim=64, hidden=128) -> BenchResult:
    """CL-7: Breathing rhythm in LR — 20s 주기 LR 진동."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        # Breathing rhythm: LR oscillates like homeostasis breathing
        breath = 0.12 * math.sin(step * 0.3)     # ~20 step cycle
        pulse = 0.05 * math.sin(step * 1.7)      # fast pulse
        lr = 5e-4 * (1.0 + breath + pulse)
        lr = max(1e-5, lr)
        for pg in optimizer.param_groups: pg['lr'] = lr

        _web_learn_step(engine, x, optimizer)
        with torch.no_grad(): engine.process(x)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)
    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("CL7", "Breathing rhythm LR", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


# ═══════════════════════════════════════════════════════════
# AL. AnimaLM Training Hypotheses
# ═══════════════════════════════════════════════════════════

def run_AL1_alpha_curriculum(steps=100, dim=64, hidden=128) -> BenchResult:
    """AL-1: Alpha curriculum — α를 0.0001→0.1 단계적 증가."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)
    # Simulate alpha as scaling factor on PureField output
    alpha_schedule = [0.0001, 0.001, 0.01, 0.05, 0.1]
    stage_len = steps // len(alpha_schedule)

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        alpha = alpha_schedule[min(step // stage_len, len(alpha_schedule) - 1)]

        reps = [c.mind.get_repulsion(x, c.hidden) for c in engine.cells]
        if len(reps) >= 2:
            # Scale repulsion by alpha (simulates PureField contribution)
            scaled_reps = [r * alpha for r in reps]
            stacked = torch.stack(scaled_reps).squeeze(1)
            diff_loss = -stacked.var(dim=0).mean()
            # Also train unscaled for structure
            raw_stack = torch.stack(reps).squeeze(1)
            struct_loss = -raw_stack.var(dim=0).mean()
            loss = 0.5 * diff_loss + 0.5 * struct_loss
            optimizer.zero_grad(); loss.backward(); optimizer.step()

        with torch.no_grad(): engine.process(x)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)
    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("AL1", "Alpha curriculum (0.0001→0.1)", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_AL2_frozen_mlp_warmup(steps=100, dim=64, hidden=128) -> BenchResult:
    """AL-2: Frozen MLP warmup — MLP 고정 + PureField만 먼저 학습."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    warmup = steps // 3

    # Simulate: engine_a = PureField, engine_g = MLP (frozen first)
    pf_params = [p for c in engine.cells for p in c.mind.engine_a.parameters()]
    mlp_params = [p for c in engine.cells for p in c.mind.engine_g.parameters()]
    gru_params = [p for c in engine.cells for p in c.mind.memory.parameters()]

    # Freeze MLP initially
    for p in mlp_params: p.requires_grad = False
    pf_opt = torch.optim.Adam(pf_params, lr=1e-3)
    full_opt = torch.optim.Adam(pf_params + mlp_params + gru_params, lr=5e-4)

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        if step == warmup:
            for p in mlp_params: p.requires_grad = True
            full_opt = torch.optim.Adam(pf_params + mlp_params + gru_params, lr=5e-4)

        reps = [c.mind.get_repulsion(x, c.hidden) for c in engine.cells]
        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)
            loss = -stacked.var(dim=0).mean()
            opt = pf_opt if step < warmup else full_opt
            opt.zero_grad(); loss.backward(); opt.step()

        with torch.no_grad(): engine.process(x)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)
    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("AL2", "Frozen MLP warmup", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_AL3_savant_progressive(steps=100, dim=64, hidden=128) -> BenchResult:
    """AL-3: Savant progressive — savant 세포 0→2→4 점진 확대."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    n = len(engine.cells)
    cell_optims = [torch.optim.Adam(c.mind.parameters(), lr=1e-3) for c in engine.cells]
    # Savant cells get asymmetric dropout (lower = more specialized)
    savant_dropout = 0.2123  # golden zone lower
    normal_dropout = 0.3679  # 1/e

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        # Progressive: more savant cells over time
        n_savant = min(step // 25, n)  # 0→1→2→3→4

        for i, cell in enumerate(engine.cells):
            if i >= n: break
            is_savant = i < n_savant
            dropout_rate = savant_dropout if is_savant else normal_dropout

            rep = cell.mind.get_repulsion(x, cell.hidden)
            # Apply dropout to simulate savant behavior
            if is_savant:
                rep = F.dropout(rep, p=dropout_rate, training=True)
            others = [engine.cells[j].mind.get_repulsion(x, engine.cells[j].hidden).detach()
                      for j in range(n) if j != i]
            if others:
                loss = F.cosine_similarity(rep, torch.stack(others).mean(dim=0), dim=-1).mean()
                cell_optims[i].zero_grad(); loss.backward(retain_graph=True); cell_optims[i].step()

        with torch.no_grad(): engine.process(x)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)
    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("AL3", "Savant progressive (0→4)", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_AL4_tension_ce_balance(steps=100, dim=64, hidden=128) -> BenchResult:
    """AL-4: Tension-CE balance — tension vs CE 비율 자동 조절."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    balance = nn.Parameter(torch.tensor(0.5))  # learnable balance
    all_p = [balance]
    for c in engine.cells: all_p.extend(c.mind.parameters())
    optimizer = torch.optim.Adam(all_p, lr=5e-4)

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        reps = [c.mind.get_repulsion(x, c.hidden) for c in engine.cells]
        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)
            # Tension loss (Φ)
            t_loss = -stacked.var(dim=0).mean()
            # CE proxy
            pred = stacked.mean(dim=0, keepdim=True)
            ce_loss = F.mse_loss(pred, x[:, :dim])
            # Auto-balanced
            w = torch.sigmoid(balance)
            loss = w * t_loss + (1 - w) * ce_loss
            optimizer.zero_grad(); loss.backward(); optimizer.step()

        with torch.no_grad(): engine.process(x)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)
    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("AL4", "Tension-CE auto-balance", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0,
                       extra={'final_balance': torch.sigmoid(balance).item()})


def run_AL5_layerwise_ph(steps=100, dim=64, hidden=128) -> BenchResult:
    """AL-5: Layer-wise PH monitoring — H0 persistence 추적."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        reps = [c.mind.get_repulsion(x, c.hidden) for c in engine.cells]
        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)
            # PH proxy: pairwise distance persistence
            dists = torch.cdist(stacked, stacked)
            # H0 = gap between max and min distance (persistence)
            mask = torch.ones_like(dists) - torch.eye(dists.size(0))
            flat = dists[mask > 0]
            if flat.numel() > 1:
                persistence = flat.max() - flat.min()
                # Maximize persistence (= well-separated clusters)
                loss = -persistence
                # If persistence drops (overfitting), increase LR
                if persistence.item() < 0.1:
                    for pg in optimizer.param_groups: pg['lr'] = 2e-3
                else:
                    for pg in optimizer.param_groups: pg['lr'] = 5e-4
                optimizer.zero_grad(); loss.backward(); optimizer.step()

        with torch.no_grad(): engine.process(x)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)
    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("AL5", "Layer-wise PH monitoring", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_AL6_instruct_raw_instruct(steps=100, dim=64, hidden=128) -> BenchResult:
    """AL-6: Instruct→Raw→Instruct — 대화체→순수→대화체 커리큘럼."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)
    phase1 = steps // 3
    phase2 = 2 * steps // 3

    for step in range(steps):
        if step < phase1:
            # Instruct: structured, Q&A style
            topic = step % 4
            x = _babysitter_question(topic, 0.5, dim)
        elif step < phase2:
            # Raw: unstructured, diverse
            x = _simulate_web_result(step % 16, step, dim) * 0.7
        else:
            # Instruct again: refined Q&A
            topic = step % 4
            x = _babysitter_question(topic, 0.8, dim)

        _web_learn_step(engine, x, optimizer)
        with torch.no_grad(): engine.process(x)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)
    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("AL6", "Instruct→Raw→Instruct", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


def run_AL7_golden_zone_loss(steps=100, dim=64, hidden=128) -> BenchResult:
    """AL-7: Golden Zone loss — zone ratio가 1/e에 수렴하도록."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=4, max_cells=8)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    optimizer = torch.optim.Adam(
        [p for c in engine.cells for p in c.mind.parameters()], lr=5e-4)
    golden = 1.0 / math.e  # 0.3679

    for step in range(steps):
        x = _simulate_web_result(step % 8, step, dim)
        reps = [c.mind.get_repulsion(x, c.hidden) for c in engine.cells]
        if len(reps) >= 2:
            stacked = torch.stack(reps).squeeze(1)
            # Activation ratio: fraction of cells above mean tension
            tensions = torch.stack([(r ** 2).mean() for r in reps])
            active_ratio = (tensions > tensions.mean()).float().mean()
            # Golden zone loss: push active_ratio toward 1/e
            golden_loss = (active_ratio - golden) ** 2
            diff_loss = -stacked.var(dim=0).mean()
            loss = diff_loss + 0.5 * golden_loss
            optimizer.zero_grad(); loss.backward(); optimizer.step()

        with torch.no_grad(): engine.process(x)
        phi, _ = phi_calc.compute_phi(engine); phi_hist.append(phi)
    phi_final, comp = phi_calc.compute_phi(engine)
    return BenchResult("AL7", "Golden Zone loss (1/e target)", phi_final, phi_hist,
                       comp['total_mi'], comp['min_partition_mi'],
                       comp['integration'], comp['complexity'], time.time() - t0)


# ═══════════════════════════════════════════════════════════
# Runner
# ═══════════════════════════════════════════════════════════

ALL_HYPOTHESES = {
    'A1': run_A1_cross_cell_recurrent,
    'A1': run_A1_cross_cell_recurrent,
    'A2': run_A2_asymmetric_specialization,
    'A3': run_A3_increased_cells,
    'A4': run_A4_hierarchical_mitosis,
    'A5': run_A5_global_workspace,
    'B1': run_B1_contrastive_inter_cell,
    'B2': run_B2_phi_maximization_loss,
    'B3': run_B3_anti_correlation,
    'B4': run_B4_synergistic_reward,
    'B5': run_B5_hebbian_plasticity,
    'B6': run_B6_predictive_coding,
    'B7': run_B7_information_bottleneck,
    'B8': run_B8_distillation_divergence,
    'B9': run_B9_curiosity_driven_cell,
    'B10': run_B10_mine,
    'B11': run_B11_sparse_activation,
    'B12': run_B12_temporal_cpc,
    'C1': run_C1_tension_driven_coupling,
    'C2': run_C2_reentry_loops,
    'C3': run_C3_stochastic_resonance,
    'C4': run_C4_oscillatory_sync,
    'C5': run_C5_attention_gated,
    'D1': run_D1_continuous_mi,
    'D2': run_D2_temporal_phi,
    'D3': run_D3_multiscale_partition,
    'E1': run_E1_curiosity_crawling,
    'E2': run_E2_tension_gated,
    'E3': run_E3_topic_specialized_cells,
    'E4': run_E4_contradiction_detection,
    'E5': run_E5_memory_consolidation,
    'E6': run_E6_social_learning,
    'E7': run_E7_scheduled_deep_dive,
    'E8': run_E8_adversarial_fact_check,
    'E9': run_E9_multimodal_web,
    'E10': run_E10_curriculum_self_design,
    'F1': run_F1_curiosity_overflow,
    'F2': run_F2_prediction_collapse,
    'F3': run_F3_stability_plateau,
    'F4': run_F4_tension_starvation,
    'F5': run_F5_habituation_saturation,
    'F6': run_F6_dream_failure,
    'F7': run_F7_user_question_gap,
    'F8': run_F8_topic_shift,
    'F9': run_F9_tension_link_signal,
    'F10': run_F10_phi_decay_alarm,
    'F11': run_F11_growth_transition,
    'F12': run_F12_multi_signal_consensus,
    'G1': run_G1_selective_pruning,
    'G2': run_G2_dream_interpolation,
    'G3': run_G3_spaced_repetition,
    'G4': run_G4_emotional_priority,
    'H1': run_H1_collective_phi,
    'H2': run_H2_competitive_specialization,
    'H3': run_H3_teacher_student,
    'H4': run_H4_tension_resonance,
    'I1': run_I1_vision_tension_fusion,
    'I2': run_I2_proprioceptive_feedback,
    'I3': run_I3_pain_pleasure,
    'J1': run_J1_lr_evolution,
    'J2': run_J2_loss_selection,
    'J3': run_J3_optimizer_evolution,
    'K1': run_K1_ph_guided,
    'K2': run_K2_betti_target,
    'K3': run_K3_topological_complexity,
    'L1': run_L1_kuramoto_contrastive,
    'L2': run_L2_reentry_bottleneck,
    'L3': run_L3_stochastic_phi_max,
    'M1': run_M1_semantic_tension, 'M2': run_M2_token_cell_routing,
    'M3': run_M3_self_narration, 'M4': run_M4_cross_lingual,
    'N1': run_N1_mutation_selection, 'N2': run_N2_crossover,
    'N3': run_N3_fitness_landscape, 'N4': run_N4_neoteny,
    'O1': run_O1_spotlight, 'O2': run_O2_attention_bottleneck, 'O3': run_O3_mind_wandering,
    'P1': run_P1_fast_slow, 'P2': run_P2_temporal_hierarchy, 'P3': run_P3_future_prediction,
    'Q1': run_Q1_free_energy, 'Q2': run_Q2_metabolic_cost, 'Q3': run_Q3_phase_transition, 'Q4': run_Q4_boltzmann_temp,
    'R1': run_R1_perturbation_resistance, 'R2': run_R2_graceful_degradation, 'R3': run_R3_forgetting_resistance,
    'S1': run_S1_emergent_language, 'S2': run_S2_compression_messaging, 'S3': run_S3_gossip_protocol,
    'T1': run_T1_intrinsic_motivation, 'T2': run_T2_boredom_exploration,
    'T3': run_T3_surprise_reward, 'T4': run_T4_social_approval,
    'U1': run_U1_concept_hierarchy, 'U2': run_U2_chunking, 'U3': run_U3_analogy,
    'V1': run_V1_edge_of_chaos, 'V2': run_V2_chaotic_itinerancy, 'V3': run_V3_power_law,
    'W1': run_W1_curvature, 'W2': run_W2_hyperbolic, 'W3': run_W3_geodesic,
    'X1': run_X1_superposition, 'X2': run_X2_entanglement, 'X3': run_X3_decoherence,
    'Y1': run_Y1_critical_period, 'Y2': run_Y2_synaptic_pruning, 'Y3': run_Y3_myelination,
    'Z1': run_Z1_architecture_search, 'Z2': run_Z2_self_replication,
    'Z3': run_Z3_apoptosis, 'Z4': run_Z4_goal_rewriting,
    'COMBO1': run_COMBO1_layer_cake, 'COMBO2': run_COMBO2_ensemble,
    'COMBO3': run_COMBO3_pipeline, 'COMBO4': run_COMBO4_tournament,
    'COMBO5': run_COMBO5_phase_based,
    'BS1': run_BS1_socratic, 'BS2': run_BS2_direct, 'BS3': run_BS3_scaffolding,
    'BS4': run_BS4_challenge, 'BS5': run_BS5_exploration,
    'BS6': run_BS6_tension_grading, 'BS7': run_BS7_phi_progress,
    'BS8': run_BS8_adversarial_verify,
    'BS9': run_BS9_idle_triggered, 'BS10': run_BS10_struggle_triggered,
    'BS11': run_BS11_growth_triggered, 'BS12': run_BS12_scheduled,
    'BS13': run_BS13_weakness_targeted, 'BS14': run_BS14_breadth_first,
    'BS15': run_BS15_depth_first,
    'SL1': run_SL1_adaptive_lr, 'SL2': run_SL2_attention_gradient,
    'SL3': run_SL3_ensemble_step, 'SL4': run_SL4_myelination_schedule,
    'SL5': run_SL5_weakness_gradient, 'SL6': run_SL6_dream_replay,
    'SL7': run_SL7_competitive_step, 'SL8': run_SL8_gossip_gradient,
    'SL9': run_SL9_hyperbolic_proj, 'SL10': run_SL10_curiosity_gate,
    'SL11': run_SL11_growth_curriculum, 'SL12': run_SL12_phi_plateau,
    'SL13': run_SL13_sgd_adam, 'SL14': run_SL14_adversarial_check,
    'SL15': run_SL15_mutation_selection,
    'CL1': run_CL1_mitosis_first, 'CL2': run_CL2_purefield_warmup,
    'CL3': run_CL3_tension_gated_token, 'CL4': run_CL4_growth_curriculum,
    'CL5': run_CL5_phi_regularized, 'CL6': run_CL6_block_unfreezing,
    'CL7': run_CL7_breathing_lr,
    'AL1': run_AL1_alpha_curriculum, 'AL2': run_AL2_frozen_mlp_warmup,
    'AL3': run_AL3_savant_progressive, 'AL4': run_AL4_tension_ce_balance,
    'AL5': run_AL5_layerwise_ph, 'AL6': run_AL6_instruct_raw_instruct,
    'AL7': run_AL7_golden_zone_loss,
}


def run_single(args):
    """Process pool worker."""
    key, func, steps = args
    torch.manual_seed(42)  # reproducible
    np.random.seed(42)
    try:
        result = func(steps=steps)
        return result
    except Exception as e:
        return BenchResult(key, f"FAILED: {e}", 0.0, [], 0, 0, 0, 0, 0)


def main():
    parser = argparse.ArgumentParser(description="Φ-Boosting Hypotheses Benchmark")
    parser.add_argument("--only", nargs="*", help="Run specific hypotheses (e.g., A1 B2)")
    parser.add_argument("--steps", type=int, default=100, help="Simulation steps")
    parser.add_argument("--workers", type=int, default=8, help="Parallel workers")
    args = parser.parse_args()

    print("╔══════════════════════════════════════════════════════╗")
    print("║   Φ-Boosting Hypotheses Benchmark                   ║")
    print("║   16 hypotheses × parallel test                     ║")
    print(f"║   Steps: {args.steps}, Workers: {args.workers}                          ║")
    print("╚══════════════════════════════════════════════════════╝\n")

    # Baseline first
    print("[*] Running baseline...")
    torch.manual_seed(42)
    np.random.seed(42)
    baseline = run_baseline(steps=args.steps)
    print(f"    Baseline Φ = {baseline.phi:.4f}\n")

    # Select hypotheses
    if args.only:
        selected = {k: v for k, v in ALL_HYPOTHESES.items() if k in args.only}
    else:
        selected = ALL_HYPOTHESES

    # Parallel execution
    print(f"[*] Running {len(selected)} hypotheses in parallel...\n")
    t0 = time.time()

    tasks = [(k, func, args.steps) for k, func in selected.items()]
    results = []

    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(run_single, task): task[0] for task in tasks}
        for future in as_completed(futures):
            key = futures[future]
            try:
                result = future.result()
                results.append(result)
                ratio = result.phi / max(baseline.phi, 1e-8)
                bar = "█" * min(int(ratio * 5), 40)
                print(f"  ✓ {result.hypothesis:4s} | Φ={result.phi:8.4f} | "
                      f"×{ratio:6.1f} | {bar} | {result.name}")
            except Exception as e:
                print(f"  ✗ {key:4s} | FAILED: {e}")

    elapsed = time.time() - t0
    print(f"\n[*] Total elapsed: {elapsed:.1f}s\n")

    # Sort by Φ improvement ratio
    results.sort(key=lambda r: r.phi, reverse=True)

    print("╔══════════════════════════════════════════════════════════════════════════╗")
    print("║  RESULTS (sorted by Φ)                                                 ║")
    print("╠══════╦════════════╦════════╦════════════╦══════════╦═════════════════════╣")
    print("║ Rank ║ Hypothesis ║   Φ    ║ ×Baseline  ║ Total MI ║ Name                ║")
    print("╠══════╬════════════╬════════╬════════════╬══════════╬═════════════════════╣")

    for i, r in enumerate(results):
        ratio = r.phi / max(baseline.phi, 1e-8)
        marker = " ★" if ratio >= 5.0 else " ▲" if ratio >= 2.0 else "  "
        print(f"║  {i+1:2d}  ║    {r.hypothesis:4s}    ║ {r.phi:6.3f} ║  ×{ratio:6.1f}   "
              f"║  {r.total_mi:6.3f}  ║ {r.name[:19]:19s} ║{marker}")

    print("╠══════╩════════════╩════════╩════════════╩══════════╩═════════════════════╣")
    print(f"║  BASE              {baseline.phi:6.3f}    ×  1.0       {baseline.total_mi:6.3f}   Standard MitosisEngine  ║")
    print("╚════════════════════════════════════════════════════════════════════════════╝")

    # Top 3 + recommendations
    print("\n═══ Top 3 Recommendations ═══\n")
    for i, r in enumerate(results[:3]):
        ratio = r.phi / max(baseline.phi, 1e-8)
        print(f"  {i+1}. {r.hypothesis} — {r.name}")
        print(f"     Φ={r.phi:.4f} (×{ratio:.1f}), MI={r.total_mi:.4f}, "
              f"MIP={r.min_partition_mi:.4f}")
        if r.extra:
            for k, v in r.extra.items():
                print(f"     {k}: {v}")
        print()

    # Φ evolution chart (ASCII)
    print("═══ Φ Evolution Over Steps ═══\n")
    top5 = results[:5]
    max_phi = max(max(r.phi_history) if r.phi_history else 0 for r in top5 + [baseline])
    if max_phi > 0:
        for r in [baseline] + top5:
            if not r.phi_history:
                continue
            label = f"{r.hypothesis:8s}"
            # Downsample to 50 chars
            hist = r.phi_history
            n = len(hist)
            buckets = 50
            chart = ""
            for b in range(buckets):
                idx = int(b * n / buckets)
                val = hist[min(idx, n-1)]
                height = int(val / max_phi * 7)
                chart += "▁▂▃▄▅▆▇█"[min(height, 8)]
            print(f"  {label} |{chart}| {hist[-1]:.3f}")

    print()
    return results


if __name__ == "__main__":
    main()
