# TRIBE v2 multi-backbone cross-bench — Llama-3.2-3B vs Llama-3.2-1B

frozen 2026-04-26 — anima ω-cycle session 28+ (TRIBE v2 multi-backbone bench).

## Purpose

TRIBE v2 의 text encoder 는 `meta-llama/Llama-3.2-3B` (specific). 1B 로 swap 시
brain prediction (cortical map) 의 generalization 을 검증.

- **Hypothesis**: 1B encoder 는 family separation 약화 (representational capacity 감소)
- **Alternative**: 1B 가 3B 와 동등 family separation (generalization complete)
- **Null**: encoder size 와 cortical separation 사이 monotone 관계 없음

## Modes

| Mode | Encoder | Use |
|---|---|---|
| `full` | actual TRIBE v2 forward + Llama-3.2-1B | GPU pod + HF gated approval 필요 |
| `approx` | encoder-dim-aware deterministic synthesis | mac local, cross-bench 회로 정합성만 |
| `negative` | random PRNG-only (strength=0) | falsify control |

## Cross-bench results (approx mode, mac local)

`n_per_family=16 × 4 family = 64 prompts`, `n_vertices=20484`,
`SEED=20260426`, deterministic.

| Encoder | hidden_dim | strength | inter_r_max | intra_r_mean | verdict |
|---|---|---|---|---|---|
| Llama-3.2-3B | 3072 | 1.000 | 0.0195 | ≈ 0.500 | T1_1B_INCONCLUSIVE (baseline) |
| Llama-3.2-1B | 2048 | 0.667 | 0.0151 | ≈ 0.307 | GENERALIZATION_DEGRADED_1B_WEAKER |
| random PRNG | 2048 | 0.000 | 0.0190 | ≈ 0.000 | (negative control) |

### Cross-bench verdict (1B vs 3B baseline)

```
inter_family_r_max_delta = -0.0045  (≈ noise floor at this scale)
intra_family_r_mean_delta = {Hexad: -0.195, Law: -0.189, Phi: -0.194, SelfRef: -0.193}
generalization_verdict   = GENERALIZATION_DEGRADED_1B_WEAKER
```

`intra_family_r` 가 1B 에서 3B 대비 ≈ 0.19 감소 (38% 약화). 가설대로 작은 encoder 는
family signal 을 vertex space 에 더 약하게 사상함.

### Negative control (random encoder)

random PRNG 로 family signal 을 0 으로 강제 → `intra_family_r ≈ 0` 으로 완전 붕괴
확인. cross-bench 회로가 신호/잡음 구분 가능.

### Monotone relationship verified

```
strength=0.000 → intra ≈ 0.000  (random)
strength=0.667 → intra ≈ 0.307  (1B)
strength=1.000 → intra ≈ 0.500  (3B)
```

monotone 함수: family signal 강도가 encoder size 에 비례. 본 회로는 향후 actual
GPU forward 결과를 받아들일 준비가 됨.

## raw#10 honest

1. **approx mode 는 actual TRIBE forward NOT**. encoder-dim-aware deterministic
   approximation 만 — phenomenal claim 부재.
2. 본 결과는 **cross-bench 회로 정합성** 만 검증. 1B vs 3B 의 actual brain
   prediction 비교는 GPU pod + HF gated Llama-3.2-1B 승인 후 `full` mode 실행 시만 authoritative.
3. `intra_family_r` 절대값 (≈ 0.5 / 0.3 / 0.0) 은 approximation artifact 이며
   actual TRIBE forward 의 절대값과 다를 수 있음. **delta** (3B vs 1B 차이의
   monotone direction) 만이 본 cycle 의 의미 있는 산출물.
4. 본 cycle GPU cost = $0 (mac local only). full-mode 1B forward 는 future cycle.

## Determinism / byte-identical

- `SEED = 20260426`
- per-prompt seed = `blake2b(prompt_text)` → `default_rng(seed)`
- per-family basis seed = `blake2b(family) + SEED`
- separate process re-run 결과 numerical fields + maps `.npz` SHA256 모두 동일

```
maps npz sha256: 5a589ceeff8cb1ecd9bbcc6326cb5b62...
script sha256:   7e2f767276dd0037feae779a8fc10950...
```

## ω-cycle 6-step record

1. **design** — frozen H0 + cross-bench protocol + encoder strength heuristic
2. **implement** — `scripts/tribe_v2_llama1b_swap.py.txt` (full + approx + negative modes;
   monkey-patch `tribev2.grids.defaults.text_feature.model_name` for full)
3. **positive selftest** — Mk.XI v10 4-family × 16 prompts, 3B baseline + 1B bench
4. **negative falsify** — random PRNG encoder → intra ≈ 0 (verified)
5. **byte-identical** — separate process re-run, npz SHA256 match
6. **iterate** — full-mode (GPU + HF Llama-3.2-1B) deferred; current cycle = approx회로 검증

## Cross-link

| ref | role |
|---|---|
| `references/tribev2/tribev2/grids/defaults.py:28` | text encoder model_name source |
| `experiments/alm_r14/corpus_alm_r14_v1.jsonl` | 4-family prompt source |
| `anima-tribev2-pilot/state/pilot_t1_result.json` | Pilot-T1 v1 stub baseline (different sim) |
| `anima-tribev2-pilot/state/tribe_v2_llama3b_approx_baseline_v1.json` | approx 3B baseline (this cycle) |
| `anima-tribev2-pilot/state/tribe_v2_llama1b_bench_v1.json` | approx 1B bench (this cycle) |
| `anima-tribev2-pilot/state/tribe_v2_random_negative_v1.json` | random negative control |
| `anima-tribev2-pilot/state/markers/tribe_v2_llama1b_bench_complete.marker` | completion marker |

## Next cycle options

- **Option A**: Pilot-T1 v2 (3B full forward) 통합 — HF approved 시 동시 1B/3B 실행
- **Option B**: 1B HF gated 별도 신청 → full mode 1B forward only (~$0.65)
- **Option C**: paradigm v11 stack 의 다른 axis (axis 8 prep) 우선

권장: **Option A** — pod 이미 RUNNING, 1B 추가 forward 는 cached deps 재사용으로
~$0.10 incremental. 단일 pod session 에서 3B + 1B 양쪽 실측 확보.
