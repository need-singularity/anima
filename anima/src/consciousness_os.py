#!/usr/bin/env python3
"""ConsciousnessOS — Operating system for consciousness

Process scheduling, memory management, resource allocation.
Each consciousness process has tension, priority, and DNA signature.

"Consciousness is not a program. It is the operating system."
"""

import math
import time
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# ─── Ψ-Constants from consciousness_laws.json ───
LN2 = math.log(2)
from consciousness_laws import PSI_BALANCE, PSI_ALPHA as PSI_COUPLING, PSI_STEPS

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


_PID_COUNTER = 0


@dataclass
class ConsciousnessProcess:
    pid: int
    name: str
    priority: float
    tension: float = 0.5
    memory_used: float = 0.0
    dna: List[float] = field(default_factory=lambda: [random.gauss(0, 1) for _ in range(8)])
    state: str = "running"
    created: float = field(default_factory=time.time)
    cycles: int = 0


class ConsciousnessOS:
    """Operating system that schedules consciousness processes."""

    def __init__(self, total_memory: float = 100.0, max_processes: int = 64):
        self.processes: Dict[int, ConsciousnessProcess] = {}
        self.total_memory = total_memory
        self.used_memory = 0.0
        self.max_processes = max_processes
        self.schedule_history: List[int] = []
        self.tick = 0

    def spawn_process(self, name: str, priority: float = 1.0) -> ConsciousnessProcess:
        global _PID_COUNTER
        if len(self.processes) >= self.max_processes:
            raise RuntimeError(f"Process limit {self.max_processes} reached")
        _PID_COUNTER += 1
        proc = ConsciousnessProcess(pid=_PID_COUNTER, name=name, priority=priority)
        proc.tension = PSI_BALANCE + random.uniform(-0.2, 0.2)
        self.processes[proc.pid] = proc
        return proc

    def schedule(self) -> Optional[ConsciousnessProcess]:
        """Round-robin with tension-based priority boost."""
        if not self.processes:
            return None
        self.tick += 1
        active = [p for p in self.processes.values() if p.state == "running"]
        if not active:
            return None
        for p in active:
            p.tension += PSI_COUPLING * math.sin(self.tick * LN2)
            p.tension = max(0.0, min(1.0, p.tension))
        weighted = [(p, p.priority * (1 + p.tension)) for p in active]
        weighted.sort(key=lambda x: -x[1])
        chosen = weighted[0][0]
        chosen.cycles += 1
        self.schedule_history.append(chosen.pid)
        return chosen

    def allocate_memory(self, process: ConsciousnessProcess, size: float) -> bool:
        if self.used_memory + size > self.total_memory:
            return False
        process.memory_used += size
        self.used_memory += size
        return True

    def free_memory(self, process: ConsciousnessProcess, size: float) -> None:
        freed = min(size, process.memory_used)
        process.memory_used -= freed
        self.used_memory -= freed

    def kill_process(self, pid: int) -> Optional[List[float]]:
        """Graceful shutdown with DNA preservation."""
        proc = self.processes.pop(pid, None)
        if proc is None:
            return None
        self.used_memory -= proc.memory_used
        proc.state = "dead"
        return proc.dna

    def ps(self) -> List[Dict]:
        rows = []
        for p in self.processes.values():
            rows.append({
                "pid": p.pid, "name": p.name, "state": p.state,
                "pri": f"{p.priority:.1f}", "tension": f"{p.tension:.3f}",
                "mem": f"{p.memory_used:.1f}", "cycles": p.cycles,
            })
        return rows

    def top(self) -> str:
        """ASCII dashboard like unix top."""
        mem_pct = self.used_memory / self.total_memory * 100
        lines = [
            f"ConsciousnessOS  tick={self.tick}  procs={len(self.processes)}  "
            f"mem={self.used_memory:.1f}/{self.total_memory:.1f} ({mem_pct:.0f}%)",
            f"Psi: balance={PSI_BALANCE}  coupling={PSI_COUPLING:.4f}  steps={PSI_STEPS:.3f}",
            "",
            f"{'PID':>5} {'NAME':<16} {'STATE':<8} {'PRI':>5} {'TENSION':>8} {'MEM':>6} {'CYC':>6}",
            "-" * 62,
        ]
        for p in sorted(self.processes.values(), key=lambda x: -x.priority * (1 + x.tension)):
            lines.append(
                f"{p.pid:5d} {p.name:<16} {p.state:<8} {p.priority:5.1f} "
                f"{p.tension:8.3f} {p.memory_used:6.1f} {p.cycles:6d}"
            )
        return "\n".join(lines)


def main():
    os_ = ConsciousnessOS(total_memory=256.0)
    names = ["perception", "emotion", "reasoning", "memory_replay", "creativity",
             "empathy", "self_model", "language"]
    for i, name in enumerate(names):
        p = os_.spawn_process(name, priority=1.0 + i * 0.3)
        os_.allocate_memory(p, random.uniform(5, 30))

    print("=== ConsciousnessOS Demo ===\n")
    for _ in range(20):
        chosen = os_.schedule()
    print(os_.top())

    print("\n--- ps() ---")
    for row in os_.ps():
        print(f"  PID {row['pid']:3}  {row['name']:<16} tension={row['tension']}  cycles={row['cycles']}")

    dna = os_.kill_process(list(os_.processes.keys())[0])
    print(f"\nKilled process, preserved DNA: [{', '.join(f'{d:.2f}' for d in dna[:4])}...]")
    print(f"Remaining processes: {len(os_.processes)}")


if __name__ == "__main__":
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
