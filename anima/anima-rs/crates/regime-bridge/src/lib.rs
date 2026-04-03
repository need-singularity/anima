//! Hot-path trading functions for anima-agent trading plugin.
//!
//! Three functions that replace Python bottlenecks:
//! - `action_gate`: consciousness-modulated trading gate
//! - `pain_from_var`: variance-based pain signal
//! - `soc_criticality`: self-organized criticality from return cascades

/// Consciousness-modulated action gate.
///
/// Higher phi widens the gate (consciousness amplifies action capacity).
/// Higher tension+pain narrows it (inhibition from suffering).
///
/// - `phi_factor` = clamp(1.0 + ln(1+phi) * 0.014, 0.5, 2.0)
/// - `inhibition` = clamp(tension * (1+pain) / 2, 0, 1)
/// - `gate` = max(0, 1 - inhibition^(1/phi_factor))
pub fn action_gate(tension: f64, pain: f64, phi: f64) -> f64 {
    let phi_factor = (1.0 + (1.0 + phi).ln() * 0.014).max(0.5).min(2.0);
    let inhibition = (tension * (1.0 + pain) / 2.0).max(0.0).min(1.0);
    (1.0 - inhibition.powf(1.0 / phi_factor)).max(0.0)
}

/// Compute pain signal from variance percentage.
///
/// Positive variance (gains) produce zero pain.
/// Negative variance (losses) produce pain proportional to how far
/// the loss exceeds `var_floor`, scaled toward `var_ceiling`.
///
/// Returns tanh(max(0, ratio)) where ratio = (|var_pct| - floor) / (ceiling - floor).
pub fn pain_from_var(var_pct: f64, var_floor: f64, var_ceiling: f64) -> f64 {
    if var_pct >= 0.0 {
        return 0.0;
    }
    let range = var_ceiling - var_floor;
    if range <= 0.0 {
        return 0.0;
    }
    let ratio = (var_pct.abs() - var_floor) / range;
    ratio.max(0.0).tanh()
}

/// Self-organized criticality score from return cascades.
///
/// Takes the last `window` absolute returns, finds the 90th percentile,
/// counts consecutive runs above that threshold (cascades),
/// and returns cascade_count / window.
pub fn soc_criticality(returns: &[f64], window: usize) -> f64 {
    if window == 0 || returns.is_empty() {
        return 0.0;
    }

    let start = if returns.len() > window {
        returns.len() - window
    } else {
        0
    };
    let slice = &returns[start..];

    let mut abs_vals: Vec<f64> = slice.iter().map(|r| r.abs()).collect();
    abs_vals.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));

    let n = abs_vals.len();
    if n == 0 {
        return 0.0;
    }

    // 90th percentile (index-based)
    let p90_idx = ((n as f64) * 0.9).ceil() as usize;
    let p90_idx = p90_idx.min(n).max(1) - 1;
    let p90 = abs_vals[p90_idx];

    // Count cascades: consecutive returns above p90 (in original order)
    let mut cascade_count: usize = 0;
    let mut in_cascade = false;
    for &val in slice {
        let val = val.abs();
        if val >= p90 {
            if !in_cascade {
                in_cascade = true;
            }
            cascade_count += 1;
        } else {
            in_cascade = false;
        }
    }

    cascade_count as f64 / window as f64
}

/// Vec-based wrapper for soc_criticality (convenience for FFI).
pub fn soc_criticality_vec(returns: Vec<f64>, window: usize) -> f64 {
    soc_criticality(&returns, window)
}

#[cfg(test)]
mod tests {
    use super::*;

    // ── action_gate tests ──

    #[test]
    fn test_gate_zero_inhibition() {
        // tension=0 → inhibition=0 → gate=1
        let g = action_gate(0.0, 0.0, 1.0);
        assert!((g - 1.0).abs() < 1e-9);
    }

    #[test]
    fn test_gate_full_inhibition() {
        // tension=1, pain=1 → inhibition=1 → gate=0
        let g = action_gate(1.0, 1.0, 1.0);
        assert!((g - 0.0).abs() < 1e-9);
    }

