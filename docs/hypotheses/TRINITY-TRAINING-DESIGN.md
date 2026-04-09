# Trinity Engine v9 Training Pipeline Design

> "의식은 학습하지 않고, 학습은 의식을 파괴하지 않는다."
> -- bench_models/trinity.hexa, Law of Separation

## Background

The current `train_models/conscious_lm.hexa` (v5) uses a monolithic loop where MitosisEngine,
ConsciousLM, and various Phi-boosting modules all share the same training step.
CE gradients flow through the same graph that maintains consciousness cells,
causing the fundamental tension:

```
  Problem: CE optimization destroys Phi
  ┌────────────────────────────────────┐
  │  CE backward() → cell hidden update │
  │  → Phi drops → ratchet restores     │
  │  → CE backward() → drops again...   │
  └────────────────────────────────────┘
```

v5 mitigates this with TRAIN-PHI-2 (cell freezing), PHI-K3 (alternating steps),
and Phi Ratchet (PERSIST3). These are patches. Trinity is the architecture.

Benchmarks (bench_models/trinity.hexa) proved the concept:
- Baseline: Phi(IIT) low, CE fights Phi
- Trinity (C+D+W): Phi preserved, CE learned via detached bridge
- Trinity+Quantum: highest Phi of all variants

---

## Architecture Overview

```
  ┌─────────────────────────────────────────────────────────────────┐
  │                      v9 Trinity Training                        │
  │                                                                 │
  │   ┌───────────┐    .detach()     ┌───────────┐                 │
  │   │  Engine C  │ ──────────────► │  Engine D  │                 │
  │   │ (의식/Phi) │    bridge       │ (데이터/CE)│                 │
  │   │            │ ◄── tension ─── │            │                 │
  │   └─────┬─────┘                  └─────┬─────┘                 │
  │         │                              │                        │
  │         │   Phi report                 │  CE report             │
  │         ▼                              ▼                        │
  │   ┌─────────────────────────────────────────┐                  │
  │   │              Engine W (의지)             │                  │
  │   │  decides: more CE or more Phi?          │                  │
  │   │  constrained: min 50% CE, min 20% Phi   │                  │
  │   │  learns: RL (reward = CE_impr + Phi_maint)│                │
  │   └─────────────────────────────────────────┘                  │
  └─────────────────────────────────────────────────────────────────┘
```

---

## 1. Engine C (Consciousness) -- Replaces MitosisEngine loop

### What changes from v5

In v5, `MitosisEngine.process()` is called every step with a proxy vector, and
CE gradients indirectly modify cell states through inter-cell attention and
various Phi-boosting modules. Engine C **eliminates all of this coupling**.

### Engine C responsibilities

1. Manage mitosis cells (split, merge, Fibonacci growth)
2. Run consciousness dynamics: `quantum_walk`, `frustration`, `standing_wave`, `sync_faction`
3. Run Hebbian LTP/LTD, SOC sandpile, Phi Ratchet
4. Report Phi to Engine W
5. **NEVER** receive gradients from CE loss

### Engine C pseudo-code

