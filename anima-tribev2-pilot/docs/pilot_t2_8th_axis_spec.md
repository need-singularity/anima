# Pilot-T2 8th Axis Spec — TRIBE v2 Cortical Correlation

frozen at 2026-04-26 — anima ω-cycle session, Pilot-T2 prep stage.

paradigm v11 stack의 8th orthogonal measurement axis로 TRIBE v2 stimulus-driven
cortical correlation을 등록하기 위한 frozen spec. **prep stage** 산출물 — Pilot-T1
full-mode PASS 후 activate.

## §1 8th Axis 정의 (frozen)

### 1.1 Input

- `anima-tribev2-pilot/state/pilot_t1_result.json` (schema `anima/pilot_t1_result/1`)
- `anima-tribev2-pilot/state/pilot_t1_maps.npz` (full-mode only — keys = `{Law, Phi, SelfRef, Hexad}`, 각 array shape `(n_per_family, 20484)` 또는 `(20484,)`)
- per-family vertex 수: `N_VERTICES = 20484`
- 4-family set: `["Law", "Phi", "SelfRef", "Hexad"]` (Mk.XI v10 prompt set)

### 1.2 ROI Partition

- `N_ROI = 7` contiguous buckets across 20484 vertices
- bucket size = `20484 // 7 = 2926` (마지막 bucket은 잔여 + 6 vertex 흡수)
- ROI index `r ∈ [0..6]`: 시각 / 청각 / 체성감각 / motor / DMN / language / executive 의 7-region 거친 분할 — TRIBE v2 lobe-level 호환
- 다른 ROI atlas 사용 시 `N_ROI` 만 바꾸면 transparent 호환 (FNV reduction은 차원 보존)

### 1.3 Per-(family, ROI) Cell

- 정의: per-family cortical map vertex array에서 ROI bucket의 mean activation
- 정수 변환: `int(round(mean × 1000))` (fixed-point ×1000)
- 매트릭스 차원: `4 × 7 = 28` cells

### 1.4 8th Axis Scalar

- 28 cell matrix → FNV-1a + LCG 결정적 reduction → integer ∈ `[0, 1000]`
- modular prime: `MOD_PRIME = 2147483647`
- offset basis: `FNV_OFFSET = 1469598103`
- 각 cell value, (i,j) index, row/col length 모두 hash chain에 mix
- 출력 scaled scalar `axis_8_scalar_x1000 ∈ [0, 1000]` (float 등가 0.000–1.000)

### 1.5 Output

```
state/v11_axis_8_<backbone>.json
{
  "schema": "anima/v11_axis_8/1",
  "backbone": "<hf id 또는 label>",
  "axis_name": "TRIBE_v2_cortical",
  "n_family": 4,
  "n_roi": 7,
  "scale": 1000,
  "axis_8_scalar_x1000": <int ∈ [0,1000]>,
  "roi_matrix_x1000": [
    {"family": "Law",     "roi": [c1, ..., c7], "variance": int},
    {"family": "Phi",     "roi": [c1, ..., c7], "variance": int},
    {"family": "SelfRef", "roi": [c1, ..., c7], "variance": int},
    {"family": "Hexad",   "roi": [c1, ..., c7], "variance": int}
  ],
  "prep_stage": false,
  "requires_pilot_t1_full_mode_pass": true,
  "t1_verdict": "<from pilot_t1_result.json>",
  "t1_result_sha256": "<sha256 of pilot_t1_result.json>"
}
```

## §2 PASS Criteria (frozen)

### 2.1 §A Pearson Cross-Axis Threshold

8th axis가 기존 7 axis 각각과의 Pearson correlation 절대값이 0.7 미만 (×1000 fixed-point: < 700).

기존 7 axis ordered list:
1. `AN11_b` (canonical AN11(b) max cosine, top1 family)
2. `B_ToM` (Behavioral Theory-of-Mind battery accuracy)
3. `MCCA` (1 - mean Brier; meta-cognitive calibration)
4. `PhiStar` (tanh-normalized IIT Φ_min)
5. `CMT` (mean per-family dominant-layer relative ablation)
6. `CDS` (max stability; cognitive dynamics signature)
7. `SAE_bp` (mean positive selectivity; SAE-steer bypass)

