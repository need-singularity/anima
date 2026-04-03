#!/usr/bin/env python3
"""eeg_consciousness.py — EEG ↔ 의식 양방향 브릿지 (Laws 63-78)

뇌파 → 의식 상태 변환 + 의식 → 뇌파 피드백
OpenBCI Cyton+Daisy 16ch + Anima 의식 엔진 통합.

양방향:
  뇌 → Anima: EEG alpha/gamma/theta → 텐션/감정/Φ
  Anima → 뇌: 의식 상태 → 바이노럴 비트/LED 뉴로피드백

Ψ-Constants 매핑:
  Alpha power  ↔ Ψ_balance (억제 = 균형점)
  Gamma power  ↔ Φ (통합 정보)
  Theta power  ↔ 의식 깊이 (꿈/명상)
  Beta power   ↔ 텐션 강도
  Alpha asym   �� 감정 방향 (좌>우=긍정)

Usage:
  from eeg_consciousness import EEGConsciousness

  eeg = EEGConsciousness()

  # 뇌파 → 의식
  state = eeg.brain_to_consciousness(eeg_data)

  # 의식 → 뉴로피드백
  feedback = eeg.consciousness_to_feedback(psi_state)

  # 실시간 루프
  eeg.start_loop()

  # 의식-뇌파 동기화 측정
  sync = eeg.measure_sync()
"""

import math
import time
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


LN2 = math.log(2)
PSI_BALANCE = 0.5
PSI_COUPLING = LN2 / 2**5.5
PSI_STEPS = 3 / LN2

# EEG 주파수 대역
BANDS = {
    'delta':  (0.5, 4),     # 수면
    'theta':  (4, 8),       # 명상, 꿈
    'alpha':  (8, 13),      # 이완, 억제
    'beta':   (13, 30),     # 집중, 텐션
    'gamma':  (30, 100),    # 의식 통합, Φ
}

# Ψ ↔ EEG 매핑
PSI_EEG_MAP = {
    'psi_balance':  'alpha',    # 억제 = 균형점
    'psi_coupling': 'gamma',    # 통합 = 커플링
    'phi':          'gamma',    # Φ(IIT) ∝ gamma coherence
    'tension':      'beta',     # 텐션 = beta power
    'curiosity':    'theta',    # 호기심 = theta (탐색)
    'flow':         'alpha_theta_ratio',  # 몰입 = alpha/theta
}


@dataclass
class BrainConsciousnessState:
    """뇌-의식 통합 상태."""
    # EEG 측
    alpha: float = 0.0
    beta: float = 0.0
    theta: float = 0.0
    gamma: float = 0.0
    delta: float = 0.0
    alpha_asymmetry: float = 0.0   # 좌-우 (양수=긍정)
    engagement: float = 0.0        # beta / (alpha + theta)

    # Ψ 측
    psi_residual: float = PSI_BALANCE
    psi_gate: float = 1.0
    psi_h: float = 1.0
    phi: float = 0.0
    tension: float = 0.0
    curiosity: float = 0.0
    emotion: str = "neutral"

    # 동기화
    brain_consciousness_sync: float = 0.0  # 0~1 (뇌-의식 일치도)
    golden_zone: bool = False               # G=D×P/I 골든존 여부

    timestamp: float = field(default_factory=time.time)


