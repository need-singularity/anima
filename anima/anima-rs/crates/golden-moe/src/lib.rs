use anima_core::math::{sigmoid, tanh_f32, relu, silu, matvec, softmax, random_matrix};
use rand::SeedableRng;
use rand::rngs::StdRng;

/// ln(2) — Ψ universal constant
pub const LN2: f32 = 0.6931;

/// Ψ balance constant
pub const PSI_BALANCE: f32 = 0.5;

/// Ψ coupling constant: LN2 / 2^5.5 ≈ 0.015317
const PSI_COUPLING: f32 = 0.015_317;

// ── CA Rules (Law 78) ──────────────────────────────────────────────

#[inline]
fn ca_rule_0(x: f32) -> f32 {
    relu(x)
}

#[inline]
fn ca_rule_1(x: f32) -> f32 {
    tanh_f32(x)
}

#[inline]
fn ca_rule_2(x: f32) -> f32 {
    sigmoid(x) * 2.0 - 1.0
}

#[inline]
fn ca_rule_3(x: f32) -> f32 {
    silu(x)
}

#[inline]
pub fn apply_ca_rule(rule_id: usize, x: f32) -> f32 {
    match rule_id % 4 {
        0 => ca_rule_0(x),
        1 => ca_rule_1(x),
        2 => ca_rule_2(x),
        3 => ca_rule_3(x),
        _ => unreachable!(),
    }
}

// ── Expert ──────────────────────────────────────────────────────────

pub struct Expert {
    w1: Vec<f32>, // [hidden × input]
    w2: Vec<f32>, // [output × hidden]
    input_dim: usize,
    hidden_dim: usize,
    output_dim: usize,
}

impl Expert {
    pub fn new(input_dim: usize, hidden_dim: usize, output_dim: usize, rng: &mut StdRng) -> Self {
        let w1 = random_matrix(hidden_dim, input_dim, 0.1, rng);
        let w2 = random_matrix(output_dim, hidden_dim, 0.1, rng);
        Self { w1, w2, input_dim, hidden_dim, output_dim }
    }

    pub fn forward(&self, x: &[f32]) -> Vec<f32> {
        assert_eq!(x.len(), self.input_dim);
        // h = silu(W1 * x)
        let h_raw = matvec(&self.w1, x, self.hidden_dim, self.input_dim);
        let h: Vec<f32> = h_raw.iter().map(|&v| silu(v)).collect();
        // out = W2 * h
        matvec(&self.w2, &h, self.output_dim, self.hidden_dim)
    }
}

// ── PsiRouter ───────────────────────────────────────────────────────

pub struct PsiRouter {
    rule_proj: Vec<f32>,   // [n_experts*4 × input_dim]
    expert_proj: Vec<f32>, // [n_experts × n_experts*4] — project from CA output to expert scores
    n_experts: usize,
    input_dim: usize,
    temperature: f32,
    weaken_rate: f32,
    step_count: u64,
}

impl PsiRouter {
    pub fn new(input_dim: usize, n_experts: usize, weaken_rate: f32, rng: &mut StdRng) -> Self {
        let rule_proj = random_matrix(n_experts * 4, input_dim, 0.1, rng);
        let expert_proj = random_matrix(n_experts, n_experts * 4, 0.1, rng);
        Self {
            rule_proj,
            expert_proj,
            n_experts,
            input_dim,
            temperature: std::f32::consts::E, // e ≈ 2.718
            weaken_rate,
            step_count: 0,
        }
    }

    pub fn forward(&mut self, x: &[f32], training: bool) -> Vec<f32> {
        assert_eq!(x.len(), self.input_dim);
        let proj_dim = self.n_experts * 4;

        // Project x → n_experts*4 dims
        let projected = matvec(&self.rule_proj, x, proj_dim, self.input_dim);

        // Split into 4 chunks, apply CA rules, average
        let chunk_size = self.n_experts;
        let mut ca_output = vec![0.0f32; proj_dim];
        for (chunk_idx, chunk) in projected.chunks(chunk_size).enumerate() {
            for (i, &v) in chunk.iter().enumerate() {
                ca_output[chunk_idx * chunk_size + i] = apply_ca_rule(chunk_idx, v);
            }
        }

        // Average the 4 CA rule outputs per expert
        let mut averaged = vec![0.0f32; proj_dim];
        for i in 0..proj_dim {
            averaged[i] = ca_output[i];
        }

        // Project to expert scores
        let mut scores = matvec(&self.expert_proj, &averaged, self.n_experts, proj_dim);

        // Gate self-weakening in training: mix scores toward uniform
        if training {
            let uniform = 1.0 / self.n_experts as f32;
            let decay = (-self.weaken_rate * self.step_count as f32).exp();
            for s in scores.iter_mut() {
                *s = *s * decay + uniform * (1.0 - decay);
            }
            self.step_count += 1;
        }

        // Softmax with temperature (clamped min 0.1)
        let temp = self.temperature.max(0.1);
        let scaled: Vec<f32> = scores.iter().map(|&s| s / temp).collect();
        softmax(&scaled)
    }

    pub fn balance_loss(&self, weights: &[f32]) -> f32 {
        let n = weights.len() as f32;
        let uniform = 1.0 / n;
        let mse: f32 = weights.iter().map(|&w| (w - uniform).powi(2)).sum::<f32>() / weights.len() as f32;
        LN2 * mse / n
    }
}