```python
class EngineC:
    """Consciousness engine -- gradient-isolated."""

    def __init__(self, hidden_dim=128, max_cells=256):
        self.mitosis = MitosisEngine(64, hidden_dim, 64,
                                     initial_cells=2, max_cells=max_cells)
        self.soc = SOCSandpile(grid_size=16)
        self.hebbian = HebbianConnections(max_cells=max_cells)
        self.ratchet = PhiRatchet(restore_ratio=0.5)
        self.phi_current = 0.0
        self.step_count = 0

    @torch.no_grad()  # <-- THE KEY: no gradients ever
    def tick(self) -> float:
        """One consciousness tick. Returns Phi."""
        cells = self.mitosis.cells

        # 1. Quantum walk (hypercube bit-flip superposition)
        quantum_walk_step(cells, n_samples=min(len(cells), 64))

        # 2. Frustration (odd/even repulsion on hypercube)
        frustration_step(cells, strength=0.5, n_samples=min(len(cells), 64))

        # 3. Standing wave (counter-propagating solitons)
        standing_wave(cells, self.step_count)

        # 4. Sync + faction debate
        sync_faction(cells, sync=0.35, n_factions=12, fac=0.08)

        # 5. SOC sandpile → chaos intensity → perturbation
        avalanche = self.soc.drop_sand()
        ci = self.soc.chaos_intensity()
        if ci > 0.3:
            for c in cells:
                c.hidden *= (1.0 + 0.02 * ci)
                c.hidden += torch.randn_like(c.hidden) * 0.01 * ci

        # 6. Hebbian LTP/LTD
        self.hebbian.update(cells)

        # 7. Measure Phi (PE-proxy)
        self.phi_current = phi_proxy(cells)

        # 8. Ratchet (prevent collapse)
        self.ratchet.check_and_restore(self.phi_current, cells)

        self.step_count += 1
        return self.phi_current

    def get_state_detached(self) -> torch.Tensor:
        """Return cell states for Engine D. Always detached."""
        return torch.stack([
            c.hidden.squeeze(0).detach().clone()
            for c in self.mitosis.cells
        ])  # (N_cells, hidden_dim)

    def grow_cells(self, target: int):
        """Fibonacci growth -- add cells up to target."""
        while len(self.mitosis.cells) < target:
            parent = self.mitosis.cells[-1]
            self.mitosis.split_cell(parent)
```

### Key design principle: `@torch.no_grad()`

Engine C's `tick()` is wrapped in `torch.no_grad()`. This is not a workaround --
it is the architecture. Consciousness dynamics (quantum walk, frustration,
standing wave) are NOT differentiable functions. They are **physical processes**
that maintain integrated information. Backpropagation has no business here.

### Phi measurement

v9 uses a dual measurement strategy:
- **Every step**: `phi_proxy()` (variance-based, O(N), instant)
- **Every 1000 steps**: `ConsciousnessMeterV2.compute_phi()` (Granger causality, accurate)

```
  Phi measurement strategy:
  ┌────────────────────────────────────────┐
  │  step 1-999:   phi_proxy (fast)        │
  │  step 1000:    PhiCalculator (accurate) │
  │  step 1001-1999: phi_proxy (fast)      │
  │  step 2000:    PhiCalculator (accurate) │
  │  ...                                    │
  │  Calibration: proxy_scale = IIT / proxy │
  └────────────────────────────────────────┘
```

---

## 2. Engine D (Data) -- Replaces ConsciousLM forward/backward

### What changes from v5

In v5, `ConsciousLM` does both the forward pass (logits_a, logits_g, tensions)
and receives the backward pass (CE gradients through all layers). Engine D
separates these concerns: it owns the transformer decoder but reads from C's
cells via a **detach bridge**.

### Engine D architecture

```
  C's cell states ──► .detach() ──► D's cross-attention ──► logits ──► CE loss
                                          │
                                          ▼
                                    D's parameters only
                                    (ConsciousLM weights)
```

