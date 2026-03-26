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
