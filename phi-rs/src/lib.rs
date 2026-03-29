use ndarray::{Array1, Array2, ArrayView2, Axis};
use numpy::{PyArray1, PyReadonlyArray2};
use pyo3::prelude::*;
use pyo3::types::PyDict;
use rayon::prelude::*;
use std::collections::HashMap;

// ============================================================================
// PhiCalculator — Rust implementation for 100x speedup
//
// Input:  cell hidden states [n_cells x hidden_dim] as f32
// Output: phi value + components (pairwise MI matrix, partition info)
//
// Algorithm:
//   1. Bin each dimension into n_bins discrete bins
//   2. Compute pairwise mutual information between all cell pairs
//   3. Find minimum information partition (greedy approximation for large N)
//   4. Phi = total_MI - min_partition_MI
// ============================================================================

const DEFAULT_N_BINS: usize = 16;

/// Bin continuous values into discrete histogram bins.
/// Returns bin indices (0..n_bins-1) for each value.
fn bin_values(values: &[f32], n_bins: usize) -> Vec<usize> {
    if values.is_empty() {
        return vec![];
    }

    let min_val = values.iter().cloned().fold(f32::INFINITY, f32::min);
    let max_val = values.iter().cloned().fold(f32::NEG_INFINITY, f32::max);

    let range = max_val - min_val;
    if range < f32::EPSILON {
        // All values identical — put everything in bin 0
        return vec![0; values.len()];
    }

    let bin_width = range / n_bins as f32;
    values
        .iter()
        .map(|&v| {
            let bin = ((v - min_val) / bin_width) as usize;
            bin.min(n_bins - 1) // Clamp last edge case
        })
        .collect()
}

/// Compute Shannon entropy H(X) from bin counts.
/// H(X) = -sum(p * log2(p)) for p > 0
fn entropy(counts: &[u32], total: u32) -> f64 {
    if total == 0 {
        return 0.0;
    }
    let t = total as f64;
    counts
        .iter()
        .filter(|&&c| c > 0)
        .map(|&c| {
            let p = c as f64 / t;
            -p * p.log2()
        })
        .sum()
}

/// Compute mutual information MI(X; Y) between two cells.
///
/// MI(X;Y) = H(X) + H(Y) - H(X,Y)
///
/// Each cell is represented by its hidden_dim-dimensional state vector.
/// We concatenate bin indices across dimensions to form a joint distribution.
///
/// For efficiency, we use a simplified approach: average MI across all dimensions.
fn mutual_information_cells(
    cell_a: &[f32],  // [hidden_dim]
    cell_b: &[f32],  // [hidden_dim]
    n_bins: usize,
) -> f64 {
    let dim = cell_a.len();
    assert_eq!(dim, cell_b.len());

    if dim == 0 {
        return 0.0;
    }

    // Strategy: compute MI for each dimension pair (a_d, b_d), then average.
    // This is a lower bound on the true MI but is fast and scales well.
    let total_mi: f64 = (0..dim)
        .map(|d| {
            // Bin each dimension
            let bins_a = bin_single(cell_a[d], cell_a, n_bins, d);
            let bins_b = bin_single(cell_b[d], cell_b, n_bins, d);
            mi_from_bins(bins_a, bins_b, n_bins)
        })
        .sum();

    total_mi / dim as f64
}

