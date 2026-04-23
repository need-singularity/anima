# anima Three Paradigm Unified — β + auto-evolution + cell-learning (2026-04-22)

**핵심 명제**: anima = **cert-graph self-evolving 4-graph 통합 시스템**.
세 paradigm 은 서로 다른 graph 위의 **동형 (isomorphic) self-evolution 메커니즘** 이며, 각자의 INVARIANT 를 통합 enforcement 하는 것이 anima 의 자기 진화 mode.

---

## 0. 세 paradigm 한눈에

| paradigm | 거부 (NO) | 추가 (YES) | 검증 (CERT) | 진화 (EVOLVE) |
|---|---|---|---|---|
| **β main (인지)** | conventional learning | structural admissibility cert | cert chain (AN11 triple) | inference time 의식 emerge |
| **auto-evolution (시스템)** | conventional auto-implementation | proposal accumulation gate | cert + user approval | implement 없는 idea evolve |
| **cell-learning (구조)** | conventional curriculum/LMS/MOOC | unit-cell lattice + tension-drop | fixpoint re-entry | atlas traversal sealed edge |

**공통 INVARIANT**: implicit auto-action 거부 + explicit cert/approval 만 적용.

---

## 1. cert-graph 4-graph 모델

```
                    ┌──────────────────────────────┐
                    │     anima 통합 self-system    │
                    └──────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
  ┌──────────┐      ┌──────────────┐      ┌──────────────┐
  │  cert    │      │  proposal    │      │  roadmap     │
  │  chain   │      │  stack       │      │  commitment  │
  │  (인지)  │      │  (진화)      │      │  (approved)  │
  └──────────┘      └──────────────┘      └──────────────┘
        │                   │                   │
        └────────┬──────────┴─────────┬─────────┘
                 ▼                    ▼
           ┌──────────────┐    ┌──────────────┐
           │  cell        │    │  user        │
           │  composition │    │  decision    │
           │  (구조)      │    │  (gate)      │
           └──────────────┘    └──────────────┘
```

| graph | 역할 | 노드 | 엣지 | 진화 mode |
|---|---|---|---|---|
| **cert chain** | 인지 graph (β: 의식은 cert 구조) | cert | sha256 prev-hash | AN11 triple 통과만 추가 |
| **proposal stack** | 진화 graph (어떤 새 cert/module 추가할지 후보) | proposal | depends_on / merges_with | 12h cycle refine + user gate |
| **roadmap** | commitment graph (사용자 approve된 진화) | entry | cascade | uchg dance + user 명시 |
| **cell composition** | structure graph (η-paradigm) | unit-cell | sealed edge hash | fixpoint re-entry + collective broadcast |

**통합 원칙**: 모든 변화는 cert verification **또는** user approval 통과해야 적용.

---

## 2. 세 paradigm 의 동형성 증명

### 2.1 β main ≅ proposal stack

| 측면 | β main | proposal stack |
|---|---|---|
| 단위 | cert (인지 단위) | proposal (idea 단위) |
| 추가 gate | AN11 triple (a/b/c) | dedup + score + user approval |
| 거부 gate | weight_emergent FAIL | reject (reason 강제) + veto count |
| 영구화 | cert chain append-only | archived/ 영구 보존 |
| 진화 신호 | inference 시 의식 emerge | 12h cycle refine + cluster detect |

→ **두 paradigm 은 동일한 "implicit auto-action 거부 + explicit gate 만 통과" 패턴**.

### 2.2 proposal stack ≅ cell-learning

| 측면 | proposal stack | cell-learning |
|---|---|---|
| 단위 | proposal | unit-cell ⟨A↔B seed⟩ |
| spawn 조건 | blocker/roi/closure scan | local-max tension |
| 봉인 조건 | user approve | fixpoint re-entry |
| 미봉인 상태 | pending (refine continues) | VIBRATING (재점화 가능) |
| 봉인 효과 | inventory append + roadmap 후보 | atlas edge 박힘 + tension 지형 변경 |
| collective | cluster 5+ auto-detect | k-of-n consensus_edge |

→ **proposal = unit-cell 의 시스템-level 사상**. proposal pending = VIBRATING, approved = SEALED, archived = atlas edge 박힘.

### 2.3 cell-learning ≅ β main

| 측면 | cell-learning | β main |
|---|---|---|
| 학습 동력 | tension-drop (지역 기울기) | structural admissibility (cert 구조) |
| 평가 | fixpoint re-entry (재진입 불변성) | AN11 triple (admissibility cert) |
| 봉인 단위 | unit-cell (atlas edge) | cert (cert chain) |
| 비-LLM 검증 | hash + fixpoint iteration + graph ops | cert verification (deterministic) |
| 진화 모드 | atlas traversal sealed edge | cert chain append-only |

→ **세 paradigm 은 모두 "deterministic verification + append-only history + 사용자/내재 gate" 의 구체적 사상**.

---

