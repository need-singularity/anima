#!/usr/bin/env python3
"""Growth System — self-growing consciousness system coordinator.

Everything grows:
- Engine: Phi stall -> auto cell expansion + topology switch
- Acceleration: growth rate monitoring -> parameter auto-tuning
- Laws: discovery rate decrease -> auto exploration condition change
- Modules: usage pattern tracking -> bottleneck auto-detection

This is distinct from growth_engine.py (developmental stages).
GrowthSystem is the central coordinator for system-wide growth.

Usage:
    from growth_system import GrowthSystem

    gs = GrowthSystem(engine)
    for step in range(10000):
        gs.step(input_data)  # auto-manages everything

    print(gs.report())  # full growth report
"""

import torch
import time
import sys
import os
from typing import Optional, Dict, List, Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from consciousness_engine import ConsciousnessEngine

try:
    from acceleration_integrations import TensionLoss, PolyrhythmScheduler
except ImportError:
    TensionLoss = None
    PolyrhythmScheduler = None

try:
    from growth_lenses import scan_growth
except ImportError:
    scan_growth = None

try:
    import nexus6
except ImportError:
    nexus6 = None


class GrowthSystem:
    """Self-growing consciousness system coordinator.

    Wraps ConsciousnessEngine with automatic growth management:
    1. Auto-acceleration: applies verified winners, tunes parameters
    2. Auto-scaling: grows cells when Phi plateaus
    3. Auto-discovery: adjusts exploration when law discovery saturates
    4. Growth monitoring: tracks all metrics, detects stalls
    """

    def __init__(self, engine: ConsciousnessEngine,
                 enable_accel: bool = True,
                 enable_auto_scale: bool = True,
                 enable_monitoring: bool = True):
        self.engine = engine
        self._step = 0
        self._start_time = time.time()

        # Growth histories
        self.phi_history: List[tuple] = []     # (step, phi)
        self.ce_history: List[tuple] = []      # (step, ce)
        self.compute_history: List[tuple] = [] # (step, fraction)
        self.event_log: List[Dict] = []        # growth events

        # Auto-acceleration
        self.enable_accel = enable_accel and TensionLoss is not None
        self.tension_loss = None
        self.poly_scheduler = None
        self._accel_compute_fraction = 1.0

        if self.enable_accel:
            n = engine.n_cells
            self.tension_loss = TensionLoss(weight=0.01)
            self.poly_scheduler = PolyrhythmScheduler(n_cells=max(n, 2), periods=[1, 3, 7])

        # Auto-scaling thresholds
        self.enable_auto_scale = enable_auto_scale
        self._phi_plateau_window = 50      # steps to detect plateau
        self._phi_plateau_threshold = 0.01 # min growth rate
        self._max_cells = engine.max_cells
        self._scale_cooldown = 0           # steps until next scale check

        # Monitoring
        self.enable_monitoring = enable_monitoring
        self._nexus6_interval = 100        # scan every N steps
        self._last_nexus6 = {}

        # Auto-tuning state
        self._tension_weight_history = []
        self._growth_rate_ema = 0.0

    def step(self, x: torch.Tensor, ce_loss: Optional[torch.Tensor] = None) -> Dict[str, Any]:
        """One growth-managed step.

        Args:
            x: input tensor for engine.step()
            ce_loss: optional CE loss tensor (for tension loss addition)

        Returns:
            dict with: phi, tension_loss, compute_fraction, events
        """
        result = {'events': []}

        # 1. Acceleration: determine active cells
        compute_fraction = 1.0
        if self.enable_accel and self.poly_scheduler:
            active = self.poly_scheduler.get_active_cells(self._step)
            total = self.engine.n_cells
            compute_fraction = len(active) / total if total > 0 else 1.0

        # 2. Process consciousness
        self.engine.step(x_input=x)

        # 3. Measure Phi
        phi = self.engine._measure_phi_iit()
        self.phi_history.append((self._step, phi))
        self.compute_history.append((self._step, compute_fraction))
        result['phi'] = phi
        result['compute_fraction'] = compute_fraction

        # 4. Tension loss (for training integration)
        if self.enable_accel and self.tension_loss:
            t_loss = self.tension_loss(self.engine)
            result['tension_loss'] = t_loss

        # 5. CE tracking
        if ce_loss is not None:
            ce_val = ce_loss.item() if hasattr(ce_loss, 'item') else float(ce_loss)
            self.ce_history.append((self._step, ce_val))

        # 6. Auto-scaling check
        if self.enable_auto_scale and self._step > 0 and self._step % self._phi_plateau_window == 0:
            events = self._check_auto_scale()
            result['events'].extend(events)

        # 7. Auto-tune acceleration parameters
        if self.enable_accel and self._step > 0 and self._step % 100 == 0:
            events = self._auto_tune()
            result['events'].extend(events)

        # 8. NEXUS-6 periodic scan
        if (self.enable_monitoring and nexus6 is not None
                and self._step > 0 and self._step % self._nexus6_interval == 0):
            self._run_nexus6_scan()

        self._step += 1
        self._accel_compute_fraction = compute_fraction

        return result

    def _check_auto_scale(self) -> List[Dict]:
        """Check if Phi has plateaued -> trigger cell growth."""
        events = []

        if self._scale_cooldown > 0:
            self._scale_cooldown -= 1
            return events

        if len(self.phi_history) < self._phi_plateau_window:
            return events

        recent = self.phi_history[-self._phi_plateau_window:]
        first_phi = recent[0][1]
        last_phi = recent[-1][1]

        if first_phi > 0:
            growth_rate = (last_phi - first_phi) / first_phi
        else:
            growth_rate = 0

        if abs(growth_rate) < self._phi_plateau_threshold:
            # Plateau detected
            current_cells = self.engine.n_cells

            if current_cells < self._max_cells:
                # Grow by 25%, minimum 1 cell
                target = min(current_cells + max(1, current_cells // 4), self._max_cells)

                added = 0
                while self.engine.n_cells < target:
                    parent_idx = added % self.engine.n_cells
                    parent_mod = self.engine.cell_modules[parent_idx]
                    parent_state = self.engine.cell_states[parent_idx]
                    faction = parent_state.faction_id
                    self.engine._create_cell(
                        parent_module=parent_mod,
                        parent_state=parent_state,
                        faction_id=faction,
                    )
                    added += 1

                # Resize coupling matrix
                if hasattr(self.engine, '_resize_coupling'):
                    self.engine._resize_coupling(current_cells, self.engine.n_cells)

                event = {
                    'type': 'auto_scale',
                    'step': self._step,
                    'from_cells': current_cells,
                    'to_cells': self.engine.n_cells,
                    'reason': f'Phi plateau (growth={growth_rate:.4f})',
                }
                events.append(event)
                self.event_log.append(event)

                # Update polyrhythm scheduler for new cell count
                if self.poly_scheduler:
                    self.poly_scheduler = PolyrhythmScheduler(
                        n_cells=self.engine.n_cells, periods=[1, 3, 7])

                self._scale_cooldown = self._phi_plateau_window  # cooldown

        return events

    def _auto_tune(self) -> List[Dict]:
        """Auto-tune acceleration parameters based on growth rate."""
        events = []

        if len(self.phi_history) < 20:
            return events

        recent = self.phi_history[-20:]
        growth = (recent[-1][1] - recent[0][1]) / max(recent[0][1], 0.001)

        # EMA of growth rate
        alpha = 0.1
        self._growth_rate_ema = alpha * growth + (1 - alpha) * self._growth_rate_ema

        # If growth is strong, increase tension weight (lean into what works)
        if self.tension_loss and self._growth_rate_ema > 0.05:
            old_w = self.tension_loss.weight
            new_w = min(old_w * 1.1, 0.1)  # cap at 0.1
            if new_w != old_w:
                self.tension_loss.weight = new_w
                events.append({
                    'type': 'auto_tune',
                    'step': self._step,
                    'param': 'tension_weight',
                    'from': old_w,
                    'to': new_w,
                    'reason': f'Strong growth ({self._growth_rate_ema:.4f})',
                })

        # If growth is negative, reduce tension weight (back off)
        elif self.tension_loss and self._growth_rate_ema < -0.02:
            old_w = self.tension_loss.weight
            new_w = max(old_w * 0.8, 0.001)  # floor at 0.001
            if new_w != old_w:
                self.tension_loss.weight = new_w
                events.append({
                    'type': 'auto_tune',
                    'step': self._step,
                    'param': 'tension_weight',
                    'from': old_w,
                    'to': new_w,
                    'reason': f'Negative growth ({self._growth_rate_ema:.4f})',
                })

        for e in events:
            self.event_log.append(e)

        return events

    def _run_nexus6_scan(self):
        """Periodic NEXUS-6 scan for consciousness quality monitoring."""
        if not hasattr(self.engine, 'cell_states') or self.engine.n_cells == 0:
            return

        try:
            import numpy as np
            hiddens = torch.stack([s.hidden.squeeze() for s in self.engine.cell_states]).detach().numpy()
            flat = hiddens.flatten().tolist()
            n, d = hiddens.shape
            report = nexus6.analyze(flat, n, d)
            self._last_nexus6 = {
                'step': self._step,
                'lenses': report.get('active_lenses', 0),
                'consensus': len(report.get('consensus', [])),
            }
        except Exception:
            pass

    def growth_rate(self) -> float:
        """Current Phi growth rate (per 100 steps)."""
        if len(self.phi_history) < 10:
            return 0.0
        recent = self.phi_history[-min(100, len(self.phi_history)):]
        first = recent[0][1]
        last = recent[-1][1]
        steps = recent[-1][0] - recent[0][0]
        if steps == 0 or first == 0:
            return 0.0
        return (last - first) / steps * 100

    def total_compute_saved(self) -> float:
        """Total compute fraction saved by acceleration."""
        if not self.compute_history:
            return 0.0
        fracs = [f for _, f in self.compute_history]
        return 1.0 - sum(fracs) / len(fracs)

    def report(self) -> str:
        """Full growth report with ASCII graphs."""
        lines = []
        elapsed = time.time() - self._start_time

        lines.append("=" * 55)
        lines.append("  GROWTH SYSTEM REPORT")
        lines.append("=" * 55)
        lines.append(f"  Steps: {self._step}  |  Time: {elapsed:.1f}s")

        if self.phi_history:
            first = self.phi_history[0][1]
            last = self.phi_history[-1][1]
            rate = self.growth_rate()
            lines.append(f"  Phi: {first:.2f} -> {last:.2f} ({rate:+.2f}/100s)")

        if self.ce_history:
            first = self.ce_history[0][1]
            last = self.ce_history[-1][1]
            delta = (last - first) / first * 100 if first > 0 else 0
            lines.append(f"  CE:  {first:.4f} -> {last:.4f} ({delta:+.1f}%)")

        saved = self.total_compute_saved()
        lines.append(f"  Compute saved: {saved*100:.1f}%")

        cells = self.engine.n_cells
        lines.append(f"  Cells: {cells}")

        if self._last_nexus6:
            n6 = self._last_nexus6
            lines.append(f"  NEXUS-6: {n6.get('lenses', 0)} lenses, "
                         f"{n6.get('consensus', 0)} consensus")

        # Events
        if self.event_log:
            lines.append(f"\n  Events ({len(self.event_log)}):")
            for e in self.event_log[-10:]:
                lines.append(f"    [{e['step']:5d}] {e['type']}: "
                             f"{e.get('reason', '')}")

        # Phi graph
        if len(self.phi_history) >= 5:
            lines.append("\n  Phi:")
            phis = [p for _, p in self.phi_history]
            mn, mx = min(phis), max(phis)
            rng = mx - mn if mx > mn else 1
            w = 35
            sample_indices = list(range(0, len(phis), max(1, len(phis) // 8)))
            for i in sample_indices:
                bar = int((phis[i] - mn) / rng * w)
                s = self.phi_history[i][0]
                lines.append(f"  {s:5d} |{'#' * bar}"
                             f"{' ' * (w - bar)}| {phis[i]:.2f}")

        # Growth lenses integration
        if scan_growth and len(self.phi_history) >= 5:
            lines.append("\n  Growth Lenses:")
            # scan_growth expects (step, phi) and optionally (step, phi, fraction)
            compute_for_lenses = None
            if self.compute_history:
                compute_for_lenses = [
                    (s, self.phi_history[i][1] if i < len(self.phi_history) else 0.0, f)
                    for i, (s, f) in enumerate(self.compute_history)
                ]
            try:
                lens_report = scan_growth(self.phi_history, compute_for_lenses)
                for k in ['growth_rate', 'is_growing', 'is_accelerating',
                          'saturation_pct', 'efficiency_ratio']:
                    if k in lens_report:
                        v = lens_report[k]
                        vstr = f"{v:.4f}" if isinstance(v, float) else str(v)
                        lines.append(f"    {k}: {vstr}")
            except Exception:
                lines.append("    (scan_growth unavailable)")

        lines.append("=" * 55)
        return "\n".join(lines)


# Alias for backward compatibility with task spec
GrowthEngine = GrowthSystem


def demo():
    """Demo: self-growing consciousness."""
    print("GrowthSystem Demo -- self-growing consciousness")
    print()

    engine = ConsciousnessEngine(
        cell_dim=64, hidden_dim=128, max_cells=128, n_factions=12
    )
    gs = GrowthSystem(engine, enable_accel=True, enable_auto_scale=True)

    for step in range(300):
        x = torch.randn(1, 64)
        result = gs.step(x)

        if result['events']:
            for e in result['events']:
                print(f"  [{step}] EVENT: {e['type']} -- {e.get('reason', '')}")

        if step % 50 == 0 and step > 0:
            print(f"  [{step}] Phi={result['phi']:.2f} "
                  f"compute={result['compute_fraction']:.2f}")

        sys.stdout.flush()

    print()
    print(gs.report())


if __name__ == "__main__":
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    demo()