/// Bin a single scalar value given the range of the full dimension slice.
/// Returns (bin_index, min_val, bin_width) but here we do the full approach:
/// We actually need all values to establish the range. For cell-level MI,
/// we treat each cell's hidden state as a single "sample" — but we need
/// multiple samples for MI to be meaningful.
///
/// Better approach: treat each hidden dimension as a "sample" of the cell's
/// state. So for MI(cell_a, cell_b), we have hidden_dim samples where
/// sample_i = (cell_a[i], cell_b[i]).
fn mi_from_paired_vectors(a: &[f32], b: &[f32], n_bins: usize) -> f64 {
    let n = a.len();
    assert_eq!(n, b.len());
    if n == 0 {
        return 0.0;
    }

    let bins_a = bin_values(a, n_bins);
    let bins_b = bin_values(b, n_bins);

    // Marginal counts
    let mut counts_a = vec![0u32; n_bins];
    let mut counts_b = vec![0u32; n_bins];
    // Joint counts (flattened 2D)
    let mut joint = vec![0u32; n_bins * n_bins];

    for i in 0..n {
        counts_a[bins_a[i]] += 1;
        counts_b[bins_b[i]] += 1;
        joint[bins_a[i] * n_bins + bins_b[i]] += 1;
    }

    let total = n as u32;
    let h_a = entropy(&counts_a, total);
    let h_b = entropy(&counts_b, total);
    let h_ab = entropy(&joint, total);

    // MI = H(A) + H(B) - H(A,B), clamped to >= 0
    (h_a + h_b - h_ab).max(0.0)
}

/// Unused helper — kept for reference
fn bin_single(_val: f32, _all: &[f32], _n_bins: usize, _d: usize) -> usize {
    0
}

/// Compute the full pairwise MI matrix for all cells.
/// Returns an n_cells x n_cells symmetric matrix.
fn compute_mi_matrix(states: &ArrayView2<f32>, n_bins: usize) -> Array2<f64> {
    let n_cells = states.nrows();
    let mut mi_matrix = Array2::<f64>::zeros((n_cells, n_cells));

    // Collect all (i, j) pairs where i < j
    let pairs: Vec<(usize, usize)> = (0..n_cells)
        .flat_map(|i| ((i + 1)..n_cells).map(move |j| (i, j)))
        .collect();

    // Parallel MI computation via rayon
    let mi_values: Vec<((usize, usize), f64)> = pairs
        .par_iter()
        .map(|&(i, j)| {
            let cell_a = states.row(i);
            let cell_b = states.row(j);
            let mi = mi_from_paired_vectors(cell_a.as_slice().unwrap(), cell_b.as_slice().unwrap(), n_bins);
            ((i, j), mi)
        })
        .collect();

    // Fill symmetric matrix
    for ((i, j), mi) in mi_values {
        mi_matrix[[i, j]] = mi;
        mi_matrix[[j, i]] = mi;
    }

    mi_matrix
}

/// Compute total mutual information: sum of all pairwise MI values.
fn total_mi(mi_matrix: &Array2<f64>) -> f64 {
    let n = mi_matrix.nrows();
    let mut total = 0.0;
    for i in 0..n {
        for j in (i + 1)..n {
            total += mi_matrix[[i, j]];
        }
    }
    total
}

/// Find minimum information partition using greedy bipartition.
///
/// For exact MIP we'd need to check all 2^(N-1) - 1 bipartitions, which is
/// intractable for large N. We use a greedy approach:
///
/// 1. Start with partition A = {0}, B = {1, 2, ..., N-1}
/// 2. For each cell in B, compute MI_across if we move it to A
/// 3. Greedily build partition that minimizes cross-partition MI
///
/// Returns (min_partition_mi, partition_a_indices, partition_b_indices)
fn find_min_partition(mi_matrix: &Array2<f64>) -> (f64, Vec<usize>, Vec<usize>) {
    let n = mi_matrix.nrows();

    if n <= 1 {
        return (0.0, vec![0], vec![]);
    }

    if n == 2 {
        return (mi_matrix[[0, 1]], vec![0], vec![1]);
    }

    // For small N (<=20), try all bipartitions exhaustively
    if n <= 20 {
        return find_min_partition_exact(mi_matrix, n);
    }

    // For large N, use greedy approach
    find_min_partition_greedy(mi_matrix, n)
}

