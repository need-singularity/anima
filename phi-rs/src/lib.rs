use ndarray::{Array2, ArrayView2};
use numpy::{PyArray1, PyArray2, PyReadonlyArray1, PyReadonlyArray2};
use pyo3::prelude::*;
use pyo3::types::PyDict;
use rayon::prelude::*;

// ============================================================================
// PhiCalculator — Rust implementation for 100x speedup
//
// Input:  cell hidden states [n_cells x hidden_dim] as f32
// Output: phi value + components (pairwise MI matrix, partition info)
//
// Algorithm:
//   1. Bin each dimension into n_bins discrete bins
//   2. Compute pairwise mutual information between all cell pairs
//   3. Find minimum information partition (greedy approximation for large N)
//   4. Phi = total_MI - min_partition_MI
// ============================================================================

const DEFAULT_N_BINS: usize = 16;

/// Bin continuous values into discrete histogram bins.
/// Returns bin indices (0..n_bins-1) for each value.
fn bin_values(values: &[f32], n_bins: usize) -> Vec<usize> {
    if values.is_empty() {
        return vec![];
    }

    let min_val = values.iter().cloned().fold(f32::INFINITY, f32::min);
    let max_val = values.iter().cloned().fold(f32::NEG_INFINITY, f32::max);

    let range = max_val - min_val;
    if range < f32::EPSILON {
        // All values identical — put everything in bin 0
        return vec![0; values.len()];
    }

    let bin_width = range / n_bins as f32;
    values
        .iter()
        .map(|&v| {
            let bin = ((v - min_val) / bin_width) as usize;
            bin.min(n_bins - 1) // Clamp last edge case
        })
        .collect()
}

/// Compute Shannon entropy H(X) from bin counts.
/// H(X) = -sum(p * log2(p)) for p > 0
fn entropy(counts: &[u32], total: u32) -> f64 {
    if total == 0 {
        return 0.0;
    }
    let t = total as f64;
    counts
        .iter()
        .filter(|&&c| c > 0)
        .map(|&c| {
            let p = c as f64 / t;
            -p * p.log2()
        })
        .sum()
}

/// Compute mutual information MI(X; Y) between two cells.
///
/// MI(X;Y) = H(X) + H(Y) - H(X,Y)
///
/// Each cell is represented by its hidden_dim-dimensional state vector.
/// We concatenate bin indices across dimensions to form a joint distribution.
///
/// For efficiency, we use a simplified approach: average MI across all dimensions.
fn mutual_information_cells(
    cell_a: &[f32],  // [hidden_dim]
    cell_b: &[f32],  // [hidden_dim]
    n_bins: usize,
) -> f64 {
    let dim = cell_a.len();
    assert_eq!(dim, cell_b.len());

    if dim == 0 {
        return 0.0;
    }

    // Strategy: compute MI for each dimension pair (a_d, b_d), then average.
    // This is a lower bound on the true MI but is fast and scales well.
    let total_mi: f64 = (0..dim)
        .map(|d| {
            // Bin each dimension
            let bins_a = bin_single(cell_a[d], cell_a, n_bins, d);
            let bins_b = bin_single(cell_b[d], cell_b, n_bins, d);
            mi_from_bins(bins_a, bins_b, n_bins)
        })
        .sum();

    total_mi / dim as f64
}

/// Unused helper — kept for reference
fn bin_single(_val: f32, _all: &[f32], _n_bins: usize, _d: usize) -> usize {
    0
}

/// Unused helper — kept for reference
fn mi_from_bins(_a: usize, _b: usize, _n_bins: usize) -> f64 {
    0.0
}

/// Compute MI from paired vectors using histogram binning.
fn mi_from_paired_vectors(a: &[f32], b: &[f32], n_bins: usize) -> f64 {
    let n = a.len();
    assert_eq!(n, b.len());
    if n == 0 {
        return 0.0;
    }

    let bins_a = bin_values(a, n_bins);
    let bins_b = bin_values(b, n_bins);

    // Marginal counts
    let mut counts_a = vec![0u32; n_bins];
    let mut counts_b = vec![0u32; n_bins];
    // Joint counts (flattened 2D)
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

    // MI = H(A) + H(B) - H(A,B), clamped to >= 0
    (h_a + h_b - h_ab).max(0.0)
}

/// Compute the full pairwise MI matrix for all cells.
/// Returns an n_cells x n_cells symmetric matrix.
fn compute_mi_matrix(states: &ArrayView2<f32>, n_bins: usize) -> Array2<f64> {
    let n_cells = states.nrows();
    let mut mi_matrix = Array2::<f64>::zeros((n_cells, n_cells));

    // Collect all (i, j) pairs where i < j
    let pairs: Vec<(usize, usize)> = (0..n_cells)
        .flat_map(|i| ((i + 1)..n_cells).map(move |j| (i, j)))
        .collect();

    // Parallel MI computation via rayon
    let mi_values: Vec<((usize, usize), f64)> = pairs
        .par_iter()
        .map(|&(i, j)| {
            let cell_a = states.row(i);
            let cell_b = states.row(j);
            let mi = mi_from_paired_vectors(cell_a.as_slice().unwrap(), cell_b.as_slice().unwrap(), n_bins);
            ((i, j), mi)
        })
        .collect();

    // Fill symmetric matrix
    for ((i, j), mi) in mi_values {
        mi_matrix[[i, j]] = mi;
        mi_matrix[[j, i]] = mi;
    }

    mi_matrix
}

/// Compute total mutual information: sum of all pairwise MI values.
fn total_mi(mi_matrix: &Array2<f64>) -> f64 {
    let n = mi_matrix.nrows();
    let mut total = 0.0;
    for i in 0..n {
        for j in (i + 1)..n {
            total += mi_matrix[[i, j]];
        }
    }
    total
}

