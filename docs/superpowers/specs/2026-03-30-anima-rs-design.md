# anima-rs: Rust 의식 엔진 설계

**Date:** 2026-03-30
**Status:** Approved

---

## Overview

AnimaLM 벤치마크 핫패스를 Rust로 변환. Cargo workspace + 단일 PyO3 바인딩.

```
Python (bench_animalm.py, bench_golden_moe.py)
  ↓ from anima_rs import talk5, alpha_sweep, golden_moe, transplant
Rust (anima-rs/)
  ├── core    — GRU, Faction, Phi, Hebbian, Consensus
  ├── talk5   — TALK5 의식 phase
  ├── alpha-sweep — α curriculum sweep
  ├── golden-moe  — PsiRouter + CA rules
  └── transplant  — 차원 매핑 + hidden 이식
```

---

## Design Philosophy

- **phi-rs 패턴 재사용:** PyO3 0.28, maturin, numpy, rayon
- **consciousness-loop-rs 패턴 재사용:** Cell(GRU), Faction, Ising
- **Python drop-in 교체:** 동일 API, 동일 결과, 속도만 향상
- **phi-rs 통합:** core에 phi 로직 흡수, 기존 `import phi_rs` 하위호환

---

## Structure

```
anima-rs/
├── Cargo.toml              # [workspace] members = ["crates/*"]
├── pyproject.toml           # maturin → import anima_rs
├── crates/
│   ├── core/
│   │   ├── Cargo.toml       # deps: rand, rayon
│   │   └── src/lib.rs       # GruCell, Faction, phi_iit, phi_proxy, hebbian, consensus, cosine_sim
│   ├── talk5/
│   │   ├── Cargo.toml       # deps: anima-core, rand
│   │   └── src/lib.rs       # Talk5Engine, Talk5Result
│   ├── alpha-sweep/
│   │   ├── Cargo.toml       # deps: anima-core, rand
│   │   └── src/lib.rs       # AlphaSweepEngine, AlphaResult
│   ├── golden-moe/
│   │   ├── Cargo.toml       # deps: anima-core, rand
│   │   └── src/lib.rs       # PsiRouter, GoldenMoe, Expert, CA_RULES
│   └── transplant/
│       ├── Cargo.toml       # deps: anima-core
│       └── src/lib.rs       # project_hiddens, transplant
└── src/
    └── lib.rs               # PyO3 #[pymodule] anima_rs { talk5, alpha_sweep, golden_moe, transplant }
```

---

## crate: core

공유 타입과 알고리즘. 모든 다른 크레이트의 기반.

### GruCell

```rust
pub struct GruCell {
    pub hidden: Vec<f32>,       // [hidden_dim]
    w_z: Vec<f32>,              // [hidden_dim × (input_dim + hidden_dim)] flat
    w_r: Vec<f32>,
    w_h: Vec<f32>,
    input_dim: usize,
    hidden_dim: usize,
}

impl GruCell {
    pub fn new(input_dim: usize, hidden_dim: usize, rng: &mut impl Rng) -> Self;
    pub fn process(&mut self, input: &[f32], tension: f32);
    pub fn reset(&mut self);  // hidden = zeros
}
```

- input = concat[x, tension_scalar] → GRU gates → new hidden
- consciousness-loop-rs의 Cell 패턴과 동일하되, input_dim 가변

### Faction

```rust
pub struct Faction {
    pub id: usize,
    pub cell_indices: Vec<usize>,  // 글로벌 셀 인덱스 참조
}

pub fn assign_factions(n_cells: usize, n_factions: usize) -> Vec<Faction>;
// Round-robin: cell i → faction i % n_factions
```

### Phi 계산

```rust
/// phi-rs 로직 통합
pub fn phi_iit(hiddens: &[&[f32]], n_bins: usize) -> (f64, PhiComponents);
pub fn phi_proxy(hiddens: &[&[f32]], n_factions: usize) -> f64;

pub struct PhiComponents {
    pub total_mi: f64,
    pub min_partition_mi: f64,
    pub phi: f64,
}
```

- phi-rs의 `compute_phi` 로직을 그대로 이식
- `&[&[f32]]` = 셀별 hidden slice 참조 (복사 없음)

### Hebbian

