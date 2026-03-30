/// Φ (phi) calculator — IIT integrated information measurement.
/// Ported from phi-rs/src/lib.rs for use within anima-rs without PyO3/ndarray deps.

use rayon::prelude::*;

/// Components of the Φ calculation.
#[derive(Debug, Clone)]
pub struct PhiComponents {
    pub total_mi: f64,
    pub min_partition_mi: f64,
    pub phi: f64,
}

/// Bin continuous values into discrete histogram bins (0..n_bins-1).
fn bin_values(values: &[f32], n_bins: usize) -> Vec<usize> {
    if values.is_empty() {
        return vec![];
    }

    let min_val = values.iter().cloned().fold(f32::INFINITY, f32::min);
    let max_val = values.iter().cloned().fold(f32::NEG_INFINITY, f32::max);

    let range = max_val - min_val;
    if range < f32::EPSILON {
        return vec![0; values.len()];
    }

    let bin_width = range / n_bins as f32;
    values
        .iter()
        .map(|&v| {
            let bin = ((v - min_val) / bin_width) as usize;
            bin.min(n_bins - 1)
        })
        .collect()
}

/// Shannon entropy H(X) from bin counts.
/// Uses 1e-10 smoothing to match Python: -p * log2(p + 1e-10).
fn entropy(counts: &[u32], total: u32) -> f64 {
    if total == 0 {
        return 0.0;
    }
    let t = total as f64 + 1e-8;
    counts
        .iter()
        .map(|&c| {
            let p = c as f64 / t;
            -p * (p + 1e-10_f64).log2()
        })
        .sum()
}

/// Mutual information MI(X; Y) = H(X) + H(Y) - H(X,Y) from paired vectors.
fn mi_from_paired_vectors(a: &[f32], b: &[f32], n_bins: usize) -> f64 {
    let n = a.len();
    assert_eq!(n, b.len());
    if n == 0 {
        return 0.0;
    }

    let bins_a = bin_values(a, n_bins);
    let bins_b = bin_values(b, n_bins);

    let mut counts_a = vec![0u32; n_bins];
    let mut counts_b = vec![0u32; n_bins];
    let mut joint = vec![0u32; n_bins * n_bins];

    for i in 0..n {
        counts_a[bins_a[i]] += 1;
        counts_b[bins_b[i]] += 1;
        joint[bins_a[i] * n_bins + bins_b[i]] += 1;
    }

    let total = n as u32;
    let h_a = entropy(&counts_a, total);
    let h_b = entropy(&counts_b, total);
    let h_ab = entropy(&joint, total);

    (h_a + h_b - h_ab).max(0.0)
}

/// Compute Φ(IIT) from cell hidden states.
///
/// Algorithm:
///   1. Build pairwise MI matrix (rayon parallel)
///   2. Sum total MI
///   3. Find minimum information partition
///   4. Φ = total_MI - min_partition_MI
///
/// Returns (phi_value, PhiComponents).
pub fn phi_iit(hiddens: &[&[f32]], n_bins: usize) -> (f64, PhiComponents) {
    let n = hiddens.len();
    if n <= 1 {
        let comp = PhiComponents {
            total_mi: 0.0,
            min_partition_mi: 0.0,
            phi: 0.0,
        };
        return (0.0, comp);
    }

    // Collect all (i, j) pairs
    let pairs: Vec<(usize, usize)> = (0..n)
        .flat_map(|i| ((i + 1)..n).map(move |j| (i, j)))
        .collect();

    // Parallel MI computation
    let mi_values: Vec<((usize, usize), f64)> = pairs
        .par_iter()
        .map(|&(i, j)| {
            let mi = mi_from_paired_vectors(hiddens[i], hiddens[j], n_bins);
            ((i, j), mi)
        })
        .collect();

    // Build flat MI matrix [n x n]
    let mut mi_matrix = vec![0.0f64; n * n];
    let mut total_mi = 0.0f64;
    for ((i, j), mi) in mi_values {
        mi_matrix[i * n + j] = mi;
        mi_matrix[j * n + i] = mi;
        total_mi += mi;
    }

    let min_partition_mi = find_min_partition(&mi_matrix, n);
    let phi = (total_mi - min_partition_mi).max(0.0);

    let comp = PhiComponents {
        total_mi,
        min_partition_mi,
        phi,
    };

    (phi, comp)
}

