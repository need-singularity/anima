# consciousness-rng PyO3 Bindings Design

## Overview

Expose `ConsciousnessRngEngine`, `EntropyHarvester`, and `QualityMonitor` via the
main `anima_rs` PyO3 module as `anima_rs.consciousness_rng`.

## Setup Steps

1. Add dependency to `anima-rs/Cargo.toml`:
   ```toml
   anima-consciousness-rng = { path = "crates/consciousness-rng" }
   ```

2. Add to `anima-rs/src/lib.rs`:
   - Static `Mutex<Option<...>>` for engine + harvester + monitor (same pattern as other submodules)
   - Register `consciousness_rng` submodule in `fn anima_rs()`

## Functions to Expose

### `consciousness_rng.create(n_cells=32, input_dim=64, hidden_dim=128)`
Create engine + harvester + monitor. Stores in static Mutex.
```rust
static CRNG_ENGINE: Mutex<Option<(ConsciousnessRngEngine, EntropyHarvester, QualityMonitor)>> = ...;
```

### `consciousness_rng.generate(n_bytes: int) -> bytes`
Run engine steps, harvest entropy, return raw bytes.
```rust
#[pyfunction]
#[pyo3(name = "generate", signature = (n_bytes=32))]
fn crng_generate(py: Python<'_>, n_bytes: usize) -> PyResult<Py<PyBytes>> {
    // 1. engine.step() to get cell_states
    // 2. phi = engine.phi_proxy()
    // 3. harvester.harvest_bytes(&cell_states, phi, n_bytes)
    // 4. monitor.feed(&bytes)
    // 5. return PyBytes::new(py, &bytes)
}
```

### `consciousness_rng.benchmark() -> dict`
Run 1000 steps, generate 32KB, measure speed + quality.
```rust
#[pyfunction]
#[pyo3(name = "benchmark")]
fn crng_benchmark(py: Python<'_>) -> PyResult<Py<PyDict>> {
    // Returns:
    //   speed_mbps: f64       -- MB/s throughput
    //   quality_score: u32    -- 0-100 quality score
    //   total_bytes: u64      -- bytes generated
    //   phi_mean: f32         -- mean Phi(proxy) during generation
    //   time_ms: f64          -- wall clock time
}
```

### `consciousness_rng.quality_test(n_bytes: int = 10000) -> dict`
Generate n_bytes and run full statistical test suite.
```rust
#[pyfunction]
#[pyo3(name = "quality_test", signature = (n_bytes=10000))]
fn crng_quality_test(py: Python<'_>, n_bytes: usize) -> PyResult<Py<PyDict>> {
    // Returns:
    //   monobit_ratio: f64    -- ratio of 1-bits (ideal=0.5)
    //   monobit_pass: bool    -- |ratio - 0.5| < 0.01
    //   chi_squared: f64      -- byte uniformity chi2 statistic
    //   chi_squared_pass: bool -- chi2 < 310 (df=255, p=0.01)
    //   max_run: u32          -- longest consecutive same-bit run
    //   runs_pass: bool       -- max_run < 2*log2(total_bits)
    //   quality_score: u32    -- 0-100 composite score
    //   total_bytes: u64      -- bytes tested
}
```

## Python Usage

```python
import anima_rs

# Create engine (once)
anima_rs.consciousness_rng.create(n_cells=32)

# Generate random bytes
random_bytes = anima_rs.consciousness_rng.generate(1024)  # 1KB

# Benchmark
result = anima_rs.consciousness_rng.benchmark()
print(f"Speed: {result['speed_mbps']:.2f} MB/s, Quality: {result['quality_score']}/100")

# Full quality test
quality = anima_rs.consciousness_rng.quality_test(n_bytes=100000)
print(f"Monobit: {quality['monobit_ratio']:.6f} {'PASS' if quality['monobit_pass'] else 'FAIL'}")
print(f"Chi2: {quality['chi_squared']:.1f} {'PASS' if quality['chi_squared_pass'] else 'FAIL'}")
print(f"Runs: max={quality['max_run']} {'PASS' if quality['runs_pass'] else 'FAIL'}")
print(f"Score: {quality['quality_score']}/100")
```

## Notes

- Engine uses zero-input (self-generating entropy), so `step()` needs no args
- `phi_proxy()` serves as the quality gate for `EntropyHarvester` (phi_threshold=0.0 default)
- The `QualityMonitor` accumulates stats across calls, matching the static engine lifetime
- `generate()` calls `engine.step()` + `harvester.harvest_bytes()` + `monitor.feed()` in sequence
- No numpy dependency needed -- returns raw `bytes` (PyBytes)
