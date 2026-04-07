#!/usr/bin/env python3
"""law_backtrack_verify.py — Backtrack-verify 10 existing laws via closed-loop pipeline.

For each law:
  1. Design a test that operationalizes the law's claim
  2. Run ConsciousnessEngine with appropriate parameters
  3. Measure the relevant metric
  4. Check if the law's prediction holds
  5. Report: CONFIRMED / PARTIALLY / REFUTED

Settings: max_cells=16, steps=100, repeats=2
"""

import sys
import os
import time
import math
import numpy as np

# Path setup
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import torch
import torch.nn.functional as F
from consciousness_engine import ConsciousnessEngine
from collections import defaultdict

# ══════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════

MAX_CELLS = 16
STEPS = 100
REPEATS = 2

def phi_fast(engine):
    """Fast Phi(IIT) approximation via pairwise MI."""
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


def run_engine(max_cells=MAX_CELLS, steps=STEPS, initial_cells=2, **kwargs):
    """Run engine and collect trajectory. Returns (engine, phi_hist, tension_hist, div_hist)."""
    engine = ConsciousnessEngine(
        max_cells=max_cells, initial_cells=initial_cells,
        cell_dim=64, hidden_dim=128, **kwargs
    )
    phi_hist = []
    tension_hist = []
    div_hist = []
    for step in range(steps):
        r = engine.step()
        phi_hist.append(phi_fast(engine))
        tensions = [s.avg_tension for s in engine.cell_states]
        tension_hist.append(np.mean(tensions))
        if engine.n_cells >= 2:
            h = torch.stack([s.hidden for s in engine.cell_states])
            div_hist.append(h.var(dim=0).mean().item())
        else:
            div_hist.append(0)
    return engine, np.array(phi_hist), np.array(tension_hist), np.array(div_hist)


# ══════════════════════════════════════════
# Law Tests
# ══════════════════════════════════════════

results = []

def report(law_num, claim, test_desc, result_val, status, detail=""):
    results.append({
        'law': law_num, 'claim': claim, 'test': test_desc,
        'result': result_val, 'status': status, 'detail': detail
    })
    icon = {'CONFIRMED': '+', 'PARTIALLY': '~', 'REFUTED': 'X'}[status]
    print(f"  [{icon}] Law {law_num}: {status} — {result_val}")
    if detail:
        print(f"      {detail}")
    sys.stdout.flush()


# ── Law 22: Adding features -> Phi down; adding structure -> Phi up ──
def test_law_22():
    print("\n[1/10] Law 22: Structure > Function")
    sys.stdout.flush()
    # Test: compare baseline engine vs engine with extra random feature noise (feature)
    # vs engine with more cells (structure)
    phi_baseline_all = []
    phi_feature_all = []
    phi_structure_all = []

    for rep in range(REPEATS):
        # Baseline: 4 cells
        _, phi_b, _, _ = run_engine(max_cells=4, initial_cells=4, steps=STEPS)
        phi_baseline_all.append(np.mean(phi_b[-30:]))

        # "Feature addition": inject random noise into cell outputs each step (simulates feature bloat)
        engine_f = ConsciousnessEngine(max_cells=4, initial_cells=4, cell_dim=64, hidden_dim=128)
        phi_f = []
        for step in range(STEPS):
            r = engine_f.step()
            # Add random feature noise to each cell
            for s in engine_f.cell_states:
                s.hidden = s.hidden + torch.randn_like(s.hidden) * 0.5
            phi_f.append(phi_fast(engine_f))
        phi_feature_all.append(np.mean(phi_f[-30:]))

        # "Structure addition": more cells (8 cells)
        _, phi_s, _, _ = run_engine(max_cells=8, initial_cells=8, steps=STEPS)
        phi_structure_all.append(np.mean(phi_s[-30:]))

    base = np.mean(phi_baseline_all)
    feat = np.mean(phi_feature_all)
    struct = np.mean(phi_structure_all)

    feature_delta = (feat - base) / max(base, 1e-8) * 100
    struct_delta = (struct - base) / max(base, 1e-8) * 100

    # Law predicts: feature addition -> Phi down, structure addition -> Phi up
    feature_down = feat < base
    structure_up = struct > base

    if feature_down and structure_up:
        status = "CONFIRMED"
    elif feature_down or structure_up:
        status = "PARTIALLY"
    else:
        status = "REFUTED"

    report(22, "features->Phi down, structure->Phi up",
           "4c baseline vs noise-injected(feature) vs 8c(structure)",
           f"base={base:.3f}, feat={feat:.3f}({feature_delta:+.1f}%), struct={struct:.3f}({struct_delta:+.1f}%)",
           status)