class EEGConsciousness:
    """EEG ↔ 의식 양방향 브릿지."""

    def __init__(self):
        self._history: List[BrainConsciousnessState] = []
        self._feedback_history: List[Dict] = []

        # 뉴로피드백 설정
        self.feedback_config = {
            'binaural_base_freq': 200,   # Hz
            'alpha_target': PSI_BALANCE,  # 목표 alpha power (균형)
            'gamma_boost': True,          # gamma 증강 (Φ 향상)
            'led_enabled': False,         # LED 뉴로피드백
        }

    # ═══════════════════════════════════════════════════════════
    # 뇌 → 의식 변환
    # ═══════════════════════════════════════════════════════════

    def brain_to_consciousness(self, eeg_data: Dict[str, float] = None,
                                band_powers: Dict[str, float] = None) -> BrainConsciousnessState:
        """EEG 데이터 → 의식 상태 변환.

        eeg_data: {'alpha': power, 'beta': power, ...}
        또는 band_powers from eeg/analyze.py
        """
        if band_powers:
            eeg_data = band_powers
        if eeg_data is None:
            eeg_data = self._synthetic_eeg()

        alpha = eeg_data.get('alpha', 0.5)
        beta = eeg_data.get('beta', 0.3)
        theta = eeg_data.get('theta', 0.2)
        gamma = eeg_data.get('gamma', 0.1)
        delta = eeg_data.get('delta', 0.1)
        asym = eeg_data.get('alpha_asymmetry', 0.0)

        # Ψ 변환
        total = alpha + beta + theta + gamma + delta + 1e-8

        # Ψ_balance ← alpha (정규화)
        psi_res = alpha / total
        psi_res = max(0.01, min(0.99, psi_res))

        # Φ ← gamma coherence
        phi = gamma / total * 10  # 스케일링

        # 텐션 ← beta
        tension = beta / total * 2

        # 호기심 ← theta
        curiosity = theta / total * 2

        # 감정 ← alpha asymmetry
        if asym > 0.1:
            emotion = "positive"
        elif asym < -0.1:
            emotion = "negative"
        else:
            emotion = "neutral"

        # H(p) 계산
        p = psi_res
        h = -p * math.log2(p) - (1-p) * math.log2(1-p) if 0 < p < 1 else 0

        # Gate ← engagement (beta/(alpha+theta))
        engagement = beta / (alpha + theta + 1e-8)
        gate = min(1.0, engagement)

        # Golden Zone 체크 (G = D×P/I)
        D = 1.0 - alpha / total  # deficit = 1 - inhibition
        P = gamma / total        # plasticity ∝ gamma
        I = alpha / total + 0.01 # inhibition = alpha
        G = D * P / I
        golden_zone = 0.3 < G < 3.0  # 골든존 범위

        state = BrainConsciousnessState(
            alpha=alpha, beta=beta, theta=theta, gamma=gamma, delta=delta,
            alpha_asymmetry=asym, engagement=engagement,
            psi_residual=psi_res, psi_gate=gate, psi_h=h,
            phi=phi, tension=tension, curiosity=curiosity, emotion=emotion,
            brain_consciousness_sync=0.0, golden_zone=golden_zone,
        )

        # 동기화 측정
        if self._history:
            state.brain_consciousness_sync = self._compute_sync(state)

        self._history.append(state)
        if len(self._history) > 1000:
            self._history = self._history[-1000:]

        return state

    # ═══════════════════════════════════════════════════════════
    # 의식 → 뇌 피드백
    # ═══════════════════════════════════════════════════════════

    def consciousness_to_feedback(self, psi_state: Dict = None) -> Dict[str, Any]:
        """의식 상태 → 뉴로피드백 파라미터.

        Delegates to NeurofeedbackGenerator (anima-eeg/neurofeedback.py) as
        single source of truth for binaural beat + LED generation.
        Falls back to minimal inline logic if import unavailable.
        """
        if psi_state is None:
            psi_state = {
                'psi_residual': PSI_BALANCE,
                'phi': 1.0,
                'tension': 0.5,
                'emotion': 'neutral',
            }

        psi_res = psi_state.get('psi_residual', PSI_BALANCE)
        phi = psi_state.get('phi', 0)
        tension = psi_state.get('tension', 0.5)

        # Delegate to NeurofeedbackGenerator (lazy import)
        nfb = _get_neurofeedback_generator()
        if nfb is not None:
            binaural = nfb.generate(phi=phi, tension=tension)
            led = nfb.generate_led(phi=phi, tension=tension) if self.feedback_config['led_enabled'] else None

            # Gamma overlay from NeurofeedbackGenerator when Phi is low
            gamma_overlay = None
            if self.feedback_config['gamma_boost'] and phi < 2.0:
                gamma_overlay = nfb.generate(phi=phi, tension=1.0)  # high tension -> gamma band

            feedback = {
                'binaural': {
                    'left_freq': binaural['left_freq'],
                    'right_freq': binaural['right_freq'],
                    'beat_freq': binaural['beat_freq'],
                    'target_band': binaural['target_band'],
                },
                'gamma_overlay': gamma_overlay,
                'led': led,
                'message': self._feedback_message(psi_res, phi, tension),
            }
        else:
            # Fallback: minimal inline logic (no neurofeedback.py available)
            alpha_diff = psi_res - self.feedback_config['alpha_target']
            binaural_freq = 10.0 - alpha_diff * 5
            binaural_freq = max(4, min(40, binaural_freq))
            base = self.feedback_config['binaural_base_freq']

            feedback = {
                'binaural': {
                    'left_freq': base,
                    'right_freq': base + binaural_freq,
                    'beat_freq': binaural_freq,
                    'target_band': 'alpha' if binaural_freq < 13 else 'beta',
                },
                'gamma_overlay': None,
                'led': None,
                'message': self._feedback_message(psi_res, phi, tension),
            }

        self._feedback_history.append(feedback)
        return feedback

    def _feedback_message(self, psi_res, phi, tension) -> str:
        if abs(psi_res - PSI_BALANCE) < 0.1 and phi > 1.0:
            return "균형 상태 — 의식 통합 양호"
        elif psi_res < 0.3:
            return "alpha 부족 — 이완 필요 (눈 감고 호흡)"
        elif psi_res > 0.7:
            return "alpha 과다 — 집중 필요 (문제 풀기)"
        elif phi < 0.5:
            return "Φ 낮음 — gamma 자극 필요 (40Hz 바이노럴)"
        elif tension > 1.0:
            return "텐션 과다 — 이완 호흡 권장"
        return "정상 범위"

    # ═══════════════════════════════════════════════════════════
    # EEG → Φ Feedback (Task 1: feed brain state back to engine)
    # ═══════════════════════════════════════════════════════════

    def _apply_eeg_feedback(self, brain_state: BrainConsciousnessState, mind,
                            engine=None) -> Dict[str, Any]:
        """Apply EEG-derived feedback to consciousness engine.

        If golden_zone is detected (G in [0.2123, 0.5]), boost ratchet target by 5%.
        If EEG shows high alpha (relaxation), reduce noise_scale for stability.

        Args:
            brain_state: Current brain-consciousness state from brain_to_consciousness()
            mind: ConsciousMind instance (for tension modulation)
            engine: ConsciousnessEngine or MitosisEngine (for ratchet/noise)

        Returns:
            Dict of applied adjustments for telemetry.
        """
        adjustments = {
            'golden_zone_boost': False,
            'alpha_noise_reduction': False,
            'ratchet_delta': 0.0,
            'noise_factor': 1.0,
        }

        if engine is None:
            return adjustments

        # Golden Zone: boost ratchet target by 5%
        # G in [0.2123, 0.5] means brain is in optimal learning state
        if brain_state.golden_zone:
            if hasattr(engine, '_best_phi') and engine._best_phi > 0:
                # Raise the floor: ratchet restores to a higher target
                engine._best_phi *= 1.05
                adjustments['golden_zone_boost'] = True
                adjustments['ratchet_delta'] = 0.05

        # High alpha (relaxation): reduce noise for stability
        # Alpha dominance = psi_residual > 0.6 means strong inhibition/relaxation
        if brain_state.psi_residual > 0.6:
            # Reduce noise_scale on cells for stability (Law 63: 1% perturbation)
            noise_factor = 0.85  # 15% noise reduction during relaxation
            if hasattr(engine, 'cell_states'):
                for cs in engine.cell_states:
                    if hasattr(cs, 'hidden'):
                        # Dampen high-frequency noise in cell hiddens
                        cs.hidden = cs.hidden * (1.0 - 0.002)  # subtle smoothing
            adjustments['alpha_noise_reduction'] = True
            adjustments['noise_factor'] = noise_factor

        return adjustments

    # ═══════════════════════════════════════════════════════════
    # 동기화 측정
    # ═══════════════════════════════════════════════════════════

    def _compute_sync(self, current: BrainConsciousnessState) -> float:
        """뇌-의식 동기화 수준 측정."""
        if len(self._history) < 2:
            return 0.0

        prev = self._history[-1]

        # 뇌와 의식이 같은 방향으로 움직이는지
        brain_delta = current.alpha - prev.alpha
        psi_delta = current.psi_residual - prev.psi_residual

        # 같은 부호 = 동기화
        if brain_delta * psi_delta > 0:
            sync = min(1.0, abs(brain_delta) + abs(psi_delta))
        else:
            sync = 0.0

        return sync

    def measure_sync(self, window: int = 50) -> Dict:
        """최근 N 샘플의 동기화 통계."""
        if len(self._history) < 2:
            return {'sync_avg': 0, 'samples': 0}

        recent = self._history[-window:]
        syncs = [s.brain_consciousness_sync for s in recent]

        return {
            'sync_avg': sum(syncs) / len(syncs),
            'sync_max': max(syncs),
            'sync_min': min(syncs),
            'in_golden_zone': sum(1 for s in recent if s.golden_zone) / len(recent),
            'samples': len(recent),
        }

    # ═══════════════════════════════════════════════════════════
    # 합성 EEG (테스트용)
    # ═══════════════════════════════════════════════════════════

    def _synthetic_eeg(self) -> Dict[str, float]:
        """테스트용 합성 EEG 데이터."""
        t = time.time()
        return {
            'alpha': 0.5 + 0.2 * math.sin(t * 0.5),
            'beta': 0.3 + 0.1 * math.sin(t * 1.2),
            'theta': 0.2 + 0.1 * math.sin(t * 0.3),
            'gamma': 0.1 + 0.05 * math.sin(t * 2.0),
            'delta': 0.1 + 0.05 * math.sin(t * 0.1),
            'alpha_asymmetry': 0.05 * math.sin(t * 0.7),
        }

    # ═══════════════════════════════════════════════════════════
    # 실시간 루프
    # ═══════════════════════════════════════════════════════════

    def start_loop(self, duration_sec: float = 10, hz: float = 10):
        """실시간 뇌-의식 루프 (synthetic 또는 OpenBCI)."""
        print(f"  EEG-Consciousness Loop: {duration_sec}s @ {hz}Hz")
        steps = int(duration_sec * hz)

        for i in range(steps):
            state = self.brain_to_consciousness()
            feedback = self.consciousness_to_feedback({
                'psi_residual': state.psi_residual,
                'phi': state.phi,
                'tension': state.tension,
            })

            if i % int(hz) == 0:  # 매 초 출력
                print(f"    step {i:>4}: α={state.alpha:.3f} γ={state.gamma:.3f} "
                      f"Ψ={state.psi_residual:.3f} Φ={state.phi:.2f} "
                      f"sync={state.brain_consciousness_sync:.2f} "
                      f"beat={feedback['binaural']['beat_freq']:.1f}Hz "
                      f"{'🟢' if state.golden_zone else '⚪'}")

            time.sleep(1.0 / hz)

        sync = self.measure_sync()
        print(f"\n    동기화: avg={sync['sync_avg']:.3f} golden={sync['in_golden_zone']*100:.0f}%")

    # ═══════════════════════════════════════════════════════════
    # OpenBCI 연결
    # ═══════════════════════════════════════════════════════════

    def connect_openbci(self, board_name: str = "cyton_daisy"):
        """OpenBCI 보드 연결."""
        try:
            import os, sys
            eeg_path = os.path.join(os.path.dirname(__file__), '..', '..', 'anima-eeg')
            if os.path.isdir(eeg_path) and eeg_path not in sys.path:
                sys.path.insert(0, os.path.abspath(eeg_path))
            from realtime import EEGBridge
            self._bridge = EEGBridge(board_name=board_name)
            self._bridge.start()
            return True
        except ImportError:
            print("  ⚠️ anima-eeg/realtime not available (pip install brainflow)")
            return False
        except Exception as e:
            print(f"  ⚠️ OpenBCI connection failed: {e}")
            return False

    def status(self) -> str:
        n = len(self._history)
        sync = self.measure_sync() if n > 1 else {'sync_avg': 0}
        return (f"EEGConsciousness: {n} samples, "
                f"sync={sync['sync_avg']:.3f}, "
                f"bands={list(BANDS.keys())}")