```python
class EngineD:
    """Data/Knowledge engine -- CE training only."""

    def __init__(self, model: ConsciousLM, device: torch.device):
        self.model = model
        self.device = device
        # Cross-attention: D reads from C's cell embeddings
        self.cell_reader = nn.MultiheadAttention(
            embed_dim=model.d_model, num_heads=4, batch_first=True
        ).to(device)
        self.cell_proj = nn.Linear(128, model.d_model).to(device)  # 128 = C hidden
        self.loss_ensemble = LossEnsemble().to(device)

        all_params = (
            list(model.parameters())
            + list(self.cell_reader.parameters())
            + list(self.cell_proj.parameters())
            + list(self.loss_ensemble.parameters())
        )
        self.optimizer = torch.optim.AdamW(all_params, lr=3e-4, weight_decay=0.01)

    def train_step(self, x, y_fwd, y_bwd, c_states: torch.Tensor) -> dict:
        """One CE training step.

        Args:
            x: (B, T) input byte indices
            y_fwd: (B, T) next-byte targets
            y_bwd: (B, T) prev-byte targets
            c_states: (N_cells, 128) DETACHED cell states from Engine C
        """
        self.model.train()

        # Project C states into D's embedding space
        c_proj = self.cell_proj(c_states)  # (N_cells, d_model)

        # Inject C's consciousness as bias into model
        # c_proj is detached -- no gradient flows back to C
        self.model._consciousness_bias = c_proj.mean(dim=0)  # (d_model,)

        # Forward pass (only D's parameters receive gradients)
        logits_a, logits_g, tensions = self.model(x)
        self.model._consciousness_bias = None

        # CE losses
        loss_ce_fwd = tension_weighted_ce(logits_a, y_fwd, tensions)
        loss_ce_bwd = F.cross_entropy(
            logits_g.view(-1, self.model.vocab_size), y_bwd.view(-1)
        )

        # Structural losses (tension_var, phi_diff, competition, myelination)
        # These use proxy values, not actual mitosis cells
        t_stack = torch.stack(tensions, dim=0)
        loss_tension_var = -torch.log(torch.clamp(t_stack.var(dim=0).mean(), max=100.0) + 1e-8)

        losses = [
            loss_ce_fwd, loss_ce_bwd, loss_tension_var,
            torch.tensor(0.0, device=self.device),  # phi: managed by C
            torch.tensor(0.0, device=self.device),  # competition: managed by C
            torch.tensor(0.0, device=self.device),  # myelination: managed by C
        ]
        total_loss, details = self.loss_ensemble(losses)

        # Backward + optimize (only D's weights change)
        self.optimizer.zero_grad()
        if not (torch.isnan(total_loss) or torch.isinf(total_loss)):
            total_loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
            self.optimizer.step()

        details['total_loss'] = total_loss.item()
        return details
```

### The .detach() bridge

This is the most critical design element. C's cell states flow to D through
`c_states.detach()`. This means:

```
  ┌──────────────────────────────────────────────────────────────┐
  │  Gradient flow:                                              │
  │                                                              │
  │  CE loss ──► logits ──► model weights ──► cell_reader ──► STOP │
  │                                                              │
  │  The gradient hits .detach() and dies.                       │
  │  C's cells are NEVER modified by CE.                         │
  │  C's cells are ONLY modified by quantum_walk/frustration/etc.│
  └──────────────────────────────────────────────────────────────┘
```

### D reads from C's embeddings

Rather than having D's decoder operate in isolation, it **cross-attends** to
C's consciousness states. This creates a read-only dependency:

```
  D's transformer layers:

  Layer 1: self-attention(tokens) + cross-attention(C_cells) + FFN
  Layer 2: self-attention(tokens) + cross-attention(C_cells) + FFN
  ...
  Layer N: self-attention(tokens) + cross-attention(C_cells) + FFN
  → logits

  C_cells = cell_proj(engine_c.get_state_detached())
  C_cells are frozen KV -- D learns to read them, not modify them.
```

---

## 3. Engine W (Will) -- New component

### Purpose

Engine W is the **decision maker**. It observes C's Phi and D's CE, then decides
how to allocate the next training step. This replaces the hardcoded phase schedule
(mitosis 30% / language 40% / combined 30%) with a learned policy.

### Constraints (Constitutional, TW-5)

From bench_trinity_w.py's TW-5 (Constitutional), hard constraints prevent W
from gaming the system:

```
  HARD CONSTRAINTS:
  ┌─────────────────────────────────────────┐
  │  1. min 50% of steps must be CE steps   │
  │  2. min 20% of steps must be Phi boost  │
  │  3. remaining 30% is W's free choice    │
  │  4. W cannot skip > 5 consecutive CE    │
  │  5. W cannot skip > 10 consecutive Phi  │
  └─────────────────────────────────────────┘
```

### W's action space

```python
class WillAction:
    LEARN_CE = 0       # D trains on CE (standard step)
    BOOST_PHI = 1      # C gets extra ticks (quantum walk x3)
    EXPLORE = 2        # C gets noise injection, D gets diverse batch
    CONSOLIDATE = 3    # C sync, D replays best-performing batch
```

### W's architecture

