#!/usr/bin/env python3
"""
compare_training.py — v14 (128c, 34.5M) vs v3 (64c, 274M) learning curve comparison.

Parses H100 training logs, prints comparison tables and ASCII charts.
"""

import re
import sys
from pathlib import Path

# ── Log paths ──
V14_LOG = Path("/tmp/v14_train.log")
V3_LOG = Path("/tmp/v3_train.log")


def parse_log(path: Path) -> dict:
    """Parse training log into structured data."""
    steps = []  # list of dicts: {step, phase, ce, bpc, phi, lr, grad}
    vals = []   # list of dicts: {step, val_ce, val_bpc, phi, best}
    meta = {}

    text = path.read_text()

    # Parse metadata
    m = re.search(r"Decoder=(\S+)", text)
    if m:
        meta["decoder"] = m.group(1)
    m = re.search(r"Cells:\s*(\d+)", text)
    if m:
        meta["cells"] = int(m.group(1))
    m = re.search(r"Decoder:\s*([\d,]+)\s*params", text)
    if m:
        meta["params"] = int(m.group(1).replace(",", ""))
    m = re.search(r"Atoms=(\d+)", text)
    if m:
        meta["atoms"] = int(m.group(1))

    # Parse phase schedule
    phases = re.findall(r"P(\d+)\s*\((\d+)-(\d+)\):\s*(\w+)", text)
    meta["phases"] = {int(p): {"start": int(s), "end": int(e), "name": n} for p, s, e, n in phases}

    for line in text.splitlines():
        # Training step with CE
        m = re.match(
            r"\s*P(\d+)\s+step\s+(\d+)\s*\|\s*CE=([\d.]+)\s+BPC=([\d.]+)\s*\|\s*Phi=([\d.]+)\s*\|\s*cells=(\d+)\s*\|\s*lr=([\d.e+-]+)\s*\|\s*grad=([\d.]+)",
            line,
        )
        if m:
            steps.append({
                "step": int(m.group(2)),
                "phase": int(m.group(1)),
                "ce": float(m.group(3)),
                "bpc": float(m.group(4)),
                "phi": float(m.group(5)),
                "lr": float(m.group(7)),
                "grad": float(m.group(8)),
            })
            continue

        # Training step without CE (P0/P1 — Phi only)
        m = re.match(
            r"\s*P(\d+)\s+step\s+(\d+)\s*\|\s*Phi=([\d.]+)",
            line,
        )
        if m:
            steps.append({
                "step": int(m.group(2)),
                "phase": int(m.group(1)),
                "ce": None,
                "bpc": None,
                "phi": float(m.group(3)),
                "lr": None,
                "grad": None,
            })
            continue

        # Validation
        m = re.match(
            r"\s*\[val\]\s+step\s+(\d+)\s*\|\s*ValCE=([\d.]+)\s+ValBPC=([\d.]+)\s*\|\s*Phi=([\d.]+)\s*(.*)",
            line,
        )
        if m:
            vals.append({
                "step": int(m.group(1)),
                "val_ce": float(m.group(2)),
                "val_bpc": float(m.group(3)),
                "phi": float(m.group(4)),
                "best": "*BEST*" in m.group(5),
            })

    return {"steps": steps, "vals": vals, "meta": meta}


