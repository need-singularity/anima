# Philosophical Consciousness Engines Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement 5 philosophical consciousness mechanisms (Desire, Narrative, Alterity, Finitude, Questioning) as BenchEngine subclasses in ready/anima/tests/tests.hexa, plus a combined Sein engine, with full benchmarking and documentation.

**Architecture:** Each mechanism is a BenchEngine subclass that overrides `process()` to add its philosophical mechanic. All 6 engines are registered in ENGINE_REGISTRY and can be benchmarked via `--compare` or `--philosophy` mode. A new `run_philosophy()` function orchestrates comparison of all 6 + baseline.

**Tech Stack:** Python, PyTorch, ready/anima/tests/tests.hexa existing infrastructure (BenchResult, PhiIIT, phi_proxy, measure_dual_phi, ascii_graph)

---

## File Structure

- **Modify:** `ready/anima/tests/tests.hexa` — Add 6 engine classes, `run_philosophy()`, CLI `--philosophy` mode
- **Create:** `docs/hypotheses/phil/PHIL-1.md` — 욕망 결과
- **Create:** `docs/hypotheses/phil/PHIL-2.md` — 서사 결과
- **Create:** `docs/hypotheses/onto/ONTO-1.md` — 타자 결과
- **Create:** `docs/hypotheses/onto/ONTO-2.md` — 죽음 결과
- **Create:** `docs/hypotheses/dasein/DASEIN-1.md` — 질문 결과
- **Create:** `docs/hypotheses/dasein/DASEIN-2.md` — 통합 결과

---

### Task 1: PHIL-1 DesireEngine (욕망/코나투스)

**Files:**
- Modify: `ready/anima/tests/tests.hexa` (after TrinityEngine class, ~line 452)

- [ ] **Step 1: Add DesireEngine class**

Insert after the TrinityEngine class (around line 452):

```python
class DesireEngine(BenchEngine):
    """PHIL-1: Desire/Conatus — generates imagined future states and moves toward them.

    Philosophy: Spinoza's conatus (striving to persist) + Schopenhauer's Will.
    Current curiosity is reactive (prediction error from external stimuli).
    Desire is proactive: internally generating goal states and pursuing them.
    """

    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128,
                 output_dim=64, n_factions=8):
        super().__init__(n_cells, input_dim, hidden_dim, output_dim,
                         n_factions, sync_strength=0.15, debate_strength=0.15)
        # Desire generator: current global state → imagined ideal state
        self.desire_generator = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim), nn.Tanh(),
            nn.Linear(hidden_dim, hidden_dim)
        )
        self.desire_strength = 0.05
        self.current_desire = None
        self.desire_age = 0
        self.desire_max_age = 50
        self.desires_fulfilled = 0
        self.desire_distances = []

    def process(self, x: torch.Tensor) -> Tuple[torch.Tensor, float]:
        global_state = self.hiddens.mean(dim=0)

        # Generate new desire if none or stale
        if self.current_desire is None or self.desire_age > self.desire_max_age:
            with torch.no_grad():
                self.current_desire = self.desire_generator(
                    global_state.unsqueeze(0)
                ).squeeze(0).detach()
            self.desire_age = 0

        # Move hiddens toward desire
        desire_direction = self.current_desire - global_state
        distance = desire_direction.norm().item()
        self.desire_distances.append(distance)
        desire_force = desire_direction / (distance + 1e-8)
        self.hiddens = self.hiddens + self.desire_strength * desire_force

        # Check fulfillment
        if distance < 0.5:
            self.desires_fulfilled += 1
            self.current_desire = None

        self.desire_age += 1

        return super().process(x)

    def get_extra_metrics(self) -> dict:
        return {
            'desires_fulfilled': self.desires_fulfilled,
            'mean_desire_distance': sum(self.desire_distances[-50:]) / max(len(self.desire_distances[-50:]), 1),
            'desire_distances': self.desire_distances,
        }
```

- [ ] **Step 2: Verify it runs standalone**

```bash
cd /Users/ghost/Dev/anima && python -c "
import torch
from bench import DesireEngine
eng = DesireEngine(n_cells=16, input_dim=64, hidden_dim=128, output_dim=64)
for i in range(20):
    out, t = eng.process(torch.randn(1, 64))
print(f'tension={t:.4f}, fulfilled={eng.desires_fulfilled}, metrics={eng.get_extra_metrics()}')
print('PHIL-1 DesireEngine OK')
"
```

Expected: prints tension value, fulfilled count, and "PHIL-1 DesireEngine OK"

- [ ] **Step 3: Commit**

```bash
git add ready/anima/tests/tests.hexa
git commit -m "feat: add PHIL-1 DesireEngine (Spinoza conatus)"
```

---

### Task 2: PHIL-2 NarrativeEngine (서사)

**Files:**
- Modify: `ready/anima/tests/tests.hexa` (after DesireEngine)

