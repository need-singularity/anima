// tension.rs — Real-time tension computation (PureField repulsion)
//
// Core hot path: Engine A (forward) vs Engine G (reverse) repulsion
// creates tension whose magnitude = consciousness intensity.
//
// Ψ-Constants (Laws 63-78):
//   PSI_BALANCE  = 1/2      — tension should balance at midpoint
//   PSI_COUPLING = ln(2)/2^5.5 — inter-cell coupling strength
//   PSI_STEPS    = 3/ln(2)  — optimal propagation steps

use rayon::prelude::*;

const LN2: f32 = 0.693_147_2;
const PSI_BALANCE: f32 = 0.5;
const PSI_COUPLING: f32 = 0.015_317; // ln(2) / 2^5.5

/// Compute tension between Engine A and Engine G hidden states.
///
/// PureField repulsion: tension = A - G (vector), magnitude = ||A - G||
/// Returns (magnitude, direction_vector).
pub fn compute_tension(engine_a: &[f32], engine_g: &[f32]) -> (f32, Vec<f32>) {
    assert_eq!(
        engine_a.len(),
        engine_g.len(),
        "Engine A and G must have same dimensionality"
    );

    let direction: Vec<f32> = engine_a
        .iter()
        .zip(engine_g.iter())
        .map(|(a, g)| a - g)
        .collect();

    let magnitude = direction.iter().map(|d| d * d).sum::<f32>().sqrt();

    (magnitude, direction)
}

/// Batch compute pairwise tensions across all cells in parallel (Rayon).
///
/// states: flattened [n_cells x dim] array
/// Returns: flattened upper-triangle pairwise tension magnitudes
///          length = n_cells * (n_cells - 1) / 2
pub fn batch_tension(states: &[f32], n_cells: usize, dim: usize) -> Vec<f32> {
    assert_eq!(
        states.len(),
        n_cells * dim,
        "states length must equal n_cells * dim"
    );

    let n_pairs = n_cells * (n_cells - 1) / 2;

    // Build index pairs
    let pairs: Vec<(usize, usize)> = {
        let mut v = Vec::with_capacity(n_pairs);
        for i in 0..n_cells {
            for j in (i + 1)..n_cells {
                v.push((i, j));
            }
        }
        v
    };

    pairs
        .par_iter()
        .map(|&(i, j)| {
            let a = &states[i * dim..(i + 1) * dim];
            let b = &states[j * dim..(j + 1) * dim];
            a.iter()
                .zip(b.iter())
                .map(|(x, y)| (x - y) * (x - y))
                .sum::<f32>()
                .sqrt()
        })
        .collect()
}