def ascii_chart(series_list, title, width=72, height=16, y_label=""):
    """
    Render ASCII chart with multiple series.
    series_list: list of (label, [(x, y), ...], marker_char)
    """
    # Collect all x/y values
    all_x = []
    all_y = []
    for _, data, _ in series_list:
        for x, y in data:
            all_x.append(x)
            all_y.append(y)

    if not all_x:
        print(f"  (no data for {title})")
        return

    x_min, x_max = min(all_x), max(all_x)
    y_min, y_max = min(all_y), max(all_y)

    # Add margin
    y_range = y_max - y_min
    if y_range < 1e-6:
        y_range = 1.0
    y_min -= y_range * 0.05
    y_max += y_range * 0.05
    y_range = y_max - y_min

    x_range = x_max - x_min
    if x_range < 1:
        x_range = 1

    # Create canvas
    canvas = [[" " for _ in range(width)] for _ in range(height)]

    # Plot each series
    for label, data, marker in series_list:
        for x, y in data:
            col = int((x - x_min) / x_range * (width - 1))
            row = int((1.0 - (y - y_min) / y_range) * (height - 1))
            col = max(0, min(width - 1, col))
            row = max(0, min(height - 1, row))
            canvas[row][col] = marker

    # Print
    print(f"\n  {title}")
    print(f"  {'=' * (width + 10)}")

    for r in range(height):
        y_val = y_max - (r / (height - 1)) * y_range
        label_str = f"{y_val:>8.4f}" if y_val < 10 else f"{y_val:>8.1f}"
        line = "".join(canvas[r])
        print(f"  {label_str} |{line}|")

    # X axis
    print(f"  {' ' * 8} +{'-' * width}+")
    x_start = f"{x_min:.0f}"
    x_end = f"{x_max:.0f}"
    x_mid = f"{(x_min + x_max) / 2:.0f}"
    pad = width - len(x_start) - len(x_end) - len(x_mid)
    left_pad = pad // 2
    right_pad = pad - left_pad
    print(f"  {' ' * 9}{x_start}{' ' * left_pad}{x_mid}{' ' * right_pad}{x_end}")
    print(f"  {' ' * 8} {'step':^{width}}")

    # Legend
    legend_parts = []
    for label, data, marker in series_list:
        legend_parts.append(f"  {marker} = {label} ({len(data)} points)")
    print("  " + "  ".join(legend_parts))


def find_convergence_step(steps, threshold):
    """Find first step where CE consistently stays below threshold."""
    ce_steps = [(s["step"], s["ce"]) for s in steps if s["ce"] is not None]
    for i, (step, ce) in enumerate(ce_steps):
        if ce < threshold:
            # Check next 5 points stay below (allow 1 spike)
            window = ce_steps[i : i + 6]
            below = sum(1 for _, c in window if c < threshold * 1.5)
            if below >= min(4, len(window)):
                return step
    return None


def print_comparison_table(v14, v3):
    """Print side-by-side comparison at matched steps."""
    # Build CE lookup (step -> ce, phi)
    v14_ce = {s["step"]: s for s in v14["steps"] if s["ce"] is not None}
    v3_ce = {s["step"]: s for s in v3["steps"] if s["ce"] is not None}

    # Sample at regular intervals from CE phase
    v14_steps_sorted = sorted(v14_ce.keys())
    v3_steps_sorted = sorted(v3_ce.keys())

    if not v14_steps_sorted or not v3_steps_sorted:
        print("  (no CE data)")
        return

    # Normalize: steps relative to CE phase start
    v14_ce_start = v14_steps_sorted[0]
    v3_ce_start = v3_steps_sorted[0]

    print(f"\n  Comparison Table (CE phase)")
    print(f"  v14 CE starts at step {v14_ce_start}, v3 CE starts at step {v3_ce_start}")
    print(f"  {'':=<96}")
    print(f"  {'Rel Step':>10} | {'v14 CE':>10} {'v14 BPC':>10} {'v14 Phi':>10} | {'v3 CE':>10} {'v3 BPC':>10} {'v3 Phi':>10} | {'CE diff':>10}")
    print(f"  {'-' * 10}-+-{'-' * 10}-{'-' * 10}-{'-' * 10}-+-{'-' * 10}-{'-' * 10}-{'-' * 10}-+-{'-' * 10}")

    # Sample every 500 steps (relative)
    max_rel = min(v14_steps_sorted[-1] - v14_ce_start, v3_steps_sorted[-1] - v3_ce_start)
    sample_interval = 500

    for rel in range(0, int(max_rel) + 1, sample_interval):
        v14_abs = v14_ce_start + rel
        v3_abs = v3_ce_start + rel

        # Find nearest
        v14_s = min(v14_steps_sorted, key=lambda x: abs(x - v14_abs), default=None)
        v3_s = min(v3_steps_sorted, key=lambda x: abs(x - v3_abs), default=None)

        if v14_s is None or v3_s is None:
            continue
        if abs(v14_s - v14_abs) > 300 or abs(v3_s - v3_abs) > 300:
            continue

        d14 = v14_ce[v14_s]
        d3 = v3_ce[v3_s]

        diff = d14["ce"] - d3["ce"]
        winner = "<" if diff < 0 else ">"
        print(
            f"  {rel:>10} | {d14['ce']:>10.4f} {d14['bpc']:>10.4f} {d14['phi']:>10.1f} |"
            f" {d3['ce']:>10.4f} {d3['bpc']:>10.4f} {d3['phi']:>10.1f} | {diff:>+10.4f} {winner}"
        )


