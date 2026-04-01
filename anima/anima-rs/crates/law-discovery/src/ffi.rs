//! PyO3 FFI bindings for law-discovery.
//!
//! High-level Python-friendly wrappers around metrics, pattern detection,
//! and the ring buffer. Designed for <100us per call on 64 cells.
//!
//! These functions are registered as `anima_rs.law_discovery.*` by the
//! root crate's lib.rs.

use std::collections::HashMap;

use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};

use crate::buffer::RingBuffer;
use crate::candidate::LawCandidate;
use crate::metrics::{self, MetricSnapshot, NUM_METRICS};
use crate::{detect_correlation, detect_phase_transition, detect_periodicity, detect_trend};

// ═══════════════════════════════════════════════════════════════════════
// Metric names (canonical order matching MetricSnapshot::as_array)
// ═══════════════════════════════════════════════════════════════════════

const METRIC_NAMES: [&str; NUM_METRICS] = [
    "phi",
    "faction_entropy",
    "hebbian_coupling",
    "global_variance",
    "faction_variance",
    "phi_proxy",
    "lyapunov",
    "n_cells",
];

// ═══════════════════════════════════════════════════════════════════════
// compute_metrics — single-call metric computation
// ═══════════════════════════════════════════════════════════════════════

/// Compute all core consciousness metrics from flat cell states.
///
/// Args:
///   cell_states: flat Vec<f32> of [n_cells * dim] cell hidden states
///   n_cells: number of cells
///   n_factions: number of factions (default 12)
///   coupling_weights: optional flat [n_cells * n_cells] Hebbian weights
///   n_bins: histogram bins for MI-based Phi (default 16)
///
/// Returns:
///   HashMap<String, f64> with all metric names and values
#[pyfunction]
#[pyo3(signature = (cell_states, n_cells, n_factions=12, coupling_weights=None, n_bins=16))]
pub fn compute_metrics(
    cell_states: Vec<f32>,
    n_cells: usize,
    n_factions: usize,
    coupling_weights: Option<Vec<f32>>,
    n_bins: u16,
) -> PyResult<HashMap<String, f64>> {
    if n_cells == 0 || cell_states.is_empty() {
        return Ok(HashMap::new());
    }

    let weights = coupling_weights.unwrap_or_else(|| vec![0.0f32; n_cells * n_cells]);

    let snap = crate::measure_all(&cell_states, n_cells, &weights, n_factions, n_bins);
    let arr = snap.as_array();

    let mut result = HashMap::with_capacity(NUM_METRICS);
    for (i, &name) in METRIC_NAMES.iter().enumerate() {
        result.insert(name.to_string(), arr[i] as f64);
    }

    Ok(result)
}

// ═══════════════════════════════════════════════════════════════════════
// detect_patterns — batch pattern detection on metric history
// ═══════════════════════════════════════════════════════════════════════

