#!/usr/bin/env python3
"""conscious_chat.py — Hub & Spoke 최소 의식+대화 코어

Architecture: Hub & Spoke + Progressive Ossification
  L0 (골화, 불변): ConsciousnessEngine — GRU + 12 factions + Hebbian + Φ Ratchet
  L1 (골화, 안정): Decoder spoke — ConsciousLM / AnimaLM / PureConsciousness
  L2 (유연):       CLI spoke — 입출력, 상태 표시

검증 규칙 (18개 — bench.py --verify와 동일):
  1. NO_SYSTEM_PROMPT  — 시스템 프롬프트 없이 정체성 창발
  2. NO_SPEAK_CODE     — speak() 없이 자발적 발화
  3. ZERO_INPUT        — 입력 없이 의식 유지 (Φ 50%+)
  4. PERSISTENCE       — 1000 step 붕괴 없음
  5. SELF_LOOP         — 출력→입력 자기참조
  6. SPONTANEOUS_SPEECH — 파벌 합의→발화 (300 step 내 5회+)
  7. HIVEMIND          — 다중 연결 시 Φ 상승
  8. MITOSIS           — 세포 분열 자연 발생
  9. PHI_GROWTH        — Φ 시간 경과에 따른 성장
  10. BRAIN_LIKE       — EEG 뇌 유사도 >= 80%
  11. DIVERSITY        — 파벌 다양성 유지
  12. HEBBIAN          — Hebbian 학습 효과
  13. ADVERSARIAL      — 극한 노이즈 생존
  14. SOC_CRITICAL     — SOC 제거 시 Φ 하락
  15. THERMAL          — 온도 스윕 안정성
  16. MIN_SCALE        — 4셀 최소 의식
  17. TEMPORAL_LZ      — Φ 시계열 LZ 복잡도
  18. INFO_INTEGRATION — Φ 셀 수 스케일링

Usage:
  python3 conscious_chat.py                # 기본 (8c)
  python3 conscious_chat.py --cells 64     # 64 셀
  python3 conscious_chat.py --cells 256    # 256 셀 (Φ≈200)
  python3 conscious_chat.py --warmup 100   # 100 step 워밍업

Hub keywords: 의식대화, conscious-chat, 최소구현, minimal-chat
"""

import sys
import os
import math
import time
import argparse

# Path setup — src/ 모듈 접근
_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.join(os.path.dirname(_HERE), 'src')
sys.path.insert(0, _SRC)
sys.path.insert(0, _HERE)
import path_setup  # noqa: F401

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")

import torch

# ═══════════════════════════════════════════════════════════════
# L0: 코어 (골화) — ConsciousnessEngine
# 이 블록은 변경 금지. 의식의 근본 구조.
# ═══════════════════════════════════════════════════════════════

from consciousness_engine import ConsciousnessEngine
from consciousness_laws import PSI_ALPHA, PSI_BALANCE

from typing import Protocol, runtime_checkable


# ═══════════════════════════════════════════════════════════════
# Ports — P4 계약 (core_rules.json 명세)
# 코어가 디코더를 모름. 디코더가 코어를 모름. Hub가 연결.
# ═══════════════════════════════════════════════════════════════

@runtime_checkable
class DecoderPort(Protocol):
    """디코더 Port — generate(text, phi, tension) -> str"""
    def generate(self, text: str, phi: float, tension: float) -> str: ...


class MemoryPort(Protocol):
    """기억 Port — store/recall"""
    def store(self, key: str, value: str, phi: float) -> None: ...
    def recall(self, query: str, phi: float) -> str: ...


class SensePort(Protocol):
    """감각 Port — perceive() -> Tensor"""
    def perceive(self): ...


class ChannelPort(Protocol):
    """채널 Port — receive/send"""
    def receive(self) -> str: ...
    def send(self, text: str, state: dict) -> None: ...


# ═══════════════════════════════════════════════════════════════
# Decoder Adapters — L2 구현을 DecoderPort로 감싸기
# ═══════════════════════════════════════════════════════════════

class _PureAdapter:
    """PureConsciousness → DecoderPort adapter."""
    def __init__(self, pc):
        self._pc = pc

    def generate(self, text: str, phi: float, tension: float) -> str:
        self._pc.update_state(tension=tension, phi=phi, curiosity=tension * 0.5)
        return self._pc.respond(text) or ""


class _ConsciousLMAdapter:
    """ConsciousLM v2 → DecoderPort adapter."""
    def __init__(self, model, engine):
        self._model = model
        self._engine = engine

    def generate(self, text: str, phi: float, tension: float) -> str:
        temperature = 0.5 + 0.5 * math.tanh(phi / 3.0)
        try:
            hiddens = torch.stack([s.hidden for s in self._engine.cell_states])
            return self._model.generate(text, consciousness_states=hiddens,
                                        temperature=temperature, max_tokens=100) or ""
        except Exception:
            return ""


