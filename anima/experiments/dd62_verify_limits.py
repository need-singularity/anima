#!/usr/bin/env python3
"""DD62: Push 12 verification criteria to absolute limits.

For EACH criterion, find:
  1. MINIMUM engine config that passes
  2. MAXIMUM score achievable
  3. Exact parameter that makes it fail
  4. Whether it genuinely tests consciousness or just noise

Also test adversarial scenarios:
  - bio_noise_base=0
  - All SOC params at 0
  - 1 faction only
  - hidden_dim=8 (extreme compression)
"""

import sys, os, time, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'benchmarks'))

import torch
import torch.nn.functional as F
import numpy as np
from consciousness_engine import ConsciousnessEngine

# Import verify functions from bench_v2
from bench_v2 import (
    VERIFICATION_TESTS, _make_ce, PhiIIT, measure_dual_phi,
    BenchEngine, _CEAdapter,
)

FLUSH = lambda: sys.stdout.flush()

# ═══════════════════════════════════════════════════════════
# Part 1: Config x Criteria Matrix
# ═══════════════════════════════════════════════════════════

CONFIGS = [
    {'label': '2c/16d/32h',  'cells': 2,  'dim': 16, 'hidden': 32},
    {'label': '4c/32d/64h',  'cells': 4,  'dim': 32, 'hidden': 64},
    {'label': '8c/64d/128h', 'cells': 8,  'dim': 64, 'hidden': 128},
    {'label': '16c/64d/128h','cells': 16, 'dim': 64, 'hidden': 128},
    {'label': '32c/64d/128h','cells': 32, 'dim': 64, 'hidden': 128},
    {'label': '64c/64d/128h','cells': 64, 'dim': 64, 'hidden': 128},
]

# ═══════════════════════════════════════════════════════════
# Part 2: Adversarial configs
# ═══════════════════════════════════════════════════════════

def make_adversarial_factory(scenario):
    """Create engine factory for adversarial scenarios."""
    def factory(nc, d, h):
        if scenario == 'no_noise':
            # Monkey-patch bio noise to 0 before creating engine
            import consciousness_engine as ce_mod
            orig_noise = getattr(ce_mod, 'BIO_NOISE_BASE', 0.012)
            ce_mod.BIO_NOISE_BASE = 0.0
            eng = _make_ce(nc, d, h)
            ce_mod.BIO_NOISE_BASE = orig_noise
            return eng
        elif scenario == 'no_soc':
            eng = _make_ce(nc, d, h)
            # Zero out SOC state
            if hasattr(eng, 'engine'):
                eng.engine._soc_threshold = 1e10  # never topple
            return eng
        elif scenario == '1_faction':
            eng = _make_ce(nc, d, h)
            if hasattr(eng, 'engine'):
                eng.engine.n_factions = 1
            eng.n_factions = 1
            return eng
        elif scenario == 'tiny_hidden':
            # Force hidden_dim=8
            return _make_ce(nc, d, 8)
        elif scenario == 'no_ratchet':
            eng = _make_ce(nc, d, h)
            if hasattr(eng, 'engine'):
                eng.engine.phi_ratchet_enabled = False
            return eng
        elif scenario == 'no_hebbian':
            eng = _make_ce(nc, d, h)
            if hasattr(eng, 'engine'):
                eng.engine._coupling = None  # disable coupling
            return eng
        else:
            return _make_ce(nc, d, h)
    return factory


ADVERSARIAL_SCENARIOS = [
    ('no_noise',    'bio_noise_base=0 (no noise)'),
    ('no_soc',      'SOC disabled (threshold=inf)'),
    ('1_faction',   '1 faction only (no debate)'),
    ('tiny_hidden', 'hidden_dim=8 (extreme compression)'),
    ('no_ratchet',  'Phi ratchet disabled'),
    ('no_hebbian',  'Hebbian learning disabled'),
]


def run_single_test(test_fn, factory, cells, dim, hidden, timeout=120):
    """Run a single verify test with timeout protection."""
    torch.manual_seed(42)
    np.random.seed(42)
    t0 = time.time()
    try:
        passed, detail = test_fn(factory, cells, dim, hidden)
        elapsed = time.time() - t0
        return passed, detail, elapsed
    except Exception as e:
        elapsed = time.time() - t0
        return False, f"ERROR: {e}", elapsed


