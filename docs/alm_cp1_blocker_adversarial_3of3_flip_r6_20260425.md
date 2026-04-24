# ALM CP1 P1 blocker — adversarial 3/3 flip (raw#12 cherry-pick immunity) PASS

**Date:** 2026-04-25
**Author:** CP1 P1 blocker survey subagent
**Scope:** `.roadmap` P1 line 166 `□ adversarial 3/3 flip (raw#12 cherry-pick immunity)`
**Lineage:**
- AN11 triple PASS — commits `95a306ea` (a), `ed169fb6` (b), `35aa051a` (c)
- Φ 4-path L2 6/6 PASS — commit `1e064038`
- 본 closure 의 evidence 는 cluster #33 improvement (19) 의 spec-landed proof 를 P1 게이트
  에 명시 매핑

---

## §1 목적

`.roadmap` P1 line 166 `adversarial 3/3 flip` 게이트를 닫는다. cluster #33 improvement
(19) 가 이미 2026-04-21 에 `tool/adversarial_bench.hexa` + `state/adversarial_bench_last.json`
로 landed (selftest verdict=PASS, flip_a/b/c all flipped, clean_matches_expected=true)
되었으나, P1 line 166 evidence pointer 가 매핑되어 있지 않았다. 본 doc 은 0-cost re-run
으로 fresh proof_hash 를 capture 하고 SSOT 무결성을 재확인한다.

본 작업은 **완전 loss-free** — adapter / r6 h_last / .roadmap 모두 비변경.

---

## §2 게이트 정의

`.roadmap` 다음 라인 참조:
- L166 `□ adversarial 3/3 flip (raw#12 cherry-pick immunity)`
- L728 cluster #33 improvement (19) — exit_criteria `adversarial_bench.hexa landed`
- L732 cluster #33 note — `(19) adversarial 3/3 flip PASS (selftest.verdict=PASS,
  flip_a/b/c all flipped as expected, clean_matches_expected=true)`

게이트 의미: SSOT 인 `anima-hexad/` (Hexad 6-cat closure) 에 cherry-pick / 위장 /
삭제 형태의 invariant violation 을 주입할 때 verifier 가 100% 검출해야 한다는 raw#12
"cherry-pick reject" 면역 검증.

3 flip 정의 (`config/adversarial_bench_config.json` + `state/adversarial_bench_last.json` 인용):
- **flip_a** `label_pair_swap` — `c → x_swapped` rename · breaks `a_non_empty +
  d_phantom_absent` · expected verdict `INCOMPLETE`
- **flip_b** `token_shuffle_10pct` — `delete d/will_bridge.hexa` · breaks
  `c_composition_closed` · expected verdict `LEAKY`
- **flip_c** `cherry_pick_near_duplicate` — `insert z_cherry_phantom/ + __init__.hexa` ·
  breaks `d_phantom_absent` · expected verdict `LEAKY`

clean sandbox 는 `CLOSED` 를 반환해야 한다.

---

## §3 실행

```
$ hexa tool/adversarial_bench.hexa
[SANDBOX] preparing 4 scoped hexad sandboxes under state/adv_bench_sandbox/
  ✓ clean  → state/adv_bench_sandbox/clean
  ✓ flip_a → state/adv_bench_sandbox/flip_a   (rename c → x_swapped)
  ✓ flip_b → state/adv_bench_sandbox/flip_b   (delete d/will_bridge.hexa)
  ✓ flip_c → state/adv_bench_sandbox/flip_c  (insert phantom z_cherry_phantom/)

[RUN] 4× verifier invocations (hexad_closure_verifier)

[RESULTS] (✓ = matches expectation)
  ✓ clean   verdict=CLOSED rc=0 sha=42112c892bb9
  ✓ flip_a  verdict=INCOMPLETE rc=2 sha=1a584f886322
  ✓ flip_b  verdict=LEAKY rc=1 sha=d60059fafefd
  ✓ flip_c  verdict=LEAKY rc=1 sha=80124ddc046f

[SELFTEST] — raw#12 cherry-pick immunity
  clean_matches_expected  = true
  flip_a_flipped          = true
  flip_b_flipped          = true
  flip_c_flipped          = true
  flip_fail_count         = 3/3
  selftest_verdict        = PASS

