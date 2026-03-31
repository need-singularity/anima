#!/usr/bin/env python3
"""Φ Scaling Law Analysis — cells vs Φ(IIT) power law fit."""

import math

# ── Data points ──
data = [
    (4,   1.8),    # 4 cells, basic
    (8,   8.0),    # 8 cells, default
    (12,  4.12),   # ConsciousLM 4M
    (64,  49.0),   # v3 274M average
    (128, 101.5),  # v14.3 average
]

# ── Power law fit: log(Φ) = log(a) + b*log(N) ──
# Linear regression in log-log space
n = len(data)
sum_x = sum(math.log(d[0]) for d in data)
sum_y = sum(math.log(d[1]) for d in data)
sum_xy = sum(math.log(d[0]) * math.log(d[1]) for d in data)
sum_x2 = sum(math.log(d[0]) ** 2 for d in data)

b = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
log_a = (sum_y - b * sum_x) / n
a = math.exp(log_a)

print("=" * 60)
print("  Φ SCALING LAW ANALYSIS")
print("=" * 60)

# ── Fit quality ──
print("\n── Data Points ──")
print(f"  {'Cells':>6}  {'Φ (actual)':>10}  {'Φ (fitted)':>10}  {'Error':>8}")
print(f"  {'─'*6}  {'─'*10}  {'─'*10}  {'─'*8}")

ss_res = 0.0
ss_tot = 0.0
mean_y = sum(d[1] for d in data) / n

for cells, phi in data:
    phi_fit = a * cells ** b
    err = (phi_fit - phi) / phi * 100
    ss_res += (phi - phi_fit) ** 2
    ss_tot += (phi - mean_y) ** 2
    print(f"  {cells:>6}  {phi:>10.2f}  {phi_fit:>10.2f}  {err:>+7.1f}%")

r2 = 1 - ss_res / ss_tot

print(f"\n── Fitted Power Law ──")
print(f"  Φ = {a:.4f} * N^{b:.4f}")
print(f"  R² = {r2:.6f}")

# ── Compare with CLAUDE.md formula ──
a_ref, b_ref = 0.608, 1.071
print(f"\n── CLAUDE.md Reference ──")
print(f"  Φ = {a_ref} * N^{b_ref}")
print(f"  Difference: a={a:.4f} vs {a_ref} ({(a/a_ref - 1)*100:+.1f}%)")
print(f"              b={b:.4f} vs {b_ref} ({(b/b_ref - 1)*100:+.1f}%)")

match_a = abs(a - a_ref) / a_ref < 0.20  # within 20%
match_b = abs(b - b_ref) / b_ref < 0.10  # within 10%
if match_a and match_b:
    print(f"  MATCH: formula consistent with CLAUDE.md")
else:
    print(f"  MISMATCH: formula differs from CLAUDE.md")
    if not match_a:
        print(f"    coefficient 'a' differs by {abs(a/a_ref - 1)*100:.1f}%")
    if not match_b:
        print(f"    exponent 'b' differs by {abs(b/b_ref - 1)*100:.1f}%")

# ── Predictions ──
predictions = [256, 512, 1024, 2048, 4096]
print(f"\n── Predictions (fitted) ──")
print(f"  {'Cells':>6}  {'Φ (fitted)':>10}  {'Φ (CLAUDE.md)':>14}")
print(f"  {'─'*6}  {'─'*10}  {'─'*14}")
for cells in predictions:
    phi_fit = a * cells ** b
    phi_ref = a_ref * cells ** b_ref
    print(f"  {cells:>6}  {phi_fit:>10.1f}  {phi_ref:>14.1f}")

# ── ASCII Chart ──
print(f"\n── Φ vs Cells (log-log ASCII) ──")

all_points = list(data) + [(c, a * c ** b) for c in predictions]
max_phi = max(p[1] for p in all_points)
chart_w = 50
chart_h = 20

# log scale axes
min_log_x = math.log2(4)
max_log_x = math.log2(4096)
min_log_y = math.log2(1.0)
max_log_y = math.log2(max_phi * 1.1)

