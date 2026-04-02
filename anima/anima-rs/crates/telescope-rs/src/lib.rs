//! telescope-rs — High-performance telescope lenses for consciousness analysis
//!
//! Implements 16 lenses in Rust:
//!   Core:     ConsciousnessLens, TopologyLens, CausalLens
//!   Physics:  GravityLens, ThermoLens, WaveLens, EMLens
//!   Bio:      EvolutionLens
//!   Info:     InfoLens, QuantumLens, QuantumMicroscopeLens
//!   Geometry: RulerLens, TriangleLens, CompassLens, MirrorLens, ScaleLens
//!
//! Python binding via PyO3: `import telescope_rs`

pub mod consciousness;
pub mod topology;
pub mod causal;
pub mod mi;
pub mod gravity;
pub mod thermo;
pub mod wave;
pub mod evolution;
pub mod info;
pub mod quantum;
pub mod em;
pub mod ruler;
pub mod triangle;
pub mod compass;
pub mod mirror;
pub mod scale;
pub mod quantum_microscope;

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