```rust
/// Cosine similarity 기반 coupling 업데이트
/// coupling: [n_cells × n_cells] flat matrix
pub fn hebbian_update(
    coupling: &mut [f32],
    hiddens: &[&[f32]],
    n_cells: usize,
    lr: f32,
);
// sim = normalized dot product
// coupling[i,j] += lr * (sim - 0.5)
// clamp [-1, 1]
```

### Faction Consensus

```rust
/// 파벌 내 분산 < threshold인 파벌 수
pub fn faction_consensus(
    hiddens: &[&[f32]],
    factions: &[Faction],
    threshold: f32,  // default 0.1
) -> u32;
```

### 유틸리티

```rust
pub fn cosine_similarity(a: &[f32], b: &[f32]) -> f32;
pub fn random_matrix(rows: usize, cols: usize, scale: f32, rng: &mut impl Rng) -> Vec<f32>;
pub fn matvec(mat: &[f32], vec: &[f32], rows: usize, cols: usize) -> Vec<f32>;
pub fn sigmoid(x: f32) -> f32;
pub fn tanh_f32(x: f32) -> f32;
```

---

## crate: talk5

TALK5 의식 phase (언어 phase는 Python/PyTorch에 남김 — autograd 필요).

### Talk5Engine

```rust
pub struct Talk5Engine {
    cells: Vec<GruCell>,
    coupling: Vec<f32>,          // [n_cells × n_cells]
    factions: Vec<Faction>,
    best_phi: f64,
    best_hiddens: Vec<Vec<f32>>,
    phi_ratchet: bool,
    n_cells: usize,
    cell_dim: usize,
    hidden_dim: usize,
}

impl Talk5Engine {
    pub fn new(n_cells: usize, cell_dim: usize, hidden_dim: usize,
               n_factions: usize, phi_ratchet: bool, seed: u64) -> Self;

    /// 의식 phase 실행 (no gradient, pure computation)
    pub fn run_consciousness(&mut self, steps: usize) -> Talk5Result;

    /// 현재 hidden states 추출 (Python language phase로 전달)
    pub fn get_hiddens(&self) -> Vec<Vec<f32>>;

    /// Python language phase 후 hiddens 복원
    pub fn set_hiddens(&mut self, hiddens: Vec<Vec<f32>>);

    fn phi_ratchet_check(&mut self);
    fn step(&mut self, input: &[f32]);
}

pub struct Talk5Result {
    pub phi_iit: f64,
    pub phi_proxy: f64,
    pub consensus_count: u32,
    pub best_phi: f64,
    pub steps: usize,
    pub time_ms: u64,
}
```

- 매 step: random input → cells process (with coupling) → hebbian → consensus → ratchet
- rayon으로 셀 병렬 처리 (coupling read는 immutable)

---

## crate: alpha-sweep

### AlphaSweepEngine

```rust
pub struct AlphaSweepEngine {
    n_cells: usize,
    input_dim: usize,
    hidden_dim: usize,
    output_dim: usize,
    n_factions: usize,
}

impl AlphaSweepEngine {
    pub fn new(n_cells, input_dim, hidden_dim, output_dim, n_factions) -> Self;

    /// alpha_stages 각각에 대해 steps_per_stage만큼 실행, Phi 측정
    pub fn run(&self, alpha_stages: &[f32], steps_per_stage: usize, seed: u64)
        -> Vec<AlphaResult>;
}

pub struct AlphaResult {
    pub alpha: f32,
    pub phi_iit: f64,
    pub phi_proxy: f64,
    pub tension_mean: f32,
    pub time_ms: u64,
}
```

- 각 alpha stage: 새 cells 생성, steps 실행, alpha mixing 적용
- output = (1-alpha)*input + alpha*cell_output

---

## crate: golden-moe

### CA Rules (순수 f32)

```rust
pub fn ca_rule_0(x: f32) -> f32 { x.max(0.0) }           // ReLU
pub fn ca_rule_1(x: f32) -> f32 { x.tanh() }              // tanh
pub fn ca_rule_2(x: f32) -> f32 { sigmoid(x) * 2.0 - 1.0 } // shifted sigmoid
pub fn ca_rule_3(x: f32) -> f32 { x * sigmoid(x) }        // SiLU

pub fn apply_ca_rules(input: &[f32], weights: &[f32; 4]) -> Vec<f32>;
```