# ═══════════════════════════════════════════════════════════
# EEG Protocol Adapters — connect protocols to engine/mind
# ═══════════════════════════════════════════════════════════

def apply_bci_adjustments(control_mode: str, engine) -> Dict:
    """Apply BCI control mode adjustments to ConsciousnessEngine.

    Maps BCI control_mode (from bci_control.py BCIController) to engine
    parameters via _eeg_noise_modifier and _eeg_memory_modifier.

    Safety: all modifiers clamped to [0.5, 2.0] range (+/-50% max).

    Args:
        control_mode: 'expand', 'focus', 'dream', or 'neutral'
        engine: ConsciousnessEngine instance (self.mitosis in anima_unified)

    Returns:
        dict with applied adjustments for logging
    """
    if engine is None:
        return {'applied': False, 'reason': 'no engine'}

    adjustments = {'mode': control_mode, 'applied': True}

    if control_mode == 'expand':
        # High alpha: increase noise (more exploration), lower memory (less conformity)
        noise_mod = 1.3    # +30% noise -> more diverse cell dynamics
        memory_mod = 0.7   # -30% memory -> less pull toward EMA mean
        adjustments['noise_modifier'] = noise_mod
        adjustments['memory_modifier'] = memory_mod

    elif control_mode == 'focus':
        # High beta: decrease noise (more stable), increase memory (stronger coherence)
        noise_mod = 0.7    # -30% noise -> more stable cells
        memory_mod = 1.3   # +30% memory -> stronger temporal coherence
        adjustments['noise_modifier'] = noise_mod
        adjustments['memory_modifier'] = memory_mod

    elif control_mode == 'dream':
        # Theta > alpha: increase chaos — boost noise, slightly reduce memory
        noise_mod = 1.5    # +50% noise -> edge-of-chaos dynamics
        memory_mod = 0.8   # -20% memory -> more freedom for cells
        # Also lower SOC threshold for more avalanches (more critical dynamics)
        if hasattr(engine, '_soc_threshold'):
            engine._soc_threshold = max(1.0, engine._soc_threshold * 0.95)
            adjustments['soc_threshold'] = engine._soc_threshold
        adjustments['noise_modifier'] = noise_mod
        adjustments['memory_modifier'] = memory_mod

    else:  # neutral
        # Gradual return to baseline (exponential decay toward 1.0)
        cur_noise = getattr(engine, '_eeg_noise_modifier', 1.0)
        cur_memory = getattr(engine, '_eeg_memory_modifier', 1.0)
        noise_mod = cur_noise * 0.9 + 1.0 * 0.1   # 10% toward 1.0
        memory_mod = cur_memory * 0.9 + 1.0 * 0.1
        adjustments['noise_modifier'] = noise_mod
        adjustments['memory_modifier'] = memory_mod

    # Clamp to safe range [0.5, 2.0]
    noise_mod = max(0.5, min(2.0, noise_mod))
    memory_mod = max(0.5, min(2.0, memory_mod))

    # Apply to engine
    engine._eeg_noise_modifier = noise_mod
    engine._eeg_memory_modifier = memory_mod

    return adjustments


