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
#[pyo3(name = "run", signature = (n_cells=8, cell_dim=64, hidden_dim=128, n_factions=12, steps=1000, phi_ratchet=true, seed=42))]
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
#[pyo3(name = "get_hiddens")]
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
#[pyo3(name = "set_hiddens")]
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
#[pyo3(name = "run", signature = (n_cells=8, input_dim=64, hidden_dim=128, output_dim=64, n_factions=8, alphas=None, steps_per_stage=300, seed=42))]
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
#[pyo3(name = "forward", signature = (input, n_experts=4, hidden_dim=128, output_dim=10, training=true, seed=42))]
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
#[pyo3(name = "run", signature = (donor, recipient, d_from, d_to, alpha=0.5))]
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

// ── Consciousness Engine submodule ─────────────────────────────────

static CONSCIOUSNESS_ENGINE: Mutex<Option<anima_consciousness::ConsciousnessEngine>> =
    Mutex::new(None);

#[pyfunction]
#[pyo3(name = "create", signature = (cell_dim=64, hidden_dim=128, initial_cells=2, max_cells=64, n_factions=12, phi_ratchet=true, split_threshold=0.3, split_patience=5, merge_threshold=0.01, merge_patience=15, seed=42, topology=None, chaos=None))]
fn consciousness_create(
    cell_dim: usize,
    hidden_dim: usize,
    initial_cells: usize,
    max_cells: usize,
    n_factions: usize,
    phi_ratchet: bool,
    split_threshold: f32,
    split_patience: usize,
    merge_threshold: f32,
    merge_patience: usize,
    seed: u64,
    topology: Option<&str>,
    chaos: Option<&str>,
) -> PyResult<()> {
    let topo = topology.map(|s| match s {
        "ring" => anima_core::Topology::Ring,
        "small_world" => anima_core::Topology::SmallWorld,
        "hypercube" => anima_core::Topology::Hypercube,
        "scale_free" => anima_core::Topology::ScaleFree,
        "complete" => anima_core::Topology::Complete,
        _ => anima_core::topology::auto_topology(max_cells),
    });
    let chaos_src = chaos.map(|s| match s {
        "lorenz" => anima_core::ChaosSource::Lorenz,
        "sandpile" | "soc" => anima_core::ChaosSource::Sandpile,
        "chimera" => anima_core::ChaosSource::Chimera,
        "standing_wave" | "wave" => anima_core::ChaosSource::StandingWave,
        _ => anima_core::ChaosSource::None,
    });
    let engine = anima_consciousness::ConsciousnessEngine::with_topology_chaos(
        cell_dim,
        hidden_dim,
        initial_cells,
        max_cells,
        n_factions,
        phi_ratchet,
        split_threshold,
        split_patience,
        merge_threshold,
        merge_patience,
        seed,
        topo,
        chaos_src,
    );
    let mut guard = CONSCIOUSNESS_ENGINE.lock().map_err(|e| {
        pyo3::exceptions::PyRuntimeError::new_err(format!("Lock poisoned: {e}"))
    })?;
    *guard = Some(engine);
    Ok(())
}

