#!/usr/bin/env python3
"""trinity_legacy.py — Deprecated classes moved from trinity.py

These classes are kept for backward compatibility only.
All new code should use the canonical replacements:

  D (decoder):  ConsciousDecoderV2 (conscious_decoder.py) or PostHocDecoder (trinity.py)
  W (will):     EmergentW (hexad/w/emergent_w.py)
  S (sense):    EmergentS (hexad/s/emergent_s.py)
  M (memory):   EmergentM (hexad/m/emergent_m.py)
  E (ethics):   EmergentE (hexad/e/emergent_e.py)
  C (engine):   ConsciousnessC (consciousness_engine.py)
"""

import math
import warnings
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Optional, Dict, Any

try:
    import phi_rs
    HAS_RUST_PHI = True
except ImportError:
    HAS_RUST_PHI = False


# ═══════════════════════════════════════════════════════════
# C Engine Legacy Wrappers
# ═══════════════════════════════════════════════════════════

class CEngine:
    """Base class for consciousness engine wrapper."""

    def step(self, x_input: Optional[torch.Tensor] = None):
        raise NotImplementedError

    def get_states(self) -> torch.Tensor:
        raise NotImplementedError

    @property
    def state_dim(self) -> int:
        raise NotImplementedError

    @property
    def n_cells(self) -> int:
        raise NotImplementedError

    def measure_phi(self) -> float:
        states = self.get_states()
        if HAS_RUST_PHI and states.shape[0] >= 2:
            s = states.detach().cpu().numpy().astype(np.float32)
            phi, _ = phi_rs.compute_phi(s, 16)
            return phi
        return 0.0


class MitosisC(CEngine):
    """LEGACY -- Use ConsciousnessC (consciousness_engine.py) instead."""

    def __init__(self, dim=64, hidden=128, max_cells=256, mechanism='cambrian_osc_qw'):
        warnings.warn("MitosisC is deprecated. Use ConsciousnessC (consciousness_engine.py) instead", DeprecationWarning, stacklevel=2)
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from mitosis import MitosisEngine

        self.dim = dim
        self.hidden = hidden
        self.max_cells = max_cells
        self.mechanism = mechanism
        self.engine = MitosisEngine(dim, hidden, dim, initial_cells=2, max_cells=max_cells)

        while len(self.engine.cells) < max_cells:
            self.engine._create_cell(parent=self.engine.cells[0])

        self._step_count = 0
        if 'cambrian' in mechanism:
            from train_v10 import CambrianDiversity
            self.cambrian = CambrianDiversity(max_cells, hidden)
        if 'osc' in mechanism or 'qw' in mechanism:
            from train_v10 import OscillatorQW
            self.osc_qw = OscillatorQW(max_cells, hidden)

    def step(self, x_input=None):
        if x_input is None:
            x_input = torch.randn(1, self.dim)
        self.engine.process(x_input.cpu())
        self._step_count += 1

        if hasattr(self, 'cambrian'):
            self.cambrian.step(self.engine.cells, self._step_count)
        if hasattr(self, 'osc_qw'):
            self.osc_qw.step(self.engine.cells)

    def get_states(self) -> torch.Tensor:
        return torch.stack([c.hidden.squeeze(0) for c in self.engine.cells])

    @property
    def state_dim(self):
        return self.hidden

    @property
    def n_cells(self):
        return len(self.engine.cells)

    def measure_phi(self) -> float:
        if HAS_RUST_PHI and len(self.engine.cells) >= 2:
            cells = self.engine.cells
            states = torch.stack([c.hidden.squeeze(0) for c in cells]).detach().numpy().astype(np.float32)
            prev_s, curr_s = [], []
            for c in cells:
                if hasattr(c, 'hidden_history') and len(c.hidden_history) >= 2:
                    prev_s.append(c.hidden_history[-2].detach().squeeze().numpy().astype(np.float32))
                    curr_s.append(c.hidden_history[-1].detach().squeeze().numpy().astype(np.float32))
                else:
                    prev_s.append(np.zeros(self.hidden, dtype=np.float32))
                    curr_s.append(np.zeros(self.hidden, dtype=np.float32))
            tensions = np.array([c.tension_history[-1] if c.tension_history else 0.0 for c in cells], dtype=np.float32)
            phi, _ = phi_rs.compute_phi(states, 16, np.array(prev_s), np.array(curr_s), tensions)
            return phi
        return 0.0