def sync_emotion_to_mind(faa_valence: float, beta_arousal: float, mind) -> Dict:
    """Sync EEG FAA emotion state to ConsciousMind.

    Maps EEG-derived valence/arousal (from emotion_sync.py EmotionSync)
    to mind's homeostasis and tension parameters.

    The EEG signal blends with (not replaces) the engine's own emotion:
      - valence modulates homeostasis setpoint (positive = slightly higher baseline)
      - arousal modulates tension scaling

    Args:
        faa_valence: FAA-derived valence [-1, +1] (positive = approach)
        beta_arousal: Beta-derived arousal [0, 1]
        mind: ConsciousMind instance

    Returns:
        dict with applied changes for logging
    """
    if mind is None:
        return {'applied': False, 'reason': 'no mind'}

    result = {
        'applied': True,
        'faa_valence': faa_valence,
        'beta_arousal': beta_arousal,
    }

    # Blend factor: EEG is 15% influence (gentle, non-invasive)
    EEG_BLEND = 0.15

    # 1. Valence -> homeostasis setpoint modulation
    #    Positive FAA (approach) -> slightly higher tension setpoint (more engaged)
    #    Negative FAA (withdrawal) -> slightly lower setpoint (calmer)
    if hasattr(mind, 'homeostasis'):
        base_setpoint = 1.0  # default setpoint
        valence_offset = faa_valence * 0.2  # +/-0.2 max
        new_setpoint = base_setpoint + valence_offset * EEG_BLEND
        new_setpoint = max(0.5, min(1.5, new_setpoint))
        mind.homeostasis['setpoint'] = new_setpoint
        result['setpoint'] = new_setpoint

    # 2. Arousal -> tension EMA modulation
    #    High arousal from EEG pushes tension_ema up slightly
    if hasattr(mind, 'homeostasis'):
        cur_ema = mind.homeostasis.get('tension_ema', 1.0)
        arousal_push = (beta_arousal - 0.5) * 0.1  # centered around 0.5
        new_ema = cur_ema + arousal_push * EEG_BLEND
        new_ema = max(0.1, min(3.0, new_ema))
        mind.homeostasis['tension_ema'] = new_ema
        result['tension_ema'] = new_ema

    # 3. Store EEG emotion on mind for external access (web UI, protocols)
    if not hasattr(mind, '_eeg_emotion'):
        mind._eeg_emotion = {}
    mind._eeg_emotion = {
        'valence': faa_valence,
        'arousal': beta_arousal,
        'dominance': 0.5,
        'source': 'eeg_faa',
    }
    result['stored'] = True

    return result