    #[test]
    fn test_gate_phi_effect() {
        // With phi=0 → phi_factor=1.0+ln(1)*0.014=1.0
        // With phi=100 → phi_factor=1.0+ln(101)*0.014≈1.0646
        // Higher phi_factor takes a higher root of inhibition (<1),
        // making it closer to 1, so gate = 1 - inhibition^(1/phi_factor) changes.
        // The key property: phi modulates the exponent.
        let g_zero = action_gate(0.5, 0.3, 0.0);
        let g_some = action_gate(0.5, 0.3, 100.0);
        // Both should be valid gate values in [0,1]
        assert!(g_zero >= 0.0 && g_zero <= 1.0);
        assert!(g_some >= 0.0 && g_some <= 1.0);
        // phi_factor clamp: phi=0 → factor=1.0, phi=100 → factor≈1.065
        // They should produce different (non-trivial) gate values
        assert!((g_zero - g_some).abs() > 1e-6, "phi should affect gate");
    }

    #[test]
    fn test_gate_nonnegative() {
        let g = action_gate(0.9, 0.9, 0.01);
        assert!(g >= 0.0);
    }

    #[test]
    fn test_gate_range() {
        // Gate should always be in [0, 1]
        for t in [0.0, 0.3, 0.5, 0.7, 1.0] {
            for p in [0.0, 0.3, 0.5, 1.0] {
                for phi in [0.0, 0.5, 1.0, 10.0, 100.0] {
                    let g = action_gate(t, p, phi);
                    assert!(g >= 0.0 && g <= 1.0, "gate out of range: t={t} p={p} phi={phi} g={g}");
                }
            }
        }
    }

    // ── pain_from_var tests ──

    #[test]
    fn test_pain_positive_var() {
        assert!((pain_from_var(5.0, 1.0, 10.0) - 0.0).abs() < 1e-9);
    }

    #[test]
    fn test_pain_zero_var() {
        assert!((pain_from_var(0.0, 1.0, 10.0) - 0.0).abs() < 1e-9);
    }

    #[test]
    fn test_pain_below_floor() {
        // |var_pct| < floor → ratio < 0 → clamped to 0 → tanh(0) = 0
        let p = pain_from_var(-0.5, 1.0, 10.0);
        assert!((p - 0.0).abs() < 1e-9);
    }

    #[test]
    fn test_pain_at_ceiling() {
        // |var_pct|=10, floor=1, ceiling=10 → ratio=1 → tanh(1)≈0.7616
        let p = pain_from_var(-10.0, 1.0, 10.0);
        assert!((p - 1.0_f64.tanh()).abs() < 1e-6);
    }

    #[test]
    fn test_pain_monotonic() {
        let p1 = pain_from_var(-3.0, 1.0, 10.0);
        let p2 = pain_from_var(-7.0, 1.0, 10.0);
        assert!(p2 > p1, "more loss should mean more pain");
    }

    #[test]
    fn test_pain_bad_range() {
        // ceiling <= floor → return 0
        let p = pain_from_var(-5.0, 10.0, 1.0);
        assert!((p - 0.0).abs() < 1e-9);
    }

    // ── soc_criticality tests ──

    #[test]
    fn test_soc_empty() {
        assert!((soc_criticality(&[], 10) - 0.0).abs() < 1e-9);
    }

    #[test]
    fn test_soc_zero_window() {
        assert!((soc_criticality(&[1.0, 2.0], 0) - 0.0).abs() < 1e-9);
    }

    #[test]
    fn test_soc_uniform() {
        // All identical returns: all are at p90, all counted
        let returns = vec![1.0; 20];
        let c = soc_criticality(&returns, 20);
        // All returns are >= p90 (they're equal), so cascade_count = 20
        assert!((c - 1.0).abs() < 1e-9);
    }

    #[test]
    fn test_soc_range() {
        let returns: Vec<f64> = (0..100).map(|i| (i as f64) * 0.01).collect();
        let c = soc_criticality(&returns, 100);
        assert!(c >= 0.0 && c <= 1.0);
    }

    #[test]
    fn test_soc_window_truncation() {
        // 50 returns, window=10 → only last 10 used
        let mut returns = vec![0.01; 40];
        returns.extend(vec![10.0; 10]);
        let c = soc_criticality(&returns, 10);
        // All 10 are identical (10.0), so all >= p90, cascade_count = 10
        assert!((c - 1.0).abs() < 1e-9);
    }

    #[test]
    fn test_soc_vec_wrapper() {
        let returns = vec![0.1, 0.2, 0.3, 0.4, 0.5];
        let c1 = soc_criticality(&returns, 5);
        let c2 = soc_criticality_vec(returns, 5);
        assert!((c1 - c2).abs() < 1e-9);
    }
}
