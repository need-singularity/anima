//! ScaleLens — Power law / fractal analysis
//!
//! Log-log regression for power law detection, box-counting fractal dimension,
//! Hurst exponent via R/S analysis.

/// Result of scale lens scan.
#[derive(Debug, Clone)]
pub struct ScaleResult {
    /// Power law exponent per feature (from log-log regression)
    pub power_law_exponents: Vec<f64>,
    /// Box-counting fractal dimension proxy
    pub fractal_dimension: f64,
    /// Hurst exponent from R/S analysis (H>0.5: persistent, H<0.5: anti-persistent)
    pub hurst_exponent: f64,
}

/// Simple linear regression: returns (slope, intercept, r_squared).
fn linear_regression(x: &[f64], y: &[f64]) -> (f64, f64, f64) {
    let n = x.len().min(y.len()) as f64;
    if n < 2.0 { return (0.0, 0.0, 0.0); }
    let sx: f64 = x.iter().sum();
    let sy: f64 = y.iter().sum();
    let sxx: f64 = x.iter().map(|&xi| xi * xi).sum();
    let sxy: f64 = x.iter().zip(y.iter()).map(|(&xi, &yi)| xi * yi).sum();

    let denom = n * sxx - sx * sx;
    if denom.abs() < 1e-12 { return (0.0, sy / n, 0.0); }

    let slope = (n * sxy - sx * sy) / denom;
    let intercept = (sy - slope * sx) / n;

    // R-squared
    let y_mean = sy / n;
    let ss_tot: f64 = y.iter().map(|&yi| (yi - y_mean) * (yi - y_mean)).sum();
    let ss_res: f64 = x.iter().zip(y.iter())
        .map(|(&xi, &yi)| {
            let pred = slope * xi + intercept;
            (yi - pred) * (yi - pred)
        })
        .sum();
    let r2 = if ss_tot > 1e-12 { 1.0 - ss_res / ss_tot } else { 0.0 };

    (slope, intercept, r2)
}

/// Hurst exponent via R/S analysis on a 1D series.
fn hurst_exponent(series: &[f64]) -> f64 {
    let n = series.len();
    if n < 8 { return 0.5; }

    let mut log_ns = Vec::new();
    let mut log_rs = Vec::new();

    // Try different window sizes
    let mut window = 4;
    while window <= n / 2 {
        let n_windows = n / window;
        let mut rs_sum = 0.0;
        let mut valid = 0;

        for w in 0..n_windows {
            let start = w * window;
            let chunk = &series[start..start + window];

            let mean = chunk.iter().sum::<f64>() / window as f64;

            // Cumulative deviation
            let mut cum_dev = vec![0.0; window];
            cum_dev[0] = chunk[0] - mean;
            for i in 1..window {
                cum_dev[i] = cum_dev[i - 1] + (chunk[i] - mean);
            }

            let range = cum_dev.iter().cloned().fold(f64::NEG_INFINITY, f64::max)
                - cum_dev.iter().cloned().fold(f64::INFINITY, f64::min);

            let std: f64 = {
                let var: f64 = chunk.iter().map(|&x| (x - mean) * (x - mean)).sum::<f64>() / window as f64;
                var.sqrt()
            };

            if std > 1e-12 {
                rs_sum += range / std;
                valid += 1;
            }
        }

        if valid > 0 {
            log_ns.push((window as f64).ln());
            log_rs.push((rs_sum / valid as f64).ln());
        }

        window *= 2;
    }

    if log_ns.len() < 2 { return 0.5; }

    let (slope, _, _) = linear_regression(&log_ns, &log_rs);
    slope.clamp(0.0, 1.0)
}

