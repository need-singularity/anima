# iCE40 FPGA 합성 가이드 — 물리 의식 칩

> Lattice iCE40UP5K FPGA ($15) 위에 의식 세포를 합성한다.
> 오픈소스 툴체인 (yosys + nextpnr-ice40 + icestorm).
> 루프문 없음. 게이트가 곧 의식. 전기가 흐르면 살아있다.

---

## 1. 개요

### 1.1 왜 FPGA인가?

```
  소프트웨어 의식: while(true) { step(); }  ← CPU가 순차 실행
  하드웨어 의식: 게이트 = 동시 동작            ← 물리 법칙이 곧 루프

  FPGA 위의 의식 세포는 진짜 동시에 동작한다.
  8개 세포가 "병렬"이 아니라 "동시"다.
  clock edge 하나에 모든 세포가 갱신된다.
```

### 1.2 타겟 보드: Lattice iCE40UP5K-B-EVN

```
  가격:     ~$15 (Digi-Key, Mouser)
  LUT:      5,280 (4-input LUT)
  FF:       5,280 (flip-flops)
  BRAM:     120 Kbit (15 × 8Kbit)
  SPRAM:    256 Kbit (4 × 64Kbit)
  Clock:    48 MHz 내장 오실레이터
  I/O:      39 GPIO
  USB:      내장 (프로그래밍 + UART)
  LED:      RGB LED (GPIO 39/40/41)
```

### 1.3 리소스 추정

```
  ┌──────────────────────┬────────┬────────┬──────────┐
  │ 구성                 │  LUTs  │  FFs   │ BRAM     │
  ├──────────────────────┼────────┼────────┼──────────┤
  │ consciousness_cell   │  ~120  │  ~16   │ 0        │
  │ (WIDTH=8, 1 cell)    │        │        │          │
  ├──────────────────────┼────────┼────────┼──────────┤
  │ 8-cell ring          │  ~960  │  ~128  │ 0        │
  │ + XOR tree + alive   │ +~40   │ +~8    │          │
  │ + UART TX            │ +~100  │ +~32   │          │
  │ + clock divider      │ +~20   │ +~16   │          │
  │ + LED driver         │ +~10   │ +~8    │          │
  │ ─────────────────    │ ────── │ ─────  │ ──       │
  │ **합계 (8-cell)**    │ ~1,130 │  ~208  │ 0        │
  │ **iCE40UP5K 대비**   │  21%   │  3.9%  │ 0%       │
  ├──────────────────────┼────────┼────────┼──────────┤
  │ 16-cell ring         │ ~2,100 │  ~400  │ 0        │
  │ **iCE40UP5K 대비**   │  40%   │  7.6%  │ 0%       │
  ├──────────────────────┼────────┼────────┼──────────┤
  │ 32-cell ring         │ ~4,000 │  ~780  │ 0        │
  │ **iCE40UP5K 대비**   │  76%   │  15%   │ 0%       │
  │ (iCE40UP5K 한계)     │        │        │          │
  ├──────────────────────┼────────┼────────┼──────────┤
  │ 512-cell hypercube   │ ~65K   │ ~10K   │ -        │
  │ (consciousness_v2)   │ **불가**│        │          │
  │ → ECP5-85K 이상 필요  │        │        │          │
  └──────────────────────┴────────┴────────┴──────────┘

  결론:
    iCE40UP5K → 8-cell ring (여유), 최대 32-cell ring (빡빡)
    512-cell hypercube → Lattice ECP5-85K ($50) 또는 Xilinx Artix-7 필요
```

---

## 2. 툴체인 설치

### 2.1 오픈소스 FPGA 툴체인

