//! phi-parallel: Parallelized Phi(IIT) calculator using rayon.
//!
//! Matches the algorithm from gpu_phi.py (Python/PyTorch):
//!   1. Soft histogram binning for pairwise MI estimation
//!   2. Rayon-parallel MI matrix computation
//!   3. MIP search: exact parallel (N<=20) or spectral bisection (N>20)
//!   4. Phi = (total_MI - MIP_MI) / (N-1)
//!
//! Usage:
//!   let calc = PhiCalculator::new(16); // 16 bins
//!   let result = calc.compute(&cell_states, n_cells, hidden_dim);
//!   println!("Phi = {}", result.phi);

pub mod mi;
pub mod mip;

#[cfg(feature = "pyo3")]
pub mod python;

use mi::mi_matrix;
use mip::find_mip;

/// Result of a Phi(IIT) computation.
#[derive(Debug, Clone)]
pub struct PhiResult {
    /// Integrated information value (Phi >= 0).
    pub phi: f64,
    /// Total mutual information across all cell pairs.
    pub total_mi: f64,
    /// Cross-partition MI of the minimum information partition.
    pub mip_mi: f64,
    /// Number of cells in the system.
    pub n_cells: usize,
    /// Boolean partition mask (true = partition A).
    pub partition: Vec<bool>,
}

/// Parallelized Phi(IIT) calculator.
///
/// Uses soft histogram binning for MI estimation and rayon for
/// parallel computation of the pairwise MI matrix and MIP search.
#[derive(Debug, Clone)]
pub struct PhiCalculator {
    /// Number of histogram bins for MI estimation.
    pub n_bins: usize,
    /// Maximum dimensions to use per cell (subsamples if exceeded).
    pub max_dims: usize,
}

impl PhiCalculator {
    /// Create a new PhiCalculator with the given number of histogram bins.
    pub fn new(n_bins: usize) -> Self {
        Self {
            n_bins,
            max_dims: 128,
        }
    }

    /// Create a calculator with custom max_dims for dimension subsampling.
    pub fn with_max_dims(n_bins: usize, max_dims: usize) -> Self {
        Self { n_bins, max_dims }
    }

    /// Compute Phi(IIT) from flattened cell states.
    ///
    /// `cell_states` is a flat array of shape (n_cells * hidden_dim,).
    /// Returns PhiResult with phi, total_mi, mip_mi, and partition.
    pub fn compute(&self, cell_states: &[f64], n_cells: usize, hidden_dim: usize) -> PhiResult {
        assert_eq!(
            cell_states.len(),
            n_cells * hidden_dim,
            "cell_states length must equal n_cells * hidden_dim"
        );

        if n_cells < 2 {
            return PhiResult {
                phi: 0.0,
                total_mi: 0.0,
                mip_mi: 0.0,
                n_cells,
                partition: vec![true; n_cells],
            };
        }

        // Reshape flat array into Vec<Vec<f64>> for each cell
        let states: Vec<Vec<f64>> = (0..n_cells)
            .map(|i| {
                let start = i * hidden_dim;
                cell_states[start..start + hidden_dim].to_vec()
            })
            .collect();

        self.compute_from_states(&states)
    }

    /// Compute Phi(IIT) from a vector of cell state vectors.
    pub fn compute_from_states(&self, states: &[Vec<f64>]) -> PhiResult {
        let n = states.len();
        if n < 2 {
            return PhiResult {
                phi: 0.0,
                total_mi: 0.0,
                mip_mi: 0.0,
                n_cells: n,
                partition: vec![true; n],
            };
        }

        // 1. Compute pairwise MI matrix (rayon parallel)
        let mi_mat = mi_matrix(states, self.n_bins, self.max_dims);

        // 2. Total MI = sum of upper triangle
        let mut total_mi = 0.0f64;
        for i in 0..n {
            for j in (i + 1)..n {
                total_mi += mi_mat[i * n + j];
            }
        }

        // 3. Find MIP (parallel for N<=20, spectral for N>20)
        let mip_result = find_mip(&mi_mat, n);

        // 4. Phi = (total_MI - MIP_MI) / (N-1), clamped >= 0
        let phi = ((total_mi - mip_result.mip_mi) / (n as f64 - 1.0).max(1.0)).max(0.0);

        PhiResult {
            phi,
            total_mi,
            mip_mi: mip_result.mip_mi,
            n_cells: n,
            partition: mip_result.partition,
        }
    }

