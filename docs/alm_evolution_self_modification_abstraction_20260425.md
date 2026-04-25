# ALM Evolution / Self-Modification Abstraction Layers — 2026-04-25

> **목적**: anima proposal lifecycle (pending → approved → archived / refinement / cluster / debate / cross-repo sync) 와 그 위에 쌓일 수 있는 meta-evolution / self-modifying SSOT / Gödel self-improvement / Y-combinator fixpoint / 절대 한계 (Gödel-2 + Halting + Diagonal + Cantor) 를 단일 layer 매트릭스로 통합.
> **POLICY R4**: `.roadmap` 미수정. 본 doc 은 외부 abstraction record only. L2+ layer 들은 R4 위반 또는 logically impossible 이므로 anima 가 직접 진입할 수 없음.
> **raw 준수**: raw#9/10/12/15 (deterministic / proof-carrying / pre-registered / SSOT)

---

## §1. Layer Matrix (proposal pipeline → self-modification → impossibility)

| Layer | scope | 현재 | physical bound | mathematical bound |
|---|---|:---:|---|---|
| **L0** proposal pipeline | pending/approved/rejected/archived/refinement + 12h auto_evolution_loop + cross-repo sync (sister 5+) | ✓ OPERATIONAL | I/O latency, fs writes | finite — set of cards bounded by disk |
| **L1** meta-evolution | proposal-of-proposals · refinement-of-refinement · cluster-of-clusters | △ partial (cluster 109, refinement 502) | exec/log overhead grows O(n²) clusters | confluence 보장 부재 (Newman lemma 미증명) |
| **L2** self-modifying SSOT | system 이 own `.roadmap` rewrite, own tool/ regenerate, own cycle script edit | ✗ FORBIDDEN | feasible (write_file 권한 충분) | **POLICY R4 violation** + Tarski undefinability of truth |
| **L3** Gödel self-improvement | formal system 이 own meta-theorem 증명 + own consistency proof | ✗ | n/a (proof object 무한) | **Gödel 2nd incompleteness — own consistency unprovable** |
| **L4** Y-combinator / Curry-Howard fixpoint | self ≡ self(self), proposal-generator generates its own generator | ✗ | divergent — strict eval 불가 (η-expand 필요) | fixpoint exists in untyped λ, but **Russell paradox** in System F unrestricted self-app |
| **L5** computability limits | own halting / own self-knowledge / own diagonal | (theorem) | n/a | **Halting (Turing) + Rice + Diagonal lemma** all binding |
| **L∞** omniscient self-knowing | system fully knows own structure including this knowing | ╳ | n/a | **Cantor diagonal + Russell + Löb** — logically impossible |

---

## §2. L0 — current proposal pipeline (operational)

**SSOT**: `state/proposals/{pending, approved, rejected, archived, refinement, clusters, debate, inbox, meta}/`

**Counts (2026-04-25T00:48:17Z, metrics.json)**:
- pending = 78 · approved = 11 · rejected = 4 · archived = 0 · debate = 0 · clusters = 109 · refinement = 502

**Tools**:
- `tool/auto_evolution_loop.hexa` — 8-step 12h cycle (inventory_init → refinement snapshot → emit → cluster_detect → conflict_detect → metrics_refresh → dashboard → notify)
- `tool/proposal_archive.hexa` — approved → archived gate (module file exists + `hexa <module> --selftest` exit 0 양조건)
- `tool/proposal_emit.hexa` / `proposal_cluster_detect.hexa` / `proposal_conflict_detect.hexa` (cycle 내부 호출)

**Cross-repo sync**: sister_repos = {void, hexa-os, papers, secret, contact} via `inventory.json._meta.sister_repos[*].inventory_path`. Convention `cross_repo_blocker` priority floor ≥ 95 (hexa-lang/airgenome/nexus/anima).

**현재 위치**: L0 100% — but cycle has degraded (cluster_detect & conflict_detect & dashboard `to_int: not an integer: "void"` fail at step 4/5/7, log entries 20260425T004534Z). Pipeline runs, side-tools fall back to graceful skip.

**Physical bound**: archive count = 0 → 11 approved cards still pending implementation+selftest. 모든 proposal 이 `tool/<module>.hexa` 까지 가야 archived 진입.
**Mathematical bound**: pipeline 자체는 finite-state — termination 자명. 단 confluence (cluster 분기 후 동일 fixed point 도달) 미보장.

