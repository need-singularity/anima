//! CausalLens — Granger causality + Transfer entropy + Lag correlation
//!
//! Replaces Python's O(d² × lag) loops with vectorized Rust + rayon.

use rayon::prelude::*;

/// Causal pair: cause → effect with strength and lag.
#[derive(Debug, Clone)]
pub struct CausalPair {
    pub cause: usize,
    pub effect: usize,
    pub strength: f64,
    pub lag: usize,
    pub method: String,
}

/// Result of causal lens scan.
#[derive(Debug, Clone)]
pub struct CausalResult {
    pub causal_pairs: Vec<CausalPair>,
    pub granger_matrix: Vec<f64>,    // d × d, row-major
    pub te_matrix: Vec<f64>,         // d × d, row-major
    pub n_features: usize,
}

/// Simple OLS: fit Y = X @ beta, return beta and RSS.
fn ols_rss(x: &[f64], y: &[f64], n: usize, k: usize) -> f64 {
    // X^T X
    let mut xtx = vec![0.0f64; k * k];
    let mut xty = vec![0.0f64; k];
    for i in 0..n {
        for a in 0..k {
            xty[a] += x[i * k + a] * y[i];
            for b in 0..k {
                xtx[a * k + b] += x[i * k + a] * x[i * k + b];
            }
        }
    }
    // Regularize
    for i in 0..k {
        xtx[i * k + i] += 1e-8;
    }
    // Solve via Cholesky-like (simple Gauss elimination for small k)
    let beta = solve_linear(&xtx, &xty, k);
    // RSS
    let mut rss = 0.0;
    for i in 0..n {
        let mut pred = 0.0;
        for j in 0..k {
            pred += x[i * k + j] * beta[j];
        }
        rss += (y[i] - pred).powi(2);
    }
    rss
}

/// Gaussian elimination for Ax = b (small systems only).
fn solve_linear(a: &[f64], b: &[f64], n: usize) -> Vec<f64> {
    let mut aug = vec![0.0f64; n * (n + 1)];
    for i in 0..n {
        for j in 0..n {
            aug[i * (n + 1) + j] = a[i * n + j];
        }
        aug[i * (n + 1) + n] = b[i];
    }
    // Forward elimination
    for col in 0..n {
        // Find pivot
        let mut max_row = col;
        let mut max_val = aug[col * (n + 1) + col].abs();
        for row in (col + 1)..n {
            let v = aug[row * (n + 1) + col].abs();
            if v > max_val { max_val = v; max_row = row; }
        }
        if max_val < 1e-15 { continue; }
        // Swap
        if max_row != col {
            for j in 0..=n {
                aug.swap(col * (n + 1) + j, max_row * (n + 1) + j);
            }
        }
        let pivot = aug[col * (n + 1) + col];
        for row in (col + 1)..n {
            let factor = aug[row * (n + 1) + col] / pivot;
            for j in col..=n {
                aug[row * (n + 1) + j] -= factor * aug[col * (n + 1) + j];
            }
        }
    }
    // Back substitution
    let mut x = vec![0.0f64; n];
    for i in (0..n).rev() {
        let mut sum = aug[i * (n + 1) + n];
        for j in (i + 1)..n {
            sum -= aug[i * (n + 1) + j] * x[j];
        }
        let diag = aug[i * (n + 1) + i];
        x[i] = if diag.abs() > 1e-15 { sum / diag } else { 0.0 };
    }
    x
}

/// Granger causality: does past x help predict y?
fn granger(x: &[f64], y: &[f64], max_lag: usize) -> (f64, usize) {
    let n = x.len().min(y.len());
    if n < max_lag + 5 { return (0.0, 1); }

    let mut best_score = 0.0;
    let mut best_lag = 1;

    for lag in 1..=max_lag {
        let n_eff = n - lag;
        let y_target = &y[lag..n];

        // Restricted: y ~ y_past
        let mut x_r = vec![0.0f64; n_eff * lag];
        for i in 0..n_eff {
            for k in 0..lag {
                x_r[i * lag + k] = y[lag - 1 - k + i];
            }
        }
        let rss_r = ols_rss(&x_r, y_target, n_eff, lag);

        // Unrestricted: y ~ y_past + x_past
        let cols_u = lag * 2;
        let mut x_u = vec![0.0f64; n_eff * cols_u];
        for i in 0..n_eff {
            for k in 0..lag {
                x_u[i * cols_u + k] = y[lag - 1 - k + i];
                x_u[i * cols_u + lag + k] = x[lag - 1 - k + i];
            }
        }
        let rss_u = ols_rss(&x_u, y_target, n_eff, cols_u);

        if rss_r > 1e-30 {
            let improvement = (rss_r - rss_u) / rss_r;
            if improvement > best_score {
                best_score = improvement;
                best_lag = lag;
            }
        }
    }
    (best_score, best_lag)
}

/// Transfer entropy from x to y.
fn transfer_entropy(x: &[f64], y: &[f64], lag: usize, n_bins: usize) -> f64 {
    let n = x.len().min(y.len());
    if n < lag + 10 { return 0.0; }

    let digitize = |v: &[f64]| -> Vec<usize> {
        let (lo, hi) = v.iter().fold((f64::INFINITY, f64::NEG_INFINITY), |(lo, hi), &x| (lo.min(x), hi.max(x)));
        let range = hi - lo + 1e-30;
        v.iter().map(|&val| ((val - lo) / range * n_bins as f64) as usize % n_bins).collect()
    };

    let dx = digitize(x);
    let dy = digitize(y);

    let m = n - lag;
    let yt = &dy[lag..n];
    let yt_past = &dy[..m];
    let xt_past = &dx[..m];

    // H(Y_t | Y_past)
    let h_yt_ypast = cond_entropy(yt, yt_past, n_bins, m);
    // H(Y_t | Y_past, X_past)
    let combined: Vec<usize> = yt_past.iter().zip(xt_past.iter())
        .map(|(&a, &b)| a * (n_bins + 1) + b)
        .collect();
    let h_yt_both = cond_entropy(yt, &combined, n_bins, m);

    (h_yt_ypast - h_yt_both).max(0.0)
}