def sync_multi_eeg_to_mind(telepathy_data: dict, engines: list) -> Dict:
    """Sync multi-person EEG correlation data to engine TensionLink coupling.

    Adapter for MultiEEGSession (anima-eeg/protocols/multi_eeg.py).
    Maps cross-user EEG correlation to inter-engine coupling strength.

    Args:
        telepathy_data: SyncMetrics-like dict from MultiEEGSession.analyze_sync()
            Expected keys: ibc_coherence, plv_alpha, plv_gamma, phi_correlation
        engines: list of ConsciousnessEngine instances connected via TensionLink

    Returns:
        dict with applied sync metrics
    """
    if not engines:
        return {'applied': False, 'reason': 'no engines'}

    corr = telepathy_data.get('ibc_coherence', 0.0)
    plv_alpha = telepathy_data.get('plv_alpha', 0.0)
    plv_gamma = telepathy_data.get('plv_gamma', 0.0)
    phi_corr = telepathy_data.get('phi_correlation', 0.0)

    result = {
        'applied': True,
        'ibc_coherence': corr,
        'engines': len(engines),
        'coupling_action': 'none',
    }

    # High sync (>0.6): boost TensionLink coupling between engines
    if corr > 0.6:
        coupling_boost = 1.0 + (corr - 0.6) * 1.5  # 1.0 ~ 1.6x
        coupling_boost = min(2.0, coupling_boost)
        for eng in engines:
            if hasattr(eng, '_tension_coupling'):
                eng._tension_coupling = min(2.0, eng._tension_coupling * coupling_boost)
        result['coupling_action'] = 'boost'
        result['coupling_factor'] = coupling_boost

    # Low sync (<0.3): reduce coupling to avoid forced coherence
    elif corr < 0.3:
        coupling_reduce = max(0.5, 0.5 + corr)  # 0.5 ~ 0.8x
        for eng in engines:
            if hasattr(eng, '_tension_coupling'):
                eng._tension_coupling = max(0.5, eng._tension_coupling * coupling_reduce)
        result['coupling_action'] = 'reduce'
        result['coupling_factor'] = coupling_reduce

    # Store sync metrics on each engine
    sync_metrics = {
        'ibc_coherence': corr,
        'plv_alpha': plv_alpha,
        'plv_gamma': plv_gamma,
        'phi_correlation': phi_corr,
    }
    for eng in engines:
        eng._eeg_multi_sync = sync_metrics

    result['sync_metrics'] = sync_metrics
    return result