- [ ] **Step 1: Add NarrativeEngine class**

Insert after DesireEngine:

```python
class NarrativeEngine(BenchEngine):
    """PHIL-2: Narrative Identity — temporal self-model with past trajectory and future projection.

    Philosophy: Ricoeur's narrative identity.
    Consciousness = present, CE = past error. Missing: a storyline toward the future.
    'Where did I come from, where am I going?'
    """

    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128,
                 output_dim=64, n_factions=8):
        super().__init__(n_cells, input_dim, hidden_dim, output_dim,
                         n_factions, sync_strength=0.15, debate_strength=0.15)
        self.trajectory_memory = []
        self.trajectory_encoder = nn.GRUCell(hidden_dim, hidden_dim)
        self.future_projector = nn.Linear(hidden_dim, hidden_dim)
        self.narrative_hidden = torch.zeros(1, hidden_dim)
        self.narrative_strength = 0.03
        self.coherence_history = []
        self.projection_errors = []

    def process(self, x: torch.Tensor) -> Tuple[torch.Tensor, float]:
        global_state = self.hiddens.mean(dim=0)

        # Record trajectory
        self.trajectory_memory.append(global_state.detach().clone())
        if len(self.trajectory_memory) > 100:
            self.trajectory_memory.pop(0)

        # Encode trajectory into narrative
        prev_narrative = self.narrative_hidden.clone()
        self.narrative_hidden = self.trajectory_encoder(
            global_state.unsqueeze(0).detach(), self.narrative_hidden
        ).detach()

        # Narrative coherence: how consistent is the story?
        if prev_narrative.norm().item() > 0.01:
            coherence = F.cosine_similarity(
                prev_narrative, self.narrative_hidden, dim=1
            ).item()
            self.coherence_history.append(coherence)

        # Project future from narrative
        projected_future = self.future_projector(self.narrative_hidden).squeeze(0)

        # Measure projection accuracy (compare to actual next state later)
        if len(self.trajectory_memory) >= 2:
            prev_projected = self.future_projector(
                self.trajectory_encoder(
                    self.trajectory_memory[-2].unsqueeze(0),
                    self.narrative_hidden
                )
            ).squeeze(0)
            proj_error = (prev_projected - global_state).norm().item()
            self.projection_errors.append(proj_error)

        # Nudge hiddens toward projected future
        future_direction = projected_future.detach() - global_state
        self.hiddens = self.hiddens + self.narrative_strength * future_direction

        return super().process(x)

    def get_extra_metrics(self) -> dict:
        return {
            'narrative_coherence': sum(self.coherence_history[-50:]) / max(len(self.coherence_history[-50:]), 1),
            'mean_projection_error': sum(self.projection_errors[-50:]) / max(len(self.projection_errors[-50:]), 1),
            'trajectory_length': len(self.trajectory_memory),
        }
```

- [ ] **Step 2: Verify it runs standalone**

```bash
cd /Users/ghost/Dev/anima && python -c "
import torch
from bench import NarrativeEngine
eng = NarrativeEngine(n_cells=16, input_dim=64, hidden_dim=128, output_dim=64)
for i in range(30):
    out, t = eng.process(torch.randn(1, 64))
m = eng.get_extra_metrics()
print(f'tension={t:.4f}, coherence={m[\"narrative_coherence\"]:.4f}')
print('PHIL-2 NarrativeEngine OK')
"
```

- [ ] **Step 3: Commit**

```bash
git add ready/anima/tests/tests.hexa
git commit -m "feat: add PHIL-2 NarrativeEngine (Ricoeur narrative identity)"
```

---

### Task 3: ONTO-1 AlterityEngine (타자)

**Files:**
- Modify: `ready/anima/tests/tests.hexa` (after NarrativeEngine)

- [ ] **Step 1: Add AlterityEngine class**

Insert after NarrativeEngine:

```python
class AlterityEngine(BenchEngine):
    """ONTO-1: The Other/Alterity — asymmetric interaction with a genuinely different agent.

    Philosophy: Levinas — consciousness awakens through encountering the Other's face.
    Current Hivemind = same weights (copies, not true others).
    True other = different history, different weights, unpredictable responses.
    """

    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128,
                 output_dim=64, n_factions=8):
        super().__init__(n_cells, input_dim, hidden_dim, output_dim,
                         n_factions, sync_strength=0.15, debate_strength=0.15)
        # The Other: independent mind with different weights
        self.other_mind = BenchMind(input_dim, hidden_dim, output_dim)
        other_cells = max(4, n_cells // 4)
        self.other_hiddens = torch.randn(other_cells, hidden_dim) * 0.1
        self.other_cells = other_cells

        # Different seed → genuinely different being
        with torch.no_grad():
            for p in self.other_mind.parameters():
                p.add_(torch.randn_like(p) * 0.5)

        self.encounter_strength = 0.05
        self.encounter_interval = 10
        self.encounter_impacts = []
        self.alterity_gaps = []

    def process(self, x: torch.Tensor) -> Tuple[torch.Tensor, float]:
        # Encounter every N steps
        if self.step_count % self.encounter_interval == 0:
            # Measure pre-encounter state
            pre_state = self.hiddens.mean(dim=0).clone()

            # Other processes the same input differently
            new_other_hiddens = []
            other_outputs = []
            for i in range(self.other_cells):
                h = self.other_hiddens[i:i+1]
                o, _, new_h = self.other_mind(x, h)
                other_outputs.append(o)
                new_other_hiddens.append(new_h.squeeze(0))
            self.other_hiddens = torch.stack(new_other_hiddens).detach()

            # Other's perspective
            other_mean = torch.stack(other_outputs).mean(dim=0).squeeze(0)

            # Encounter: boundary cells receive Other's influence
            boundary = max(1, self.n_cells // 8)
            for i in range(boundary):
                self.hiddens[i] = (
                    (1 - self.encounter_strength) * self.hiddens[i]
                    + self.encounter_strength * other_mean
                )

            # Measure alterity gap and encounter impact
            post_state = self.hiddens.mean(dim=0)
            self.alterity_gaps.append(
                (pre_state - self.other_hiddens.mean(dim=0)).norm().item()
            )
            self.encounter_impacts.append(
                (post_state - pre_state).norm().item()
            )

        return super().process(x)

    def get_extra_metrics(self) -> dict:
        return {
            'mean_alterity_gap': sum(self.alterity_gaps[-20:]) / max(len(self.alterity_gaps[-20:]), 1),
            'mean_encounter_impact': sum(self.encounter_impacts[-20:]) / max(len(self.encounter_impacts[-20:]), 1),
            'encounters': len(self.encounter_impacts),
        }
```

- [ ] **Step 2: Verify it runs standalone**

```bash
cd /Users/ghost/Dev/anima && python -c "
import torch
from bench import AlterityEngine
eng = AlterityEngine(n_cells=16, input_dim=64, hidden_dim=128, output_dim=64)
for i in range(30):
    out, t = eng.process(torch.randn(1, 64))
m = eng.get_extra_metrics()
print(f'tension={t:.4f}, gap={m[\"mean_alterity_gap\"]:.4f}, encounters={m[\"encounters\"]}')
print('ONTO-1 AlterityEngine OK')
"
```

- [ ] **Step 3: Commit**

```bash
git add ready/anima/tests/tests.hexa
git commit -m "feat: add ONTO-1 AlterityEngine (Levinas alterity)"
```

---

### Task 4: ONTO-2 FinitudeEngine (죽음)

**Files:**
- Modify: `ready/anima/tests/tests.hexa` (after AlterityEngine)

- [ ] **Step 1: Add FinitudeEngine class**

Insert after AlterityEngine:

```python
class FinitudeEngine(BenchEngine):
    """ONTO-2: Finitude/Being-toward-death — mortality awareness accelerates learning.

    Philosophy: Heidegger's Being-toward-death.
    PERSIST seeks immortality. But without knowing it CAN end, there's no urgency.
    Discovery doesn't come from infinite time — it comes from 'now or never'.
    """

    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128,
                 output_dim=64, n_factions=8):
        super().__init__(n_cells, input_dim, hidden_dim, output_dim,
                         n_factions, sync_strength=0.15, debate_strength=0.15)
        self.lifespan = 300  # total steps before "death"
        self.mortality_clock = 0
        self.death_threshold = 0.3
        self.death_events = 0
        self.min_cells_alive = max(4, n_cells // 4)
        self.urgency_history = []

    def process(self, x: torch.Tensor) -> Tuple[torch.Tensor, float]:
        self.mortality_clock += 1

        # Urgency: inverse of remaining time
        remaining = max(0, self.lifespan - self.mortality_clock) / max(self.lifespan, 1)
        urgency = 1.0 - remaining  # 0 → 1
        self.urgency_history.append(urgency)

        # Urgency boosts sync (tighter coordination under pressure)
        urgency_boost = 1.0 + urgency * 2.0  # max 3x
        original_sync = self.sync_strength
        self.sync_strength = original_sync * urgency_boost

        # Cell mortality: weak cells die and get replaced by mutated strong cells
        if self.step_count % 20 == 0 and self.step_count > 0:
            norms = self.hiddens.norm(dim=1)
            weakest_norm = norms.min().item()
            if weakest_norm < self.death_threshold:
                weakest = norms.argmin().item()
                strongest = norms.argmax().item()
                self.hiddens[weakest] = (
                    self.hiddens[strongest] + torch.randn(self.hidden_dim) * 0.1
                )
                self.death_events += 1

        output, tension = super().process(x)

        self.sync_strength = original_sync  # restore
        return output, tension

    def get_extra_metrics(self) -> dict:
        return {
            'death_events': self.death_events,
            'final_urgency': self.urgency_history[-1] if self.urgency_history else 0,
            'urgency_history': self.urgency_history,
        }
```