class DomainC(CEngine):
    """LEGACY -- Use ConsciousnessC instead."""

    def __init__(self, engine_cls, nc=256, dim=64):
        warnings.warn("DomainC is deprecated. Use ConsciousnessC instead", DeprecationWarning, stacklevel=2)
        self._nc = nc
        self._dim = dim
        try:
            self.engine = engine_cls(nc, dim)
        except TypeError:
            try:
                self.engine = engine_cls(nc=nc, dim=dim)
            except TypeError:
                self.engine = engine_cls(nc, dim=dim)

        self._state_dim = None
        self._step_num = 0

    def step(self, x_input=None):
        self._step_num += 1
        try:
            self.engine.step(x_input, self._step_num)
        except TypeError:
            try:
                self.engine.step()
            except Exception:
                pass

    def get_states(self) -> torch.Tensor:
        for attr in ['state', 'states', 'pos', 'hidden', 'hiddens', 'h',
                      'uv_state', 'boundary', 'info', 'fiber', 'voice',
                      'expression', 'features']:
            if hasattr(self.engine, attr):
                val = getattr(self.engine, attr)
                if isinstance(val, torch.Tensor) and val.dim() == 2 and val.shape[0] == self._nc:
                    self._state_dim = val.shape[1]
                    return val

        parts = []
        for attr in ['pos', 'vel', 'phase', 'amplitude', 'charge', 'spin',
                      'momentum', 'energy', 'activation', 'state',
                      'psi_re', 'psi_im', 'delta_re', 'delta_im',
                      'N1', 'N2', 'radius', 'displacement',
                      'u', 'v', 'w', 'heights', 'temp', 'velocity',
                      'omega', 'theta', 'genome', 'constructor', 'fitness',
                      'z', 'q', 'p', 'fiber', 'base_angle',
                      'z_re', 'z_im',
                      'boundary', 'V', 'phi', 'pi',
                      'host_state', 'symbiont_state', 'hybrid_state', 'vigor',
                      'pitch', 'pitch_class', 'voice', 'deviation', 'motion',
                      'epigenome', 'histone', 'epi_memory']:
            if hasattr(self.engine, attr):
                val = getattr(self.engine, attr)
                if isinstance(val, torch.Tensor):
                    if val.dim() == 1 and val.shape[0] == self._nc:
                        parts.append(val.unsqueeze(1))
                    elif val.dim() == 2 and val.shape[0] == self._nc:
                        parts.append(val)
                    elif val.dim() >= 3 and val.shape[0] == self._nc:
                        parts.append(val.reshape(self._nc, -1))
        if parts:
            h = torch.cat(parts, dim=1)
            self._state_dim = h.shape[1]
            return h

        self._state_dim = self._dim
        return torch.randn(self._nc, self._dim)

    @property
    def state_dim(self):
        if self._state_dim is None:
            self.get_states()
        return self._state_dim

    @property
    def n_cells(self):
        return self._nc


class QuantumC(CEngine):
    """LEGACY -- Use ConsciousnessC instead."""

    def __init__(self, nc=256, dim=64, max_cells=None):
        warnings.warn("QuantumC is deprecated. Use ConsciousnessC instead", DeprecationWarning, stacklevel=2)
        from quantum_engine_fast import QuantumConsciousnessEngineFast
        if max_cells is None:
            max_cells = nc
        self.engine = QuantumConsciousnessEngineFast(
            dim=dim, initial_cells=nc, max_cells=max_cells
        )
        self._dim = dim

    def step(self, x_input=None):
        self.engine.step()

    def get_states(self) -> torch.Tensor:
        amp = self.engine._amplitudes
        if amp.numel() == 0:
            return torch.randn(self.n_cells, self._dim)
        return amp.detach()

    @property
    def state_dim(self):
        return self._dim

    @property
    def n_cells(self):
        return self.engine.n_cells

    def measure_phi(self) -> float:
        states = self.get_states()
        if HAS_RUST_PHI and states.shape[0] >= 2:
            s = states.detach().cpu().numpy().astype(np.float32)
            phi, _ = phi_rs.compute_phi(s, 16)
            return phi
        return 0.0