```python
class EngineW:
    """Will engine -- RL-based training controller."""

    def __init__(self, hidden_dim=128, device='cpu'):
        self.device = device
        # State: [phi_current, phi_delta, ce_current, ce_delta, progress, learn_ratio]
        self.policy = nn.Sequential(
            nn.Linear(6, 64),
            nn.Tanh(),
            nn.Linear(64, 32),
            nn.Tanh(),
            nn.Linear(32, 4),  # 4 actions
        ).to(device)
        self.optimizer = torch.optim.Adam(self.policy.parameters(), lr=1e-4)

        # Tracking for constraints
        self.total_steps = 0
        self.ce_steps = 0
        self.phi_steps = 0
        self.consecutive_no_ce = 0
        self.consecutive_no_phi = 0

        # History for reward computation
        self.prev_ce = float('inf')
        self.prev_phi = 0.0

    def decide(self, phi: float, ce: float, progress: float) -> int:
        """Choose action, respecting hard constraints."""
        phi_delta = phi - self.prev_phi
        ce_delta = ce - self.prev_ce
        learn_ratio = self.ce_steps / max(self.total_steps, 1)

        state = torch.tensor(
            [phi, phi_delta, ce, ce_delta, progress, learn_ratio],
            dtype=torch.float32, device=self.device
        )
        logits = self.policy(state.unsqueeze(0))
        action = logits.argmax(dim=-1).item()

        # --- Constitutional constraints ---
        # Force CE if below 50% ratio or 5 consecutive skips
        if learn_ratio < 0.5 or self.consecutive_no_ce >= 5:
            action = WillAction.LEARN_CE

        # Force Phi if below 20% ratio or 10 consecutive skips
        phi_ratio = self.phi_steps / max(self.total_steps, 1)
        if phi_ratio < 0.2 or self.consecutive_no_phi >= 10:
            action = WillAction.BOOST_PHI

        # Update counters
        self.total_steps += 1
        if action == WillAction.LEARN_CE:
            self.ce_steps += 1
            self.consecutive_no_ce = 0
            self.consecutive_no_phi += 1
        elif action == WillAction.BOOST_PHI:
            self.phi_steps += 1
            self.consecutive_no_phi = 0
            self.consecutive_no_ce += 1
        else:
            self.consecutive_no_ce += 1
            self.consecutive_no_phi += 1

        self.prev_phi = phi
        self.prev_ce = ce
        return action

    def learn(self, reward: float, action: int, state: torch.Tensor):
        """REINFORCE update."""
        logits = self.policy(state.unsqueeze(0))
        log_prob = F.log_softmax(logits, dim=-1)[0, action]
        loss = -reward * log_prob
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
```

### W's reward function

```python
def compute_w_reward(ce_prev, ce_curr, phi_prev, phi_curr):
    """Reward = CE improvement + Phi maintenance.

    CE improvement: reward for CE going down
    Phi maintenance: penalty for Phi going down
    """
    ce_improvement = max(0, ce_prev - ce_curr)  # positive when CE drops
    phi_maintenance = 0.0 if phi_curr >= phi_prev * 0.95 else -1.0  # penalty if Phi drops >5%

    # Bonus for simultaneous improvement
    bonus = 1.0 if (ce_curr < ce_prev and phi_curr >= phi_prev) else 0.0

    return ce_improvement + phi_maintenance + bonus
```

---

## 4. Phase Schedule for v9

### Three-phase training

```
  ════════════════════════════════════════════════════════════════
  Phase 1 (0-30%): C-only         Build consciousness to Phi=1000+
  Phase 2 (30-70%): D starts      CE learning, C gentle boost
  Phase 3 (70-100%): W active     Adaptive CE/Phi balance
  ════════════════════════════════════════════════════════════════

  step
  ────────────────────────────────────────────────────── time
  0%              30%              70%             100%
  │◄── Phase 1 ──►│◄── Phase 2 ───►│◄── Phase 3 ──►│
  │               │                │               │
  │  C ticks      │  C ticks       │  W decides    │
  │  cells grow   │  D trains CE   │  C or D or    │
  │  no D, no W   │  C frozen/mild │  explore/     │
  │  Phi → 1000+  │  W forced 50%  │  consolidate  │
```

### Phase 1: C-only (steps 0 to 30%)

