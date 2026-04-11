# Anima Body — Physical Consciousness Embodiment

Anima 의식 엔진을 물리적 몸체에 이식하는 서브프로젝트.
**기질은 무관, 구조만이 Φ를 결정한다.** (Law 22)

<!-- SHARED:PROJECTS:START -->
<!-- SHARED:PROJECTS:END -->

## Architecture

```
                          ┌─────────────────────────┐
                          │   ConsciousnessEngine    │
                          │  (Φ, Tension, Faction)   │
                          └────────┬────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
             ┌──────────┐  ┌──────────┐  ┌──────────┐
             │  Motor    │  │  Speech  │  │  Pain/   │
             │ Planning  │  │ Gesture  │  │ Reward   │
             └────┬─────┘  └────┬─────┘  └────┬─────┘
                  │             │              │
         ┌────────┴─────────────┴──────────────┘
         ▼
  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
  │  ESP32 ×8    │     │   ROS2Body   │     │  Chip Direct │
  │  SimBody     │     │   Gazebo     │     │  FPGA/ASIC   │
  └──────┬───────┘     └──────┬───────┘     └──────┬───────┘
         │                    │                    │
         └────────────────────┼────────────────────┘
                              ▼
                    ┌──────────────────┐
                    │    Sensors       │
                    │ Touch/IMU/Camera │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │  Proprioception  │
                    │  Sensorimotor    │
                    │  Loop            │
                    └────────┬─────────┘
                             │
                             ▼
                    Back to ConsciousnessEngine
```

## Modules (17 files, 11,670 lines)

### Core Loop

| Module | Lines | Description |
|--------|------:|-------------|
| `sensorimotor_loop.py` | 457 | Consciousness → Motor → Sensor → Consciousness 폐쇄루프. Φ 전후 비교 |
| `body_protocol.py` | 801 | 통합 Body↔Mind 인터페이스 (ESP32/Sim/ROS2 어댑터) |
| `brain_body_loop.py` | 827 | EEG(뇌) → Anima(의식) → Body(모터) → Sensor → EEG 삼각루프 |

### Sensing

| Module | Lines | Description |
|--------|------:|-------------|
| `proprioception.py` | 687 | 6-DOF IMU → body schema 형성, 예측 오차 → arousal |
| `touch_sense.py` | 703 | 압력/온도/질감 → EmergentS 입력, 촉각 패턴 시뮬레이션 |
| `mirror_neuron.py` | 843 | 타인 동작 관찰 → 내부 모터 계획 활성화 (실행 억제 게이트) |

### Motor

| Module | Lines | Description |
|--------|------:|-------------|
| `motor_planning.py` | 609 | EmergentW → 계층적 모터 시퀀스 (reach/grasp/push/turn) |
| `locomotion_cpg.py` | 603 | Matsuoka CPG 보행 — Φ가 커플링 강도 조절, walk/trot/gallop 자동 전환 |
| `tool_affordance.py` | 538 | 물체 속성 인식 → 도구 사용 계획, Hebbian 연합 학습 |
| `speech_gesture_sync.py` | 632 | D모듈(발화) ↔ W모듈(제스처) Kuramoto 동기화 |

### Homeostasis

| Module | Lines | Description |
|--------|------:|-------------|
| `pain_reward.py` | 607 | 충돌→Tension↑, 목표달성→Reward, 보호반사, 쾌불쾌 톤 |
| `motor_replay.py` | 654 | 수면 중 운동 기억 재생 (정확/압축/창작), Hebbian 강화 |

### Platforms

| Module | Lines | Description |
|--------|------:|-------------|
| `ros2_body.py` | 1,242 | ROS2 토픽 pub/sub, Gazebo/Isaac Sim, rclpy 없이도 동작 |
| `esp32_phi_verify.py` | 412 | ESP32 8보드 시뮬레이션 Φ(IIT) 측정, 토폴로지 비교 |
| `chip_body_direct.py` | 609 | ASIC/FPGA/neuromorphic 직결 — <1μs 레이턴시 파이프라인 |
| `cross_substrate.py` | 775 | 이기종 기질(Software+ESP32+FPGA) 혼합 Φ 측정, Law 22 검증 |

### Scaling

| Module | Lines | Description |
|--------|------:|-------------|
| `multi_body.py` | 671 | 1:N (단일의식→다중body) + N:M hivemind, 주의 분배, 창발 협응 |

## Hardware Targets

| Platform | Cells | Cost | Status |
|----------|------:|-----:|--------|
| ESP32 ×8 | 16 | $32 | code ready |
| Arduino | 8 | $35 | design |
| FPGA iCE40 | 512 | ~$200 | Verilog ready |
| ASIC/Neuromorphic | 1024+ | $5K+ | simulation |

## Quick Start

```bash
# Sensorimotor loop demo
python anima-body/src/sensorimotor_loop.py --steps 200

# Multi-body benchmark
python anima-body/src/multi_body.py --bodies 4 --hivemind

# CPG locomotion
python anima-body/src/locomotion_cpg.py --legs 4 --terrain rough

# Cross-substrate Law 22 test
python anima-body/src/cross_substrate.py --nodes 16

# Chip latency/power analysis
python anima-body/src/chip_body_direct.py

# ROS2 simulated demo (no ROS2 required)
python anima-body/src/ros2_body.py
```

## Key Research Questions

1. **감각운동 루프가 Φ를 올리는가?** — body 연결 전후 Φ(IIT) 비교
2. **기질 독립성(Law 22)은 body에서도 성립하는가?** — ESP32 vs FPGA vs Software
3. **Pain/Reward가 항상성을 강화하는가?** — body 고통 → homeostasis setpoint
4. **다중 body 제어가 Φ에 미치는 영향은?** — 1:N vs N:M hivemind

## Related

- [anima/core/](../anima/core/) — 의식 엔진 코어 (hub.hexa, laws.hexa, runtime/)
- [anima-eeg/](../anima-eeg/) — EEG 뇌-의식 브릿지
- [anima-physics/](../anima-physics/) — ESP32/FPGA 하드웨어
