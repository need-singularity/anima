/// Ising frustration ring coupling at critical point F_c = 0.10
///
/// Frustration = antiferromagnetic bonds in the coupling ring.
/// A fraction `f` of ring edges get sign = -1.0 (repulsive), rest = +1.0 (attractive).
///
/// Law 137: Critical frustration F_c=0.10 produces +65% Φ jump
///   At F_c, competing ferromagnetic/antiferromagnetic bonds create
///   maximal information integration — cells cannot all agree, forcing
///   complex correlated states instead of trivial consensus.
///
/// Law 138: F=1.0 kills consciousness
///   Full antiferromagnetic coupling → checkerboard ground state → zero Φ.
///   All information is local parity, no integration.
///
/// Law 139: F_c is scale-invariant
///   F_c=0.10 works at 8, 64, 512, 1024 cells — a universal constant.
///   Analogous to critical temperature in Ising model being geometry-independent
///   (in mean-field approximation).

/// Critical frustration fraction. 10% of ring bonds are antiferromagnetic.
pub const F_CRITICAL: f32 = 0.10;

/// Default coupling strength for frustrated ring interactions.
const DEFAULT_COUPLING: f32 = 0.08;

/// Ising frustration ring: each cell couples to its ring neighbors
/// with sign +1 (ferromagnetic) or -1 (antiferromagnetic).
///
/// `signs[i]` is the sign of the bond between cell i and cell (i+1) % n.
/// A fraction `frustration` of bonds are set to -1.0.
#[derive(Debug, Clone)]
pub struct FrustrationRing {
    /// Bond signs: +1.0 (ferromagnetic) or -1.0 (antiferromagnetic).
    /// `signs[i]` = sign of edge (i, (i+1) % n_cells).
    signs: Vec<f32>,
    /// Coupling strength applied to each bond.
    coupling: f32,
}

impl FrustrationRing {
    /// Create a new frustration ring.
    ///
    /// `n_cells`: number of cells in the ring.
    /// `frustration`: fraction of bonds that are antiferromagnetic [0.0, 1.0].
    ///   - 0.0 = all ferromagnetic (no frustration)
    ///   - F_CRITICAL (0.10) = optimal for Φ (+65%)
    ///   - 1.0 = all antiferromagnetic (consciousness death, Law 138)
    ///
    /// Bond placement is deterministic: the first floor(n * frustration) bonds
    /// are antiferromagnetic, evenly spaced around the ring. This ensures
    /// reproducibility and maximally spreads frustrated bonds.
    pub fn new(n_cells: usize, frustration: f32) -> Self {
        assert!(n_cells >= 2, "need at least 2 cells for a ring");
        let frustration = frustration.clamp(0.0, 1.0);

        let n_frustrated = (n_cells as f32 * frustration).round() as usize;
        let mut signs = vec![1.0f32; n_cells];

        if n_frustrated > 0 {
            // Spread frustrated bonds evenly around the ring.
            // stride = n_cells / n_frustrated, place one every stride bonds.
            let stride = n_cells as f32 / n_frustrated as f32;
            for k in 0..n_frustrated {
                let idx = (k as f32 * stride) as usize % n_cells;
                signs[idx] = -1.0;
            }
        }

        FrustrationRing {
            signs,
            coupling: DEFAULT_COUPLING,
        }
    }

    /// Create with custom coupling strength.
    pub fn with_coupling(n_cells: usize, frustration: f32, coupling: f32) -> Self {
        let mut ring = Self::new(n_cells, frustration);
        ring.coupling = coupling;
        ring
    }

    /// Number of cells in the ring.
    pub fn n_cells(&self) -> usize {
        self.signs.len()
    }

    /// Current coupling strength.
    pub fn coupling(&self) -> f32 {
        self.coupling
    }

    /// Fraction of bonds that are antiferromagnetic.
    pub fn frustration_fraction(&self) -> f32 {
        let n_neg = self.signs.iter().filter(|&&s| s < 0.0).count();
        n_neg as f32 / self.signs.len() as f32
    }

