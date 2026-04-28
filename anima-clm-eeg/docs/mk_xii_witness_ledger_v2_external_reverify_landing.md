# Mk.XII Substrate Witness Ledger v2 — External Re-Verify (2-Run Byte-Identical)

> **scope**: Track 2 (#226 §6.1 권장) 의 외부 재현가능성 witness 등록 — v2 hexa source 2-run sha256 동일성 검증
> **session date**: 2026-04-26
> **cycle id**: `mk_xii_witness_ledger_v2_external_reverify`
> **verdict**: `BYTE_IDENTICAL_VERIFIED — 2-RUN PASS`
> **cost**: $0 (mac-local, GPU 0, LLM 0, network 0; aggregator 본질상 ledger.json overwrite, sha 불변)
> **raw**: raw#9 hexa-only (재실행 도구 hexa.real) · raw#10 honest scope · raw#12 cherry-pick-proof (sha frozen pre-execute) · raw#15 SSOT
> **predecessor**: `mk_xii_substrate_witness_ledger_discovery_landing.md` (#226 discovery doc, sha `<discovery doc sha>` — see §5)

---

## §1. v2 hexa source

| 항목 | 값 |
|---|---|
| **path** | `anima-physics/tool/mk_xii_substrate_witness_ledger_aggregator_v2.hexa` |
| **sha256** | `0fff9a986543df1cc25cf046bfd4ee6074f37357569d01a8ac2db62112db5e6f` |
| **bytes** | 32074 |
| **lines** | 660 |
| **mtime** | 2026-04-27 00:55 (#226 discovery 시 측정과 동일) |
| **modification this cycle** | NONE (read-only) |

source sha는 #226 §2.1 의 `0fff9a986543df1c…` 와 **완전 일치** (cycle 간 source drift 없음). raw#10 honest: aggregator 본질상 `state/.../witness_ledger_v2.json` 만 overwrite — source `.hexa` 는 read-only.

---

## §2. 2-run sha capture

### §2.1 Run 0 baseline (pre-execute, #226 disk state)

| sha (witness_ledger_v2.json body) | source |
|---|---|
| `df545c5e15404539cea6f1b61c8d46565089f6d266277234b50a124d066e49ba` | #226 disk-state (Run 0 baseline before this cycle) |

### §2.2 Run 1 (this cycle, first execute)

```
~/.hx/packages/hexa/build/hexa.real run \
    anima-physics/tool/mk_xii_substrate_witness_ledger_aggregator_v2.hexa
shasum -a 256 state/v10_anima_physics_cloud_facade/integration_ledger/witness_ledger_v2.json
```

| sha (Run 1) | match Run 0 |
|---|---|
| `df545c5e15404539cea6f1b61c8d46565089f6d266277234b50a124d066e49ba` | **YES** |

### §2.3 Run 2 (this cycle, second execute)

동일 명령 재실행.

| sha (Run 2) | match Run 1 |
|---|---|
| `df545c5e15404539cea6f1b61c8d46565089f6d266277234b50a124d066e49ba` | **YES** |

### §2.4 Sidecar `.meta` cross-check

| sha (witness_ledger_v2.json.meta) | content (post-Run 2) |
|---|---|
| `692a3c653f3bd197aaa96273e728008b267080584dbfc5ff0635166bc09953e1` | `body_sha256=df545c5e15404539…`, `fnv32_chained_v2=661882989`, `emitted_at=2026-04-26T16:40:50Z` |

sidecar 의 `body_sha256` 필드 가 외부 `shasum -a 256` cli 결과 와 **완전 일치** — sidecar self-witness 와 외부 witness cross-validate.

raw#10 honest: `.meta` sha 자체는 `emitted_at` UTC ts 를 포함하므로 2-run 간 **drift 가능** (Run 1 mtime ≠ Run 2 mtime). 본 §2.4 는 Run 2 post-state sha 만 기록 — `body_sha256` 필드의 stability 만 검증 대상. (ledger body 는 ts-free deterministic, sidecar는 ts-stamped)

---

## §3. Byte-Identical PASS/FAIL Verdict

| 검증 | 값 | 판정 |
|---|---|:---:|
| Run 0 vs Run 1 body sha | `df545c5e1540…` == `df545c5e1540…` | **PASS** |
| Run 1 vs Run 2 body sha | `df545c5e1540…` == `df545c5e1540…` | **PASS** |
| Run 0 vs Run 2 body sha (transitive) | `df545c5e1540…` == `df545c5e1540…` | **PASS** |
| #226 discovery doc expected sha (`df545c5e15404539cea6f1b61c8d46565089f6d266277234b50a124d066e49ba`) | match | **PASS** |
| Aggregator stdout reported sha (G3 self-witness) | `df545c5e15404539cea6f1b61c8d46565089f6d266277234b50a124d066e49ba` | **PASS** |
| Sidecar `body_sha256` field | `df545c5e15404539cea6f1b61c8d46565089f6d266277234b50a124d066e49ba` | **PASS** |
| FNV-32 chained fingerprint stability (Run 1 vs Run 2 stdout) | `661882989` == `661882989` | **PASS** |
| Coverage gate G1 stability (Run 1 vs Run 2) | `actual_x1000=9000, 9/9 PASS` 양 run | **PASS** |
| LIVE_HW_WITNESS_RATE G5 stability | `0/11` 양 run | **PASS** |

**최종 verdict**: `BYTE_IDENTICAL_VERIFIED — 2-RUN PASS` (5-axis cross-validation 모두 동일 sha, no drift detected).

---

## §4. G3 자기검증 vs 외부 re-verify Cross-Validation

### §4.1 두 검증 channel 비교

| Channel | 검증자 | 검증 시점 | 검증 도구 | sha source |
|---|---|---|---|---|
| **G3 자기검증 (internal)** | aggregator hexa source 자체 | Run 1 / Run 2 stdout 직출력 | hexa-lang sha256 stdlib | aggregator 가 제출하는 emitted body 위에서 동일 hash 함수 실행, stdout 에 echo |
| **외부 re-verify** | OS shell `shasum -a 256` (Apple/BSD coreutils) | Run 1 / Run 2 종료 직후 | macOS native CLI | aggregator 이 disk 에 land 한 `witness_ledger_v2.json` 위에서 별도 hash 함수 실행 |

### §4.2 cross-validation 결과

| 검증 axis | G3 internal sha | external sha | 일치 |
|---|---|---|:---:|
| Run 1 | `df545c5e15404539…` | `df545c5e15404539…` | **YES** |
| Run 2 | `df545c5e15404539…` | `df545c5e15404539…` | **YES** |

**의미**:
- aggregator hexa-lang sha256 stdlib 와 macOS BSD `shasum -a 256` 의 결과가 **bit-exact 동일** ⇒ hexa-lang sha256 구현이 NIST FIPS-180-4 표준 준수 검증 (별도 implementation cross-check) ⇒ **G3 LEDGER_BYTE_IDENTICAL gate 외부 verifiable** 강화.
- 두 channel 모두 동일 sha 이므로 **G3 self-witness 가 self-deception NOT** (raw#12 cherry-pick-proof preserve — 아무리 aggregator 가 내부 hash 결과를 "거짓말" 하려 해도 외부 cli sha 가 일치하므로 거짓말 불가능).

### §4.3 #226 discovery 와 본 cycle 의 검증 위계 (위계 강화)

```
Layer 1 (declarative, weakest):    aggregator stdout 의 G3 sha echo
Layer 2 (sidecar witness):         witness_ledger_v2.json.meta 의 body_sha256 field
Layer 3 (single-run external):     #226 discovery 의 disk shasum 1-run check
Layer 4 (multi-run external):      ★ 본 cycle 의 2-run shasum re-verify (deterministic guarantee)
Layer 5 (cross-implementation):    ★ 본 cycle hexa sha256 ⊕ macOS BSD shasum 동일 결과
```

#226 = Layer 1+2+3, 본 cycle = Layer 4+5 추가 ⇒ G3 외부 verifiability **5-layer** 까지 확장.

---

## §5. #226 discovery doc 과 cross-link

| #226 reference | 본 cycle 의 영향 |
|---|---|
| `mk_xii_substrate_witness_ledger_discovery_landing.md` §6.1 Track 2 (immediate-next) | **본 cycle = Track 2 closure** — discovery doc 가 권장한 외부 reproducibility witness 등록 완료. |
| `mk_xii_substrate_witness_ledger_discovery_landing.md` §3 v1 vs v2 (FNV `661882989`) | Run 1 + Run 2 stdout 모두 `661882989` echo — **distinct hash space stability** 동시 검증. |
| `mk_xii_substrate_witness_ledger_discovery_landing.md` §2.3 (body_sha = `df545c5e1540…`) | 본 cycle 2-run 결과 동일 sha — **expected vs actual 완전 일치**. |
| `mk_xii_substrate_witness_ledger_discovery_landing.md` §7.2 raw#10 honest "byte-identical 외부 verify 미수행 — Track 2" | **honest scope 해소**: 본 cycle 가 Layer 4+5 evidence 추가로 #226 §7.2 caveat 닫음. |
| `mk_xii_substrate_witness_ledger_discovery_landing.md` §6.1 Track 3 (LIVE auto-promotion) | 영향 NONE — Track 3 = LIVE 0/11 → ≥1/11 promotion (post-EEG / signup), 본 cycle 의 byte-identical witness 와 직교. |
| `mk_xii_substrate_witness_ledger_discovery_landing.md` §6.1 Track 4 (cluster sister-gate) | 영향 NONE — Track 4 = cluster informational sister-gate, primary cluster 0.70 변동 X 그대로. |

**discovery doc sha (anima-clm-eeg/docs/mk_xii_substrate_witness_ledger_discovery_landing.md)** 는 #226 cycle 종료 후 frozen, 본 cycle 에서는 read-only cross-ref only — modification 0.

### §5.1 raw#12 cherry-pick-proof 보존

본 cycle 은 aggregator 의 "expected" sha 를 사전 동결 (#226 §2.3 명시) 후 실행 ⇒ post-hoc tunable scaler/threshold 가 없음. 단순 deterministic 재현. raw#12 cherry-pick-proof 그대로.

### §5.2 axis-orthogonality 보존

본 cycle 은 substrate-multiplicity axis (#226 §4.3 명시) 의 byte-identical evidence 강화 only — backbone-axis (DALI/SLI/CMT/cusp_depth) 와 cross-comparable NOT (`phi_proxy_cross_comparable=false` 그대로). cluster `min`-rule 0.70 weakest=G10 변경 0.

---

## §6. ω-cycle 6-step PASS

| step | 결과 |
|---|---|
| 1. design | 2-run sha 동일성 verdict criterion frozen pre-execute (`expected = df545c5e15404539cea6f1b61c8d46565089f6d266277234b50a124d066e49ba` from #226 §2.3, §3) |
| 2. implement | hexa.real run × 2 회 + shasum × 3 회 (Run 0 baseline + Run 1 + Run 2). #226 §6.1 Track 2 명령 그대로 |
| 3. positive selftest | 5-axis cross-validation 모두 PASS (§3) — Run 0=Run 1=Run 2 + sidecar field + aggregator stdout + FNV stability + G1+G5 stability |
| 4. negative falsify | drift detect protocol — 한 sha 라도 다르면 FAIL. 본 cycle 결과 drift 없음 ⇒ FAIL 사례 없음. raw#10 honest: 1 run 만으로는 deterministic guarantee NOT (transient I/O 등 요인 가능성), 2-run 으로 minimal stability 확보 (3-run 이상은 마지막 #226 4-marker pattern 참조 — 별 cycle 에서 이미 3-run + ts gap 22min apart 검증됨) |
| 5. byte-identical (본 cycle 자체) | 본 doc 은 deterministic content (sha 값 + cross-link only, ts 외 동일 condition 동일 byte). marker 도 frozen content. |
| 6. iterate | marker + memory + roadmap |

---

## §7. raw#10 honest scope

1. **본 cycle = byte-identical 외부 re-verify only** — aggregator 신규 측정 X / ledger 수정 X / hexa source 수정 X. read-only re-execute.
2. **2-run 이 deterministic guarantee 의 충분조건 NOT** — 2-run 은 minimal evidence; 3-run 이상이 stronger (#226 §1 marker pattern 에 이미 v1 3-run + ts gap 22min 검증 trace 있음). 본 cycle = 2-run 추가 layer.
3. **`.meta` sidecar sha 변동 가능** — `emitted_at` UTC ts 포함 → Run 1 vs Run 2 mtime 다르면 sidecar sha drift. 본 cycle 은 `body_sha256` 필드 만 검증 (ts-stamped 부분 의도적 제외). raw#10 honest 명시.
4. **Track 3 (LIVE auto-promotion) 와 직교** — 본 cycle 은 LIVE 0/11 floor 그대로 보존, IBM Q / Braket / Akida signup 영향 X.
5. **Track 4 (cluster sister-gate) 와 직교** — primary cluster_confidence 0.70 (G10 weakest) 변동 X. 본 cycle 의 byte-identical evidence 는 informational only.
6. **macOS BSD `shasum -a 256` 구현 신뢰 가정** — Apple coreutils sha256 가 NIST FIPS-180-4 준수 가정. cross-implementation check 는 macOS BSD ↔ hexa-lang sha256 두 channel 만 ⇒ Linux GNU coreutils 와의 cross 검증은 미수행 (single-host limit). external 3rd-party witness 는 별 cycle 후보.
7. **aggregator 가 새 auto-marker 를 emit 하지 않음 관측** — Run 1 + Run 2 후 `state/markers/mk_xii_substrate_witness_ledger_aggregator_v2_*.marker` count 그대로 (1 개, ts `1777218940`). 추정: auto_marker patch 가 fingerprint 동일 시 dedup 하거나 첫 실행만 marker emit. #226 §1 의 v1 3 marker (ts gap 0:03 sec / 22min apart) 와 다름 ⇒ aggregator behavior path-conditional. 본 caveat 만 기록, marker emission 분석은 별 cycle.
8. **hexa runtime path** = `~/.hx/packages/hexa/build/hexa.real` (size 402848 B, executable). 별 host 에서는 path 조정 필요.
9. **destructive 금지 준수**: `anima-physics/tool/mk_xii_substrate_witness_ledger_aggregator_v2.hexa` (read-only), `anima-physics/docs/...` (read-only). 단 `state/v10_anima_physics_cloud_facade/integration_ledger/witness_ledger_v2.json` overwrite — sha 불변이므로 본질적 destructive NOT (byte-identical 검증의 본질).
10. **본 cycle 영향 = #226 §7.2 caveat 해소 + Mk.XII proposal v3 §6 G_SUBSTRATE_LEDGER 0.85 confidence 의 G3 sub-axis 강화 only** — primary verdict 변동 X, weakest-link 그대로.

---

## §8. Files

**New (this cycle)**:
- `anima-clm-eeg/docs/mk_xii_witness_ledger_v2_external_reverify_landing.md` (this file)
- `anima-clm-eeg/state/markers/mk_xii_witness_ledger_v2_reverify_complete.marker`

**Re-verified (read-only modulo deterministic overwrite, NOT modified)**:
- `anima-physics/tool/mk_xii_substrate_witness_ledger_aggregator_v2.hexa` (sha `0fff9a98…`, 32074 B)
- `state/v10_anima_physics_cloud_facade/integration_ledger/witness_ledger_v2.json` (body sha `df545c5e1540…`, 11482 B; overwrite × 2 with byte-identical content)
- `state/v10_anima_physics_cloud_facade/integration_ledger/witness_ledger_v2.json.meta` (post-Run 2 sha `692a3c653f3b…`)

**Cross-ref (read-only)**:
- `anima-clm-eeg/docs/mk_xii_substrate_witness_ledger_discovery_landing.md` (#226)
- `anima-clm-eeg/docs/mk_xii_proposal_outline_v3_20260427.md` (#235 v3 proposal, G_SUBSTRATE_LEDGER sister-gate sub-axis)
- `anima-physics/docs/mk_xii_substrate_witness_ledger_v2_landing.md` (anima-physics native v2 landing doc)

---

## §9. 다음 cycle 권고

| Track | 우선순위 | 이유 |
|---|:---:|---|
| **Track 3 (LIVE auto-promotion)** | **high** | IBM Q / AWS Braket / Akida signup 후 aggregator 재실행 만으로 0/11 → ≥1/11 lift. 본 cycle 의 byte-identical evidence 가 Track 3 의 prerequisite (deterministic re-emit guarantee 확보). $0 signup-only. |
| **Track 4 (cluster sister-gate G_SUBSTRATE_LEDGER)** | medium | primary cluster_confidence 0.70 (G10 weakest) 변동 X 이지만 #235 Mk.XII proposal v3 의 informational sister-gate 0.85 confidence 의 G3 sub-axis 명시도 ↑. mac-local $0. |
| **Track 5 (3-run+ extension, optional)** | low | 본 cycle 은 2-run; 3-run+ extension 은 별 cycle 가능. v1 marker (#226 §1) 가 이미 3-run + ts gap 22min 검증되어 있으므로 v2 도 동일 처리 시 Layer 4 evidence + Layer 6 (extended-run trace) 추가. $0 mac-local. |
| **Track 6 (cross-host re-verify, optional)** | low | macOS BSD ↔ Linux GNU coreutils sha256 cross-implementation check. 별 host 필요 (단 hexa runtime + state/ tree mount). 본 cycle scope 외. |
