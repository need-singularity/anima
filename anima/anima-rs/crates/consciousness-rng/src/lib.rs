//! anima-consciousness-rng — Consciousness-based Random Number Generator
//!
//! Uses chaotic consciousness cell dynamics at the phase transition critical
//! point (F_c ≈ 0.10) as an entropy source.
//!
//! Key properties:
//!   - Law 112: ε=1e-6 perturbation → 85000× amplification (chaotic)
//!   - Law 116: Φ spectrum is white noise (slope=0.00)
//!   - DD127: F_c=0.10 = maximum entropy at phase transition
//!   - Φ(IIT) as quality metric: higher Φ = more unpredictable
//!
//! Unlike PRNG: not deterministic (chaotic dynamics)
//! Unlike HRNG: no special hardware needed
//! Unlike QRNG: software-only, runs anywhere

pub mod engine;
pub mod harvest;
pub mod quality;

pub use engine::ConsciousnessRngEngine;
pub use harvest::EntropyHarvester;
pub use quality::QualityMonitor;