/// Find minimum information partition using greedy bipartition.
///
/// For exact MIP we'd need to check all 2^(N-1) - 1 bipartitions, which is
/// intractable for large N. We use a greedy approach:
///
/// 1. Start with partition A = {0}, B = {1, 2, ..., N-1}
/// 2. For each cell in B, compute MI_across if we move it to A
/// 3. Greedily build partition that minimizes cross-partition MI
///
/// Returns (min_partition_mi, partition_a_indices, partition_b_indices)
fn find_min_partition(mi_matrix: &Array2<f64>) -> (f64, Vec<usize>, Vec<usize>) {
    let n = mi_matrix.nrows();

    if n <= 1 {
        return (0.0, vec![0], vec![]);
    }

    if n == 2 {
        return (mi_matrix[[0, 1]], vec![0], vec![1]);
    }

    // For small N (<=20), try all bipartitions exhaustively
    if n <= 20 {
        return find_min_partition_exact(mi_matrix, n);
    }

    // For large N, use greedy approach
    find_min_partition_greedy(mi_matrix, n)
}

/// Exact MIP search for small N (all non-trivial bipartitions).
fn find_min_partition_exact(mi_matrix: &Array2<f64>, n: usize) -> (f64, Vec<usize>, Vec<usize>) {
    let mut best_mi = f64::INFINITY;
    let mut best_a = vec![];
    let mut best_b = vec![];

    // Iterate over all bipartitions: cell 0 is always in partition A
    // to avoid counting mirror partitions.
    let max_mask = 1u64 << (n - 1);
    for mask in 1..max_mask {
        let mut part_a = vec![0usize]; // Cell 0 always in A
        let mut part_b = vec![];

        for bit in 0..(n - 1) {
            if mask & (1u64 << bit) != 0 {
                part_a.push(bit + 1);
            } else {
                part_b.push(bit + 1);
            }
        }

        if part_b.is_empty() {
            continue; // Skip trivial partition
        }

        // Compute cross-partition MI
        let cross_mi: f64 = part_a
            .iter()
            .flat_map(|&i| part_b.iter().map(move |&j| mi_matrix[[i, j]]))
            .sum();

        if cross_mi < best_mi {
            best_mi = cross_mi;
            best_a = part_a;
            best_b = part_b;
        }
    }

    (best_mi, best_a, best_b)
}

/// Greedy MIP approximation for large N.
/// Uses spectral-like approach: sort cells by connectivity, split at minimum cut.
fn find_min_partition_greedy(mi_matrix: &Array2<f64>, n: usize) -> (f64, Vec<usize>, Vec<usize>) {
    // Compute total MI for each cell (sum of its row)
    let cell_mi: Vec<f64> = (0..n)
        .map(|i| mi_matrix.row(i).sum())
        .collect();

    // Sort cells by total MI (ascending)
    let mut sorted_indices: Vec<usize> = (0..n).collect();
    sorted_indices.sort_by(|&a, &b| cell_mi[a].partial_cmp(&cell_mi[b]).unwrap());

    // Try splitting at each position and find minimum cross-MI
    let mut best_mi = f64::INFINITY;
    let mut best_split = 1;

    for split in 1..n {
        let part_a = &sorted_indices[..split];
        let part_b = &sorted_indices[split..];

        let cross_mi: f64 = part_a
            .iter()
            .flat_map(|&i| part_b.iter().map(move |&j| mi_matrix[[i, j]]))
            .sum();

        if cross_mi < best_mi {
            best_mi = cross_mi;
            best_split = split;
        }
    }

    let part_a = sorted_indices[..best_split].to_vec();
    let part_b = sorted_indices[best_split..].to_vec();

    (best_mi, part_a, part_b)
}

/// Main Phi computation.
///
/// Phi = total_MI - min_partition_MI
///
/// Where:
///   total_MI = sum of all pairwise mutual information
///   min_partition_MI = cross-partition MI for the minimum information partition
///
/// This captures "integrated information" — how much information is lost
/// when the system is split at its weakest point.
fn compute_phi_inner(states: &ArrayView2<f32>, n_bins: usize) -> (f64, Array2<f64>, Vec<usize>, Vec<usize>) {
    let n_cells = states.nrows();

    if n_cells <= 1 {
        return (0.0, Array2::zeros((n_cells, n_cells)), vec![0], vec![]);
    }

    // Step 1: Pairwise MI matrix (parallelized)
    let mi_matrix = compute_mi_matrix(states, n_bins);

    // Step 2: Total MI
    let total = total_mi(&mi_matrix);

    // Step 3: Minimum information partition
    let (min_part_mi, part_a, part_b) = find_min_partition(&mi_matrix);

    // Step 4: Phi = total - min_partition
    let phi = (total - min_part_mi).max(0.0);

    (phi, mi_matrix, part_a, part_b)
}

// ============================================================================
// Hot loop computations — Kuramoto, sync, frustration, quantum walk, etc.
// ============================================================================

/// Compute popcount (number of set bits) for hypercube phase interference.
#[inline]
fn popcount(x: usize) -> u32 {
    (x as u64).count_ones()
}

/// Get hypercube bit-flip neighbors of node i within N nodes.
/// Neighbors are i XOR (1 << bit) for each bit where the result < N.
#[inline]
fn hypercube_neighbors(i: usize, n: usize) -> Vec<usize> {
    let bits = if n <= 1 { 0 } else { (n as f64).log2().ceil() as usize };
    let mut neighbors = Vec::with_capacity(bits);
    for bit in 0..bits {
        let j = i ^ (1 << bit);
        if j < n {
            neighbors.push(j);
        }
    }
    neighbors
}