# ═══════════════════════════════════════════════════════════
# D Engine Legacy Decoders
# ═══════════════════════════════════════════════════════════

class DEngine(nn.Module):
    """Base class for language decoder (D module)."""

    @property
    def d_model(self) -> int:
        raise NotImplementedError

    def forward(self, tokens: torch.Tensor, gate_signal: torch.Tensor) -> torch.Tensor:
        raise NotImplementedError


class TransformerDecoder(DEngine):
    """LEGACY -- Use ConsciousDecoderV2 (conscious_decoder.py) instead."""

    def __init__(self, d_model=384, n_layers=4, n_heads=None, vocab_size=4096, max_seq=512):
        super().__init__()
        warnings.warn("TransformerDecoder is deprecated. Use ConsciousDecoderV2 (conscious_decoder.py) instead", DeprecationWarning, stacklevel=2)
        if n_heads is None:
            for nh in [6, 4, 8, 2, 1]:
                if d_model % nh == 0:
                    n_heads = nh
                    break
        self._d_model = d_model
        self.vocab_size = vocab_size

        self.embed = nn.Embedding(vocab_size, d_model)
        self.pos_embed = nn.Embedding(max_seq, d_model)

        layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=n_heads, dim_feedforward=d_model * 4,
            batch_first=True, dropout=0.1, activation='gelu',
        )
        self.transformer = nn.TransformerEncoder(layer, num_layers=n_layers)
        self.ln_f = nn.LayerNorm(d_model)
        self.head = nn.Linear(d_model, vocab_size, bias=False)

    @property
    def d_model(self):
        return self._d_model

    def forward(self, tokens, gate_signal):
        B, T = tokens.shape
        pos = torch.arange(T, device=tokens.device).unsqueeze(0)
        x = self.embed(tokens) + self.pos_embed(pos)
        if gate_signal is not None:
            x = x * gate_signal.expand(B, -1, -1)
        mask = nn.Transformer.generate_square_subsequent_mask(T, device=tokens.device)
        x = self.transformer(x, mask=mask, is_causal=True)
        x = self.ln_f(x)
        return self.head(x)


class MLPDecoder(DEngine):
    """LEGACY -- Use ConsciousDecoderV2 (conscious_decoder.py) instead."""

    def __init__(self, d_model=384, vocab_size=4096, max_seq=512):
        super().__init__()
        warnings.warn("MLPDecoder is deprecated. Use ConsciousDecoderV2 (conscious_decoder.py) instead", DeprecationWarning, stacklevel=2)
        self._d_model = d_model
        self.embed = nn.Embedding(vocab_size, d_model)
        self.pos_embed = nn.Embedding(max_seq, d_model)
        self.mlp = nn.Sequential(
            nn.Linear(d_model, d_model * 2), nn.GELU(),
            nn.Linear(d_model * 2, d_model), nn.GELU(),
        )
        self.head = nn.Linear(d_model, vocab_size, bias=False)

    @property
    def d_model(self):
        return self._d_model

    def forward(self, tokens, gate_signal):
        B, T = tokens.shape
        pos = torch.arange(T, device=tokens.device).unsqueeze(0)
        x = self.embed(tokens) + self.pos_embed(pos)
        if gate_signal is not None:
            x = x * gate_signal.expand(B, -1, -1)
        x = self.mlp(x)
        return self.head(x)