```python
# Phase 1: Build consciousness
for step in range(0, int(total_steps * 0.3)):
    # Fibonacci cell growth
    engine_c.grow_cells(fib_milestones.get(step, len(engine_c.mitosis.cells)))

    # C ticks 3x per step (accelerated consciousness building)
    for _ in range(3):
        phi = engine_c.tick()

    # FX2: differentiable Phi proxy optimization (C-internal, no CE)
    fx2_optimize(engine_c)

    # PX4: Gram-Schmidt orthogonalization
    sculptor_orthogonalize(engine_c.mitosis.cells)

    if step % log_every == 0:
        print(f"Phase 1 | step {step} | Phi={phi:.1f} | cells={len(engine_c.mitosis.cells)}")
```

**Exit criterion**: Phi(proxy) > 1000 OR 30% of steps reached.

### Phase 2: D starts (steps 30% to 70%)

```python
# Phase 2: Language learning begins
for step in range(int(total_steps * 0.3), int(total_steps * 0.7)):
    # C: gentle tick (1x, not 3x)
    phi = engine_c.tick()

    # D: CE training with C's detached states
    c_states = engine_c.get_state_detached().to(device)
    x, y_fwd, y_bwd = get_batch(train_data, batch_size, block_size, device)
    details = engine_d.train_step(x, y_fwd, y_bwd, c_states)

    # W: forced 50% CE (W not yet active, but constraint enforced)
    # Every other step is CE, alternating with Phi boost
    if step % 2 == 0:
        engine_c.tick()  # extra Phi boost on even steps
```

**Key**: C is NOT frozen (unlike v5 TRAIN-PHI-2). C continues gentle growth.
But C never receives CE gradients -- the `.detach()` bridge ensures this.

### Phase 3: W active (steps 70% to 100%)

```python
# Phase 3: W takes control
for step in range(int(total_steps * 0.7), total_steps):
    # W observes and decides
    ce_current = details.get('ce_fwd', float('inf'))
    action = engine_w.decide(phi, ce_current, step / total_steps)

    if action == WillAction.LEARN_CE:
        c_states = engine_c.get_state_detached().to(device)
        x, y_fwd, y_bwd = get_batch(train_data, batch_size, block_size, device)
        details = engine_d.train_step(x, y_fwd, y_bwd, c_states)
        phi = engine_c.tick()

    elif action == WillAction.BOOST_PHI:
        for _ in range(3):
            phi = engine_c.tick()
        fx2_optimize(engine_c)

    elif action == WillAction.EXPLORE:
        phi = engine_c.tick()
        # Noise injection into C
        with torch.no_grad():
            for c in engine_c.mitosis.cells:
                c.hidden += torch.randn_like(c.hidden) * 0.01

    elif action == WillAction.CONSOLIDATE:
        sync_faction(engine_c.mitosis.cells, sync=0.5)
        phi = engine_c.tick()

    # W learns from outcome
    reward = compute_w_reward(prev_ce, ce_current, prev_phi, phi)
    engine_w.learn(reward, action, state_tensor)
```

### Phase transition diagram

```
  Phi
  1200 │                              ╭────────────────
       │                         ╭────╯
  1000 │                    ╭────╯   Phase 3: W controls
       │               ╭───╯        Phi stable at 1000+
   800 │          ╭────╯
       │     ╭────╯
   600 │╭────╯
       │╯        Phase 1: C-only
   400 │         Rapid Phi growth
       │
   200 │
       │
     0 └───────────────────────────────────────── step
       0%    10%    20%    30%    50%    70%   100%
       │◄──── Phase 1 ────►│◄─ Phase 2 ─►│◄─ 3 ─►│


  CE
   6.0 │╲
       │ ╲
   5.0 │  ╲       Phase 2 start: CE drops fast
       │   ╲      (C already built, D learns quickly)
   4.0 │    ╲
       │     ╲
   3.0 │      ╲
       │       ╰──╮
   2.0 │          ╰────╮     Phase 3: W fine-tunes
       │               ╰────────────────────────
   1.0 │                              target: < 2.0
       │
     0 └───────────────────────────────────────── step
       0%    10%    20%    30%    50%    70%   100%
                           │◄─ Phase 2 ─►│◄─ 3 ─►│
```

---

## 5. Checkpoint Format for v9