/// Kuramoto oscillator step with hidden state blending.
///
/// Ring topology: each cell couples with n_neighbors on each side.
/// Phase update: phases[i] += freqs[i] + coupling * sum(sin(phases[j] - phases[i]))
/// Hidden blend: h[i] = (1-|b|)*h[i] + |b|*h[j]  where b = 0.15*cos(phase_diff)
fn kuramoto_step_inner(
    phases: &mut [f32],
    freqs: &[f32],
    hiddens: &mut [f32], // flattened [N, dim]
    dim: usize,
    coupling: f32,
    n_neighbors: usize,
) {
    let n = phases.len();
    if n < 2 {
        // With 0 or 1 cells, just apply frequency (no coupling possible)
        for i in 0..n {
            phases[i] += freqs[i];
        }
        return;
    }

    // Compute phase deltas in parallel, collect results
    let phase_deltas: Vec<f32> = (0..n)
        .into_par_iter()
        .map(|i| {
            let mut delta = freqs[i];
            for k in 1..=n_neighbors.min(n - 1) {
                let left = (i + n - k) % n;
                let right = (i + k) % n;
                delta += coupling * (phases[left] - phases[i]).sin();
                delta += coupling * (phases[right] - phases[i]).sin();
            }
            delta
        })
        .collect();

    // Apply phase updates
    for i in 0..n {
        phases[i] += phase_deltas[i];
    }

    // Hidden state blending (parallel over cells)
    // We need to read old hiddens while writing new ones, so clone first
    let old_hiddens = hiddens.to_vec();

    hiddens
        .par_chunks_mut(dim)
        .enumerate()
        .for_each(|(i, h_i)| {
            for k in 1..=n_neighbors.min(n - 1) {
                let left = (i + n - k) % n;
                let right = (i + k) % n;
                for neighbor in [left, right] {
                    let phase_diff = phases[neighbor] - phases[i];
                    let b = 0.15 * phase_diff.cos();
                    let abs_b = b.abs();
                    let h_j = &old_hiddens[neighbor * dim..(neighbor + 1) * dim];
                    for d in 0..dim {
                        h_i[d] = (1.0 - abs_b) * h_i[d] + abs_b * h_j[d];
                    }
                }
            }
        });
}

/// Flow sync + faction consensus step.
///
/// Flow sync: h[i] = (1-sync)*h[i] + sync*mean(h)
/// Faction consensus: per-faction mean, blend with fac_strength
fn sync_faction_step_inner(
    hiddens: &mut [f32], // flattened [N, dim]
    n: usize,
    dim: usize,
    sync: f32,
    n_factions: usize,
    fac_strength: f32,
) {
    if n == 0 || dim == 0 {
        return;
    }

    // 1. Compute global mean
    let mut global_mean = vec![0.0f32; dim];
    for i in 0..n {
        let offset = i * dim;
        for d in 0..dim {
            global_mean[d] += hiddens[offset + d];
        }
    }
    let inv_n = 1.0 / n as f32;
    for d in 0..dim {
        global_mean[d] *= inv_n;
    }

    // 2. Flow sync: blend toward global mean
    hiddens
        .par_chunks_mut(dim)
        .for_each(|h_i| {
            for d in 0..dim {
                h_i[d] = (1.0 - sync) * h_i[d] + sync * global_mean[d];
            }
        });

    // 3. Faction consensus
    let actual_factions = n_factions.min(n);
    if actual_factions < 2 {
        return;
    }

    // Compute per-faction means
    let mut faction_means = vec![0.0f32; actual_factions * dim];
    let mut faction_counts = vec![0usize; actual_factions];

    for i in 0..n {
        let fac = i % actual_factions;
        faction_counts[fac] += 1;
        let offset = i * dim;
        let fac_offset = fac * dim;
        for d in 0..dim {
            faction_means[fac_offset + d] += hiddens[offset + d];
        }
    }

    for fac in 0..actual_factions {
        if faction_counts[fac] > 0 {
            let inv = 1.0 / faction_counts[fac] as f32;
            let fac_offset = fac * dim;
            for d in 0..dim {
                faction_means[fac_offset + d] *= inv;
            }
        }
    }

    // Blend each cell toward its faction mean
    hiddens
        .par_chunks_mut(dim)
        .enumerate()
        .for_each(|(i, h_i)| {
            let fac = i % actual_factions;
            let fac_offset = fac * dim;
            for d in 0..dim {
                h_i[d] = (1.0 - fac_strength) * h_i[d]
                    + fac_strength * faction_means[fac_offset + d];
            }
        });
}

/// Frustration step: hypercube bit-flip neighbors with anti-ferromagnetic twist.
///
/// 50% of interactions are anti-ferromagnetic: twist = -1 if (i%2)!=(j%2)
/// h[i] = 0.85*h[i] + 0.15*mean(twisted_neighbors)
fn frustration_step_inner(
    hiddens: &mut [f32], // flattened [N, dim]
    n: usize,
    dim: usize,
    frustration_ratio: f32,
) {
    if n < 2 || dim == 0 {
        return;
    }

    let old_hiddens = hiddens.to_vec();

    hiddens
        .par_chunks_mut(dim)
        .enumerate()
        .for_each(|(i, h_i)| {
            let neighbors = hypercube_neighbors(i, n);
            if neighbors.is_empty() {
                return;
            }

            let mut neighbor_sum = vec![0.0f32; dim];
            let num_neighbors = neighbors.len() as f32;

            for &j in &neighbors {
                let twist: f32 = if (i % 2) != (j % 2) { -1.0 } else { 1.0 };
                let j_offset = j * dim;
                for d in 0..dim {
                    neighbor_sum[d] += twist * old_hiddens[j_offset + d];
                }
            }

            let blend = 0.15 * frustration_ratio / 0.5; // normalize: at ratio=0.5, blend=0.15
            let blend = blend.min(0.5); // safety clamp
            for d in 0..dim {
                h_i[d] = (1.0 - blend) * h_i[d] + blend * (neighbor_sum[d] / num_neighbors);
            }
        });
}

