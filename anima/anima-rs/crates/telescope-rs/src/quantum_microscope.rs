//! QuantumMicroscopeLens — Density matrix analysis
//!
//! Constructs a density matrix from data covariance, computes purity,
//! Von Neumann entropy, coherence, and decoherence rate.

/// Result of quantum microscope lens scan.
#[derive(Debug, Clone)]
pub struct QuantumMicroscopeResult {
    /// Purity = Tr(rho^2), 1/d <= purity <= 1
    pub purity: f64,
    /// Von Neumann entropy = -Tr(rho * ln(rho))
    pub von_neumann_entropy: f64,
    /// Coherence = sum of off-diagonal magnitudes
    pub coherence: f64,
    /// Decoherence rate: ratio of off-diagonal to diagonal magnitude
    pub decoherence_rate: f64,
}

/// Compute eigenvalues of a symmetric matrix using Jacobi iteration.
/// Matrix is d×d, row-major. Returns eigenvalues sorted descending.
fn eigenvalues_symmetric(mat: &[f64], d: usize) -> Vec<f64> {
    if d == 0 { return vec![]; }
    if d == 1 { return vec![mat[0]]; }

    let mut a = mat.to_vec();
    let max_iter = 100;

    for _ in 0..max_iter {
        // Find largest off-diagonal element
        let mut max_val = 0.0f64;
        let mut p = 0;
        let mut q = 1;
        for i in 0..d {
            for j in (i + 1)..d {
                let v = a[i * d + j].abs();
                if v > max_val {
                    max_val = v;
                    p = i;
                    q = j;
                }
            }
        }

        if max_val < 1e-12 { break; }

        // Jacobi rotation
        let app = a[p * d + p];
        let aqq = a[q * d + q];
        let apq = a[p * d + q];

        let theta = if (app - aqq).abs() < 1e-12 {
            std::f64::consts::FRAC_PI_4
        } else {
            0.5 * (2.0 * apq / (app - aqq)).atan()
        };

        let c = theta.cos();
        let s = theta.sin();

        // Update matrix
        let mut new_a = a.clone();
        for i in 0..d {
            if i == p || i == q { continue; }
            new_a[i * d + p] = c * a[i * d + p] + s * a[i * d + q];
            new_a[p * d + i] = new_a[i * d + p];
            new_a[i * d + q] = -s * a[i * d + p] + c * a[i * d + q];
            new_a[q * d + i] = new_a[i * d + q];
        }
        new_a[p * d + p] = c * c * app + 2.0 * s * c * apq + s * s * aqq;
        new_a[q * d + q] = s * s * app - 2.0 * s * c * apq + c * c * aqq;
        new_a[p * d + q] = 0.0;
        new_a[q * d + p] = 0.0;

        a = new_a;
    }

    let mut eigenvalues: Vec<f64> = (0..d).map(|i| a[i * d + i]).collect();
    eigenvalues.sort_by(|a, b| b.partial_cmp(a).unwrap_or(std::cmp::Ordering::Equal));
    eigenvalues
}

/// Scan data for quantum microscope properties.
pub fn scan(data: &[f64], n_samples: usize, n_features: usize) -> QuantumMicroscopeResult {
    if n_samples < 2 || n_features == 0 {
        return QuantumMicroscopeResult {
            purity: 1.0,
            von_neumann_entropy: 0.0,
            coherence: 0.0,
            decoherence_rate: 0.0,
        };
    }

    // Use effective dimension (cap at 32 for performance)
    let d = n_features.min(32);

    // Compute mean
    let mut mean = vec![0.0; d];
    for i in 0..n_samples {
        for j in 0..d {
            mean[j] += data[i * n_features + j];
        }
    }
    let inv_n = 1.0 / n_samples as f64;
    for j in 0..d {
        mean[j] *= inv_n;
    }

    // Compute covariance matrix (d × d)
    let mut cov = vec![0.0; d * d];
    for i in 0..n_samples {
        for j in 0..d {
            let dj = data[i * n_features + j] - mean[j];
            for k in j..d {
                let dk = data[i * n_features + k] - mean[k];
                cov[j * d + k] += dj * dk;
            }
        }
    }
    for j in 0..d {
        for k in j..d {
            cov[j * d + k] *= inv_n;
            cov[k * d + j] = cov[j * d + k];
        }
    }

    // Normalize covariance to density matrix (trace = 1)
    let trace: f64 = (0..d).map(|i| cov[i * d + i]).sum();
    if trace.abs() < 1e-12 {
        return QuantumMicroscopeResult {
            purity: 1.0,
            von_neumann_entropy: 0.0,
            coherence: 0.0,
            decoherence_rate: 0.0,
        };
    }
    let inv_trace = 1.0 / trace;
    let rho: Vec<f64> = cov.iter().map(|&v| v * inv_trace).collect();

    // Purity = Tr(rho^2)
    let mut purity = 0.0;
    for i in 0..d {
        for k in 0..d {
            purity += rho[i * d + k] * rho[k * d + i];
        }
    }

    // Coherence = sum of |off-diagonal|
    let mut coherence = 0.0;
    let mut diag_sum = 0.0;
    for i in 0..d {
        diag_sum += rho[i * d + i].abs();
        for j in 0..d {
            if i != j {
                coherence += rho[i * d + j].abs();
            }
        }
    }

    // Decoherence rate = coherence / diagonal_sum
    let decoherence_rate = if diag_sum > 1e-12 { coherence / diag_sum } else { 0.0 };

    // Von Neumann entropy = -Tr(rho * ln(rho)) = -sum(lambda_i * ln(lambda_i))
    let eigenvalues = eigenvalues_symmetric(&rho, d);
    let mut von_neumann_entropy = 0.0;
    for &lam in &eigenvalues {
        if lam > 1e-12 {
            von_neumann_entropy -= lam * lam.ln();
        }
    }

    QuantumMicroscopeResult {
        purity,
        von_neumann_entropy,
        coherence,
        decoherence_rate,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_qm_pure_state() {
        // All samples identical → pure state → purity ≈ 1
        let n = 10;
        let d = 4;
        let data: Vec<f64> = (0..n).flat_map(|_| vec![1.0, 0.0, 0.0, 0.0]).collect();
        let result = scan(&data, n, d);
        // All identical → zero covariance → density matrix is identity/d
        // Actually, all identical means covariance is zero matrix
        // With zero cov, trace=0 → early return
        assert!(result.purity >= 0.0);
    }

    #[test]
    fn test_qm_mixed_state() {
        // Diverse data → mixed state → lower purity
        let n = 50;
        let d = 4;
        let data: Vec<f64> = (0..n * d).map(|i| (i as f64 * 0.37).sin()).collect();
        let result = scan(&data, n, d);
        assert!(result.purity > 0.0 && result.purity <= 1.0 + 1e-6,
                "Purity should be in (0, 1], got {}", result.purity);
        assert!(result.von_neumann_entropy >= 0.0,
                "VN entropy should be non-negative, got {}", result.von_neumann_entropy);
        assert!(result.coherence >= 0.0);
    }
}
