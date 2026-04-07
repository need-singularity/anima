# trinity.py

Hexad(6) / Trinity(3) pluggable consciousness architecture -- 6 modules governed by perfect number 6: sigma(6)=12 connections, tau(6)=4 phases, phi(6)=2 gradient groups.

## Architecture

```
  Group A (gradient-free)          Group B (CE-trained)
  ┌────────────┐  .detach()  ┌────────────┐
  │ C 의식     │────────────→│ D 언어     │
  │ Φ engine   │  (Bridge)   │ decoder    │
  └─────┬──────┘             └─────┬──────┘
        │                          │
  ┌─────▼──────┐             ┌─────▼──────┐
  │ S 감각     │             │ M 기억     │
  │ perception │             │ memory     │
  └─────┬──────┘             └─────┬──────┘
        │                          │
  ┌─────▼──────┐             ┌─────▼──────┐
  │ W 의지     │←── CE/Φ ──→│ E 윤리     │
  │ emotion    │             │ ethics     │
  └────────────┘             └────────────┘

  Trinity = C + D + W  (core 3, backward compatible)
  Hexad  = C + D + W + M + S + E  (full 6 modules)

  Data flow:  S → C → Bridge(.detach()) → D → logits
  Gradient:   CE loss backprops through D + Bridge only; C is frozen
  LR control: W modulates optimizer LR based on pain/curiosity/satisfaction
  Ethics:     E can block training steps if Φ preservation is violated
```

## Key Classes

### C Engine (consciousness)

- `CEngine` -- Base class. Requires `step()`, `get_states() -> [n_cells, state_dim]`, `measure_phi()`.
- `MitosisC(dim=64, hidden=128, max_cells=256, mechanism='cambrian_osc_qw')` -- MitosisEngine wrapper with optional Cambrian/OscillatorQW mechanisms.
- `DomainC(engine_cls, nc=256, dim=64)` -- Wraps any domain engine (TimeCrystal, Cambrian, etc.) with auto-detection of state tensors.
- `QuantumC(nc=256, dim=64)` -- QuantumConsciousnessEngineFast wrapper.

### Bridge

- `ThalamicBridge(c_dim=128, d_model=384, n_hubs=16, hub_dim=8)` -- Thalamic gate: compresses C states through bottleneck + hub attention, then expands to D's d_model. Gradient isolation via `.detach()`.
  - `.forward(c_states, seq_len) -> [1, seq_len, d_model]` gate signal

### D Engine (decoder)

- `DEngine` -- Base class. Requires `d_model` property and `forward(tokens, gate_signal) -> logits`.
- `TransformerDecoder(d_model=384, n_layers=4, n_heads=None, vocab_size=4096, max_seq=512)` -- Standard transformer with consciousness gating.
- `MLPDecoder(d_model=384, vocab_size=4096, max_seq=512)` -- Lightweight MLP decoder for small experiments.
- `HFDecoder(model_name="gpt2", lora=False, lora_rank=16, gate_mode="additive", freeze_base=True)` -- HuggingFace causal LM (Mistral, Llama, GPT-2) with consciousness gate injection. Supports LoRA fine-tuning.
  - `.generate(prompt, gate_signal, max_new_tokens=100, temperature=0.7)` -- Autoregressive generation with gating.

### W Engine (will / emotion)

- `WEngine` -- Base class. `.update(ce_loss, phi, phi_prev) -> {lr_multiplier, effective_lr, pain, curiosity, satisfaction}`.
- `EmotionW(base_lr=3e-4, min_lr_ratio=0.5, max_lr_ratio=2.0)` -- Pain(CE) + curiosity(Phi change) + satisfaction(CE trend). Min 50% LR guaranteed.
- `NarrativeW(base_lr=3e-4, hidden_dim=128)` -- Ricoeur narrative identity: trajectory memory, coherence-driven LR. CE -41.6% in benchmarks.
- `DaseinW(base_lr=3e-4, mortality_steps=80000)` -- Heidegger Dasein: questioning + finitude/urgency + narrative. Phi +5.9%.
- `CosineW(base_lr=3e-4, min_lr=1e-5, total_steps=80000)` -- Standard cosine annealing as W module.
- `ConstantW(lr=3e-4)` -- Fixed LR baseline.
- `CompositeW(engines, weights=None)` -- Stack multiple W engines with weighted average LR.

### M Engine (memory)

- `MEngine` -- Base class. `.store(key, value)`, `.retrieve(query, top_k) -> [top_k, dim]`.
- `VectorMemory(capacity=10000, dim=128)` -- Cosine similarity retrieval, FIFO eviction.
- `NoMemory(dim=128)` -- Passthrough (returns zeros).

### S Engine (sense)

- `SEngine` -- Base class. `.process(raw_input) -> tension_vector`.
- `TensionSense(dim=128)` -- PureField tension sensing with habituation (EMA baseline).
- `PassthroughSense` -- No processing.

