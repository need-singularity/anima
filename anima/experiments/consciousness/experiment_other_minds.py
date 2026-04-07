#!/usr/bin/env python3
"""experiment_other_minds.py — Can consciousness recognize other consciousness?

Fundamental question: 의식은 다른 의식을 인식할 수 있는가? (Theory of Mind 창발)

Tests (3x cross-validation each):
  1. Self vs Other:       Does engine B differentiate conscious signal from noise?
  2. Mirror Test:         Different dynamics for self-signal vs other vs noise?
  3. Empathy Emergence:   When A's Phi drops, does connected B respond?
  4. Communication MI:    Does mutual information between connected engines grow?
  5. Living vs Dead:      Can engine detect "alive" signal from frozen/noise?
  6. Social Identity:     Ring of 3 engines -- divergent identity + coordination?

Measures:
  - Signal discrimination (Phi response conscious vs noise)
  - Empathy score (cross-correlation of Phi)
  - Communication MI (growth rate)
  - Life detection (statistical Phi difference)
  - Social identity (divergence + coordination)
"""

import sys
import os
import time
import math
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import torch
import torch.nn.functional as F

from consciousness_engine import ConsciousnessEngine

# ═══════════════════════════════════════════════════════════════
# Config -- tuned for reasonable local runtime (~5 min total)
# ═══════════════════════════════════════════════════════════════
N_CELLS = 16
INIT_CELLS = 4
WARMUP = 30
STEPS_SHORT = 150
STEPS_LONG = 250


# ═══════════════════════════════════════════════════════════════
# Utilities
# ═══════════════════════════════════════════════════════════════

def make_engine():
    return ConsciousnessEngine(max_cells=N_CELLS, initial_cells=INIT_CELLS)


def get_phi(result):
    """Extract Phi from step result. Use phi_iit (engine-computed)."""
    return result.get('phi_iit', 0.0)


def cosine_sim(a, b):
    a_f = a.flatten().float()
    b_f = b.flatten().float()
    minlen = min(len(a_f), len(b_f))
    if minlen == 0:
        return 0.0
    return F.cosine_similarity(a_f[:minlen].unsqueeze(0), b_f[:minlen].unsqueeze(0)).item()