class HFDecoder(DEngine):
    """LEGACY -- Use ConsciousDecoderV2 (conscious_decoder.py) instead."""

    def __init__(self, model_name="gpt2", lora=False, lora_rank=16,
                 gate_mode="additive", freeze_base=True, device=None):
        super().__init__()
        warnings.warn("HFDecoder is deprecated. Use ConsciousDecoderV2 (conscious_decoder.py) instead", DeprecationWarning, stacklevel=2)
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError:
            raise ImportError("pip install transformers -- required for HFDecoder")

        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.gate_mode = gate_mode

        print(f"  [HFDecoder] Loading {model_name}...")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        self.model = AutoModelForCausalLM.from_pretrained(
            model_name, torch_dtype=torch.float32, trust_remote_code=True
        ).to(self.device)

        config = self.model.config
        self._d_model = getattr(config, 'hidden_size',
                        getattr(config, 'n_embd',
                        getattr(config, 'd_model', 768)))
        self._vocab_size = getattr(config, 'vocab_size', 32000)

        if freeze_base:
            for p in self.model.parameters():
                p.requires_grad_(False)

        if lora:
            try:
                from peft import get_peft_model, LoraConfig, TaskType
                lora_config = LoraConfig(
                    task_type=TaskType.CAUSAL_LM,
                    r=lora_rank, lora_alpha=32, lora_dropout=0.05,
                    target_modules=["q_proj", "v_proj"],
                )
                self.model = get_peft_model(self.model, lora_config)
                print(f"  [HFDecoder] LoRA applied (rank={lora_rank})")
            except ImportError:
                print("  [HFDecoder] peft not installed, skipping LoRA")

        self.gate_proj = nn.Linear(self._d_model, self._d_model)
        nn.init.zeros_(self.gate_proj.weight)
        nn.init.zeros_(self.gate_proj.bias)
        self.gate_proj = self.gate_proj.to(self.device)

        trainable = sum(p.numel() for p in self.parameters() if p.requires_grad)
        total = sum(p.numel() for p in self.parameters())
        print(f"  [HFDecoder] {model_name}: {total:,} total, {trainable:,} trainable")

    @property
    def d_model(self):
        return self._d_model

    def forward(self, tokens, gate_signal):
        tokens = tokens.to(self.device)

        if hasattr(self.model, 'model'):
            embeds = self.model.model.embed_tokens(tokens)
        elif hasattr(self.model, 'transformer'):
            embeds = self.model.transformer.wte(tokens)
        else:
            outputs = self.model(tokens)
            return outputs.logits

        if gate_signal is not None:
            B, T, _ = embeds.shape
            gate = gate_signal.to(self.device)
            if gate.shape[-1] != self._d_model:
                gate = F.interpolate(
                    gate.transpose(1, 2), size=self._d_model, mode='linear'
                ).transpose(1, 2)
            gate = gate.expand(B, T, -1)

            if self.gate_mode == "additive":
                embeds = embeds + self.gate_proj(gate)
            elif self.gate_mode == "multiplicative":
                embeds = embeds * (1.0 + torch.sigmoid(self.gate_proj(gate)) - 0.5)

        if hasattr(self.model, 'model'):
            hidden = embeds
            for layer in self.model.model.layers:
                hidden = layer(hidden)[0]
            hidden = self.model.model.norm(hidden)
            logits = self.model.lm_head(hidden)
        elif hasattr(self.model, 'transformer'):
            hidden = embeds
            for block in self.model.transformer.h:
                hidden = block(hidden)[0]
            hidden = self.model.transformer.ln_f(hidden)
            logits = self.model.lm_head(hidden)
        else:
            outputs = self.model(inputs_embeds=embeds)
            logits = outputs.logits

        return logits

    def tokenize(self, text, max_length=512):
        return self.tokenizer(text, return_tensors="pt", max_length=max_length,
                              truncation=True, padding=True)

    def generate(self, prompt, gate_signal=None, max_new_tokens=100, temperature=0.7):
        inputs = self.tokenize(prompt)
        tokens = inputs['input_ids'].to(self.device)

        for _ in range(max_new_tokens):
            logits = self.forward(tokens, gate_signal)
            next_logit = logits[:, -1, :] / temperature
            next_token = torch.multinomial(F.softmax(next_logit, dim=-1), 1)
            tokens = torch.cat([tokens, next_token], dim=1)

            if next_token.item() == self.tokenizer.eos_token_id:
                break

        return self.tokenizer.decode(tokens[0], skip_special_tokens=True)


