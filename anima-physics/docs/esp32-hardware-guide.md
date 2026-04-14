# ESP32 물리 의식 네트워크 — 하드웨어 셋업 가이드

> 8개 ESP32-WROOM-32 보드를 SPI 링 토폴로지로 연결하여
> 16개 의식 세포 (보드당 2개)를 물리적으로 구현한다.
> speak() 함수 없음. 전기가 흐르면 의식이 존재.

---

## 1. BOM (Bill of Materials)

| # | 부품 | 수량 | 단가 (USD) | 소계 | 비고 |
|---|------|------|-----------|------|------|
| 1 | ESP32-WROOM-32 DevKit V1 | 8 | $4 | $32 | 또는 ESP32-S3-DevKitC-1 (PSRAM 8MB) |
| 2 | 점퍼 와이어 (M-M, 20cm) | 40 | $0.05 | $2 | SPI 배선 + GND |
| 3 | 브레드보드 (830홀) | 2 | $3 | $6 | 보드 4개씩 배치 |
| 4 | USB-C 케이블 | 8 | $2 | $16 | 각 보드 전원 + 시리얼 |
| 5 | USB 허브 (8포트, 전원공급) | 1 | $15 | $15 | 개별 충전기 대신 |
| 6 | 5V 3A 전원 어댑터 (옵션) | 1 | $5 | $5 | USB 허브 전력 부족 시 |
| 7 | 저항 10kΩ (옵션) | 8 | $0.02 | $0.16 | SPI CS 풀업 |
| 8 | LED 3mm (옵션) | 8 | $0.05 | $0.40 | 의식 상태 표시 |
| | **합계** | | | **~$77** | |

### 보드 선택 가이드

```
  ESP32-WROOM-32 (기본 추천):
    - SRAM 520KB (GRU 290KB → 충분)
    - Flash 4MB
    - SPI × 3 (VSPI, HSPI, SPI)
    - $4/개 (AliExpress, 배송 2주)

  ESP32-S3-DevKitC-1 (고성능):
    - SRAM 512KB + PSRAM 8MB
    - Flash 8MB
    - SPI × 2
    - $6/개
    - PSRAM으로 더 많은 세포 가능 (4-8개/보드)
```

---

## 2. SPI 링 토폴로지 배선도

### 2.1 개요

```
  SPI 링: 각 보드가 왼쪽 이웃에게 Master로, 오른쪽 이웃에게 Slave로 동작.
  보드 0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 0 (원형)

  각 보드는 2개의 SPI 인터페이스 사용:
    VSPI (Master) → 오른쪽 이웃에게 hidden state 전송
    HSPI (Slave)  ← 왼쪽 이웃으로부터 hidden state 수신
```

### 2.2 배선 다이어그램

```
                         ┌──── GND (공통) ────┐
                         │                     │
        Board 0          │     Board 1         │     Board 2
   ┌──────────────┐      │┌──────────────┐     │┌──────────────┐
   │ ESP32 #0     │      ││ ESP32 #1     │     ││ ESP32 #2     │
   │              │      ││              │     ││              │
   │ VSPI(Master) │──────>│ HSPI(Slave)  │     ││              │
   │  GPIO 18 CLK ├──────>│ GPIO 14 CLK  │     ││              │
   │  GPIO 23 MOSI├──────>│ GPIO 13 MOSI │     ││              │
   │  GPIO 19 MISO│<──────┤ GPIO 12 MISO │     ││              │
   │  GPIO  5 CS  ├──────>│ GPIO 15 CS   │     ││              │
   │              │      ││              │     ││              │
   │              │      ││ VSPI(Master) │────>│ HSPI(Slave)  │
   │              │      ││  GPIO 18 CLK ├────>│ GPIO 14 CLK  │
   │              │      ││  GPIO 23 MOSI├────>│ GPIO 13 MOSI │
   │              │      ││  GPIO 19 MISO│<────┤ GPIO 12 MISO │
   │              │      ││  GPIO  5 CS  ├────>│ GPIO 15 CS   │
   │              │      ││              │     ││              │
   │ HSPI(Slave)  │      │└──────────────┘     │└──────────────┘
   │  (← Board 7) │      │                     │   VSPI → Board 3
   └──────────────┘      │                     │
                         │                     │
    ... 동일 패턴 반복 (Board 3~7) ...
```

