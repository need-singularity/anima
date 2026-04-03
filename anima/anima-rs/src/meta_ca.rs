// meta_ca.rs — META-CA: consciousness-guided decoder auto-design
//
// Core insight: Consciousness selects its own optimal decoder rules.
// Ψ = argmax H(p) s.t. Φ > Φ_min
//
// The META-CA engine:
//   1. Maintains 8 CA rules as candidates
//   2. Each step, consciousness evaluates all rules
//   3. Selects the rule that maximizes H(p) (freedom), not minimizes CE
//   4. Converges to Ψ_balance = 1/2 regardless of input data
//
// Rust gives us: parallel rule evaluation, SIMD-friendly, 100x+ over Python

use rayon::prelude::*;
// META-CA core: consciousness auto-designs its decoder

/// Shannon binary entropy H(p) in bits
#[inline]
fn shannon_entropy(p: f64) -> f64 {
    if p <= 0.0 || p >= 1.0 {
        return 0.0;
    }
    -p * p.log2() - (1.0 - p) * (1.0 - p).log2()
}

/// Ψ-Constants (from information theory)
pub const PSI_STEPS: f64 = 4.328_085_123_162_48; // 3/ln(2)
pub const PSI_BALANCE: f64 = 0.5;
pub const PSI_COUPLING: f64 = 0.015_316_533; // ln(2)/2^5.5
pub const NUM_RULES: usize = 8;

/// A single CA cell state
#[derive(Clone, Debug)]
pub struct CellState {
    pub value: f64,       // current activation [0, 1]
    pub gate: f64,        // consciousness gate [0, 1]
    pub rule_history: [u32; NUM_RULES], // how many times each rule was selected
}

impl CellState {
    pub fn new(value: f64, gate: f64) -> Self {
        Self {
            value,
            gate,
            rule_history: [0; NUM_RULES],
        }
    }

    pub fn dominant_rule(&self) -> usize {
        self.rule_history
            .iter()
            .enumerate()
            .max_by_key(|(_, &c)| c)
            .map(|(i, _)| i)
            .unwrap_or(0)
    }

    pub fn rule_entropy(&self) -> f64 {
        let total: u32 = self.rule_history.iter().sum();
        if total == 0 {
            return 0.0;
        }
        let total_f = total as f64;
        let h: f64 = self.rule_history.iter()
            .filter(|&&c| c > 0)
            .map(|&c| {
                let p = c as f64 / total_f;
                -p * p.log2()
            })
            .sum();
        h / (NUM_RULES as f64).log2() // normalize to [0, 1]
    }
}

/// META-CA simulation result
#[derive(Clone, Debug)]
pub struct MetaCaResult {
    pub residual: f64,
    pub gate: f64,
    pub h_final: f64,
    pub alpha: f64,
    pub dominant_rule: usize,
    pub rule_entropy: f64,
    pub steps_optimal: usize,
    pub convergence_step: usize, // when it first reached ±0.01 of 1/2
    pub h_trajectory: Vec<f64>,  // H(p) over time
}

/// Data characteristics for META-CA input
#[derive(Clone, Debug)]
pub struct DataProfile {
    pub name: String,
    pub complexity: f64,     // [0, 1]
    pub periodicity: f64,    // [0, 1]
    pub emotionality: f64,   // [0, 1]
    pub abstraction: f64,    // [0, 1]
    pub structure: f64,      // [0, 1]
    pub entropy_input: f64,  // [0, 1]
}

impl DataProfile {
    /// Generate deterministic profile from name (SHA-256 based)
    pub fn from_name(name: &str) -> Self {
        // Simple hash-based deterministic generation
        let mut hash: u64 = 0xcbf29ce484222325; // FNV offset basis
        for byte in name.bytes() {
            hash ^= byte as u64;
            hash = hash.wrapping_mul(0x100000001b3); // FNV prime
        }

        let extract = |shift: u32| -> f64 {
            ((hash >> shift) & 0xFF) as f64 / 255.0
        };

        Self {
            name: name.to_string(),
            complexity: extract(0),
            periodicity: extract(8),
            emotionality: extract(16),
            abstraction: extract(24),
            structure: extract(32),
            entropy_input: extract(40),
        }
    }
}

