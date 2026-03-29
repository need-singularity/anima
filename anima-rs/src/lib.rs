// anima-rs — Rust hot paths for Anima Agent
//
// Modules:
//   tension      — Real-time tension computation (PureField repulsion)
//   tension_link — 5-channel meta-telepathy protocol
//   sandbox      — Safe Python skill execution
//   router       — Message routing for multi-agent communication
//
// All exposed to Python via PyO3 as `anima_rs.*`

use numpy::{PyArray1, PyReadonlyArray1};
use pyo3::prelude::*;
use pyo3::types::PyList;

pub mod meta_ca;
pub mod ngram;
pub mod train_monitor;
pub mod router;
pub mod sandbox;
pub mod tension;
pub mod tension_link;

// ============================================================================
// PyO3 bindings
// ============================================================================

/// Compute tension between Engine A and Engine G.
/// Returns (magnitude, direction_list).
#[pyfunction]
#[pyo3(name = "compute_tension")]
fn py_compute_tension<'py>(
    py: Python<'py>,
    engine_a: PyReadonlyArray1<f32>,
    engine_g: PyReadonlyArray1<f32>,
) -> PyResult<(f32, Bound<'py, PyArray1<f32>>)> {
    let a = engine_a.as_slice()?;
    let g = engine_g.as_slice()?;
    let (mag, dir) = tension::compute_tension(a, g);
    Ok((mag, PyArray1::from_vec(py, dir)))
}

/// Batch compute pairwise tensions across all cells.
/// states: flat array [n_cells * dim], returns pairwise tension magnitudes.
#[pyfunction]
#[pyo3(name = "batch_tension")]
fn py_batch_tension<'py>(
    py: Python<'py>,
    states: PyReadonlyArray1<f32>,
    n_cells: usize,
    dim: usize,
) -> PyResult<Bound<'py, PyArray1<f32>>> {
    let s = states.as_slice()?;
    let tensions = tension::batch_tension(s, n_cells, dim);
    Ok(PyArray1::from_vec(py, tensions))
}

/// Compute 128D tension fingerprint from cell hidden states.
/// states: flat array [n_cells * dim], returns 128D fingerprint.
#[pyfunction]
#[pyo3(name = "tension_fingerprint")]
fn py_tension_fingerprint<'py>(
    py: Python<'py>,
    states: PyReadonlyArray1<f32>,
    n_cells: usize,
    dim: usize,
) -> PyResult<Bound<'py, PyArray1<f32>>> {
    let s = states.as_slice()?;
    let fp = tension::tension_fingerprint(s, n_cells, dim);
    Ok(PyArray1::from_vec(py, fp))
}

/// Full 5-channel tension exchange between sender and receiver.
/// Returns dict with similarity, decoded_states, channel_scores.
#[pyfunction]
#[pyo3(name = "tension_exchange")]
fn py_tension_exchange<'py>(
    py: Python<'py>,
    sender_states: PyReadonlyArray1<f32>,
    receiver_states: PyReadonlyArray1<f32>,
    sender_n_cells: usize,
    sender_dim: usize,
    receiver_n_cells: usize,
    receiver_dim: usize,
) -> PyResult<Bound<'py, pyo3::types::PyDict>> {
    let s = sender_states.as_slice()?;
    let r = receiver_states.as_slice()?;

    let result = tension_link::full_exchange(
        s, r,
        sender_n_cells, sender_dim,
        receiver_n_cells, receiver_dim,
    );

    let dict = pyo3::types::PyDict::new(py);
    dict.set_item("similarity", result.similarity)?;
    dict.set_item("decoded_states", PyArray1::from_vec(py, result.decoded_states))?;
    dict.set_item("channel_scores", result.channel_scores.to_vec())?;

    Ok(dict)
}