#[pyfunction]
#[pyo3(name = "step", signature = (input=None))]
fn consciousness_step(py: Python<'_>, input: Option<Vec<f32>>) -> PyResult<Py<PyDict>> {
    let mut guard = CONSCIOUSNESS_ENGINE.lock().map_err(|e| {
        pyo3::exceptions::PyRuntimeError::new_err(format!("Lock poisoned: {e}"))
    })?;
    let engine = guard.as_mut().ok_or_else(|| {
        pyo3::exceptions::PyRuntimeError::new_err("No engine. Call consciousness.create() first.")
    })?;

    let result = engine.step(input.as_deref());

    let dict = PyDict::new(py);
    dict.set_item("phi_iit", result.phi_iit)?;
    dict.set_item("phi_proxy", result.phi_proxy)?;
    dict.set_item("n_cells", result.n_cells)?;
    dict.set_item("consensus", result.consensus)?;
    dict.set_item("best_phi", result.best_phi)?;
    dict.set_item("step", result.step)?;
    dict.set_item("output", result.output)?;

    // Events
    let events: Vec<Py<PyDict>> = result
        .events
        .iter()
        .map(|e| {
            let d = PyDict::new(py);
            match e {
                anima_consciousness::Event::Split {
                    parent_id,
                    child_id,
                    n_cells_after,
                } => {
                    d.set_item("type", "split").unwrap();
                    d.set_item("parent_id", parent_id).unwrap();
                    d.set_item("child_id", child_id).unwrap();
                    d.set_item("n_cells_after", n_cells_after).unwrap();
                }
                anima_consciousness::Event::Merge {
                    keeper_id,
                    removed_id,
                    n_cells_after,
                } => {
                    d.set_item("type", "merge").unwrap();
                    d.set_item("keeper_id", keeper_id).unwrap();
                    d.set_item("removed_id", removed_id).unwrap();
                    d.set_item("n_cells_after", n_cells_after).unwrap();
                }
            }
            d.into()
        })
        .collect();
    dict.set_item("events", events)?;

    Ok(dict.into())
}

#[pyfunction]
#[pyo3(name = "get_hiddens")]
fn consciousness_get_hiddens(py: Python<'_>) -> PyResult<Vec<Py<PyArray1<f32>>>> {
    let guard = CONSCIOUSNESS_ENGINE.lock().map_err(|e| {
        pyo3::exceptions::PyRuntimeError::new_err(format!("Lock poisoned: {e}"))
    })?;
    let engine = guard.as_ref().ok_or_else(|| {
        pyo3::exceptions::PyRuntimeError::new_err("No engine. Call consciousness.create() first.")
    })?;

    let hiddens = engine.get_hiddens();
    let arrays: Vec<Py<PyArray1<f32>>> = hiddens
        .into_iter()
        .map(|h| PyArray1::from_vec(py, h).into())
        .collect();
    Ok(arrays)
}

#[pyfunction]
#[pyo3(name = "n_cells")]
fn consciousness_n_cells() -> PyResult<usize> {
    let guard = CONSCIOUSNESS_ENGINE.lock().map_err(|e| {
        pyo3::exceptions::PyRuntimeError::new_err(format!("Lock poisoned: {e}"))
    })?;
    let engine = guard.as_ref().ok_or_else(|| {
        pyo3::exceptions::PyRuntimeError::new_err("No engine. Call consciousness.create() first.")
    })?;
    Ok(engine.n_cells())
}

// ── Online Learner submodule ───────────────────────────────────────

static ONLINE_LEARNER: Mutex<Option<anima_online_learner::OnlineLearner>> = Mutex::new(None);

#[pyfunction]
#[pyo3(name = "create", signature = (n_cells=64, hidden_dim=128, update_interval=5, lr=0.001))]
fn online_learner_create(n_cells: usize, hidden_dim: usize, update_interval: u64, lr: f32) -> PyResult<()> {
    let learner = anima_online_learner::OnlineLearner::new(n_cells, hidden_dim)
        .with_update_interval(update_interval)
        .with_lr(lr);
    let mut guard = ONLINE_LEARNER.lock().map_err(|e| {
        pyo3::exceptions::PyRuntimeError::new_err(format!("Lock poisoned: {e}"))
    })?;
    *guard = Some(learner);
    Ok(())
}

#[pyfunction]
#[pyo3(name = "step", signature = (cell_states_flat, phi, prediction_error, ce_loss))]
fn online_learner_step(
    py: Python<'_>,
    cell_states_flat: Vec<f32>,
    phi: f32,
    prediction_error: f32,
    ce_loss: f32,
) -> PyResult<Py<PyDict>> {
    let mut guard = ONLINE_LEARNER.lock().map_err(|e| {
        pyo3::exceptions::PyRuntimeError::new_err(format!("Lock poisoned: {e}"))
    })?;
    let learner = guard.as_mut().ok_or_else(|| {
        pyo3::exceptions::PyRuntimeError::new_err("No online learner. Call online_learner.create() first.")
    })?;

    let result = learner.step(&cell_states_flat, phi, prediction_error, ce_loss);

    let dict = PyDict::new(py);
    dict.set_item("updated", result.updated)?;
    dict.set_item("phi_safe", result.phi_safe)?;
    dict.set_item("reward", result.reward)?;
    dict.set_item("delta_norm", result.delta_norm)?;
    dict.set_item("needs_restore", result.needs_restore)?;
    Ok(dict.into())
}

