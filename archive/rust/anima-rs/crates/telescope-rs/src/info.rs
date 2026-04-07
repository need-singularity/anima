//! InfoLens — Information theory analysis
//!
//! Shannon entropy, Lempel-Ziv complexity proxy, mutual information matrix,
//! redundant feature detection.

use crate::mi;

/// Result of information lens scan.
#[derive(Debug, Clone)]
pub struct InfoResult {
    /// Shannon entropy per feature (binned)
    pub entropy_per_feature: Vec<f64>,
    /// Lempel-Ziv complexity proxy per feature
    pub lz_complexity: Vec<f64>,
    /// Mutual information matrix (n_features × n_features, row-major)
    pub mi_matrix: Vec<f64>,
    /// Redundant feature pairs: (i, j, MI value)
    pub redundant_features: Vec<(usize, usize, f64)>,
}

/// Binned Shannon entropy.
fn shannon_entropy(values: &[f64], n_bins: usize) -> f64 {
    let n = values.len();
    if n < 2 || n_bins < 2 { return 0.0; }
    let (mut lo, mut hi) = (f64::INFINITY, f64::NEG_INFINITY);
    for &v in values {
        if v < lo { lo = v; }
        if v > hi { hi = v; }
    }
    let range = hi - lo + 1e-12;
    let mut counts = vec![0u32; n_bins];
    for &v in values {
        let bin = ((v - lo) / range * n_bins as f64) as usize;
        counts[bin.min(n_bins - 1)] += 1;
    }
    let n_f = n as f64;
    let mut h = 0.0;
    for &c in &counts {
        if c > 0 {
            let p = c as f64 / n_f;
            h -= p * p.ln();
        }
    }
    h
}

/// Lempel-Ziv complexity proxy: count distinct substrings on binned sequence.
/// Uses run-length encoding as a fast proxy.
fn lz_complexity_proxy(values: &[f64], n_bins: usize) -> f64 {
    let n = values.len();
    if n < 2 { return 0.0; }
    let (mut lo, mut hi) = (f64::INFINITY, f64::NEG_INFINITY);
    for &v in values {
        if v < lo { lo = v; }
        if v > hi { hi = v; }
    }
    let range = hi - lo + 1e-12;
    let bins: Vec<usize> = values.iter()
        .map(|&v| {
            let b = ((v - lo) / range * n_bins as f64) as usize;
            b.min(n_bins - 1)
        })
        .collect();

    // Count number of distinct consecutive patterns (run-length proxy)
    let mut complexity = 1.0;
    let mut i = 0;
    while i < bins.len() {
        let mut len = 1;
        // Try to find the longest previous match
        let mut found = false;
        if i > 0 {
            for start in 0..i {
                let mut match_len = 0;
                while i + match_len < bins.len() && start + match_len < i && bins[start + match_len] == bins[i + match_len] {
                    match_len += 1;
                }
                if match_len > len {
                    len = match_len;
                    found = true;
                }
            }
        }
        if !found {
            complexity += 1.0;
        }
        i += len;
    }
    // Normalize by theoretical maximum
    let max_c = n as f64 / (n as f64).ln().max(1.0);
    complexity / max_c.max(1.0)
}

/// Scan data for information-theoretic properties.
pub fn scan(data: &[f64], n_samples: usize, n_features: usize) -> InfoResult {
    let n_bins = 16;

    if n_samples < 2 || n_features == 0 {
        return InfoResult {
            entropy_per_feature: vec![],
            lz_complexity: vec![],
            mi_matrix: vec![],
            redundant_features: vec![],
        };
    }

    // Extract columns
    let columns: Vec<Vec<f64>> = (0..n_features)
        .map(|j| (0..n_samples).map(|i| data[i * n_features + j]).collect())
        .collect();

    let entropy_per_feature: Vec<f64> = columns.iter()
        .map(|col| shannon_entropy(col, n_bins))
        .collect();

    let lz_complexity: Vec<f64> = columns.iter()
        .map(|col| lz_complexity_proxy(col, n_bins))
        .collect();

    // MI matrix (using mi.rs)
    let d = n_features;
    let mut mi_matrix = vec![0.0; d * d];
    let mut redundant_features = Vec::new();

    let max_pairs = 500;
    let mut count = 0;
    for i in 0..d {
        mi_matrix[i * d + i] = entropy_per_feature[i]; // MI(X,X) = H(X)
        for j in (i + 1)..d {
            if count >= max_pairs { break; }
            let m = mi::mutual_info(&columns[i], &columns[j], n_bins);
            mi_matrix[i * d + j] = m;
            mi_matrix[j * d + i] = m;
            // Redundant if MI > 50% of min entropy
            let min_h = entropy_per_feature[i].min(entropy_per_feature[j]);
            if min_h > 0.0 && m > 0.5 * min_h {
                redundant_features.push((i, j, m));
            }
            count += 1;
        }
    }

    InfoResult {
        entropy_per_feature,
        lz_complexity,
        mi_matrix,
        redundant_features,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_info_basic() {
        let n = 50;
        let d = 4;
        let data: Vec<f64> = (0..n * d).map(|i| (i as f64 * 0.1).sin()).collect();
        let result = scan(&data, n, d);
        assert_eq!(result.entropy_per_feature.len(), d);
        assert_eq!(result.lz_complexity.len(), d);
        assert_eq!(result.mi_matrix.len(), d * d);
        for &h in &result.entropy_per_feature {
            assert!(h >= 0.0, "Entropy should be non-negative, got {h}");
        }
    }

    #[test]
    fn test_lz_constant() {
        let vals = vec![1.0; 50];
        let c = lz_complexity_proxy(&vals, 16);
        assert!(c < 0.5, "Constant signal should have low LZ, got {c}");
    }
}