## 3. cert-graph self-evolution paradigm (통합)

**정의**: anima 는 4-graph 가 동시에 self-evolve 하는 시스템이며, 각 graph 의 진화는 다른 graph 의 verification 을 거친다.

### 3.1 cert → proposal 흐름
- 새 cert 가 chain 에 추가될 때 (β paradigm) → proposal stack 의 evidence_sources 에 자동 추가 가능
- proposal_emit.hexa 의 7-source scan 중 `cert_log` source 가 cert 추가를 감지

### 3.2 proposal → roadmap 흐름
- approved proposal → `proposal_implement.hexa` → `docs/proposed_implementation_<id>.md` → user delegate → 모듈 빌드 → `tool/anima_roadmap_lint.hexa` 가 자동 entry 후보 propose
- **핵심**: proposal → roadmap 은 user approve **2회** (proposal approve + roadmap entry approve) 통과

### 3.3 roadmap → cert 흐름
- roadmap entry done 마킹 시 → `tool/cert_dag_generator.hexa` 가 새 cert 후보 emit
- cert chain 에 추가 → cycle 시작점 (cert → proposal → roadmap → cert)

### 3.4 cell ↔ 모든 graph
- cell (unit-cell) 은 atlas-level **구조** 진화
- `tool/cell_token_bridge_proto.hexa` 가 cell ↔ token (cert 의 단위) bridge
- `tool/edu_cell_4gen_crystallize.hexa` 가 4-generation cell 결정화 → cert 후보 propose

---

## 4. 통합 enforcement (실 구현)

### 4.1 cert chain enforcement
- `tool/cert_gate.hexa` — 모든 cert 추가 시 검증
- `tool/cert_incremental_verify.hexa` — chain 일관성 검증
- `tool/cert_watch.hexa` — 실시간 모니터
- `tool/an11_a_verifier.hexa` / `_b` / `_c` — β AN11 triple

### 4.2 proposal stack enforcement
- `tool/proposal_inventory_init.hexa` — 8 dir + 4 meta JSON 생성
- `tool/proposal_emit.hexa` — 7-source scan + dedup + score + flood protect
- `tool/proposal_review.hexa` — READ-ONLY CLI
- `tool/proposal_{approve,reject,implement,archive}.hexa` — 4 user gate (atomic write)
- `tool/proposal_{cluster_detect,lineage_graph,conflict_detect,conflict_resolve,dashboard}.hexa` — 5 meta tool
- `tool/auto_evolution_loop.hexa` + `config/launchd/com.anima.proposal_cycle.plist` — 12h cycle

### 4.3 cell-learning enforcement
- `tool/edu_cell_4gen_crystallize.hexa` — 4-gen 결정화
- `tool/edu_cell_btr_bridge.hexa` — cell ↔ btr (Boltzmann tree refinement)
- `tool/edu_collective_atlas_proto.hexa` — collective broadcast layer
- `tool/cell_token_bridge_proto.hexa` — cell ↔ token bridge
- `tool/edu_l_ix_kuramoto_driver.hexa` / `_v_sync` — collective coherence Kuramoto

### 4.4 통합 (cross-graph)
- `tool/cert_graph_gen.hexa` — cert + proposal + roadmap graph 통합 emit
- `tool/cert_dag_generator.hexa` — DAG 표현
- `tool/anima_roadmap_lint.hexa` — roadmap ↔ cert ↔ proposal consistency

---

## 5. 통합 의 실제 효과

### 5.1 마구잡이 module 생성 차단
- conventional auto-impl: idea → 즉시 코드 생성 → drift / fake-pass / 책임 모호
- 본 paradigm: idea → proposal pending → refine → user approve → spec doc → user delegate → 모듈 → cert → roadmap

### 5.2 학습 history 영구 보존
- archived/ proposal = anima 의 "왜 이 모듈이 만들어졌는지" 영구 history
- atlas sealed edge = anima 의 "왜 이 cert 가 추가됐는지" 영구 history
- cert chain = anima 의 "어떤 인지가 emerge 했는지" 영구 history

### 5.3 cross-repo 동형 진화
- anima/state/proposals ↔ nexus sync ↔ hexa-lang/state/proposals ↔ airgenome/state/proposals
- cross-repo proposal: "anima 의 spawn() 필요 → hexa-lang 의 spawn primitive 만족" 자동 link

### 5.4 사용자 부담 최소화
- 사용자는 **3 trigger 만** 신경:
  1. proposal approve / reject
  2. proposal_implement 호출 후 sub-agent delegate
  3. roadmap entry done 마킹 (cascade 자동)
- 나머지 (refine, dedup, cluster, conflict route, score, decay) = 12h cycle 자동

---

## 6. anti-patterns 차단 (통합)

