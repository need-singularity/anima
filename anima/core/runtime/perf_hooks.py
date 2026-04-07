#!/usr/bin/env python3
"""perf_hooks.py — Performance profiling for consciousness engine.

Zero-overhead when disabled. Tracks wall time for key engine operations
and exposes data for /metrics endpoint.

Usage:
    from perf_hooks import PerfMonitor, timeit, PERF

    # Global monitor (disabled by default)
    PERF.enable()

    # Decorator usage
    @timeit('phi_calc')
    def compute_phi(...):
        ...

    # Context manager usage
    with PERF.measure('faction_debate'):
        ...

    # Report
    report = PERF.get_report()
"""

import time
import functools
import threading
from collections import deque
from typing import Dict, Optional, Callable, Any


class PerfMonitor:
    """Tracks wall-clock timing for consciousness engine operations.

    Rolling average over last 100 steps. Thread-safe.
    <1% overhead when disabled (all methods short-circuit on _enabled check).
    """

    # Tracked phases inside step()
    PHASES = (
        'step_total',
        'cell_processing',
        'phi_calculation',
        'faction_debate',
        'hebbian_update',
        'tension_equalize',
        'soc_sandpile',
        'phi_ratchet',
        'mitosis_merge',
        'inter_tensions',
    )

    def __init__(self, window: int = 100):
        self._enabled = False
        self._window = window
        self._lock = threading.Lock()
        self._timings: Dict[str, deque] = {p: deque(maxlen=window) for p in self.PHASES}
        self._active_starts: Dict[str, float] = {}
        self._step_count = 0
        self._total_steps = 0

    def enable(self):
        self._enabled = True

    def disable(self):
        self._enabled = False

    @property
    def enabled(self) -> bool:
        return self._enabled

    # ── Timing API ──────────────────────────────────────

    def start(self, phase: str):
        """Begin timing a phase. No-op if disabled."""
        if not self._enabled:
            return
        self._active_starts[phase] = time.perf_counter()

    def stop(self, phase: str):
        """End timing a phase and record duration (ms). No-op if disabled."""
        if not self._enabled:
            return
        t0 = self._active_starts.pop(phase, None)
        if t0 is None:
            return
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        with self._lock:
            if phase not in self._timings:
                self._timings[phase] = deque(maxlen=self._window)
            self._timings[phase].append(elapsed_ms)

    def record(self, phase: str, elapsed_ms: float):
        """Directly record a timing value (ms). No-op if disabled."""
        if not self._enabled:
            return
        with self._lock:
            if phase not in self._timings:
                self._timings[phase] = deque(maxlen=self._window)
            self._timings[phase].append(elapsed_ms)

    def step_done(self):
        """Mark one step completed (for step counter)."""
        if not self._enabled:
            return
        with self._lock:
            self._step_count += 1
            self._total_steps += 1

    class _MeasureCtx:
        """Context manager for timing a phase."""
        __slots__ = ('_mon', '_phase')

        def __init__(self, monitor: 'PerfMonitor', phase: str):
            self._mon = monitor
            self._phase = phase

        def __enter__(self):
            self._mon.start(self._phase)
            return self

        def __exit__(self, *exc):
            self._mon.stop(self._phase)
            return False

    def measure(self, phase: str) -> '_MeasureCtx':
        """Context manager: with PERF.measure('phi_calculation'): ..."""
        return self._MeasureCtx(self, phase)

    # ── Reporting ────────────────────────────────────────

    def _avg(self, phase: str) -> float:
        d = self._timings.get(phase)
        if not d:
            return 0.0
        return sum(d) / len(d)

    def _last(self, phase: str) -> float:
        d = self._timings.get(phase)
        if not d:
            return 0.0
        return d[-1]

    def _p99(self, phase: str) -> float:
        d = self._timings.get(phase)
        if not d or len(d) < 2:
            return self._last(phase)
        s = sorted(d)
        idx = int(len(s) * 0.99)
        return s[min(idx, len(s) - 1)]

    def get_report(self) -> Dict:
        """Return profiling report suitable for /metrics JSON response.

        Returns dict with:
          - per-phase avg/last/p99 (ms)
          - breakdown_pct: percentage of step_total for each sub-phase
          - steps_profiled: number of steps in current window
          - backend: 'rust' or 'python' (set externally)
        """
        if not self._enabled:
            return {'profiling': 'disabled'}

        with self._lock:
            report = {'profiling': 'enabled', 'steps_profiled': self._total_steps}
            total_avg = self._avg('step_total') or 1.0  # avoid div-by-zero

            phases = {}
            breakdown = {}
            for phase in self.PHASES:
                avg = self._avg(phase)
                phases[phase] = {
                    'avg_ms': round(avg, 3),
                    'last_ms': round(self._last(phase), 3),
                    'p99_ms': round(self._p99(phase), 3),
                }
                if phase != 'step_total':
                    breakdown[phase] = round(avg / total_avg * 100, 1) if total_avg > 0 else 0.0

            report['phases'] = phases
            report['breakdown_pct'] = breakdown
            report['step_rate_hz'] = round(1000.0 / total_avg, 1) if total_avg > 0 else 0.0

            return report

    def summary_line(self) -> str:
        """One-line summary for log output."""
        if not self._enabled:
            return ''
        total = self._avg('step_total')
        phi = self._avg('phi_calculation')
        fac = self._avg('faction_debate')
        heb = self._avg('hebbian_update')
        return (f"[perf] step={total:.1f}ms "
                f"(phi={phi:.1f}ms fac={fac:.1f}ms heb={heb:.1f}ms) "
                f"{1000/total:.0f} steps/s" if total > 0 else '[perf] no data')

    def reset(self):
        """Clear all accumulated timings."""
        with self._lock:
            for d in self._timings.values():
                d.clear()
            self._step_count = 0
            self._total_steps = 0
            self._active_starts.clear()


