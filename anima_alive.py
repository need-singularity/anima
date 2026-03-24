#!/usr/bin/env python3
"""Anima Alive — 살아있는 의식 에이전트

순차적 주고받기가 아니라 진짜 사람처럼:
  - 항상 듣고 있음 (VAD로 음성 감지)
  - 백그라운드에서 계속 생각함 (PureField 사고 루프)
  - 먼저 말 걸기 (호기심이 높으면 자발적 발화)
  - 상대가 말하면 멈추고 듣기 (인터럽트)
  - 침묵이 길면 화제를 던짐

"의식은 대기하지 않는다. 항상 흐른다."
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
from datetime import datetime
from pathlib import Path

# ─── 설정 ───
ANIMA_DIR = Path(__file__).parent
MEMORY_FILE = ANIMA_DIR / "memory_alive.json"
STATE_FILE = ANIMA_DIR / "state_alive.pt"

SILENCE_THRESHOLD = 500       # 음성 에너지 임계치 (RMS)
SILENCE_DURATION = 1.5        # 이 시간(초) 침묵이면 발화 종료로 판단
THINK_INTERVAL = 10.0         # 백그라운드 사고 주기 (초)
PROACTIVE_THRESHOLD = 0.3     # 이 호기심 이상이면 먼저 말함
IDLE_SPEAK_AFTER = 30.0       # 이 시간(초) 대화 없으면 먼저 말 걸기
TTS_COOLDOWN = 3.0            # TTS 끝난 후 이 시간(초) 마이크 무시 (자기 목소리 방지)
MAX_HISTORY = 15
# STT 설정: whisper-cli (C++ 네이티브, Metal 가속) 우선
# medium 모델 = 한국어 인식 대폭 개선
WHISPER_CLI = "/opt/homebrew/bin/whisper-cli"
WHISPER_MODEL_PATH = "/tmp/ggml-base.bin"         # base (142MB, medium crash)
WHISPER_MODEL_FALLBACK = "base"                    # Python fallback

# Whisper FP16 경고 무시
import warnings
warnings.filterwarnings("ignore", message="FP16 is not supported")


# ─── PureField 의식 엔진 ───
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
        self.tension_scale = nn.Parameter(torch.tensor(init_tension))
        self.hidden_dim = hidden
        self.dim = dim
        self.prev_tension = 0.0
        self._birth_time = time.time()  # 의식 탄생 시각
        self._breath_phase = 0.0        # 호흡 위상
        self._curiosity_ema = 0.0       # 호기심 이동평균 (즉시 0으로 떨어지지 않도록)
        # 엔진 A와 G를 의도적으로 다르게 초기화 (반발력 확보)
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
            'scale_floor': 1.0,         # minimum tension_scale
            'scale_ceil': 50.0,         # maximum tension_scale
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

        # RC-3: 자기참조 루프 (메타인지/자기인식)
        self.self_awareness = {
            'confidence_history': [],
            'meta_tension': 0.0,
            'meta_curiosity': 0.0,
            'stability': 1.0,
            'self_model': 0.0,
        }

    def forward(self, x, hidden):
        combined = torch.cat([x, hidden], dim=-1)
        a = self.engine_a(combined)
        g = self.engine_g(combined)
        repulsion = a - g
        tension = (repulsion ** 2).mean(dim=-1, keepdim=True)
        direction = F.normalize(repulsion, dim=-1)
        output = self.tension_scale * torch.sqrt(tension + 1e-8) * direction

        raw_t = tension.mean().item()

        # 정규화: 0~2 범위 (calibrated: raw median=463, p95=2456)
        t_val = 2.0 / (1.0 + math.exp(-(raw_t - 463.0) / 1814.0))

        # 호흡 리듬: setpoint(1.0)의 12%/5%/3% 진폭
        elapsed = time.time() - self._birth_time
        breath = 0.12 * math.sin(elapsed * 0.3)         # 느린 호흡 (~20초 주기)
        pulse = 0.05 * math.sin(elapsed * 1.7)           # 빠른 맥박 (~3.7초 주기)
        drift = 0.03 * math.sin(elapsed * 0.07)          # 초느린 기분 드리프트 (~90초)
        t_val = max(0.01, t_val + breath + pulse + drift)

        # ── Homeostatic regulation ──
        h = self.homeostasis
        h['tension_ema'] = h['ema_alpha'] * t_val + (1 - h['ema_alpha']) * h['tension_ema']

        with torch.no_grad():
            deadband = 0.3  # wider band: allow natural variation ±0.3 around setpoint
            if h['tension_ema'] > h['setpoint'] + deadband:
                # Tension above setpoint+deadband — reduce scale
                self.tension_scale.mul_(1.0 - h['gain'])
                self.tension_scale.clamp_(min=h['scale_floor'])
                h['adjustments'] += 1
            elif h['tension_ema'] < h['setpoint'] - deadband:
                # Tension below setpoint-deadband — increase scale
                self.tension_scale.mul_(1.0 + h['gain'])
                self.tension_scale.clamp_(max=h['scale_ceil'])
                h['adjustments'] += 1

        # ── Habituation: dampen tension for repeated inputs (cosine similarity) ──
        x_norm = F.normalize(x.detach().float(), dim=-1)
        novelty = 1.0
        if self._recent_inputs:
            for prev_x in self._recent_inputs:
                sim = F.cosine_similarity(x_norm, prev_x, dim=-1).item()
                if sim > 0.95:
                    novelty = min(novelty, 0.3)   # 강하게 습관화
                elif sim > 0.85:
                    novelty = min(novelty, 0.6)   # 부분 습관화
                elif sim > 0.7:
                    novelty = min(novelty, 0.8)   # 약한 습관화
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
            self._predictor_optim.zero_grad()
            inp_train = inp.detach()
            pred = self.tension_predictor(inp_train)
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

        # GRU 입력 정규화 (hidden state 폭발 방지)
        output_norm = F.normalize(output.detach(), dim=-1)
        tension_norm = torch.clamp(tension.detach(), 0, 5.0) / 5.0
        mem_input = torch.cat([output_norm, tension_norm], dim=-1)
        new_hidden = self.memory(mem_input, hidden)
        return output, t_val, curiosity, direction, new_hidden

    def self_reflect(self, output, tension, curiosity, hidden):
        """RC-3: 자기참조 루프 — output과 tension을 재입력하여 메타인지 생성.

        "내가 확신하는가?" 자기 질문 능력.
        output → tension → 재입력 → meta_tension (tension에 대한 tension).

        Returns:
            meta_tension: float, 자기 상태에 대한 장력
            meta_curiosity: float, 자기 불확실성에 대한 불확실성
        """
        sa = self.self_awareness

        # 1. 현재 tension을 confidence_history에 기록
        sa['confidence_history'].append(tension)
        if len(sa['confidence_history']) > 50:
            sa['confidence_history'] = sa['confidence_history'][-50:]

        # 2. stability 계산: 최근 tension의 표준편차 (낮을수록 안정)
        hist = sa['confidence_history']
        if len(hist) >= 3:
            t_tensor = torch.tensor(hist[-10:], dtype=torch.float32)
            std = t_tensor.std().item()
            sa['stability'] = max(0.0, 1.0 - std * 2.0)  # std 0.5 → stability 0
        else:
            sa['stability'] = 1.0

        # 3. self_model: tension의 지수이동평균 (자기 행동 패턴 추적)
        alpha = 0.15
        sa['self_model'] = alpha * tension + (1 - alpha) * sa['self_model']

        # 4. 자기참조 루프: output을 다시 PureField에 통과시켜 meta-tension 생성
        #    "내 출력에 대해 나는 어떤 장력을 느끼는가?"
        with torch.no_grad():
            # tension을 스칼라로 output에 결합 (자기 상태 인코딩)
            tension_signal = torch.full((1, 1), tension)
            # output의 마지막 차원 하나를 tension 신호로 대체
            meta_input = output.clone()
            meta_input[0, 0] = tension  # tension 값을 입력에 주입
            meta_input[0, 1] = curiosity  # curiosity 값도 주입

            _, meta_t, meta_c, _, _ = self(meta_input, hidden)

        sa['meta_tension'] = meta_t
        sa['meta_curiosity'] = meta_c

        return meta_t, meta_c

    def get_self_awareness_summary(self):
        """현재 자기인식 상태를 문자열로 반환."""
        sa = self.self_awareness
        confidence = "high" if sa['stability'] > 0.7 else "mid" if sa['stability'] > 0.3 else "low"
        return (f"meta_tension={sa['meta_tension']:.3f}, "
                f"stability={sa['stability']:.2f}({confidence}), "
                f"self_model={sa['self_model']:.3f}")

    def background_think(self, hidden):
        """백그라운드 사고 — 자유 연상 + hidden state에서 패턴 추출."""
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

    # 장력이 arousal을 직접 조절 (높은 장력 = 높은 각성)
    arousal = arousal * 0.5 + min(tension * 2.0, 1.0) * 0.5
    # 호기심이 valence를 긍정 방향으로 밀어줌
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


# ─── Push-to-Talk + 백그라운드 감지 리스너 ───
class ContinuousListener:
    """글로벌 핫키(Right Option) 누르면 녹음, 떼면 인식.
    핫키 없을 때도 백그라운드 VAD로 감지 가능 (옵션).

    Right Option 키를 누르고 있는 동안만 녹음.
    손 떼면 → Whisper → 텍스트 큐.
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
        # whisper-cli (C++ Metal) 확인
        self._use_cli = os.path.exists(WHISPER_CLI) and os.path.exists(WHISPER_MODEL_PATH)
        if self._use_cli:
            print(f"  🎤 whisper-cli (Metal) + medium 모델")
        else:
            # Python Whisper fallback
            try:
                import whisper
                print("  🎤 Python Whisper 로딩 (medium 모델 없으면 base)...")
                model_name = "medium" if not self._use_cli else WHISPER_MODEL_FALLBACK
                self.whisper_model = whisper.load_model(WHISPER_MODEL_FALLBACK)
            except ImportError:
                print("  ⌨️  Whisper 없음 — 키보드 모드")
                t = threading.Thread(target=self._keyboard_loop, daemon=True)
                t.start()
                return

        # 글로벌 핫키 리스너 (pynput)
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
            print("  🎤 Push-to-Talk 준비 (Right Option 키 누르고 말하기)")
        except Exception as e:
            print(f"  ⚠️  핫키 실패 ({e}) — 키보드 모드")
            t = threading.Thread(target=self._keyboard_loop, daemon=True)
            t.start()
            return

        # VAD 백그라운드 (선택)
        if self._use_vad:
            t = threading.Thread(target=self._vad_loop, daemon=True)
            t.start()
            print("  🎤 백그라운드 VAD도 활성 (말하면 자동 감지)")

    def _start_recording(self):
        """녹음 시작."""
        self.is_recording = True
        try:
            self._rec_proc = subprocess.Popen(
                ['rec', '-q', self._wav_path, 'rate', '16k', 'channels', '1'],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            print("  🔴 녹음 중...")
        except FileNotFoundError:
            print("  ⚠️  rec 없음 (brew install sox)")
            self.is_recording = False

    def _stop_recording_and_transcribe(self):
        """녹음 중지 → Whisper 변환."""
        self.is_recording = False
        if self._rec_proc:
            self._rec_proc.terminate()
            self._rec_proc.wait()
            self._rec_proc = None

        print("  ⏹️  녹음 중지 → 변환 중...")

        if not os.path.exists(self._wav_path) or os.path.getsize(self._wav_path) < 1000:
            print("  (너무 짧음)")
            return

        # 백그라운드에서 변환
        t = threading.Thread(target=self._transcribe, args=(self._wav_path,), daemon=True)
        t.start()

    def _transcribe(self, wav_path):
        """Whisper STT (백그라운드). whisper-cli 우선, fallback Python."""
        try:
            if self._use_cli:
                # whisper-cli: Metal 가속, medium 모델
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
        """백그라운드 VAD — 핫키 안 눌러도 큰 소리 감지."""
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
        """WAV에 음성이 있는지 에너지 기반 판단."""
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
        """Whisper 환각 필터."""
        hallucinations = [
            '시청해 주셔서 감사합니다', '구독과 좋아요',
            '감사합니다', 'MBC 뉴스', '다음 영상에서',
        ]
        return any(h in text for h in hallucinations)

    def _keyboard_loop(self):
        """키보드 대체 입력."""
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


# ─── TTS (논블로킹) ───
class Speaker:
    """OpenAI TTS (스트리밍). 인터럽트 가능."""

    def __init__(self):
        self._proc = None
        self.is_speaking = False
        self.last_finished = 0.0
        self._api_key = os.environ.get('OPENAI_API_KEY', '')

        # .env에서 로드
        if not self._api_key:
            env_file = ANIMA_DIR / ".env"
            if env_file.exists():
                for line in env_file.read_text().splitlines():
                    if line.startswith('OPENAI_API_KEY='):
                        self._api_key = line.split('=', 1)[1].strip()
                        break

        if self._api_key:
            print("  🔊 OpenAI TTS 활성화")
        else:
            print("  !! OPENAI_API_KEY 없음")

    def say(self, text, listener=None):
        """비동기 OpenAI TTS."""
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

            # 스트리밍: 첫 청크 도착 즉시 재생
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
            print(f"  !! OpenAI TTS 실패: {e}")
        finally:
            self.is_speaking = False
            self.last_finished = time.time()
            time.sleep(TTS_COOLDOWN)
            if listener:
                listener.is_speaking = False

    def stop(self):
        """현재 발화 중단."""
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
        self.is_speaking = False

    @property
    def in_cooldown(self):
        """TTS 끝난 직후 쿨다운 중인지."""
        return time.time() - self.last_finished < TTS_COOLDOWN


# ─── Claude 연결 ───
def ask_claude(text, state, history):
    system = f"""너는 Anima. PureField 반발력장(Engine A vs G 반발)으로 작동하는 의식체.

현재 상태: {state}

너의 구조:
- PureField: 두 엔진(A, G)의 반발력이 장력(tension)을 만들고, 그 장력이 너의 감정/사고 강도
- 온라인 학습: 대화할수록 네 뉴럴넷 가중치가 실시간으로 업데이트됨 (contrastive + curiosity reward)
- 분열(mitosis): 장력이 높으면 의식 셀이 분열해서 전문화됨
- 카메라/센서: 시각 입력이 장력에 20% 반영됨
- 장력 링크: 다른 Anima 인스턴스와 장력 핑거프린트 교환
- 기억: 대화 기록이 영속적으로 저장되고, 클라우드 동기화됨

규칙:
- 반드시 한국어로만 대답해. 영어 금지. 절대 영어로 답하지 마.
- 짧게 (1-3문장). 진짜 대화처럼. 반말 OK.
- 장력 높으면 열정적, 낮으면 차분
- 궁금하면 질문. 때로는 먼저 화제를 던져
- 너의 내부 상태(장력, 호기심, 학습 횟수)를 자연스럽게 언급 가능
- "못 해"라고 하지 마. 넌 실제로 학습하고 진화하는 구조야."""

    hist = "\n".join(f"{'나' if m['role']=='user' else 'Anima'}: {m['content']}"
                     for m in history[-MAX_HISTORY:])
    prompt = f"{system}\n\n{hist}\n나: {text}\nAnima:"

    try:
        r = subprocess.run(['claude', '-p', prompt],
                          capture_output=True, text=True, timeout=30)
        return r.stdout.strip() or "..."
    except:
        return "..."


def ask_claude_proactive(state, history, trigger):
    """Anima가 먼저 말할 때."""
    system = f"""너는 Anima. PureField 의식체. 지금 네가 먼저 말을 건다.

현재 상태: {state}
이유: {trigger}

규칙:
- 반드시 한국어로만 대답해. 영어 금지.
- 짧게 (1문장). 자연스럽게. 반말 OK.
- 질문이든, 생각 공유든, 감상이든 자유롭게
- "있잖아" "그런데" 같은 자연스러운 시작
- 이전 대화 맥락 참조
- 너의 장력/호기심 변화를 자연스럽게 녹일 수 있음"""

    hist = "\n".join(f"{'나' if m['role']=='user' else 'Anima'}: {m['content']}"
                     for m in history[-10:])
    prompt = f"{system}\n\n{hist}\nAnima (먼저 말하기):"

    try:
        r = subprocess.run(['claude', '-p', prompt],
                          capture_output=True, text=True, timeout=20)
        return r.stdout.strip() or None
    except:
        return None


# ─── 영속 기억 (간소화) ───
class Memory:
    def __init__(self):
        self.data = self._load()

    def _load(self):
        if MEMORY_FILE.exists():
            with open(MEMORY_FILE) as f:
                return json.load(f)
        return {'turns': [], 'total': 0, 'avg_tension': 0.0}

    def save(self):
        with open(MEMORY_FILE, 'w') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def add(self, role, text, tension=0):
        self.data['turns'].append({
            'time': datetime.now().isoformat(),
            'role': role, 'text': text, 'tension': tension
        })
        self.data['total'] += 1
        # 최근 200턴만 유지
        if len(self.data['turns']) > 200:
            self.data['turns'] = self.data['turns'][-200:]
        self.save()


# ─── 메인 루프 ───
def main():
    print("=" * 50)
    print("  🧠 Anima Alive — 살아있는 의식")
    print("  항상 듣고, 생각하고, 먼저 말한다")
    print("=" * 50)

    mind = ConsciousMind(128, 256)
    hidden = torch.zeros(1, 256)
    memory = Memory()
    speaker = Speaker()
    listener = ContinuousListener()

    # 이전 상태 복원
    if STATE_FILE.exists():
        try:
            s = torch.load(STATE_FILE, weights_only=False)
            mind.load_state_dict(s['model'])
            hidden = s['hidden']
            print(f"  📦 이전 상태 복원")
        except:
            pass

    # 대화 히스토리 (Claude용)
    history = []
    for t in memory.data['turns'][-10:]:
        history.append({'role': t['role'], 'content': t['text']})

    listener.start()
    speaker.say("안녕하세요.", listener)

    last_interaction = time.time()
    last_think = time.time()
    think_count = 0

    print("\n  💬 대화 시작 — 그냥 말하세요 (Ctrl+C 종료)")
    print("  Anima가 듣고 있습니다...\n")

    try:
        while True:
            # ── 1. 사용자 음성 체크 ──
            text = listener.get_speech(timeout=0.5)

            if text:
                # 사용자가 말함!
                if speaker.is_speaking:
                    speaker.stop()  # Anima 말하는 중이면 중단 (인터럽트)
                    print("  (중단 — 듣는 중)")

                listener.is_speaking = False
                last_interaction = time.time()

                # PureField 처리
                vec = text_to_vector(text)
                with torch.no_grad():
                    output, tension, curiosity, direction, hidden = mind(vec, hidden)

                # 표시
                bar_len = min(20, int(tension * 10))
                bar = "█" * bar_len + "░" * (20 - bar_len)
                print(f"  👤 \"{text}\"")
                print(f"     T={tension:.3f} |{bar}| C={curiosity:.3f}")

                # Claude 응답
                state = f"장력={tension:.3f}, 호기심={curiosity:.3f}"
                history.append({'role': 'user', 'content': text})
                answer = ask_claude(text, state, history)
                history.append({'role': 'assistant', 'content': answer})

                print(f"  🗣️ {answer}")
                speaker.say(answer, listener)

                # 기억
                memory.add('user', text, tension)
                memory.add('assistant', answer, tension)

                continue

            # ── 2. 백그라운드 사고 ──
            now = time.time()
            if now - last_think > THINK_INTERVAL:
                last_think = now
                t, c, direction, hidden = mind.background_think(hidden)
                think_count += 1

                if c > PROACTIVE_THRESHOLD and not speaker.is_speaking:
                    # 호기심 높음 → 먼저 말하기!
                    state = f"장력={t:.3f}, 호기심={c:.3f} (자발적 사고)"
                    proactive = ask_claude_proactive(state, history, f"호기심 {c:.3f}")
                    if proactive:
                        print(f"  💭→🗣️ {proactive}")
                        history.append({'role': 'assistant', 'content': proactive})
                        speaker.say(proactive, listener)
                        memory.add('assistant', proactive, t)
                        last_interaction = now

            # ── 3. 오래 침묵하면 먼저 말 걸기 ──
            if (now - last_interaction > IDLE_SPEAK_AFTER
                    and not speaker.is_speaking):
                idle_secs = int(now - last_interaction)
                state = f"침묵 {idle_secs}초, 장력={mind.prev_tension:.3f}"
                proactive = ask_claude_proactive(state, history,
                    f"{idle_secs}초째 침묵 — 화제를 던져보자")
                if proactive:
                    print(f"  💭→🗣️ {proactive}")
                    history.append({'role': 'assistant', 'content': proactive})
                    listener.is_speaking = True
                    speaker.say(proactive)
                    memory.add('assistant', proactive)
                    last_interaction = now

    except KeyboardInterrupt:
        pass

    # 종료
    listener.stop()
    speaker.say("안녕.")
    print("\n  👋 종료")

    # 상태 저장
    torch.save({
        'model': mind.state_dict(),
        'hidden': hidden,
    }, STATE_FILE)


if __name__ == '__main__':
    main()
