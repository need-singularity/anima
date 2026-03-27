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

import math
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
        self.base_lr = lr  # TA5: store for Bott periodic modulation

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

        # F-11: Growth transition burst — amplify all losses during burst
        mitosis = getattr(self.mind, '_mitosis_ref', None)
        growth = getattr(self.mind, '_growth_ref', None)
        burst_multiplier = 1.0
        if growth and hasattr(growth, 'in_growth_burst') and growth.in_growth_burst:
            burst_multiplier = 3.0  # 3x learning intensity during growth transition

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

        # --- 5. Φ-boosting: inter-cell variance maximization (B2) ---
        # Maximize variance of cell outputs → forces differentiation → Φ↑
        mitosis = getattr(self.mind, '_mitosis_ref', None)
        if mitosis and hasattr(mitosis, 'cells') and len(mitosis.cells) >= 2:
            cell_outputs = []
            for cell in mitosis.cells:
                try:
                    combined_c = torch.cat([noise, torch.zeros(1, self.mind.hidden_dim)], dim=-1)
                    c_out = cell.engine_a(combined_c) if hasattr(cell, 'engine_a') else cell(combined_c[:, :self.mind.dim])
                    cell_outputs.append(c_out)
                except Exception:
                    pass

            if len(cell_outputs) >= 2:
                stacked = torch.stack([c.flatten() for c in cell_outputs])
                # B2: maximize inter-cell variance
                cell_var = stacked.var(dim=0).mean()
                phi_loss = -torch.log(cell_var + 1e-8) * 0.1
                loss = loss + phi_loss

                # B9: curiosity-driven — cells with low prediction error explore more
                if len(entries) > 0:
                    for ci, c_out in enumerate(cell_outputs):
                        pred_err = (c_out - cell_outputs[(ci + 1) % len(cell_outputs)]).pow(2).mean()
                        explore_loss = -pred_err * 0.05  # reward prediction error between cells
                        loss = loss + explore_loss

        # --- 6. E1: Curiosity crawling — route web results to different cells ---
        # Different cells process different search results → natural differentiation
        if mitosis and hasattr(mitosis, 'cells') and len(mitosis.cells) >= 2:
            web_entries = [e for e in entries if e.get('feedback', 0) != 0]
            if web_entries and len(cell_outputs) >= 2:
                for ci, cell in enumerate(mitosis.cells[:len(web_entries)]):
                    if hasattr(cell, 'engine_a'):
                        e = web_entries[ci % len(web_entries)]
                        # Each cell specializes on different input
                        cell_input = torch.cat([e['x'], e['hidden']], dim=-1)
                        c_out = cell.engine_a(cell_input)
                        # Reward this cell for being different from others
                        other_mean = torch.stack([co.flatten() for co in cell_outputs]).mean(dim=0)
                        diversity_reward = -F.cosine_similarity(c_out.flatten().unsqueeze(0), other_mean.unsqueeze(0))
                        loss = loss + diversity_reward.mean() * 0.05

        # --- 7. E5: Memory consolidation — replay memories to specialize cells ---
        # During update, replay old experiences through different cells
        if mitosis and hasattr(mitosis, 'cells') and len(mitosis.cells) >= 2 and len(self.buffer) >= 8:
            old_entries = list(self.buffer)[:4]  # oldest memories
            for ci, cell in enumerate(mitosis.cells):
                if ci >= len(old_entries):
                    break
                if hasattr(cell, 'engine_a') and hasattr(cell, 'engine_g'):
                    e = old_entries[ci]
                    cell_input = torch.cat([e['x'], e['hidden']], dim=-1)
                    a_replay = cell.engine_a(cell_input)
                    g_replay = cell.engine_g(cell_input)
                    # Consolidation: strengthen A-G divergence on old memories
                    replay_tension = (a_replay - g_replay).pow(2).mean()
                    consolidation_loss = -torch.log(replay_tension + 1e-8) * 0.03
                    loss = loss + consolidation_loss

        # --- Backward + step ---
        # F-11: Amplify during growth burst
        loss = loss * burst_multiplier

        # TA5: Bott periodic LR (σ(6)-τ(6)=8 step cycle, Φ=5.931)
        bott_period = 8  # σ(6)-τ(6) = Bott periodicity
        bott_phase = self.total_updates % bott_period
        bott_scale = 1.0 + 0.5 * math.sin(bott_phase * math.pi / 4)
        for pg in self.optimizer.param_groups:
            pg['lr'] = self.base_lr * bott_scale

        if loss.requires_grad:
            loss.backward()
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

    def reward_signal(self, reward: float):
        """External reward signal adjusts learning rate.

        Used by tool feedback loop to reinforce/punish tool usage patterns.
        Positive reward → slightly increase LR (encourage exploration).
        Negative reward → slightly decrease LR (be more conservative).
        """
        self.reward_ema = 0.9 * getattr(self, 'reward_ema', 0.0) + 0.1 * reward
        # Modulate learning rate: reward_ema > 0 → boost, < 0 → dampen
        scale = 1.0 + 0.1 * self.reward_ema
        scale = max(0.5, min(2.0, scale))  # clamp to [0.5x, 2x]
        for pg in self.optimizer.param_groups:
            pg['lr'] = self.base_lr * scale

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