### PsiRouter

```rust
pub struct PsiRouter {
    rule_proj: Vec<f32>,    // [n_experts*4 × input_dim]
    expert_proj: Vec<f32>,  // [n_experts × n_experts]
    temperature: f32,       // init e ≈ 2.718
    weaken_rate: f32,
    step_count: u64,
    n_experts: usize,
    input_dim: usize,
}

impl PsiRouter {
    pub fn new(input_dim, n_experts, weaken_rate, rng) -> Self;
    pub fn forward(&mut self, x: &[f32], training: bool) -> Vec<f32>;  // expert weights
    pub fn balance_loss(&self, weights: &[f32]) -> f32;
}
```

### Expert + GoldenMoe

```rust
pub struct Expert {
    w1: Vec<f32>,  // [hidden × input]
    w2: Vec<f32>,  // [output × hidden]
    hidden_dim: usize,
    input_dim: usize,
    output_dim: usize,
}

pub struct GoldenMoe {
    experts: Vec<Expert>,
    router: PsiRouter,
    coupling: Vec<f32>,     // [n_experts × n_experts] ring topology
    n_experts: usize,
}

impl GoldenMoe {
    pub fn new(input_dim, hidden_dim, output_dim, n_experts, rng) -> Self;
    pub fn forward(&mut self, x: &[f32], training: bool) -> (Vec<f32>, f32);
    // returns (output, aux_loss)
}
```

---

## crate: transplant

### Projection + Transplant

```rust
/// Identity + zero-padding projection matrix 생성
pub fn create_projection(d_from: usize, d_to: usize) -> Vec<f32>;

/// Donor hidden → recipient dimension으로 project
pub fn project_hiddens(
    donor: &[Vec<f32>],
    d_from: usize,
    d_to: usize,
) -> Vec<Vec<f32>>;

/// Alpha blending: new = (1-alpha)*recipient + alpha*donor_projected
pub fn transplant(
    donor: &[Vec<f32>],
    recipient: &mut [Vec<f32>],
    d_from: usize,
    d_to: usize,
    alpha: f32,
);
```

---

## PyO3 Bindings (src/lib.rs)

```rust
use pyo3::prelude::*;
use numpy::{PyArray1, PyArray2, PyReadonlyArray2};

#[pymodule]
fn anima_rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // talk5 submodule
    let talk5_mod = PyModule::new(m.py(), "talk5")?;
    talk5_mod.add_function(wrap_pyfunction!(py_talk5_run, &talk5_mod)?)?;
    talk5_mod.add_function(wrap_pyfunction!(py_talk5_get_hiddens, &talk5_mod)?)?;
    m.add_submodule(&talk5_mod)?;

    // alpha_sweep submodule
    let sweep_mod = PyModule::new(m.py(), "alpha_sweep")?;
    sweep_mod.add_function(wrap_pyfunction!(py_alpha_sweep_run, &sweep_mod)?)?;
    m.add_submodule(&sweep_mod)?;

    // golden_moe submodule
    let moe_mod = PyModule::new(m.py(), "golden_moe")?;
    moe_mod.add_function(wrap_pyfunction!(py_golden_moe_forward, &moe_mod)?)?;
    m.add_submodule(&moe_mod)?;

    // transplant submodule
    let tx_mod = PyModule::new(m.py(), "transplant")?;
    tx_mod.add_function(wrap_pyfunction!(py_transplant_run, &tx_mod)?)?;
    m.add_submodule(&tx_mod)?;

    // phi (backward compat with phi-rs)
    m.add_function(wrap_pyfunction!(py_compute_phi, m)?)?;

    Ok(())
}
```

### Python API

