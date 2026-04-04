//! MemoryLens — Autocorrelation depth & memory lifetime analysis
//!
//! Measures temporal memory in data:
//!   1. Autocorrelation function decay time
//!   2. Mutual information between past and future
//!   3. Recurrence quantification (recurrence rate, determinism)

/// Result of memory lens scan.
#[derive(Debug, Clone)]
pub struct MemoryResult {
    /// Autocorrelation decay time per feature (lag where ACF drops below 1/e)
    pub acf_decay_times: Vec<f64>,
    /// Mean memory depth across features
    pub mean_memory_depth: f64,
    /// Time-delayed mutual information (lag=1)
    pub delayed_mi: Vec<f64>,
    /// Recurrence rate: fraction of recurrence points in the recurrence matrix
    pub recurrence_rate: f64,
    /// Determinism: fraction of recurrence points forming diagonal lines
    pub determinism: f64,
    /// Longest diagonal line in recurrence plot (max predictability)
    pub max_diagonal_length: usize,
}

use crate::mi;

/// Scan data for temporal memory properties.
pub fn scan(data: &[f64], n_samples: usize, n_features: usize) -> MemoryResult {
    if n_samples < 8 || n_features == 0 {
        return MemoryResult {
            acf_decay_times: vec![],
            mean_memory_depth: 0.0,
            delayed_mi: vec![],
            recurrence_rate: 0.0,
            determinism: 0.0,
            max_diagonal_length: 0,
        };
    }

    let nf = n_features.min(32);

    // Autocorrelation decay times
    let max_lag = (n_samples / 3).min(50);
    let mut acf_decay_times = Vec::with_capacity(nf);

    for j in 0..nf {
        let col: Vec<f64> = (0..n_samples).map(|i| data[i * n_features + j]).collect();
        let mean = col.iter().sum::<f64>() / n_samples as f64;
        let var: f64 = col.iter().map(|&x| (x - mean) * (x - mean)).sum::<f64>() / n_samples as f64;

        if var < 1e-12 {
            acf_decay_times.push(0.0);
            continue;
        }

        let mut decay = max_lag as f64; // default: no decay
        let threshold = 1.0 / std::f64::consts::E; // 1/e

        for lag in 1..=max_lag {
            let acf: f64 = (0..n_samples - lag)
                .map(|i| (col[i] - mean) * (col[i + lag] - mean))
                .sum::<f64>() / ((n_samples - lag) as f64 * var);
            if acf < threshold {
                // Interpolate
                let prev_lag = lag - 1;
                let prev_acf = if prev_lag == 0 { 1.0 } else {
                    (0..n_samples - prev_lag)
                        .map(|i| (col[i] - mean) * (col[i + prev_lag] - mean))
                        .sum::<f64>() / ((n_samples - prev_lag) as f64 * var)
                };
                if (prev_acf - acf).abs() > 1e-12 {
                    decay = prev_lag as f64 + (prev_acf - threshold) / (prev_acf - acf);
                } else {
                    decay = lag as f64;
                }
                break;
            }
        }
        acf_decay_times.push(decay);
    }

    let mean_memory_depth = if acf_decay_times.is_empty() { 0.0 } else {
        acf_decay_times.iter().sum::<f64>() / acf_decay_times.len() as f64
    };

    // Time-delayed mutual information (lag=1)
    let delayed_mi: Vec<f64> = (0..nf)
        .map(|j| {
            let past: Vec<f64> = (0..n_samples - 1).map(|i| data[i * n_features + j]).collect();
            let future: Vec<f64> = (1..n_samples).map(|i| data[i * n_features + j]).collect();
            mi::mutual_info(&past, &future, 16)
        })
        .collect();

    // Recurrence analysis (sampled for performance)
    let max_points = n_samples.min(200);
    let step = (n_samples as f64 / max_points as f64).max(1.0) as usize;
    let indices: Vec<usize> = (0..n_samples).step_by(step).collect();
    let np = indices.len();

    // Compute distance threshold (10th percentile of pairwise distances)
    let mut dists: Vec<f64> = Vec::with_capacity(np * (np - 1) / 2);
    for a in 0..np {
        for b in (a + 1)..np {
            let d: f64 = (0..nf)
                .map(|f| {
                    let diff = data[indices[a] * n_features + f] - data[indices[b] * n_features + f];
                    diff * diff
                })
                .sum::<f64>()
                .sqrt();
            dists.push(d);
        }
    }
    dists.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));

    let eps = if dists.is_empty() { 1.0 } else {
        let p10 = (dists.len() as f64 * 0.1) as usize;
        dists[p10.min(dists.len() - 1)].max(1e-12)
    };

    // Build recurrence matrix and analyze
    let mut recurrence_count = 0;
    let mut diagonal_count = 0;
    let mut max_diag = 0;
    let total_pairs = np * (np - 1) / 2;

    // Check recurrence and diagonal lines
    let mut recurrence = vec![false; np * np];
    for a in 0..np {
        for b in (a + 1)..np {
            let d: f64 = (0..nf)
                .map(|f| {
                    let diff = data[indices[a] * n_features + f] - data[indices[b] * n_features + f];
                    diff * diff
                })
                .sum::<f64>()
                .sqrt();
            if d < eps {
                recurrence[a * np + b] = true;
                recurrence[b * np + a] = true;
                recurrence_count += 1;
            }
        }
    }

    // Diagonal lines (parallel to main diagonal)
    for offset in 1..np {
        let mut current_diag = 0;
        for k in 0..np - offset {
            let i = k;
            let j = k + offset;
            if recurrence[i * np + j] {
                current_diag += 1;
                diagonal_count += 1;
            } else {
                if current_diag > max_diag { max_diag = current_diag; }
                current_diag = 0;
            }
        }
        if current_diag > max_diag { max_diag = current_diag; }
    }

    let recurrence_rate = if total_pairs > 0 { recurrence_count as f64 / total_pairs as f64 } else { 0.0 };
    let determinism = if recurrence_count > 0 { diagonal_count as f64 / recurrence_count as f64 } else { 0.0 };

    MemoryResult {
        acf_decay_times,
        mean_memory_depth,
        delayed_mi,
        recurrence_rate,
        determinism,
        max_diagonal_length: max_diag,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_memory_periodic() {
        // Periodic signal = long memory
        let n = 100;
        let d = 2;
        let data: Vec<f64> = (0..n * d).map(|i| {
            let row = i / d;
            (row as f64 * 0.2).sin()
        }).collect();
        let r = scan(&data, n, d);
        assert!(!r.acf_decay_times.is_empty());
        assert!(r.mean_memory_depth > 1.0, "Periodic signal should have memory > 1");
        assert!(r.recurrence_rate > 0.0);
    }

    #[test]
    fn test_memory_random() {
        // Pseudo-random = short memory
        let n = 100;
        let d = 2;
        let data: Vec<f64> = (0..n * d).map(|i| ((i as f64 * 1.618033) % 1.0) * 2.0 - 1.0).collect();
        let r = scan(&data, n, d);
        assert_eq!(r.acf_decay_times.len(), d);
        assert_eq!(r.delayed_mi.len(), d);
    }
}