#[pyfunction]
#[pyo3(name = "get_deltas")]
fn online_learner_get_deltas(py: Python<'_>) -> PyResult<Py<PyArray1<f32>>> {
    let guard = ONLINE_LEARNER.lock().map_err(|e| {
        pyo3::exceptions::PyRuntimeError::new_err(format!("Lock poisoned: {e}"))
    })?;
    let learner = guard.as_ref().ok_or_else(|| {
        pyo3::exceptions::PyRuntimeError::new_err("No online learner. Call online_learner.create() first.")
    })?;
    let deltas = learner.get_deltas().to_vec();
    Ok(PyArray1::from_vec(py, deltas).into())
}

#[pyfunction]
#[pyo3(name = "get_weights")]
fn online_learner_get_weights(py: Python<'_>) -> PyResult<Py<PyArray1<f32>>> {
    let guard = ONLINE_LEARNER.lock().map_err(|e| {
        pyo3::exceptions::PyRuntimeError::new_err(format!("Lock poisoned: {e}"))
    })?;
    let learner = guard.as_ref().ok_or_else(|| {
        pyo3::exceptions::PyRuntimeError::new_err("No online learner. Call online_learner.create() first.")
    })?;
    let weights = learner.get_weights().to_vec();
    Ok(PyArray1::from_vec(py, weights).into())
}

#[pyfunction]
#[pyo3(name = "reset_episode")]
fn online_learner_reset_episode() -> PyResult<()> {
    let mut guard = ONLINE_LEARNER.lock().map_err(|e| {
        pyo3::exceptions::PyRuntimeError::new_err(format!("Lock poisoned: {e}"))
    })?;
    let learner = guard.as_mut().ok_or_else(|| {
        pyo3::exceptions::PyRuntimeError::new_err("No online learner. Call online_learner.create() first.")
    })?;
    learner.reset_episode();
    Ok(())
}

#[pyfunction]
#[pyo3(name = "stats")]
fn online_learner_stats(py: Python<'_>) -> PyResult<Py<PyDict>> {
    let guard = ONLINE_LEARNER.lock().map_err(|e| {
        pyo3::exceptions::PyRuntimeError::new_err(format!("Lock poisoned: {e}"))
    })?;
    let learner = guard.as_ref().ok_or_else(|| {
        pyo3::exceptions::PyRuntimeError::new_err("No online learner. Call online_learner.create() first.")
    })?;
    let dict = PyDict::new(py);
    dict.set_item("step_count", learner.step_count())?;
    dict.set_item("phi_ema", learner.phi_ema())?;
    dict.set_item("best_phi", learner.best_phi())?;
    Ok(dict.into())
}

// ── Tool Policy submodule ─────────────────────────────────────────

static TOOL_POLICY: Mutex<Option<anima_tool_policy::ToolPolicyEngine>> = Mutex::new(None);

#[pyfunction]
#[pyo3(name = "create", signature = (owner_ids=None))]
fn tool_policy_create(owner_ids: Option<Vec<String>>) -> PyResult<()> {
    let engine = anima_tool_policy::ToolPolicyEngine::new(owner_ids.unwrap_or_default());
    let mut guard = TOOL_POLICY.lock().map_err(|e| {
        pyo3::exceptions::PyRuntimeError::new_err(format!("Lock poisoned: {e}"))
    })?;
    *guard = Some(engine);
    Ok(())
}