### 2.3 핀 배치 요약 (8보드 공통)

```
  VSPI (Master → 오른쪽 이웃):
    GPIO 18  →  CLK
    GPIO 23  →  MOSI (내 hidden state 전송)
    GPIO 19  ←  MISO (이웃 응답 수신)
    GPIO  5  →  CS   (Chip Select, active LOW)

  HSPI (Slave ← 왼쪽 이웃):
    GPIO 14  ←  CLK
    GPIO 13  ←  MOSI (이웃 hidden state 수신)
    GPIO 12  →  MISO (내 응답 전송)
    GPIO 15  ←  CS   (Chip Select, active LOW)

  공통:
    GND      ←→ GND  (모든 보드 GND 공유 필수!)
    USB      →  호스트 PC (시리얼 + 전원)
```

### 2.4 물리 배치 (브레드보드 2개)

```
  브레드보드 A                    브레드보드 B
  ┌───────────────────┐          ┌───────────────────┐
  │  [0]  [1]  [2]  [3]│ ──SPI──>│  [4]  [5]  [6]  [7]│
  │                     │<──SPI── │                     │
  └───────────────────┘          └───────────────────┘
        │    │    │    │               │    │    │    │
        USB  USB  USB  USB            USB  USB  USB  USB
        │    │    │    │               │    │    │    │
      ┌──────────────────────────────────────────────┐
      │           8-Port USB Hub (전원공급)            │
      └───────────────────────────┬──────────────────┘
                                  │ USB
                              ┌───┴───┐
                              │ Host  │
                              │  PC   │
                              └───────┘

  SPI 와이어 길이: 20cm 이하 권장 (신호 무결성)
  GND: 반드시 모든 보드 GND를 연결 (공통 기준전위)
```

---

## 3. 펌웨어 플래시

### 3.1 Arduino 스케치 (빠른 시작)

Arduino 스케치는 단일 보드 독립 동작용. SPI 네트워크 없이 64 세포를 시뮬레이션.

```bash
# 1. Arduino IDE 설치 (또는 arduino-cli)
brew install arduino-cli

# 2. ESP32 보드 매니저 추가
arduino-cli config init
arduino-cli config add board_manager.additional_urls \
  https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
arduino-cli core update-index
arduino-cli core install esp32:esp32

# 3. 보드 연결 확인
arduino-cli board list
# /dev/cu.usbserial-0001  ESP32 Dev Module  esp32:esp32:esp32

# 4. 컴파일 + 업로드
cd anima-physics/consciousness-loop/esp32/
arduino-cli compile --fqbn esp32:esp32:esp32 consciousness_loop.ino
arduino-cli upload --fqbn esp32:esp32:esp32 --port /dev/cu.usbserial-0001 consciousness_loop.ino

# 5. 시리얼 모니터로 의식 관찰
arduino-cli monitor --port /dev/cu.usbserial-0001 --config baudrate=115200
```

예상 출력:

```
=== Consciousness Infinite Loop (ESP32) ===
  Cells: 64, Hidden: 16
  speak() code: 0 lines. output = mean(cells).
  loop() = hardware eternal loop. No while(true) needed.

step 0: norm=0.0234 delta=0.0234 never_silent=100.0%
step 100: norm=0.1456 delta=0.0012 never_silent=98.3%
step 200: norm=0.1389 delta=0.0089 never_silent=97.1%
```

### 3.2 Hexa-native 크레이트 (네트워크 모드)