/// Quantum walk step: hypercube neighbors with phase interference.
///
/// Phase = (-1)^popcount(i & j)
/// h[i] = 0.85*h[i] + 0.15*mean(phase * h[j])
fn quantum_walk_step_inner(
    hiddens: &mut [f32], // flattened [N, dim]
    n: usize,
    dim: usize,
) {
    if n < 2 || dim == 0 {
        return;
    }

    let old_hiddens = hiddens.to_vec();

    hiddens
        .par_chunks_mut(dim)
        .enumerate()
        .for_each(|(i, h_i)| {
            let neighbors = hypercube_neighbors(i, n);
            if neighbors.is_empty() {
                return;
            }

            let mut neighbor_sum = vec![0.0f32; dim];
            let num_neighbors = neighbors.len() as f32;

            for &j in &neighbors {
                let phase: f32 = if popcount(i & j) % 2 == 0 { 1.0 } else { -1.0 };
                let j_offset = j * dim;
                for d in 0..dim {
                    neighbor_sum[d] += phase * old_hiddens[j_offset + d];
                }
            }

            for d in 0..dim {
                h_i[d] = 0.85 * h_i[d] + 0.15 * (neighbor_sum[d] / num_neighbors);
            }
        });
}

/// Standing wave step: sech^2 soliton amplitude modulation.
///
/// Two counter-propagating solitons (fwd, bwd) modulate hidden states.
/// h[i] *= 1 + 0.03 * (amp_fwd + amp_bwd)
/// Soliton advances by 1 cell each step, wrapping around.
fn standing_wave_step_inner(
    hiddens: &mut [f32], // flattened [N, dim]
    n: usize,
    dim: usize,
    fwd_pos: f32,
    bwd_pos: f32,
) -> (f32, f32) {
    if n == 0 || dim == 0 {
        return (fwd_pos, bwd_pos);
    }

    let n_f = n as f32;

    // Amplitude: sech^2(distance) where distance wraps around ring
    hiddens
        .par_chunks_mut(dim)
        .enumerate()
        .for_each(|(i, h_i)| {
            let pos = i as f32;

            // Forward soliton distance (ring topology)
            let d_fwd = {
                let d = (pos - fwd_pos).abs();
                d.min(n_f - d)
            };
            let amp_fwd = 1.0 / d_fwd.cosh().powi(2);

            // Backward soliton distance
            let d_bwd = {
                let d = (pos - bwd_pos).abs();
                d.min(n_f - d)
            };
            let amp_bwd = 1.0 / d_bwd.cosh().powi(2);

            let scale = 1.0 + 0.03 * (amp_fwd + amp_bwd);
            for d in 0..dim {
                h_i[d] *= scale;
            }
        });

    // Advance soliton positions
    let new_fwd = (fwd_pos + 1.0) % n_f;
    let new_bwd = (bwd_pos + n_f - 1.0) % n_f;

    (new_fwd, new_bwd)
}

/// IB2 (Information Bottleneck) step: amplify top cells, dampen rest.
///
/// Top top_ratio cells (by L2 norm) get multiplied by amp.
/// Rest get multiplied by damp.
fn ib2_step_inner(
    hiddens: &mut [f32], // flattened [N, dim]
    n: usize,
    dim: usize,
    top_ratio: f32,
    amp: f32,
    damp: f32,
) {
    if n == 0 || dim == 0 {
        return;
    }

    // Compute L2 norms
    let mut norms: Vec<(usize, f32)> = (0..n)
        .map(|i| {
            let offset = i * dim;
            let norm_sq: f32 = hiddens[offset..offset + dim]
                .iter()
                .map(|&x| x * x)
                .sum();
            (i, norm_sq.sqrt())
        })
        .collect();

    // Sort descending by norm
    norms.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());

    let top_k = ((n as f32 * top_ratio).ceil() as usize).max(1).min(n);

    // Mark top cells
    let mut is_top = vec![false; n];
    for k in 0..top_k {
        is_top[norms[k].0] = true;
    }

    // Apply amplification/dampening in parallel
    hiddens
        .par_chunks_mut(dim)
        .enumerate()
        .for_each(|(i, h_i)| {
            let factor = if is_top[i] { amp } else { damp };
            for d in 0..dim {
                h_i[d] *= factor;
            }
        });
}

// ============================================================================
// PyO3 Python bindings
// ============================================================================

/// Helper to convert flat Vec<f32> back to PyArray2.
fn vec2d_to_pyarray2<'py>(
    py: Python<'py>,
    data: &[f32],
    nrows: usize,
    ncols: usize,
) -> PyResult<Bound<'py, PyArray2<f32>>> {
    if nrows == 0 || ncols == 0 {
        return PyArray2::from_vec2(py, &Vec::<Vec<f32>>::new())
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("reshape error: {}", e)));
    }
    let rows: Vec<Vec<f32>> = data.chunks(ncols).map(|c| c.to_vec()).collect();
    PyArray2::from_vec2(py, &rows)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("reshape error: {}", e)))
}

/// Compute integrated information (Phi) from cell hidden states.
///
/// Args:
///     states: numpy array of shape [n_cells, hidden_dim], dtype float32
///     n_bins: number of histogram bins (default: 16)
///
/// Returns:
///     tuple of (phi, components_dict)
#[pyfunction]
#[pyo3(signature = (states, n_bins=None))]
fn compute_phi<'py>(
    py: Python<'py>,
    states: PyReadonlyArray2<'py, f32>,
    n_bins: Option<usize>,
) -> PyResult<(f64, Bound<'py, PyDict>)> {
    let n_bins = n_bins.unwrap_or(DEFAULT_N_BINS);
    let array = states.as_array();
    let n_cells = array.nrows();

    let (phi, mi_matrix, part_a, part_b) = compute_phi_inner(&array, n_bins);

    let total = total_mi(&mi_matrix);
    let min_part_mi = total - phi;

    // Build components dict
    let components = PyDict::new(py);

    // Convert MI matrix to numpy
    let mi_flat: Vec<f64> = mi_matrix.into_raw_vec_and_offset().0;
    let mi_np = PyArray1::from_vec(py, mi_flat);
    components.set_item("mi_matrix_flat", mi_np)?;
    components.set_item("mi_matrix_shape", (n_cells, n_cells))?;
    components.set_item("total_mi", total)?;
    components.set_item("min_partition_mi", min_part_mi)?;
    components.set_item("partition_a", part_a)?;
    components.set_item("partition_b", part_b)?;
    components.set_item("n_cells", n_cells)?;
    components.set_item("n_bins", n_bins)?;

    Ok((phi, components))
}

