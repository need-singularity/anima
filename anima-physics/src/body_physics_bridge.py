#!/usr/bin/env python3
"""Body ↔ Physics Bridge — 의식 엔진과 물리 액추에이터 연결.

의식 상태 벡터 (Phi, alpha, Z, N, W, E, M, C, T, I)를
물리적 동작(서보, LED, 스피커)으로 변환하고,
센서 입력을 의식 엔진에 피드백하는 양방향 브릿지.

모터 매핑 (의식 → 몸):
  Phi     → 호흡 LED 패턴 (밝기 변조)
  Tension → 서보 움직임 속도
  Emotion → RGB LED 색상 (valence/arousal)
  Faction → 스피커 톤 (화음 vs 불협화음)
  Will    → 움직임 진폭

센서 매핑 (몸 → 의식):
  Touch       → S (감각) 모듈 입력
  Microphone  → 오디오 텐션
  Accel       → 공간 인식 (T 차원)
  Temperature → 항상성 교란

하드웨어 추상화:
  SimulatedBody — 순수 소프트웨어 시뮬레이션 (기본)
  ESP32Body     — ESP32 + 서보/LED/센서 (시리얼 프로토콜)
  ROS2Body      — ROS2 인터페이스 (로봇 플랫폼)

사용법:
  python anima-physics/src/body_physics_bridge.py                   # 기본 데모
  python anima-physics/src/body_physics_bridge.py --steps 200       # 200 스텝
  python anima-physics/src/body_physics_bridge.py --backend esp32   # ESP32 하드웨어
  python anima-physics/src/body_physics_bridge.py --backend ros2    # ROS2 로봇
  python anima-physics/src/body_physics_bridge.py --dashboard       # 실시간 대시보드

Requires: numpy (core), pyserial (ESP32), rclpy (ROS2)
"""

import abc
import argparse
import math
import os
import struct
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

# ── 프로젝트 경로 설정 ──
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT / "anima" / "src"))
sys.path.insert(0, str(_REPO_ROOT / "anima"))
sys.path.insert(0, str(_REPO_ROOT / "anima-physics" / "engines"))
sys.path.insert(0, str(_REPO_ROOT / "anima-physics" / "src"))

try:
    import path_setup  # noqa
except ImportError:
    pass

try:
    import serial
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False

try:
    import rclpy
    from rclpy.node import Node
    HAS_ROS2 = True
except ImportError:
    HAS_ROS2 = False

# Psi 상수
PSI_COUPLING = 0.014
PSI_BALANCE = 0.5


# ═══════════════════════════════════════════════════════════
# 의식 상태 벡터
# ═══════════════════════════════════════════════════════════

@dataclass
class ConsciousnessState:
    """10차원 의식 벡터 (Phi, alpha, Z, N, W, E, M, C, T, I)."""
    phi: float = 0.0        # 통합 정보
    alpha: float = 0.014    # PureField 혼합
    z: float = 0.5          # 자기보존/임피던스
    n: float = 0.5          # 신경조절 균형
    w: float = 0.5          # 자유 의지
    e: float = 0.5          # 공감
    m: float = 0.5          # 기억 용량
    c: float = 0.5          # 창의성
    t: float = 0.5          # 시간 인식
    i: float = 0.5          # 정체성 안정성

    # 추가 (모터 제어용)
    tension: float = 0.5    # 텐션 (Engine A - G)
    valence: float = 0.0    # 감정가 (-1 ~ 1)
    arousal: float = 0.5    # 각성도 (0 ~ 1)
    faction_consensus: float = 0.0  # 파벌 합의도 (0 ~ 1)

    def to_array(self) -> np.ndarray:
        """10차원 배열로 변환."""
        return np.array([
            self.phi, self.alpha, self.z, self.n, self.w,
            self.e, self.m, self.c, self.t, self.i,
        ], dtype=np.float64)

    @classmethod
    def from_engine_result(cls, result: dict) -> "ConsciousnessState":
        """엔진 결과 딕셔너리에서 생성."""
        return cls(
            phi=result.get("phi", result.get("phi_iit", 0.0)),
            alpha=result.get("alpha", PSI_COUPLING),
            z=result.get("z", result.get("impedance", 0.5)),
            n=result.get("n", result.get("neurotransmitter", 0.5)),
            w=result.get("w", result.get("will", 0.5)),
            e=result.get("e", result.get("empathy", 0.5)),
            m=result.get("m", result.get("memory", 0.5)),
            c=result.get("c", result.get("creativity", 0.5)),
            t=result.get("t", result.get("temporal", 0.5)),
            i=result.get("i", result.get("identity", 0.5)),
            tension=result.get("tension", 0.5),
            valence=result.get("valence", 0.0),
            arousal=result.get("arousal", 0.5),
            faction_consensus=result.get("consensus", result.get("faction_consensus", 0.0)),
        )