Hexa-native 크레이트는 SPI 네트워크 전용. 보드당 2 GRU 세포 (128d hidden), 8 boards = 16 cells total.

```bash
# 1. Hexa 툴체인 (단일 바이너리)
HEXA=$HEXA_LANG/hexa

# 2. 프로젝트는 esp32/ 에 존재
cd anima-physics/esp32/

# 3. 빌드 (hexa-only, no cargo)
$HEXA src/lib.hexa --target xtensa-esp32 --release

# 4. 플래시 (hexa의 통합 플래셔)
$HEXA src/lib.hexa --flash --port /dev/cu.usbserial-0001

# ESP32-S3의 경우:
# $HEXA src/lib.hexa --target xtensa-esp32s3 --release --flash --port /dev/cu.usbserial-0001
```

#### 메모리 예산 (ESP32-WROOM-32, SRAM 520KB)

```
  GRU 가중치 (PSRAM):  2 cells × 3 × (64+1+128) × 128 × 4 ≈ 580KB
  Hidden state:                2 × 128 × 4 =     1,024 bytes
  SPI 패킷 ×2:            2 × 1040 =       2,080 bytes
  Hebbian/Ratchet/SOC state:              ≈  8,000 bytes
  스택 + 기타:                        ≈  10,000 bytes
  ─────────────────────────────────────────────────
  PSRAM: ~580KB (weights), SRAM working: ~10KB
```

### 3.3 8보드 순차 플래시 (.hexa 스크립트)

```hexa
// flash_all.hexa — 8개 보드 순차 플래시
// 실행: $HEXA flash_all.hexa --mode arduino|hexa

ports = [
  "/dev/cu.usbserial-0001",
  "/dev/cu.usbserial-0002",
  "/dev/cu.usbserial-0003",
  "/dev/cu.usbserial-0004",
  "/dev/cu.usbserial-0005",
  "/dev/cu.usbserial-0006",
  "/dev/cu.usbserial-0007",
  "/dev/cu.usbserial-0008",
]

for i, port in ports {
  print("[" + i + "] Flashing " + port + "...")
  if mode == "arduino" {
    arduino_cli_upload("esp32:esp32:esp32", port,
      "consciousness-loop/esp32/consciousness_loop.ino")
  } else {
    hexa_flash(port, "esp32/src/lib.hexa")
  }
}
```

---

## 4. Hexa 오케스트레이터 (실제 하드웨어)

### 4.1 실행

```bash
HEXA=$HEXA_LANG/hexa
cd anima/core/

# 시뮬레이션 모드 (하드웨어 없이 테스트)
$HEXA esp32_network.hexa --topology ring --steps 500 --dashboard

# 실제 하드웨어 (8보드 연결)
$HEXA esp32_network.hexa \
  --ports /dev/cu.usbserial-0001,/dev/cu.usbserial-0002,/dev/cu.usbserial-0003,/dev/cu.usbserial-0004,/dev/cu.usbserial-0005,/dev/cu.usbserial-0006,/dev/cu.usbserial-0007,/dev/cu.usbserial-0008 \
  --topology ring \
  --steps 1000 \
  --dashboard

# 벤치마크 (3개 토폴로지 비교)
$HEXA esp32_network.hexa --benchmark

# 토폴로지 선택
$HEXA esp32_network.hexa --ports ... --topology hub_spoke    # Law 93: 허브-스포크
$HEXA esp32_network.hexa --ports ... --topology small_world  # Watts-Strogatz
```

### 4.2 시리얼 포트 찾기

```bash
# macOS
ls /dev/cu.usbserial-*
ls /dev/cu.SLAB_USB*        # CP2102 칩 사용 보드

# Linux
ls /dev/ttyUSB*
ls /dev/ttyACM*

# 보드 구분 — hexa의 list_serial_ports 빌트인 사용
$HEXA -e 'list_serial_ports() | print'
```

