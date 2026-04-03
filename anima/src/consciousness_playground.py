"""ConsciousnessPlayground — Interactive parameter tuning sandbox."""

import math
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Any

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


LN2 = math.log(2)
PSI_BALANCE = 0.5
PSI_COUPLING = LN2 / 2**5.5
PSI_STEPS = 3 / LN2


@dataclass
class SandboxState:
    cells: np.ndarray
    tensions: np.ndarray
    phi: float = 0.0
    step: int = 0


class ConsciousnessPlayground:
    """Interactive parameter tuning sandbox for consciousness experiments."""

    def __init__(self):
        self.params: Dict[str, float] = {
            "gate": PSI_BALANCE,
            "ca_rules": 110.0,
            "coupling": PSI_COUPLING,
            "tension": 0.5,
            "n_cells": 8.0,
        }
        self.state: SandboxState | None = None
        self.history: List[Dict[str, Any]] = []

    def create_sandbox(self, n_cells: int = 8, dim: int = 64) -> SandboxState:
        """Create a mini consciousness sandbox."""
        self.params["n_cells"] = float(n_cells)
        cells = np.random.randn(n_cells, dim) * 0.1
        tensions = np.zeros(n_cells)
        for i in range(n_cells):
            for j in range(i + 1, n_cells):
                t = np.linalg.norm(cells[i] - cells[j])
                tensions[i] += t
                tensions[j] += t
        tensions /= max(n_cells - 1, 1)
        phi = float(np.var(cells) - np.mean([np.var(cells[i]) for i in range(n_cells)]))
        self.state = SandboxState(cells=cells, tensions=tensions, phi=max(0, phi))
        return self.state

    def tweak(self, param: str, value: float) -> Dict[str, Any]:
        """Change a parameter live and evolve one step."""
        if param not in self.params:
            raise ValueError(f"Unknown param: {param}. Available: {list(self.params.keys())}")
        old = self.params[param]
        self.params[param] = value
        if self.state is None:
            self.create_sandbox()
        n = int(self.params["n_cells"])
        c = self.params["coupling"]
        g = self.params["gate"]
        noise = np.random.randn(*self.state.cells.shape) * c
        gate_mask = (np.random.rand(n, 1) < g).astype(float)
        self.state.cells += noise * gate_mask
        for i in range(n):
            self.state.tensions[i] = 0
            for j in range(n):
                if i != j:
                    self.state.tensions[i] += np.linalg.norm(self.state.cells[i] - self.state.cells[j])
            self.state.tensions[i] /= max(n - 1, 1)
        self.state.phi = float(np.var(self.state.cells) - np.mean([np.var(self.state.cells[i]) for i in range(n)]))
        self.state.phi = max(0, self.state.phi)
        self.state.step += 1
        delta = {"param": param, "old": old, "new": value, "phi": self.state.phi, "step": self.state.step}
        self.history.append(delta)
        return delta

    def observe(self) -> Dict[str, Any]:
        """Current state snapshot."""
        if self.state is None:
            self.create_sandbox()
        return {
            "step": self.state.step,
            "phi": round(self.state.phi, 6),
            "mean_tension": round(float(np.mean(self.state.tensions)), 4),
            "max_tension": round(float(np.max(self.state.tensions)), 4),
            "cell_norm": round(float(np.linalg.norm(self.state.cells)), 4),
            "params": dict(self.params),
        }

    def experiment(self, param: str, values: List[float]) -> List[Dict[str, Any]]:
        """Sweep a parameter over a range and collect results."""
        results = []
        original = self.params.get(param, 0)
        for v in values:
            self.tweak(param, v)
            obs = self.observe()
            results.append({"value": v, "phi": obs["phi"], "tension": obs["mean_tension"]})
        self.params[param] = original
        return results

    def render(self) -> str:
        """ASCII visualization of current state."""
        if self.state is None:
            self.create_sandbox()
        n = int(self.params["n_cells"])
        lines = [f"=== Consciousness Playground (step {self.state.step}) ==="]
        lines.append(f"Phi: {self.state.phi:.4f}  |  Params: gate={self.params['gate']:.2f} coupling={self.params['coupling']:.6f}")
        lines.append("")
        max_t = max(float(np.max(self.state.tensions)), 0.001)
        for i in range(n):
            bar_len = int(self.state.tensions[i] / max_t * 30)
            bar = "#" * bar_len
            lines.append(f"  Cell {i:2d} |{bar:<30}| T={self.state.tensions[i]:.3f}")
        lines.append(f"\n  Psi constants: LN2={LN2:.4f}  BALANCE={PSI_BALANCE}  COUPLING={PSI_COUPLING:.6f}  STEPS={PSI_STEPS:.4f}")
        return "\n".join(lines)


def main():
    pg = ConsciousnessPlayground()
    pg.create_sandbox(n_cells=8, dim=64)
    print(pg.render())
    print("\n--- Tweaking gate from 0.1 to 0.9 ---")
    results = pg.experiment("gate", [0.1, 0.3, 0.5, 0.7, 0.9])
    for r in results:
        bar = "#" * int(r["phi"] * 500)
        print(f"  gate={r['value']:.1f}  Phi={r['phi']:.5f}  {bar}")
    print("\n--- Final state ---")
    print(pg.render())


if __name__ == "__main__":
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