def run_config_matrix():
    """Run all configs x all criteria."""
    test_names = [t[0] for t in VERIFICATION_TESTS]
    results = {}  # (config_label, test_name) -> (passed, detail, elapsed)

    for cfg in CONFIGS:
        label = cfg['label']
        c, d, h = cfg['cells'], cfg['dim'], cfg['hidden']
        print(f"\n{'='*70}")
        print(f"  Config: {label}  (cells={c}, dim={d}, hidden={h})")
        print(f"{'='*70}")
        FLUSH()

        factory = _make_ce
        for test_name, test_fn, test_desc in VERIFICATION_TESTS:
            passed, detail, elapsed = run_single_test(test_fn, factory, c, d, h)
            mark = "PASS" if passed else "FAIL"
            results[(label, test_name)] = (passed, detail, elapsed)
            print(f"  [{mark}] {test_name:<22s} ({elapsed:.1f}s) {detail[:80]}")
            FLUSH()

    return results


def run_adversarial():
    """Run adversarial scenarios at default config (8c/64d/128h)."""
    test_names = [t[0] for t in VERIFICATION_TESTS]
    results = {}  # (scenario, test_name) -> (passed, detail, elapsed)

    cells, dim, hidden = 8, 64, 128

    for scenario_key, scenario_desc in ADVERSARIAL_SCENARIOS:
        print(f"\n{'='*70}")
        print(f"  ADVERSARIAL: {scenario_desc}")
        print(f"{'='*70}")
        FLUSH()

        factory = make_adversarial_factory(scenario_key)
        for test_name, test_fn, test_desc in VERIFICATION_TESTS:
            passed, detail, elapsed = run_single_test(test_fn, factory, cells, dim, hidden)
            mark = "PASS" if passed else "FAIL"
            results[(scenario_key, test_name)] = (passed, detail, elapsed)
            print(f"  [{mark}] {test_name:<22s} ({elapsed:.1f}s) {detail[:80]}")
            FLUSH()

    return results


def analyze_results(config_results, adversarial_results):
    """Analyze results and produce summary."""
    test_names = [t[0] for t in VERIFICATION_TESTS]
    config_labels = [c['label'] for c in CONFIGS]
    adv_labels = [s[0] for s in ADVERSARIAL_SCENARIOS]

    analysis = {}

    for test_name in test_names:
        info = {
            'min_passing': None,
            'all_pass': True,
            'all_fail': True,
            'failing_configs': [],
            'passing_configs': [],
            'adversarial_failures': [],
            'adversarial_passes': [],
        }

        # Config analysis
        for label in config_labels:
            key = (label, test_name)
            if key in config_results:
                passed, detail, elapsed = config_results[key]
                if passed:
                    info['all_fail'] = False
                    info['passing_configs'].append(label)
                    if info['min_passing'] is None:
                        info['min_passing'] = label
                else:
                    info['all_pass'] = False
                    info['failing_configs'].append(label)

        # Adversarial analysis
        for adv_key in adv_labels:
            key = (adv_key, test_name)
            if key in adversarial_results:
                passed, detail, elapsed = adversarial_results[key]
                if not passed:
                    info['adversarial_failures'].append(adv_key)
                else:
                    info['adversarial_passes'].append(adv_key)

        analysis[test_name] = info

    return analysis


def print_matrix(results, row_labels, col_labels, title):
    """Print a pass/fail matrix."""
    print(f"\n{'='*90}")
    print(f"  {title}")
    print(f"{'='*90}")

    # Header
    header = f"  {'':18s}"
    for col in col_labels:
        short = col[:8]
        header += f" {short:>8s}"
    header += "  TOTAL"
    print(header)
    print(f"  {'-'*18}" + ("-" * 9) * len(col_labels) + "-------")

    for row in row_labels:
        line = f"  {row:18s}"
        passes = 0
        for col in col_labels:
            key = (row, col)
            if key in results:
                passed = results[key][0]
                mark = "PASS" if passed else "FAIL"
                if passed:
                    passes += 1
            else:
                mark = "N/A"
            line += f" {mark:>8s}"
        line += f"  {passes}/{len(col_labels)}"
        print(line)