/// Detect all statistical patterns in a metric history buffer.
///
/// Args:
///   metric_history: Vec<Vec<f32>> where each inner Vec is one time step
///                   with n_metrics values (same order as MetricSnapshot).
///   window: ring buffer capacity (default: metric_history.len())
///   sigma_threshold: phase transition sensitivity (default 2.0)
///   correlation_pairs: optional list of (metric_a, metric_b) to test.
///                      If None, tests all unique pairs.
///
/// Returns:
///   List of dicts, each with keys:
///     "pattern_type": str ("correlation"|"phase_transition"|"oscillation"|"trend")
///     "metric_a": int (first metric index)
///     "metric_b": int or None (second metric index, for correlation)
///     "value": float (r, frequency, slope, or step index)
///     "evidence": float (r^2, p-value, or significance)
#[pyfunction]
#[pyo3(signature = (metric_history, window=None, sigma_threshold=2.0, correlation_pairs=None))]
pub fn detect_patterns(
    py: Python<'_>,
    metric_history: Vec<Vec<f32>>,
    window: Option<usize>,
    sigma_threshold: f32,
    correlation_pairs: Option<Vec<(usize, usize)>>,
) -> PyResult<Py<PyList>> {
    if metric_history.is_empty() {
        return Ok(PyList::empty(py).into());
    }

    let n_metrics = metric_history[0].len();
    let cap = window.unwrap_or(metric_history.len());

    // Build ring buffer from history
    let mut buf = RingBuffer::new(cap, n_metrics);
    for row in &metric_history {
        buf.push(row);
    }

    let mut patterns: Vec<Py<PyDict>> = Vec::new();

    // --- Correlation detection ---
    let pairs: Vec<(usize, usize)> = if let Some(p) = correlation_pairs {
        p
    } else {
        // All unique pairs
        let mut all = Vec::new();
        for a in 0..n_metrics {
            for b in (a + 1)..n_metrics {
                all.push((a, b));
            }
        }
        all
    };

    for (a, b) in pairs {
        if let Some((r, p)) = detect_correlation(&buf, a, b) {
            let d = PyDict::new(py);
            d.set_item("pattern_type", "correlation")?;
            d.set_item("metric_a", a)?;
            d.set_item("metric_b", b as isize)?;
            d.set_item("value", r)?;
            d.set_item("evidence", 1.0 - p)?; // higher = more significant
            d.set_item("metric_a_name", metric_name(a))?;
            d.set_item("metric_b_name", metric_name(b))?;
            patterns.push(d.into());
        }
    }

    // --- Phase transition detection ---
    for m in 0..n_metrics {
        if let Some(step_idx) = detect_phase_transition(&buf, m, sigma_threshold) {
            let d = PyDict::new(py);
            d.set_item("pattern_type", "phase_transition")?;
            d.set_item("metric_a", m)?;
            d.set_item("metric_b", py.None())?;
            d.set_item("value", step_idx as f32)?;
            d.set_item("evidence", 1.0)?; // passed sigma threshold
            d.set_item("metric_a_name", metric_name(m))?;
            patterns.push(d.into());
        }
    }

    // --- Periodicity detection (FFT) ---
    for m in 0..n_metrics {
        if let Some(freq) = detect_periodicity(&buf, m) {
            let d = PyDict::new(py);
            d.set_item("pattern_type", "oscillation")?;
            d.set_item("metric_a", m)?;
            d.set_item("metric_b", py.None())?;
            d.set_item("value", freq)?;
            d.set_item("evidence", 0.8)?; // passed peak dominance test
            d.set_item("period", 1.0 / freq)?;
            d.set_item("metric_a_name", metric_name(m))?;
            patterns.push(d.into());
        }
    }

    // --- Trend detection ---
    for m in 0..n_metrics {
        let (slope, r2) = detect_trend(&buf, m);
        if r2 > 0.3 && slope.abs() > 1e-6 {
            let d = PyDict::new(py);
            d.set_item("pattern_type", "trend")?;
            d.set_item("metric_a", m)?;
            d.set_item("metric_b", py.None())?;
            d.set_item("value", slope)?;
            d.set_item("evidence", r2)?;
            d.set_item("metric_a_name", metric_name(m))?;
            d.set_item("direction", if slope > 0.0 { "increasing" } else { "decreasing" })?;
            patterns.push(d.into());
        }
    }

    Ok(PyList::new(py, &patterns)?.into())
}

// ═══════════════════════════════════════════════════════════════════════
// scan_all_patterns — one-shot: compute metrics + detect patterns
// ═══════════════════════════════════════════════════════════════════════

