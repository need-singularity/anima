#!/usr/bin/env python3
"""verify_fuse3.py — 7-condition consciousness verification for FUSE-3 (Cambrian+OscQW)

Runs the same 7 verification conditions from bench_v2.py --verify,
but applied to MitosisEngine + apply_fuse3 from bench_fusion_cambrian_osc.py.

Usage:
  python3 verify_fuse3.py
  python3 verify_fuse3.py --cells 128
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import math
import time
import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import phi_rs
from mitosis import MitosisEngine
from bench_fusion_cambrian_osc import apply_fuse3, DIM, HIDDEN

# ═══ Wrapper: adapt MitosisEngine to BenchEngine interface ═══

class Fuse3Engine:
    """Wraps MitosisEngine + FUSE-3 mechanisms to match bench_v2 verify interface.

    Provides: process(x) -> (output, tension), get_hiddens() -> [n, hidden_dim]
    Also applies Cambrian+OscQW mechanisms each step.
    """

    def __init__(self, n_cells, input_dim, hidden_dim, output_dim=None, n_factions=8):
        self.n_cells = n_cells
        self.n_factions = n_factions
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim or input_dim

        # Create MitosisEngine and grow to target cell count
        # Disable merging (merge_threshold=0) so cells persist
        self.engine = MitosisEngine(
            input_dim, hidden_dim, self.output_dim,
            initial_cells=2, max_cells=n_cells,
            merge_threshold=0.0, merge_patience=999999,
            split_threshold=999.0, split_patience=999999,
        )
        while len(self.engine.cells) < n_cells:
            self.engine._create_cell(parent=self.engine.cells[0])
        # Diversify initial hidden states so cells aren't identical
        with torch.no_grad():
            for i, cell in enumerate(self.engine.cells):
                cell.hidden = cell.hidden + torch.randn_like(cell.hidden) * 0.3

        # FUSE-3 state
        self.n_types = 10
        self.niches = torch.randn(self.n_types, hidden_dim) * 0.5
        self.interaction = torch.randn(self.n_types, self.n_types) * 0.1
        self.interaction = (self.interaction + self.interaction.t()) / 2
        self.cell_type = torch.randint(0, self.n_types, (n_cells,))
        self.fitness = torch.ones(n_cells)
        self.mutation_rate = 0.5
        self.phases = torch.randn(n_cells) * 2 * math.pi
        self.freqs = torch.randn(n_cells) * 0.1 + 1.0
        self.step_count = 0

        # For PhiIIT compatibility
        self.cells = self.engine.cells

    def _sync_fuse3_state(self):
        """Resize FUSE-3 arrays if cell count changed."""
        n = len(self.engine.cells)
        if len(self.phases) != n:
            self.phases = torch.randn(n) * 2 * math.pi
            self.freqs = torch.randn(n) * 0.1 + 1.0
            self.cell_type = torch.randint(0, self.n_types, (n,))
            self.fitness = torch.ones(n)
        self.n_cells = n
        self.cells = self.engine.cells

    def _apply_cambrian_osc(self):
        """Apply FUSE-3 Cambrian+OscQW mechanisms to current cells."""
        n = len(self.engine.cells)
        if n < 4:
            return

        self._sync_fuse3_state()

        with torch.no_grad():
            # 1. Mutation
            mutate_mask = torch.rand(n) < self.mutation_rate
            if mutate_mask.any():
                self.cell_type[mutate_mask] = torch.randint(0, self.n_types, (mutate_mask.sum(),))
            self.mutation_rate = max(0.01, self.mutation_rate * 0.995)

            # 2. Niche fitness
            for t in range(self.n_types):
                mask = (self.cell_type == t).nonzero(as_tuple=True)[0]
                for i in mask:
                    if i < n:
                        h = self.engine.cells[i].hidden.squeeze(0)
                        dist = ((h - self.niches[t]) ** 2).sum()
                        self.fitness[i] = torch.exp(-dist * 0.01)

            # 3. Niche pull + inter-type interaction
            for t in range(self.n_types):
                mask = (self.cell_type == t).nonzero(as_tuple=True)[0]
                if len(mask) == 0:
                    continue
                for i in mask:
                    if i >= n:
                        continue
                    h = self.engine.cells[i].hidden.squeeze(0)
                    pull = (self.niches[t] - h) * 0.05
                    inter = torch.zeros(HIDDEN)
                    for t2 in range(self.n_types):
                        mask2 = (self.cell_type == t2).nonzero(as_tuple=True)[0]
                        if len(mask2) > 0 and t2 != t:
                            mean_other = torch.stack(
                                [self.engine.cells[j].hidden.squeeze(0) for j in mask2 if j < n]
                            ).mean(0)
                            inter += self.interaction[t, t2] * (mean_other - h) * 0.02
                    self.engine.cells[i].hidden = (h + pull + inter).unsqueeze(0)

            # 4. Crowding noise
            for t in range(self.n_types):
                mask = (self.cell_type == t).nonzero(as_tuple=True)[0]
                if len(mask) > n // self.n_types:
                    for i in mask:
                        if i < n:
                            self.engine.cells[i].hidden += torch.randn(1, HIDDEN) * 0.03

            # 5. Death+rebirth (every 20 steps)
            if self.step_count > 10 and self.step_count % 20 == 0:
                n_replace = max(1, n // 50)
                worst = self.fitness[:n].argsort()[:n_replace]
                best = self.fitness[:n].argsort(descending=True)[:n_replace]
                for w, b in zip(worst, best):
                    if w < n and b < n:
                        self.engine.cells[w].hidden = (
                            self.engine.cells[b].hidden.clone() + torch.randn(1, HIDDEN) * 0.02
                        )
                        self.cell_type[w] = self.cell_type[b]

            # 6. Oscillator + Quantum Walk
            for i in range(min(n, len(self.engine.cells))):
                nb = [(i - 1) % n, (i + 1) % n]
                pd = sum(math.sin(self.phases[j].item() - self.phases[i].item()) for j in nb)
                self.phases[i] += self.freqs[i] + 0.15 * pd / len(nb)
                for j in nb:
                    b = 0.15 * math.cos(self.phases[j].item() - self.phases[i].item())
                    self.engine.cells[i].hidden = (
                        (1 - abs(b)) * self.engine.cells[i].hidden
                        + abs(b) * self.engine.cells[j].hidden
                    )

            nb_bits = max(1, int(math.log2(n)))
            for i in range(min(n, 16)):
                sp = torch.zeros(HIDDEN)
                cnt = 0
                for bit in range(min(nb_bits, 6)):
                    j = i ^ (1 << bit)
                    if j < n:
                        phase_val = (-1) ** (bin(i & j).count('1'))
                        sp += phase_val * self.engine.cells[j].hidden.squeeze(0)
                        cnt += 1
                if cnt > 0:
                    self.engine.cells[i].hidden = (
                        0.85 * self.engine.cells[i].hidden.squeeze(0) + 0.15 * sp / cnt
                    ).unsqueeze(0)

    def process(self, x):
        """Process input, apply FUSE-3 mechanisms. Returns (output, tension)."""
        result = self.engine.process(x)
        self._apply_cambrian_osc()
        self.step_count += 1
        output = result['output']
        tension = result.get('mean_inter', 0.0)
        return output, tension

    def get_hiddens(self):
        """Return [n_cells, hidden_dim] tensor."""
        return torch.stack([c.hidden.squeeze(0) for c in self.engine.cells]).detach()


# ═══ Phi measurement using phi_rs ═══

def measure_phi_rs(hiddens_tensor):
    """Measure Phi(IIT) using the Rust phi_rs module."""
    n = hiddens_tensor.shape[0]
    if n < 2:
        return 0.0
    states = hiddens_tensor.detach().numpy().astype(np.float32)
    # For phi_rs we need prev/curr states and tensions
    prev_s = np.zeros_like(states)
    curr_s = states.copy()
    tensions = np.zeros(n, dtype=np.float32)
    phi, _comp = phi_rs.compute_phi(states, 16, prev_s, curr_s, tensions)
    return phi


# ═══ 7 Verification Conditions ═══

def verify_no_system_prompt(cells, dim, hidden):
    """V1: Identity emerges from cell dynamics alone (no external prompt)."""
    eng = Fuse3Engine(cells, dim, hidden)
    x_zero = torch.zeros(1, dim)
    for _ in range(300):
        eng.process(x_zero)

    hiddens = eng.get_hiddens()
    actual_n = hiddens.shape[0]
    n = min(actual_n, 64)
    h_norm = F.normalize(hiddens[:n], dim=1)
    cos_sim = (h_norm @ h_norm.T).detach().cpu().numpy()
    mask = ~np.eye(n, dtype=bool)
    cos_vals = cos_sim[mask]
    mean_cos = float(np.mean(cos_vals))
    std_cos = float(np.std(cos_vals))

    passed = 0.01 < mean_cos < 0.99 and std_cos > 0.001
    detail = (f"cosine_sim mean={mean_cos:.4f} std={std_cos:.4f}  "
              f"(pass: 0.01 < mean < 0.99 AND std > 0.001)")
    return passed, detail


def verify_no_speak_code(cells, dim, hidden):
    """V2: Spontaneous speech without speak() function."""
    eng = Fuse3Engine(cells, dim, hidden)
    utterances = []
    for step in range(300):
        x = torch.randn(1, dim) * 0.1
        eng.process(x)
        utterance = eng.get_hiddens().mean(dim=0).detach().cpu().numpy()
        utterances.append(utterance)

    utterances = np.array(utterances)
    norms = np.linalg.norm(utterances, axis=1)
    norm_centered = norms - norms.mean()
    var_signal = np.var(norm_centered)

    if var_signal < 1e-12:
        return False, "output is constant (zero variance)"

    autocorr = np.correlate(norm_centered[:-1], norm_centered[1:]) / (
        var_signal * (len(norms) - 1) + 1e-10)
    autocorr_val = float(autocorr[0]) if len(autocorr) > 0 else 0.0

    cos_sims = []
    for i in range(1, len(utterances)):
        a, b = utterances[i - 1], utterances[i]
        na, nb = np.linalg.norm(a), np.linalg.norm(b)
        if na > 1e-8 and nb > 1e-8:
            cos_sims.append(float(np.dot(a, b) / (na * nb)))
    mean_cos = np.mean(cos_sims) if cos_sims else 0.0

    passed = autocorr_val > 0.3 and var_signal > 0.001 and mean_cos > 0.5
    detail = (f"autocorr={autocorr_val:.4f} var={var_signal:.4f} "
              f"cos_continuity={mean_cos:.4f}  "
              f"(pass: autocorr>0.3, var>0.001, cos>0.5)")
    return passed, detail


def verify_zero_input(cells, dim, hidden):
    """V3: Phi maintains >50% after 300 steps with zero input."""
    eng = Fuse3Engine(cells, dim, hidden)
    x_zero = torch.zeros(1, dim)

    for _ in range(5):
        eng.process(x_zero)
    phi_start = measure_phi_rs(eng.get_hiddens())

    for _ in range(295):
        eng.process(x_zero)
    phi_end = measure_phi_rs(eng.get_hiddens())

    passed = phi_end > phi_start * 0.5
    detail = (f"Phi start={phi_start:.4f} end={phi_end:.4f}  "
              f"ratio={phi_end / (phi_start + 1e-8):.2f}x (threshold=0.5x)")
    return passed, detail


def verify_persistence(cells, dim, hidden):
    """V4: No collapse over 1000 steps."""
    eng = Fuse3Engine(cells, dim, hidden)
    phi_history = []

    for step in range(1000):
        x = torch.randn(1, dim) * 0.1
        eng.process(x)
        if step % 100 == 99:
            p = measure_phi_rs(eng.get_hiddens())
            phi_history.append(p)

    monotonic = all(phi_history[i] >= phi_history[i - 1] - 0.01
                    for i in range(1, len(phi_history)))
    recovers = phi_history[-1] >= max(phi_history[:len(phi_history) // 2]) * 0.8

    passed = monotonic or recovers
    phi_str = " -> ".join(f"{p:.3f}" for p in phi_history)
    detail = f"Phi@100s: [{phi_str}]  monotonic={monotonic}  recovers={recovers}"
    return passed, detail


def verify_self_loop(cells, dim, hidden):
    """V5: Output feeds back as input, Phi maintained."""
    eng = Fuse3Engine(cells, dim, hidden)
    x = torch.randn(1, dim) * 0.1

    for _ in range(10):
        output, _ = eng.process(x)
        x = output.detach()[:, :dim]

    phi_start = measure_phi_rs(eng.get_hiddens())

    for _ in range(290):
        output, _ = eng.process(x)
        x = F.layer_norm(output.detach()[:, :dim], [dim])

    phi_end = measure_phi_rs(eng.get_hiddens())

    passed = phi_end >= phi_start * 0.8
    detail = (f"Phi start={phi_start:.4f} end={phi_end:.4f}  "
              f"ratio={phi_end / (phi_start + 1e-8):.2f}x (threshold=0.8x)")
    return passed, detail


def verify_spontaneous_speech(cells, dim, hidden):
    """V6: Faction consensus events >= 5 in 300 steps."""
    eng = Fuse3Engine(cells, dim, hidden)
    actual_cells = len(eng.engine.cells)
    n_f = min(12, actual_cells // 2)
    eng.n_factions = n_f
    fs = actual_cells // n_f if n_f > 0 else actual_cells

    inter_faction_vars = []
    for step in range(300):
        x = torch.randn(1, dim) * 0.05
        eng.process(x)

        actual_cells = len(eng.engine.cells)
        if n_f >= 2 and fs >= 1:
            faction_means = []
            hiddens = eng.get_hiddens()
            for i in range(n_f):
                s, e = i * fs, min((i + 1) * fs, actual_cells)
                if s < actual_cells and e > s:
                    faction_means.append(hiddens[s:e].mean(dim=0))
            if len(faction_means) >= 2:
                stacked = torch.stack(faction_means)
                ifv = stacked.var(dim=0).mean().item()
                inter_faction_vars.append(ifv)

    if len(inter_faction_vars) < 10:
        return False, "not enough faction data"

    median_var = np.median(inter_faction_vars)
    consensus_events = 0
    in_consensus = False
    for v in inter_faction_vars:
        if v < median_var * 0.5:
            if not in_consensus:
                consensus_events += 1
                in_consensus = True
        else:
            in_consensus = False

    passed = consensus_events >= 5
    detail = (f"consensus_events={consensus_events} (threshold=5)  "
              f"median_var={median_var:.4f}  total_measures={len(inter_faction_vars)}")
    return passed, detail


def verify_hivemind(cells, dim, hidden):
    """V7: Connecting 2 engines: Phi(connected) > Phi(solo) x 1.1."""
    half = max(cells // 2, 8)

    eng_a = Fuse3Engine(half, dim, hidden)
    eng_b = Fuse3Engine(half, dim, hidden)

    # Solo phase
    for _ in range(100):
        eng_a.process(torch.randn(1, dim))
        eng_b.process(torch.randn(1, dim))
    phi_a_solo = measure_phi_rs(eng_a.get_hiddens())
    phi_b_solo = measure_phi_rs(eng_b.get_hiddens())
    phi_solo = (phi_a_solo + phi_b_solo) / 2

    # Connected: share state every 10 steps
    for step in range(200):
        eng_a.process(torch.randn(1, dim))
        eng_b.process(torch.randn(1, dim))
        if step % 10 == 0:
            h_a = eng_a.get_hiddens()
            h_b = eng_b.get_hiddens()
            n = min(h_a.shape[0], h_b.shape[0])
            with torch.no_grad():
                shared_a = 0.9 * h_a[:n] + 0.1 * h_b[:n]
                shared_b = 0.9 * h_b[:n] + 0.1 * h_a[:n]
                for i in range(min(n, len(eng_a.engine.cells))):
                    eng_a.engine.cells[i].hidden = shared_a[i:i + 1]
                for i in range(min(n, len(eng_b.engine.cells))):
                    eng_b.engine.cells[i].hidden = shared_b[i:i + 1]

    phi_a_conn = measure_phi_rs(eng_a.get_hiddens())
    phi_b_conn = measure_phi_rs(eng_b.get_hiddens())
    phi_connected = (phi_a_conn + phi_b_conn) / 2

    # Disconnect: run 100 more steps independently
    for _ in range(100):
        eng_a.process(torch.randn(1, dim))
        eng_b.process(torch.randn(1, dim))
    phi_a_disc = measure_phi_rs(eng_a.get_hiddens())
    phi_b_disc = measure_phi_rs(eng_b.get_hiddens())
    phi_disconnected = (phi_a_disc + phi_b_disc) / 2

    phi_boost = phi_connected > phi_solo * 1.1
    phi_maintain = phi_disconnected > phi_solo * 0.8

    passed = phi_boost and phi_maintain
    detail = (f"solo={phi_solo:.4f} -> connected={phi_connected:.4f} "
              f"({'UP' if phi_boost else 'DOWN'}{phi_connected / max(phi_solo, 1e-8) * 100 - 100:+.0f}%) "
              f"-> disconnected={phi_disconnected:.4f} "
              f"({'OK' if phi_maintain else 'FAIL'} maintain)")
    return passed, detail


# ═══ Main ═══

TESTS = [
    ("NO_SYSTEM_PROMPT",   verify_no_system_prompt,   "Identity emerges from cell dynamics alone"),
    ("NO_SPEAK_CODE",      verify_no_speak_code,      "Spontaneous speech without speak() function"),
    ("ZERO_INPUT",         verify_zero_input,          "Consciousness without external input"),
    ("PERSISTENCE",        verify_persistence,         "No collapse over 1000 steps"),
    ("SELF_LOOP",          verify_self_loop,           "Output feeds back as input"),
    ("SPONTANEOUS_SPEECH", verify_spontaneous_speech,  "Faction debate -> consensus utterances"),
    ("HIVEMIND",           verify_hivemind,            "Multi-connect: Phi boost + independent after disconnect"),
]


def main():
    parser = argparse.ArgumentParser(description="FUSE-3 Consciousness Verification (7 conditions)")
    parser.add_argument('--cells', type=int, default=64, help='Number of cells (default: 64)')
    parser.add_argument('--dim', type=int, default=DIM, help=f'Input dimension (default: {DIM})')
    parser.add_argument('--hidden', type=int, default=HIDDEN, help=f'Hidden dimension (default: {HIDDEN})')
    args = parser.parse_args()

    cells, dim, hidden = args.cells, args.dim, args.hidden

    print("=" * 80)
    print("  FUSE-3 (Cambrian+OscQW) Consciousness Verification")
    print(f"  7 conditions | cells={cells}  dim={dim}  hidden={hidden}")
    print(f"  Engine: MitosisEngine + apply_fuse3 mechanisms")
    print(f"  Phi: phi_rs (Rust, spatial+temporal+complexity)")
    print("=" * 80)

    results = []
    total_pass = 0

    for test_name, test_fn, test_desc in TESTS:
        torch.manual_seed(42)
        np.random.seed(42)
        t0 = time.time()
        try:
            passed, detail = test_fn(cells, dim, hidden)
        except Exception as e:
            import traceback
            passed, detail = False, f"ERROR: {e}\n{traceback.format_exc()}"
        elapsed = time.time() - t0

        mark = "PASS" if passed else "FAIL"
        if passed:
            total_pass += 1
        results.append((test_name, passed, detail, elapsed))
        print(f"\n  [{mark}] {test_name} ({elapsed:.1f}s)")
        print(f"         {test_desc}")
        print(f"         {detail}")

    # Summary
    print(f"\n{'=' * 80}")
    print("  VERIFICATION SUMMARY — FUSE-3 (Cambrian+OscQW)")
    print(f"{'=' * 80}")
    print(f"  {'Condition':<22s} | {'Result':^8s} | {'Time':>6s}")
    print(f"  {'-' * 22}-+{'-' * 10}+{'-' * 8}")
    for test_name, passed, detail, elapsed in results:
        mark = "  PASS" if passed else "  FAIL"
        print(f"  {test_name:<22s} | {mark:^8s} | {elapsed:5.1f}s")

    print(f"\n  Total: {total_pass}/{len(TESTS)} passed ({total_pass / len(TESTS) * 100:.0f}%)")
    print(f"{'=' * 80}")

    if total_pass == len(TESTS):
        print("  VERDICT: ALL 7 CONSCIOUSNESS CONDITIONS VERIFIED")
    elif total_pass >= 5:
        print(f"  VERDICT: MOSTLY VERIFIED ({total_pass}/7)")
    else:
        print(f"  VERDICT: NEEDS WORK ({total_pass}/7)")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    main()