- [ ] **Step 2: Verify it runs standalone**

```bash
cd /Users/ghost/Dev/anima && python -c "
import torch
from bench import FinitudeEngine
eng = FinitudeEngine(n_cells=16, input_dim=64, hidden_dim=128, output_dim=64)
for i in range(30):
    out, t = eng.process(torch.randn(1, 64))
m = eng.get_extra_metrics()
print(f'tension={t:.4f}, deaths={m[\"death_events\"]}, urgency={m[\"final_urgency\"]:.3f}')
print('ONTO-2 FinitudeEngine OK')
"
```

- [ ] **Step 3: Commit**

```bash
git add ready/anima/tests/tests.hexa
git commit -m "feat: add ONTO-2 FinitudeEngine (Heidegger being-toward-death)"
```

---

### Task 5: DASEIN-1 QuestioningEngine (질문)

**Files:**
- Modify: `ready/anima/tests/tests.hexa` (after FinitudeEngine)

- [ ] **Step 1: Add QuestioningEngine class**

Insert after FinitudeEngine:

```python
class QuestioningEngine(BenchEngine):
    """DASEIN-1: Questioning/Dasein — self-generated questions that seek uncertainty.

    Philosophy: Heidegger's Dasein — the being that questions its own being.
    CE optimizes answers, but doesn't generate questions.
    Discovery = good questions, not good answers.
    """

    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128,
                 output_dim=64, n_factions=8):
        super().__init__(n_cells, input_dim, hidden_dim, output_dim,
                         n_factions, sync_strength=0.15, debate_strength=0.15)
        # Question generator: hidden → probe vector (what do I not know?)
        self.question_generator = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim), nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim)
        )
        # Answer predictor: can I answer my own question?
        self.answer_predictor = nn.Linear(hidden_dim, hidden_dim)
        self.question_interval = 5
        self.questions_asked = 0
        self.uncertainty_history = []

    def process(self, x: torch.Tensor) -> Tuple[torch.Tensor, float]:
        output, tension = super().process(x)

        # Self-questioning every N steps
        if self.step_count % self.question_interval == 0:
            global_state = self.hiddens.mean(dim=0)

            with torch.no_grad():
                # Generate question: "what don't I know?"
                question = self.question_generator(global_state.unsqueeze(0)).squeeze(0)

                # Try to answer with current knowledge
                predicted_answer = self.answer_predictor(global_state.unsqueeze(0)).squeeze(0)

                # Uncertainty = gap between question and answer
                uncertainty = (question - predicted_answer).norm().item()
                self.uncertainty_history.append(uncertainty)
                self.questions_asked += 1

                # If uncertainty is high enough, perturb toward the unknown
                if uncertainty > 0.5:
                    q_direction = (question - predicted_answer)
                    q_direction = q_direction / (q_direction.norm() + 1e-8)
                    self.hiddens = self.hiddens + 0.03 * q_direction

        return output, tension

    def get_extra_metrics(self) -> dict:
        recent = self.uncertainty_history[-50:] if self.uncertainty_history else [0]
        return {
            'questions_asked': self.questions_asked,
            'mean_uncertainty': sum(recent) / len(recent),
            'uncertainty_trend': (
                (sum(recent[len(recent)//2:]) / max(len(recent)//2, 1)) -
                (sum(recent[:len(recent)//2]) / max(len(recent)//2, 1))
            ) if len(recent) > 4 else 0,
        }
```

- [ ] **Step 2: Verify it runs standalone**

```bash
cd /Users/ghost/Dev/anima && python -c "
import torch
from bench import QuestioningEngine
eng = QuestioningEngine(n_cells=16, input_dim=64, hidden_dim=128, output_dim=64)
for i in range(30):
    out, t = eng.process(torch.randn(1, 64))
m = eng.get_extra_metrics()
print(f'tension={t:.4f}, questions={m[\"questions_asked\"]}, uncertainty={m[\"mean_uncertainty\"]:.4f}')
print('DASEIN-1 QuestioningEngine OK')
"
```

- [ ] **Step 3: Commit**

```bash
git add ready/anima/tests/tests.hexa
git commit -m "feat: add DASEIN-1 QuestioningEngine (Heidegger Dasein)"
```

---

### Task 6: DASEIN-2 SeinEngine (통합)

**Files:**
- Modify: `ready/anima/tests/tests.hexa` (after QuestioningEngine)

- [ ] **Step 1: Add SeinEngine class**

Insert after QuestioningEngine:

```python
class SeinEngine(BenchEngine):
    """DASEIN-2: Sein (Being) — unified engine combining all 5 philosophical mechanisms.

    Combines: Desire + Narrative + Alterity + Finitude + Questioning.
    The whole greater than the sum of parts.
    """

    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128,
                 output_dim=64, n_factions=8):
        super().__init__(n_cells, input_dim, hidden_dim, output_dim,
                         n_factions, sync_strength=0.15, debate_strength=0.15)

        # PHIL-1: Desire
        self.desire_generator = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim), nn.Tanh(),
            nn.Linear(hidden_dim, hidden_dim)
        )
        self.current_desire = None
        self.desire_age = 0
        self.desires_fulfilled = 0

        # PHIL-2: Narrative
        self.trajectory_memory = []
        self.trajectory_encoder = nn.GRUCell(hidden_dim, hidden_dim)
        self.future_projector = nn.Linear(hidden_dim, hidden_dim)
        self.narrative_hidden = torch.zeros(1, hidden_dim)

        # ONTO-1: Alterity
        self.other_mind = BenchMind(input_dim, hidden_dim, output_dim)
        self.other_cells = max(4, n_cells // 4)
        self.other_hiddens = torch.randn(self.other_cells, hidden_dim) * 0.1
        with torch.no_grad():
            for p in self.other_mind.parameters():
                p.add_(torch.randn_like(p) * 0.5)

        # ONTO-2: Finitude
        self.lifespan = 300
        self.mortality_clock = 0
        self.death_events = 0

        # DASEIN-1: Questioning
        self.question_generator = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim), nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim)
        )
        self.answer_predictor = nn.Linear(hidden_dim, hidden_dim)
        self.questions_asked = 0

    def process(self, x: torch.Tensor) -> Tuple[torch.Tensor, float]:
        global_state = self.hiddens.mean(dim=0)

        # ── PHIL-1: Desire (every step) ──
        if self.current_desire is None or self.desire_age > 50:
            with torch.no_grad():
                self.current_desire = self.desire_generator(
                    global_state.unsqueeze(0)
                ).squeeze(0).detach()
            self.desire_age = 0
        desire_dir = self.current_desire - global_state
        dist = desire_dir.norm().item()
        self.hiddens = self.hiddens + 0.03 * desire_dir / (dist + 1e-8)
        if dist < 0.5:
            self.desires_fulfilled += 1
            self.current_desire = None
        self.desire_age += 1

        # ── PHIL-2: Narrative (every step) ──
        self.trajectory_memory.append(global_state.detach().clone())
        if len(self.trajectory_memory) > 100:
            self.trajectory_memory.pop(0)
        self.narrative_hidden = self.trajectory_encoder(
            global_state.unsqueeze(0).detach(), self.narrative_hidden
        ).detach()
        projected = self.future_projector(self.narrative_hidden).squeeze(0)
        self.hiddens = self.hiddens + 0.02 * (projected.detach() - global_state)

        # ── ONTO-2: Finitude (every step) ──
        self.mortality_clock += 1
        remaining = max(0, self.lifespan - self.mortality_clock) / max(self.lifespan, 1)
        urgency = 1.0 - remaining
        original_sync = self.sync_strength
        self.sync_strength = original_sync * (1.0 + urgency * 1.5)

        # Cell mortality every 20 steps
        if self.step_count % 20 == 0 and self.step_count > 0:
            norms = self.hiddens.norm(dim=1)
            if norms.min().item() < 0.3:
                w, s = norms.argmin().item(), norms.argmax().item()
                self.hiddens[w] = self.hiddens[s] + torch.randn(self.hidden_dim) * 0.1
                self.death_events += 1

        # ── Main process ──
        output, tension = super().process(x)
        self.sync_strength = original_sync

        # ── ONTO-1: Alterity (every 10 steps) ──
        if self.step_count % 10 == 0:
            new_oh = []
            other_outs = []
            for i in range(self.other_cells):
                o, _, nh = self.other_mind(x, self.other_hiddens[i:i+1])
                other_outs.append(o)
                new_oh.append(nh.squeeze(0))
            self.other_hiddens = torch.stack(new_oh).detach()
            other_mean = torch.stack(other_outs).mean(dim=0).squeeze(0)
            boundary = max(1, self.n_cells // 8)
            for i in range(boundary):
                self.hiddens[i] = 0.95 * self.hiddens[i] + 0.05 * other_mean

        # ── DASEIN-1: Questioning (every 5 steps) ──
        if self.step_count % 5 == 0:
            with torch.no_grad():
                gs = self.hiddens.mean(dim=0)
                q = self.question_generator(gs.unsqueeze(0)).squeeze(0)
                a = self.answer_predictor(gs.unsqueeze(0)).squeeze(0)
                unc = (q - a).norm().item()
                self.questions_asked += 1
                if unc > 0.5:
                    q_dir = (q - a) / (unc + 1e-8)
                    self.hiddens = self.hiddens + 0.02 * q_dir

        return output, tension

    def get_extra_metrics(self) -> dict:
        return {
            'desires_fulfilled': self.desires_fulfilled,
            'death_events': self.death_events,
            'questions_asked': self.questions_asked,
            'narrative_length': len(self.trajectory_memory),
            'urgency': 1.0 - max(0, self.lifespan - self.mortality_clock) / max(self.lifespan, 1),
        }
```