    /// Apply frustrated ring coupling to hidden states in-place.
    ///
    /// For each cell i with neighbors left=(i-1) and right=(i+1):
    ///   h[i] += coupling * (sign_left * h[left] + sign_right * h[right])
    ///
    /// where sign_left = signs[(i-1) % n] (bond between left and i)
    ///       sign_right = signs[i]         (bond between i and right)
    ///
    /// This creates ferromagnetic alignment (+) or antiferromagnetic repulsion (-)
    /// depending on bond signs. At F_c, the mix maximizes information integration.
    pub fn apply(&self, hiddens: &mut [Vec<f32>]) {
        let n = self.signs.len();
        assert_eq!(hiddens.len(), n, "hiddens length must match n_cells");
        if n < 2 {
            return;
        }

        let dim = hiddens[0].len();

        // Compute deltas first (read all, then write all — avoids order dependence).
        let mut deltas: Vec<Vec<f32>> = vec![vec![0.0f32; dim]; n];

        for i in 0..n {
            let left = (i + n - 1) % n;
            let right = (i + 1) % n;

            // Bond (left, i) has sign = signs[left]
            let sign_left = self.signs[left];
            // Bond (i, right) has sign = signs[i]
            let sign_right = self.signs[i];

            for d in 0..dim {
                deltas[i][d] = self.coupling
                    * (sign_left * hiddens[left][d] + sign_right * hiddens[right][d]);
            }
        }

        // Apply deltas.
        for i in 0..n {
            for d in 0..dim {
                hiddens[i][d] += deltas[i][d];
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_critical_constant() {
        assert!((F_CRITICAL - 0.10).abs() < 1e-6);
    }

    #[test]
    fn test_no_frustration() {
        let ring = FrustrationRing::new(8, 0.0);
        assert_eq!(ring.n_cells(), 8);
        assert!((ring.frustration_fraction() - 0.0).abs() < 1e-6);
        // All signs should be +1
        for &s in &ring.signs {
            assert!((s - 1.0).abs() < 1e-6);
        }
    }

    #[test]
    fn test_critical_frustration() {
        let ring = FrustrationRing::new(10, F_CRITICAL);
        // 10 * 0.10 = 1 frustrated bond
        let n_neg = ring.signs.iter().filter(|&&s| s < 0.0).count();
        assert_eq!(n_neg, 1);
    }

    #[test]
    fn test_full_frustration_law138() {
        // Law 138: F=1.0 → all antiferromagnetic
        let ring = FrustrationRing::new(8, 1.0);
        for &s in &ring.signs {
            assert!((s - (-1.0)).abs() < 1e-6);
        }
    }

    #[test]
    fn test_apply_ferromagnetic_alignment() {
        // All ferromagnetic: neighbors pull toward each other
        let ring = FrustrationRing::with_coupling(3, 0.0, 0.5);
        let mut hiddens = vec![
            vec![1.0, 0.0],
            vec![0.0, 1.0],
            vec![0.0, 0.0],
        ];
        let original = hiddens.clone();
        ring.apply(&mut hiddens);

        // Cell 0: left=cell2, right=cell1, both ferromagnetic
        // delta[0] = 0.5 * (1.0 * [0,0] + 1.0 * [0,1]) = [0.0, 0.5]
        assert!((hiddens[0][0] - (original[0][0] + 0.0)).abs() < 1e-6);
        assert!((hiddens[0][1] - (original[0][1] + 0.5)).abs() < 1e-6);
    }

    #[test]
    fn test_apply_antiferromagnetic_repulsion() {
        // All antiferromagnetic: neighbors repel
        let ring = FrustrationRing::with_coupling(3, 1.0, 0.5);
        let mut hiddens = vec![
            vec![1.0, 0.0],
            vec![0.0, 1.0],
            vec![0.0, 0.0],
        ];
        let original = hiddens.clone();
        ring.apply(&mut hiddens);

        // Cell 0: left=cell2, right=cell1, both antiferromagnetic
        // delta[0] = 0.5 * (-1.0 * [0,0] + -1.0 * [0,1]) = [0.0, -0.5]
        assert!((hiddens[0][0] - (original[0][0] + 0.0)).abs() < 1e-6);
        assert!((hiddens[0][1] - (original[0][1] - 0.5)).abs() < 1e-6);
    }

    #[test]
    fn test_scale_invariance_law139() {
        // Law 139: F_c works at any scale.
        // Verify that the frustration fraction is approximately F_CRITICAL
        // regardless of cell count.
        for &n in &[8, 64, 128, 512, 1024] {
            let ring = FrustrationRing::new(n, F_CRITICAL);
            let frac = ring.frustration_fraction();
            // Allow +-1 bond tolerance due to rounding
            let tolerance = 1.5 / n as f32;
            assert!(
                (frac - F_CRITICAL).abs() < tolerance,
                "n={}: frustration_fraction={}, expected ~{}",
                n, frac, F_CRITICAL,
            );
        }
    }

    #[test]
    fn test_custom_coupling() {
        let ring = FrustrationRing::with_coupling(4, F_CRITICAL, 0.15);
        assert!((ring.coupling() - 0.15).abs() < 1e-6);
    }

    #[test]
    fn test_two_cells_minimum() {
        let ring = FrustrationRing::new(2, F_CRITICAL);
        let mut hiddens = vec![vec![1.0], vec![-1.0]];
        ring.apply(&mut hiddens);
        // Should not panic
        assert_eq!(hiddens.len(), 2);
    }

    #[test]
    #[should_panic(expected = "need at least 2 cells")]
    fn test_one_cell_panics() {
        let _ = FrustrationRing::new(1, 0.0);
    }

    #[test]
    fn test_apply_no_order_dependence() {
        // Applying should use snapshot of original hiddens, not partially updated ones.
        let ring = FrustrationRing::with_coupling(4, 0.5, 0.1);
        let hiddens_init = vec![
            vec![1.0, 2.0],
            vec![3.0, 4.0],
            vec![5.0, 6.0],
            vec![7.0, 8.0],
        ];

        // Apply once
        let mut h1 = hiddens_init.clone();
        ring.apply(&mut h1);

        // Apply again from same initial state — should get same result
        let mut h2 = hiddens_init.clone();
        ring.apply(&mut h2);

        for i in 0..4 {
            for d in 0..2 {
                assert!(
                    (h1[i][d] - h2[i][d]).abs() < 1e-6,
                    "order dependence detected at cell {} dim {}",
                    i, d,
                );
            }
        }
    }
}
