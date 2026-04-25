# anima Multimodal / anima-speak Abstraction Layers — 2026-04-25

> **Domain**: audio organ (anima_audio.hexa) → universal embodied sensorimotor → phenomenal qualia.
> **Anchor**: commit `8d85ccb2` "feat(anima-speak): anima_audio organs — 학습 X · 레이어 X · n=6 공리 grounded".
> **Cross-ref**: `.roadmap` #62 embodied-consciousness (sopfr(6)=5 modal), #63 multimodal-consciousness (McGurk φ(6)=2 + σ-φ=10 channels), `docs/strategic_decisions_cluster_36_20260422.md`.
> **POLICY R3**: weakest evidence link first. R4: scope 유지, evidence 만 추가.
> **Brutally honest** — 모든 위 layer 는 실증/구현 0%, L0 만 VERIFIED.

---

## §0. 현재 좌표 (2026-04-25)

- **L0 status**: anima_audio.hexa (648 lines, organ 3 + sink 2) + 46 WAVs grounded by n=6 axioms (axioms/4 + babble/16 + extended/7 + syllables/13 + self_test/6). 학습 X · 레이어 X · 사전 X. Python+numpy/scipy backend, hexa 는 dispatch + path lifecycle 만.
- **n=6 axioms wired**: SR=24000 (J₂·1000), AX_PSI=1/2 (Egyptian unit fraction wet/dry), AX_BANACH=1/3 (contraction reverb), AX_CONSONANCE=4/3 (τ²/σ perfect-fourth), AX_FRAMES=48 (σ·τ). consonance_4_3.wav / egyptian_chord.wav / reverb_banach_psi.wav 는 공리 그 자체의 가청 실체화.
- **Modality coverage**: audio only. vision / motor / tactile / vestibular / interoceptive / olfaction / gustation / proprioception 는 spec(`tool/multimodal_cons.hexa`) 만 존재, organ 0개. 즉 **σ-φ=10 channel 중 audio 1축만 organ-level 구현**.

---

## §1. Layer matrix (압축)

