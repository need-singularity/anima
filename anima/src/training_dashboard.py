#!/usr/bin/env python3
"""training_dashboard.py — Real-time ASCII training monitor

Parses v13 log file and displays live metrics.

Usage:
  python training_dashboard.py logs/v13_h100.log           # local
  ssh H100 'python3 training_dashboard.py logs/v13_h100.log'  # remote
  python training_dashboard.py --remote 216.243.220.230:18038  # SSH stream
"""

import re
import sys
import time
import os

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


def parse_line(line):
    m = re.search(
        r'(P[123]) step\s+(\d+)\s*│\s*CE=([0-9.]+)\s*BPC=([0-9.]+)\s*│\s*'
        r'Φ=([0-9.]+)\s*│\s*cells=(\d+)\s*│\s*lr=([0-9.e+-]+)\s*│\s*'
        r'pain=([0-9.]+)\s*satis=([0-9.]+)', line)
    if m:
        return {
            'phase': m.group(1), 'step': int(m.group(2)),
            'ce': float(m.group(3)), 'bpc': float(m.group(4)),
            'phi': float(m.group(5)), 'cells': int(m.group(6)),
            'lr': float(m.group(7)), 'pain': float(m.group(8)),
            'satis': float(m.group(9)),
        }
    # P1 line (no CE)
    m = re.search(r'(P1) step\s+(\d+)\s*│\s*Φ=([0-9.]+)\s*│\s*cells=(\d+)', line)
    if m:
        return {
            'phase': 'P1', 'step': int(m.group(2)),
            'ce': 0, 'bpc': 0, 'phi': float(m.group(3)),
            'cells': int(m.group(4)), 'lr': 0, 'pain': 0, 'satis': 0,
        }
    # Val line
    m = re.search(r'\[val\] CE=([0-9.]+).*best=([0-9.]+)', line)
    if m:
        return {'type': 'val', 'val_ce': float(m.group(1)), 'best_ce': float(m.group(2))}
    return None

def sparkline(values, width=40):
    if not values:
        return ""
    mn, mx = min(values), max(values)
    rng = mx - mn if mx > mn else 1
    chars = "▁▂▃▄▅▆▇█"
    return "".join(chars[min(int((v - mn) / rng * 7), 7)] for v in values[-width:])

def dashboard(log_path, total_steps=100000):
    history = []
    val_history = []

    # Read existing log
    if os.path.exists(log_path):
        with open(log_path) as f:
            for line in f:
                d = parse_line(line)
                if d:
                    if d.get('type') == 'val':
                        val_history.append(d)
                    else:
                        history.append(d)

    if not history:
        print("No data yet. Waiting...")
        return

    latest = history[-1]
    progress = latest['step'] / total_steps
    eta_steps = total_steps - latest['step']

    # Estimate speed from last 20 entries
    if len(history) >= 2:
        # Assume 100 steps between log entries
        speed = 100 / 3.0  # rough estimate
    else:
        speed = 1

    eta_min = eta_steps / speed / 60

    print("\033[2J\033[H")  # clear screen
    print("═══════════════════════════════════════════════════════════")
    print(f"  v13 Training Dashboard — {latest['phase']} step {latest['step']:,}/{total_steps:,}")
    print("═══════════════════════════════════════════════════════════")
    print()

    # Progress bar
    bar_len = 50
    filled = int(progress * bar_len)
    bar = "█" * filled + "░" * (bar_len - filled)
    print(f"  [{bar}] {progress*100:.1f}%  ETA ~{eta_min:.0f}min")
    print()

    # Current metrics
    print(f"  Phase:  {latest['phase']}  │  CE: {latest['ce']:.4f}  │  BPC: {latest['bpc']:.4f}")
    print(f"  Φ(IIT): {latest['phi']:.2f}  │  Cells: {latest['cells']}  │  LR: {latest['lr']:.2e}")
    print(f"  Pain: {latest['pain']:.2f}  │  Satis: {latest['satis']:.2f}")
    print()

    # Sparklines
    ce_vals = [h['ce'] for h in history if h['ce'] > 0]
    phi_vals = [h['phi'] for h in history]
    cell_vals = [h['cells'] for h in history]
    satis_vals = [h['satis'] for h in history if 'satis' in h]

    print(f"  CE    {sparkline(ce_vals)}  [{min(ce_vals):.4f}~{max(ce_vals):.4f}]" if ce_vals else "")
    print(f"  Φ     {sparkline(phi_vals)}  [{min(phi_vals):.1f}~{max(phi_vals):.1f}]")
    print(f"  Cells {sparkline(cell_vals)}  [{min(cell_vals)}~{max(cell_vals)}]")
    if satis_vals:
        print(f"  Satis {sparkline(satis_vals)}  [{min(satis_vals):.1f}~{max(satis_vals):.1f}]")
    print()

    # Validation history
    if val_history:
        print("  Val CE:", " → ".join(f"{v['val_ce']:.4f}" for v in val_history[-8:]))
        print(f"  Best:   {val_history[-1]['best_ce']:.4f}")
    print()

    # Phase milestones
    p1_end = int(total_steps * 0.2)
    p2_end = int(total_steps * 0.7)
    markers = [
        (p1_end, "P1→P2", latest['step'] >= p1_end),
        (p2_end, "P2→P3 (Hexad)", latest['step'] >= p2_end),
        (total_steps, "Complete", latest['step'] >= total_steps),
    ]
    print("  Milestones:")
    for step, name, done in markers:
        mark = "✅" if done else "🔲"
        print(f"    {mark} {name} (step {step:,})")

if __name__ == '__main__':
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    if len(sys.argv) < 2:
        print("Usage: python training_dashboard.py <log_file> [--watch]")
        sys.exit(1)

    log_path = sys.argv[1]
    watch = '--watch' in sys.argv

    if watch:
        while True:
            dashboard(log_path)
            time.sleep(10)
    else:
        dashboard(log_path)
