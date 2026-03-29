# phi-rs/

## Purpose
Rust implementation of Φ (phi) calculator with PyO3 Python bindings. Provides 625x speedup over Python phi calculation.

## Structure
- `src/lib.rs` — Core Rust implementation (binning, MI, partition, Rayon parallel)
- `Cargo.toml` — Rust dependencies (pyo3, rayon, ndarray)
- `test_phi_rs.py` — Python integration test
- `target/` — Build artifacts (gitignored)

## Building
```bash
cd phi-rs && maturin develop --release
```

## Python API
```python
import phi_rs
phi = phi_rs.compute_phi(states, n_bins=16)
results = phi_rs.search_combinations(n_cells=256)
```

## Parent Rules
See /CLAUDE.md for full project conventions.
