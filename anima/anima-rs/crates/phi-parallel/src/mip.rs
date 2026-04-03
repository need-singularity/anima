//! Minimum Information Partition (MIP) search.
//!
//! For N <= 20: Parallel exhaustive search over all 2^(N-1) bipartitions using rayon.
//! For N > 20: Spectral bisection using Fiedler vector of the MI graph Laplacian.

use rayon::prelude::*;

/// Result of MIP search.
#[derive(Debug, Clone)]
pub struct MipResult {
    /// The cross-partition MI of the minimum partition.
    pub mip_mi: f64,
    /// Boolean mask: true = partition A, false = partition B.
    pub partition: Vec<bool>,
}

/// Find the minimum information partition.
///
/// `mi_matrix` is a flattened n x n symmetric MI matrix.
///
/// - N <= 1: returns 0
/// - N == 2: returns MI(0,1)
/// - N <= 20: parallel exhaustive search (rayon)
/// - N > 20: spectral bisection (Fiedler vector)
pub fn find_mip(mi_matrix: &[f64], n: usize) -> MipResult {
    if n <= 1 {
        return MipResult {
            mip_mi: 0.0,
            partition: vec![true; n],
        };
    }
    if n == 2 {
        return MipResult {
            mip_mi: mi_matrix[0 * n + 1],
            partition: vec![true, false],
        };
    }

    if n <= 20 {
        find_mip_exact_parallel(mi_matrix, n)
    } else {
        find_mip_spectral(mi_matrix, n)
    }
}

/// Parallel exhaustive MIP search for small N (<=20).
///
/// Cell 0 is always in partition A to avoid mirror duplicates.
/// Iterates over all 2^(N-1) - 1 valid bipartitions using rayon par_iter.
fn find_mip_exact_parallel(mi_matrix: &[f64], n: usize) -> MipResult {
    let max_mask: u64 = 1u64 << (n - 1);

    // Parallel search over all bipartition masks
    let (best_mask, best_mi) = (1..max_mask)
        .into_par_iter()
        .filter_map(|mask| {
            // Build partition: cell 0 always in A
            let mut has_b = false;
            for bit in 0..(n - 1) {
                if mask & (1u64 << bit) == 0 {
                    has_b = true;
                    break;
                }
            }
            if !has_b {
                return None; // All cells in A, no valid partition
            }

            // Compute cross-partition MI
            let mut cross_mi = 0.0f64;
            // Cell 0 is always in A
            for bit_j in 0..(n - 1) {
                let j = bit_j + 1;
                let j_in_a = mask & (1u64 << bit_j) != 0;

                if !j_in_a {
                    // j is in B, cell 0 is in A
                    cross_mi += mi_matrix[0 * n + j];
                }
            }

            // Pairs among cells 1..n
            for bit_i in 0..(n - 1) {
                let i = bit_i + 1;
                let i_in_a = mask & (1u64 << bit_i) != 0;

                for bit_j in (bit_i + 1)..(n - 1) {
                    let j = bit_j + 1;
                    let j_in_a = mask & (1u64 << bit_j) != 0;

                    if i_in_a != j_in_a {
                        cross_mi += mi_matrix[i * n + j];
                    }
                }
            }

            Some((mask, cross_mi))
        })
        .reduce_with(|a, b| if a.1 < b.1 { a } else { b })
        .unwrap_or((1, f64::INFINITY));

    // Reconstruct partition from best mask
    let mut partition = vec![false; n];
    partition[0] = true; // Cell 0 always in A
    for bit in 0..(n - 1) {
        if best_mask & (1u64 << bit) != 0 {
            partition[bit + 1] = true;
        }
    }

    MipResult {
        mip_mi: if best_mi == f64::INFINITY {
            0.0
        } else {
            best_mi
        },
        partition,
    }
}