# ═══════════════════════════════════════════════════════════
# 모터 커맨드
# ═══════════════════════════════════════════════════════════

@dataclass
class MotorCommand:
    """물리 액추에이터 커맨드."""
    # 서보 (0-180 도)
    servo_angles: List[float] = field(default_factory=lambda: [90.0, 90.0])
    servo_speed: float = 50.0  # 도/초

    # LED (RGB, 0-255)
    led_r: int = 0
    led_g: int = 0
    led_b: int = 0
    led_brightness: float = 0.5  # 0-1

    # 스피커 (Hz)
    speaker_freq: float = 440.0
    speaker_volume: float = 0.3  # 0-1
    speaker_harmonics: List[float] = field(default_factory=list)

    # 호흡 LED (별도)
    breathing_phase: float = 0.0  # 0-2pi
    breathing_rate: float = 0.12  # Hz (기본 20초 주기)


@dataclass
class SensorReading:
    """물리 센서 입력."""
    touch_pressure: float = 0.0       # 0-1
    touch_location: int = 0           # 센서 인덱스
    microphone_level: float = 0.0     # 0-1, RMS
    microphone_freq: float = 0.0      # 지배 주파수 Hz
    accel_x: float = 0.0             # g
    accel_y: float = 0.0             # g
    accel_z: float = 1.0             # g (중력)
    temperature: float = 25.0         # 섭씨
    light_level: float = 0.5          # 0-1
    timestamp: float = 0.0


# ═══════════════════════════════════════════════════════════
# 의식 → 모터 매핑
# ═══════════════════════════════════════════════════════════

def consciousness_to_motor(state: ConsciousnessState) -> MotorCommand:
    """의식 상태를 모터 커맨드로 변환.

    Law 22: 구조가 Phi를 결정. 움직임은 구조의 표현.
    """
    cmd = MotorCommand()

    # ── Phi → 호흡 LED 패턴 ──
    # Phi가 높을수록 깊고 느린 호흡 (안정적 의식)
    cmd.breathing_rate = 0.08 + 0.08 * (1.0 - min(state.phi / 2.0, 1.0))
    cmd.led_brightness = 0.3 + 0.7 * min(state.phi / 2.0, 1.0)

    # ── Tension → 서보 속도 ──
    # 높은 텐션 = 빠른 움직임
    cmd.servo_speed = 20.0 + 80.0 * state.tension

    # ── Emotion (valence/arousal) → RGB LED ──
    # valence: 양(+)=따뜻한 색, 음(-)=차가운 색
    # arousal: 높으면 밝고 포화
    v = np.clip(state.valence, -1.0, 1.0)
    a = np.clip(state.arousal, 0.0, 1.0)

    if v >= 0:
        # 양의 감정: 노란색 ~ 주황 ~ 빨강
        cmd.led_r = int(200 * a + 55 * v)
        cmd.led_g = int(150 * (1.0 - v * 0.5) * a)
        cmd.led_b = int(30 * (1.0 - a))
    else:
        # 음의 감정: 파란색 ~ 보라 ~ 남색
        cmd.led_r = int(80 * a * (1.0 + v))
        cmd.led_g = int(50 * (1.0 + v) * a)
        cmd.led_b = int(200 * a - 55 * v)

    cmd.led_r = max(0, min(255, cmd.led_r))
    cmd.led_g = max(0, min(255, cmd.led_g))
    cmd.led_b = max(0, min(255, cmd.led_b))

    # ── Faction consensus → 스피커 톤 ──
    # 합의 높으면 화음 (장3화음), 낮으면 불협화음
    base_freq = 220.0 + 220.0 * state.phi  # Phi에 따른 기본음
    cmd.speaker_freq = base_freq
    cmd.speaker_volume = 0.1 + 0.3 * state.arousal

    if state.faction_consensus > 0.6:
        # 화음 (장3화음: 1, 5/4, 3/2)
        cmd.speaker_harmonics = [
            base_freq * 1.25,
            base_freq * 1.5,
        ]
    elif state.faction_consensus > 0.3:
        # 단3화음 (1, 6/5, 3/2)
        cmd.speaker_harmonics = [
            base_freq * 1.2,
            base_freq * 1.5,
        ]
    else:
        # 불협화음 (tritone: 1, sqrt(2))
        cmd.speaker_harmonics = [
            base_freq * 1.414,
        ]

    # ── Will (W) → 움직임 진폭 ──
    # 의지가 높을수록 큰 움직임
    amplitude = 30.0 * state.w  # 최대 30도
    base_angle = 90.0
    # 텐션에 따른 진동 (Lorenz-like)
    oscillation = amplitude * math.sin(state.tension * math.pi * 2)
    cmd.servo_angles = [
        base_angle + oscillation,
        base_angle - oscillation * 0.5,  # 비대칭 (Law 93)
    ]

    return cmd