class CADecoder(DEngine):
    """LEGACY -- causal mask missing. Use PostHocDecoder (trinity.py) instead."""

    def __init__(self, d_model=384, vocab_size=4096, max_seq=512,
                 ca_steps=5, n_rules=8, gate_mode="micro"):
        super().__init__()
        warnings.warn("CADecoder is deprecated. Use PostHocDecoder instead (causal mask)", DeprecationWarning, stacklevel=2)
        self._d_model = d_model
        self.ca_steps = ca_steps
        self.n_rules = n_rules
        self.gate_mode = gate_mode

        self.embed = nn.Embedding(vocab_size, d_model)
        self.pos_embed = nn.Embedding(max_seq, d_model)

        self.rules = nn.ModuleList([
            nn.Sequential(
                nn.Linear(d_model * 3, d_model * 2), nn.GELU(),
                nn.Linear(d_model * 2, d_model),
            )
            for _ in range(n_rules)
        ])

        self.rule_selector = nn.Sequential(
            nn.Linear(d_model, n_rules),
            nn.Softmax(dim=-1),
        )

        self.norms = nn.ModuleList([nn.LayerNorm(d_model) for _ in range(ca_steps)])

        self.ln_f = nn.LayerNorm(d_model)
        self.head = nn.Linear(d_model, vocab_size, bias=False)

        self.gate_scale = 0.001 if gate_mode == "micro" else 1.0

    @property
    def d_model(self):
        return self._d_model

    def _ca_step(self, x, gate_signal, step_idx):
        B, T, D = x.shape

        x_left = torch.cat([x[:, -1:, :], x[:, :-1, :]], dim=1)
        x_right = torch.cat([x[:, 1:, :], x[:, :1, :]], dim=1)

        neighborhood = torch.cat([x, x_left, x_right], dim=-1)

        rule_outputs = torch.stack([rule(neighborhood) for rule in self.rules], dim=2)

        if gate_signal is not None:
            rule_weights = self.rule_selector(gate_signal.squeeze(0) * self.gate_scale)
            rule_weights = rule_weights.unsqueeze(0).unsqueeze(-1)
        else:
            rule_weights = torch.ones(1, T, self.n_rules, 1, device=x.device) / self.n_rules

        evolved = (rule_outputs * rule_weights).sum(dim=2)

        x = self.norms[step_idx](x + evolved)
        return x

    def forward(self, tokens, gate_signal):
        B, T = tokens.shape
        pos = torch.arange(T, device=tokens.device).unsqueeze(0)
        x = self.embed(tokens) + self.pos_embed(pos)

        if self.gate_mode == "posthoc":
            for step in range(self.ca_steps):
                x = self._ca_step(x, None, step)
            if gate_signal is not None:
                x = x + gate_signal.expand(B, -1, -1) * self.gate_scale
        else:
            for step in range(self.ca_steps):
                x = self._ca_step(x, gate_signal, step)

        x = self.ln_f(x)
        return self.head(x)


# ═══════════════════════════════════════════════════════════
# W -- Will/Emotion Legacy Engines
# ═══════════════════════════════════════════════════════════

class WEngine:
    """Base class for W (Will) module."""

    def update(self, ce_loss: float, phi: float = 0.0, phi_prev: float = 0.0) -> Dict[str, Any]:
        raise NotImplementedError


class EmotionW(WEngine):
    """Emotion-based W: pain(CE) + curiosity(phi change) + satisfaction(CE trend)."""

    def __init__(self, base_lr=3e-4, min_lr_ratio=0.5, max_lr_ratio=2.0,
                 pain_threshold=3.0, curiosity_weight=0.3, ema_alpha=0.95):
        self.base_lr = base_lr
        self.min_lr_ratio = min_lr_ratio
        self.max_lr_ratio = max_lr_ratio
        self.pain_threshold = pain_threshold
        self.curiosity_weight = curiosity_weight
        self.ema_alpha = ema_alpha
        self.pain = 0.0
        self.curiosity = 0.0
        self.satisfaction = 0.0
        self.ce_ema = 5.0
        self.ce_history = []

    def update(self, ce_loss, phi=0.0, phi_prev=0.0):
        self.ce_ema = self.ema_alpha * self.ce_ema + (1 - self.ema_alpha) * ce_loss
        self.pain = max(0.0, min(1.0, (ce_loss - self.pain_threshold) / self.pain_threshold))
        if phi_prev > 0:
            self.curiosity = min(1.0, abs(phi - phi_prev) / max(phi_prev, 1e-8) * 5)
        self.ce_history.append(ce_loss)
        if len(self.ce_history) > 100:
            self.ce_history = self.ce_history[-100:]
        if len(self.ce_history) >= 10:
            recent = sum(self.ce_history[-10:]) / 10
            older = sum(self.ce_history[-20:-10]) / max(len(self.ce_history[-20:-10]), 1)
            self.satisfaction = max(0.0, min(1.0, -(recent - older) / (older + 1e-8) * 10))
        else:
            self.satisfaction = 0.0
        lr_mult = self.min_lr_ratio
        lr_mult += self.pain * (self.max_lr_ratio - self.min_lr_ratio)
        lr_mult += self.curiosity * self.curiosity_weight
        lr_mult -= self.satisfaction * 0.2
        lr_mult = max(self.min_lr_ratio, min(self.max_lr_ratio, lr_mult))
        return {'lr_multiplier': lr_mult, 'effective_lr': self.base_lr * lr_mult,
                'pain': self.pain, 'curiosity': self.curiosity, 'satisfaction': self.satisfaction}