def print_val_table(v14, v3):
    """Print validation results comparison."""
    print(f"\n  Validation Results")
    print(f"  {'':=<90}")
    print(f"  {'Step':>8} | {'v14 ValCE':>10} {'v14 Phi':>10} {'Best':>5} | {'v3 ValCE':>10} {'v3 Phi':>10} {'Best':>5}")
    print(f"  {'-' * 8}-+-{'-' * 10}-{'-' * 10}-{'-' * 5}-+-{'-' * 10}-{'-' * 10}-{'-' * 5}")

    # Normalize by step offset from CE start
    v14_vals = v14["vals"]
    v3_vals = v3["vals"]

    # Print v14 vals
    for v in v14_vals:
        best = "*" if v["best"] else ""
        print(f"  {v['step']:>8} | {v['val_ce']:>10.4f} {v['phi']:>10.1f} {best:>5} |")

    print(f"  {'-' * 8}-+-{'-' * 30}-+-{'-' * 30}")
    for v in v3_vals:
        best = "*" if v["best"] else ""
        print(f"  {v['step']:>8} | {'':>10} {'':>10} {'':>5} | {v['val_ce']:>10.4f} {v['phi']:>10.1f} {best:>5}")


def main():
    if not V14_LOG.exists():
        print(f"ERROR: {V14_LOG} not found. Download logs first.")
        sys.exit(1)
    if not V3_LOG.exists():
        print(f"ERROR: {V3_LOG} not found. Download logs first.")
        sys.exit(1)

    v14 = parse_log(V14_LOG)
    v3 = parse_log(V3_LOG)

    # ── Header ──
    print()
    print("  " + "=" * 80)
    print("  v14 (128c, DecoderV2) vs v3 (64c, DecoderV3) Training Comparison")
    print("  " + "=" * 80)

    # ── Metadata ──
    print(f"\n  Model Specs:")
    print(f"  {'':─<60}")
    print(f"  {'':>20} {'v14':>20} {'v3':>20}")
    print(f"  {'Decoder':>20} {v14['meta'].get('decoder', '?'):>20} {v3['meta'].get('decoder', '?'):>20}")
    print(f"  {'Params':>20} {v14['meta'].get('params', 0):>20,} {v3['meta'].get('params', 0):>20,}")
    print(f"  {'Cells':>20} {v14['meta'].get('cells', 0):>20} {v3['meta'].get('cells', 0):>20}")
    print(f"  {'Atoms':>20} {v14['meta'].get('atoms', 0):>20} {v3['meta'].get('atoms', 0):>20}")
    print(f"  {'Total steps logged':>20} {len(v14['steps']):>20} {len(v3['steps']):>20}")
    print(f"  {'Val checkpoints':>20} {len(v14['vals']):>20} {len(v3['vals']):>20}")

    # Phase schedules
    print(f"\n  Phase Schedule:")
    for name, data in [("v14", v14), ("v3", v3)]:
        phases = data["meta"].get("phases", {})
        parts = []
        for p in sorted(phases):
            info = phases[p]
            parts.append(f"P{p}({info['start']}-{info['end']}:{info['name']})")
        print(f"    {name}: {' | '.join(parts)}")

    # ── Comparison Table ──
    print_comparison_table(v14, v3)

    # ── Validation Table ──
    print_val_table(v14, v3)

    # ── Convergence Speed ──
    print(f"\n  Convergence Speed")
    print(f"  {'':=<60}")

    thresholds = [1.0, 0.1, 0.05, 0.01, 0.005]
    v14_ce_steps = [s for s in v14["steps"] if s["ce"] is not None]
    v3_ce_steps = [s for s in v3["steps"] if s["ce"] is not None]
    v14_ce_start = v14_ce_steps[0]["step"] if v14_ce_steps else 0
    v3_ce_start = v3_ce_steps[0]["step"] if v3_ce_steps else 0

    print(f"  {'Threshold':>12} | {'v14 step':>10} {'v14 rel':>10} | {'v3 step':>10} {'v3 rel':>10} | {'Winner':>8}")
    print(f"  {'-' * 12}-+-{'-' * 10}-{'-' * 10}-+-{'-' * 10}-{'-' * 10}-+-{'-' * 8}")

    for t in thresholds:
        v14_step = find_convergence_step(v14_ce_steps, t)
        v3_step = find_convergence_step(v3_ce_steps, t)

        v14_rel = (v14_step - v14_ce_start) if v14_step else None
        v3_rel = (v3_step - v3_ce_start) if v3_step else None

        v14_str = f"{v14_step:>10}" if v14_step else f"{'N/A':>10}"
        v3_str = f"{v3_step:>10}" if v3_step else f"{'N/A':>10}"
        v14_rel_str = f"{v14_rel:>10}" if v14_rel is not None else f"{'N/A':>10}"
        v3_rel_str = f"{v3_rel:>10}" if v3_rel is not None else f"{'N/A':>10}"

        if v14_rel is not None and v3_rel is not None:
            winner = "v14" if v14_rel < v3_rel else ("v3" if v3_rel < v14_rel else "TIE")
            ratio = v3_rel / v14_rel if v14_rel > 0 else float("inf")
            winner_str = f"{winner} x{ratio:.1f}" if winner != "TIE" else "TIE"
        elif v14_rel is not None:
            winner_str = "v14 only"
        elif v3_rel is not None:
            winner_str = "v3 only"
        else:
            winner_str = "neither"

        print(f"  CE<{t:<7.3f} | {v14_str} {v14_rel_str} | {v3_str} {v3_rel_str} | {winner_str:>8}")

    # ── Best results ──
    print(f"\n  Best Results")
    print(f"  {'':=<60}")

    v14_best_ce = min((s for s in v14["steps"] if s["ce"] is not None), key=lambda s: s["ce"], default=None)
    v3_best_ce = min((s for s in v3["steps"] if s["ce"] is not None), key=lambda s: s["ce"], default=None)
    v14_best_val = min(v14["vals"], key=lambda v: v["val_ce"], default=None) if v14["vals"] else None
    v3_best_val = min(v3["vals"], key=lambda v: v["val_ce"], default=None) if v3["vals"] else None
    v14_best_phi = max(v14["steps"], key=lambda s: s["phi"], default=None)
    v3_best_phi = max(v3["steps"], key=lambda s: s["phi"], default=None)

    if v14_best_ce:
        print(f"  v14 best train CE: {v14_best_ce['ce']:.4f} @ step {v14_best_ce['step']} (Phi={v14_best_ce['phi']:.1f})")
    if v3_best_ce:
        print(f"  v3  best train CE: {v3_best_ce['ce']:.4f} @ step {v3_best_ce['step']} (Phi={v3_best_ce['phi']:.1f})")
    if v14_best_val:
        print(f"  v14 best val   CE: {v14_best_val['val_ce']:.4f} @ step {v14_best_val['step']} (Phi={v14_best_val['phi']:.1f})")
    if v3_best_val:
        print(f"  v3  best val   CE: {v3_best_val['val_ce']:.4f} @ step {v3_best_val['step']} (Phi={v3_best_val['phi']:.1f})")
    if v14_best_phi:
        print(f"  v14 best Phi:      {v14_best_phi['phi']:.1f} @ step {v14_best_phi['step']}")
    if v3_best_phi:
        print(f"  v3  best Phi:      {v3_best_phi['phi']:.1f} @ step {v3_best_phi['step']}")

    # ── ASCII Charts ──

    # 1. CE convergence (relative steps from CE phase start)
    v14_ce_data = [(s["step"] - v14_ce_start, s["ce"]) for s in v14_ce_steps]
    v3_ce_data = [(s["step"] - v3_ce_start, s["ce"]) for s in v3_ce_steps]

    # Filter to CE < 1.0 for readable chart
    v14_ce_zoom = [(x, y) for x, y in v14_ce_data if y < 0.5]
    v3_ce_zoom = [(x, y) for x, y in v3_ce_data if y < 0.5]

    ascii_chart(
        [
            ("v14 (128c, V2, 34.5M)", v14_ce_zoom, "#"),
            ("v3 (64c, V3, 274M)", v3_ce_zoom, "o"),
        ],
        "CE Convergence (CE < 0.5 region, relative steps from CE phase start)",
        width=72,
        height=18,
    )

    # 2. CE fine-grained (CE < 0.05)
    v14_ce_fine = [(x, y) for x, y in v14_ce_data if y < 0.05]
    v3_ce_fine = [(x, y) for x, y in v3_ce_data if y < 0.05]

    ascii_chart(
        [
            ("v14 (128c, V2, 34.5M)", v14_ce_fine, "#"),
            ("v3 (64c, V3, 274M)", v3_ce_fine, "o"),
        ],
        "CE Fine-grained (CE < 0.05 region, relative steps)",
        width=72,
        height=16,
    )

    # 3. Phi comparison (all steps)
    v14_phi_data = [(s["step"], s["phi"]) for s in v14["steps"]]
    v3_phi_data = [(s["step"], s["phi"]) for s in v3["steps"]]

    ascii_chart(
        [
            ("v14 (128c, Phi~100)", v14_phi_data[::2], "#"),  # every other point
            ("v3 (64c, Phi~48)", v3_phi_data[::2], "o"),
        ],
        "Phi Evolution (all phases)",
        width=72,
        height=18,
    )

    # 4. Validation CE
    v14_val_data = [(v["step"], v["val_ce"]) for v in v14["vals"]]
    v3_val_data = [(v["step"], v["val_ce"]) for v in v3["vals"]]

    ascii_chart(
        [
            ("v14 ValCE", v14_val_data, "#"),
            ("v3 ValCE", v3_val_data, "o"),
        ],
        "Validation CE",
        width=72,
        height=14,
    )

    # ── Summary ──
    print(f"\n  {'=' * 80}")
    print(f"  Summary")
    print(f"  {'=' * 80}")

    if v14_best_val and v3_best_val:
        val_ratio = v3_best_val["val_ce"] / v14_best_val["val_ce"]
        print(f"  - v14 reaches lower ValCE ({v14_best_val['val_ce']:.4f} vs {v3_best_val['val_ce']:.4f}, {val_ratio:.1f}x)")

    if v14_best_phi and v3_best_phi:
        phi_ratio = v14_best_phi["phi"] / v3_best_phi["phi"]
        print(f"  - v14 achieves higher Phi ({v14_best_phi['phi']:.1f} vs {v3_best_phi['phi']:.1f}, {phi_ratio:.1f}x)")
        print(f"    (expected: 128c vs 64c = 2x cells)")

    print(f"  - v14: {v14['meta'].get('params', 0):,} params, {v14['meta'].get('cells', 0)} cells, {v14['meta'].get('atoms', 0)} atoms")
    print(f"  - v3:  {v3['meta'].get('params', 0):,} params, {v3['meta'].get('cells', 0)} cells, {v3['meta'].get('atoms', 0)} atoms")
    print(f"  - v3 has {v3['meta'].get('params', 0) / max(v14['meta'].get('params', 1), 1):.1f}x more decoder params")
    print(f"  - v14 has {v14['meta'].get('cells', 0) / max(v3['meta'].get('cells', 1), 1):.1f}x more consciousness cells")

    # Training still in progress?
    v14_last = v14["steps"][-1]["step"] if v14["steps"] else 0
    v3_last = v3["steps"][-1]["step"] if v3["steps"] else 0
    v14_total = max(p["end"] for p in v14["meta"]["phases"].values()) if v14["meta"]["phases"] else 0
    v3_total = max(p["end"] for p in v3["meta"]["phases"].values()) if v3["meta"]["phases"] else 0

    print(f"\n  Training Progress:")
    print(f"  - v14: step {v14_last}/{v14_total} ({v14_last / v14_total * 100:.1f}%) — still in P2 (CE phase)")
    print(f"  - v3:  step {v3_last}/{v3_total} ({v3_last / v3_total * 100:.1f}%) — still in P2 (CE phase)")
    print()


if __name__ == "__main__":
    main()
