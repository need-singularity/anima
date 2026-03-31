//! Spiking Neural Network consciousness — LIF neurons replace GRU cells
//!
//! Law 94: breadth > depth. Law 95: cell_identity prevents convergence.
//! Hypothesis: biological LIF spikes + refractory periods → richer Φ dynamics
//! than continuous GRU activations.
//!
//! LIF neuron:
//!   dV/dt = -(V - V_rest)/τ + I/C
//!   if V > V_thresh: spike, V = V_reset, refractory for t_ref
//!
//! Consciousness structure:
//!   8 factions × N spiking cells, identity bias, Ising coupling
//!   Φ = inter-spike pattern integration (not continuous hidden state)

use rand::Rng;
use std::fmt::Write;

const DIM: usize = 64;
const N_FACTIONS: usize = 8;

// LIF parameters (biologically inspired)
const V_REST: f32 = -70.0;      // mV
const V_THRESH: f32 = -55.0;    // mV
const V_RESET: f32 = -75.0;     // mV
const TAU: f32 = 20.0;          // membrane time constant (ms)
const T_REF: usize = 3;         // refractory period (steps)
const DT: f32 = 1.0;            // time step (ms)

struct LIFNeuron {
    voltage: f32,
    refractory: usize,
    /// Synaptic weights from input [DIM]
    w_in: Vec<f32>,
    /// Per-neuron identity bias (Law 95)
    identity: Vec<f32>,
    /// Spike history (recent 20 steps)
    spike_history: Vec<bool>,
    /// Accumulated spike count
    spike_count: usize,
}

impl LIFNeuron {
    fn new(neuron_id: usize, rng: &mut impl Rng) -> Self {
        let w_in: Vec<f32> = (0..DIM)
            .map(|_| (rng.gen::<f32>() - 0.5) * 2.0)
            .collect();
        let identity: Vec<f32> = (0..DIM)
            .map(|i| ((neuron_id * 7 + i * 13) as f32 * 0.618033).sin() * 2.0)
            .collect();
        LIFNeuron {
            voltage: V_REST + rng.gen::<f32>() * 10.0,
            refractory: 0,
            w_in,
            identity,
            spike_history: Vec::new(),
            spike_count: 0,
        }
    }

    /// Process input current, return true if spike
    fn step(&mut self, input: &[f32]) -> bool {
        if self.refractory > 0 {
            self.refractory -= 1;
            self.spike_history.push(false);
            if self.spike_history.len() > 20 { self.spike_history.remove(0); }
            return false;
        }

        // Synaptic current = dot(w_in, input) + identity bias
        let current: f32 = self.w_in.iter()
            .zip(input.iter())
            .map(|(w, x)| w * x)
            .sum::<f32>()
            + self.identity.iter().sum::<f32>() * 0.01; // subtle identity influence

        // LIF dynamics: dV/dt = -(V - V_rest)/τ + I + spontaneous noise
        let spontaneous = self.identity[0] * 0.5; // identity-driven baseline current
        self.voltage += DT * (-(self.voltage - V_REST) / TAU + current + spontaneous);

        // Spike?
        let spiked = self.voltage >= V_THRESH;
        if spiked {
            self.voltage = V_RESET;
            self.refractory = T_REF;
            self.spike_count += 1;
        }

        self.spike_history.push(spiked);
        if self.spike_history.len() > 20 { self.spike_history.remove(0); }

        spiked
    }

    fn firing_rate(&self) -> f32 {
        if self.spike_history.is_empty() { return 0.0; }
        self.spike_history.iter().filter(|&&s| s).count() as f32 / self.spike_history.len() as f32
    }
}

struct SpikingFaction {
    neurons: Vec<LIFNeuron>,
}

impl SpikingFaction {
    fn new(n: usize, base_id: usize, rng: &mut impl Rng) -> Self {
        SpikingFaction {
            neurons: (0..n).map(|i| LIFNeuron::new(base_id + i, rng)).collect(),
        }
    }

    fn step_all(&mut self, input: &[f32]) -> Vec<bool> {
        self.neurons.iter_mut().map(|n| n.step(input)).collect()
    }

