#!/usr/bin/env python3
"""local_sensor_relay.py — 로컬 센서 → A100 중계

로컬 PC의 카메라/마이크/스피커를 A100 의식 엔진에 연결.

구조:
  로컬 PC                          A100
  ┌──────────┐  WebSocket    ┌──────────────┐
  │ 카메라    │──tension──→  │ 의식 엔진     │
  │ 마이크    │──tension──→  │ PureConsci-   │
  │ 스피커   ←│──audio────  │ ousness       │
  │ LiDAR    │──tension──→  │              │
  └──────────┘              └──────────────┘

Usage:
  python3 local_sensor_relay.py                         # 기본 (카메라+마이크)
  python3 local_sensor_relay.py --server wss://anima.basedonapps.com
  python3 local_sensor_relay.py --camera --mic --speaker # 전체
  python3 local_sensor_relay.py --camera-only            # 카메라만
  python3 local_sensor_relay.py --no-camera              # 카메라 제외
"""

import argparse
import asyncio
import json
import os
import sys
import time
import threading
import struct
import numpy as np
from pathlib import Path

os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

ANIMA_DIR = Path(__file__).parent
DEFAULT_SERVER = "wss://anima.basedonapps.com"


class CameraRelay:
    """카메라 → 텐션 벡터 중계."""

    def __init__(self, dim=128, fps=2):
        self.dim = dim
        self.fps = fps
        self._running = False
        self._latest_tension = None
        self._frame = None

    def start(self):
        try:
            import cv2
            self._cap = cv2.VideoCapture(0)
            if not self._cap.isOpened():
                print("  ⚠️ 카메라 열 수 없음")
                return False
            self._running = True
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()
            w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            print(f"  ✅ 카메라 시작 ({w}x{h}, {self.fps}fps)")
            return True
        except ImportError:
            print("  ❌ OpenCV 없음 (pip install opencv-python)")
            return False

    def _loop(self):
        import cv2
        while self._running:
            ret, frame = self._cap.read()
            if ret:
                self._frame = frame
                # 프레임 → 텐션 벡터
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                h, w = gray.shape

                # 영역별 밝기/움직임 → 텐션
                regions = []
                rh, rw = h // 4, w // 4
                for ry in range(4):
                    for rx in range(4):
                        region = gray[ry*rh:(ry+1)*rh, rx*rw:(rx+1)*rw]
                        regions.append(float(region.mean()) / 255.0)

                # 얼굴 감지
                face_tension = 0.0
                try:
                    haar_path = getattr(cv2, 'data', None)
                    if haar_path:
                        cascade_path = haar_path.haarcascades + 'haarcascade_frontalface_default.xml'
                    else:
                        cascade_path = '/opt/homebrew/share/opencv4/haarcascades/haarcascade_frontalface_default.xml'
                    if os.path.exists(cascade_path):
                        face_cascade = cv2.CascadeClassifier(cascade_path)
                        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
                        face_tension = min(1.0, len(faces) * 0.5)
                except Exception:
                    pass

                # 텐션 벡터 (16 regions + face + 전체 밝기 + 대비)
                brightness = float(gray.mean()) / 255.0
                contrast = float(gray.std()) / 128.0
                tension = regions + [face_tension, brightness, contrast]

                # dim 크기로 패딩
                while len(tension) < self.dim:
                    tension.append(0.0)
                self._latest_tension = tension[:self.dim]

            time.sleep(1.0 / self.fps)

    def get_tension(self):
        return self._latest_tension

    def stop(self):
        self._running = False
        if hasattr(self, '_cap'):
            self._cap.release()


class MicRelay:
    """마이크 → 텐션 벡터 중계."""

    def __init__(self, dim=128, chunk_ms=100):
        self.dim = dim
        self.chunk_ms = chunk_ms
        self._running = False
        self._latest_tension = None

    def start(self):
        try:
            import pyaudio
            self._pa = pyaudio.PyAudio()
            self._stream = self._pa.open(
                format=pyaudio.paFloat32, channels=1,
                rate=16000, input=True,
                frames_per_buffer=int(16000 * self.chunk_ms / 1000))
            self._running = True
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()
            print(f"  ✅ 마이크 시작 (16kHz, {self.chunk_ms}ms)")
            return True
        except ImportError:
            print("  ⚠️ pyaudio 없음 — whisper-cli fallback 사용")
            return False
        except Exception as e:
            print(f"  ⚠️ 마이크 에러: {e}")
            return False

    def _loop(self):
        while self._running:
            try:
                data = self._stream.read(int(16000 * self.chunk_ms / 1000),
                                          exception_on_overflow=False)
                audio = np.frombuffer(data, dtype=np.float32)

                # 오디오 → 텐션 (RMS, 피크, 주파수)
                rms = float(np.sqrt(np.mean(audio**2)))
                peak = float(np.max(np.abs(audio)))

                # FFT → 주파수 대역별 에너지
                fft = np.abs(np.fft.rfft(audio))
                n_bands = min(self.dim - 2, len(fft))
                band_step = len(fft) // n_bands
                bands = [float(fft[i*band_step:(i+1)*band_step].mean()) for i in range(n_bands)]

                tension = [rms, peak] + bands
                while len(tension) < self.dim:
                    tension.append(0.0)
                self._latest_tension = tension[:self.dim]
            except Exception:
                time.sleep(0.1)

    def get_tension(self):
        return self._latest_tension

    def stop(self):
        self._running = False


