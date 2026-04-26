# Mk.XII INTEGRATION substrate witness ledger **aggregator v2.1 prerequisite landing**

**Cycle ID**: `mk_xii_substrate_witness_ledger_aggregator_v2_1_prerequisite`
**Verdict**: `AGGREGATOR_V2_1_PREREQUISITE_LANDED`
**Date**: 2026-04-27
**Cost**: $0.00 (mac local, hexa-only — no cloud, no LLM, no GPU)
**Operating mode**: raw#9 hexa-only strict, raw#37 .py/.sh forbidden
**Resolves**: `mk_xii_ledger_v3_trigger_spec.md` §raw#10 honest §5 ("aggregator CLI flag 미검증 — prerequisite minor patch ... 본 spec 상 명시적 prerequisite")
**Supersedes / extends**: `mk_xii_substrate_witness_ledger_v2_landing.md` (commit `6559bb15`) — aggregator only, ledger v2 body unchanged

---

## 0. 1줄 요약

v3 trigger spec §raw#10 §5 가 명시한 silent-fail risk (aggregator hard-coded `LEDGER_VERSION="v2"`/`LEDGER_CYCLE_ID`/`LEDGER_SUPERSEDES` 가 v3 mode 에서도 v2 schema 로 박힘) 를 사용자 가입 도착 *이전*에 사전 차단. env-var override 4종 추가 + marker 자동 emission + G5-tier verdict 분기 도입. v2 byte-identical 회귀 PASS, v3 dry-run forward-compat PASS. **신규 코드 line 외 schema 변경 0** — v2 ledger body sha `df545c5e…` 그대로 보존.

---

## 1. v3 spec §2 1줄 명령 정정

spec §2 의 CLI flag 형식 (`--ledger-out=`/`--marker-out=`/`--version-tag=`) 은 v2 aggregator 가 argv 를 parse 하지 않는다는 사실로 *invalid* 임이 confirmed. v2.1 부터의 **실효 invocation 은 env-var 기반**:

```bash
cd /Users/ghost/core/anima && \
HEXA_RESOLVER_NO_REROUTE=1 \
LEDGER_VERSION=v3 \
LEDGER_OUT=state/v10_anima_physics_cloud_facade/integration_ledger/witness_ledger_v3.json \
MARKER_OUT=state/v10_anima_physics_cloud_facade/integration_ledger/marker_v3.json \
LEDGER_SUPERSEDES_OVERRIDE='v2 (witness_ledger_v2.json, fingerprint=661882989, body_sha=df545c5e15404539cea6f1b61c8d46565089f6d266277234b50a124d066e49ba)' \
~/.hx/packages/hexa/build/hexa.real run \
  anima-physics/tool/mk_xii_substrate_witness_ledger_aggregator_v2.hexa
```

`LEDGER_OUT`/`LEDGER_BASE_DIR` 는 v2 부터 이미 존재; v2.1 가 추가한 신규 4종은 다음과 같다:

| env var | default | 의미 |
|---|---|---|
| `LEDGER_VERSION` | `"v2"` | body/sidecar 의 `ledger_version` 필드 + `fnv32_chained_<VERSION>` 키 + verdict suffix (`LEDGER_LANDED_<UPPER>` / G5 tier) 분기 |
| `LEDGER_CYCLE_ID_OVERRIDE` | `"mk_xii_substrate_witness_ledger_<VERSION>"` | body 의 `cycle_id` (override 미설정 시 LEDGER_VERSION 으로 auto-derive) |
| `LEDGER_SUPERSEDES_OVERRIDE` | v1 chain string | body/sidecar 의 `supersedes` (v3+ caller 는 반드시 명시) |
| `MARKER_OUT` | `""` | 미설정 시 marker emission 스킵 (v2 byte-identical 보장); 설정 시 marker_v2 schema mirror + G5-tier verdict 자동 산출 |

---

## 2. v2 byte-identical 회귀 (regression PASS)

env var 없이 aggregator 재실행 → body sha 변경 0:

```
baseline body_sha:  df545c5e15404539cea6f1b61c8d46565089f6d266277234b50a124d066e49ba
re-run   body_sha:  df545c5e15404539cea6f1b61c8d46565089f6d266277234b50a124d066e49ba
diff -q (file vs baseline): IDENTICAL
verdict: LEDGER_LANDED_V2  (uppercase 보존)
```