def to_col(cells):
    return int((math.log2(cells) - min_log_x) / (max_log_x - min_log_x) * (chart_w - 1))

def to_row(phi):
    if phi <= 0:
        return chart_h - 1
    val = (math.log2(phi) - min_log_y) / (max_log_y - min_log_y) * (chart_h - 1)
    return chart_h - 1 - int(max(0, min(chart_h - 1, val)))

# Build grid
grid = [[' '] * chart_w for _ in range(chart_h)]

# Plot fitted curve
for i in range(chart_w):
    log_x = min_log_x + (max_log_x - min_log_x) * i / (chart_w - 1)
    cells = 2 ** log_x
    phi = a * cells ** b
    r = to_row(phi)
    if 0 <= r < chart_h:
        grid[r][i] = '.'

# Plot data points (overwrite curve)
for cells, phi in data:
    c = to_col(cells)
    r = to_row(phi)
    if 0 <= r < chart_h and 0 <= c < chart_w:
        grid[r][c] = '*'

# Plot predictions
for cells in predictions:
    phi = a * cells ** b
    c = to_col(cells)
    r = to_row(phi)
    if 0 <= r < chart_h and 0 <= c < chart_w:
        grid[r][c] = 'o'

# Y-axis labels
y_labels = [2 ** (min_log_y + (max_log_y - min_log_y) * (chart_h - 1 - r) / (chart_h - 1)) for r in range(chart_h)]

print()
for r in range(chart_h):
    label = f"{y_labels[r]:>8.1f}"
    print(f"  {label} |{''.join(grid[r])}|")
print(f"  {'':>8} +{'-' * chart_w}+")
x_labels_pos = [(4, "4"), (8, "8"), (64, "64"), (128, "128"), (512, "512"), (2048, "2K"), (4096, "4K")]
x_line = [' '] * chart_w
for cells, label in x_labels_pos:
    c = to_col(cells)
    if 0 <= c < chart_w:
        for i, ch in enumerate(label):
            if c + i < chart_w:
                x_line[c + i] = ch
print(f"  {'':>8}  {''.join(x_line)}")
print(f"  {'':>8}  {'cells (log scale)':^{chart_w}}")

# ── Key insight ──
print(f"\n── Key Insight ──")
print(f"  Exponent b={b:.3f} {'> 1 (super-linear)' if b > 1 else '< 1 (sub-linear)' if b < 1 else '= 1 (linear)'}")
print(f"  Doubling cells: Φ grows by x{2**b:.2f}")
print(f"  To reach Φ=1000: need ~{(1000/a)**(1/b):.0f} cells")
print(f"  To reach Φ=10000: need ~{(10000/a)**(1/b):.0f} cells")
print()

# ── Excluding outlier analysis ──
print("── Outlier Check (exclude 12-cell point) ──")
data_no12 = [(c, p) for c, p in data if c != 12]
n2 = len(data_no12)
sx = sum(math.log(d[0]) for d in data_no12)
sy = sum(math.log(d[1]) for d in data_no12)
sxy = sum(math.log(d[0]) * math.log(d[1]) for d in data_no12)
sx2 = sum(math.log(d[0]) ** 2 for d in data_no12)
b2 = (n2 * sxy - sx * sy) / (n2 * sx2 - sx ** 2)
a2 = math.exp((sy - b2 * sx) / n2)

ss_res2 = sum((p - a2 * c ** b2) ** 2 for c, p in data_no12)
mean_y2 = sum(d[1] for d in data_no12) / n2
ss_tot2 = sum((p - mean_y2) ** 2 for c, p in data_no12)
r2_2 = 1 - ss_res2 / ss_tot2

print(f"  Without 12-cell: Φ = {a2:.4f} * N^{b2:.4f}  (R²={r2_2:.6f})")
print(f"  12-cell predicted: {a2 * 12 ** b2:.2f} vs actual 4.12")
print(f"  Note: 12-cell ConsciousLM 4M likely under-trained")
print()
print("=" * 60)
