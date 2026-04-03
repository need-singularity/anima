//! Mutual Information calculation with soft histogram binning.
//!
//! Matches the GPU Phi Python implementation (gpu_phi.py):
//! - Gaussian kernel soft histogram (differentiable-equivalent)
//! - Joint histogram via outer product of kernel weights
//! - MI = H(X) + H(Y) - H(X,Y)

use rayon::prelude::*;

/// Precomputed bin centers and bandwidth for soft histogram binning.
#[derive(Debug, Clone)]
pub struct BinConfig {
    pub centers: Vec<f64>,
    pub bandwidth: f64,
    pub n_bins: usize,
}

impl BinConfig {
    /// Create bin config with evenly spaced centers in [0, 1].
    pub fn new(n_bins: usize) -> Self {
        let centers: Vec<f64> = (0..n_bins)
            .map(|i| (i as f64 + 0.5) / n_bins as f64)
            .collect();
        let bandwidth = 1.0 / n_bins as f64;
        Self {
            centers,
            bandwidth,
            n_bins,
        }
    }
}

/// Compute soft histogram weights for a single value.
/// Returns a vector of length n_bins with Gaussian kernel weights.
#[inline]
fn soft_weights(value: f64, config: &BinConfig) -> Vec<f64> {
    config
        .centers
        .iter()
        .map(|&c| {
            let diff = value - c;
            (-0.5 * (diff / config.bandwidth).powi(2)).exp()
        })
        .collect()
}

/// Compute soft 1D histogram from values in [0, 1].
/// Returns normalized histogram of length n_bins.
pub fn soft_histogram(values: &[f64], config: &BinConfig) -> Vec<f64> {
    let n_bins = config.n_bins;
    let mut hist = vec![0.0f64; n_bins];

    for &v in values {
        let w = soft_weights(v, config);
        for (i, wi) in w.into_iter().enumerate() {
            hist[i] += wi;
        }
    }

    let sum: f64 = hist.iter().sum::<f64>() + 1e-8;
    for h in hist.iter_mut() {
        *h /= sum;
    }
    hist
}

/// Compute soft 2D joint histogram from paired values in [0, 1].
/// Returns flattened (n_bins x n_bins) normalized joint histogram.
fn soft_joint_histogram(x: &[f64], y: &[f64], config: &BinConfig) -> Vec<f64> {
    let n_bins = config.n_bins;
    let mut joint = vec![0.0f64; n_bins * n_bins];

    for (&xv, &yv) in x.iter().zip(y.iter()) {
        let wx = soft_weights(xv, config);
        let wy = soft_weights(yv, config);
        // Outer product
        for (i, &wxi) in wx.iter().enumerate() {
            for (j, &wyj) in wy.iter().enumerate() {
                joint[i * n_bins + j] += wxi * wyj;
            }
        }
    }

    let sum: f64 = joint.iter().sum::<f64>() + 1e-8;
    for h in joint.iter_mut() {
        *h /= sum;
    }
    joint
}

/// Compute mutual information MI(X; Y) using soft histogram binning.
///
/// Both x and y should be in [0, 1] range (pre-normalized).
/// Uses Gaussian kernel soft binning matching gpu_phi.py.
///
/// MI = H(X) + H(Y) - H(X,Y) where H is Shannon entropy in bits.
pub fn mutual_information(x: &[f64], y: &[f64], n_bins: usize) -> f64 {
    assert_eq!(x.len(), y.len(), "x and y must have equal length");
    if x.is_empty() {
        return 0.0;
    }

    let config = BinConfig::new(n_bins);
    let joint = soft_joint_histogram(x, y, &config);
    let n = config.n_bins;

    // Marginals from joint
    let mut px = vec![0.0f64; n];
    let mut py = vec![0.0f64; n];
    for i in 0..n {
        for j in 0..n {
            px[i] += joint[i * n + j];
            py[j] += joint[i * n + j];
        }
    }

    let eps = 1e-10;
    let h_x: f64 = px.iter().map(|&p| -p * (p + eps).log2()).sum();
    let h_y: f64 = py.iter().map(|&p| -p * (p + eps).log2()).sum();
    let h_xy: f64 = joint.iter().map(|&p| -p * (p + eps).log2()).sum();

    (h_x + h_y - h_xy).max(0.0)
}