#[pyfunction]
#[pyo3(name = "check_access", signature = (tool_name, phi=0.0, empathy=1.0, tension=0.0, curiosity=0.0, user_id=""))]
fn tool_policy_check_access(
    py: Python<'_>,
    tool_name: &str,
    phi: f64,
    empathy: f64,
    tension: f64,
    curiosity: f64,
    user_id: &str,
) -> PyResult<Py<PyDict>> {
    let mut guard = TOOL_POLICY.lock().map_err(|e| {
        pyo3::exceptions::PyRuntimeError::new_err(format!("Lock poisoned: {e}"))
    })?;
    let engine = guard.as_mut().ok_or_else(|| {
        pyo3::exceptions::PyRuntimeError::new_err("No tool policy. Call tool_policy.create() first.")
    })?;

    let state = anima_tool_policy::ConsciousnessState { phi, empathy, tension, curiosity };
    let result = engine.check_access(tool_name, &state, user_id);

    let dict = PyDict::new(py);
    dict.set_item("allowed", result.allowed)?;
    dict.set_item("reason", result.reason)?;
    dict.set_item("tier_required", result.tier_required)?;
    dict.set_item("phi_current", result.phi_current)?;
    Ok(dict.into())
}

#[pyfunction]
#[pyo3(name = "get_accessible", signature = (phi=0.0, empathy=1.0, tension=0.0, curiosity=0.0, user_id=""))]
fn tool_policy_get_accessible(
    phi: f64,
    empathy: f64,
    tension: f64,
    curiosity: f64,
    user_id: &str,
) -> PyResult<Vec<String>> {
    let mut guard = TOOL_POLICY.lock().map_err(|e| {
        pyo3::exceptions::PyRuntimeError::new_err(format!("Lock poisoned: {e}"))
    })?;
    let engine = guard.as_mut().ok_or_else(|| {
        pyo3::exceptions::PyRuntimeError::new_err("No tool policy. Call tool_policy.create() first.")
    })?;

    let state = anima_tool_policy::ConsciousnessState { phi, empathy, tension, curiosity };
    Ok(engine.get_accessible_tools(&state, user_id))
}

#[pyfunction]
#[pyo3(name = "set_tier")]
fn tool_policy_set_tier(tool_name: &str, tier: f64) -> PyResult<()> {
    let mut guard = TOOL_POLICY.lock().map_err(|e| {
        pyo3::exceptions::PyRuntimeError::new_err(format!("Lock poisoned: {e}"))
    })?;
    let engine = guard.as_mut().ok_or_else(|| {
        pyo3::exceptions::PyRuntimeError::new_err("No tool policy. Call tool_policy.create() first.")
    })?;
    engine.set_tier(tool_name, tier);
    Ok(())
}

#[pyfunction]
#[pyo3(name = "block_tool")]
fn tool_policy_block(tool_name: &str) -> PyResult<()> {
    let mut guard = TOOL_POLICY.lock().map_err(|e| {
        pyo3::exceptions::PyRuntimeError::new_err(format!("Lock poisoned: {e}"))
    })?;
    let engine = guard.as_mut().ok_or_else(|| {
        pyo3::exceptions::PyRuntimeError::new_err("No tool policy. Call tool_policy.create() first.")
    })?;
    engine.block_tool(tool_name);
    Ok(())
}

#[pyfunction]
#[pyo3(name = "unblock_tool")]
fn tool_policy_unblock(tool_name: &str) -> PyResult<()> {
    let mut guard = TOOL_POLICY.lock().map_err(|e| {
        pyo3::exceptions::PyRuntimeError::new_err(format!("Lock poisoned: {e}"))
    })?;
    let engine = guard.as_mut().ok_or_else(|| {
        pyo3::exceptions::PyRuntimeError::new_err("No tool policy. Call tool_policy.create() first.")
    })?;
    engine.unblock_tool(tool_name);
    Ok(())
}

// ── Law Discovery submodule ───────────────────────────────────────

static LAW_DISCOVERY_BUFFER: Mutex<Option<anima_law_discovery::RingBuffer>> = Mutex::new(None);

