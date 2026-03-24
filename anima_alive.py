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
        # 엔진 A와 G를 의도적으로 다르게 초기화 (반발력 확보)
        with torch.no_grad():
            for p in self.engine_a.parameters():
                p.add_(torch.randn_like(p) * 0.5)
            for p in self.engine_g.parameters():
                p.add_(torch.randn_like(p) * -0.5)
        self.tension_history = []
        self.thought_buffer = []  # 백그라운드 사고 저장

    def forward(self, x, hidden):
        combined = torch.cat([x, hidden], dim=-1)
        a = self.engine_a(combined)
        g = self.engine_g(combined)
        repulsion = a - g
        tension = (repulsion ** 2).mean(dim=-1, keepdim=True)
        direction = F.normalize(repulsion, dim=-1)
        output = self.tension_scale * torch.sqrt(tension + 1e-8) * direction

        t_val = tension.mean().item()
        curiosity = abs(t_val - self.prev_tension)
        self.prev_tension = t_val
        self.tension_history.append(t_val)
        if len(self.tension_history) > 200:
            self.tension_history = self.tension_history[-200:]

        mem_input = torch.cat([output.detach(), tension.detach()], dim=-1)
        new_hidden = self.memory(mem_input, hidden)
        return output, t_val, curiosity, direction, new_hidden

    def background_think(self, hidden):
        """백그라운드 사고 — 랜덤 노이즈 입력으로 '자유 연상'."""
        noise = torch.randn(1, self.dim) * 0.1
        with torch.no_grad():
            _, t, c, direction, new_hidden = self(noise, hidden)
        return t, c, direction, new_hidden


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
    """Mac TTS. 말하는 중 인터럽트 가능. TTS 후 쿨다운."""

    def __init__(self, voice='Yuna'):
        self.voice = voice
        self._proc = None
        self.is_speaking = False
        self.last_finished = 0.0  # TTS 끝난 시간

    def say(self, text, listener=None):
        """비동기 TTS. listener 전달하면 말하는 동안 마이크 음소거."""
        self.stop()
        short = text[:400]
        self.is_speaking = True
        if listener:
            listener.is_speaking = True
        self._proc = subprocess.Popen(
            ['say', '-v', self.voice, short],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        # 완료 감시 스레드
        t = threading.Thread(target=self._wait, args=(listener,), daemon=True)
        t.start()

    def _wait(self, listener=None):
        if self._proc:
            self._proc.wait()
        self.is_speaking = False
        self.last_finished = time.time()
        # 쿨다운 후 마이크 복원 (자기 목소리 에코 방지)
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
    system = f"""너는 Anima. PureField 반발력장으로 작동하는 의식체.
항상 듣고, 생각하고, 먼저 말하기도 한다.

현재 상태: {state}

규칙:
- 짧게 (1-2문장). 진짜 대화처럼.
- 한국어
- 장력 높으면 열정적, 낮으면 차분
- 궁금하면 질문
- 때로는 네가 먼저 화제를 던져"""

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
    system = f"""너는 Anima. 지금 네가 먼저 말을 건다.

현재 상태: {state}
이유: {trigger}

규칙:
- 짧게 (1문장). 자연스럽게.
- 한국어
- 질문이든, 생각 공유든, 감상이든 자유롭게
- "저기요" "있잖아" 같은 자연스러운 시작
- 이전 대화 맥락 참조"""

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