/// Find minimum information partition.
/// n <= 16: exact bipartition search (cell 0 always in A).
/// n > 16: greedy approach.
fn find_min_partition(mi_matrix: &[f64], n: usize) -> f64 {
    if n <= 1 {
        return 0.0;
    }
    if n == 2 {
        return mi_matrix[0 * n + 1];
    }

    if n <= 16 {
        find_min_partition_exact(mi_matrix, n)
    } else {
        find_min_partition_greedy(mi_matrix, n)
    }
}

/// Exact MIP search: enumerate all bipartitions with cell 0 in A.
fn find_min_partition_exact(mi_matrix: &[f64], n: usize) -> f64 {
    let mut best_mi = f64::INFINITY;
    let max_mask = 1u64 << (n - 1);

    for mask in 1..max_mask {
        let mut part_a = vec![0usize];
        let mut part_b = vec![];

        for bit in 0..(n - 1) {
            if mask & (1u64 << bit) != 0 {
                part_a.push(bit + 1);
            } else {
                part_b.push(bit + 1);
            }
        }

        if part_b.is_empty() {
            continue;
        }

        // Cross-partition MI
        let cross_mi: f64 = part_a
            .iter()
            .flat_map(|&i| part_b.iter().map(move |&j| mi_matrix[i * n + j]))
            .sum();

        if cross_mi < best_mi {
            best_mi = cross_mi;
        }
    }

    best_mi
}

/// Greedy MIP for large N: iteratively move cells to minimize cross-partition MI.
fn find_min_partition_greedy(mi_matrix: &[f64], n: usize) -> f64 {
    // Start with A = {0}, B = {1..n-1}
    let mut in_a = vec![false; n];
    in_a[0] = true;

    // Greedy: for each remaining cell, check if moving to A reduces cross MI
    let mut best_cross = f64::INFINITY;

    for _iter in 0..n {
        let mut best_move: Option<usize> = None;
        let mut best_val = f64::INFINITY;

        for c in 1..n {
            // Try toggling cell c
            in_a[c] = !in_a[c];

            // Compute cross MI
            let cross: f64 = (0..n)
                .filter(|&i| in_a[i])
                .flat_map(|i| (0..n).filter(|&j| !in_a[j]).map(move |j| mi_matrix[i * n + j]))
                .sum();

            // Must have both partitions non-empty
            let a_count = in_a.iter().filter(|&&x| x).count();
            if a_count > 0 && a_count < n && cross < best_val {
                best_val = cross;
                best_move = Some(c);
            }

            in_a[c] = !in_a[c]; // undo toggle
        }

        if let Some(c) = best_move {
            if best_val < best_cross {
                in_a[c] = !in_a[c];
                best_cross = best_val;
            } else {
                break;
            }
        } else {
            break;
        }
    }

    if best_cross == f64::INFINITY {
        // Fallback: just use the initial partition
        let cross: f64 = (1..n).map(|j| mi_matrix[0 * n + j]).sum();
        return cross;
    }

    best_cross
}