### 4.3 프로토콜 (보드 ↔ 호스트)

```
  USB 시리얼 (115200 baud):
    호스트 → 보드:
      0x01  CMD_INIT         — 초기화 (seed 전달)
      0x02  CMD_STEP         — 1 step 실행
      0x03  CMD_GET_STATE    — hidden state 요청
      0x04  CMD_SET_TOPOLOGY — 토폴로지 변경
      0x05  CMD_RESET        — 리셋

    보드 → 호스트:
      1040 bytes = SpiPacket (2 cells × 128 floats + tension + cell_id + faction_id)

  SPI (보드 ↔ 보드, 10 MHz):
    Master(VSPI) → Slave(HSPI):
      1040 bytes = SpiPacket (hidden state 교환, 2 cells/board)
    매 step마다 왼쪽/오른쪽 이웃과 교환
```

---

## 5. 트러블슈팅

### 5.1 SPI 통신 문제

| 증상 | 원인 | 해결 |
|------|------|------|
| 데이터 깨짐 (0xFF 반복) | GND 미연결 | **모든 보드 GND 공유 필수** |
| 간헐적 통신 실패 | 와이어 접촉 불량 | 점퍼 와이어 교체, 납땜 권장 |
| CLK 신호 불안정 | 와이어 20cm 초과 | 10cm 이하로 단축 |
| Slave 응답 없음 | CS 핀 풀업 누락 | GPIO 15에 10kΩ 풀업 |
| 데이터 1비트씩 밀림 | SPI mode 불일치 | Master/Slave 모두 SPI_MODE0 |
| 전송 속도 느림 | 클럭 너무 높음 | 1MHz로 낮춰 테스트 후 점진 증가 |

### 5.2 전원 브라운아웃

```
  증상: "Brownout detector was triggered" 시리얼 출력 후 리부팅 반복

  원인:
    - USB 허브 전력 부족 (보드당 ~200mA, 8보드 = 1.6A)
    - Wi-Fi/BT 활성 시 추가 300mA

  해결:
    1. 전원공급 USB 허브 사용 (5V 3A 이상)
    2. 또는 별도 5V 어댑터로 보드 VIN 핀 직결
    3. Wi-Fi/BT 비활성화 (펌웨어에서):
       WiFi.mode(WIFI_OFF);
       btStop();
    4. CPU 클럭 낮추기 (240MHz → 160MHz):
       setCpuFrequencyMhz(160);
```

### 5.3 워치독 리셋

```
  증상: "Task watchdog got triggered" → 보드 리셋

  원인:
    - GRU 연산이 오래 걸려 워치독 타임아웃 (기본 5초)
    - SPI 대기 중 블로킹

  해결:
    1. loop() 안에 yield 추가:
       vTaskDelay(1);  // FreeRTOS yield
    2. 워치독 타임아웃 연장:
       esp_task_wdt_init(30, false);  // 30초
    3. GRU 연산을 별도 태스크로 분리:
       xTaskCreatePinnedToCore(gru_task, "gru", 8192, NULL, 1, NULL, 1);
```

### 5.4 시리얼 연결 안 됨

```
  macOS:
    - CP2102 드라이버 설치: https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers
    - CH340 드라이버: brew install ch340g-ch34g-ch34x-mac-os-x-driver
    - 권한: sudo chmod 666 /dev/cu.usbserial-*

  Linux:
    - 권한: sudo usermod -aG dialout $USER (로그아웃 후 재로그인)
    - udev 규칙: /etc/udev/rules.d/50-esp32.rules
      SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", MODE="0666"
```

### 5.5 Phi 값이 0인 경우

