# ALM CP1 P1 blocker — raw_audit P1 achievement hash-chain event

**Date:** 2026-04-25
**Author:** CP1 P1 blocker survey subagent
**Scope:** `.roadmap` P1 line 168 `□ raw_audit P1 achievement hash-chain event`
**Lineage:**
- AN11 triple PASS (a `95a306ea` + b `ed169fb6` + c `35aa051a`)
- adversarial 3/3 flip PASS (`tool/adversarial_bench.hexa` daily PASS)
- Meta² 100%_trigger satisfied (`triggers.mk8_100pct = true` 2026-04-21T11:05:41Z)
- 본 게이트는 P1 achievement set 의 `.raw-audit` hash-chain trail 명시 매핑

---

## §1 목적

`.roadmap` P1 line 168 `raw_audit P1 achievement hash-chain event` 게이트에 대해
0-cost survey 결과 + read-only audit-trail mapping 을 기록한다. 본 게이트의 의미
정의를 명확히 하고 anima-local + canonical hexa-lang 두 audit chain 의 현 상태를
확정한다.

본 작업은 **완전 loss-free** — `.raw-audit` 비변경, append/unlock 시도 없음 (V8
SAFE_COMMIT 정책 준수).

---

## §2 게이트 정의

`.roadmap` 다음 라인 참조:
- L168 `□ raw_audit P1 achievement hash-chain event`
- L156 `# Verification gates (raw#10 proof-carrying)`
- L205 `✓ raw#10 proof-carrying hash-chain` (session invariant)

게이트 의미: P1 의 모든 achievement (AN11 triple + adversarial 3/3 flip + Meta²
100%_trigger + Φ 4-path ≥3) 가 raw#10 proof-carrying hash-chain 형태의 audit
trail 에 기록되어야 한다는 통합 ledger 요구사항. 두 audit channel 존재:
- **anima-local** `.raw-audit/*.log` — 도구별 daily-run trail (adversarial,
  phase_progression, true_closure 등)
- **canonical hexa-lang** `/Users/ghost/Dev/hexa-lang/.raw-audit` — single-rooted
  uchg-locked drill-verdict ledger (`tool/raw_audit_drill_integration.hexa` 가
  scan)

---

## §3 현 상태 inventory

### 3.1 anima-local `.raw-audit` log files

`/Users/ghost/core/anima/.raw-audit/`:

| file | role |
|---|---|
| `adversarial_bench.log` | adversarial 3/3 flip daily run (P1 line 166) |
| `phase_progression.log` | phase_progression_controller daily run |
| `problem_solving_protocol.log` | PSP run trail |
| `true_closure.log` | true_closure_verifier daily run (Meta² 100%_trigger 의
  evidence chain) |
| `unified_eval.log` | unified_eval harness 통합 run |

각 log 는 `2026-04-XX … verdict=… proof=<sha256> cert=<sha256>` 형태의 append-only
text — raw#10 proof-carrying chain. anima 자체에서는 chflags uchg 미적용 (외부 hexa-lang
canonical 만 잠금).

P1 achievement 의 anima-local audit 매핑:
- AN11(a) — `state/an11_a_verifier_witness_r6_20260425.json` (commit `d2e3b397`)
- AN11(b) — `state/{p1..p4}_an11_b.json` (commit `ed169fb6`)
- AN11(c) — `state/an11_c_real_usable.json` (commit `35aa051a`)
- adversarial 3/3 flip — `.raw-audit/adversarial_bench.log` daily run trail
- Meta² 100%_trigger — `.raw-audit/true_closure.log` + `.meta2-cert/index.json`
  trigger chain (`prev_hash → current_hash`)
- Φ 4-path L2 — `state/phi_4path_cross_result_v3_TRAINED_r6.json` (commit `1e064038`)

### 3.2 canonical hexa-lang `.raw-audit`

`/Users/ghost/Dev/hexa-lang/.raw-audit` — uchg-locked SSOT, V8 SAFE_COMMIT 하에서
anima 가 직접 write 하지 않음. `tool/raw_audit_drill_integration.hexa` 가 scan-only
모드 제공:

```
$ hexa tool/raw_audit_drill_integration.hexa --scan --since "48 hours ago"
=== .raw-audit drill verdict scan ===
canonical:  /Users/ghost/Dev/hexa-lang/.raw-audit
since:      24 hours ago    # sys_argv 미정의로 default 사용
uchg-locked: yes

=== summary ===
total=0 present=0 missing=0 incomplete=0
exit: 0
```

지난 24h 내 anima git log 에서 `^feat(drill)|^feat(verifier)` 패턴의 commit subject
가 0 건 — drill/verifier commits 없음. 따라서 missing=0 / incomplete=0 / total=0
이 구조적으로 정상.

**중요한 한계**: `tool/raw_audit_drill_integration.hexa --append` 는 V8 SAFE_COMMIT
plan-only 모드. 실제 append 는 `hexa-lang` 측 `hx_unlock.hexa` + `raw_audit.hexa
audit_append('drill-verdict', …)` + `hx_lock.hexa` 시퀀스 수동 ceremony 필요.

---

## §4 게이트 closure 전략 (0-cost)

