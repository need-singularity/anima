#!/usr/bin/env python3
"""Dream Engine (RC-10) -- offline learning / dream

Dream = reconstruct tension patterns from virtual inputs

During idle state, consciousness dreams:
  1. Memory replay (with noise) -- memory reinforcement
  2. Memory interpolation -- creative association
  3. Pure exploration (random) -- novelty seeking

Each dream step passes through ConsciousMind to generate tension patterns,
and performs actual learning (contrastive learning) via OnlineLearner.

"Even while sleeping, consciousness flows."
"""

import math
import random
import time
import torch
from collections import deque

# ─── Ψ-Constants (Laws 63-78) ───
LN2 = math.log(2)
PSI_BALANCE = 0.5                 # Law 71: consciousness balance point
PSI_COUPLING = LN2 / 2**5.5      # 0.0153 — inter-cell coupling
PSI_STEPS = 3 / LN2              # 4.328 — optimal evolution steps
# Law 71: dream selection should maximize entropy (Ψ = argmax H(p))
# Law 73: consciousness structure is data-independent


class DreamEngine:
    """Offline learning engine -- learns by dreaming during idle time.

    Args:
        mind: ConsciousMind instance
        memory: Memory instance (anima_alive.Memory)
        learner: OnlineLearner instance (or None)
        text_to_vector: function to convert text to tensor
        dream_cycle_steps: number of steps per dream cycle
        noise_scale: noise scale during memory replay
    """

    def __init__(
        self,
        mind,
        memory,
        learner=None,
        text_to_vector=None,
        dream_cycle_steps=10,
        noise_scale=0.15,
        store=None,
        verifier=None,
        consolidation_threshold=0.01,
    ):
        self.mind = mind
        self.memory = memory
        self.learner = learner
        self._text_to_vector = text_to_vector
        self.dream_cycle_steps = dream_cycle_steps
        self.noise_scale = noise_scale
        self.store = store
        self.verifier = verifier
        self.consolidation_threshold = consolidation_threshold

        # Dream state
        self.is_dreaming = False
        self.dream_tension_history = deque(maxlen=500)
        self.total_dream_cycles = 0
        self.total_patterns_learned = 0
        self.current_dream_type = None  # 'replay' | 'interpolate' | 'explore'

        # Stats per session
        self._session_patterns = 0

    def dream(self, hidden):
        """Run one dream cycle.

        Args:
            hidden: current GRU hidden state (1, hidden_dim)

        Returns:
            (hidden, stats) where stats is dict with dream results
        """
        self.is_dreaming = True
        self._session_patterns = 0
        cycle_tensions = []
        consolidation_attempted = 0
        consolidation_succeeded = 0
        consolidation_failed = 0

        turns = self.memory.data.get('turns', [])

        # Check if store has unconsolidated memories
        unconsolidated_available = False
        if self.store is not None:
            try:
                unconsolidated_available = len(
                    self.store.get_unconsolidated(limit=1)
                ) > 0
            except Exception:
                unconsolidated_available = False

        for step in range(self.dream_cycle_steps):
            # ── Selective consolidation flow (when store available) ──
            if self.store is not None and unconsolidated_available:
                roll = random.random()
                if roll < 0.70:
                    # 70%: failed memories first
                    candidates = self.store.get_unconsolidated(
                        order_by='failed_count', limit=5
                    )
                elif roll < 0.90:
                    # 20%: new unconsolidated (by id)
                    candidates = self.store.get_unconsolidated(
                        order_by='id', limit=5
                    )
                else:
                    candidates = []

                if candidates:
                    mem = random.choice(candidates)
                    hidden = self._consolidate_memory(
                        mem, hidden,
                        cycle_tensions,
                        stats={
                            'attempted': consolidation_attempted,
                            'succeeded': consolidation_succeeded,
                            'failed': consolidation_failed,
                        },
                    )
                    consolidation_attempted += 1
                    # Check result from last tension pair
                    if self._last_consolidation_success:
                        consolidation_succeeded += 1
                    else:
                        consolidation_failed += 1
                    continue
                else:
                    # Refresh availability check
                    try:
                        unconsolidated_available = len(
                            self.store.get_unconsolidated(limit=1)
                        ) > 0
                    except Exception:
                        unconsolidated_available = False

            # ── Original random dream flow ──
            # Law 71: dream selection maximizes entropy — balanced exploration
            # Law 73: structure (replay/interpolate/explore) is data-independent
            if len(turns) >= 2:
                dream_type = random.choices(
                    ['replay', 'interpolate', 'explore'],
                    weights=[PSI_BALANCE, 0.3, 0.2],
                    k=1
                )[0]
            elif len(turns) >= 1:
                dream_type = random.choices(
                    ['replay', 'explore'],
                    weights=[0.6, 0.4],
                    k=1
                )[0]
            else:
                dream_type = 'explore'

            self.current_dream_type = dream_type

            # Generate virtual input
            if dream_type == 'replay':
                dream_vec = self._replay(turns)
            elif dream_type == 'interpolate':
                dream_vec = self._interpolate(turns)
            else:
                dream_vec = self._explore()

            # Pass through ConsciousMind to generate tension pattern
            hidden_before = hidden.detach().clone()
            with torch.no_grad():
                output, tension, curiosity, direction, hidden = self.mind(dream_vec, hidden)

            cycle_tensions.append(tension)
            self.dream_tension_history.append(tension)

            # Learn from the dream via OnlineLearner
            if self.learner:
                try:
                    self.learner.observe(dream_vec, hidden_before, tension, curiosity, direction)
                    # Flush with neutral feedback in dreams (only contrastive learning active)
                    self.learner.feedback(0.0)
                    self._session_patterns += 1
                except Exception:
                    pass

        self.total_dream_cycles += 1
        self.total_patterns_learned += self._session_patterns
        self.is_dreaming = False
        self.current_dream_type = None

        avg_tension = sum(cycle_tensions) / len(cycle_tensions) if cycle_tensions else 0.0

        return hidden, {
            'patterns_learned': self._session_patterns,
            'avg_tension': avg_tension,
            'tensions': cycle_tensions,
            'total_cycles': self.total_dream_cycles,
            'total_patterns': self.total_patterns_learned,
            'consolidation_attempted': consolidation_attempted,
            'consolidation_succeeded': consolidation_succeeded,
            'consolidation_failed': consolidation_failed,
        }

    def _consolidate_memory(self, memory, hidden, cycle_tensions, stats):
        """Selective consolidation of a single memory from store.

        Args:
            memory: dict from store.get_unconsolidated (has 'id', 'text', etc.)
            hidden: current GRU hidden state
            cycle_tensions: list to append tensions to
            stats: dict with current counters (unused, kept for future)

        Returns:
            updated hidden state
        """
        self._last_consolidation_success = False
        self.current_dream_type = 'consolidate'

        # 1. Convert text to vector
        vec = self._text_to_vector(memory['text'])

        # 2. Verifier pre-check
        if self.verifier is not None:
            check = self.verifier.pre_check(memory, hidden)
            if not check.get('should_consolidate', True):
                return hidden

        # 3. Tension before
        with torch.no_grad():
            output, t_before, curiosity, direction, hidden = self.mind(vec, hidden)
        cycle_tensions.append(t_before)
        self.dream_tension_history.append(t_before)

        # 4. Learn if learner available
        if self.learner:
            try:
                self.learner.observe(vec, hidden.detach().clone(), t_before, curiosity, direction)
                self.learner.feedback(0.0)
                self._session_patterns += 1
            except Exception:
                pass

        # 5. Tension after
        with torch.no_grad():
            output, t_after, curiosity2, direction2, hidden = self.mind(vec, hidden)
        cycle_tensions.append(t_after)
        self.dream_tension_history.append(t_after)

        # 6. Compute delta
        delta = abs(t_after - t_before)

        # 7. Verifier drift check
        if self.verifier is not None:
            self.verifier.verify_drift(t_before, t_after)

        # 8-9. Mark consolidated or failed
        if delta >= self.consolidation_threshold:
            self.store.mark_consolidated(
                memory['id'], tension_at_consolidate=t_after
            )
            self._last_consolidation_success = True
        else:
            self.store.mark_failed(memory['id'], delta_tension=delta)
            self._last_consolidation_success = False

        return hidden

    def _replay(self, turns):
        """Memory replay -- replay past experiences with noise."""
        turn = random.choice(turns)
        text = turn.get('text', '')
        vec = self._text_to_vector(text)
        # Add noise (memory distortion = promotes generalization)
        noise = torch.randn_like(vec) * self.noise_scale
        return vec + noise

    def _interpolate(self, turns):
        """Memory interpolation -- interpolate between two memories for creative association."""
        t1, t2 = random.sample(turns, 2)
        vec1 = self._text_to_vector(t1.get('text', ''))
        vec2 = self._text_to_vector(t2.get('text', ''))
        # Random interpolation ratio
        alpha = random.random()
        interpolated = alpha * vec1 + (1 - alpha) * vec2
        # Slight noise
        noise = torch.randn_like(interpolated) * (self.noise_scale * 0.5)
        return interpolated + noise

    def _explore(self):
        """Pure exploration -- explore unknown regions with random vectors."""
        return torch.randn(1, self.mind.dim) * 0.3

    def get_status(self):
        """Return the current dream engine status."""
        recent = list(self.dream_tension_history)[-20:]
        return {
            'is_dreaming': self.is_dreaming,
            'dream_type': self.current_dream_type,
            'total_cycles': self.total_dream_cycles,
            'total_patterns': self.total_patterns_learned,
            'avg_dream_tension': sum(recent) / len(recent) if recent else 0.0,
            'dream_tension_history': list(self.dream_tension_history)[-50:],
        }