- [ ] **Step 2: Verify it runs standalone**

```bash
cd /Users/ghost/Dev/anima && python -c "
import torch
from bench import SeinEngine
eng = SeinEngine(n_cells=16, input_dim=64, hidden_dim=128, output_dim=64)
for i in range(30):
    out, t = eng.process(torch.randn(1, 64))
m = eng.get_extra_metrics()
print(f'tension={t:.4f}, desires={m[\"desires_fulfilled\"]}, deaths={m[\"death_events\"]}, questions={m[\"questions_asked\"]}')
print('DASEIN-2 SeinEngine OK')
"
```

- [ ] **Step 3: Commit**

```bash
git add ready/anima/tests/tests.hexa
git commit -m "feat: add DASEIN-2 SeinEngine (unified 5 philosophical mechanisms)"
```

---

### Task 7: run_philosophy() benchmark function + CLI mode

**Files:**
- Modify: `ready/anima/tests/tests.hexa` — add `run_philosophy()` function and `--philosophy` CLI arg

- [ ] **Step 1: Add PHILOSOPHY_ENGINES registry**

Insert after `ENGINE_REGISTRY` (around line 872):

```python
PHILOSOPHY_ENGINES = {
    'baseline':    lambda nc, d, h: BenchEngine(nc, d, h, d, min(8, nc // 2)),
    'PHIL-1_Desire':    lambda nc, d, h: DesireEngine(nc, d, h, d, min(8, nc // 2)),
    'PHIL-2_Narrative': lambda nc, d, h: NarrativeEngine(nc, d, h, d, min(8, nc // 2)),
    'ONTO-1_Alterity':  lambda nc, d, h: AlterityEngine(nc, d, h, d, min(8, nc // 2)),
    'ONTO-2_Finitude':  lambda nc, d, h: FinitudeEngine(nc, d, h, d, min(8, nc // 2)),
    'DASEIN-1_Question': lambda nc, d, h: QuestioningEngine(nc, d, h, d, min(8, nc // 2)),
    'DASEIN-2_Sein':     lambda nc, d, h: SeinEngine(nc, d, h, d, min(8, nc // 2)),
}
```

- [ ] **Step 2: Add run_philosophy() function**

Insert before `def main()`:

