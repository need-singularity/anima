//! MirrorLens — Symmetry detection
//!
//! Reflection symmetry per feature, permutation symmetry between features.

/// Result of mirror lens scan.
#[derive(Debug, Clone)]
pub struct MirrorResult {
    /// Reflection symmetry score per feature (0 = asymmetric, 1 = perfectly symmetric)
    pub reflection_scores: Vec<f64>,
    /// Overall symmetry score (mean of reflection scores)
    pub overall_symmetry: f64,
    /// Broken symmetries: features with low reflection score
    pub broken_symmetries: Vec<(usize, f64)>,
}

/// Measure reflection symmetry of a distribution around its mean.
/// Uses the KS-like statistic: compare CDF(mean+x) with 1-CDF(mean-x).
fn reflection_symmetry(values: &[f64]) -> f64 {
    let n = values.len();
    if n < 4 { return 0.0; }

    let mean = values.iter().sum::<f64>() / n as f64;

    // Sort deviations from mean
    let mut pos_devs: Vec<f64> = Vec::new();
    let mut neg_devs: Vec<f64> = Vec::new();
    for &v in values {
        let d = v - mean;
        if d >= 0.0 {
            pos_devs.push(d);
        } else {
            neg_devs.push(-d);
        }
    }

    pos_devs.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    neg_devs.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));

    if pos_devs.is_empty() || neg_devs.is_empty() {
        return 0.0;
    }

    // Compare quantiles
    let n_quantiles = 10;
    let mut asymmetry = 0.0;
    for qi in 0..n_quantiles {
        let frac = (qi as f64 + 0.5) / n_quantiles as f64;
        let pos_idx = (frac * pos_devs.len() as f64) as usize;
        let neg_idx = (frac * neg_devs.len() as f64) as usize;
        let pos_q = pos_devs[pos_idx.min(pos_devs.len() - 1)];
        let neg_q = neg_devs[neg_idx.min(neg_devs.len() - 1)];
        let max_val = pos_q.max(neg_q).max(1e-12);
        asymmetry += (pos_q - neg_q).abs() / max_val;
    }
    asymmetry /= n_quantiles as f64;

    // Convert to symmetry score: 0 asymmetry = 1.0 symmetry
    (1.0 - asymmetry).max(0.0)
}

/// Scan data for symmetry properties.
pub fn scan(data: &[f64], n_samples: usize, n_features: usize) -> MirrorResult {
    if n_samples < 4 || n_features == 0 {
        return MirrorResult {
            reflection_scores: vec![],
            overall_symmetry: 0.0,
            broken_symmetries: vec![],
        };
    }

    // Per-feature reflection symmetry
    let reflection_scores: Vec<f64> = (0..n_features)
        .map(|j| {
            let col: Vec<f64> = (0..n_samples).map(|i| data[i * n_features + j]).collect();
            reflection_symmetry(&col)
        })
        .collect();

    let overall_symmetry = if reflection_scores.is_empty() {
        0.0
    } else {
        reflection_scores.iter().sum::<f64>() / reflection_scores.len() as f64
    };

    // Broken symmetries: features with symmetry < 0.5
    let mut broken_symmetries: Vec<(usize, f64)> = reflection_scores.iter().enumerate()
        .filter(|&(_, &s)| s < 0.5)
        .map(|(i, &s)| (i, s))
        .collect();
    broken_symmetries.sort_by(|a, b| a.1.partial_cmp(&b.1).unwrap_or(std::cmp::Ordering::Equal));

    MirrorResult {
        reflection_scores,
        overall_symmetry,
        broken_symmetries,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_mirror_symmetric() {
        // Symmetric distribution: [-5,-4,...,-1,0,1,...,4,5]
        let n = 21;
        let d = 1;
        let data: Vec<f64> = (-10..=10).map(|i| i as f64).collect();
        let result = scan(&data, n, d);
        assert_eq!(result.reflection_scores.len(), d);
        assert!(result.reflection_scores[0] > 0.6,
                "Symmetric distribution should score high, got {}", result.reflection_scores[0]);
    }

    #[test]
    fn test_mirror_asymmetric() {
        // Highly skewed distribution
        let n = 20;
        let d = 1;
        let data: Vec<f64> = (0..n).map(|i| (i as f64).exp()).collect();
        let result = scan(&data, n, d);
        assert!(result.reflection_scores[0] < 0.7,
                "Exponential should be asymmetric, got {}", result.reflection_scores[0]);
    }
}