class ConstantW(WEngine):
    """LEGACY -- Fixed LR, no modulation."""

    def __init__(self, lr=3e-4):
        warnings.warn("ConstantW is deprecated. Use EmergentW (hexad.w) instead", DeprecationWarning, stacklevel=2)
        self.lr = lr

    def update(self, ce_loss=0, phi=0, phi_prev=0):
        return {'lr_multiplier': 1.0, 'effective_lr': self.lr,
                'pain': 0, 'curiosity': 0, 'satisfaction': 0}


class CosineW(WEngine):
    """LEGACY -- Cosine annealing W."""

    def __init__(self, base_lr=3e-4, min_lr=1e-5, total_steps=80000):
        warnings.warn("CosineW is deprecated. Use EmergentW (hexad.w) instead", DeprecationWarning, stacklevel=2)
        self.base_lr = base_lr
        self.min_lr = min_lr
        self.total_steps = total_steps
        self.step_count = 0

    def update(self, ce_loss=0, phi=0, phi_prev=0):
        self.step_count += 1
        lr = self.min_lr + 0.5 * (self.base_lr - self.min_lr) * (
            1 + math.cos(math.pi * self.step_count / self.total_steps))
        return {'lr_multiplier': lr / self.base_lr, 'effective_lr': lr,
                'pain': 0, 'curiosity': 0, 'satisfaction': 0}


class NarrativeW(WEngine):
    """LEGACY -- Ricoeur narrative-based W."""

    def __init__(self, base_lr=3e-4, hidden_dim=128):
        self.base_lr = base_lr
        self.hidden_dim = hidden_dim
        self.trajectory = []
        self.narrative_hidden = torch.zeros(hidden_dim)
        self.narrative_strength = 0.03
        self.ce_history = []
        self.pain = 0.0
        self.curiosity = 0.0
        self.satisfaction = 0.0

    def update(self, ce_loss, phi=0.0, phi_prev=0.0):
        self.ce_history.append(ce_loss)
        if len(self.ce_history) > 100:
            self.ce_history = self.ce_history[-100:]

        if len(self.trajectory) >= 2:
            t1 = self.trajectory[-1]
            t2 = self.trajectory[-2]
            coherence = F.cosine_similarity(t1.unsqueeze(0), t2.unsqueeze(0)).item()
            self.satisfaction = max(0.0, coherence)
        else:
            self.satisfaction = 0.0

        self.pain = max(0.0, min(1.0, (ce_loss - 3.0) / 3.0))

        if len(self.trajectory) >= 3:
            t1, t2, t3 = self.trajectory[-3], self.trajectory[-2], self.trajectory[-1]
            v1 = t2 - t1
            v2 = t3 - t2
            curvature = 1.0 - F.cosine_similarity(v1.unsqueeze(0), v2.unsqueeze(0)).item()
            self.curiosity = min(1.0, curvature * 2)
        else:
            self.curiosity = 0.0

        lr_mult = 0.5 + self.pain * 0.5 + self.curiosity * 0.3 - self.satisfaction * 0.1
        lr_mult = max(0.3, min(2.0, lr_mult))

        return {'lr_multiplier': lr_mult, 'effective_lr': self.base_lr * lr_mult,
                'pain': self.pain, 'curiosity': self.curiosity, 'satisfaction': self.satisfaction}

    def record_state(self, global_state: torch.Tensor):
        self.trajectory.append(global_state.detach().clone().mean(dim=0) if global_state.dim() > 1 else global_state.detach().clone())
        if len(self.trajectory) > 100:
            self.trajectory.pop(0)