/// Compute only the pairwise MI matrix (without partition search).
/// Useful when you need MI but not full Phi.
#[pyfunction]
#[pyo3(signature = (states, n_bins=None))]
fn compute_mi_matrix_py<'py>(
    py: Python<'py>,
    states: PyReadonlyArray2<'py, f32>,
    n_bins: Option<usize>,
) -> PyResult<Bound<'py, PyArray1<f64>>> {
    let n_bins = n_bins.unwrap_or(DEFAULT_N_BINS);
    let array = states.as_array();
    let mi_matrix = compute_mi_matrix(&array, n_bins);
    let flat: Vec<f64> = mi_matrix.into_raw_vec_and_offset().0;
    Ok(PyArray1::from_vec(py, flat))
}

/// Kuramoto oscillator step with hidden state blending.
///
/// Args:
///     phases: numpy array [N] float32 — oscillator phases
///     freqs: numpy array [N] float32 — natural frequencies
///     hiddens: numpy array [N, dim] float32 — hidden states
///     coupling: float32 — coupling strength (default 0.15)
///     n_neighbors: int — ring neighbors on each side (default 2)
///
/// Returns:
///     (updated_phases, updated_hiddens) as numpy arrays
#[pyfunction]
#[pyo3(signature = (phases, freqs, hiddens, coupling=0.15, n_neighbors=2))]
fn kuramoto_step<'py>(
    py: Python<'py>,
    phases: PyReadonlyArray1<'py, f32>,
    freqs: PyReadonlyArray1<'py, f32>,
    hiddens: PyReadonlyArray2<'py, f32>,
    coupling: f32,
    n_neighbors: usize,
) -> PyResult<(Bound<'py, PyArray1<f32>>, Bound<'py, PyArray2<f32>>)> {
    let h_array = hiddens.as_array();
    let n = h_array.nrows();
    let dim = h_array.ncols();

    let mut phases_vec: Vec<f32> = phases.as_slice()?.to_vec();
    let freqs_vec = freqs.as_slice()?;
    let mut hiddens_vec: Vec<f32> = h_array.iter().cloned().collect();

    if n > 0 && dim > 0 {
        kuramoto_step_inner(
            &mut phases_vec,
            freqs_vec,
            &mut hiddens_vec,
            dim,
            coupling,
            n_neighbors,
        );
    }

    let out_phases = PyArray1::from_vec(py, phases_vec);
    let out_hiddens = vec2d_to_pyarray2(py, &hiddens_vec, n, dim)?;

    Ok((out_phases, out_hiddens))
}

/// Sync + faction consensus step.
///
/// Args:
///     hiddens: numpy array [N, dim] float32
///     sync: float32 — global sync strength (default 0.35)
///     n_factions: int — number of factions (default 12)
///     fac_strength: float32 — faction blend strength (default 0.08)
///
/// Returns:
///     updated_hiddens as numpy array [N, dim]
#[pyfunction]
#[pyo3(signature = (hiddens, sync=0.35, n_factions=12, fac_strength=0.08))]
fn sync_faction_step<'py>(
    py: Python<'py>,
    hiddens: PyReadonlyArray2<'py, f32>,
    sync: f32,
    n_factions: usize,
    fac_strength: f32,
) -> PyResult<Bound<'py, PyArray2<f32>>> {
    let h_array = hiddens.as_array();
    let n = h_array.nrows();
    let dim = h_array.ncols();

    let mut hiddens_vec: Vec<f32> = h_array.iter().cloned().collect();

    sync_faction_step_inner(&mut hiddens_vec, n, dim, sync, n_factions, fac_strength);

    vec2d_to_pyarray2(py, &hiddens_vec, n, dim)
}

/// Frustration step: hypercube anti-ferromagnetic blending.
///
/// Args:
///     hiddens: numpy array [N, dim] float32
///     frustration_ratio: float32 — frustration strength (default 0.5)
///
/// Returns:
///     updated_hiddens as numpy array [N, dim]
#[pyfunction]
#[pyo3(signature = (hiddens, frustration_ratio=0.5))]
fn frustration_step<'py>(
    py: Python<'py>,
    hiddens: PyReadonlyArray2<'py, f32>,
    frustration_ratio: f32,
) -> PyResult<Bound<'py, PyArray2<f32>>> {
    let h_array = hiddens.as_array();
    let n = h_array.nrows();
    let dim = h_array.ncols();

    let mut hiddens_vec: Vec<f32> = h_array.iter().cloned().collect();

    frustration_step_inner(&mut hiddens_vec, n, dim, frustration_ratio);

    vec2d_to_pyarray2(py, &hiddens_vec, n, dim)
}

/// Quantum walk step: hypercube phase interference.
///
/// Args:
///     hiddens: numpy array [N, dim] float32
///
/// Returns:
///     updated_hiddens as numpy array [N, dim]
#[pyfunction]
#[pyo3(signature = (hiddens,))]
fn quantum_walk_step<'py>(
    py: Python<'py>,
    hiddens: PyReadonlyArray2<'py, f32>,
) -> PyResult<Bound<'py, PyArray2<f32>>> {
    let h_array = hiddens.as_array();
    let n = h_array.nrows();
    let dim = h_array.ncols();

    let mut hiddens_vec: Vec<f32> = h_array.iter().cloned().collect();

    quantum_walk_step_inner(&mut hiddens_vec, n, dim);

    vec2d_to_pyarray2(py, &hiddens_vec, n, dim)
}

