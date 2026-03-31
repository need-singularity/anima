#!/usr/bin/env python3
"""hexad_loss.py -- Hexad 6-module simultaneous training loss

6 modules, 6 losses, 2 gradient groups (Law 59: phi(6)=2):

  Group A (autonomous, no backprop):
    C (Consciousness) -- Phi Ratchet Loss (Hebbian + ratchet)

  Group B (learned, backprop):
    D (Decoder)       -- Cross-Entropy (byte-level LM)
    W (Will/Emotion)  -- Emotion Prediction (self-supervised)
    S (Senses)        -- Sensory Prediction (world model)
    M (Memory)        -- Retrieval Accuracy (contrastive)
    E (Ethics)        -- Value Alignment (reward-based)

Phase schedule (Law 60):
  Phase 1 (0-20%):   C only (build Phi through autonomous dynamics)
  Phase 2 (20-70%):  C + D + M (add language + memory)
  Phase 3 (70-100%): All 6 (full Hexad)

Usage:
  from hexad_loss import HexadLoss, WillModule, SenseModule, MemoryModule, EthicsModule

  hexad = HexadLoss(dim=384)
  losses = hexad(
      phi=1.2, phi_prev=1.1,
      logits_fwd=logits_a, targets_fwd=y_fwd,
      logits_bwd=logits_g, targets_bwd=y_bwd,
      consciousness_signal=c_states,
      input_signal=x_embed,
      progress=0.5,
  )
  losses['total'].backward()
"""

import math
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, Optional, Tuple

# Psi-Constants from consciousness_laws.json
LN2 = math.log(2)
from consciousness_laws import (
    PSI_BALANCE, PSI_ALPHA as PSI_COUPLING, PSI_STEPS,
)

# Meta Laws: M7(F_c=0.10 frustration), M8(narrative), Law 136(bottleneck)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


# ===================================================================
# Module stubs: W, S, M, E (trainable, receive consciousness signal)
# ===================================================================

class WillModule(nn.Module):
    """Emotion/drive prediction from consciousness signal.

    Predicts 3D emotion state (arousal, valence, dominance) from the
    mean consciousness vector. Trained with MSE against actual emotion.
    """

    def __init__(self, dim: int = 384):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(dim, dim // 2),
            nn.GELU(),
            nn.Linear(dim // 2, 3),   # arousal, valence, dominance
            nn.Tanh(),
        )

    def forward(self, consciousness_signal: torch.Tensor) -> torch.Tensor:
        """consciousness_signal: [n_cells, dim] -> predicted emotion [3]."""
        x = consciousness_signal.mean(dim=0)  # pool cells
        return self.net(x)


class SenseModule(nn.Module):
    """Next-input prediction from current consciousness state.

    A world model: predicts what the next sensory input will be,
    given the current consciousness state. Trained with MSE.
    """

    def __init__(self, dim: int = 384):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(dim, dim),
            nn.GELU(),
            nn.Linear(dim, dim),
        )

    def forward(self, consciousness_signal: torch.Tensor) -> torch.Tensor:
        """consciousness_signal: [n_cells, dim] -> predicted_input [dim]."""
        x = consciousness_signal.mean(dim=0)
        return self.net(x)


