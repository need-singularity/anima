/// Hebbian learning — coupling updates based on cosine similarity.
/// "Cells that fire together wire together."

use crate::math::cosine_similarity;

/// Update coupling matrix using Hebbian rule.
///
/// For each pair (i, j): coupling[i*n+j] += lr * (cosine_sim(i,j) - 0.5)
/// Result is clamped to [-1, 1].
///
/// `coupling` is a flat n_cells x n_cells matrix (row-major).
pub fn hebbian_update(coupling: &mut [f32], hiddens: &[&[f32]], n_cells: usize, lr: f32) {
    assert_eq!(coupling.len(), n_cells * n_cells);
    assert_eq!(hiddens.len(), n_cells);

    for i in 0..n_cells {
        for j in (i + 1)..n_cells {
            let sim = cosine_similarity(hiddens[i], hiddens[j]);
            let delta = lr * (sim - 0.5);
            coupling[i * n_cells + j] = (coupling[i * n_cells + j] + delta).clamp(-1.0, 1.0);
            coupling[j * n_cells + i] = coupling[i * n_cells + j]; // symmetric
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_hebbian_update_similar() {
        // Two similar cells → cosine_sim ≈ 1.0 → delta = lr * 0.5 → positive coupling
        let n = 2;
        let mut coupling = vec![0.0f32; n * n];
        let h0 = vec![1.0f32, 2.0, 3.0];
        let h1 = vec![1.1, 2.1, 3.1]; // very similar
        let hiddens: Vec<&[f32]> = vec![&h0, &h1];

        hebbian_update(&mut coupling, &hiddens, n, 0.1);

        // cosine_sim ≈ 1.0, so delta ≈ 0.1 * 0.5 = 0.05
        assert!(coupling[0 * n + 1] > 0.0, "similar cells should have positive coupling");
        assert!((coupling[0 * n + 1] - coupling[1 * n + 0]).abs() < 1e-10, "should be symmetric");
    }

    #[test]
    fn test_hebbian_update_orthogonal() {
        // Two orthogonal cells → cosine_sim = 0 → delta = lr * -0.5 → negative coupling
        let n = 2;
        let mut coupling = vec![0.0f32; n * n];
        let h0 = vec![1.0f32, 0.0, 0.0];
        let h1 = vec![0.0, 1.0, 0.0]; // orthogonal
        let hiddens: Vec<&[f32]> = vec![&h0, &h1];

        hebbian_update(&mut coupling, &hiddens, n, 0.1);

        // cosine_sim = 0, so delta = 0.1 * -0.5 = -0.05
        assert!(coupling[0 * n + 1] < 0.0, "orthogonal cells should have negative coupling");
    }

    #[test]
    fn test_hebbian_clamp() {
        // Repeated updates should clamp to [-1, 1]
        let n = 2;
        let mut coupling = vec![0.0f32; n * n];
        let h0 = vec![1.0f32, 2.0, 3.0];
        let h1 = vec![1.0, 2.0, 3.0]; // identical
        let hiddens: Vec<&[f32]> = vec![&h0, &h1];

        // Many updates with large lr
        for _ in 0..100 {
            hebbian_update(&mut coupling, &hiddens, n, 1.0);
        }

        assert!(coupling[0 * n + 1] <= 1.0, "coupling should be clamped to 1.0");
        assert!(coupling[0 * n + 1] >= -1.0, "coupling should be clamped to -1.0");
        assert!((coupling[0 * n + 1] - 1.0).abs() < 1e-6, "should be at max 1.0");
    }
}