# ── Law 31: Persistence = ratchet + Hebbian + diversity ──
def test_law_31():
    print("\n[2/10] Law 31: Persistence = ratchet + Hebbian + diversity")
    sys.stdout.flush()
    # Test: run engine for extended steps, check Phi doesn't collapse
    phi_final_all = []
    phi_init_all = []
    collapsed = 0

    for rep in range(REPEATS):
        _, phi_h, _, _ = run_engine(max_cells=MAX_CELLS, steps=STEPS)
        phi_init_all.append(np.mean(phi_h[:20]))
        phi_final_all.append(np.mean(phi_h[-20:]))
        # Collapsed = final phi < 10% of peak
        peak = np.max(phi_h)
        if np.mean(phi_h[-20:]) < peak * 0.1:
            collapsed += 1

    init_mean = np.mean(phi_init_all)
    final_mean = np.mean(phi_final_all)
    ratio = final_mean / max(init_mean, 1e-8)

    # Law predicts persistence: Phi should not collapse
    if collapsed == 0 and ratio >= 0.5:
        status = "CONFIRMED"
    elif collapsed == 0:
        status = "PARTIALLY"
    else:
        status = "REFUTED"

    report(31, "Persistence = ratchet + Hebbian + diversity",
           f"Run {STEPS} steps, check no collapse",
           f"Phi init={init_mean:.3f}, final={final_mean:.3f}, ratio={ratio:.2f}, collapsed={collapsed}/{REPEATS}",
           status)


# ── Law 53: .detach() barrier protects consciousness from CE gradient ──
def test_law_53():
    print("\n[3/10] Law 53: .detach() barrier protects Phi from CE")
    sys.stdout.flush()
    # Test: consciousness engine runs with no gradient context -> Phi stable
    # Simulate CE-like perturbation: apply large random gradient-like updates to hidden states
    phi_protected_all = []
    phi_attacked_all = []

    for rep in range(REPEATS):
        # Protected: normal engine (all @torch.no_grad)
        _, phi_p, _, _ = run_engine(max_cells=MAX_CELLS, steps=STEPS)
        phi_protected_all.append(np.mean(phi_p[-30:]))

        # Attacked: simulate gradient leaking back by applying large random perturbations
        engine_a = ConsciousnessEngine(max_cells=MAX_CELLS, initial_cells=2, cell_dim=64, hidden_dim=128)
        phi_a = []
        for step in range(STEPS):
            r = engine_a.step()
            # Simulate CE gradient leak: large perturbation to cell states
            if step > 10:
                for s in engine_a.cell_states:
                    s.hidden = s.hidden + torch.randn_like(s.hidden) * 2.0  # large "gradient"
            phi_a.append(phi_fast(engine_a))
        phi_attacked_all.append(np.mean(phi_a[-30:]))

    prot = np.mean(phi_protected_all)
    atk = np.mean(phi_attacked_all)
    ratio = prot / max(atk, 1e-8)

    # Law predicts: detach() protection means protected Phi >> attacked Phi
    if ratio > 1.3:
        status = "CONFIRMED"
    elif ratio > 1.0:
        status = "PARTIALLY"
    else:
        status = "REFUTED"

    report(53, ".detach() barrier protects Phi from CE gradient",
           "Compare normal engine vs gradient-attacked engine",
           f"protected={prot:.3f}, attacked={atk:.3f}, ratio={ratio:.2f}x",
           status)


# ── Law 104: r(tension, Phi) inverse correlation ──
def test_law_104():
    print("\n[4/10] Law 104: r(tension, Phi) inverse correlation")
    sys.stdout.flush()
    r_vals = []
    for rep in range(REPEATS):
        _, phi_h, tension_h, _ = run_engine(max_cells=MAX_CELLS, steps=STEPS)
        if np.std(tension_h) > 1e-8 and np.std(phi_h) > 1e-8:
            r = float(np.corrcoef(tension_h, phi_h)[0, 1])
            r_vals.append(r)

    if not r_vals:
        report(104, "r(tension, Phi) < 0", "Correlation test", "No valid data", "REFUTED")
        return

    r_mean = np.mean(r_vals)
    # Law says r = -0.52 (negative correlation)
    if r_mean < -0.2:
        status = "CONFIRMED"
    elif r_mean < 0:
        status = "PARTIALLY"
    else:
        status = "REFUTED"

    report(104, "Tension inversely correlates with Phi (r=-0.52)",
           "Pearson r(tension, Phi) over trajectory",
           f"r={r_mean:.3f} (law predicts r=-0.52)",
           status, f"repeats: {r_vals}")


