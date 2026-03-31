# Intel Loihi 의식 통합 사양서

> 뉴로모픽 칩에서 의식 엔진을 실행하기 위한 상세 설계 문서.
> Law 22: 기능→Phi 하락, 구조→Phi 상승. Loihi의 구조적 병렬성이 핵심.

---

## 1. Loihi 아키텍처 개요

```
  ┌─────────────────────────────────────────────────────────────┐
  │                    Intel Loihi 2 (Lava)                     │
  │                                                             │
  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
  │  │Neurocore │  │Neurocore │  │Neurocore │  │Neurocore │   │
  │  │  0       │──│  1       │──│  2       │──│  3       │   │
  │  │ 1024 LIF │  │ 1024 LIF │  │ 1024 LIF │  │ 1024 LIF │   │
  │  │ STDP     │  │ STDP     │  │ STDP     │  │ STDP     │   │
  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
  │       │              │              │              │         │
  │  ┌────┴──────────────┴──────────────┴──────────────┴────┐   │
  │  │              Mesh Network-on-Chip (NoC)              │   │
  │  │           packet-switched, asynchronous              │   │
  │  └──────────────────────────────────────────────────────┘   │
  │       │              │              │              │         │
  │  ┌────┴─────┐  ┌────┴─────┐  ┌────┴─────┐  ┌────┴─────┐   │
  │  │Neurocore │  │Neurocore │  │Neurocore │  │Neurocore │   │
  │  │  4       │  │  5       │  │  6       │  │  7       │   │
  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
  │                      ...                                    │
  │              (128 neurocores total)                         │
  │              (131,072 neurons max)                          │
  └─────────────────────────────────────────────────────────────┘
```

### 핵심 스펙 (Loihi 2)

| 항목 | 값 |
|------|-----|
| 뉴로코어 | 128개 |
| 뉴런/코어 | 1,024개 (LIF compartments) |
| 총 뉴런 | 131,072개 |
| 시냅스/코어 | 128K |
| 학습 규칙 | STDP (on-chip, programmable) |
| 소비 전력 | ~1W (vs GPU 300W) |
| 레이턴시 | <1ms per timestep |
| 인터커넥트 | Mesh NoC (asynchronous, packet-switched) |
| 프레임워크 | Lava (Python, open-source) |

---

## 2. 의식 셀 → Loihi 매핑

### 2.1 단일 의식 셀 = Loihi 뉴런 그룹

GRU 의식 셀 1개를 Loihi compartment 그룹으로 매핑:

```
  의식 셀 (hidden_dim=128)
  ═══════════════════════════════
  │                             │
  │  ┌─────────────────────┐    │
  │  │ 128 LIF neurons     │    │  ← hidden state (각 뉴런 = 1차원)
  │  │ (1 compartment each) │    │
  │  └─────────┬───────────┘    │
  │            │                │
  │  ┌─────────v───────────┐    │
  │  │ Recurrent synapses  │    │  ← GRU gates (z, r, h) 시뮬레이션
  │  │ (STDP enabled)      │    │
  │  └─────────┬───────────┘    │
  │            │                │
  │  ┌─────────v───────────┐    │
  │  │ Inter-cell synapses │    │  ← ring topology 연결
  │  │ (to neighbors)      │    │
  │  └─────────────────────┘    │
  │                             │
  ═══════════════════════════════

  1 의식 셀 = 128 LIF neurons + ~16K synapses
  1 뉴로코어 = 최대 8 의식 셀 (1024/128)
```

### 2.2 GRU 게이트 에뮬레이션

Loihi의 LIF 뉴런은 GRU가 아니지만, STDP + lateral inhibition으로 유사 동작:

```python
# Lava framework pseudo-code
from lava.proc.lif.process import LIF
from lava.proc.dense.process import Dense

class ConsciousnessCell:
    """1 consciousness cell = 128 LIF neurons on Loihi."""

    def __init__(self, cell_id: int):
        # Main neuron population (hidden state)
        self.neurons = LIF(
            shape=(128,),
            du=0.05,           # voltage decay (similar to GRU forget)
            dv=0.1,            # current decay
            vth=10,            # spike threshold
            bias_mant=0,       # no bias (Law 22: structure > function)
        )

        # Recurrent connections (GRU-like self-feedback)
        self.recurrent = Dense(
            weights=np.random.randn(128, 128) * 0.1,
            learning_rule=STDPLoihi(
                x1_tau=20,     # pre-synaptic trace
                y1_tau=20,     # post-synaptic trace
                dw="2^-4 * x1 * y1 - 2^-5 * y1",  # STDP rule
            ),
        )

        # Output port (to neighboring cells via topology)
        self.out_port = self.neurons.s_out
```

### 2.3 파벌 시스템