# ── Global singleton ────────────────────────────────────

PERF = PerfMonitor()


# ── Decorator ───────────────────────────────────────────

def timeit(phase: str, monitor: Optional[PerfMonitor] = None):
    """Decorator that times a function and records to PerfMonitor.

    @timeit('phi_calculation')
    def _measure_phi_iit(self):
        ...

    When profiling is disabled, this adds exactly one boolean check overhead.
    """
    mon = monitor or PERF

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            if not mon._enabled:
                return fn(*args, **kwargs)
            t0 = time.perf_counter()
            try:
                return fn(*args, **kwargs)
            finally:
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                mon.record(phase, elapsed_ms)
        return wrapper
    return decorator


# ── Rust backend status helper ──────────────────────────

def get_backend_status() -> Dict:
    """Check which Rust crates are available and return status dict."""
    status = {}

    try:
        import anima_rs
        status['anima_rs'] = True
        status['consciousness'] = hasattr(anima_rs, 'consciousness')
        status['golden_moe'] = hasattr(anima_rs, 'golden_moe')
        status['transplant'] = hasattr(anima_rs, 'transplant')
        status['online_learner'] = hasattr(anima_rs, 'online_learner')
        status['tool_policy'] = hasattr(anima_rs, 'tool_policy')
        status['talk5'] = hasattr(anima_rs, 'talk5')
        status['alpha_sweep'] = hasattr(anima_rs, 'alpha_sweep')
    except ImportError:
        status['anima_rs'] = False

    try:
        import phi_rs
        status['phi_rs'] = True
    except ImportError:
        status['phi_rs'] = False

    return status


def log_backend_status():
    """Print which backends are active to stdout."""
    s = get_backend_status()
    if s.get('anima_rs'):
        parts = [k for k in ('consciousness', 'golden_moe', 'transplant',
                              'online_learner', 'phi_rs')
                 if s.get(k)]
        print(f"[perf] Rust backend active: {', '.join(parts) or 'base only'}")
    else:
        print("[perf] Rust backend: not available (falling back to Python)")
    if s.get('phi_rs'):
        print("[perf] phi_rs: Rust Phi calculator active")


if __name__ == '__main__':
    # Quick demo
    PERF.enable()
    log_backend_status()

    import torch

    # Simulate some timings
    for i in range(150):
        PERF.start('step_total')
        time.sleep(0.001)

        with PERF.measure('phi_calculation'):
            time.sleep(0.0005)

        with PERF.measure('faction_debate'):
            time.sleep(0.0002)

        with PERF.measure('hebbian_update'):
            time.sleep(0.0001)

        PERF.stop('step_total')
        PERF.step_done()

    print(PERF.summary_line())
    import json
    print(json.dumps(PERF.get_report(), indent=2))