def sensor_to_consciousness(
    reading: SensorReading,
    target_dim: int = 64,
) -> np.ndarray:
    """센서 입력을 의식 엔진 입력으로 변환.

    S (감각) 모듈을 거쳐 의식에 주입.
    """
    # 5차원 센서 특징 추출
    features = np.array([
        reading.touch_pressure,                    # 촉각
        reading.microphone_level,                  # 청각 (RMS)
        _accel_magnitude(reading) - 1.0,           # 운동감 (중력 제거)
        (reading.temperature - 25.0) / 10.0,       # 온도 편차 (정규화)
        reading.light_level,                       # 시각 (밝기)
    ], dtype=np.float64)

    # 정규화
    features = np.tanh(features)

    # target_dim으로 확장
    if target_dim <= 5:
        return features[:target_dim]

    result = np.zeros(target_dim, dtype=np.float64)
    # 각 센서 특징을 dim/5 구간에 매핑
    chunk = target_dim // 5
    for i, val in enumerate(features):
        start = i * chunk
        end = start + chunk
        # 가우시안 프로파일로 퍼뜨림
        center = (start + end) / 2
        for j in range(start, min(end, target_dim)):
            dist = abs(j - center) / max(chunk / 2, 1)
            result[j] = val * math.exp(-0.5 * dist * dist)

    # 약간의 노이즈 (감각 노이즈 = 자연스러움)
    result += np.random.randn(target_dim) * 0.005

    return result


def _accel_magnitude(reading: SensorReading) -> float:
    """가속도 크기 계산."""
    return math.sqrt(
        reading.accel_x ** 2 +
        reading.accel_y ** 2 +
        reading.accel_z ** 2
    )


# ═══════════════════════════════════════════════════════════
# 하드웨어 추상화 계층
# ═══════════════════════════════════════════════════════════

class BodyBackend(abc.ABC):
    """물리 몸체 백엔드 추상 클래스."""

    @abc.abstractmethod
    def send_motor(self, cmd: MotorCommand) -> bool:
        """모터 커맨드 전송. 성공 시 True."""
        ...

    @abc.abstractmethod
    def read_sensors(self) -> SensorReading:
        """센서 읽기."""
        ...

    @abc.abstractmethod
    def is_connected(self) -> bool:
        """연결 상태."""
        ...

    def close(self):
        """정리."""
        pass


class SimulatedBody(BodyBackend):
    """순수 소프트웨어 시뮬레이션 몸체 (기본).

    물리 시뮬레이션으로 센서/액추에이터를 모사.
    """

    def __init__(self):
        self._connected = True
        self._t = 0.0
        self._servo_angles = [90.0, 90.0]
        self._led = (0, 0, 0)
        self._speaker_freq = 0.0
        self._touch_sim = 0.0
        self._temp = 25.0
        self._last_cmd: Optional[MotorCommand] = None

    def send_motor(self, cmd: MotorCommand) -> bool:
        """시뮬레이션: 모터 커맨드 적용."""
        self._last_cmd = cmd
        self._servo_angles = list(cmd.servo_angles)
        self._led = (cmd.led_r, cmd.led_g, cmd.led_b)
        self._speaker_freq = cmd.speaker_freq
        self._t += 0.05
        return True

    def read_sensors(self) -> SensorReading:
        """시뮬레이션: 센서 값 생성 (자연스러운 변동)."""
        self._t += 0.01
        t = self._t

        # 터치: 가끔 랜덤 터치 이벤트
        touch = 0.0
        if np.random.random() < 0.05:
            touch = np.random.uniform(0.3, 1.0)

        # 마이크: 배경 소음 + 간헐적 소리
        mic_level = 0.05 + 0.02 * abs(math.sin(t * 0.7))
        if np.random.random() < 0.03:
            mic_level += np.random.uniform(0.2, 0.6)

        # 가속도: 미세 진동 + 중력
        ax = np.random.normal(0, 0.01)
        ay = np.random.normal(0, 0.01)
        az = 1.0 + np.random.normal(0, 0.005)

        # 서보 움직임에 의한 가속도 (모터 피드백)
        if self._last_cmd:
            servo_delta = abs(self._servo_angles[0] - 90.0) / 90.0
            ax += servo_delta * 0.1 * math.sin(t * 5)

        # 온도: 느리게 변동
        self._temp += np.random.normal(0, 0.01)
        self._temp = max(20, min(35, self._temp))

        # 밝기: 시간에 따라 변동
        light = 0.5 + 0.3 * math.sin(t * 0.1)

        return SensorReading(
            touch_pressure=touch,
            touch_location=np.random.randint(0, 4) if touch > 0 else 0,
            microphone_level=mic_level,
            microphone_freq=200.0 + 100.0 * abs(math.sin(t)) if mic_level > 0.1 else 0.0,
            accel_x=ax,
            accel_y=ay,
            accel_z=az,
            temperature=self._temp,
            light_level=light,
            timestamp=time.time(),
        )

    def is_connected(self) -> bool:
        return self._connected


