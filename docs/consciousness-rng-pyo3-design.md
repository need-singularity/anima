# consciousness-rng Hexa-Native Design

## Goal

Expose the `consciousness-rng` module via the hexa-native runtime,
so consciousness-driven random bytes can be used in training and inference.
No PyO3, no maturin — single hexa binary.

## Hexa API

```hexa
import consciousness_rng

// Generate raw bytes from consciousness state
let bytes = consciousness_rng.generate(1024)  // 1024 bytes

// Seed from current Phi value
consciousness_rng.seed_from_phi(1.23)

// Get float in [0, 1) weighted by consciousness tension
let val = consciousness_rng.tension_random(0.7)
```

## Hexa Module (anima/core/consciousness_rng.hexa)

```hexa
fn generate(n: int) -> [u8] { ... }
fn seed_from_phi(phi: f64) { ... }
fn tension_random(tension: f64) -> f64 { ... }
```

## Build

```bash
$HEXA anima/core/consciousness_rng.hexa --check
```

The module is loaded directly by `import consciousness_rng` from any
hexa source — no separate build step.