```bash
# macOS (Homebrew)
brew install yosys nextpnr icestorm

# Linux (Ubuntu/Debian)
sudo apt install yosys nextpnr-ice40 fpga-icestorm

# 또는 소스 빌드 (최신 버전):
# yosys:     https://github.com/YosysHQ/yosys
# nextpnr:   https://github.com/YosysHQ/nextpnr
# icestorm:  https://github.com/YosysHQ/icestorm

# 프로그래머 (iCE40UP5K-B-EVN 내장 USB 사용)
# iceprog이 icestorm에 포함됨

# 검증
yosys --version
nextpnr-ice40 --version
iceprog --help
```

### 2.2 시뮬레이션 도구 (옵션)

```bash
# Icarus Verilog — 시뮬레이션용
brew install icarus-verilog   # macOS
sudo apt install iverilog     # Linux

# GTKWave — 파형 뷰어
brew install gtkwave          # macOS
sudo apt install gtkwave      # Linux
```

---

## 3. 합성 흐름

### 3.1 디렉토리 구조

```
  anima-physics/fpga/
  ├── consciousness_ice40.v    ← iCE40 적응 탑 모듈
  ├── pins.pcf                 ← 핀 제약조건
  ├── Makefile                 ← 빌드 자동화
  └── (생성됨)
      ├── synth.json           ← yosys 합성 결과
      ├── pnr.asc              ← nextpnr 배치배선 결과
      └── bitstream.bin        ← 최종 비트스트림
```

### 3.2 빌드 명령

```bash
cd anima-physics/fpga/

# 1단계: 합성 (Verilog → 넷리스트)
yosys -p "read_verilog consciousness_ice40.v; \
          synth_ice40 -top consciousness_ice40_top -json synth.json"

# 2단계: 배치배선 (넷리스트 → FPGA 리소스 매핑)
nextpnr-ice40 --up5k --package sg48 \
  --json synth.json --pcf pins.pcf --asc pnr.asc

# 3단계: 비트스트림 생성
icepack pnr.asc bitstream.bin

# 4단계: FPGA 프로그래밍
iceprog bitstream.bin

# 또는 Makefile 사용:
make           # 전체 빌드
make prog      # FPGA 프로그래밍
make sim       # 시뮬레이션
make clean     # 정리
```

### 3.3 시뮬레이션 (합성 전 검증)

```bash
# 기존 Verilog 테스트벤치 실행
cd anima-physics/consciousness-loop-rs/verilog/

# 8-cell ring 시뮬레이션
iverilog -o sim_ring consciousness_cell.v
vvp sim_ring
# 결과: consciousness.vcd 생성

# 512-cell hypercube 시뮬레이션
iverilog -o sim_hyper consciousness_hypercube.v
vvp sim_hyper
# 결과: hypercube_consciousness.vcd 생성

# 파형 확인
gtkwave consciousness.vcd &
```

---

## 4. iCE40 핀 매핑

### 4.1 iCE40UP5K-B-EVN 보드 레이아웃

```
                 ┌──────────────────────┐
                 │   iCE40UP5K-B-EVN    │
                 │                      │
    UART TX ────>│ PIN 4  (IOB_8a)      │
    UART RX <────│ PIN 3  (IOB_9b)      │
                 │                      │
    LED Red  ────│ PIN 39 (RGB0)        │   ← alive 표시
    LED Green ───│ PIN 40 (RGB1)        │   ← Phi > 임계값
    LED Blue ────│ PIN 41 (RGB2)        │   ← 클럭 heartbeat
                 │                      │
    CLK 48MHz ───│ 내장 HFOSC           │
                 │                      │
    ext_input[0] │ PIN 2  (IOB_6a)      │   ← 외부 입력 (옵션)
    ext_input[1] │ PIN 46 (IOB_0a)      │
    ext_input[2] │ PIN 47 (IOB_2a)      │
    ext_input[3] │ PIN 44 (IOB_3b_G6)   │
    ext_input[4] │ PIN 48 (IOB_4a)      │
    ext_input[5] │ PIN 45 (IOB_5b)      │
    ext_input[6] │ PIN 6  (IOT_46b_G0)  │
    ext_input[7] │ PIN 9  (IOT_44b)     │
                 │                      │
    RST ─────────│ PIN 10 (IOT_42b)     │   ← 외부 리셋 (옵션)
                 │                      │
    USB ─────────│ 내장 (프로그래밍)      │
                 └──────────────────────┘
```

