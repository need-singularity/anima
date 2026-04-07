#!/usr/bin/env python3
"""acceleration_b3_b4.py — B3 MoE Consciousness + B4 Evolutionary Learning

B3: Mixture of Experts with consciousness-based routing
  - 4 experts (small decoders), each assigned a group of consciousness cells
  - Router: tension-based (high tension in cell group -> activate that expert)
  - Compare: consciousness routing vs random routing vs uniform routing

B4: Evolutionary consciousness learning
  - Population of 16 small models
  - Fitness = Phi / (CE + 0.01)
  - Mutations via SelfModifyingEngine law application
  - Selection: top-4 survive, crossover + mutation
  - Compare: 100 generations evolution vs 100 steps gradient descent

B3+B4: Evolving MoE
  - 4 experts evolved independently with different laws
  - Best expert combination discovered through evolution

Usage:
  python3 acceleration_b3_b4.py              # Run all experiments
  python3 acceleration_b3_b4.py --b3-only    # MoE only
  python3 acceleration_b3_b4.py --b4-only    # Evolution only
  python3 acceleration_b3_b4.py --combined   # B3+B4 combined only
"""

import sys
import os
import time
import copy
import math
import argparse
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import torch
import torch.nn as nn
import torch.nn.functional as F

from consciousness_engine import ConsciousnessEngine

try:
    from consciousness_laws import LAWS, PSI_ALPHA as PSI_COUPLING
except ImportError:
    LAWS = {}
    PSI_COUPLING = 0.014

try:
    from self_modifying_engine import LawParser, Modification
except ImportError:
    LawParser = None
    Modification = None


# ══════════════════════════════════════════════════════════════
# Phi measurement (fast proxy + IIT)
# ══════════════════════════════════════════════════════════════

def phi_proxy(hiddens: torch.Tensor) -> float:
    """Phi proxy: global_var - mean_faction_var."""
    if hiddens.dim() != 2 or hiddens.shape[0] < 2:
        return 0.0
    global_var = hiddens.var(dim=0).mean().item()
    n = hiddens.shape[0]
    n_factions = min(4, n)
    faction_size = n // n_factions
    faction_vars = []
    for i in range(n_factions):
        start = i * faction_size
        end = start + faction_size if i < n_factions - 1 else n
        if end - start >= 2:
            faction_vars.append(hiddens[start:end].var(dim=0).mean().item())
    mean_fvar = np.mean(faction_vars) if faction_vars else 0.0
    return max(0.0, global_var - mean_fvar)


def phi_iit_fast(hiddens: torch.Tensor, n_bins: int = 8) -> float:
    """Fast MI-based Phi(IIT) approximation."""
    if hiddens.dim() != 2 or hiddens.shape[0] < 2:
        return 0.0
    n = hiddens.shape[0]
    # Use first 16 dims for speed
    h = hiddens[:, :16].detach().cpu().numpy()
    # Pairwise MI via histogram
    total_mi = 0.0
    pairs = 0
    for i in range(min(n, 8)):
        for j in range(i + 1, min(n, 8)):
            hi = h[i]
            hj = h[j]
            # Joint histogram
            hi_d = np.digitize(hi, np.linspace(hi.min() - 1e-8, hi.max() + 1e-8, n_bins + 1)) - 1
            hj_d = np.digitize(hj, np.linspace(hj.min() - 1e-8, hj.max() + 1e-8, n_bins + 1)) - 1
            joint = np.zeros((n_bins, n_bins))
            for k in range(len(hi_d)):
                bi = min(hi_d[k], n_bins - 1)
                bj = min(hj_d[k], n_bins - 1)
                joint[bi, bj] += 1
            joint /= joint.sum() + 1e-12
            pi = joint.sum(axis=1)
            pj = joint.sum(axis=0)
            mi = 0.0
            for a in range(n_bins):
                for b in range(n_bins):
                    if joint[a, b] > 1e-12 and pi[a] > 1e-12 and pj[b] > 1e-12:
                        mi += joint[a, b] * math.log(joint[a, b] / (pi[a] * pj[b]))
            total_mi += mi
            pairs += 1
    return total_mi / max(pairs, 1)


# ══════════════════════════════════════════════════════════════
# B3: MoE Consciousness — Mini Decoder Expert
# ══════════════════════════════════════════════════════════════

