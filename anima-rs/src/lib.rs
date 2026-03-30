use std::sync::Mutex;

use numpy::{PyArray1, PyReadonlyArray2, PyUntypedArrayMethods};
use pyo3::prelude::*;
use pyo3::types::PyDict;

use anima_core::phi_iit;

// ── Static Talk5 engine storage ────────────────────────────────────

static TALK5_ENGINE: Mutex<Option<anima_talk5::Talk5Engine>> = Mutex::new(None);

// ── compute_phi (backward compat, top-level) ───────────────────────

#[pyfunction]
#[pyo3(signature = (states, n_bins=16))]
fn compute_phi(states: PyReadonlyArray2<f32>, n_bins: usize) -> PyResult<(f64, f64, f64)> {
    let shape = states.shape();
    let n_rows = shape[0];
    let n_cols = shape[1];

    // Convert rows to Vec<Vec<f32>>
    let data = states.as_slice().map_err(|e| {
        pyo3::exceptions::PyValueError::new_err(format!("Cannot read array as contiguous: {e}"))
    })?;

    let rows: Vec<Vec<f32>> = (0..n_rows)
        .map(|i| data[i * n_cols..(i + 1) * n_cols].to_vec())
        .collect();

    let refs: Vec<&[f32]> = rows.iter().map(|r| r.as_slice()).collect();
    let (phi, components) = phi_iit(&refs, n_bins);

    Ok((phi, components.total_mi, components.min_partition_mi))
}

// ── Talk5 submodule ────────────────────────────────────────────────

#[pyfunction]
#[pyo3(signature = (n_cells=8, cell_dim=64, hidden_dim=128, n_factions=12, steps=1000, phi_ratchet=true, seed=42))]
fn talk5_run(
    py: Python<'_>,
    n_cells: usize,
    cell_dim: usize,
    hidden_dim: usize,
    n_factions: usize,
    steps: usize,
    phi_ratchet: bool,
    seed: u64,
) -> PyResult<Py<PyDict>> {
    let mut engine =
        anima_talk5::Talk5Engine::new(n_cells, cell_dim, hidden_dim, n_factions, phi_ratchet, seed);
    let result = engine.run_consciousness(steps);

    let dict = PyDict::new(py);
    dict.set_item("phi_iit", result.phi_iit)?;
    dict.set_item("phi_proxy", result.phi_proxy)?;
    dict.set_item("consensus_count", result.consensus_count)?;
    dict.set_item("best_phi", result.best_phi)?;
    dict.set_item("steps", result.steps)?;
    dict.set_item("time_ms", result.time_ms)?;

    // Store engine for later get/set
    let mut guard = TALK5_ENGINE.lock().map_err(|e| {
        pyo3::exceptions::PyRuntimeError::new_err(format!("Lock poisoned: {e}"))
    })?;
    *guard = Some(engine);

    Ok(dict.into())
}

#[pyfunction]
fn talk5_get_hiddens(py: Python<'_>) -> PyResult<Vec<Py<PyArray1<f32>>>> {
    let guard = TALK5_ENGINE.lock().map_err(|e| {
        pyo3::exceptions::PyRuntimeError::new_err(format!("Lock poisoned: {e}"))
    })?;
    let engine = guard.as_ref().ok_or_else(|| {
        pyo3::exceptions::PyRuntimeError::new_err("No Talk5 engine. Call talk5.run() first.")
    })?;

    let hiddens = engine.get_hiddens();
    let arrays: Vec<Py<PyArray1<f32>>> = hiddens
        .into_iter()
        .map(|h| PyArray1::from_vec(py, h).into())
        .collect();
    Ok(arrays)
}

#[pyfunction]
fn talk5_set_hiddens(hiddens: Vec<Vec<f32>>) -> PyResult<()> {
    let mut guard = TALK5_ENGINE.lock().map_err(|e| {
        pyo3::exceptions::PyRuntimeError::new_err(format!("Lock poisoned: {e}"))
    })?;
    let engine = guard.as_mut().ok_or_else(|| {
        pyo3::exceptions::PyRuntimeError::new_err("No Talk5 engine. Call talk5.run() first.")
    })?;

    engine.set_hiddens(&hiddens);
    Ok(())
}

// ── Alpha-sweep submodule ──────────────────────────────────────────

