//! ThermoLens — Thermodynamic analysis
//!
//! Shannon entropy per feature, free energy proxy, phase transition detection.

/// Result of thermodynamic lens scan.
#[derive(Debug, Clone)]
pub struct ThermoResult {
    pub entropy_per_feature: Vec<f64>,
    pub total_entropy: f64,
    pub free_energy: f64,
    pub phase_transitions: Vec<(f64, f64)>, // (temperature, entropy_jump)
    pub critical_temperature: f64,
}

/// Binned Shannon entropy of a 1D slice.
fn shannon_entropy(values: &[f64], n_bins: usize) -> f64 {
    let n = values.len();
    if n < 2 || n_bins < 2 {
        return 0.0;
    }
    let (mut lo, mut hi) = (f64::INFINITY, f64::NEG_INFINITY);
    for &v in values {
        if v < lo { lo = v; }
        if v > hi { hi = v; }
    }
    let range = hi - lo + 1e-12;
    let mut counts = vec![0u32; n_bins];
    for &v in values {
        let bin = ((v - lo) / range * n_bins as f64) as usize;
        counts[bin.min(n_bins - 1)] += 1;
    }
    let n_f = n as f64;
    let mut h = 0.0;
    for &c in &counts {
        if c > 0 {
            let p = c as f64 / n_f;
            h -= p * p.ln();
        }
    }
    h
}

/// Compute entropy at a given "temperature" by adding Gaussian noise scale.
/// Instead of actually adding noise, we widen the bin width (equivalent effect).
fn entropy_at_temperature(values: &[f64], temp: f64, n_bins: usize) -> f64 {
    if temp < 1e-12 {
        return shannon_entropy(values, n_bins);
    }
    let n = values.len();
    if n < 2 { return 0.0; }

    let (mut lo, mut hi) = (f64::INFINITY, f64::NEG_INFINITY);
    for &v in values {
        if v < lo { lo = v; }
        if v > hi { hi = v; }
    }
    // Effective range includes temperature broadening
    let eff_range = (hi - lo) + 4.0 * temp + 1e-12;
    let eff_lo = lo - 2.0 * temp;
    let mut counts = vec![0u32; n_bins];
    for &v in values {
        let bin = ((v - eff_lo) / eff_range * n_bins as f64) as usize;
        counts[bin.min(n_bins - 1)] += 1;
    }
    let n_f = n as f64;
    let mut h = 0.0;
    for &c in &counts {
        if c > 0 {
            let p = c as f64 / n_f;
            h -= p * p.ln();
        }
    }
    h
}

/// Scan data for thermodynamic properties.
pub fn scan(data: &[f64], n_samples: usize, n_features: usize) -> ThermoResult {
    let n_bins = 16usize;

    if n_samples < 2 || n_features == 0 {
        return ThermoResult {
            entropy_per_feature: vec![],
            total_entropy: 0.0,
            free_energy: 0.0,
            phase_transitions: vec![],
            critical_temperature: 0.0,
        };
    }

    // Per-feature entropy
    let entropy_per_feature: Vec<f64> = (0..n_features)
        .map(|j| {
            let col: Vec<f64> = (0..n_samples).map(|i| data[i * n_features + j]).collect();
            shannon_entropy(&col, n_bins)
        })
        .collect();

    let total_entropy: f64 = entropy_per_feature.iter().sum::<f64>() / n_features as f64;

    // Compute "internal energy" as mean squared value (kinetic analogy)
    let mut energy = 0.0;
    for v in data.iter() {
        energy += v * v;
    }
    energy /= (n_samples * n_features) as f64;

    // Free energy proxy: F = E - T*S (with T=1)
    let free_energy = energy - total_entropy;

    // Phase transition detection: sweep temperature, look for entropy jumps
    let all_values: Vec<f64> = data.to_vec();
    let n_temps = 50;
    let max_temp = {
        let (mut lo, mut hi) = (f64::INFINITY, f64::NEG_INFINITY);
        for &v in &all_values {
            if v < lo { lo = v; }
            if v > hi { hi = v; }
        }
        (hi - lo).max(1.0)
    };

    let mut entropies_at_t: Vec<(f64, f64)> = Vec::with_capacity(n_temps);
    for ti in 0..n_temps {
        let temp = max_temp * (ti as f64 + 0.5) / n_temps as f64;
        let h = entropy_at_temperature(&all_values, temp, n_bins);
        entropies_at_t.push((temp, h));
    }

    // Find discontinuities (large second derivative)
    let mut phase_transitions = Vec::new();
    let mut max_jump = 0.0f64;
    let mut critical_temp = entropies_at_t.first().map(|t| t.0).unwrap_or(0.0);

    for i in 1..entropies_at_t.len() - 1 {
        let d2 = (entropies_at_t[i + 1].1 - 2.0 * entropies_at_t[i].1 + entropies_at_t[i - 1].1).abs();
        if d2 > 0.1 {
            phase_transitions.push((entropies_at_t[i].0, d2));
        }
        if d2 > max_jump {
            max_jump = d2;
            critical_temp = entropies_at_t[i].0;
        }
    }

    ThermoResult {
        entropy_per_feature,
        total_entropy,
        free_energy,
        phase_transitions,
        critical_temperature: critical_temp,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_thermo_basic() {
        let data: Vec<f64> = (0..100).map(|i| (i as f64 * 0.1).sin()).collect();
        let result = scan(&data, 20, 5);
        assert_eq!(result.entropy_per_feature.len(), 5);
        assert!(result.total_entropy >= 0.0);
        assert!(result.critical_temperature >= 0.0);
    }

    #[test]
    fn test_shannon_entropy_uniform() {
        let vals: Vec<f64> = (0..100).map(|i| i as f64).collect();
        let h = shannon_entropy(&vals, 16);
        // Uniform distribution should have high entropy
        assert!(h > 1.0, "Uniform entropy should be > 1.0, got {h}");
    }
}