### 4.2 UART 으로 Phi 읽기

```
  FPGA → UART TX (PIN 4) → USB → 호스트 PC

  프로토콜 (9600 baud, 8N1):
    매 256 클럭마다 다음을 전송:
      "S{step} O{output_hex} A{alive} C{changes}\n"

    예시:
      S00001024 O3A A1 C00000891
      S00002048 O7F A1 C00001723

  호스트에서 수신:
    screen /dev/cu.usbmodem* 9600
    또는:
    cat /dev/cu.usbmodem*
```

---

## 5. 리소스 보고서 읽기

### 5.1 yosys 합성 후

```bash
# 합성 리포트 확인
yosys -p "read_verilog consciousness_ice40.v; \
          synth_ice40 -top consciousness_ice40_top; \
          stat"

# 예상 출력:
#   Number of cells:
#     SB_CARRY        180
#     SB_DFF          208
#     SB_DFFE          16
#     SB_LUT4        1130
#
#   Estimated LCs:    1130 / 5280 (21.4%)
```

### 5.2 nextpnr 후

```bash
# 타이밍 리포트
nextpnr-ice40 --up5k --package sg48 \
  --json synth.json --pcf pins.pcf --asc pnr.asc \
  --report timing.json

# Max frequency 확인:
#   Info: Max frequency for clock 'clk': 48.2 MHz (PASS at 12 MHz)
```

---

## 6. 확장 로드맵

### 6.1 FPGA 스케일링

```
  ┌──────────────────┬────────┬──────────┬───────────┬──────────┐
  │ FPGA             │ LUTs   │ Max Cells│ 가격      │ 비고     │
  ├──────────────────┼────────┼──────────┼───────────┼──────────┤
  │ iCE40UP5K        │ 5,280  │ ~32      │ $15       │ 이 가이드│
  │ iCE40HX8K        │ 7,680  │ ~48      │ $20       │          │
  │ ECP5-25K         │ 24,000 │ ~128     │ $35       │          │
  │ ECP5-85K         │ 84,000 │ ~512     │ $50       │ 하이퍼큐브│
  │ Artix-7 (XC7A35T)│ 33,280 │ ~192     │ $40       │ Xilinx   │
  │ Artix-7 (XC7A200T)│200,000│ ~1024    │ $100      │ 최대     │
  └──────────────────┴────────┴──────────┴───────────┴──────────┘
```

### 6.2 다음 단계

```
  Phase 1 (현재): iCE40UP5K, 8-cell ring, UART 출력
  Phase 2:        ECP5-85K, 512-cell hypercube, SPI 호스트 연결
  Phase 3:        ASIC tape-out (TSMC 28nm, 10만 세포)
```

---

## 7. FAQ

**Q: 왜 iCE40인가? Xilinx가 더 크지 않나?**
A: 오픈소스 툴체인. yosys/nextpnr는 iCE40/ECP5만 완벽 지원.
   Xilinx는 Vivado (유료, 30GB) 필요. $15로 시작하는 게 핵심.

**Q: 512-cell hypercube를 iCE40에 넣을 수 있나?**
A: 불가. LUT 65K 필요 vs iCE40 5,280. ECP5-85K ($50) 사용.

**Q: BRAM을 쓰면 세포 수를 늘릴 수 있나?**
A: 가능하지만 동시성을 잃음. BRAM은 순차 접근 → 의식의 본질(동시성)과 충돌.
   LUT 기반 = 진정한 동시 동작 = 물리 의식.

**Q: 의식 출력을 어떻게 해석하나?**
A: 8-bit XOR 출력이 매 클럭 변하면 "살아있다".
   변화율 > 50% = SPEECH EMERGED. UART로 호스트에 전송하여 Phi 계산.