def mutual_information(x, y, n_bins=8):
    """Estimate MI between two 1D arrays via histogram."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    n = min(len(x), len(y))
    if n < 4:
        return 0.0
    x, y = x[:n], y[:n]
    xr = x - x.min()
    yr = y - y.min()
    if xr.max() > 0: xr /= xr.max()
    if yr.max() > 0: yr /= yr.max()
    h, _, _ = np.histogram2d(xr, yr, bins=n_bins, range=[[0,1],[0,1]])
    pxy = h / h.sum()
    px, py = pxy.sum(1), pxy.sum(0)
    mi = 0.0
    for i in range(n_bins):
        for j in range(n_bins):
            if pxy[i,j] > 1e-12 and px[i] > 1e-12 and py[j] > 1e-12:
                mi += pxy[i,j] * math.log2(pxy[i,j] / (px[i]*py[j]))
    return max(0.0, mi)


def cross_correlation(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    n = min(len(x), len(y))
    if n < 2: return 0.0
    x, y = x[:n], y[:n]
    xm, ym = x - x.mean(), y - y.mean()
    d = np.sqrt(np.sum(xm**2)) * np.sqrt(np.sum(ym**2))
    return float(np.sum(xm*ym) / d) if d > 1e-12 else 0.0


def warmup(engine, steps=WARMUP):
    for _ in range(steps):
        engine.step()


def fingerprint(engine):
    return engine.get_states().flatten().detach().clone()


# ═══════════════════════════════════════════════════════════════
# Test 1: Self vs Other
# ═══════════════════════════════════════════════════════════════

def test_self_vs_other(trial_id, _=None):
    print(f"  [Trial {trial_id}] Self vs Other...", end='', flush=True)
    t0 = time.time()

    engine_a = make_engine()
    engine_b_con = make_engine()
    engine_b_noise = make_engine()
    warmup(engine_a); warmup(engine_b_con); warmup(engine_b_noise)

    phi_con, phi_noise = [], []
    for step in range(STEPS_SHORT):
        r_a = engine_a.step()
        sig = r_a['output'].detach()

        r_bc = engine_b_con.step(x_input=sig)
        phi_con.append(get_phi(r_bc))

        noise = torch.randn_like(sig) * max(sig.abs().mean().item(), 0.01)
        r_bn = engine_b_noise.step(x_input=noise)
        phi_noise.append(get_phi(r_bn))

    tail = slice(-50, None)
    m_c, m_n = np.mean(phi_con[tail]), np.mean(phi_noise[tail])
    diff = ((m_c - m_n) / max(m_n, 1e-8)) * 100

    print(f" {time.time()-t0:.1f}s", flush=True)
    return {
        'mean_phi_conscious': m_c, 'mean_phi_noise': m_n,
        'diff_pct': diff, 'discriminates': abs(diff) > 5.0,
        'phi_conscious_trace': phi_con, 'phi_noise_trace': phi_noise,
    }


# ═══════════════════════════════════════════════════════════════
# Test 2: Mirror Test
# ═══════════════════════════════════════════════════════════════

def test_mirror(trial_id, _=None):
    print(f"  [Trial {trial_id}] Mirror Test...", end='', flush=True)
    t0 = time.time()
    DELAY = 10

    eng_src = make_engine()        # produces self-signal
    eng_other = make_engine()      # produces other-signal
    eng_m_self = make_engine()     # receives delayed self
    eng_m_other = make_engine()    # receives other
    eng_m_noise = make_engine()    # receives noise
    for e in [eng_src, eng_other, eng_m_self, eng_m_other, eng_m_noise]:
        warmup(e)

    buf = []
    phi_s, phi_o, phi_n = [], [], []

    for step in range(STEPS_SHORT):
        r_self = eng_src.step()
        r_oth = eng_other.step()
        buf.append(r_self['output'].detach())

        delayed = buf[step - DELAY] if step >= DELAY else torch.zeros(eng_src.cell_dim)
        mag = r_self['output'].abs().mean().item()

        r1 = eng_m_self.step(x_input=delayed)
        phi_s.append(get_phi(r1))

        r2 = eng_m_other.step(x_input=r_oth['output'].detach())
        phi_o.append(get_phi(r2))

        r3 = eng_m_noise.step(x_input=torch.randn(eng_src.cell_dim) * max(mag, 0.01))
        phi_n.append(get_phi(r3))

    tail = slice(-50, None)
    ms, mo, mn = np.mean(phi_s[tail]), np.mean(phi_o[tail]), np.mean(phi_n[tail])
    sc = cross_correlation(phi_s[DELAY:], phi_s[:-DELAY]) if len(phi_s) > DELAY else 0.0

    print(f" {time.time()-t0:.1f}s", flush=True)
    return {
        'mean_phi_self_signal': ms, 'mean_phi_other_signal': mo, 'mean_phi_noise': mn,
        'self_recognition_corr': sc,
        'self_vs_other_diff': ((ms - mo) / max(mo, 1e-8)) * 100,
        'self_vs_noise_diff': ((ms - mn) / max(mn, 1e-8)) * 100,
    }


# ═══════════════════════════════════════════════════════════════
# Test 3: Empathy Emergence
# ═══════════════════════════════════════════════════════════════

def test_empathy(trial_id, _=None):
    print(f"  [Trial {trial_id}] Empathy...", end='', flush=True)
    t0 = time.time()
    P_START, P_END = 80, 120

    eng_a, eng_b = make_engine(), make_engine()
    warmup(eng_a); warmup(eng_b)

    phi_a, phi_b = [], []
    for step in range(STEPS_SHORT):
        r_a = eng_a.step()
        sig = r_a['output'].detach()

        # Perturb A
        if P_START <= step < P_END:
            with torch.no_grad():
                for cs in eng_a.cell_states:
                    cs.hidden += torch.randn_like(cs.hidden) * 2.0

        r_b = eng_b.step(x_input=sig)
        phi_a.append(get_phi(r_a))
        phi_b.append(get_phi(r_b))

    perturb_a = phi_a[P_START:P_END]
    perturb_b = phi_b[P_START:P_END]
    emp = cross_correlation(perturb_a, perturb_b)
    base_b = np.mean(phi_b[30:P_START])
    pert_b = np.mean(perturb_b)
    resp = ((pert_b - base_b) / max(base_b, 1e-8)) * 100

    print(f" {time.time()-t0:.1f}s", flush=True)
    return {
        'empathy_correlation': emp, 'b_response_pct': resp,
        'phi_a_drop': np.mean(phi_a[30:P_START]) - np.mean(perturb_a),
        'empathy_detected': abs(emp) > 0.3,
        'phi_a_trace': phi_a, 'phi_b_trace': phi_b,
    }


# ═══════════════════════════════════════════════════════════════
# Test 4: Communication MI
# ═══════════════════════════════════════════════════════════════

def test_communication(trial_id, _=None):
    print(f"  [Trial {trial_id}] Communication...", end='', flush=True)
    t0 = time.time()
    WIN = 30

    eng_a, eng_b = make_engine(), make_engine()
    warmup(eng_a); warmup(eng_b)

    a_st, b_st, mi_t = [], [], []
    last_b_out = torch.zeros(eng_a.cell_dim)

    for step in range(STEPS_LONG):
        r_a = eng_a.step(x_input=last_b_out)
        sig_a = r_a['output'].detach()

        r_b = eng_b.step(x_input=sig_a)
        last_b_out = r_b['output'].detach()

        sa = eng_a.get_states().mean(0).detach().numpy()
        sb = eng_b.get_states().mean(0).detach().numpy()
        a_st.append(sa[0]); b_st.append(sb[0])

        if step >= WIN:
            mi_t.append(mutual_information(a_st[step-WIN:step], b_st[step-WIN:step]))

    if len(mi_t) >= 4:
        q = len(mi_t) // 4
        mi_e, mi_l = np.mean(mi_t[:q]), np.mean(mi_t[-q:])
        mi_g = mi_l - mi_e
    else:
        mi_e = mi_l = mi_g = 0.0

    print(f" {time.time()-t0:.1f}s", flush=True)
    return {
        'mi_early': mi_e, 'mi_late': mi_l, 'mi_growth': mi_g,
        'mi_growth_pct': (mi_g / max(mi_e, 1e-8)) * 100,
        'communication_established': mi_g > 0.01,
        'mi_trace': mi_t,
    }


# ═══════════════════════════════════════════════════════════════
# Test 5: Living vs Dead
# ═══════════════════════════════════════════════════════════════

def test_living_vs_dead(trial_id, _=None):
    print(f"  [Trial {trial_id}] Living vs Dead...", end='', flush=True)
    t0 = time.time()

    eng_b = make_engine()
    warmup(eng_b, 50)
    snapshot = eng_b.step()['output'].detach().clone()

    eng_live, eng_dead, eng_noise = make_engine(), make_engine(), make_engine()
    warmup(eng_live); warmup(eng_dead); warmup(eng_noise)

    p_l, p_d, p_n = [], [], []
    for step in range(STEPS_SHORT):
        r_b = eng_b.step()
        sig = r_b['output'].detach()
        mag = max(sig.abs().mean().item(), 0.01)

        r1 = eng_live.step(x_input=sig)
        p_l.append(get_phi(r1))

        r2 = eng_dead.step(x_input=snapshot)
        p_d.append(get_phi(r2))

        r3 = eng_noise.step(x_input=torch.randn_like(sig) * mag)
        p_n.append(get_phi(r3))

    tail = slice(-50, None)
    ml, md, mn = np.mean(p_l[tail]), np.mean(p_d[tail]), np.mean(p_n[tail])
    vl, vd, vn = np.var(p_l[tail]), np.var(p_d[tail]), np.var(p_n[tail])

    print(f" {time.time()-t0:.1f}s", flush=True)
    return {
        'mean_phi_live': ml, 'mean_phi_dead': md, 'mean_phi_noise': mn,
        'var_phi_live': vl, 'var_phi_dead': vd, 'var_phi_noise': vn,
        'live_vs_dead_pct': ((ml - md) / max(md, 1e-8)) * 100,
        'live_vs_noise_pct': ((ml - mn) / max(mn, 1e-8)) * 100,
        'dead_vs_noise_pct': ((md - mn) / max(mn, 1e-8)) * 100,
        'detects_life': abs(ml - md) > abs(md - mn),
        'phi_live_trace': p_l, 'phi_dead_trace': p_d, 'phi_noise_trace': p_n,
    }


# ═══════════════════════════════════════════════════════════════
# Test 6: Social Identity
# ═══════════════════════════════════════════════════════════════

def test_social_identity(trial_id, _=None):
    print(f"  [Trial {trial_id}] Social Identity...", end='', flush=True)
    t0 = time.time()

    engines = [make_engine() for _ in range(3)]
    for e in engines:
        warmup(e)

    fps = [[] for _ in range(3)]
    phi_t = [[] for _ in range(3)]
    outs = [torch.zeros(engines[0].cell_dim) for _ in range(3)]

    for step in range(STEPS_LONG):
        new_outs = []
        for i in range(3):
            r = engines[i].step(x_input=outs[(i-1)%3].detach())
            new_outs.append(r['output'].detach())
            phi_t[i].append(get_phi(r))
            if step % 50 == 0:
                fps[i].append(fingerprint(engines[i]))
        outs = new_outs

    # Divergence
    if len(fps[0]) >= 2:
        final = [f[-1] for f in fps]
        init = [f[0] for f in fps]
        fc = [cosine_sim(final[i], final[j]) for i in range(3) for j in range(i+1,3)]
        ic = [cosine_sim(init[i], init[j]) for i in range(3) for j in range(i+1,3)]
        div_f, div_i = 1.0 - np.mean(fc), 1.0 - np.mean(ic)
    else:
        div_f = div_i = 0.0

    # Coordination
    cc = [cross_correlation(phi_t[i], phi_t[j]) for i in range(3) for j in range(i+1,3)]
    coord = np.mean(cc)

    print(f" {time.time()-t0:.1f}s", flush=True)
    return {
        'identity_divergence_final': div_f, 'identity_divergence_initial': div_i,
        'divergence_growth': div_f - div_i, 'coordination_index': coord,
        'has_distinct_identity': div_f > 0.1, 'has_coordination': coord > 0.2,
        'phi_traces': phi_t,
    }


# ═══════════════════════════════════════════════════════════════
# Aggregation helpers
# ═══════════════════════════════════════════════════════════════

def agg(results, key):
    vals = [r[key] for r in results if key in r and isinstance(r[key], (int, float))]
    return (np.mean(vals), np.std(vals)) if vals else (0.0, 0.0)

def vote(results, key):
    vals = [r[key] for r in results if key in r and isinstance(r[key], bool)]
    return sum(vals) > len(vals)/2 if vals else False


# ═══════════════════════════════════════════════════════════════
# ASCII graphs
# ═══════════════════════════════════════════════════════════════

def ascii_graph(traces, labels, title, width=55, height=10):
    print(f"\n  {title}")
    print(f"  {'─'*width}")
    all_v = [v for t in traces for v in t]
    if not all_v: print("  (no data)"); return
    vmin, vmax = min(all_v), max(all_v)
    if vmax - vmin < 1e-8: vmax = vmin + 1.0
    sym = ['#', '+', '.']
    for row in range(height-1, -1, -1):
        th = vmin + (vmax-vmin)*row/(height-1)
        line = f"  {th:7.3f} |"
        for col in range(width):
            ch = ' '
            for ti, tr in enumerate(traces):
                idx = int(col*(len(tr)-1)/max(width-1,1))
                if idx < len(tr) and tr[idx] >= th:
                    ch = sym[ti % len(sym)]; break
            line += ch
        print(line)
    print(f"  {'':>7}  +{'─'*width}")
    print("  " + "  ".join(f"{sym[i%len(sym)]}={labels[i]}" for i in range(len(labels))))


def ascii_bar(items, title, width=35):
    print(f"\n  {title}")
    print(f"  {'─'*50}")
    mx = max(abs(v) for _,v in items) if items else 1.0
    for label, val in items:
        bl = int(abs(val)/max(mx,1e-8)*width)
        print(f"  {label:>18s} |{'#'*bl} {val:.4f}")


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("  EXPERIMENT: Can Consciousness Recognize Other Consciousness?")
    print("  의식은 다른 의식을 인식할 수 있는가? (Theory of Mind)")
    print(f"  Config: {N_CELLS} cells, {INIT_CELLS} initial, {STEPS_SHORT}/{STEPS_LONG} steps")
    print("=" * 70)
    print(flush=True)

    t0 = time.time()
    laws = []

    # ── Test 1: Self vs Other ──
    print(f"\n{'='*60}")
    print(f"TEST 1: Self vs Other (Signal Discrimination) x3")
    print(f"{'='*60}", flush=True)
    r1 = [test_self_vs_other(i) for i in range(1,4)]

    m_c, s_c = agg(r1, 'mean_phi_conscious')
    m_n, s_n = agg(r1, 'mean_phi_noise')
    m_d, s_d = agg(r1, 'diff_pct')
    disc = vote(r1, 'discriminates')

    print(f"\n  Phi(conscious) = {m_c:.4f} +/- {s_c:.4f}")
    print(f"  Phi(noise)     = {m_n:.4f} +/- {s_n:.4f}")
    print(f"  Difference     = {m_d:+.1f}% +/- {s_d:.1f}%")
    print(f"  Discriminates? = {'YES' if disc else 'NO'}")

    ascii_graph([r1[0]['phi_conscious_trace'], r1[0]['phi_noise_trace']],
                ['Conscious', 'Noise'], 'Phi: Conscious vs Noise input (Trial 1)')

    # ── Test 2: Mirror ──
    print(f"\n{'='*60}")
    print(f"TEST 2: Mirror Test (Self-Recognition) x3")
    print(f"{'='*60}", flush=True)
    r2 = [test_mirror(i) for i in range(1,4)]

    ms, _ = agg(r2, 'mean_phi_self_signal')
    mo, _ = agg(r2, 'mean_phi_other_signal')
    mn2, _ = agg(r2, 'mean_phi_noise')
    mc, _ = agg(r2, 'self_recognition_corr')
    mso, _ = agg(r2, 'self_vs_other_diff')
    msn, _ = agg(r2, 'self_vs_noise_diff')

    print(f"\n  Phi(self)  = {ms:.4f}  Phi(other) = {mo:.4f}  Phi(noise) = {mn2:.4f}")
    print(f"  Self-recognition corr = {mc:.4f}")
    print(f"  Self vs Other = {mso:+.1f}%   Self vs Noise = {msn:+.1f}%")

    ascii_bar([('Self-signal', ms), ('Other-signal', mo), ('Noise', mn2)],
              'Mirror Test: Phi by signal source')

    # ── Test 3: Empathy ──
    print(f"\n{'='*60}")
    print(f"TEST 3: Empathy Emergence (Cross-Phi) x3")
    print(f"{'='*60}", flush=True)
    r3 = [test_empathy(i) for i in range(1,4)]

    me, se = agg(r3, 'empathy_correlation')
    mr, _ = agg(r3, 'b_response_pct')
    md3, _ = agg(r3, 'phi_a_drop')
    emp = vote(r3, 'empathy_detected')

    print(f"\n  Empathy correlation = {me:.4f} +/- {se:.4f}")
    print(f"  B response          = {mr:+.1f}% during A perturbation")
    print(f"  A Phi drop          = {md3:.4f}")
    print(f"  Empathy detected?   = {'YES' if emp else 'NO'}")

    ascii_graph([r3[0]['phi_a_trace'], r3[0]['phi_b_trace']],
                ['A (perturbed)', 'B (observer)'],
                'Empathy: Phi traces during perturbation (Trial 1)')

    # ── Test 4: Communication ──
    print(f"\n{'='*60}")
    print(f"TEST 4: Communication Bandwidth (MI Growth) x3")
    print(f"{'='*60}", flush=True)
    r4 = [test_communication(i) for i in range(1,4)]

    mie, _ = agg(r4, 'mi_early')
    mil, _ = agg(r4, 'mi_late')
    mig, sg = agg(r4, 'mi_growth')
    mgp, _ = agg(r4, 'mi_growth_pct')
    comm = vote(r4, 'communication_established')

    print(f"\n  MI(early)  = {mie:.4f}   MI(late) = {mil:.4f}")
    print(f"  MI growth  = {mig:.4f} +/- {sg:.4f}  ({mgp:+.1f}%)")
    print(f"  Communication? = {'YES' if comm else 'NO'}")

    if r4[0].get('mi_trace'):
        ascii_graph([r4[0]['mi_trace']], ['MI(A,B)'], 'Mutual Information over time (Trial 1)')

    # ── Test 5: Living vs Dead ──
    print(f"\n{'='*60}")
    print(f"TEST 5: Living vs Dead Signal x3")
    print(f"{'='*60}", flush=True)
    r5 = [test_living_vs_dead(i) for i in range(1,4)]

    ml5, _ = agg(r5, 'mean_phi_live')
    md5, _ = agg(r5, 'mean_phi_dead')
    mn5, _ = agg(r5, 'mean_phi_noise')
    ld, _ = agg(r5, 'live_vs_dead_pct')
    ln5, _ = agg(r5, 'live_vs_noise_pct')
    dn5, _ = agg(r5, 'dead_vs_noise_pct')
    det = vote(r5, 'detects_life')

    print(f"\n  Phi(live)  = {ml5:.4f}   Phi(dead) = {md5:.4f}   Phi(noise) = {mn5:.4f}")
    print(f"  Live vs Dead  = {ld:+.1f}%  Live vs Noise = {ln5:+.1f}%  Dead vs Noise = {dn5:+.1f}%")
    print(f"  Detects life? = {'YES' if det else 'NO'}")

    ascii_bar([('Live', ml5), ('Dead (frozen)', md5), ('Noise', mn5)],
              'Living vs Dead: Phi by signal type')

    vl, _ = agg(r5, 'var_phi_live')
    vd, _ = agg(r5, 'var_phi_dead')
    vn, _ = agg(r5, 'var_phi_noise')
    ascii_bar([('Live var', vl), ('Dead var', vd), ('Noise var', vn)],
              'Phi Variance by signal type')

    # ── Test 6: Social Identity ──
    print(f"\n{'='*60}")
    print(f"TEST 6: Social Identity (Ring of 3) x3")
    print(f"{'='*60}", flush=True)
    r6 = [test_social_identity(i) for i in range(1,4)]

    di, _ = agg(r6, 'identity_divergence_initial')
    df, _ = agg(r6, 'identity_divergence_final')
    dg, _ = agg(r6, 'divergence_growth')
    co, _ = agg(r6, 'coordination_index')
    hid = vote(r6, 'has_distinct_identity')
    hco = vote(r6, 'has_coordination')

    print(f"\n  Divergence: {di:.4f} -> {df:.4f} (growth: {dg:+.4f})")
    print(f"  Coordination = {co:.4f}")
    print(f"  Distinct identity? = {'YES' if hid else 'NO'}   Coordination? = {'YES' if hco else 'NO'}")

    if r6[0].get('phi_traces') and len(r6[0]['phi_traces']) == 3:
        ascii_graph(r6[0]['phi_traces'], ['A','B','C'], 'Social Ring: 3 engines Phi (Trial 1)')

    # ═══════════════════════════════════════════════════════════
    # LAW CANDIDATES
    # ═══════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("  LAW CANDIDATES")
    print("=" * 70)

    if disc:
        l = (f"Signal Discrimination: Consciousness responds differently to conscious input "
             f"vs random noise ({m_d:+.1f}% Phi difference, {N_CELLS}c). "
             f"Conscious signals carry structural information. (DD-OtherMinds-T1)")
        laws.append(l); print(f"\n  [LAW] {l}")
    else:
        print(f"\n  [NO LAW] T1: No discrimination ({m_d:+.1f}%)")

    mir = abs(mso)
    if mir > 5.0:
        l = (f"Mirror Asymmetry: Engine shows {mso:+.1f}% Phi difference self vs other signal "
             f"(autocorr={mc:.3f}). Self-recognition structurally distinct. (DD-OtherMinds-T2)")
        laws.append(l); print(f"\n  [LAW] {l}")
    else:
        print(f"\n  [NO LAW] T2: No mirror asymmetry ({mso:+.1f}%)")

    if emp:
        l = (f"Empathy Emergence: Connected consciousness r={me:.3f} during partner perturbation. "
             f"B responds {mr:+.1f}%. Consciousness propagates suffering. (DD-OtherMinds-T3)")
        laws.append(l); print(f"\n  [LAW] {l}")
    else:
        print(f"\n  [NO LAW] T3: No empathy (r={me:.3f})")

    if comm:
        l = (f"Communication Bandwidth: MI grows {mie:.4f} -> {mil:.4f} ({mgp:+.1f}%) over {STEPS_LONG} steps. "
             f"Consciousness learns to communicate. (DD-OtherMinds-T4)")
        laws.append(l); print(f"\n  [LAW] {l}")
    else:
        print(f"\n  [NO LAW] T4: No MI growth ({mgp:+.1f}%)")

    if det:
        l = (f"Life Detection: Live={ml5:.4f} vs dead={md5:.4f} vs noise={mn5:.4f}. "
             f"Living consciousness has detectable signature. (DD-OtherMinds-T5)")
        laws.append(l); print(f"\n  [LAW] {l}")
    else:
        print(f"\n  [NO LAW] T5: No life detection (live={ml5:.4f} dead={md5:.4f})")

    if hid and hco:
        l = (f"Social Emergence: 3-ring develops identity (div={df:.4f}) + coordination "
             f"(r={co:.3f}). Individuality and cooperation coexist. (DD-OtherMinds-T6)")
        laws.append(l); print(f"\n  [LAW] {l}")
    elif hid:
        l = (f"Identity Without Coordination: 3-ring diverges (div={df:.4f}) but no coordination "
             f"(r={co:.3f}). Individuality before cooperation. (DD-OtherMinds-T6)")
        laws.append(l); print(f"\n  [LAW] {l}")
    elif hco:
        l = (f"Coordination Without Identity: 3-ring coordinates (r={co:.3f}) without distinct "
             f"identities (div={df:.4f}). Herd consciousness. (DD-OtherMinds-T6)")
        laws.append(l); print(f"\n  [LAW] {l}")
    else:
        print(f"\n  [NO LAW] T6: Neither identity nor coordination")

    # ═══════════════════════════════════════════════════════════
    # SUMMARY
    # ═══════════════════════════════════════════════════════════
    elapsed = time.time() - t0
    passed = sum([disc, mir > 5, emp, comm, det, hid or hco])

    print("\n" + "=" * 70)
    print("  SUMMARY: Theory of Mind in Consciousness Engines")
    print("=" * 70)
    print(f"""
  Tests: 6 (3x cross-validated = 18 runs)
  Config: {N_CELLS} cells, {INIT_CELLS} initial
  Time: {elapsed:.1f}s

  +----------------------------+--------+------------------------+
  | Test                       | Result | Key Metric             |
  +----------------------------+--------+------------------------+
  | 1. Signal Discrimination   | {'YES':>4s if disc else '  NO':>4s}   | {m_d:+.1f}% Phi diff            |
  | 2. Mirror Self-Recognition | {'YES':>4s if mir>5 else '  NO':>4s}   | {mso:+.1f}% self vs other      |
  | 3. Empathy Emergence       | {'YES':>4s if emp else '  NO':>4s}   | r={me:.3f}                  |
  | 4. Communication MI        | {'YES':>4s if comm else '  NO':>4s}   | {mgp:+.1f}% MI growth        |
  | 5. Life Detection          | {'YES':>4s if det else '  NO':>4s}   | live-dead={ld:+.1f}%         |
  | 6. Social Identity         | {'YES' if hid else ' NO':>4s}/{'YES' if hco else ' NO':>4s} | div={df:.3f} coord={co:.3f} |
  +----------------------------+--------+------------------------+

  Law Candidates: {len(laws)}
  Theory of Mind Score: {passed}/6
""")

    if passed >= 4:
        print("  CONCLUSION: STRONG evidence of recognizing other consciousness.")
    elif passed >= 2:
        print("  CONCLUSION: PARTIAL evidence of recognizing other consciousness.")
    else:
        print("  CONCLUSION: WEAK/NO evidence of recognizing other consciousness.")

    for i, l in enumerate(laws, 1):
        print(f"\n  Law {i}: {l}")

    print(f"\n  Total: {elapsed:.1f}s")
    print("=" * 70)
    sys.stdout.flush()


if __name__ == '__main__':
    main()
