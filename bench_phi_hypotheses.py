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
# Runner
# ═══════════════════════════════════════════════════════════

ALL_HYPOTHESES = {
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
