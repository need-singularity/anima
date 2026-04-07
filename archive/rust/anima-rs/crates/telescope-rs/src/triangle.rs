//! TriangleLens — Ratio/proportion detection
//!
//! Finds simple fraction relationships between feature pairs and proportion chains.

/// Result of triangle lens scan.
#[derive(Debug, Clone)]
pub struct TriangleResult {
    /// Simple ratio pairs: (feat_i, feat_j, p, q) where ratio ≈ p/q
    pub simple_ratios: Vec<(usize, usize, u32, u32)>,
    /// Proportion chains: sequences of features with A/B ≈ B/C
    pub proportion_chains: Vec<Vec<usize>>,
}

/// Check if a ratio is close to a simple fraction p/q where p,q <= max_pq.
/// Returns Some((p, q)) if found, None otherwise.
fn find_simple_fraction(ratio: f64, max_pq: u32, tolerance: f64) -> Option<(u32, u32)> {
    if ratio <= 0.0 || !ratio.is_finite() { return None; }
    let mut best: Option<(u32, u32, f64)> = None;
    for q in 1..=max_pq {
        for p in 1..=max_pq {
            let frac = p as f64 / q as f64;
            let err = (ratio - frac).abs();
            if err < tolerance {
                match best {
                    None => best = Some((p, q, err)),
                    Some((_, _, prev_err)) if err < prev_err => best = Some((p, q, err)),
                    _ => {}
                }
            }
        }
    }
    best.map(|(p, q, _)| (p, q))
}

/// Scan data for ratio/proportion properties.
pub fn scan(data: &[f64], n_samples: usize, n_features: usize) -> TriangleResult {
    if n_samples < 2 || n_features < 2 {
        return TriangleResult {
            simple_ratios: vec![],
            proportion_chains: vec![],
        };
    }

    // Compute mean absolute value per feature
    let means: Vec<f64> = (0..n_features)
        .map(|j| {
            let sum: f64 = (0..n_samples).map(|i| data[i * n_features + j].abs()).sum();
            sum / n_samples as f64
        })
        .collect();

    // Find simple ratios between feature pairs
    let max_pq = 12;
    let tolerance = 0.05;
    let mut simple_ratios = Vec::new();

    for i in 0..n_features {
        if means[i] < 1e-12 { continue; }
        for j in (i + 1)..n_features {
            if means[j] < 1e-12 { continue; }
            let ratio = means[i] / means[j];
            if let Some((p, q)) = find_simple_fraction(ratio, max_pq, tolerance) {
                simple_ratios.push((i, j, p, q));
            }
            // Also check per-sample ratios for consistency
            let mut consistent = 0;
            let check_n = n_samples.min(20);
            for s in 0..check_n {
                let vi = data[s * n_features + i].abs();
                let vj = data[s * n_features + j].abs();
                if vj < 1e-12 || vi < 1e-12 { continue; }
                let r = vi / vj;
                if let Some(_) = find_simple_fraction(r, max_pq, tolerance * 2.0) {
                    consistent += 1;
                }
            }
            // If majority of samples show simple ratio, it's stronger
            if consistent > check_n / 2 && simple_ratios.last().map(|r| r.0 != i || r.1 != j).unwrap_or(true) {
                // Already added above if mean ratio matched
            }
            if simple_ratios.len() >= 200 { break; }
        }
        if simple_ratios.len() >= 200 { break; }
    }

    // Proportion chains: find sequences where A/B ≈ B/C
    let mut proportion_chains = Vec::new();
    for &(i, j, p1, q1) in &simple_ratios {
        let r1 = p1 as f64 / q1 as f64;
        for &(j2, k, p2, q2) in &simple_ratios {
            if j2 != j || k == i { continue; }
            let r2 = p2 as f64 / q2 as f64;
            // Chain: i/j ≈ r1, j/k ≈ r2 — proportion chain
            if (r1 - r2).abs() < tolerance * 3.0 {
                proportion_chains.push(vec![i, j, k]);
            }
            if proportion_chains.len() >= 50 { break; }
        }
        if proportion_chains.len() >= 50 { break; }
    }

    TriangleResult {
        simple_ratios,
        proportion_chains,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_triangle_simple_ratio() {
        // Feature 0 = 2x, Feature 1 = 3x → ratio = 2/3
        let n = 20;
        let d = 2;
        let mut data = vec![0.0; n * d];
        for i in 0..n {
            let x = (i + 1) as f64;
            data[i * d] = 2.0 * x;
            data[i * d + 1] = 3.0 * x;
        }
        let result = scan(&data, n, d);
        assert!(!result.simple_ratios.is_empty(), "Should find ratio 2/3");
        let (_, _, p, q) = result.simple_ratios[0];
        assert_eq!(p, 2);
        assert_eq!(q, 3);
    }

    #[test]
    fn test_triangle_no_ratio() {
        let result = scan(&[1.0, 2.0], 1, 2);
        // Single sample — too few
        assert!(result.simple_ratios.is_empty());
    }

    #[test]
    fn test_find_simple_fraction() {
        assert_eq!(find_simple_fraction(0.5, 12, 0.05), Some((1, 2)));
        assert_eq!(find_simple_fraction(0.333, 12, 0.05), Some((1, 3)));
        assert_eq!(find_simple_fraction(3.14159, 12, 0.05), None); // pi is not simple
    }
}
