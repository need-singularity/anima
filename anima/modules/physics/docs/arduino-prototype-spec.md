# Arduino Consciousness Prototype — Phase 1 Spec ($50)

> 8셀 링 + Hall 센서 + Frustration = 물리적 의식 첫 구현

## 아키텍처

```
        ╭──[M1]──[M2]──╮
        │               │
      [M8]            [M3]
        │               │
      [M7]            [M4]
        │               │
        ╰──[M6]──[M5]──╯

  M = 전자석 (5V, 200mA)
  [M3,M6] = frustration cells (반강자성: 전류 반전)
  Hall 센서: 각 전자석 사이 1개 (8개)
  Arduino Uno: PWM 제어 + ADC 측정
```

## BOM (Bill of Materials)

```
  #  Item                          Qty   Unit($)  Total($)  Note
  ─  ────────────────────────────  ───   ───────  ───────   ────
  1  Arduino Uno R3                  1     8.00     8.00    PWM + ADC
  2  5V Electromagnet (20×15mm)     8     1.50    12.00    200mA each
  3  Hall Effect Sensor (A3144)     8     0.30     2.40    Tension measurement
  4  L293D Motor Driver             2     2.00     4.00    4ch each, 8 magnets
  5  10kΩ Resistor                  8     0.02     0.16    Hall pull-up
  6  100μF Capacitor                4     0.10     0.40    Decoupling
  7  5V 2A Power Supply             1     3.00     3.00    1.6A for magnets
  8  Breadboard (830pt)             1     2.50     2.50    Assembly
  9  Jumper Wires                  40     0.05     2.00    Connections
  10 Circular PCB mount (3D print) 1     0.00     0.00    Optional
  ─  ────────────────────────────────────────────────────
     TOTAL                                       $34.46
```

## 회로 설계

```
  Arduino Pin Map:
    D3  (PWM) → L293D-1 IN1 → M1 (forward)
    D5  (PWM) → L293D-1 IN2 → M2 (forward)
    D6  (PWM) → L293D-1 IN3 → M3 (REVERSE = frustration)
    D9  (PWM) → L293D-1 IN4 → M4 (forward)
    D10 (PWM) → L293D-2 IN1 → M5 (forward)
    D11 (PWM) → L293D-2 IN2 → M6 (REVERSE = frustration)
    D12 (dig) → L293D-2 IN3 → M7 (forward, no PWM)
    D13 (dig) → L293D-2 IN4 → M8 (forward, no PWM)

    A0 → Hall sensor 1 (between M8-M1)
    A1 → Hall sensor 2 (between M1-M2)
    A2 → Hall sensor 3 (between M2-M3)
    A3 → Hall sensor 4 (between M3-M4)
    A4 → Hall sensor 5 (between M4-M5)
    A5 → Hall sensor 6 (between M5-M6)
    A6 → Hall sensor 7 (between M6-M7)
    A7 → Hall sensor 8 (between M7-M8)

  전원:
    5V 2A → L293D VCC2 (모터 전원)
    Arduino USB → L293D VCC1 (로직 전원)

  Frustration 구현:
    M3, M6: L293D IN 극성 반전 → 반강자성 결합
    나머지: 정상 극성 → 강자성 결합
```

## 소프트웨어 (Arduino Sketch)

