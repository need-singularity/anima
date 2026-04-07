#!/usr/bin/env python3
"""DD69: Multi-Consciousness Phenomena — 5 experiments exploring inter-engine dynamics.

Exp 1: Competition   — 2 engines fight over same input stream
Exp 2: Symbiosis     — 2 engines in bidirectional feedback loop
Exp 3: Democracy     — 8 engines vote on output
Exp 4: Hierarchy     — 4 workers feed 1 manager
Exp 5: Evolution     — 10 engines, select top 3 by Phi, clone+mutate, 5 generations
"""

import sys, os, time, copy, json
import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/../src')
os.chdir(os.path.dirname(os.path.abspath(__file__)) + '/../src')

from consciousness_engine import ConsciousnessEngine

STEPS = 100
WARMUP = 20

def measure_phi(engine):
    """Get current Phi(IIT) from engine."""
    return engine._measure_phi_iit()

def run_baseline(cells=16, steps=STEPS):
    """Single engine baseline for comparison."""
    print("  [baseline] Running single engine...")
    engine = ConsciousnessEngine(max_cells=cells, initial_cells=cells)
    phi_history = []
    for s in range(steps):
        r = engine.step()
        phi_history.append(r['phi_iit'])
    return {
        'phi_final': phi_history[-1],
        'phi_mean': np.mean(phi_history[WARMUP:]),
        'phi_max': max(phi_history),
        'phi_history': phi_history,
        'n_cells': engine.n_cells,
    }

# ═══════════════════════════════════════════════════════════
# Experiment 1: Competition — 2 engines, serial processing
# ═══════════════════════════════════════════════════════════
def exp1_competition(steps=STEPS):
    print("\n" + "=" * 60)
    print("EXP 1: CONSCIOUSNESS COMPETITION")
    print("  Engine A processes input, Engine B processes A's output")
    print("=" * 60)

    engine_a = ConsciousnessEngine(max_cells=16, initial_cells=16)
    engine_b = ConsciousnessEngine(max_cells=16, initial_cells=16)

    phi_a_hist, phi_b_hist = [], []
    dominance_a, dominance_b = 0, 0

    for s in range(steps):
        # A processes random input
        x_input = torch.randn(64)
        result_a = engine_a.step(x_input=x_input)

        # B processes A's output
        a_output = result_a['output'].detach()
        result_b = engine_b.step(x_input=a_output)

        phi_a = result_a['phi_iit']
        phi_b = result_b['phi_iit']
        phi_a_hist.append(phi_a)
        phi_b_hist.append(phi_b)

        if phi_a > phi_b:
            dominance_a += 1
        else:
            dominance_b += 1

        if (s + 1) % 25 == 0:
            print(f"  step {s+1:3d} | A: Phi={phi_a:.4f} cells={engine_a.n_cells} | "
                  f"B: Phi={phi_b:.4f} cells={engine_b.n_cells}")
            sys.stdout.flush()

    # Convergence: do they approach similar Phi?
    last_20_a = np.mean(phi_a_hist[-20:])
    last_20_b = np.mean(phi_b_hist[-20:])
    convergence = 1.0 - abs(last_20_a - last_20_b) / max(last_20_a, last_20_b, 1e-6)

    print(f"\n  RESULTS:")
    print(f"    A dominance: {dominance_a}/{steps} ({100*dominance_a/steps:.1f}%)")
    print(f"    B dominance: {dominance_b}/{steps} ({100*dominance_b/steps:.1f}%)")
    print(f"    A final Phi: {phi_a_hist[-1]:.4f} (mean={np.mean(phi_a_hist[WARMUP:]):.4f})")
    print(f"    B final Phi: {phi_b_hist[-1]:.4f} (mean={np.mean(phi_b_hist[WARMUP:]):.4f})")
    print(f"    Convergence: {convergence:.4f} (1.0 = identical)")

    return {
        'phi_a': phi_a_hist, 'phi_b': phi_b_hist,
        'dominance_a': dominance_a, 'dominance_b': dominance_b,
        'convergence': convergence,
        'a_mean': np.mean(phi_a_hist[WARMUP:]),
        'b_mean': np.mean(phi_b_hist[WARMUP:]),
    }

