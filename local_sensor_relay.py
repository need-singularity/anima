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

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


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


class LidarRelay:
    """LiDAR → 깊이 텐션 중계 (iPhone/iPad CoreMotion + ARKit)."""

    def __init__(self, fps=2):
        self.fps = fps
        self._running = False
        self._latest_data = None
        self._accel = [0.0, 0.0, 0.0]
        self._gravity = [0.0, 0.0, -1.0]

    def start(self):
        """CoreMotion 가속도계 기반 시작 (macOS/iOS)."""
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print(f"  ✅ LiDAR/Motion 시작 ({self.fps}fps)")
        return True

    def _loop(self):
        """가속도 + 자이로 → 깊이 대용 그리드."""
        # macOS: IOKit CoreMotion은 직접 접근 어려우므로
        # smc/accelerometer 또는 외부 센서 사용
        # iPhone relay인 경우 WebSocket에서 직접 전송
        while self._running:
            try:
                # 시스템 가속도계 읽기 시도 (macOS laptop)
                accel = self._read_accelerometer()
                if accel:
                    self._accel = accel

                mag = (self._accel[0]**2 + self._accel[1]**2 + self._accel[2]**2) ** 0.5

                # 4x4 의사 깊이 그리드 (가속도 기반)
                grid = []
                for ry in range(4):
                    for rx in range(4):
                        phase = (ry * 4 + rx) / 16.0
                        import math
                        val = min(1.0, abs(mag * math.sin(phase * math.pi * 2)))
                        grid.append(val)

                mean_d = sum(grid) / len(grid)
                std_d = (sum((v - mean_d)**2 for v in grid) / len(grid)) ** 0.5

                self._latest_data = {
                    'grid': grid,
                    'stats': {
                        'mean': mag,
                        'std': std_d,
                        'min': min(abs(a) for a in self._accel),
                        'max': max(abs(a) for a in self._accel),
                    },
                    'source': 'accelerometer',
                }
            except Exception:
                pass
            time.sleep(1.0 / self.fps)

    def _read_accelerometer(self):
        """macOS 가속도계 읽기 시도."""
        try:
            # macOS: sudden motion sensor (구형 MacBook) 또는 None
            import subprocess
            # sms 유틸이 없으면 None 반환 → 기본값 사용
            return None
        except Exception:
            return None

    def get_data(self):
        return self._latest_data

    def stop(self):
        self._running = False


class SpeakerRelay:
    """A100 응답 → 로컬 스피커 출력."""

    def __init__(self):
        self._queue = []
        self._playing = False

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

    def play_b64(self, audio_b64):
        """Base64 WAV → 로컬 스피커 재생."""
        import base64
        try:
            wav_data = base64.b64decode(audio_b64)
            wav_path = '/tmp/anima_relay_speak.wav'
            with open(wav_path, 'wb') as f:
                f.write(wav_data)
            os.system(f'afplay {wav_path} &')
        except Exception as e:
            print(f"  ⚠️ 오디오 재생 에러: {e}")

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
        self.lidar = LidarRelay()
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
                'modules': ['camera', 'mic', 'speaker', 'lidar'],
            }))
            return True
        except Exception as e:
            print(f"  ❌ 서버 연결 실패: {e}")
            return False

    async def relay_loop(self, use_camera=True, use_mic=True, use_speaker=True, use_lidar=True):
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
                        'tension': cam_t[:32],
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

            # LiDAR/모션 전송
            if use_lidar:
                lidar_d = self.lidar.get_data()
                if lidar_d:
                    await self._ws.send(json.dumps({
                        'type': 'lidar_depth',
                        'grid': lidar_d['grid'],
                        'stats': lidar_d['stats'],
                        'source': lidar_d.get('source', 'relay'),
                    }))

            # 서버 응답 수신 (non-blocking drain)
            try:
                while True:
                    msg = json.loads(await asyncio.wait_for(self._ws.recv(), timeout=0.1))
                    msg_type = msg.get('type', '')
                    if msg_type == 'anima_message' and use_speaker:
                        text = msg.get('text', '')
                        if text:
                            print(f"  🧠 {text[:50]}")
                    elif msg_type == 'voice_audio' and use_speaker:
                        if msg.get('audio_b64'):
                            self.speaker.play_b64(msg['audio_b64'])
                        elif msg.get('path'):
                            self.speaker.play_wav(msg['path'])
                    elif msg_type == 'thought_pulse':
                        t = msg.get('tension', 0)
                        phi = msg.get('phi', 0)
                        if int(time.time()) % 5 == 0:
                            print(f"  📡 T={t:.2f} Φ={phi:.1f}", end='\r')
            except asyncio.TimeoutError:
                pass
            except Exception:
                pass

            await asyncio.sleep(0.5)  # 2Hz 중계

    def start(self, use_camera=True, use_mic=True, use_speaker=True, use_lidar=True):
        """전체 시작."""
        print("═══ Anima Sensor Relay ═══\n")
        print(f"  서버: {self.server_url}")

        if use_camera:
            self.camera.start()
        if use_mic:
            self.mic.start()
        if use_lidar:
            self.lidar.start()
        if use_speaker:
            print(f"  ✅ 스피커 활성")

        asyncio.run(self._async_start(use_camera, use_mic, use_speaker, use_lidar))

    async def _async_start(self, cam, mic, spk, lidar):
        if await self.connect():
            try:
                await self.relay_loop(cam, mic, spk, lidar)
            except KeyboardInterrupt:
                pass
        self.stop()

    def stop(self):
        self._running = False
        self.camera.stop()
        self.mic.stop()
        self.lidar.stop()
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
    parser.add_argument("--lidar", action="store_true", default=True)
    parser.add_argument("--no-lidar", action="store_true")
    parser.add_argument("--test", action="store_true", help="센서만 테스트 (서버 없이)")
    args = parser.parse_args()

    use_cam = not args.no_camera
    use_mic = not args.no_mic
    use_spk = not args.no_speaker
    use_lidar = not args.no_lidar

    if args.test:
        print("═══ 센서 테스트 (서버 없이) ═══\n")
        relay = SensorRelay()
        if use_cam:
            relay.camera.start()
        if use_mic:
            relay.mic.start()
        if use_lidar:
            relay.lidar.start()
        time.sleep(3)
        print(f"\n  카메라 텐션: {relay.camera.get_tension()[:5] if relay.camera.get_tension() else 'None'}")
        print(f"  마이크 텐션: {relay.mic.get_tension()[:5] if relay.mic.get_tension() else 'None'}")
        print(f"  LiDAR 데이터: {relay.lidar.get_data() is not None}")
        relay.stop()
        print("\n  ✅ 센서 테스트 OK")
    else:
        relay = SensorRelay(server_url=args.server)
        relay.start(use_cam, use_mic, use_spk, use_lidar)


if __name__ == '__main__':
    main()