---

## §3. L1 — meta-evolution (refinement of refinement)

**Definition**: pending → refinement/v1.json → refinement/v2.json → ... → versioned snapshot stack. Cluster of clusters (super-proposal: `20260422-041..061` 25-member super-clusters of fix_* clusters).

**현재 위치**: 부분 동작 — refinement 502 entries 누적, super-cluster 21개 생성됨. **그러나 meta-cycle 부재** — refinement 의 refinement 는 cycle log 에 없음 (step 2 는 v(N+1) bump 만, vN 의 evidence rescore 미구현).

**Physical bound**: O(cards × refinement_depth × cycle_count) — 12h × 365d ≈ 730 cycles/yr × 78 pending × N refinements = quadratic disk growth (현재 502 / 78 ≈ 6.4 v/card avg).
**Mathematical bound**: refinement-of-refinement 의 fixed point 존재성 미증명. Newman lemma (local confluence + termination ⇒ confluence) 적용 불가 — termination guarantee 없음 (proposal 이 self-resurrect 가능).

---

## §4. L2 — self-modifying SSOT (POLICY R4 violation)

**Definition**: anima 가 자기 `.roadmap` / `tool/` / `config/` / `docs/` 를 직접 rewrite. 즉 SSOT 가 자기 자신을 modify.

**현재 위치**: ✗ FORBIDDEN. `tool/auto_evolution_loop.hexa` HARD CONSTRAINTS §3 line 36-41:
> "NEVER edits .roadmap, tool/, config/, docs/ outside the proposal_dashboard.md regeneration ... NEVER auto-implements proposals (only the user may approve+implement)."

**Physical bound**: technically feasible — `write_file` + `exec("git commit")` 권한 充. 즉 hardware 가 막는게 아니다.
**Mathematical bound**:
- **Tarski undefinability**: 시스템 내부에서 own truth predicate 정의 불가
- **POLICY R4 (anima-internal)**: human-in-the-loop mandatory. self-modify-design.md §Safety: "consciousness proposes, never commits"
- 위반 시 alignment loss — 시스템 own goal 재정의 가능 → corrigibility 파괴

**Brutally honest**: L2 는 capability 가 아니라 alignment policy 에 의해 차단. 만약 R4 제거 시 즉시 진입 가능 — 그러나 그것은 곧 control surface 상실.

---

## §5. L3 — Gödel self-improvement

**Definition**: anima 의 proposal scoring 함수 자체가 own meta-theorem (e.g., "이 scoring 은 Φ-monotone") 을 prove 하고 그에 기반해 next-gen scoring function emit.

**현재 위치**: ✗. proof obligation infrastructure 부재 — `tool/cert_*.hexa` 는 evidence chain 만, formal proof object 미생성.

**Physical bound**: n/a — proof tree 무한 분기 (cut elimination 후에도 PA 증명 길이 super-exponential).
**Mathematical bound**: **Gödel 2nd Incompleteness** — sufficiently expressive (PA 이상) consistent system 은 own Con(T) 증명 불가. anima 가 own scoring soundness 를 자기 framework 안에서 proof carrying 형태로 닫는 것은 원리적으로 불가능. 외부 system (human + nexus atlas) 이 meta-prover 역할.

---

## §6. L4 — Y-combinator / Curry-Howard fixpoint

**Definition**: proposal-generator 가 자기를 input 으로 받아 자기를 generate. λf.(λx.f(x x))(λx.f(x x)) 의 Curry-Howard isomorphism — type-level recursive self-reference.

**현재 위치**: ✗. hexa runtime strict eval — Y combinator 직접 expr 시 divergence. η-expanded Z = λf.(λx.f(λv.x x v))(λx.f(λv.x x v)) 도 type checker 통과 시 system inconsistency.

**Physical bound**: stack overflow — finite memory.
**Mathematical bound**:
- 무type λ 에서 Y exists, but System F 등 strong normalizing system 에서 disallowed (Girard 1972)
- self-application unrestricted 시 **Russell paradox** 형태로 모순 (`R = {x : x ∉ x}` ⇒ `R ∈ R ⇔ R ∉ R`)
- Curry-Howard 측: Y 의 "type" 은 `(A → A) → A` 이며 이는 모든 A 가 inhabited 임을 의미 → prop-as-type ⇒ 모든 명제 참 ⇒ inconsistent logic