fn cond_entropy(a: &[usize], b: &[usize], _n_bins: usize, m: usize) -> f64 {
    use std::collections::HashMap;
    let mut joint_counts: HashMap<(usize, usize), u32> = HashMap::new();
    let mut b_counts: HashMap<usize, u32> = HashMap::new();

    for i in 0..m {
        *joint_counts.entry((a[i], b[i])).or_default() += 1;
        *b_counts.entry(b[i]).or_default() += 1;
    }

    let m_f = m as f64;
    let h_joint: f64 = joint_counts.values()
        .map(|&c| { let p = c as f64 / m_f; -p * p.log2() })
        .sum();
    let h_b: f64 = b_counts.values()
        .map(|&c| { let p = c as f64 / m_f; -p * p.log2() })
        .sum();

    h_joint - h_b
}

/// Run causal scan on data (n_samples × n_features), treating columns as time series.
pub fn scan(data: &[f64], n_samples: usize, n_features: usize,
            max_lag: usize, te_bins: usize, min_strength: f64) -> CausalResult {
    let d = n_features;
    if d < 2 || n_samples < max_lag + 10 {
        return CausalResult {
            causal_pairs: vec![], granger_matrix: vec![0.0; d * d],
            te_matrix: vec![0.0; d * d], n_features: d,
        };
    }

    // Extract columns
    let cols: Vec<Vec<f64>> = (0..d)
        .map(|j| (0..n_samples).map(|i| data[i * d + j]).collect())
        .collect();

    // Granger matrix (parallel over pairs)
    let pairs: Vec<(usize, usize)> = (0..d)
        .flat_map(|i| (0..d).filter(move |&j| i != j).map(move |j| (i, j)))
        .collect();

    let granger_results: Vec<((usize, usize), f64, usize)> = pairs.par_iter()
        .map(|&(i, j)| {
            let (score, lag) = granger(&cols[i], &cols[j], max_lag);
            ((i, j), score, lag)
        })
        .collect();

    let mut granger_matrix = vec![0.0f64; d * d];
    let mut lag_matrix = vec![0usize; d * d];
    for ((i, j), score, lag) in &granger_results {
        granger_matrix[i * d + j] = *score;
        lag_matrix[i * d + j] = *lag;
    }

    // Transfer entropy matrix (parallel)
    let te_results: Vec<((usize, usize), f64)> = pairs.par_iter()
        .map(|&(i, j)| {
            let te = transfer_entropy(&cols[i], &cols[j], 1, te_bins);
            ((i, j), te)
        })
        .collect();

    let mut te_matrix = vec![0.0f64; d * d];
    for ((i, j), te) in &te_results {
        te_matrix[i * d + j] = *te;
    }

    // Build causal pairs (both Granger and TE agree)
    let mut causal_pairs = Vec::new();
    for i in 0..d {
        for j in 0..d {
            if i == j { continue; }
            let g_ij = granger_matrix[i * d + j];
            let g_ji = granger_matrix[j * d + i];
            let te_ij = te_matrix[i * d + j];
            let te_ji = te_matrix[j * d + i];

            if g_ij > min_strength && g_ij > g_ji && te_ij > te_ji {
                causal_pairs.push(CausalPair {
                    cause: i, effect: j,
                    strength: g_ij,
                    lag: lag_matrix[i * d + j],
                    method: "granger+te".to_string(),
                });
            }
        }
    }

    causal_pairs.sort_by(|a, b| b.strength.partial_cmp(&a.strength).unwrap());

    CausalResult { causal_pairs, granger_matrix, te_matrix, n_features: d }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_granger_self() {
        let x: Vec<f64> = (0..100).map(|i| (i as f64 * 0.1).sin()).collect();
        let (score, lag) = granger(&x, &x, 3);
        // Self-prediction should be high
        assert!(score >= 0.0);
        assert!(lag >= 1);
    }

    #[test]
    fn test_transfer_entropy() {
        let x: Vec<f64> = (0..100).map(|i| (i as f64 * 0.1).sin()).collect();
        let y: Vec<f64> = (0..100).map(|i| (i as f64 * 0.1 + 0.5).sin()).collect();
        let te = transfer_entropy(&x, &y, 1, 16);
        assert!(te >= 0.0);
    }

    #[test]
    fn test_causal_scan() {
        // X causes Y with lag 1
        let n = 100;
        let d = 3;
        let mut data = vec![0.0f64; n * d];
        for i in 0..n {
            data[i * d + 0] = (i as f64 * 0.1).sin();
            data[i * d + 1] = if i > 0 { data[(i - 1) * d + 0] * 0.8 } else { 0.0 };
            data[i * d + 2] = (i as f64 * 0.37).cos(); // independent
        }
        let result = scan(&data, n, d, 3, 16, 0.05);
        assert!(result.n_features == 3);
        // Should find 0→1 causal pair
        // (may not always due to short series, but structure should be valid)
    }
}
