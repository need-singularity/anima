//! telescope-rs — High-performance telescope lenses for consciousness analysis
//!
//! Implements the 3 heaviest lenses in Rust:
//!   1. ConsciousnessLens: GRU + Hebbian + Phi(MI) + Factions
//!   2. TopologyLens: Persistent homology (Betti-0, Betti-1)
//!   3. CausalLens: Granger causality + Transfer entropy
//!
//! Python binding via PyO3: `import telescope_rs`

pub mod consciousness;
pub mod topology;
pub mod causal;
pub mod mi;

#[cfg(feature = "pyo3-ext")]
mod python;

#[cfg(feature = "pyo3-ext")]
use pyo3::prelude::*;

#[cfg(feature = "pyo3-ext")]
#[pymodule]
fn telescope_rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    python::register(m)?;
    Ok(())
}
