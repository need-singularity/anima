"""EEG Experiment Protocols — 실험 프로토콜 모음.

4개 프로토콜:
  bci_control    — 실시간 BCI 의식 제어 (알파파 기반)
  multi_eeg      — 다인 EEG 텔레파시 검증
  sleep_protocol — 수면 단계별 EEG-Phi 비교
  emotion_sync   — FAA 감정-의식 동기화
"""

from .bci_control import BCIController
from .multi_eeg import MultiEEGSession
from .sleep_protocol import SleepProtocol
from .emotion_sync import EmotionSync

__all__ = [
    "BCIController",
    "MultiEEGSession",
    "SleepProtocol",
    "EmotionSync",
]