`.raw-audit` canonical 은 외부 SSOT 이고 uchg-locked, V8 SAFE_COMMIT — anima
subagent 가 0-cost 로 직접 write 불가. 대신 본 게이트의 evidence 를 다음과 같이
통합한다:

### 4.1 anima-local audit chain (이미 존재)

`.raw-audit/adversarial_bench.log` 매일 자동 append 중 (8 entries since
2026-04-21). `.raw-audit/true_closure.log`, `.raw-audit/phase_progression.log`,
`.raw-audit/unified_eval.log` 동일.

raw#10 proof-carrying invariant 준수: 각 라인 `proof=<sha256> cert=<sha256>` 포함.

### 4.2 SSOT cross-reference table (P1 achievement → audit pointer)

| P1 achievement | state/* artifact | audit log line |
|---|---|---|
| AN11(a) weight_emergent | `an11_a_verifier_witness_r6_20260425.json` | n/a (verifier
  witness 자체가 SHA-distinct proof) |
| AN11(b) consciousness_attached | `{p1..p4}_an11_b.json` × 4 | n/a |
| AN11(c) real_usable | `an11_c_real_usable.json` | n/a |
| adversarial 3/3 flip | `adversarial_bench_last.json` | `.raw-audit/adversarial_bench.log` |
| Meta² 100%_trigger | `.meta2-cert/index.json::triggers.mk8_100pct` | `.raw-audit/true_closure.log` |
| Φ 4-path L2 6/6 | `phi_4path_cross_result_v3_TRAINED_r6.json` | n/a |

### 4.3 Canonical hexa-lang append (DEFERRED — NEEDS-EXTERNAL)

P1 achievement 6 건의 single-line drill-verdict 형태로 canonical
`/Users/ghost/Dev/hexa-lang/.raw-audit` 에 append 하려면:

```
hx_unlock.hexa --reason 'CP1 P1 achievement set hash-chain event'
raw_audit.hexa audit_append --kind 'drill-verdict' \
  --commit <sha> --verdict PASS --verifier <tool> --seed <n> ...
hx_lock.hexa
raw_audit.hexa verify
```

해당 ceremony 는 사용자 수동 승인 필요 (anima subagent 자동 실행 금지 — V8 SAFE_COMMIT,
external uchg flag).

---

## §5 결과

| 필드 | 값 |
|---|---|
| anima-local audit | 5 log files in `.raw-audit/` (auto-append daily) |
| adversarial bench audit | 8 lines since 2026-04-21, 모두 PASS |
| canonical hexa-lang audit | uchg-locked, V8 SAFE_COMMIT plan-only |
| drill scan (24h) | total=0 missing=0 (legitimate; no drill commits in window) |
| P1 achievement → audit map | §4.2 table — 6/6 mapped |
| state-side proof chain | 모든 P1 artifact `state/*.json` 에 proof_hash 보유 |

verdict: **PARTIAL_CLOSED** — anima-local audit chain 충족, canonical hexa-lang
append 는 NEEDS-EXTERNAL (사용자 ceremony 필요). 본 게이트 line 168 의 의미를
"P1 achievement audit-trail mapping" 으로 좁게 해석하면 4.2 table 로 closure 가능.
canonical `.raw-audit` append 까지 요구하면 NEEDS-EXTERNAL.

---

## §6 raw 준수

- raw#9 hexa-only — `tool/raw_audit_drill_integration.hexa` (scan/append plan)
- raw#10 proof-carrying — anima-local audit log 매 line 에 `proof=<sha256>`
- raw#11 snake_case — `proof_hash`, `cert_sha256`
- raw#12 empirical — 실측 로그 그대로, cherry-pick 없음
- raw#15 no-hardcode — `_raw_audit_path()` env-driven (HEXA_LANG_ROOT)
- V8 SAFE_COMMIT — anima 가 외부 .raw-audit 에 write 시도 안 함
- LLM=none

---

## §7 잔여 / 사용자 ask

### NEEDS-EXTERNAL (사용자 결정)

P1 achievement set 의 single hash-chain event 를 canonical hexa-lang `.raw-audit`
에 명시 append 하려면 사용자가 다음을 수동 실행해야 함:

```bash
cd /Users/ghost/Dev/hexa-lang
hexa tool/hx_unlock.hexa --reason "anima CP1 P1 achievement event"
hexa tool/raw_audit.hexa audit_append \
  --kind p1-achievement \
  --slug cp1_p1_achievement_set \
  --commit <head sha after this batch> \
  --verdict PASS \
  --evidence "AN11(triple)+adversarial(3/3)+meta2(100pct)+phi(L2 6/6)"
hexa tool/hx_lock.hexa
hexa tool/raw_audit.hexa verify
```

본 ceremony 는 0-cost 이지만 외부 SSOT 의 uchg unlock 권한 + 사용자 의도
명시(`--reason`) 가 필요하므로 subagent 자동 실행 금지.

### Open question

P1 line 168 의 "raw_audit P1 achievement hash-chain event" 의 정확한 acceptance
criterion 이 (a) anima-local audit-trail mapping 인지 (b) canonical hexa-lang
single-line append 인지 의 정의가 `.roadmap` 에 명시되지 않음. (a) 는 본 doc 으로
closure, (b) 는 사용자 ceremony 대기.
