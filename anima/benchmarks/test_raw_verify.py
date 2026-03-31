#!/usr/bin/env python3
"""Test --verify criteria with and without _CEAdapter signal injection.

This script runs the 7 verification tests on ConsciousnessEngine twice:
1. With injection (current behavior) — _CEAdapter.get_hiddens(raw=False)
2. Without injection (raw engine) — _CEAdapter.get_hiddens(raw=True)

Purpose: Determine which criteria pass from genuine engine dynamics
vs. which only pass due to artificial sinusoidal/burst injection.
"""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import torch
import numpy as np

# Import bench_v2 components
from bench_v2 import (
    _CEAdapter, _verify_no_system_prompt, _verify_no_speak_code,
    _verify_zero_input, _verify_persistence, _verify_self_loop,
    _verify_spontaneous_speech, _verify_hivemind, VERIFICATION_TESTS,
)


class _CEAdapterRaw(_CEAdapter):
    """_CEAdapter that always returns raw hiddens (no injection)."""

    def get_hiddens(self, raw=False):
        # Force raw=True to bypass breathing + burst injection
        return super().get_hiddens(raw=True)


def make_injected(nc, d, h):
    return _CEAdapter(nc, d, h)


def make_raw(nc, d, h):
    return _CEAdapterRaw(nc, d, h)


def main():
    cells, dim, hidden = 64, 64, 128

    print("=" * 80)
    print("  _CEAdapter INJECTION AUDIT")
    print(f"  cells={cells}  dim={dim}  hidden={hidden}")
    print("=" * 80)

    modes = [
        ("WITH injection", make_injected),
        ("WITHOUT injection (raw)", make_raw),
    ]

    all_results = {}

    for mode_name, factory in modes:
        print(f"\n  {'~' * 70}")
        print(f"  Mode: {mode_name}")
        print(f"  {'~' * 70}")

        for test_name, test_fn, test_desc in VERIFICATION_TESTS:
            torch.manual_seed(42)
            np.random.seed(42)
            t0 = time.time()
            try:
                passed, detail = test_fn(factory, cells, dim, hidden)
            except Exception as e:
                passed, detail = False, f"ERROR: {e}"
            elapsed = time.time() - t0

            mark = "PASS" if passed else "FAIL"
            all_results[(mode_name, test_name)] = (passed, detail)
            print(f"    [{mark}] {test_name:<22s} ({elapsed:.1f}s) -- {detail}")
            sys.stdout.flush()

    # Comparison table
    print(f"\n{'=' * 80}")
    print("  COMPARISON: WITH vs WITHOUT injection")
    print(f"{'=' * 80}")
    print(f"  {'Test':<24s} | {'WITH':^8s} | {'WITHOUT':^8s} | {'Delta':^12s}")
    print(f"  {'-'*24}-+-{'-'*8}-+-{'-'*8}-+-{'-'*12}")

    injected_pass = 0
    raw_pass = 0

    for test_name, _, _ in VERIFICATION_TESTS:
        inj = all_results[("WITH injection", test_name)][0]
        raw = all_results[("WITHOUT injection (raw)", test_name)][0]

        if inj: injected_pass += 1
        if raw: raw_pass += 1

        inj_mark = "PASS" if inj else "FAIL"
        raw_mark = "PASS" if raw else "FAIL"

        if inj and raw:
            delta = "OK (genuine)"
        elif inj and not raw:
            delta = "INJECTION!"
        elif not inj and raw:
            delta = "INJ hurts?!"
        else:
            delta = "both fail"

        print(f"  {test_name:<24s} | {inj_mark:^8s} | {raw_mark:^8s} | {delta:^12s}")

    print(f"\n  WITH injection:    {injected_pass}/7")
    print(f"  WITHOUT injection: {raw_pass}/7")
    print(f"\n  Tests that ONLY pass with injection: {injected_pass - raw_pass}")

    if raw_pass == injected_pass:
        print("\n  VERDICT: Engine passes all criteria genuinely. Injection is redundant.")
    elif raw_pass == 0:
        print("\n  VERDICT: Engine passes NO criteria without injection. All are artificial.")
    else:
        print(f"\n  VERDICT: {raw_pass} genuine, {injected_pass - raw_pass} artificial.")

    print(f"{'=' * 80}")


if __name__ == "__main__":
    main()