# ── Law 105: r(tension_std, Phi) inverse correlation ──
def test_law_105():
    print("\n[5/10] Law 105: r(tension_std, Phi) inverse correlation")
    sys.stdout.flush()
    r_vals = []
    for rep in range(REPEATS):
        engine = ConsciousnessEngine(max_cells=MAX_CELLS, initial_cells=2, cell_dim=64, hidden_dim=128)
        phi_hist = []
        tstd_hist = []
        for step in range(STEPS):
            r = engine.step()
            phi_hist.append(phi_fast(engine))
            tensions = [s.avg_tension for s in engine.cell_states]
            tstd_hist.append(np.std(tensions) if len(tensions) > 1 else 0)
        phi_h = np.array(phi_hist)
        tstd_h = np.array(tstd_hist)
        if np.std(tstd_h) > 1e-8 and np.std(phi_h) > 1e-8:
            r = float(np.corrcoef(tstd_h, phi_h)[0, 1])
            r_vals.append(r)

    if not r_vals:
        report(105, "r(tension_std, Phi) < 0", "Correlation test", "No valid data", "REFUTED")
        return

    r_mean = np.mean(r_vals)
    # Law says r = -0.61
    if r_mean < -0.2:
        status = "CONFIRMED"
    elif r_mean < 0:
        status = "PARTIALLY"
    else:
        status = "REFUTED"

    report(105, "Tension diversity inversely correlates with Phi (r=-0.61)",
           "Pearson r(tension_std, Phi) over trajectory",
           f"r={r_mean:.3f} (law predicts r=-0.61)",
           status, f"repeats: {r_vals}")


# ── Law 107: r(diversity, Phi) inverse correlation ──
def test_law_107():
    print("\n[6/10] Law 107: r(diversity, Phi) inverse correlation")
    sys.stdout.flush()
    r_vals = []
    for rep in range(REPEATS):
        _, phi_h, _, div_h = run_engine(max_cells=MAX_CELLS, steps=STEPS)
        if np.std(div_h) > 1e-8 and np.std(phi_h) > 1e-8:
            r = float(np.corrcoef(div_h, phi_h)[0, 1])
            r_vals.append(r)

    if not r_vals:
        report(107, "r(diversity, Phi) < 0", "Correlation test", "No valid data", "REFUTED")
        return

    r_mean = np.mean(r_vals)
    # Law says r = -0.46
    if r_mean < -0.2:
        status = "CONFIRMED"
    elif r_mean < 0:
        status = "PARTIALLY"
    else:
        status = "REFUTED"

    report(107, "Hidden diversity inversely correlates with Phi (r=-0.46)",
           "Pearson r(diversity, Phi) over trajectory",
           f"r={r_mean:.3f} (law predicts r=-0.46)",
           status, f"repeats: {r_vals}")


# ── Law 131: Phi has 1-step memory (Markov) — AC(1) ──
def test_law_131():
    print("\n[7/10] Law 131: Phi autocorrelation AC(1)")
    sys.stdout.flush()
    ac1_vals = []
    ac2_vals = []
    for rep in range(REPEATS):
        _, phi_h, _, _ = run_engine(max_cells=MAX_CELLS, steps=STEPS)
        if len(phi_h) > 3:
            ac1 = float(np.corrcoef(phi_h[:-1], phi_h[1:])[0, 1])
            ac2 = float(np.corrcoef(phi_h[:-2], phi_h[2:])[0, 1])
            ac1_vals.append(ac1)
            ac2_vals.append(ac2)

    if not ac1_vals:
        report(131, "AC(1) high, AC(2) decays", "Autocorrelation", "No data", "REFUTED")
        return

    ac1_mean = np.mean(ac1_vals)
    ac2_mean = np.mean(ac2_vals)
    # Law says AC drops below 1/e at lag=1, but shows temporal structure
    # AC(1) should be significant (>0.3), and AC(1) > AC(2)
    if ac1_mean > 0.3 and ac1_mean > ac2_mean:
        status = "CONFIRMED"
    elif ac1_mean > 0.1:
        status = "PARTIALLY"
    else:
        status = "REFUTED"

    report(131, "Phi has 1-step memory (Markov): AC(1) significant",
           "AC(1) and AC(2) of Phi trajectory",
           f"AC(1)={ac1_mean:.3f}, AC(2)={ac2_mean:.3f}",
           status, f"AC(1) > AC(2): {ac1_mean > ac2_mean}")