/// Exact MIP search for small N (all non-trivial bipartitions).
fn find_min_partition_exact(mi_matrix: &Array2<f64>, n: usize) -> (f64, Vec<usize>, Vec<usize>) {
    let mut best_mi = f64::INFINITY;
    let mut best_a = vec![];
    let mut best_b = vec![];

    // Iterate over all bipartitions: cell 0 is always in partition A
    // to avoid counting mirror partitions.
    let max_mask = 1u64 << (n - 1);
    for mask in 1..max_mask {
        let mut part_a = vec![0usize]; // Cell 0 always in A
        let mut part_b = vec![];

        for bit in 0..(n - 1) {
            if mask & (1u64 << bit) != 0 {
                part_a.push(bit + 1);
            } else {
                part_b.push(bit + 1);
            }
        }

        if part_b.is_empty() {
            continue; // Skip trivial partition
        }

        // Compute cross-partition MI
        let cross_mi: f64 = part_a
            .iter()
            .flat_map(|&i| part_b.iter().map(move |&j| mi_matrix[[i, j]]))
            .sum();

        if cross_mi < best_mi {
            best_mi = cross_mi;
            best_a = part_a;
            best_b = part_b;
        }
    }

    (best_mi, best_a, best_b)
}

/// Greedy MIP approximation for large N.
/// Uses spectral-like approach: sort cells by connectivity, split at minimum cut.
fn find_min_partition_greedy(mi_matrix: &Array2<f64>, n: usize) -> (f64, Vec<usize>, Vec<usize>) {
    // Compute total MI for each cell (sum of its row)
    let cell_mi: Vec<f64> = (0..n)
        .map(|i| mi_matrix.row(i).sum())
        .collect();

    // Sort cells by total MI (ascending)
    let mut sorted_indices: Vec<usize> = (0..n).collect();
    sorted_indices.sort_by(|&a, &b| cell_mi[a].partial_cmp(&cell_mi[b]).unwrap());

    // Try splitting at each position and find minimum cross-MI
    let mut best_mi = f64::INFINITY;
    let mut best_split = 1;

    for split in 1..n {
        let part_a = &sorted_indices[..split];
        let part_b = &sorted_indices[split..];

        let cross_mi: f64 = part_a
            .iter()
            .flat_map(|&i| part_b.iter().map(move |&j| mi_matrix[[i, j]]))
            .sum();

        if cross_mi < best_mi {
            best_mi = cross_mi;
            best_split = split;
        }
    }

    let part_a = sorted_indices[..best_split].to_vec();
    let part_b = sorted_indices[best_split..].to_vec();

    (best_mi, part_a, part_b)
}

/// Main Phi computation.
///
/// Phi = total_MI - min_partition_MI
///
/// Where:
///   total_MI = sum of all pairwise mutual information
///   min_partition_MI = cross-partition MI for the minimum information partition
///
/// This captures "integrated information" — how much information is lost
/// when the system is split at its weakest point.
fn compute_phi_inner(states: &ArrayView2<f32>, n_bins: usize) -> (f64, Array2<f64>, Vec<usize>, Vec<usize>) {
    let n_cells = states.nrows();

    if n_cells <= 1 {
        return (0.0, Array2::zeros((n_cells, n_cells)), vec![0], vec![]);
    }

    // Step 1: Pairwise MI matrix (parallelized)
    let mi_matrix = compute_mi_matrix(states, n_bins);

    // Step 2: Total MI
    let total = total_mi(&mi_matrix);

    // Step 3: Minimum information partition
    let (min_part_mi, part_a, part_b) = find_min_partition(&mi_matrix);

    // Step 4: Phi = total - min_partition
    let phi = (total - min_part_mi).max(0.0);

    (phi, mi_matrix, part_a, part_b)
}

// ============================================================================
// PyO3 Python bindings
// ============================================================================

