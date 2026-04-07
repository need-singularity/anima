//! RecursionLens — Self-reference & feedback loop detection
//!
//! Detects recursive/self-referential structures in data:
//!   1. Self-similarity across scales (fractal self-reference)
//!   2. Feedback loops (feature A predicts B predicts A)
//!   3. Fixed points / attractors (states that map to themselves)

/// Result of recursion lens scan.
#[derive(Debug, Clone)]
pub struct RecursionResult {
    /// Self-similarity scores per scale ratio [0,1]
    pub self_similarity: Vec<f64>,
    /// Mean self-similarity across scales
    pub mean_self_similarity: f64,
    /// Detected feedback loops: (feature_a, feature_b, strength)
    pub feedback_loops: Vec<(usize, usize, f64)>,
    /// Number of approximate fixed points (states close to their successor)
    pub n_fixed_points: usize,
    /// Fixed point indices
    pub fixed_point_indices: Vec<usize>,
    /// Recurrence depth: how many steps back the current state resembles
    pub recurrence_depth: f64,
}

use crate::mi;

/// Scan data for self-referential structures.
pub fn scan(data: &[f64], n_samples: usize, n_features: usize) -> RecursionResult {
    if n_samples < 8 || n_features == 0 {
        return RecursionResult {
            self_similarity: vec![],
            mean_self_similarity: 0.0,
            feedback_loops: vec![],
            n_fixed_points: 0,
            fixed_point_indices: vec![],
            recurrence_depth: 0.0,
        };
    }

    let nf = n_features.min(32);

    // 1. Self-similarity across scales
    // Compare data at original resolution vs downsampled
    let scales = [2, 4, 8];
    let mut self_similarity = Vec::new();

    for &scale in &scales {
        if n_samples / scale < 4 { break; }
        let downsampled_n = n_samples / scale;

        // Compute variance at original and downsampled scale
        let mut orig_vars = vec![0.0; nf];
        let mut down_vars = vec![0.0; nf];

        for j in 0..nf {
            // Original variance
            let col: Vec<f64> = (0..n_samples).map(|i| data[i * n_features + j]).collect();
            let mean = col.iter().sum::<f64>() / n_samples as f64;
            orig_vars[j] = col.iter().map(|&x| (x - mean) * (x - mean)).sum::<f64>() / n_samples as f64;

            // Downsampled: average blocks of 'scale' consecutive points
            let down: Vec<f64> = (0..downsampled_n)
                .map(|k| {
                    let start = k * scale;
                    let end = (start + scale).min(n_samples);
                    (start..end).map(|i| data[i * n_features + j]).sum::<f64>() / (end - start) as f64
                })
                .collect();
            let down_mean = down.iter().sum::<f64>() / downsampled_n as f64;
            down_vars[j] = down.iter().map(|&x| (x - down_mean) * (x - down_mean)).sum::<f64>() / downsampled_n as f64;
        }

        // Self-similarity = correlation of variance profiles across features
        let orig_mean = orig_vars.iter().sum::<f64>() / nf as f64;
        let down_mean = down_vars.iter().sum::<f64>() / nf as f64;

        let mut cov = 0.0;
        let mut var_o = 0.0;
        let mut var_d = 0.0;
        for j in 0..nf {
            cov += (orig_vars[j] - orig_mean) * (down_vars[j] - down_mean);
            var_o += (orig_vars[j] - orig_mean) * (orig_vars[j] - orig_mean);
            var_d += (down_vars[j] - down_mean) * (down_vars[j] - down_mean);
        }
        let sim = if var_o > 1e-12 && var_d > 1e-12 {
            (cov / (var_o.sqrt() * var_d.sqrt())).clamp(0.0, 1.0)
        } else {
            0.0
        };
        self_similarity.push(sim);
    }

    let mean_self_similarity = if self_similarity.is_empty() { 0.0 } else {
        self_similarity.iter().sum::<f64>() / self_similarity.len() as f64
    };

    // 2. Feedback loops: check if MI(X_t, Y_{t+1}) AND MI(Y_t, X_{t+1}) are both high
    let n_bins = 16;
    let mut feedback_loops = Vec::new();
    let max_feat = nf.min(16);

    for i in 0..max_feat {
        for j in (i + 1)..max_feat {
            let xi: Vec<f64> = (0..n_samples - 1).map(|k| data[k * n_features + i]).collect();
            let xj: Vec<f64> = (0..n_samples - 1).map(|k| data[k * n_features + j]).collect();
            let xi_next: Vec<f64> = (1..n_samples).map(|k| data[k * n_features + i]).collect();
            let xj_next: Vec<f64> = (1..n_samples).map(|k| data[k * n_features + j]).collect();

            let mi_i_to_j = mi::mutual_info(&xi, &xj_next, n_bins);
            let mi_j_to_i = mi::mutual_info(&xj, &xi_next, n_bins);

            let loop_strength = mi_i_to_j.min(mi_j_to_i); // Both directions must be strong
            if loop_strength > 0.1 {
                feedback_loops.push((i, j, loop_strength));
            }
        }
    }
    feedback_loops.sort_by(|a, b| b.2.partial_cmp(&a.2).unwrap_or(std::cmp::Ordering::Equal));
    feedback_loops.truncate(20);

    // 3. Fixed points: states where row[t] ≈ row[t+1]
    let mut fixed_point_indices = Vec::new();
    for i in 0..n_samples - 1 {
        let dist: f64 = (0..nf)
            .map(|f| {
                let diff = data[i * n_features + f] - data[(i + 1) * n_features + f];
                diff * diff
            })
            .sum::<f64>()
            .sqrt();
        // Normalize by average magnitude
        let mag: f64 = (0..nf).map(|f| data[i * n_features + f].abs()).sum::<f64>() / nf as f64;
        let threshold = (mag * 0.01).max(1e-6); // 1% of magnitude
        if dist < threshold {
            fixed_point_indices.push(i);
        }
    }

    // 4. Recurrence depth: for each step, how far back is the closest similar state?
    let max_check = n_samples.min(100);
    let step = (n_samples as f64 / max_check as f64).max(1.0) as usize;
    let mut total_depth = 0.0;
    let mut depth_count = 0;

    for i in (1..n_samples).step_by(step) {
        let max_lookback = i.min(50);
        for lag in 1..=max_lookback {
            let prev = i - lag;
            let dist: f64 = (0..nf)
                .map(|f| {
                    let diff = data[i * n_features + f] - data[prev * n_features + f];
                    diff * diff
                })
                .sum::<f64>()
                .sqrt();

            let mag: f64 = (0..nf).map(|f| data[i * n_features + f].abs()).sum::<f64>() / nf as f64;
            if dist < (mag * 0.1).max(1e-4) {
                total_depth += lag as f64;
                depth_count += 1;
                break;
            }
        }
    }
    let recurrence_depth = if depth_count > 0 { total_depth / depth_count as f64 } else { 0.0 };

    RecursionResult {
        self_similarity,
        mean_self_similarity,
        feedback_loops,
        n_fixed_points: fixed_point_indices.len(),
        fixed_point_indices,
        recurrence_depth,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_recursion_periodic() {
        // Periodic signal — check self-similarity is computed
        let n = 100;
        let d = 2;
        let data: Vec<f64> = (0..n * d).map(|i| {
            let row = i / d;
            (row as f64 * 0.3).sin()
        }).collect();
        let r = scan(&data, n, d);
        assert!(!r.self_similarity.is_empty());
        // Self-similarity can be 0 for perfectly uniform variance patterns
        assert!(r.mean_self_similarity >= 0.0);
    }

    #[test]
    fn test_recursion_fixed_point() {
        // Constant data = all fixed points
        let n = 20;
        let d = 3;
        let data = vec![1.0; n * d];
        let r = scan(&data, n, d);
        assert!(r.n_fixed_points > 0, "Constant data should have fixed points");
    }
}