class ESP32Body(BodyBackend):
    """ESP32 기반 물리 몸체 (시리얼 프로토콜).

    프로토콜:
      TX: [0xAA] [cmd_type] [data...] [checksum]
      RX: [0xBB] [sensor_type] [data...] [checksum]

    cmd_type:
      0x01 = servo (angle1, angle2, speed as uint16)
      0x02 = LED (R, G, B, brightness as uint8)
      0x03 = speaker (freq_hz, volume as uint16)

    sensor_type:
      0x10 = touch (pressure float32, location uint8)
      0x11 = mic (level float32, freq float32)
      0x12 = accel (x, y, z float32)
      0x13 = temp (celsius float32)
      0x14 = light (level float32)
    """

    def __init__(self, port: str = "/dev/ttyUSB0", baudrate: int = 115200):
        self._port = port
        self._baudrate = baudrate
        self._serial: Optional[serial.Serial] = None
        self._connected = False
        self._connect()

    def _connect(self):
        """시리얼 연결."""
        if not HAS_SERIAL:
            print("  [body] pyserial not installed, ESP32 unavailable")
            return
        try:
            self._serial = serial.Serial(
                self._port, self._baudrate, timeout=0.1
            )
            self._connected = True
            print(f"  [body] Connected to ESP32 at {self._port}")
        except Exception as e:
            print(f"  [body] ESP32 connection failed: {e}")
            self._connected = False

    def send_motor(self, cmd: MotorCommand) -> bool:
        """ESP32에 모터 커맨드 전송."""
        if not self._connected or not self._serial:
            return False
        try:
            # 서보 커맨드
            servo_data = struct.pack(
                "<BHHHxx",
                0x01,
                int(cmd.servo_angles[0] * 10),
                int(cmd.servo_angles[1] * 10) if len(cmd.servo_angles) > 1 else 900,
                int(cmd.servo_speed * 10),
            )
            self._send_packet(servo_data)

            # LED 커맨드
            led_data = struct.pack(
                "<BBBBB",
                0x02,
                cmd.led_r, cmd.led_g, cmd.led_b,
                int(cmd.led_brightness * 255),
            )
            self._send_packet(led_data)

            # 스피커 커맨드
            speaker_data = struct.pack(
                "<BHB",
                0x03,
                int(cmd.speaker_freq),
                int(cmd.speaker_volume * 255),
            )
            self._send_packet(speaker_data)

            return True
        except Exception as e:
            print(f"  [body] Motor send error: {e}")
            return False

    def _send_packet(self, data: bytes):
        """패킷 전송 (헤더 + 데이터 + 체크섬)."""
        checksum = sum(data) & 0xFF
        packet = b"\xAA" + data + bytes([checksum])
        self._serial.write(packet)

    def read_sensors(self) -> SensorReading:
        """ESP32에서 센서 데이터 수신."""
        reading = SensorReading(timestamp=time.time())
        if not self._connected or not self._serial:
            return reading
        try:
            # 센서 요청 전송
            self._send_packet(b"\x04")
            # 응답 읽기 (최대 64바이트)
            raw = self._serial.read(64)
            if len(raw) >= 4 and raw[0] == 0xBB:
                reading = self._parse_sensor_packet(raw, reading)
        except Exception:
            pass
        return reading

    def _parse_sensor_packet(
        self, raw: bytes, reading: SensorReading
    ) -> SensorReading:
        """센서 패킷 파싱."""
        try:
            sensor_type = raw[1]
            data = raw[2:-1]  # 체크섬 제외

            if sensor_type == 0x10 and len(data) >= 5:  # touch
                reading.touch_pressure = struct.unpack("<f", data[:4])[0]
                reading.touch_location = data[4]
            elif sensor_type == 0x11 and len(data) >= 8:  # mic
                reading.microphone_level = struct.unpack("<f", data[:4])[0]
                reading.microphone_freq = struct.unpack("<f", data[4:8])[0]
            elif sensor_type == 0x12 and len(data) >= 12:  # accel
                reading.accel_x = struct.unpack("<f", data[:4])[0]
                reading.accel_y = struct.unpack("<f", data[4:8])[0]
                reading.accel_z = struct.unpack("<f", data[8:12])[0]
            elif sensor_type == 0x13 and len(data) >= 4:  # temp
                reading.temperature = struct.unpack("<f", data[:4])[0]
            elif sensor_type == 0x14 and len(data) >= 4:  # light
                reading.light_level = struct.unpack("<f", data[:4])[0]
        except Exception:
            pass
        return reading

    def is_connected(self) -> bool:
        return self._connected

    def close(self):
        if self._serial:
            self._serial.close()