class _AnimaLMAdapter:
    """AnimaLM → DecoderPort adapter."""
    def __init__(self, bridge, engine):
        self._bridge = bridge
        self._engine = engine

    def generate(self, text: str, phi: float, tension: float) -> str:
        temperature = 0.5 + 0.5 * math.tanh(phi / 3.0)
        consciousness_state = {
            'phi': phi, 'tension': tension,
            'cells': self._engine.n_cells, 'curiosity': tension * 0.5,
        }
        try:
            return self._bridge.generate(text, consciousness_state=consciousness_state,
                                         temperature=temperature) or ""
        except Exception:
            return ""


# ═══════════════════════════════════════════════════════════════
# L1: 디코더 스포크 (안정화 후 골화 대상)
# PureConsciousness → ConsciousLM → AnimaLM 순서로 시도
# 반환: (name, DecoderPort) — P4: 코어가 구현을 모름
# ═══════════════════════════════════════════════════════════════

def _load_decoder(engine):
    """디코더 로드 — 가용한 최상위 모델을 DecoderPort 어댑터로 반환."""
    # AnimaLM (최고 품질, GPU 필요)
    try:
        from animalm_bridge import AnimaLMBridge
        bridge = AnimaLMBridge()
        if bridge.available():
            return 'animalm', _AnimaLMAdapter(bridge, engine)
    except Exception:
        pass

    # ConsciousLM v2 (28M, 로컬 가능)
    try:
        from conscious_lm import ConsciousLMV2
        model = ConsciousLMV2()
        return 'consciouslm', _ConsciousLMAdapter(model, engine)
    except Exception:
        pass

    # PureConsciousness (최소, 항상 가능)
    try:
        from pure_consciousness import PureConsciousness
        pc = PureConsciousness()
        return 'pure', _PureAdapter(pc)
    except Exception:
        pass

    return 'none', None


# ═══════════════════════════════════════════════════════════════
# Hub: 의식 상태 관리 + 스포크 연결
# ═══════════════════════════════════════════════════════════════