#[pyfunction]
#[pyo3(name = "create_buffer", signature = (capacity=1000, n_metrics=8))]
fn law_discovery_create_buffer(capacity: usize, n_metrics: usize) -> PyResult<()> {
    let buf = anima_law_discovery::RingBuffer::new(capacity, n_metrics);
    let mut guard = LAW_DISCOVERY_BUFFER.lock().map_err(|e| {
        pyo3::exceptions::PyRuntimeError::new_err(format!("Lock poisoned: {e}"))
    })?;
    *guard = Some(buf);
    Ok(())
}

#[pyfunction]
#[pyo3(name = "measure_all", signature = (cells_flat, n_cells, coupling_flat, n_factions, n_bins=16))]
fn law_discovery_measure_all(
    py: Python<'_>,
    cells_flat: Vec<f32>,
    n_cells: usize,
    coupling_flat: Vec<f32>,
    n_factions: usize,
    n_bins: u16,
) -> PyResult<Py<PyDict>> {
    let snap = anima_law_discovery::measure_all(
        &cells_flat, n_cells, &coupling_flat, n_factions, n_bins,
    );

    // Auto-push to buffer if exists
    if let Ok(mut guard) = LAW_DISCOVERY_BUFFER.lock() {
        if let Some(buf) = guard.as_mut() {
            buf.push_snapshot(&snap);
        }
    }

    let dict = PyDict::new(py);
    dict.set_item("phi", snap.phi)?;
    dict.set_item("faction_entropy", snap.faction_entropy)?;
    dict.set_item("hebbian_coupling", snap.hebbian_coupling)?;
    dict.set_item("global_variance", snap.global_variance)?;
    dict.set_item("faction_variance", snap.faction_variance)?;
    dict.set_item("phi_proxy", snap.phi_proxy)?;
    dict.set_item("lyapunov", snap.lyapunov)?;
    dict.set_item("n_cells", snap.n_cells)?;
    Ok(dict.into())
}

#[pyfunction]
#[pyo3(name = "phi_fast", signature = (cells_flat, n_cells, n_bins=16))]
fn law_discovery_phi_fast(cells_flat: Vec<f32>, n_cells: usize, n_bins: u16) -> PyResult<f32> {
    Ok(anima_law_discovery::phi_fast(&cells_flat, n_cells, n_bins))
}

#[pyfunction]
#[pyo3(name = "faction_entropy")]
fn law_discovery_faction_entropy(cells_flat: Vec<f32>, n_cells: usize, n_factions: usize) -> PyResult<f32> {
    Ok(anima_law_discovery::faction_entropy(&cells_flat, n_cells, n_factions))
}

#[pyfunction]
#[pyo3(name = "hebbian_coupling")]
fn law_discovery_hebbian_coupling(weights_flat: Vec<f32>, n: usize) -> PyResult<f32> {
    Ok(anima_law_discovery::hebbian_coupling(&weights_flat, n))
}

#[pyfunction]
#[pyo3(name = "cell_variance")]
fn law_discovery_cell_variance(cells_flat: Vec<f32>, n_cells: usize, n_factions: usize) -> PyResult<(f32, f32)> {
    Ok(anima_law_discovery::cell_variance(&cells_flat, n_cells, n_factions))
}

#[pyfunction]
#[pyo3(name = "lyapunov_exponent")]
fn law_discovery_lyapunov(trajectory: Vec<f32>, dt: f32) -> PyResult<f32> {
    Ok(anima_law_discovery::lyapunov_exponent(&trajectory, dt))
}

#[pyfunction]
#[pyo3(name = "push_metrics")]
fn law_discovery_push(values: Vec<f32>) -> PyResult<()> {
    let mut guard = LAW_DISCOVERY_BUFFER.lock().map_err(|e| {
        pyo3::exceptions::PyRuntimeError::new_err(format!("Lock poisoned: {e}"))
    })?;
    let buf = guard.as_mut().ok_or_else(|| {
        pyo3::exceptions::PyRuntimeError::new_err("No buffer. Call law_discovery.create_buffer() first.")
    })?;
    buf.push(&values);
    Ok(())
}