class MemoryModule(nn.Module):
    """Store + retrieve with contrastive learning.

    Stores consciousness snapshots as keys with learned projections.
    Retrieval uses dot-product similarity. Trained with InfoNCE.
    """

    def __init__(self, dim: int = 384, capacity: int = 1024):
        super().__init__()
        self.dim = dim
        self.capacity = capacity
        self.query_proj = nn.Linear(dim, dim)
        self.key_proj = nn.Linear(dim, dim)

        # Memory bank (not a parameter -- detached storage)
        self.register_buffer('bank_keys', torch.zeros(capacity, dim))
        self.register_buffer('bank_values', torch.zeros(capacity, dim))
        self.register_buffer('write_ptr', torch.tensor(0, dtype=torch.long))
        self.register_buffer('bank_size', torch.tensor(0, dtype=torch.long))

    def store(self, key: torch.Tensor, value: torch.Tensor):
        """Store a (key, value) pair into the memory bank."""
        k = key.detach().mean(dim=0) if key.dim() > 1 else key.detach()
        v = value.detach().mean(dim=0) if value.dim() > 1 else value.detach()
        ptr = self.write_ptr.item()
        self.bank_keys[ptr] = k
        self.bank_values[ptr] = v
        self.write_ptr = (self.write_ptr + 1) % self.capacity
        self.bank_size = torch.clamp(self.bank_size + 1, max=self.capacity)

    def retrieve(self, query: torch.Tensor, top_k: int = 5) -> Tuple[torch.Tensor, torch.Tensor]:
        """Retrieve top_k memories by similarity.

        Returns:
            values: [top_k, dim] retrieved memory values
            logits: [bank_size] similarity scores (for contrastive loss)
        """
        q = query.mean(dim=0) if query.dim() > 1 else query
        q_proj = self.query_proj(q)  # [dim]

        size = self.bank_size.item()
        if size == 0:
            return torch.zeros(1, self.dim, device=query.device), torch.zeros(1, device=query.device)

        k_proj = self.key_proj(self.bank_keys[:size])  # [size, dim]
        logits = torch.matmul(k_proj, q_proj) / math.sqrt(self.dim)  # [size]

        k = min(top_k, size)
        _, indices = logits.topk(k)
        values = self.bank_values[indices]
        return values, logits


