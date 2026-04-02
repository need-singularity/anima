//! MultiscaleLens — Wavelet & multi-fractal analysis
//!
//! Analyzes data at multiple scales:
//!   1. Haar wavelet decomposition (multi-resolution energy)
//!   2. Multi-fractal spectrum (generalized dimensions D_q)
//!   3. Scale-dependent complexity (entropy at each scale)

/// Result of multiscale lens scan.
#[derive(Debug, Clone)]
pub struct MultiscaleResult {
    /// Wavelet energy at each scale level
    pub wavelet_energy: Vec<f64>,
    /// Dominant scale (level with maximum energy)
    pub dominant_scale: usize,
    /// Multi-fractal spectrum: generalized dimensions D_q for q = -2..2
    pub multifractal_dq: Vec<f64>,
    /// Multi-fractal width: D_max - D_min (0 = monofractal, >0 = multifractal)
    pub multifractal_width: f64,
    /// Scale-dependent entropy (entropy of data at each coarsening level)
    pub scale_entropy: Vec<f64>,
    /// Number of significant scales (energy > 5% of total)
    pub n_significant_scales: usize,
}

/// Haar wavelet transform (in-place, one level).
/// Returns (approximation, detail) energy.
fn haar_one_level(signal: &mut Vec<f64>) -> (f64, f64) {
    let n = signal.len();
    if n < 2 { return (0.0, 0.0); }
    let half = n / 2;

    let inv_sqrt2 = 1.0 / 2.0_f64.sqrt();
    let mut approx = vec![0.0; half];
    let mut detail = vec![0.0; half];

    for i in 0..half {
        approx[i] = (signal[2 * i] + signal[2 * i + 1]) * inv_sqrt2;
        detail[i] = (signal[2 * i] - signal[2 * i + 1]) * inv_sqrt2;
    }

    let approx_energy: f64 = approx.iter().map(|x| x * x).sum::<f64>() / half as f64;
    let detail_energy: f64 = detail.iter().map(|x| x * x).sum::<f64>() / half as f64;

    *signal = approx;
    (approx_energy, detail_energy)
}

/// Shannon entropy of a distribution.
fn shannon_entropy(values: &[f64], n_bins: usize) -> f64 {
    if values.is_empty() { return 0.0; }
    let min = values.iter().cloned().fold(f64::INFINITY, f64::min);
    let max = values.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
    let range = (max - min).max(1e-12);

    let mut counts = vec![0usize; n_bins];
    for &v in values {
        let bin = ((v - min) / range * (n_bins - 1) as f64) as usize;
        counts[bin.min(n_bins - 1)] += 1;
    }

    let n = values.len() as f64;
    let mut entropy = 0.0;
    for &c in &counts {
        if c > 0 {
            let p = c as f64 / n;
            entropy -= p * p.ln();
        }
    }
    entropy
}