/// Spectral bisection MIP for large N (>20).
///
/// Computes the Fiedler vector (2nd smallest eigenvector of graph Laplacian)
/// and tries all split points along the sorted Fiedler values.
fn find_mip_spectral(mi_matrix: &[f64], n: usize) -> MipResult {
    // Build Laplacian: L = D - W
    let mut degree = vec![0.0f64; n];
    for i in 0..n {
        for j in 0..n {
            degree[i] += mi_matrix[i * n + j];
        }
    }

    let mut laplacian = vec![0.0f64; n * n];
    for i in 0..n {
        for j in 0..n {
            if i == j {
                laplacian[i * n + j] = degree[i];
            } else {
                laplacian[i * n + j] = -mi_matrix[i * n + j];
            }
        }
    }

    // Power iteration to find Fiedler vector (2nd smallest eigenvector)
    // First, find smallest eigenvector (constant vector), then deflate and find next.
    let fiedler = compute_fiedler_vector(&laplacian, n);

    // Sort cells by Fiedler value and try all split points
    let mut sorted_indices: Vec<usize> = (0..n).collect();
    sorted_indices.sort_by(|&a, &b| fiedler[a].partial_cmp(&fiedler[b]).unwrap());

    let mut best_mi = f64::INFINITY;
    let mut best_split = 1;

    for split in 1..n {
        let cross_mi = compute_cross_mi_from_split(mi_matrix, n, &sorted_indices, split);
        if cross_mi < best_mi {
            best_mi = cross_mi;
            best_split = split;
        }
    }

    let mut partition = vec![false; n];
    for &idx in &sorted_indices[..best_split] {
        partition[idx] = true;
    }

    MipResult {
        mip_mi: if best_mi == f64::INFINITY {
            0.0
        } else {
            best_mi
        },
        partition,
    }
}

/// Compute cross-partition MI for a split point in sorted order.
fn compute_cross_mi_from_split(
    mi_matrix: &[f64],
    n: usize,
    sorted_indices: &[usize],
    split: usize,
) -> f64 {
    let part_a = &sorted_indices[..split];
    let part_b = &sorted_indices[split..];

    let mut cross = 0.0f64;
    for &i in part_a {
        for &j in part_b {
            cross += mi_matrix[i * n + j];
        }
    }
    cross
}