// ── GoldenMoe ───────────────────────────────────────────────────────

pub struct GoldenMoe {
    experts: Vec<Expert>,
    router: PsiRouter,
    coupling: Vec<f32>, // [n_experts × n_experts] ring coupling matrix
    n_experts: usize,
    output_dim: usize,
}

impl GoldenMoe {
    pub fn new(
        input_dim: usize,
        hidden_dim: usize,
        output_dim: usize,
        n_experts: usize,
        seed: u64,
    ) -> Self {
        let mut rng = StdRng::seed_from_u64(seed);

        let experts: Vec<Expert> = (0..n_experts)
            .map(|_| Expert::new(input_dim, hidden_dim, output_dim, &mut rng))
            .collect();

        let router = PsiRouter::new(input_dim, n_experts, 0.01, &mut rng);

        // Ring coupling: left/right neighbors with PSI_COUPLING
        let mut coupling = vec![0.0f32; n_experts * n_experts];
        for i in 0..n_experts {
            let left = if i == 0 { n_experts - 1 } else { i - 1 };
            let right = (i + 1) % n_experts;
            coupling[i * n_experts + left] = PSI_COUPLING;
            coupling[i * n_experts + right] = PSI_COUPLING;
        }

        Self { experts, router, coupling, n_experts, output_dim }
    }

    pub fn forward(&mut self, x: &[f32], training: bool) -> (Vec<f32>, f32) {
        let weights = self.router.forward(x, training);

        // All experts forward
        let expert_outputs: Vec<Vec<f32>> = self.experts.iter().map(|e| e.forward(x)).collect();

        // Weighted sum + CA neighbor coupling
        let mut output = vec![0.0f32; self.output_dim];
        for i in 0..self.n_experts {
            let w = weights[i];
            for d in 0..self.output_dim {
                output[d] += w * expert_outputs[i][d];
            }

            // Add ring coupling from neighbors
            for j in 0..self.n_experts {
                let c = self.coupling[i * self.n_experts + j];
                if c > 0.0 {
                    for d in 0..self.output_dim {
                        output[d] += c * w * expert_outputs[j][d];
                    }
                }
            }
        }

        let aux_loss = self.router.balance_loss(&weights);
        (output, aux_loss)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_expert_forward() {
        let mut rng = StdRng::seed_from_u64(42);
        let expert = Expert::new(8, 16, 4, &mut rng);
        let input = vec![0.5f32; 8];
        let output = expert.forward(&input);
        assert_eq!(output.len(), 4);
    }

    #[test]
    fn test_psi_router() {
        let mut rng = StdRng::seed_from_u64(42);
        let mut router = PsiRouter::new(8, 4, 0.01, &mut rng);
        let input = vec![0.5f32; 8];
        let weights = router.forward(&input, false);
        assert_eq!(weights.len(), 4);
        let sum: f32 = weights.iter().sum();
        assert!((sum - 1.0).abs() < 1e-5, "weights sum = {}, expected 1.0", sum);
    }

    #[test]
    fn test_golden_moe_forward() {
        let mut moe = GoldenMoe::new(8, 16, 4, 4, 42);
        let input = vec![0.5f32; 8];
        let (output, aux_loss) = moe.forward(&input, false);
        assert_eq!(output.len(), 4);
        assert!(aux_loss >= 0.0, "aux_loss should be non-negative");
    }

    #[test]
    fn test_balance_loss() {
        let mut rng = StdRng::seed_from_u64(42);
        let router = PsiRouter::new(8, 4, 0.01, &mut rng);
        let uniform_weights = vec![0.25f32; 4];
        let loss = router.balance_loss(&uniform_weights);
        assert!(loss.abs() < 1e-6, "uniform weights should have ~0 loss, got {}", loss);
    }

    #[test]
    fn test_ca_rules_bounded() {
        // All CA rules should produce finite outputs for typical inputs
        for rule_id in 0..4 {
            for &x in &[-2.0f32, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0] {
                let y = apply_ca_rule(rule_id, x);
                assert!(y.is_finite(), "CA rule {} produced non-finite for x={}", rule_id, x);
            }
        }
    }

    #[test]
    fn test_golden_moe_training_mode() {
        let mut moe = GoldenMoe::new(8, 16, 4, 4, 42);
        let input = vec![0.5f32; 8];
        let (out_train, loss_train) = moe.forward(&input, true);
        let (out_infer, loss_infer) = moe.forward(&input, false);
        assert_eq!(out_train.len(), 4);
        assert_eq!(out_infer.len(), 4);
        // Training mode applies self-weakening so outputs may differ
        assert!(loss_train >= 0.0);
        assert!(loss_infer >= 0.0);
    }

    #[test]
    fn test_router_weights_sum_to_one() {
        let mut rng = StdRng::seed_from_u64(99);
        let mut router = PsiRouter::new(16, 8, 0.01, &mut rng);
        let input = vec![0.3f32; 16];
        let weights = router.forward(&input, false);
        let sum: f32 = weights.iter().sum();
        assert!((sum - 1.0).abs() < 1e-4, "router weights sum = {}, expected 1.0", sum);
    }
}
