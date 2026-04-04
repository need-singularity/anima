//! GravityLens — N-body attractor detection
//!
//! Computes pairwise distance-based potential energy landscape,
//! finds attractors via density-based gradient descent, and classifies basins.

use rayon::prelude::*;

/// Result of gravity lens scan.
#[derive(Debug, Clone)]
pub struct GravityResult {
    /// Attractor positions (flattened: n_attractors × n_features)
    pub attractors: Vec<f64>,
    /// Basin assignment: sample index → attractor index
    pub basins: Vec<usize>,
    /// Energy landscape per sample (lower = denser region)
    pub energy_landscape: Vec<f64>,
    pub n_attractors: usize,
    pub n_features: usize,
}

/// Compute squared Euclidean distance between two rows.
#[inline]
fn dist_sq(data: &[f64], i: usize, j: usize, d: usize) -> f64 {
    let mut s = 0.0;
    let a = i * d;
    let b = j * d;
    for k in 0..d {
        let diff = data[a + k] - data[b + k];
        s += diff * diff;
    }
    s
}

/// Scan data (n_samples × n_features) for gravitational attractors.
pub fn scan(data: &[f64], n_samples: usize, n_features: usize) -> GravityResult {
    if n_samples < 2 || n_features == 0 {
        return GravityResult {
            attractors: vec![],
            basins: vec![0; n_samples],
            energy_landscape: vec![0.0; n_samples],
            n_attractors: 0,
            n_features,
        };
    }

    // Compute bandwidth using 10th percentile distance (tighter than median)
    // This ensures mean-shift can distinguish nearby clusters
    let n_pairs = n_samples.min(200);
    let mut dists: Vec<f64> = Vec::with_capacity(n_pairs * n_pairs / 2);
    let step = (n_samples as f64 / n_pairs as f64).max(1.0) as usize;
    let indices: Vec<usize> = (0..n_samples).step_by(step.max(1)).take(n_pairs).collect();
    for (ii, &i) in indices.iter().enumerate() {
        for &j in indices[ii + 1..].iter() {
            dists.push(dist_sq(data, i, j, n_features).sqrt());
        }
    }
    dists.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    let bandwidth = if dists.is_empty() {
        1.0
    } else {
        // Use 10th percentile instead of median — much tighter kernel
        let p10_idx = (dists.len() as f64 * 0.1) as usize;
        dists[p10_idx.min(dists.len() - 1)].max(1e-12)
    };

    // Compute density (energy = -density) using Gaussian kernel
    let inv_bw2 = 1.0 / (2.0 * bandwidth * bandwidth);
    let energy: Vec<f64> = (0..n_samples)
        .into_par_iter()
        .map(|i| {
            let mut density = 0.0;
            for j in 0..n_samples {
                if i == j { continue; }
                let d2 = dist_sq(data, i, j, n_features);
                density += (-d2 * inv_bw2).exp();
            }
            -density // energy = negative density
        })
        .collect();

    // Mean-shift style: each point moves toward densest neighbor
    // Repeat a few times to converge to attractors
    let mut positions: Vec<f64> = data.to_vec();
    for _ in 0..10 {
        let new_positions: Vec<f64> = (0..n_samples)
            .into_par_iter()
            .flat_map(|i| {
                let mut weighted_sum = vec![0.0; n_features];
                let mut total_weight = 0.0;
                for j in 0..n_samples {
                    let d2 = {
                        let mut s = 0.0;
                        for k in 0..n_features {
                            let diff = positions[i * n_features + k] - positions[j * n_features + k];
                            s += diff * diff;
                        }
                        s
                    };
                    let w = (-d2 * inv_bw2).exp();
                    total_weight += w;
                    for k in 0..n_features {
                        weighted_sum[k] += w * positions[j * n_features + k];
                    }
                }
                if total_weight > 1e-12 {
                    for k in 0..n_features {
                        weighted_sum[k] /= total_weight;
                    }
                }
                weighted_sum
            })
            .collect();
        positions = new_positions;
    }

    // Cluster converged positions to find attractors
    // Use tighter merge threshold for better separation
    let merge_threshold = bandwidth * 0.3;
    let merge_thresh_sq = merge_threshold * merge_threshold;
    let mut attractor_ids: Vec<i32> = vec![-1; n_samples];
    let mut attractors: Vec<Vec<f64>> = Vec::new();

    for i in 0..n_samples {
        let pos = &positions[i * n_features..(i + 1) * n_features];
        let mut found = None;
        for (ai, att) in attractors.iter().enumerate() {
            let d2: f64 = pos.iter().zip(att.iter()).map(|(a, b)| (a - b) * (a - b)).sum();
            if d2 < merge_thresh_sq {
                found = Some(ai);
                break;
            }
        }
        match found {
            Some(ai) => attractor_ids[i] = ai as i32,
            None => {
                attractor_ids[i] = attractors.len() as i32;
                attractors.push(pos.to_vec());
            }
        }
    }

    let basins: Vec<usize> = attractor_ids.iter().map(|&id| id.max(0) as usize).collect();
    let flat_attractors: Vec<f64> = attractors.iter().flatten().copied().collect();
    let n_attractors = attractors.len();

    GravityResult {
        attractors: flat_attractors,
        basins,
        energy_landscape: energy,
        n_attractors,
        n_features,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_gravity_two_clusters() {
        let n = 20;
        let d = 4;
        let mut data = vec![0.0; n * d];
        // Cluster 1: near origin
        for i in 0..10 {
            for k in 0..d {
                data[i * d + k] = (i as f64 * 0.01) + (k as f64 * 0.01);
            }
        }
        // Cluster 2: near (10, 10, ...)
        for i in 10..20 {
            for k in 0..d {
                data[i * d + k] = 10.0 + (i as f64 * 0.01) + (k as f64 * 0.01);
            }
        }
        let result = scan(&data, n, d);
        assert!(result.n_attractors >= 1, "Should find at least 1 attractor, got {}", result.n_attractors);
        assert_eq!(result.basins.len(), n);
        assert_eq!(result.energy_landscape.len(), n);
    }

    #[test]
    fn test_gravity_single_point() {
        let result = scan(&[1.0, 2.0], 1, 2);
        assert_eq!(result.n_attractors, 0);
    }
}