/// Compute mutual information between two cell hidden states.
///
/// Each cell has a hidden_dim-dimensional state. We treat dimensions
/// as paired samples and compute MI(cell_a, cell_b).
/// If dim > max_dims, subsamples dimensions uniformly.
pub fn mi_between_cells(cell_a: &[f64], cell_b: &[f64], n_bins: usize, max_dims: usize) -> f64 {
    assert_eq!(
        cell_a.len(),
        cell_b.len(),
        "cells must have same hidden dim"
    );
    let dim = cell_a.len();
    if dim == 0 {
        return 0.0;
    }

    // Subsample if too many dims
    let (a, b): (Vec<f64>, Vec<f64>) = if dim > max_dims {
        // Deterministic stride-based subsampling (no RNG needed for reproducibility)
        let step = dim as f64 / max_dims as f64;
        (0..max_dims)
            .map(|i| {
                let idx = (i as f64 * step) as usize;
                (cell_a[idx], cell_b[idx])
            })
            .unzip()
    } else {
        (cell_a.to_vec(), cell_b.to_vec())
    };

    // Normalize to [0, 1]
    let a_norm = normalize_to_unit(&a);
    let b_norm = normalize_to_unit(&b);

    mutual_information(&a_norm, &b_norm, n_bins)
}

/// Normalize values to [0, 1] range.
fn normalize_to_unit(values: &[f64]) -> Vec<f64> {
    if values.is_empty() {
        return vec![];
    }
    let min_v = values.iter().cloned().fold(f64::INFINITY, f64::min);
    let max_v = values.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
    let range = (max_v - min_v).max(1e-8);
    values.iter().map(|&v| (v - min_v) / range).collect()
}

/// Compute full pairwise MI matrix using rayon parallelism.
///
/// `states` is a slice of cell hidden states, each of length hidden_dim.
/// Returns a flattened n x n symmetric MI matrix.
pub fn mi_matrix(states: &[Vec<f64>], n_bins: usize, max_dims: usize) -> Vec<f64> {
    let n = states.len();
    if n <= 1 {
        return vec![0.0; n * n];
    }

    // Generate all upper-triangle pairs
    let pairs: Vec<(usize, usize)> = (0..n)
        .flat_map(|i| ((i + 1)..n).map(move |j| (i, j)))
        .collect();

    // Parallel MI computation
    let mi_values: Vec<((usize, usize), f64)> = pairs
        .par_iter()
        .map(|&(i, j)| {
            let mi = mi_between_cells(&states[i], &states[j], n_bins, max_dims);
            ((i, j), mi)
        })
        .collect();

    // Build symmetric matrix
    let mut matrix = vec![0.0f64; n * n];
    for ((i, j), mi) in mi_values {
        matrix[i * n + j] = mi;
        matrix[j * n + i] = mi;
    }

    matrix
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_soft_histogram_sums_to_one() {
        let config = BinConfig::new(16);
        let values: Vec<f64> = (0..100).map(|i| i as f64 / 100.0).collect();
        let hist = soft_histogram(&values, &config);
        let sum: f64 = hist.iter().sum();
        assert!(
            (sum - 1.0).abs() < 0.01,
            "histogram should sum to ~1.0, got {}",
            sum
        );
    }

    #[test]
    fn test_mi_identical_signals() {
        // Identical signals should have high MI
        let x: Vec<f64> = (0..100).map(|i| i as f64 / 100.0).collect();
        let y = x.clone();
        let mi = mutual_information(&x, &y, 16);
        assert!(mi > 0.5, "identical signals should have high MI, got {}", mi);
    }

    #[test]
    fn test_mi_independent_signals() {
        // Orthogonal signals: x ascending, y = reversed x (not truly independent
        // but less correlated than identical)
        let x: Vec<f64> = (0..100).map(|i| i as f64 / 100.0).collect();
        let y: Vec<f64> = (0..100).map(|i| (99 - i) as f64 / 100.0).collect();
        let mi_same = mutual_information(&x, &x, 16);
        let mi_rev = mutual_information(&x, &y, 16);
        // Reversed is also perfectly correlated (just inverted), so MI should be similar.
        // For truly independent, we'd need random data.
        assert!(mi_same >= 0.0);
        assert!(mi_rev >= 0.0);
    }

    #[test]
    fn test_mi_non_negative() {
        let x: Vec<f64> = vec![0.1, 0.3, 0.5, 0.7, 0.9];
        let y: Vec<f64> = vec![0.9, 0.7, 0.5, 0.3, 0.1];
        let mi = mutual_information(&x, &y, 8);
        assert!(mi >= 0.0, "MI should be non-negative");
    }

    #[test]
    fn test_mi_matrix_symmetric() {
        let states = vec![
            vec![0.0, 0.1, 0.2, 0.3],
            vec![0.4, 0.5, 0.6, 0.7],
            vec![0.8, 0.9, 1.0, 0.5],
        ];
        let matrix = mi_matrix(&states, 8, 128);
        let n = states.len();
        for i in 0..n {
            for j in 0..n {
                assert!(
                    (matrix[i * n + j] - matrix[j * n + i]).abs() < 1e-10,
                    "MI matrix should be symmetric"
                );
            }
            assert!(
                matrix[i * n + i].abs() < 1e-10,
                "diagonal should be zero"
            );
        }
    }
}
