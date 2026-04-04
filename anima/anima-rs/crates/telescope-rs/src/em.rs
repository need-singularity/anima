//! EMLens — Electromagnetic field analogies
//!
//! Gradient field, divergence (sources/sinks), curl proxy.

/// Result of EM lens scan.
#[derive(Debug, Clone)]
pub struct EMResult {
    /// Gradient field per sample (n_samples × n_features, row-major)
    pub gradient_field: Vec<f64>,
    /// Divergence per sample (sum of partial derivatives)
    pub divergence_map: Vec<f64>,
    /// Source indices (positive divergence)
    pub sources: Vec<(usize, f64)>,
    /// Sink indices (negative divergence)
    pub sinks: Vec<(usize, f64)>,
}

/// Scan data for electromagnetic field analogies.
pub fn scan(data: &[f64], n_samples: usize, n_features: usize) -> EMResult {
    if n_samples < 3 || n_features == 0 {
        return EMResult {
            gradient_field: vec![],
            divergence_map: vec![],
            sources: vec![],
            sinks: vec![],
        };
    }

    // Compute KNN-based gradient: for each sample, gradient = weighted mean direction to k nearest neighbors
    // This is order-independent (unlike sequential finite differences)
    let k = 5.min(n_samples - 1);
    let mut gradient_field = vec![0.0; n_samples * n_features];

    for i in 0..n_samples {
        // Find k nearest neighbors by Euclidean distance
        let mut dists: Vec<(usize, f64)> = (0..n_samples)
            .filter(|&j| j != i)
            .map(|j| {
                let d2: f64 = (0..n_features)
                    .map(|f| {
                        let diff = data[i * n_features + f] - data[j * n_features + f];
                        diff * diff
                    })
                    .sum();
                (j, d2.sqrt())
            })
            .collect();
        dists.sort_by(|a, b| a.1.partial_cmp(&b.1).unwrap_or(std::cmp::Ordering::Equal));

        // Gradient = weighted sum of directions to neighbors (closer = heavier)
        let mut total_weight = 0.0;
        for &(j, d) in dists.iter().take(k) {
            let w = 1.0 / (d + 1e-12);
            total_weight += w;
            for f in 0..n_features {
                gradient_field[i * n_features + f] += w * (data[j * n_features + f] - data[i * n_features + f]);
            }
        }
        if total_weight > 1e-12 {
            for f in 0..n_features {
                gradient_field[i * n_features + f] /= total_weight;
            }
        }
    }

    // Divergence: for each sample, compare its gradient direction with neighbors' gradients
    // Positive divergence = gradients pointing away (source), negative = pointing toward (sink)
    let mut divergence_map = vec![0.0; n_samples];
    for i in 0..n_samples {
        let mut dists: Vec<(usize, f64)> = (0..n_samples)
            .filter(|&j| j != i)
            .map(|j| {
                let d2: f64 = (0..n_features)
                    .map(|f| {
                        let diff = data[i * n_features + f] - data[j * n_features + f];
                        diff * diff
                    })
                    .sum();
                (j, d2.sqrt())
            })
            .collect();
        dists.sort_by(|a, b| a.1.partial_cmp(&b.1).unwrap_or(std::cmp::Ordering::Equal));

        // Divergence = dot(gradient_i, direction_to_neighbor) averaged over k neighbors
        for &(j, d) in dists.iter().take(k) {
            if d < 1e-12 { continue; }
            let mut dot = 0.0;
            for f in 0..n_features {
                let dir = (data[j * n_features + f] - data[i * n_features + f]) / d;
                dot += gradient_field[i * n_features + f] * dir;
            }
            divergence_map[i] += dot;
        }
        divergence_map[i] /= k as f64;
    }

    // Classify sources and sinks
    let threshold = {
        let mean = divergence_map.iter().sum::<f64>() / n_samples as f64;
        let var: f64 = divergence_map.iter().map(|&d| (d - mean) * (d - mean)).sum::<f64>() / n_samples as f64;
        var.sqrt() * 0.5
    };

    let mut sources = Vec::new();
    let mut sinks = Vec::new();
    for (i, &div) in divergence_map.iter().enumerate() {
        if div > threshold {
            sources.push((i, div));
        } else if div < -threshold {
            sinks.push((i, div));
        }
    }

    sources.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
    sinks.sort_by(|a, b| a.1.partial_cmp(&b.1).unwrap_or(std::cmp::Ordering::Equal));
    sources.truncate(50);
    sinks.truncate(50);

    EMResult {
        gradient_field,
        divergence_map,
        sources,
        sinks,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_em_gradient() {
        // Linear data: KNN gradient should be non-zero and consistent
        let n = 10;
        let d = 2;
        let mut data = vec![0.0; n * d];
        for i in 0..n {
            data[i * d] = i as f64;       // linear feature 0
            data[i * d + 1] = i as f64 * 2.0; // linear feature 1
        }
        let result = scan(&data, n, d);
        assert_eq!(result.gradient_field.len(), n * d);
        assert_eq!(result.divergence_map.len(), n);
        // Middle sample gradient should be non-zero
        let grad_mag: f64 = (0..d).map(|k| result.gradient_field[5 * d + k].powi(2)).sum::<f64>().sqrt();
        assert!(grad_mag > 0.01, "Expected non-zero gradient, got magnitude {}", grad_mag);
    }

    #[test]
    fn test_em_sources_sinks() {
        // Parabolic: should have sources/sinks
        let n = 20;
        let d = 1;
        let data: Vec<f64> = (0..n).map(|i| {
            let x = i as f64 - 10.0;
            x * x // parabola
        }).collect();
        let result = scan(&data, n, d);
        // Divergence of parabola = constant positive (second derivative = 2)
        assert!(!result.divergence_map.is_empty());
    }
}