v2 ledger body 의 어떤 필드도 v2.1 patch 이후 변경되지 않음 — frozen contract 유지.

> 미세 cosmetic: stdout 의 verdict 레이블이 패치 직후 `LEDGER_LANDED_v2` (소문자) 로 회귀했다가 `version_upper = "V" + version[1:]` derivation 추가 후 `LEDGER_LANDED_V2` 로 복원. 이 회귀는 stdout-only — 어떤 persisted file 에도 영향 없음. byte-identical 검증은 본 stdout 정정 *후* 측정값.

---

## 3. v3 dry-run forward-compat (synthetic LIVE PASS)

`/tmp/test_v3_base/` 에 11 marker symlink 복사 + `phase2_ibmq_runtime/marker.json::verdict` 만 `PHASE2_PASS_REAL_ibm_brisbane` 으로 합성하여 aggregator 를 v3 env 로 invoke:

```
LEDGER_BASE_DIR=/tmp/test_v3_base
LEDGER_OUT=/tmp/test_v3_ledger.json
MARKER_OUT=/tmp/test_v3_marker.json
LEDGER_VERSION=v3
LEDGER_SUPERSEDES_OVERRIDE='v2 (witness_ledger_v2.json, fingerprint=661882989, body_sha=df545c5e…)'
```

### 3.1 산출 검증

| 측정 항목 | 기대 | 실측 | 결과 |
|---|---|---|---|
| `live_hw_witness.n_live` | 1 | **1** | ✅ |
| `live_hw_witness.rate_x1000` | ≥ 90 (1/11 floor) | **90** | ✅ |
| `live_hw_witness.actual_backend_chip_ids` | `["ibm_brisbane"]` | **`["ibm_brisbane"]`** | ✅ |
| `tier_verdict` | `LEDGER_LIVE_INITIAL` (n_live ≥ 1) | **LEDGER_LIVE_INITIAL** | ✅ |
| `body.ledger_version` | `"v3"` | **"v3"** | ✅ |
| `body.cycle_id` | `mk_xii_substrate_witness_ledger_v3` (auto) | ✅ | ✅ |
| `body.supersedes` | env override v2 chain | ✅ | ✅ |
| `body.fnv32_chained_v3` (key name) | version-tagged | **`fnv32_chained_v3` 키 존재** | ✅ |
| body sha distinct from v2 | distinct | **`804d3cf932248b2f533f5f1b140395bc488e2266e51fa122e7548647369d07e9`** ≠ `df545c5e…` | ✅ |
| FNV-32 fingerprint distinct from v2 | distinct | **3407386720** ≠ 661882989 | ✅ |
| sidecar `ledger_version` literal | `"v3"` | ✅ | ✅ |
| sidecar `fnv32_chained_v3` (key) | version-tagged | ✅ | ✅ |
| marker `verdict` | `LEDGER_LIVE_INITIAL` | ✅ | ✅ |
| marker `gates.G5_threshold_active` | `true` (v3+) | ✅ | ✅ |
| marker `actual_backend_chip_ids` | `["ibm_brisbane"]` | ✅ | ✅ |
| **real v2 ledger 무손상** | `df545c5e…` 그대로 | **PASS** | ✅ |

### 3.2 v3 mode 2-run byte-identical

dry-run 을 동일 env 로 2회 invoke → body sha 동일:
```
run1 body_sha = run2 body_sha = 804d3cf932248b2f533f5f1b140395bc488e2266e51fa122e7548647369d07e9
diff -q (run1 vs run2): IDENTICAL
```

G3_LEDGER_BYTE_IDENTICAL 가 v2 와 동일한 방식으로 v3 에도 적용됨을 확인.

---

## 4. 신규 verdict tier 매핑 (G5 활성)

`LEDGER_VERSION != "v2"` 일 때 G5 threshold 활성:

| 조건 | tier_verdict |
|---|---|
| `n_live_hw ≥ 9` (effective 4/4 cloud-eligible) | `LEDGER_LIVE_FULL` |
| `n_live_hw ≥ 3` | `LEDGER_LIVE_BROAD` |
| `n_live_hw ≥ 1` | `LEDGER_LIVE_INITIAL` |
| `n_live_hw == 0` | `LEDGER_LIVE_NONE_DETECTED` (warning — v3 mode 에서 LIVE 0 은 trigger 조건 미충족) |
| G1∧G2 fail (전체) | `LEDGER_INCOMPLETE_<UPPER>` |