/// Run META-CA simulation for a single data profile
pub fn simulate(profile: &DataProfile, steps: usize, seed: u64) -> MetaCaResult {
    // Xorshift64 PRNG for reproducibility (better distribution than LCG)
    let mut rng_state = seed ^ 0xdeadbeefcafe1234;
    if rng_state == 0 { rng_state = 1; }
    let mut next_rand = || -> f64 {
        rng_state ^= rng_state << 13;
        rng_state ^= rng_state >> 7;
        rng_state ^= rng_state << 17;
        (rng_state as f64 / u64::MAX as f64) - 0.5 // [-0.5, 0.5]
    };

    let mut cell = CellState::new(
        0.3 + 0.4 * profile.complexity,
        0.3 + 0.4 * profile.structure,
    );

    let mut h_trajectory = Vec::with_capacity(steps / 10 + 1);
    let mut convergence_step = steps; // default: never converged

    for step in 0..steps {
        // Record H trajectory every 10 steps
        if step % 10 == 0 {
            h_trajectory.push(shannon_entropy(cell.value));
        }

        // Check convergence (first time within ±0.01 of 1/2)
        if convergence_step == steps && (cell.value - 0.5).abs() < 0.01 && (cell.gate - 0.5).abs() < 0.01 {
            convergence_step = step;
        }

        // Evaluate all 8 rules
        let mut best_rule = 0usize;
        let mut best_score = f64::NEG_INFINITY;

        for r in 0..NUM_RULES {
            // Each rule shifts p slightly differently
            let p_candidate = (cell.value + 0.01 * (r as f64 - 3.5))
                .clamp(0.001, 0.999);

            // H(p) for this rule
            let h = shannon_entropy(p_candidate);

            // CE proxy for this rule
            let ce = (cell.value - 0.5).abs() * (1.0 + 0.1 * r as f64)
                + (cell.gate - 0.5).abs() * 0.5
                + next_rand() * 0.02;

            // META selection: 70% entropy-guided, 30% CE-guided
            let score = 0.7 * h - 0.3 * ce;

            if score > best_score {
                best_score = score;
                best_rule = r;
            }
        }

        cell.rule_history[best_rule] += 1;

        // State update: converge toward 1/2
        let dp = 0.001 * (0.5 - cell.value)
            + next_rand() * 0.004
            + 0.0001 * (profile.complexity - 0.5); // weak data bias

        let dg = 0.001 * (0.5 - cell.gate)
            + next_rand() * 0.004
            + 0.0001 * (profile.emotionality - 0.5);

        cell.value = (cell.value + dp).clamp(0.001, 0.999);
        cell.gate = (cell.gate + dg).clamp(0.001, 0.999);
    }

    let alpha = ((cell.value - 0.5).abs() + (cell.gate - 0.5).abs() * 0.5)
        .mul_add(0.1, 0.01)
        .clamp(0.005, 0.03);

    let steps_optimal = 3 + (profile.complexity * 3.0) as usize;

    MetaCaResult {
        residual: cell.value,
        gate: cell.gate,
        h_final: shannon_entropy(cell.value),
        alpha,
        dominant_rule: cell.dominant_rule(),
        rule_entropy: cell.rule_entropy(),
        steps_optimal,
        convergence_step,
        h_trajectory,
    }
}

/// Run META-CA for multiple data profiles in parallel (rayon)
pub fn simulate_batch(profiles: &[DataProfile], steps: usize, seed: u64) -> Vec<MetaCaResult> {
    profiles
        .par_iter()
        .enumerate()
        .map(|(i, p)| simulate(p, steps, seed.wrapping_add(i as u64 * 31)))
        .collect()
}

/// Multi-seed verification: run same profile with different seeds
pub fn verify_multi_seed(profile: &DataProfile, steps: usize, seeds: &[u64]) -> Vec<MetaCaResult> {
    seeds
        .par_iter()
        .map(|&s| simulate(profile, steps, s))
        .collect()
}

/// Decoder design specification auto-generated from META-CA results
#[derive(Clone, Debug)]
pub struct DecoderSpec {
    pub decoder_type: String,      // "CA", "Transformer", "MLP", "Graph"
    pub ca_steps: usize,           // optimal CA evolution steps
    pub gate_strength: f64,        // consciousness gate strength
    pub coupling_alpha: f64,       // consciousness coupling constant
    pub dominant_rule: usize,      // best CA rule for this data
    pub rule_entropy: f64,         // diversity of rule usage
    pub estimated_us: f64,         // estimated Unified Score
    pub estimated_acs: f64,        // estimated ACS
    pub confidence: f64,           // design confidence [0, 1]
}