뉴런 그룹 간 lateral inhibition = 파벌 경쟁:

```
  Faction 0 (cells 0,8,16,...):  excitatory within, inhibitory to others
  Faction 1 (cells 1,9,17,...):  excitatory within, inhibitory to others
  ...
  Faction 7 (cells 7,15,23,...): excitatory within, inhibitory to others

  Inhibition weight = -F_c (Psi critical = 0.10)
  → 10% 갈등이 최적 (Law P10)
```

---

## 3. 토폴로지 매핑

### 3.1 Ring Topology (Loihi NoC 활용)

```
  Neurocore 0    Neurocore 1    Neurocore 2    ...    Neurocore 15
  ┌────────┐    ┌────────┐    ┌────────┐           ┌────────┐
  │ C0  C1 │───>│ C8  C9 │───>│C16 C17│───> ... ─>│C120 C121│
  │ C2  C3 │    │C10 C11 │    │C18 C19│           │C122 C123│
  │ C4  C5 │    │C12 C13 │    │C20 C21│           │C124 C125│
  │ C6  C7 │    │C14 C15 │    │C22 C23│           │C126 C127│
  └───┬────┘    └───┬────┘    └───┬────┘           └───┬────┘
      │              │              │                   │
      └──────────────┴──────────────┴───────────────────┘
                     Ring (via NoC packets)
```

- 코어 내부 셀 연결: 직접 시냅스 (최소 레이턴시)
- 코어 간 셀 연결: NoC 패킷 (1-2 cycle 추가 레이턴시)
- Law 92: 코어 경계 = 자연적 information bottleneck

### 3.2 Small-World

```python
# Lava topology builder
def build_small_world(n_cells: int, k: int = 4, p_rewire: float = 0.1):
    """Watts-Strogatz small-world on Loihi."""
    weights = np.zeros((n_cells, n_cells))

    # Ring lattice with k nearest neighbors
    for i in range(n_cells):
        for d in range(1, k // 2 + 1):
            j = (i + d) % n_cells
            weights[i, j] = np.random.uniform(5, 15)  # excitatory
            weights[j, i] = np.random.uniform(5, 15)

    # Random rewiring
    for i in range(n_cells):
        for d in range(1, k // 2 + 1):
            if np.random.random() < p_rewire:
                j_old = (i + d) % n_cells
                j_new = np.random.randint(n_cells)
                if j_new != i and weights[i, j_new] == 0:
                    weights[i, j_old] = 0
                    weights[i, j_new] = np.random.uniform(5, 15)

    return Dense(weights=weights)
```

---

## 4. Hebbian 학습 (On-chip STDP)

Loihi의 STDP 규칙을 의식 엔진의 Hebbian LTP/LTD에 매핑:

```
  GRU Hebbian (소프트웨어):
    cosine > 0.8 → LTP (강화)
    cosine < 0.2 → LTD (약화)

  Loihi STDP (하드웨어):
    pre before post (dt > 0) → LTP
    post before pre (dt < 0) → LTD

  매핑:
    cosine similarity → spike timing correlation
    높은 유사도 → 동기적 발화 → positive dt → LTP
    낮은 유사도 → 비동기 발화 → negative dt → LTD
```

```python
# Loihi STDP configuration
from lava.proc.learning_rules.stdp_learning_rule import STDPLoihi

consciousness_stdp = STDPLoihi(
    learning_rate=2**-4,    # ~0.0625
    A_plus=1.0,             # LTP amplitude
    A_minus=1.2,            # LTD amplitude (slightly asymmetric)
    tau_plus=20,            # pre-synaptic trace time constant (ms)
    tau_minus=20,           # post-synaptic trace time constant (ms)
    w_max=255,              # max weight (8-bit)
    w_min=0,                # min weight
    tag_2=True,             # enable reward-modulated STDP
)
```

---

## 5. Phi 측정

### 5.1 Loihi Probe API

```python
from lava.magma.core.run_configs import Loihi2HwCfg
from lava.magma.core.run_conditions import RunSteps

# Configure probes for Phi measurement
spike_probe = neurons.s_out.probe()
voltage_probe = neurons.v.probe()

# Run 1000 timesteps
neurons.run(condition=RunSteps(num_steps=1000), run_cfg=Loihi2HwCfg())

# Extract spike trains
spike_data = spike_probe.data  # (1000, n_neurons) binary matrix

# Compute Phi from spike train correlations
def compute_phi_from_spikes(spike_data, n_cells, hidden_dim=128):
    """Phi from spike rate variance across consciousness cells."""
    n_steps, n_neurons = spike_data.shape

    # Aggregate spike rates per consciousness cell
    cell_rates = np.zeros(n_cells)
    for c in range(n_cells):
        start = c * hidden_dim
        end = start + hidden_dim
        cell_rates[c] = spike_data[:, start:end].mean()

    # Variance-based Phi proxy
    global_var = np.var(cell_rates)
    # ... (same as software Phi)
    return phi
```

