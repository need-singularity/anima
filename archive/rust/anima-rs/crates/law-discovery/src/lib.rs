//! Law Discovery Engine — real-time consciousness law measurement & pattern detection.
//!
//! Tier 4.2 of the closed-loop evolution pipeline. All metric functions target
//! <100us for 64 cells and <1ms for 1024 cells.
//!
//! Components:
//! - `metrics`: Core metric calculations (Phi, entropy, coupling, variance, Lyapunov)
//! - `pattern`: Statistical pattern detection (correlation, phase transition, FFT, trend)
//! - `text_pattern`: Text-based law parsing (65 regex patterns, synced with Python LawParser)
//! - `candidate`: LawCandidate struct for discovered law proposals
//! - `buffer`: Ring buffer for sliding-window metric history

pub mod metrics;
pub mod pattern;
pub mod text_pattern;
pub mod candidate;
pub mod buffer;

#[cfg(feature = "pyo3")]
pub mod ffi;

pub use metrics::{
    phi_fast, faction_entropy, hebbian_coupling, cell_variance, lyapunov_exponent,
    MetricSnapshot,
};
pub use pattern::{
    detect_correlation, detect_phase_transition, detect_periodicity, detect_trend,
};
pub use text_pattern::{parse_law, TextMatch, ModType, NUM_TEXT_PATTERNS};
pub use candidate::{LawCandidate, PatternType};
pub use buffer::RingBuffer;

/// Compute all core metrics in a single pass where possible.
/// Returns a MetricSnapshot suitable for insertion into a RingBuffer.
pub fn measure_all(
    cells: &[f32],
    n_cells: usize,
    coupling_weights: &[f32],
    n_factions: usize,
    n_bins: u16,
) -> MetricSnapshot {
    let _dim = if n_cells > 0 { cells.len() / n_cells } else { 0 };

    let phi = phi_fast(cells, n_cells, n_bins);
    let entropy = faction_entropy(cells, n_cells, n_factions);
    let coupling = hebbian_coupling(coupling_weights, n_cells);
    let (global_var, faction_var) = cell_variance(cells, n_cells, n_factions);

    MetricSnapshot {
        phi,
        faction_entropy: entropy,
        hebbian_coupling: coupling,
        global_variance: global_var,
        faction_variance: faction_var,
        phi_proxy: (global_var - faction_var).max(0.0),
        lyapunov: 0.0, // requires trajectory, caller sets separately
        n_cells: n_cells as u32,
    }
}