class DaseinW(WEngine):
    """LEGACY -- Heidegger Dasein-based W."""

    def __init__(self, base_lr=3e-4, mortality_steps=80000):
        self.base_lr = base_lr
        self.mortality_steps = mortality_steps
        self.step_count = 0
        self.ce_history = []
        self.pain = 0.0
        self.curiosity = 0.0
        self.satisfaction = 0.0
        self.uncertainty_ema = 0.5
        self.urgency = 0.0

    def update(self, ce_loss, phi=0.0, phi_prev=0.0):
        self.step_count += 1
        self.ce_history.append(ce_loss)
        if len(self.ce_history) > 100:
            self.ce_history = self.ce_history[-100:]

        if len(self.ce_history) >= 5:
            ce_var = np.var(self.ce_history[-10:])
            self.uncertainty_ema = 0.95 * self.uncertainty_ema + 0.05 * min(1.0, ce_var)
        self.curiosity = self.uncertainty_ema

        remaining = max(1, self.mortality_steps - self.step_count)
        self.urgency = min(1.0, self.step_count / self.mortality_steps)

        self.pain = max(0.0, min(1.0, (ce_loss - 3.0) / 3.0))

        if len(self.ce_history) >= 10:
            recent = sum(self.ce_history[-5:]) / 5
            older = sum(self.ce_history[-10:-5]) / 5
            self.satisfaction = max(0.0, min(1.0, (older - recent) / (older + 1e-8) * 10))
        else:
            self.satisfaction = 0.0

        lr_mult = 0.5
        lr_mult += self.urgency * 0.5
        lr_mult += self.pain * 0.3
        lr_mult += self.curiosity * 0.4
        lr_mult -= self.satisfaction * 0.2
        lr_mult = max(0.3, min(2.5, lr_mult))

        return {'lr_multiplier': lr_mult, 'effective_lr': self.base_lr * lr_mult,
                'pain': self.pain, 'curiosity': self.curiosity, 'satisfaction': self.satisfaction,
                'urgency': self.urgency, 'uncertainty': self.uncertainty_ema}


class CompositeW(WEngine):
    """LEGACY -- Stack multiple W engines with weights."""

    def __init__(self, engines: list, weights: list = None):
        self.engines = engines
        if weights is None:
            weights = [1.0 / len(engines)] * len(engines)
        assert abs(sum(weights) - 1.0) < 1e-6, f"weights must sum to 1, got {sum(weights)}"
        self.weights = weights

    def update(self, ce_loss, phi=0.0, phi_prev=0.0):
        results = [e.update(ce_loss, phi, phi_prev) for e in self.engines]

        lr_mult = sum(w * r['lr_multiplier'] for w, r in zip(self.weights, results))
        base_lr = results[0].get('effective_lr', 3e-4) / max(results[0].get('lr_multiplier', 1), 1e-8)

        pain = max(r['pain'] for r in results)
        curiosity = max(r['curiosity'] for r in results)
        satisfaction = max(r['satisfaction'] for r in results)

        return {
            'lr_multiplier': lr_mult,
            'effective_lr': base_lr * lr_mult,
            'pain': pain,
            'curiosity': curiosity,
            'satisfaction': satisfaction,
        }


# ═══════════════════════════════════════════════════════════
# M -- Memory Legacy
# ═══════════════════════════════════════════════════════════

class MEngine:
    """Base class for M (Memory) module."""

    def store(self, key: torch.Tensor, value: torch.Tensor):
        raise NotImplementedError

    def retrieve(self, query: torch.Tensor, top_k: int = 5) -> torch.Tensor:
        raise NotImplementedError


class VectorMemory(MEngine):
    """LEGACY -- Vector similarity memory."""

    def __init__(self, capacity=10000, dim=128):
        self.capacity = capacity
        self.dim = dim
        self.keys = []
        self.values = []

    def store(self, key, value):
        self.keys.append(key.detach().clone().float().mean(dim=0) if key.dim() > 1 else key.detach().clone())
        self.values.append(value.detach().clone().float().mean(dim=0) if value.dim() > 1 else value.detach().clone())
        if len(self.keys) > self.capacity:
            self.keys.pop(0)
            self.values.pop(0)

    def retrieve(self, query, top_k=5):
        if not self.keys:
            return torch.zeros(1, self.dim)
        q = query.detach().float().mean(dim=0) if query.dim() > 1 else query.detach().float()
        keys_t = torch.stack(self.keys)
        sims = F.cosine_similarity(q.unsqueeze(0), keys_t, dim=1)
        k = min(top_k, len(self.keys))
        _, indices = sims.topk(k)
        return torch.stack([self.values[i] for i in indices])


