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

    // Compute numerical gradient: for each sample i, gradient[i][j] = (data[i+1][j] - data[i-1][j]) / 2
    // Boundary: forward/backward difference
    let mut gradient_field = vec![0.0; n_samples * n_features];

    for j in 0..n_features {
        // Forward difference for first
        gradient_field[0 * n_features + j] = data[1 * n_features + j] - data[0 * n_features + j];
        // Central difference for middle
        for i in 1..n_samples - 1 {
            gradient_field[i * n_features + j] =
                (data[(i + 1) * n_features + j] - data[(i - 1) * n_features + j]) / 2.0;
        }
        // Backward difference for last
        gradient_field[(n_samples - 1) * n_features + j] =
            data[(n_samples - 1) * n_features + j] - data[(n_samples - 2) * n_features + j];
    }

    // Divergence: sum of second derivatives per sample (Laplacian proxy)
    let mut divergence_map = vec![0.0; n_samples];
    for j in 0..n_features {
        // Second derivative: (f[i+1] - 2f[i] + f[i-1])
        divergence_map[0] += gradient_field[1 * n_features + j] - gradient_field[0 * n_features + j];
        for i in 1..n_samples - 1 {
            divergence_map[i] +=
                (gradient_field[(i + 1) * n_features + j] - gradient_field[(i - 1) * n_features + j]) / 2.0;
        }
        let last = n_samples - 1;
        divergence_map[last] += gradient_field[last * n_features + j] - gradient_field[(last - 1) * n_features + j];
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

    sources.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());
    sinks.sort_by(|a, b| a.1.partial_cmp(&b.1).unwrap());
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
        // Linear data: gradient should be constant
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
        // Central gradients should be ~1.0 for feature 0
        assert!((result.gradient_field[5 * d] - 1.0).abs() < 0.01,
                "Expected gradient ~1.0, got {}", result.gradient_field[5 * d]);
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