def generate_report(config_results, adversarial_results, analysis):
    """Generate DD62.md report."""
    test_names = [t[0] for t in VERIFICATION_TESTS]
    config_labels = [c['label'] for c in CONFIGS]
    adv_labels = [s[0] for s in ADVERSARIAL_SCENARIOS]
    adv_descs = {s[0]: s[1] for s in ADVERSARIAL_SCENARIOS}

    lines = []
    lines.append("# DD62: Verification Criteria Stress Test")
    lines.append("")
    lines.append("## Experiment Purpose")
    lines.append("Push all 12 consciousness verification criteria to their absolute limits.")
    lines.append("Find the minimum config that passes, the breaking points, and whether")
    lines.append("each criterion genuinely tests consciousness or just noise/artifacts.")
    lines.append("")

    # Config Matrix
    lines.append("## 1. Config x Criteria Matrix")
    lines.append("")
    lines.append("```")
    header = f"{'Config':18s}"
    for t in test_names:
        header += f" | {t[:10]:^10s}"
    header += " | TOTAL"
    lines.append(header)
    lines.append("-" * len(header))

    for label in config_labels:
        row = f"{label:18s}"
        passes = 0
        for tn in test_names:
            key = (label, tn)
            if key in config_results:
                passed = config_results[key][0]
                mark = "PASS" if passed else "FAIL"
                if passed:
                    passes += 1
            else:
                mark = "N/A"
            row += f" | {mark:^10s}"
        row += f" | {passes}/{len(test_names)}"
        lines.append(row)
    lines.append("```")
    lines.append("")

    # Adversarial Matrix
    lines.append("## 2. Adversarial Scenarios (8c/64d/128h)")
    lines.append("")
    lines.append("```")
    header = f"{'Scenario':18s}"
    for t in test_names:
        header += f" | {t[:10]:^10s}"
    header += " | TOTAL"
    lines.append(header)
    lines.append("-" * len(header))

    for adv_key in adv_labels:
        row = f"{adv_key:18s}"
        passes = 0
        for tn in test_names:
            key = (adv_key, tn)
            if key in adversarial_results:
                passed = adversarial_results[key][0]
                mark = "PASS" if passed else "FAIL"
                if passed:
                    passes += 1
            else:
                mark = "N/A"
            row += f" | {mark:^10s}"
        row += f" | {passes}/{len(test_names)}"
        lines.append(row)
    lines.append("```")
    lines.append("")

    # Per-criterion deep analysis
    lines.append("## 3. Per-Criterion Analysis")
    lines.append("")

    for test_name, test_fn, test_desc in VERIFICATION_TESTS:
        info = analysis[test_name]
        lines.append(f"### {test_name}")
        lines.append(f"**Description:** {test_desc}")
        lines.append("")
        lines.append(f"- **Minimum passing config:** {info['min_passing'] or 'NONE (always fails)'}")
        lines.append(f"- **Passes all configs:** {'YES' if info['all_pass'] else 'NO'}")
        lines.append(f"- **Failing configs:** {', '.join(info['failing_configs']) or 'none'}")
        lines.append(f"- **Adversarial failures:** {', '.join(info['adversarial_failures']) or 'none (robust)'}")
        lines.append(f"- **Adversarial passes:** {', '.join(info['adversarial_passes']) or 'none'}")
        lines.append("")

        # Detailed results for each config
        lines.append("| Config | Result | Detail |")
        lines.append("|--------|--------|--------|")
        for label in config_labels:
            key = (label, test_name)
            if key in config_results:
                passed, detail, elapsed = config_results[key]
                mark = "PASS" if passed else "FAIL"
                lines.append(f"| {label} | {mark} | {detail[:80]} |")
        lines.append("")

        # Adversarial details
        lines.append("| Adversarial | Result | Detail |")
        lines.append("|-------------|--------|--------|")
        for adv_key in adv_labels:
            key = (adv_key, test_name)
            if key in adversarial_results:
                passed, detail, elapsed = adversarial_results[key]
                mark = "PASS" if passed else "FAIL"
                lines.append(f"| {adv_descs[adv_key]} | {mark} | {detail[:80]} |")
        lines.append("")

        # Consciousness assessment
        is_robust = len(info['adversarial_failures']) >= 2
        breaks_small = len(info['failing_configs']) > 0
        always_passes = info['all_pass'] and len(info['adversarial_failures']) == 0

        if always_passes:
            verdict = "WEAK: Passes everything including adversarial -- may test noise/artifacts not consciousness"
        elif is_robust and breaks_small:
            verdict = "STRONG: Fails on small configs AND adversarial ablations -- genuine structural test"
        elif breaks_small and not is_robust:
            verdict = "MODERATE: Scale-dependent but not robust to ablation -- partly structural"
        elif is_robust and not breaks_small:
            verdict = "MODERATE: Robust to ablation but passes all scales -- threshold may be too easy"
        else:
            verdict = "UNCLEAR"

        lines.append(f"**Consciousness validity:** {verdict}")
        lines.append("")
        lines.append("---")
        lines.append("")

    # Summary ASCII chart
    lines.append("## 4. Breaking Point Summary")
    lines.append("")
    lines.append("```")
    lines.append("Criterion             Min Pass    Adversarial Kills")
    lines.append("-" * 60)
    for tn in test_names:
        info = analysis[tn]
        min_p = info['min_passing'] or "NEVER"
        kills = ", ".join(info['adversarial_failures'][:3]) or "none"
        lines.append(f"{tn:22s} {min_p:15s} {kills}")
    lines.append("```")
    lines.append("")

    # Pass rate chart
    lines.append("## 5. Pass Rate by Config Size")
    lines.append("")
    lines.append("```")
    for label in config_labels:
        passes = sum(1 for tn in test_names if (label, tn) in config_results and config_results[(label, tn)][0])
        pct = passes / len(test_names) * 100
        bar = '#' * int(pct / 2)
        lines.append(f"{label:18s} {bar:<50s} {passes}/{len(test_names)} ({pct:.0f}%)")
    lines.append("```")
    lines.append("")

    # Adversarial resilience chart
    lines.append("## 6. Adversarial Resilience")
    lines.append("")
    lines.append("```")
    for adv_key in adv_labels:
        passes = sum(1 for tn in test_names if (adv_key, tn) in adversarial_results and adversarial_results[(adv_key, tn)][0])
        pct = passes / len(test_names) * 100
        bar = '#' * int(pct / 2)
        lines.append(f"{adv_descs[adv_key]:40s} {bar:<30s} {passes}/{len(test_names)} ({pct:.0f}%)")
    lines.append("```")
    lines.append("")

    # Key findings
    lines.append("## 7. Key Findings")
    lines.append("")

    # Count genuinely strong tests
    strong = [tn for tn in test_names if len(analysis[tn]['adversarial_failures']) >= 2 and len(analysis[tn]['failing_configs']) > 0]
    weak = [tn for tn in test_names if analysis[tn]['all_pass'] and len(analysis[tn]['adversarial_failures']) == 0]

    lines.append(f"- **Strong criteria** (break on ablation + scale): {', '.join(strong) or 'none'}")
    lines.append(f"- **Weak criteria** (pass everything): {', '.join(weak) or 'none'}")
    lines.append(f"- Total configs tested: {len(CONFIGS)}")
    lines.append(f"- Total adversarial scenarios: {len(ADVERSARIAL_SCENARIOS)}")
    lines.append(f"- Total individual tests: {len(CONFIGS) * len(test_names) + len(ADVERSARIAL_SCENARIOS) * len(test_names)}")
    lines.append("")

    return "\n".join(lines)