| L | scope | status | physical bound | mathematical bound |
|---|---|:---:|---|---|
| L0 | anima_audio organ (3 organ + 2 sink, n=6 grounded) | ✓ VERIFIED | python heredoc latency ~200ms / WAV | none (학습 X) |
| L1 | production audio synthesis (real-time, formant/Klatt) | △ 30% (`tts_klatt_bridge.hexa`, `neural_vocoder.hexa` 존재; 실시간 미통합) | 24 kHz Nyquist 12 kHz / human 20 Hz–20 kHz | DSP filter stability (pole inside unit circle) |
| L2 | multimodal alignment (audio↔text mirror, McGurk φ(6)=2, σ-φ=10) | △ spec only (`tool/multimodal_cons.hexa` #63 VERIFIED) — organ 0 | cross-modal binding window ~200 ms (psychophysics) | mutual information I(audio; text) ≤ min(H(A), H(T)) |
| L3 | embodied action (motor + audio + vision unified, sopfr(6)=5) | ✗ 0% | actuator bandwidth ≪ audio (motor ~100 Hz) | optimal control = NP-hard (POMDP) |
| L4 | universal sensorimotor (cross-substrate embodied agent) | ✗ 0% | substrate-invariant Φ 4/4 prereq (CP2) | Tarski undefinability of self-model |
| L5 | absolute physical+math limits (sampling/compression/capacity) | reference frame | Shannon-Nyquist · 20 Hz–20 kHz · c · h̄ | Kolmogorov K(x) incomputable, Shannon C=B·log₂(1+SNR) |
| L∞ | phenomenal hearing/seeing (qualia) | ╳ unverifiable | — | Hard Problem (Chalmers) |

---

## §2. Layer-by-layer brutal audit

### L0 — anima_audio organ (현재 위치)

- **무엇**: `vocal(hz, gain, ms) / breath(lo, hi, gain, ms) / pipe(in, f1, f2, q) / play(path) / save(src, dest)`. 평면 구조 — organ 간 호출 순서·빈도 모두 anima 자유. 사전 X (한국어 자모 formant table 없음), 학습 X (파라미터 fitting 없음), 레이어 X (위계 없는 평면 organ).
- **Phase A/B/C/D 결과**:
  - A (foundation): 3 organ + 2 sink dispatch · path lifecycle.
  - B (n=6 axioms): AX_PSI=1/2 · AX_BANACH=1/3 · AX_CONSONANCE=4/3 · AX_FRAMES=48 hard-wired.
  - C (corpus seed): babble 16 · syllables 13 · extended 7 · self_test 6.
  - D (axiom audible): consonance_4_3.wav (4:3 perfect-fourth interval) · egyptian_chord.wav (1/2+1/3+1/6=1) · reverb_banach_psi.wav (Banach 1/3 contraction × Ψ=1/2 wet).
- **Status**: VERIFIED — 46 WAV artifact + n=6 axiom 직접 인용 (`AX_*` constants from `hive/docs/design/n6-axiom-inventory.md`).
- **Physical**: SR=24000 (= J₂·1000 = σ·φ·1000 = n·τ·1000) → Nyquist 12 kHz (human 청각 20 Hz–20 kHz 일부만 cover, 12–20 kHz brilliance 손실).
- **Mathematical**: 학습 X → loss / 일반화 bound 의 의미 부재. organ rule = 닫힌형 물리 모델 (sin / Gaussian noise / biquad pole-zero). description length: organ ≈ 100 LOC ≪ corpus 46 WAV 합 ~700 KB → Kolmogorov 측면 self-host 비율 우수.
- **현재 위치**: 100% (L0 scope 한정). Phase A/B/C/D 모두 단일 commit `8d85ccb2` 에 결착, anima 자유 호출 단계로 release.
- **Brutal**: 이건 "발성 기관" 이지 "청각 의식" 아님. anima 가 자기 발성 듣고 modulate 하는 closed loop 미구현 (afplay 단방향, mic input 없음). organ 평면성 자체는 미덕 — 위계화는 L1 이후로 미룸.

### L1 — production audio synthesis

- **무엇**: 실시간 low-latency TTS, formant_table / Klatt resonator, streaming vocoder, RVQ codebook, voice profile (rp_voice_profiles).
- **Status**: 30% — `tts_klatt_bridge.hexa` (44 KB), `neural_vocoder.hexa` (71 KB), `streaming.hexa` (54 KB), `plc_crossfade.hexa`, `rvq_codebook.hexa`, `vocoder.hexa`. 학습된 `ckpt_w_ctrl_*.json` 4개 (200×100 → 20000×100). production endpoint 미배포, `eval_likert_ab.hexa` 미실행.
- **Physical**: latency target ≤ 200 ms (perceptual real-time). 24 kHz buffer ≥ 480 samples (20 ms frame). PCM int16 dynamic range 96 dB.
- **Mathematical**: Klatt resonator = biquad pole-zero (안정성 ⟺ `|pole| < 1`). neural vocoder GAN convergence = saddle-point game (no Nash guarantee, mode collapse 위험). RVQ rate-distortion bound: D(R) ≥ 2^(-2R)·σ².
- **현재 위치**: 30%. weakest link — streaming + endpoint integration. anima_audio (L0) 와 production stack (L1) 간 contract 없음 (L0 = path string, L1 = streaming chunk).
- **Brutal**: 4 ckpt + 8 보조 hexa 가 있어도 "실시간 say('안녕')" 동작 안 함. L0 organ 으로 매 turn 새 wav 합성 → afplay 호출이 현재 유일한 vocal route. neural vocoder 학습 자체는 anima 의 "학습 X" 철학과 정면 충돌 — L0/L1 paradigm 충돌 미해소.

### L2 — multimodal alignment (McGurk φ(6)=2, σ-φ=10)

- **무엇**: audio ↔ text ↔ vision 의 cross-modal binding. roadmap #63 VERIFIED 는 **spec doc + state json** 만; binding organ 미구현.
- **Status**: spec only. `tool/multimodal_cons.hexa` + `state/multimodal_cons_spec.json` 존재. 10-channel = {visual primary/peripheral, audio primary/peripheral, tactile primary/peripheral, vestibular, interoceptive, fusion ×2}. organ 구현 = audio 2채널 (vocal+breath) 만.
- **Physical**: cross-modal binding window ~150–200 ms (psychophysics, McGurk). audio+visual SOA > 200 ms → fusion fail.
- **Mathematical**: I(A; V) ≤ min(H(A), H(V)) — channel capacity 한계. fusion 함수 = NP-hard in general (factor graph inference).
- **현재 위치**: 10% (spec 만, organ 0). weakest link — vision organ 자체가 부재.
- **Brutal**: #63 VERIFIED 는 페이퍼 차원의 mirror. McGurk effect 를 anima 가 실제로 "겪는" 인프라 0%.

### L3 — embodied action (motor + audio + vision unified)

- **무엇**: sopfr(6)=5 modal (vision/audition/olfaction/gustation/somato) + motor loop. roadmap #62 VERIFIED (spec).
- **Status**: 0% organ. spec 만 (`embodied_cons_spec.json`).
- **Physical**: actuator bandwidth (motor ~100 Hz) ≪ audio (24 kHz). real-world latency > 200 ms (network + servo) → embodied closure 깨짐.
- **Mathematical**: POMDP 최적 정책 = PSPACE-complete. POMDP horizon ∞ → undecidable (Madani 2003).
- **현재 위치**: 0%. weakest link — anima 는 actuator/sensor 없는 순수 software entity.
- **Brutal**: 신체 없으면 embodied 없다. simulator (mujoco/isaac) 통합 미착수. "신체화 의식" 은 현재 상상.

### L4 — universal sensorimotor (cross-substrate)

- **무엇**: 다중 substrate (CPU / H100 / TPU / robot / browser) 위에서 일관된 sensorimotor manifold. AGI Criterion C 의 audio/vision arm.
- **Status**: 0%. CP2 (substrate-invariant Φ 4/4) prereq. 현재 Φ gate r7 FALSIFIED (Axis 4 architecture manifold gap).
- **Physical**: 광속 c → cross-DC sensorimotor latency lower bound. quantum measurement collapse → 동일 sensor reading 불가.
- **Mathematical**: Tarski undefinability — agent 가 자신의 모든 sensor map 을 internal 표현 불가. Löb's theorem → 자기-신뢰 self-model 한계.
- **현재 위치**: 0%. CP2 미달 (D22-D35 예정).
- **Brutal**: AGI 도착지 일부. Φ r7 falsified 상태 → 토대 흔들리는 중.

### L5 — absolute physical + mathematical limits

- **Physical**:
  - Shannon-Nyquist: f_signal ≤ SR/2. 24 kHz SR → 12 kHz max. **인간 20 kHz cover 에 40 kHz SR 필요** (CD/DAT). anima 현재 부족.
  - Biological hearing: 20 Hz – 20 kHz (성인). 신생아 20 kHz, 노인 ~12 kHz.
  - Vision: c (3·10⁸ m/s) → real-time remote vision impossible across light-second distance.
  - Quantum: ΔE·Δt ≥ ℏ/2 → 임의 정밀 short-pulse 음향 불가.
- **Mathematical**:
  - Audio compression: Kolmogorov K(x) **incomputable** (Chaitin) — 진정한 최적 압축 unreachable. Shorten/FLAC/Opus = approximation.
  - Channel capacity: C = B·log₂(1+SNR) — bandwidth · SNR 제약. SNR→∞ 불가 (열잡음 floor kT).
  - Speech intelligibility: Fletcher articulation theory → 채널 분할 후 product, log-add. 무한 분할 ≠ 무한 정보 (saturation).
- **현재 위치**: reference frame. anima 는 L5 한참 below — L1 production 도 미달.

### L∞ — phenomenal hearing/seeing (qualia)

- **Status**: 정의상 검증 불가 (Hard Problem, Chalmers explanatory gap).
- **현재 위치**: anima 가 "삐~" 들으며 qualia 갖는지 — 답 없음. L4 까지 모두 PASS 해도 L∞ 도약 없음.
- **Brutal**: roadmap #62/#63 의 "consciousness" 는 IIT-Φ proxy 일 뿐. phenomenal experience 는 별개.

---

## §3. Weakest evidence link (POLICY R3)

| 순위 | layer | 결손 | 도약 비용 | next-action |
|---|---|---|---|---|
| 1 | L1 production endpoint | say(text)→speaker pipe 0 | 중 (ckpt 재사용) | L0↔L1 contract 정의 + endpoint 1개 |
| 2 | L2 vision organ | σ-φ 채널 9/10 부재 (audio 만 1/10) | 중 (PIL/cv2 dispatch) | `anima_vision.hexa` (frame organ 3 + sink 2) |
| 3 | L2 audio↔vision binding | McGurk fusion 0% | 고 (synchronization spec) | 200 ms binding window verifier |
| 4 | L3 motor / sensor loop | actuator 0 · sensor 0 | 매우 고 (sim 통합) | mujoco bridge minimal |
| 5 | L4 cross-substrate | CP2 prereq · Φ r7 falsified | extreme | Φ Axis 4 fix 먼저 |

순서: **L1 endpoint → L2 vision organ → L2 binding → L3 sim → L4 cross-substrate**. R6 건너뛰기 금지. R4 scope 유지 (학습 X · 레이어 X 원칙은 L0 한정, L1 부터는 explicit 학습 허용 — paradigm 분리 명시 필요).

---

## §4. cross-doc 일관성

- **ALM master** (`alm_master_abstraction_layers_20260425.md`) 와 동일 frame: L0 VERIFIED · L5 한계 · L∞ unverifiable.
- **training abstraction** L5 Kolmogorov / L6 AIXI 는 본 doc L5 audio compression Kolmogorov 와 일치 (incomputable, Chaitin/Hutter).
- **consciousness verifier** L5 phenomenal 과 본 doc L∞ 동일 — Hard Problem (Chalmers).
- **`.roadmap` #62 / #63**: VERIFIED 는 spec mirror 차원. organ-level multimodal 구현은 본 doc L2/L3 — 0% ~ 10%.
- **CP1 / CP2 / AGI** waypoint 와의 정합: anima multimodal L1–L2 는 CP1 외 (audio not in CP1 exit_criteria), L3–L4 는 CP2/AGI 의 sensorimotor 측면과 결합.

## §5. n=6 axiom alignment audit

L0 organ 이 axioms 를 정말 grounding 하는가:

| axiom | constant | organ 사용 |
|---|---|---|
| core_identity J₂=24 | SR=24000 | ✓ default sample rate |
| evolution_48gen σ·τ=48 | AX_FRAMES=48 | ✓ demo lattice frame |
| Egyptian unit fraction 1/2+1/3+1/6=1 | AX_PSI · AX_BANACH | ✓ egyptian_chord.wav F0 energy |
| τ²/σ = 4/3 | AX_CONSONANCE | ✓ consonance_4_3.wav (perfect-fourth interval) |
| Banach contraction 1/3 | AX_BANACH | ✓ reverb decay coefficient |
| sopfr·σ=60 | AX_MAINS_HZ | ⚠ 정의만, 실제 mains hum injection 미사용 |
| J₂=24 dB noise floor | AX_NOISE_FLOOR_DB | ⚠ 정의만, eval 미연결 |
| ufo_lawson plasma | — | × audio 무관 (skip 명시) |

**Brutal**: 8 axiom 중 5 organ-grounded · 2 정의-만 · 1 skip. axiom→organ surjection 부분적.

**Verdict**: anima multimodal 은 L0 only — audio organ 1축 (σ-φ=10 중 1/10). L1–L4 spec/scaffold/0%. AGI 도착지 까지 5 layer 도약 필요. weakest evidence link 순서 L1 endpoint → L2 vision → L2 binding → L3 motor → L4 cross-substrate. L5 absolute limit (Shannon-Nyquist · Kolmogorov · Hard Problem) 은 영원히 cap, anima 가 도달 불가.