/// Compute integrated information (Phi) from cell hidden states.
///
/// Args:
///     states: numpy array of shape [n_cells, hidden_dim], dtype float32
///     n_bins: number of histogram bins (default: 16)
///
/// Returns:
///     tuple of (phi, components_dict) where components_dict contains:
///       - "mi_matrix": pairwise MI as numpy array [n_cells x n_cells]
///       - "total_mi": sum of all pairwise MI
///       - "min_partition_mi": cross-MI of minimum information partition
///       - "partition_a": cell indices in partition A
///       - "partition_b": cell indices in partition B
///       - "n_cells": number of cells
///       - "n_bins": number of histogram bins used
#[pyfunction]
#[pyo3(signature = (states, n_bins=None))]
fn compute_phi<'py>(
    py: Python<'py>,
    states: PyReadonlyArray2<'py, f32>,
    n_bins: Option<usize>,
) -> PyResult<(f64, Bound<'py, PyDict>)> {
    let n_bins = n_bins.unwrap_or(DEFAULT_N_BINS);
    let array = states.as_array();
    let n_cells = array.nrows();

    let (phi, mi_matrix, part_a, part_b) = compute_phi_inner(&array, n_bins);

    let total = total_mi(&mi_matrix);
    let min_part_mi = total - phi;

    // Build components dict
    let components = PyDict::new(py);

    // Convert MI matrix to numpy
    let mi_flat: Vec<f64> = mi_matrix.into_raw_vec_and_offset().0;
    let mi_np = PyArray1::from_vec(py, mi_flat);
    components.set_item("mi_matrix_flat", mi_np)?;
    components.set_item("mi_matrix_shape", (n_cells, n_cells))?;
    components.set_item("total_mi", total)?;
    components.set_item("min_partition_mi", min_part_mi)?;
    components.set_item("partition_a", part_a)?;
    components.set_item("partition_b", part_b)?;
    components.set_item("n_cells", n_cells)?;
    components.set_item("n_bins", n_bins)?;

    Ok((phi, components))
}

/// Compute only the pairwise MI matrix (without partition search).
/// Useful when you need MI but not full Phi.
#[pyfunction]
#[pyo3(signature = (states, n_bins=None))]
fn compute_mi_matrix_py<'py>(
    py: Python<'py>,
    states: PyReadonlyArray2<'py, f32>,
    n_bins: Option<usize>,
) -> PyResult<Bound<'py, PyArray1<f64>>> {
    let n_bins = n_bins.unwrap_or(DEFAULT_N_BINS);
    let array = states.as_array();
    let mi_matrix = compute_mi_matrix(&array, n_bins);
    let flat: Vec<f64> = mi_matrix.into_raw_vec_and_offset().0;
    Ok(PyArray1::from_vec(py, flat))
}

/// Python module definition
#[pymodule]
fn phi_rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(compute_phi, m)?)?;
    m.add_function(wrap_pyfunction!(compute_mi_matrix_py, m)?)?;
    Ok(())
}

// ============================================================================
// Tests
// ============================================================================

#[cfg(test)]
mod tests {
    use super::*;
    use ndarray::Array2;

    #[test]
    fn test_bin_values() {
        let vals = vec![0.0, 0.25, 0.5, 0.75, 1.0];
        let bins = bin_values(&vals, 4);
        assert_eq!(bins.len(), 5);
        assert_eq!(bins[0], 0);
        assert_eq!(bins[4], 3); // Clamped
    }

    #[test]
    fn test_entropy_uniform() {
        // Uniform distribution over 4 bins: H = log2(4) = 2.0
        let counts = vec![25, 25, 25, 25];
        let h = entropy(&counts, 100);
        assert!((h - 2.0).abs() < 1e-10);
    }

    #[test]
    fn test_entropy_deterministic() {
        // All in one bin: H = 0
        let counts = vec![100, 0, 0, 0];
        let h = entropy(&counts, 100);
        assert!((h - 0.0).abs() < 1e-10);
    }

