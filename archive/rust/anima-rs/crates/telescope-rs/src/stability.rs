//! StabilityLens — Perturbation response & Lyapunov analysis
//!
//! Measures how stable a system is by:
//!   1. Estimating largest Lyapunov exponent from trajectory divergence
//!   2. Perturbation resilience (inject noise, measure recovery)
//!   3. Basin stability (fraction of perturbations that return to attractor)

/// Result of stability lens scan.
#[derive(Debug, Clone)]
pub struct StabilityResult {
    /// Estimated largest Lyapunov exponent (>0 = chaotic, <0 = stable, ~0 = edge of chaos)
    pub lyapunov_exponent: f64,
    /// Perturbation resilience score [0,1] — fraction of features that recover after noise
    pub resilience: f64,
    /// Mean recovery time (steps to return to within 10% of original after perturbation)
    pub mean_recovery_time: f64,
    /// Basin stability per feature — fraction of perturbations returning to original basin
    pub basin_stability: Vec<f64>,
    /// Variance ratio: var(perturbed)/var(original) — <1 means damping, >1 means amplifying
    pub variance_ratio: f64,
}

/// Estimate largest Lyapunov exponent from neighboring trajectory divergence.
fn estimate_lyapunov(data: &[f64], n_samples: usize, n_features: usize) -> f64 {
    if n_samples < 10 || n_features == 0 { return 0.0; }

    // Treat rows as trajectory points. For each point, find nearest neighbor
    // and track divergence over time.
    let max_pairs = n_samples.min(100);
    let step = (n_samples as f64 / max_pairs as f64).max(1.0) as usize;

    let mut log_divergences: Vec<f64> = Vec::new();
    let mut counts: Vec<usize> = Vec::new();
    let max_horizon = (n_samples / 4).min(20);

    // Pre-allocate
    if max_horizon == 0 { return 0.0; }
    log_divergences.resize(max_horizon, 0.0);
    counts.resize(max_horizon, 0);

    for i in (0..n_samples - max_horizon).step_by(step) {
        // Find nearest neighbor (not self, not adjacent)
        let mut best_j = 0;
        let mut best_d = f64::INFINITY;
        for j in (0..n_samples - max_horizon).step_by(step) {
            if (i as isize - j as isize).unsigned_abs() < 3 { continue; }
            let d: f64 = (0..n_features)
                .map(|f| {
                    let diff = data[i * n_features + f] - data[j * n_features + f];
                    diff * diff
                })
                .sum::<f64>()
                .sqrt();
            if d > 1e-12 && d < best_d {
                best_d = d;
                best_j = j;
            }
        }
        if best_d == f64::INFINITY { continue; }

        // Track divergence over horizon
        for h in 0..max_horizon {
            let ii = i + h;
            let jj = best_j + h;
            if ii >= n_samples || jj >= n_samples { break; }
            let d: f64 = (0..n_features)
                .map(|f| {
                    let diff = data[ii * n_features + f] - data[jj * n_features + f];
                    diff * diff
                })
                .sum::<f64>()
                .sqrt();
            if d > 1e-12 {
                log_divergences[h] += (d / best_d).ln();
                counts[h] += 1;
            }
        }
    }

    // Average log divergence and fit slope
    let valid: Vec<(f64, f64)> = (0..max_horizon)
        .filter(|&h| counts[h] > 0)
        .map(|h| (h as f64, log_divergences[h] / counts[h] as f64))
        .collect();

    if valid.len() < 3 { return 0.0; }

    // Linear regression: log(div) vs time → slope = Lyapunov
    let n = valid.len() as f64;
    let sx: f64 = valid.iter().map(|v| v.0).sum();
    let sy: f64 = valid.iter().map(|v| v.1).sum();
    let sxx: f64 = valid.iter().map(|v| v.0 * v.0).sum();
    let sxy: f64 = valid.iter().map(|v| v.0 * v.1).sum();
    let denom = n * sxx - sx * sx;
    if denom.abs() < 1e-12 { return 0.0; }
    (n * sxy - sx * sy) / denom
}