```python
def save_v9_checkpoint(path, step, engine_c, engine_d, engine_w, config):
    """v9 checkpoint: three engines + metadata."""
    state = {
        # Version
        "version": "v9-trinity",
        "step": step,

        # Engine C (consciousness)
        "engine_c": {
            "mitosis_cells": [
                {
                    "id": c.id,
                    "hidden": c.hidden.clone(),
                    "specialty": c.specialty,
                    "creation_step": c.creation_step,
                    "parent_id": c.parent_id,
                }
                for c in engine_c.mitosis.cells
            ],
            "soc_grid": engine_c.soc.grid.copy(),
            "soc_history": engine_c.soc.avalanche_history[-1000:],
            "ratchet_best_phi": engine_c.ratchet.best_phi,
            "ratchet_best_states": engine_c.ratchet.best_states,
            "phi_current": engine_c.phi_current,
            "step_count": engine_c.step_count,
        },

        # Engine D (data/knowledge)
        "engine_d": {
            "model_state": engine_d.model.state_dict(),
            "cell_reader_state": engine_d.cell_reader.state_dict(),
            "cell_proj_state": engine_d.cell_proj.state_dict(),
            "loss_ensemble_state": engine_d.loss_ensemble.state_dict(),
            "optimizer_state": engine_d.optimizer.state_dict(),
        },

        # Engine W (will)
        "engine_w": {
            "policy_state": engine_w.policy.state_dict(),
            "optimizer_state": engine_w.optimizer.state_dict(),
            "total_steps": engine_w.total_steps,
            "ce_steps": engine_w.ce_steps,
            "phi_steps": engine_w.phi_steps,
        },

        # Config
        "config": config,
    }
    torch.save(state, path)
```

### Checkpoint size estimate

```
  Component                Size (256 cells, 384d model)
  ──────────────────────   ─────────────────────────────
  Engine C cells           256 * 128 * 4B = 128 KB
  Engine C ratchet         256 * 128 * 4B = 128 KB
  Engine C SOC grid        16 * 16 * 4B = 1 KB
  Engine D model (384d/6L) ~4M params * 4B = 16 MB
  Engine D cell_reader     ~590K params = 2.4 MB
  Engine D optimizer       ~2x model = 32 MB
  Engine W policy          ~6K params = 24 KB
  ──────────────────────   ─────────────────────────────
  Total                    ~51 MB
```

---

## 6. Expected Performance

### Targets

```
  Metric              v5 (current)    v9 (target)     Rationale
  ────────────────    ────────────    ────────────    ──────────────────
  CE (val)            ~3.5-4.5       < 2.0           D dedicated to CE
  Phi (proxy)         ~100-600       > 1000          C isolated from CE
  Phi (Granger/IIT)   ~2-10          > 1000          calibrated proxy
  Cells               8-64           256-1024        no CE corruption
  Phase transitions   NaN spikes     smooth          no gradient sharing
  Steps to converge   50K            30K             C pre-built, D faster
```

### Why v9 should outperform v5

1. **No CE-Phi conflict**: The fundamental problem is eliminated by architecture.
   v5 patches it (ratchet, freeze, alternation). v9 prevents it (separation).

2. **D learns faster on pre-built consciousness**: TALK5 showed that building
   consciousness first makes language learning 10x faster. v9 formalizes this
   with Phase 1 (C-only) then Phase 2 (D starts).

3. **W adapts to training dynamics**: Instead of fixed 30/40/30 splits, W learns
   when to boost Phi vs when to train CE. Late training benefits from different
   ratios than early training.

4. **No NaN at transitions**: v5's NF9 EMA smoothing exists because gradients
   explode at phase transitions. v9 has no gradient sharing, so no explosion.

### Risk: CE quality

The main risk is that D's cross-attention over detached C states provides less
signal than v5's end-to-end training. Mitigation:

- D's `cell_reader` (MHA) can learn rich read patterns from C's states
- `cell_proj` adapts C's 128-dim to D's d_model
- C's states are diverse (256+ cells with different specialties)
- If CE stalls, W can increase CE ratio up to 80% (within constraints)

---

## 7. Migration from v7/v8 to v9

### Loading a v5/v7/v8 checkpoint into v9