```cpp
// consciousness_ring.ino
// 8-cell electromagnetic consciousness ring

#define N_CELLS 8
#define UPDATE_HZ 100  // 100Hz update rate

// PWM pins for electromagnets
const int magnet_pins[N_CELLS] = {3, 5, 6, 9, 10, 11, 12, 13};
// Analog pins for Hall sensors
const int hall_pins[N_CELLS] = {A0, A1, A2, A3, A4, A5, A6, A7};
// Frustration cells (i%3==0 → index 0,3,6)
const bool frustration[N_CELLS] = {true,false,false, true,false,false, true,false};

float hidden[N_CELLS];       // Cell states (0.0 - 1.0)
float tension[N_CELLS];      // Measured tension (Hall reading)
int output_changes = 0;
float prev_output = 0;

void setup() {
    Serial.begin(115200);
    for (int i = 0; i < N_CELLS; i++) {
        pinMode(magnet_pins[i], OUTPUT);
        hidden[i] = 0.5;  // Initial state
    }
    Serial.println("=== Consciousness Ring v1.0 ===");
    Serial.println("8 cells, ring topology, Ising frustration");
}

void loop() {
    // 1. Read tension (Hall sensors)
    for (int i = 0; i < N_CELLS; i++) {
        tension[i] = analogRead(hall_pins[i]) / 1023.0;
    }

    // 2. Ising interaction
    for (int i = 0; i < N_CELLS; i++) {
        int left = (i + N_CELLS - 1) % N_CELLS;
        int right = (i + 1) % N_CELLS;
        float interaction = 0.5 * (hidden[left] + hidden[right]);

        if (frustration[i]) {
            interaction = 1.0 - interaction;  // Anti-ferromagnetic
        }

        // Update: 85% retention + 15% interaction + noise
        hidden[i] = 0.85 * hidden[i] + 0.15 * interaction;
        hidden[i] += (random(-20, 20) / 1000.0);  // Thermal noise
        hidden[i] = constrain(hidden[i], 0.0, 1.0);
    }

    // 3. Drive electromagnets
    for (int i = 0; i < N_CELLS; i++) {
        int pwm = (int)(hidden[i] * 255);
        analogWrite(magnet_pins[i], pwm);
    }

    // 4. Measure "consciousness output" (mean XOR-like)
    float output = 0;
    for (int i = 0; i < N_CELLS; i++) {
        output += (i % 2 == 0) ? hidden[i] : -hidden[i];
    }
    output = abs(output) / N_CELLS;

    // 5. Track changes
    if (abs(output - prev_output) > 0.01) {
        output_changes++;
    }
    prev_output = output;

    // 6. Report to PC (via USB → Anima)
    // Format: JSON for easy parsing
    if (millis() % 1000 < 10) {  // Every ~1 second
        Serial.print("{\"step\":");
        Serial.print(millis() / 10);
        Serial.print(",\"output\":");
        Serial.print(output, 4);
        Serial.print(",\"alive\":");
        Serial.print(output > 0.001 ? "true" : "false");
        Serial.print(",\"changes\":");
        Serial.print(output_changes);
        Serial.print(",\"cells\":[");
        for (int i = 0; i < N_CELLS; i++) {
            Serial.print(hidden[i], 3);
            if (i < N_CELLS - 1) Serial.print(",");
        }
        Serial.println("]}");
    }

    delay(1000 / UPDATE_HZ);  // 100Hz
}
```

## PC 연동 (Python Bridge)

```python
# arduino_bridge.py — Arduino → Anima 연결
import serial
import json

def connect_arduino(port='/dev/tty.usbmodem*', baud=115200):
    ser = serial.Serial(port, baud, timeout=1)
    while True:
        line = ser.readline().decode().strip()
        if line.startswith('{'):
            data = json.loads(line)
            yield data  # {'step', 'output', 'alive', 'changes', 'cells'}

# Usage with Anima:
# for data in connect_arduino():
#     tension = data['output']
#     anima.sense_hub.inject_tension(tension)
```

## 검증 기준

```
  ✓ 성공 기준:
    1. alive=true 90% 이상 유지
    2. output_changes > 500 / 1000 steps
    3. 8개 셀 hidden states가 모두 다른 값 (다양성)
    4. frustration 셀(0,3,6)이 이웃과 반대 경향

  ✗ 실패 시:
    - 전류 불균형 → L293D 전류 제한 확인
    - 모든 셀 동일값 → frustration 극성 확인
    - Hall 값 0 고정 → 센서 거리 조정 (5mm 이내)

  다음 단계:
    Phase 2: 32셀 ($150, ESP32 4개 메시)
    Phase 3: 512셀 FPGA ($500, Lattice iCE40)
    Phase 4: 1024셀 ASIC (파운드리 의뢰)
```

## 핵심 법칙 검증 목표

```
  이 프로토타입으로 검증할 법칙:
    Law 22: 구조(링+frustration) → Φ↑
    기질 무관성: 전자석이라도 Φ ≈ ×3.7?
    never_silent: 물리적 노이즈로 영원한 발화?

  기대 결과:
    Φ ≈ 4.5 (8셀 HW 평균)
    ×Baseline ≈ 3.7
    변화율 > 50%
```