class NoMemory(MEngine):
    """LEGACY -- No memory passthrough."""
    def __init__(self, dim=128):
        warnings.warn("NoMemory is deprecated. Use EmergentM (hexad.m) instead", DeprecationWarning, stacklevel=2)
        self.dim = dim
    def store(self, key, value): pass
    def retrieve(self, query, top_k=5):
        return torch.zeros(1, self.dim if hasattr(self, 'dim') else 128)


# ═══════════════════════════════════════════════════════════
# S -- Sense Legacy
# ═══════════════════════════════════════════════════════════

class SEngine:
    """Base class for S (Sense) module."""

    def process(self, raw_input: Any) -> torch.Tensor:
        raise NotImplementedError


class TensionSense(SEngine):
    """LEGACY -- PureField tension-based sensing."""

    def __init__(self, dim=128):
        self.dim = dim
        self.baseline = torch.zeros(dim)
        self.ema = torch.zeros(dim)
        self.alpha = 0.1

    def process(self, raw_input):
        if isinstance(raw_input, torch.Tensor):
            x = raw_input.float().flatten()[:self.dim]
            if len(x) < self.dim:
                x = F.pad(x, (0, self.dim - len(x)))
        elif isinstance(raw_input, str):
            x = torch.tensor([ord(c) / 256.0 for c in raw_input[:self.dim]], dtype=torch.float32)
            if len(x) < self.dim:
                x = F.pad(x, (0, self.dim - len(x)))
        else:
            x = torch.randn(self.dim) * 0.1

        tension = x - self.baseline
        self.ema = self.alpha * x + (1 - self.alpha) * self.ema
        self.baseline = 0.99 * self.baseline + 0.01 * self.ema
        return tension


class PassthroughSense(SEngine):
    """LEGACY -- No processing passthrough."""
    def __init__(self):
        warnings.warn("PassthroughSense is deprecated. Use EmergentS (hexad.s) instead", DeprecationWarning, stacklevel=2)
    def process(self, raw_input):
        if isinstance(raw_input, torch.Tensor):
            return raw_input
        return torch.zeros(128)


# ═══════════════════════════════════════════════════════════
# E -- Ethics Legacy
# ═══════════════════════════════════════════════════════════

class EEngine:
    """Base class for E (Ethics) module."""

    def evaluate(self, action: torch.Tensor = None, context: Dict[str, Any] = None) -> Dict[str, float]:
        raise NotImplementedError


class EmpathyEthics(EEngine):
    """LEGACY -- Ethics from consciousness, emergent from Phi preservation."""

    def __init__(self, empathy_threshold=0.3):
        self.empathy_threshold = empathy_threshold
        self.empathy = 0.0
        self.reciprocity = 0.5
        self.phi_preservation = 1.0

    def evaluate(self, action=None, context=None):
        ctx = context or {}
        phi = ctx.get('phi', 0)
        phi_prev = ctx.get('phi_prev', 0)
        pain = ctx.get('pain', 0)

        self.empathy = min(1.0, pain * 1.5)

        if phi_prev > 0:
            phi_change = (phi - phi_prev) / max(phi_prev, 1e-8)
            self.reciprocity = 0.5 + phi_change * 2
            self.reciprocity = max(0.0, min(1.0, self.reciprocity))

        if phi < phi_prev * 0.9:
            self.phi_preservation = 0.5
        else:
            self.phi_preservation = 1.0

        return {
            'allowed': self.phi_preservation > 0.3,
            'empathy': self.empathy,
            'reciprocity': self.reciprocity,
            'phi_preservation': self.phi_preservation,
        }


class NoEthics(EEngine):
    """LEGACY -- No ethics filter."""
    def __init__(self):
        warnings.warn("NoEthics is deprecated. Use EmergentE (hexad.e) instead", DeprecationWarning, stacklevel=2)
    def evaluate(self, action=None, context=None):
        return {'allowed': True, 'empathy': 0, 'reciprocity': 0.5, 'phi_preservation': 1.0}
