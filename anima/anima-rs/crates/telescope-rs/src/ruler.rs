//! RulerLens — Orthogonality/SVD analysis
//!
//! SVD of data matrix, effective dimensionality, cosine similarity matrix.

/// Result of ruler lens scan.
#[derive(Debug, Clone)]
pub struct RulerResult {
    /// Singular values (sorted descending)
    pub singular_values: Vec<f64>,
    /// Effective dimensionality (number of significant singular values)
    pub effective_dim: usize,
    /// Cosine similarity matrix between features (n_features × n_features, row-major)
    pub cosine_matrix: Vec<f64>,
    /// Groups of orthogonal features (cosine < 0.1)
    pub orthogonal_groups: Vec<Vec<usize>>,
}

/// Power iteration SVD: find top-k singular values.
/// data is n_samples × n_features, row-major.
fn power_svd(data: &[f64], n: usize, d: usize, max_k: usize) -> Vec<f64> {
    let k = max_k.min(n).min(d);
    if k == 0 || n == 0 || d == 0 { return vec![]; }

    let mut singular_values = Vec::with_capacity(k);
    // Work with A^T A (d × d) for efficiency when d < n
    // Else A A^T (n × n)
    let use_ata = d <= n;
    let dim = if use_ata { d } else { n };

    // Deflated residual
    let mut residual = data.to_vec();

    for _ in 0..k {
        // Random initial vector
        let mut v: Vec<f64> = (0..dim).map(|i| ((i as f64 * 0.618 + 0.5) % 1.0) - 0.5).collect();
        let norm: f64 = v.iter().map(|x| x * x).sum::<f64>().sqrt().max(1e-12);
        for x in v.iter_mut() { *x /= norm; }

        let mut sigma = 0.0;

        for _ in 0..50 {
            // Multiply: if use_ata, compute (A^T A) v
            // else compute (A A^T) v
            let mut new_v = vec![0.0; dim];
            if use_ata {
                // temp = A @ v (n-dim)
                let mut temp = vec![0.0; n];
                for i in 0..n {
                    for j in 0..d {
                        temp[i] += residual[i * d + j] * v[j];
                    }
                }
                // new_v = A^T @ temp (d-dim)
                for j in 0..d {
                    for i in 0..n {
                        new_v[j] += residual[i * d + j] * temp[i];
                    }
                }
            } else {
                // temp = A^T @ v (d-dim)
                let mut temp = vec![0.0; d];
                for j in 0..d {
                    for i in 0..n {
                        temp[j] += residual[i * d + j] * v[i];
                    }
                }
                // new_v = A @ temp (n-dim)
                for i in 0..n {
                    for j in 0..d {
                        new_v[i] += residual[i * d + j] * temp[j];
                    }
                }
            }

            let norm: f64 = new_v.iter().map(|x| x * x).sum::<f64>().sqrt().max(1e-12);
            sigma = norm.sqrt(); // singular value ~ sqrt of eigenvalue of A^TA
            for x in new_v.iter_mut() { *x /= norm; }
            v = new_v;
        }

        singular_values.push(sigma);

        // Deflate: residual -= sigma * u * v^T
        if use_ata {
            // u = A @ v / sigma
            let mut u = vec![0.0; n];
            for i in 0..n {
                for j in 0..d {
                    u[i] += residual[i * d + j] * v[j];
                }
            }
            let u_norm: f64 = u.iter().map(|x| x * x).sum::<f64>().sqrt().max(1e-12);
            for x in u.iter_mut() { *x /= u_norm; }
            for i in 0..n {
                for j in 0..d {
                    residual[i * d + j] -= sigma * u[i] * v[j];
                }
            }
        } else {
            // v_right = A^T @ v / sigma
            let mut v_right = vec![0.0; d];
            for j in 0..d {
                for i in 0..n {
                    v_right[j] += residual[i * d + j] * v[i];
                }
            }
            let vr_norm: f64 = v_right.iter().map(|x| x * x).sum::<f64>().sqrt().max(1e-12);
            for x in v_right.iter_mut() { *x /= vr_norm; }
            for i in 0..n {
                for j in 0..d {
                    residual[i * d + j] -= sigma * v[i] * v_right[j];
                }
            }
        }
    }

    singular_values
}

/// Scan data for SVD/orthogonality properties.
pub fn scan(data: &[f64], n_samples: usize, n_features: usize) -> RulerResult {
    if n_samples < 2 || n_features == 0 {
        return RulerResult {
            singular_values: vec![],
            effective_dim: 0,
            cosine_matrix: vec![],
            orthogonal_groups: vec![],
        };
    }

    // SVD
    let max_k = n_features.min(n_samples).min(20);
    let singular_values = power_svd(data, n_samples, n_features, max_k);

    // Effective dimensionality: count singular values > 1% of max
    let sv_max = singular_values.first().copied().unwrap_or(0.0);
    let threshold = sv_max * 0.01;
    let effective_dim = singular_values.iter().filter(|&&s| s > threshold).count();

    // Cosine similarity between features (columns)
    let d = n_features;
    let mut cosine_matrix = vec![0.0; d * d];
    let mut norms = vec![0.0f64; d];
    for j in 0..d {
        let mut sq = 0.0;
        for i in 0..n_samples {
            sq += data[i * d + j] * data[i * d + j];
        }
        norms[j] = sq.sqrt().max(1e-12);
    }
    for i in 0..d {
        cosine_matrix[i * d + i] = 1.0;
        for j in (i + 1)..d {
            let mut dot = 0.0;
            for s in 0..n_samples {
                dot += data[s * d + i] * data[s * d + j];
            }
            let cos = dot / (norms[i] * norms[j]);
            cosine_matrix[i * d + j] = cos;
            cosine_matrix[j * d + i] = cos;
        }
    }

    // Find orthogonal groups (features with pairwise cosine < 0.1)
    let mut assigned = vec![false; d];
    let mut orthogonal_groups = Vec::new();
    for i in 0..d {
        if assigned[i] { continue; }
        let mut group = vec![i];
        assigned[i] = true;
        for j in (i + 1)..d {
            if assigned[j] { continue; }
            let all_orth = group.iter().all(|&g| cosine_matrix[g * d + j].abs() < 0.1);
            if all_orth {
                group.push(j);
                assigned[j] = true;
            }
        }
        if group.len() >= 2 {
            orthogonal_groups.push(group);
        }
    }

    RulerResult {
        singular_values,
        effective_dim,
        cosine_matrix,
        orthogonal_groups,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_ruler_basic() {
        let n = 20;
        let d = 4;
        let data: Vec<f64> = (0..n * d).map(|i| (i as f64 * 0.1).sin()).collect();
        let result = scan(&data, n, d);
        assert!(!result.singular_values.is_empty());
        assert!(result.effective_dim >= 1);
        assert_eq!(result.cosine_matrix.len(), d * d);
        // Diagonal should be 1.0
        for i in 0..d {
            assert!((result.cosine_matrix[i * d + i] - 1.0).abs() < 1e-9);
        }
    }

    #[test]
    fn test_ruler_orthogonal() {
        // Two orthogonal features
        let n = 20;
        let d = 2;
        let mut data = vec![0.0; n * d];
        for i in 0..n {
            data[i * d] = i as f64;     // (1, 0) direction
            data[i * d + 1] = 0.0;       // orthogonal
        }
        let result = scan(&data, n, d);
        // Cosine between features should be low
        let cos01 = result.cosine_matrix[0 * d + 1].abs();
        assert!(cos01 < 0.2, "Expected near-zero cosine, got {cos01}");
    }
}