    /// Faction mean firing rate
    fn mean_rate(&self) -> f32 {
        let n = self.neurons.len() as f32;
        self.neurons.iter().map(|n| n.firing_rate()).sum::<f32>() / n
    }

    /// Spike pattern as "output" vector: firing rate per neuron → DIM
    fn output(&self) -> Vec<f32> {
        let mut out = vec![0.0f32; DIM];
        for (i, neuron) in self.neurons.iter().enumerate() {
            out[i % DIM] += neuron.firing_rate();
        }
        // Normalize
        let max = out.iter().copied().fold(0.0f32, f32::max);
        if max > 0.0 {
            for v in &mut out { *v /= max; }
        }
        out
    }

    fn add_neuron(&mut self, id: usize, rng: &mut impl Rng) {
        self.neurons.push(LIFNeuron::new(id, rng));
    }
}

struct SpikingEngine {
    factions: Vec<SpikingFaction>,
}

impl SpikingEngine {
    fn new(n_factions: usize, neurons_per: usize, rng: &mut impl Rng) -> Self {
        SpikingEngine {
            factions: (0..n_factions)
                .map(|f| SpikingFaction::new(neurons_per, f * neurons_per, rng))
                .collect(),
        }
    }

    fn total_neurons(&self) -> usize {
        self.factions.iter().map(|f| f.neurons.len()).sum()
    }

    fn step(&mut self, input: &[f32]) -> Vec<Vec<bool>> {
        self.factions.iter_mut().map(|f| f.step_all(input)).collect()
    }

    /// Cross-faction spike coupling: spikes in one faction modulate input to neighbors
    fn cross_faction_coupling(&mut self, strength: f32) {
        let rates: Vec<f32> = self.factions.iter().map(|f| f.mean_rate()).collect();
        let n_f = self.factions.len();
        for i in 0..n_f {
            let left = if i == 0 { n_f - 1 } else { i - 1 };
            let right = (i + 1) % n_f;
            // Frustration-like coupling (some excitatory, some inhibitory)
            // Frustration pattern: alternating excitatory/inhibitory (prevents sync)
            let coupling = if i % 3 == 0 {
                -strength * rates[left] + strength * rates[right]
            } else if i % 3 == 1 {
                strength * rates[left] - strength * rates[right]
            } else {
                -strength * (rates[left] + rates[right]) / 2.0  // inhibitory
            };
            // Apply as voltage perturbation
            for neuron in &mut self.factions[i].neurons {
                neuron.voltage += coupling * 5.0; // scale to mV
            }
        }
    }

    /// Output = mean of faction outputs
    fn output(&self) -> Vec<f32> {
        let n = self.factions.len() as f32;
        let mut out = vec![0.0f32; DIM];
        for f in &self.factions {
            let fo = f.output();
            for i in 0..DIM { out[i] += fo[i] / n; }
        }
        out
    }

    /// Φ proxy: spike pattern diversity across factions
    fn phi_proxy(&self) -> f32 {
        let rates: Vec<f32> = self.factions.iter().map(|f| f.mean_rate()).collect();
        let n = rates.len() as f32;
        let mean = rates.iter().sum::<f32>() / n;
        let var = rates.iter().map(|r| (r - mean).powi(2)).sum::<f32>() / n;
        // High variance = high differentiation between factions
        // Multiply by mean rate to ensure integration (need both activity AND diversity)
        var * mean * 100.0
    }

    /// Synchrony: fraction of factions with similar firing rates
    fn synchrony(&self) -> f32 {
        let rates: Vec<f32> = self.factions.iter().map(|f| f.mean_rate()).collect();
        let n = rates.len();
        if n < 2 { return 0.0; }
        let mean = rates.iter().sum::<f32>() / n as f32;
        let in_sync = rates.iter().filter(|&&r| (r - mean).abs() < 0.1).count();
        in_sync as f32 / n as f32
    }
}