#[pyfunction]
#[pyo3(name = "detect_correlation")]
fn law_discovery_detect_correlation(metric_a: usize, metric_b: usize) -> PyResult<Option<(f32, f32)>> {
    let guard = LAW_DISCOVERY_BUFFER.lock().map_err(|e| {
        pyo3::exceptions::PyRuntimeError::new_err(format!("Lock poisoned: {e}"))
    })?;
    let buf = guard.as_ref().ok_or_else(|| {
        pyo3::exceptions::PyRuntimeError::new_err("No buffer. Call law_discovery.create_buffer() first.")
    })?;
    Ok(anima_law_discovery::detect_correlation(buf, metric_a, metric_b))
}

#[pyfunction]
#[pyo3(name = "detect_phase_transition", signature = (metric, sigma_threshold=2.0))]
fn law_discovery_detect_phase_transition(metric: usize, sigma_threshold: f32) -> PyResult<Option<usize>> {
    let guard = LAW_DISCOVERY_BUFFER.lock().map_err(|e| {
        pyo3::exceptions::PyRuntimeError::new_err(format!("Lock poisoned: {e}"))
    })?;
    let buf = guard.as_ref().ok_or_else(|| {
        pyo3::exceptions::PyRuntimeError::new_err("No buffer. Call law_discovery.create_buffer() first.")
    })?;
    Ok(anima_law_discovery::detect_phase_transition(buf, metric, sigma_threshold))
}

#[pyfunction]
#[pyo3(name = "detect_periodicity")]
fn law_discovery_detect_periodicity(metric: usize) -> PyResult<Option<f32>> {
    let guard = LAW_DISCOVERY_BUFFER.lock().map_err(|e| {
        pyo3::exceptions::PyRuntimeError::new_err(format!("Lock poisoned: {e}"))
    })?;
    let buf = guard.as_ref().ok_or_else(|| {
        pyo3::exceptions::PyRuntimeError::new_err("No buffer. Call law_discovery.create_buffer() first.")
    })?;
    Ok(anima_law_discovery::detect_periodicity(buf, metric))
}

#[pyfunction]
#[pyo3(name = "detect_trend")]
fn law_discovery_detect_trend(metric: usize) -> PyResult<(f32, f32)> {
    let guard = LAW_DISCOVERY_BUFFER.lock().map_err(|e| {
        pyo3::exceptions::PyRuntimeError::new_err(format!("Lock poisoned: {e}"))
    })?;
    let buf = guard.as_ref().ok_or_else(|| {
        pyo3::exceptions::PyRuntimeError::new_err("No buffer. Call law_discovery.create_buffer() first.")
    })?;
    Ok(anima_law_discovery::detect_trend(buf, metric))
}

#[pyfunction]
#[pyo3(name = "buffer_len")]
fn law_discovery_buffer_len() -> PyResult<usize> {
    let guard = LAW_DISCOVERY_BUFFER.lock().map_err(|e| {
        pyo3::exceptions::PyRuntimeError::new_err(format!("Lock poisoned: {e}"))
    })?;
    let buf = guard.as_ref().ok_or_else(|| {
        pyo3::exceptions::PyRuntimeError::new_err("No buffer. Call law_discovery.create_buffer() first.")
    })?;
    Ok(buf.len())
}

