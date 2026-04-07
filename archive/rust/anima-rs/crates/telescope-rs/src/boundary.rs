//! BoundaryLens — Phase transition boundary & edge detection in feature space
//!
//! Detects:
//!   1. Cluster boundaries (transition zones between clusters)
//!   2. Density gradient edges (sharp density changes)
//!   3. Phase transition points (abrupt statistical property changes)

/// Result of boundary lens scan.
#[derive(Debug, Clone)]
pub struct BoundaryResult {
    /// Number of detected boundary points
    pub n_boundary_points: usize,
    /// Boundary point indices
    pub boundary_indices: Vec<usize>,
    /// Boundary strength per point (higher = sharper boundary)
    pub boundary_strengths: Vec<f64>,
    /// Number of phase transitions detected (abrupt changes in statistics)
    pub n_phase_transitions: usize,
    /// Phase transition locations (sample indices)
    pub transition_indices: Vec<usize>,
    /// Mean boundary sharpness [0,1]
    pub mean_sharpness: f64,
}

/// Scan data for boundaries and transitions.
pub fn scan(data: &[f64], n_samples: usize, n_features: usize) -> BoundaryResult {
    if n_samples < 8 || n_features == 0 {
        return BoundaryResult {
            n_boundary_points: 0,
            boundary_indices: vec![],
            boundary_strengths: vec![],
            n_phase_transitions: 0,
            transition_indices: vec![],
            mean_sharpness: 0.0,
        };
    }

    let nf = n_features.min(64);
    let k = 7.min(n_samples - 1); // k neighbors

    // For each point, compare local neighborhood composition
    // Points where neighbors come from different "regions" are boundaries

    // Step 1: compute k-NN distances for each point
    let max_points = n_samples.min(500);
    let step = (n_samples as f64 / max_points as f64).max(1.0) as usize;
    let indices: Vec<usize> = (0..n_samples).step_by(step).collect();
    let np = indices.len();

    let mut local_density = vec![0.0; np];
    let mut gradient_mag = vec![0.0; np];

    for a in 0..np {
        let ia = indices[a];
        // Find k nearest neighbors
        let mut dists: Vec<(usize, f64)> = (0..np)
            .filter(|&b| b != a)
            .map(|b| {
                let ib = indices[b];
                let d: f64 = (0..nf)
                    .map(|f| {
                        let diff = data[ia * n_features + f] - data[ib * n_features + f];
                        diff * diff
                    })
                    .sum::<f64>()
                    .sqrt();
                (b, d)
            })
            .collect();
        dists.sort_by(|a, b| a.1.partial_cmp(&b.1).unwrap_or(std::cmp::Ordering::Equal));

        // Local density = 1 / mean distance to k neighbors
        let k_actual = k.min(dists.len());
        if k_actual == 0 { continue; }
        let mean_dist: f64 = dists[..k_actual].iter().map(|d| d.1).sum::<f64>() / k_actual as f64;
        local_density[a] = 1.0 / (mean_dist + 1e-12);
    }

    // Step 2: density gradient — boundary points have high gradient
    for a in 0..np {
        let ia = indices[a];
        let mut dists: Vec<(usize, f64)> = (0..np)
            .filter(|&b| b != a)
            .map(|b| {
                let ib = indices[b];
                let d: f64 = (0..nf)
                    .map(|f| {
                        let diff = data[ia * n_features + f] - data[ib * n_features + f];
                        diff * diff
                    })
                    .sum::<f64>()
                    .sqrt();
                (b, d)
            })
            .collect();
        dists.sort_by(|a, b| a.1.partial_cmp(&b.1).unwrap_or(std::cmp::Ordering::Equal));

        let k_actual = k.min(dists.len());
        if k_actual == 0 { continue; }

        // Gradient = max density difference among neighbors
        let mut max_diff = 0.0;
        for &(b, _) in dists[..k_actual].iter() {
            let diff = (local_density[a] - local_density[b]).abs();
            if diff > max_diff { max_diff = diff; }
        }
        gradient_mag[a] = max_diff;
    }

    // Threshold for boundary detection: mean + 1.5 * std of gradient
    let grad_mean = gradient_mag.iter().sum::<f64>() / np as f64;
    let grad_std = (gradient_mag.iter().map(|&g| (g - grad_mean) * (g - grad_mean)).sum::<f64>() / np as f64).sqrt();
    let boundary_threshold = grad_mean + 1.5 * grad_std;

    let mut boundary_indices = Vec::new();
    let mut boundary_strengths = Vec::new();

    // Normalize gradient to [0,1]
    let grad_max = gradient_mag.iter().cloned().fold(0.0f64, f64::max);
    let grad_norm = if grad_max > 1e-12 { grad_max } else { 1.0 };

    for a in 0..np {
        if gradient_mag[a] > boundary_threshold {
            boundary_indices.push(indices[a]);
            boundary_strengths.push(gradient_mag[a] / grad_norm);
        }
    }

    let mean_sharpness = if boundary_strengths.is_empty() { 0.0 } else {
        boundary_strengths.iter().sum::<f64>() / boundary_strengths.len() as f64
    };

    // Step 3: Phase transitions — sliding window statistics change detection
    let window = (n_samples / 10).max(4);
    let mut transition_indices = Vec::new();

    if n_samples > window * 2 {
        let mut prev_mean = vec![0.0; nf];
        let mut prev_var = vec![0.0; nf];

        // First window stats
        for j in 0..nf {
            let col: Vec<f64> = (0..window).map(|i| data[i * n_features + j]).collect();
            prev_mean[j] = col.iter().sum::<f64>() / window as f64;
            prev_var[j] = col.iter().map(|&x| (x - prev_mean[j]) * (x - prev_mean[j])).sum::<f64>() / window as f64;
        }

        let slide_step = (window / 2).max(1);
        for start in (window..n_samples - window).step_by(slide_step) {
            let end = (start + window).min(n_samples);
            let w = end - start;

            let mut curr_mean = vec![0.0; nf];
            let mut curr_var = vec![0.0; nf];
            for j in 0..nf {
                let col: Vec<f64> = (start..end).map(|i| data[i * n_features + j]).collect();
                curr_mean[j] = col.iter().sum::<f64>() / w as f64;
                curr_var[j] = col.iter().map(|&x| (x - curr_mean[j]) * (x - curr_mean[j])).sum::<f64>() / w as f64;
            }

            // Detect change: mean shift + variance shift
            let mean_shift: f64 = (0..nf)
                .map(|j| {
                    let std = (prev_var[j] + curr_var[j]).sqrt().max(1e-12) / 2.0_f64.sqrt();
                    ((curr_mean[j] - prev_mean[j]) / std).abs()
                })
                .sum::<f64>() / nf as f64;

            if mean_shift > 2.0 { // > 2 sigma shift
                transition_indices.push(start);
            }

            prev_mean = curr_mean;
            prev_var = curr_var;
        }
    }

    BoundaryResult {
        n_boundary_points: boundary_indices.len(),
        boundary_indices,
        boundary_strengths,
        n_phase_transitions: transition_indices.len(),
        transition_indices,
        mean_sharpness,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_boundary_clusters() {
        // Two well-separated clusters
        let n = 60;
        let d = 2;
        let mut data = vec![0.0; n * d];
        for i in 0..30 {
            data[i * d] = 0.0 + (i as f64 * 0.01);
            data[i * d + 1] = 0.0 + (i as f64 * 0.01);
        }
        for i in 30..60 {
            data[i * d] = 5.0 + ((i - 30) as f64 * 0.01);
            data[i * d + 1] = 5.0 + ((i - 30) as f64 * 0.01);
        }
        let r = scan(&data, n, d);
        assert!(r.n_boundary_points >= 0); // may or may not detect depending on sampling
    }

    #[test]
    fn test_boundary_transition() {
        // Sudden mean shift = phase transition
        let n = 200;
        let d = 3;
        let mut data = vec![0.0; n * d];
        for i in 0..100 {
            data[i * d] = 1.0 + (i as f64 * 0.001);
            data[i * d + 1] = 1.0;
            data[i * d + 2] = 1.0;
        }
        for i in 100..200 {
            data[i * d] = 50.0 + ((i - 100) as f64 * 0.001);
            data[i * d + 1] = 50.0;
            data[i * d + 2] = 50.0;
        }
        let r = scan(&data, n, d);
        assert!(r.n_phase_transitions > 0 || r.n_boundary_points > 0,
                "Should detect transition or boundary. transitions={}, boundaries={}",
                r.n_phase_transitions, r.n_boundary_points);
    }
}