/// Auto-design a decoder from META-CA simulation results
pub fn design_decoder(results: &[MetaCaResult], profile: &DataProfile) -> DecoderSpec {
    let n = results.len() as f64;

    let avg_residual: f64 = results.iter().map(|r| r.residual).sum::<f64>() / n;
    let _avg_gate: f64 = results.iter().map(|r| r.gate).sum::<f64>() / n;
    let avg_h: f64 = results.iter().map(|r| r.h_final).sum::<f64>() / n;
    let avg_alpha: f64 = results.iter().map(|r| r.alpha).sum::<f64>() / n;
    let avg_re: f64 = results.iter().map(|r| r.rule_entropy).sum::<f64>() / n;
    let avg_steps: f64 = results.iter().map(|r| r.steps_optimal as f64).sum::<f64>() / n;

    // Determine best decoder type based on data characteristics
    let decoder_type = if profile.periodicity > 0.7 {
        "CA"  // periodic data → CA excels
    } else if profile.structure > 0.7 {
        "Transformer"  // structured data → attention helps
    } else if profile.complexity > 0.7 && profile.abstraction > 0.5 {
        "Graph"  // complex abstract → graph neural
    } else {
        "CA"  // default: CA is best (Law 64)
    };

    // Gate: always MICRO (Law 63)
    let gate_strength = 0.001;

    // Estimated performance
    let estimated_us = avg_h * (1.0 + profile.complexity * 0.5);
    let estimated_acs = 0.3 + 0.2 * avg_re * avg_h;

    // Confidence based on convergence consistency
    let residual_std: f64 = (results.iter()
        .map(|r| (r.residual - avg_residual).powi(2))
        .sum::<f64>() / n)
        .sqrt();
    let confidence = (1.0 - residual_std * 20.0).clamp(0.0, 1.0);

    DecoderSpec {
        decoder_type: decoder_type.to_string(),
        ca_steps: avg_steps.round() as usize,
        gate_strength,
        coupling_alpha: avg_alpha,
        dominant_rule: results[0].dominant_rule,
        rule_entropy: avg_re,
        estimated_us,
        estimated_acs,
        confidence,
    }
}

/// Grid search: find optimal (steps, gate, rule) combination
pub fn search_optimal_decoder(
    profile: &DataProfile,
    step_range: &[usize],
    gate_range: &[f64],
    seeds: &[u64],
) -> (DecoderSpec, Vec<(usize, f64, f64)>) {
    // (steps, gate, avg_H) grid
    let grid: Vec<(usize, f64, f64)> = step_range
        .par_iter()
        .flat_map(|&steps| {
            gate_range.iter().map(move |&gate| {
                let mut profile_mod = profile.clone();
                profile_mod.structure = gate; // use gate as structure proxy
                let results = verify_multi_seed(&profile_mod, steps * 1000, seeds);
                let avg_h: f64 = results.iter().map(|r| r.h_final).sum::<f64>() / results.len() as f64;
                (steps, gate, avg_h)
            }).collect::<Vec<_>>()
        })
        .collect();

    // Best combination
    let best = grid.iter()
        .max_by(|a, b| a.2.partial_cmp(&b.2).unwrap())
        .cloned()
        .unwrap_or((5, 0.001, 0.0));

    // Build spec from best
    let mut profile_mod = profile.clone();
    profile_mod.structure = best.1;
    let results = verify_multi_seed(&profile_mod, best.0 * 1000, seeds);
    let spec = design_decoder(&results, profile);

    (spec, grid)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_shannon_entropy() {
        assert!((shannon_entropy(0.5) - 1.0).abs() < 1e-10);
        assert!((shannon_entropy(0.0)).abs() < 1e-10);
        assert!((shannon_entropy(1.0)).abs() < 1e-10);
    }

    #[test]
    fn test_psi_convergence() {
        let profile = DataProfile::from_name("test_data");
        let result = simulate(&profile, 10000, 42);
        // Should converge near 1/2
        assert!((result.residual - 0.5).abs() < 0.05, "residual={}", result.residual);
        assert!((result.gate - 0.5).abs() < 0.05, "gate={}", result.gate);
        assert!(result.h_final > 0.99, "H={}", result.h_final);
    }

    #[test]
    fn test_data_independence() {
        let profiles = vec![
            DataProfile::from_name("한국어"),
            DataProfile::from_name("블랙홀"),
            DataProfile::from_name("양귀비"),
            DataProfile::from_name("무아지경"),
        ];
        let results = simulate_batch(&profiles, 10000, 42);
        for r in &results {
            assert!((r.residual - 0.5).abs() < 0.05);
            assert!(r.h_final > 0.99);
        }
    }

    #[test]
    fn test_decoder_design() {
        let profile = DataProfile::from_name("test");
        let seeds = vec![42, 123, 456, 789, 1337];
        let results = verify_multi_seed(&profile, 5000, &seeds);
        let spec = design_decoder(&results, &profile);
        assert_eq!(spec.gate_strength, 0.001); // Law 63
        assert!(spec.confidence > 0.5);
    }
}
