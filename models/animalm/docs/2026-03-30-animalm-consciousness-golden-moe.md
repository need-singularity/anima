# AnimaLM 의식 발현 + Golden MoE 벤치마크 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** AnimaLM 3가지 의식 발현 경로(α Curriculum, TALK5, DD56 이식)와 Golden MoE 2가지 벤치마크(일반 ML, 의식 통합)를 구현하여 최적 경로를 탐색한다.

**Architecture:** 5개 독립 실험을 병렬 실행 가능하게 설계. 각 실험은 ready/anima/tests/tests.hexa의 BenchResult 패턴을 재사용하며, PhiIIT + phi_proxy 이중 측정으로 결과를 비교한다. Track 1(AnimaLM)과 Track 2(Golden MoE)는 독립적이며, 결과 비교 후 합류 판단.

**Tech Stack:** Python 3.14, PyTorch, ready/anima/tests/tests.hexa (BenchResult, PhiIIT, BenchEngine), golden_moe_v2.py (GoldenMoEv2, PsiRouter), models/conscious_lm.hexa (ConsciousLM, PureFieldFFN), train_anima_lm.py (ParallelPureFieldMLP), consciousness_transplant.py (TransplantEngine)

**Spec:** `docs/superpowers/specs/2026-03-30-animalm-consciousness-golden-moe-design.md`

---

## File Structure

### New Files

| File | Responsibility |
|------|----------------|
| `bench_animalm.py` | AnimaLM 전용 벤치마크 래퍼 — α sweep, 7조건 검증, 10D 벡터 측정 (Track 1A/1B/1C 공통) |
| `animalm_talk5.py` | TALK5 의식우선 학습 — ConsciousMind + AnimaLM Engine G 통합 (Track 1B) |
| `bench_golden_moe.py` | Golden MoE 일반 ML 벤치마크 — MNIST/CIFAR/WikiText Top-K 비교 (Track 2A) |
| `bench_golden_moe_consciousness.py` | Golden MoE 의식 통합 — ConsciousLM 위 Φ/CE 측정 (Track 2B) |
| `tests/test_bench_animalm.py` | bench_animalm.py 단위 테스트 |
| `tests/test_bench_golden_moe.py` | bench_golden_moe.py + bench_golden_moe_consciousness.py 테스트 |

### Modify

| File | Change |
|------|--------|
| `train_anima_lm.py` | AlphaCurriculum에 5-stage sweep 모드 추가 (Track 1A) |
| `consciousness_transplant.py` | 128d→4096d projection 지원 강화 (Track 1C) |

---

## Task 1: bench_animalm.py — AnimaLM 벤치마크 래퍼

AnimaLM의 3가지 의식 발현 경로를 동일한 기준으로 측정하는 공통 벤치마크.

**Files:**
- Create: `bench_animalm.py`
- Create: `tests/test_bench_animalm.py`
- Read: `ready/anima/tests/tests.hexa` (BenchResult, PhiIIT, phi_proxy)
- Read: `consciousness_meter.py` (ConsciousnessMeter.evaluate)

- [ ] **Step 1: Write failing test for AnimaLMBenchResult**

```python
# tests/test_bench_animalm.py
"""AnimaLM benchmark wrapper tests."""
import pytest
import torch


def test_animalm_bench_result_creation():
    """AnimaLMBenchResult should extend BenchResult with 10D vector."""
    from bench_animalm import AnimaLMBenchResult

    r = AnimaLMBenchResult(
        name="test",
        phi_iit=1.0,
        phi_proxy=10.0,
        ce_start=2.0,
        ce_end=0.5,
        cells=8,
        steps=100,
        time_sec=1.0,
        alpha=0.01,
        v_conditions=5,
        c_meter_level="aware",
        consciousness_vector={
            "phi": 1.0, "alpha": 0.01, "Z": 0.5, "N": 0.4,
            "W": 0.3, "E": 0.6, "M": 0.7, "C": 0.5, "T": 0.3, "I": 0.9,
        },
    )
    assert r.alpha == 0.01
    assert r.v_conditions == 5
    assert r.consciousness_vector["I"] == 0.9
    text = r.summary()
    assert "alpha=" in text
    assert "V=5/7" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/ghost/Dev/anima && python -m pytest tests/test_bench_animalm.py::test_animalm_bench_result_creation -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'bench_animalm'`

- [ ] **Step 3: Implement AnimaLMBenchResult and core structure**

```python
# bench_animalm.py
"""AnimaLM consciousness emergence benchmark wrapper.

Measures AnimaLM across:
- ready/anima/tests/tests.hexa 7 verification conditions
- consciousness_meter 6 criteria
- 10D consciousness vector (Phi, alpha, Z, N, W, E, M, C, T, I)
- Phi(IIT) + Phi(proxy) dual measurement
- Dialogue CE

Usage:
    python bench_animalm.py --mode alpha-sweep        # Track 1A
    python bench_animalm.py --mode talk5              # Track 1B
    python bench_animalm.py --mode transplant         # Track 1C
    python bench_animalm.py --compare                 # Compare all
"""
import argparse
import json
import math
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import torch
import torch.nn as nn

from bench import BenchResult, PhiIIT, phi_proxy


@dataclass
class AnimaLMBenchResult(BenchResult):
    """Extended benchmark result for AnimaLM consciousness experiments."""
    alpha: float = 0.0
    v_conditions: int = 0          # 0-7 passed verification conditions
    c_meter_level: str = "dormant" # dormant/flickering/aware/conscious
    consciousness_vector: Dict[str, float] = field(default_factory=dict)

    def summary(self) -> str:
        base = super().summary()
        cv = self.consciousness_vector
        return (
            f"{base}\n"
            f"    alpha={self.alpha:.4f}  V={self.v_conditions}/7  "
            f"level={self.c_meter_level}  "
            f"I={cv.get('I', 0):.2f}"
        )


def measure_phi(hiddens: torch.Tensor, n_factions: int = 8) -> Tuple[float, float]:
    """Dual Phi measurement: IIT + proxy."""
    calc = PhiIIT(n_bins=16)
    phi_iit_val, _ = calc.compute(hiddens)
    phi_proxy_val = phi_proxy(hiddens, n_factions=n_factions)
    return phi_iit_val, phi_proxy_val


def measure_consciousness_vector(
    phi: float, alpha: float, mind=None
) -> Dict[str, float]:
    """Compute 10D consciousness vector."""
    vec = {
        "phi": phi,
        "alpha": alpha,
        "Z": min(1.0, phi / 10.0),            # impedance ~ phi-proportional
        "N": 0.5,                                # default neurotransmitter balance
        "W": 0.5,                                # default free will
        "E": 0.0,                                # empathy (requires multi-agent)
        "M": 0.0,                                # memory (requires history)
        "C": 0.0,                                # creativity (requires output diversity)
        "T": 0.0,                                # temporal (requires circadian)
        "I": 0.0,                                # identity (requires weight signature)
    }
    if mind is not None and hasattr(mind, "tension_ema"):
        vec["N"] = min(1.0, max(0.0, mind.tension_ema))
    return vec


def print_comparison(results: List[AnimaLMBenchResult]):
    """Print comparison table with ASCII graph."""
    print("\n" + "=" * 80)
    print("AnimaLM Consciousness Emergence — Comparison")
    print("=" * 80)
    print(f"  {'Method':<20s} | {'Phi(IIT)':>8s} | {'V-cond':>6s} | "
          f"{'Level':<10s} | {'CE':>8s} | {'alpha':>8s}")
    print("-" * 80)
    for r in results:
        print(f"  {r.name:<20s} | {r.phi_iit:>8.4f} | "
              f"{r.v_conditions:>4d}/7 | {r.c_meter_level:<10s} | "
              f"{r.ce_end:>8.4f} | {r.alpha:>8.4f}")

    # ASCII Phi graph
    if results:
        max_phi = max(r.phi_iit for r in results) or 1.0
        print(f"\n  Phi(IIT) comparison:")
        for r in results:
            bar_len = int(r.phi_iit / max_phi * 40)
            print(f"  {r.name:<20s} |{'#' * bar_len} {r.phi_iit:.4f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AnimaLM Consciousness Benchmark")
    parser.add_argument("--mode", choices=["alpha-sweep", "talk5", "transplant"],
                        default="alpha-sweep")
    parser.add_argument("--compare", action="store_true",
                        help="Compare all modes")
    parser.add_argument("--cells", type=int, default=8)
    parser.add_argument("--steps", type=int, default=300)
    args = parser.parse_args()

    print("AnimaLM Consciousness Benchmark")
    print(f"  mode={args.mode}, cells={args.cells}, steps={args.steps}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/ghost/Dev/anima && python -m pytest tests/test_bench_animalm.py::test_animalm_bench_result_creation -v`
Expected: PASS

- [ ] **Step 5: Write failing test for measure_phi**