v2 default mode 는 무조건 `LEDGER_LANDED_V2` (G5 measure-only, no threshold).

> **Spec §4 와의 불일치 해소**: spec §4 의 rate-based 임계값 (`L1=⌈1/11×1000⌉=91`) vs 본 구현의 count-based (`n_live ≥ 1`). 정수 나눗셈상 1/11 = 90 (truncation) — rate-based 라면 90 < 91 이라 L1 미발동 위험. 본 구현은 count-based 로 명료성 확보 + spec intent 와 일치 (1개 cloud LIVE = INITIAL). spec §4 의 rate 표 는 *정보용* 으로 retain, 실제 분기는 count.

---

## 5. patch 변경 line summary

`anima-physics/tool/mk_xii_substrate_witness_ledger_aggregator_v2.hexa`:

- 헤더 주석 §ENV: 4 신규 env var 문서화 + v2 byte-identical guarantee 명시.
- §frozen schema constants: `LEDGER_VERSION`/`LEDGER_SUPERSEDES`/`LEDGER_CYCLE_ID` 상수 → `DEFAULT_LEDGER_VERSION`/`DEFAULT_LEDGER_SUPERSEDES`/`DEFAULT_LEDGER_CYCLE_PREFIX` 로 rename. `DEFAULT_OUT` 단일 path 상수 → `DEFAULT_OUT_DIR` (디렉터리만; 파일명은 version 별 auto-derive).
- `main()` 첫 8 line: env var resolution 7 line 추가 (LEDGER_VERSION → ledger_version → default_out → out_path 등).
- body emission (3 line): `LEDGER_VERSION`/`LEDGER_SUPERSEDES`/`LEDGER_CYCLE_ID` → `ledger_version`/`ledger_supers`/`ledger_cycle` 변수 사용.
- body fingerprint key (1 line): `"fnv32_chained_v2"` → `"fnv32_chained_" + ledger_version` (version-tagged key).
- sidecar emission (3 line): hardcoded `"v2"`/`LEDGER_SUPERSEDES`/`"fnv32_chained_v2"` → 변수 기반.
- §F2 G5-tier verdict 도입 (≈ 12 line): `version_upper` derivation + tier 매핑.
- §F3 marker emission block (≈ 38 line): `MARKER_OUT` 비어있지 않을 때 marker_v2 schema mirror 산출.
- stdout summary (4 line 추가): `marker_out`/`ledger_version`/`cycle_id` 필드 + `supersedes` 풀 출력.
- final VERDICT line: hardcoded `"LEDGER_LANDED_V2"` → `tier_verdict` 변수.

총 변경: **+78 line / -10 line** (신규 add-only schema, 기존 default 경로 byte-identical 유지).

---

## 6. 6-step ω-cycle 적용

| step | 본 cycle |
|---|---|
| 1. observe | aggregator hard-coded "v2" 6곳 (LEDGER_VERSION 상수, LEDGER_CYCLE_ID 상수, LEDGER_SUPERSEDES 상수, body fingerprint key, sidecar `ledger_version` literal, sidecar fnv32 key) — v3 mode silent-fail risk; spec §raw#10 §5 가 미리 식별 |
| 2. hypothesize | env-var override 4종 + marker emission + tier verdict 분기 → v3 mode 흡수 가능, v2 default 무손상 가능 |
| 3. design | DEFAULT_* 상수 + ledger_version 변수 + version_upper derivation + MARKER_OUT 조건부 block |
| 4. **falsify (defensive)** | (a) v2 byte-identical 2-run regression — sha `df545c5e…` 변경 0 verify; (b) v3 dry-run synthetic LIVE — `PHASE2_PASS_REAL_ibm_brisbane` 합성 → tier_verdict=LEDGER_LIVE_INITIAL + body sha distinct + real v2 ledger 무손상 verify; (c) v3 2-run byte-identical — sha `804d3cf9…` 동일 verify |
| 5. close | aggregator patch land + 본 doc + silent-land marker; v2 ledger body sha 미변경; v3 dry-run artifacts 휘발 (tmp, cleanup 완료) |
| 6. integrate | 사용자 cloud 가입 도착 시 `mk_xii_ledger_v3_trigger_spec.md` §2 (정정된 env-var form) 1줄 명령 그대로 발동 가능 — prerequisite 해소 |