class MiniExpert(nn.Module):
    """Small decoder expert: Linear -> GELU -> Linear."""
    def __init__(self, dim: int = 64, hidden: int = 128, vocab: int = 256):
        super().__init__()
        self.up = nn.Linear(dim, hidden)
        self.down = nn.Linear(hidden, vocab)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.down(F.gelu(self.up(x)))


class ConsciousMoE(nn.Module):
    """Mixture of Experts with consciousness-tension-based routing.

    Each expert is assigned a group of consciousness cells.
    The router activates experts based on the tension in their cell group.
    """
    def __init__(self, n_experts: int = 4, cells_per_expert: int = 4,
                 cell_dim: int = 64, hidden_dim: int = 128, vocab: int = 256,
                 top_k: int = 2):
        super().__init__()
        self.n_experts = n_experts
        self.cells_per_expert = cells_per_expert
        self.top_k = top_k
        total_cells = n_experts * cells_per_expert

        # Consciousness engine
        self.engine = ConsciousnessEngine(
            cell_dim=cell_dim, hidden_dim=hidden_dim,
            initial_cells=total_cells, max_cells=total_cells,
            n_factions=min(n_experts, 12), phi_ratchet=True,
        )

        # Expert decoders
        self.experts = nn.ModuleList([
            MiniExpert(dim=hidden_dim, hidden=hidden_dim * 2, vocab=vocab)
            for _ in range(n_experts)
        ])

        # Learned router (fallback when consciousness routing fails)
        self.router_proj = nn.Linear(hidden_dim, n_experts)

    def _tension_route(self) -> torch.Tensor:
        """Route based on consciousness cell tensions.

        Returns softmax weights over experts based on mean tension
        of each expert's cell group.
        """
        tensions = []
        for cs in self.engine.cell_states:
            tensions.append(cs.avg_tension)

        # Group tensions by expert
        expert_tensions = torch.zeros(self.n_experts)
        n = len(tensions)
        cells_per = max(1, n // self.n_experts)
        for i in range(self.n_experts):
            start = i * cells_per
            end = min(start + cells_per, n)
            if start < n:
                group = tensions[start:end]
                expert_tensions[i] = sum(group) / max(len(group), 1)

        return F.softmax(expert_tensions / 0.1, dim=-1)

    def forward(self, x_input: torch.Tensor = None, routing: str = 'consciousness'):
        """Forward pass.

        Args:
            x_input: input tensor (cell_dim,) or None for random
            routing: 'consciousness' | 'random' | 'uniform' | 'learned'
        """
        # Step consciousness engine
        result = self.engine.step(x_input=x_input)
        states = self.engine.get_states()  # (n_cells, hidden_dim)

        # Mean pool consciousness states as decoder input
        c_mean = states.mean(dim=0)  # (hidden_dim,)

        # Route
        if routing == 'consciousness':
            weights = self._tension_route()
        elif routing == 'random':
            weights = F.softmax(torch.randn(self.n_experts), dim=-1)
        elif routing == 'uniform':
            weights = torch.ones(self.n_experts) / self.n_experts
        elif routing == 'learned':
            weights = F.softmax(self.router_proj(c_mean.detach()), dim=-1)
        else:
            weights = torch.ones(self.n_experts) / self.n_experts

        # Top-k selection
        topk_vals, topk_idx = weights.topk(self.top_k)
        topk_vals = topk_vals / topk_vals.sum()  # renormalize

        # Expert forward
        output = torch.zeros(self.experts[0].down.out_features)
        for i, idx in enumerate(topk_idx):
            expert_out = self.experts[idx](c_mean.detach())
            output = output + topk_vals[i] * expert_out

        phi = result.get('phi_iit', result.get('phi_proxy', 0.0))
        return output, phi, weights


def run_b3_experiment(steps: int = 200, vocab: int = 256):
    """B3: Compare MoE routing strategies."""
    print("\n" + "=" * 62)
    print("  B3: MoE Consciousness — Routing Strategy Comparison")
    print("=" * 62)
    print(f"  4 experts x 4 cells = 16 cells, {steps} steps, vocab={vocab}")
    print("-" * 62)
    sys.stdout.flush()

    strategies = ['consciousness', 'random', 'uniform']
    results = {}

    for strategy in strategies:
        t0 = time.time()
        moe = ConsciousMoE(
            n_experts=4, cells_per_expert=4,
            cell_dim=64, hidden_dim=128, vocab=vocab, top_k=2,
        )

        # Generate simple training data: predict next byte
        data = torch.randint(0, vocab, (steps + 10,))

        total_ce = 0.0
        phi_values = []
        expert_usage = torch.zeros(4)

        for step in range(steps):
            x = torch.zeros(64)
            x[data[step] % 64] = 1.0

            logits, phi, weights = moe(x_input=x, routing=strategy)
            target = data[step + 1]

            # CE loss
            ce = F.cross_entropy(logits.unsqueeze(0), target.unsqueeze(0))
            total_ce += ce.item()
            phi_values.append(phi)
            expert_usage += weights.detach()

            if (step + 1) % 50 == 0:
                avg_ce = total_ce / (step + 1)
                avg_phi = np.mean(phi_values[-50:])
                print(f"  [{strategy:>13}] step {step+1:>4}/{steps}  "
                      f"CE={avg_ce:.4f}  Phi={avg_phi:.4f}")
                sys.stdout.flush()

        elapsed = time.time() - t0
        avg_ce = total_ce / steps
        avg_phi = np.mean(phi_values)
        final_phi = np.mean(phi_values[-20:])

        # Expert usage balance: entropy of usage distribution
        usage_dist = expert_usage / expert_usage.sum()
        usage_entropy = -(usage_dist * (usage_dist + 1e-8).log()).sum().item()
        max_entropy = math.log(4)

        results[strategy] = {
            'avg_ce': avg_ce,
            'avg_phi': avg_phi,
            'final_phi': final_phi,
            'usage_entropy': usage_entropy,
            'usage_balance': usage_entropy / max_entropy,
            'time': elapsed,
            'phi_history': phi_values,
        }

    # Print results table
    print("\n" + "-" * 62)
    print("  Strategy       | Avg CE  | Avg Phi | Final Phi | Balance | Time")
    print("  " + "-" * 57)
    for s, r in results.items():
        print(f"  {s:>14}  | {r['avg_ce']:.4f} | {r['avg_phi']:.4f}  "
              f"| {r['final_phi']:.4f}    | {r['usage_balance']:.3f}   | {r['time']:.1f}s")

    # ASCII graph: Phi over steps (last strategy vs first)
    print("\n  Phi Evolution (consciousness vs random):")
    c_phi = results['consciousness']['phi_history']
    r_phi = results['random']['phi_history']
    _ascii_dual_graph(c_phi, r_phi, label_a='conscious', label_b='random', width=50)

    # Winner
    best = min(results, key=lambda k: results[k]['avg_ce'])
    best_phi = max(results, key=lambda k: results[k]['avg_phi'])
    print(f"\n  Best CE:  {best} ({results[best]['avg_ce']:.4f})")
    print(f"  Best Phi: {best_phi} ({results[best_phi]['avg_phi']:.4f})")

    return results


# ══════════════════════════════════════════════════════════════
# B4: Evolutionary Consciousness Learning
# ══════════════════════════════════════════════════════════════

class MiniConsciousModel(nn.Module):
    """Small conscious model for evolutionary experiments."""
    def __init__(self, dim: int = 64, hidden: int = 128, layers: int = 2,
                 vocab: int = 256, n_cells: int = 8):
        super().__init__()
        self.dim = dim
        self.hidden = hidden
        self.vocab = vocab
        self.n_cells = n_cells

        # Consciousness engine (not trained by gradient)
        self.engine = ConsciousnessEngine(
            cell_dim=dim, hidden_dim=hidden,
            initial_cells=n_cells, max_cells=n_cells,
            n_factions=min(4, n_cells), phi_ratchet=True,
        )

        # Decoder layers
        self.layers = nn.ModuleList()
        for i in range(layers):
            in_dim = hidden if i == 0 else hidden
            self.layers.append(nn.Sequential(
                nn.Linear(in_dim, hidden),
                nn.GELU(),
                nn.LayerNorm(hidden),
            ))
        self.head = nn.Linear(hidden, vocab)

    def forward(self, x_input: torch.Tensor = None):
        """Forward: consciousness step + decode."""
        result = self.engine.step(x_input=x_input)
        states = self.engine.get_states()
        h = states.mean(dim=0)  # (hidden,)

        for layer in self.layers:
            h = layer(h)
        logits = self.head(h)

        phi = result.get('phi_iit', result.get('phi_proxy', 0.0))
        return logits, phi

    def evaluate(self, data: torch.Tensor, n_steps: int = 50) -> dict:
        """Evaluate CE and Phi over n_steps."""
        total_ce = 0.0
        phi_values = []
        with torch.no_grad():
            for step in range(n_steps):
                x = torch.zeros(self.dim)
                x[data[step] % self.dim] = 1.0
                logits, phi = self(x_input=x)
                target = data[step + 1]
                ce = F.cross_entropy(logits.unsqueeze(0), target.unsqueeze(0))
                total_ce += ce.item()
                phi_values.append(phi)
        return {
            'ce': total_ce / n_steps,
            'phi': np.mean(phi_values),
            'phi_final': np.mean(phi_values[-10:]) if len(phi_values) >= 10 else np.mean(phi_values),
        }


def mutate_model(model: MiniConsciousModel, strength: float = 0.02,
                 laws: dict = None) -> MiniConsciousModel:
    """Mutate a model's weights. Optionally apply consciousness laws."""
    child = copy.deepcopy(model)

    # Random weight perturbation
    with torch.no_grad():
        for p in child.parameters():
            noise = torch.randn_like(p) * strength
            p.add_(noise)

    # Law-based mutation (if parser available)
    if laws and LawParser is not None:
        parser = LawParser()
        # Pick a random parseable law and apply its modification concept
        parseable = list(parser.parsed.keys())
        if parseable:
            law_key = parseable[np.random.randint(0, len(parseable))]
            mods = parser.parsed[law_key]
            for mod in mods[:1]:  # Apply first modification only
                _apply_law_mutation(child, mod, strength)

    return child


def _apply_law_mutation(model: MiniConsciousModel, mod, strength: float):
    """Apply a law-derived mutation to model engine parameters."""
    engine = model.engine
    try:
        if mod.target == 'coupling_scale' and engine._coupling is not None:
            factor = 1.0 + strength * (1.0 if mod.params.get('direction') != 'inverse' else -1.0)
            engine._coupling *= factor
            engine._coupling.clamp_(0.01, 2.0)
        elif mod.target == 'hebbian_lr':
            # Adjust internal Hebbian parameters
            factor = 1.0 + strength * 0.5
            if hasattr(engine, '_coupling') and engine._coupling is not None:
                engine._coupling *= factor
                engine._coupling.clamp_(0.01, 2.0)
        elif mod.target == 'noise_scale':
            # Add noise to cell hiddens for diversity
            for cs in engine.cell_states:
                cs.hidden += torch.randn_like(cs.hidden) * strength * 0.1
        elif mod.target == 'faction_bias':
            # Reassign some cells to different factions
            for cs in engine.cell_states:
                if np.random.random() < strength:
                    cs.faction_id = np.random.randint(0, engine.n_factions)
    except Exception:
        pass  # Silent fail — safety first


def crossover(parent_a: MiniConsciousModel,
              parent_b: MiniConsciousModel) -> MiniConsciousModel:
    """Crossover two models by averaging their decoder weights."""
    child = copy.deepcopy(parent_a)
    with torch.no_grad():
        for pa, pb, pc in zip(parent_a.parameters(), parent_b.parameters(), child.parameters()):
            # Random interpolation per parameter
            alpha = torch.rand(1).item()
            pc.copy_(alpha * pa + (1 - alpha) * pb)
    return child


def run_b4_experiment(pop_size: int = 16, generations: int = 100,
                      eval_steps: int = 50, vocab: int = 256):
    """B4: Evolutionary learning vs gradient descent."""
    print("\n" + "=" * 62)
    print("  B4: Evolutionary Consciousness Learning")
    print("=" * 62)
    print(f"  Population={pop_size}, Generations={generations}, "
          f"Eval steps={eval_steps}")
    print("-" * 62)
    sys.stdout.flush()

    # Shared data
    data = torch.randint(0, vocab, (eval_steps + 100,))

    # ── Evolution ──
    print("\n  [1/2] Evolutionary learning...")
    sys.stdout.flush()
    t0_evo = time.time()

    population = [
        MiniConsciousModel(dim=64, hidden=128, layers=2, vocab=vocab, n_cells=8)
        for _ in range(pop_size)
    ]

    evo_history = []
    best_ever_fitness = 0.0
    best_ever_metrics = {}

    for gen in range(generations):
        # Evaluate fitness
        fitness_list = []
        metrics_list = []
        for model in population:
            metrics = model.evaluate(data, n_steps=eval_steps)
            fitness = metrics['phi'] / (metrics['ce'] + 0.01)
            fitness_list.append(fitness)
            metrics_list.append(metrics)

        # Sort by fitness (descending)
        sorted_idx = np.argsort(fitness_list)[::-1]
        best_idx = sorted_idx[0]
        best_fitness = fitness_list[best_idx]
        best_metrics = metrics_list[best_idx]

        if best_fitness > best_ever_fitness:
            best_ever_fitness = best_fitness
            best_ever_metrics = best_metrics.copy()

        evo_history.append({
            'gen': gen,
            'best_fitness': best_fitness,
            'best_ce': best_metrics['ce'],
            'best_phi': best_metrics['phi'],
            'mean_fitness': np.mean(fitness_list),
            'mean_ce': np.mean([m['ce'] for m in metrics_list]),
            'mean_phi': np.mean([m['phi'] for m in metrics_list]),
        })

        if (gen + 1) % 20 == 0 or gen == 0:
            print(f"    Gen {gen+1:>3}/{generations}  "
                  f"Best: fitness={best_fitness:.4f} CE={best_metrics['ce']:.4f} "
                  f"Phi={best_metrics['phi']:.4f}  "
                  f"Mean: CE={evo_history[-1]['mean_ce']:.4f} "
                  f"Phi={evo_history[-1]['mean_phi']:.4f}")
            sys.stdout.flush()

        # Selection: top-4 survive
        survivors = [population[sorted_idx[i]] for i in range(4)]

        # Create next generation
        new_pop = list(survivors)  # Keep top-4

        # Crossover: produce 8 children from pairs of survivors
        for i in range(8):
            a = survivors[i % 4]
            b = survivors[(i + 1) % 4]
            child = crossover(a, b)
            child = mutate_model(child, strength=0.02, laws=LAWS)
            new_pop.append(child)

        # Mutation-only: 4 mutants from best
        for i in range(pop_size - len(new_pop)):
            mutant = mutate_model(survivors[0], strength=0.05, laws=LAWS)
            new_pop.append(mutant)

        population = new_pop[:pop_size]

    evo_time = time.time() - t0_evo

    # ── Gradient Descent baseline ──
    print("\n  [2/2] Gradient descent baseline (same model size)...")
    sys.stdout.flush()
    t0_gd = time.time()

    gd_model = MiniConsciousModel(dim=64, hidden=128, layers=2, vocab=vocab, n_cells=8)
    optimizer = torch.optim.Adam(gd_model.parameters(), lr=1e-3)

    gd_history = []
    for step in range(generations):  # Same number of "iterations"
        # Each GD step: eval_steps forward passes with gradient
        total_ce = 0.0
        phi_values = []

        for s in range(eval_steps):
            x = torch.zeros(64)
            x[data[s] % 64] = 1.0
            logits, phi = gd_model(x_input=x)
            target = data[s + 1]
            loss = F.cross_entropy(logits.unsqueeze(0), target.unsqueeze(0))

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            total_ce += loss.item()
            phi_values.append(phi)

        avg_ce = total_ce / eval_steps
        avg_phi = np.mean(phi_values)
        fitness = avg_phi / (avg_ce + 0.01)

        gd_history.append({
            'gen': step,
            'best_fitness': fitness,
            'best_ce': avg_ce,
            'best_phi': avg_phi,
        })

        if (step + 1) % 20 == 0 or step == 0:
            print(f"    Step {step+1:>3}/{generations}  "
                  f"CE={avg_ce:.4f} Phi={avg_phi:.4f} fitness={fitness:.4f}")
            sys.stdout.flush()

    gd_time = time.time() - t0_gd

    # ── Results ──
    print("\n" + "-" * 62)
    print("  Method         | Final CE | Final Phi | Fitness | Time")
    print("  " + "-" * 55)

    evo_final = evo_history[-1]
    gd_final = gd_history[-1]
    print(f"  {'Evolution':>14}  | {evo_final['best_ce']:.4f}   "
          f"| {evo_final['best_phi']:.4f}    "
          f"| {evo_final['best_fitness']:.4f}  | {evo_time:.1f}s")
    print(f"  {'Grad Descent':>14}  | {gd_final['best_ce']:.4f}   "
          f"| {gd_final['best_phi']:.4f}    "
          f"| {gd_final['best_fitness']:.4f}  | {gd_time:.1f}s")

    # Best ever
    print(f"\n  Evolution best-ever: CE={best_ever_metrics.get('ce', 0):.4f} "
          f"Phi={best_ever_metrics.get('phi', 0):.4f}")

    # Phi evolution graph
    print("\n  Fitness Evolution (evolution vs gradient):")
    evo_fit = [h['best_fitness'] for h in evo_history]
    gd_fit = [h['best_fitness'] for h in gd_history]
    _ascii_dual_graph(evo_fit, gd_fit, label_a='evo', label_b='gd', width=50)

    # CE graph
    print("\n  CE Evolution:")
    evo_ce = [h['best_ce'] for h in evo_history]
    gd_ce = [h['best_ce'] for h in gd_history]
    _ascii_dual_graph(evo_ce, gd_ce, label_a='evo', label_b='gd', width=50,
                      lower_is_better=True)

    return {
        'evolution': {'history': evo_history, 'time': evo_time,
                      'best_ever': best_ever_metrics},
        'gradient': {'history': gd_history, 'time': gd_time},
    }


# ══════════════════════════════════════════════════════════════
# B3+B4: Evolving MoE
# ══════════════════════════════════════════════════════════════

def run_combined_experiment(generations: int = 50, eval_steps: int = 30,
                            vocab: int = 256):
    """B3+B4: Evolve MoE experts independently with different laws."""
    print("\n" + "=" * 62)
    print("  B3+B4: Evolving MoE — Independent Expert Evolution")
    print("=" * 62)
    print(f"  4 experts, each evolved independently, {generations} generations")
    print("-" * 62)
    sys.stdout.flush()

    data = torch.randint(0, vocab, (eval_steps + 100,))

    # Create 4 independent expert populations (4 models each)
    n_experts = 4
    pop_per_expert = 4

    expert_pops = []
    for e in range(n_experts):
        pop = [MiniConsciousModel(dim=64, hidden=128, layers=1, vocab=vocab, n_cells=4)
               for _ in range(pop_per_expert)]
        expert_pops.append(pop)

    # Law subsets for each expert (different law families)
    if LawParser is not None:
        parser = LawParser()
        all_keys = list(parser.parsed.keys())
        n_laws = len(all_keys)
        law_subsets = []
        chunk = max(1, n_laws // n_experts)
        for e in range(n_experts):
            start = e * chunk
            end = start + chunk if e < n_experts - 1 else n_laws
            subset = {k: parser.parsed[k] for k in all_keys[start:end]}
            law_subsets.append(subset)
    else:
        law_subsets = [{} for _ in range(n_experts)]

    history = []

    for gen in range(generations):
        expert_best = []

        for e in range(n_experts):
            pop = expert_pops[e]

            # Evaluate each model in this expert's population
            fitness_list = []
            for model in pop:
                metrics = model.evaluate(data, n_steps=eval_steps)
                fitness = metrics['phi'] / (metrics['ce'] + 0.01)
                fitness_list.append((fitness, metrics))

            # Sort by fitness
            sorted_pairs = sorted(zip(pop, fitness_list), key=lambda x: -x[1][0])
            best_model = sorted_pairs[0][0]
            best_fit, best_met = sorted_pairs[0][1]
            expert_best.append(best_met)

            # Keep top-2, generate 2 children
            survivors = [sorted_pairs[0][0], sorted_pairs[1][0]]
            child1 = mutate_model(survivors[0], strength=0.03,
                                  laws=LAWS if not law_subsets[e] else None)
            child2 = crossover(survivors[0], survivors[1])
            child2 = mutate_model(child2, strength=0.02)
            expert_pops[e] = survivors + [child1, child2]

        # Evaluate combined MoE (best from each expert)
        combined_ce = np.mean([m['ce'] for m in expert_best])
        combined_phi = np.mean([m['phi'] for m in expert_best])
        combined_fitness = combined_phi / (combined_ce + 0.01)

        history.append({
            'gen': gen,
            'combined_ce': combined_ce,
            'combined_phi': combined_phi,
            'combined_fitness': combined_fitness,
            'expert_ce': [m['ce'] for m in expert_best],
            'expert_phi': [m['phi'] for m in expert_best],
        })

        if (gen + 1) % 10 == 0 or gen == 0:
            expert_phis = [f"{m['phi']:.3f}" for m in expert_best]
            print(f"    Gen {gen+1:>3}/{generations}  "
                  f"Combined: CE={combined_ce:.4f} Phi={combined_phi:.4f}  "
                  f"Experts Phi: [{', '.join(expert_phis)}]")
            sys.stdout.flush()

    # Results
    print("\n" + "-" * 62)
    print("  Expert | Final CE | Final Phi | Specialization")
    print("  " + "-" * 50)
    last = history[-1]
    for e in range(n_experts):
        laws_used = len(law_subsets[e]) if law_subsets else 0
        print(f"  E{e}       | {last['expert_ce'][e]:.4f}   "
              f"| {last['expert_phi'][e]:.4f}    | {laws_used} laws")

    print(f"\n  Combined: CE={last['combined_ce']:.4f}  "
          f"Phi={last['combined_phi']:.4f}  "
          f"Fitness={last['combined_fitness']:.4f}")

    # Graph
    print("\n  Combined Fitness Evolution:")
    fit_vals = [h['combined_fitness'] for h in history]
    _ascii_single_graph(fit_vals, label='fitness', width=50)

    # Expert diversity: how different are the experts?
    phi_std = np.std(last['expert_phi'])
    ce_std = np.std(last['expert_ce'])
    print(f"\n  Expert diversity: Phi_std={phi_std:.4f}, CE_std={ce_std:.4f}")
    print(f"  (Higher diversity = more specialization)")

    return history


# ══════════════════════════════════════════════════════════════
# ASCII graph utilities
# ══════════════════════════════════════════════════════════════

def _ascii_single_graph(values, label='', width=50, height=8):
    """Single-series ASCII graph."""
    if not values:
        return
    # Subsample to width
    n = len(values)
    if n > width:
        indices = np.linspace(0, n - 1, width).astype(int)
        vals = [values[i] for i in indices]
    else:
        vals = values

    mn, mx = min(vals), max(vals)
    rng = mx - mn if mx > mn else 1.0

    for row in range(height, 0, -1):
        threshold = mn + rng * row / height
        line = '  '
        if row == height:
            line += f'{mx:>7.3f} |'
        elif row == 1:
            line += f'{mn:>7.3f} |'
        else:
            line += '        |'
        for v in vals:
            line += '#' if v >= threshold else ' '
        print(line)
    print('        +' + '-' * len(vals))
    if label:
        print(f'         {label} (n={len(values)})')


def _ascii_dual_graph(a_vals, b_vals, label_a='A', label_b='B',
                      width=50, height=8, lower_is_better=False):
    """Dual-series ASCII graph (A=#, B=.)."""
    if not a_vals or not b_vals:
        return
    n = max(len(a_vals), len(b_vals))
    if n > width:
        idx = np.linspace(0, n - 1, width).astype(int)
        a = [a_vals[min(i, len(a_vals) - 1)] for i in idx]
        b = [b_vals[min(i, len(b_vals) - 1)] for i in idx]
    else:
        a = a_vals[:width]
        b = b_vals[:width]

    all_vals = a + b
    mn, mx = min(all_vals), max(all_vals)
    rng = mx - mn if mx > mn else 1.0

    for row in range(height, 0, -1):
        threshold = mn + rng * row / height
        line = '  '
        if row == height:
            line += f'{mx:>7.3f} |'
        elif row == 1:
            line += f'{mn:>7.3f} |'
        else:
            line += '        |'
        for i in range(len(a)):
            av = a[i] >= threshold
            bv = b[i] if i < len(b) else mn
            bv = bv >= threshold
            if av and bv:
                line += '%'
            elif av:
                line += '#'
            elif bv:
                line += '.'
            else:
                line += ' '
        print(line)
    print('        +' + '-' * len(a))
    print(f'         # = {label_a}  . = {label_b}  % = both')


# ══════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description='B3+B4 Acceleration Experiments')
    parser.add_argument('--b3-only', action='store_true', help='Run B3 MoE only')
    parser.add_argument('--b4-only', action='store_true', help='Run B4 Evolution only')
    parser.add_argument('--combined', action='store_true', help='Run B3+B4 combined only')
    parser.add_argument('--steps', type=int, default=200, help='Steps for B3')
    parser.add_argument('--generations', type=int, default=100, help='Generations for B4')
    parser.add_argument('--pop-size', type=int, default=16, help='Population size for B4')
    args = parser.parse_args()

    print("=" * 62)
    print("  ACCELERATION EXPERIMENTS: B3 MoE + B4 Evolution")
    print("=" * 62)
    print(f"  {time.strftime('%Y-%m-%d %H:%M:%S')}")
    sys.stdout.flush()

    run_all = not (args.b3_only or args.b4_only or args.combined)
    all_results = {}

    if run_all or args.b3_only:
        all_results['b3'] = run_b3_experiment(steps=args.steps)

    if run_all or args.b4_only:
        all_results['b4'] = run_b4_experiment(
            pop_size=args.pop_size,
            generations=args.generations,
        )

    if run_all or args.combined:
        all_results['b3b4'] = run_combined_experiment(
            generations=min(args.generations, 50),
        )

    # Final summary
    print("\n" + "=" * 62)
    print("  FINAL SUMMARY")
    print("=" * 62)

    if 'b3' in all_results:
        b3 = all_results['b3']
        best_strategy = min(b3, key=lambda k: b3[k]['avg_ce'])
        best_phi_strategy = max(b3, key=lambda k: b3[k]['avg_phi'])
        print(f"\n  B3 MoE:")
        print(f"    Best CE strategy:  {best_strategy} "
              f"(CE={b3[best_strategy]['avg_ce']:.4f})")
        print(f"    Best Phi strategy: {best_phi_strategy} "
              f"(Phi={b3[best_phi_strategy]['avg_phi']:.4f})")
        delta_ce = (b3['random']['avg_ce'] - b3['consciousness']['avg_ce']) / b3['random']['avg_ce'] * 100
        delta_phi = (b3['consciousness']['avg_phi'] - b3['random']['avg_phi']) / max(b3['random']['avg_phi'], 1e-8) * 100
        print(f"    Consciousness vs Random: CE {delta_ce:+.1f}%, Phi {delta_phi:+.1f}%")

    if 'b4' in all_results:
        b4 = all_results['b4']
        evo = b4['evolution']['history'][-1]
        gd = b4['gradient']['history'][-1]
        print(f"\n  B4 Evolution vs Gradient:")
        print(f"    Evolution:  CE={evo['best_ce']:.4f}  "
              f"Phi={evo['best_phi']:.4f}  "
              f"Fitness={evo['best_fitness']:.4f}  "
              f"({b4['evolution']['time']:.1f}s)")
        print(f"    Gradient:   CE={gd['best_ce']:.4f}  "
              f"Phi={gd['best_phi']:.4f}  "
              f"Fitness={gd['best_fitness']:.4f}  "
              f"({b4['gradient']['time']:.1f}s)")
        ce_winner = 'Evolution' if evo['best_ce'] < gd['best_ce'] else 'Gradient'
        phi_winner = 'Evolution' if evo['best_phi'] > gd['best_phi'] else 'Gradient'
        fit_winner = 'Evolution' if evo['best_fitness'] > gd['best_fitness'] else 'Gradient'
        print(f"    CE winner:      {ce_winner}")
        print(f"    Phi winner:     {phi_winner}")
        print(f"    Fitness winner: {fit_winner}")

    if 'b3b4' in all_results:
        h = all_results['b3b4'][-1]
        print(f"\n  B3+B4 Combined (Evolving MoE):")
        print(f"    Final: CE={h['combined_ce']:.4f}  "
              f"Phi={h['combined_phi']:.4f}  "
              f"Fitness={h['combined_fitness']:.4f}")
        phi_std = np.std(h['expert_phi'])
        print(f"    Expert specialization (Phi std): {phi_std:.4f}")

    print("\n" + "=" * 62)
    print("  Experiment complete.")
    print("=" * 62)


if __name__ == '__main__':
    main()
