//! CompassLens — Curvature detection
//!
//! Menger curvature for sample triples, circle fitting for subsets.

/// Result of compass lens scan.
#[derive(Debug, Clone)]
pub struct CompassResult {
    /// Mean Menger curvature across sampled triples
    pub mean_curvature: f64,
    /// High curvature regions: (sample_idx, local_curvature)
    pub high_curvature_regions: Vec<(usize, f64)>,
    /// Circular structures: (center_sample, radius, n_points)
    pub circular_structures: Vec<(usize, f64, usize)>,
}

/// Menger curvature of three points: 4 * area(triangle) / (|AB| * |BC| * |CA|)
fn menger_curvature(a: &[f64], b: &[f64], c: &[f64]) -> f64 {
    let d = a.len();
    // Distances
    let mut ab2 = 0.0;
    let mut bc2 = 0.0;
    let mut ca2 = 0.0;
    for k in 0..d {
        ab2 += (a[k] - b[k]) * (a[k] - b[k]);
        bc2 += (b[k] - c[k]) * (b[k] - c[k]);
        ca2 += (c[k] - a[k]) * (c[k] - a[k]);
    }
    let ab = ab2.sqrt();
    let bc = bc2.sqrt();
    let ca = ca2.sqrt();

    // Area via cross product magnitude (works in any dimension)
    // |AB × AC| = |AB| * |AC| * sin(theta)
    // For general dimension, use: area = 0.5 * sqrt(|AB|²|AC|² - (AB·AC)²)
    let mut ab_vec = vec![0.0; d];
    let mut ac_vec = vec![0.0; d];
    for k in 0..d {
        ab_vec[k] = b[k] - a[k];
        ac_vec[k] = c[k] - a[k];
    }
    let dot: f64 = ab_vec.iter().zip(ac_vec.iter()).map(|(x, y)| x * y).sum();
    let cross_mag_sq = ab2 * ca2 - dot * dot;
    let area = 0.5 * cross_mag_sq.max(0.0).sqrt();

    let denom = ab * bc * ca;
    if denom < 1e-12 { 0.0 } else { 4.0 * area / denom }
}

/// Scan data for curvature properties.
pub fn scan(data: &[f64], n_samples: usize, n_features: usize) -> CompassResult {
    if n_samples < 3 || n_features == 0 {
        return CompassResult {
            mean_curvature: 0.0,
            high_curvature_regions: vec![],
            circular_structures: vec![],
        };
    }

    // Compute curvature for consecutive triples (treat samples as ordered path)
    let mut curvatures = vec![0.0; n_samples];
    let mut total_curv = 0.0;
    let mut count = 0;

    for i in 1..n_samples - 1 {
        let a = &data[(i - 1) * n_features..i * n_features];
        let b = &data[i * n_features..(i + 1) * n_features];
        let c = &data[(i + 1) * n_features..(i + 2) * n_features];
        let k = menger_curvature(a, b, c);
        curvatures[i] = k;
        total_curv += k;
        count += 1;
    }

    let mean_curvature = if count > 0 { total_curv / count as f64 } else { 0.0 };

    // High curvature regions: above mean + 1 std
    let var: f64 = curvatures.iter().map(|&k| (k - mean_curvature) * (k - mean_curvature)).sum::<f64>()
        / n_samples as f64;
    let std = var.sqrt();
    let high_threshold = mean_curvature + std;

    let mut high_curvature_regions: Vec<(usize, f64)> = curvatures.iter().enumerate()
        .filter(|&(_, &k)| k > high_threshold)
        .map(|(i, &k)| (i, k))
        .collect();
    high_curvature_regions.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());
    high_curvature_regions.truncate(50);

    // Circular structures: find samples at approximately constant distance from a center
    let mut circular_structures = Vec::new();
    let n_check = n_samples.min(50);
    for ci in 0..n_check {
        // Compute distances from sample ci to all others
        let mut dists: Vec<f64> = (0..n_samples)
            .filter(|&j| j != ci)
            .map(|j| {
                let mut d2 = 0.0;
                for k in 0..n_features {
                    let diff = data[ci * n_features + k] - data[j * n_features + k];
                    d2 += diff * diff;
                }
                d2.sqrt()
            })
            .collect();
        dists.sort_by(|a, b| a.partial_cmp(b).unwrap());

        // Check for a "shell" — cluster of distances near the same value
        if dists.len() < 3 { continue; }
        let median_dist = dists[dists.len() / 2];
        if median_dist < 1e-12 { continue; }
        let tolerance = median_dist * 0.2;
        let n_on_circle = dists.iter().filter(|&&d| (d - median_dist).abs() < tolerance).count();
        if n_on_circle >= n_samples / 3 && n_on_circle >= 3 {
            circular_structures.push((ci, median_dist, n_on_circle));
        }
        if circular_structures.len() >= 20 { break; }
    }

    CompassResult {
        mean_curvature,
        high_curvature_regions,
        circular_structures,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::f64::consts::PI;

    #[test]
    fn test_compass_circle() {
        // Points on a circle should have constant curvature = 1/R
        let n = 32;
        let d = 2;
        let r = 5.0;
        let mut data = vec![0.0; n * d];
        for i in 0..n {
            let theta = 2.0 * PI * i as f64 / n as f64;
            data[i * d] = r * theta.cos();
            data[i * d + 1] = r * theta.sin();
        }
        let result = scan(&data, n, d);
        // Curvature of a circle = 1/R = 0.2
        assert!((result.mean_curvature - 1.0 / r).abs() < 0.05,
                "Expected curvature ~{}, got {}", 1.0 / r, result.mean_curvature);
    }

    #[test]
    fn test_compass_line() {
        // Straight line should have zero curvature
        let n = 10;
        let d = 2;
        let mut data = vec![0.0; n * d];
        for i in 0..n {
            data[i * d] = i as f64;
            data[i * d + 1] = i as f64 * 2.0;
        }
        let result = scan(&data, n, d);
        assert!(result.mean_curvature < 0.01,
                "Line should have ~0 curvature, got {}", result.mean_curvature);
    }
}