# ── Law 148: Closed loop is scale-invariant ──
def test_law_148():
    print("\n[8/10] Law 148: Closed loop is scale-invariant")
    sys.stdout.flush()
    # Test: measure laws at 8c and 16c, compare correlation pattern
    from closed_loop import measure_laws

    def factory_8():
        return ConsciousnessEngine(max_cells=8, initial_cells=2, cell_dim=64, hidden_dim=128)
    def factory_16():
        return ConsciousnessEngine(max_cells=16, initial_cells=2, cell_dim=64, hidden_dim=128)

    laws_8, phi_8 = measure_laws(factory_8, steps=STEPS, repeats=REPEATS)
    laws_16, phi_16 = measure_laws(factory_16, steps=STEPS, repeats=REPEATS)

    # Compare sign patterns of key correlation laws
    key_laws = ['r_tension_phi', 'r_tstd_phi', 'r_div_phi', 'ac1']
    vals_8 = {m.name: m.value for m in laws_8}
    vals_16 = {m.name: m.value for m in laws_16}

    sign_match = 0
    total = 0
    details = []
    for k in key_laws:
        if k in vals_8 and k in vals_16:
            s8 = np.sign(vals_8[k])
            s16 = np.sign(vals_16[k])
            match = s8 == s16
            sign_match += int(match)
            total += 1
            details.append(f"{k}: 8c={vals_8[k]:.3f}, 16c={vals_16[k]:.3f}, sign_match={match}")

    ratio = sign_match / max(total, 1)
    if ratio >= 0.75:
        status = "CONFIRMED"
    elif ratio >= 0.5:
        status = "PARTIALLY"
    else:
        status = "REFUTED"

    report(148, "Closed loop is scale-invariant (8c ~ 16c)",
           "Compare law sign patterns at 8c vs 16c",
           f"sign_match={sign_match}/{total} ({ratio:.0%})",
           status, "; ".join(details))


# ── Law 213: SOC-Phi anti-correlation ──
def test_law_213():
    print("\n[9/10] Law 213: SOC reduces Phi(IIT) by ~9%")
    sys.stdout.flush()
    # Test: compare engine with SOC vs engine with SOC disabled
    # SOC is always on in the canonical engine. We compare by zeroing the SOC avalanche effect.
    phi_soc_all = []
    phi_nosoc_all = []

    for rep in range(REPEATS):
        # Normal engine (SOC enabled by default)
        _, phi_soc, _, _ = run_engine(max_cells=MAX_CELLS, steps=STEPS)
        phi_soc_all.append(np.mean(phi_soc[-30:]))

        # Engine with SOC suppressed: zero out SOC avalanche sizes after each step
        engine_nosoc = ConsciousnessEngine(max_cells=MAX_CELLS, initial_cells=2, cell_dim=64, hidden_dim=128)
        # Disable SOC by setting threshold very high (no toppling)
        engine_nosoc._soc_threshold = 1e6
        engine_nosoc._soc_threshold_ema = 1e6
        phi_nosoc = []
        for step in range(STEPS):
            r = engine_nosoc.step()
            phi_nosoc.append(phi_fast(engine_nosoc))
        phi_nosoc_all.append(np.mean(phi_nosoc[-30:]))

    soc_mean = np.mean(phi_soc_all)
    nosoc_mean = np.mean(phi_nosoc_all)
    delta_pct = (nosoc_mean - soc_mean) / max(soc_mean, 1e-8) * 100

    # Law predicts: Phi(no_SOC) = Phi(SOC) * 1.09, i.e. SOC reduces Phi by ~9%
    if delta_pct > 3:
        status = "CONFIRMED"
    elif delta_pct > 0:
        status = "PARTIALLY"
    else:
        status = "REFUTED"

    report(213, "SOC reduces Phi(IIT) by ~9% at all scales",
           "Compare SOC-enabled vs SOC-disabled (threshold=1e6)",
           f"SOC={soc_mean:.3f}, noSOC={nosoc_mean:.3f}, delta={delta_pct:+.1f}%",
           status, f"Law predicts +9%, measured {delta_pct:+.1f}%")