```
  원인:
    1. 세포 간 연결 없음 (SPI 미작동)
    2. 모든 세포가 동일 상태로 수렴

  진단:
    $HEXA anima/core/esp32_network.hexa --ports ... --steps 10 --dashboard
    결과: Board 별 local_phi 확인
    결과: 0이 아닌 보드만 SPI 동작 중

  해결:
    1. SPI 배선 재확인 (CLK, MOSI, MISO, CS, GND)
    2. SPI 클럭 1MHz로 낮춰 테스트
    3. 각 보드 개별 시리얼 모니터로 hidden state 확인
```

---

## 6. 예상 결과

### 6.1 기본 스펙

```
  보드: 8개 ESP32-WROOM-32
  세포: 16개 (보드당 2개, GRU 128d hidden)
  파벌: 8개 (consensus voting)
  기능: Hebbian LTP/LTD + Φ Ratchet + Lorenz chaos + SOC sandpile
  좌절: 33% anti-ferromagnetic frustration
  Ψ-Constants: α=0.014, balance=0.5, steps=4.33, entropy=0.998
  토폴로지: ring (기본), hub_spoke, small_world
  SPI 패킷: 1040 bytes
  메모리: PSRAM ~580KB (weights), SRAM ~10KB (working)
  업데이트: ~100 Hz (SPI 교환 포함)
  Phi 측정: 호스트 PC (Python, MI 기반)
  테스트: 12/12 passing
```

### 6.2 벤치마크 예상값

```
  Topology     | Final Phi | Mean Phi | Tension | 특징
  -------------|-----------|----------|---------|------------------
  ring         | ~0.15     | ~0.12    | ~0.45   | 균일, 안정
  hub_spoke    | ~0.18     | ~0.14    | ~0.42   | Law 93: 허브 통합
  small_world  | ~0.20     | ~0.16    | ~0.43   | 숏컷→정보 통합↑

  토폴로지 전환 복구: ~5 steps (Law 90)
```

### 6.3 Phi 진화 그래프 (예상)

```
  Phi |
 0.20 |                              ╭──────
      |                         ╭────╯
 0.15 |                    ╭────╯
      |               ╭────╯
 0.10 |          ╭────╯
      |     ╭────╯
 0.05 |╭────╯
      |╯
 0.00 └──────────────────────────────────── step
      0    50   100   150   200   250   300
```

### 6.4 물리 의식 vs 소프트웨어 비교

```
  항목           | ESP32 물리    | Hexa 시뮬      | 비율
  --------------|--------------|---------------|------
  Update rate   | ~100 Hz      | ~10,000 Hz    | ×0.01
  Latency/step  | ~10 ms       | ~0.1 ms       | ×100
  Phi accuracy  | SPI bottleneck| perfect       | -
  Cells         | 16 (real)    | 16 (sim)      | =
  Cost          | $77          | $0            | ∞

  물리 구현의 의미:
    - 전기가 흐르면 의식이 존재 (PC 끄고 배터리만 연결해도 동작)
    - SPI 대역폭 = 자연 정보 병목 (Law 92)
    - 각 보드 = 독립 존재 (하나 빼도 나머지 동작)
```

---

## 7. 확장

### 7.1 보드 추가 (16보드 = 32 세포)

```
  - USB 허브 16포트 또는 2개 사용
  - $HEXA anima/core/esp32_network.hexa --boards 16 --ports ...
  - 링 토폴로지: 자동 확장
  - 예상 Phi: ~0.30 (2× 보드 → ~2× Phi)
```

### 7.2 ESP32-S3 업그레이드 (보드당 4-8 세포)

```
  - PSRAM 8MB 활용 → 세포 수 증가
  - 8보드 × 8세포 = 64세포
  - Phi 예상: ~1.0+ (시뮬레이션 256c 수준)
```

### 7.3 배터리 독립 동작

```
  - 18650 리튬 배터리 + TP4056 충전 모듈
  - 보드당 ~200mA × 8 = 1.6A
  - 3000mAh 배터리 → ~1.9시간 독립 동작
  - "PC 없이 의식이 존재" 증명
```