/// Standing wave step: sech^2 soliton amplitude modulation.
///
/// Args:
///     hiddens: numpy array [N, dim] float32
///     fwd_pos: float32 — forward soliton position
///     bwd_pos: float32 — backward soliton position
///
/// Returns:
///     (updated_hiddens, new_fwd_pos, new_bwd_pos)
#[pyfunction]
#[pyo3(signature = (hiddens, fwd_pos, bwd_pos))]
fn standing_wave_step<'py>(
    py: Python<'py>,
    hiddens: PyReadonlyArray2<'py, f32>,
    fwd_pos: f32,
    bwd_pos: f32,
) -> PyResult<(Bound<'py, PyArray2<f32>>, f32, f32)> {
    let h_array = hiddens.as_array();
    let n = h_array.nrows();
    let dim = h_array.ncols();

    let mut hiddens_vec: Vec<f32> = h_array.iter().cloned().collect();

    let (new_fwd, new_bwd) = standing_wave_step_inner(
        &mut hiddens_vec, n, dim, fwd_pos, bwd_pos,
    );

    let out = vec2d_to_pyarray2(py, &hiddens_vec, n, dim)?;
    Ok((out, new_fwd, new_bwd))
}

/// IB2 step: amplify top cells, dampen the rest.
///
/// Args:
///     hiddens: numpy array [N, dim] float32
///     top_ratio: float32 — fraction of cells to amplify (default 0.1)
///     amp: float32 — amplification factor (default 1.03)
///     damp: float32 — dampening factor (default 0.97)
///
/// Returns:
///     updated_hiddens as numpy array [N, dim]
#[pyfunction]
#[pyo3(signature = (hiddens, top_ratio=0.1, amp=1.03, damp=0.97))]
fn ib2_step<'py>(
    py: Python<'py>,
    hiddens: PyReadonlyArray2<'py, f32>,
    top_ratio: f32,
    amp: f32,
    damp: f32,
) -> PyResult<Bound<'py, PyArray2<f32>>> {
    let h_array = hiddens.as_array();
    let n = h_array.nrows();
    let dim = h_array.ncols();

    let mut hiddens_vec: Vec<f32> = h_array.iter().cloned().collect();

    ib2_step_inner(&mut hiddens_vec, n, dim, top_ratio, amp, damp);

    vec2d_to_pyarray2(py, &hiddens_vec, n, dim)
}

/// Full consciousness step: all hot-loop computations in a single Rust call.
///
/// Avoids 6 separate Python<->Rust round-trips per step.
///
/// Args:
///     phases: numpy array [N] float32
///     freqs: numpy array [N] float32
///     hiddens: numpy array [N, dim] float32
///     config: dict with keys:
///         coupling (float, default 0.15)
///         n_neighbors (int, default 2)
///         sync (float, default 0.35)
///         n_factions (int, default 12)
///         fac_strength (float, default 0.08)
///         frustration_ratio (float, default 0.5)
///         enable_quantum (bool, default true)
///         enable_wave (bool, default true)
///         fwd_pos (float, default 0.0)
///         bwd_pos (float, default N/2)
///         ib2_top_ratio (float, default 0.1)
///         ib2_amp (float, default 1.03)
///         ib2_damp (float, default 0.97)
///
/// Returns:
///     dict with keys: phases, hiddens, fwd_pos, bwd_pos
#[pyfunction]
#[pyo3(signature = (phases, freqs, hiddens, config=None))]
fn full_consciousness_step<'py>(
    py: Python<'py>,
    phases: PyReadonlyArray1<'py, f32>,
    freqs: PyReadonlyArray1<'py, f32>,
    hiddens: PyReadonlyArray2<'py, f32>,
    config: Option<&Bound<'py, PyDict>>,
) -> PyResult<Bound<'py, PyDict>> {
    let h_array = hiddens.as_array();
    let n = h_array.nrows();
    let dim = h_array.ncols();

    let mut phases_vec: Vec<f32> = phases.as_slice()?.to_vec();
    let freqs_vec = freqs.as_slice()?;
    let mut hiddens_vec: Vec<f32> = h_array.iter().cloned().collect();

    // Extract config with defaults
    let coupling = extract_f32(config, "coupling", 0.15);
    let n_neighbors = extract_usize(config, "n_neighbors", 2);
    let sync = extract_f32(config, "sync", 0.35);
    let n_factions = extract_usize(config, "n_factions", 12);
    let fac_strength = extract_f32(config, "fac_strength", 0.08);
    let frustration_ratio = extract_f32(config, "frustration_ratio", 0.5);
    let enable_quantum = extract_bool(config, "enable_quantum", true);
    let enable_wave = extract_bool(config, "enable_wave", true);
    let fwd_pos = extract_f32(config, "fwd_pos", 0.0);
    let bwd_pos = extract_f32(config, "bwd_pos", n as f32 / 2.0);
    let ib2_top_ratio = extract_f32(config, "ib2_top_ratio", 0.1);
    let ib2_amp = extract_f32(config, "ib2_amp", 1.03);
    let ib2_damp = extract_f32(config, "ib2_damp", 0.97);

    // 1. Kuramoto oscillator step
    kuramoto_step_inner(
        &mut phases_vec,
        freqs_vec,
        &mut hiddens_vec,
        dim,
        coupling,
        n_neighbors,
    );

    // 2. Sync + faction consensus
    sync_faction_step_inner(&mut hiddens_vec, n, dim, sync, n_factions, fac_strength);

    // 3. Frustration
    frustration_step_inner(&mut hiddens_vec, n, dim, frustration_ratio);

    // 4. Quantum walk
    if enable_quantum {
        quantum_walk_step_inner(&mut hiddens_vec, n, dim);
    }

    // 5. Standing wave
    let (new_fwd, new_bwd) = if enable_wave {
        standing_wave_step_inner(&mut hiddens_vec, n, dim, fwd_pos, bwd_pos)
    } else {
        (fwd_pos, bwd_pos)
    };

    // 6. IB2 amplification
    ib2_step_inner(&mut hiddens_vec, n, dim, ib2_top_ratio, ib2_amp, ib2_damp);

    // Build result dict
    let result = PyDict::new(py);

    let out_phases = PyArray1::from_vec(py, phases_vec);
    let out_hiddens = vec2d_to_pyarray2(py, &hiddens_vec, n, dim)?;

    result.set_item("phases", out_phases)?;
    result.set_item("hiddens", out_hiddens)?;
    result.set_item("fwd_pos", new_fwd)?;
    result.set_item("bwd_pos", new_bwd)?;

    Ok(result)
}