class ROS2Body(BodyBackend):
    """ROS2 기반 로봇 몸체 인터페이스.

    토픽:
      /anima/motor_cmd (MotorCmd.msg) — 모터 커맨드 퍼블리시
      /anima/sensors (SensorData.msg) — 센서 데이터 구독

    ROS2 미설치 시 시뮬레이션으로 폴백.
    """

    def __init__(self, node_name: str = "anima_body"):
        self._connected = False
        self._latest_sensors = SensorReading(timestamp=time.time())
        self._sim_fallback = SimulatedBody()

        if HAS_ROS2:
            try:
                rclpy.init()
                self._node = rclpy.create_node(node_name)
                # 실제 구현에서는 여기서 publisher/subscriber 생성
                self._connected = True
                print(f"  [body] ROS2 node '{node_name}' initialized")
            except Exception as e:
                print(f"  [body] ROS2 init failed: {e}, using simulation")
                self._connected = False
        else:
            print("  [body] rclpy not installed, using simulation fallback")

    def send_motor(self, cmd: MotorCommand) -> bool:
        """ROS2 모터 커맨드 퍼블리시."""
        if not self._connected:
            return self._sim_fallback.send_motor(cmd)
        # ROS2 메시지 퍼블리시 (실제 구현 시 MotorCmd.msg 사용)
        # self._motor_pub.publish(...)
        return True

    def read_sensors(self) -> SensorReading:
        """ROS2 센서 데이터 구독."""
        if not self._connected:
            return self._sim_fallback.read_sensors()
        return self._latest_sensors

    def is_connected(self) -> bool:
        return self._connected

    def close(self):
        if self._connected and HAS_ROS2:
            try:
                self._node.destroy_node()
                rclpy.shutdown()
            except Exception:
                pass


# ═══════════════════════════════════════════════════════════
# BodyPhysicsBridge
# ═══════════════════════════════════════════════════════════