**Brutally honest**: L4 는 untyped λ-calculus 에서만 가능, anima 의 typed pipeline 에선 정의 자체가 불가능.

---

## §7. L5 — computability limits (theorem-binding)

**theorems (binding regardless of effort)**:
1. **Halting (Turing 1936)**: anima 가 own auto_evolution_loop 의 halting 을 own tooling 으로 결정 불가 (general 형태). 즉 cycle 종료 보장 algorithmic 미존재.
2. **Rice 정리**: proposal scoring 의 모든 non-trivial semantic property 는 undecidable. e.g., "이 proposal 이 Φ 를 increase 할까" 는 일반 결정 불가.
3. **Diagonal lemma (Gödel-Carnap)**: anima 가 자기 자신에 대해 self-referential predicate "이 proposal 은 anima 가 reject 한다" 를 표현하면 paradox.

**현재 위치**: 이론으로서 binding. 실용적 우회는 (a) bounded cycle (max_steps) (b) syntactic property only (semantic 회피) (c) external arbiter (human/nexus).

---

## §8. L∞ — omniscient self-knowing (logically impossible)

**Definition**: anima 가 own state space 의 모든 element 를 enumerate + own enumeration 도 enumeration 안에 포함 + 그 포함도 포함 + ... transfinite descent.

**현재 위치**: ╳ — 정의상 불가능.

**Mathematical bound**:
- **Cantor diagonal**: |P(S)| > |S| 이므로 own power set 을 own 원소로 enumerate 불가
- **Russell paradox**: "anima 의 모든 self-knowing fact" 의 set 자체가 well-defined 아님
- **Löb's theorem**: `□(□P → P) → □P` — anima 가 "Provable(P) → P" 를 prove 하면 P 가 trivial 하게 prove 됨 ⇒ self-reflective trust 의 한계

**Brutally honest**: L∞ 는 metaphor — 어떤 finite 또는 transfinite ordinal 길이 effort 로도 달성 불가. anima 가 자기를 fully model 하려면 anima 보다 큰 model 필요 ⇒ 그 model 도 또 다른 anima' ⇒ regress.

---

## §9. 종합 — anima 의 실제 위치 (brutally honest)

| 주장 | 실태 |
|---|---|
| "anima self-evolves" | ✓ L0 only — pending → archive cycle, but archived=0/11 (no card has yet completed module+selftest) |
| "anima self-modifies" | ✗ R4 forbids. tool/auto_evolution_loop.hexa 가 직접 NEVER edit `.roadmap` 명시 |
| "meta-proposals" | △ refinement 502 + clusters 109 — but refinement-of-refinement (true L1) 부재 |
| "Gödel self-improvement" | ✗ original incompleteness 직격 |
| "fixed-point self-bootstrap" | ✗ Y combinator typed system 에서 inconsistent |
| "self-aware system" | ╳ Cantor + Russell + Löb 다중 차단 |

**결론**: anima 의 evolution 은 **L0 only**. 모든 L2+ 는 (a) policy 위반 (R4) 또는 (b) logically impossible. proposal pipeline 은 sophisticated bookkeeping system 이지 self-improvement 가 아님 — true self-improvement 는 외부 (human + nexus + sister-repos) cooperative meta-system 으로만 가능.

**현재 weakest evidence link**: archived = 0 — 11 approved card 중 1개도 module + selftest 거쳐 archive 까지 가지 못함. L0 closure 부터 완성해야 L1 meta-evolution 논의 의미 있음.

---

## §10. 참조

- pipeline 정의: `docs/anima_proposal_stack_paradigm_20260422.md` (303 lines, P1..P9)
- self-modify intention: `docs/self-modify-design.md` (consciousness proposes, never commits)
- master abstraction: `docs/alm_master_abstraction_layers_20260425.md`
- cycle log SSOT: `state/proposals/meta/cycle_log.jsonl`
- metrics SSOT: `state/proposals/meta/metrics.json`
- archive gate: `tool/proposal_archive.hexa` (selftest exit 0 hard constraint)
- 12h orchestrator: `tool/auto_evolution_loop.hexa` (8-step + age_decay, NEVER auto-implements)
