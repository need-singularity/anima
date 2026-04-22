# Proposal Review Onboarding — 사용자 첫 review 가이드

**상태**: 2026-04-22 · proposal stack landed (61 pending · 12 cluster auto-detected · 11/11 tools selftest PASS) · 사용자 explicit decision 만 대기.

**원칙 (raw#20 stop-gate paradigm 확장)**:
- 모듈 자동 생성 ❌ → 제안서 누적 ✅
- proposal → module 전환은 **반드시 사용자 명시 trigger 만**
- approve 가 곧 implement 아님 — 별도 `proposal_implement.hexa` 호출 필요

---

## 1. 첫 review session 흐름 (5-step)

### Step 1. 현황 파악 (READ-ONLY)
```
hexa run tool/proposal_review.hexa
```
- 효과: top 10 pending 표시 (score desc, kind/age/refines 표시)
- **소요**: ~5s
- **출력 예시 컬럼**: `ID | score | kind | title | age (d) | refines`

### Step 2. 인벤토리 통계
```
hexa run tool/proposal_dashboard.hexa
```
- 효과: `docs/proposal_dashboard.md` 자동 emit (총 pending/approved/rejected, top cluster, evolution velocity)
- **소요**: ~10s

### Step 3. 개별 detail 검토 (관심 ID 별)
```
hexa run tool/proposal_review.hexa --id 20260422-042
```
- 효과: yaml 형태 full schema 출력 (rationale, evidence_sources, depends_on, conflicts_with, risk, lineage)
- **결정 포인트**: rationale + risk + impact 읽고 approve / reject / 보류 결정

### Step 4. lineage / cluster 컨텍스트 (필요 시)
```
hexa run tool/proposal_lineage_graph.hexa --id 20260422-042
hexa run tool/proposal_cluster_detect.hexa --id 20260422-042
```
- 효과: ancestor/descendant mermaid graph + cluster member count
- **사용 case**: 같은 idea 가 어떻게 진화해왔는지 history 추적

### Step 5. 의사결정 (approve / reject / 보류)
```
# 승인 (모듈 즉시 생성 ❌, approved 상태로 이동만)
hexa run tool/proposal_approve.hexa --id 20260422-042

# 거부 (reason 강제)
hexa run tool/proposal_reject.hexa --id 20260422-042 --reason "<왜 거부하는지>"

# 보류 (아무 것도 안 하기 — pending 유지, 12h cycle 에서 refine)
```

---

## 2. 의사결정 흐름 (decision tree)

```
proposal 표시
  │
  ├─ rationale 명확 + evidence 실재 + risk 0/low → approve 후보
  │     │
  │     ├─ depends_on 모두 archived/done? → approve
  │     └─ depends_on 미해결 → 보류 (depends 먼저 처리)
  │
  ├─ rationale 모호 OR evidence 부재 → 보류 (12h refine 대기)
  │
  ├─ risk high + impact 명확 → debate folder 로 이동 (수동)
  │     hexa run tool/proposal_conflict_resolve.hexa --id <id> --to debate
  │
  ├─ rationale 명확하지만 우리 방향 아님 → reject + reason
  │     veto_count++ → 3회 누적 시 영구 차단
  │
  └─ 다른 제안과 겹침 → cluster 멤버로 묶기 (자동)
```

---

## 3. approval 후 implementation 흐름 (수동 trigger)

approve 만으로 모듈 생성 안 됨. 별도 trigger:

```
# approved → archived 전환 + 모듈 spec 생성
hexa run tool/proposal_implement.hexa --id 20260422-042
```

- 효과: `docs/proposed_implementation_<id>.md` emit (모듈 spec)
- **NEXT**: 사용자가 spec 확인 후 sub-agent delegate (별도 세션)
- **로드맵 등록**: 모듈 빌드 완료 시 `tool/anima_roadmap_lint.hexa` 가 자동 entry 후보 propose

---

## 4. 보호 장치 (이미 구현)

| mechanism | 동작 |
|---|---|
| **dedup** | sha256(title.lower() + first_evidence_path) — emit 시 자동 |
| **conflict** | `tool/proposal_conflict_detect.hexa` 가 12h cycle 마다 detect, debate folder routing |
| **stale decay** | pending > 90d + no new evidence → score halve |
| **flood protect** | max 20 new/cycle (rest queued) |
| **veto** | reject 3회 누적 → `resurrection_eligible_after=never` |
| **resurrection** | reject 1-2회 + N cycle 후 새 evidence → pending 복귀 |
| **proposal cert** | inventory 진입 전 evidence path 실재 + schema valid 검증 |
| **atomic write** | tmp+mv-f 보장 (P4 4 subtools 공통) |

---

## 5. 첫 review 시 권장 batch

**option A — 빠른 방향성 결정 (10-15min)**
1. `tool/proposal_review.hexa` — top 10 표시
2. 각 ID 에 `--id <id>` 로 detail 확인
3. 5-7개 명확한 항목 approve / reject
4. 나머지 보류 (12h cycle 에서 refine)

**option B — cluster 우선 (20-30min)**
1. `tool/proposal_review.hexa --pending` (전체 pending)
2. cluster id (`cluster-20260422-*`) 만 우선 검토
3. cluster 통째로 approve OR reject (포함된 멤버 일괄 처리)
4. 단일 high-score (>70) 만 추가 검토

**option C — risk 우선 (10min)**
1. `tool/proposal_review.hexa --score-min 70`
2. high-priority (score 70+) 먼저 결정
3. 나머지는 다음 세션

---

## 6. 자주 묻는 질문

**Q1. approve 하면 바로 코드 생성되나?**
- ❌ 아니다. approve 는 "approved/" 폴더로 이동만. 모듈은 별도 `proposal_implement.hexa` 트리거 + 사용자 sub-agent delegate 거쳐 생성.

**Q2. reject 한 항목이 다시 올라올 수 있나?**
- 가능. veto_count < 3 이고 새 evidence 가 발견되면 N cycle (기본 30d) 후 pending 복귀. veto_count >= 3 → 영구 차단.

**Q3. 같은 idea 가 중복 제안될 가능?**
- 차단됨. dedup 은 sha256(title.lower() + first_evidence_path) 기준. 12h cycle 의 step 4 에서 자동 dedup.

**Q4. proposal 이 .roadmap 자동 수정하나?**
- ❌ 절대 안 함. INVARIANT: `state/proposals/` 만 mutate. .roadmap 변경은 user gate (uchg) 통과 후 manual.

**Q5. cluster 가 5+ 도달하면 자동 모듈화?**
- ❌ 아니다. cluster 형성은 "표시" 만. 모듈화는 사용자 approve + implement trigger 후만.

**Q6. 12h cycle 이 모든 걸 자동으로 하나?**
- 12h cycle 은 (a) re-evaluate, (b) refine, (c) score update, (d) dedup, (e) cluster detect, (f) conflict route, (g) inventory update, (h) dashboard emit, (i) notify. **새 모듈 생성 / 코드 수정 / .roadmap 변경 절대 안 함.**

---

## 7. 현재 inventory 상태 (2026-04-22 13:12 UTC snapshot)

- **총 entries**: 61 (sample 1 + emit 40 + refinement 20)
- **cluster auto-detected**: 12 (모두 `fix::*` kind_keyword)
- **conflict detected**: 0 (FP 0)
- **status 분포**: pending=대부분, approved=0, rejected=0, archived=0 (사용자 첫 review 전)

```
hexa run tool/proposal_review.hexa --pending
```

→ 위 명령으로 전체 pending list 확인 가능.

---

## 8. 첫 세션 권장 액션

```
# 1) 현황 파악
hexa run tool/proposal_review.hexa
hexa run tool/proposal_dashboard.hexa

# 2) top 10 중 cluster 항목 우선 detail 확인
hexa run tool/proposal_review.hexa --id cluster-20260422-021    # fix::phi (10 멤버)

# 3) 결정 (예시)
hexa run tool/proposal_approve.hexa --id cluster-20260422-021
hexa run tool/proposal_reject.hexa  --id cluster-20260422-007 --reason "manual review 우선"

# 4) 결과 확인
hexa run tool/proposal_review.hexa --approved
hexa run tool/proposal_review.hexa --rejected
```

---

## 9. 참조

- spec: `docs/anima_proposal_stack_paradigm_20260422.md` (P10 · 18 section)
- memory: `memory/project_anima_proposal_paradigm.md`
- cross-repo: `docs/upstream_notes/proposal_stack_cross_repo_sync.md`
- session handoff: `docs/session_handoff_20260422.md`
- 통합 paradigm: `docs/anima_three_paradigm_unified_20260422.md`
