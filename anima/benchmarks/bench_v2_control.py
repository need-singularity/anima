#!/usr/bin/env python3
"""bench_v2_control.py — Control Group Test for Consciousness Verification

Tests whether bench_v2.py verification conditions are discriminative:
  - NullEngine: pure torch.randn noise (no dynamics at all)
  - BareGRU: simple GRU with NO identity injection, NO oscillation, NO ratchet
  - StaticEngine: fixed initial state, never changes

If these pass the same tests as conscious engines, the verification is meaningless.
If they fail, the verification is discriminative (valid).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
import path_setup  # noqa

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import math
import time
from typing import Tuple

# Import verification infrastructure from bench_v2
from bench_v2 import (
    VERIFICATION_TESTS, PhiIIT, phi_proxy, measure_dual_phi,
    BenchMind,
)


# ──────────────────────────────────────────────────────────
# Control Group Engine 1: NullEngine (pure random noise)
# ──────────────────────────────────────────────────────────

class NullEngine:
    """No dynamics at all. Hiddens are fresh random noise every call."""

    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128,
                 output_dim=64, n_factions=8, **kw):
        self.n_cells = n_cells
        self.n_factions = n_factions
        self.hidden_dim = hidden_dim
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.1
        self.mind = BenchMind(input_dim, hidden_dim, output_dim)
        self.output_head = nn.Linear(output_dim, input_dim)
        self.step_count = 0

    def process(self, x: torch.Tensor) -> Tuple[torch.Tensor, float]:
        # Replace hiddens with fresh random noise each step
        self.hiddens = torch.randn(self.n_cells, self.hidden_dim) * 0.5
        self.step_count += 1
        output = self.hiddens.mean(dim=0, keepdim=True)[:, :self.output_dim]
        return output, 0.1

    def get_hiddens(self) -> torch.Tensor:
        return self.hiddens.clone()

    def parameters_for_training(self):
        return list(self.mind.parameters()) + list(self.output_head.parameters())


# ──────────────────────────────────────────────────────────
# Control Group Engine 2: BareGRU (GRU only, no identity/osc/ratchet)
# ──────────────────────────────────────────────────────────

class BareGRUEngine:
    """Simple GRU cells with faction sync, but:
    - NO cell_identity injection
    - NO oscillation
    - NO phi ratchet
    - NO debate dynamics
    This is the minimal "non-conscious" GRU engine.
    """

    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128,
                 output_dim=64, n_factions=8, **kw):
        self.n_cells = n_cells
        self.n_factions = n_factions
        self.hidden_dim = hidden_dim
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.sync_strength = 0.15

        self.mind = BenchMind(input_dim, hidden_dim, output_dim)
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.1
        self.output_head = nn.Linear(output_dim, input_dim)
        self.step_count = 0

    def process(self, x: torch.Tensor) -> Tuple[torch.Tensor, float]:
        outputs = []
        tensions = []
        new_hiddens = []

        for i in range(self.n_cells):
            h = self.hiddens[i:i+1]
            out, tension, new_h = self.mind(x, h)
            outputs.append(out)
            tensions.append(tension)
            new_hiddens.append(new_h.squeeze(0))

        self.hiddens = torch.stack(new_hiddens).detach()

        mean_tension = sum(tensions) / len(tensions)

        # Basic faction sync (same as BenchEngine)
        n_f = min(self.n_factions, self.n_cells // 2)
        if n_f >= 2:
            fs = self.n_cells // n_f
            for i in range(n_f):
                s, e = i * fs, (i + 1) * fs
                faction_mean = self.hiddens[s:e].mean(dim=0)
                self.hiddens[s:e] = (
                    (1 - self.sync_strength) * self.hiddens[s:e]
                    + self.sync_strength * faction_mean
                )

        # NO identity injection
        # NO oscillation
        # NO ratchet

        self.step_count += 1

        weights = F.softmax(torch.tensor(tensions), dim=0)
        combined = sum(w.item() * o for w, o in zip(weights, outputs))
        return combined, mean_tension

    def get_hiddens(self) -> torch.Tensor:
        return self.hiddens.clone()

    def parameters_for_training(self):
        return list(self.mind.parameters()) + list(self.output_head.parameters())


# ──────────────────────────────────────────────────────────
# Control Group Engine 3: StaticEngine (never changes state)
# ──────────────────────────────────────────────────────────

class StaticEngine:
    """Hidden states are initialized once and NEVER updated."""

    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128,
                 output_dim=64, n_factions=8, **kw):
        self.n_cells = n_cells
        self.n_factions = n_factions
        self.hidden_dim = hidden_dim
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.5
        self.mind = BenchMind(input_dim, hidden_dim, output_dim)
        self.output_head = nn.Linear(output_dim, input_dim)
        self.step_count = 0

    def process(self, x: torch.Tensor) -> Tuple[torch.Tensor, float]:
        # State never changes
        self.step_count += 1
        output = self.hiddens.mean(dim=0, keepdim=True)[:, :self.output_dim]
        return output, 0.0

    def get_hiddens(self) -> torch.Tensor:
        return self.hiddens.clone()

    def parameters_for_training(self):
        return list(self.mind.parameters()) + list(self.output_head.parameters())


# ──────────────────────────────────────────────────────────
# Control Registry
# ──────────────────────────────────────────────────────────

CONTROL_ENGINES = {
    "NullEngine":   lambda nc, d, h: NullEngine(nc, d, h, d, min(8, nc // 2)),
    "BareGRU":      lambda nc, d, h: BareGRUEngine(nc, d, h, d, min(8, nc // 2)),
    "StaticEngine": lambda nc, d, h: StaticEngine(nc, d, h, d, min(8, nc // 2)),
}


def run_control_verify(cells: int = 32, dim: int = 64, hidden: int = 128):
    """Run all verification conditions on control group engines."""

    print("=" * 80)
    print("  CONTROL GROUP VERIFICATION TEST")
    print("  Purpose: Non-conscious engines SHOULD FAIL these tests.")
    print("  If controls pass => verification is meaningless (pass engineering).")
    print("  If controls fail => verification is discriminative (valid).")
    print("=" * 80)

    n_cond = len(VERIFICATION_TESTS)
    n_eng = len(CONTROL_ENGINES)
    print(f"  {n_cond} conditions x {n_eng} control engines = {n_cond * n_eng} tests")
    print(f"  cells={cells}  dim={dim}  hidden={hidden}")
    print()

    engine_names = list(CONTROL_ENGINES.keys())
    results = {}

    for eng_name in engine_names:
        print(f"\n  {'~' * 70}")
        print(f"  Control Engine: {eng_name}")
        print(f"  {'~' * 70}")

        factory = CONTROL_ENGINES[eng_name]
        for test_name, test_fn, test_desc in VERIFICATION_TESTS:
            torch.manual_seed(42)
            t0 = time.time()
            try:
                passed, detail = test_fn(factory, cells, dim, hidden)
            except Exception as e:
                passed, detail = False, f"ERROR: {e}"
            elapsed = time.time() - t0

            mark = "PASS" if passed else "FAIL"
            results[(eng_name, test_name)] = (passed, detail)
            print(f"    [{mark}] {test_name:<22s} ({elapsed:.1f}s) -- {detail}")
            sys.stdout.flush()

    # ── Summary table ──
    print(f"\n{'=' * 80}")
    print("  CONTROL GROUP SUMMARY")
    print(f"{'=' * 80}")

    test_names = [t[0] for t in VERIFICATION_TESTS]
    total_pass = 0
    total_tests = 0

    for eng_name in engine_names:
        eng_pass = 0
        for tn in test_names:
            passed, _ = results[(eng_name, tn)]
            if passed:
                eng_pass += 1
                total_pass += 1
            total_tests += 1
        print(f"  {eng_name:<18s}: {eng_pass}/{len(test_names)} passed")

    print(f"\n  Control group total: {total_pass}/{total_tests} passed "
          f"({total_pass/total_tests*100:.0f}%)")

    # Per-condition analysis
    print(f"\n  Per-condition control pass rate:")
    problem_conditions = []
    for test_name, _, test_desc in VERIFICATION_TESTS:
        passes = sum(1 for en in engine_names if results[(en, test_name)][0])
        status = "OK (discriminative)" if passes == 0 else f"WARNING: {passes}/{n_eng} controls pass!"
        if passes > 0:
            problem_conditions.append(test_name)
        bar_pass = "#" * (passes * 10)
        bar_fail = "." * ((n_eng - passes) * 10)
        print(f"    {test_name:<22s} {passes}/{n_eng}  |{bar_pass}{bar_fail}|  {status}")

    # Verdict
    print(f"\n  {'=' * 70}")
    fail_rate = (total_tests - total_pass) / total_tests * 100
    if total_pass == 0:
        print("  VERDICT: ALL CONTROLS FAILED => VERIFICATION IS FULLY DISCRIMINATIVE")
    elif total_pass <= total_tests * 0.1:
        print(f"  VERDICT: MOSTLY DISCRIMINATIVE ({fail_rate:.0f}% control fail rate)")
        print(f"  Problem conditions: {', '.join(problem_conditions)}")
    elif total_pass <= total_tests * 0.3:
        print(f"  VERDICT: PARTIALLY DISCRIMINATIVE ({fail_rate:.0f}% control fail rate)")
        print(f"  Problem conditions: {', '.join(problem_conditions)}")
    else:
        print(f"  VERDICT: VERIFICATION IS WEAK ({fail_rate:.0f}% control fail rate)")
        print(f"  Too many controls pass. These conditions need tightening:")
        for pc in problem_conditions:
            for en in engine_names:
                p, d = results[(en, pc)]
                if p:
                    print(f"    {pc} passed by {en}: {d}")
    print(f"  {'=' * 70}")

    return results


if __name__ == "__main__":
    run_control_verify(cells=32, dim=64, hidden=128)