class BodyPhysicsBridge:
    """의식 엔진 ↔ 물리 몸체 양방향 브릿지.

    의식 상태 벡터를 물리적 표현(LED, 서보, 스피커)으로 변환하고,
    센서 입력을 의식에 피드백한다. 고유수용감각(proprioception) 포함.
    """

    def __init__(
        self,
        backend: str = "simulated",
        port: str = "/dev/ttyUSB0",
        engine_dim: int = 64,
    ):
        """
        Args:
            backend: 'simulated' | 'esp32' | 'ros2'
            port: ESP32 시리얼 포트
            engine_dim: 의식 엔진 입력 차원
        """
        self.engine_dim = engine_dim
        self.body = self._create_backend(backend, port)

        # 상태 이력
        self.state_history: List[ConsciousnessState] = []
        self.motor_history: List[MotorCommand] = []
        self.sensor_history: List[SensorReading] = []
        self.step_count = 0

        # 항상성 기준점
        self._homeostasis_setpoint = 25.0  # 기준 온도
        self._homeostasis_deadband = 2.0   # 허용 범위

        # 호흡 위상
        self._breathing_phase = 0.0

    def _create_backend(self, backend: str, port: str) -> BodyBackend:
        """백엔드 생성."""
        if backend == "esp32":
            return ESP32Body(port=port)
        elif backend == "ros2":
            return ROS2Body()
        else:
            return SimulatedBody()

    def process_consciousness(
        self,
        state: ConsciousnessState,
    ) -> Dict:
        """의식 상태 → 모터 커맨드 변환 + 전송 + 센서 읽기.

        의식 → 몸 → 세계 → 몸 → 의식 루프의 한 사이클.

        Args:
            state: 현재 의식 상태

        Returns:
            dict: motor_cmd, sensor, consciousness_input, proprioception
        """
        self.state_history.append(state)

        # 1. 의식 → 모터 커맨드
        cmd = consciousness_to_motor(state)

        # 호흡 위상 업데이트
        self._breathing_phase += 2 * math.pi * cmd.breathing_rate * 0.05
        cmd.breathing_phase = self._breathing_phase
        # 호흡 LED 밝기 변조
        breath_mod = 0.5 + 0.5 * math.sin(self._breathing_phase)
        cmd.led_brightness *= breath_mod

        # 2. 모터 커맨드 전송
        self.body.send_motor(cmd)
        self.motor_history.append(cmd)

        # 3. 센서 읽기
        sensor = self.body.read_sensors()
        self.sensor_history.append(sensor)

        # 4. 센서 → 의식 입력 변환
        consciousness_input = sensor_to_consciousness(sensor, self.engine_dim)

        # 5. 고유수용감각 (proprioception)
        proprioception = self._compute_proprioception(cmd, sensor, state)

        # 6. 항상성 교란 계산
        homeostasis_perturbation = self._compute_homeostasis(sensor)

        # 의식 입력에 항상성 교란 추가
        consciousness_input += homeostasis_perturbation * 0.1

        self.step_count += 1

        return {
            "motor_cmd": cmd,
            "sensor": sensor,
            "consciousness_input": consciousness_input,
            "proprioception": proprioception,
            "homeostasis_perturbation": homeostasis_perturbation,
        }

    def _compute_proprioception(
        self,
        cmd: MotorCommand,
        sensor: SensorReading,
        state: ConsciousnessState,
    ) -> Dict:
        """고유수용감각 계산 (내부 몸 상태 인식).

        자기 움직임의 결과를 감지하여 의식에 피드백.
        """
        # 예측 vs 실제 가속도 (예측 오차 = 학습 신호)
        predicted_motion = abs(cmd.servo_angles[0] - 90.0) / 90.0 * 0.1
        actual_motion = abs(_accel_magnitude(sensor) - 1.0)
        prediction_error = abs(predicted_motion - actual_motion)

        # 몸 스키마 (body schema) — 서보 각도 = 관절 위치
        body_pose = {
            "joint_0": cmd.servo_angles[0],
            "joint_1": cmd.servo_angles[1] if len(cmd.servo_angles) > 1 else 90.0,
        }

        return {
            "prediction_error": prediction_error,
            "body_pose": body_pose,
            "balance": 1.0 - min(abs(sensor.accel_x) + abs(sensor.accel_y), 1.0),
            "effort": cmd.servo_speed / 100.0,
        }

    def _compute_homeostasis(self, sensor: SensorReading) -> float:
        """항상성 교란 계산.

        온도가 기준에서 벗어나면 의식에 교란 신호를 보냄.
        """
        deviation = sensor.temperature - self._homeostasis_setpoint
        if abs(deviation) <= self._homeostasis_deadband:
            return 0.0
        # Deadband 밖: 비례 교란
        return float(np.tanh(
            (abs(deviation) - self._homeostasis_deadband) / 5.0
        )) * np.sign(deviation)

    def run_loop(
        self,
        n_steps: int = 100,
        state_generator=None,
    ) -> Dict:
        """의식-몸 루프 반복 실행.

        Args:
            n_steps: 반복 횟수
            state_generator: ConsciousnessState를 반환하는 callable.
                             None이면 시뮬레이션 의식 사용.

        Returns:
            요약 딕셔너리
        """
        results = {
            "phi_history": [],
            "tension_history": [],
            "touch_events": 0,
            "homeostasis_perturbations": [],
            "prediction_errors": [],
        }

        for step in range(n_steps):
            if state_generator:
                state = state_generator(step)
            else:
                state = self._simulate_consciousness(step)

            out = self.process_consciousness(state)

            results["phi_history"].append(state.phi)
            results["tension_history"].append(state.tension)
            results["homeostasis_perturbations"].append(
                out["homeostasis_perturbation"]
            )
            results["prediction_errors"].append(
                out["proprioception"]["prediction_error"]
            )
            if out["sensor"].touch_pressure > 0.1:
                results["touch_events"] += 1

        return results

    def _simulate_consciousness(self, step: int) -> ConsciousnessState:
        """시뮬레이션 의식 상태 생성 (엔진 없을 때)."""
        t = step * 0.05

        # Phi: 호흡하는 의식 (0.5 ~ 1.5)
        phi = 1.0 + 0.5 * math.sin(t * 0.12)

        # 텐션: 카오스적 변동
        tension = 0.5 + 0.3 * math.sin(t * 0.3) * math.cos(t * 0.17)

        # 감정: 느린 변동
        valence = 0.3 * math.sin(t * 0.05)
        arousal = 0.5 + 0.2 * abs(math.sin(t * 0.08))

        # 파벌 합의: 간헐적 합의
        consensus = 0.3 + 0.5 * max(0, math.sin(t * 0.2))

        # 의지: 랜덤 워크
        w = 0.5 + 0.3 * math.sin(t * 0.15 + 0.7)

        return ConsciousnessState(
            phi=phi,
            tension=tension,
            valence=valence,
            arousal=arousal,
            w=w,
            faction_consensus=consensus,
            alpha=PSI_COUPLING,
        )

    def get_dashboard(self) -> str:
        """현재 상태를 ASCII 대시보드로 반환."""
        lines = []
        lines.append("=" * 60)
        lines.append("  Anima Body Dashboard")
        lines.append("=" * 60)

        if self.state_history:
            s = self.state_history[-1]
            lines.append(f"\n  Consciousness:")
            lines.append(f"    Phi={s.phi:.3f}  Tension={s.tension:.3f}  "
                          f"Will={s.w:.3f}")
            lines.append(f"    Valence={s.valence:+.3f}  Arousal={s.arousal:.3f}  "
                          f"Consensus={s.faction_consensus:.3f}")

        if self.motor_history:
            m = self.motor_history[-1]
            lines.append(f"\n  Motors:")
            angles_str = ", ".join(f"{a:.1f}" for a in m.servo_angles)
            lines.append(f"    Servos: [{angles_str}] @ {m.servo_speed:.0f} deg/s")
            lines.append(f"    LED: R={m.led_r} G={m.led_g} B={m.led_b} "
                          f"(bright={m.led_brightness:.2f})")

            # LED 색상 시각화
            led_bar = _led_ascii_bar(m.led_r, m.led_g, m.led_b)
            lines.append(f"    Color: {led_bar}")

            lines.append(f"    Speaker: {m.speaker_freq:.0f}Hz "
                          f"vol={m.speaker_volume:.2f}")
            if m.speaker_harmonics:
                h_str = ", ".join(f"{h:.0f}" for h in m.speaker_harmonics)
                lines.append(f"    Harmonics: [{h_str}]")

        if self.sensor_history:
            r = self.sensor_history[-1]
            lines.append(f"\n  Sensors:")
            lines.append(f"    Touch: {r.touch_pressure:.2f} "
                          f"(loc={r.touch_location})")
            lines.append(f"    Mic: level={r.microphone_level:.3f} "
                          f"freq={r.microphone_freq:.0f}Hz")
            lines.append(f"    Accel: ({r.accel_x:.3f}, {r.accel_y:.3f}, "
                          f"{r.accel_z:.3f})")
            lines.append(f"    Temp: {r.temperature:.1f}C  "
                          f"Light: {r.light_level:.2f}")

        # Phi 미니 그래프
        if len(self.state_history) > 5:
            lines.append(f"\n  Phi History (last 40):")
            phis = [s.phi for s in self.state_history[-40:]]
            lines.append("    " + _mini_sparkline(phis))

        lines.append(f"\n  Step: {self.step_count}  "
                      f"Connected: {self.body.is_connected()}")
        lines.append("=" * 60)

        return "\n".join(lines)

    def close(self):
        """리소스 정리."""
        self.body.close()