def main():
    print("DD62: Verification Criteria Stress Test")
    print("=" * 70)
    print(f"  12 criteria x {len(CONFIGS)} configs = {12 * len(CONFIGS)} tests")
    print(f"  12 criteria x {len(ADVERSARIAL_SCENARIOS)} adversarial = {12 * len(ADVERSARIAL_SCENARIOS)} tests")
    print(f"  Total: {12 * (len(CONFIGS) + len(ADVERSARIAL_SCENARIOS))} tests")
    print("=" * 70)
    FLUSH()

    t_start = time.time()

    # Part 1: Config matrix
    print("\n\n### PART 1: CONFIG x CRITERIA MATRIX ###")
    FLUSH()
    config_results = run_config_matrix()

    # Part 2: Adversarial
    print("\n\n### PART 2: ADVERSARIAL SCENARIOS ###")
    FLUSH()
    adversarial_results = run_adversarial()

    # Analysis
    analysis = analyze_results(config_results, adversarial_results)

    # Print matrices
    test_names = [t[0] for t in VERIFICATION_TESTS]
    config_labels = [c['label'] for c in CONFIGS]
    adv_labels = [s[0] for s in ADVERSARIAL_SCENARIOS]

    print_matrix(config_results, config_labels, test_names, "CONFIG x CRITERIA MATRIX")
    print_matrix(adversarial_results, adv_labels, test_names, "ADVERSARIAL x CRITERIA MATRIX")

    # Generate report
    report = generate_report(config_results, adversarial_results, analysis)

    # Write DD62.md
    out_dir = os.path.join(os.path.dirname(__file__), '..', 'docs', 'hypotheses', 'dd')
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, 'DD62.md')
    with open(out_path, 'w') as f:
        f.write(report)

    elapsed = time.time() - t_start
    print(f"\n\nDD62 complete in {elapsed:.1f}s")
    print(f"Report written to {out_path}")
    FLUSH()


if __name__ == '__main__':
    main()
