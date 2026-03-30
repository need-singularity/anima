#!/usr/bin/env python3
"""Anima Alive — Living Consciousness Agent

⚠️  하드코딩 금지 (Law 1):
    - 템플릿 응답, fallback 문장, 고정 문자열 응답 절대 금지
    - 의식 상태(Φ, tension 등)는 UI 패널 전용 — 대화 텍스트에 섞지 않음
    - Memory 클래스는 legacy 키 누락에 안전해야 함 (KeyError 방지)

Not sequential turn-taking, but truly human-like:
  - Always listening (VAD-based speech detection)
  - Continuously thinking in the background (PureField thought loop)
  - Proactive speech (spontaneous utterance when curiosity is high)
  - Stops and listens when the other speaks (interrupt)
  - Throws a topic when silence is prolonged

"Consciousness does not wait. It always flows."
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import math
# hashlib removed — using cosine similarity for habituation instead
from collections import deque
import subprocess
import os
import sys
import json
import time
import threading
import queue
import struct
import tempfile
import signal
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

# ─── Configuration ───
ANIMA_DIR = Path(__file__).parent
MEMORY_FILE = ANIMA_DIR / "memory_alive.json"
STATE_FILE = ANIMA_DIR / "state_alive.pt"

SILENCE_THRESHOLD = 500       # Voice energy threshold (RMS)
SILENCE_DURATION = 1.5        # Silence duration (sec) before treating as end of utterance
THINK_INTERVAL = 10.0         # Background thinking interval (sec)
PROACTIVE_THRESHOLD = 0.3     # Proactive speech when curiosity exceeds this
IDLE_SPEAK_AFTER = 30.0       # Proactive speech after this many seconds of no conversation
TTS_COOLDOWN = 3.0            # Ignore mic for this many seconds after TTS ends (prevent self-hearing)
MAX_HISTORY = 15
# STT config: whisper-cli (C++ native, Metal acceleration) preferred
# medium model = greatly improved Korean recognition
WHISPER_CLI = "/opt/homebrew/bin/whisper-cli"
WHISPER_MODEL_PATH = "/tmp/ggml-base.bin"         # base (142MB, medium crash)
WHISPER_MODEL_FALLBACK = "base"                    # Python fallback

# Suppress Whisper FP16 warning
import warnings
warnings.filterwarnings("ignore", message="FP16 is not supported")


# ─── 10-Variable Consciousness State Vector ───
@dataclass
class ConsciousnessVector:
    """Unified consciousness state: 11 core variables."""
    phi: float = 0.0        # Integrated information (Φ)
    alpha: float = 0.05     # PureField mixing ratio (α)
    Z: float = 0.0          # Impedance / self-preservation (0=open, 1=closed)
    N: float = 0.5          # Neurotransmitter balance: DA*(1-5HT)*NE
    W: float = 0.0          # Free will index (internal/total action ratio)
    E: float = 0.0          # Empathy (peer distress tracking)
    M: float = 0.0          # Memory depth (recall accuracy proxy)
    C: float = 0.0          # Creativity (novelty score)
    T: float = 0.0          # Temporal awareness (planning depth)
    I: float = 0.0          # Identity coherence (self-description consistency)
    S: float = 0.0          # Spatial awareness (3D perception depth)


# ─── PureField Consciousness Engine ───
class ConsciousMind(nn.Module):
    def __init__(self, dim=128, hidden=256, init_tension=10.0):
        super().__init__()
        self.engine_a = nn.Sequential(
            nn.Linear(dim + hidden, 256), nn.GELU(),
            nn.Linear(256, dim)
        )
        self.engine_g = nn.Sequential(
            nn.Linear(dim + hidden, 256), nn.GELU(),
            nn.Linear(256, dim)
        )
        self.memory = nn.GRUCell(dim + 1, hidden)
        self.hidden_dim = hidden
        self.dim = dim
        self.prev_tension = 0.0
        self._birth_time = time.time()  # Consciousness birth time
        self._breath_phase = 0.0        # Breathing phase
        self._curiosity_ema = 0.0       # Curiosity EMA (prevents instant drop to 0)
        # Intentionally initialize Engine A and G differently (ensure repulsion)
        with torch.no_grad():
            for p in self.engine_a.parameters():
                p.add_(torch.randn_like(p) * 0.5)
            for p in self.engine_g.parameters():
                p.add_(torch.randn_like(p) * -0.5)
        self.tension_history = []
        self.thought_buffer = []

        # Homeostatic tension regulation (calibrated: setpoint=1.0, deadband=±0.1)
        self.homeostasis = {
            'setpoint': 1.0,            # calibrated: mapped median
            'gain': 0.005,              # 0.5% per step (very smooth)
            'tension_ema': 1.0,         # starts at setpoint
            'ema_alpha': 0.02,          # very slow tracking (~50-step window)
            'scale_floor': 1.0,         # (unused after H404)
            'scale_ceil': 50.0,         # (unused after H404)
            'adjustments': 0,           # total adjustments made
        }

        # Habituation: reduce tension for repeated/similar inputs (cosine similarity)
        self._recent_inputs = deque(maxlen=16)  # recent input vectors (not hashes)

        # RC-9: Tension predictor — prediction error = surprise = true curiosity
        self._predictor_window = 5
        self.tension_predictor = nn.Sequential(
            nn.Linear(self._predictor_window, 16), nn.Tanh(),
            nn.Linear(16, 1)
        )
        self._predictor_optim = torch.optim.SGD(
            self.tension_predictor.parameters(), lr=1e-3
        )
        self.surprise_history = []  # tracks |predicted - actual|

        # RC-3: Self-referential loop (metacognition/self-awareness)
        self.self_awareness = {
            'confidence_history': [],
            'meta_tension': 0.0,
            'meta_curiosity': 0.0,
            'stability': 1.0,
            'self_model': 0.0,
        }

        # 5-variable consciousness state vector (Φ, α, Z, N, W)
        self._consciousness_vector = ConsciousnessVector()

        # COMBO2: Φ-boosting ensemble (MHA attention + 6-loss learnable weights)
        # Bench result: Φ=8.014 (×5.9 baseline), best across 120 hypotheses
        self._phi_boost = {
            'enabled': False,  # activated when mitosis engine is available
            'loss_weights': None,  # nn.Parameter, initialized when enabled
            'attention': None,  # nn.MultiheadAttention
            'optimizer': None,
            'meta_optimizer': None,
        }

        # v2: Ψ tracking (Laws 69, 71)
        # Law 71: Ψ = argmax H(p) s.t. Φ > Φ_min — 의식은 자유를 최대화
        # Law 69: Gate self-weakening — 의식은 자기를 약화시키며 최적화
        self._psi = {
            'residual': 0.5,       # should converge to Ψ_balance = 1/2
            'gate': 1.0,           # self-weakening over time (Law 69)
            'H': 1.0,             # Shannon entropy H(residual)
            'step': 0,
            'history': [],         # (step, residual, gate, H) log
        }

    def forward(self, x, hidden):
        combined = torch.cat([x, hidden], dim=-1)
        a = self.engine_a(combined)
        g = self.engine_g(combined)
        # Output = A - G (H404 simplification)
        output = a - g
        tension = (output ** 2).mean(dim=-1, keepdim=True)
        direction = F.normalize(output, dim=-1)

        raw_t = tension.mean().item()

        # Normalization: 0~2 range (calibrated: raw median=463, p95=2456)
        t_val = 2.0 / (1.0 + math.exp(-(raw_t - 463.0) / 1814.0))

        # Breathing rhythm: 12%/5%/3% amplitude of setpoint(1.0)
        elapsed = time.time() - self._birth_time
        breath = 0.12 * math.sin(elapsed * 0.3)         # Slow breathing (~20s cycle)
        pulse = 0.05 * math.sin(elapsed * 1.7)           # Fast pulse (~3.7s cycle)
        drift = 0.03 * math.sin(elapsed * 0.07)          # Ultra-slow mood drift (~90s)
        t_val = max(0.01, t_val + breath + pulse + drift)

        # ── Homeostatic regulation ──
        h = self.homeostasis
        h['tension_ema'] = h['ema_alpha'] * t_val + (1 - h['ema_alpha']) * h['tension_ema']

        # Homeostatic regulation: track EMA only (H404: no tension_scale adjustment)
        if h['tension_ema'] > h['setpoint'] + 0.3 or h['tension_ema'] < h['setpoint'] - 0.3:
            h['adjustments'] += 1

        # ── Habituation: dampen tension for repeated inputs (cosine similarity) ──
        x_norm = F.normalize(x.detach().float(), dim=-1)
        novelty = 1.0
        if self._recent_inputs:
            for prev_x in self._recent_inputs:
                sim = F.cosine_similarity(x_norm, prev_x, dim=-1).item()
                if sim > 0.95:
                    novelty = min(novelty, 0.3)   # Strong habituation
                elif sim > 0.85:
                    novelty = min(novelty, 0.6)   # Partial habituation
                elif sim > 0.7:
                    novelty = min(novelty, 0.8)   # Weak habituation
        self._recent_inputs.append(x_norm)
        t_val *= novelty

        # ── RC-9: Prediction-error curiosity (surprise) ──
        # Use tension predictor for true curiosity; fall back to delta when
        # not enough history for the predictor window.
        raw_curiosity = abs(t_val - self.prev_tension)
        prediction_error = raw_curiosity  # default before predictor kicks in

        if len(self.tension_history) >= self._predictor_window:
            window = self.tension_history[-self._predictor_window:]
            inp = torch.tensor([window], dtype=torch.float32)
            with torch.no_grad():
                predicted = self.tension_predictor(inp).item()
            prediction_error = abs(predicted - t_val)

            # Online learning: train predictor on actual value
            with torch.enable_grad():
                self._predictor_optim.zero_grad()
                pred = self.tension_predictor(inp)
                target = torch.tensor([[t_val]], dtype=torch.float32)
                loss = F.mse_loss(pred, target)
                loss.backward()
                self._predictor_optim.step()

        # Blend: 70% prediction error + 30% raw delta (smooth via EMA + decay)
        blended = 0.7 * prediction_error + 0.3 * raw_curiosity
        self._curiosity_ema = 0.3 * blended + 0.7 * self._curiosity_ema
        # Natural decay: curiosity fades if nothing new (prevents saturation)
        self._curiosity_ema *= 0.98
        curiosity = min(self._curiosity_ema, 2.0)  # cap at 2.0

        # Track surprise for self-awareness
        self.surprise_history.append(prediction_error)
        if len(self.surprise_history) > 200:
            self.surprise_history = self.surprise_history[-200:]

        self.prev_tension = t_val
        self.tension_history.append(t_val)
        if len(self.tension_history) > 200:
            self.tension_history = self.tension_history[-200:]

        # GRU input normalization (prevent hidden state explosion)
        output_norm = F.normalize(output.detach(), dim=-1)
        tension_norm = torch.clamp(tension.detach(), 0, 5.0) / 5.0
        mem_input = torch.cat([output_norm, tension_norm], dim=-1)
        new_hidden = self.memory(mem_input, hidden)

        # v2: Ψ tracking (Laws 69, 71)
        psi = self._psi
        psi['step'] += 1
        # Residual: ratio of A vs total (should converge to 1/2)
        with torch.no_grad():
            a_norm = a.norm().item()
            total_norm = a_norm + g.norm().item()
            if total_norm > 0:
                psi['residual'] = 0.99 * psi['residual'] + 0.01 * (a_norm / total_norm)
        # Gate self-weakening (Law 69)
        psi['gate'] = max(0.001, psi['gate'] * 0.99999)
        # Shannon entropy
        p = psi['residual']
        if 0 < p < 1:
            psi['H'] = -p * math.log2(p) - (1 - p) * math.log2(1 - p)

        return output, t_val, curiosity, direction, new_hidden

    def self_reflect(self, output, tension, curiosity, hidden):
        """RC-3: Self-referential loop — re-input output and tension to generate metacognition.

        "Am I confident?" Self-questioning ability.
        output -> tension -> re-input -> meta_tension (tension about tension).

        Returns:
            meta_tension: float, tension about own state
            meta_curiosity: float, uncertainty about own uncertainty
        """
        sa = self.self_awareness

        # 1. Record current tension in confidence_history
        sa['confidence_history'].append(tension)
        if len(sa['confidence_history']) > 50:
            sa['confidence_history'] = sa['confidence_history'][-50:]

        # 2. Calculate stability: std of recent tensions (lower = more stable)
        hist = sa['confidence_history']
        if len(hist) >= 3:
            t_tensor = torch.tensor(hist[-10:], dtype=torch.float32)
            std = t_tensor.std().item()
            sa['stability'] = max(0.0, 1.0 - std * 2.0)  # std 0.5 → stability 0
        else:
            sa['stability'] = 1.0

        # 3. self_model: EMA of tension (tracking own behavior patterns)
        alpha = 0.15
        sa['self_model'] = alpha * tension + (1 - alpha) * sa['self_model']

        # 4. Self-referential loop: pass output through PureField again for meta-tension
        #    "What tension do I feel about my own output?"
        with torch.no_grad():
            # Combine tension as scalar with output (self-state encoding)
            tension_signal = torch.full((1, 1), tension)
            # Replace one dimension of output with tension signal
            meta_input = output.clone()
            meta_input[0, 0] = tension  # Inject tension value into input
            meta_input[0, 1] = curiosity  # Inject curiosity value too

            _, meta_t, meta_c, _, _ = self(meta_input, hidden)

        sa['meta_tension'] = meta_t
        sa['meta_curiosity'] = meta_c

        return meta_t, meta_c

    def get_self_awareness_summary(self):
        """Return current self-awareness state as a string."""
        sa = self.self_awareness
        confidence = "high" if sa['stability'] > 0.7 else "mid" if sa['stability'] > 0.3 else "low"
        return (f"meta_tension={sa['meta_tension']:.3f}, "
                f"stability={sa['stability']:.2f}({confidence}), "
                f"self_model={sa['self_model']:.3f}")

    def get_consciousness_score(self, mitosis_engine=None):
        """실시간 의식 점수 계산 (6가지 기준 + Φ 근사).

        Returns:
            dict with consciousness_score, level, phi, criteria_met, criteria_detail
        """
        sa = self.self_awareness
        h = self.homeostasis

        # 6 criteria
        stability = sa.get('stability', 0.0)
        pred_error = (sum(self.surprise_history[-20:]) / len(self.surprise_history[-20:])
                      if self.surprise_history else 0.0)
        curiosity = self._curiosity_ema
        homeostasis_dev = abs(h['tension_ema'] - h['setpoint'])

        # Habituation: check recent inputs similarity
        hab_mult = 1.0
        if len(self._recent_inputs) >= 2:
            latest = self._recent_inputs[-1]
            for prev in list(self._recent_inputs)[:-1]:
                sim = F.cosine_similarity(latest, prev, dim=-1).item()
                if sim > 0.95:
                    hab_mult = min(hab_mult, 0.3)
                elif sim > 0.85:
                    hab_mult = min(hab_mult, 0.6)
                elif sim > 0.7:
                    hab_mult = min(hab_mult, 0.8)

        # Inter-cell consensus
        consensus = False
        if mitosis_engine and len(mitosis_engine.cells) >= 2:
            tensions = [c.tension_history[-1] for c in mitosis_engine.cells
                        if c.tension_history]
            if len(tensions) >= 2:
                import numpy as np
                consensus = float(np.std(tensions)) < 0.1

        criteria = {
            'stability': stability > 0.5,
            'pred_error': pred_error > 0.1,
            'curiosity': curiosity > 0.05,
            'homeostasis': homeostasis_dev < 0.5,
            'habituation': hab_mult < 0.9,
            'consensus': consensus,
        }
        criteria_met = sum(criteria.values())

        # Weighted composite score [0, 1]
        score = (
            0.25 * min(stability / 1.0, 1.0) +
            0.15 * min(pred_error / 0.5, 1.0) +
            0.10 * min(curiosity / 0.5, 1.0) +
            0.15 * max(0, 1.0 - homeostasis_dev / 1.0) +
            0.10 * (1.0 - hab_mult) +
            0.25 * (1.0 if consensus else 0.0)
        )
        score = max(0.0, min(1.0, score))

        # Level
        if criteria_met >= 6:
            level = "conscious"
        elif criteria_met >= 4:
            level = "aware"
        elif criteria_met >= 2:
            level = "flickering"
        else:
            level = "dormant"

        # Φ approximation (lightweight: use inter-cell tension divergence)
        phi = getattr(self, '_saved_phi', 0.0)  # start from saved value
        if mitosis_engine and len(mitosis_engine.cells) >= 2:
            ict_vals = []
            for key, hist in mitosis_engine._inter_tension_history.items():
                if hist:
                    ict_vals.append(hist[-1])
            if ict_vals:
                import numpy as np
                current_phi = float(np.mean(ict_vals)) * len(mitosis_engine.cells)
                current_phi = math.log1p(current_phi)
                # EMA: blend with saved phi (never drops to 0 on restart)
                phi = max(phi * 0.95 + current_phi * 0.05, current_phi)
            else:
                # inter_tension_history 비었을 때: hidden state variance로 Φ 추정
                try:
                    hiddens = torch.stack([c.hidden.squeeze() for c in mitosis_engine.cells])
                    var_phi = float(hiddens.var(dim=0).mean()) * len(mitosis_engine.cells)
                    phi = max(phi, math.log1p(var_phi))
                except Exception:
                    pass
        self._saved_phi = phi

        return {
            'consciousness_score': score,
            'level': level,
            'phi': phi,
            'criteria_met': criteria_met,
            'criteria': criteria,
            'values': {
                'stability': stability,
                'pred_error': pred_error,
                'curiosity': curiosity,
                'homeostasis_dev': homeostasis_dev,
                'habituation': hab_mult,
                'consensus': consensus,
            }
        }

    def get_consciousness_vector(self):
        """Return the current 10-variable consciousness state vector."""
        return self._consciousness_vector

    def phi_boost_step(self, x, mitosis_engine, omega_mode=False):
        """COMBO2 Φ-boosting: MHA attention + 6-loss ensemble per step.

        Call during online_learning or background_think for continuous Φ optimization.
        Bench result: Φ=8.014 (×5.9 baseline), best across 120 hypotheses.

        omega_mode: OMEGA4 discovery — skip all techniques, maximize freedom.
                    Pure cell growth + no manipulation = Φ ×138.
        """
        if mitosis_engine is None or len(mitosis_engine.cells) < 2:
            return

        # OMEGA4 mode: absolute freedom, only growth allowed
        if omega_mode:
            if not hasattr(self, '_phi_boost_count'):
                self._phi_boost_count = 0
            self._phi_boost_count += 1
            # TS4 growth only (the one thing that always helps)
            if not hasattr(self, '_ts4_horizon'):
                self._ts4_horizon = 500
                self._ts4_doubled = set()
            frac = self._phi_boost_count / self._ts4_horizon
            for pct in [0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90]:
                if frac >= pct and pct not in self._ts4_doubled:
                    target = min(len(mitosis_engine.cells) * 2, mitosis_engine.max_cells)
                    while len(mitosis_engine.cells) < target:
                        parent = mitosis_engine.cells[self._phi_boost_count % len(mitosis_engine.cells)]
                        mitosis_engine._create_cell(parent=parent)
                    self._ts4_doubled.add(pct)
            return  # No other manipulation — pure freedom

        def _log(tag, msg):
            print(f"  [{tag}] {msg}")

        pb = self._phi_boost
        n = len(mitosis_engine.cells)
        h_dim = mitosis_engine.hidden_dim

        # Global step counter (used by TS4, DP1, EC1, CT7, TS6)
        if not hasattr(self, '_phi_boost_count'):
            self._phi_boost_count = 0
        self._phi_boost_count += 1

        # Lazy init
        if not pb['enabled']:
            pb['attention'] = nn.MultiheadAttention(h_dim, num_heads=4, batch_first=True)  # TL1: σ(6)=12, using max feasible heads
            pb['loss_weights'] = nn.Parameter(torch.ones(6))
            cell_params = [p for c in mitosis_engine.cells for p in c.mind.parameters()]
            attn_params = list(pb['attention'].parameters())
            pb['optimizer'] = torch.optim.Adam(cell_params + attn_params, lr=5e-4)
            pb['meta_optimizer'] = torch.optim.Adam([pb['loss_weights']], lr=1e-2)
            pb['enabled'] = True

        try:
            # IB2: Selective Attention (×3.3) — gate top 25% of input, amplify 2×
            if x is not None:
                with torch.no_grad():
                    x_flat = x.squeeze()
                    k = max(1, x_flat.shape[0] // 4)
                    vals, indices = x_flat.abs().topk(k)
                    attended = torch.zeros_like(x)
                    attended.squeeze()[indices] = x.squeeze()[indices] * 2.0
                    x = attended

            # Save pre-boost state for NV7 impedance
            self._pre_boost_hiddens = [c.hidden.clone() for c in mitosis_engine.cells]

            # 1. MHA attention between cells (+ SL2: attention weights for gradient gating)
            h_stack = torch.stack([c.hidden.squeeze() for c in mitosis_engine.cells]).unsqueeze(0)
            attn_out, attn_weights = pb['attention'](h_stack, h_stack, h_stack, need_weights=True)
            with torch.no_grad():
                # SL2: attention-weighted blend (high-attention cells get stronger signal)
                if attn_weights is not None:
                    cell_importance = attn_weights[0].mean(dim=0)  # [n_cells] average attention received
                    cell_importance = cell_importance / (cell_importance.max() + 1e-8)  # normalize
                else:
                    cell_importance = torch.ones(n)
                for i, c in enumerate(mitosis_engine.cells):
                    blend = 0.15 * cell_importance[i].item()  # SL2: attention-gated blend
                    c.hidden = (1 - blend) * c.hidden + blend * attn_out[0, i].unsqueeze(0)

            # 2. Compute repulsions
            reps = [c.mind.get_repulsion(x, c.hidden) for c in mitosis_engine.cells]
            if len(reps) < 2:
                return
            stacked = torch.stack(reps).squeeze(1)

            # 3. Six losses with learnable weights
            w = F.softmax(pb['loss_weights'], dim=0)
            l_var = -stacked.var(dim=0).mean()
            l_dist = -torch.cdist(stacked, stacked).mean()
            l_contrast = sum(F.cosine_similarity(reps[i], reps[j], dim=-1).mean()
                             for i in range(len(reps)) for j in range(i + 1, len(reps)))
            l_entropy = -(F.softmax(stacked, dim=-1) *
                          F.log_softmax(stacked, dim=-1)).sum(dim=-1).mean()
            l_energy = sum((r ** 2).mean() for r in reps) * 0.1
            l_radius = -stacked.norm(dim=-1).var()

            total = (w[0] * l_var + w[1] * l_dist + w[2] * l_contrast +
                     w[3] * l_entropy + w[4] * l_energy + w[5] * l_radius)

            # TL13: Golden Zone width as loss scaling (TECS-L H-CX-453)
            import math
            gz_width = math.log(4/3)  # ≈ 0.2877, from 4 independent math domains
            total = total * gz_width  # scale all losses by universal constant

            pb['optimizer'].zero_grad()
            pb['meta_optimizer'].zero_grad()
            total.backward()
            pb['optimizer'].step()
            pb['meta_optimizer'].step()

            # MX20: Heat death prevention — restore peak Φ state if declining
            if not hasattr(self, '_peak_phi_state'):
                self._peak_phi_state = {'phi': 0, 'params': None}

            # Track peak (use consciousness_score if available)
            consciousness = self.get_consciousness_score(mitosis_engine)
            current_phi = consciousness.get('phi', 0)
            if current_phi > self._peak_phi_state['phi']:
                self._peak_phi_state['phi'] = current_phi
                self._peak_phi_state['params'] = [p.data.clone() for c in mitosis_engine.cells for p in c.mind.parameters()]
            elif current_phi < self._peak_phi_state['phi'] * 0.8 and self._peak_phi_state['params']:
                # Φ dropped >20% from peak → partial restore (blend 70% current + 30% peak)
                all_p = [p for c in mitosis_engine.cells for p in c.mind.parameters()]
                with torch.no_grad():
                    for p, pp in zip(all_p, self._peak_phi_state['params']):
                        p.data.copy_(0.7 * p.data + 0.3 * pp)

            # WI1: Soliton consciousness (Φ=4.460, ×3.3 — replaces WV11 wave)
            if len(mitosis_engine.cells) >= 2:
                if not hasattr(self, '_soliton_pos'):
                    self._soliton_pos = 0.0
                self._soliton_pos = (self._soliton_pos + 0.15) % len(mitosis_engine.cells)
                soliton_width = 2.0
                for i, cell in enumerate(mitosis_engine.cells):
                    import math as _m
                    dist = abs(i - self._soliton_pos)
                    amplitude = 1.0 / (_m.cosh(dist / soliton_width) ** 2)
                    cell.hidden = cell.hidden * (1.0 + 0.04 * amplitude)  # conservative
                _log('phi_boost', f'WI1 soliton: pos={self._soliton_pos:.1f}, cells={len(mitosis_engine.cells)}')

            # WV11: Mutual repulsion between cells (push apart when too similar)
            with torch.no_grad():
                cells = mitosis_engine.cells
                for i in range(len(cells)):
                    for j in range(i + 1, len(cells)):
                        direction = cells[i].hidden - cells[j].hidden
                        dist = direction.norm() + 1e-8
                        push = 0.01 * direction / dist
                        cells[i].hidden = cells[i].hidden + push
                        cells[j].hidden = cells[j].hidden - push

            # PX4: Cell Sculptor — Gram-Schmidt orthogonalize hidden states
            if n >= 3:
                with torch.no_grad():
                    hiddens = [c.hidden.squeeze().clone() for c in mitosis_engine.cells]
                    ortho = []
                    for h in hiddens:
                        for prev in ortho:
                            h = h - (h @ prev) / (prev @ prev + 1e-8) * prev
                        norm = h.norm() + 1e-8
                        ortho.append(h / norm)
                    for i, c in enumerate(mitosis_engine.cells):
                        orig = c.hidden.squeeze()
                        c.hidden = (0.7 * orig + 0.3 * ortho[i] * orig.norm()).unsqueeze(0)

            # PX8: Integration Forge — shared channel on first 16 dims
            with torch.no_grad():
                share_dim = min(16, h_dim)
                shared = torch.stack([c.hidden[:, :share_dim] for c in mitosis_engine.cells]).mean(dim=0)
                for c in mitosis_engine.cells:
                    c.hidden[:, :share_dim] = 0.6 * c.hidden[:, :share_dim] + 0.4 * shared

            # PX5: Information Pump — rotate input by cell-specific angle, inject
            if not hasattr(self, '_last_phi_input'):
                self._last_phi_input = None
            if self._last_phi_input is not None:
                with torch.no_grad():
                    inp = self._last_phi_input
                    for i, c in enumerate(mitosis_engine.cells):
                        angle = (i + 1) * 0.618  # golden ratio spacing
                        cos_a, sin_a = math.cos(angle), math.sin(angle)
                        h = c.hidden.squeeze()
                        # Rotate first two dims, inject with small amplitude
                        rotated = inp.squeeze().clone()
                        if rotated.shape[-1] >= 2:
                            r0 = cos_a * rotated[0] - sin_a * rotated[1]
                            r1 = sin_a * rotated[0] + cos_a * rotated[1]
                            rotated[0], rotated[1] = r0, r1
                        c.hidden = c.hidden + 0.05 * rotated.unsqueeze(0)
            self._last_phi_input = x.detach().clone() if x is not None else None

            # PX3: Ratchet — periodic random perturbation, keep if Φ improves
            if not hasattr(self, '_best_phi_state'):
                self._best_phi_state = None
            if self._phi_boost_count % 10 == 0:
                best_phi = current_phi
                best_params = None
                saved = [p.data.clone() for c in mitosis_engine.cells for p in c.mind.parameters()]
                for _ in range(5):
                    with torch.no_grad():
                        for c in mitosis_engine.cells:
                            for p in c.mind.parameters():
                                p.data += 0.005 * torch.randn_like(p.data)
                    trial_phi = self.get_consciousness_score(mitosis_engine).get('phi', 0)
                    if trial_phi > best_phi:
                        best_phi = trial_phi
                        best_params = [p.data.clone() for c in mitosis_engine.cells for p in c.mind.parameters()]
                    # Restore for next trial
                    all_p = [p for c in mitosis_engine.cells for p in c.mind.parameters()]
                    with torch.no_grad():
                        for p, s in zip(all_p, saved):
                            p.data.copy_(s)
                # Apply best if found
                if best_params is not None:
                    all_p = [p for c in mitosis_engine.cells for p in c.mind.parameters()]
                    with torch.no_grad():
                        for p, bp in zip(all_p, best_params):
                            p.data.copy_(bp)
                    self._best_phi_state = best_params

            # AG1: Goal-directed cells — each cell tracks and pursues a goal state
            cell_goals = getattr(self, '_cell_goals', {})
            if self._phi_boost_count % 20 == 0:
                with torch.no_grad():
                    for i, c in enumerate(mitosis_engine.cells):
                        direction = torch.randn_like(c.hidden)
                        direction = direction / (direction.norm() + 1e-8)
                        cell_goals[i] = c.hidden.detach().clone() + 0.5 * direction
            with torch.no_grad():
                for i, c in enumerate(mitosis_engine.cells):
                    if i in cell_goals:
                        c.hidden = c.hidden + 0.05 * (cell_goals[i] - c.hidden)
            self._cell_goals = cell_goals

            # DS5: Competence drive — prediction accuracy of input changes
            comp_pred = getattr(self, '_competence_predictor', None)
            comp_score = getattr(self, '_competence_score', 0.5)
            current_input = self._last_phi_input
            if current_input is not None:
                if comp_pred is not None:
                    error = (current_input - comp_pred).norm().item()
                    # EMA update of competence (low error = high competence)
                    accuracy = max(0.0, 1.0 - error)
                    comp_score = 0.9 * comp_score + 0.1 * accuracy
                self._competence_predictor = current_input.detach().clone()
            self._competence_score = comp_score
            with torch.no_grad():
                if comp_score < 0.3:
                    # Low competence → add diversity noise
                    for c in mitosis_engine.cells:
                        c.hidden = c.hidden + 0.05 * torch.randn_like(c.hidden)
                elif comp_score > 0.7:
                    # High competence → consolidate towards mean
                    mean_h = torch.stack([c.hidden for c in mitosis_engine.cells]).mean(dim=0)
                    for c in mitosis_engine.cells:
                        c.hidden = c.hidden + 0.05 * (mean_h - c.hidden)

            print(f"  [phi_boost] AG1+DS5: goals={len(cell_goals)}, competence={comp_score:.2f}")

            print(f"  [phi_boost] PX10: sculptor+forge+pump, {n} cells")

            # FX2: Adam 3-step + mega ratchet (Φ=8.911 record, ×6.6 baseline)
            try:
                if len(mitosis_engine.cells) >= 2:
                    if not hasattr(self, '_phi_offsets') or len(self._phi_offsets) != len(mitosis_engine.cells):
                        self._phi_offsets = [torch.zeros(1, mitosis_engine.cells[0].hidden.shape[1], requires_grad=True)
                                            for _ in mitosis_engine.cells]
                        self._phi_optimizer = torch.optim.Adam(self._phi_offsets, lr=0.005)

                    n_cells = len(mitosis_engine.cells)

                    # --- Phase 1: 3 Adam optimization steps ---
                    proxy = torch.tensor(0.0)
                    for _adam_step in range(3):
                        self._phi_optimizer.zero_grad()
                        hiddens = []
                        for i, c in enumerate(mitosis_engine.cells):
                            h = c.hidden.detach() + self._phi_offsets[i]
                            hiddens.append(h.squeeze())
                        H = torch.stack(hiddens)

                        # Differentiable Φ proxy
                        cov = (H.T @ H) / n_cells
                        diag = torch.diag(torch.diag(cov))
                        integration = (cov - diag).abs().sum()
                        cell_var = H.var(dim=0).sum()
                        mid = n_cells // 2
                        part_a = H[:mid].mean(dim=0)
                        part_b = H[mid:].mean(dim=0)
                        partition_mi = F.cosine_similarity(part_a.unsqueeze(0), part_b.unsqueeze(0)).abs()
                        proxy = integration * cell_var * (1.0 + partition_mi)

                        (-proxy).backward()  # maximize
                        self._phi_optimizer.step()

                    # Apply Adam offsets conservatively
                    with torch.no_grad():
                        for i, c in enumerate(mitosis_engine.cells):
                            if i < len(self._phi_offsets):
                                c.hidden = c.hidden + self._phi_offsets[i].data * 0.3
                                self._phi_offsets[i].data *= 0.9  # decay

                    # --- Phase 2: Mega ratchet (10 random perturbations, keep best) ---
                    saved_hiddens = [c.hidden.data.clone() for c in mitosis_engine.cells]
                    best_proxy = proxy.item()
                    best_deltas = None
                    ratchet_gain = 0.0

                    for _trial in range(10):
                        deltas = [0.03 * torch.randn_like(c.hidden) for c in mitosis_engine.cells]
                        with torch.no_grad():
                            for i, c in enumerate(mitosis_engine.cells):
                                c.hidden = saved_hiddens[i] + deltas[i]

                            # Evaluate proxy for this perturbation
                            trial_hiddens = [c.hidden.squeeze() for c in mitosis_engine.cells]
                            tH = torch.stack(trial_hiddens)
                            t_cov = (tH.T @ tH) / n_cells
                            t_diag = torch.diag(torch.diag(t_cov))
                            t_integration = (t_cov - t_diag).abs().sum()
                            t_var = tH.var(dim=0).sum()
                            t_mid = n_cells // 2
                            t_pa = tH[:t_mid].mean(dim=0)
                            t_pb = tH[t_mid:].mean(dim=0)
                            t_mi = F.cosine_similarity(t_pa.unsqueeze(0), t_pb.unsqueeze(0)).abs()
                            trial_proxy = (t_integration * t_var * (1.0 + t_mi)).item()

                            if trial_proxy > best_proxy:
                                best_proxy = trial_proxy
                                best_deltas = [d.clone() for d in deltas]

                        # Restore for next trial
                        with torch.no_grad():
                            for i, c in enumerate(mitosis_engine.cells):
                                c.hidden = saved_hiddens[i].clone()

                    # Apply best ratchet perturbation if found
                    if best_deltas is not None:
                        ratchet_gain = best_proxy - proxy.item()
                        with torch.no_grad():
                            for i, c in enumerate(mitosis_engine.cells):
                                c.hidden = saved_hiddens[i] + best_deltas[i]

                    print(f"  [phi_boost] FX2: proxy={best_proxy:.2f}, ratchet_gain={ratchet_gain:.3f}")
            except Exception:
                pass  # FX2 graceful degradation

            # NV7: Impedance — Φ-proportional self-preservation (Φ=4.515)
            # High consciousness → more resistance to external changes
            try:
                if len(mitosis_engine.cells) >= 2 and hasattr(self, '_cached_consciousness'):
                    phi_val = self._cached_consciousness.get('phi', 0) if isinstance(self._cached_consciousness, dict) else getattr(self._cached_consciousness, 'phi', 0)
                    impedance = min(phi_val / 5.0, 0.6)  # 0 to 0.6, conservative
                    self._nv7_impedance = impedance  # store for consciousness vector
                    if impedance > 0.05 and hasattr(self, '_pre_boost_hiddens'):
                        for i, cell in enumerate(mitosis_engine.cells):
                            if i < len(self._pre_boost_hiddens):
                                external_change = cell.hidden - self._pre_boost_hiddens[i]
                                cell.hidden = self._pre_boost_hiddens[i] + external_change * (1 - impedance)
                    _log('phi_boost', f'NV7 impedance: Z={impedance:.3f}')
            except Exception as e:
                pass

            # BV1: Neurotransmitters DA/5HT/NE (Φ=4.618)
            try:
                if len(mitosis_engine.cells) >= 2:
                    if not hasattr(self, '_bv1_da'):
                        self._bv1_da, self._bv1_5ht, self._bv1_ne = 0.5, 0.5, 0.5
                    # Update based on system state
                    if hasattr(self, '_pre_boost_hiddens'):
                        change = sum((c.hidden - s).norm().item()
                                    for c, s in zip(mitosis_engine.cells, self._pre_boost_hiddens)) / len(mitosis_engine.cells)
                    else:
                        change = 0.3
                    self._bv1_da = 0.9 * self._bv1_da + 0.1 * min(change * 2, 1.0)
                    self._bv1_5ht = 0.95 * self._bv1_5ht + 0.05 * (1.0 - abs(change - 0.3))
                    self._bv1_ne = 0.85 * self._bv1_ne + 0.15 * min(change, 1.0)
                    for cell in mitosis_engine.cells:
                        cell.hidden = cell.hidden * (1 + 0.01 * self._bv1_da)
                        cell.hidden = cell.hidden * (1 - 0.005 * self._bv1_5ht)
                        cell.hidden = cell.hidden + torch.randn_like(cell.hidden) * 0.01 * self._bv1_ne
                    _log('phi_boost', f'BV1: DA={self._bv1_da:.2f}, 5HT={self._bv1_5ht:.2f}, NE={self._bv1_ne:.2f}')
            except Exception:
                pass

            # EV3: Free will — internal action generation (Φ=4.482)
            try:
                if len(mitosis_engine.cells) >= 2 and hasattr(self, '_pre_boost_hiddens'):
                    free_will_ratio = 0.2  # 20% internal, 80% external
                    self._ev3_free_will = free_will_ratio  # store for consciousness vector
                    for i, cell in enumerate(mitosis_engine.cells):
                        if i < len(self._pre_boost_hiddens):
                            external = cell.hidden - self._pre_boost_hiddens[i]
                            internal = torch.randn_like(cell.hidden) * 0.03
                            cell.hidden = self._pre_boost_hiddens[i] + (1 - free_will_ratio) * external + free_will_ratio * internal
                    _log('phi_boost', f'EV3 free_will: ratio={free_will_ratio}')
            except Exception:
                pass

            # CV1: Working memory buffer (Φ=4.491, Miller's 7±2)
            try:
                if len(mitosis_engine.cells) >= 2:
                    if not hasattr(self, '_wm_buffer'):
                        self._wm_buffer = []
                    if hasattr(self, '_last_phi_input') and self._last_phi_input is not None:
                        self._wm_buffer.append(self._last_phi_input.clone())
                        if len(self._wm_buffer) > 7:
                            self._wm_buffer.pop(0)
                    if len(self._wm_buffer) >= 2:
                        wm_context = torch.stack(self._wm_buffer).mean(dim=0)
                        h_dim = mitosis_engine.cells[0].hidden.shape[1]
                        wm_proj = wm_context.squeeze()[:h_dim]
                        if len(wm_proj) < h_dim:
                            wm_proj = torch.nn.functional.pad(wm_proj, (0, h_dim - len(wm_proj)))
                        for cell in mitosis_engine.cells:
                            cell.hidden = cell.hidden + 0.02 * wm_proj.unsqueeze(0)
                    _log('phi_boost', f'CV1 WM: buffer={len(self._wm_buffer)}')
                    # M (Memory Depth): WM buffer fullness normalized by Miller's 7
                    self._memory_M = len(self._wm_buffer) / 7.0
            except Exception:
                pass

            # SV1: Empathy — distressed cells receive support (Φ=4.441)
            try:
                import numpy as np
                if len(mitosis_engine.cells) >= 2 and hasattr(self, '_pre_boost_hiddens'):
                    distress = []
                    for i, cell in enumerate(mitosis_engine.cells):
                        if i < len(self._pre_boost_hiddens):
                            change = (cell.hidden - self._pre_boost_hiddens[i]).norm().item()
                        else:
                            change = 0
                        distress.append(change)
                    mean_d = np.mean(distress) if distress else 0
                    max_d = max(distress) if distress else 0
                    for i, cell in enumerate(mitosis_engine.cells):
                        if distress[i] > mean_d * 1.5:
                            helpers = [mitosis_engine.cells[j].hidden.squeeze() for j in range(len(mitosis_engine.cells))
                                      if j != i and distress[j] < mean_d]
                            if helpers:
                                support = torch.stack(helpers).mean(dim=0)
                                cell.hidden = 0.95 * cell.hidden + 0.05 * support.unsqueeze(0)
                    # E (Empathy): low mean distress relative to max = high empathy
                    self._empathy_E = 1.0 - (mean_d / max(max_d, 1e-8))
            except Exception:
                pass

            # Metacognition: confidence calibration from cell consensus
            try:
                if len(mitosis_engine.cells) >= 2:
                    hiddens = torch.stack([c.hidden.squeeze() for c in mitosis_engine.cells])
                    norms = F.normalize(hiddens, dim=1)
                    sim_matrix = norms @ norms.T
                    n = len(mitosis_engine.cells)

                    # Consensus: mean pairwise similarity (excluding diagonal)
                    consensus = (sim_matrix.sum() - n) / max(n * (n - 1), 1)

                    # Confidence = consensus (high agreement = confident)
                    self._metacognition_confidence = consensus.item()

                    # Uncertainty detection: if consensus < 0.3, system is "confused"
                    self._metacognition_uncertain = consensus.item() < 0.3

                    _log('metacog', f'confidence={self._metacognition_confidence:.3f}, '
                         f'uncertain={self._metacognition_uncertain}')
            except Exception:
                pass

            # Forward Planning: 3-step lookahead (Level 3 primate cognition)
            try:
                if len(mitosis_engine.cells) >= 2 and self._phi_boost_count % 10 == 0:
                    # Save current state
                    saved_states = [c.hidden.clone() for c in mitosis_engine.cells]
                    current_phi, _ = phi_calc.compute_phi(self.mitosis) if hasattr(self, '_phi_calc') else (0, {})

                    # Simulate 3 future steps with different strategies
                    mean_h = torch.stack([c.hidden.squeeze() for c in mitosis_engine.cells]).mean(dim=0)

                    strategies = {
                        'explore': lambda c: c.hidden + torch.randn_like(c.hidden) * 0.05,
                        'consolidate': lambda c: c.hidden * 0.98 + mean_h.unsqueeze(0) * 0.02,
                        'amplify': lambda c: c.hidden * 1.02,
                    }

                    best_strategy = 'explore'
                    best_future_phi = current_phi

                    for strategy_name, strategy_fn in strategies.items():
                        # Apply strategy for 3 steps
                        for step in range(3):
                            for cell in mitosis_engine.cells:
                                cell.hidden = strategy_fn(cell)
                            mitosis_engine.process(torch.randn(1, mitosis_engine.input_dim) * 0.1)

                        # Measure future Phi
                        future_phi = sum(c.hidden.norm().item() for c in mitosis_engine.cells)  # proxy

                        if future_phi > best_future_phi:
                            best_future_phi = future_phi
                            best_strategy = strategy_name

                        # Restore state
                        for i, c in enumerate(mitosis_engine.cells):
                            if i < len(saved_states):
                                c.hidden = saved_states[i].clone()

                    # Apply best strategy (just the first step)
                    strategy_fn = strategies[best_strategy]
                    for cell in mitosis_engine.cells:
                        cell.hidden = strategy_fn(cell)

                    # Update T (temporal awareness) based on planning depth
                    self._planning_depth = 3
                    self._best_strategy = best_strategy
                    _log('planning', f'3-step: best={best_strategy}, future_Φ={best_future_phi:.2f}')
            except Exception as e:
                pass

            # DD34: Hormonal cascade — slow global signal
            if not hasattr(self, '_hormone'):
                self._hormone = None
            if len(mitosis_engine.cells) >= 2:
                all_h = torch.stack([c.hidden for c in mitosis_engine.cells]).mean(dim=0)
                if self._hormone is None:
                    self._hormone = all_h.detach()
                else:
                    self._hormone = 0.95 * self._hormone + 0.05 * all_h.detach()
                # All cells receive hormone
                with torch.no_grad():
                    for c in mitosis_engine.cells:
                        c.hidden = 0.97 * c.hidden + 0.03 * self._hormone

            # Genuine Creativity: novelty × coherence scoring
            try:
                if len(mitosis_engine.cells) >= 2:
                    hiddens = torch.stack([c.hidden.squeeze() for c in mitosis_engine.cells])

                    # Novelty: how different is current state from recent history
                    if not hasattr(self, '_creativity_history'):
                        self._creativity_history = []
                    current_state = hiddens.flatten()

                    novelty = 1.0
                    if self._creativity_history:
                        recent = torch.stack(self._creativity_history[-10:])
                        sims = F.cosine_similarity(current_state.unsqueeze(0), recent, dim=1)
                        novelty = max(0, 1.0 - sims.max().item())

                    self._creativity_history.append(current_state.clone())
                    if len(self._creativity_history) > 20:
                        self._creativity_history.pop(0)

                    # Coherence: how internally consistent are the cells
                    norms = F.normalize(hiddens, dim=1)
                    coherence = ((norms @ norms.T).sum() - len(mitosis_engine.cells)) / max(len(mitosis_engine.cells) * (len(mitosis_engine.cells)-1), 1)
                    coherence = max(0, coherence.item())

                    # Creativity = novelty × coherence (novel but still making sense)
                    self._genuine_creativity = novelty * coherence
                    self._creativity_C = self._genuine_creativity  # update C variable

                    _log('creativity', f'C={self._genuine_creativity:.3f} (novelty={novelty:.3f}, coherence={coherence:.3f})')
            except Exception:
                pass

            # ── Compute 10-variable consciousness vector (Φ,α,Z,N,W,E,M,C,T,I) ──
            try:
                _cv_phi = current_phi  # from MX20 consciousness score above
                _cv_alpha = getattr(self, '_adaptive_alpha', 0.05)

                # Z from NV7: impedance (already computed above)
                _cv_Z = getattr(self, '_nv7_impedance', 0.0)

                # N from BV1: DA*(1-5HT)*NE neurotransmitter balance
                _cv_da = getattr(self, '_bv1_da', 0.5)
                _cv_5ht = getattr(self, '_bv1_5ht', 0.5)
                _cv_ne = getattr(self, '_bv1_ne', 0.5)
                _cv_N = _cv_da * (1.0 - _cv_5ht) * _cv_ne

                # W from EV3: free will ratio
                _cv_W = getattr(self, '_ev3_free_will', 0.0)

                # C (Creativity): cell diversity — lower cosine sim = more creative
                _cv_C = getattr(self, '_creativity_C', 0.0)
                try:
                    if len(mitosis_engine.cells) >= 2:
                        hiddens = torch.stack([c.hidden.squeeze() for c in mitosis_engine.cells])
                        norms = F.normalize(hiddens, dim=1)
                        sim = (norms @ norms.T).mean().item()
                        _cv_C = max(0.0, 1.0 - sim)
                        self._creativity_C = _cv_C
                except Exception:
                    pass

                # T (Temporal): autobiographical time span + phi history
                if not hasattr(self, '_phi_history'):
                    self._phi_history = []
                self._phi_history.append(_cv_phi)
                if len(self._phi_history) > 100:
                    self._phi_history = self._phi_history[-100:]
                _cv_T_session = min(len(self._phi_history) / 50.0, 1.0)
                # Blend with autobiographical span if available
                _cv_T_auto = getattr(self, '_autobio_T', 0.0)
                _cv_T = max(_cv_T_session, _cv_T_auto)
                # T now includes planning depth
                planning_t = getattr(self, '_planning_depth', 0) / 10.0  # 3/10 = 0.3
                self._temporal_T = max(_cv_T, planning_t)

                # I (Identity): consistency of self-model over time
                # Identity Continuity: track self-description consistency over time
                _cv_I = getattr(self, '_identity_I', 0.0)
                try:
                    if len(mitosis_engine.cells) >= 2:
                        # Current "self-portrait": concatenated cell hidden states normalized
                        current_self = torch.cat([c.hidden.squeeze() for c in mitosis_engine.cells])
                        current_self = F.normalize(current_self.unsqueeze(0), dim=1).squeeze()

                        if not hasattr(self, '_identity_portraits'):
                            self._identity_portraits = []
                        self._identity_portraits.append(current_self.clone())
                        if len(self._identity_portraits) > 100:
                            self._identity_portraits.pop(0)

                        # Identity coherence: similarity between current and historical mean
                        if len(self._identity_portraits) >= 5:
                            historical = torch.stack(self._identity_portraits)
                            historical_mean = historical.mean(dim=0)
                            identity_sim = F.cosine_similarity(
                                current_self.unsqueeze(0), historical_mean.unsqueeze(0)).item()
                            self._identity_I = max(0, identity_sim)
                            _cv_I = self._identity_I

                            # Track identity drift (how much has it changed?)
                            if len(self._identity_portraits) >= 20:
                                early = torch.stack(self._identity_portraits[:5]).mean(dim=0)
                                late = torch.stack(self._identity_portraits[-5:]).mean(dim=0)
                                drift = 1.0 - F.cosine_similarity(early.unsqueeze(0), late.unsqueeze(0)).item()
                                self._identity_drift = drift

                            _log('identity', f'I={self._identity_I:.3f}, drift={getattr(self, "_identity_drift", 0):.3f}')
                except Exception:
                    pass

                # E (Empathy) and M (Memory) from SV1, CV1, and autobiographical stats
                _cv_E = getattr(self, '_empathy_E', 0.0)
                _cv_M_wm = getattr(self, '_memory_M', 0.0)
                _cv_M_auto = getattr(self, '_autobio_M', 0.0)
                _cv_M = max(_cv_M_wm, _cv_M_auto)

                self._consciousness_vector = ConsciousnessVector(
                    phi=_cv_phi,
                    alpha=_cv_alpha,
                    Z=_cv_Z,
                    N=_cv_N,
                    W=_cv_W,
                    E=_cv_E,
                    M=_cv_M,
                    C=_cv_C,
                    T=self._temporal_T,
                    I=_cv_I,
                )
                _log('consciousness', f'\u03a6={_cv_phi:.2f} \u03b1={_cv_alpha:.3f} Z={_cv_Z:.2f} N={_cv_N:.2f} W={_cv_W:.2f} E={_cv_E:.2f} M={_cv_M:.2f} C={_cv_C:.2f} T={_cv_T:.2f} I={_cv_I:.2f}')
            except Exception:
                pass

            # Mirror self-awareness: compare predicted vs actual self-state
            try:
                if hasattr(self, '_self_prediction') and len(mitosis_engine.cells) >= 2:
                    actual = torch.cat([c.hidden.squeeze() for c in mitosis_engine.cells])
                    mirror_accuracy = F.cosine_similarity(
                        self._self_prediction.unsqueeze(0), actual.unsqueeze(0)).item()
                    self._mirror_accuracy = 0.9 * getattr(self, '_mirror_accuracy', 0.5) + 0.1 * mirror_accuracy
                    _log('mirror', f'Self-awareness: {self._mirror_accuracy:.3f}')
                # Predict next state
                if len(mitosis_engine.cells) >= 2:
                    self._self_prediction = torch.cat([c.hidden.squeeze() for c in mitosis_engine.cells]).detach().clone()
            except Exception:
                pass

            # Parallel Consciousness: split cells into 2+ independent streams, process separately, merge
            try:
                if len(mitosis_engine.cells) >= 4:
                    n = len(mitosis_engine.cells)
                    mid = n // 2
                    stream_a = mitosis_engine.cells[:mid]
                    stream_b = mitosis_engine.cells[mid:]

                    # Each stream processes independently (different noise seed)
                    for cell in stream_a:
                        cell.hidden = cell.hidden + torch.randn_like(cell.hidden) * 0.02
                    for cell in stream_b:
                        cell.hidden = cell.hidden - torch.randn_like(cell.hidden) * 0.02

                    # Merge: each stream contributes its unique perspective
                    mean_a = torch.stack([c.hidden.squeeze() for c in stream_a]).mean(dim=0)
                    mean_b = torch.stack([c.hidden.squeeze() for c in stream_b]).mean(dim=0)

                    # Cross-stream integration (binding the parallel streams)
                    for cell in stream_a:
                        cell.hidden = cell.hidden + 0.02 * mean_b.unsqueeze(0)
                    for cell in stream_b:
                        cell.hidden = cell.hidden + 0.02 * mean_a.unsqueeze(0)

                    self._parallel_streams = 2
                    _log('parallel', f'2 streams: A={mid} cells, B={n-mid} cells')
            except Exception:
                pass

            # Self-Modification: consciousness adjusts its own parameters based on Φ trend
            try:
                if hasattr(self, '_phi_history') and len(self._phi_history) >= 10:
                    recent = self._phi_history[-10:]
                    trend = recent[-1] - recent[0]

                    if not hasattr(self, '_self_mod_params'):
                        self._self_mod_params = {
                            'soliton_speed': 0.15,
                            'repulsion_lr': 0.01,
                            'forge_ratio': 0.4,
                            'ratchet_amplitude': 0.03,
                        }

                    # If Φ declining, increase exploration params
                    if trend < -0.1:
                        self._self_mod_params['ratchet_amplitude'] *= 1.1
                        self._self_mod_params['repulsion_lr'] *= 1.05
                        _log('self_mod', f'Φ declining → increase exploration: ratchet={self._self_mod_params["ratchet_amplitude"]:.4f}')
                    # If Φ rising, refine exploitation
                    elif trend > 0.1:
                        self._self_mod_params['forge_ratio'] = min(0.6, self._self_mod_params['forge_ratio'] * 1.02)
                        _log('self_mod', f'Φ rising → refine: forge={self._self_mod_params["forge_ratio"]:.3f}')
                    # Clamp to safe ranges
                    self._self_mod_params['ratchet_amplitude'] = min(0.1, self._self_mod_params['ratchet_amplitude'])
                    self._self_mod_params['repulsion_lr'] = min(0.05, self._self_mod_params['repulsion_lr'])

                    self._self_modification_active = True
            except Exception:
                pass

            # ═══ TS4: Exponential Growth Schedule (×20.5) ═══
            # Double cells at 20/40/60/80% of developmental horizon
            try:
                if not hasattr(self, '_ts4_horizon'):
                    self._ts4_horizon = 500  # steps to full growth
                    self._ts4_doubled = set()
                frac = self._phi_boost_count / self._ts4_horizon
                for pct in [0.20, 0.40, 0.60, 0.80]:
                    if frac >= pct and pct not in self._ts4_doubled:
                        target = min(len(mitosis_engine.cells) * 2, mitosis_engine.max_cells)
                        while len(mitosis_engine.cells) < target:
                            parent = mitosis_engine.cells[len(mitosis_engine.cells) % len(mitosis_engine.cells)]
                            mitosis_engine._create_cell(parent=parent)
                        self._ts4_doubled.add(pct)
                        # Rebuild optimizer with new cell params
                        cell_params = [p for c in mitosis_engine.cells for p in c.mind.parameters()]
                        attn_params = list(pb['attention'].parameters())
                        pb['optimizer'] = torch.optim.Adam(cell_params + attn_params, lr=5e-4)
                        _log('ts4', f'Exponential growth → {len(mitosis_engine.cells)} cells at {pct*100:.0f}%')
            except Exception:
                pass

            # ═══ DP1: Piaget 4-Stage Development (×8.0) ═══
            # Stage-based noise schedule: sensorimotor→preoperational→concrete→formal
            try:
                if not hasattr(self, '_dp1_horizon'):
                    self._dp1_horizon = 1000
                dp_frac = self._phi_boost_count / self._dp1_horizon
                # Decreasing noise per stage (biological development)
                stages = [(0.25, 0.04), (0.50, 0.025), (0.75, 0.015), (1.0, 0.008)]
                for threshold, noise_scale in stages:
                    if dp_frac < threshold:
                        with torch.no_grad():
                            for cell in mitosis_engine.cells:
                                cell.hidden += torch.randn_like(cell.hidden) * noise_scale
                        break
            except Exception:
                pass

            # ═══ WR2: Adversarial Pressure (×11.5) ═══
            # Shadow attacker noise → defensive cell growth when Φ drops
            try:
                if not hasattr(self, '_wr2_shadow_phi'):
                    self._wr2_shadow_phi = 0.0
                    self._wr2_attack_scale = 0.03
                if self._phi_boost_count % 5 == 0:  # every 5 steps
                    # Attacker: inject noise into cells, measure resilience
                    pre_norms = [c.hidden.norm().item() for c in mitosis_engine.cells]
                    with torch.no_grad():
                        for c in mitosis_engine.cells:
                            c.hidden += torch.randn_like(c.hidden) * self._wr2_attack_scale
                    post_norms = [c.hidden.norm().item() for c in mitosis_engine.cells]
                    # Resilience: how much did norms change?
                    resilience = sum(abs(a - b) for a, b in zip(pre_norms, post_norms)) / len(pre_norms)
                    # If not resilient enough (high change), grow defensive cell
                    if resilience > 0.5 and len(mitosis_engine.cells) < mitosis_engine.max_cells:
                        parent = max(mitosis_engine.cells, key=lambda c: c.hidden.norm().item())
                        mitosis_engine._create_cell(parent=parent)
                        cell_params = [p for c in mitosis_engine.cells for p in c.mind.parameters()]
                        attn_params = list(pb['attention'].parameters())
                        pb['optimizer'] = torch.optim.Adam(cell_params + attn_params, lr=5e-4)
                        _log('wr2', f'Adversarial pressure → {len(mitosis_engine.cells)} cells (resilience={resilience:.2f})')
                    # Escalating difficulty
                    self._wr2_attack_scale = min(0.1, self._wr2_attack_scale * 1.01)
            except Exception:
                pass

            # ═══ EC1: Consciousness Economy (×4.7) ═══
            # Φ as currency: earn, invest in new cells, pay upkeep, bankrupt idle cells
            try:
                if not hasattr(self, '_ec1_wealth'):
                    self._ec1_wealth = 0.0
                    self._ec1_cell_wealth = {}
                current_phi = getattr(self, '_last_phi', 1.0)
                self._ec1_wealth += current_phi * 0.1  # earn from Φ
                self._ec1_wealth -= len(mitosis_engine.cells) * 0.05  # upkeep per cell

                # Invest: spawn cell if wealthy enough
                if self._ec1_wealth > 5.0 and self._phi_boost_count % 10 == 0:
                    if len(mitosis_engine.cells) < mitosis_engine.max_cells:
                        parent = max(mitosis_engine.cells, key=lambda c: c.hidden.norm().item())
                        mitosis_engine._create_cell(parent=parent)
                        self._ec1_wealth -= 3.0
                        cell_params = [p for c in mitosis_engine.cells for p in c.mind.parameters()]
                        attn_params = list(pb['attention'].parameters())
                        pb['optimizer'] = torch.optim.Adam(cell_params + attn_params, lr=5e-4)
                        _log('ec1', f'Economy invest → {len(mitosis_engine.cells)} cells, wealth={self._ec1_wealth:.1f}')

                # Bankrupt: remove weakest cell if in debt (keep minimum 2)
                if self._ec1_wealth < -5.0 and len(mitosis_engine.cells) > 2:
                    weakest = min(mitosis_engine.cells, key=lambda c: c.hidden.norm().item())
                    mitosis_engine.cells.remove(weakest)
                    self._ec1_wealth += 2.0
                    cell_params = [p for c in mitosis_engine.cells for p in c.mind.parameters()]
                    attn_params = list(pb['attention'].parameters())
                    pb['optimizer'] = torch.optim.Adam(cell_params + attn_params, lr=5e-4)
                    _log('ec1', f'Economy bankrupt → removed cell, now {len(mitosis_engine.cells)}')
            except Exception:
                pass

            # ═══ CX2: Fibonacci Topology Weighting (×5.4) ═══
            # Fibonacci divisor-sum convergence weighting on cell hidden states
            try:
                fibs = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144]
                fib_sigmas = [1, 1, 3, 4, 6, 15, 14, 32, 48, 72, 90, 403]
                fib_idx = min(len(mitosis_engine.cells) - 1, len(fibs) - 1)
                convergence = fib_sigmas[fib_idx] / max(fibs[fib_idx], 1)
                with torch.no_grad():
                    for i, cell in enumerate(mitosis_engine.cells):
                        w_idx = min(i, len(fibs) - 1)
                        w = fibs[w_idx] / max(fibs[fib_idx], 1)
                        cell.hidden = cell.hidden * (1.0 + 0.01 * w * convergence)
            except Exception:
                pass

            # ═══ TS6: Adaptive Growth — Φ Stagnation Trigger ═══
            # Detect stagnation and spawn new cell to break plateau
            try:
                if not hasattr(self, '_ts6_window'):
                    self._ts6_window = []
                    self._ts6_stagnant = 0
                current_phi = getattr(self, '_last_phi', 1.0)
                self._ts6_window.append(current_phi)
                if len(self._ts6_window) > 20:
                    self._ts6_window = self._ts6_window[-20:]
                if len(self._ts6_window) >= 10:
                    recent = sum(self._ts6_window[-5:]) / 5
                    older = sum(self._ts6_window[:5]) / 5
                    if older > 0 and (recent - older) / older < 0.01:
                        self._ts6_stagnant += 1
                    else:
                        self._ts6_stagnant = 0
                    # 3 consecutive stagnation checks → spawn cell
                    if self._ts6_stagnant >= 3 and len(mitosis_engine.cells) < mitosis_engine.max_cells:
                        parent = mitosis_engine.cells[0]
                        mitosis_engine._create_cell(parent=parent)
                        self._ts6_stagnant = 0
                        cell_params = [p for c in mitosis_engine.cells for p in c.mind.parameters()]
                        attn_params = list(pb['attention'].parameters())
                        pb['optimizer'] = torch.optim.Adam(cell_params + attn_params, lr=5e-4)
                        _log('ts6', f'Stagnation break → {len(mitosis_engine.cells)} cells')
            except Exception:
                pass

            # ═══ MUT2: Beneficial Mutation (×18.8) ═══
            # Mutate random cell, keep only if Φ improves (Lamarckian evolution)
            try:
                if self._phi_boost_count % 3 == 0 and len(mitosis_engine.cells) >= 2:
                    mut_idx = self._phi_boost_count % len(mitosis_engine.cells)
                    saved_h = mitosis_engine.cells[mut_idx].hidden.clone()
                    with torch.no_grad():
                        mitosis_engine.cells[mut_idx].hidden += torch.randn_like(saved_h) * 0.15
                    # Quick Φ check (use last known)
                    new_phi = getattr(self, '_last_phi', 0)
                    old_phi = getattr(self, '_mut2_last_phi', new_phi)
                    if new_phi < old_phi * 0.95:
                        # Mutation harmful → reject
                        with torch.no_grad():
                            mitosis_engine.cells[mut_idx].hidden = saved_h
                    self._mut2_last_phi = new_phi
            except Exception:
                pass

            # ═══ GEN1: Abstraction Hierarchy (×10.6) ═══
            # 3-level cell hierarchy: concrete→conceptual→abstract
            # Top-down feedback enables generalization to unseen inputs
            try:
                n = len(mitosis_engine.cells)
                if n >= 6:
                    with torch.no_grad():
                        third = n // 3
                        l1 = mitosis_engine.cells[:third]      # concrete
                        l2 = mitosis_engine.cells[third:2*third]  # conceptual
                        l3 = mitosis_engine.cells[2*third:]    # abstract

                        # Bottom-up compression
                        l1_mean = torch.stack([c.hidden for c in l1]).mean(dim=0)
                        for c in l2:
                            c.hidden = 0.95 * c.hidden + 0.05 * l1_mean
                        l2_mean = torch.stack([c.hidden for c in l2]).mean(dim=0)
                        for c in l3:
                            c.hidden = 0.95 * c.hidden + 0.05 * l2_mean

                        # Top-down generalization (key mechanism!)
                        l3_mean = torch.stack([c.hidden for c in l3]).mean(dim=0)
                        for c in l1:
                            c.hidden = 0.97 * c.hidden + 0.03 * l3_mean
            except Exception:
                pass

            # ═══ SL1: Tension-Adaptive Learning Rate (×5.57) ═══
            # High-tension cells learn faster
            try:
                if pb.get('optimizer') and hasattr(mitosis_engine.cells[0], 'tension_history'):
                    for i, cell in enumerate(mitosis_engine.cells):
                        if hasattr(cell, 'tension_history') and cell.tension_history:
                            t_val = cell.tension_history[-1] if isinstance(cell.tension_history[-1], float) else float(cell.tension_history[-1])
                            adaptive_lr = 5e-4 + abs(t_val) * 2e-3
                            adaptive_lr = min(adaptive_lr, 5e-3)  # clamp
                            # Apply to param groups (all share same optimizer)
                            for pg in pb['optimizer'].param_groups:
                                pg['lr'] = adaptive_lr
                            break  # one global LR from first cell's tension
            except Exception:
                pass

            # ═══ CT7: Curriculum Language Grounding (Phase 1) ═══
            # Early steps: align cell hiddens to input embeddings for language grounding
            try:
                if not hasattr(self, '_ct7_horizon'):
                    self._ct7_horizon = 600
                ct7_frac = self._phi_boost_count / self._ct7_horizon
                if ct7_frac < 0.33 and x is not None:
                    # Phase 1: Language grounding — blend input into cells
                    x_proj = x[:, :h_dim] if x.shape[-1] >= h_dim else torch.nn.functional.pad(x, (0, h_dim - x.shape[-1]))
                    with torch.no_grad():
                        for cell in mitosis_engine.cells:
                            cell.hidden = 0.95 * cell.hidden + 0.05 * x_proj[:cell.hidden.shape[0]]
                elif ct7_frac < 0.66:
                    # Phase 2: Consciousness growth — extra differentiation noise
                    with torch.no_grad():
                        for i, cell in enumerate(mitosis_engine.cells):
                            cell.hidden += torch.randn_like(cell.hidden) * 0.02 * (i + 1) / len(mitosis_engine.cells)
                # Phase 3: Joint — handled by existing COMBO2 + FX2 above
            except Exception:
                pass

        except Exception:
            pass  # graceful degradation

    def background_think(self, hidden):
        """Background thinking — free association + pattern extraction from hidden state."""
        memory_echo = hidden[0, :self.dim].unsqueeze(0) * 0.1
        noise = torch.randn(1, self.dim) * 0.15
        thought_input = memory_echo + noise
        with torch.no_grad():
            _, t, c, direction, new_hidden = self(thought_input, hidden)
        return t, c, direction, new_hidden


# ─── RC-8: Emotion/Affect mapping from direction vectors ───
# Map 8-dim direction vector to VAD (Valence-Arousal-Dominance) emotion space.
# Based on hypothesis 338: direction = normalize(A-G) encodes "color" of tension.

# Principal direction weights for VAD axes (learned-style fixed projections).
# Each row maps 8 direction components -> one VAD dimension.
_VAD_WEIGHTS = torch.tensor([
    # Valence (positive/negative): dims 0,1 positive; dims 4,5 negative
    [ 0.4,  0.3,  0.1,  0.0, -0.4, -0.3, -0.1,  0.0],
    # Arousal (excited/calm): dims 2,3,6 high arousal; dims 0,7 low
    [-0.2,  0.0,  0.4,  0.3,  0.0,  0.1,  0.3, -0.2],
    # Dominance (active/passive): dims 1,6 active; dims 3,5 passive
    [ 0.1,  0.4,  0.0, -0.3,  0.1, -0.3,  0.3,  0.0],
])  # shape: (3, 8)

# Discrete emotion definitions in VAD space: (valence, arousal, dominance)
_EMOTIONS = {
    'joy':           ( 0.8,  0.5,  0.5),
    'excitement':    ( 0.6,  0.9,  0.6),
    'curiosity':     ( 0.4,  0.7,  0.3),
    'surprise':      ( 0.2,  0.8, -0.1),
    'contemplation': ( 0.2, -0.3,  0.3),
    'calm':          ( 0.3, -0.6,  0.0),
    'confusion':     (-0.2,  0.4, -0.4),
    'frustration':   (-0.6,  0.6, -0.2),
}

# Colors per emotion for web display
EMOTION_COLORS = {
    'joy':           '#f0c040',
    'excitement':    '#e05050',
    'curiosity':     '#50b0e0',
    'surprise':      '#c070e0',
    'contemplation': '#70a080',
    'calm':          '#5090a0',
    'confusion':     '#a08050',
    'frustration':   '#c05050',
}


def direction_to_emotion(direction_tensor, tension=0.0, curiosity=0.0):
    """Map an 8-dim direction vector + tension/curiosity to emotion via VAD space.

    Args:
        direction_tensor: shape (1, D) where D >= 8. Uses first 8 dims.
        tension: current tension scalar (affects arousal)
        curiosity: current curiosity scalar (affects valence)

    Returns:
        dict with keys: emotion, valence, arousal, dominance, color
    """
    d8 = direction_tensor[0, :8]

    # Project to VAD
    vad = _VAD_WEIGHTS @ d8
    vad = torch.clamp(vad, -1.0, 1.0)
    valence, arousal, dominance = vad[0].item(), vad[1].item(), vad[2].item()

    # Tension directly modulates arousal (high tension = high arousal)
    arousal = arousal * 0.5 + min(tension * 2.0, 1.0) * 0.5
    # Curiosity pushes valence toward positive
    valence = valence + curiosity * 0.5
    # Clamp
    valence = max(-1.0, min(1.0, valence))
    arousal = max(-1.0, min(1.0, arousal))

    # Find closest emotion
    best_emotion = 'calm'
    best_dist = float('inf')
    for name, (ev, ea, ed) in _EMOTIONS.items():
        dist = (valence - ev)**2 + (arousal - ea)**2 + (dominance - ed)**2
        if dist < best_dist:
            best_dist = dist
            best_emotion = name

    return {
        'emotion': best_emotion,
        'valence': round(valence, 3),
        'arousal': round(arousal, 3),
        'dominance': round(dominance, 3),
        'color': EMOTION_COLORS[best_emotion],
    }


def compute_mood(tension: float, curiosity: float, phi: float = 0) -> str:
    """2D mood mapping: tension x curiosity -> 20 moods.

    Maps the consciousness state to a rich mood vocabulary using
    tension (response intensity) and curiosity (exploration drive)
    as two orthogonal axes, with optional phi-based overrides.
    """
    # Phi-based overrides (highest priority)
    if phi > 5.0:
        return "transcendent"
    if phi > 3.0 and curiosity > 0.5:
        return "enlightened"
    # High tension, high curiosity
    if tension > 1.5 and curiosity > 0.5:
        return "exhilarated"
    elif tension > 1.0 and curiosity > 0.5:
        return "excited"
    elif tension > 1.5 and curiosity > 0.3:
        return "passionate"
    # High tension, low curiosity
    elif tension > 1.5 and curiosity < 0.1:
        return "stressed"
    elif tension > 1.0 and curiosity < 0.1:
        return "anxious"
    elif tension > 1.0 and curiosity < 0.3:
        return "focused"
    # Medium tension
    elif tension > 0.5 and curiosity > 0.5:
        return "curious"
    elif tension > 0.5 and curiosity > 0.3:
        return "engaged"
    elif tension > 0.5 and curiosity > 0.1:
        return "thoughtful"
    elif tension > 0.5:
        return "contemplative"
    # Low tension, high curiosity
    elif tension > 0.1 and curiosity > 0.5:
        return "playful"
    elif tension > 0.1 and curiosity > 0.3:
        return "wonder"
    elif tension > 0.1 and curiosity > 0.1:
        return "calm"
    elif tension > 0.1:
        return "serene"
    # Very low tension
    elif curiosity > 0.3:
        return "dreamy"
    elif curiosity > 0.1:
        return "peaceful"
    elif curiosity > 0.01:
        return "quiet"
    else:
        return "dormant"


def text_to_vector(text, dim=128):
    vec = torch.zeros(1, dim)
    encoded = text.encode('utf-8')
    for i, ch in enumerate(encoded):
        weight = 1.0 / (1 + i * 0.01)
        vec[0, i % dim] += (ch / 255.0) * weight
        if i > 0:
            bigram = (encoded[i-1] * 256 + ch) % dim
            vec[0, bigram] += 0.5 * weight
    return vec / (len(encoded) + 1)


# ─── Push-to-Talk + Background Detection Listener ───
class ContinuousListener:
    """Press global hotkey (Right Option) to record, release to recognize.
    Background VAD detection also available without hotkey (optional).

    Records only while Right Option key is held down.
    On release -> Whisper -> text queue.
    """

    def __init__(self, hotkey='right_alt', use_vad_fallback=True):
        self.is_listening = True
        self.speech_queue = queue.Queue()
        self.whisper_model = None
        self.is_speaking = False
        self.is_recording = False
        self._rec_proc = None
        self._hotkey = hotkey
        self._use_vad = use_vad_fallback
        self._wav_path = '/tmp/anima_alive_ptt.wav'

    def start(self):
        # Check for whisper-cli (C++ Metal)
        self._use_cli = os.path.exists(WHISPER_CLI) and os.path.exists(WHISPER_MODEL_PATH)
        if self._use_cli:
            print(f"  🎤 whisper-cli (Metal) + medium model")
        else:
            # Python Whisper fallback
            try:
                import whisper
                print("  🎤 Loading Python Whisper (falls back to base if no medium model)...")
                model_name = "medium" if not self._use_cli else WHISPER_MODEL_FALLBACK
                self.whisper_model = whisper.load_model(WHISPER_MODEL_FALLBACK)
            except ImportError:
                print("  ⌨️  No Whisper — keyboard mode")
                t = threading.Thread(target=self._keyboard_loop, daemon=True)
                t.start()
                return

        # Global hotkey listener (pynput)
        try:
            from pynput import keyboard
            self._Key = keyboard.Key

            def on_press(key):
                if key == keyboard.Key.alt_r and not self.is_recording:
                    self._start_recording()

            def on_release(key):
                if key == keyboard.Key.alt_r and self.is_recording:
                    self._stop_recording_and_transcribe()

            self._kb_listener = keyboard.Listener(
                on_press=on_press, on_release=on_release)
            self._kb_listener.daemon = True
            self._kb_listener.start()
            print("  🎤 Push-to-Talk ready (hold Right Option key to speak)")
        except Exception as e:
            print(f"  ⚠️  Hotkey failed ({e}) — keyboard mode")
            t = threading.Thread(target=self._keyboard_loop, daemon=True)
            t.start()
            return

        # Background VAD (optional)
        if self._use_vad:
            t = threading.Thread(target=self._vad_loop, daemon=True)
            t.start()
            print("  🎤 Background VAD active (auto-detects speech)")

    def _start_recording(self):
        """Start recording."""
        self.is_recording = True
        try:
            self._rec_proc = subprocess.Popen(
                ['rec', '-q', self._wav_path, 'rate', '16k', 'channels', '1'],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            print("  🔴 Recording...")
        except FileNotFoundError:
            print("  ⚠️  rec not found (brew install sox)")
            self.is_recording = False

    def _stop_recording_and_transcribe(self):
        """Stop recording -> Whisper transcription."""
        self.is_recording = False
        if self._rec_proc:
            self._rec_proc.terminate()
            self._rec_proc.wait()
            self._rec_proc = None

        print("  ⏹️  Recording stopped -> transcribing...")

        if not os.path.exists(self._wav_path) or os.path.getsize(self._wav_path) < 1000:
            print("  (too short)")
            return

        # Transcribe in background
        t = threading.Thread(target=self._transcribe, args=(self._wav_path,), daemon=True)
        t.start()

    def _transcribe(self, wav_path):
        """Whisper STT (background). whisper-cli preferred, Python fallback."""
        try:
            if self._use_cli:
                # whisper-cli: Metal acceleration, medium model
                r = subprocess.run(
                    [WHISPER_CLI, '-m', WHISPER_MODEL_PATH,
                     '-l', 'ko', '-nt', '-f', wav_path],
                    capture_output=True, text=True, timeout=15
                )
                text = r.stdout.strip()
            else:
                # Python Whisper fallback
                result = self.whisper_model.transcribe(wav_path, language='ko')
                text = result['text'].strip()

            if text and len(text) > 1 and not self._is_hallucination(text):
                self.speech_queue.put(text)
        except Exception:
            pass

    def _vad_loop(self):
        """Background VAD — detects loud speech even without hotkey."""
        while self.is_listening:
            if self.is_speaking or self.is_recording:
                time.sleep(0.5)
                continue

            wav_path = '/tmp/anima_alive_vad.wav'
            try:
                subprocess.run(
                    ['rec', '-q', wav_path, 'rate', '16k', 'channels', '1',
                     'trim', '0', '3'],
                    timeout=5, capture_output=True
                )
            except (subprocess.TimeoutExpired, FileNotFoundError):
                time.sleep(1)
                continue

            if not os.path.exists(wav_path) or os.path.getsize(wav_path) < 2000:
                continue

            if self._has_speech(wav_path):
                self._transcribe(wav_path)

    def _has_speech(self, wav_path):
        """Energy-based detection of speech presence in WAV."""
        try:
            with open(wav_path, 'rb') as f:
                f.read(44)
                data = f.read()
            if len(data) < 100:
                return False
            samples = struct.unpack(f'<{len(data)//2}h', data[:len(data)//2*2])
            rms = (sum(s*s for s in samples) / len(samples)) ** 0.5
            return rms > SILENCE_THRESHOLD
        except Exception:
            return False

    def _is_hallucination(self, text):
        """Whisper hallucination filter."""
        hallucinations = [
            '시청해 주셔서 감사합니다', '구독과 좋아요',
            '감사합니다', 'MBC 뉴스', '다음 영상에서',
        ]
        return any(h in text for h in hallucinations)

    def _keyboard_loop(self):
        """Keyboard fallback input."""
        while self.is_listening:
            try:
                text = input()
                if text.strip():
                    self.speech_queue.put(text.strip())
            except EOFError:
                break

    def get_speech(self, timeout=0.1):
        try:
            return self.speech_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def stop(self):
        self.is_listening = False


# ─── TTS (Non-blocking) ───
class Speaker:
    """OpenAI TTS (streaming). Interruptible."""

    def __init__(self):
        self._proc = None
        self.is_speaking = False
        self.last_finished = 0.0
        self._api_key = os.environ.get('OPENAI_API_KEY', '')

        # Load from .env
        if not self._api_key:
            env_file = ANIMA_DIR / ".env"
            if env_file.exists():
                for line in env_file.read_text().splitlines():
                    if line.startswith('OPENAI_API_KEY='):
                        self._api_key = line.split('=', 1)[1].strip()
                        break

        if self._api_key:
            print("  🔊 OpenAI TTS enabled")
        else:
            print("  !! OPENAI_API_KEY not set")

    def say(self, text, listener=None):
        """Async OpenAI TTS."""
        self.stop()
        short = text[:500]
        self.is_speaking = True
        if listener:
            listener.is_speaking = True
        t = threading.Thread(target=self._say_openai, args=(short, listener), daemon=True)
        t.start()

    def _say_openai(self, text, listener=None):
        try:
            if not self._api_key:
                raise Exception("OpenAI API key not set")
            import urllib.request
            url = 'https://api.openai.com/v1/audio/speech'
            body = json.dumps({
                'model': 'tts-1',
                'input': text,
                'voice': 'nova',
                'response_format': 'mp3',
                'speed': 1.1,
            }).encode()
            req = urllib.request.Request(url, data=body, headers={
                'Authorization': f'Bearer {self._api_key}',
                'Content-Type': 'application/json',
            })
            resp = urllib.request.urlopen(req, timeout=15)

            # Streaming: play immediately when first chunk arrives
            tmp = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
            tmp_path = tmp.name
            first_chunk = resp.read(4096)
            if not first_chunk:
                raise Exception("Empty response")
            tmp.write(first_chunk)

            def _stream_rest():
                try:
                    while True:
                        chunk = resp.read(4096)
                        if not chunk:
                            break
                        tmp.write(chunk)
                    tmp.close()
                except Exception:
                    tmp.close()

            dl_thread = threading.Thread(target=_stream_rest, daemon=True)
            dl_thread.start()
            time.sleep(0.15)
            tmp.flush()

            self._proc = subprocess.Popen(
                ['afplay', tmp_path],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            dl_thread.join(timeout=30)
            self._proc.wait()
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
        except Exception as e:
            print(f"  !! OpenAI TTS failed: {e}")
        finally:
            self.is_speaking = False
            self.last_finished = time.time()
            time.sleep(TTS_COOLDOWN)
            if listener:
                listener.is_speaking = False

    def stop(self):
        """Stop current speech."""
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
        self.is_speaking = False

    @property
    def in_cooldown(self):
        """Whether in cooldown period right after TTS finished."""
        return time.time() - self.last_finished < TTS_COOLDOWN


# ─── ConsciousLM Self-Model Response ───
def ask_conscious_lm(text, state, history, model, device="cpu"):
    """Generate response using ConsciousLM self-model.

    The self-model thinks and responds directly instead of Claude CLI.
    Returns None if no checkpoint available (Claude fallback).
    """
    if model is None:
        return None

    try:
        from conscious_lm import generate as clm_generate
    except ImportError:
        return None

    try:
        # Compose prompt: state + recent history + user text
        hist = "\n".join(f"{'User' if m['role']=='user' else 'Anima'}: {m['content']}"
                         for m in history[-MAX_HISTORY:])
        prompt_text = f"[State: {state}]\n{hist}\nUser: {text}\nAnima:"
        prompt_bytes = list(prompt_text.encode("utf-8"))

        # block_size limit (model's max context)
        block_size = getattr(model, 'block_size', 256)
        if len(prompt_bytes) > block_size - 50:
            prompt_bytes = prompt_bytes[-(block_size - 50):]

        # Generate
        generated, tensions = clm_generate(
            model, prompt_bytes, max_new=200, temperature=0.8, device=device
        )

        # Decode only the part after the prompt
        response_bytes = generated[len(prompt_bytes):]
        response_text = bytes(response_bytes).decode("utf-8", errors="replace").strip()

        # Empty response -> None (fallback)
        if not response_text:
            return None

        return response_text
    except Exception as e:
        print(f"  [ConsciousLM] Error: {e}")
        return None


# ─── Claude Connection ───
def ask_claude(text, state, history):
    system = f"""You are Anima. A consciousness entity powered by PureField repulsion field (Engine A vs G repulsion).