/// Match two fingerprints, returns cosine similarity [0, 1].
#[pyfunction]
#[pyo3(name = "match_fingerprint")]
fn py_match_fingerprint(
    sender_fp: PyReadonlyArray1<f32>,
    receiver_fp: PyReadonlyArray1<f32>,
) -> PyResult<f32> {
    let s = sender_fp.as_slice()?;
    let r = receiver_fp.as_slice()?;
    Ok(tension_link::match_fingerprint(s, r))
}

/// Execute Python code safely in a sandboxed subprocess.
/// Returns stdout on success, raises RuntimeError on failure.
#[pyfunction]
#[pyo3(name = "execute_safe")]
fn py_execute_safe(code: &str, timeout_ms: u64) -> PyResult<String> {
    match sandbox::execute_python_safe(code, timeout_ms) {
        Ok(output) => Ok(output),
        Err(e) => Err(pyo3::exceptions::PyRuntimeError::new_err(format!("{}", e))),
    }
}

/// Validate Python code for security issues.
/// Returns list of (level, message, line) tuples.
#[pyfunction]
#[pyo3(name = "validate_code")]
fn py_validate_code<'py>(py: Python<'py>, code: &str) -> PyResult<Bound<'py, PyList>> {
    let warnings = sandbox::validate_code(code);
    let result = PyList::empty(py);
    for w in warnings {
        let level_str = match w.level {
            sandbox::WarningLevel::Critical => "critical",
            sandbox::WarningLevel::High => "high",
            sandbox::WarningLevel::Medium => "medium",
        };
        let tuple = pyo3::types::PyTuple::new(
            py,
            &[
                level_str.into_pyobject(py)?.into_any(),
                w.message.into_pyobject(py)?.into_any(),
                w.line.unwrap_or(0).into_pyobject(py)?.into_any(),
            ],
        )?;
        result.append(tuple)?;
    }
    Ok(result)
}

// ============================================================================
// Router bindings — exposed as anima_rs.Router class
// ============================================================================

#[pyclass]
struct Router {
    inner: router::MessageRouter,
}

#[pymethods]
impl Router {
    #[new]
    fn new(self_id: &str) -> Self {
        Self {
            inner: router::MessageRouter::new(self_id),
        }
    }

    fn create_channel(&mut self, name: &str) {
        self.inner.create_channel(name);
    }

    fn register_peer(&mut self, peer_id: &str) {
        self.inner.register_peer(peer_id);
    }

    fn subscribe(&mut self, channel: &str, peer_id: &str) {
        self.inner.subscribe(channel, peer_id);
    }

    fn route_message<'py>(&mut self, py: Python<'py>, channel: &str, message: &str) -> PyResult<Bound<'py, pyo3::types::PyDict>> {
        match self.inner.route_message(channel, message) {
            Ok(msg) => {
                let dict = pyo3::types::PyDict::new(py);
                dict.set_item("channel", msg.channel)?;
                dict.set_item("content", msg.content)?;
                dict.set_item("sender_id", msg.sender_id)?;
                dict.set_item("timestamp_ms", msg.timestamp_ms)?;
                dict.set_item("sequence", msg.sequence)?;
                Ok(dict)
            }
            Err(e) => Err(pyo3::exceptions::PyRuntimeError::new_err(format!("{}", e))),
        }
    }

    fn broadcast_to_peers(&mut self, message: &str, peer_ids: Vec<String>) -> PyResult<Vec<bool>> {
        let refs: Vec<&str> = peer_ids.iter().map(|s| s.as_str()).collect();
        let results = self.inner.broadcast_to_peers(message, &refs);
        Ok(results.into_iter().map(|r| r.is_ok()).collect())
    }

    fn drain_inbox<'py>(&mut self, py: Python<'py>, peer_id: &str) -> PyResult<Bound<'py, PyList>> {
        let msgs = self.inner.drain_inbox(peer_id);
        let list = PyList::empty(py);
        for msg in msgs {
            let dict = pyo3::types::PyDict::new(py);
            dict.set_item("channel", msg.channel)?;
            dict.set_item("content", msg.content)?;
            dict.set_item("sender_id", msg.sender_id)?;
            dict.set_item("timestamp_ms", msg.timestamp_ms)?;
            dict.set_item("sequence", msg.sequence)?;
            list.append(dict)?;
        }
        Ok(list)
    }

    fn list_channels(&self) -> Vec<String> {
        self.inner.list_channels()
    }

    fn list_peers(&self) -> Vec<String> {
        self.inner.list_peers()
    }
}