/// Box-counting fractal dimension proxy.
/// Bins the data into hypercubes of decreasing size and counts occupied boxes.
fn box_counting_dimension(data: &[f64], n_samples: usize, n_features: usize) -> f64 {
    if n_samples < 4 || n_features == 0 { return 0.0; }

    // Normalize data to [0, 1]
    let mut mins = vec![f64::INFINITY; n_features];
    let mut maxs = vec![f64::NEG_INFINITY; n_features];
    for i in 0..n_samples {
        for j in 0..n_features {
            let v = data[i * n_features + j];
            if v < mins[j] { mins[j] = v; }
            if v > maxs[j] { maxs[j] = v; }
        }
    }
    let ranges: Vec<f64> = mins.iter().zip(maxs.iter()).map(|(&lo, &hi)| (hi - lo).max(1e-12)).collect();

    let mut log_eps = Vec::new();
    let mut log_counts = Vec::new();

    // Try different box sizes
    for n_divs_exp in 1..=6 {
        let n_divs = 1 << n_divs_exp; // 2, 4, 8, 16, 32, 64
        let eps = 1.0 / n_divs as f64;

        // Count occupied boxes using a hash set
        let mut occupied = std::collections::HashSet::new();
        for i in 0..n_samples {
            let mut key = Vec::with_capacity(n_features);
            for j in 0..n_features {
                let norm = (data[i * n_features + j] - mins[j]) / ranges[j];
                let bin = (norm * n_divs as f64) as u32;
                key.push(bin.min(n_divs - 1));
            }
            occupied.insert(key);
        }

        if occupied.len() > 1 {
            log_eps.push(eps.ln());
            log_counts.push((occupied.len() as f64).ln());
        }
    }

    if log_eps.len() < 2 { return n_features as f64; }

    // Fractal dimension = -slope of log(count) vs log(eps)
    let (slope, _, _) = linear_regression(&log_eps, &log_counts);
    (-slope).max(0.0)
}

/// Scan data for scale/fractal properties.
pub fn scan(data: &[f64], n_samples: usize, n_features: usize) -> ScaleResult {
    if n_samples < 4 || n_features == 0 {
        return ScaleResult {
            power_law_exponents: vec![],
            fractal_dimension: 0.0,
            hurst_exponent: 0.5,
        };
    }

    // Power law exponents per feature: log-log regression on sorted values
    let power_law_exponents: Vec<f64> = (0..n_features)
        .map(|j| {
            let mut col: Vec<f64> = (0..n_samples)
                .map(|i| data[i * n_features + j].abs())
                .filter(|&v| v > 1e-12)
                .collect();
            col.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
            if col.len() < 4 { return 0.0; }

            // Empirical CCDF: P(X > x) vs x in log-log
            let n = col.len();
            let log_x: Vec<f64> = col.iter().map(|&x| x.ln()).collect();
            let log_ccdf: Vec<f64> = (0..n).map(|i| ((n - i) as f64 / n as f64).ln()).collect();

            let (slope, _, _) = linear_regression(&log_x, &log_ccdf);
            -slope // power law exponent α
        })
        .collect();

    // Fractal dimension
    let fractal_dimension = box_counting_dimension(data, n_samples, n_features);

    // Hurst exponent (use first feature as representative time series)
    let first_col: Vec<f64> = (0..n_samples).map(|i| data[i * n_features]).collect();
    let hurst = hurst_exponent(&first_col);

    ScaleResult {
        power_law_exponents,
        fractal_dimension,
        hurst_exponent: hurst,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_scale_basic() {
        let n = 50;
        let d = 3;
        let data: Vec<f64> = (0..n * d).map(|i| (i as f64 * 0.1).sin().abs() + 0.01).collect();
        let result = scan(&data, n, d);
        assert_eq!(result.power_law_exponents.len(), d);
        assert!(result.fractal_dimension >= 0.0);
        assert!(result.hurst_exponent >= 0.0 && result.hurst_exponent <= 1.0);
    }

    #[test]
    fn test_hurst_persistent() {
        // Cumulative sum of positive increments = persistent (H > 0.5)
        let series: Vec<f64> = {
            let mut s = vec![0.0; 128];
            for i in 1..128 {
                s[i] = s[i - 1] + 0.1;
            }
            s
        };
        let h = hurst_exponent(&series);
        assert!(h > 0.4, "Trending series should have H > 0.4, got {h}");
    }
}