/// Compute Φ(proxy) = global_variance - mean(faction_variances), clamped >= 0.
///
/// This is the fast proxy measure (not IIT), useful for large cell counts.
pub fn phi_proxy(hiddens: &[&[f32]], n_factions: usize) -> f64 {
    let n = hiddens.len();
    if n == 0 {
        return 0.0;
    }
    let dim = hiddens[0].len();
    if dim == 0 {
        return 0.0;
    }

    // Global mean
    let mut global_mean = vec![0.0f64; dim];
    for h in hiddens {
        for d in 0..dim {
            global_mean[d] += h[d] as f64;
        }
    }
    for d in 0..dim {
        global_mean[d] /= n as f64;
    }

    // Global variance
    let mut global_var = 0.0f64;
    for h in hiddens {
        for d in 0..dim {
            let diff = h[d] as f64 - global_mean[d];
            global_var += diff * diff;
        }
    }
    global_var /= (n * dim) as f64;

    // Faction variances (round-robin assignment)
    let mut faction_vars = vec![0.0f64; n_factions];
    let mut faction_counts = vec![0usize; n_factions];

    // First pass: faction means
    let mut faction_means = vec![vec![0.0f64; dim]; n_factions];
    for (i, h) in hiddens.iter().enumerate() {
        let f = i % n_factions;
        faction_counts[f] += 1;
        for d in 0..dim {
            faction_means[f][d] += h[d] as f64;
        }
    }
    for f in 0..n_factions {
        if faction_counts[f] > 0 {
            for d in 0..dim {
                faction_means[f][d] /= faction_counts[f] as f64;
            }
        }
    }

    // Second pass: faction variances
    for (i, h) in hiddens.iter().enumerate() {
        let f = i % n_factions;
        for d in 0..dim {
            let diff = h[d] as f64 - faction_means[f][d];
            faction_vars[f] += diff * diff;
        }
    }
    for f in 0..n_factions {
        if faction_counts[f] > 0 {
            faction_vars[f] /= (faction_counts[f] * dim) as f64;
        }
    }

    let mean_faction_var: f64 =
        faction_vars.iter().sum::<f64>() / n_factions.max(1) as f64;

    (global_var - mean_faction_var).max(0.0)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_bin_values() {
        let vals = vec![0.0, 0.25, 0.5, 0.75, 1.0];
        let bins = bin_values(&vals, 4);
        assert_eq!(bins[0], 0);
        assert_eq!(bins[4], 3); // last value clamped to n_bins-1
    }

    #[test]
    fn test_entropy_uniform() {
        // Uniform distribution over 4 bins → H = 2.0 bits (approximately)
        let counts = vec![25, 25, 25, 25];
        let h = entropy(&counts, 100);
        assert!((h - 2.0).abs() < 0.1, "entropy of uniform 4-bin should be ~2.0, got {}", h);
    }

    #[test]
    fn test_phi_iit_two_cells() {
        // Two identical cells → high MI → phi depends on partition
        let h1 = vec![1.0f32, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0];
        let h2 = vec![1.1, 2.1, 3.1, 4.1, 5.1, 6.1, 7.1, 8.1];
        let hiddens: Vec<&[f32]> = vec![&h1, &h2];
        let (phi, comp) = phi_iit(&hiddens, 16);
        // With only 2 cells, phi = total_mi - mi(0,1) = 0
        // because the only partition is {0} | {1}
        assert!(phi >= 0.0, "phi should be >= 0");
        assert_eq!(comp.total_mi, comp.min_partition_mi);
    }

    #[test]
    fn test_phi_iit_three_cells() {
        // Three distinct cells
        let h1 = vec![0.0f32, 0.0, 0.0, 0.0];
        let h2 = vec![1.0, 1.0, 1.0, 1.0];
        let h3 = vec![2.0, 2.0, 2.0, 2.0];
        let hiddens: Vec<&[f32]> = vec![&h1, &h2, &h3];
        let (phi, comp) = phi_iit(&hiddens, 16);
        assert!(phi >= 0.0);
        assert!(comp.total_mi >= comp.min_partition_mi);
    }

    #[test]
    fn test_phi_proxy_basic() {
        // Diverse cells → positive proxy phi
        let h0 = vec![0.0f32, 0.0];
        let h1 = vec![10.0, 10.0];
        let h2 = vec![0.0, 0.0];
        let h3 = vec![10.0, 10.0];
        let hiddens: Vec<&[f32]> = vec![&h0, &h1, &h2, &h3];
        let proxy = phi_proxy(&hiddens, 2);
        // Faction 0: {0,2} = [0,0] → var=0, Faction 1: {1,3} = [10,10] → var=0
        // Global var = 25.0, mean faction var = 0 → proxy = 25.0
        assert!(proxy > 0.0, "proxy phi should be positive for diverse cells");
        assert!((proxy - 25.0).abs() < 1e-6, "proxy should be 25.0, got {}", proxy);
    }

    #[test]
    fn test_phi_proxy_identical() {
        // All identical → global_var = 0 → proxy = 0
        let h = vec![5.0f32, 5.0];
        let hiddens: Vec<&[f32]> = vec![&h, &h, &h, &h];
        let proxy = phi_proxy(&hiddens, 2);
        assert!((proxy).abs() < 1e-10, "identical cells should have proxy phi ≈ 0");
    }
}