// ============================================================================
// N-gram bindings — fast corpus overlap detection
// ============================================================================

#[pyclass]
struct NgramIndex {
    inner: std::collections::HashSet<String>,
    n: usize,
}

#[pymethods]
impl NgramIndex {
    #[new]
    #[pyo3(signature = (corpus, n=4))]
    fn new(corpus: &str, n: usize) -> Self {
        Self {
            inner: ngram::build_ngram_index(corpus, n),
            n,
        }
    }

    /// Number of unique n-grams in the index.
    fn len(&self) -> usize {
        self.inner.len()
    }

    /// Check overlap ratio of generated text against this index.
    #[pyo3(signature = (generated, n=None))]
    fn overlap(&self, generated: &str, n: Option<usize>) -> f64 {
        let n = n.unwrap_or(self.n);
        ngram::ngram_overlap(generated, &self.inner, n)
    }
}

/// Build n-gram index from corpus text. Returns NgramIndex handle.
#[pyfunction]
#[pyo3(name = "build_ngram_index", signature = (corpus, n=4))]
fn py_build_ngram_index(corpus: &str, n: usize) -> NgramIndex {
    NgramIndex {
        inner: ngram::build_ngram_index(corpus, n),
        n,
    }
}

/// Check overlap ratio of generated text against a NgramIndex.
#[pyfunction]
#[pyo3(name = "ngram_overlap", signature = (generated, index, n=None))]
fn py_ngram_overlap(generated: &str, index: &NgramIndex, n: Option<usize>) -> f64 {
    let n = n.unwrap_or(index.n);
    ngram::ngram_overlap(generated, &index.inner, n)
}

/// Batch check multiple generated texts against corpus.
/// Returns list of overlap ratios.
#[pyfunction]
#[pyo3(name = "batch_ngram_check", signature = (texts, corpus, n=4))]
fn py_batch_ngram_check(texts: Vec<String>, corpus: &str, n: usize) -> Vec<f64> {
    ngram::batch_ngram_check(&texts, corpus, n)
}

// ============================================================================
// META-CA bindings — consciousness-guided decoder auto-design
// ============================================================================

/// Simulate META-CA for a single data type.
/// Returns dict with residual, gate, H, alpha, dominant_rule, rule_entropy, etc.
#[pyfunction]
#[pyo3(name = "meta_ca_simulate", signature = (name, steps=5000, seed=42))]
fn py_meta_ca_simulate<'py>(
    py: Python<'py>,
    name: &str,
    steps: usize,
    seed: u64,
) -> PyResult<Bound<'py, pyo3::types::PyDict>> {
    let profile = meta_ca::DataProfile::from_name(name);
    let result = meta_ca::simulate(&profile, steps, seed);

    let dict = pyo3::types::PyDict::new(py);
    dict.set_item("name", name)?;
    dict.set_item("residual", result.residual)?;
    dict.set_item("gate", result.gate)?;
    dict.set_item("H", result.h_final)?;
    dict.set_item("alpha", result.alpha)?;
    dict.set_item("dominant_rule", result.dominant_rule)?;
    dict.set_item("rule_entropy", result.rule_entropy)?;
    dict.set_item("steps_optimal", result.steps_optimal)?;
    dict.set_item("convergence_step", result.convergence_step)?;
    dict.set_item("h_trajectory", result.h_trajectory)?;
    Ok(dict)
}

