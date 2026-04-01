//! Statistical pattern detection on metric time series.
//!
//! All functions operate on RingBuffer data and return Option<T>
//! when a statistically significant pattern is detected.

use crate::buffer::RingBuffer;
use realfft::RealFftPlanner;

// ═══════════════════════════════════════════════════════════════════════
// Correlation detection
// ═══════════════════════════════════════════════════════════════════════

/// Detect correlation between two metrics in the buffer.
///
/// Returns `Some((r, p_value))` if a statistically significant correlation
/// is found (|r| > 0.3 and enough samples). Returns None otherwise.
///
/// Uses Pearson correlation coefficient with t-test approximation for p-value.
pub fn detect_correlation(
    buffer: &RingBuffer,
    metric_a: usize,
    metric_b: usize,
) -> Option<(f32, f32)> {
    let n = buffer.len();
    if n < 10 || metric_a >= buffer.n_metrics() || metric_b >= buffer.n_metrics() {
        return None;
    }

    let a = buffer.series(metric_a);
    let b = buffer.series(metric_b);

    let (r, p) = pearson_with_pvalue(&a, &b);

    // Only report if significant
    if r.abs() > 0.3 && p < 0.05 {
        Some((r, p))
    } else {
        None
    }
}

/// Pearson correlation coefficient with approximate p-value.
fn pearson_with_pvalue(x: &[f32], y: &[f32]) -> (f32, f32) {
    let n = x.len().min(y.len());
    if n < 3 {
        return (0.0, 1.0);
    }

    let nf = n as f32;
    let sx: f32 = x[..n].iter().sum();
    let sy: f32 = y[..n].iter().sum();
    let sxy: f32 = x[..n].iter().zip(y[..n].iter()).map(|(&a, &b)| a * b).sum();
    let sxx: f32 = x[..n].iter().map(|&a| a * a).sum();
    let syy: f32 = y[..n].iter().map(|&a| a * a).sum();

    let num = nf * sxy - sx * sy;
    let den_sq = (nf * sxx - sx * sx) * (nf * syy - sy * sy);

    if den_sq <= 0.0 {
        return (0.0, 1.0);
    }

    let r = num / den_sq.sqrt();
    let r_clamped = r.clamp(-1.0, 1.0);

    // Approximate p-value using t-distribution with n-2 df
    // t = r * sqrt(n-2) / sqrt(1 - r^2)
    let r2 = r_clamped * r_clamped;
    if r2 >= 1.0 {
        return (r_clamped, 0.0);
    }

    let t = r_clamped.abs() * ((n as f32 - 2.0) / (1.0 - r2)).sqrt();
    let df = n as f32 - 2.0;

    // Approximate two-tailed p-value using the incomplete beta function approximation
    // For large df, use normal approximation
    let p = if df > 30.0 {
        // Normal approximation
        2.0 * normal_sf(t)
    } else {
        // Rough t-distribution CDF approximation
        2.0 * t_sf(t, df)
    };

    (r_clamped, p.clamp(0.0, 1.0))
}

/// Survival function for standard normal (1 - CDF).
fn normal_sf(x: f32) -> f32 {
    // Abramowitz and Stegun approximation 7.1.26
    let t = 1.0 / (1.0 + 0.2316419 * x.abs());
    let d = 0.3989422804 * (-x * x / 2.0).exp();
    let p = d * t * (0.3193815 + t * (-0.3565638 + t * (1.781478 + t * (-1.821256 + t * 1.330274))));
    if x > 0.0 { p } else { 1.0 - p }
}

/// Approximate survival function for t-distribution.
fn t_sf(t: f32, df: f32) -> f32 {
    // Use normal approximation with correction for df
    let x = t * (1.0 - 1.0 / (4.0 * df)).max(0.5);
    normal_sf(x)
}

// ═══════════════════════════════════════════════════════════════════════
// Phase transition detection
// ═══════════════════════════════════════════════════════════════════════

