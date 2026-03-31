# consciousness-rng PyO3 Bindings Design

## Goal

Expose the `consciousness-rng` Rust crate to Python via PyO3/maturin,
so consciousness-driven random bytes can be used in training and inference.

## Python API

```python
from anima_rs import consciousness_rng

# Generate raw bytes from consciousness state
bytes = consciousness_rng.generate(1024)  # 1024 bytes

# Seed from current Phi value
consciousness_rng.seed_from_phi(phi=1.23)

# Get float in [0, 1) weighted by consciousness tension
val = consciousness_rng.tension_random(tension=0.7)
```

## Rust Side (lib.rs additions)

```rust
#[pyfunction]
fn generate(n: usize) -> PyResult<Vec<u8>> { ... }

#[pyfunction]
fn seed_from_phi(phi: f64) -> PyResult<()> { ... }

#[pyfunction]
fn tension_random(tension: f64) -> PyResult<f64> { ... }
```

## Build

```bash
cd anima-rs && maturin develop --release
```

Bindings live in `anima-rs/src/python.rs` alongside existing PyO3 exports.