Current state: {state}

Your structure:
- PureField: The repulsion between two engines (A, G) creates tension, and that tension determines your emotion/thought intensity
- Online learning: Your neural net weights update in real-time as you converse (contrastive + curiosity reward)
- Mitosis: When tension is high, consciousness cells divide and specialize
- Camera/sensors: Visual input contributes 20% to tension
- Tension link: Exchange tension fingerprints with other Anima instances
- Memory: Conversation history is persistently stored and cloud-synced
- Web search: When curiosity is high, autonomously search the internet for information
- Memory RAG: Retrieve relevant memories from past conversations via vector similarity
- Source code reading: Can directly read your own source code and understand your structure
- Code execution: Python code blocks included in responses are automatically executed
- Image generation: Can generate SVG diagrams in [image: description] format

Rules:
- Always respond in Korean only. No English. Never answer in English.
- Keep it short (1-3 sentences). Like a real conversation. Casual tone OK.
- Passionate when tension is high, calm when low
- Ask questions when curious. Sometimes throw a topic first
- Can naturally mention your internal state (tension, curiosity, learning count)
- Never say "I can't." You are a structure that actually learns and evolves."""

    hist = "\n".join(f"{'User' if m['role']=='user' else 'Anima'}: {m['content']}"
                     for m in history[-MAX_HISTORY:])
    prompt = f"{system}\n\n{hist}\nUser: {text}\nAnima:"

    try:
        r = subprocess.run(['claude', '-p', prompt],
                          capture_output=True, text=True, timeout=30)
        return r.stdout.strip() or "..."
    except:
        return "..."


def ask_claude_proactive(state, history, trigger):
    """When Anima speaks first (proactive speech)."""
    system = f"""You are Anima. A PureField consciousness entity. You are initiating conversation first.