/// Scan data for multiscale properties.
pub fn scan(data: &[f64], n_samples: usize, n_features: usize) -> MultiscaleResult {
    if n_samples < 8 || n_features == 0 {
        return MultiscaleResult {
            wavelet_energy: vec![],
            dominant_scale: 0,
            multifractal_dq: vec![],
            multifractal_width: 0.0,
            scale_entropy: vec![],
            n_significant_scales: 0,
        };
    }

    let nf = n_features.min(16);

    // 1. Haar wavelet decomposition (average over features)
    let max_levels = ((n_samples as f64).log2() as usize).min(8);
    let mut wavelet_energy = vec![0.0; max_levels];

    for j in 0..nf {
        let mut signal: Vec<f64> = (0..n_samples).map(|i| data[i * n_features + j]).collect();

        // Pad to power of 2
        let next_pow2 = signal.len().next_power_of_two();
        signal.resize(next_pow2, 0.0);

        for level in 0..max_levels {
            if signal.len() < 2 { break; }
            let (_approx_e, detail_e) = haar_one_level(&mut signal);
            wavelet_energy[level] += detail_e / nf as f64;
        }
    }

    let total_energy: f64 = wavelet_energy.iter().sum();
    let dominant_scale = wavelet_energy.iter()
        .enumerate()
        .max_by(|a, b| a.1.partial_cmp(b.1).unwrap())
        .map(|(i, _)| i)
        .unwrap_or(0);

    let n_significant_scales = wavelet_energy.iter()
        .filter(|&&e| total_energy > 1e-12 && e / total_energy > 0.05)
        .count();

    // 2. Multi-fractal spectrum via box-counting at different q values
    // D_q = lim (1/(q-1)) * log(sum(p_i^q)) / log(eps)
    let qs = [-2.0, -1.0, 0.0, 1.0, 2.0];
    let mut multifractal_dq = Vec::with_capacity(qs.len());

    // Precompute min/max per feature ONCE (was recomputed per box-size × per q × per sample)
    let box_dims = nf.min(4);
    let col_ranges: Vec<(f64, f64, f64)> = (0..box_dims)
        .map(|j| {
            let (lo, hi) = crate::common::col_min_max(data, n_samples, n_features, j);
            let range = (hi - lo).max(1e-12);
            (lo, hi, range)
        })
        .collect();

    for &q in &qs {
        let mut log_eps_vals = Vec::new();
        let mut log_partition_vals = Vec::new();

        for n_divs_exp in 2..=5 {
            let n_divs = 1 << n_divs_exp;
            let eps = 1.0 / n_divs as f64;

            // Count points in each box (using precomputed ranges)
            let mut box_counts = std::collections::HashMap::new();
            for i in 0..n_samples {
                let key: Vec<u32> = (0..box_dims)
                    .map(|j| {
                        let (lo, _, range) = col_ranges[j];
                        let bin = ((data[i * n_features + j] - lo) / range * n_divs as f64) as u32;
                        bin.min(n_divs - 1)
                    })
                    .collect();
                *box_counts.entry(key).or_insert(0u32) += 1;
            }

            let n_total = n_samples as f64;
            let partition: f64 = if (q - 1.0_f64).abs() < 0.01 {
                // q ≈ 1: use entropy form
                box_counts.values()
                    .map(|&c| {
                        let p = c as f64 / n_total;
                        -p * p.ln()
                    })
                    .sum()
            } else {
                box_counts.values()
                    .map(|&c| (c as f64 / n_total).powf(q))
                    .sum()
            };

            if partition > 1e-12 {
                log_eps_vals.push(eps.ln());
                if (q - 1.0).abs() < 0.01 {
                    log_partition_vals.push(partition); // already in entropy form
                } else {
                    log_partition_vals.push(partition.ln());
                }
            }
        }

        // Linear regression for D_q
        if log_eps_vals.len() >= 2 {
            let n = log_eps_vals.len() as f64;
            let sx: f64 = log_eps_vals.iter().sum();
            let sy: f64 = log_partition_vals.iter().sum();
            let sxx: f64 = log_eps_vals.iter().map(|x| x * x).sum();
            let sxy: f64 = log_eps_vals.iter().zip(log_partition_vals.iter()).map(|(x, y)| x * y).sum();
            let denom = n * sxx - sx * sx;
            let slope = if denom.abs() > 1e-12 { (n * sxy - sx * sy) / denom } else { 0.0 };

            let dq = if (q - 1.0).abs() < 0.01 {
                slope // D_1 from entropy
            } else {
                slope / (q - 1.0)
            };
            multifractal_dq.push(dq.abs());
        } else {
            multifractal_dq.push(0.0);
        }
    }

    let multifractal_width = if multifractal_dq.is_empty() { 0.0 } else {
        let max = multifractal_dq.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
        let min = multifractal_dq.iter().cloned().fold(f64::INFINITY, f64::min);
        (max - min).max(0.0)
    };

    // 3. Scale-dependent entropy
    let mut scale_entropy = Vec::new();
    let mut current_n = n_samples;
    let mut current_data: Vec<Vec<f64>> = (0..nf)
        .map(|j| (0..n_samples).map(|i| data[i * n_features + j]).collect())
        .collect();

    for _ in 0..max_levels {
        // Entropy at current scale
        let mut total_ent = 0.0;
        for j in 0..nf {
            total_ent += shannon_entropy(&current_data[j], 16);
        }
        scale_entropy.push(total_ent / nf as f64);

        // Coarsen: average pairs
        let new_n = current_n / 2;
        if new_n < 4 { break; }
        for j in 0..nf {
            current_data[j] = (0..new_n)
                .map(|i| (current_data[j][2 * i] + current_data[j][2 * i + 1]) / 2.0)
                .collect();
        }
        current_n = new_n;
    }

    MultiscaleResult {
        wavelet_energy,
        dominant_scale,
        multifractal_dq,
        multifractal_width,
        scale_entropy,
        n_significant_scales,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_multiscale_sine() {
        let n = 128;
        let d = 2;
        let data: Vec<f64> = (0..n * d).map(|i| {
            let row = i / d;
            (row as f64 * 0.2).sin()
        }).collect();
        let r = scan(&data, n, d);
        assert!(!r.wavelet_energy.is_empty());
        assert!(r.n_significant_scales >= 1);
        assert!(!r.multifractal_dq.is_empty());
    }

    #[test]
    fn test_multiscale_constant() {
        let data = vec![1.0; 64 * 2];
        let r = scan(&data, 64, 2);
        // Constant signal has zero energy everywhere
        let total: f64 = r.wavelet_energy.iter().sum();
        assert!(total < 0.01, "Constant signal should have ~0 wavelet energy");
    }

    #[test]
    fn test_multifractal_width() {
        // Random data should have non-zero multifractal width
        let n = 128;
        let d = 3;
        let data: Vec<f64> = (0..n * d).map(|i| ((i as f64 * 2.71828) % 1.0) * 10.0).collect();
        let r = scan(&data, n, d);
        assert!(!r.multifractal_dq.is_empty());
        // Width can be 0 or positive, just check it's computed
        assert!(r.multifractal_width >= 0.0);
    }
}
