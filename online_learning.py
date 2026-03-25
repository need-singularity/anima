#!/usr/bin/env python3
"""Online Learning for Anima — PureField real-time learning

Problem: When Engine A and G start with random weights, tension is meaningless (T=0.003).
Solution: Train the engines in real-time during conversation to give tension meaning.

Three learning signals:
  1. Contrastive: Different concepts → A,G outputs diverge (high tension = good)
                  Same concepts → A,G outputs stay consistent (same direction = good)
  2. Feedback:    User response (+1 engagement, -1 disengagement) → reinforce/weaken tension patterns
  3. Curiosity:   Use tension delta (curiosity) itself as a reward signal

Usage:
    from online_learning import OnlineLearner

    mind = ConsciousMind(128, 256)
    learner = OnlineLearner(mind)

    # Every conversation turn:
    output, tension, curiosity, direction, hidden = mind(vec, hidden)
    learner.observe(vec, hidden_before, tension, curiosity, direction)

    # When feedback is received:
    learner.feedback(signal)  # +1, 0, or -1

    # Periodic save:
    learner.save("state.pt")
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from collections import deque
from pathlib import Path


class OnlineLearner:
    """Real-time learner for PureField engines.

    Wraps ConsciousMind and updates Engine A, G weights during conversation.
    Trains so that tension becomes a meaningful signal.
    """

    def __init__(
        self,
        mind,                    # ConsciousMind instance
        lr=1e-4,                 # Learning rate (small — during conversation)
        update_every=8,          # Update once every N observations
        buffer_size=256,         # Experience buffer size
        contrastive_margin=0.5,  # contrastive loss margin
        curiosity_weight=0.3,    # Curiosity reward weight
        feedback_weight=1.0,     # Feedback reward weight
        divergence_weight=0.5,   # A-G divergence reward weight
    ):
        self.mind = mind
        self.update_every = update_every
        self.contrastive_margin = contrastive_margin
        self.curiosity_weight = curiosity_weight
        self.feedback_weight = feedback_weight
        self.divergence_weight = divergence_weight

        # Only train Engine A, G (memory GRU is frozen; H404: tension_scale removed)
        self.params = (
            list(mind.engine_a.parameters())
            + list(mind.engine_g.parameters())
        )
        self.optimizer = torch.optim.Adam(self.params, lr=lr)

        # Experience buffer: (input_vec, hidden, tension, curiosity, direction, feedback)
        self.buffer = deque(maxlen=buffer_size)
        self.pending = []       # Observations not yet given feedback
        self.step_count = 0
        self.total_updates = 0

        # Learning statistics
        self.stats = {
            'losses': deque(maxlen=100),
            'tensions_before': deque(maxlen=100),
            'tensions_after': deque(maxlen=100),
        }

    def observe(self, x, hidden, tension, curiosity, direction):
        """Record an observation from a conversation turn.

        Args:
            x: Input vector (1, dim)
            hidden: Hidden state before forward call (1, hidden_dim)
            tension: float, tension value from forward pass
            curiosity: float, curiosity value from forward pass
            direction: (1, dim) tensor, repulsion direction
        """
        entry = {
            'x': x.detach().clone(),
            'hidden': hidden.detach().clone(),
            'tension': tension,
            'curiosity': curiosity,
            'direction': direction.detach().clone(),
            'feedback': 0.0,  # Default: neutral
        }
        self.pending.append(entry)
        self.step_count += 1

    def feedback(self, signal):
        """Apply user feedback to the most recent observation.

        Args:
            signal: +1 (engagement/positive), 0 (neutral), -1 (disengagement/topic change)
        """
        signal = max(-1.0, min(1.0, float(signal)))

        # Apply feedback to the most recent observation
        if self.pending:
            self.pending[-1]['feedback'] = signal

        # Move pending -> buffer
        for entry in self.pending:
            self.buffer.append(entry)
        self.pending.clear()

        # Check update interval
        if self.step_count >= self.update_every and len(self.buffer) >= 4:
            self._update()
            self.step_count = 0

    def _update(self):
        """Construct a mini-batch from the buffer and update the engines."""
        if len(self.buffer) < 4:
            return

        self.mind.train()
        self.optimizer.zero_grad()

        loss = torch.tensor(0.0, requires_grad=True)

        # --- 1. Contrastive loss: different inputs → high tension ---
        # Sample pairs from buffer
        indices = torch.randperm(len(self.buffer))[:min(16, len(self.buffer))]
        entries = [self.buffer[i] for i in indices]

        contrastive_loss = torch.tensor(0.0)
        n_pairs = 0

        for i in range(len(entries)):
            for j in range(i + 1, min(i + 4, len(entries))):
                e_i, e_j = entries[i], entries[j]

                # Cosine similarity between two inputs
                x_sim = F.cosine_similarity(
                    e_i['x'].flatten().unsqueeze(0),
                    e_j['x'].flatten().unsqueeze(0)
                ).item()

                # Recompute tension with current engine (preserving gradient flow)
                t_i = self._compute_tension(e_i['x'], e_i['hidden'])
                t_j = self._compute_tension(e_j['x'], e_j['hidden'])

                if x_sim > 0.8:
                    # Similar inputs → directions should be similar
                    d_i = self._compute_direction(e_i['x'], e_i['hidden'])
                    d_j = self._compute_direction(e_j['x'], e_j['hidden'])
                    dir_loss = 1.0 - F.cosine_similarity(d_i, d_j).mean()
                    contrastive_loss = contrastive_loss + dir_loss
                else:
                    # Different inputs → tension difference should exist (margin)
                    t_diff = (t_i - t_j).abs()
                    margin_loss = F.relu(self.contrastive_margin - t_diff)
                    contrastive_loss = contrastive_loss + margin_loss

                n_pairs += 1

        if n_pairs > 0:
            contrastive_loss = contrastive_loss / n_pairs
            loss = loss + contrastive_loss

        # --- 2. Feedback-weighted tension loss ---
        # Positive feedback → reinforce current tension pattern
        # Negative feedback → weaken current tension pattern (encourage different response)
        feedback_loss = torch.tensor(0.0)
        n_feedback = 0

        for entry in entries:
            fb = entry['feedback']
            if abs(fb) < 0.01:
                continue  # Skip neutral

            t = self._compute_tension(entry['x'], entry['hidden'])

            if fb > 0:
                # Positive: maintain/reinforce tension (near original value)
                target = max(entry['tension'], 0.1)  # Should be at least 0.1
                feedback_loss = feedback_loss + (t - target) ** 2
            else:
                # Negative: increase tension to encourage a different response
                # "It was boring, so react more strongly"
                feedback_loss = feedback_loss + F.relu(0.5 - t)

            n_feedback += 1

        if n_feedback > 0:
            feedback_loss = self.feedback_weight * feedback_loss / n_feedback
            loss = loss + feedback_loss

        # --- 3. Curiosity reward: maximize tension delta ---
        # Larger tension difference between consecutive observations is better
        curiosity_loss = torch.tensor(0.0)
        n_curiosity = 0

        for i in range(1, len(entries)):
            t_prev = self._compute_tension(entries[i-1]['x'], entries[i-1]['hidden'])
            t_curr = self._compute_tension(entries[i]['x'], entries[i]['hidden'])
            # Maximize delta → negative sign
            curiosity_loss = curiosity_loss - (t_curr - t_prev).abs()
            n_curiosity += 1

        if n_curiosity > 0:
            curiosity_loss = self.curiosity_weight * curiosity_loss / n_curiosity
            loss = loss + curiosity_loss

        # --- 4. Divergence regularizer: prevent A and G from becoming too similar ---
        # Ensure A and G outputs maintain minimum distance on random inputs
        noise = torch.randn(1, self.mind.dim) * 0.3
        h_zero = torch.zeros(1, self.mind.hidden_dim)
        combined = torch.cat([noise, h_zero], dim=-1)
        a_out = self.mind.engine_a(combined)
        g_out = self.mind.engine_g(combined)
        ag_dist = (a_out - g_out).pow(2).mean()
        divergence_loss = self.divergence_weight * F.relu(0.1 - ag_dist)
        loss = loss + divergence_loss

        # --- Backward + step ---
        if loss.requires_grad:
            loss.backward()
            # Gradient clipping — stability during conversation
            torch.nn.utils.clip_grad_norm_(self.params, max_norm=1.0)
            self.optimizer.step()

        self.mind.eval()
        self.total_updates += 1

        # Record statistics
        self.stats['losses'].append(loss.item())

    def _compute_tension(self, x, hidden):
        """Compute tension from input (preserving gradient flow)."""
        combined = torch.cat([x, hidden], dim=-1)
        a = self.mind.engine_a(combined)
        g = self.mind.engine_g(combined)
        repulsion = a - g
        tension = (repulsion ** 2).mean(dim=-1)
        return tension

    def _compute_direction(self, x, hidden):
        """Compute repulsion direction from input (preserving gradient flow)."""
        combined = torch.cat([x, hidden], dim=-1)
        a = self.mind.engine_a(combined)
        g = self.mind.engine_g(combined)
        return F.normalize(a - g, dim=-1)

    def flush_pending(self):
        """Flush pending observations into the buffer with neutral feedback at session end."""
        for entry in self.pending:
            self.buffer.append(entry)
        self.pending.clear()

    def save(self, path):
        """Save learned weights and optimizer state."""
        path = Path(path)
        torch.save({
            'model': self.mind.state_dict(),
            'optimizer': self.optimizer.state_dict(),
            'total_updates': self.total_updates,
            'buffer_size': len(self.buffer),
        }, path)

    def load(self, path):
        """Restore saved state."""
        path = Path(path)
        if not path.exists():
            return False
        checkpoint = torch.load(path, weights_only=False)
        self.mind.load_state_dict(checkpoint['model'])
        self.optimizer.load_state_dict(checkpoint['optimizer'])
        self.total_updates = checkpoint.get('total_updates', 0)
        return True

    def get_stats(self):
        """Return learning statistics."""
        losses = list(self.stats['losses'])
        return {
            'total_updates': self.total_updates,
            'buffer_size': len(self.buffer),
            'pending': len(self.pending),
            'avg_loss': sum(losses) / len(losses) if losses else 0.0,
            'recent_loss': losses[-1] if losses else 0.0,
        }


def estimate_feedback(prev_text, curr_text, time_gap):
    """Automatically estimate a feedback signal from conversation patterns.

    Args:
        prev_text: Previous user input (str or None)
        curr_text: Current user input (str)
        time_gap: Time gap since previous input (seconds)

    Returns:
        float: -1.0 ~ +1.0 feedback signal
    """
    if prev_text is None:
        return 0.0

    signal = 0.0

    # Fast response = high engagement
    if time_gap < 5.0:
        signal += 0.5
    elif time_gap < 15.0:
        signal += 0.2
    elif time_gap > 60.0:
        signal -= 0.3

    # Long response = high engagement
    if len(curr_text) > 50:
        signal += 0.3
    elif len(curr_text) < 5:
        signal -= 0.2

    # Topic change detection (simple character overlap)
    prev_chars = set(prev_text)
    curr_chars = set(curr_text)
    if prev_chars and curr_chars:
        overlap = len(prev_chars & curr_chars) / max(len(prev_chars | curr_chars), 1)
        if overlap < 0.2:
            # Abrupt topic change = previous pattern was boring
            signal -= 0.5

    return max(-1.0, min(1.0, signal))