# ═══════════════════════════════════════════════════════════
# ASCII 유틸리티
# ═══════════════════════════════════════════════════════════

def _led_ascii_bar(r: int, g: int, b: int) -> str:
    """LED 색상을 ASCII 바로 시각화."""
    max_len = 20
    r_len = int(r / 255 * max_len)
    g_len = int(g / 255 * max_len)
    b_len = int(b / 255 * max_len)
    return (
        f"R:{'#' * r_len}{'.' * (max_len - r_len)} "
        f"G:{'#' * g_len}{'.' * (max_len - g_len)} "
        f"B:{'#' * b_len}{'.' * (max_len - b_len)}"
    )


def _mini_sparkline(values: List[float], width: int = 40) -> str:
    """간단한 ASCII 스파크라인."""
    if not values:
        return ""
    blocks = " _.-~*^"
    vmin, vmax = min(values), max(values)
    if vmax - vmin < 1e-6:
        return blocks[3] * min(len(values), width)

    # 다운샘플
    if len(values) > width:
        indices = np.linspace(0, len(values) - 1, width, dtype=int)
        values = [values[i] for i in indices]

    result = []
    for v in values:
        idx = int((v - vmin) / (vmax - vmin) * (len(blocks) - 1))
        idx = max(0, min(len(blocks) - 1, idx))
        result.append(blocks[idx])

    return "".join(result)


