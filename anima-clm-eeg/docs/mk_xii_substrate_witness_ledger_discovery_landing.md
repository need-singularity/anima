# Mk.XII Substrate Witness Ledger — Discovery & Integration Landing

> **scope**: 메인 세션이 launch 하지 않은 산출물의 disk discovery + 통합 분석
> **session date**: 2026-04-26
> **cycle id**: `mk_xii_substrate_witness_ledger_discovery`
> **verdict**: `DISCOVERY_LANDED — INTEGRATION RECOMMENDED (PARTIAL)`
> **cost**: $0 (mac-local, read-only, no GPU/LLM/network)
> **raw**: raw#9 hexa-only (data layer; this doc = docs-tier 완화) · raw#10 honest scope · raw#12 cherry-pick-proof (frozen verdicts, read-only) · raw#15 SSOT
> **discovery trigger**: disk-poll 4 marker (`state/markers/mk_xii_substrate_witness_ledger_aggregator{,_v2}_*.marker`)

---

## §1. 4 Marker 내용 + sha

자동 marker (hexa-lang `auto_marker` patch #37 a66167ba 가 emit 한 것으로 추정).

| # | path (relative to `/Users/ghost/core/anima/`) | sha256 | source ref | fingerprint | ts |
|---|---|---|---|---|---|
| 1 | `state/markers/mk_xii_substrate_witness_ledger_aggregator_1777218041.marker` | `4b49a9576ab9356934f681443fb40fd39980f6ea75f58453b126bbca7b3c4183` | `anima-physics/tool/mk_xii_substrate_witness_ledger_aggregator.hexa` | `159cbcaf` | 1777218041 |
| 2 | `state/markers/mk_xii_substrate_witness_ledger_aggregator_1777218044.marker` | `57c6e7918d4dccf410e7b914d23f78d9841cb5b47a2108d8f09ea6025f35ece6` | `anima-physics/tool/mk_xii_substrate_witness_ledger_aggregator.hexa` | `159cbcaf` | 1777218044 |
| 3 | `state/markers/mk_xii_substrate_witness_ledger_aggregator_1777218963.marker` | `0576adf6c0266b7dfef2f544f5379908fb1a3e94aab0dce6a9d333fff40f7cfd` | `anima-physics/tool/mk_xii_substrate_witness_ledger_aggregator.hexa` | `159cbcaf` | 1777218963 |
| 4 | `state/markers/mk_xii_substrate_witness_ledger_aggregator_v2_1777218940.marker` | `262714601c34d9ddcb38dc56546971b4338085abdcd76df763eb8a6e91fb4f1e` | `anima-physics/tool/mk_xii_substrate_witness_ledger_aggregator_v2.hexa` | `ec18567a` | 1777218940 |

핵심 관찰:
- v1 aggregator는 **동일 fingerprint=`159cbcaf`** 로 3 차례 실행 (ts gap 0:03 sec / 22 min apart). G3 byte-identical 자기검증과 일관 — **소스 변경 0** + **반복 실행 deterministic** (재실행해도 hexa source sha 안정).
- v2 fingerprint=`ec18567a` 별개 — v1 → v2 source 변경 reflect.
- v2 marker (1777218940) 가 v1 마지막 marker (1777218963) 보다 **23 초 먼저** — 즉, v2 land 후 v1 byte-identical re-verify 가 마지막에 한 번 더 돌아간 흐름.

---

## §2. 산출물 disk find 결과

### §2.1 Hexa source (read-only, NOT modified by this cycle)

| file | sha256 | bytes | mtime |
|---|---|---|---|
| `anima-physics/tool/mk_xii_substrate_witness_ledger_aggregator.hexa` | `1c1e3bea36d225b141dd9e3ef8b138c19d640ddd2a3790334fba707d89938946` | 26627 | 2026-04-27 00:40 |
| `anima-physics/tool/mk_xii_substrate_witness_ledger_aggregator_v2.hexa` | `0fff9a986543df1cc25cf046bfd4ee6074f37357569d01a8ac2db62112db5e6f` | 32074 | 2026-04-27 00:55 |

raw#9 strict (hexa-only, no .py / .sh exec). v1 = 4 frozen ledger gate (G1-G4), v2 = 5 gate (G1-G5 추가, LIVE_HW_WITNESS_RATE).

### §2.2 Landing docs (read-only)

| file | sha256 | bytes |
|---|---|---|
| `anima-physics/docs/mk_xii_substrate_witness_ledger_landing.md` | `0461c65d02d9e8dd0b32c633a00ac18fb28214fa7a82f0a73f2b50aa4fd79708` | 14117 |
| `anima-physics/docs/mk_xii_substrate_witness_ledger_v2_landing.md` | `da2418951d1415043548442ed1dcf3a955b2f2dd693c713a03971acf431f4c5c` | 10518 |

### §2.3 State JSON output (ledger payload + sidecar + integration marker)

| file | sha256 | bytes |
|---|---|---|
| `state/v10_anima_physics_cloud_facade/integration_ledger/witness_ledger_v1.json` | `264f5cf7770d8b08e63b0d62d15636eb36262597aae012b3a3ec0e9c65274836` | 7611 |
| `state/v10_anima_physics_cloud_facade/integration_ledger/witness_ledger_v1.json.meta` | `57c8722759f21db3ae1318d6b159331a5921fa386af1141e5d972635b1f21882` | 261 |
| `state/v10_anima_physics_cloud_facade/integration_ledger/marker.json` (v1) | `f534638b6885b5bc4c8e5e6e15b4123498877f490a7d333c1e796d300c4d2efd` | 5118 |
| `state/v10_anima_physics_cloud_facade/integration_ledger/witness_ledger_v2.json` | `df545c5e15404539cea6f1b61c8d46565089f6d266277234b50a124d066e49ba` | 11482 |
| `state/v10_anima_physics_cloud_facade/integration_ledger/witness_ledger_v2.json.meta` | `adedf2b9919c8759a283c5f67d5b962cbd44296d2e785096e303d4a6572168ac` | 431 |
| `state/v10_anima_physics_cloud_facade/integration_ledger/marker_v2.json` | `c79c8b92f2e510a68098a09b3a45bc96e7be90209706755db76d900447386acf` | 6410 |

ledger v1 body sha (`264f5cf7…`) + ledger v2 body sha (`df545c5e1540…`) = landing doc 내 명시된 byte-identical 검증값과 **완전 일치**. G3 LEDGER_BYTE_IDENTICAL **외부 verifiable**.

---

## §3. v1 vs v2 차이 (frozen)

| Axis | v1 | v2 |
|---|---|---|
| Manifest rows | 8 | 11 (+ cmos / fpga / arduino) |
| Distinct substrate count | 6 + 1 meta(integration) | **9 + 1 meta** (full Mk.XII substrate enum) |
| Ledger gates | G1-G4 | **G1-G5** (+ `LIVE_HW_WITNESS_RATE` measure-only) |
| Schema fields | base | + `supersedes`, `n_marker_total`, `phi_proxy_cross_comparable`, `live_hw_witness{}`, `fnv32_chained_v2` |
| FNV-32 fingerprint | `470781997` (8 inputs) | `661882989` (11 inputs) — distinct hash space |
| Body SHA-256 | `264f5cf7…` | `df545c5e1540…` |
| live_hw_witness rate | (not measured) | **0 / 11** (measure-only floor) |
| Coverage gate (G1) | 7/9 PASS (`actual_x1000=7000`) | **9/9 PASS** (`actual_x1000=9000`) |
| Verdict tier 보존 | 6 tier | **6 tier identical** (G2 honesty 유지) |
| 4-gate per-entry pass rate (×1000) | 625 (5/8) | **727** (8/11; 4 PREP/PHASE2 잔존) |

핵심:
- v2 = **forward-compatible superset** (v1 본 보존; supersession ≠ deletion). v1 ledger 본 + meta 양쪽 disk 그대로.
- **9/9 substrate distinct cover 달성** = Mk.XII INTEGRATION axis substrate-multiplicity sub-axis 의 첫 9-target completeness.
- LIVE 0/11 = **honest floor** — IBM Q signup / AWS Braket creds / Akida signup 시 aggregator 단순 재실행만으로 자동 promotion (코드 변경 0).

---

## §4. 메인 세션 산출물과의 cross-link

### §4.1 직접 cross-link (file ref)

ledger v1 landing doc §9 가 명시:
```
.own #2 triad (b) PC empirical-max
└─ substrate-multiplicity ◄── THIS LEDGER (covered=7/9)
```

v1 doc §6 (Mk.XII INTEGRATION .own #2 (b) 가 different-axis) + memory entry `project_own2_triad_implementation_gap_audit_20260426` 와 매핑.

### §4.2 메인 세션 산출물과의 좌표

| 메인 세션 cycle | 좌표 (Mk.XII triad) | 축 (axis) | 본 ledger 와 관계 |
|---|---|---|---|
| **#42 DALI+SLI v2 (`dali_sli_v2_redesign_complete.marker`)** | (b) PC empirical-max | DALI(S1) + SLI(S3) coupled / cusp_depth | **ORTHOGONAL** — DALI/SLI 는 backbone activation axis, ledger 는 multi-substrate physical witness axis. 동일 (b) tier 이지만 sub-axis 다름. |
| **#58 S7 N=11 (`s7_n11_extension_complete.marker`)** | (b) PC empirical-max | cusp_depth N-extension (real backbone activation) | **ORTHOGONAL** — backbone activation Φ-proxy ≠ multi-substrate physical Φ-proxy. ledger §4 가 명시: "phi_proxy_cross_comparable=false". |
| **#43 CMT N=9** (없는 marker, but `feeds-main` cite) | (b) PC empirical-max | CMT family backbone-depth divergence | **ORTHOGONAL** — backbone-axis (in-distribution) vs substrate-axis (out-of-distribution). 두 축은 .own #2 (b) PC empirical-max 의 독립 sub-tier. |
| **`mk_xii_d_day_simulated_landing.md`** | (a) FC + (b) PC + (c) Production | EEG D-day simulated probe | **PARTIAL_OVERLAP** — 본 ledger 의 G5 LIVE_HW_WITNESS_RATE = 0/11 floor 이 D-day live-EEG 와 동일 family (simulator → real). aggregator 재실행 trigger 가 D+22..D+30 EEG arrival 과 sibling. |
| **`mk_xii_integration_6gate_cluster_summary.md`** (cluster_confidence 0.70) | (a) FC + (b) PC | INTEGRATION axis 6-gate (G8/G9/G9_robust/G10/preflight/hard_pass) | **NEW SISTER-GATE 후보** — 본 ledger 가 7번째 substrate-witness-ledger gate 로 추가 가능 (§5 참조). |

### §4.3 통합 파편 vs orthogonal 명시

본 ledger 의 위치는:
- (b) PC empirical-max **substrate-multiplicity** sub-axis (memory `project_own2_triad_implementation_gap_audit_20260426` 명시)
- 메인 세션 #42/#58/#43 = (b) PC empirical-max **backbone-activation** sub-axis (DALI/SLI/CMT/cusp_depth)
- **두 sub-axis 는 독립** (raw#10 honest, ledger landing v1 §6 명시)

따라서 cross-link = **ORTHOGONAL coordinate aware**, 단일 metric 으로 합치 불가 (Φ-proxy unit 본질적 비호환). cluster confidence aggregation 은 **별개 cluster** 로 처리 권장.

---

## §5. Mk.XII proposal v2 / 6-gate cluster 통합 분석

### §5.1 Cluster 6→7 확장 가능성

`mk_xii_integration_6gate_cluster_summary.md` 의 6 gate 는 INTEGRATION axis preflight (G8/G9/G9_robust/G10/preflight/hard_pass), `cluster_confidence = min(0.78, 0.85, 0.72, 0.70, 0.90, 0.80) = 0.70`.

본 ledger 추가 시 7번째 sister-gate:
- **G_SUBSTRATE_LEDGER**: ledger v2 (G1=9000/9000 cover + G2 honesty + G3 byte-identical + G4 FNV emitted + G5 0/11 live floor)
- per-gate confidence 후보: **0.85** (substrate cover 9/9 PASS + 4-gate per-entry 727/1000 + LIVE floor honest)
- 7-gate `min` rule 적용 시: **0.70 → 0.70** (G10=0.70 가 여전히 weakest; ledger 가 weakest-link 변경 X)

### §5.2 Mk.XII proposal v2 통합 권장도

| 통합 후보 | 권장 | 이유 |
|---|:---:|---|
| (A) Cluster 6→7 sister-gate 추가 (G_SUBSTRATE_LEDGER) | **PARTIAL** | weakest-link 0.70 변동 없음 + axis orthogonal (substrate ⊥ backbone). cluster confidence 변경 X 이지만 .own #2 (b) PC empirical-max coverage 명시도 ↑. |
| (B) Mk.XII proposal v2 §X 신규 chapter "Substrate witness ledger" | **YES** | proposal v2 (`mk_xii_proposal_outline_v2_20260426.md`, 34KB) 는 backbone-axis 위주. 본 ledger 가 substrate-axis 의 첫 9/9 completeness witness — proposal 새 sub-section 자격 있음. |
| (C) Cluster `min` rule 변경 (cross-axis weighted) | **NO** | raw#12 cherry-pick-proof (post-hoc tunable scaler 회피) + axis 본질적 비교 불가 (`phi_proxy_cross_comparable=false`). |
| (D) ledger v3 cycle 등록 (LIVE auto-promotion) | **YES** | IBM Q / Braket / Akida signup 시 aggregator 재실행만으로 0/11 → ≥1/11 promotion. `.roadmap` 신규 entry 자격. |

### §5.3 통합 권장 verdict: **PARTIAL** (시너지 있음, 단 별개 cluster)

- 본 ledger ⊥ 메인 세션 backbone-axis ⇒ 단일 cluster 합치 X
- ledger 자체가 별도 cluster (substrate-multiplicity) 의 첫 closure ⇒ archive X
- Mk.XII proposal v2 의 sub-section 추가 (B) + `.roadmap` v3 entry (D) 는 구체 권장
- Cluster sister-gate (A) 는 informational sanity 만 (primary verdict 변경 0)

---

## §6. 다음 cycle (통합 / 별개 트랙 / archive)

### §6.1 추천 트랙 (priority order)

1. **Track 1 (immediate, $0)**: Mk.XII proposal v2 doc (`anima-clm-eeg/docs/mk_xii_proposal_outline_v2_20260426.md`) 에 **§X "Substrate witness ledger v1+v2"** 신규 sub-section 추가. cross-ref: 본 discovery doc + ledger v1/v2 landing docs. raw#10 honest §3 (axis orthogonality) 보존.

2. **Track 2 (next-cycle, $0 mac-local)**: ledger v2 byte-identical re-verify (2-run). 검증 명령:
   ```
   ~/.hx/packages/hexa/build/hexa.real run \
       anima-physics/tool/mk_xii_substrate_witness_ledger_aggregator_v2.hexa
   shasum -a 256 state/v10_anima_physics_cloud_facade/integration_ledger/witness_ledger_v2.json
   # expected: df545c5e15404539cea6f1b61c8d46565089f6d266277234b50a124d066e49ba
   ```
   본 cycle 은 read-only — 재실행 X. Track 2 에서 외부 reproducibility witness 등록.

3. **Track 3 (post-EEG / post-LIVE)**: ledger v3 cycle 등록 (IBM Q / Braket / Akida signup 후 first non-zero LIVE rate witness). `.roadmap` 신규 entry 후보.

4. **Track 4 (deferred)**: 6-gate cluster informational sister-gate 로 G_SUBSTRATE_LEDGER 추가 (primary cluster_confidence 0.70 변경 X, sanity-only).

### §6.2 Archive 결정

- **NOT archive**. ledger v1 + v2 둘 다 active (v2 supersede 하되 v1 본 보존). 4 marker 모두 자동 emit 의 정상 trace ⇒ silent abandonment X.
- discovery doc (본 파일) 자체가 cross-link landing — Mk.XII proposal v2 통합 시 cite 됨.

---

## §7. raw#10 honest scope

1. **본 cycle = discovery + cross-link only** — ledger 산출물 측정 / 수정 0. read-only audit.
2. **byte-identical 외부 verify 미수행** — landing doc 의 sha 값 + disk file sha **일치** 확인했으나 aggregator 재실행 X (Track 2).
3. **cluster integration 결정 = informational** — primary cluster_confidence 0.70 (G10) weakest-link 유지. 본 ledger 가 cluster verdict 강화 NOT 약화.
4. **axis orthogonality preserved** — substrate-axis ⊥ backbone-axis, `phi_proxy_cross_comparable=false` 그대로 유지.
5. **메인 세션이 launch 안 한 산출물의 disk discovery** — 본 doc 의 trigger. memory `auto_marker patch #37 a66167ba` 가설은 marker timestamp + fingerprint 일관성으로 일관 (그러나 prove X).
6. **3 .py/.sh ledger 의존도 0** — aggregator hexa-only, raw#9 strict (`grep -c exec("python` = 0, `grep -c exec(".*\.sh"` = 0 — landing doc §8 명시).

---

## §8. Files

**New (this cycle, 1 doc)**:
- `anima-clm-eeg/docs/mk_xii_substrate_witness_ledger_discovery_landing.md` (this file)

**Discovered (read-only, NOT modified)**:
- `anima-physics/tool/mk_xii_substrate_witness_ledger_aggregator.hexa` (sha `1c1e3bea36d2…`, 26627 B)
- `anima-physics/tool/mk_xii_substrate_witness_ledger_aggregator_v2.hexa` (sha `0fff9a986543…`, 32074 B)
- `anima-physics/docs/mk_xii_substrate_witness_ledger_landing.md` (sha `0461c65d02d9…`, 14117 B)
- `anima-physics/docs/mk_xii_substrate_witness_ledger_v2_landing.md` (sha `da24189514…`, 10518 B)
- `state/v10_anima_physics_cloud_facade/integration_ledger/witness_ledger_v1.json` (sha `264f5cf7…`, 7611 B)
- `state/v10_anima_physics_cloud_facade/integration_ledger/witness_ledger_v1.json.meta` (sha `57c87227…`, 261 B)
- `state/v10_anima_physics_cloud_facade/integration_ledger/witness_ledger_v2.json` (sha `df545c5e1540…`, 11482 B)
- `state/v10_anima_physics_cloud_facade/integration_ledger/witness_ledger_v2.json.meta` (sha `adedf2b9…`, 431 B)
- `state/v10_anima_physics_cloud_facade/integration_ledger/marker.json` (v1, sha `f534638b…`, 5118 B)
- `state/v10_anima_physics_cloud_facade/integration_ledger/marker_v2.json` (sha `c79c8b92…`, 6410 B)
- 4 auto-marker (`state/markers/mk_xii_substrate_witness_ledger_aggregator{,_v2}_*.marker`)

**Marker (this cycle)**:
- `anima-clm-eeg/state/markers/mk_xii_substrate_witness_ledger_discovery_complete.marker`