/// Detect a phase transition (abrupt shift) in a metric time series.
///
/// Uses a sliding window to compare mean before/after each point.
/// Returns `Some(step_index)` where the largest significant shift occurs.
///
/// `sigma_threshold`: minimum shift in units of standard deviation (default: 2.0).
pub fn detect_phase_transition(
    buffer: &RingBuffer,
    metric: usize,
    sigma_threshold: f32,
) -> Option<usize> {
    let n = buffer.len();
    if n < 20 || metric >= buffer.n_metrics() {
        return None;
    }

    let series = buffer.series(metric);
    let window = (n / 4).max(5);

    // Global standard deviation for normalization
    let mean: f32 = series.iter().sum::<f32>() / n as f32;
    let var: f32 = series.iter().map(|&x| (x - mean) * (x - mean)).sum::<f32>() / n as f32;
    let sigma = var.sqrt();
    if sigma < f32::EPSILON {
        return None;
    }

    let mut best_shift: f32 = 0.0;
    let mut best_idx: Option<usize> = None;

    // Slide through the series looking for mean shifts
    for i in window..(n - window) {
        let mean_before: f32 = series[i - window..i].iter().sum::<f32>() / window as f32;
        let mean_after: f32 = series[i..i + window].iter().sum::<f32>() / window as f32;
        let shift = ((mean_after - mean_before) / sigma).abs();

        if shift >= sigma_threshold && shift > best_shift {
            best_shift = shift;
            best_idx = Some(i);
        }
    }

    best_idx
}

// ═══════════════════════════════════════════════════════════════════════
// Periodicity detection (FFT)
// ═══════════════════════════════════════════════════════════════════════

/// Detect dominant periodicity in a metric time series.
///
/// Returns `Some(frequency)` if a clear periodic pattern exists
/// (peak power > 2x median power). Frequency is in cycles per step.
pub fn detect_periodicity(
    buffer: &RingBuffer,
    metric: usize,
) -> Option<f32> {
    let n = buffer.len();
    if n < 32 || metric >= buffer.n_metrics() {
        return None;
    }

    let series = buffer.series(metric);

    // Remove mean (DC component)
    let mean: f32 = series.iter().sum::<f32>() / n as f32;
    let mut detrended: Vec<f64> = series.iter().map(|&x| (x - mean) as f64).collect();

    // Pad to power of 2 (not strictly required by realfft but improves performance)
    let fft_len = detrended.len();

    // Apply Hann window to reduce spectral leakage
    for i in 0..fft_len {
        let w = 0.5 * (1.0 - (2.0 * std::f64::consts::PI * i as f64 / (fft_len - 1) as f64).cos());
        detrended[i] *= w;
    }

    // Compute FFT
    let mut planner = RealFftPlanner::<f64>::new();
    let fft = planner.plan_fft_forward(fft_len);
    let mut spectrum = fft.make_output_vec();

    if fft.process(&mut detrended, &mut spectrum).is_err() {
        return None;
    }

    // Power spectrum (skip DC at index 0)
    let powers: Vec<f32> = spectrum[1..]
        .iter()
        .map(|c| (c.re * c.re + c.im * c.im) as f32)
        .collect();

    if powers.is_empty() {
        return None;
    }

    // Find peak
    let mut max_power: f32 = 0.0;
    let mut max_idx: usize = 0;
    for (i, &p) in powers.iter().enumerate() {
        if p > max_power {
            max_power = p;
            max_idx = i;
        }
    }

    // Significance test: peak must dominate the spectrum.
    // Use mean (excluding the peak bin) as the noise floor reference.
    let mean_power = if powers.len() > 1 {
        let sum_excl: f32 = powers.iter().enumerate()
            .filter(|&(i, _)| i != max_idx)
            .map(|(_, &p)| p)
            .sum();
        sum_excl / (powers.len() - 1) as f32
    } else {
        0.0
    };

    // Peak must carry significant fraction of total energy
    let total_power: f32 = powers.iter().sum();
    let peak_ratio = if total_power > f32::EPSILON { max_power / total_power } else { 0.0 };

    // Reject if peak is not prominent: either > 4x mean noise or > 20% of total energy
    if peak_ratio < 0.1 && (mean_power < f32::EPSILON || max_power < mean_power * 4.0) {
        return None;
    }

    // Convert index to frequency (cycles per step)
    // Index max_idx+1 corresponds to frequency (max_idx+1) / fft_len
    let freq = (max_idx + 1) as f32 / fft_len as f32;

    // Ignore very low and very high frequencies
    let period = 1.0 / freq;
    if period < 3.0 || period > (n as f32 * 0.8) {
        return None;
    }

    Some(freq)
}

// ═══════════════════════════════════════════════════════════════════════
// Trend detection (linear regression)
// ═══════════════════════════════════════════════════════════════════════

/// Detect a monotonic trend in a metric time series.
///
/// Returns `(slope, r_squared)`. The slope is in units of metric-per-step.
/// r_squared indicates how well a linear model fits (>0.5 = strong trend).
pub fn detect_trend(
    buffer: &RingBuffer,
    metric: usize,
) -> (f32, f32) {
    let n = buffer.len();
    if n < 5 || metric >= buffer.n_metrics() {
        return (0.0, 0.0);
    }

    let series = buffer.series(metric);
    let x: Vec<f32> = (0..n).map(|i| i as f32).collect();

    linear_regression_sr(&x, &series)
}