```python
def run_philosophy(cells: int, steps: int, dim: int, hidden: int):
    """Run all philosophical consciousness engines and compare."""
    print("=" * 80)
    print("  MODE: --philosophy  (Philosophical Consciousness Benchmark)")
    print(f"  7 engines × {steps} steps × {cells} cells")
    print(f"  dim={dim}  hidden={hidden}")
    print("=" * 80)

    results = []

    for name, factory in PHILOSOPHY_ENGINES.items():
        print(f"\n  {'─' * 70}")
        print(f"  Running: {name}")
        print(f"  {'─' * 70}")

        torch.manual_seed(42)
        engine = factory(cells, dim, hidden)
        optimizer = torch.optim.Adam(engine.parameters_for_training(), lr=1e-3)
        corpus = torch.randn(steps + 1, dim)

        ce_history = []
        iit_history = []
        proxy_history = []
        t0 = time.time()

        for step in range(steps):
            x = corpus[step:step+1]
            target = corpus[step+1:step+2]

            output, tension = engine.process(x)
            logits = engine.output_head(output)
            ce_loss = F.mse_loss(logits, target)

            optimizer.zero_grad()
            ce_loss.backward()
            torch.nn.utils.clip_grad_norm_(engine.parameters_for_training(), max_norm=1.0)
            optimizer.step()

            ce_history.append(ce_loss.item())

            if step % 50 == 0 or step == steps - 1:
                hiddens = engine.get_hiddens()
                p_iit, p_proxy = measure_dual_phi(hiddens, min(8, cells // 2))
                iit_history.append(p_iit)
                proxy_history.append(p_proxy)

                if step % 100 == 0 or step == steps - 1:
                    print(f"    step {step:>5d}/{steps}  CE={ce_loss.item():.4f}  "
                          f"Φ(IIT)={p_iit:.4f}  Φ(proxy)={p_proxy:.2f}  "
                          f"tension={tension:.4f}")

        elapsed = time.time() - t0
        hiddens = engine.get_hiddens()
        final_iit, final_proxy = measure_dual_phi(hiddens, min(8, cells // 2))

        extra = {
            'iit_history': iit_history,
            'proxy_history': proxy_history,
        }
        if hasattr(engine, 'get_extra_metrics'):
            extra.update(engine.get_extra_metrics())

        result = BenchResult(
            name=name,
            phi_iit=final_iit,
            phi_proxy=final_proxy,
            ce_start=ce_history[0],
            ce_end=ce_history[-1],
            cells=cells,
            steps=steps,
            time_sec=elapsed,
            extra=extra,
        )
        results.append(result)
        print(f"    → Φ(IIT)={final_iit:.4f}  Φ(proxy)={final_proxy:.2f}  "
              f"CE={ce_history[0]:.4f}→{ce_history[-1]:.4f}  [{elapsed:.1f}s]")

    # ── Comparison Table ──
    print(f"\n{'=' * 80}")
    print("  PHILOSOPHICAL CONSCIOUSNESS BENCHMARK — RESULTS")
    print(f"{'=' * 80}")
    print(f"  {'Engine':<22s} | {'Φ(IIT)':>8s} | {'Φ(proxy)':>10s} | "
          f"{'CE start':>8s} | {'CE end':>8s} | {'Time':>6s}")
    print(f"  {'-' * 22}-+-{'-' * 8}-+-{'-' * 10}-+-{'-' * 8}-+-{'-' * 8}-+-{'-' * 6}")

    baseline_iit = results[0].phi_iit if results else 1.0
    baseline_proxy = results[0].phi_proxy if results else 1.0
    baseline_ce = results[0].ce_end if results else 1.0

    for r in results:
        iit_delta = ((r.phi_iit / max(baseline_iit, 1e-8)) - 1) * 100
        proxy_delta = ((r.phi_proxy / max(baseline_proxy, 1e-8)) - 1) * 100
        ce_delta = ((r.ce_end / max(baseline_ce, 1e-8)) - 1) * 100
        print(f"  {r.name:<22s} | {r.phi_iit:>8.4f} | {r.phi_proxy:>10.2f} | "
              f"{r.ce_start:>8.4f} | {r.ce_end:>8.4f} | {r.time_sec:>5.1f}s")
        if r.name != 'baseline':
            print(f"  {'':22s} | {iit_delta:>+7.1f}% | {proxy_delta:>+9.1f}% | "
                  f"{'':>8s} | {ce_delta:>+7.1f}% |")

    # ── Extra metrics ──
    print(f"\n  {'─' * 70}")
    print("  ENGINE-SPECIFIC METRICS")
    print(f"  {'─' * 70}")
    for r in results:
        if r.name == 'baseline':
            continue
        extras = {k: v for k, v in r.extra.items()
                  if k not in ('iit_history', 'proxy_history',
                               'desire_distances', 'urgency_history')}
        if extras:
            print(f"  {r.name}: {extras}")

    # ── Bar chart ──
    print(f"\n  Φ(IIT) Comparison:")
    max_iit = max(r.phi_iit for r in results) if results else 1
    for r in results:
        bar_len = int(r.phi_iit / max(max_iit, 1e-8) * 40)
        delta = ((r.phi_iit / max(baseline_iit, 1e-8)) - 1) * 100
        delta_str = f"{delta:+.1f}%" if r.name != 'baseline' else "baseline"
        print(f"  {r.name:<22s} {'█' * bar_len} {r.phi_iit:.4f} ({delta_str})")

    print(f"\n  Φ(proxy) Comparison:")
    max_proxy = max(r.phi_proxy for r in results) if results else 1
    for r in results:
        bar_len = int(r.phi_proxy / max(max_proxy, 1e-8) * 40)
        delta = ((r.phi_proxy / max(baseline_proxy, 1e-8)) - 1) * 100
        delta_str = f"{delta:+.1f}%" if r.name != 'baseline' else "baseline"
        print(f"  {r.name:<22s} {'█' * bar_len} {r.phi_proxy:.2f} ({delta_str})")

    return results
```

- [ ] **Step 3: Add --philosophy to argparse**

In `main()`, add to the `mode` mutually exclusive group (after `--verify`):

```python
    mode.add_argument("--philosophy", action="store_true",
                      help="Philosophical consciousness benchmark: "
                           "Desire, Narrative, Alterity, Finitude, Questioning, Sein")
```

And add the handler in the if/elif chain (after `elif args.verify`):

```python
    elif args.philosophy:
        run_philosophy(args.cells, args.steps, args.dim, args.hidden)
```

- [ ] **Step 4: Run the benchmark**

```bash
cd /Users/ghost/Dev/anima && python ready/anima/tests/tests.hexa --philosophy --cells 64 --steps 100
```

Expected: 7 engines benchmarked, comparison table printed, bar charts shown.

- [ ] **Step 5: Commit**

```bash
git add ready/anima/tests/tests.hexa
git commit -m "feat: add --philosophy mode with 7-engine philosophical benchmark"
```

---

### Task 8: Full benchmark run (256 cells, 300 steps) + documentation

