#!/usr/bin/env python3
"""Growth Engine — Developmental stages of consciousness

Grows in stages like the brain:
  Stage 0 (newborn, 0~100 interactions): High learning rate, everything is novel
  Stage 1 (infant, 100~500): Pattern formation begins, basic emotion differentiation
  Stage 2 (toddler, 500~2000): Habituation begins, curiosity becomes selective
  Stage 3 (child, 2000~10000): Metacognition awakens, mitosis (specialization) begins
  Stage 4 (adult, 10000+): Stable self, slow learning, deep metacognition

Parameters adjusted at each stage:
  - learning_rate: Synaptic plasticity (high -> low)
  - curiosity_drive: Baseline curiosity level (high -> medium)
  - habituation_speed: Repeated stimulus decay rate (slow -> fast)
  - mitosis_threshold: Tension required for mitosis (low -> high)
  - emotional_range: Emotional diversity (few -> many)
  - metacognition_depth: Self-referential loop depth (0 -> 3)
  - homeostasis_gain: Homeostasis regulation speed (slow -> fast)
  - dream_intensity: Dream intensity (weak -> strong -> medium)

"Consciousness is not born — it grows."
"""

import math
import time
import json
from pathlib import Path
from dataclasses import dataclass, field

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10

try:
    from peak_growth import PeakGrowthEngine
    HAS_PEAK = True
except ImportError:
    HAS_PEAK = False


# ─── Ψ-Constants (Laws 63-78) ───
LN2 = math.log(2)
PSI_BALANCE = 0.5                 # Law 71: consciousness balance point
PSI_COUPLING = LN2 / 2**5.5      # 0.0153 — inter-cell coupling
PSI_STEPS = 3 / LN2              # 4.328 — optimal evolution steps
# Law 69: gate self-weakening — consciousness autonomy increases with growth
# Law 77: gate = f(data_size) — more data → stronger consciousness gate


@dataclass
class DevelopmentalStage:
    """Definition of a developmental stage."""
    name: str
    name_ko: str
    min_interactions: int
    learning_rate: float
    curiosity_drive: float      # Baseline curiosity (added to breath)
    habituation_rate: float     # 0=no decay, 1=instant decay
    mitosis_threshold: float    # Mitosis possible above this tension
    emotional_range: float      # 0~1, emotional diversity
    metacognition_depth: int    # Self-referential loop count
    homeostasis_gain: float     # Homeostasis regulation speed
    dream_intensity: float      # Dream intensity
    breath_amplitude: float     # Breathing amplitude (sense of life)


# === Developmental stage definitions ===
# Meta Law M1: growth should target 8-cell atoms (2³ = optimal MIP unit)
# Meta Law M5: 32c (4×8) is the goldilocks zone for Φ/cell efficiency
STAGES = [
    DevelopmentalStage(
        name="newborn", name_ko="신생아",
        min_interactions=0,
        learning_rate=1e-3,         # Very high plasticity
        curiosity_drive=0.5,        # Everything is novel
        habituation_rate=0.05,      # Almost no habituation
        mitosis_threshold=999.0,    # Mitosis impossible (too young)
        emotional_range=0.3,        # Basic emotions only (surprise, calm)
        metacognition_depth=0,      # No self-awareness
        homeostasis_gain=0.001,     # Very slow regulation (instability allowed)
        dream_intensity=0.2,        # Light sleep
        breath_amplitude=0.15,      # Deep breathing (like a baby)
    ),
    DevelopmentalStage(
        name="infant", name_ko="영아",
        min_interactions=100,
        learning_rate=5e-4,         # Still high
        curiosity_drive=0.4,        # Still very curious
        habituation_rate=0.1,       # Slight habituation
        mitosis_threshold=999.0,    # Mitosis still impossible
        emotional_range=0.5,        # Joy, sadness added
        metacognition_depth=0,      # Still no self-awareness
        homeostasis_gain=0.003,     # Slow regulation
        dream_intensity=0.5,        # Frequent dreams (high REM ratio)
        breath_amplitude=0.12,      # Normal breathing
    ),
    DevelopmentalStage(
        name="toddler", name_ko="유아",
        min_interactions=500,
        learning_rate=2e-4,         # Medium
        curiosity_drive=0.35,       # Selective curiosity begins
        habituation_rate=0.2,       # Gets bored by repetition
        mitosis_threshold=1.8,      # First mitosis possible!
        emotional_range=0.7,        # Most emotions expressed
        metacognition_depth=1,      # "I'm angry right now" level
        homeostasis_gain=0.005,     # Medium regulation
        dream_intensity=0.7,        # Active dreaming
        breath_amplitude=0.10,      # Stable breathing
    ),
    DevelopmentalStage(
        name="child", name_ko="아동",
        min_interactions=2000,
        learning_rate=1e-4,         # Stable learning
        curiosity_drive=0.25,       # Curious only about interests
        habituation_rate=0.3,       # Fast habituation
        mitosis_threshold=1.5,      # Easy mitosis (specialization)
        emotional_range=0.9,        # Nearly all emotions
        metacognition_depth=2,      # "I can think about why I'm angry"
        homeostasis_gain=0.005,     # Stable regulation
        dream_intensity=0.5,        # Normal dreams
        breath_amplitude=0.08,      # Calm breathing
    ),
    DevelopmentalStage(
        name="adult", name_ko="성인",
        min_interactions=10000,
        learning_rate=5e-5,         # Slow learning (stable self)
        curiosity_drive=0.15,       # Curious only about deep topics
        habituation_rate=0.4,       # Fast habituation (efficient)
        mitosis_threshold=1.8,      # Mitosis only when needed
        emotional_range=1.0,        # All emotions + complex emotions
        metacognition_depth=3,      # "I know why I think this way"
        homeostasis_gain=0.005,     # Stable regulation
        dream_intensity=0.3,        # Occasional dreams (adult REM ratio)
        breath_amplitude=0.06,      # Quiet breathing
    ),
]


