//! Tension-based learning rate scaling (Law 187).
//!
//! lr = tension_ratio * base_lr, capped at 5x base.
//! When tension is high relative to its EMA, learning rate increases
//! to capture the novel signal. When tension is low, lr decreases
//! to avoid overwriting stable representations.

/// Compute tension-scaled learning rate.
///
/// `ratio = current_tension / tension_ema` scales the base_lr.
/// Capped at 5x base_lr to prevent instability.
///
/// # Law 187: lr = tension_ratio * base_lr (Pareto optimal)
pub fn tension_lr(current_tension: f32, tension_ema: f32, base_lr: f32) -> f32 {
    let ratio = current_tension / tension_ema.max(1e-8);
    (ratio * base_lr).min(base_lr * 5.0)
}

/// Update exponential moving average of tension.
///
/// `decay` controls smoothing (e.g., 0.99 = slow adaptation, 0.9 = fast).
pub fn update_tension_ema(ema: f32, current: f32, decay: f32) -> f32 {
    decay * ema + (1.0 - decay) * current
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_tension_lr_normal() {
        // tension == ema → ratio = 1.0 → lr = base_lr
        let lr = tension_lr(0.5, 0.5, 0.001);
        assert!((lr - 0.001).abs() < 1e-7);
    }

    #[test]
    fn test_tension_lr_high_tension() {
        // tension = 3x ema → lr = 3x base
        let lr = tension_lr(1.5, 0.5, 0.001);
        assert!((lr - 0.003).abs() < 1e-7);
    }

    #[test]
    fn test_tension_lr_capped() {
        // tension = 10x ema → capped at 5x base
        let lr = tension_lr(5.0, 0.5, 0.001);
        assert!((lr - 0.005).abs() < 1e-7);
    }

    #[test]
    fn test_tension_lr_low_tension() {
        // tension = 0.5x ema → lr = 0.5x base
        let lr = tension_lr(0.25, 0.5, 0.001);
        assert!((lr - 0.0005).abs() < 1e-7);
    }

    #[test]
    fn test_tension_lr_zero_ema() {
        // ema near zero → uses 1e-8 floor, ratio is huge → capped at 5x
        let lr = tension_lr(0.5, 0.0, 0.001);
        assert!((lr - 0.005).abs() < 1e-7);
    }

    #[test]
    fn test_update_tension_ema() {
        let ema = update_tension_ema(0.5, 1.0, 0.9);
        // 0.9 * 0.5 + 0.1 * 1.0 = 0.55
        assert!((ema - 0.55).abs() < 1e-7);
    }

    #[test]
    fn test_update_tension_ema_no_decay() {
        let ema = update_tension_ema(0.5, 1.0, 0.0);
        // 0.0 * 0.5 + 1.0 * 1.0 = 1.0
        assert!((ema - 1.0).abs() < 1e-7);
    }
}