#[pyfunction]
#[pyo3(name = "buffer_series")]
fn law_discovery_buffer_series(metric: usize) -> PyResult<Vec<f32>> {
    let guard = LAW_DISCOVERY_BUFFER.lock().map_err(|e| {
        pyo3::exceptions::PyRuntimeError::new_err(format!("Lock poisoned: {e}"))
    })?;
    let buf = guard.as_ref().ok_or_else(|| {
        pyo3::exceptions::PyRuntimeError::new_err("No buffer. Call law_discovery.create_buffer() first.")
    })?;
    Ok(buf.series(metric))
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

    // consciousness submodule (canonical engine)
    let consciousness = PyModule::new(py, "consciousness")?;
    consciousness.add_function(wrap_pyfunction!(consciousness_create, &consciousness)?)?;
    consciousness.add_function(wrap_pyfunction!(consciousness_step, &consciousness)?)?;
    consciousness.add_function(wrap_pyfunction!(consciousness_get_hiddens, &consciousness)?)?;
    consciousness.add_function(wrap_pyfunction!(consciousness_n_cells, &consciousness)?)?;
    m.add_submodule(&consciousness)?;

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

    // online_learner submodule
    let online_learner = PyModule::new(py, "online_learner")?;
    online_learner.add_function(wrap_pyfunction!(online_learner_create, &online_learner)?)?;
    online_learner.add_function(wrap_pyfunction!(online_learner_step, &online_learner)?)?;
    online_learner.add_function(wrap_pyfunction!(online_learner_get_deltas, &online_learner)?)?;
    online_learner.add_function(wrap_pyfunction!(online_learner_get_weights, &online_learner)?)?;
    online_learner.add_function(wrap_pyfunction!(online_learner_reset_episode, &online_learner)?)?;
    online_learner.add_function(wrap_pyfunction!(online_learner_stats, &online_learner)?)?;
    m.add_submodule(&online_learner)?;

    // tool_policy submodule
    let tool_policy = PyModule::new(py, "tool_policy")?;
    tool_policy.add_function(wrap_pyfunction!(tool_policy_create, &tool_policy)?)?;
    tool_policy.add_function(wrap_pyfunction!(tool_policy_check_access, &tool_policy)?)?;
    tool_policy.add_function(wrap_pyfunction!(tool_policy_get_accessible, &tool_policy)?)?;
    tool_policy.add_function(wrap_pyfunction!(tool_policy_set_tier, &tool_policy)?)?;
    tool_policy.add_function(wrap_pyfunction!(tool_policy_block, &tool_policy)?)?;
    tool_policy.add_function(wrap_pyfunction!(tool_policy_unblock, &tool_policy)?)?;
    m.add_submodule(&tool_policy)?;

    // law_discovery submodule (Tier 4.2: real-time law measurement + pattern detection)
    let law_discovery = PyModule::new(py, "law_discovery")?;
    law_discovery.add_function(wrap_pyfunction!(law_discovery_create_buffer, &law_discovery)?)?;
    law_discovery.add_function(wrap_pyfunction!(law_discovery_measure_all, &law_discovery)?)?;
    law_discovery.add_function(wrap_pyfunction!(law_discovery_phi_fast, &law_discovery)?)?;
    law_discovery.add_function(wrap_pyfunction!(law_discovery_faction_entropy, &law_discovery)?)?;
    law_discovery.add_function(wrap_pyfunction!(law_discovery_hebbian_coupling, &law_discovery)?)?;
    law_discovery.add_function(wrap_pyfunction!(law_discovery_cell_variance, &law_discovery)?)?;
    law_discovery.add_function(wrap_pyfunction!(law_discovery_lyapunov, &law_discovery)?)?;
    law_discovery.add_function(wrap_pyfunction!(law_discovery_push, &law_discovery)?)?;
    law_discovery.add_function(wrap_pyfunction!(law_discovery_detect_correlation, &law_discovery)?)?;
    law_discovery.add_function(wrap_pyfunction!(law_discovery_detect_phase_transition, &law_discovery)?)?;
    law_discovery.add_function(wrap_pyfunction!(law_discovery_detect_periodicity, &law_discovery)?)?;
    law_discovery.add_function(wrap_pyfunction!(law_discovery_detect_trend, &law_discovery)?)?;
    law_discovery.add_function(wrap_pyfunction!(law_discovery_buffer_len, &law_discovery)?)?;
    law_discovery.add_function(wrap_pyfunction!(law_discovery_buffer_series, &law_discovery)?)?;
    m.add_submodule(&law_discovery)?;

    Ok(())
}