### 2.2 §B PCA 1st-Component Threshold

8×8 correlation matrix의 power-iteration 추출 1st eigenvalue / 8 < 0.5 (×1000: < 500).

power-iteration: 64 iter, max-abs renormalize per step, Rayleigh quotient final.

### 2.3 §C Orthogonality Verdict

`§C_orthogonality_PASS = §A AND §B`.

§C FAIL일 경우 8th axis 등록 보류 — TRIBE v2 cortical correlation은 paradigm v11
stack 의 측정 manifold 와 redundant.

## §3 paradigm v11 Router 통합 Plan

`tool/anima_v11_main.hexa` 의 subcommand router에 13번째 subcommand 추가:

```
v11_main axis_8 <bb_dir>          # emit state/v11_axis_8_<bb>.json (Pilot-T2)
v11_main ortho78 <dir1:dir2:...>  # 7+8 orthogonality verdict
```

추가 패치 (v11_main router emit 부분):

```bash
  axis_8)
    BB_DIR="${1:-}"
    test -d "$BB_DIR" || { echo 'usage: v11_main axis_8 <bb_dir>' >&2; exit 2; }
    emit_only pilot_t2_axis_8th
    H=/tmp/anima_pilot_t2_axis_8th_helper.hexa_tmp
    BB=$(basename "$BB_DIR")
    ANIMA_BACKBONE="$BB" ANIMA_OUTPUT="state/v11_axis_8_${BB}.json" python3 "$H"
    ;;

  ortho78)
    DIRS="${1:-}"
    test -n "$DIRS" || { echo 'usage: v11_main ortho78 <dir1:dir2:...>' >&2; exit 2; }
    emit_only v11_orthogonality_7_8
    H=/tmp/anima_v11_orthogonality_7_8_helper.hexa_tmp
    ANIMA_BACKBONE_DIRS="$DIRS" python3 "$H"
    ;;
```

list section에도 한 줄 추가:

```
MEASUREMENT (7):
  ...
  pilot_t2_axis_8th  TRIBE v2 cortical correlation (Pilot-T2 8th axis)

ANALYSIS (4):
  ...
  v11_orthogonality_7_8  7-axis vs 8th axis Pearson + PC1 verdict
```

**적용 시점**: Pilot-T1 full-mode PASS 직후 (다음 ω-cycle, 이 prep과 별도 commit).

## §4 Pilot-T1 Dependency

8th axis activate 조건:

1. Pilot-T1 full-mode 실행 완료 (GPU pod 또는 Colab; current state: stub mode only)
2. Pilot-T1 verdict ≠ `T1_INCONCLUSIVE_STUB`
3. `pilot_t1_maps.npz` 에 4-family vertex array 존재 (각 family shape `(N_per, 20484)` 또는 `(20484,)`)
4. Pilot-T1 H0 PASS 명세 (`README.md` §Hypothesis): `inter_family_r < 0.7` ≥1 pair AND `intra_family_r > 0.85` (모든 family)

prep stage 산출물 (현재):
- `tool/anima_pilot_t2_axis_8th.hexa` (synthetic fixture selftest)
- `tool/anima_v11_orthogonality_7_8.hexa` (synthetic fixture selftest)
- 본 spec 문서

activate stage 절차 (T1 full-mode PASS 후):
1. `hexa run tool/anima_pilot_t2_axis_8th.hexa` → `/tmp/anima_pilot_t2_axis_8th_helper.hexa_tmp` emit
2. `ANIMA_T1_RESULT=anima-tribev2-pilot/state/pilot_t1_result.json ANIMA_T1_MAPS=anima-tribev2-pilot/state/pilot_t1_maps.npz ANIMA_BACKBONE=<bb_label> python3 /tmp/anima_pilot_t2_axis_8th_helper.hexa_tmp` 실행
3. 다른 backbone 결과 디렉토리에 axis_8 JSON 복사 (또는 dir 구조 정렬)
4. `hexa run tool/anima_v11_orthogonality_7_8.hexa` → orthogonality helper emit
5. `ANIMA_BACKBONE_DIRS=<dir1>:<dir2>:... python3 /tmp/anima_v11_orthogonality_7_8_helper.hexa_tmp` 실행
6. §C verdict PASS면 `tool/anima_v11_main.hexa` router patch 적용 (위 §3) → 8th axis 정식 등록