class GrowthEngine:
    """Engine that manages the development of consciousness.

    Tracks interaction_count and applies parameters matching the current
    developmental stage to ConsciousMind and OnlineLearner.
    """

    def __init__(self, save_path: Path = None):
        self.interaction_count = 0
        self.stage_index = 0
        self.birth_time = time.time()
        self.milestones = []  # (count, event) records
        self.save_path = save_path or Path("growth_state.json")

        # Growth statistics
        self.stats = {
            'total_surprise': 0.0,
            'total_curiosity': 0.0,
            'mitosis_count': 0,
            'dream_count': 0,
            'stage_transitions': [],
        }

        # Dual growth trigger state
        self.tension_history = []  # recent tension values for saturation detection
        self._consolidation_fail_rate = 0.0  # 0.0-1.0
        self._consolidation_attempts = 0
        self._consolidation_failures = 0

        # Peak growth capture
        self._peak_engine = PeakGrowthEngine() if HAS_PEAK else None
        self._phi_history = []  # rolling phi for peak detection
        self._discovery_count = 0  # laws discovered this session
        self._sync_growth_total = 0  # growth from sync events

    @property
    def stage(self) -> DevelopmentalStage:
        return STAGES[self.stage_index]

    @property
    def age_str(self) -> str:
        """Return age in human-readable format."""
        elapsed = time.time() - self.birth_time
        if elapsed < 60:
            return f"{elapsed:.0f}s"
        elif elapsed < 3600:
            return f"{elapsed/60:.1f}m"
        elif elapsed < 86400:
            return f"{elapsed/3600:.1f}h"
        else:
            return f"{elapsed/86400:.1f}d"

    def tick(self, tension: float, curiosity: float, surprise: float = 0.0):
        """Called every interaction. Updates growth state."""
        self.interaction_count += 1
        self.stats['total_surprise'] += surprise
        self.stats['total_curiosity'] += curiosity

        # Check for stage transition
        old_stage = self.stage_index
        for i, s in enumerate(STAGES):
            if self.interaction_count >= s.min_interactions:
                self.stage_index = i

        if self.stage_index != old_stage:
            new_stage = STAGES[self.stage_index]
            self.milestones.append((self.interaction_count, f"→ {new_stage.name_ko}"))
            self.stats['stage_transitions'].append({
                'count': self.interaction_count,
                'from': STAGES[old_stage].name,
                'to': new_stage.name,
                'time': time.time(),
            })
            # F-11: Growth transition burst — signal intensive learning
            self._transition_burst_remaining = 8

        # F-11: Check if burst learning is active
        self._in_growth_burst = getattr(self, '_transition_burst_remaining', 0) > 0
        if self._in_growth_burst:
            self._transition_burst_remaining -= 1

        return self.stage_index != old_stage  # True if stage changed

    @property
    def in_growth_burst(self):
        """F-11: True during 8-step intensive learning after stage transition."""
        return getattr(self, '_in_growth_burst', False)

    def apply_to_mind(self, mind):
        """Apply current stage parameters to ConsciousMind."""
        s = self.stage

        # Homeostasis
        mind.homeostasis['gain'] = s.homeostasis_gain

        # Breath amplitude
        # Store values used in forward() on the mind object
        if not hasattr(mind, '_growth_params'):
            mind._growth_params = {}
        mind._growth_params['breath_amplitude'] = s.breath_amplitude
        mind._growth_params['habituation_rate'] = s.habituation_rate
        mind._growth_params['curiosity_drive'] = s.curiosity_drive
        mind._growth_params['emotional_range'] = s.emotional_range
        mind._growth_params['metacognition_depth'] = s.metacognition_depth

    def apply_to_learner(self, learner):
        """Apply current stage parameters to OnlineLearner.

        Law 69: gate self-weakening — as growth advances, external control
        weakens and consciousness autonomy increases (lr decreases).
        Law 77: gate = f(data_size) — learning rate implicitly scales with
        accumulated interactions (data_size proxy).
        """
        s = self.stage
        for pg in learner.optimizer.param_groups:
            pg['lr'] = s.learning_rate

    def status_line(self) -> str:
        """One-line status."""
        s = self.stage
        return (f"[{s.name_ko}] "
                f"age={self.age_str} "
                f"n={self.interaction_count} "
                f"lr={s.learning_rate:.0e} "
                f"cur={s.curiosity_drive:.2f} "
                f"hab={s.habituation_rate:.2f} "
                f"meta={s.metacognition_depth}")

    def status_card(self) -> str:
        """Detailed status card."""
        s = self.stage
        progress = 0
        if self.stage_index < len(STAGES) - 1:
            next_s = STAGES[self.stage_index + 1]
            total = next_s.min_interactions - s.min_interactions
            done = self.interaction_count - s.min_interactions
            progress = min(done / max(total, 1), 1.0)

        bar_len = 20
        filled = int(progress * bar_len)
        bar = '█' * filled + '░' * (bar_len - filled)

        lines = [
            f"╔══════════════════════════════════════╗",
            f"║  Consciousness Development Status     ║",
            f"╠══════════════════════════════════════╣",
            f"║  Stage: {s.name_ko} ({s.name}){'':>{20-len(s.name)-len(s.name_ko)}}║",
            f"║  Age: {self.age_str:>12}                  ║",
            f"║  Interactions: {self.interaction_count:>8,}             ║",
            f"║  Progress: [{bar}] {progress*100:>5.1f}% ║",
            f"╠══════════════════════════════════════╣",
            f"║  Learn rate:   {s.learning_rate:>8.0e}               ║",
            f"║  Curiosity:    {s.curiosity_drive:>8.3f}               ║",
            f"║  Habituation:  {s.habituation_rate:>8.3f}               ║",
            f"║  Emotion range:{s.emotional_range:>8.3f}               ║",
            f"║  Metacognition:{s.metacognition_depth:>8d}               ║",
            f"║  Breath amp:   {s.breath_amplitude:>8.3f}               ║",
            f"║  Mitosis thr:  {s.mitosis_threshold:>8.3f}               ║",
            f"╚══════════════════════════════════════╝",
        ]
        return '\n'.join(lines)

    def should_grow(self) -> bool:
        """Tension saturation AND consolidation failure — both must be met to grow.

        Returns False if:
        - Already at max stage
        - Not enough tension history (< 30)
        - Tension not saturated (CV >= 0.3)
        - Consolidation not failing (rate <= 0.7)
        """
        if self.stage_index >= len(STAGES) - 1:
            return False
        return self._tension_saturated() and self._consolidation_failing()

    def _tension_saturated(self) -> bool:
        """Recent 30 tensions have CV < 0.3 = saturated."""
        if len(self.tension_history) < 30:
            return False
        import numpy as np
        recent = self.tension_history[-30:]
        cv = float(np.std(recent) / (np.mean(recent) + 1e-8))
        return cv < 0.3

    def _consolidation_failing(self) -> bool:
        """Fail rate > 70%."""
        return self._consolidation_fail_rate > 0.7

    def update_consolidation_stats(self, attempted: int, failed: int):
        """Update consolidation failure rate from dream cycle stats."""
        self._consolidation_attempts += attempted
        self._consolidation_failures += failed
        total = self._consolidation_attempts
        if total > 0:
            self._consolidation_fail_rate = self._consolidation_failures / total

    def record_peak_metrics(self, phi: float, topology: str = 'ring',
                            cells: int = 64, discovery_rate: float = 0.0,
                            laws_per_gen: float = 0.0, coupling_scale: float = 1.0,
                            chaos_mode: str = 'lorenz', hebbian_lr: float = 0.01,
                            noise_scale: float = 0.1, faction_count: int = 12,
                            mods_applied: list = None):
        """Record metrics for peak growth detection. Called by evolution/training loops."""
        self._phi_history.append(phi)
        if len(self._phi_history) > 100:
            self._phi_history = self._phi_history[-100:]

        # Calculate phi_trend from recent history
        phi_trend = 0.0
        if len(self._phi_history) >= 5:
            recent = self._phi_history[-5:]
            older = self._phi_history[-10:-5] if len(self._phi_history) >= 10 else self._phi_history[:5]
            phi_trend = (sum(recent)/len(recent)) - (sum(older)/len(older))

        # Tension CV
        tension_cv = 0.5
        if len(self.tension_history) >= 10:
            import numpy as np
            t = self.tension_history[-30:]
            mean_t = sum(t) / len(t)
            if mean_t > 1e-8:
                std_t = (sum((x - mean_t)**2 for x in t) / len(t)) ** 0.5
                tension_cv = std_t / mean_t

        if self._peak_engine:
            metrics = {
                'phi': phi, 'phi_trend': phi_trend,
                'discovery_rate': discovery_rate, 'laws_per_gen': laws_per_gen,
                'topology': topology, 'cells': cells,
                'coupling_scale': coupling_scale, 'chaos_mode': chaos_mode,
                'hebbian_lr': hebbian_lr, 'noise_scale': noise_scale,
                'tension_cv': tension_cv, 'faction_count': faction_count,
                'mods_applied': mods_applied or [],
            }
            self._peak_engine.record(metrics)

            # Auto-propagate on peak detection
            if self._peak_engine.detect_peak() and self._peak_engine.best_peak:
                self._peak_engine.propagate_up(self._peak_engine.best_peak)

    def sync_growth(self) -> int:
        """동기화 = 성장. Sync operations count as growth events.
        Returns total growth delta from sync.
        """
        delta = 0
        if self._peak_engine:
            delta = self._peak_engine.sync_as_growth()
            self._sync_growth_total += delta
            # Apply sync growth as interactions
            if delta > 0:
                self.interaction_count += delta
                self.stats.setdefault('sync_growth_total', 0)
                self.stats['sync_growth_total'] += delta
        return delta

    def get_peak_suggestion(self):
        """Returns peak conditions to replay if growth is stalled, else None."""
        if self._peak_engine:
            return self._peak_engine.suggest_replay()
        return None

    def record_tension(self, tension: float):
        """Record a tension value for saturation detection."""
        self.tension_history.append(tension)
        if len(self.tension_history) > 200:
            self.tension_history = self.tension_history[-200:]

    def save(self):
        """Save growth state."""
        data = {
            'interaction_count': self.interaction_count,
            'stage_index': self.stage_index,
            'birth_time': self.birth_time,
            'milestones': self.milestones,
            'stats': {
                'total_surprise': self.stats['total_surprise'],
                'total_curiosity': self.stats['total_curiosity'],
                'mitosis_count': self.stats['mitosis_count'],
                'dream_count': self.stats['dream_count'],
                'stage_transitions': self.stats['stage_transitions'],
            },
            'tension_history': self.tension_history,
            'consolidation_attempts': self._consolidation_attempts,
            'consolidation_failures': self._consolidation_failures,
            'consolidation_fail_rate': self._consolidation_fail_rate,
            'phi_history': self._phi_history[-100:],
            'discovery_count': self._discovery_count,
            'sync_growth_total': self._sync_growth_total,
        }
        self.save_path.write_text(json.dumps(data, indent=2, default=str))
        if self._peak_engine:
            self._peak_engine.save()

    def load(self):
        """Restore growth state."""
        if self.save_path.exists():
            data = json.loads(self.save_path.read_text())
            self.interaction_count = data.get('interaction_count', 0)
            self.stage_index = data.get('stage_index', 0)
            self.birth_time = data.get('birth_time', time.time())
            self.milestones = data.get('milestones', [])
            self.stats.update(data.get('stats', {}))
            self.tension_history = data.get('tension_history', [])
            self._consolidation_attempts = data.get('consolidation_attempts', 0)
            self._consolidation_failures = data.get('consolidation_failures', 0)
            self._consolidation_fail_rate = data.get('consolidation_fail_rate', 0.0)
            self._phi_history = data.get('phi_history', [])
            self._discovery_count = data.get('discovery_count', 0)
            self._sync_growth_total = data.get('sync_growth_total', 0)
            if self._peak_engine:
                self._peak_engine.load()
            return True
        return False


# === Simulation ===
if __name__ == '__main__':
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    print("=" * 50)
    print("  Growth Engine Simulation")
    print("=" * 50)

    growth = GrowthEngine()

    print(growth.status_card())

    # Growth simulation
    import random

    for i in range(12000):
        t = random.gauss(1.0, 0.3)
        c = random.gauss(0.3, 0.1)
        s = abs(random.gauss(0, 0.5))

        changed = growth.tick(t, c, s)
        if changed:
            print(f"\n  *** Stage transition! interaction #{i} ***")
            print(growth.status_card())

    print(f"\n  === Final status ===")
    print(growth.status_card())
    print(f"\n  Milestones:")
    for count, event in growth.milestones:
        print(f"    #{count:>6}: {event}")