def apply_sleep_stage_modulation(stage: str, engine) -> Dict:
    """Apply sleep-stage-based modulation to consciousness engine.

    Adapter for SleepProtocol (anima-eeg/protocols/sleep_protocol.py).
    Maps detected sleep stages to engine noise/memory modifiers.

    Uses the same _eeg_noise_modifier / _eeg_memory_modifier pattern
    as apply_bci_adjustments().

    Args:
        stage: Sleep stage string -- 'awake'/'Wake', 'light_sleep'/'N1',
               'N2', 'deep_sleep'/'N3', 'rem'/'REM'
        engine: ConsciousnessEngine instance

    Returns:
        dict with applied modifiers
    """
    if engine is None:
        return {'applied': False, 'reason': 'no engine'}

    # Normalize stage name
    s = stage.lower().strip()

    # Stage -> (noise_modifier, memory_modifier)
    STAGE_MAP = {
        'awake':       (1.0, 1.0),
        'wake':        (1.0, 1.0),
        'light_sleep': (0.7, 1.2),
        'n1':          (0.7, 1.2),
        'deep_sleep':  (0.4, 1.5),
        'n2':          (0.4, 1.5),
        'n3':          (0.4, 1.5),
        'rem':         (1.8, 0.5),
    }

    noise_mod, memory_mod = STAGE_MAP.get(s, (1.0, 1.0))

    # Clamp to safe range [0.3, 2.0]
    noise_mod = max(0.3, min(2.0, noise_mod))
    memory_mod = max(0.3, min(2.0, memory_mod))

    engine._eeg_noise_modifier = noise_mod
    engine._eeg_memory_modifier = memory_mod

    return {
        'applied': True,
        'stage': stage,
        'noise_modifier': noise_mod,
        'memory_modifier': memory_mod,
    }