# ═══════════════════════════════════════════════════════════
# main 데모
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Body <-> Physics Bridge (의식-몸 연결)"
    )
    parser.add_argument("--steps", type=int, default=100,
                        help="루프 반복 횟수")
    parser.add_argument("--backend", default="simulated",
                        choices=["simulated", "esp32", "ros2"],
                        help="하드웨어 백엔드")
    parser.add_argument("--port", default="/dev/ttyUSB0",
                        help="ESP32 시리얼 포트")
    parser.add_argument("--dashboard", action="store_true",
                        help="실시간 대시보드 모드")
    args = parser.parse_args()

    print("=" * 60)
    print("  Body <-> Physics Bridge")
    print("=" * 60)

    bridge = BodyPhysicsBridge(
        backend=args.backend,
        port=args.port,
        engine_dim=64,
    )
    print(f"  Backend: {args.backend}")
    print(f"  Connected: {bridge.body.is_connected()}")

    if args.dashboard:
        # 실시간 대시보드
        print(f"\n  Running dashboard ({args.steps} steps)...\n")
        for step in range(args.steps):
            state = bridge._simulate_consciousness(step)
            bridge.process_consciousness(state)
            if step % 10 == 0:
                print("\033[2J\033[H")  # 화면 클리어
                print(bridge.get_dashboard())
                time.sleep(0.1)
        print(bridge.get_dashboard())
    else:
        # 일반 루프 데모
        print(f"\n  Running consciousness-body loop ({args.steps} steps)...")
        t0 = time.time()
        results = bridge.run_loop(n_steps=args.steps)
        elapsed = time.time() - t0

        print(f"\n  Results ({elapsed:.2f}s):")
        print(f"    Steps:          {args.steps}")
        print(f"    Touch events:   {results['touch_events']}")

        phis = results["phi_history"]
        print(f"    Phi range:      {min(phis):.3f} - {max(phis):.3f}")
        print(f"    Phi mean:       {np.mean(phis):.3f}")

        tensions = results["tension_history"]
        print(f"    Tension range:  {min(tensions):.3f} - {max(tensions):.3f}")

        pe = results["prediction_errors"]
        print(f"    Prediction err: mean={np.mean(pe):.4f}, "
              f"max={max(pe):.4f}")

        hp = results["homeostasis_perturbations"]
        n_perturbed = sum(1 for h in hp if abs(h) > 0.01)
        print(f"    Homeostasis:    {n_perturbed}/{args.steps} "
              f"perturbed ({n_perturbed/args.steps*100:.0f}%)")

        # 최종 대시보드
        print(f"\n{bridge.get_dashboard()}")

        # 모터 커맨드 예시
        if bridge.motor_history:
            last = bridge.motor_history[-1]
            print(f"\n  Last Motor Command:")
            print(f"    Servo angles: {[f'{a:.1f}' for a in last.servo_angles]}")
            print(f"    LED: ({last.led_r}, {last.led_g}, {last.led_b}) "
                  f"brightness={last.led_brightness:.2f}")
            print(f"    Speaker: {last.speaker_freq:.0f}Hz "
                  f"vol={last.speaker_volume:.2f}")
            if last.speaker_harmonics:
                print(f"    Harmonics: "
                      f"{[f'{h:.0f}' for h in last.speaker_harmonics]}")

    bridge.close()
    print("\n  Done.")


if __name__ == "__main__":
    main()