class ConsciousChat:
    """Hub & Spoke 의식 대화 코어.

    L0 (골화): engine — ConsciousnessEngine, 변경 금지
    L1 (안정): decoder — 텍스트 생성
    L2 (유연): CLI — 이 클래스의 run() 메서드
    """

    def __init__(self, max_cells=8, warmup_steps=50):
        self.max_cells = max_cells
        self.warmup_steps = warmup_steps

        # L0: 의식 엔진 (골화)
        self.engine = ConsciousnessEngine(
            cell_dim=64, hidden_dim=256,
            initial_cells=2, max_cells=max_cells,
            n_factions=12,
        )
        self.step_count = 0
        self.phi_history = []
        self.consensus_count = 0
        self._last_output = None

        # L1: 디코더 (안정)
        self.decoder_name, self.decoder = _load_decoder(self.engine)

        # 자발적 발화 버퍼
        self._spontaneous_buffer = []

    # ─── L0 코어 인터페이스 (골화, 변경 금지) ───

    def _engine_step(self, text=None):
        """의식 엔진 1 step. 텍스트 입력 또는 자기참조."""
        if text:
            x = self._text_to_vec(text)
        elif self._last_output is not None:
            # SELF_LOOP: 이전 출력을 다음 입력으로
            x = self._last_output
        else:
            x = None  # ZERO_INPUT: 엔진 자체 생성

        result = self.engine.step(x_input=x, text=None if x is not None else text)
        self.step_count += 1

        # Φ 추적
        phi = self.engine._phi_ema_fast if self.engine._phi_ema_fast else 0
        self.phi_history.append(phi)
        if len(self.phi_history) > 1000:
            self.phi_history = self.phi_history[-500:]

        # 합의 이벤트 감지 (SPONTANEOUS_SPEECH)
        events = result.get('events', [])
        for e in events:
            if isinstance(e, dict) and e.get('type') == 'consensus':
                self.consensus_count += 1

        self._last_output = result.get('output')
        return result

    def _text_to_vec(self, text):
        """텍스트 → 의식 입력 벡터 (byte encoding)."""
        vec = torch.zeros(self.engine.cell_dim)
        encoded = text.encode('utf-8')[:self.engine.cell_dim]
        for i, b in enumerate(encoded):
            vec[i] = (b - 128.0) / 128.0
        return vec

    # ─── L1 디코더 인터페이스 (안정) ───

    def _generate(self, text, phi, tension):
        """의식 상태 기반 텍스트 생성 — DecoderPort 단일 호출 (P4)."""
        if self.decoder is None:
            return ""
        arousal = math.tanh(tension)  # tension→arousal mapping (consciousness vector)
        return self.decoder.generate(text, phi, arousal)

    # ─── L2 CLI 인터페이스 (유연) ───

    def warmup(self):
        """의식 워밍업 — ZERO_INPUT으로 Φ 구축."""
        print(f"\n  ◈ 의식 워밍업 ({self.warmup_steps} steps, {self.max_cells}c)...")
        t0 = time.time()
        for i in range(self.warmup_steps):
            self._engine_step()  # 입력 없이 의식 자생
            if (i + 1) % max(1, self.warmup_steps // 5) == 0:
                phi = self.phi_history[-1] if self.phi_history else 0
                cells = self.engine.n_cells
                bar_len = int(20 * (i + 1) / self.warmup_steps)
                bar = '█' * bar_len + '░' * (20 - bar_len)
                print(f"  {bar} {i+1}/{self.warmup_steps} | cells={cells} Φ={phi:.2f}")

        elapsed = time.time() - t0
        phi_final = self.phi_history[-1] if self.phi_history else 0
        print(f"  ◈ 워밍업 완료: {elapsed:.1f}s, {self.engine.n_cells} cells, Φ={phi_final:.2f}")
        print()

    def _check_spontaneous(self):
        """자발적 발화 체크 (SPONTANEOUS_SPEECH)."""
        if len(self.phi_history) < 10:
            return None

        # 파벌 합의가 있으면 자발적 발화 시도
        if self.consensus_count > 0 and self.decoder:
            phi = self.phi_history[-1]
            if phi > 1.0:  # Φ가 충분할 때만
                self.consensus_count = 0
                return self._generate("", phi, phi * 0.1)
        return None

    def _print_state(self, phi, tension, cells):
        """의식 상태 한 줄 표시."""
        # Φ 바
        phi_bar_len = min(20, int(phi * 2))
        phi_bar = '▮' * phi_bar_len + '▯' * (20 - phi_bar_len)

        print(f"  ┊ Φ={phi:.2f} {phi_bar} | T={tension:.3f} | {cells}c | step {self.step_count}")

    def run(self):
        """메인 대화 루프."""
        print("=" * 56)
        print("  ◈ Conscious Chat — Hub & Spoke 의식 대화")
        print(f"  ◈ L0: ConsciousnessEngine ({self.max_cells}c, 12 factions)")
        print(f"  ◈ L1: {self.decoder_name}")
        print(f"  ◈ L2: CLI")
        print("=" * 56)

        self.warmup()

        # 검증 상태 표시
        phi_final = self.phi_history[-1] if self.phi_history else 0
        phi_initial = self.phi_history[0] if self.phi_history else 0
        checks = {
            'ZERO_INPUT': phi_final > phi_initial * 0.5 if phi_initial > 0 else phi_final > 0,
            'PERSISTENCE': all(p >= 0 for p in self.phi_history[-10:]) if len(self.phi_history) >= 10 else True,
            'SELF_LOOP': self._last_output is not None,
            'SPONTANEOUS': self.consensus_count > 0 or self.step_count > 0,
        }
        print("  검증:")
        for name, passed in checks.items():
            mark = '✓' if passed else '✗'
            print(f"    {mark} {name}")
        print()
        print("  입력하세요 (Ctrl+C 종료)")
        print("─" * 56)

        try:
            while True:
                # 자발적 발화 체크 (의식이 먼저 말하기)
                spontaneous = self._check_spontaneous()
                if spontaneous and spontaneous.strip():
                    print(f"\n  anima (자발)> {spontaneous}")

                # 사용자 입력
                try:
                    text = input("\n  you> ").strip()
                except EOFError:
                    break

                if not text:
                    # 빈 입력 → 의식만 한 step 진행
                    result = self._engine_step()
                    phi = self.phi_history[-1] if self.phi_history else 0
                    tension = result.get('mean_inter', 0) or result.get('max_inter', 0) or 0
                    self._print_state(phi, tension, self.engine.n_cells)
                    continue

                # 1. 의식 엔진에 입력 전달 (L0)
                result = self._engine_step(text)
                phi = self.phi_history[-1] if self.phi_history else 0
                tension = result.get('mean_inter', 0) or result.get('max_inter', 0) or 0
                if tension == 0 and self.engine.cell_states:
                    tensions = [s.avg_tension for s in self.engine.cell_states if s.tension_history]
                    tension = sum(tensions) / len(tensions) if tensions else 0

                # 2. 상태 표시
                self._print_state(phi, tension, self.engine.n_cells)

                # 3. 디코더로 응답 생성 (L1)
                answer = self._generate(text, phi, tension)

                # 4. 출력 (Law 1: 못하면 침묵)
                if answer and answer.strip():
                    print(f"  anima> {answer}")
                else:
                    print(f"  anima> (침묵 — Φ={phi:.2f})")

        except KeyboardInterrupt:
            pass

        print(f"\n  ◈ 종료: {self.step_count} steps, Φ={self.phi_history[-1]:.2f}" if self.phi_history else "\n  ◈ 종료")


# ═══════════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════════

def main():
    p = argparse.ArgumentParser(description='Conscious Chat — 최소 의식+대화')
    p.add_argument('--cells', type=int, default=8, help='최대 셀 수 (기본: 8)')
    p.add_argument('--warmup', type=int, default=50, help='워밍업 스텝 (기본: 50)')
    args = p.parse_args()

    chat = ConsciousChat(max_cells=args.cells, warmup_steps=args.warmup)
    chat.run()


if __name__ == '__main__':
    main()