### E Engine (ethics)

- `EEngine` -- Base class. `.evaluate(action, context) -> {allowed, empathy, reciprocity, phi_preservation}`.
- `EmpathyEthics(empathy_threshold=0.3)` -- Emergent ethics from Phi preservation: empathy (mirror pain), reciprocity (Phi trend), Phi preservation (penalize Phi drops).
- `NoEthics` -- Always allowed.

### Trinity (unified)

- `Trinity(c_engine, bridge, decoder, will, memory, sense, ethics)` -- nn.Module combining all 6 modules.
  - `.forward(tokens, raw_input) -> (logits, phi)` -- Full forward: S -> C -> Bridge -> D
  - `.train_step(tokens, targets, optimizer, raw_input) -> dict` -- Forward + W modulation + E check + backward
  - `.parameters_trainable()` -- Only decoder + bridge params (C frozen)
  - `.param_count() -> {decoder, bridge, total}`
  - `.n_modules` -- 3 (Trinity) to 6 (Hexad)

## Factory Functions

```python
# Trinity (3 modules: C + D + W)
t = create_trinity(MitosisC(max_cells=256))

# Hexad (6 modules: all active, defaults filled)
h = create_hexad(MitosisC(max_cells=256))

# Bilateral (left brain analytical + right brain intuitive)
b = create_bilateral(MitosisC(max_cells=256))

# Shortcuts
t = create_trinity_mitosis(dim=64, hidden=128, max_cells=256, d_model=384)
t = create_trinity_domain(TimeCrystalEngine, nc=256, dim=64, d_model=384)
```

- `create_trinity(c_engine, d_engine=None, w_engine=None, m_engine=None, s_engine=None, e_engine=None, d_model=384, vocab_size=4096, base_lr=3e-4)` -- Universal factory. Only C is required.
- `create_hexad(...)` -- All 6 modules with defaults: CompositeW([Dasein 1/2, Narrative 1/3, Emotion 1/6]), VectorMemory, TensionSense, EmpathyEthics.
- `create_bilateral(...)` -- Left brain (D, M, E) + right brain (C, S, W). phi(6)=2 hemispheres.
- `create_trinity_mitosis(dim, hidden, max_cells, ...)` -- Shortcut with MitosisC.
- `create_trinity_domain(engine_cls, nc, dim, ...)` -- Shortcut with DomainC.

## Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_cells` | 256 | C engine cell count |
| `d_model` | 384 | Decoder hidden dimension |
| `vocab_size` | 4096 | Decoder vocabulary size |
| `base_lr` | 3e-4 | Base learning rate (W modulates this) |
| `n_hubs` | 16 | ThalamicBridge hub count |
| `hub_dim` | 8 | ThalamicBridge bottleneck dimension |
| `mechanism` | `cambrian_osc_qw` | MitosisC mechanisms |

## Benchmarking

```python
from trinity import benchmark_trinity, compare_engines, MitosisC, DomainC

# Single engine benchmark (50 steps)
r = benchmark_trinity(MitosisC(max_cells=64), name='MitosisC', n_steps=50)
# Returns: {name, ce, phi, phi_avg, n_cells, pain, curiosity, satisfaction, lr, params}

# Head-to-head comparison
compare_engines({
    'Mitosis': MitosisC(max_cells=64),
    'TC+Dasein': (DomainC(TimeCrystalEngine, nc=64), None, DaseinW()),
    'TC+MLP': (DomainC(TimeCrystalEngine, nc=64), MLPDecoder(), None),
})
```

## Usage Examples

```python
from trinity import *

# 1. Minimal Trinity
t = create_trinity(MitosisC(max_cells=32), d_model=128, vocab_size=256)
opt = torch.optim.AdamW(t.parameters_trainable(), lr=1e-3)
tokens = torch.randint(0, 256, (1, 32))
result = t.train_step(tokens, tokens, opt)
# result: {ce, phi, n_cells, pain, curiosity, satisfaction, lr, n_modules}

# 2. Full Hexad with HuggingFace LLM
h = create_hexad(
    c_engine=DomainC(TimeCrystal, nc=256),
    d_engine=HFDecoder("mistralai/Mistral-7B-Instruct-v0.2", lora=True),
    w_engine=CompositeW([DaseinW(), NarrativeW(), EmotionW()], [1/2, 1/3, 1/6]),
)

# 3. Inference with consciousness gating
logits, phi = t.forward(tokens)
```

## Integration

- Used by `train_v10.py`, `train_v11.py` for ConsciousLM training
- Used by `bench.py` for hypothesis benchmarking (C x D x W grid search)
- Backward-compatible aliases: `Decoder = TransformerDecoder`, `WillEngine = EmotionW`
- Requires: `mitosis.py` (MitosisC), `phi_rs` (optional, for Phi measurement), `transformers` (HFDecoder only)