/// Compute Fiedler vector via inverse power iteration on the Laplacian.
/// Uses a simple approach: power iteration on (L + shift*I)^{-1} - find
/// the smallest non-trivial eigenvector.
///
/// For robustness, we use the simpler approach: compute eigenvectors
/// via repeated power iteration with deflation.
fn compute_fiedler_vector(laplacian: &[f64], n: usize) -> Vec<f64> {
    // Simple approach: use the row sums of MI matrix as a proxy for Fiedler ordering.
    // For a more accurate implementation, we'd use a proper eigendecomposition.
    // This proxy works well because high-MI-sum cells are hubs that should be split.

    // Actually, let's do a proper power iteration for the smallest non-trivial eigenvector.
    // We use inverse iteration: solve (L - sigma*I)x = b repeatedly.
    // For simplicity and robustness, use Lanczos-like approach with deflation.

    // Step 1: The smallest eigenvector of L is the constant vector [1,1,...,1]/sqrt(n).
    // Step 2: Deflate and find the next smallest via power iteration on -L (largest of -L).

    // For numerical stability with arbitrary sizes, use QR-free approach:
    // Repeatedly multiply by L, orthogonalize against constant vector, normalize.
    // The vector that converges is the Fiedler vector.

    let sqrt_n = (n as f64).sqrt();
    let e1: Vec<f64> = vec![1.0 / sqrt_n; n]; // constant eigenvector

    // Random-ish starting vector (deterministic for reproducibility)
    let mut v: Vec<f64> = (0..n).map(|i| (i as f64 * 0.618).sin()).collect();

    // Orthogonalize against constant vector
    let dot_e1: f64 = v.iter().zip(e1.iter()).map(|(a, b)| a * b).sum();
    for i in 0..n {
        v[i] -= dot_e1 * e1[i];
    }
    let norm: f64 = v.iter().map(|x| x * x).sum::<f64>().sqrt();
    if norm < 1e-12 {
        // Fallback: use index-based ordering
        return (0..n).map(|i| i as f64).collect();
    }
    for x in v.iter_mut() {
        *x /= norm;
    }

    // Power iteration on L (converges to largest eigenvector of L).
    // We want the smallest non-trivial, so we use (max_eig * I - L) instead.
    // First estimate max eigenvalue.
    let max_eig_estimate: f64 = (0..n)
        .map(|i| {
            let mut row_sum = 0.0;
            for j in 0..n {
                row_sum += laplacian[i * n + j].abs();
            }
            row_sum
        })
        .fold(0.0f64, f64::max);

    let shift = max_eig_estimate + 1.0;

    // Build shifted matrix: M = shift*I - L (largest eigenvector of M = smallest non-trivial of L)
    for _iter in 0..100 {
        // w = M * v = shift*v - L*v
        let mut w = vec![0.0f64; n];
        for i in 0..n {
            let mut lv = 0.0f64;
            for j in 0..n {
                lv += laplacian[i * n + j] * v[j];
            }
            w[i] = shift * v[i] - lv;
        }

        // Orthogonalize against constant vector
        let dot_e1: f64 = w.iter().zip(e1.iter()).map(|(a, b)| a * b).sum();
        for i in 0..n {
            w[i] -= dot_e1 * e1[i];
        }

        // Normalize
        let norm: f64 = w.iter().map(|x| x * x).sum::<f64>().sqrt();
        if norm < 1e-12 {
            break;
        }
        for x in w.iter_mut() {
            *x /= norm;
        }

        v = w;
    }

    v
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_mip_two_cells() {
        // 2 cells: only one partition {0}|{1}
        let mi_matrix = vec![0.0, 0.5, 0.5, 0.0];
        let result = find_mip(&mi_matrix, 2);
        assert!((result.mip_mi - 0.5).abs() < 1e-10);
    }

    #[test]
    fn test_mip_three_cells_symmetric() {
        // 3 cells with equal MI between all pairs
        // Best partition should split 1 vs 2 (cross MI = some value)
        let mi = 0.3;
        #[rustfmt::skip]
        let mi_matrix = vec![
            0.0, mi,  mi,
            mi,  0.0, mi,
            mi,  mi,  0.0,
        ];
        let result = find_mip(&mi_matrix, 3);
        // With symmetric MI, best is {0}|{1,2} with cross = 2*0.3 = 0.6
        // or {0,1}|{2} with cross = 0.3+0.3 = 0.6
        // All splits give 0.6, minimum is 0.3 (single link: {0,1}|{2} => MI(0,2)+MI(1,2)=0.6)
        // Actually {0}|{1,2} cross = MI(0,1)+MI(0,2) = 0.6
        // {0,1}|{2} cross = MI(0,2)+MI(1,2) = 0.6
        // So mip_mi = 0.6
        assert!(result.mip_mi > 0.0);
        assert!((result.mip_mi - 0.6).abs() < 1e-10);
    }

    #[test]
    fn test_mip_finds_natural_cut() {
        // 4 cells in two clusters: {0,1} strongly connected, {2,3} strongly connected
        // Weak connection between clusters
        let strong = 1.0;
        let weak = 0.01;
        #[rustfmt::skip]
        let mi_matrix = vec![
            0.0,    strong, weak,   weak,
            strong, 0.0,    weak,   weak,
            weak,   weak,   0.0,    strong,
            weak,   weak,   strong, 0.0,
        ];
        let result = find_mip(&mi_matrix, 4);
        // Best partition: {0,1}|{2,3} with cross = 4*0.01 = 0.04
        assert!(result.mip_mi < 0.1, "MIP should find the natural cluster cut");
        // Check partition separates the clusters
        assert_eq!(result.partition[0], result.partition[1]);
        assert_eq!(result.partition[2], result.partition[3]);
        assert_ne!(result.partition[0], result.partition[2]);
    }

    #[test]
    fn test_mip_single_cell() {
        let result = find_mip(&[0.0], 1);
        assert_eq!(result.mip_mi, 0.0);
    }
}