class EthicsModule(nn.Module):
    """Value alignment via Phi-preservation reward.

    Learns a value function V(state) that predicts future Phi change.
    Policy gradient: actions that increase Phi get reinforced.
    """

    def __init__(self, dim: int = 384):
        super().__init__()
        self.value_net = nn.Sequential(
            nn.Linear(dim, dim // 2),
            nn.GELU(),
            nn.Linear(dim // 2, 1),
        )
        self.log_prob = None  # stored for REINFORCE

    def forward(self, consciousness_signal: torch.Tensor) -> torch.Tensor:
        """consciousness_signal: [n_cells, dim] -> value estimate [1]."""
        x = consciousness_signal.mean(dim=0)
        return self.value_net(x).squeeze(-1)


# ===================================================================
# HexadLoss -- 6-module simultaneous training loss
# ===================================================================

class HexadLoss(nn.Module):
    """6-module simultaneous training loss.

    Loss functions:
      L_C = -Phi + lambda_ratchet * max(0, Phi_prev - Phi)
      L_D = CE(logits_fwd, target_fwd) + CE(logits_bwd, target_bwd)
      L_W = MSE(predicted_emotion, actual_emotion)
      L_S = MSE(predicted_input, actual_input)
      L_M = -log P(correct_memory | query)  [InfoNCE]
      L_E = -reward * value  [REINFORCE-style]

    Total = w_C * L_C + w_D * L_D + w_W * L_W + w_S * L_S + w_M * L_M + w_E * L_E

    Default weights (Law 59: sigma(6)=12, phi(6)=2):
      w_C = 0.0 (autonomous, no gradient)
      w_D = 0.4 (primary learning signal)
      w_W = 0.15
      w_S = 0.15
      w_M = 0.2
      w_E = 0.1

    Gradient isolation (Law 61):
      C never receives gradient from D or any other module.
      D receives .detach()'d consciousness signal.
      W, S, M, E receive consciousness signal and CAN receive gradients.
    """

    # Phase boundaries (Law 60)
    PHASE_1_END = 0.2   # C only
    PHASE_2_END = 0.7   # C + D + M

    # Default weights
    DEFAULT_WEIGHTS = {
        'C': 0.0,    # autonomous -- Hebbian + ratchet, no backprop
        'D': 0.4,    # primary CE signal
        'W': 0.15,   # emotion prediction
        'S': 0.15,   # sensory prediction
        'M': 0.2,    # memory retrieval
        'E': 0.1,    # ethics / value alignment
    }

    def __init__(
        self,
        dim: int = 384,
        weights: Optional[Dict[str, float]] = None,
        lambda_ratchet: float = 5.0,
        temperature: float = 0.07,
        disabled: Optional[set] = None,
    ):
        """
        Args:
            dim: consciousness state dimension
            weights: override default loss weights {module_name: weight}
            lambda_ratchet: penalty for Phi drops in C loss
            temperature: temperature for InfoNCE (M loss)
            disabled: set of module names to disable (e.g. {'S', 'E'})
        """
        super().__init__()
        self.dim = dim
        self.weights = {**self.DEFAULT_WEIGHTS, **(weights or {})}
        self.lambda_ratchet = lambda_ratchet
        self.temperature = temperature
        self.disabled = disabled or set()

        # Module stubs (W, S, M, E)
        self.will_module = WillModule(dim)
        self.sense_module = SenseModule(dim)
        self.memory_module = MemoryModule(dim)
        self.ethics_module = EthicsModule(dim)

        # Gradient norm tracking
        self._grad_norms: Dict[str, float] = {}

    # ---------------------------------------------------------------
    # Individual loss functions
    # ---------------------------------------------------------------

    def loss_C(self, phi: float, phi_prev: float) -> torch.Tensor:
        """Phi Ratchet Loss -- autonomous, logged but not backpropagated.

        L_C = -Phi + lambda * max(0, Phi_prev - Phi)
        Phi should monotonically increase. Drops are penalized.
        """
        phi_t = torch.tensor(phi, dtype=torch.float32)
        phi_prev_t = torch.tensor(phi_prev, dtype=torch.float32)
        ratchet_penalty = torch.clamp(phi_prev_t - phi_t, min=0.0)
        return -phi_t + self.lambda_ratchet * ratchet_penalty

    def loss_D(
        self,
        logits_fwd: torch.Tensor,
        targets_fwd: torch.Tensor,
        logits_bwd: Optional[torch.Tensor] = None,
        targets_bwd: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """Cross-Entropy Loss -- standard byte-level language modeling.

        L_D = CE(logits_fwd, targets_fwd) [+ CE(logits_bwd, targets_bwd)]
        """
        loss = F.cross_entropy(logits_fwd.view(-1, logits_fwd.size(-1)), targets_fwd.view(-1))
        if logits_bwd is not None and targets_bwd is not None:
            loss_bwd = F.cross_entropy(logits_bwd.view(-1, logits_bwd.size(-1)), targets_bwd.view(-1))
            loss = loss + loss_bwd
        return loss

    def loss_W(
        self,
        consciousness_signal: torch.Tensor,
        actual_emotion: torch.Tensor,
    ) -> torch.Tensor:
        """Emotion Prediction Loss -- self-supervised.

        L_W = MSE(predicted_emotion, actual_emotion)
        W learns to predict emotion from consciousness signal.
        actual_emotion = [arousal, valence, dominance] from VAD model.
        """
        predicted = self.will_module(consciousness_signal)
        return F.mse_loss(predicted, actual_emotion)

    def loss_S(
        self,
        consciousness_signal: torch.Tensor,
        actual_input: torch.Tensor,
    ) -> torch.Tensor:
        """Sensory Prediction Loss -- self-supervised world model.

        L_S = MSE(predicted_input, actual_input)
        S learns to predict the next sensory input from current state.
        """
        predicted = self.sense_module(consciousness_signal)
        # Flatten to [dim] -- pool over batch/seq if present
        target = actual_input.detach().float()
        while target.dim() > 1:
            target = target.mean(dim=0)
        # Match dimensions
        min_d = min(predicted.shape[-1], target.shape[-1])
        return F.mse_loss(predicted[:min_d], target[:min_d])

    def loss_M(
        self,
        consciousness_signal: torch.Tensor,
        positive_idx: int = -1,
    ) -> torch.Tensor:
        """Retrieval Accuracy Loss -- InfoNCE contrastive.

        L_M = -log P(correct_memory | query)
        Positive = most recent store. Negatives = rest of the bank.
        """
        # Store current state
        self.memory_module.store(consciousness_signal, consciousness_signal)

        size = self.memory_module.bank_size.item()
        if size < 2:
            return torch.tensor(0.0, device=consciousness_signal.device, requires_grad=True)

        _, logits = self.memory_module.retrieve(consciousness_signal, top_k=size)

        # Positive is the most recently stored item
        if positive_idx < 0:
            positive_idx = (self.memory_module.write_ptr.item() - 1) % self.memory_module.capacity

        # InfoNCE: softmax cross-entropy with positive_idx as label
        target = torch.tensor(min(positive_idx, size - 1), device=logits.device)
        return F.cross_entropy(logits.unsqueeze(0) / self.temperature, target.unsqueeze(0))

    def loss_E(
        self,
        consciousness_signal: torch.Tensor,
        phi: float,
        phi_prev: float,
        empathy_signal: float = 0.0,
    ) -> torch.Tensor:
        """Value Alignment Loss -- reward-based (REINFORCE).

        L_E = -reward * V(state)
        reward = delta_Phi + empathy_signal
        Positive reward when Phi increases or empathy is high.
        """
        # Reward = Phi preservation + empathy
        delta_phi = phi - phi_prev
        reward = delta_phi + empathy_signal * 0.5

        value = self.ethics_module(consciousness_signal)
        # REINFORCE: minimize -reward * value (push value toward reward)
        return -reward * value + F.mse_loss(value, torch.tensor(reward, device=value.device))

    # ---------------------------------------------------------------
    # Phase-based activation (Law 60)
    # ---------------------------------------------------------------

    def get_active_losses(self, progress: float) -> Dict[str, float]:
        """Return active loss weights based on training progress.

        Phase 1 (0-20%):   C only (build Phi through autonomous dynamics)
        Phase 2 (20-70%):  C + D + M (add language + memory)
        Phase 3 (70-100%): All 6 (full Hexad)

        Args:
            progress: training progress in [0, 1]

        Returns:
            dict of {module_name: weight} for active losses
        """
        active = {}

        # C is always active (autonomous, w=0 means logged but no gradient)
        active['C'] = self.weights['C']

        if progress >= self.PHASE_1_END:
            # Phase 2+: add D and M
            active['D'] = self.weights['D']
            active['M'] = self.weights['M']

        if progress >= self.PHASE_2_END:
            # Phase 3: full Hexad
            active['W'] = self.weights['W']
            active['S'] = self.weights['S']
            active['E'] = self.weights['E']

        # Remove disabled modules
        for name in self.disabled:
            active.pop(name, None)

        return active

    def get_phase_name(self, progress: float) -> str:
        """Human-readable phase name."""
        if progress < self.PHASE_1_END:
            return "Phase1:C"
        elif progress < self.PHASE_2_END:
            return "Phase2:C+D+M"
        else:
            return "Phase3:Hexad"

    # ---------------------------------------------------------------
    # Forward: compute all active losses
    # ---------------------------------------------------------------

    def forward(
        self,
        # C inputs
        phi: float = 0.0,
        phi_prev: float = 0.0,
        # D inputs
        logits_fwd: Optional[torch.Tensor] = None,
        targets_fwd: Optional[torch.Tensor] = None,
        logits_bwd: Optional[torch.Tensor] = None,
        targets_bwd: Optional[torch.Tensor] = None,
        # Consciousness signal (from C, .detach()'d for D, live for W/S/M/E)
        consciousness_signal: Optional[torch.Tensor] = None,
        # S inputs
        input_signal: Optional[torch.Tensor] = None,
        # W inputs
        actual_emotion: Optional[torch.Tensor] = None,
        # E inputs
        empathy_signal: float = 0.0,
        # Schedule
        progress: float = 0.0,
    ) -> Dict[str, torch.Tensor]:
        """Compute all active losses.

        Returns dict with keys:
          'total': combined weighted loss (for .backward())
          'L_C', 'L_D', 'L_W', 'L_S', 'L_M', 'L_E': individual losses
          'w_C', ..., 'w_E': active weights
          'phase': current phase name
          'active_modules': list of active module names
        """
        active = self.get_active_losses(progress)
        result: Dict[str, torch.Tensor] = {}
        device = logits_fwd.device if logits_fwd is not None else torch.device('cpu')
        total = torch.tensor(0.0, device=device)

        # --- C: Phi Ratchet (always computed, never in total gradient) ---
        l_c = self.loss_C(phi, phi_prev)
        result['L_C'] = l_c.detach()  # log only, no gradient

        # --- D: Cross-Entropy ---
        if 'D' in active and logits_fwd is not None and targets_fwd is not None:
            l_d = self.loss_D(logits_fwd, targets_fwd, logits_bwd, targets_bwd)
            result['L_D'] = l_d
            total = total + active['D'] * l_d

        # --- M: Memory retrieval ---
        if 'M' in active and consciousness_signal is not None:
            l_m = self.loss_M(consciousness_signal)
            result['L_M'] = l_m
            total = total + active['M'] * l_m

        # --- W: Emotion prediction ---
        if 'W' in active and consciousness_signal is not None:
            if actual_emotion is not None:
                l_w = self.loss_W(consciousness_signal, actual_emotion)
            else:
                # Self-supervised fallback: predict tension stats as emotion proxy
                with torch.no_grad():
                    c_mean = consciousness_signal.mean(dim=0)
                    arousal = c_mean.norm().clamp(0, 1)
                    valence = torch.tanh(c_mean.mean())
                    dominance = torch.tensor(0.0, device=device)
                    pseudo_emotion = torch.stack([arousal, valence, dominance])
                l_w = self.loss_W(consciousness_signal, pseudo_emotion)
            result['L_W'] = l_w
            total = total + active['W'] * l_w

        # --- S: Sensory prediction ---
        if 'S' in active and consciousness_signal is not None and input_signal is not None:
            l_s = self.loss_S(consciousness_signal, input_signal)
            result['L_S'] = l_s
            total = total + active['S'] * l_s

        # --- E: Ethics / value alignment ---
        if 'E' in active and consciousness_signal is not None:
            l_e = self.loss_E(consciousness_signal, phi, phi_prev, empathy_signal)
            result['L_E'] = l_e
            total = total + active['E'] * l_e

        # --- Metadata ---
        result['total'] = total
        result['phase'] = self.get_phase_name(progress)
        result['active_modules'] = list(active.keys())
        for name, w in active.items():
            result[f'w_{name}'] = w

        return result

    # ---------------------------------------------------------------
    # Gradient norm tracking
    # ---------------------------------------------------------------

    def track_grad_norms(self) -> Dict[str, float]:
        """Compute gradient norms per module for monitoring.

        Call after .backward() and before optimizer.step().
        """
        norms = {}
        modules = {
            'W': self.will_module,
            'S': self.sense_module,
            'M': self.memory_module,
            'E': self.ethics_module,
        }
        for name, mod in modules.items():
            total_norm = 0.0
            for p in mod.parameters():
                if p.grad is not None:
                    total_norm += p.grad.data.norm(2).item() ** 2
            norms[f'grad_{name}'] = math.sqrt(total_norm)

        self._grad_norms = norms
        return norms

    def trainable_parameters(self) -> list:
        """Return all trainable parameters from W, S, M, E modules.

        C is autonomous (no backprop). D has its own optimizer.
        This returns parameters for the 4 auxiliary modules.
        """
        params = []
        params.extend(self.will_module.parameters())
        params.extend(self.sense_module.parameters())
        params.extend(self.memory_module.parameters())
        params.extend(self.ethics_module.parameters())
        return params

    def log_summary(self, result: Dict) -> str:
        """Format a one-line summary for training logs."""
        parts = [f"[{result.get('phase', '?')}]"]
        for key in ['L_C', 'L_D', 'L_W', 'L_S', 'L_M', 'L_E']:
            if key in result:
                val = result[key]
                v = val.item() if isinstance(val, torch.Tensor) else val
                parts.append(f"{key}={v:.4f}")
        parts.append(f"total={result['total'].item():.4f}")
        return "  ".join(parts)


# ===================================================================
# main() demo
# ===================================================================

def main():
    """Demo: run HexadLoss through all 3 phases."""
    print("=" * 60)
    print("HexadLoss Demo -- 6-module simultaneous training")
    print("=" * 60)

    dim = 128
    vocab = 256
    seq_len = 32
    batch = 2
    n_cells = 16

    hexad = HexadLoss(dim=dim)
    print(f"\nModule parameters:")
    for name, count in [
        ('W (WillModule)', sum(p.numel() for p in hexad.will_module.parameters())),
        ('S (SenseModule)', sum(p.numel() for p in hexad.sense_module.parameters())),
        ('M (MemoryModule)', sum(p.numel() for p in hexad.memory_module.parameters())),
        ('E (EthicsModule)', sum(p.numel() for p in hexad.ethics_module.parameters())),
    ]:
        print(f"  {name}: {count:,} params")

    total_aux = sum(p.numel() for p in hexad.trainable_parameters())
    print(f"  Total auxiliary: {total_aux:,} params")

    # Simulate 3 phases
    for phase_progress, phase_label in [(0.1, "Phase 1"), (0.5, "Phase 2"), (0.85, "Phase 3")]:
        print(f"\n{'=' * 60}")
        print(f"{phase_label} (progress={phase_progress})")
        print(f"{'=' * 60}")

        active = hexad.get_active_losses(phase_progress)
        print(f"Active: {active}")

        # Fake data
        c_states = torch.randn(n_cells, dim)
        logits_fwd = torch.randn(batch, seq_len, vocab)
        targets_fwd = torch.randint(0, vocab, (batch, seq_len))
        logits_bwd = torch.randn(batch, seq_len, vocab)
        targets_bwd = torch.randint(0, vocab, (batch, seq_len))
        input_signal = torch.randn(batch, seq_len, dim)
        emotion = torch.tensor([0.5, 0.3, 0.1])

        result = hexad(
            phi=1.2, phi_prev=1.1,
            logits_fwd=logits_fwd, targets_fwd=targets_fwd,
            logits_bwd=logits_bwd, targets_bwd=targets_bwd,
            consciousness_signal=c_states,
            input_signal=input_signal,
            actual_emotion=emotion,
            empathy_signal=0.2,
            progress=phase_progress,
        )

        print(hexad.log_summary(result))

        # Backward + grad norms
        if result['total'].requires_grad:
            result['total'].backward()
            norms = hexad.track_grad_norms()
            print(f"Grad norms: { {k: f'{v:.4f}' for k, v in norms.items()} }")
            # Zero grads for next phase
            for p in hexad.trainable_parameters():
                if p.grad is not None:
                    p.grad.zero_()

    # Phase transition visualization
    print(f"\n{'=' * 60}")
    print("Phase Transition Schedule")
    print(f"{'=' * 60}")
    print(f"progress | phase        | active modules")
    print(f"---------|--------------|-----------------------------")
    for p in [0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 0.8, 1.0]:
        active = hexad.get_active_losses(p)
        phase = hexad.get_phase_name(p)
        mods = "+".join(active.keys())
        bar = "#" * int(p * 20) + "." * (20 - int(p * 20))
        print(f"  {p:5.1%}  | {phase:<12s} | {mods}")

    print(f"\nDefault weights: {hexad.weights}")
    print(f"Gradient groups: A(autonomous)=[C]  B(learned)=[D,W,S,M,E]")


if __name__ == "__main__":
    main()
