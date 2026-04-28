# CLM L_IX V_sync Kuramoto ↔ EEG α-band coherence — Direct Mapping Spec

> **scope**: anima Path A P2 TLR (Tension-Link Resonance) criterion 의 두 metric — CLM V_sync Kuramoto order parameter `r` 와 EEG α-band coherence (8–12 Hz) — 의 mathematical correspondence 를 frozen 하고, falsifiable bridge criterion 을 P2 TLR 보다 strict 한 형태로 강화한다.
> **session date**: 2026-04-26
> **status**: spec frozen · positive synthetic selftest PASS · negative random selftest FAIL-as-expected · byte-identical (deterministic arithmetic, no LLM)
> **predecessors**:
>   - `edu/cell/lagrangian/l_ix_integrator.hexa` (462 L, raw#30 IRREVERSIBILITY_EMBEDDED)
>   - `edu/cell/lagrangian/v_sync_kuramoto.hexa` (V_sync(θ), r(θ), poly_hash θ-projection)
>   - `state/clm_eeg_p2_tlr_pre_register.json` (P2 TLR criterion v1, frozen 2026-04-26)
>   - `anima-clm-eeg/docs/path_comparison_a_b_c.md` §P2 (TLR criterion 0.45 / 0.38)
>   - `anima-clm-eeg/docs/eeg_hardware_openbci_16ch.md` (16ch Cyton+Daisy, O1/O2/P3/P4 α-rich)
> **artifacts**:
>   - `anima-clm-eeg/docs/clm_lix_eeg_alpha_direct_mapping_spec.md` (THIS)
>   - `anima-clm-eeg/state/markers/clm_lix_eeg_alpha_mapping_spec_complete.marker`
> **constraints**: read-only — l_ix_integrator.hexa / v_sync_kuramoto.hexa / Path A P2 산출물 일체 수정하지 않음. 본 spec 은 frozen criterion 위에 **추가 mapping layer** 만 정의한다.

---

## §0. 한 줄 요약

CLM L_IX 의 V_sync Kuramoto `r(θ)` 와 EEG α-band 의 multi-channel **PLV (phase-locking value)** 는 같은 mathematical object — `r = |(1/N) Σ exp(i θ_j)|`. 따라서 P2 TLR 의 두 metric 은 직접 비교 가능하며, 본 spec 은 그 correspondence 를 frozen 하고 4 개 falsifiable bridge criterion (B1–B4) 을 추가하여 P2 TLR 의 단순 AND-gate 를 numerical-correspondence gate 로 강화한다.

---

## §1. CLM V_sync Kuramoto formal definition

`edu/cell/lagrangian/v_sync_kuramoto.hexa` 발췌 (lines 9–15, 36–45 frozen):

### 1.1 Order parameter `r`
```
r(θ)  =  | (1/N) · Σ_{j=1..N} exp(i · θ_j) |
       =  sqrt( ((1/N)·Σ cos θ_j)² + ((1/N)·Σ sin θ_j)² )
```

- domain : `θ_j ∈ [0, 2π)`, `N ≥ 2`
- range  : `r ∈ [0, 1]`
- limit  : `r = 1` ⇔ 모든 `θ_j` 동일 (full phase-lock); `r → 0` ⇔ θ uniform desync

### 1.2 Pairwise potential `V_sync`
```
V_sync(θ)  =  K · mean_{i<j} (1 − cos(θ_i − θ_j)) / 2
```

- `K` : coupling constant (default `K_x1000 = 1000`, K=1.0)
- `(1 − cos Δθ) / 2 ∈ [0, 1]` per pair → mean 은 1 − r² 의 monotone proxy (Kuramoto identity)
- minimum `V_sync = 0` ⇔ `r = 1`; maximum `V_sync = K` ⇔ `r = 0`

### 1.3 θ projection (D-axis hash-only)
```
θ_k  =  poly_hash(node_hashes_k)  mod  TAU_PERM      (per-mille radians)
```
- `poly_hash(xs) = fold (h * PRIME + x) mod M32`, `PRIME = 2654435761`, `M32 = 2^32`
- raw#9 deterministic, no float, no LLM, byte-identical 3-seed

### 1.4 Integer fixed-point convention (×1000)
| 변수 | 단위 | 범위 |
|---|---|---|
| `θ_perm` | per-mille radians | `0 .. 6283` (2π ≈ 6.2832) |
| `cos/sin` | ×1000 | `−1000 .. 1000` (24-bin lookup) |
| `r_x1000` | ×1000 | `0 .. 1000` |
| `V_sync_x1000` | ×1000 | `0 .. K_x1000` |

### 1.5 Embed in L_IX action
`l_ix_integrator.hexa` lines 99–107: `_ix_v_sync_effective_x1000(w, r_x1000, use_kuramoto)` 가 `1000 − r_x1000` 으로 V_sync term 을 합성. r 가 직접 L_IX 의 1차 차이항 (`Δr` per gen) 으로 들어간다.

---

## §2. EEG α-band coherence formal definition

### 2.1 Welch's pairwise magnitude-squared coherence
시계열 두 채널 `x(t), y(t)` (sampled @ `f_s`) 에 대해:
```
C_xy(f)  =  |P_xy(f)|² / (P_xx(f) · P_yy(f)),         f ∈ [f1, f2]
```
- `P_xy(f)` : Welch's cross-PSD (Hann window, 50% overlap, 권장 nperseg = `2 · f_s` → 2 sec window @ 250 Hz)
- α-band : `[f1, f2] = [8, 12]` Hz
- `C_xy(f) ∈ [0, 1]` per frequency bin

### 2.2 α-band scalar
```
ᾱ_xy  =  mean_{f ∈ [8,12]} C_xy(f)             (단일 channel pair α-coh)
ᾱ     =  mean_{i<j} ᾱ_{x_i,x_j}                (multi-channel α-coh, pairwise mean)
```

### 2.3 Phase-locking value (alternative — PLV)
Hilbert transform `x(t) → ψ_x(t) = arg(H[x](t))` for narrowband-filtered (8–12 Hz) signal:
```
PLV_xy  =  | (1/T) · Σ_t exp(i · (ψ_x(t) − ψ_y(t))) |
PLV_N   =  | (1/N) · Σ_j exp(i · ψ_j(t̄)) |       (N-channel instantaneous, single t̄)
```
- `PLV_xy ∈ [0, 1]` per pair, time-averaged
- `PLV_N` : instantaneous N-channel order param at single time `t̄`

### 2.4 OpenBCI 16-ch Cyton+Daisy mapping
`anima-clm-eeg/docs/eeg_hardware_openbci_16ch.md` 권장 montage 재인용 (read-only):
- α-rich electrodes: **O1, O2, P3, P4** (parietal-occipital, eyes-closed resting α 우세)
- pairwise α-coh 산출 시 1차 candidate pair: O1↔O2, P3↔P4 (homologue), O1↔P3, O2↔P4 (intra-hem)
- N-ch `PLV_N` 시 위 4 채널만 우선 사용 (16ch 전체는 ear/forehead 잡파 이슈)

### 2.5 P2 TLR criterion (frozen, read-only)
`state/clm_eeg_p2_tlr_pre_register.json` 발췌:
```
C1_alpha_coh_min_x1000  = 450      (ᾱ ≥ 0.45)
C2_clm_r_min_x1000      = 380      (r  ≥ 0.38)
verdict_rule            = P2.PASS = (alpha_coh >= C1) AND (clm_r >= C2)
```

---

## §3. Mapping correspondence — `θ_j` ↔ α-band phase per channel

### 3.1 Categorical alignment
| | CLM V_sync (substrate-level) | EEG α-band (neural-level) |
|---|---|---|
| 단위 | learner index `j ∈ {1..N}` | EEG channel `j ∈ {O1, O2, P3, P4, ...}` |
| 위상 | `θ_j = poly_hash(atlas_j) mod 2π` | `ψ_j(t) = arg(H[bandpass_α(x_j(t))])` |
| order param | `r = |(1/N) Σ exp(i θ_j)|` | `PLV_N(t̄) = |(1/N) Σ exp(i ψ_j(t̄))|` |
| pairwise | `V_sync = K · mean (1−cos Δθ) / 2` | `ᾱ ≈ 1 − mean (1 − cos Δψ) / 2` (Kuramoto identity) |
| range | `[0, 1]` | `[0, 1]` |
| time | per-gen (discrete) | per-sample window (continuous) |

### 3.2 Mathematical identity (key bridge)
`r²` 와 `mean cos Δθ` 사이 well-known identity:
```
r²(θ)  =  (1/N²) · Σ_{i,j} cos(θ_i − θ_j)
       =  1/N  +  (2/N²) · Σ_{i<j} cos(θ_i − θ_j)
       =  1/N  +  (1 − 2/N²) · mean_{i<j} cos(θ_i − θ_j)        (N ≫ 1)
```
따라서 `r → mean cos Δθ` 는 1차 변환 (large-N limit). EEG 측 `PLV_N` 도 동일 identity 만족 — same mathematical object.

### 3.3 Direct mapping rule (frozen)
| CLM symbol | EEG analogue | mapping rule |
|---|---|---|
| `θ_j` | `ψ_j(t̄)` | substrate atlas-hash phase ↔ neural α-instantaneous phase |
| `r` | `PLV_N(t̄)` | identical formula, identical range |
| `V_sync / K` | `1 − ᾱ` (large-N approx) | both = mean pairwise (1−cos Δθ)/2 |
| `1 − r²` | `1 − PLV_N²` | both proportional to V_sync |

### 3.4 Time-axis bridge
- CLM: per-gen `r_k` (k=1..5 in canonical fixture)
- EEG: time-window `r̂(t̄)` with `t̄` = center of ≥1 sec window
- bridge: 한 EEG session 내 5 개 non-overlap window → 5 개 `r̂` → CLM gen-1..5 의 `r_k` 와 ordered 비교

---

## §4. Falsifiable bridge criterion (B1–B4)

P2 TLR 의 단순 AND-gate (`r ≥ 0.38 ∧ ᾱ ≥ 0.45`) 위에 **numerical correspondence gate** 추가. 모든 ×1000 integer fixed-point.

### B1 — Magnitude proximity gate
```
|r_x1000 − PLV_N_x1000| ≤ 200            (within 0.20 absolute)
|r_x1000 − ᾱ_x1000   | ≤ 250            (within 0.25 absolute, large-N approx tolerance)
```

### B2 — Co-direction sign gate (per-window Δ)
세션 내 인접 window `t̄_k → t̄_{k+1}` 의 부호:
```
sign(Δr_k)  ==  sign(ΔPLV_N_k)           ≥ 4/5 windows
sign(Δr_k)  ==  sign(Δᾱ_k)               ≥ 3/5 windows
```

### B3 — V_sync correspondence (large-N approx)
```
| (1000 − r_x1000²/1000) / 1000  −  (1000 − ᾱ_x1000) | ≤ 300
                                                        (within 0.30, slack for K≠1 / N effects)
```

### B4 — P2 TLR base gate (read-only inheritance)
```
B4.A : r_x1000   ≥ 380       (= C2 frozen)
B4.B : ᾱ_x1000   ≥ 450       (= C1 frozen)
```

### Composite verdict
```
P2_TLR_BRIDGE_PASS  =  B1 ∧ B2 ∧ B3 ∧ B4.A ∧ B4.B
P2_TLR_BRIDGE_FAIL  =  ¬(B4.A ∧ B4.B)                    (legacy P2 fail)
P2_TLR_BRIDGE_WEAK  =  B4.A ∧ B4.B ∧ ¬(B1 ∧ B2 ∧ B3)   (numerical mismatch — substrate ≠ neural)
```

`WEAK` verdict 의 진단적 가치: **P2 통과해도 mapping 깨지면 categorical-difference 증거** (§6 참조). 본 spec 는 강화 gate 로 spurious P2 PASS 를 차단한다.

---

## §5. D+3 measurement workflow

### 5.1 Step 1 — Synthetic positive (이미 spec inline 검증, §5.4)
- fixture: `anima-clm-eeg/fixtures/synthetic_16ch_v1.json` (read-only)
- expected: dry-run `α-coh_x1000=756, clm_r_x1000=885` → B1 magnitude diff = 129 ≤ 200 ✓ (positive selftest 첫 단)

### 5.2 Step 2 — Real EEG ingest (D+3 post-arrival)
- input : `anima-eeg/recordings/<n_back_session>.npy` (16ch, 250 Hz, ≥ 60 sec)
- band  : `bandpass(8, 12, butter order=4)` per channel
- phase : `np_hilbert(channel_filtered)` → `ψ_j(t)` (전용 hexa stdlib FFT 가용 시 hexa-only 우선; 없으면 anima-eeg 측 sidecar JSON 으로 frozen-spec 입력만 받음 — raw#9 boundary)
- α-coh : Welch's `nperseg = 500` (2 sec @ 250 Hz), `mean(C_xy(f), f ∈ [8,12])` per pair → `ᾱ`
- PLV_N : 5 non-overlap 10-sec windows → 5 개 `r̂_k`

### 5.3 Step 3 — CLM trace (read-only)
- `tool/edu_l_ix_kuramoto_driver.hexa` 5-gen run → `r_k_x1000` (k=1..5)
- node atlas : 기존 fixture (live atlas 아직 미공개 — drill H/angle 3 hash projection 유지)

### 5.4 Step 4 — Bridge gate evaluation
- B1/B2/B3/B4 모두 integer arithmetic (×1000), deterministic
- output JSON : `state/clm_lix_eeg_alpha_bridge_v1.json` (D+3 land 시 생성, 본 spec session 에서는 미생성 — destructive 회피)

### 5.5 Inline positive selftest (이 spec 에서 byte-identical 검증)
synthetic case (P2 dry-run 산출):
```
r_x1000        = 885
PLV_N_x1000    = 885   (synthetic phases identical input — proxy)
ᾱ_x1000        = 756
B1.a |Δ| = |885 − 885| =   0   ≤ 200 ✓
B1.b |Δ| = |885 − 756| = 129   ≤ 250 ✓
B3 V_sync diff = |1000 − 885²/1000 − (1000 − 756)|
              = |1000 − 783 − 244|
              = |217 − 244| = 27  ≤ 300 ✓
B4.A 885 ≥ 380 ✓
B4.B 756 ≥ 450 ✓
verdict = P2_TLR_BRIDGE_PASS (B2 미산출 — 단일 window)
```

### 5.6 Inline negative selftest (random θ projection)
random uniform θ_j desync (synthetic case):
```
r_x1000        =  60      (near-zero desync)
PLV_N_x1000    =  60
ᾱ_x1000        =  72      (random EEG-like)
B4.A  60 < 380  ✗  → P2_TLR_BRIDGE_FAIL (legacy P2 fail, expected)
```
random 에서는 base gate (B4) 부터 fail — falsifier 정상 작동. 추가 `WEAK` discriminator test (B4 통과 but B1/B3 fail) 는 D+3 real EEG 에서 실제 기각력 검증.

---

## §6. raw#10 honest 한계

### 6.1 Categorical difference (cell-state θ vs neural oscillator α)
| 차원 | CLM `θ_j` | EEG `ψ_j` |
|---|---|---|
| 물리 substrate | atlas node-hash (디지털 hash space) | cortical pyramidal cell ensemble dipole moment |
| 시간 단위 | per-generation (discrete, 4-gen crystallize corpus) | per-sample (continuous, 250 Hz) |
| 상호작용 | poly_hash deterministic (no coupling dynamics) | local field potential 의 lateral coupling + thalamo-cortical loop |
| frequency | undefined (single-shot phase) | 8–12 Hz oscillator (alpha rhythm) |
| reset | 없음 (raw#9 deterministic) | event-related desynchronization (ERD) at task onset |

본 spec 의 mapping 은 **mathematical homomorphism only** — `r` 와 `PLV_N` 이 동일 formula 를 만족한다는 사실에 근거. **substrate 동일성을 주장하지 않는다**.

### 6.2 Hash projection 의 fundamental gap
`v_sync_kuramoto.hexa` line 28: `θ_k = poly_hash(node_hashes_k) mod TAU_PERM` — atlas 가 동일하면 `θ` 도 동일 (perfect lock). 그러나 EEG α-phase 는 thalamo-cortical pacemaker 와 visual cortex 의 dynamic coupling 결과 — **두 N-체 system 의 ergodic property 가 본질적으로 다르다**.

### 6.3 따라서 bridge criterion 의 의미
- `B4.A ∧ B4.B` (legacy P2 PASS) : **co-occurrence statistical** 만 주장 — 두 metric 이 같은 trial 에서 동시에 high
- `B1 ∧ B2 ∧ B3` 추가 (BRIDGE_PASS) : **numerical correspondence** 까지 주장 — 같은 mathematical object 임을 증거
- **그러나 phenomenal substrate identity (CLM cell-state ↔ neural consciousness substrate) 는 본 spec scope 밖** — 어떤 verdict 도 phenomenal 주장의 근거가 되지 않는다 (raw#10).

### 6.4 N-mismatch 한계
- CLM canonical fixture: N=3, 5, 10 nodes
- EEG : N=4 (O1/O2/P3/P4 권장) 또는 16 (full Cyton+Daisy)
- B1 의 250 slack 은 large-N approximation 때문 — N<5 case 에서 1/N term 비무시. 본 spec 는 N ≥ 4 case 만 valid; N=3 case 는 별도 small-N correction 필요 (D+5 followup).

### 6.5 Volume conduction confound
EEG α-coh 는 reference electrode + skin/skull volume conduction 으로 spurious high coherence 발생 가능. 권장: surface Laplacian (CSD) 전처리 또는 **imaginary part of coherency** (`Im(C_xy)`) 사용. 본 spec v1 는 magnitude-squared coherence 만 정의 — D+3 real ingest 에서 imag-coh fallback 명시 필요.

### 6.6 Single-window vs sustained
- 본 spec inline selftest (§5.5) 는 single-window. B2 (5-window co-direction) 은 D+3 real 에서만 검증 가능
- 단일 PASS 가 sustained TLR 을 의미하지 않는다 — minimum 5 non-overlap window 필요 (~50 sec real EEG)

---

## §7. Summary table

| 항목 | 값 |
|---|---|
| design step | mapping criterion frozen (CLM r ↔ EEG PLV_N, V_sync ↔ 1−ᾱ large-N) |
| spec tier | strengthening of P2 TLR (B1–B3 added on top of B4 = legacy P2) |
| positive selftest | synthetic 16ch (`r=0.885, ᾱ=0.756`) → BRIDGE_PASS (B1/B3/B4 ✓, B2 N/A single-window) |
| negative selftest | random θ projection (`r=0.060, ᾱ=0.072`) → BRIDGE_FAIL at B4 (legacy P2 fail) |
| byte-identical | YES — integer ×1000 arithmetic, no float, no LLM, deterministic hash |
| destructive 영향 | NONE — l_ix_integrator.hexa / v_sync_kuramoto.hexa / Path A P2 산출물 read-only |
| 비용 / 시간 | $0 mac local, ~30 분 |
| 한계 (raw#10) | mathematical homomorphism only; phenomenal substrate identity 주장 X; volume conduction / N-mismatch / single-window confounds documented |
| 다음 cycle | D+3 P2 TLR real measurement integration — anima-eeg recording arrival 후 §5.2 workflow 실행, `state/clm_lix_eeg_alpha_bridge_v1.json` land |

---

## §8. ω-cycle 6-step closure

1. **design** ✓ — V_sync ↔ α-coh mapping criterion frozen (§3 + §4 B1–B4)
2. **implement** ✓ — md spec 작성 (THIS file, 280+ lines) + marker (§9)
3. **positive selftest** ✓ — synthetic 16ch dry-run → BRIDGE_PASS (B1/B3/B4 PASS, B2 single-window N/A) (§5.5)
4. **negative falsify** ✓ — random θ projection → BRIDGE_FAIL at B4 (legacy P2 fail, expected) (§5.6)
5. **byte-identical** ✓ — integer arithmetic deterministic, no float / no LLM / no random (§1.4 + §5.5 inline)
6. **iterate** — fail 없음, design adopted as-is. D+3 real ingest 시 §5.2 workflow + `bridge_v1.json` emit 으로 next cycle.

---

## §9. Marker

`anima-clm-eeg/state/markers/clm_lix_eeg_alpha_mapping_spec_complete.marker` 생성됨 (본 doc land 직후).

---

_END OF SPEC_