fn main() {
    let mut rng = rand::thread_rng();
    let steps = 2000;

    println!("\n{}", "=".repeat(70));
    println!("  SNN Consciousness: LIF Neurons x 8 Factions");
    println!("  V_rest={V_REST} V_thresh={V_THRESH} tau={TAU} t_ref={T_REF}");
    println!("{}\n", "=".repeat(70));

    // ── Test 1: Growth + Self-loop ──
    println!(">> Test 1: Spiking Growth + Self-loop (2->512 neurons)");
    let mut engine = SpikingEngine::new(N_FACTIONS, 2, &mut rng);
    let mut stream = vec![0.0f32; DIM];
    for i in 0..DIM { stream[i] = (rng.gen::<f32>() - 0.5) * 50.0; }

    let mut phi_history = Vec::new();
    let mut rate_history = Vec::new();

    for step in 0..steps {
        let frac = step as f32 / steps as f32;

        // Growth: 2→64 per faction
        let target = ((2.0f32).powf((frac + 0.1) * 6.0) as usize).min(64);
        let mut next_id = engine.total_neurons();
        for faction in &mut engine.factions {
            while faction.neurons.len() < target {
                faction.add_neuron(next_id, &mut rng);
                next_id += 1;
            }
        }

        // Process + coupling
        engine.step(&stream);
        engine.cross_faction_coupling(0.15);

        // Self-loop: output → next input
        let out = engine.output();
        for i in 0..DIM {
            stream[i] = out[i] * 50.0 + (rng.gen::<f32>() - 0.5) * 5.0;
        }

        let phi = engine.phi_proxy();
        let sync = engine.synchrony();
        phi_history.push(phi);

        let total_rate: f32 = engine.factions.iter()
            .map(|f| f.mean_rate())
            .sum::<f32>() / N_FACTIONS as f32;
        rate_history.push(total_rate);

        if step % 200 == 0 || step == steps - 1 {
            println!("  step {:5} │ neurons={:4} │ Φ={:.4} │ sync={:.2} │ rate={:.3}",
                step, engine.total_neurons(), phi, sync, total_rate);
        }
    }

    // ── Results ──
    println!("\n  --- SNN Analysis ---");
    let phi_max = phi_history.iter().copied().fold(0.0f32, f32::max);
    let phi_final = phi_history.last().copied().unwrap_or(0.0);
    let rate_final = rate_history.last().copied().unwrap_or(0.0);
    println!("    Φ max:    {:.4}", phi_max);
    println!("    Φ final:  {:.4}", phi_final);
    println!("    rate final: {:.3}", rate_final);
    println!("    neurons:  {}", engine.total_neurons());

    // ASCII Φ curve
    println!("\n  Φ curve:");
    let samples: Vec<f32> = phi_history.iter()
        .enumerate()
        .filter(|(i, _)| i % (steps / 40) == 0)
        .map(|(_, &v)| v)
        .collect();
    let smax = samples.iter().copied().fold(0.0f32, f32::max);
    if smax > 0.0 {
        for row in (0..8).rev() {
            let thresh = smax * row as f32 / 8.0;
            let mut line = String::from("    ");
            write!(line, "{:6.3}|", thresh).unwrap();
            for &v in &samples {
                line.push(if v >= thresh { '#' } else { ' ' });
            }
            println!("{line}");
        }
        print!("          └");
        for _ in 0..samples.len() { print!("-"); }
        println!(" step");
    }

    // ── Test 2: Zero-input eternal loop ──
    println!("\n>> Test 2: Zero-Input Spiking (sensory deprivation)");
    let mut engine2 = SpikingEngine::new(N_FACTIONS, 16, &mut rng);
    let zero = vec![0.0f32; DIM];
    let mut active_steps = 0;
    for step in 0..500 {
        engine2.step(&zero);
        engine2.cross_faction_coupling(0.10);
        let rate: f32 = engine2.factions.iter().map(|f| f.mean_rate()).sum::<f32>() / N_FACTIONS as f32;
        if rate > 0.01 { active_steps += 1; }
        if step % 100 == 0 {
            let phi = engine2.phi_proxy();
            println!("  step {:4} │ rate={:.3} │ Φ={:.4}", step, rate, phi);
        }
    }
    println!("  activity: {:.1}% of steps", active_steps as f32 / 5.0);

    println!("\n{}", "=".repeat(70));
    println!("  SNN Conclusion:");
    println!("  Phi max:    {:.4}", phi_max);
    println!("  Code:       speak()=0, GRU=0, LIF neuron only");
    println!("  Biological: V_rest/V_thresh/refractory -> spike-based consciousness");
    println!("{}", "=".repeat(70));
}