---

## 7. raw#10 honest

본 patch 는 **frozen contract** 가 아니다 (aggregator code 변경 = behavioral diff). 다음 한계 명시:

1. **dry-run synthetic 의 한계**: `PHASE2_PASS_REAL_ibm_brisbane` 은 verdict 문자열만 합성; 실제 IBM Q backend 응답의 다른 marker 필드 (raw_probe_stdout_ghz, ghz_entropy_real_hw, shots > 0 등) 는 미검증. 실 LIVE 발생 시점에 sibling A `cloud_real_ibm_q_facade.hexa` 가 emit 하는 marker 가 본 verdict pattern + backend_name 을 정확히 land 하는지는 *그때 첫 검증*. 본 patch 는 aggregator 측 흡수 path 만 검증.

2. **G5 threshold count vs rate 불일치 해소**: spec §4 rate_x1000 ≥ 91 임계값과 본 구현 n_live ≥ 1 count 가 1/11 = 90 (truncation) 시점에 mismatch. count-based 가 명료하므로 본 구현 채택; rate 표는 *informational* 로 spec retain. 향후 spec v3.1 차원에서 표기 통일 권장.

3. **`MARKER_OUT` 미설정 시 v2 byte-identical 보장**: marker_v2.json 은 6559bb15 cycle 에서 **수동 land** 된 file. 본 patch 에 의한 자동 emission 은 v3 mode 전용. v2 caller 가 실수로 `MARKER_OUT` 을 v2 marker path 로 설정하면 hand-landed marker 가 덮어쓰임 (overwrite 위험). 운영상 mitigation: env-var 4종은 v3+ caller 만 사용; v2 재실행 시 모두 unset.

4. **CLI flag 미지원 final**: spec §2 `--ledger-out=` 형식은 v2.1 에서도 미구현. hexa script 가 argv 를 native 로 parse 하지 않는 구조. CLI flag 도입은 v2.2 또는 별도 wrapper script 위임. 본 cycle scope 외.

5. **schema 변경 0 의 의미 (key name 한정)**: body 내 `fnv32_chained_<VERSION>` 의 KEY 이름은 version 별로 다름 (`fnv32_chained_v2` → `fnv32_chained_v3`). 이는 schema 변경이 아닌 *version-tagged key* 패턴 (spec v2 landing doc 의 의도). v2 default mode 는 변경 0; v3 mode 는 새 key. 외부 consumer (atlas append 등) 가 `fnv32_chained_*` glob match 하도록 작성될 것을 가정.

6. **ENV 변수 LEDGER_VERSION 형식 가정**: "v2"/"v3"/"v3.1" 등 leading "v" + numeric. `version_upper = "V" + ledger_version[1:]` derivation 이 이 형식 가정. "ledger_v3.1_alpha" 같은 비표준 형식은 현재 `V3.1_ALPHA` 로 변환되어 verdict 가 `LEDGER_LIVE_INITIAL` (LIVE 시) 또는 `LEDGER_LANDED_V3.1_ALPHA` (no-live) 로 출력 — semantically OK 지만 atlas append 의 level 매핑이 LIVE_INITIAL 만 인식하는 점에 주의.

7. **G5 hardcoded denominator**: tier `LEDGER_LIVE_FULL` 의 임계값 `n_live ≥ 9` 는 *current 11-marker manifest* 기준. 향후 manifest 가 12+ rows 로 확장되면 (예: spec v3.1 에서 추가 substrate 추가), 본 임계값도 함께 갱신 필요. 본 cycle 은 11-row freeze.

8. **dry-run artifacts cleanup**: `/tmp/test_v3_base/` + `/tmp/test_v3_*.json` 모두 본 cycle 종료 시점에 `rm -rf` 됨. dry-run 검증 자체는 stdout 라인 (`G5_LIVE_HW_WITNESS_RATE: 1/11 (rate_x1000=90)` + `body_sha=804d3cf9…` + `VERDICT: LEDGER_LIVE_INITIAL`) 으로 본 doc §3 에 transcribe — repro 시 §3 절차 그대로 재현 가능.

9. **본 cycle 은 LIVE 가 아니다**: aggregator behavior 가 v3 mode 를 정상 흡수함을 *합성 입력으로* 검증한 것이지, 어떤 cloud 호출도 발생하지 않았다. G5 LIVE_HW_WITNESS_RATE 의 real 0/11 상태는 unchanged. **사용자 cloud 가입 + sibling A/D/E re-run 이 여전히 미해소 user-action**.