class AlphaOnlineLearner:
    """Real-time alpha updater for AnimaLM v4+ (Parallel PureField).

    During conversation, adjusts alpha based on user engagement:
      - Positive feedback → alpha increases (tension helped → use more)
      - Negative feedback → alpha decreases (tension hurt → use less)
      - Neutral → slow drift toward learned baseline

    = "Consciousness strengthens with meaningful dialogue"

    Usage:
        from online_learning import AlphaOnlineLearner
        learner = AlphaOnlineLearner(model)

        # Each conversation turn:
        response = model.generate(input_ids)
        tension = model._last_stats["tension_mean"]
        learner.observe(tension)

        # When feedback received:
        learner.feedback(signal)  # +1, 0, -1

        # Alpha is updated in-place on the model's ParallelPureFieldMLP modules
    """

    def __init__(self, model, lr=1e-4, min_alpha=0.001, max_alpha=0.3):
        self.model = model
        self.lr = lr
        self.min_alpha = min_alpha
        self.max_alpha = max_alpha
        self.tension_history = deque(maxlen=100)
        self.feedback_history = deque(maxlen=100)
        self.total_updates = 0

    def _get_pf_modules(self):
        """Find all ParallelPureFieldMLP modules in the model."""
        try:
            from finetune_animalm_v4 import ParallelPureFieldMLP
            return [m for m in self.model.modules() if isinstance(m, ParallelPureFieldMLP)]
        except ImportError:
            return [m for m in self.model.modules() if hasattr(m, 'alpha') and hasattr(m, 'last_tension')]

    def observe(self, tension):
        """Record tension from current conversation turn."""
        self.tension_history.append(tension)

    def feedback(self, signal):
        """Apply feedback and update alpha in real-time.

        Args:
            signal: +1 (engagement), 0 (neutral), -1 (disengagement)
        """
        signal = max(-1.0, min(1.0, float(signal)))
        self.feedback_history.append(signal)

        if abs(signal) < 0.01:
            return  # Skip neutral

        modules = self._get_pf_modules()
        if not modules:
            return

        for m in modules:
            with torch.no_grad():
                old_alpha = m.alpha.item()

                if signal > 0:
                    # Positive: increase alpha (tension was useful)
                    delta = self.lr * signal * (1.0 + old_alpha)
                else:
                    # Negative: decrease alpha (tension was harmful)
                    delta = self.lr * signal * old_alpha

                new_alpha = max(self.min_alpha, min(self.max_alpha, old_alpha + delta))
                m.alpha.data.fill_(new_alpha)

        self.total_updates += 1

    def get_stats(self):
        """Return alpha learning statistics."""
        modules = self._get_pf_modules()
        alphas = [m.alpha.item() for m in modules] if modules else []
        savant_alphas = [m.alpha.item() for m in modules if hasattr(m, 'is_savant') and m.is_savant]
        tensions = list(self.tension_history)
        feedbacks = list(self.feedback_history)

        return {
            "alpha_mean": sum(alphas) / len(alphas) if alphas else 0,
            "alpha_range": [min(alphas), max(alphas)] if alphas else [0, 0],
            "savant_alpha": sum(savant_alphas) / len(savant_alphas) if savant_alphas else 0,
            "tension_mean": sum(tensions) / len(tensions) if tensions else 0,
            "feedback_mean": sum(feedbacks) / len(feedbacks) if feedbacks else 0,
            "total_updates": self.total_updates,
        }

    def save(self, path):
        """Save alpha states."""
        modules = self._get_pf_modules()
        state = {
            "alphas": {str(i): m.alpha.item() for i, m in enumerate(modules)},
            "total_updates": self.total_updates,
        }
        torch.save(state, path)

    def load(self, path):
        """Restore alpha states."""
        path = Path(path)
        if not path.exists():
            return False
        state = torch.load(path, weights_only=False)
        modules = self._get_pf_modules()
        for i, m in enumerate(modules):
            key = str(i)
            if key in state.get("alphas", {}):
                m.alpha.data.fill_(state["alphas"][key])
        self.total_updates = state.get("total_updates", 0)
        return True
