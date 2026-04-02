//! Mutual Information — shared hot path for consciousness + causal lenses
//!
//! Replaces Python's double for-loop histogram with vectorized Rust.

/// Compute mutual information between two f64 slices via binned histogram.
/// Uses vectorized bin assignment + flat histogram for cache efficiency.
pub fn mutual_info(a: &[f64], b: &[f64], n_bins: usize) -> f64 {
    let n = a.len().min(b.len());
    if n < 2 || n_bins < 2 {
        return 0.0;
    }

    // Use first min(n, 32) dims for speed (matches Python behavior)
    let n = n.min(32);

    let (a_min, a_max) = min_max(&a[..n]);
    let (b_min, b_max) = min_max(&b[..n]);

    let a_range = a_max - a_min + 1e-12;
    let b_range = b_max - b_min + 1e-12;

    // Flat joint histogram
    let mut joint = vec![0u32; n_bins * n_bins];
    for i in 0..n {
        let ai = ((a[i] - a_min) / a_range * n_bins as f64) as usize;
        let bi = ((b[i] - b_min) / b_range * n_bins as f64) as usize;
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

    if n_rows < 2 {
        return (vec![], 0.0);
    }

    // Collect pairs (ring + random sample up to max_pairs)
    let mut pairs: Vec<(usize, usize)> = Vec::new();
    for i in 0..n_rows {
        pairs.push((i, (i + 1) % n_rows));
    }
    // Add random pairs
    use rand::Rng;
    let mut rng = rand::thread_rng();
    while pairs.len() < max_pairs && pairs.len() < n_rows * (n_rows - 1) / 2 {
        let i = rng.gen_range(0..n_rows);
        let j = rng.gen_range(0..n_rows);
        if i != j {
            let pair = (i.min(j), i.max(j));
            if !pairs.contains(&pair) {
                pairs.push(pair);
            }
        }
    }

    let mi_vals: Vec<f64> = pairs
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

#[inline]
fn min_max(s: &[f64]) -> (f64, f64) {
    let mut lo = f64::INFINITY;
    let mut hi = f64::NEG_INFINITY;
    for &v in s {
        if v < lo { lo = v; }
        if v > hi { hi = v; }
    }
    (lo, hi)
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
        // Independent signals: MI should be finite and non-negative
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
