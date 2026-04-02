//! common.rs — Shared hot-path utilities for all telescope lenses
//!
//! Optimized once, used by 22+ lenses. New lenses should use these
//! instead of reimplementing distance/entropy/normalization.
//!
//! Usage matrix (current):
//!   dist_sq / dist        — 11 lenses (topology, stability, boundary, gravity, ...)
//!   min_max               — 10 lenses
//!   shannon_entropy       — 4 lenses (thermo, multiscale, info, mirror)
//!   column_vectors        — 7 lenses (causal, network, wave, info, ...)
//!   mean_var              — 6 lenses (consciousness, stability, boundary, ...)
//!   normalize_zscore      — 3 lenses (consciousness, boundary, ...)
//!   knn_indices           — 4 lenses (boundary, em, quantum, evolution)

/// Squared Euclidean distance between row i and row j in row-major data.
#[inline(always)]
pub fn dist_sq(data: &[f64], i: usize, j: usize, n_features: usize) -> f64 {
    let ri = i * n_features;
    let rj = j * n_features;
    let mut sum = 0.0;
    // Process 4 elements at a time for better ILP
    let chunks = n_features / 4;
    let rem = n_features % 4;
    for c in 0..chunks {
        let base = c * 4;
        let d0 = data[ri + base] - data[rj + base];
        let d1 = data[ri + base + 1] - data[rj + base + 1];
        let d2 = data[ri + base + 2] - data[rj + base + 2];
        let d3 = data[ri + base + 3] - data[rj + base + 3];
        sum += d0 * d0 + d1 * d1 + d2 * d2 + d3 * d3;
    }
    let base = chunks * 4;
    for k in 0..rem {
        let d = data[ri + base + k] - data[rj + base + k];
        sum += d * d;
    }
    sum
}

/// Euclidean distance between row i and row j.
#[inline(always)]
pub fn dist(data: &[f64], i: usize, j: usize, n_features: usize) -> f64 {
    dist_sq(data, i, j, n_features).sqrt()
}

/// Min and max of a slice. Returns (min, max).
#[inline]
pub fn min_max(s: &[f64]) -> (f64, f64) {
    let mut lo = f64::INFINITY;
    let mut hi = f64::NEG_INFINITY;
    for &v in s {
        if v < lo { lo = v; }
        if v > hi { hi = v; }
    }
    (lo, hi)
}

/// Min and max of column j in row-major data (n_samples x n_features).
#[inline]
pub fn col_min_max(data: &[f64], n_samples: usize, n_features: usize, j: usize) -> (f64, f64) {
    let mut lo = f64::INFINITY;
    let mut hi = f64::NEG_INFINITY;
    for i in 0..n_samples {
        let v = data[i * n_features + j];
        if v < lo { lo = v; }
        if v > hi { hi = v; }
    }
    (lo, hi)
}

/// Extract column vectors from row-major data. Returns Vec of column Vecs.
pub fn column_vectors(data: &[f64], n_samples: usize, n_features: usize) -> Vec<Vec<f64>> {
    let nf = n_features;
    (0..nf)
        .map(|j| {
            let mut col = Vec::with_capacity(n_samples);
            for i in 0..n_samples {
                col.push(data[i * nf + j]);
            }
            col
        })
        .collect()
}

/// Compute mean and variance per feature. Returns (means, vars).
pub fn mean_var(data: &[f64], n_samples: usize, n_features: usize) -> (Vec<f64>, Vec<f64>) {
    let mut means = vec![0.0f64; n_features];
    for i in 0..n_samples {
        let row = i * n_features;
        for j in 0..n_features {
            means[j] += data[row + j];
        }
    }
    let inv_n = 1.0 / n_samples as f64;
    for j in 0..n_features {
        means[j] *= inv_n;
    }

    let mut vars = vec![0.0f64; n_features];
    for i in 0..n_samples {
        let row = i * n_features;
        for j in 0..n_features {
            let d = data[row + j] - means[j];
            vars[j] += d * d;
        }
    }
    for j in 0..n_features {
        vars[j] *= inv_n;
    }
    (means, vars)
}

/// Z-score normalize data in-place into output buffer.
/// Requires pre-computed means and stds (sqrt of vars).
pub fn normalize_zscore_into(
    data: &[f64],
    n_samples: usize,
    n_features: usize,
    means: &[f64],
    stds: &[f64],
    out: &mut [f64],
) {
    for i in 0..n_samples {
        let row = i * n_features;
        for j in 0..n_features {
            out[row + j] = (data[row + j] - means[j]) / stds[j];
        }
    }
}

/// Shannon entropy of a slice via histogram binning.
pub fn shannon_entropy(values: &[f64], n_bins: usize) -> f64 {
    if values.is_empty() || n_bins < 2 {
        return 0.0;
    }
    let (lo, hi) = min_max(values);
    let range = (hi - lo).max(1e-12);
    let scale = (n_bins - 1) as f64 / range;

    let mut counts = vec![0u32; n_bins];
    for &v in values {
        let bin = ((v - lo) * scale) as usize;
        counts[bin.min(n_bins - 1)] += 1;
    }

    let inv_n = 1.0 / values.len() as f64;
    let mut entropy = 0.0;
    for &c in &counts {
        if c > 0 {
            let p = c as f64 * inv_n;
            entropy -= p * p.ln();
        }
    }
    entropy
}