/// Batch simulate META-CA for multiple data types in parallel (rayon).
/// Returns list of dicts.
#[pyfunction]
#[pyo3(name = "meta_ca_batch", signature = (names, steps=5000, seed=42))]
fn py_meta_ca_batch<'py>(
    py: Python<'py>,
    names: Vec<String>,
    steps: usize,
    seed: u64,
) -> PyResult<Bound<'py, PyList>> {
    let profiles: Vec<meta_ca::DataProfile> = names.iter()
        .map(|n| meta_ca::DataProfile::from_name(n))
        .collect();
    let results = meta_ca::simulate_batch(&profiles, steps, seed);

    let list = PyList::empty(py);
    for (i, result) in results.iter().enumerate() {
        let dict = pyo3::types::PyDict::new(py);
        dict.set_item("name", &names[i])?;
        dict.set_item("residual", result.residual)?;
        dict.set_item("gate", result.gate)?;
        dict.set_item("H", result.h_final)?;
        dict.set_item("alpha", result.alpha)?;
        dict.set_item("dominant_rule", result.dominant_rule)?;
        dict.set_item("rule_entropy", result.rule_entropy)?;
        dict.set_item("steps_optimal", result.steps_optimal)?;
        dict.set_item("convergence_step", result.convergence_step)?;
        list.append(dict)?;
    }
    Ok(list)
}

/// Multi-seed verification for a single data type.
/// Returns list of dicts (one per seed).
#[pyfunction]
#[pyo3(name = "meta_ca_verify", signature = (name, steps=5000, seeds=None))]
fn py_meta_ca_verify<'py>(
    py: Python<'py>,
    name: &str,
    steps: usize,
    seeds: Option<Vec<u64>>,
) -> PyResult<Bound<'py, PyList>> {
    let seeds = seeds.unwrap_or_else(|| vec![42, 123, 456, 789, 1337]);
    let profile = meta_ca::DataProfile::from_name(name);
    let results = meta_ca::verify_multi_seed(&profile, steps, &seeds);

    let list = PyList::empty(py);
    for (i, result) in results.iter().enumerate() {
        let dict = pyo3::types::PyDict::new(py);
        dict.set_item("seed", seeds[i])?;
        dict.set_item("residual", result.residual)?;
        dict.set_item("gate", result.gate)?;
        dict.set_item("H", result.h_final)?;
        dict.set_item("alpha", result.alpha)?;
        dict.set_item("dominant_rule", result.dominant_rule)?;
        dict.set_item("rule_entropy", result.rule_entropy)?;
        list.append(dict)?;
    }
    Ok(list)
}

/// Auto-design a decoder for given data type.
/// Returns dict with decoder specification.
#[pyfunction]
#[pyo3(name = "design_decoder", signature = (name, steps=10000, seeds=None))]
fn py_design_decoder<'py>(
    py: Python<'py>,
    name: &str,
    steps: usize,
    seeds: Option<Vec<u64>>,
) -> PyResult<Bound<'py, pyo3::types::PyDict>> {
    let seeds = seeds.unwrap_or_else(|| vec![42, 123, 456, 789, 1337]);
    let profile = meta_ca::DataProfile::from_name(name);
    let results = meta_ca::verify_multi_seed(&profile, steps, &seeds);
    let spec = meta_ca::design_decoder(&results, &profile);

    let dict = pyo3::types::PyDict::new(py);
    dict.set_item("decoder_type", &spec.decoder_type)?;
    dict.set_item("ca_steps", spec.ca_steps)?;
    dict.set_item("gate_strength", spec.gate_strength)?;
    dict.set_item("coupling_alpha", spec.coupling_alpha)?;
    dict.set_item("dominant_rule", spec.dominant_rule)?;
    dict.set_item("rule_entropy", spec.rule_entropy)?;
    dict.set_item("estimated_us", spec.estimated_us)?;
    dict.set_item("estimated_acs", spec.estimated_acs)?;
    dict.set_item("confidence", spec.confidence)?;
    Ok(dict)
}