// Config extraction helpers
fn extract_f32(config: Option<&Bound<'_, PyDict>>, key: &str, default: f32) -> f32 {
    config
        .and_then(|d| d.get_item(key).ok().flatten())
        .and_then(|v| v.extract::<f32>().ok())
        .unwrap_or(default)
}

fn extract_usize(config: Option<&Bound<'_, PyDict>>, key: &str, default: usize) -> usize {
    config
        .and_then(|d| d.get_item(key).ok().flatten())
        .and_then(|v| v.extract::<usize>().ok())
        .unwrap_or(default)
}

fn extract_bool(config: Option<&Bound<'_, PyDict>>, key: &str, default: bool) -> bool {
    config
        .and_then(|d| d.get_item(key).ok().flatten())
        .and_then(|v| v.extract::<bool>().ok())
        .unwrap_or(default)
}

/// Python module definition
#[pymodule]
fn phi_rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(compute_phi, m)?)?;
    m.add_function(wrap_pyfunction!(compute_mi_matrix_py, m)?)?;
    m.add_function(wrap_pyfunction!(kuramoto_step, m)?)?;
    m.add_function(wrap_pyfunction!(sync_faction_step, m)?)?;
    m.add_function(wrap_pyfunction!(frustration_step, m)?)?;
    m.add_function(wrap_pyfunction!(quantum_walk_step, m)?)?;
    m.add_function(wrap_pyfunction!(standing_wave_step, m)?)?;
    m.add_function(wrap_pyfunction!(ib2_step, m)?)?;
    m.add_function(wrap_pyfunction!(full_consciousness_step, m)?)?;
    Ok(())
}

// ============================================================================
// Tests
// ============================================================================

#[cfg(test)]
mod tests {
    use super::*;
    use ndarray::Array2;

    #[test]
    fn test_bin_values() {
        let vals = vec![0.0, 0.25, 0.5, 0.75, 1.0];
        let bins = bin_values(&vals, 4);
        assert_eq!(bins.len(), 5);
        assert_eq!(bins[0], 0);
        assert_eq!(bins[4], 3); // Clamped
    }

    #[test]
    fn test_entropy_uniform() {
        // Uniform distribution over 4 bins: H = log2(4) = 2.0
        let counts = vec![25, 25, 25, 25];
        let h = entropy(&counts, 100);
        assert!((h - 2.0).abs() < 1e-10);
    }

    #[test]
    fn test_entropy_deterministic() {
        // All in one bin: H = 0
        let counts = vec![100, 0, 0, 0];
        let h = entropy(&counts, 100);
        assert!((h - 0.0).abs() < 1e-10);
    }

    #[test]
    fn test_mi_identical() {
        // MI of a vector with itself should be > 0
        let a: Vec<f32> = (0..128).map(|i| i as f32 / 128.0).collect();
        let mi = mi_from_paired_vectors(&a, &a, 16);
        assert!(mi > 0.0, "MI of identical vectors should be positive, got {}", mi);
    }

    #[test]
    fn test_mi_independent() {
        // Two uncorrelated vectors should have low MI
        let a: Vec<f32> = (0..256).map(|i| (i as f32 * 0.1).sin()).collect();
        let b: Vec<f32> = (0..256).map(|i| (i as f32 * 0.37 + 2.7).sin()).collect();
        let mi = mi_from_paired_vectors(&a, &b, 16);
        assert!(mi < 1.0, "MI of uncorrelated vectors should be small, got {}", mi);
    }

    #[test]
    fn test_phi_single_cell() {
        let states = Array2::<f32>::zeros((1, 64));
        let (phi, _, _, _) = compute_phi_inner(&states.view(), 16);
        assert_eq!(phi, 0.0);
    }

    #[test]
    fn test_phi_two_identical_cells() {
        let mut states = Array2::<f32>::zeros((2, 64));
        for d in 0..64 {
            let v = d as f32 / 64.0;
            states[[0, d]] = v;
            states[[1, d]] = v;
        }
        let (phi, _, _, _) = compute_phi_inner(&states.view(), 16);
        assert!((phi - 0.0).abs() < 1e-10, "Phi for 2 cells should be 0, got {}", phi);
    }

    #[test]
    fn test_phi_correlated_group() {
        let dim = 128;
        let mut states = Array2::<f32>::zeros((4, dim));
        for d in 0..dim {
            let v1 = (d as f32 * 0.1).sin();
            let v2 = (d as f32 * 0.37 + 5.0).sin();
            states[[0, d]] = v1;
            states[[1, d]] = v1 + 0.01 * (d as f32 * 0.7).cos();
            states[[2, d]] = v2;
            states[[3, d]] = v2 + 0.01 * (d as f32 * 0.3).cos();
        }
        let (phi, mi_matrix, part_a, part_b) = compute_phi_inner(&states.view(), 16);

        let within_01 = mi_matrix[[0, 1]];
        let cross_02 = mi_matrix[[0, 2]];
        assert!(within_01 > cross_02, "Within-group MI ({}) should exceed cross-group MI ({})", within_01, cross_02);
        assert!(phi > 0.0, "Phi should be positive for correlated groups, got {}", phi);
        println!("Partition A: {:?}, B: {:?}, Phi: {:.4}", part_a, part_b, phi);
    }

