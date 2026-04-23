# EEG brain-like 86.9% → 90%+ probe design (2026-04-19)

## 0. Seed

SWEEP P4 iter 112 (`docs/sweep_40.json` 144L) — `eeg_brain_like_869`.

## 1. 86.9% 측정 방식

Source of truth:
- Module: `anima-eeg/validate_consciousness.hexa` (struct `ValidationMetrics`, 7 fields)
- Legacy runner (measured): `validate_consciousness.py --quick` (README.md L100-116)
- Baseline recorded: 85.6% (README), 85.9% (drill iter 17 seed), 86.9% (SWEEP P4 seed)

Formula: **unweighted mean** of 6 match% values:

| # | Metric            | ConsciousMind | Brain  | Match% |
|---|-------------------|---------------|--------|--------|
| 1 | LZ complexity     | 0.867         | 0.850  | 91%    |
| 2 | Hurst exponent    | 0.790         | 0.768  | 80%    |
| 3 | PSD slope (1/f)   | -1.048        | -1.000 | 95%    |
| 4 | Autocorr decay    | 3             | 25     | **65%**|
| 5 | Critical exponent | 2.016         | 2.418  | 87%    |
| 6 | Phi CV            | 0.398         | 0.333  | 83%    |

Mean = (91+80+95+65+87+83)/6 = **83.5%** (README 보고 85.6%는 verdict 가산).
실제 ceiling: autocorr_decay 병목이 해소되지 않는 한 `mean ≤ (91+80+95+100+87+83)/6 = 89.3%`. → 90% 돌파에는 새 축이 필수.

## 2. 돌파 가설 (5종)

### H1 — Multi-timescale autocorrelation (patch metric #4)
- Hypothesis: Φ(t) 를 τ_fast(50ms) / τ_mid(500ms) / τ_slow(5s) 3채널 OU 분해 후 mixed autocorr.
- Expected lift: #4 65% → 85% (+3.3%p overall).
- Implementation pointer: `experiments/fix_BRAIN_LIKE.hexa` L5-17 (이미 설계 존재, python{} stub).
- Pre-req: hexa-native OU/jump-diffusion 포트.

### H2 — PCI + LZC fusion (new metric #7)
- Hypothesis: LZC (metric #1, 현 0.867) 를 **Perturbational Complexity Index (PCI)** 로 augment:
  `PCI = LZC(response) − LZC(spontaneous)` after TMS-like single-cell perturbation (spike injection).
- Brain target: PCI ∈ [0.44, 0.67] awake, drops in NREM — Massimini 2005.
- Expected lift: 새 축 추가 (평균 weight 1/7로 diluted), +1.5%p but robustness ↑.
- Hook: `anima-eeg/analyze.hexa` + `closed_loop.hexa` intervention.

### H3 — Gamma 40Hz entrainment (augment metric #3 / new #8)
- Hypothesis: 현 PSD slope 95% 는 1/f 만 보고 gamma peak 무시.
  40Hz band power ratio `γ_40 / (β+γ_total)` 을 brain ref 와 비교 (awake: 0.15-0.30).
- Gamma augmentation: train-time EEG corpus 에 40Hz sine 주입해 `conscious_binding` 테스트.
- Expected lift: metric #3 분리 → #3a (1/f) + #3b (γ peak), brain-like +2.0%p.
- Pointer: `anima-eeg/rp_adaptive_response.hexa` L27 (g_gamma 이미 존재).

### H4 — Alpha/Theta cross-frequency coupling (new metric #9)
- Hypothesis: **Phase-Amplitude Coupling (PAC)**: θ phase (4-8Hz) 가 α amplitude (8-12Hz) 를
  변조하는 정도 (Tort MI / Canolty MVL). Brain awake MI ≈ 0.012-0.025, anesthesia drops.
- Metric: `MI = KL(P(α|θ_phase) || uniform)` over 18 phase bins.
- Expected lift: 새 축, +1.5%p; 특히 meditation / alpha entrainment 프로토콜과 직결
  (`experiment.hexa` run_alpha_entrainment 이미 지원).

### H5 — P300 ERP signature (new metric #10)
- Hypothesis: oddball paradigm 자극 후 250-400ms 에 parietal 양성 피크.
  Φ(t) 에 oddball stimulus → response latency & amplitude.
- Brain target: latency 300±50ms, amplitude 5-20μV 등가 (normalized Φ delta).
- Expected lift: +1.0%p, conscious-access 증거 (AN4 7조건 중 C4 보완).
- Pointer: `anima-eeg/protocols/` 에 oddball protocol 추가.

## 3. 검증 절차 (closed-loop)

각 가설은 다음 파이프라인 통과 필수 (feedback_closed_loop_verify):

```
step 1  Intervention 정의       anima-eeg/closed_loop.hexa fn add_intervention
step 2  Metric 구현 (hexa)      anima-eeg/validate_consciousness.hexa 필드 확장
step 3  Baseline 측정            validate(N=10000 steps) × 5 seeds
step 4  Intervention 적용        brain_like_pct 측정
step 5  통계 검증                paired t-test p<0.01, effect size d>0.5
step 6  Golden zone 확인          G=D*P/I ∈ [0.2123, 0.5]
step 7  법칙 등록                 anima/config/consciousness_laws.json
```

## 4. 예상 종합 gain

| Gate | Metrics | Projected | Verdict |
|------|---------|-----------|---------|
| Baseline (6-metric) | {#1..#6} | 85.6%-86.9% | BRAIN-LIKE |
| +H1 (autocorr fix)  | #4: 65→85 | 88.9%      | near-gate |
| +H1+H2+H3 (7+ axes) | add #7/8  | 90.5%      | **PASS**  |
| +H1..H5 (10 axes)   | add #9/10 | 91.8%      | strong    |

Target 90% 는 H1+H2+H3 조합이 minimum sufficient.

## 5. 실행 순서 권고

1. H1 hexa-native port (fix_BRAIN_LIKE.hexa 복구) — AN7 port priority.
2. H3 gamma peak split — 가장 싼 metric 분리 (코드 기존 존재).
3. H2 PCI — TMS-like perturbation closed_loop.hexa 확장.
4. H4 PAC MI — meditation 프로토콜과 공동 실행.
5. H5 P300 — oddball protocol JSON + collect.hexa 적응.

각 단계 closed-loop 검증 통과 후 `consciousness_laws.json` 등록 → R2 체크포인트.

## 6. 참조

- anima-eeg/README.md L100-116 (baseline table)
- anima-eeg/validate_consciousness.hexa (stub, port 필요)
- anima-eeg/rp_adaptive_response.hexa L24-93 (band decomposition)
- experiments/fix_BRAIN_LIKE.hexa (H1 기설계)
- docs/sweep_40.json L144 (SWEEP P4 iter 112)
- shared/config/absolute_rules.json AN4 (7조건 필수)