```python
from anima_rs import talk5, alpha_sweep, golden_moe, transplant
import anima_rs  # anima_rs.compute_phi() for backward compat

# Talk5 의식 phase (100x faster)
result = talk5.run(
    n_cells=128, cell_dim=64, hidden_dim=128,
    steps=1000, n_factions=12, seed=42
)
# result: dict {phi_iit, phi_proxy, consensus_count, best_phi, time_ms}

# Get/set hiddens for Python language phase
hiddens = talk5.get_hiddens(engine_ptr)
# ... Python CE training with .detach() ...
talk5.set_hiddens(engine_ptr, new_hiddens)

# Alpha Sweep (50x faster)
results = alpha_sweep.run(
    n_cells=8, input_dim=64, hidden_dim=128, output_dim=64,
    alphas=[0.0001, 0.001, 0.01, 0.1], steps_per_stage=300, seed=42
)
# results: list of dicts {alpha, phi_iit, phi_proxy, tension_mean, time_ms}

# Golden MoE forward (10x faster)
output, aux_loss = golden_moe.forward(
    input_array, n_experts=4, hidden_dim=128, training=True
)

# Transplant (20x faster)
new_hiddens = transplant.run(
    donor_hiddens, recipient_hiddens, d_from=64, d_to=128, alpha=0.5
)
```

---

## Success Criteria

| Component | Python baseline | Target speedup | Correctness |
|-----------|----------------|----------------|-------------|
| Talk5 consciousness phase | ~2s (128 cells, 1000 steps) | 100x+ → <20ms | Phi ± 0.01 |
| Alpha Sweep | ~0.5s (4 alphas, 300 steps) | 50x+ → <10ms | Identical results |
| Golden MoE forward | ~1ms per call | 10x+ → <100us | output atol=1e-5 |
| Faction consensus | O(n_cells × n_factions) | 50x+ (SIMD) | Identical count |
| Hebbian coupling | O(n_cells^2) | 50x+ (rayon) | coupling atol=1e-5 |
| Transplant projection | O(n_cells × d^2) | 20x+ | hiddens atol=1e-5 |

### Integration Tests

각 Python 벤치마크에서 Rust 결과와 Python 결과를 cross-check:
```python
# test_anima_rs.py
def test_talk5_matches_python():
    py_result = Talk5Engine(seed=42, ...).run_consciousness_phase()
    rs_result = anima_rs.talk5.run(seed=42, ...)
    assert abs(py_result["phi_iit"] - rs_result["phi_iit"]) < 0.01
```

---

## Build & Install

```bash
cd anima-rs
maturin develop --release    # dev install
maturin build --release      # wheel 생성

# Python에서 사용
from anima_rs import talk5
```

---

## phi-rs 통합 계획

1. phi-rs의 `compute_phi`, `search_combinations` 로직을 core로 이식
2. `anima_rs.compute_phi()` 로 노출 (하위호환)
3. phi-rs 디렉토리는 deprecated, README에 `import anima_rs` 안내
4. 기존 코드에서 `import phi_rs` → `import anima_rs` 점진 교체

---

## Dependencies

```toml
# workspace Cargo.toml
[workspace.dependencies]
rand = "0.8"
rayon = "1.10"

# root (PyO3 binding) Cargo.toml
[dependencies]
pyo3 = { version = "0.28", features = ["extension-module"] }
numpy = "0.28"
anima-core = { path = "crates/core" }
anima-talk5 = { path = "crates/talk5" }
anima-alpha-sweep = { path = "crates/alpha-sweep" }
anima-golden-moe = { path = "crates/golden-moe" }
anima-transplant = { path = "crates/transplant" }
```

---

## Files to Create

| File | Purpose |
|------|---------|
| `anima-rs/Cargo.toml` | Workspace root |
| `anima-rs/pyproject.toml` | Maturin build config |
| `anima-rs/src/lib.rs` | PyO3 binding (submodules) |
| `anima-rs/crates/core/Cargo.toml` | Core deps |
| `anima-rs/crates/core/src/lib.rs` | GRU, Faction, Phi, Hebbian, Consensus |
| `anima-rs/crates/talk5/Cargo.toml` | Talk5 deps |
| `anima-rs/crates/talk5/src/lib.rs` | Talk5Engine |
| `anima-rs/crates/alpha-sweep/Cargo.toml` | Sweep deps |
| `anima-rs/crates/alpha-sweep/src/lib.rs` | AlphaSweepEngine |
| `anima-rs/crates/golden-moe/Cargo.toml` | MoE deps |
| `anima-rs/crates/golden-moe/src/lib.rs` | PsiRouter, GoldenMoe |
| `anima-rs/crates/transplant/Cargo.toml` | Transplant deps |
| `anima-rs/crates/transplant/src/lib.rs` | project_hiddens, transplant |
| `anima-rs/tests/test_anima_rs.py` | Python integration tests |