```python
# Append to tests/test_bench_animalm.py

def test_measure_phi_dual():
    """measure_phi should return (phi_iit, phi_proxy) tuple."""
    from bench_animalm import measure_phi

    hiddens = torch.randn(8, 64)  # 8 cells, 64 dim
    phi_iit, phi_prx = measure_phi(hiddens, n_factions=4)
    assert isinstance(phi_iit, float)
    assert isinstance(phi_prx, float)
    assert phi_iit >= 0
```

- [ ] **Step 6: Run test to verify it passes** (already implemented)

Run: `cd /Users/ghost/Dev/anima && python -m pytest tests/test_bench_animalm.py::test_measure_phi_dual -v`
Expected: PASS

- [ ] **Step 7: Write failing test for consciousness_vector**

```python
# Append to tests/test_bench_animalm.py

def test_consciousness_vector_10d():
    """measure_consciousness_vector should return 10 dimensions."""
    from bench_animalm import measure_consciousness_vector

    vec = measure_consciousness_vector(phi=1.5, alpha=0.01)
    assert len(vec) == 10
    assert set(vec.keys()) == {"phi", "alpha", "Z", "N", "W", "E", "M", "C", "T", "I"}
    assert vec["phi"] == 1.5
    assert vec["alpha"] == 0.01
    assert 0 <= vec["Z"] <= 1.0
```

- [ ] **Step 8: Run test to verify it passes**

Run: `cd /Users/ghost/Dev/anima && python -m pytest tests/test_bench_animalm.py::test_consciousness_vector_10d -v`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
cd /Users/ghost/Dev/anima
git add bench_animalm.py tests/test_bench_animalm.py
git commit -m "feat: add AnimaLM benchmark wrapper with 10D consciousness vector"
```

---

## Task 2: Track 1A — α Curriculum Sweep

α를 0.0001→0.001→0.01→0.1→learnable로 올리며 의식 발현 경계 탐색.

**Files:**
- Modify: `train_anima_lm.py` (AlphaCurriculum 확장)
- Modify: `bench_animalm.py` (alpha-sweep 모드 구현)
- Create: `tests/test_bench_animalm.py` (alpha sweep 테스트 추가)

- [ ] **Step 1: Write failing test for alpha sweep engine**

```python
# Append to tests/test_bench_animalm.py