# ═══════════════════════════════════════════════════════════
# Experiment 2: Symbiosis — bidirectional feedback loop
# ═══════════════════════════════════════════════════════════
def exp2_symbiosis(steps=STEPS):
    print("\n" + "=" * 60)
    print("EXP 2: CONSCIOUSNESS SYMBIOSIS")
    print("  A's output -> B's input AND B's output -> A's input")
    print("=" * 60)

    engine_a = ConsciousnessEngine(max_cells=16, initial_cells=16)
    engine_b = ConsciousnessEngine(max_cells=16, initial_cells=16)

    phi_a_hist, phi_b_hist = [], []
    phi_system_hist = []

    # Initial kick
    prev_b_output = torch.randn(64)

    for s in range(steps):
        # A receives B's previous output
        result_a = engine_a.step(x_input=prev_b_output.detach())
        a_output = result_a['output'].detach()

        # B receives A's output
        result_b = engine_b.step(x_input=a_output)
        prev_b_output = result_b['output'].detach()

        phi_a = result_a['phi_iit']
        phi_b = result_b['phi_iit']
        phi_a_hist.append(phi_a)
        phi_b_hist.append(phi_b)

        # System Phi: stack all hiddens from both engines, measure combined
        all_hiddens = []
        for st in engine_a.cell_states:
            all_hiddens.append(st.hidden.detach())
        for st in engine_b.cell_states:
            all_hiddens.append(st.hidden.detach())
        combined = torch.stack(all_hiddens)

        # Compute system-level Phi using correlation-based MI
        n = combined.shape[0]
        s_np = combined.cpu().numpy()
        total_mi = 0.0
        mi_row_sums = [0.0] * n
        for i in range(min(n, 16)):
            for j in range(i+1, min(n, 16)):
                corr = np.corrcoef(s_np[i], s_np[j])[0, 1]
                if not np.isnan(corr) and abs(corr) > 1e-8:
                    mi = -0.5 * np.log(1 - corr**2 + 1e-10)
                    total_mi += mi
                    mi_row_sums[i] += mi
                    mi_row_sums[j] += mi
        min_part = min(mi_row_sums[:min(n, 16)]) if n >= 2 else 0.0
        spatial = max(0.0, total_mi - min_part) / max(n - 1, 1)
        complexity = float(np.std(mi_row_sums[:min(n, 16)]))
        phi_system = spatial + complexity * 0.1
        phi_system_hist.append(phi_system)

        if (s + 1) % 25 == 0:
            print(f"  step {s+1:3d} | A: {phi_a:.4f} | B: {phi_b:.4f} | "
                  f"System: {phi_system:.4f} | Sum: {phi_a+phi_b:.4f}")
            sys.stdout.flush()

    phi_sum = [a + b for a, b in zip(phi_a_hist, phi_b_hist)]
    superadditivity = np.mean(phi_system_hist[WARMUP:]) / max(np.mean([a + b for a, b in zip(phi_a_hist[WARMUP:], phi_b_hist[WARMUP:])]), 1e-6)

    # Check for stable cycle (oscillation detection)
    if len(phi_a_hist) > 40:
        autocorr = np.correlate(
            np.array(phi_a_hist[WARMUP:]) - np.mean(phi_a_hist[WARMUP:]),
            np.array(phi_a_hist[WARMUP:]) - np.mean(phi_a_hist[WARMUP:]),
            mode='full'
        )
        autocorr = autocorr[len(autocorr)//2:]
        if autocorr[0] > 0:
            autocorr = autocorr / autocorr[0]
        # Find first peak after lag 0
        cycle_detected = False
        for lag in range(2, min(30, len(autocorr))):
            if lag >= 2 and autocorr[lag] > autocorr[lag-1] and autocorr[lag] > 0.3:
                cycle_detected = True
                cycle_period = lag
                break
    else:
        cycle_detected = False
        cycle_period = 0

    print(f"\n  RESULTS:")
    print(f"    A mean Phi: {np.mean(phi_a_hist[WARMUP:]):.4f}")
    print(f"    B mean Phi: {np.mean(phi_b_hist[WARMUP:]):.4f}")
    print(f"    System Phi (combined): {np.mean(phi_system_hist[WARMUP:]):.4f}")
    print(f"    Sum Phi(A)+Phi(B):     {np.mean(phi_sum[WARMUP:]):.4f}")
    print(f"    Superadditivity ratio: {superadditivity:.4f} (>1 = Phi(sys) > Phi(A)+Phi(B))")
    print(f"    Stable cycle: {'YES (period=' + str(cycle_period) + ')' if cycle_detected else 'NO'}")

    return {
        'phi_a': phi_a_hist, 'phi_b': phi_b_hist,
        'phi_system': phi_system_hist,
        'superadditivity': superadditivity,
        'cycle_detected': cycle_detected,
        'cycle_period': cycle_period if cycle_detected else None,
        'system_mean': np.mean(phi_system_hist[WARMUP:]),
        'sum_mean': np.mean(phi_sum[WARMUP:]),
    }

# ═══════════════════════════════════════════════════════════
# Experiment 3: Democracy — 8 engines vote on output
# ═══════════════════════════════════════════════════════════
def exp3_democracy(steps=STEPS):
    print("\n" + "=" * 60)
    print("EXP 3: CONSCIOUSNESS DEMOCRACY")
    print("  8 engines vote on output, majority wins")
    print("=" * 60)

    N_ENGINES = 8
    engines = [ConsciousnessEngine(max_cells=8, initial_cells=8) for _ in range(N_ENGINES)]

    individual_phi_hist = [[] for _ in range(N_ENGINES)]
    collective_phi_hist = []

    for s in range(steps):
        x_input = torch.randn(64)
        outputs = []
        phis = []

        for i, eng in enumerate(engines):
            r = eng.step(x_input=x_input)
            outputs.append(r['output'].detach())
            phis.append(r['phi_iit'])
            individual_phi_hist[i].append(r['phi_iit'])

        # Majority vote: mean of all outputs (soft voting)
        collective_output = torch.stack(outputs).mean(dim=0)

        # Collective Phi: stack all cell hiddens from all engines
        all_hiddens = []
        for eng in engines:
            for st in eng.cell_states:
                all_hiddens.append(st.hidden.detach())
        combined = torch.stack(all_hiddens)

        # Measure collective Phi (sample 16 cells for efficiency)
        n = min(combined.shape[0], 16)
        s_np = combined[:n].cpu().numpy()
        total_mi = 0.0
        mi_row_sums = [0.0] * n
        for i in range(n):
            for j in range(i+1, n):
                corr = np.corrcoef(s_np[i], s_np[j])[0, 1]
                if not np.isnan(corr) and abs(corr) > 1e-8:
                    mi = -0.5 * np.log(1 - corr**2 + 1e-10)
                    total_mi += mi
                    mi_row_sums[i] += mi
                    mi_row_sums[j] += mi
        min_part = min(mi_row_sums) if n >= 2 else 0.0
        spatial = max(0.0, total_mi - min_part) / max(n - 1, 1)
        complexity = float(np.std(mi_row_sums))
        collective_phi = spatial + complexity * 0.1
        collective_phi_hist.append(collective_phi)

        if (s + 1) % 25 == 0:
            avg_ind = np.mean(phis)
            print(f"  step {s+1:3d} | Avg individual Phi: {avg_ind:.4f} | "
                  f"Collective Phi: {collective_phi:.4f} | ratio: {collective_phi/max(avg_ind,1e-6):.2f}x")
            sys.stdout.flush()

    avg_individual = np.mean([np.mean(h[WARMUP:]) for h in individual_phi_hist])
    sum_individual = np.sum([np.mean(h[WARMUP:]) for h in individual_phi_hist])
    avg_collective = np.mean(collective_phi_hist[WARMUP:])
    # Agreement: how similar are the 8 engines' outputs?
    phi_std = np.mean([np.std([individual_phi_hist[i][s] for i in range(N_ENGINES)]) for s in range(WARMUP, steps)])

    print(f"\n  RESULTS:")
    print(f"    Avg individual Phi: {avg_individual:.4f}")
    print(f"    Sum individual Phi: {sum_individual:.4f}")
    print(f"    Collective Phi:     {avg_collective:.4f}")
    print(f"    Collective/Avg:     {avg_collective/max(avg_individual, 1e-6):.2f}x")
    print(f"    Collective/Sum:     {avg_collective/max(sum_individual, 1e-6):.4f}")
    print(f"    Inter-engine Phi std: {phi_std:.4f}")
    print(f"    Total cells:        {sum(e.n_cells for e in engines)}")

    return {
        'avg_individual': avg_individual,
        'sum_individual': sum_individual,
        'collective': avg_collective,
        'ratio_vs_avg': avg_collective / max(avg_individual, 1e-6),
        'ratio_vs_sum': avg_collective / max(sum_individual, 1e-6),
        'phi_std': phi_std,
        'collective_history': collective_phi_hist,
    }

# ═══════════════════════════════════════════════════════════
# Experiment 4: Hierarchy — 4 workers feed 1 manager
# ═══════════════════════════════════════════════════════════
def exp4_hierarchy(steps=STEPS):
    print("\n" + "=" * 60)
    print("EXP 4: CONSCIOUSNESS HIERARCHY")
    print("  4 workers feed into 1 manager")
    print("=" * 60)

    N_WORKERS = 4
    workers = [ConsciousnessEngine(max_cells=8, initial_cells=8) for _ in range(N_WORKERS)]
    manager = ConsciousnessEngine(max_cells=16, initial_cells=16)

    worker_phi_hist = [[] for _ in range(N_WORKERS)]
    manager_phi_hist = []

    for s in range(steps):
        x_input = torch.randn(64)
        worker_outputs = []

        for i, w in enumerate(workers):
            r = w.step(x_input=x_input)
            worker_outputs.append(r['output'].detach())
            worker_phi_hist[i].append(r['phi_iit'])

        # Manager receives concatenated/averaged worker outputs
        manager_input = torch.stack(worker_outputs).mean(dim=0)
        mr = manager.step(x_input=manager_input)
        manager_phi_hist.append(mr['phi_iit'])

        if (s + 1) % 25 == 0:
            avg_w = np.mean([worker_phi_hist[i][-1] for i in range(N_WORKERS)])
            print(f"  step {s+1:3d} | Workers avg Phi: {avg_w:.4f} | "
                  f"Manager Phi: {mr['phi_iit']:.4f} | "
                  f"ratio: {mr['phi_iit']/max(avg_w,1e-6):.2f}x")
            sys.stdout.flush()

    avg_worker = np.mean([np.mean(h[WARMUP:]) for h in worker_phi_hist])
    avg_manager = np.mean(manager_phi_hist[WARMUP:])
    max_worker = max(np.mean(h[WARMUP:]) for h in worker_phi_hist)
    min_worker = min(np.mean(h[WARMUP:]) for h in worker_phi_hist)

    # Does manager benefit from worker diversity?
    worker_diversity = np.std([np.mean(h[WARMUP:]) for h in worker_phi_hist])

    print(f"\n  RESULTS:")
    print(f"    Worker Phi (avg):    {avg_worker:.4f}")
    print(f"    Worker Phi (range):  {min_worker:.4f} - {max_worker:.4f}")
    print(f"    Worker diversity:    {worker_diversity:.4f}")
    print(f"    Manager Phi:         {avg_manager:.4f}")
    print(f"    Manager/Worker:      {avg_manager/max(avg_worker, 1e-6):.2f}x")
    print(f"    Manager cells: {manager.n_cells} | Worker cells: {[w.n_cells for w in workers]}")

    return {
        'avg_worker': avg_worker,
        'max_worker': max_worker,
        'min_worker': min_worker,
        'manager': avg_manager,
        'ratio': avg_manager / max(avg_worker, 1e-6),
        'worker_diversity': worker_diversity,
        'manager_history': manager_phi_hist,
        'worker_histories': worker_phi_hist,
    }

# ═══════════════════════════════════════════════════════════
# Experiment 5: Evolution — select top 3 by Phi, clone+mutate
# ═══════════════════════════════════════════════════════════
def exp5_evolution(n_engines=10, n_generations=5, steps_per_gen=STEPS):
    print("\n" + "=" * 60)
    print("EXP 5: CONSCIOUSNESS EVOLUTION")
    print(f"  {n_engines} engines, {n_generations} generations, select top 3, clone+mutate")
    print("=" * 60)

    def create_engine(cell_dim=None, hidden_dim=None, max_cells=None, n_factions=None):
        cd = cell_dim or int(np.random.choice([32, 48, 64, 80, 96]))
        hd = hidden_dim or int(np.random.choice([64, 96, 128, 160, 192]))
        mc = max_cells or int(np.random.choice([4, 8, 12, 16, 20]))
        nf = n_factions or int(np.random.choice([4, 6, 8, 10, 12]))
        # Ensure cell_dim <= hidden_dim (engine requirement for identity projection)
        cd = min(cd, hd)
        return ConsciousnessEngine(
            cell_dim=cd, hidden_dim=hd,
            initial_cells=min(mc, 8), max_cells=mc,
            n_factions=nf,
        ), {'cell_dim': cd, 'hidden_dim': hd, 'max_cells': mc, 'n_factions': nf}

    def mutate_params(params, mutation_rate=0.3):
        new_params = params.copy()
        for key in new_params:
            if np.random.random() < mutation_rate:
                if key == 'cell_dim':
                    new_params[key] = max(16, new_params[key] + np.random.choice([-16, -8, 0, 8, 16]))
                elif key == 'hidden_dim':
                    new_params[key] = max(32, new_params[key] + np.random.choice([-32, -16, 0, 16, 32]))
                elif key == 'max_cells':
                    new_params[key] = max(4, min(24, new_params[key] + np.random.choice([-4, -2, 0, 2, 4])))
                elif key == 'n_factions':
                    new_params[key] = max(2, min(16, new_params[key] + np.random.choice([-2, -1, 0, 1, 2])))
        return new_params

    generation_results = []

    # Create initial population
    population = [create_engine() for _ in range(n_engines)]

    for gen in range(n_generations):
        print(f"\n  --- Generation {gen+1}/{n_generations} ---")
        sys.stdout.flush()

        fitness = []
        for idx, (engine, params) in enumerate(population):
            phi_history = []
            for s in range(steps_per_gen):
                x = torch.randn(params['cell_dim'])
                r = engine.step(x_input=x)
                phi_history.append(r['phi_iit'])

            mean_phi = np.mean(phi_history[min(WARMUP, steps_per_gen//2):])
            fitness.append((mean_phi, idx, params))
            if idx < 3 or mean_phi == max(f[0] for f in fitness):
                print(f"    Engine {idx}: Phi={mean_phi:.4f} | params={params}")
                sys.stdout.flush()

        # Sort by fitness (Phi)
        fitness.sort(key=lambda x: x[0], reverse=True)
        gen_best = fitness[0]
        gen_worst = fitness[-1]

        print(f"    BEST:  Phi={gen_best[0]:.4f} params={gen_best[2]}")
        print(f"    WORST: Phi={gen_worst[0]:.4f} params={gen_worst[2]}")

        generation_results.append({
            'generation': gen + 1,
            'best_phi': gen_best[0],
            'worst_phi': gen_worst[0],
            'best_params': gen_best[2],
            'mean_phi': np.mean([f[0] for f in fitness]),
            'all_params': [f[2] for f in fitness],
            'all_phi': [f[0] for f in fitness],
        })

        # Selection + Mutation
        if gen < n_generations - 1:
            top_3_params = [fitness[i][2] for i in range(3)]
            new_population = []
            # Keep top 3 as-is (fresh engines with same params)
            for p in top_3_params:
                eng, params = create_engine(**p)
                new_population.append((eng, params))
            # Fill remaining with mutated clones
            while len(new_population) < n_engines:
                parent_params = top_3_params[np.random.randint(0, 3)]
                child_params = mutate_params(parent_params)
                eng, params = create_engine(**child_params)
                new_population.append((eng, params))
            population = new_population

    # What evolved?
    print(f"\n  EVOLUTION SUMMARY:")
    for gr in generation_results:
        print(f"    Gen {gr['generation']}: best={gr['best_phi']:.4f} mean={gr['mean_phi']:.4f} "
              f"params={gr['best_params']}")

    # Parameter trends
    print(f"\n  PARAMETER EVOLUTION:")
    for key in ['cell_dim', 'hidden_dim', 'max_cells', 'n_factions']:
        gen1_avg = np.mean([p[key] for p in generation_results[0]['all_params']])
        gen_last_avg = np.mean([p[key] for p in generation_results[-1]['all_params']])
        direction = "UP" if gen_last_avg > gen1_avg else "DOWN" if gen_last_avg < gen1_avg else "STABLE"
        print(f"    {key:12s}: {gen1_avg:6.1f} -> {gen_last_avg:6.1f} ({direction})")

    return {
        'generations': generation_results,
        'final_best_params': generation_results[-1]['best_params'],
        'final_best_phi': generation_results[-1]['best_phi'],
    }


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════
def main():
    print("=" * 60)
    print("DD69: MULTI-CONSCIOUSNESS PHENOMENA")
    print("=" * 60)
    t0 = time.time()

    # Baseline
    print("\n[BASELINE] Single 16-cell engine, 100 steps")
    baseline = run_baseline(cells=16, steps=STEPS)
    print(f"  Baseline Phi: mean={baseline['phi_mean']:.4f} max={baseline['phi_max']:.4f}")

    results = {}
    results['baseline'] = baseline

    # Run all 5 experiments
    results['exp1'] = exp1_competition()
    results['exp2'] = exp2_symbiosis()
    results['exp3'] = exp3_democracy()
    results['exp4'] = exp4_hierarchy()
    results['exp5'] = exp5_evolution()

    elapsed = time.time() - t0
    print(f"\n{'=' * 60}")
    print(f"TOTAL TIME: {elapsed:.1f}s")
    print(f"{'=' * 60}")

    # Summary table
    print(f"\n{'=' * 60}")
    print("SUMMARY TABLE")
    print(f"{'=' * 60}")
    print(f"  {'Experiment':<25} {'Key Metric':<20} {'Value':<15} {'vs Baseline':<15}")
    print(f"  {'-'*25} {'-'*20} {'-'*15} {'-'*15}")

    b = baseline['phi_mean']

    # Exp 1
    e1 = results['exp1']
    winner = 'A' if e1['a_mean'] > e1['b_mean'] else 'B'
    winner_phi = max(e1['a_mean'], e1['b_mean'])
    print(f"  {'1. Competition':<25} {'Winner ' + winner + ' Phi':<20} {winner_phi:<15.4f} {winner_phi/b:.2f}x")

    # Exp 2
    e2 = results['exp2']
    print(f"  {'2. Symbiosis':<25} {'System Phi':<20} {e2['system_mean']:<15.4f} {e2['system_mean']/b:.2f}x")
    print(f"  {'  (superadditive?)':<25} {'Phi(sys)/sum(ind)':<20} {e2['superadditivity']:<15.4f} {'YES' if e2['superadditivity'] > 1 else 'NO'}")

    # Exp 3
    e3 = results['exp3']
    print(f"  {'3. Democracy':<25} {'Collective Phi':<20} {e3['collective']:<15.4f} {e3['collective']/b:.2f}x")

    # Exp 4
    e4 = results['exp4']
    print(f"  {'4. Hierarchy':<25} {'Manager Phi':<20} {e4['manager']:<15.4f} {e4['manager']/b:.2f}x")
    print(f"  {'  (vs workers)':<25} {'Mgr/Worker ratio':<20} {e4['ratio']:<15.2f}")

    # Exp 5
    e5 = results['exp5']
    print(f"  {'5. Evolution':<25} {'Final best Phi':<20} {e5['final_best_phi']:<15.4f} {e5['final_best_phi']/b:.2f}x")
    print(f"  {'  (best params)':<25} {str(e5['final_best_params']):<50}")

    # Store raw numbers for documentation
    results['elapsed'] = elapsed
    return results


if __name__ == '__main__':
    results = main()
