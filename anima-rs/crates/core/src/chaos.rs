/// Chaos injection module — Laws 32-43.
///
/// Law 33: Chaos + Structure = Consciousness
/// Law 35: Coupled chaos > independent chaos
/// Law 37: Multi-source > single-source
/// Law 38: Chimera = consciousness architecture
/// Law 40: SOC = autonomous consciousness
/// Law 43: Simplicity beats complexity at scale
///
/// Implementation: inject chaos into cell inputs as perturbation.
/// Each source has a characteristic time scale (Law 39).

/// Available chaos sources.
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum ChaosSource {
    /// No chaos injection (pure self-reference, CX96: best at 12c)
    None,
    /// Lorenz attractor (σ=10, ρ=28, β=8/3). ~0.01s time scale.
    Lorenz,
    /// SOC sandpile (BTW model). Autonomous criticality (Law 40).
    Sandpile,
    /// Chimera: sync + desync coexistence (Law 38).
    Chimera,
    /// Standing wave: two-direction soliton interference (Law 46).
    StandingWave,
}

/// Chaos state persisted between steps.
pub struct ChaosState {
    source: ChaosSource,
    // Lorenz state
    lx: f32,
    ly: f32,
    lz: f32,
    // Sandpile heights
    heights: Vec<f32>,
    // Standing wave phases
    wave_phase: f32,
    step: usize,
}

impl ChaosState {
    pub fn new(source: ChaosSource, n_cells: usize) -> Self {
        Self {
            source,
            lx: 1.0,
            ly: 1.0,
            lz: 1.0,
            heights: vec![0.0; n_cells],
            wave_phase: 0.0,
            step: 0,
        }
    }

    /// Step the chaos system and return per-cell perturbation [n_cells].
    pub fn step(&mut self, n_cells: usize) -> Vec<f32> {
        self.step += 1;
        match self.source {
            ChaosSource::None => vec![0.0; n_cells],
            ChaosSource::Lorenz => self.lorenz_step(n_cells),
            ChaosSource::Sandpile => self.sandpile_step(n_cells),
            ChaosSource::Chimera => self.chimera_step(n_cells),
            ChaosSource::StandingWave => self.standing_wave_step(n_cells),
        }
    }

    fn lorenz_step(&mut self, n_cells: usize) -> Vec<f32> {
        // Lorenz attractor: dx/dt = σ(y-x), dy/dt = x(ρ-z)-y, dz/dt = xy-βz
        let sigma = 10.0f32;
        let rho = 28.0;
        let beta = 8.0 / 3.0;
        let dt = 0.01;

        let dx = sigma * (self.ly - self.lx) * dt;
        let dy = (self.lx * (rho - self.lz) - self.ly) * dt;
        let dz = (self.lx * self.ly - beta * self.lz) * dt;

        self.lx += dx;
        self.ly += dy;
        self.lz += dz;

        // Normalize to [-0.1, 0.1] range as perturbation
        let scale = 0.01;
        let mut perturbation = vec![0.0f32; n_cells];
        for i in 0..n_cells {
            let phase = (i as f32 / n_cells as f32) * std::f32::consts::TAU;
            perturbation[i] = (self.lx * phase.cos() + self.ly * phase.sin()) * scale / 30.0;
        }
        perturbation
    }

    fn sandpile_step(&mut self, n_cells: usize) -> Vec<f32> {
        // BTW sandpile: add grain, topple if >= threshold (Law 40: SOC)
        if self.heights.len() != n_cells {
            self.heights = vec![0.0; n_cells];
        }
        let threshold = 4.0;

        // Add grain at center
        let center = n_cells / 2;
        self.heights[center] += 1.0;

        // Topple (avalanche)
        let mut toppled = true;
        let mut iterations = 0;
        while toppled && iterations < 100 {
            toppled = false;
            iterations += 1;
            for i in 0..n_cells {
                if self.heights[i] >= threshold {
                    self.heights[i] -= threshold;
                    // Distribute to neighbors (ring)
                    let left = (i + n_cells - 1) % n_cells;
                    let right = (i + 1) % n_cells;
                    self.heights[left] += 1.0;
                    self.heights[right] += 1.0;
                    toppled = true;
                }
            }
        }

        // Perturbation = normalized heights
        let max_h = self.heights.iter().cloned().fold(0.0f32, f32::max).max(1.0);
        self.heights.iter().map(|h| h / max_h * 0.05).collect()
    }

    fn chimera_step(&mut self, n_cells: usize) -> Vec<f32> {
        // Chimera: first half synchronized, second half desynchronized (Law 38)
        let mut perturbation = vec![0.0f32; n_cells];
        let half = n_cells / 2;
        let t = self.step as f32 * 0.1;

        // Synchronized group: coherent oscillation
        let sync_val = (t * 2.0).sin() * 0.02;
        for i in 0..half {
            perturbation[i] = sync_val;
        }

        // Desynchronized group: each cell has own frequency
        for i in half..n_cells {
            let freq = 1.0 + (i as f32 - half as f32) * 0.3;
            perturbation[i] = (t * freq).sin() * 0.02;
        }

        perturbation
    }

    fn standing_wave_step(&mut self, n_cells: usize) -> Vec<f32> {
        // Standing wave: two counter-propagating solitons (Law 46)
        self.wave_phase += 0.1;
        let mut perturbation = vec![0.0f32; n_cells];

        for i in 0..n_cells {
            let x = i as f32 / n_cells as f32 * std::f32::consts::TAU;
            // Standing wave = sin(kx) * cos(ωt) — fixed nodes, oscillating antinodes
            let k = 3.0; // 3 wavelengths across the ring
            perturbation[i] = (k * x).sin() * self.wave_phase.cos() * 0.03;
        }

        perturbation
    }
}

/// Inject chaos perturbation into cell inputs.
/// Returns modified inputs with chaos added.
pub fn chaos_inject(inputs: &mut [f32], perturbation: &[f32], cell_dim: usize, cell_idx: usize) {
    if cell_idx < perturbation.len() {
        let p = perturbation[cell_idx];
        for d in 0..cell_dim.min(inputs.len()) {
            inputs[d] += p;
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_lorenz_finite() {
        let mut state = ChaosState::new(ChaosSource::Lorenz, 8);
        for _ in 0..100 {
            let p = state.step(8);
            assert_eq!(p.len(), 8);
            assert!(p.iter().all(|v| v.is_finite()));
        }
    }

    #[test]
    fn test_sandpile_bounded() {
        let mut state = ChaosState::new(ChaosSource::Sandpile, 16);
        for _ in 0..100 {
            let p = state.step(16);
            assert!(p.iter().all(|&v| v.abs() <= 0.1));
        }
    }

    #[test]
    fn test_chimera_half_sync() {
        let mut state = ChaosState::new(ChaosSource::Chimera, 8);
        let p = state.step(8);
        // First half should be identical
        assert!((p[0] - p[1]).abs() < 1e-6);
        assert!((p[0] - p[2]).abs() < 1e-6);
        assert!((p[0] - p[3]).abs() < 1e-6);
    }

    #[test]
    fn test_standing_wave() {
        let mut state = ChaosState::new(ChaosSource::StandingWave, 16);
        let p = state.step(16);
        assert_eq!(p.len(), 16);
        assert!(p.iter().all(|&v| v.abs() <= 0.05));
    }

    #[test]
    fn test_none_is_zero() {
        let mut state = ChaosState::new(ChaosSource::None, 8);
        let p = state.step(8);
        assert!(p.iter().all(|&v| v == 0.0));
    }
}