/// K-nearest neighbor indices for each point. Returns Vec of Vec<usize> (k indices per point).
/// Uses partial sort for efficiency when k << n.
pub fn knn_indices(data: &[f64], n_samples: usize, n_features: usize, k: usize) -> Vec<Vec<usize>> {
    let k = k.min(n_samples - 1);
    (0..n_samples)
        .map(|i| {
            let mut dists: Vec<(f64, usize)> = (0..n_samples)
                .filter(|&j| j != i)
                .map(|j| (dist_sq(data, i, j, n_features), j))
                .collect();
            let nth = k.min(dists.len() - 1);
            dists.select_nth_unstable_by(nth, |a, b| {
                a.0.partial_cmp(&b.0).unwrap()
            });
            dists[..k].iter().map(|&(_, j)| j).collect()
        })
        .collect()
}

/// Precomputed pairwise distance matrix (upper triangle, row-major flat).
/// Returns (flat_distances, n_samples). Access: flat[i * n + j] for i < j.
pub fn pairwise_dist_matrix(data: &[f64], n_samples: usize, n_features: usize) -> Vec<f64> {
    use rayon::prelude::*;

    let n = n_samples;
    let mut matrix = vec![0.0f64; n * n];

    if n > 64 {
        // Parallel for larger matrices
        let rows: Vec<(usize, Vec<f64>)> = (0..n)
            .into_par_iter()
            .map(|i| {
                let mut row = vec![0.0f64; n];
                for j in (i + 1)..n {
                    row[j] = dist(data, i, j, n_features);
                }
                (i, row)
            })
            .collect();
        for (i, row) in rows {
            for j in (i + 1)..n {
                matrix[i * n + j] = row[j];
                matrix[j * n + i] = row[j];
            }
        }
    } else {
        for i in 0..n {
            for j in (i + 1)..n {
                let d = dist(data, i, j, n_features);
                matrix[i * n + j] = d;
                matrix[j * n + i] = d;
            }
        }
    }
    matrix
}

/// Dot product of two slices.
#[inline(always)]
pub fn dot(a: &[f64], b: &[f64]) -> f64 {
    let n = a.len().min(b.len());
    let mut sum = 0.0;
    let chunks = n / 4;
    let rem = n % 4;
    for c in 0..chunks {
        let base = c * 4;
        sum += a[base] * b[base]
            + a[base + 1] * b[base + 1]
            + a[base + 2] * b[base + 2]
            + a[base + 3] * b[base + 3];
    }
    let base = chunks * 4;
    for k in 0..rem {
        sum += a[base + k] * b[base + k];
    }
    sum
}

/// Norm (L2) of a slice.
#[inline(always)]
pub fn norm(a: &[f64]) -> f64 {
    dot(a, a).sqrt()
}

/// Cosine similarity between two slices.
#[inline]
pub fn cosine_sim(a: &[f64], b: &[f64]) -> f64 {
    let d = dot(a, b);
    let na = norm(a);
    let nb = norm(b);
    if na < 1e-12 || nb < 1e-12 {
        return 0.0;
    }
    d / (na * nb)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_dist_sq() {
        let data = vec![1.0, 0.0, 0.0, 1.0]; // 2 points, 2 features
        assert!((dist_sq(&data, 0, 1, 2) - 2.0).abs() < 1e-12);
    }

    #[test]
    fn test_dist_sq_4way() {
        // Test 4-element unrolling path
        let data = vec![
            1.0, 2.0, 3.0, 4.0, 5.0,
            2.0, 3.0, 4.0, 5.0, 6.0,
        ];
        let d = dist_sq(&data, 0, 1, 5);
        assert!((d - 5.0).abs() < 1e-12); // each diff = 1, 5 features
    }

    #[test]
    fn test_min_max() {
        let v = vec![3.0, 1.0, 4.0, 1.0, 5.0];
        let (lo, hi) = min_max(&v);
        assert!((lo - 1.0).abs() < 1e-12);
        assert!((hi - 5.0).abs() < 1e-12);
    }

    #[test]
    fn test_mean_var() {
        let data = vec![1.0, 2.0, 3.0, 4.0]; // 2x2
        let (means, vars) = mean_var(&data, 2, 2);
        assert!((means[0] - 2.0).abs() < 1e-12);
        assert!((means[1] - 3.0).abs() < 1e-12);
        assert!((vars[0] - 1.0).abs() < 1e-12);
        assert!((vars[1] - 1.0).abs() < 1e-12);
    }

    #[test]
    fn test_shannon_entropy_uniform() {
        // 4 equal bins = ln(4)
        let v: Vec<f64> = (0..400).map(|i| (i % 4) as f64).collect();
        let e = shannon_entropy(&v, 4);
        assert!((e - 4.0_f64.ln()).abs() < 0.1);
    }

    #[test]
    fn test_dot_product() {
        let a = vec![1.0, 2.0, 3.0, 4.0, 5.0];
        let b = vec![5.0, 4.0, 3.0, 2.0, 1.0];
        assert!((dot(&a, &b) - 35.0).abs() < 1e-12);
    }

    #[test]
    fn test_cosine_sim_identical() {
        let a = vec![1.0, 2.0, 3.0];
        assert!((cosine_sim(&a, &a) - 1.0).abs() < 1e-12);
    }

    #[test]
    fn test_pairwise_dist_matrix() {
        let data = vec![0.0, 0.0, 1.0, 0.0, 0.0, 1.0]; // 3 points, 2d
        let m = pairwise_dist_matrix(&data, 3, 2);
        assert!((m[0 * 3 + 1] - 1.0).abs() < 1e-12);
        assert!((m[0 * 3 + 2] - 1.0).abs() < 1e-12);
        assert!((m[1 * 3 + 2] - 2.0_f64.sqrt()).abs() < 1e-12);
    }
}
