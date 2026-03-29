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

    Ok(())
}