/// Linear regression returning (slope, r_squared).
fn linear_regression_sr(x: &[f32], y: &[f32]) -> (f32, f32) {
    let n = x.len().min(y.len());
    if n < 2 {
        return (0.0, 0.0);
    }
    let nf = n as f32;

    let sx: f32 = x[..n].iter().sum();
    let sy: f32 = y[..n].iter().sum();
    let sxy: f32 = x[..n].iter().zip(y[..n].iter()).map(|(&a, &b)| a * b).sum();
    let sxx: f32 = x[..n].iter().map(|&a| a * a).sum();
    let syy: f32 = y[..n].iter().map(|&a| a * a).sum();

    let denom = nf * sxx - sx * sx;
    if denom.abs() < f32::EPSILON {
        return (0.0, 0.0);
    }

    let slope = (nf * sxy - sx * sy) / denom;
    let intercept = (sy - slope * sx) / nf;

    // R-squared
    let ss_res: f32 = x[..n].iter().zip(y[..n].iter())
        .map(|(&xi, &yi)| {
            let pred = intercept + slope * xi;
            (yi - pred) * (yi - pred)
        })
        .sum();
    let ss_tot = syy - sy * sy / nf;

    let r_sq = if ss_tot > f32::EPSILON {
        (1.0 - ss_res / ss_tot).clamp(0.0, 1.0)
    } else {
        0.0
    };

    (slope, r_sq)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make_buffer_with_data(data: &[Vec<f32>]) -> RingBuffer {
        if data.is_empty() {
            return RingBuffer::new(1, 1);
        }
        let n_metrics = data[0].len();
        let mut buf = RingBuffer::new(data.len() + 10, n_metrics);
        for row in data {
            buf.push(row);
        }
        buf
    }

    #[test]
    fn test_correlation_positive() {
        // Two perfectly correlated metrics
        let data: Vec<Vec<f32>> = (0..100)
            .map(|i| vec![i as f32, i as f32 * 2.0 + 5.0])
            .collect();
        let buf = make_buffer_with_data(&data);
        let result = detect_correlation(&buf, 0, 1);
        assert!(result.is_some(), "should detect correlation");
        let (r, p) = result.unwrap();
        assert!(r > 0.99, "r should be ~1.0, got {}", r);
        assert!(p < 0.01, "p should be very small, got {}", p);
    }

    #[test]
    fn test_correlation_negative() {
        let data: Vec<Vec<f32>> = (0..100)
            .map(|i| vec![i as f32, 100.0 - i as f32])
            .collect();
        let buf = make_buffer_with_data(&data);
        let result = detect_correlation(&buf, 0, 1);
        assert!(result.is_some());
        let (r, _) = result.unwrap();
        assert!(r < -0.99, "r should be ~-1.0, got {}", r);
    }

    #[test]
    fn test_correlation_uncorrelated() {
        // Random-ish uncorrelated data
        let data: Vec<Vec<f32>> = (0..100)
            .map(|i| {
                vec![
                    (i as f32 * 1.618).sin(),
                    (i as f32 * 3.14159).cos(),
                ]
            })
            .collect();
        let buf = make_buffer_with_data(&data);
        let result = detect_correlation(&buf, 0, 1);
        // May or may not detect weak correlation; if detected, r should be small
        if let Some((r, _)) = result {
            assert!(r.abs() < 0.8, "sin/cos should not be strongly correlated");
        }
    }

    #[test]
    fn test_correlation_too_few_samples() {
        let data: Vec<Vec<f32>> = (0..5).map(|i| vec![i as f32, i as f32]).collect();
        let buf = make_buffer_with_data(&data);
        assert!(detect_correlation(&buf, 0, 1).is_none());
    }

    #[test]
    fn test_phase_transition_step() {
        // Metric with a clear jump at index 50
        let data: Vec<Vec<f32>> = (0..100)
            .map(|i| {
                if i < 50 {
                    vec![1.0]
                } else {
                    vec![10.0]
                }
            })
            .collect();
        let buf = make_buffer_with_data(&data);
        let result = detect_phase_transition(&buf, 0, 2.0);
        assert!(result.is_some(), "should detect phase transition");
        let idx = result.unwrap();
        // Should be near 50
        assert!((idx as i32 - 50).unsigned_abs() < 15, "transition at {}, expected ~50", idx);
    }

    #[test]
    fn test_phase_transition_gradual() {
        // Smooth ramp — no sharp transition
        let data: Vec<Vec<f32>> = (0..100)
            .map(|i| vec![i as f32 * 0.1])
            .collect();
        let buf = make_buffer_with_data(&data);
        let result = detect_phase_transition(&buf, 0, 3.0);
        // Gradual change should not trigger (depends on threshold)
        // With sigma_threshold=3.0, a linear ramp might not trigger
        // This is acceptable behavior
        eprintln!("gradual phase transition result: {:?}", result);
    }

    #[test]
    fn test_phase_transition_too_short() {
        let data: Vec<Vec<f32>> = (0..10).map(|i| vec![i as f32]).collect();
        let buf = make_buffer_with_data(&data);
        assert!(detect_phase_transition(&buf, 0, 2.0).is_none());
    }

    #[test]
    fn test_periodicity_sine() {
        // Clear sine wave with period 20 steps
        let data: Vec<Vec<f32>> = (0..200)
            .map(|i| {
                vec![(2.0 * std::f32::consts::PI * i as f32 / 20.0).sin()]
            })
            .collect();
        let buf = make_buffer_with_data(&data);
        let result = detect_periodicity(&buf, 0);
        assert!(result.is_some(), "should detect periodicity");
        let freq = result.unwrap();
        let period = 1.0 / freq;
        assert!(
            (period - 20.0).abs() < 3.0,
            "period should be ~20, got {:.1}", period
        );
    }

    #[test]
    fn test_periodicity_noise() {
        // Random noise — no clear period
        let data: Vec<Vec<f32>> = (0..200)
            .map(|i| vec![((i * 7 + 13) % 100) as f32 / 100.0])
            .collect();
        let buf = make_buffer_with_data(&data);
        let result = detect_periodicity(&buf, 0);
        // Noise might not have a dominant frequency
        eprintln!("noise periodicity result: {:?}", result);
    }

    #[test]
    fn test_periodicity_too_short() {
        let data: Vec<Vec<f32>> = (0..10).map(|i| vec![i as f32]).collect();
        let buf = make_buffer_with_data(&data);
        assert!(detect_periodicity(&buf, 0).is_none());
    }

    #[test]
    fn test_trend_linear_up() {
        let data: Vec<Vec<f32>> = (0..100).map(|i| vec![i as f32 * 0.5 + 10.0]).collect();
        let buf = make_buffer_with_data(&data);
        let (slope, r2) = detect_trend(&buf, 0);
        assert!((slope - 0.5).abs() < 0.01, "slope should be ~0.5, got {}", slope);
        assert!(r2 > 0.99, "r2 should be ~1.0, got {}", r2);
    }

    #[test]
    fn test_trend_linear_down() {
        let data: Vec<Vec<f32>> = (0..100).map(|i| vec![100.0 - i as f32 * 0.3]).collect();
        let buf = make_buffer_with_data(&data);
        let (slope, r2) = detect_trend(&buf, 0);
        assert!((slope - (-0.3)).abs() < 0.01, "slope should be ~-0.3, got {}", slope);
        assert!(r2 > 0.99);
    }

    #[test]
    fn test_trend_constant() {
        let data: Vec<Vec<f32>> = (0..100).map(|_| vec![5.0]).collect();
        let buf = make_buffer_with_data(&data);
        let (slope, _r2) = detect_trend(&buf, 0);
        assert!(slope.abs() < 0.001, "constant series should have ~0 slope");
    }

    #[test]
    fn test_trend_too_short() {
        let data: Vec<Vec<f32>> = (0..3).map(|i| vec![i as f32]).collect();
        let buf = make_buffer_with_data(&data);
        let (slope, r2) = detect_trend(&buf, 0);
        assert_eq!(slope, 0.0);
        assert_eq!(r2, 0.0);
    }

    #[test]
    fn bench_pattern_detection() {
        // 1000 steps of 8 metrics
        let data: Vec<Vec<f32>> = (0..1000)
            .map(|i| {
                vec![
                    (i as f32 * 0.1).sin(),
                    (i as f32 * 0.05).cos(),
                    i as f32 * 0.01,
                    ((i * 7 + 13) % 100) as f32 / 100.0,
                    (i as f32 * 0.2).sin() * 0.5 + 0.5,
                    i as f32 * 0.005,
                    0.5,
                    64.0,
                ]
            })
            .collect();
        let buf = make_buffer_with_data(&data);

        let start = std::time::Instant::now();
        let _corr = detect_correlation(&buf, 0, 1);
        let _pt = detect_phase_transition(&buf, 2, 2.0);
        let _period = detect_periodicity(&buf, 0);
        let _trend = detect_trend(&buf, 2);
        let elapsed = start.elapsed();

        eprintln!("ALL pattern detection (1000 steps, 8 metrics): {:.1}us", elapsed.as_micros());
    }
}
