//! PyO3 bindings for phi-parallel.
//!
//! Exposes PhiCalculator to Python with numpy array support.
//!
//! Python usage:
//!   from phi_parallel import PhiCalculator
//!   calc = PhiCalculator(n_bins=16)
//!   result = calc.compute(cell_states_np, n_cells, hidden_dim)
//!   print(result["phi"])
//!
//!   results = calc.compute_batch([states1, states2, ...])

#[cfg(feature = "pyo3")]
use numpy::PyReadonlyArray1;
#[cfg(feature = "pyo3")]
use pyo3::prelude::*;
#[cfg(feature = "pyo3")]
use pyo3::types::PyDict;

#[cfg(feature = "pyo3")]
use crate::PhiCalculator as RustPhiCalculator;

/// Python-facing PhiCalculator wrapping the Rust implementation.
#[cfg(feature = "pyo3")]
#[pyclass(name = "PhiCalculator")]
pub struct PyPhiCalculator {
    inner: RustPhiCalculator,
}

#[cfg(feature = "pyo3")]
#[pymethods]
impl PyPhiCalculator {
    /// Create a new PhiCalculator.
    ///
    /// Args:
    ///     n_bins: Number of histogram bins for MI estimation (default 16).
    ///     max_dims: Maximum dimensions per cell before subsampling (default 128).
    #[new]
    #[pyo3(signature = (n_bins=16, max_dims=128))]
    fn new(n_bins: usize, max_dims: usize) -> Self {
        Self {
            inner: RustPhiCalculator::with_max_dims(n_bins, max_dims),
        }
    }

    /// Compute Phi(IIT) from a flat numpy array of cell states.
    ///
    /// Args:
    ///     cell_states: 1D numpy array of shape (n_cells * hidden_dim,).
    ///     n_cells: Number of cells.
    ///     hidden_dim: Dimension of each cell's hidden state.
    ///
    /// Returns:
    ///     dict with keys: phi, total_mi, mip_mi, n_cells, partition.
    fn compute<'py>(
        &self,
        py: Python<'py>,
        cell_states: PyReadonlyArray1<f64>,
        n_cells: usize,
        hidden_dim: usize,
    ) -> PyResult<Bound<'py, PyDict>> {
        let states = cell_states.as_slice()?;
        let result = self.inner.compute(states, n_cells, hidden_dim);

        let dict = PyDict::new(py);
        dict.set_item("phi", result.phi)?;
        dict.set_item("total_mi", result.total_mi)?;
        dict.set_item("mip_mi", result.mip_mi)?;
        dict.set_item("n_cells", result.n_cells)?;
        dict.set_item("partition", result.partition)?;
        Ok(dict)
    }

    /// Batch compute Phi for multiple state sets.
    ///
    /// Args:
    ///     states_list: List of 1D numpy arrays, each (n_cells_i * hidden_dim_i,).
    ///     shapes: List of (n_cells, hidden_dim) tuples.
    ///
    /// Returns:
    ///     List of dicts, each with phi, total_mi, mip_mi, n_cells, partition.
    fn compute_batch<'py>(
        &self,
        py: Python<'py>,
        states_list: Vec<PyReadonlyArray1<f64>>,
        shapes: Vec<(usize, usize)>,
    ) -> PyResult<Vec<Bound<'py, PyDict>>> {
        let mut results = Vec::with_capacity(states_list.len());

        for (states_arr, (n_cells, hidden_dim)) in states_list.iter().zip(shapes.iter()) {
            let states = states_arr.as_slice()?;
            let result = self.inner.compute(states, *n_cells, *hidden_dim);

            let dict = PyDict::new(py);
            dict.set_item("phi", result.phi)?;
            dict.set_item("total_mi", result.total_mi)?;
            dict.set_item("mip_mi", result.mip_mi)?;
            dict.set_item("n_cells", result.n_cells)?;
            dict.set_item("partition", result.partition)?;
            results.push(dict);
        }

        Ok(results)
    }

    /// Get the number of bins.
    #[getter]
    fn n_bins(&self) -> usize {
        self.inner.n_bins
    }

    /// Get the max dimensions setting.
    #[getter]
    fn max_dims(&self) -> usize {
        self.inner.max_dims
    }
}

/// Register the phi_parallel Python module.
#[cfg(feature = "pyo3")]
pub fn register_module(parent: &Bound<'_, PyModule>) -> PyResult<()> {
    let m = PyModule::new(parent.py(), "phi_parallel")?;
    m.add_class::<PyPhiCalculator>()?;
    parent.add_submodule(&m)?;
    Ok(())
}