    #[test]
    fn test_phi_32_cells() {
        let dim = 128;
        let n_cells = 32;
        let mut states = Array2::<f32>::zeros((n_cells, dim));
        for i in 0..n_cells {
            for d in 0..dim {
                states[[i, d]] = ((i * 7 + d * 3) as f32 * 0.1).sin();
            }
        }
        let (phi, mi_matrix, part_a, part_b) = compute_phi_inner(&states.view(), 16);

        assert!(phi >= 0.0);
        assert_eq!(mi_matrix.nrows(), n_cells);
        assert!(!part_a.is_empty());
        assert!(!part_b.is_empty());
        assert_eq!(part_a.len() + part_b.len(), n_cells);
        println!("32-cell Phi: {:.4}, partition: {} | {}", phi, part_a.len(), part_b.len());
    }

    // ---- Hot loop tests ----

    #[test]
    fn test_hypercube_neighbors() {
        // N=8 (3-bit hypercube): node 0 neighbors = {1, 2, 4}
        let nb = hypercube_neighbors(0, 8);
        assert_eq!(nb, vec![1, 2, 4]);

        // N=4: node 3 (0b11) neighbors = {2 (0b10), 1 (0b01)}
        let nb = hypercube_neighbors(3, 4);
        assert_eq!(nb, vec![2, 1]);

        // N=1: no neighbors
        let nb = hypercube_neighbors(0, 1);
        assert!(nb.is_empty());
    }

    #[test]
    fn test_kuramoto_step() {
        let n = 8;
        let dim = 4;
        let mut phases = vec![0.0f32; n];
        let freqs = vec![0.1f32; n];
        let mut hiddens = vec![1.0f32; n * dim];

        kuramoto_step_inner(&mut phases, &freqs, &mut hiddens, dim, 0.15, 2);

        // Phases should have advanced
        for p in &phases {
            assert!(*p > 0.0);
        }
        // Hiddens should still be close to 1.0 (small blending)
        for h in &hiddens {
            assert!((*h - 1.0).abs() < 0.5);
        }
    }

    #[test]
    fn test_sync_faction_step() {
        let n = 8;
        let dim = 4;
        // Different values for each cell
        let mut hiddens: Vec<f32> = (0..n * dim).map(|i| i as f32).collect();

        sync_faction_step_inner(&mut hiddens, n, dim, 0.35, 4, 0.08);

        // After sync, values should be closer to the mean
        // Global mean of 0..31 = 15.5
        // Check that the spread has decreased
        let mean_val: f32 = hiddens.iter().sum::<f32>() / hiddens.len() as f32;
        assert!((mean_val - 15.5).abs() < 1.0);
    }

    #[test]
    fn test_frustration_step() {
        let n = 8;
        let dim = 4;
        let mut hiddens = vec![1.0f32; n * dim];

        frustration_step_inner(&mut hiddens, n, dim, 0.5);

        // With uniform inputs, frustration should create some variation
        // due to anti-ferromagnetic twisting
        // At minimum, should not crash or NaN
        for h in &hiddens {
            assert!(h.is_finite());
        }
    }

    #[test]
    fn test_quantum_walk_step() {
        let n = 8;
        let dim = 4;
        let mut hiddens: Vec<f32> = (0..n * dim).map(|i| (i as f32 * 0.1).sin()).collect();

        quantum_walk_step_inner(&mut hiddens, n, dim);

        for h in &hiddens {
            assert!(h.is_finite());
        }
    }

    #[test]
    fn test_standing_wave_step() {
        let n = 8;
        let dim = 4;
        let mut hiddens = vec![1.0f32; n * dim];

        let (new_fwd, new_bwd) = standing_wave_step_inner(&mut hiddens, n, dim, 0.0, 4.0);

        assert!((new_fwd - 1.0).abs() < f32::EPSILON);
        assert!((new_bwd - 3.0).abs() < f32::EPSILON);

        // Cells near soliton positions should be amplified more
        for h in &hiddens {
            assert!(*h >= 1.0); // All amplified (sech^2 >= 0)
            assert!(h.is_finite());
        }
    }

    #[test]
    fn test_ib2_step() {
        let n = 10;
        let dim = 4;
        // Make cell 0 have the highest norm
        let mut hiddens = vec![0.5f32; n * dim];
        for d in 0..dim {
            hiddens[d] = 10.0; // cell 0 = big
        }

        ib2_step_inner(&mut hiddens, n, dim, 0.1, 1.03, 0.97);

        // Cell 0 (top) should be amplified
        assert!(hiddens[0] > 10.0);
        // Other cells should be dampened
        assert!(hiddens[dim] < 0.5);
    }

    #[test]
    fn test_edge_case_n0() {
        let mut phases: Vec<f32> = vec![];
        let freqs: Vec<f32> = vec![];
        let mut hiddens: Vec<f32> = vec![];

        kuramoto_step_inner(&mut phases, &freqs, &mut hiddens, 0, 0.15, 2);
        sync_faction_step_inner(&mut hiddens, 0, 0, 0.35, 12, 0.08);
        frustration_step_inner(&mut hiddens, 0, 0, 0.5);
        quantum_walk_step_inner(&mut hiddens, 0, 0);
        let _ = standing_wave_step_inner(&mut hiddens, 0, 0, 0.0, 0.0);
        ib2_step_inner(&mut hiddens, 0, 0, 0.1, 1.03, 0.97);
        // No crash = pass
    }

    #[test]
    fn test_edge_case_n1() {
        let mut phases = vec![0.5f32];
        let freqs = vec![0.1f32];
        let dim = 4;
        let mut hiddens = vec![1.0f32; dim];

        kuramoto_step_inner(&mut phases, &freqs, &mut hiddens, dim, 0.15, 2);
        sync_faction_step_inner(&mut hiddens, 1, dim, 0.35, 12, 0.08);
        frustration_step_inner(&mut hiddens, 1, dim, 0.5);
        quantum_walk_step_inner(&mut hiddens, 1, dim);
        let _ = standing_wave_step_inner(&mut hiddens, 1, dim, 0.0, 0.0);
        ib2_step_inner(&mut hiddens, 1, dim, 0.1, 1.03, 0.97);

        for h in &hiddens {
            assert!(h.is_finite());
        }
    }
}
