//! Mutual Information — shared hot path for consciousness + causal lenses
//!
//! Replaces Python's double for-loop histogram with vectorized Rust.
//!
//! Optimizations:
//!   - HashSet for pair dedup in pairwise_mi (was O(n) linear search)
//!   - Uses common::min_max

use crate::common;

/// Compute mutual information between two f64 slices via binned histogram.
/// Uses vectorized bin assignment + flat histogram for cache efficiency.
pub fn mutual_info(a: &[f64], b: &[f64], n_bins: usize) -> f64 {
    let n = a.len().min(b.len());
    if n < 2 || n_bins < 2 {
        return 0.0;
    }

    // Use first min(n, 32) dims for speed (matches Python behavior)
    let n = n.min(32);

    let (a_min, a_max) = common::min_max(&a[..n]);
    let (b_min, b_max) = common::min_max(&b[..n]);

    let a_range = a_max - a_min + 1e-12;
    let b_range = b_max - b_min + 1e-12;
    let a_scale = n_bins as f64 / a_range;
    let b_scale = n_bins as f64 / b_range;

    // Flat joint histogram
    let mut joint = vec![0u32; n_bins * n_bins];
    for i in 0..n {
        let ai = ((a[i] - a_min) * a_scale) as usize;
        let bi = ((b[i] - b_min) * b_scale) as usize;
        let ai = ai.min(n_bins - 1);
        let bi = bi.min(n_bins - 1);
        joint[ai * n_bins + bi] += 1;
    }

    // Marginals
    let mut pa = vec![0u32; n_bins];
    let mut pb = vec![0u32; n_bins];
    for ai in 0..n_bins {
        for bi in 0..n_bins {
            let c = joint[ai * n_bins + bi];
            pa[ai] += c;
            pb[bi] += c;
        }
    }

    // MI = sum p(a,b) * log(p(a,b) / (p(a)*p(b)))
    let n_f = n as f64;
    let mut mi = 0.0;
    for ai in 0..n_bins {
        if pa[ai] == 0 {
            continue;
        }
        let p_a = pa[ai] as f64 / n_f;
        for bi in 0..n_bins {
            let c = joint[ai * n_bins + bi];
            if c == 0 || pb[bi] == 0 {
                continue;
            }
            let p_ab = c as f64 / n_f;
            let p_b = pb[bi] as f64 / n_f;
            mi += p_ab * (p_ab / (p_a * p_b)).ln();
        }
    }
    mi.max(0.0)
}

/// Compute pairwise MI matrix for an (n_cells, hidden_dim) matrix.
/// Returns flat row-major upper triangle MI values + average MI (= Phi proxy).
pub fn pairwise_mi(data: &[f64], n_rows: usize, n_cols: usize, n_bins: usize, max_pairs: usize) -> (Vec<f64>, f64) {
    use rayon::prelude::*;
    use std::collections::HashSet;

    if n_rows < 2 {
        return (vec![], 0.0);
    }

    // Collect pairs: ring + random sample up to max_pairs
    let mut pairs: HashSet<(usize, usize)> = HashSet::with_capacity(max_pairs);
    for i in 0..n_rows {
        pairs.insert((i, (i + 1) % n_rows));
    }

    // Add random pairs using HashSet for O(1) dedup
    use rand::Rng;
    let mut rng = rand::thread_rng();
    let max_possible = n_rows * (n_rows - 1) / 2;
    let target = max_pairs.min(max_possible);
    let mut attempts = 0;
    while pairs.len() < target && attempts < target * 3 {
        let i = rng.gen_range(0..n_rows);
        let j = rng.gen_range(0..n_rows);
        if i != j {
            pairs.insert((i.min(j), i.max(j)));
        }
        attempts += 1;
    }

    let pairs_vec: Vec<(usize, usize)> = pairs.into_iter().collect();

    let mi_vals: Vec<f64> = pairs_vec
        .par_iter()
        .map(|&(i, j)| {
            let row_i = &data[i * n_cols..(i + 1) * n_cols];
            let row_j = &data[j * n_cols..(j + 1) * n_cols];
            mutual_info(row_i, row_j, n_bins)
        })
        .collect();

    let avg = if mi_vals.is_empty() {
        0.0
    } else {
        mi_vals.iter().sum::<f64>() / mi_vals.len() as f64
    };

    (mi_vals, avg)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_mi_identical() {
        let a = vec![0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9];
        let mi = mutual_info(&a, &a, 16);
        assert!(mi > 0.0, "MI of identical vectors should be > 0, got {mi}");
    }

    #[test]
    fn test_mi_independent() {
        let a: Vec<f64> = (0..100).map(|i| (i as f64 * 0.1).sin()).collect();
        let b: Vec<f64> = (0..100).map(|i| (i as f64 * 0.37 + 2.0).cos()).collect();
        let mi = mutual_info(&a, &b, 16);
        assert!(mi >= 0.0 && mi.is_finite(), "MI should be finite, got {mi}");
    }

    #[test]
    fn test_pairwise_mi() {
        let n = 8;
        let dim = 16;
        let data: Vec<f64> = (0..n * dim).map(|i| (i as f64 * 0.1).sin()).collect();
        let (vals, avg) = pairwise_mi(&data, n, dim, 16, 20);
        assert!(!vals.is_empty());
        assert!(avg >= 0.0);
    }
}