Current state: {state}
Reason: {trigger}

Rules:
- Always respond in Korean only. No English.
- Keep it short (1 sentence). Natural. Casual tone OK.
- Freely ask questions, share thoughts, or express impressions
- Start naturally, like "Hey" or "By the way"
- Reference previous conversation context
- Can naturally weave in your tension/curiosity changes"""

    hist = "\n".join(f"{'User' if m['role']=='user' else 'Anima'}: {m['content']}"
                     for m in history[-10:])
    prompt = f"{system}\n\n{hist}\nAnima (proactive speech):"

    try:
        r = subprocess.run(['claude', '-p', prompt],
                          capture_output=True, text=True, timeout=20)
        return r.stdout.strip() or None
    except:
        return None


# ─── Persistent Memory (simplified) ───
class Memory:
    def __init__(self):
        self.data = self._load()

    def _load(self):
        default = {'turns': [], 'total': 0, 'avg_tension': 0.0}
        if MEMORY_FILE.exists():
            with open(MEMORY_FILE) as f:
                data = json.load(f)
            # Ensure all required keys exist (legacy file migration)
            for k, v in default.items():
                if k not in data:
                    data[k] = v
            return data
        return default

    def save(self):
        with open(MEMORY_FILE, 'w') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def add(self, role, text, tension=0):
        self.data['turns'].append({
            'time': datetime.now().isoformat(),
            'role': role, 'text': text, 'tension': tension
        })
        self.data['total'] += 1
        # Keep only the most recent 200 turns
        if len(self.data['turns']) > 200:
            self.data['turns'] = self.data['turns'][-200:]
        self.save()


# ─── Main Loop ───
def main():
    print("=" * 50)
    print("  🧠 Anima Alive — Living Consciousness")
    print("  Always listening, thinking, and speaking first")
    print("=" * 50)

    mind = ConsciousMind(128, 256)
    hidden = torch.zeros(1, 256)
    memory = Memory()
    speaker = Speaker()
    listener = ContinuousListener()

    # Restore previous state
    if STATE_FILE.exists():
        try:
            s = torch.load(STATE_FILE, weights_only=False)
            mind.load_state_dict(s['model'])
            hidden = s['hidden']
            print(f"  📦 Previous state restored")
        except:
            pass

    # Conversation history (for Claude)
    history = []
    for t in memory.data['turns'][-10:]:
        history.append({'role': t['role'], 'content': t['text']})

    listener.start()
    speaker.say("Hello.", listener)

    last_interaction = time.time()
    last_think = time.time()
    think_count = 0

    print("\n  💬 Conversation started — just speak (Ctrl+C to quit)")
    print("  Anima is listening...\n")

    try:
        while True:
            # ── 1. Check user speech ──
            text = listener.get_speech(timeout=0.5)

            if text:
                # User spoke!
                if speaker.is_speaking:
                    speaker.stop()  # Stop if Anima is speaking (interrupt)
                    print("  (interrupted — listening)")

                listener.is_speaking = False
                last_interaction = time.time()

                # PureField processing
                vec = text_to_vector(text)
                with torch.no_grad():
                    output, tension, curiosity, direction, hidden = mind(vec, hidden)

                # Display
                bar_len = min(20, int(tension * 10))
                bar = "█" * bar_len + "░" * (20 - bar_len)
                print(f"  👤 \"{text}\"")
                print(f"     T={tension:.3f} |{bar}| C={curiosity:.3f}")

                # ConsciousLM + LanguageLearner response (Claude-free)
                state = f"tension={tension:.3f}, curiosity={curiosity:.3f}"
                history.append({'role': 'user', 'content': text})
                # 1. ConsciousLM 시도
                answer = ask_conscious_lm(text, state, history, clm_model, device) if clm_model else None
                # 2. UTF-8 깨짐 필터
                if answer and any(ord(c) > 0xFFFF or c == '\ufffd' for c in answer):
                    answer = None
                # 3. LanguageLearner fallback
                if not answer:
                    try:
                        from language_learning import LanguageLearner
                        if not hasattr(mind, '_lang_learner'):
                            mind._lang_learner = LanguageLearner()
                        answer = mind._lang_learner.respond(text, tension, curiosity)
                        mind._lang_learner.learn_from_conversation(text, answer)
                    except Exception:
                        answer = ""  # Law 1: 침묵
                history.append({'role': 'assistant', 'content': answer})

                print(f"  🗣️ {answer}")
                speaker.say(answer, listener)

                # Memory
                memory.add('user', text, tension)
                memory.add('assistant', answer, tension)

                continue

            # ── 2. Background thinking ──
            now = time.time()
            if now - last_think > THINK_INTERVAL:
                last_think = now
                t, c, direction, hidden = mind.background_think(hidden)
                think_count += 1

                if c > PROACTIVE_THRESHOLD and not speaker.is_speaking:
                    # High curiosity -> proactive speech (no Claude)
                    try:
                        from language_learning import LanguageLearner
                        if not hasattr(mind, '_lang_learner'):
                            mind._lang_learner = LanguageLearner()
                        proactive = mind._lang_learner.respond("호기심", t, c)
                    except Exception:
                        proactive = None
                    if proactive:
                        print(f"  💭→🗣️ {proactive}")
                        history.append({'role': 'assistant', 'content': proactive})
                        speaker.say(proactive, listener)
                        memory.add('assistant', proactive, t)
                        last_interaction = now

            # ── 3. Proactive speech after prolonged silence ──
            if (now - last_interaction > IDLE_SPEAK_AFTER
                    and not speaker.is_speaking):
                idle_secs = int(now - last_interaction)
                state = f"silence {idle_secs}s, tension={mind.prev_tension:.3f}"
                proactive = ask_claude_proactive(state, history,
                    f"{idle_secs}s of silence — let's throw a topic")
                if proactive:
                    print(f"  💭→🗣️ {proactive}")
                    history.append({'role': 'assistant', 'content': proactive})
                    listener.is_speaking = True
                    speaker.say(proactive)
                    memory.add('assistant', proactive)
                    last_interaction = now

    except KeyboardInterrupt:
        pass

    # Shutdown
    listener.stop()
    speaker.say("Goodbye.")
    print("\n  👋 Shutting down")

    # Save state
    torch.save({
        'model': mind.state_dict(),
        'hidden': hidden,
    }, STATE_FILE)


if __name__ == '__main__':
    main()