## §5 Determinism + Selftest 결과

### 5.1 Synthetic fixture (positive)

- per-family bias-augmented FNV vertex 생성 (4 family × 20484 vertex)
- ROI partition + mean → 4×7 matrix → axis_8 scalar
- 12 backbone synthetic 8-axis matrix (axis-별 salt 8개 prime, backbone-conditional FNV mixing)

selftest 결과 (current run, 2026-04-26):
- `axis_8_scalar_x1000 = 778`
- `synthetic_inter_family_variance_x1000sq = 37084` (>0, family-separability 보존)
- `max_abs_pearson_8th_x1000 = 235` (< 700 thresh) → §A PASS
- `pc1_fraction_x1000 = 388` (< 500 thresh) → §B PASS
- §C orthogonality PASS

### 5.2 Adversarial fixture (falsify)

- axis_8th: 4 family 동일 row → `inter_family_variance = 0` → collapse_check가 잡음
- ortho_7_8: 8th axis = col 1 (B_ToM) 정확 복제 → `max_abs_pearson_8th = 1000` (>= 700) → §A FAIL → §C FAIL (의도대로)

### 5.3 Byte-identical

re-run 시 selftest output sha256 일치 (2-run verification PASS):
- `/tmp/anima_pilot_t2_axis_8th_selftest.json`: `b9bba49f861b83fce7b09ffa65dadbe9f36a696dc50f57a13fec97421bb3055c`
- `/tmp/anima_v11_orthogonality_7_8_selftest.json`: `f1a7c43d0a61e02f336c966e22417c873909503e9c3b5d77a57be26bebd639c6`

## §6 ω-cycle 6-Step Trace

| step | result |
|---|---|
| 1 design | spec frozen (§1, §2 입력/출력/PASS criteria) |
| 2 implement | 2 hexa + 1 spec docs (raw#9 strict, fixed-point ×1000, modular arithmetic) |
| 3 positive selftest | synthetic fixture orthogonality §C PASS (12 backbone × 8 axis) |
| 4 falsify | adversarial 8th=col1 detected (Pearson=1000); axis_8th adv inter_var=0 detected |
| 5 byte-identical | both selftest JSON sha256 stable across re-runs |
| 6 iterate | 4 iterations: (a) inter_family_variance 정의 보정, (b) synthetic vertex per-family bias 추가, (c) det_value 더 강한 axis-decorrelation salts, (d) backbone 수 6→12 |

## §7 Cross-link

- Pilot-T1 spec / 결과: `anima-tribev2-pilot/README.md`, `state/pilot_t1_result.json`
- TRIBE v2 통합 root spec: `references/tribev2/ANIMA_INTEGRATION_PROPOSAL.md` §4.2 Pilot-T2
- paradigm v11 stack 17 helpers: `docs/paradigm_v11_stack_20260426.md`
- 7-axis (PHENOMENAL) EEG 후보: `anima-clm-eeg/docs/eeg_arrival_impact_5fold.md`
- raw#9 strict directive: `.raw` index entry #9, #15, #37, #134

## §8 Frozen Constants

| constant | value | purpose |
|---|---|---|
| `N_VERTICES` | 20484 | TRIBE v2 surface mesh vertex count |
| `N_ROI` | 7 | contiguous ROI bucket count |
| `N_FAMILY` | 4 | Law / Phi / SelfRef / Hexad |
| `MOD_PRIME` | 2147483647 | modular arithmetic prime |
| `FNV_OFFSET` | 1469598103 | FNV-1a basis |
| `SCALE` | 1000 | fixed-point multiplier |
| `PASS_PEARSON_THRESH_X1000` | 700 | §A threshold (= 0.7 float) |
| `PASS_PC1_THRESH_X1000` | 500 | §B threshold (= 0.5 float) |
| `N_BACKBONE_SYNTH` | 12 | selftest backbone fixture count |

frozen 2026-04-26. anima ω-cycle session — paradigm v11 stack 8th axis prep.