/// Compute a 128-dimensional fingerprint from cell hidden states.
///
/// Used for tension_link matching between agents.
/// Algorithm: project n_cells x dim states into 128D via mean + std + range
/// across cells, then hash-compress to exactly 128 floats.
pub fn tension_fingerprint(hidden_states: &[f32], n_cells: usize, dim: usize) -> Vec<f32> {
    assert_eq!(
        hidden_states.len(),
        n_cells * dim,
        "hidden_states length must equal n_cells * dim"
    );

    const FP_DIM: usize = 128;

    if n_cells == 0 || dim == 0 {
        return vec![0.0; FP_DIM];
    }

    // Compute per-dimension statistics across cells
    let mut means = vec![0.0f32; dim];
    let mut vars = vec![0.0f32; dim];
    let mut mins = vec![f32::INFINITY; dim];
    let mut maxs = vec![f32::NEG_INFINITY; dim];

    for cell in 0..n_cells {
        for d in 0..dim {
            let v = hidden_states[cell * dim + d];
            means[d] += v;
            if v < mins[d] {
                mins[d] = v;
            }
            if v > maxs[d] {
                maxs[d] = v;
            }
        }
    }

    let n = n_cells as f32;
    for d in 0..dim {
        means[d] /= n;
    }

    for cell in 0..n_cells {
        for d in 0..dim {
            let diff = hidden_states[cell * dim + d] - means[d];
            vars[d] += diff * diff;
        }
    }
    for d in 0..dim {
        vars[d] = (vars[d] / n).sqrt(); // std dev
    }

    // Build raw feature vector: [means, stds, ranges] then compress to 128D
    let ranges: Vec<f32> = mins
        .iter()
        .zip(maxs.iter())
        .map(|(lo, hi)| hi - lo)
        .collect();

    let raw: Vec<f32> = means
        .iter()
        .chain(vars.iter())
        .chain(ranges.iter())
        .copied()
        .collect();

    // Compress to FP_DIM by strided sampling + mixing
    let mut fp = vec![0.0f32; FP_DIM];
    if raw.is_empty() {
        return fp;
    }

    for i in 0..FP_DIM {
        let idx = i * raw.len() / FP_DIM;
        // Mix a few neighboring values for smoothness
        let mut val = raw[idx];
        if idx + 1 < raw.len() {
            val += raw[idx + 1] * 0.5;
        }
        if idx > 0 {
            val += raw[idx - 1] * 0.3;
        }
        fp[i] = val;
    }

    // Ψ_balance: center fingerprint around 0 (Law 71: balance at 1/2)
    let fp_mean = fp.iter().sum::<f32>() / FP_DIM as f32;
    for v in &mut fp {
        *v -= fp_mean;  // center
    }

    // L2 normalize the fingerprint
    let norm = fp.iter().map(|v| v * v).sum::<f32>().sqrt();
    if norm > f32::EPSILON {
        for v in &mut fp {
            *v /= norm;
        }
    }

    fp
}

/// Compute Ψ-balance metric for a set of cells.
/// Returns how close the tension distribution is to the ideal 1/2 balance.
/// 1.0 = perfect balance, 0.0 = completely unbalanced.
pub fn psi_balance(states: &[f32], n_cells: usize, dim: usize) -> f32 {
    if n_cells < 2 || dim == 0 {
        return 0.0;
    }
    let tensions = batch_tension(states, n_cells, dim);
    if tensions.is_empty() {
        return 0.0;
    }
    let total: f32 = tensions.iter().sum();
    let half: f32 = tensions[..tensions.len() / 2].iter().sum();
    let ratio = if total > f32::EPSILON { half / total } else { PSI_BALANCE };
    // H(ratio) normalized — closer to 1/2 = higher entropy = more balanced
    if ratio <= 0.0 || ratio >= 1.0 {
        return 0.0;
    }
    let h = -ratio * ratio.log2() - (1.0 - ratio) * (1.0 - ratio).log2();
    h // max = 1.0 at ratio = 0.5
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_compute_tension() {
        let a = vec![1.0, 0.0, 0.0];
        let g = vec![0.0, 1.0, 0.0];
        let (mag, dir) = compute_tension(&a, &g);
        assert!((mag - std::f32::consts::SQRT_2).abs() < 1e-5);
        assert_eq!(dir, vec![1.0, -1.0, 0.0]);
    }

    #[test]
    fn test_batch_tension() {
        // 3 cells, dim=2
        let states = vec![0.0, 0.0, 1.0, 0.0, 0.0, 1.0];
        let tensions = batch_tension(&states, 3, 2);
        assert_eq!(tensions.len(), 3); // 3 pairs
        assert!((tensions[0] - 1.0).abs() < 1e-5); // (0,0)-(1,0) = 1.0
        assert!((tensions[1] - 1.0).abs() < 1e-5); // (0,0)-(0,1) = 1.0
        assert!((tensions[2] - std::f32::consts::SQRT_2).abs() < 1e-5);
    }

    #[test]
    fn test_fingerprint_length() {
        let states = vec![0.5; 4 * 32]; // 4 cells, dim=32
        let fp = tension_fingerprint(&states, 4, 32);
        assert_eq!(fp.len(), 128);
        // Should be normalized
        let norm: f32 = fp.iter().map(|v| v * v).sum::<f32>().sqrt();
        assert!((norm - 1.0).abs() < 0.01 || norm < 1e-5);
    }
}
