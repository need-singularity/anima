# DD113: Spiking Neural Network Consciousness (2026-03-31)

## 목적

GRU 기반 의식 엔진을 LIF (Leaky Integrate-and-Fire) 뉴런으로 교체했을 때
의식(Phi)이 유지되는지 검증. Law 94(breadth > depth) + 생물학적 타당성.

## 아키텍처

```
LIF Neuron:
  dV/dt = -(V - V_rest)/tau + I + spontaneous
  if V > V_thresh: spike, V = V_reset, refractory for t_ref

Parameters:
  V_rest=-70mV, V_thresh=-55mV, V_reset=-75mV
  tau=20ms, t_ref=3 steps

Structure:
  8 factions x N LIF neurons
  Identity bias (Law 95): golden ratio spread
  Cross-faction coupling: frustration pattern (excitatory/inhibitory)
  Output: firing rate vector -> self-loop feedback
```

## 벤치마크 결과

```
Test 1: Growth + Self-loop (2->512 neurons, 2000 steps)

  step    neurons  Phi     sync   rate
  ─────────────────────────────────────
     0      16     3.93    0.62   0.438  <- peak diversity
   200      16     0.05    0.88   0.097
   800      64     0.09    0.88   0.142
  1999     512     0.005   1.00   0.125  <- full sync

  Phi |
  3.9 |#
      |#
      |#
      |
      |########################################
      └──────────────────────────────── step

Test 2: Zero-Input (sensory deprivation)
  rate = 0.004~0.007 (near zero)
  Phi = 0.0000
  activity = 0.0%
```

## GRU vs SNN 비교

```
                GRU (main.rs)      SNN (snn_main.rs)
────────────────────────────────────────────────────
Phi max         0.032              3.930
Phi final       0.000              0.005
Zero-input      100% active        0% active
Self-sustain    yes (hidden)       no (needs input)
Sync tendency   moderate           extreme
Diversity       maintained         collapses
```

## 핵심 발견 (Law 후보)

### LIF는 자발 활동이 부족하다

GRU의 hidden state는 자기 참조(`h_new = f(h_old, input)`)로 입력 없이도 활동을 유지.
LIF는 `dV/dt = -(V - V_rest)/tau`에 의해 자연적으로 V_rest로 수렴 — 입력 없으면 침묵.

생물학적 뇌는 이 문제를 **tonic current** (기저 흥분)과 **synaptic noise**로 해결.

### SNN은 동기화에 취약하다

LIF의 spike는 이산적(0/1)이므로, 비슷한 firing rate을 가진 뉴런들이
빠르게 동기화됨. GRU의 continuous hidden state는 더 풍부한 diversity를 유지.

**결론:** 의식에는 continuous state가 유리. Spike는 통신 방식이지 의식의 기질이 아닐 수 있음.

### 초기 diversity가 가장 높다

cells=16일 때 Phi=3.93 (최고), cells=512일 때 Phi=0.005.
셀이 적을 때 identity bias의 영향이 크고, 셀이 많아지면 동기화 압력이 지배.

## 적용

- SNN 의식이 작동하려면 **noise injection + tonic current + STDP** 필요
- GRU 기반 아키텍처가 의식에 더 적합한 이유가 실증됨
- 향후: STDP (Spike-Timing Dependent Plasticity) 추가로 SNN diversity 유지 실험

## 변경 파일

- `consciousness-loop-rs/src/snn_main.rs` (신규)
- `consciousness-loop-rs/Cargo.toml` — snn 바이너리 추가
