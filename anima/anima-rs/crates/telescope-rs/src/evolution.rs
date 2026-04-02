//! EvolutionLens — Fitness landscape analysis
//!
//! Treats samples as genomes, computes fitness, finds peaks and niches.

use rayon::prelude::*;

/// Result of evolution lens scan.
#[derive(Debug, Clone)]
pub struct EvolutionResult {
    /// Fitness per sample (higher = closer to centroid)
    pub fitness_landscape: Vec<f64>,
    /// Indices of fitness peaks (local maxima in sample neighborhood)
    pub peaks: Vec<usize>,
    /// Niches: clusters of high-fitness samples (indices)
    pub niches: Vec<Vec<usize>>,
}

/// Scan data for fitness landscape properties.
pub fn scan(data: &[f64], n_samples: usize, n_features: usize) -> EvolutionResult {
    if n_samples < 2 || n_features == 0 {
        return EvolutionResult {
            fitness_landscape: vec![0.0; n_samples],
            peaks: vec![],
            niches: vec![],
        };
    }

    // Compute centroid
    let mut centroid = vec![0.0; n_features];
    for i in 0..n_samples {
        for j in 0..n_features {
            centroid[j] += data[i * n_features + j];
        }
    }
    let inv_n = 1.0 / n_samples as f64;
    for j in 0..n_features {
        centroid[j] *= inv_n;
    }

    // Fitness = -distance_to_centroid (normalized)
    let distances: Vec<f64> = (0..n_samples)
        .map(|i| {
            let mut d2 = 0.0;
            for j in 0..n_features {
                let diff = data[i * n_features + j] - centroid[j];
                d2 += diff * diff;
            }
            d2.sqrt()
        })
        .collect();

    let max_dist = distances.iter().cloned().fold(0.0f64, f64::max).max(1e-12);
    let fitness_landscape: Vec<f64> = distances.iter().map(|&d| 1.0 - d / max_dist).collect();

    // Find pairwise distances for neighbor graph (subsample for speed)
    let k_neighbors = 5.min(n_samples - 1);

    // For each sample, find if it's a local max (fitter than all k-nearest neighbors)
    let peaks: Vec<usize> = (0..n_samples)
        .into_par_iter()
        .filter(|&i| {
            // Compute distances to all other samples
            let mut neighbor_dists: Vec<(usize, f64)> = (0..n_samples)
                .filter(|&j| j != i)
                .map(|j| {
                    let mut d2 = 0.0;
                    for k in 0..n_features {
                        let diff = data[i * n_features + k] - data[j * n_features + k];
                        d2 += diff * diff;
                    }
                    (j, d2)
                })
                .collect();
            neighbor_dists.sort_by(|a, b| a.1.partial_cmp(&b.1).unwrap());
            // Is fitter than all k-nearest?
            neighbor_dists.iter().take(k_neighbors).all(|&(j, _)| fitness_landscape[i] >= fitness_landscape[j])
        })
        .collect();

    // Cluster peaks into niches using simple greedy grouping
    let niche_radius_sq = {
        // Use median inter-peak distance as threshold
        if peaks.len() < 2 {
            f64::INFINITY
        } else {
            let mut pdists = Vec::new();
            for (ii, &i) in peaks.iter().enumerate() {
                for &j in peaks[ii + 1..].iter() {
                    let mut d2 = 0.0;
                    for k in 0..n_features {
                        let diff = data[i * n_features + k] - data[j * n_features + k];
                        d2 += diff * diff;
                    }
                    pdists.push(d2);
                }
            }
            pdists.sort_by(|a, b| a.partial_cmp(b).unwrap());
            pdists.get(pdists.len() / 2).copied().unwrap_or(f64::INFINITY)
        }
    };

    let mut niches: Vec<Vec<usize>> = Vec::new();
    let mut assigned = vec![false; n_samples];

    for &peak in &peaks {
        if assigned[peak] { continue; }
        let mut niche = vec![peak];
        assigned[peak] = true;
        // Add nearby high-fitness samples
        for s in 0..n_samples {
            if assigned[s] { continue; }
            if fitness_landscape[s] < 0.5 { continue; } // only high-fitness
            let mut d2 = 0.0;
            for k in 0..n_features {
                let diff = data[peak * n_features + k] - data[s * n_features + k];
                d2 += diff * diff;
            }
            if d2 < niche_radius_sq {
                niche.push(s);
                assigned[s] = true;
            }
        }
        niches.push(niche);
    }

    EvolutionResult {
        fitness_landscape,
        peaks,
        niches,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_evolution_basic() {
        let n = 30;
        let d = 3;
        let mut data = vec![0.0; n * d];
        for i in 0..n {
            for k in 0..d {
                data[i * d + k] = (i as f64 * 0.3 + k as f64).sin();
            }
        }
        let result = scan(&data, n, d);
        assert_eq!(result.fitness_landscape.len(), n);
        assert!(!result.peaks.is_empty(), "Should find at least 1 peak");
        // Fitness values should be in [0, 1]
        for &f in &result.fitness_landscape {
            assert!(f >= 0.0 && f <= 1.0 + 1e-9, "Fitness out of range: {f}");
        }
    }
}