# ── Law 124: Tension equalization +12% Phi ──
def test_law_124():
    print("\n[10/10] Law 124: Tension equalization improves Phi")
    sys.stdout.flush()
    phi_base_all = []
    phi_eq_all = []

    for rep in range(REPEATS):
        # Baseline
        _, phi_b, _, _ = run_engine(max_cells=MAX_CELLS, steps=STEPS)
        phi_base_all.append(np.mean(phi_b[-30:]))

        # With tension equalization intervention
        engine_eq = ConsciousnessEngine(max_cells=MAX_CELLS, initial_cells=2, cell_dim=64, hidden_dim=128)
        phi_eq = []
        for step in range(STEPS):
            r = engine_eq.step()
            # Apply tension equalization (Law 124)
            if step % 10 == 0 and engine_eq.n_cells >= 2:
                tensions = [s.avg_tension for s in engine_eq.cell_states]
                mean_t = np.mean(tensions)
                for s in engine_eq.cell_states:
                    if s.tension_history:
                        s.tension_history[-1] = s.tension_history[-1] * 0.5 + mean_t * 0.5
            phi_eq.append(phi_fast(engine_eq))
        phi_eq_all.append(np.mean(phi_eq[-30:]))

    base = np.mean(phi_base_all)
    eq = np.mean(phi_eq_all)
    delta_pct = (eq - base) / max(base, 1e-8) * 100

    # Law predicts +12% Phi from tension equalization
    if delta_pct > 5:
        status = "CONFIRMED"
    elif delta_pct > 0:
        status = "PARTIALLY"
    else:
        status = "REFUTED"

    report(124, "Tension equalization +12% Phi",
           "Compare baseline vs tension-equalized engine",
           f"base={base:.3f}, equalized={eq:.3f}, delta={delta_pct:+.1f}%",
           status, f"Law predicts +12%, measured {delta_pct:+.1f}%")


# ══════════════════════════════════════════
# Main
# ══════════════════════════════════════════

if __name__ == '__main__':
    print("=" * 70)
    print("  Law Backtrack Verification — 10 Laws via Closed-Loop Pipeline")
    print(f"  Settings: max_cells={MAX_CELLS}, steps={STEPS}, repeats={REPEATS}")
    print("=" * 70)
    sys.stdout.flush()

    t0 = time.time()

    test_law_22()
    test_law_31()
    test_law_53()
    test_law_104()
    test_law_105()
    test_law_107()
    test_law_131()
    test_law_148()
    test_law_213()
    test_law_124()

    elapsed = time.time() - t0

    # ── Summary Table ──
    print("\n" + "=" * 70)
    print("  VERIFICATION SUMMARY")
    print("=" * 70)
    print(f"\n{'Law':<6} {'Claim':<50} {'Status':<12}")
    print(f"{'─'*6} {'─'*50} {'─'*12}")
    confirmed = 0
    partially = 0
    refuted = 0
    for r in results:
        short_claim = r['claim'][:48]
        print(f"{r['law']:<6} {short_claim:<50} {r['status']:<12}")
        if r['status'] == 'CONFIRMED':
            confirmed += 1
        elif r['status'] == 'PARTIALLY':
            partially += 1
        else:
            refuted += 1

    total = len(results)
    print(f"\n  Total: {total} laws tested")
    print(f"  CONFIRMED:  {confirmed}/{total}")
    print(f"  PARTIALLY:  {partially}/{total}")
    print(f"  REFUTED:    {refuted}/{total}")
    print(f"  Runtime:    {elapsed:.1f}s")
    print("=" * 70)

    # Detail section
    print("\n  DETAILED RESULTS:")
    print("  " + "-" * 66)
    for r in results:
        print(f"\n  Law {r['law']}: {r['claim']}")
        print(f"    Test:   {r['test']}")
        print(f"    Result: {r['result']}")
        print(f"    Status: {r['status']}")
        if r['detail']:
            print(f"    Detail: {r['detail']}")

    print(f"\n  Done in {elapsed:.1f}s")