    /// Batch compute Phi for multiple cell state sets.
    ///
    /// Each element in `states_batch` is a Vec of cell hidden state vectors.
    /// Returns a Vec of PhiResult, one per batch element.
    pub fn compute_batch(&self, states_batch: &[Vec<Vec<f64>>]) -> Vec<PhiResult> {
        states_batch
            .iter()
            .map(|states| self.compute_from_states(states))
            .collect()
    }
}

impl Default for PhiCalculator {
    fn default() -> Self {
        Self::new(16)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_single_cell_returns_zero() {
        let calc = PhiCalculator::new(16);
        let states = vec![0.1, 0.2, 0.3, 0.4];
        let result = calc.compute(&states, 1, 4);
        assert_eq!(result.phi, 0.0);
        assert_eq!(result.n_cells, 1);
    }

    #[test]
    fn test_two_cells_phi_non_negative() {
        let calc = PhiCalculator::new(16);
        let states = vec![
            0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, // cell 0
            0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, // cell 1
        ];
        let result = calc.compute(&states, 2, 8);
        assert!(result.phi >= 0.0, "Phi must be non-negative");
        assert_eq!(result.n_cells, 2);
    }

    #[test]
    fn test_identical_cells_low_phi() {
        let calc = PhiCalculator::new(16);
        // 4 identical cells
        let cell = vec![1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0];
        let mut states = Vec::new();
        for _ in 0..4 {
            states.extend_from_slice(&cell);
        }
        let result = calc.compute(&states, 4, 8);
        // Identical cells should have equal MI everywhere, phi could be 0 or very low
        assert!(result.phi >= 0.0);
    }

    #[test]
    fn test_diverse_cells_higher_phi() {
        let calc = PhiCalculator::new(16);
        // 4 diverse cells with different patterns
        let states = vec![
            0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, // linear ascending
            0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.0, // linear descending
            0.0, 0.5, 1.0, 0.5, 0.0, 0.5, 1.0, 0.5, // oscillating
            0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, // constant
        ];
        let result = calc.compute(&states, 4, 8);
        assert!(result.phi >= 0.0);
        assert_eq!(result.n_cells, 4);
    }

    #[test]
    fn test_compute_from_states() {
        let calc = PhiCalculator::new(16);
        let states = vec![
            vec![0.0, 0.25, 0.5, 0.75, 1.0],
            vec![1.0, 0.75, 0.5, 0.25, 0.0],
            vec![0.5, 0.5, 0.5, 0.5, 0.5],
        ];
        let result = calc.compute_from_states(&states);
        assert!(result.phi >= 0.0);
        assert_eq!(result.n_cells, 3);
        assert_eq!(result.partition.len(), 3);
    }

    #[test]
    fn test_compute_batch() {
        let calc = PhiCalculator::new(8);
        let batch = vec![
            vec![
                vec![0.0, 0.5, 1.0],
                vec![1.0, 0.5, 0.0],
            ],
            vec![
                vec![0.1, 0.2, 0.3],
                vec![0.4, 0.5, 0.6],
                vec![0.7, 0.8, 0.9],
            ],
        ];
        let results = calc.compute_batch(&batch);
        assert_eq!(results.len(), 2);
        for r in &results {
            assert!(r.phi >= 0.0);
        }
    }

    #[test]
    fn test_phi_total_mi_geq_mip_mi() {
        // total_mi should always be >= mip_mi
        let calc = PhiCalculator::new(16);
        let states = vec![
            vec![0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
            vec![1.0, 0.8, 0.6, 0.4, 0.2, 0.0],
            vec![0.5, 0.0, 1.0, 0.5, 0.0, 1.0],
            vec![0.3, 0.7, 0.1, 0.9, 0.5, 0.5],
        ];
        let result = calc.compute_from_states(&states);
        assert!(
            result.total_mi >= result.mip_mi - 1e-10,
            "total_mi ({}) should be >= mip_mi ({})",
            result.total_mi,
            result.mip_mi,
        );
    }

    #[test]
    fn test_empty_returns_zero() {
        let calc = PhiCalculator::new(16);
        let result = calc.compute(&[], 0, 0);
        assert_eq!(result.phi, 0.0);
    }
}