#[pyfunction]
#[pyo3(signature = (n_cells=8, input_dim=64, hidden_dim=128, output_dim=64, n_factions=8, alphas=None, steps_per_stage=300, seed=42))]
fn alpha_sweep_run(
    py: Python<'_>,
    n_cells: usize,
    input_dim: usize,
    hidden_dim: usize,
    output_dim: usize,
    n_factions: usize,
    alphas: Option<Vec<f32>>,
    steps_per_stage: usize,
    seed: u64,
) -> PyResult<Vec<Py<PyDict>>> {
    let alpha_values = alphas.unwrap_or_else(|| vec![0.0001, 0.001, 0.01, 0.1]);

    let engine =
        anima_alpha_sweep::AlphaSweepEngine::new(n_cells, input_dim, hidden_dim, output_dim, n_factions);
    let results = engine.run(&alpha_values, steps_per_stage, seed);

    let dicts: Vec<Py<PyDict>> = results
        .into_iter()
        .map(|r| {
            let dict = PyDict::new(py);
            dict.set_item("alpha", r.alpha).unwrap();
            dict.set_item("phi_iit", r.phi_iit).unwrap();
            dict.set_item("phi_proxy", r.phi_proxy).unwrap();
            dict.set_item("tension_mean", r.tension_mean).unwrap();
            dict.set_item("time_ms", r.time_ms).unwrap();
            dict.into()
        })
        .collect();

    Ok(dicts)
}

// ── Golden-MoE submodule ───────────────────────────────────────────

#[pyfunction]
#[pyo3(signature = (input, n_experts=4, hidden_dim=128, output_dim=10, training=true, seed=42))]
fn golden_moe_forward(
    py: Python<'_>,
    input: Vec<f32>,
    n_experts: usize,
    hidden_dim: usize,
    output_dim: usize,
    training: bool,
    seed: u64,
) -> PyResult<(Py<PyArray1<f32>>, f32)> {
    let input_dim = input.len();
    let mut moe = anima_golden_moe::GoldenMoe::new(input_dim, hidden_dim, output_dim, n_experts, seed);
    let (output, aux_loss) = moe.forward(&input, training);

    let arr = PyArray1::from_vec(py, output);
    Ok((arr.into(), aux_loss))
}

// ── Transplant submodule ───────────────────────────────────────────

#[pyfunction]
#[pyo3(signature = (donor, recipient, d_from, d_to, alpha=0.5))]
fn transplant_run(
    py: Python<'_>,
    donor: Vec<Vec<f32>>,
    mut recipient: Vec<Vec<f32>>,
    d_from: usize,
    d_to: usize,
    alpha: f32,
) -> PyResult<Vec<Py<PyArray1<f32>>>> {
    anima_transplant::transplant(&donor, &mut recipient, d_from, d_to, alpha);

    let arrays: Vec<Py<PyArray1<f32>>> = recipient
        .into_iter()
        .map(|h| PyArray1::from_vec(py, h).into())
        .collect();
    Ok(arrays)
}

// ── Module registration ────────────────────────────────────────────

#[pymodule]
fn anima_rs(py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add("__version__", "0.1.0")?;
    m.add_function(wrap_pyfunction!(compute_phi, m)?)?;

    // talk5 submodule
    let talk5 = PyModule::new(py, "talk5")?;
    talk5.add_function(wrap_pyfunction!(talk5_run, &talk5)?)?;
    talk5.add_function(wrap_pyfunction!(talk5_get_hiddens, &talk5)?)?;
    talk5.add_function(wrap_pyfunction!(talk5_set_hiddens, &talk5)?)?;
    m.add_submodule(&talk5)?;

    // alpha_sweep submodule
    let alpha_sweep = PyModule::new(py, "alpha_sweep")?;
    alpha_sweep.add_function(wrap_pyfunction!(alpha_sweep_run, &alpha_sweep)?)?;
    m.add_submodule(&alpha_sweep)?;

    // golden_moe submodule
    let golden_moe = PyModule::new(py, "golden_moe")?;
    golden_moe.add_function(wrap_pyfunction!(golden_moe_forward, &golden_moe)?)?;
    m.add_submodule(&golden_moe)?;

    // transplant submodule
    let transplant = PyModule::new(py, "transplant")?;
    transplant.add_function(wrap_pyfunction!(transplant_run, &transplant)?)?;
    m.add_submodule(&transplant)?;

    Ok(())
}