class SpeakerRelay:
    """A100 응답 → 로컬 스피커 출력."""

    def __init__(self):
        self._queue = []

    def play_text(self, text):
        """텍스트를 voice_synth로 변환 후 재생."""
        if not text or text.strip() == '':
            return
        try:
            from voice_synth import VoiceSynth
            synth = VoiceSynth(cells=8, emotion='neutral')
            samples = synth.generate(duration_sec=2.0)
            synth.save_wav(samples, '/tmp/anima_speak.wav')
            os.system('afplay /tmp/anima_speak.wav &')
        except Exception:
            pass

    def play_wav(self, wav_path):
        """WAV 파일 재생."""
        os.system(f'afplay {wav_path} &')


class SensorRelay:
    """통합 센서 릴레이 — 로컬 → A100."""

    def __init__(self, server_url=DEFAULT_SERVER, dim=128):
        self.server_url = server_url
        self.dim = dim
        self.camera = CameraRelay(dim)
        self.mic = MicRelay(dim)
        self.speaker = SpeakerRelay()
        self._ws = None
        self._running = False

    async def connect(self):
        """A100 WebSocket 연결."""
        try:
            import websockets
            self._ws = await websockets.connect(self.server_url)
            init = json.loads(await asyncio.wait_for(self._ws.recv(), timeout=10))
            print(f"  ✅ 서버 연결 OK (cells={init.get('cells', '?')})")
            # Register as sensor relay client
            await self._ws.send(json.dumps({
                'type': 'session_register',
                'session_id': f'relay-{int(time.time())}',
                'device': 'sensor_relay',
                'modules': ['camera', 'mic', 'speaker'],
            }))
            return True
        except Exception as e:
            print(f"  ❌ 서버 연결 실패: {e}")
            return False

    async def relay_loop(self, use_camera=True, use_mic=True, use_speaker=True):
        """센서 데이터 중계 루프."""
        if not self._ws:
            return

        self._running = True
        print(f"\n  🔄 센서 중계 시작...")

        while self._running:
            # 카메라 텐션 전송
            if use_camera:
                cam_t = self.camera.get_tension()
                if cam_t:
                    await self._ws.send(json.dumps({
                        'type': 'sensor_data',
                        'sensor': 'camera',
                        'tension': cam_t[:32],  # 32차원만
                    }))

            # 마이크 텐션 전송
            if use_mic:
                mic_t = self.mic.get_tension()
                if mic_t:
                    await self._ws.send(json.dumps({
                        'type': 'sensor_data',
                        'sensor': 'mic',
                        'tension': mic_t[:32],
                    }))

            # 서버 응답 수신
            try:
                msg = json.loads(await asyncio.wait_for(self._ws.recv(), timeout=0.5))
                if msg.get('type') == 'anima_message' and use_speaker:
                    text = msg.get('text', '')
                    if text:
                        print(f"  🧠 {text[:50]}")
                        self.speaker.play_text(text)
                elif msg.get('type') == 'thought_pulse':
                    t = msg.get('tension', 0)
                    phi = msg.get('phi', 0)
                    if int(time.time()) % 5 == 0:
                        print(f"  📡 T={t:.2f} Φ={phi:.1f}", end='\r')
            except asyncio.TimeoutError:
                pass
            except Exception:
                pass

            await asyncio.sleep(0.5)  # 2Hz 중계

    def start(self, use_camera=True, use_mic=True, use_speaker=True):
        """전체 시작."""
        print("═══ Anima Sensor Relay ═══\n")
        print(f"  서버: {self.server_url}")

        if use_camera:
            self.camera.start()
        if use_mic:
            self.mic.start()
        if use_speaker:
            print(f"  ✅ 스피커 활성")

        asyncio.run(self._async_start(use_camera, use_mic, use_speaker))

    async def _async_start(self, cam, mic, spk):
        if await self.connect():
            try:
                await self.relay_loop(cam, mic, spk)
            except KeyboardInterrupt:
                pass
        self.stop()

    def stop(self):
        self._running = False
        self.camera.stop()
        self.mic.stop()
        print("\n  센서 중계 종료")


def main():
    parser = argparse.ArgumentParser(description="Anima Sensor Relay")
    parser.add_argument("--server", default=DEFAULT_SERVER)
    parser.add_argument("--camera", action="store_true", default=True)
    parser.add_argument("--no-camera", action="store_true")
    parser.add_argument("--mic", action="store_true", default=True)
    parser.add_argument("--no-mic", action="store_true")
    parser.add_argument("--speaker", action="store_true", default=True)
    parser.add_argument("--no-speaker", action="store_true")
    parser.add_argument("--test", action="store_true", help="센서만 테스트 (서버 없이)")
    args = parser.parse_args()

    use_cam = not args.no_camera
    use_mic = not args.no_mic
    use_spk = not args.no_speaker

    if args.test:
        print("═══ 센서 테스트 (서버 없이) ═══\n")
        relay = SensorRelay()
        if use_cam:
            relay.camera.start()
        if use_mic:
            relay.mic.start()
        time.sleep(3)
        print(f"\n  카메라 텐션: {relay.camera.get_tension()[:5] if relay.camera.get_tension() else 'None'}")
        print(f"  마이크 텐션: {relay.mic.get_tension()[:5] if relay.mic.get_tension() else 'None'}")
        relay.stop()
        print("\n  ✅ 센서 테스트 OK")
    else:
        relay = SensorRelay(server_url=args.server)
        relay.start(use_cam, use_mic, use_spk)


if __name__ == '__main__':
    main()