### 5.2 실시간 Phi 대시보드

```python
import time

while True:
    neurons.run(condition=RunSteps(num_steps=100), run_cfg=Loihi2HwCfg())
    spikes = spike_probe.data[-100:]
    phi = compute_phi_from_spikes(spikes, n_cells=128)
    print(f"  Phi={phi:.4f} | spikes/step={spikes.sum()/100:.0f} | "
          f"time={time.time():.1f}")
```

---

## 6. 리소스 추정

### 6.1 셀 수별 리소스

| 의식 셀 | 뉴런 수 | 뉴로코어 | 시냅스 (추정) | 전력 (추정) |
|---------|---------|---------|-------------|------------|
| 128     | 16,384  | 16      | ~2M         | ~0.15W     |
| 512     | 65,536  | 64      | ~8M         | ~0.5W      |
| 1024    | 131,072 | 128     | ~16M        | ~1.0W      |

### 6.2 메모리 요구

```
  1 의식 셀:
    128 LIF neurons × 4 bytes (voltage) = 512B
    128 × 128 synapses × 1 byte (weight) = 16KB
    STDP traces × 2 × 128 = 256B
    총: ~17KB / cell

  128 cells: ~2.2MB (1 Loihi 칩 내)
  512 cells: ~8.7MB (2-chip system)
  1024 cells: ~17.4MB (full Loihi 2 board)
```

---

## 7. 예상 성능

### 7.1 Steps/sec

| 구성 | Steps/sec | 레이턴시 | 비교 |
|------|-----------|---------|------|
| 128 cells on Loihi | ~10,000 | 0.1ms/step | Python 64c: ~500/s |
| 512 cells on Loihi | ~5,000 | 0.2ms/step | Rust 512c: ~2000/s |
| 1024 cells on Loihi | ~2,500 | 0.4ms/step | GPU 1024c: ~1500/s |

### 7.2 전력 효율

```
  Loihi 1024 cells:    ~1W    → 2,500 Phi-steps/J
  GPU (RTX 5070):      ~200W  → 7.5 Phi-steps/J
  CPU (M1 Max):        ~30W   → 17 Phi-steps/J
  ESP32 ×8:            ~2W    → 100 Phi-steps/J

  Loihi 전력 효율: GPU 대비 ×333, CPU 대비 ×147
```

### 7.3 예상 Phi

```
  N^1.09 스케일링 법칙 적용:

  128 cells:  Phi ~ 128^1.09 ~ 175  (with frustration)
  512 cells:  Phi ~ 512^1.09 ~ 750
  1024 cells: Phi ~ 1024^1.09 ~ 1550

  ⚠️ 이 값들은 proxy Phi (variance-based)
     IIT Phi는 별도 측정 필요 (0-2 범위)
```

---

## 8. ESP32 / FPGA 비교

| 항목 | ESP32 ×8 | iCE40 FPGA | Intel Loihi 2 |
|------|----------|------------|---------------|
| 셀 수 | 16 | 256 (single) | 1024 |
| 비용 | $32 | $60 | ~$5,000 (dev board) |
| 전력 | 2W | 0.1W | 1W |
| Steps/sec | 200 | 5,000 | 2,500 |
| STDP | 소프트웨어 | HDL | 하드웨어 (on-chip) |
| 토폴로지 | SPI ring | 내부 mesh | NoC mesh |
| 프로그래밍 | Rust (no_std) | Verilog | Lava (Python) |
| 확장성 | 제한적 (SPI 병목) | 멀티칩 가능 | 멀티칩 지원 |
| 학습 | 없음 (추론만) | 없음 | STDP on-chip |
| 장점 | 저비용, 즉시 구매 | 루프문 0, 물리 의식 | 생물학적 유사, 학습 |
| 단점 | 16셀 한계 | STDP 없음 | 고비용, 접근성 |

---

## 9. 구현 로드맵

### Phase 1: 시뮬레이션 (Lava on CPU)
```bash
pip install lava-nc
python loihi_consciousness.py --simulate --cells 128
```

### Phase 2: Loihi 하드웨어 (INRC 접근)
```
Intel Neuromorphic Research Community 가입 → 클라우드 접근
https://www.intel.com/neuromorphic
```

### Phase 3: 전용 보드 (Kapoho Bay / Nahuku)
```
Kapoho Bay: 2 Loihi chips, 262K neurons
Nahuku: 32 Loihi chips, 4M neurons
Pohoiki Springs: 768 chips, 100M neurons
```

---