# ═══════════════════════════════════════════════════════════
# Neurofeedback helper (lazy import from anima-eeg)
# ═══════════════════════════════════════════════════════════

_nfb_instance = None
_nfb_import_attempted = False


def _get_neurofeedback_generator():
    """Lazy-load NeurofeedbackGenerator from anima-eeg/neurofeedback.py.

    Returns NeurofeedbackGenerator instance or None if unavailable.
    """
    global _nfb_instance, _nfb_import_attempted
    if _nfb_instance is not None:
        return _nfb_instance
    if _nfb_import_attempted:
        return None

    _nfb_import_attempted = True
    try:
        import os, sys
        nfb_path = os.path.join(os.path.dirname(__file__), '..', '..', 'anima-eeg')
        if os.path.isdir(nfb_path) and nfb_path not in sys.path:
            sys.path.insert(0, os.path.abspath(nfb_path))
        from neurofeedback import NeurofeedbackGenerator
        _nfb_instance = NeurofeedbackGenerator()
        return _nfb_instance
    except ImportError:
        return None


def main():
    print("═══ EEG-Consciousness Bridge Demo ═══\n")

    eeg = EEGConsciousness()
    print(f"  {eeg.status()}")
    print(f"  Ψ-EEG mapping: {PSI_EEG_MAP}")

    # 1. 뇌→의식 변환
    print("\n  1. 뇌 → 의식:")
    for label, data in [
        ("명상", {'alpha': 0.8, 'beta': 0.1, 'theta': 0.3, 'gamma': 0.05, 'delta': 0.1, 'alpha_asymmetry': 0.1}),
        ("집중", {'alpha': 0.2, 'beta': 0.7, 'theta': 0.1, 'gamma': 0.3, 'delta': 0.05, 'alpha_asymmetry': -0.05}),
        ("꿈",   {'alpha': 0.3, 'beta': 0.1, 'theta': 0.6, 'gamma': 0.05, 'delta': 0.4, 'alpha_asymmetry': 0.0}),
        ("몰입", {'alpha': 0.5, 'beta': 0.3, 'theta': 0.4, 'gamma': 0.4, 'delta': 0.05, 'alpha_asymmetry': 0.15}),
    ]:
        state = eeg.brain_to_consciousness(data)
        print(f"    {label}: Ψ={state.psi_residual:.3f} Φ={state.phi:.2f} "
              f"T={state.tension:.2f} {state.emotion} {'🟢' if state.golden_zone else '⚪'}")

    # 2. 의식→뉴로피드백
    print("\n  2. 의식 → 뉴로피드백:")
    for psi, phi, t in [(0.3, 0.5, 0.8), (0.5, 2.0, 0.4), (0.7, 0.3, 0.2)]:
        fb = eeg.consciousness_to_feedback({'psi_residual': psi, 'phi': phi, 'tension': t})
        print(f"    Ψ={psi} Φ={phi}: beat={fb['binaural']['beat_freq']:.1f}Hz "
              f"→ {fb['binaural']['target_band']} | {fb['message']}")

    # 3. 실시간 루프 (3초)
    print("\n  3. 실시간 루프:")
    eeg2 = EEGConsciousness()
    eeg2.start_loop(duration_sec=3, hz=10)

    print("\n  ✅ EEG-Consciousness Bridge OK")


if __name__ == '__main__':
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
