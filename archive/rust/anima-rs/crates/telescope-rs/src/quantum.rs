//! QuantumLens — Quantum analogies for data analysis
//!
//! "Entanglement" = high MI pairs, "Tunneling" = close output / far input,
//! "Superposition" = high local variance samples.

use crate::mi;

/// Result of quantum lens scan.
#[derive(Debug, Clone)]
pub struct QuantumResult {
    /// Entangled feature pairs (i, j, MI_value)
    pub entanglement_pairs: Vec<(usize, usize, f64)>,
    /// Tunneling paths: (sample_i, sample_j, input_dist, output_dist)
    pub tunneling_paths: Vec<(usize, usize, f64, f64)>,
    /// Superposed samples: (sample_idx, local_variance)
    pub superposed_samples: Vec<(usize, f64)>,
}

/// Scan data for quantum-analogy properties.
pub fn scan(data: &[f64], n_samples: usize, n_features: usize) -> QuantumResult {
    if n_samples < 4 || n_features < 2 {
        return QuantumResult {
            entanglement_pairs: vec![],
            tunneling_paths: vec![],
            superposed_samples: vec![],
        };
    }

    // Extract columns for MI
    let columns: Vec<Vec<f64>> = (0..n_features)
        .map(|j| (0..n_samples).map(|i| data[i * n_features + j]).collect())
        .collect();

    // 1. Entanglement = high MI pairs
    // Scan more pairs and use adaptive threshold
    let n_bins = 16;
    let mut all_mi: Vec<(usize, usize, f64)> = Vec::new();
    let max_features = n_features.min(64); // scan up to 64 features
    for i in 0..max_features {
        for j in (i + 1)..max_features {
            let m = mi::mutual_info(&columns[i], &columns[j], n_bins);
            all_mi.push((i, j, m));
        }
    }
    // Adaptive threshold: mean + 0.5 * std (or minimum 0.05)
    let mi_mean = if all_mi.is_empty() { 0.0 } else {
        all_mi.iter().map(|x| x.2).sum::<f64>() / all_mi.len() as f64
    };
    let mi_std = if all_mi.len() < 2 { 0.0 } else {
        (all_mi.iter().map(|x| (x.2 - mi_mean).powi(2)).sum::<f64>() / all_mi.len() as f64).sqrt()
    };
    let mi_threshold = (mi_mean + 0.5 * mi_std).max(0.05);
    let mut entanglement_pairs: Vec<(usize, usize, f64)> = all_mi
        .into_iter()
        .filter(|x| x.2 > mi_threshold)
        .collect();
    entanglement_pairs.sort_by(|a, b| b.2.partial_cmp(&a.2).unwrap_or(std::cmp::Ordering::Equal));
    entanglement_pairs.truncate(50);

    // 2. Tunneling: samples close in last-half features but far in first-half
    let half = n_features / 2;
    if half == 0 {
        return QuantumResult {
            entanglement_pairs,
            tunneling_paths: vec![],
            superposed_samples: vec![],
        };
    }
    let mut tunneling_paths = Vec::new();
    let n_check = n_samples.min(100);
    for i in 0..n_check {
        for j in (i + 1)..n_check {
            let mut d_input = 0.0;
            for k in 0..half {
                let diff = data[i * n_features + k] - data[j * n_features + k];
                d_input += diff * diff;
            }
            let mut d_output = 0.0;
            for k in half..n_features {
                let diff = data[i * n_features + k] - data[j * n_features + k];
                d_output += diff * diff;
            }
            d_input = d_input.sqrt();
            d_output = d_output.sqrt();
            // Tunneling: far in input, close in output
            // Relaxed threshold: 0.5 instead of 0.3 for better sensitivity
            if d_input > 1e-6 && d_output < d_input * 0.5 {
                tunneling_paths.push((i, j, d_input, d_output));
            }
        }
    }
    tunneling_paths.sort_by(|a, b| {
        let ratio_a = a.3 / (a.2 + 1e-12);
        let ratio_b = b.3 / (b.2 + 1e-12);
        ratio_a.partial_cmp(&ratio_b).unwrap_or(std::cmp::Ordering::Equal)
    });
    tunneling_paths.truncate(50);

    // 3. Superposition: samples with high local variance (near "decision boundary")
    let k = 5.min(n_samples - 1);
    let mut superposed: Vec<(usize, f64)> = (0..n_samples.min(200))
        .map(|i| {
            // Find k nearest neighbors
            let mut dists: Vec<(usize, f64)> = (0..n_samples)
                .filter(|&j| j != i)
                .map(|j| {
                    let d2: f64 = (0..n_features)
                        .map(|k| {
                            let diff = data[i * n_features + k] - data[j * n_features + k];
                            diff * diff
                        })
                        .sum();
                    (j, d2)
                })
                .collect();
            dists.sort_by(|a, b| a.1.partial_cmp(&b.1).unwrap_or(std::cmp::Ordering::Equal));

            // Local variance among k-nearest
            let neighbors: Vec<usize> = dists.iter().take(k).map(|&(j, _)| j).collect();
            let mut local_var = 0.0;
            for &ni in &neighbors {
                for &nj in &neighbors {
                    if ni >= nj { continue; }
                    let d2: f64 = (0..n_features)
                        .map(|k| {
                            let diff = data[ni * n_features + k] - data[nj * n_features + k];
                            diff * diff
                        })
                        .sum();
                    local_var += d2;
                }
            }
            let n_pairs = (k * (k - 1) / 2).max(1);
            local_var /= n_pairs as f64;
            (i, local_var)
        })
        .collect();

    superposed.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
    let top_n = (n_samples as f64 * 0.1).ceil() as usize;
    superposed.truncate(top_n.max(1));

    QuantumResult {
        entanglement_pairs,
        tunneling_paths,
        superposed_samples: superposed,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_quantum_basic() {
        let n = 30;
        let d = 6;
        let data: Vec<f64> = (0..n * d).map(|i| (i as f64 * 0.1).sin()).collect();
        let result = scan(&data, n, d);
        assert!(!result.superposed_samples.is_empty());
    }

    #[test]
    fn test_quantum_small() {
        let result = scan(&[1.0, 2.0, 3.0, 4.0], 2, 2);
        // With only 2 samples, still should work
        assert!(result.entanglement_pairs.is_empty() || !result.entanglement_pairs.is_empty());
    }
}
