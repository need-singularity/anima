# anima 자동 진화 + 제안서 stack — 총 구조 브레인스토밍 (2026-04-22)

핵심 원칙: **모듈 자동 생성 ❌ → 제안서 누적 ✅** (raw#20 stop-gate paradigm 확장)

배경: 사용자 요구 "모듈 같은건 제안서를 쌓아두는 형태로 (마구잡이로 만들어지면 곤란하니까), 다음 또 메타 자동화시에는 모듈이 안만들어졌더라도 쌓아둔것 토대로 또 쌓고 하는식으로". β main 같은 root-level paradigm 발견 logic 을 **시스템 진화** 영역으로 확장.

---

## 1. 디렉토리 구조 (proposal stack 본진)

```
state/proposals/
├── inventory.json                    # 메타 인덱스 (단일 SSOT)
├── pending/                          # 사용자 검토 대기 (쌓이는 곳)
│   └── 20260422-001_<slug>.json
├── refinement/                       # 같은 제안 다회 refine 이력
│   └── 20260422-001/
│       ├── v1.json (initial)
│       ├── v2.json (cycle+1 enhanced)
│       └── vN.json
├── approved/                         # 사용자 approval, 모듈화 대기
├── rejected/                         # 사용자 reject + reason
├── archived/                         # 모듈화 완료 (영구 보존)
├── debate/                           # 충돌 제안 (ω vs β 같은 case)
├── clusters/                         # 5+ 관련 제안 → cluster 후보
└── meta/
    ├── metrics.json
    ├── lineage.json                  # parent-child 제안 graph
    └── decay_log.json                # 오래된 pending decay 기록
```

## 2. proposal schema (SSOT v1)

```json
{
  "id": "20260422-042",
  "version": 3,
  "first_seen_ts": "2026-04-22T...",
  "last_refined_ts": "2026-04-25T...",
  "title": "...",
  "kind": "tool|paradigm|axis|cert|cluster|fix|module|deprecation",
  "rationale": "...",
  "evidence_sources": [{"path": "...", "field": "...", "snapshot_sha256": "..."}],
  "estimated_effort": "1h|1d|1w|...",
  "estimated_impact": "narrative",
  "risk_level": "0|low|med|high",
  "loss_free": true,
  "depends_on": ["20260420-007", ...],
  "conflicts_with": ["20260418-003"],
  "merges_with": [],                 // cluster 멤버
  "refinement_history": [{"v": N, "ts": "...", "diff": "..."}],
  "score_priority": 0-100,           // 자동 계산
  "user_status": "pending|approved|rejected|archived|debate|veto",
  "user_decision_at": null,
  "user_decision_reason": null,
  "implementation_module_path": null,  // archive 시 채워짐
  "lineage_parent": null,            // 다른 제안의 child 인 경우
  "lineage_children": [],
  "veto_count": 0,                   // reject 누적
  "resurrection_eligible_after": null
}
```

## 3. 12h cycle (auto-evolution loop)

```
cycle_N (매 12h, launchd plist):
  step 1. read inventory.json
  step 2. for each pending:
            re-evaluate evidence (mtime, new probe)
            update score (stale → decay, new evidence → boost)
            refine description if context 변경
            bump version
  step 3. scan blocker + roi + closure_axis + conjecture → propose new
  step 4. dedup (sha256 of {title.lower()+first_source})
  step 5. cluster: 5+ related → cluster proposal emit
  step 6. conflict: 2 incompatible → debate folder
  step 7. update inventory + lineage graph
  step 8. emit docs/proposal_dashboard_<repo>.md
  step 9. notify (slack/email)

INVARIANT: 절대 tool/, config/, .roadmap 수정 안 함. state/proposals/ 만 mutate.
```

## 4. 누적 patterns (시간 축)

| period | count (typical) | 특징 |
|---|---|---|
| day 1 | 10 (manual seed) | 사용자 직접 입력 |
| day 7 | 30 | auto-refined + blocker scan |
| day 30 | 80 | cluster 5-7 형성, 일부 conflict 해결 |
| day 90 | 150 | mature stack · top 20 score 일관 |
| day 90 batch | -5 (approved) | user batch review → 5 implement |
| ongoing | 100+ | low priority pending, 계속 refine |

→ **시간이 흐를수록 anima 진화 wisdom 누적**.

## 5. 사용자 CLI

```
hexa run tool/proposal_review.hexa                    # top 10 pending interactive
hexa run tool/proposal_review.hexa --id 042
hexa run tool/proposal_approve.hexa --id 042
hexa run tool/proposal_reject.hexa --id 042 --reason "..."
hexa run tool/proposal_implement.hexa --id 042        # post-approve only
hexa run tool/proposal_dashboard.hexa
hexa run tool/proposal_lineage.hexa --id 042          # ancestor/descendant graph
hexa run tool/proposal_debate_resolve.hexa --pair 042,055 --winner 042
hexa run tool/proposal_resurrect.hexa --id 022       # rejected → pending (N cycles 후 가능)
```

## 6. 보호 mechanisms

| mechanism | 동작 |
|---|---|
| **dedup** | sha256(title.lower() + first_evidence_path) |
| **conflict** | conflicts_with[] 필드 + cycle 마다 detect |
| **circular dep** | depends_on cycle detection (DAG verify) |
| **stale decay** | pending > 90d + no new evidence → score halve |
| **flood protect** | max 20 new/cycle (rest queued) |
| **rollback** | archived 잘못 implement → unimplement + back to pending |
| **veto** | reject 3회 누적 → 영구 차단 (resurrection_eligible_after = never) |
| **resurrection** | reject 1-2회 + N cycle 후 새 evidence 발견 시 pending 복귀 |
| **proposal cert** | inventory 진입 전 cert verify (evidence path 실재 + schema valid) |

## 7. cluster auto-detection

5+ related → cluster auto:
- "CP1 acceleration cluster": serve_alm_persona + h_last_ffi + persona swap-in
- "cell learning paradigm cluster": cell extract + composition graph + hexad closure + ablation
- "auto-evolution cluster": closure axis + conjecture + verify + loop
- cluster 형성 시 → roadmap entry 후보 자동 propose (cluster-level meta proposal)

## 8. proposal → module transition gate

```
approved/<id>.json
  ↓ user: hexa run tool/proposal_implement.hexa --id <id>
  ↓ tool spawns sub-agent with proposal as full spec
  ↓ sub-agent builds module + selftest + audit
  ↓ on success: move to archived/, emit module + roadmap entry
  ↓ on fail: stay in approved/, log fail in history
```

→ **자동 implement 절대 금지** (사용자 명시 trigger 만).

## 9. lineage (parent-child 제안)

- 제안 A 가 발전하면서 제안 A' 생성 → A' 의 lineage_parent = A
- B + C merge → D, D 의 merges_with = [B, C]
- E split → E1, E2 — 각각 lineage_parent = E
- 시각화: docs/proposal_lineage_graph.md (mermaid)

## 10. cross-repo sync (nexus hub)

```
anima/state/proposals/      ←→ nexus sync ←→ hexa-lang/state/proposals/
                                                    ↓
                                          airgenome/state/proposals/
```

cross-repo proposal: "anima 의 spawn() 필요 → hexa-lang 의 spawn primitive 만족" → 자동 link.

## 11. metrics dashboard

```
state/proposals/meta/metrics.json:
  total_pending: N
  total_approved: M (waiting impl)
  total_archived: K (impl done)
  total_rejected: R
  total_debate: D
  approval_rate_30d: %
  implementation_lag_days: avg (approved → archived)
  median_age_pending_days: Z
  top_clusters: [...]
  evolution_velocity: proposals_per_cycle
  user_review_lag_days: avg (first_seen → user_decision)
  highest_score_pending: [top 10]
```

→ 매 cycle update.

## 12. β main + auto-evolution + proposal stack 통합 = **cert-graph self-evolution paradigm**

| component | 역할 |
|---|---|
| **cert chain** | anima 의 **인지 graph** (β: 의식은 cert 구조) |
| **proposal stack** | anima 의 **진화 graph** (어떤 새 cert/module 추가할지 후보) |
| **roadmap** | anima 의 **commitment graph** (사용자 approve된 진화) |
| **cell composition** | anima 의 **structure graph** (η-paradigm) |

**통합 원칙**: 모든 변화는 cert verification 또는 user approval 통과해야 적용. anima = 4-graph 의 통합 self-evolving 시스템.

## 13. anti-patterns 방지

- ❌ 자동 implement
- ❌ 자동 .roadmap 수정 (uchg + user gate)
- ❌ circular proposal
- ❌ 동일 idea 중복 spawn (dedup 강제)
- ❌ "implementation 부담 없는 idea 만 쌓기" — effort/impact 필드 강제, score 에 반영
- ❌ 영원한 pending (90d decay)
- ❌ resurrection 무한 (veto count = 3 이면 영구 차단)
- ❌ 자동 cluster 화 (5+ 도달해도 user approve 시까지 cluster 단순 표시)
- ❌ proposal 직접 코드화 (반드시 spec → user → sub-agent 단계)

## 14. snapshot / restore

- proposal stack 전체 = state/proposals/ 디렉토리
- git 으로 일반 commit 가능
- 매주 자동 tag: `proposal-snapshot-week-N`
- restore: git checkout <tag> -- state/proposals/

→ proposal 진화 자체가 anima 학습 history 가 됨 (영구 archived).

## 15. 추가 paradigm — proposal-driven anima

가장 root-level 통찰: **anima = proposal-driven self-system**

- 모든 변화 = 제안에서 시작
- 검증 = cert + user + cycle test
- 적용 = 명시 transition 만
- 폐기 = veto 누적 OR resurrect
- 영구 보존 = archived (영원한 학습)

이 paradigm 자체가 anima 의 **메타 학습 mode** — anima 가 자신의 구조 진화에 대해 학습하는 mode.

---

## 16. 작업 후보 (12 sub-agent batch 가능)

| # | task | 산출물 |
|---|---|---|
| P1 | tool/proposal_inventory_init.hexa (state/proposals/ 구조 + inventory.json 생성) | state/proposals/* + tool |
| P2 | tool/proposal_emit.hexa (blocker/roi scan 후 자동 emit, dedup 포함) | tool + cycle 통합 |
| P3 | tool/proposal_review.hexa (CLI interactive, top 10 표시) | tool |
| P4 | tool/proposal_approve\|reject\|implement\|archive.hexa (4 CLI subtools) | 4 tool |
| P5 | tool/proposal_dashboard.hexa (docs/proposal_dashboard.md) | tool + auto-doc |
| P6 | tool/proposal_lineage_graph.hexa (mermaid) | tool + doc |
| P7 | tool/proposal_cluster_detect.hexa (5+ related → cluster propose) | tool |
| P8 | tool/proposal_conflict_resolve.hexa (debate folder routing) | tool |
| P9 | tool/auto_evolution_loop.hexa (12h cron 통합 — 위 P1-P8 호출) | tool + launchd plist |
| P10 | docs/anima_proposal_stack_paradigm_20260422.md (전체 spec 문서 — 본 문서) | doc ✅ |
| P11 | memory/project_anima_proposal_paradigm.md (β + auto-evolution + proposal 통합 메모) | memory |
| P12 | hexa-lang upstream prompt 작성 (cross-repo proposal sync hub) | docs/upstream_notes/ |

→ **anima local: P1-P11 = 11 tool/doc**. hexa-lang 통합 (P12) 은 별도. 1-2 batch 로 충분.

---

## 17. 7-axis (다른 세션 strategic framework) 매핑

본 paradigm 은 **G axis (meta — 로드맵 자체 자동화)** 의 핵심 구현체.

| axis | 본 paradigm 과의 관계 |
|---|---|
| A launch 최적화 | 분리 (이미 ROI v1 27 항목으로 처리) |
| B post-H100 연구 | 제안 형태로 stack 에 들어감 |
| C 신규 영역 (memory) | 제안 형태로 stack 에 들어감 |
| D ship | 제안 형태로 stack 에 들어감 |
| E infra | 제안 형태로 stack 에 들어감 |
| F CPU superlimit | 제안 형태로 stack 에 들어감 |
| **G meta** | **본 paradigm = G axis 의 핵심 구조** ✅ |

→ A 외 모든 axis 의 work 가 proposal stack 에 누적되어 사용자 검토 대기. 마구잡이 module 생성 방지.

## 18. β paradigm 과의 비교

| 측면 | β main (인지 paradigm) | proposal stack (시스템 paradigm) |
|---|---|---|
| 핵심 거부 | conventional learning | conventional auto-implementation |
| 핵심 추가 | structural admissibility cert | proposal accumulation gate |
| 검증 | cert chain | cert + user approval |
| 진화 | 학습 없는 의식 emerge | implement 없는 idea evolve |
| 적용 시점 | inference time | user trigger time |
| 안전장치 | AN11 triple | veto + decay + dedup |

→ **두 paradigm 은 동형** — 모두 "implicit auto-action 거부 + explicit cert/approval 만 적용".

## 19. roadmap link 후보

`.roadmap` 추가 entries (proposal stack 자체를 roadmap 화):
- #90 proposal stack inventory infra (P1-P5)
- #91 proposal cluster + lineage (P6-P8)
- #92 auto-evolution loop integration (P9)
- #93 cross-repo proposal sync (P12, hexa-lang 의존)

## 20. 메모

본 문서 = `/Users/ghost/core/anima/docs/anima_proposal_stack_paradigm_20260422.md`.
세션: 2026-04-22 anima.
관련:
- `docs/h100_roi_improvements_20260422.md` (ROI 82 항목)
- `docs/cp1_eta_comparison_20260422.md` (CP1→CP2→AGI 비교)
- `docs/upstream_notes/hexa_lang_20260422.md` (hexa-lang 마이그레이션 노트)
- `docs/upstream_notes/roadmap_engine_continuous_meta_proposal_20260422.md` (= hexa-lang/docs 미러)
- memory: `project_h100_launch_pending.md` · `project_main_track_beta.md`

지시 형태:
- (a) P1-P5 batch 1 (core proposal infra)
- (b) P6-P9 batch 2 (cluster/lineage/loop)
- (c) P10-P11 doc + memory
- (d) 위 모두 한번에 (12 sub-agent 병렬)