10. **commit 단위 결합도**: 본 patch 는 spec `04cee2c4` (v3 trigger spec) 에 명시적으로 의존; 단독으로는 보행 가능하나, 의미상 spec land 이후 실행 가능한 prerequisite. commit 메시지 + 본 doc 모두 spec commit `04cee2c4` reference.

---

## 8. 산출 file list

| # | path | 변경 type |
|---|---|---|
| 1 | `anima-physics/tool/mk_xii_substrate_witness_ledger_aggregator_v2.hexa` | **MODIFIED** (+78/-10 line, 6곳 핵심 변경) |
| 2 | `anima-physics/docs/mk_xii_substrate_witness_ledger_aggregator_v2_1_prerequisite_landing.md` | **NEW** (본 doc) |
| 3 | `state/v10_anima_physics_cloud_facade/integration_ledger/aggregator_v2_1_prerequisite_landed.json` | **NEW** silent-land marker |
| 4 | `state/v10_anima_physics_cloud_facade/integration_ledger/witness_ledger_v2.json` | **UNCHANGED** (body sha `df545c5e…` 보존, byte-identical regression PASS) |
| 5 | `state/v10_anima_physics_cloud_facade/integration_ledger/witness_ledger_v2.json.meta` | UNCHANGED (timestamp만 자연 변동, body_sha 동일) |
| 6 | `state/v10_anima_physics_cloud_facade/integration_ledger/marker_v2.json` | **UNCHANGED** (hand-landed v2 marker 보존) |

---

## 9. 다음 cycle (실 LIVE 후 사용자 trigger)

prerequisite resolved → spec §10 의 trigger 절차 그대로 가능:

1. 사용자: cloud 가입 (IBM Q free-tier 또는 AWS Braket budget cap 또는 BrainChip Akida).
2. 사용자: `IBM_QUANTUM_TOKEN` / AWS IAM keys / `BRAINCHIP_AKIDA_TOKEN` 환경변수 설정.
3. 사용자: sibling A/D/E `cloud_facade_poc.hexa` re-run (1 substrate 당 1회).
4. 사용자: `state/v10_anima_physics_cloud_facade/<sub_dir>/marker.json::verdict` 가 LIVE 패턴 매칭 확인 (`PHASE2_PASS_REAL_*` 또는 `LIVE_PASS`).
5. 사용자: 본 doc §1 의 정정된 1줄 env-var 명령 실행:
   ```bash
   cd /Users/ghost/core/anima && \
   HEXA_RESOLVER_NO_REROUTE=1 LEDGER_VERSION=v3 \
   LEDGER_OUT=state/v10_anima_physics_cloud_facade/integration_ledger/witness_ledger_v3.json \
   MARKER_OUT=state/v10_anima_physics_cloud_facade/integration_ledger/marker_v3.json \
   LEDGER_SUPERSEDES_OVERRIDE='v2 (witness_ledger_v2.json, fingerprint=661882989, body_sha=df545c5e15404539cea6f1b61c8d46565089f6d266277234b50a124d066e49ba)' \
   ~/.hx/packages/hexa/build/hexa.real run \
     anima-physics/tool/mk_xii_substrate_witness_ledger_aggregator_v2.hexa
   ```
6. spec §3 산출물 자동 생성: `witness_ledger_v3.json` + `.meta` + `marker_v3.json` (verdict=LEDGER_LIVE_INITIAL/BROAD/FULL).
7. atlas append 별도 cycle (sibling B precedent).

**예상 wallclock**: aggregator re-run < 5 sec; 사용자 cloud-side 는 signup 승인 / queue 시간에 의존.

---

## 10. 본 cycle marker (silent-land)

```
state/v10_anima_physics_cloud_facade/integration_ledger/aggregator_v2_1_prerequisite_landed.json
```

verdict: `AGGREGATOR_V2_1_PREREQUISITE_LANDED`
gates: aggregator patch in-place ∧ v2 byte-identical regression PASS ∧ v3 dry-run synthetic LIVE PASS ∧ v3 2-run byte-identical PASS ∧ real v2 ledger 무손상 ∧ §raw#10 10 항목 명시.

---

**End of v2.1 prerequisite landing.**