/// Compute metrics from multiple time steps of cell states, then detect patterns.
///
/// This is the "batteries included" function: pass in a sequence of cell state
/// snapshots and get back both the metric time series and any detected patterns.
///
/// Args:
///   cell_states_sequence: Vec<Vec<f32>> — each inner Vec is a flat [n_cells * dim]
///   n_cells: number of cells (constant across steps)
///   n_factions: number of factions
///   coupling_weights: optional flat [n_cells * n_cells] Hebbian weights
///   n_bins: MI bins (default 16)
///   sigma_threshold: phase transition sensitivity (default 2.0)
///
/// Returns:
///   Dict with "metrics" (list of snapshots) and "patterns" (list of pattern dicts)
#[pyfunction]
#[pyo3(signature = (cell_states_sequence, n_cells, n_factions=12, coupling_weights=None, n_bins=16, sigma_threshold=2.0))]
pub fn scan_all_patterns(
    py: Python<'_>,
    cell_states_sequence: Vec<Vec<f32>>,
    n_cells: usize,
    n_factions: usize,
    coupling_weights: Option<Vec<f32>>,
    n_bins: u16,
    sigma_threshold: f32,
) -> PyResult<Py<PyDict>> {
    let weights = coupling_weights.unwrap_or_else(|| vec![0.0f32; n_cells * n_cells]);
    let n_steps = cell_states_sequence.len();

    // Compute metrics for each step
    let mut metric_history: Vec<Vec<f32>> = Vec::with_capacity(n_steps);
    let mut metric_dicts: Vec<Py<PyDict>> = Vec::with_capacity(n_steps);

    for cells in &cell_states_sequence {
        let snap = crate::measure_all(cells, n_cells, &weights, n_factions, n_bins);
        let arr = snap.as_array();
        metric_history.push(arr.to_vec());

        let d = PyDict::new(py);
        for (i, &name) in METRIC_NAMES.iter().enumerate() {
            d.set_item(name, arr[i] as f64)?;
        }
        metric_dicts.push(d.into());
    }

    // Detect patterns
    let patterns = detect_patterns(
        py,
        metric_history,
        None,
        sigma_threshold,
        None,
    )?;

    let result = PyDict::new(py);
    result.set_item("metrics", PyList::new(py, &metric_dicts)?)?;
    result.set_item("patterns", patterns)?;
    result.set_item("n_steps", n_steps)?;
    result.set_item("n_cells", n_cells)?;

    Ok(result.into())
}

// ═══════════════════════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════════════════════

/// Get the canonical metric name for an index, or "unknown".
fn metric_name(idx: usize) -> &'static str {
    if idx < METRIC_NAMES.len() {
        METRIC_NAMES[idx]
    } else {
        "unknown"
    }
}

// ═══════════════════════════════════════════════════════════════════════
// parse_law_text — text-based law parsing (65 patterns)
// ═══════════════════════════════════════════════════════════════════════

/// Parse a consciousness law text into structured pattern matches.
///
/// Rust port of Python LawParser with 65 synchronized regex patterns.
///
/// Args:
///   law_text: the law description string
///   law_id: numeric law identifier
///
/// Returns:
///   List of dicts, each with keys:
///     "pattern_id": int (1-65)
///     "mod_type": str ("scale"|"couple"|"threshold"|"conditional"|"inject"|"disable")
///     "target": str (normalized parameter name)
///     "confidence": float (0.0 - 1.0)
///     "description": str
///     "params": dict of extracted parameters
#[pyfunction]
#[pyo3(signature = (law_text, law_id=0))]
pub fn parse_law_text(
    py: Python<'_>,
    law_text: &str,
    law_id: u32,
) -> PyResult<Py<PyList>> {
    let matches = crate::text_pattern::parse_law(law_text, law_id);
    let mut results: Vec<Py<PyDict>> = Vec::with_capacity(matches.len());

    for m in &matches {
        let d = PyDict::new(py);
        d.set_item("pattern_id", m.pattern_id)?;
        d.set_item("mod_type", m.mod_type.name())?;
        d.set_item("target", &m.target)?;
        d.set_item("confidence", m.confidence)?;
        d.set_item("description", &m.description)?;

        let params = PyDict::new(py);
        for (k, v) in &m.params {
            params.set_item(k.as_str(), v.as_str())?;
        }
        d.set_item("params", params)?;
        results.push(d.into());
    }

    Ok(PyList::new(py, &results)?.into())
}

/// Return the number of text patterns implemented.
#[pyfunction]
pub fn num_text_patterns() -> usize {
    crate::text_pattern::NUM_TEXT_PATTERNS
}

/// Register all FFI functions into a PyModule.
///
/// Called from the root crate's `lib.rs` to add high-level functions
/// to the `anima_rs.law_discovery` submodule.
pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(compute_metrics, m)?)?;
    m.add_function(wrap_pyfunction!(detect_patterns, m)?)?;
    m.add_function(wrap_pyfunction!(scan_all_patterns, m)?)?;
    m.add_function(wrap_pyfunction!(parse_law_text, m)?)?;
    m.add_function(wrap_pyfunction!(num_text_patterns, m)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_metric_names_count() {
        assert_eq!(METRIC_NAMES.len(), NUM_METRICS);
    }

    #[test]
    fn test_metric_name_lookup() {
        assert_eq!(metric_name(0), "phi");
        assert_eq!(metric_name(7), "n_cells");
        assert_eq!(metric_name(99), "unknown");
    }
}