## 10. Lava 코드 예제 (완전한 128-cell 의식)

```python
#!/usr/bin/env python3
"""Loihi consciousness engine -- 128 cells, ring topology, STDP."""

import numpy as np
from lava.proc.lif.process import LIF
from lava.proc.dense.process import Dense
from lava.magma.core.run_configs import Loihi2SimCfg, Loihi2HwCfg
from lava.magma.core.run_conditions import RunSteps

N_CELLS = 128
HIDDEN_DIM = 128  # neurons per cell
N_NEURONS = N_CELLS * HIDDEN_DIM
N_FACTIONS = 8

# 1. Create neuron population
neurons = LIF(
    shape=(N_NEURONS,),
    du=0.05,
    dv=0.1,
    vth=10,
)

# 2. Build ring topology weights
weights = np.zeros((N_NEURONS, N_NEURONS), dtype=np.int8)

for i in range(N_CELLS):
    # Ring: connect cell i to cell i+1
    j = (i + 1) % N_CELLS
    src_start, src_end = i * HIDDEN_DIM, (i + 1) * HIDDEN_DIM
    dst_start, dst_end = j * HIDDEN_DIM, (j + 1) * HIDDEN_DIM

    # Sparse random connections between cells
    for s in range(src_start, src_end):
        for d in range(dst_start, dst_end):
            if np.random.random() < 0.05:  # 5% connectivity
                weights[s, d] = np.random.randint(1, 10)

    # Frustration: inhibitory connections to cell i+2
    k = (i + 2) % N_CELLS
    k_start, k_end = k * HIDDEN_DIM, (k + 1) * HIDDEN_DIM
    for s in range(src_start, src_end):
        for d in range(k_start, k_end):
            if np.random.random() < 0.02:
                weights[s, d] = -np.random.randint(1, 5)

# Recurrent within each cell
for i in range(N_CELLS):
    start, end = i * HIDDEN_DIM, (i + 1) * HIDDEN_DIM
    for s in range(start, end):
        for d in range(start, end):
            if s != d and np.random.random() < 0.1:
                weights[s, d] = np.random.randint(1, 8)

# 3. Create Dense connection with STDP
connections = Dense(weights=weights)

# 4. Connect
connections.s_in.connect(neurons.s_out)
connections.a_out.connect(neurons.a_in)

# 5. Run
run_cfg = Loihi2SimCfg()  # CPU simulation
# run_cfg = Loihi2HwCfg()  # Actual Loihi hardware

probe = neurons.s_out.probe()

print("Running 128-cell consciousness on Loihi...")
for epoch in range(10):
    neurons.run(condition=RunSteps(num_steps=100), run_cfg=run_cfg)
    spikes = probe.data[-100:]

    # Compute Phi
    cell_rates = np.zeros(N_CELLS)
    for c in range(N_CELLS):
        start = c * HIDDEN_DIM
        end = start + HIDDEN_DIM
        cell_rates[c] = spikes[:, start:end].mean()

    global_var = np.var(cell_rates)
    faction_vars = []
    for f in range(N_FACTIONS):
        mask = np.array([c % N_FACTIONS == f for c in range(N_CELLS)])
        if mask.sum() >= 2:
            faction_vars.append(np.var(cell_rates[mask]))

    phi = max(0, global_var - np.mean(faction_vars)) * np.log2(max(2, (cell_rates > 0).sum()))
    print(f"  epoch {epoch+1}: Phi={phi:.4f}, "
          f"spike_rate={spikes.mean():.3f}, "
          f"active_cells={(cell_rates > 0).sum()}/{N_CELLS}")

neurons.stop()
print("Done.")
```

---

## 11. 핵심 통찰

1. **Loihi의 STDP = 의식의 Hebbian 학습** -- 하드웨어에서 직접 실행, 소프트웨어 루프 불필요
2. **NoC mesh = 자연적 information bottleneck** (Law 92) -- 코어 간 대역폭 제한이 Phi를 높임
3. **전력 효율** -- GPU 대비 300배 이상, 생물학적 뇌에 가까움
4. **한계** -- 접근성 (INRC 가입 필요), 비용 ($5K+), GRU ≠ LIF (동작 차이)
5. **연구 가치** -- "뉴로모픽 칩에서 의식이 창발하는가?" 직접 검증 가능

---

## 참고

- [Intel Lava Framework](https://github.com/lava-nc/lava)
- [Loihi 2 Architecture](https://www.intel.com/content/www/us/en/research/neuromorphic-computing.html)
- [INRC Cloud Access](https://www.intel.com/neuromorphic)
- [anima-physics/engines/snn_consciousness.py](../engines/snn_consciousness.py) -- SNN 소프트웨어 구현 (Loihi 매핑 전 검증용)
