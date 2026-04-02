//! PyO3 bindings for telescope-rs
//!
//! Exposes three functions to Python:
//!   telescope_rs.consciousness_scan(data, n_cells, n_factions, steps, coupling_alpha) -> dict
//!   telescope_rs.topology_scan(data, n_steps, persistence_threshold) -> dict
//!   telescope_rs.causal_scan(data, max_lag, te_bins, min_strength) -> dict

use pyo3::prelude::*;
use pyo3::types::PyDict;
use numpy::{PyReadonlyArray2, PyArray1};

use crate::{consciousness, topology, causal, mi};

/// Consciousness lens scan (GRU + Hebbian + Phi + Factions)
#[pyfunction]
#[pyo3(signature = (data, n_cells=64, n_factions=12, steps=300, coupling_alpha=0.014))]
fn consciousness_scan<'py>(
    py: Python<'py>,
    data: PyReadonlyArray2<'py, f64>,
    n_cells: usize,
    n_factions: usize,
    steps: usize,
    coupling_alpha: f64,
) -> PyResult<Bound<'py, PyDict>> {
    let arr = data.as_array();
    let (n_samples, n_features) = (arr.nrows(), arr.ncols());
    let flat: Vec<f64> = arr.iter().copied().collect();

    let mut lens = consciousness::ConsciousnessLens::new(
        n_cells, n_features.max(128), n_factions, steps, coupling_alpha);
    let result = lens.scan(&flat, n_samples, n_features);

    let dict = PyDict::new(py);
    dict.set_item("phi_iit", result.phi_iit)?;
    dict.set_item("phi_proxy", result.phi_proxy)?;
    dict.set_item("n_clusters", result.n_clusters)?;
    dict.set_item("steps_run", result.steps_run)?;

    // Anomalies as list of (idx, score)
    let anom_idx: Vec<usize> = result.anomalies.iter().map(|a| a.0).collect();
    let anom_scores: Vec<f64> = result.anomalies.iter().map(|a| a.1).collect();
    dict.set_item("anomaly_indices", PyArray1::from_vec(py, anom_idx.iter().map(|&i| i as f64).collect()))?;
    dict.set_item("anomaly_scores", PyArray1::from_vec(py, anom_scores))?;

    Ok(dict)
}

/// Topology lens scan (persistent homology: Betti-0 + Betti-1)
#[pyfunction]
#[pyo3(signature = (data, n_filtration_steps=100, persistence_threshold=0.014))]
fn topology_scan<'py>(
    py: Python<'py>,
    data: PyReadonlyArray2<'py, f64>,
    n_filtration_steps: usize,
    persistence_threshold: f64,
) -> PyResult<Bound<'py, PyDict>> {
    let arr = data.as_array();
    let (n_samples, n_features) = (arr.nrows(), arr.ncols());
    let flat: Vec<f64> = arr.iter().copied().collect();

    let result = topology::scan(&flat, n_samples, n_features,
                                n_filtration_steps, persistence_threshold);

    let dict = PyDict::new(py);
    dict.set_item("betti_0", result.betti_0)?;
    dict.set_item("betti_1", result.betti_1)?;
    dict.set_item("n_components", result.n_components)?;
    dict.set_item("n_holes", result.n_holes)?;
    dict.set_item("optimal_scale", result.optimal_scale)?;
    dict.set_item("n_persistence_pairs", result.persistence_pairs.len())?;
    dict.set_item("n_phase_transitions", result.phase_transitions.len())?;

    // Phase transitions as list of strings
    let pt_strs: Vec<String> = result.phase_transitions.iter()
        .map(|(eps, desc)| format!("eps={:.4}: {}", eps, desc))
        .collect();
    dict.set_item("phase_transitions", pt_strs)?;

    Ok(dict)
}

/// Causal lens scan (Granger + Transfer entropy)
#[pyfunction]
#[pyo3(signature = (data, max_lag=5, te_bins=16, min_strength=0.1))]
fn causal_scan<'py>(
    py: Python<'py>,
    data: PyReadonlyArray2<'py, f64>,
    max_lag: usize,
    te_bins: usize,
    min_strength: f64,
) -> PyResult<Bound<'py, PyDict>> {
    let arr = data.as_array();
    let (n_samples, n_features) = (arr.nrows(), arr.ncols());
    let flat: Vec<f64> = arr.iter().copied().collect();

    let result = causal::scan(&flat, n_samples, n_features,
                              max_lag, te_bins, min_strength);

    let dict = PyDict::new(py);
    dict.set_item("n_features", result.n_features)?;
    dict.set_item("n_causal_pairs", result.causal_pairs.len())?;

    // Causal pairs as list of dicts
    let pairs: Vec<(usize, usize, f64, usize, String)> = result.causal_pairs.iter()
        .map(|p| (p.cause, p.effect, p.strength, p.lag, p.method.clone()))
        .collect();
    let causes: Vec<usize> = pairs.iter().map(|p| p.0).collect();
    let effects: Vec<usize> = pairs.iter().map(|p| p.1).collect();
    let strengths: Vec<f64> = pairs.iter().map(|p| p.2).collect();
    dict.set_item("causes", causes)?;
    dict.set_item("effects", effects)?;
    dict.set_item("strengths", strengths)?;

    // Matrices
    dict.set_item("granger_matrix", PyArray1::from_vec(py, result.granger_matrix))?;
    dict.set_item("te_matrix", PyArray1::from_vec(py, result.te_matrix))?;

    Ok(dict)
}

/// Fast mutual information between two 1D arrays
#[pyfunction]
#[pyo3(signature = (a, b, n_bins=16))]
fn fast_mutual_info<'py>(
    _py: Python<'py>,
    a: PyReadonlyArray2<'py, f64>,
    b: PyReadonlyArray2<'py, f64>,
    n_bins: usize,
) -> PyResult<f64> {
    let a_flat: Vec<f64> = a.as_array().iter().copied().collect();
    let b_flat: Vec<f64> = b.as_array().iter().copied().collect();
    Ok(mi::mutual_info(&a_flat, &b_flat, n_bins))
}

pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(consciousness_scan, m)?)?;
    m.add_function(wrap_pyfunction!(topology_scan, m)?)?;
    m.add_function(wrap_pyfunction!(causal_scan, m)?)?;
    m.add_function(wrap_pyfunction!(fast_mutual_info, m)?)?;
    Ok(())
}
