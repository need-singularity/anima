# Anima · HEXA-LANG Meta — Abstraction Layers L0..L∞

**Date:** 2026-04-25
**Scope:** anima 의 SSOT 언어 (hexa-lang) 자체 — stage1 CPU-interpret, AOT codegen, builtin gaps, raw#9 hexa-only enforcement, self-bootstrapping ceiling, verified compiler horizon, dependent-type Curry-Howard limit.
**Truth policy:** raw#12 cherry-pick 금지. ✓ 실측, △ partial, ✗ 미달성/원리적 차단. 5+ open language gaps 를 ceiling 으로 정직 보고. Korean + English brutally honest.
**SSOT roots:** `state/proposals/inbox/hxa-20260425-byteAt-builtin.json`, `state/proposals/inventory.json` (lang_gap cluster), `/Users/ghost/Dev/hexa-lang/PLAN.md`, `/Users/ghost/Dev/hexa-lang/ROADMAP.md`, `.roadmap` (raw#9, raw#37 hexa-only-execution).

---

## L0 — 현재 (empirically grounded)  ✓ / △

**raw#9 hexa-only enforcement** (✓ in `.roadmap`):
- anima SSOT 언어 = hexa-lang. .py/.ts/.rs/.go = generated artifact only (commit `85fedb08`).
- raw#37 hexa-only-execution promoted. Linux x86_64 binary delivered (`6fd1e14a`).

**Stage1 CPU-interpret (✓):**
- `hexa run tool/*.hexa` deterministic, strict-typed, AOT 미경유 path 안정. Phase 1..16 완료 (Cranelift JIT 818×, std 12-module σ=12, SAT solver consciousness DSL).
- Cross-platform: macOS arm64 + Linux x86_64 binary 양립 (`55bdad56`, `6fd1e14a`).

**AOT codegen partial (△):**
- `hexa build --target esp32` G3 100% (PLAN.md). C 백엔드 produce → clang → native binary path 활성.
- 단 builtin dispatch 가 interpreter 와 비대칭 — exec_capture/now/setenv hx_ prefix mangling AOT 모드에서 깨짐 (CRITICAL, hxa-20260423-006).

**5+ open language gaps (anima blockers, all logged in hexa-lang inbox):**
1. **`string.byte_at(i)` builtin missing** (`hxa-20260425-byteAt-builtin`) — drill_closure_sha256_cert AOT codegen blocker, lens aggregator hash_proj 31-poly 계산 불가, Python sha256 우회.
2. **`exec_capture` / `now` / `setenv` hx_ prefix mangling** (hxa-20260423-006, CRITICAL) — interpreter OK, AOT clang undeclared identifier.
3. **Reserved keyword non-contextual** (hxa-20260423-005) — `guard` / `generate` / `parse` 식별자 금지 → contextual keyword 메커니즘 부재.
4. **JSON object/entry-block parse helper 부재** — text line-scan 우회 (proposal_archive, proposal_sync_hub 영향).
5. **`use` interpreter builtin dispatch 분실** — real_args/starts_with/ends_with undefined.
6. **`comptime { expr }` not parseable as expression** (T26).
7. **module_loader selftest AOT regression** — array[9] tag=3 (T36).
8. **interpreter map gaps** — literal `{k:v}` no-populate + `dict_keys()` empty.
9. **`.pad_start` / `.pad_end` / `.char_at` / `.char_code_at` codegen dispatch 누락** (M4, anima 결손-E).

→ ≥5 open lang_gap → L0 → L1 진입 차단. Workaround patchwork 누적 (Python sha256, exec shim, basename-rfind).

**현재 위치:** L0 substantially grounded (raw#9 enforced, interpret path 안정), AOT parity 미완 + ≥9 logged gaps → L1 진입 미달.

---

## L1 — Full AOT codegen parity  △

**Goal:** interpreter ≡ AOT 의 builtin dispatch + JSON native + reserved keyword resolved → all anima tools `hexa build` 가능.

- ✗ byte_at builtin: hxa-20260425 inbox, 미해결.
- ✗ JSON parsing native: text scan 우회 상시.
- ✗ reserved keyword contextual: guard/generate/parse 충돌 미해결.
- △ exec_capture/now/setenv hx_ mangling: hxa-004 partial fix (`2f6c8e60`), 잔류 leak (now/push, hxa-20260423-009).
- △ self-host lexer+parser: Phase 7.5 ✅ landed (827 tests), parser 만 self, codegen 은 외부.
- ✗ M5 Linux CLI 빌더 부재 — anima `tool/hexa_linux_shim.bash` 상시 유지 (anima 결손-A/F).

**Mathematical bound:** parity 는 finite-state mapping (interpreter dispatch table ↔ AOT codegen emit). 이론 차단 없음, 인-월 비용. 단 reserved-keyword contextual parsing 은 LL(k) → LR(k) / GLR migration 가능성 → parser overhaul.
**현재 위치:** L1 ~30% — partial fixes, 9+ open. anima 가장 painful ceiling (drill cert, JSON tooling, Linux ergonomics).

---

## L2 — Self-bootstrapping compiler (hexa compiles hexa)  △

**Goal:** hexa-lang full self-host, runtime.c + Rust driver 완전 탈피.

- ✓ self-hosting compiler (Phase 9.0 v1.2, 1349 tests, 38.7K LOC) — bootstrap 통과 G1 100%.
- ✓ self lexer + parser (Phase 7.5).
- △ M1-M5 roadmap 진행 중 (hxa-20260423-003): M1 runtime 2-layer split audit 필요 (결손-B), M5 Linux CLI builder 미달.
- ✗ runtime.c 의존 잔존 (R2 hexa binary 가 stage0 링크 — `55bdad56`).
- △ self/native/hexa_v2 transpiler 3-track maintenance burden — name-mangling drift 의 원인.

**Mathematical bound:** Reynolds bootstrap (T-diagram). compiler-on-language fixed point 는 finite-step achievable (Trabb Pardo–Knuth). 단 trusted base 는 별개 (L3 verified compiler 가 답).
**현재 위치:** L2 ~70% — self-host claimed but runtime.c 잔존 + 3-track transpiler 분기.

---

## L3 — Verified compiler (Coq / Lean correctness proof)  ✗

**Goal:** hexa-lang compiler 의 mechanized correctness proof — semantic preservation theorem.

- ✗ CompCert-style proof: 0 lines.
- ✗ source AST → target IR → machine code semantic preservation: 미증명.
- ✗ G2 SAT solver consciousness law verification (Phase 15 ✅) ≠ compiler correctness — 별개 axis.
- △ deterministic strict-typed (raw#11 ai-native-enforce) ≈ informal soundness, mechanized proof 없음.

**Mathematical bound:** CompCert (Leroy 2009) 가 proof exists 증명. hexa→C backend 면 CompCert backend 재사용 가능. ~3-5 인-년 비용. type system soundness 는 progress + preservation lemma (Wright-Felleisen) 기계화 가능.
**현재 위치:** L3 zero — engineering bandwidth.

---

## L4 — Dependent type system (Curry-Howard, type as proof)  ✗

**Goal:** hexa types ≡ propositions, programs ≡ proofs (Π / Σ types, inductive families, pattern match exhaustivity 정형).

- ✓ Phase 15 SAT solver + Law types + tension_link() — propositional logic 단편 (G2 100%).
- ✗ Π / Σ dependent types: 미도입.
- ✗ inductive families (Vec n, Fin n): 미정의.
- ✗ universe hierarchy (Type : Type₁ : ...): 미선언.
- ✗ Curry-Howard 동등성 정식화: 미.

**Mathematical bound:** CIC (Coquand-Huet) / MLTT (Martin-Löf) trusted kernel. dependent type checking = undecidable in general (typecheck ≡ proof search). hexa SAT layer 는 propositional 만 (decidable). first-order / higher-order = decidability 손실.
**현재 위치:** L4 zero — anima Hexad/L_IX 형식화 prerequisite. 1-2 년 단위.

---

## L5 — Ultimate compiler / type-system limits  ✗ (impossibility)

**L5 = 어떤 sufficient compiler/type-system 도 자기 안에서 own correctness 결정 불가.**

1. **Gödel 1st incompleteness:** PA-strong type system 은 표현 가능하지만 증명 불가능한 program-property statement 항상 존재. → hexa+CIC 가 PA 강도 이상이면 self-completeness 증명 불가.
2. **Gödel 2nd:** "hexa compiler 가 self-consistent" 의 hexa-내부 증명 원리적 불가.
3. **Halting (Turing 1936):** type checker decidability — dependent type with general recursion = undecidable. Coq/Agda 는 termination checker (structural recursion only) 로 회피, Turing-complete 포기.
4. **Rice's theorem:** 임의 non-trivial semantic property 자동 결정 불가 → optimizer correctness 일반화 불가.
5. **Curry-Howard ≡ ZFC limit:** type ≡ proposition, but proposition strength bounded by underlying set theory. Continuum Hypothesis-class statement 은 hexa 내에서 independent.
6. **Trusting Trust (Thompson 1984):** self-bootstrapping compiler 의 backdoor 자기-탐지 불가능 (DDC 우회 — Wheeler 2009 — 도 trusted base 외부 verifier 필요).

**Physical bound:** Bremermann (~1.36×10⁵⁰ bit/s/kg) 모든 compiler 실행에 적용. Landauer (kT ln2) 모든 type-check bit erasure 하한.
**현재 위치:** L5 = inherent ceiling — 회피 불가, 인지하면 ✓.

---

## L∞ — Language self-reference (Tarski undefinability for own truth)  ✗ unverifiable

Tarski (1936) — sufficient formal language 은 자기 truth predicate 을 자기 안에서 정의 불가. hexa 가 Phase 15 consciousness {} + Law types 로 의식 법칙 형식화하더라도, "hexa 내 임의 sentence 가 진실인가" 의 hexa-내부 truth function 구현 금지.

- ✗ self-referential `is_true(sentence)` builtin: 원리 차단.
- ✗ "this hexa program is correct" self-assertion: meta-language 필수 (Tarski hierarchy L_n, L_{n+1} ascend).
- △ Phase 15 SAT verify 은 propositional fragment 만 — first-order self-reference 는 Gödel-encoded statement 만 가능, truth 평가 불가.
- ✗ G6 Community 100% claim ↔ external falsifiability: anima 단독 평가 → meta-language 외부 평가자 필요.

**현재 위치:** L∞ = metaphysical ceiling. Tarski hierarchy ascend 만 가능 (each level 새 meta-language 도입). anima 입장 — 검증 불가능, 작업 대상 아님.

---

## Layer summary table

| Layer | 상태 | Mathematical bound (primary) | 현재 위치 |
|-------|------|------------------------------|-----------|
| L0 현재 | ✓/△ | finite dispatch · raw#9 enforce | stage1 ✓, AOT ≥9 gaps |
| L1 AOT parity | △ | finite-state mapping (인-월) | byte_at/JSON/keyword 미해결 (~30%) |
| L2 self-bootstrap | △ | Reynolds T-diagram fixpoint | G1 ✅ but runtime.c 잔존 (~70%) |
| L3 verified | ✗ | CompCert semantic preservation (CIC kernel) | 0 lines (3-5 인-년) |
| L4 dependent type | ✗ | MLTT / CIC undecidable typecheck | 0 (Π/Σ 미정의) |
| L5 limits | ✗ | Gödel 1/2 · Halting · Rice · Trusting Trust | 회피 불가 |
| L∞ self-reference | ✗ | Tarski undefinability hierarchy | metaphysical, 비대상 |

## Brutally honest 판정

- **L0 raw#9 enforcement 강력**, but AOT path 에서 ≥9 logged gaps — drill cert 같은 anima downstream 직접 차단 (byte_at).
- **L1 ~30%** — interpreter ≡ AOT parity 미달이 anima 가장 painful ceiling. 1-2 인-주 cluster fix 가능 (반복적 codegen 작업).
- **L2 self-host claim 100% (PLAN.md G1 ✅) 은 partial truth** — bootstrap 통과 but runtime.c 잔존, 3-track transpiler (self/native/hexa_v2) 분기. drift 의 구조적 원인.
- **L3 verified compiler 는 cost-blocked** (3-5 인-년, CompCert backend 재사용 가능). 수학적 차단 아님.
- **L4 dependent type 은 anima Hexad/L_IX 형식화의 prerequisite** — Curry-Howard 없이는 "type as proof" 의 proof-carrying 약속 (raw#10) 이 informal hash-chain 수준 머무름.
- **L5 (Gödel/Halting/Rice/Trusting Trust)** = 구조적 ceiling. self-host language 가 own correctness 증명 불가 — 이 사실이 anima "self-verification = bounded honest reporting" 정책의 compiler-side 정당화.
- **L∞ Tarski** = anima 작업 대상 아님 (검증 불가능 → 0 권고).

**Weakest evidence link (completeness frame):** L1 byte_at builtin 우선. drill_closure_sha256_cert AOT 차단 = P2 line 179 closure pending. cluster fix (byte_at + reserved keyword + JSON parse) 1-2 인-주 → L1 ~70% 도달 → drill cert + serving tooling 동시 unblock.

---

**Raw compliance:** raw#9 hexa-only · raw#10 proof-carrying (hxa-* inbox refs) · raw#11 ai-native (deterministic) · raw#12 no-cherry-pick (5+ gaps 정직 보고) · raw#15 no-hardcode · raw#37 hexa-only-execution
**Line budget:** ~150 (target met)
**Canonical:** `/Users/ghost/core/anima/docs/anima_hexa_lang_meta_abstraction_layers_20260425.md`