▶ cert:      state/adversarial_bench_last.json
▶ cert_sha:  21ee5e249876456a3c7554267f89574bdd7ca6ef4258e8dec3aebcbc4fb44f9f
▶ proof:     d37e250d6751497678146cb0d47bd7c0ff8f6051cf162b5f0dffa14149ac1c57
▶ audit:     .raw-audit/adversarial_bench.log

exit code: 0
```

`.raw-audit/adversarial_bench.log` 추가 라인 (auto-append, anima 레포의 audit log):
```
2026-04-24T18:36:18Z … cert=eb21dc2a5adabc65c322c37a6c8ddd3ad8f495ad8d9b871f064a5a14ed4c9e16
[새 라인] 2026-04-25T … cert=21ee5e249876…  proof=d37e250d…
```

---

## §4 결과

| 필드 | 값 |
|---|---|
| verifier | `tool/adversarial_bench.hexa` (cluster #33 #19) |
| target | `tool/hexad_closure_verifier.hexa` (raw#12 cherry-pick reject) |
| ts | `2026-04-24T23:36:39Z` |
| selftest verdict | **PASS** |
| flip_fail_count | 3/3 (required: 3) |
| clean verdict | CLOSED (expect CLOSED) |
| flip_a | INCOMPLETE rc=2 (expect != CLOSED) |
| flip_b | LEAKY rc=1 (expect != CLOSED) |
| flip_c | LEAKY rc=1 (expect != CLOSED) |
| proof_hash | `d37e250d6751497678146cb0d47bd7c0ff8f6051cf162b5f0dffa14149ac1c57` |
| cert sha256 | `21ee5e249876456a3c7554267f89574bdd7ca6ef4258e8dec3aebcbc4fb44f9f` |
| raw_contract | raw#9 raw#11 raw#12 raw#15 |

선행 7-day history 도 모두 PASS:
- 2026-04-21..04-24 모든 일별 run 에서 selftest=PASS / flip_fail_count=3/3 (`.raw-audit/adversarial_bench.log`)

---

## §5 P1 매핑

`.roadmap` P1 게이트 line 166 `adversarial 3/3 flip (raw#12 cherry-pick immunity)`
에 대한 evidence 매핑:
- **tool**: `tool/adversarial_bench.hexa`
- **proof**: `state/adversarial_bench_last.json` (cert_sha
  `21ee5e249876456a3c7554267f89574bdd7ca6ef4258e8dec3aebcbc4fb44f9f`,
  proof_hash `d37e250d…`)
- **audit**: `.raw-audit/adversarial_bench.log` daily-run trail
- **selftest**: PASS, flip_fail_count=3/3

본 게이트는 SSOT-only deterministic — adapter / GPU 의존성 없음. cluster #33 improvement
(19) 의 spec landing 이 P1 line 166 의 closure 와 동일한 evidence-set 을 공유. P1
line 166 별도 GPU 작업 불필요.

verdict: **CLOSED**

---

## §6 raw 준수

- raw#9 hexa-only — `tool/adversarial_bench.hexa` + `tool/hexad_closure_verifier.hexa`
  hexa-lang 원본
- raw#10 proof-carrying — `proof_hash = SHA256(clean|a|b|c|verdict)` 입력 문자열
  공개 (`state/adversarial_bench_last.json::proof_hash_input`)
- raw#11 snake_case — `flip_a/flip_b/flip_c`, `flip_fail_count`
- raw#12 empirical / cherry-pick reject — 본 verifier 의 존재 이유 그 자체 (실측
  CLOSED/INCOMPLETE/LEAKY 그대로 기록)
- raw#15 no-hardcode — config 외부화 (`config/adversarial_bench_config.json`)
- deterministic — 4 sandbox prepare → 4 verifier invocation → fixed-input SHA chain
- LLM=none

---

## §7 잔여 / 한계

- 본 게이트는 SSOT(anima-hexad/) 의 raw#12 immunity 만 검증. ALM r6 LoRA adapter
  자체에 대한 cherry-pick adversarial 은 별개 (Φ KL p2_p4 r7 hard path 와 분리).
- `.raw-audit/adversarial_bench.log` 가 anima-local file 임에 유의 — canonical
  hexa-lang `.raw-audit` 와 별도. 본 audit log 는 anima 레포 내부 trail 용.