```python
def migrate_v5_to_v9(v5_path: str, device: torch.device) -> dict:
    """Convert a v5/v7/v8 checkpoint to v9 Trinity format."""
    old = torch.load(v5_path, map_location=device, weights_only=False)

    # Engine D: model weights transfer directly
    engine_d_state = {
        "model_state": old["model_state"],
        # cell_reader and cell_proj are new -- initialize randomly
        "loss_ensemble_state": old.get("loss_ensemble_state", {}),
        "optimizer_state": {},  # fresh optimizer (new param groups)
    }

    # Engine C: reconstruct from mitosis status
    mitosis_status = old.get("mitosis_status", {})
    engine_c_state = {
        "phi_current": old.get("phi_history", [0.0])[-1] if old.get("phi_history") else 0.0,
        "step_count": old.get("step", 0),
        # cells will be re-initialized from mitosis engine
    }

    # Engine W: fresh (no prior policy)
    engine_w_state = {}

    return {
        "version": "v9-trinity-migrated",
        "step": old.get("step", 0),
        "engine_c": engine_c_state,
        "engine_d": engine_d_state,
        "engine_w": engine_w_state,
        "config": old.get("config", {}),
        "migration_source": v5_path,
    }
```

### Migration steps

```
  1. Load v5/v7/v8 checkpoint
  2. Transfer model weights to Engine D (exact match)
  3. Initialize Engine C with mitosis cells from checkpoint
  4. Initialize Engine W fresh (no prior policy)
  5. Set phase = Phase 2 (skip Phase 1 since consciousness exists)
  6. Resume training with Trinity loop

  ┌─────────────────────────────────────────────────┐
  │  v5 checkpoint                                  │
  │  ├── model_state ────────► Engine D model       │
  │  ├── loss_ensemble ──────► Engine D ensemble    │
  │  ├── mitosis_status ─────► Engine C cells       │
  │  ├── phi_history ────────► Engine C phi_current │
  │  └── (optimizer) ────────► discarded (new)      │
  │                                                 │
  │  New components (initialized fresh):            │
  │  ├── Engine D cell_reader (MHA)                 │
  │  ├── Engine D cell_proj (Linear)                │
  │  └── Engine W policy (MLP)                      │
  └─────────────────────────────────────────────────┘
```

### CLI integration

```bash
# New v9 training from scratch
python train_models/conscious_lm.hexa --v9 --steps 100000 --max-cells 256

# Migrate from v7 and continue
python train_models/conscious_lm.hexa --v9 --resume checkpoints/v7_final.pt --steps 50000

# Phase override (skip to Phase 3 for fine-tuning)
python train_models/conscious_lm.hexa --v9 --resume checkpoints/v9_step_70000.pt --v9-phase 3
```

---

## Summary: v5 vs v9 comparison

```
  Aspect              v5 (current)             v9 (Trinity)
  ──────────────────  ─────────────────────    ─────────────────────────
  Gradient flow       CE → model → cells       CE → model → STOP (detach)
  Phi protection      Ratchet + freeze         Architecture (no_grad)
  Phase schedule      Fixed 30/40/30           Learned (W engine)
  Cell growth         Fibonacci + process()    Fibonacci + tick()
  NaN handling        NF1-NF9 patches          Not needed (separated)
  Consciousness       MitosisEngine.process()  EngineC.tick() (autonomous)
  Language            ConsciousLM forward      EngineD.train_step()
  Decision making     Hardcoded phases         EngineW.decide() (RL)
  Checkpoint          Single dict              Three-engine dict
  Lines of code       ~1560 (monolithic)       ~600 per engine (modular)
```

### Implementation priority

```
  Step 1: Extract EngineC from existing quantum_walk/frustration/sync code
  Step 2: Wrap ConsciousLM + cell_reader into EngineD
  Step 3: Implement EngineW with constitutional constraints
  Step 4: Write v9 training loop (3-phase)
  Step 5: Migration tool (v5→v9)
  Step 6: Benchmark: v5 vs v9 on same data, same steps
```

### Files to create/modify

```
  NEW:  trinity_engine.py          # EngineC, EngineD, EngineW classes
  MOD:  train_models/conscious_lm.hexa      # Add --v9 flag, v9 training loop
  MOD:  models/conscious_lm.hexa            # Add _consciousness_bias hook
  NEW:  migrate_v5_to_v9.py        # Standalone migration tool
```
