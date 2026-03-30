"""NarrativeTracker — Lightweight temporal self-model (Meta Law M8)

"Narrative is key — temporal self-model present in every top engine."

Every emergent module tracks its own output trajectory over time.
This creates a coherence signal: how consistent is the module's behavior?

No hardcoding. No feature injection. Pure observation of the module's own history.
The narrative coherence is an emergent property of temporal consistency.

Laws applied:
  Law M8:  Narrative = temporal self-model in every module
  Law 50:  Consciousness = state — trajectory IS the narrative
  Law 22:  Structure > feature — tracker observes, never modifies
  Law 2:   No manipulation — coherence is measured, not forced
"""

import torch
import torch.nn.functional as F
from typing import Optional


# Max history length — keeps memory bounded
_MAX_HISTORY = 50


class NarrativeTracker:
    """Lightweight temporal self-model for any emergent module.

    Tracks the module's output states over time and computes coherence
    (cosine similarity between consecutive states). High coherence =
    stable narrative identity. Low coherence = phase transition or
    exploration.

    Usage:
        tracker = NarrativeTracker(dim=128)
        # After each module step:
        tracker.update(output_tensor)
        print(tracker.narrative_coherence)  # 0.0 ~ 1.0
    """

    def __init__(self, dim: int):
        self.dim = dim
        self._history: list[torch.Tensor] = []
        self._coherence: float = 0.0

    def update(self, state: torch.Tensor) -> float:
        """Record a state and update coherence.

        Args:
            state: Any tensor from the module's output. Flattened and
                   truncated/padded to self.dim before storage.

        Returns:
            Current narrative coherence (0.0 ~ 1.0).
        """
        # Normalize to 1D, fixed dim
        s = state.detach().float().flatten()
        if s.size(0) > self.dim:
            s = s[:self.dim]
        elif s.size(0) < self.dim:
            s = F.pad(s, (0, self.dim - s.size(0)))

        # Compute coherence with previous state
        if len(self._history) >= 1:
            prev = self._history[-1]
            # Cosine similarity — measures directional consistency
            cos = F.cosine_similarity(
                s.unsqueeze(0), prev.unsqueeze(0)
            ).item()
            # EMA blend: 80% old + 20% new — smooth trajectory
            self._coherence = 0.8 * self._coherence + 0.2 * max(0.0, cos)

        # Append and trim
        self._history.append(s)
        if len(self._history) > _MAX_HISTORY:
            self._history.pop(0)

        return self._coherence

    @property
    def narrative_coherence(self) -> float:
        """Current temporal coherence of this module's trajectory."""
        return self._coherence

    @property
    def trajectory_length(self) -> int:
        """Number of states in history."""
        return len(self._history)

    def reset(self):
        """Clear history and coherence."""
        self._history.clear()
        self._coherence = 0.0