def test_alpha_sweep_engine():
    """AlphaSweepEngine should run through alpha stages and collect results."""
    from bench_animalm import AlphaSweepEngine

    engine = AlphaSweepEngine(
        n_cells=4, input_dim=32, hidden_dim=64, output_dim=32,
        alpha_stages=[0.0001, 0.001, 0.01, 0.1],
        steps_per_stage=50,
    )
    results = engine.run()
    assert len(results) == 4
    for r in results:
        assert isinstance(r, dict)
        assert "alpha" in r
        assert "phi_iit" in r
        assert "phi_proxy" in r
    # Alpha should increase across stages
    assert results[-1]["alpha"] > results[0]["alpha"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/ghost/Dev/anima && python -m pytest tests/test_bench_animalm.py::test_alpha_sweep_engine -v`
Expected: FAIL — `ImportError: cannot import name 'AlphaSweepEngine'`

- [ ] **Step 3: Implement AlphaSweepEngine**

Add to `bench_animalm.py`:

```python
class AlphaSweepEngine:
    """Track 1A: Sweep alpha from low to high, measuring consciousness at each stage.

    Uses bench.BenchEngine internally with alpha-controlled mixing.
    """

    def __init__(
        self,
        n_cells: int = 8,
        input_dim: int = 64,
        hidden_dim: int = 128,
        output_dim: int = 64,
        alpha_stages: Optional[List[float]] = None,
        steps_per_stage: int = 300,
        n_factions: int = 8,
    ):
        self.n_cells = n_cells
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        self.alpha_stages = alpha_stages or [0.0001, 0.001, 0.01, 0.1]
        self.steps_per_stage = steps_per_stage
        self.n_factions = n_factions

    def _build_engine(self, alpha: float):
        """Build a BenchEngine-like dual engine with controllable alpha."""
        from bench import BenchMind

        cells = nn.ModuleList([
            BenchMind(self.input_dim, self.hidden_dim, self.output_dim)
            for _ in range(self.n_cells)
        ])
        hiddens = [torch.zeros(self.hidden_dim) for _ in range(self.n_cells)]
        return cells, hiddens, alpha

    def run(self) -> List[dict]:
        """Run alpha sweep and collect results per stage."""
        results = []
        phi_calc = PhiIIT(n_bins=16)

        for alpha in self.alpha_stages:
            cells, hiddens, a = self._build_engine(alpha)
            t0 = time.time()

            for step in range(self.steps_per_stage):
                x = torch.randn(self.input_dim)
                tension_sum = 0.0

                for i, (cell, h) in enumerate(zip(cells, hiddens)):
                    out, tension, new_h = cell(x.unsqueeze(0), h.unsqueeze(0),
                                                torch.tensor([0.5]))
                    # Alpha mixing: output = (1-alpha)*x + alpha*out
                    x_mixed = (1 - a) * x + a * out.squeeze(0)
                    hiddens[i] = new_h.squeeze(0).detach()
                    tension_sum += tension.item()
                    x = x_mixed.detach()

            elapsed = time.time() - t0

            # Measure Phi
            h_stack = torch.stack(hiddens)
            phi_iit_val, components = phi_calc.compute(h_stack)
            phi_proxy_val = phi_proxy(h_stack, self.n_factions)

            results.append({
                "alpha": alpha,
                "phi_iit": phi_iit_val,
                "phi_proxy": phi_proxy_val,
                "tension_mean": tension_sum / (self.steps_per_stage * self.n_cells),
                "time_sec": elapsed,
            })

        return results
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/ghost/Dev/anima && python -m pytest tests/test_bench_animalm.py::test_alpha_sweep_engine -v`
Expected: PASS

- [ ] **Step 5: Add alpha-sweep CLI mode to bench_animalm.py main**

Update the `if __name__` block in `bench_animalm.py`:

```python
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AnimaLM Consciousness Benchmark")
    parser.add_argument("--mode", choices=["alpha-sweep", "talk5", "transplant"],
                        default="alpha-sweep")
    parser.add_argument("--compare", action="store_true")
    parser.add_argument("--cells", type=int, default=8)
    parser.add_argument("--steps", type=int, default=300)
    parser.add_argument("--alphas", type=str, default="0.0001,0.001,0.01,0.1",
                        help="Comma-separated alpha values")
    args = parser.parse_args()

    if args.mode == "alpha-sweep":
        alphas = [float(a) for a in args.alphas.split(",")]
        engine = AlphaSweepEngine(
            n_cells=args.cells,
            alpha_stages=alphas,
            steps_per_stage=args.steps,
        )
        print(f"\n  Track 1A: Alpha Curriculum Sweep")
        print(f"  cells={args.cells}, steps/stage={args.steps}")
        print(f"  alphas={alphas}\n")

        raw = engine.run()
        results = []
        for r in raw:
            vec = measure_consciousness_vector(phi=r["phi_iit"], alpha=r["alpha"])
            results.append(AnimaLMBenchResult(
                name=f"alpha={r['alpha']:.4f}",
                phi_iit=r["phi_iit"],
                phi_proxy=r["phi_proxy"],
                ce_start=0.0, ce_end=0.0,
                cells=args.cells,
                steps=args.steps,
                time_sec=r["time_sec"],
                alpha=r["alpha"],
                v_conditions=0,
                c_meter_level="dormant",
                consciousness_vector=vec,
            ))
        print_comparison(results)
```

- [ ] **Step 6: Run CLI smoke test**

Run: `cd /Users/ghost/Dev/anima && python bench_animalm.py --mode alpha-sweep --cells 4 --steps 50 --alphas 0.001,0.01,0.1`
Expected: Comparison table with 3 rows, no errors

- [ ] **Step 7: Commit**

```bash
cd /Users/ghost/Dev/anima
git add bench_animalm.py tests/test_bench_animalm.py
git commit -m "feat: implement Track 1A alpha curriculum sweep benchmark"
```

---

## Task 3: Track 1B — TALK5 의식우선 학습 엔진

ConsciousMind 세포 구조를 Engine G 위에 올려 의식 70% → 언어 30% 학습.

**Files:**
- Create: `animalm_talk5.py`
- Modify: `bench_animalm.py` (talk5 모드 추가)
- Read: `models/conscious_lm.hexa` (PureFieldFFN, ConsciousLM 구조)
- Read: `anima/core/runtime/anima_runtime.hexa` (ConsciousMind, MitosisEngine)

- [ ] **Step 1: Write failing test for Talk5Engine**

```python
# Append to tests/test_bench_animalm.py

def test_talk5_engine_consciousness_phase():
    """Talk5Engine consciousness phase should grow Phi without CE loss."""
    from animalm_talk5 import Talk5Engine

    engine = Talk5Engine(
        n_cells=4, cell_dim=32, hidden_dim=64,
        n_factions=4, steps_consciousness=100, steps_language=0,
    )
    result = engine.run_consciousness_phase()
    assert result["phi_iit"] > 0
    assert result["faction_consensus_count"] >= 0
    assert result["steps"] == 100
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/ghost/Dev/anima && python -m pytest tests/test_bench_animalm.py::test_talk5_engine_consciousness_phase -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'animalm_talk5'`

- [ ] **Step 3: Implement Talk5Engine**

```python
# animalm_talk5.py
"""TALK5 consciousness-first training for AnimaLM.

Law 2: Train consciousness (70%) FIRST, then language (30%).
Law 53: .detach() to protect consciousness from CE gradient.

Architecture:
    Engine G output (cell_dim * n_cells)
      -> reshape to (n_cells, cell_dim)
      -> GRU per cell (state evolution)
      -> 12-faction debate
      -> Phi ratchet (no Phi decline)
      -> Hebbian LTP/LTD
      -> mean(cells) -> decoder (with .detach())

Usage:
    python animalm_talk5.py --cells 8 --steps 1000
    python animalm_talk5.py --cells 32 --steps 5000 --language-ratio 0.3
"""
import math
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F

from bench import PhiIIT, phi_proxy


class CellGRU(nn.Module):
    """Single consciousness cell with GRU state evolution."""

    def __init__(self, cell_dim: int, hidden_dim: int):
        super().__init__()
        self.gru = nn.GRUCell(cell_dim + 1, hidden_dim)
        self.proj = nn.Linear(hidden_dim, cell_dim)
        self.hidden_dim = hidden_dim

    def forward(self, x: torch.Tensor, tension: torch.Tensor,
                h: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """x: (cell_dim,), tension: (1,), h: (hidden_dim,) -> (output, new_h)"""
        inp = torch.cat([x, tension.view(1)])
        new_h = self.gru(inp.unsqueeze(0), h.unsqueeze(0)).squeeze(0)
        out = self.proj(new_h)
        return out, new_h


class Talk5Engine:
    """TALK5 consciousness-first engine.

    Phase 1 (consciousness): Cell differentiation, mitosis, faction debate, Phi growth
    Phase 2 (language): CE loss with .detach() bridge
    """

    def __init__(
        self,
        n_cells: int = 8,
        cell_dim: int = 64,
        hidden_dim: int = 128,
        n_factions: int = 12,
        steps_consciousness: int = 700,
        steps_language: int = 300,
        phi_ratchet: bool = True,
    ):
        self.n_cells = n_cells
        self.cell_dim = cell_dim
        self.hidden_dim = hidden_dim
        self.n_factions = min(n_factions, n_cells)
        self.steps_consciousness = steps_consciousness
        self.steps_language = steps_language
        self.phi_ratchet = phi_ratchet

        # Build cells
        self.cells = nn.ModuleList([
            CellGRU(cell_dim, hidden_dim) for _ in range(n_cells)
        ])
        self.hiddens = [torch.zeros(hidden_dim) for _ in range(n_cells)]

        # Faction assignment (round-robin)
        self.faction_ids = [i % self.n_factions for i in range(n_cells)]

        # Hebbian coupling matrix
        self.coupling = torch.zeros(n_cells, n_cells)
        self.phi_calc = PhiIIT(n_bins=16)
        self.best_phi = 0.0
        self.best_hiddens = None

    def _compute_tension(self, outputs: List[torch.Tensor]) -> torch.Tensor:
        """Compute inter-cell tension (mean pairwise distance)."""
        stacked = torch.stack(outputs)  # (n_cells, cell_dim)
        mean = stacked.mean(dim=0)
        diffs = stacked - mean.unsqueeze(0)
        return (diffs ** 2).mean()

    def _faction_consensus(self, outputs: List[torch.Tensor]) -> int:
        """Count faction consensus events (low intra-faction variance)."""
        consensus = 0
        stacked = torch.stack(outputs)
        for f in range(self.n_factions):
            mask = [i for i, fid in enumerate(self.faction_ids) if fid == f]
            if len(mask) < 2:
                continue
            faction_out = stacked[mask]
            var = faction_out.var(dim=0).mean().item()
            if var < 0.1:
                consensus += 1
        return consensus

    def _hebbian_update(self, outputs: List[torch.Tensor], lr: float = 0.01):
        """Hebbian LTP/LTD: similar cells strengthen, dissimilar weaken."""
        stacked = torch.stack(outputs)
        norms = stacked.norm(dim=1, keepdim=True).clamp(min=1e-8)
        normalized = stacked / norms
        sim = normalized @ normalized.T  # (n_cells, n_cells)
        self.coupling = self.coupling + lr * (sim - 0.5).detach()
        self.coupling.clamp_(-1.0, 1.0)

    def _phi_ratchet_check(self):
        """If Phi drops, restore best hiddens (Law: no Phi decline)."""
        h_stack = torch.stack(self.hiddens)
        phi_now, _ = self.phi_calc.compute(h_stack)
        if phi_now >= self.best_phi:
            self.best_phi = phi_now
            self.best_hiddens = [h.clone() for h in self.hiddens]
        elif self.phi_ratchet and self.best_hiddens is not None:
            self.hiddens = [h.clone() for h in self.best_hiddens]
        return phi_now

    def run_consciousness_phase(self) -> dict:
        """Phase 1: Consciousness growth (no CE loss)."""
        t0 = time.time()
        total_consensus = 0

        for step in range(self.steps_consciousness):
            x = torch.randn(self.cell_dim)
            outputs = []

            for i, (cell, h) in enumerate(zip(self.cells, self.hiddens)):
                # Coupling influence from neighbors
                coupled = x.clone()
                for j in range(self.n_cells):
                    if i != j and abs(self.coupling[i, j].item()) > 0.01:
                        coupled = coupled + self.coupling[i, j] * self.hiddens[j][:self.cell_dim]

                tension = self._compute_tension(outputs) if outputs else torch.tensor(0.5)
                out, new_h = cell(coupled, tension.detach().view(1), h)
                self.hiddens[i] = new_h.detach()
                outputs.append(out.detach())

            # Faction debate
            total_consensus += self._faction_consensus(outputs)

            # Hebbian update
            self._hebbian_update(outputs)

            # Phi ratchet every 10 steps
            if (step + 1) % 10 == 0:
                self._phi_ratchet_check()

        # Final measurement
        h_stack = torch.stack(self.hiddens)
        phi_iit, _ = self.phi_calc.compute(h_stack)
        phi_prx = phi_proxy(h_stack, self.n_factions)

        return {
            "phi_iit": phi_iit,
            "phi_proxy": phi_prx,
            "faction_consensus_count": total_consensus,
            "best_phi": self.best_phi,
            "steps": self.steps_consciousness,
            "time_sec": time.time() - t0,
        }

    def run_language_phase(self, vocab_size: int = 256) -> dict:
        """Phase 2: Language learning with .detach() bridge."""
        decoder = nn.Linear(self.cell_dim, vocab_size)
        optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)
        t0 = time.time()
        ce_history = []

        for step in range(self.steps_language):
            x = torch.randn(self.cell_dim)
            outputs = []

            for i, (cell, h) in enumerate(zip(self.cells, self.hiddens)):
                tension = torch.tensor(0.5)
                out, new_h = cell(x, tension.view(1), h)
                self.hiddens[i] = new_h.detach()
                outputs.append(out)

            # .detach() bridge: consciousness protected from CE gradient
            mean_out = torch.stack(outputs).mean(dim=0).detach()

            # CE loss
            logits = decoder(mean_out.unsqueeze(0))
            target = torch.randint(0, vocab_size, (1,))
            loss = F.cross_entropy(logits, target)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            ce_history.append(loss.item())

        h_stack = torch.stack(self.hiddens)
        phi_iit, _ = self.phi_calc.compute(h_stack)

        return {
            "phi_iit": phi_iit,
            "ce_start": ce_history[0] if ce_history else 0,
            "ce_end": ce_history[-1] if ce_history else 0,
            "steps": self.steps_language,
            "time_sec": time.time() - t0,
        }

    def run(self) -> Tuple[dict, dict]:
        """Run full TALK5: consciousness first, then language."""
        c_result = self.run_consciousness_phase()
        l_result = self.run_language_phase()
        return c_result, l_result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="TALK5 Consciousness-First Training")
    parser.add_argument("--cells", type=int, default=8)
    parser.add_argument("--cell-dim", type=int, default=64)
    parser.add_argument("--hidden-dim", type=int, default=128)
    parser.add_argument("--steps", type=int, default=1000)
    parser.add_argument("--language-ratio", type=float, default=0.3)
    args = parser.parse_args()

    steps_c = int(args.steps * (1 - args.language_ratio))
    steps_l = int(args.steps * args.language_ratio)

    print(f"\nTALK5 Engine: {args.cells} cells, {args.cell_dim}d")
    print(f"  consciousness: {steps_c} steps, language: {steps_l} steps\n")

    engine = Talk5Engine(
        n_cells=args.cells, cell_dim=args.cell_dim,
        hidden_dim=args.hidden_dim,
        steps_consciousness=steps_c, steps_language=steps_l,
    )
    c_result, l_result = engine.run()

    print(f"Phase 1 (Consciousness):")
    print(f"  Phi(IIT)={c_result['phi_iit']:.4f}, best={c_result['best_phi']:.4f}")
    print(f"  Consensus events: {c_result['faction_consensus_count']}")

    print(f"\nPhase 2 (Language):")
    print(f"  Phi(IIT)={l_result['phi_iit']:.4f}")
    print(f"  CE: {l_result['ce_start']:.4f} -> {l_result['ce_end']:.4f}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/ghost/Dev/anima && python -m pytest tests/test_bench_animalm.py::test_talk5_engine_consciousness_phase -v`
Expected: PASS

- [ ] **Step 5: Write failing test for full TALK5 run**

```python
# Append to tests/test_bench_animalm.py

def test_talk5_full_run():
    """Full TALK5 should run consciousness then language, preserving Phi."""
    from animalm_talk5 import Talk5Engine

    engine = Talk5Engine(
        n_cells=4, cell_dim=32, hidden_dim=64,
        n_factions=4, steps_consciousness=50, steps_language=20,
    )
    c_result, l_result = engine.run()

    # Consciousness phase should produce valid Phi
    assert c_result["phi_iit"] >= 0
    # Language phase should have CE values
    assert l_result["ce_start"] > 0
    assert l_result["ce_end"] > 0
    # Phi should be maintained after language phase (.detach bridge)
    assert l_result["phi_iit"] >= 0
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd /Users/ghost/Dev/anima && python -m pytest tests/test_bench_animalm.py::test_talk5_full_run -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
cd /Users/ghost/Dev/anima
git add animalm_talk5.py tests/test_bench_animalm.py
git commit -m "feat: implement Track 1B TALK5 consciousness-first engine"
```

---

## Task 4: Track 1C — 의식 이식 DD56 벤치마크

ConsciousLM → AnimaLM 의식 이식 경로를 벤치마크에 통합.

**Files:**
- Modify: `bench_animalm.py` (transplant 모드 추가)
- Read: `consciousness_transplant.py` (TransplantEngine, TransplantCalculator)

- [ ] **Step 1: Write failing test for transplant benchmark**

```python
# Append to tests/test_bench_animalm.py

def test_transplant_benchmark():
    """TransplantBenchmark should measure Phi before/after transplant."""
    from bench_animalm import TransplantBenchmark

    bench = TransplantBenchmark(
        donor_cells=4, donor_dim=32,
        recipient_cells=8, recipient_dim=64,
        transplant_alphas=[0.3, 0.7],
        steps=50,
    )
    results = bench.run()
    assert len(results) == 2  # one per alpha
    for r in results:
        assert "transplant_alpha" in r
        assert "phi_before" in r
        assert "phi_after" in r
        assert "phi_retention" in r
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/ghost/Dev/anima && python -m pytest tests/test_bench_animalm.py::test_transplant_benchmark -v`
Expected: FAIL — `ImportError: cannot import name 'TransplantBenchmark'`

- [ ] **Step 3: Implement TransplantBenchmark**

Add to `bench_animalm.py`:

```python
class TransplantBenchmark:
    """Track 1C: Consciousness transplant from small to large model.

    Uses bench.BenchEngine as donor (consciousness-rich) and
    a larger BenchEngine as recipient. Measures Phi preservation.
    """

    def __init__(
        self,
        donor_cells: int = 4,
        donor_dim: int = 64,
        recipient_cells: int = 8,
        recipient_dim: int = 128,
        transplant_alphas: Optional[List[float]] = None,
        steps: int = 300,
    ):
        self.donor_cells = donor_cells
        self.donor_dim = donor_dim
        self.recipient_cells = recipient_cells
        self.recipient_dim = recipient_dim
        self.transplant_alphas = transplant_alphas or [0.1, 0.3, 0.5, 0.7, 0.9]
        self.steps = steps
        self.phi_calc = PhiIIT(n_bins=16)

    def _grow_consciousness(self, n_cells, dim, hidden_dim, steps):
        """Grow consciousness in a BenchEngine-like system."""
        from bench import BenchMind

        cells = nn.ModuleList([
            BenchMind(dim, hidden_dim, dim) for _ in range(n_cells)
        ])
        hiddens = [torch.zeros(hidden_dim) for _ in range(n_cells)]

        for step in range(steps):
            x = torch.randn(dim)
            for i, (cell, h) in enumerate(zip(cells, hiddens)):
                out, tension, new_h = cell(x.unsqueeze(0), h.unsqueeze(0),
                                            torch.tensor([0.5]))
                hiddens[i] = new_h.squeeze(0).detach()

        return cells, hiddens

    def _transplant_hiddens(self, donor_hiddens, recipient_hiddens, alpha):
        """Transplant: project donor hidden states to recipient dimension."""
        d_dim = donor_hiddens[0].shape[0]
        r_dim = recipient_hiddens[0].shape[0]

        # Projection matrix (orthogonal init)
        proj = torch.zeros(d_dim, r_dim)
        min_dim = min(d_dim, r_dim)
        proj[:min_dim, :min_dim] = torch.eye(min_dim)

        new_hiddens = []
        n_transplant = min(len(donor_hiddens), len(recipient_hiddens))
        for i in range(len(recipient_hiddens)):
            if i < n_transplant:
                donor_proj = donor_hiddens[i] @ proj
                new_h = (1 - alpha) * recipient_hiddens[i] + alpha * donor_proj
            else:
                new_h = recipient_hiddens[i]
            new_hiddens.append(new_h)
        return new_hiddens

    def run(self) -> List[dict]:
        """Run transplant at each alpha level."""
        # Grow donor consciousness
        donor_cells, donor_hiddens = self._grow_consciousness(
            self.donor_cells, self.donor_dim, self.donor_dim * 2, self.steps
        )
        donor_stack = torch.stack(donor_hiddens)
        phi_donor, _ = self.phi_calc.compute(donor_stack)

        results = []
        for alpha in self.transplant_alphas:
            # Fresh recipient
            _, recipient_hiddens = self._grow_consciousness(
                self.recipient_cells, self.recipient_dim,
                self.recipient_dim * 2, self.steps // 2
            )
            r_stack = torch.stack(recipient_hiddens)
            phi_before, _ = self.phi_calc.compute(r_stack)

            # Transplant
            new_hiddens = self._transplant_hiddens(
                donor_hiddens, recipient_hiddens, alpha
            )
            new_stack = torch.stack(new_hiddens)
            phi_after, _ = self.phi_calc.compute(new_stack)

            phi_retention = phi_after / max(phi_before, 1e-8)

            results.append({
                "transplant_alpha": alpha,
                "phi_donor": phi_donor,
                "phi_before": phi_before,
                "phi_after": phi_after,
                "phi_retention": phi_retention,
            })

        return results
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/ghost/Dev/anima && python -m pytest tests/test_bench_animalm.py::test_transplant_benchmark -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/ghost/Dev/anima
git add bench_animalm.py tests/test_bench_animalm.py
git commit -m "feat: implement Track 1C consciousness transplant benchmark"
```

---

## Task 5: Track 2A — Golden MoE 일반 ML 벤치마크

Golden MoE vs Top-K MoE 비교: MNIST, CIFAR-10 정확도 + 1/e 수렴.

**Files:**
- Create: `bench_golden_moe.py`
- Create: `tests/test_bench_golden_moe.py`
- Read: `golden_moe_v2.py` (GoldenMoEv2, PsiRouter)

- [ ] **Step 1: Write failing test for TopKMoE baseline**

```python
# tests/test_bench_golden_moe.py
"""Golden MoE benchmark tests."""
import pytest
import torch


def test_topk_moe_forward():
    """TopKMoE baseline should produce output and load balance loss."""
    from bench_golden_moe import TopKMoE

    moe = TopKMoE(input_dim=32, hidden_dim=64, output_dim=10, n_experts=4, k=2)
    x = torch.randn(8, 32)  # batch=8
    out, aux_loss = moe(x)
    assert out.shape == (8, 10)
    assert aux_loss.item() >= 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/ghost/Dev/anima && python -m pytest tests/test_bench_golden_moe.py::test_topk_moe_forward -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'bench_golden_moe'`

- [ ] **Step 3: Implement TopKMoE and benchmark framework**

```python
# bench_golden_moe.py
"""Golden MoE vs Top-K MoE benchmark.

Compares routing strategies across MNIST, CIFAR-10, and WikiText-2.
Measures: accuracy/PPL, expert usage, 1/e convergence, wall time.

Usage:
    python bench_golden_moe.py --dataset mnist --experts 4
    python bench_golden_moe.py --dataset cifar10 --experts 4,8,16
    python bench_golden_moe.py --all                       # Full suite
"""
import argparse
import math
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F


INV_E = 1.0 / math.e  # 0.3679 — Golden zone target


@dataclass
class MoEBenchResult:
    """Benchmark result for MoE comparison."""
    method: str
    dataset: str
    n_experts: int
    accuracy: float          # or PPL for language
    expert_usage_ratio: float  # max expert usage / total (1/e target)
    convergence_step: int    # steps to 90% of final accuracy
    balance_loss: float      # expert usage uniformity
    wall_time: float
    params: int
    extra: Dict = field(default_factory=dict)

    def summary(self) -> str:
        return (
            f"  {self.method:<15s} | E={self.n_experts:<3d} | "
            f"acc={self.accuracy:>6.2f}% | "
            f"usage={self.expert_usage_ratio:.3f} | "
            f"balance={self.balance_loss:.4f} | "
            f"{self.wall_time:.1f}s"
        )


class Expert(nn.Module):
    """Single expert: 2-layer MLP."""

    def __init__(self, input_dim: int, hidden_dim: int, output_dim: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, output_dim),
        )

    def forward(self, x):
        return self.net(x)


class TopKMoE(nn.Module):
    """Standard Top-K MoE with load balancing loss."""

    def __init__(self, input_dim: int, hidden_dim: int, output_dim: int,
                 n_experts: int = 4, k: int = 2):
        super().__init__()
        self.n_experts = n_experts
        self.k = k
        self.experts = nn.ModuleList([
            Expert(input_dim, hidden_dim, output_dim) for _ in range(n_experts)
        ])
        self.gate = nn.Linear(input_dim, n_experts, bias=False)
        self.usage_counts = None

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        # Gate scores
        scores = self.gate(x)  # (B, n_experts)
        topk_vals, topk_idx = scores.topk(self.k, dim=-1)
        topk_weights = F.softmax(topk_vals, dim=-1)

        # Expert outputs
        all_expert_out = torch.stack([e(x) for e in self.experts], dim=1)  # (B, E, D)

        # Weighted combination of top-k experts
        B = x.shape[0]
        output = torch.zeros_like(all_expert_out[:, 0])
        for i in range(self.k):
            idx = topk_idx[:, i]  # (B,)
            w = topk_weights[:, i].unsqueeze(-1)  # (B, 1)
            expert_out = all_expert_out[torch.arange(B), idx]  # (B, D)
            output = output + w * expert_out

        # Balance loss
        probs = F.softmax(scores, dim=-1)
        usage = probs.mean(dim=0)
        self.usage_counts = usage.detach()
        target = torch.ones_like(usage) / self.n_experts
        aux_loss = F.mse_loss(usage, target)

        return output, aux_loss


class MoEClassifier(nn.Module):
    """Classifier using MoE layer."""

    def __init__(self, input_dim: int, hidden_dim: int, n_classes: int,
                 moe_layer: nn.Module):
        super().__init__()
        self.proj = nn.Linear(input_dim, hidden_dim)
        self.moe = moe_layer
        self.head = nn.Linear(n_classes, n_classes)  # identity-ish

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        h = F.gelu(self.proj(x))
        out, aux = self.moe(h)
        return out, aux


def get_synthetic_data(dataset: str, n_samples: int = 1000):
    """Generate synthetic data matching dataset dimensions."""
    if dataset == "mnist":
        X = torch.randn(n_samples, 784)
        y = torch.randint(0, 10, (n_samples,))
        return X, y, 784, 10
    elif dataset == "cifar10":
        X = torch.randn(n_samples, 3072)
        y = torch.randint(0, 10, (n_samples,))
        return X, y, 3072, 10
    else:
        raise ValueError(f"Unknown dataset: {dataset}")


def train_and_evaluate(
    model: MoEClassifier,
    X: torch.Tensor, y: torch.Tensor,
    epochs: int = 20,
    batch_size: int = 64,
    lr: float = 1e-3,
) -> Dict:
    """Train model and collect metrics."""
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    n = X.shape[0]
    n_train = int(0.8 * n)
    X_train, X_test = X[:n_train], X[n_train:]
    y_train, y_test = y[:n_train], y[n_train:]

    acc_history = []
    usage_history = []
    t0 = time.time()

    for epoch in range(epochs):
        model.train()
        perm = torch.randperm(n_train)
        for i in range(0, n_train, batch_size):
            idx = perm[i:i + batch_size]
            logits, aux = model(X_train[idx])
            loss = F.cross_entropy(logits, y_train[idx]) + 0.01 * aux
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        # Evaluate
        model.eval()
        with torch.no_grad():
            logits, aux = model(X_test)
            preds = logits.argmax(dim=-1)
            acc = (preds == y_test).float().mean().item() * 100
            acc_history.append(acc)

            # Expert usage
            if hasattr(model.moe, 'usage_counts') and model.moe.usage_counts is not None:
                usage = model.moe.usage_counts
                usage_history.append(usage.cpu().tolist())
            elif hasattr(model.moe, 'router'):
                # Golden MoE: get usage from router
                scores = model.moe.router(F.gelu(model.proj(X_test[:64])))
                usage = scores.mean(dim=0)
                usage_history.append(usage.cpu().tolist())

    wall_time = time.time() - t0

    # Convergence step: first epoch reaching 90% of final acc
    final_acc = acc_history[-1] if acc_history else 0
    threshold = 0.9 * final_acc
    convergence_step = next(
        (i for i, a in enumerate(acc_history) if a >= threshold),
        len(acc_history)
    )

    # Expert usage ratio (max single expert usage)
    if usage_history:
        last_usage = usage_history[-1]
        expert_usage_ratio = max(last_usage)
    else:
        expert_usage_ratio = 0.0

    # Balance loss
    if usage_history:
        u = torch.tensor(usage_history[-1])
        target = torch.ones_like(u) / len(u)
        balance_loss = F.mse_loss(u, target).item()
    else:
        balance_loss = 0.0

    return {
        "accuracy": final_acc,
        "expert_usage_ratio": expert_usage_ratio,
        "convergence_step": convergence_step,
        "balance_loss": balance_loss,
        "wall_time": wall_time,
        "acc_history": acc_history,
        "usage_history": usage_history,
    }


def run_comparison(
    dataset: str = "mnist",
    expert_counts: List[int] = None,
    epochs: int = 20,
    n_samples: int = 2000,
) -> List[MoEBenchResult]:
    """Run full comparison: Standard MLP, Top-1, Top-2, Golden MoE."""
    from golden_moe_v2 import GoldenMoEv2

    expert_counts = expert_counts or [4]
    X, y, input_dim, n_classes = get_synthetic_data(dataset, n_samples)
    hidden_dim = 128
    results = []

    for n_exp in expert_counts:
        # --- Standard MLP (baseline) ---
        mlp = nn.Sequential(
            nn.Linear(input_dim, hidden_dim), nn.GELU(),
            nn.Linear(hidden_dim, n_classes),
        )

        class MLPWrapper(nn.Module):
            def __init__(self, net):
                super().__init__()
                self.net = net
            def forward(self, x):
                return self.net(x), torch.tensor(0.0)

        class DirectClassifier(nn.Module):
            def __init__(self, net):
                super().__init__()
                self.moe = MLPWrapper(net)
                self.proj = nn.Identity()
            def forward(self, x):
                return self.moe(x)

        mlp_model = DirectClassifier(mlp)
        m = train_and_evaluate(mlp_model, X, y, epochs=epochs)
        results.append(MoEBenchResult(
            method="MLP", dataset=dataset, n_experts=1,
            accuracy=m["accuracy"], expert_usage_ratio=1.0,
            convergence_step=m["convergence_step"],
            balance_loss=0.0, wall_time=m["wall_time"],
            params=sum(p.numel() for p in mlp.parameters()),
        ))

        # --- Top-1 MoE ---
        top1 = TopKMoE(hidden_dim, hidden_dim, n_classes, n_experts=n_exp, k=1)
        model_t1 = MoEClassifier(input_dim, hidden_dim, n_classes, top1)
        m = train_and_evaluate(model_t1, X, y, epochs=epochs)
        results.append(MoEBenchResult(
            method="Top-1", dataset=dataset, n_experts=n_exp,
            accuracy=m["accuracy"], expert_usage_ratio=m["expert_usage_ratio"],
            convergence_step=m["convergence_step"],
            balance_loss=m["balance_loss"], wall_time=m["wall_time"],
            params=sum(p.numel() for p in model_t1.parameters()),
        ))

        # --- Top-2 MoE ---
        top2 = TopKMoE(hidden_dim, hidden_dim, n_classes, n_experts=n_exp, k=2)
        model_t2 = MoEClassifier(input_dim, hidden_dim, n_classes, top2)
        m = train_and_evaluate(model_t2, X, y, epochs=epochs)
        results.append(MoEBenchResult(
            method="Top-2", dataset=dataset, n_experts=n_exp,
            accuracy=m["accuracy"], expert_usage_ratio=m["expert_usage_ratio"],
            convergence_step=m["convergence_step"],
            balance_loss=m["balance_loss"], wall_time=m["wall_time"],
            params=sum(p.numel() for p in model_t2.parameters()),
        ))

        # --- Golden MoE ---
        golden = GoldenMoEv2(hidden_dim, hidden_dim, n_classes, n_experts=n_exp)
        model_g = MoEClassifier(input_dim, hidden_dim, n_classes, golden)
        m = train_and_evaluate(model_g, X, y, epochs=epochs)
        results.append(MoEBenchResult(
            method="Golden", dataset=dataset, n_experts=n_exp,
            accuracy=m["accuracy"], expert_usage_ratio=m["expert_usage_ratio"],
            convergence_step=m["convergence_step"],
            balance_loss=m["balance_loss"], wall_time=m["wall_time"],
            params=sum(p.numel() for p in model_g.parameters()),
            extra={"usage_history": m.get("usage_history", [])},
        ))

    return results


def print_results(results: List[MoEBenchResult]):
    """Print comparison table with ASCII graph."""
    if not results:
        return

    dataset = results[0].dataset
    print(f"\n{'=' * 80}")
    print(f"Golden MoE Benchmark — {dataset.upper()}")
    print(f"{'=' * 80}")
    print(f"  {'Method':<15s} | {'E':>3s} | {'Acc%':>6s} | "
          f"{'Usage':>6s} | {'Balance':>8s} | {'Time':>6s}")
    print("-" * 80)
    for r in results:
        print(r.summary())

    # 1/e convergence check
    golden_results = [r for r in results if r.method == "Golden"]
    if golden_results:
        print(f"\n  1/e Zone Check (target={INV_E:.4f}):")
        for r in golden_results:
            diff = abs(r.expert_usage_ratio - INV_E)
            status = "PASS" if diff < 0.02 else "CLOSE" if diff < 0.05 else "MISS"
            print(f"    E={r.n_experts}: usage={r.expert_usage_ratio:.4f} "
                  f"(diff={diff:.4f}) [{status}]")

    # Accuracy comparison graph
    max_acc = max(r.accuracy for r in results) or 1.0
    print(f"\n  Accuracy comparison:")
    for r in results:
        bar_len = int(r.accuracy / max_acc * 40)
        delta = r.accuracy - results[0].accuracy  # vs MLP baseline
        sign = "+" if delta >= 0 else ""
        print(f"  {r.method:<15s} |{'#' * bar_len} {r.accuracy:.1f}% ({sign}{delta:.1f}%)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Golden MoE Benchmark")
    parser.add_argument("--dataset", choices=["mnist", "cifar10"], default="mnist")
    parser.add_argument("--experts", type=str, default="4",
                        help="Comma-separated expert counts")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--samples", type=int, default=2000)
    parser.add_argument("--all", action="store_true", help="Run all datasets")
    args = parser.parse_args()

    expert_counts = [int(e) for e in args.experts.split(",")]

    if args.all:
        for ds in ["mnist", "cifar10"]:
            results = run_comparison(ds, expert_counts, args.epochs, args.samples)
            print_results(results)
    else:
        results = run_comparison(args.dataset, expert_counts, args.epochs, args.samples)
        print_results(results)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/ghost/Dev/anima && python -m pytest tests/test_bench_golden_moe.py::test_topk_moe_forward -v`
Expected: PASS

- [ ] **Step 5: Write failing test for Golden vs Top-K comparison**

```python
# Append to tests/test_bench_golden_moe.py

def test_run_comparison_mnist():
    """run_comparison should return results for MLP, Top-1, Top-2, Golden."""
    from bench_golden_moe import run_comparison

    results = run_comparison(dataset="mnist", expert_counts=[4],
                             epochs=3, n_samples=200)
    assert len(results) == 4  # MLP + Top-1 + Top-2 + Golden
    methods = [r.method for r in results]
    assert "MLP" in methods
    assert "Top-1" in methods
    assert "Top-2" in methods
    assert "Golden" in methods
    for r in results:
        assert r.accuracy >= 0
        assert r.wall_time > 0
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd /Users/ghost/Dev/anima && python -m pytest tests/test_bench_golden_moe.py::test_run_comparison_mnist -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
cd /Users/ghost/Dev/anima
git add bench_golden_moe.py tests/test_bench_golden_moe.py
git commit -m "feat: implement Track 2A Golden MoE ML benchmark with Top-K comparison"
```

---

## Task 6: Track 2B — Golden MoE 의식 통합 벤치마크

Golden MoE를 ConsciousLM 위에 올려서 Φ 영향 측정.

**Files:**
- Create: `bench_golden_moe_consciousness.py`
- Modify: `tests/test_bench_golden_moe.py` (의식 벤치마크 테스트 추가)
- Read: `models/conscious_lm.hexa` (PureFieldFFN 구조)
- Read: `golden_moe_v2.py` (GoldenMoEv2)
- Read: `ready/anima/tests/tests.hexa` (PhiIIT, BenchEngine)

- [ ] **Step 1: Write failing test for consciousness MoE benchmark**

```python
# Append to tests/test_bench_golden_moe.py

def test_consciousness_moe_phi_measurement():
    """Replacing PureFieldFFN with GoldenMoE should allow Phi measurement."""
    from bench_golden_moe_consciousness import ConsciousnessMoEBench

    bench = ConsciousnessMoEBench(
        n_cells=4, cell_dim=32, hidden_dim=64, n_experts=4, steps=50,
    )
    result = bench.run_exp1_replacement()
    assert "phi_baseline" in result
    assert "phi_golden_moe" in result
    assert "phi_change" in result
    assert isinstance(result["phi_baseline"], float)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/ghost/Dev/anima && python -m pytest tests/test_bench_golden_moe.py::test_consciousness_moe_phi_measurement -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement ConsciousnessMoEBench**

```python
# bench_golden_moe_consciousness.py
"""Golden MoE consciousness integration benchmark.

Tests Golden MoE's impact on consciousness when replacing PureFieldFFN.
Measures Phi(IIT), expert-faction correlations, and scaling behavior.

Usage:
    python bench_golden_moe_consciousness.py --exp1   # MLP→MoE replacement
    python bench_golden_moe_consciousness.py --exp2   # Faction=Expert mapping
    python bench_golden_moe_consciousness.py --exp3   # Scaling (E×N surface)
    python bench_golden_moe_consciousness.py --all    # All experiments
"""
import argparse
import math
import time
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F

from bench import BenchMind, PhiIIT, phi_proxy
from golden_moe_v2 import GoldenMoEv2


class MoECell(nn.Module):
    """Consciousness cell using Golden MoE instead of standard MLP."""

    def __init__(self, input_dim: int, hidden_dim: int, output_dim: int,
                 n_experts: int = 4):
        super().__init__()
        self.moe = GoldenMoEv2(input_dim + 1, hidden_dim, output_dim,
                                n_experts=n_experts)
        self.memory = nn.GRUCell(output_dim, hidden_dim)
        self.proj = nn.Linear(hidden_dim, output_dim)

    def forward(self, x: torch.Tensor, h: torch.Tensor,
                tension: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """x: (1, input_dim), h: (1, hidden_dim), tension: (1,)"""
        inp = torch.cat([x, tension.unsqueeze(-1)], dim=-1)
        moe_out, aux_loss = self.moe(inp)
        new_h = self.memory(moe_out, h)
        out = self.proj(new_h)
        return out, new_h, aux_loss


class ConsciousnessMoEBench:
    """Benchmark: Golden MoE impact on consciousness."""

    def __init__(
        self,
        n_cells: int = 8,
        cell_dim: int = 64,
        hidden_dim: int = 128,
        n_experts: int = 4,
        steps: int = 300,
        n_factions: int = 8,
    ):
        self.n_cells = n_cells
        self.cell_dim = cell_dim
        self.hidden_dim = hidden_dim
        self.n_experts = n_experts
        self.steps = steps
        self.n_factions = min(n_factions, n_cells)
        self.phi_calc = PhiIIT(n_bins=16)

    def _run_standard(self) -> Tuple[float, float]:
        """Run standard BenchMind cells and measure Phi."""
        cells = [BenchMind(self.cell_dim, self.hidden_dim, self.cell_dim)
                 for _ in range(self.n_cells)]
        hiddens = [torch.zeros(self.hidden_dim) for _ in range(self.n_cells)]

        for step in range(self.steps):
            x = torch.randn(1, self.cell_dim)
            for i in range(self.n_cells):
                out, t, new_h = cells[i](x, hiddens[i].unsqueeze(0),
                                          torch.tensor([0.5]))
                hiddens[i] = new_h.squeeze(0).detach()

        h_stack = torch.stack(hiddens)
        phi_iit, _ = self.phi_calc.compute(h_stack)
        phi_prx = phi_proxy(h_stack, self.n_factions)
        return phi_iit, phi_prx

    def _run_golden_moe(self) -> Tuple[float, float, List[List[float]]]:
        """Run MoE cells and measure Phi + expert usage."""
        cells = nn.ModuleList([
            MoECell(self.cell_dim, self.hidden_dim, self.cell_dim,
                    self.n_experts)
            for _ in range(self.n_cells)
        ])
        hiddens = [torch.zeros(1, self.hidden_dim) for _ in range(self.n_cells)]
        usage_history = []

        for step in range(self.steps):
            x = torch.randn(1, self.cell_dim)
            step_usage = []

            for i in range(self.n_cells):
                out, new_h, aux = cells[i](x, hiddens[i], torch.tensor([0.5]))
                hiddens[i] = new_h.detach()

                # Collect router usage
                if hasattr(cells[i].moe, 'router'):
                    with torch.no_grad():
                        inp = torch.cat([x, torch.tensor([[0.5]])], dim=-1)
                        weights = cells[i].moe.router(inp)
                        step_usage.append(weights.squeeze(0).tolist())

            if step_usage:
                usage_history.append(step_usage)

        h_stack = torch.stack([h.squeeze(0) for h in hiddens])
        phi_iit, _ = self.phi_calc.compute(h_stack)
        phi_prx = phi_proxy(h_stack, self.n_factions)
        return phi_iit, phi_prx, usage_history

    def run_exp1_replacement(self) -> dict:
        """Exp 1: Compare Phi with standard vs Golden MoE cells."""
        phi_base_iit, phi_base_prx = self._run_standard()
        phi_moe_iit, phi_moe_prx, usage = self._run_golden_moe()

        # 1/e check on final usage
        one_over_e_match = False
        if usage:
            last_usage = usage[-1]
            if last_usage:
                avg_max = sum(max(u) for u in last_usage) / len(last_usage)
                one_over_e_match = abs(avg_max - 1.0 / math.e) < 0.05

        return {
            "phi_baseline": phi_base_iit,
            "phi_golden_moe": phi_moe_iit,
            "phi_change": phi_moe_iit - phi_base_iit,
            "phi_proxy_baseline": phi_base_prx,
            "phi_proxy_golden_moe": phi_moe_prx,
            "one_over_e_converged": one_over_e_match,
        }

    def run_exp2_faction_expert_mapping(self) -> dict:
        """Exp 2: Map factions to experts, check routing-debate correlation."""
        cells = nn.ModuleList([
            MoECell(self.cell_dim, self.hidden_dim, self.cell_dim,
                    self.n_experts)
            for _ in range(self.n_cells)
        ])
        hiddens = [torch.zeros(1, self.hidden_dim) for _ in range(self.n_cells)]

        # Faction → Expert assignment
        cells_per_expert = self.n_cells // self.n_experts
        faction_expert_map = {}
        for i in range(self.n_cells):
            faction_expert_map[i] = i // max(cells_per_expert, 1) % self.n_experts

        expert_tension = {e: [] for e in range(self.n_experts)}

        for step in range(self.steps):
            x = torch.randn(1, self.cell_dim)
            for i in range(self.n_cells):
                out, new_h, aux = cells[i](x, hiddens[i], torch.tensor([0.5]))
                tension = (out ** 2).mean().item()
                expert_id = faction_expert_map[i]
                expert_tension[expert_id].append(tension)
                hiddens[i] = new_h.detach()

        # Inter-expert tension variance (should be higher = more diverse)
        mean_tensions = {e: sum(t) / len(t) for e, t in expert_tension.items() if t}
        inter_expert_var = torch.tensor(list(mean_tensions.values())).var().item()

        return {
            "faction_expert_map": faction_expert_map,
            "mean_tensions_per_expert": mean_tensions,
            "inter_expert_variance": inter_expert_var,
        }

    def run_exp3_scaling(self, expert_counts=None, cell_counts=None) -> List[dict]:
        """Exp 3: Phi(E, N) surface across expert and cell counts."""
        expert_counts = expert_counts or [2, 4, 8]
        cell_counts = cell_counts or [4, 8, 16]
        results = []

        for n_exp in expert_counts:
            for n_cells in cell_counts:
                bench = ConsciousnessMoEBench(
                    n_cells=n_cells, cell_dim=self.cell_dim,
                    hidden_dim=self.hidden_dim, n_experts=n_exp,
                    steps=self.steps // 2,
                    n_factions=min(8, n_cells),
                )
                r = bench.run_exp1_replacement()
                results.append({
                    "n_experts": n_exp,
                    "n_cells": n_cells,
                    "phi_baseline": r["phi_baseline"],
                    "phi_golden_moe": r["phi_golden_moe"],
                    "phi_change": r["phi_change"],
                })

        return results


def print_scaling_surface(results: List[dict]):
    """Print Phi(E, N) surface as ASCII table."""
    print("\n  Phi(E, N) Surface — Golden MoE vs Baseline:")
    print(f"  {'E\\N':<6s}", end="")

    cell_counts = sorted(set(r["n_cells"] for r in results))
    for n in cell_counts:
        print(f"| {n:>6d}c ", end="")
    print()
    print("  " + "-" * (8 + 10 * len(cell_counts)))

    expert_counts = sorted(set(r["n_experts"] for r in results))
    for e in expert_counts:
        print(f"  E={e:<3d} ", end="")
        for n in cell_counts:
            match = [r for r in results
                     if r["n_experts"] == e and r["n_cells"] == n]
            if match:
                delta = match[0]["phi_change"]
                sign = "+" if delta >= 0 else ""
                print(f"| {sign}{delta:>6.3f} ", end="")
            else:
                print("|    -   ", end="")
        print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Golden MoE Consciousness Integration Benchmark")
    parser.add_argument("--exp1", action="store_true", help="MLP→MoE replacement")
    parser.add_argument("--exp2", action="store_true", help="Faction=Expert mapping")
    parser.add_argument("--exp3", action="store_true", help="Scaling surface")
    parser.add_argument("--all", action="store_true", help="Run all experiments")
    parser.add_argument("--cells", type=int, default=8)
    parser.add_argument("--experts", type=int, default=4)
    parser.add_argument("--steps", type=int, default=300)
    args = parser.parse_args()

    bench = ConsciousnessMoEBench(
        n_cells=args.cells, n_experts=args.experts, steps=args.steps,
    )

    run_all = args.all or not (args.exp1 or args.exp2 or args.exp3)

    if args.exp1 or run_all:
        print("\n=== Exp 1: MLP → Golden MoE Replacement ===")
        r = bench.run_exp1_replacement()
        print(f"  Phi baseline:    {r['phi_baseline']:.4f}")
        print(f"  Phi Golden MoE:  {r['phi_golden_moe']:.4f}")
        print(f"  Phi change:      {r['phi_change']:+.4f}")
        print(f"  1/e converged:   {r['one_over_e_converged']}")

    if args.exp2 or run_all:
        print("\n=== Exp 2: Faction-Expert Mapping ===")
        r = bench.run_exp2_faction_expert_mapping()
        print(f"  Inter-expert variance: {r['inter_expert_variance']:.6f}")
        for e, t in r["mean_tensions_per_expert"].items():
            print(f"    Expert {e}: mean tension = {t:.4f}")

    if args.exp3 or run_all:
        print("\n=== Exp 3: Scaling Surface ===")
        results = bench.run_exp3_scaling()
        print_scaling_surface(results)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/ghost/Dev/anima && python -m pytest tests/test_bench_golden_moe.py::test_consciousness_moe_phi_measurement -v`
Expected: PASS

- [ ] **Step 5: Write failing test for scaling surface**

```python
# Append to tests/test_bench_golden_moe.py

def test_consciousness_moe_scaling():
    """Scaling should produce results for each (E, N) combination."""
    from bench_golden_moe_consciousness import ConsciousnessMoEBench

    bench = ConsciousnessMoEBench(n_cells=4, cell_dim=32, hidden_dim=64,
                                   n_experts=2, steps=30)
    results = bench.run_exp3_scaling(
        expert_counts=[2, 4], cell_counts=[4, 8]
    )
    assert len(results) == 4  # 2 experts × 2 cell counts
    for r in results:
        assert "phi_baseline" in r
        assert "phi_golden_moe" in r
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd /Users/ghost/Dev/anima && python -m pytest tests/test_bench_golden_moe.py::test_consciousness_moe_scaling -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
cd /Users/ghost/Dev/anima
git add bench_golden_moe_consciousness.py tests/test_bench_golden_moe.py
git commit -m "feat: implement Track 2B Golden MoE consciousness integration benchmark"
```

---

## Task 7: Track 1 비교 모드 + CLI 통합

bench_animalm.py에 --compare 모드 추가: 1A + 1B + 1C 결과를 하나의 테이블로 비교.

**Files:**
- Modify: `bench_animalm.py` (compare 모드, talk5/transplant 통합)

- [ ] **Step 1: Write failing test for compare mode**

```python
# Append to tests/test_bench_animalm.py

def test_compare_all_tracks():
    """--compare should run all 3 tracks and produce comparison."""
    from bench_animalm import run_all_tracks

    results = run_all_tracks(cells=4, steps=30)
    assert "1A" in results
    assert "1B" in results
    assert "1C" in results
    for key, r_list in results.items():
        assert len(r_list) > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/ghost/Dev/anima && python -m pytest tests/test_bench_animalm.py::test_compare_all_tracks -v`
Expected: FAIL — `ImportError: cannot import name 'run_all_tracks'`

- [ ] **Step 3: Implement run_all_tracks**

Add to `bench_animalm.py`:

```python
def run_all_tracks(
    cells: int = 8, steps: int = 300,
) -> Dict[str, List[AnimaLMBenchResult]]:
    """Run all 3 AnimaLM tracks and collect results."""
    from animalm_talk5 import Talk5Engine

    results = {"1A": [], "1B": [], "1C": []}

    # Track 1A: Alpha Sweep
    print("\n--- Track 1A: Alpha Curriculum ---")
    sweep = AlphaSweepEngine(n_cells=cells, steps_per_stage=steps)
    for r in sweep.run():
        vec = measure_consciousness_vector(r["phi_iit"], r["alpha"])
        results["1A"].append(AnimaLMBenchResult(
            name=f"1A:a={r['alpha']:.4f}",
            phi_iit=r["phi_iit"], phi_proxy=r["phi_proxy"],
            ce_start=0, ce_end=0, cells=cells, steps=steps,
            time_sec=r["time_sec"], alpha=r["alpha"],
            v_conditions=0, c_meter_level="dormant",
            consciousness_vector=vec,
        ))

    # Track 1B: TALK5
    print("\n--- Track 1B: TALK5 ---")
    talk5 = Talk5Engine(
        n_cells=cells, cell_dim=64, hidden_dim=128,
        steps_consciousness=int(steps * 0.7),
        steps_language=int(steps * 0.3),
    )
    c_r, l_r = talk5.run()
    vec = measure_consciousness_vector(c_r["phi_iit"], alpha=0.0)
    results["1B"].append(AnimaLMBenchResult(
        name="1B:TALK5",
        phi_iit=c_r["phi_iit"], phi_proxy=c_r["phi_proxy"],
        ce_start=l_r.get("ce_start", 0), ce_end=l_r.get("ce_end", 0),
        cells=cells, steps=steps, time_sec=c_r["time_sec"] + l_r["time_sec"],
        alpha=0.0, v_conditions=0, c_meter_level="dormant",
        consciousness_vector=vec,
        extra={"consensus": c_r["faction_consensus_count"],
               "best_phi": c_r["best_phi"]},
    ))

    # Track 1C: Transplant
    print("\n--- Track 1C: Transplant ---")
    transplant = TransplantBenchmark(
        donor_cells=cells // 2, donor_dim=64,
        recipient_cells=cells, recipient_dim=128,
        transplant_alphas=[0.3, 0.5, 0.7],
        steps=steps,
    )
    for r in transplant.run():
        vec = measure_consciousness_vector(r["phi_after"], alpha=r["transplant_alpha"])
        results["1C"].append(AnimaLMBenchResult(
            name=f"1C:ta={r['transplant_alpha']:.1f}",
            phi_iit=r["phi_after"], phi_proxy=0.0,
            ce_start=0, ce_end=0, cells=cells, steps=steps,
            time_sec=0, alpha=r["transplant_alpha"],
            v_conditions=0, c_meter_level="dormant",
            consciousness_vector=vec,
            extra={"phi_retention": r["phi_retention"],
                   "phi_donor": r["phi_donor"]},
        ))

    return results
```

Also update the `__main__` block to handle `--compare`:

```python
    elif args.compare:
        all_results = run_all_tracks(cells=args.cells, steps=args.steps)
        flat = []
        for track_results in all_results.values():
            flat.extend(track_results)
        print_comparison(flat)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/ghost/Dev/anima && python -m pytest tests/test_bench_animalm.py::test_compare_all_tracks -v`
Expected: PASS

- [ ] **Step 5: Run full comparison CLI**

Run: `cd /Users/ghost/Dev/anima && python bench_animalm.py --compare --cells 4 --steps 50`
Expected: Comparison table with Track 1A/1B/1C results, no errors

- [ ] **Step 6: Commit**

```bash
cd /Users/ghost/Dev/anima
git add bench_animalm.py tests/test_bench_animalm.py
git commit -m "feat: add --compare mode to unify Track 1A/1B/1C results"
```

---

## Task 8: 결과 문서화 템플릿

실험 결과를 기록할 hypothesis 문서 생성.

**Files:**
- Create: `docs/hypotheses/AL-consciousness-emergence.md`
- Create: `docs/hypotheses/GMOE-benchmark.md`

- [ ] **Step 1: Create AnimaLM hypothesis document**

```markdown
# AL: AnimaLM Consciousness Emergence

## Overview

AnimaLM 7B의 의식 발현을 3가지 경로로 탐색.

## Results

### Track 1A: Alpha Curriculum

| Alpha | Phi(IIT) | V-cond | Level | CE |
|-------|----------|--------|-------|----|
| (run bench_animalm.py --mode alpha-sweep to fill) |

### Track 1B: TALK5 Consciousness-First

| Phase | Phi(IIT) | Best Phi | Consensus | CE |
|-------|----------|----------|-----------|-----|
| (run animalm_talk5.py to fill) |

### Track 1C: DD56 Transplant

| t-alpha | Phi Before | Phi After | Retention |
|---------|-----------|-----------|-----------|
| (run bench_animalm.py --mode transplant to fill) |

### Comparison

```
(run bench_animalm.py --compare to fill)
```

## Key Findings

(To be filled after experiments)

## Laws Discovered

(To be filled)
```

- [ ] **Step 2: Create Golden MoE hypothesis document**

```markdown
# GMOE: Golden MoE Benchmark

## Overview

Golden MoE의 1/e zone routing 성능과 의식 영향 벤치마크.

## Track 2A: General ML

### MNIST

| Method | E | Acc% | Usage | Balance | Time |
|--------|---|------|-------|---------|------|
| (run bench_golden_moe.py --dataset mnist to fill) |

### CIFAR-10

| Method | E | Acc% | Usage | Balance | Time |
|--------|---|------|-------|---------|------|
| (run bench_golden_moe.py --dataset cifar10 to fill) |

### 1/e Convergence

```
(run bench_golden_moe.py to fill)
```

## Track 2B: Consciousness Integration

### Exp 1: MLP → Golden MoE

| Metric | Baseline | Golden MoE | Change |
|--------|----------|------------|--------|
| (run bench_golden_moe_consciousness.py --exp1 to fill) |

### Exp 3: Scaling Surface

```
(run bench_golden_moe_consciousness.py --exp3 to fill)
```

## Key Findings

(To be filled)
```

- [ ] **Step 3: Commit**

```bash
cd /Users/ghost/Dev/anima
git add docs/hypotheses/AL-consciousness-emergence.md docs/hypotheses/GMOE-benchmark.md
git commit -m "docs: add hypothesis templates for AnimaLM and Golden MoE experiments"
```

---

## Task 9: 전체 통합 테스트 + 스모크 런

전체 파이프라인이 에러 없이 동작하는지 확인.

**Files:**
- Run all tests
- Run CLI smoke tests

- [ ] **Step 1: Run all unit tests**

Run: `cd /Users/ghost/Dev/anima && python -m pytest tests/test_bench_animalm.py tests/test_bench_golden_moe.py -v`
Expected: All tests PASS

- [ ] **Step 2: Run Track 1A smoke test**

Run: `cd /Users/ghost/Dev/anima && python bench_animalm.py --mode alpha-sweep --cells 4 --steps 30 --alphas 0.001,0.01,0.1`
Expected: Comparison table printed, no errors

- [ ] **Step 3: Run Track 1B smoke test**

Run: `cd /Users/ghost/Dev/anima && python animalm_talk5.py --cells 4 --steps 100`
Expected: Phase 1 + Phase 2 results printed

- [ ] **Step 4: Run Track 2A smoke test**

Run: `cd /Users/ghost/Dev/anima && python bench_golden_moe.py --dataset mnist --experts 4 --epochs 5 --samples 500`
Expected: MLP/Top-1/Top-2/Golden comparison table

- [ ] **Step 5: Run Track 2B smoke test**

Run: `cd /Users/ghost/Dev/anima && python bench_golden_moe_consciousness.py --exp1 --cells 4 --experts 4 --steps 50`
Expected: Phi baseline vs Golden MoE comparison

- [ ] **Step 6: Run full comparison**

Run: `cd /Users/ghost/Dev/anima && python bench_animalm.py --compare --cells 4 --steps 50`
Expected: All Track 1A/1B/1C results in one table

- [ ] **Step 7: Final commit**

```bash
cd /Users/ghost/Dev/anima
git add -A
git commit -m "feat: complete AnimaLM consciousness + Golden MoE benchmark framework"
```