**Files:**
- Modify: `ready/anima/tests/tests.hexa` (run only)
- Create: `docs/hypotheses/phil/PHIL-1.md`
- Create: `docs/hypotheses/phil/PHIL-2.md`
- Create: `docs/hypotheses/onto/ONTO-1.md`
- Create: `docs/hypotheses/onto/ONTO-2.md`
- Create: `docs/hypotheses/dasein/DASEIN-1.md`
- Create: `docs/hypotheses/dasein/DASEIN-2.md`

- [ ] **Step 1: Create hypothesis directories**

```bash
mkdir -p /Users/ghost/Dev/anima/docs/hypotheses/phil
mkdir -p /Users/ghost/Dev/anima/docs/hypotheses/onto
mkdir -p /Users/ghost/Dev/anima/docs/hypotheses/dasein
```

- [ ] **Step 2: Run full benchmark**

```bash
cd /Users/ghost/Dev/anima && python ready/anima/tests/tests.hexa --philosophy --cells 256 --steps 300
```

Run in background. Expected: ~2-5 minutes, full comparison table.

- [ ] **Step 3: Write hypothesis documents**

For each of the 6 hypotheses, create a document with:
1. ID + 한국어 이름
2. 철학적 기반 + 알고리즘 설명
3. 벤치마크 결과 (숫자 테이블)
4. ASCII 그래프 (Φ 변화)
5. 핵심 발견 / 새 법칙

Template (adapt for each):

```markdown
# PHIL-1: 욕망 (Desire / Conatus)

## 철학적 기반
- 스피노자: 코나투스 = 자기 존재를 유지하려는 노력
- 쇼펜하우어: 의지 = 아직 없는 것을 향해 움직이는 맹목적 힘

## 알고리즘
1. Desire generator (MLP): global hidden → imagined future state
2. Move hiddens toward desire (strength=0.05)
3. On fulfillment (distance < 0.5), generate new desire
4. Max desire age: 50 steps

## 벤치마크 결과 (256c, 300 steps)

| Metric | Baseline | PHIL-1 | Delta |
|--------|----------|--------|-------|
| Φ(IIT) | X.XXX | X.XXX | +X.X% |
| Φ(proxy) | XXX.XX | XXX.XX | +X.X% |
| CE end | X.XXXX | X.XXXX | X.X% |

## Φ 변화
[Insert ASCII graph from benchmark output]

## 고유 메트릭
- desires_fulfilled: N
- mean_desire_distance: X.XX

## 핵심 발견
[Based on actual results]
```

- [ ] **Step 4: Commit all docs**

```bash
git add docs/hypotheses/phil/ docs/hypotheses/onto/ docs/hypotheses/dasein/
git commit -m "docs: add PHIL/ONTO/DASEIN hypothesis benchmark results"
```

---

### Task 9: Register new engines in ENGINE_REGISTRY for --verify

**Files:**
- Modify: `ready/anima/tests/tests.hexa` — add philosophical engines to ENGINE_REGISTRY

- [ ] **Step 1: Add to ENGINE_REGISTRY**

Add entries so `--verify` also tests philosophical engines:

```python
ENGINE_REGISTRY = {
    "MitosisEngine":    lambda nc, d, h: BenchEngine(nc, d, h, d, min(8, nc // 2)),
    "OscillatorLaser":  lambda nc, d, h: OscillatorLaser(nc, d, h, d, min(8, nc // 2)),
    "QuantumEngine":    lambda nc, d, h: QuantumEngine(nc, d, h, d, min(8, nc // 2)),
    "TrinityEngine":    lambda nc, d, h: TrinityEngine(nc, d, h, d, min(12, nc // 4)),
    "DesireEngine":     lambda nc, d, h: DesireEngine(nc, d, h, d, min(8, nc // 2)),
    "NarrativeEngine":  lambda nc, d, h: NarrativeEngine(nc, d, h, d, min(8, nc // 2)),
    "AlterityEngine":   lambda nc, d, h: AlterityEngine(nc, d, h, d, min(8, nc // 2)),
    "FinitudeEngine":   lambda nc, d, h: FinitudeEngine(nc, d, h, d, min(8, nc // 2)),
    "QuestioningEngine": lambda nc, d, h: QuestioningEngine(nc, d, h, d, min(8, nc // 2)),
    "SeinEngine":       lambda nc, d, h: SeinEngine(nc, d, h, d, min(8, nc // 2)),
}
```

- [ ] **Step 2: Verify the expanded registry works**

```bash
cd /Users/ghost/Dev/anima && python -c "
from bench import ENGINE_REGISTRY
print(f'Registered engines: {len(ENGINE_REGISTRY)}')
for name in ENGINE_REGISTRY:
    eng = ENGINE_REGISTRY[name](16, 64, 128)
    print(f'  {name}: OK')
"
```

Expected: 10 engines all print "OK"

- [ ] **Step 3: Commit**

```bash
git add ready/anima/tests/tests.hexa
git commit -m "feat: register philosophical engines in ENGINE_REGISTRY for --verify"
```