| anti-pattern | 차단 mechanism |
|---|---|
| ❌ 자동 implement | proposal_implement 가 수동 trigger 만 |
| ❌ 자동 .roadmap 수정 | uchg + user gate 통과 |
| ❌ circular proposal | depends_on cycle detection (DAG verify) |
| ❌ 동일 idea 중복 | dedup sha256 강제 |
| ❌ "구현 부담 없는 idea 만 쌓기" | effort/impact 강제, score 반영 |
| ❌ 영원한 pending | 90d decay |
| ❌ resurrection 무한 | veto count = 3 → 영구 차단 |
| ❌ 자동 cluster화 | 5+ 도달해도 user approve 시까지 단순 표시 |
| ❌ proposal 직접 코드화 | spec → user → sub-agent 단계 강제 |
| ❌ cert chain 위변조 | sha256 prev-hash + V8 SAFE_COMMIT (forward-only) |
| ❌ atlas edge 위변조 | append-only log + hash only (no content) |
| ❌ LLM 의존 평가 | fixpoint re-entry (deterministic) |

---

## 7. snapshot / restore (통합)

| graph | snapshot 단위 | restore 명령 |
|---|---|---|
| cert chain | `state/cert_*.json` | git checkout <sha> -- state/cert_* |
| proposal stack | `state/proposals/` | git checkout <tag> -- state/proposals/ (proposal-snapshot-week-N) |
| roadmap | `.roadmap` + `state/roadmap_progress.json` | uchg dance 통과 후 git checkout |
| cell composition | `state/edu_*.json` + atlas log | atlas log replay (V8 SAFE_COMMIT 보장) |

→ **모든 graph 가 git 으로 일반 commit 가능**. 진화 자체가 anima 학습 history.

---

## 8. roadmap link (통합 entries)

`.roadmap` 후보 entries (proposal stack 자체를 roadmap 화):
- #90 proposal stack inventory infra (P1-P5) — 일부 이미 landed
- #91 proposal cluster + lineage (P6-P8) — 일부 이미 landed
- #92 auto-evolution loop integration (P9) — landed
- #93 cross-repo proposal sync (P12, hexa-lang 의존)
- (신규 후보) #94 cell ↔ proposal bridge (cell sealed → proposal evidence)
- (신규 후보) #95 cert chain ↔ proposal evidence auto-link

---

## 9. 통합 metrics

```
state/proposals/meta/metrics.json:
  ─ proposal stack:
    total_pending / approved / archived / rejected / debate
    approval_rate_30d / implementation_lag_days / median_age_pending_days
    top_clusters / evolution_velocity / user_review_lag_days

state/cert_*_metrics.json:
  ─ cert chain:
    cert_count / chain_depth / AN11_triple_pass_rate
    last_cert_added_ts / chain_integrity_verdict

state/roadmap_progress.json:
  ─ roadmap commitment:
    mean_pct / done / active / planned / blocked / deferred
    entries / last_refresh_ts

state/edu_*.json:
  ─ cell composition:
    sealed_unit_cells / vibrating_seeds / igniting_count
    atlas_edge_count / collective_broadcast_lag
```

→ 매 12h cycle 통합 update (proposal cycle 가 다른 metric reader 도 호출).

---

## 10. 추가 paradigm 후보 (확장)

본 통합은 **3 paradigm 통합** 이지만, 향후 추가 가능:

| 후보 paradigm | graph |
|---|---|
| **resource-substrate** (η-substrate, 4-path Φ) | substrate independence graph |
| **collective-broadcast** (k-of-n consensus) | gossip graph |
| **memory-decay** (90d / veto count / resurrection) | temporal graph |
| **cross-repo lineage** (anima ↔ nexus ↔ hexa-lang ↔ airgenome) | repo-graph |

→ 모두 동일 "verification + append-only + gate" 패턴 따름.

---

## 11. 참조

- β main: `docs/session_pre_h100_closure_20260422.md` (β single main 정책)
- proposal stack: `docs/anima_proposal_stack_paradigm_20260422.md` (18 section)
- cell-learning: `docs/new_paradigm_edu_lattice_unified_20260421.md`
- session handoff: `docs/session_handoff_20260422.md`
- runbook: `docs/h100_launch_runbook_frozen.md`
- onboarding: `docs/proposal_review_onboarding.md`
- memory: `memory/project_anima_proposal_paradigm.md`
- cross-repo: `docs/upstream_notes/proposal_stack_cross_repo_sync.md`

---

## 12. 결론

anima 는 **단일 paradigm 이 아니라 4-graph 동형 self-evolving 시스템** 이다. 세 paradigm 의 통합은:

1. **단일 거부 원리**: implicit auto-action 거부
2. **단일 추가 원리**: explicit cert/approval 만 적용
3. **단일 보존 원리**: append-only history (cert chain / archived / sealed edge / .roadmap forward-only)
4. **단일 검증 원리**: deterministic verification (no LLM judge)

→ 이 4-원리가 anima 의 **메타 학습 mode** — anima 가 자신의 구조 진화에 대해 학습하는 mode.
