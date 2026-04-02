//! WaveLens — FFT + resonance detection
//!
//! FFT per feature, cross-spectral coherence, resonance (harmonic) detection.

use std::f64::consts::PI;

/// Result of wave lens scan.
#[derive(Debug, Clone)]
pub struct WaveResult {
    /// Dominant frequency per feature
    pub dominant_frequencies: Vec<f64>,
    /// Coherence between feature pairs (flattened upper triangle)
    pub coherences: Vec<(usize, usize, f64)>,
    /// Resonance pairs: (feat_i, feat_j, ratio near integer)
    pub resonances: Vec<(usize, usize, f64)>,
}

/// Simple DFT for small N (no external FFT crate needed).
/// Returns magnitude spectrum (N/2 + 1 bins).
fn dft_magnitudes(signal: &[f64]) -> Vec<f64> {
    let n = signal.len();
    let half = n / 2 + 1;
    let mut mags = vec![0.0; half];
    for k in 0..half {
        let mut re = 0.0;
        let mut im = 0.0;
        let w = 2.0 * PI * k as f64 / n as f64;
        for (t, &x) in signal.iter().enumerate() {
            re += x * (w * t as f64).cos();
            im -= x * (w * t as f64).sin();
        }
        mags[k] = (re * re + im * im).sqrt();
    }
    mags
}

/// Find the dominant frequency bin (skip DC at bin 0).
fn dominant_freq_bin(mags: &[f64]) -> (usize, f64) {
    let mut best_bin = 1;
    let mut best_mag = 0.0;
    for (k, &m) in mags.iter().enumerate().skip(1) {
        if m > best_mag {
            best_mag = m;
            best_bin = k;
        }
    }
    (best_bin, best_mag)
}

/// Cross-spectral coherence between two signals.
fn coherence(a: &[f64], b: &[f64]) -> f64 {
    let n = a.len().min(b.len());
    if n < 4 { return 0.0; }

    let ma = dft_magnitudes(a);
    let mb = dft_magnitudes(b);
    let half = ma.len().min(mb.len());

    // Coherence = |Sxy|² / (Sxx * Syy)
    // Simplified: correlation of magnitude spectra
    let mean_a: f64 = ma.iter().sum::<f64>() / half as f64;
    let mean_b: f64 = mb.iter().sum::<f64>() / half as f64;
    let mut cov = 0.0;
    let mut var_a = 0.0;
    let mut var_b = 0.0;
    for k in 0..half {
        let da = ma[k] - mean_a;
        let db = mb[k] - mean_b;
        cov += da * db;
        var_a += da * da;
        var_b += db * db;
    }
    let denom = (var_a * var_b).sqrt();
    if denom < 1e-12 { 0.0 } else { (cov / denom).abs() }
}

/// Scan data for wave/frequency properties.
pub fn scan(data: &[f64], n_samples: usize, n_features: usize) -> WaveResult {
    if n_samples < 4 || n_features == 0 {
        return WaveResult {
            dominant_frequencies: vec![],
            coherences: vec![],
            resonances: vec![],
        };
    }

    // Extract columns
    let columns: Vec<Vec<f64>> = (0..n_features)
        .map(|j| (0..n_samples).map(|i| data[i * n_features + j]).collect())
        .collect();

    // Dominant frequencies
    let dominant_frequencies: Vec<f64> = columns
        .iter()
        .map(|col| {
            let mags = dft_magnitudes(col);
            let (bin, _) = dominant_freq_bin(&mags);
            bin as f64 / n_samples as f64
        })
        .collect();

    // Cross-spectral coherence (upper triangle)
    let max_pairs = 200;
    let mut coherences = Vec::new();
    let mut count = 0;
    'outer: for i in 0..n_features {
        for j in (i + 1)..n_features {
            let c = coherence(&columns[i], &columns[j]);
            if c > 0.3 {
                coherences.push((i, j, c));
            }
            count += 1;
            if count >= max_pairs { break 'outer; }
        }
    }

    // Resonance detection: frequency ratios close to simple integers
    let mut resonances = Vec::new();
    for i in 0..n_features {
        for j in (i + 1)..n_features {
            let fi = dominant_frequencies[i];
            let fj = dominant_frequencies[j];
            if fi < 1e-12 || fj < 1e-12 { continue; }
            let ratio = fi.max(fj) / fi.min(fj);
            let nearest_int = ratio.round();
            if nearest_int >= 1.0 && nearest_int <= 8.0 && (ratio - nearest_int).abs() < 0.1 {
                resonances.push((i, j, nearest_int));
            }
            if resonances.len() >= 100 { break; }
        }
        if resonances.len() >= 100 { break; }
    }

    WaveResult {
        dominant_frequencies,
        coherences,
        resonances,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::f64::consts::PI;

    #[test]
    fn test_wave_sine() {
        let n = 64;
        let d = 2;
        let mut data = vec![0.0; n * d];
        for i in 0..n {
            data[i * d] = (2.0 * PI * 4.0 * i as f64 / n as f64).sin(); // 4 cycles
            data[i * d + 1] = (2.0 * PI * 8.0 * i as f64 / n as f64).sin(); // 8 cycles
        }
        let result = scan(&data, n, d);
        assert_eq!(result.dominant_frequencies.len(), 2);
        // Frequency 0 should be near 4/64, freq 1 near 8/64
        assert!((result.dominant_frequencies[0] - 4.0 / 64.0).abs() < 0.02,
                "Expected ~0.0625, got {}", result.dominant_frequencies[0]);
        assert!((result.dominant_frequencies[1] - 8.0 / 64.0).abs() < 0.02,
                "Expected ~0.125, got {}", result.dominant_frequencies[1]);
    }

    #[test]
    fn test_wave_empty() {
        let result = scan(&[], 0, 0);
        assert!(result.dominant_frequencies.is_empty());
    }
}