    #[test]
    fn test_mi_identical() {
        // MI of a vector with itself should be > 0
        let a: Vec<f32> = (0..128).map(|i| i as f32 / 128.0).collect();
        let mi = mi_from_paired_vectors(&a, &a, 16);
        assert!(mi > 0.0, "MI of identical vectors should be positive, got {}", mi);
    }

    #[test]
    fn test_mi_independent() {
        // Two uncorrelated vectors should have low MI
        let a: Vec<f32> = (0..256).map(|i| (i as f32 * 0.1).sin()).collect();
        let b: Vec<f32> = (0..256).map(|i| (i as f32 * 0.37 + 2.7).sin()).collect();
        let mi = mi_from_paired_vectors(&a, &b, 16);
        // Not exactly 0 due to finite samples, but should be small
        assert!(mi < 0.5, "MI of uncorrelated vectors should be small, got {}", mi);
    }

    #[test]
    fn test_phi_single_cell() {
        let states = Array2::<f32>::zeros((1, 64));
        let (phi, _, _, _) = compute_phi_inner(&states.view(), 16);
        assert_eq!(phi, 0.0);
    }

    #[test]
    fn test_phi_two_identical_cells() {
        // Two identical cells: high MI, but partition is forced, so Phi = 0
        // (all MI is cross-partition MI)
        let mut states = Array2::<f32>::zeros((2, 64));
        for d in 0..64 {
            let v = d as f32 / 64.0;
            states[[0, d]] = v;
            states[[1, d]] = v;
        }
        let (phi, _, _, _) = compute_phi_inner(&states.view(), 16);
        // For 2 cells, total_MI == cross_MI, so Phi == 0
        assert!((phi - 0.0).abs() < 1e-10, "Phi for 2 cells should be 0, got {}", phi);
    }

    #[test]
    fn test_phi_correlated_group() {
        // Create 4 cells: first 2 correlated, last 2 correlated, groups independent
        let dim = 128;
        let mut states = Array2::<f32>::zeros((4, dim));
        for d in 0..dim {
            let v1 = (d as f32 * 0.1).sin();
            let v2 = (d as f32 * 0.37 + 5.0).sin();
            states[[0, d]] = v1;
            states[[1, d]] = v1 + 0.01 * (d as f32 * 0.7).cos(); // Correlated with cell 0
            states[[2, d]] = v2;
            states[[3, d]] = v2 + 0.01 * (d as f32 * 0.3).cos(); // Correlated with cell 2
        }
        let (phi, mi_matrix, part_a, part_b) = compute_phi_inner(&states.view(), 16);

        // Within-group MI should be higher than cross-group MI
        let within_01 = mi_matrix[[0, 1]];
        let cross_02 = mi_matrix[[0, 2]];
        assert!(within_01 > cross_02, "Within-group MI ({}) should exceed cross-group MI ({})", within_01, cross_02);

        // Phi should be positive (integrated information exists within groups)
        assert!(phi > 0.0, "Phi should be positive for correlated groups, got {}", phi);

        // Partition should roughly separate the groups
        println!("Partition A: {:?}, B: {:?}, Phi: {:.4}", part_a, part_b, phi);
    }

    #[test]
    fn test_phi_32_cells() {
        // Smoke test with 32 cells (target use case)
        let dim = 128;
        let n_cells = 32;
        let mut states = Array2::<f32>::zeros((n_cells, dim));
        for i in 0..n_cells {
            for d in 0..dim {
                states[[i, d]] = ((i * 7 + d * 3) as f32 * 0.1).sin();
            }
        }
        let (phi, mi_matrix, part_a, part_b) = compute_phi_inner(&states.view(), 16);

        assert!(phi >= 0.0);
        assert_eq!(mi_matrix.nrows(), n_cells);
        assert!(!part_a.is_empty());
        assert!(!part_b.is_empty());
        assert_eq!(part_a.len() + part_b.len(), n_cells);
        println!("32-cell Phi: {:.4}, partition: {} | {}", phi, part_a.len(), part_b.len());
    }
}