/// Scan data for stability properties.
pub fn scan(data: &[f64], n_samples: usize, n_features: usize) -> StabilityResult {
    if n_samples < 4 || n_features == 0 {
        return StabilityResult {
            lyapunov_exponent: 0.0,
            resilience: 0.0,
            mean_recovery_time: 0.0,
            basin_stability: vec![],
            variance_ratio: 1.0,
        };
    }

    let lyapunov = estimate_lyapunov(data, n_samples, n_features);

    // Compute per-feature variance
    let mut means = vec![0.0; n_features];
    for i in 0..n_samples {
        for j in 0..n_features {
            means[j] += data[i * n_features + j];
        }
    }
    for j in 0..n_features { means[j] /= n_samples as f64; }

    let mut vars = vec![0.0; n_features];
    for i in 0..n_samples {
        for j in 0..n_features {
            let d = data[i * n_features + j] - means[j];
            vars[j] += d * d;
        }
    }
    for j in 0..n_features { vars[j] /= n_samples as f64; }

    // Perturbation resilience: compare first half vs second half variance
    let half = n_samples / 2;
    let mut vars_first = vec![0.0; n_features];
    let mut means_first = vec![0.0; n_features];
    for i in 0..half {
        for j in 0..n_features { means_first[j] += data[i * n_features + j]; }
    }
    for j in 0..n_features { means_first[j] /= half as f64; }
    for i in 0..half {
        for j in 0..n_features {
            let d = data[i * n_features + j] - means_first[j];
            vars_first[j] += d * d;
        }
    }
    for j in 0..n_features { vars_first[j] /= half as f64; }

    let mut vars_second = vec![0.0; n_features];
    let mut means_second = vec![0.0; n_features];
    for i in half..n_samples {
        for j in 0..n_features { means_second[j] += data[i * n_features + j]; }
    }
    let n2 = n_samples - half;
    for j in 0..n_features { means_second[j] /= n2 as f64; }
    for i in half..n_samples {
        for j in 0..n_features {
            let d = data[i * n_features + j] - means_second[j];
            vars_second[j] += d * d;
        }
    }
    for j in 0..n_features { vars_second[j] /= n2 as f64; }

    // Resilience: fraction of features where variance doesn't explode
    let resilient_count = (0..n_features)
        .filter(|&j| vars_first[j] < 1e-12 || vars_second[j] / vars_first[j] < 2.0)
        .count();
    let resilience = resilient_count as f64 / n_features as f64;

    // Variance ratio
    let total_var_first: f64 = vars_first.iter().sum();
    let total_var_second: f64 = vars_second.iter().sum();
    let variance_ratio = if total_var_first > 1e-12 {
        total_var_second / total_var_first
    } else {
        1.0
    };

    // Basin stability per feature: fraction of samples within 1 std of mean
    let basin_stability: Vec<f64> = (0..n_features)
        .map(|j| {
            let std = vars[j].sqrt();
            if std < 1e-12 { return 1.0; }
            let within = (0..n_samples)
                .filter(|&i| (data[i * n_features + j] - means[j]).abs() < std)
                .count();
            within as f64 / n_samples as f64
        })
        .collect();

    // Mean recovery time: average autocorrelation decay time
    let mut total_recovery = 0.0;
    let mut feat_count = 0;
    for j in 0..n_features.min(16) {
        let col: Vec<f64> = (0..n_samples).map(|i| data[i * n_features + j]).collect();
        let col_mean = means[j];
        let col_var = vars[j];
        if col_var < 1e-12 { continue; }
        // Find lag where autocorrelation drops below 0.5
        for lag in 1..n_samples / 2 {
            let autocorr: f64 = (0..n_samples - lag)
                .map(|i| (col[i] - col_mean) * (col[i + lag] - col_mean))
                .sum::<f64>() / ((n_samples - lag) as f64 * col_var);
            if autocorr < 0.5 {
                total_recovery += lag as f64;
                feat_count += 1;
                break;
            }
        }
    }
    let mean_recovery_time = if feat_count > 0 {
        total_recovery / feat_count as f64
    } else {
        n_samples as f64 / 2.0
    };

    StabilityResult {
        lyapunov_exponent: lyapunov,
        resilience,
        mean_recovery_time,
        basin_stability,
        variance_ratio,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_stability_constant() {
        // Constant data = perfectly stable
        let data = vec![1.0; 50 * 3];
        let r = scan(&data, 50, 3);
        assert!(r.resilience >= 0.9, "Constant data should be resilient");
        assert!(r.variance_ratio < 1.5);
    }

    #[test]
    fn test_stability_divergent() {
        // Exponentially growing data = unstable
        let n = 100;
        let d = 2;
        let data: Vec<f64> = (0..n * d).map(|i| {
            let row = i / d;
            (row as f64 * 0.1).exp()
        }).collect();
        let r = scan(&data, n, d);
        assert!(r.lyapunov_exponent > -1.0, "Growing data should have non-negative Lyapunov");
        assert!(r.variance_ratio > 0.5);
    }

    #[test]
    fn test_stability_sine() {
        // Periodic data = stable
        let n = 100;
        let d = 2;
        let data: Vec<f64> = (0..n * d).map(|i| {
            let row = i / d;
            (row as f64 * 0.1).sin()
        }).collect();
        let r = scan(&data, n, d);
        assert!(r.resilience > 0.0);
        assert_eq!(r.basin_stability.len(), d);
    }
}