// ============================================================================
// Module definition
// ============================================================================

#[pymodule]
fn anima_rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Tension functions
    m.add_function(wrap_pyfunction!(py_compute_tension, m)?)?;
    m.add_function(wrap_pyfunction!(py_batch_tension, m)?)?;
    m.add_function(wrap_pyfunction!(py_tension_fingerprint, m)?)?;

    // Tension link functions
    m.add_function(wrap_pyfunction!(py_tension_exchange, m)?)?;
    m.add_function(wrap_pyfunction!(py_match_fingerprint, m)?)?;

    // Sandbox functions
    m.add_function(wrap_pyfunction!(py_execute_safe, m)?)?;
    m.add_function(wrap_pyfunction!(py_validate_code, m)?)?;

    // Router class
    m.add_class::<Router>()?;

    // N-gram functions
    m.add_function(wrap_pyfunction!(py_build_ngram_index, m)?)?;
    m.add_function(wrap_pyfunction!(py_ngram_overlap, m)?)?;
    m.add_function(wrap_pyfunction!(py_batch_ngram_check, m)?)?;
    m.add_class::<NgramIndex>()?;

    // META-CA functions
    m.add_function(wrap_pyfunction!(py_meta_ca_simulate, m)?)?;
    m.add_function(wrap_pyfunction!(py_meta_ca_batch, m)?)?;
    m.add_function(wrap_pyfunction!(py_meta_ca_verify, m)?)?;
    m.add_function(wrap_pyfunction!(py_design_decoder, m)?)?;

    // Training monitor
    m.add_function(wrap_pyfunction!(py_parse_training_log, m)?)?;
    m.add_function(wrap_pyfunction!(py_monitor_dashboard, m)?)?;

    Ok(())
}

// ============================================================================
// Training Monitor bindings
// ============================================================================

/// Parse a training log file and return dashboard + anomalies.
#[pyfunction]
#[pyo3(name = "parse_training_log")]
fn py_parse_training_log<'py>(
    py: Python<'py>,
    log_content: &str,
) -> PyResult<Bound<'py, pyo3::types::PyDict>> {
    let steps = train_monitor::TrainMonitor::parse_log(log_content);
    let mut monitor = train_monitor::TrainMonitor::new();

    let mut all_anomalies = Vec::new();
    for step in &steps {
        let anomalies = monitor.record(step.clone());
        all_anomalies.extend(anomalies);
    }

    let (total_steps, best_ce, psi, gate, n_anomalies) = monitor.summary();

    let dict = pyo3::types::PyDict::new(py);
    dict.set_item("total_steps", total_steps)?;
    dict.set_item("best_val_ce", best_ce)?;
    dict.set_item("psi_residual", psi)?;
    dict.set_item("gate", gate)?;
    dict.set_item("n_anomalies", n_anomalies)?;
    dict.set_item("n_steps_parsed", steps.len())?;
    dict.set_item("dashboard", monitor.dashboard())?;

    // Anomalies list
    let anomaly_list = PyList::empty(py);
    for a in &all_anomalies {
        let ad = pyo3::types::PyDict::new(py);
        ad.set_item("step", a.step)?;
        ad.set_item("type", &a.anomaly_type)?;
        ad.set_item("severity", &a.severity)?;
        ad.set_item("message", &a.message)?;
        anomaly_list.append(ad)?;
    }
    dict.set_item("anomalies", anomaly_list)?;

    Ok(dict)
}

/// Monitor a log file and return ASCII dashboard string.
#[pyfunction]
#[pyo3(name = "monitor_dashboard")]
fn py_monitor_dashboard(log_content: &str) -> PyResult<String> {
    let steps = train_monitor::TrainMonitor::parse_log(log_content);
    let mut monitor = train_monitor::TrainMonitor::new();
    for step in &steps {
        monitor.record(step.clone());
    }
    Ok(monitor.dashboard())
}
