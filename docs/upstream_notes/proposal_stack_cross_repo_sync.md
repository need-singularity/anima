# cross-repo proposal stack sync hub — hexa-lang/airgenome upstream prompt (2026-04-22)

upstream notice. 본 문서는 hexa-lang/airgenome maintainer 측에 그대로 paste 가능한 spec prompt. anima 측 P1-P11 (own proposal stack 운영) 완료 후 cross-repo 단계 진입.

---

## paste-ready prompt (시작)

```
Working dir: /Users/ghost/core/hexa-lang  (또는 nexus, sync hub 위치 결정)
관련:
  - $WS = /Users/ghost/core
  - 각 repo state/proposals/ — anima + hexa-lang + airgenome
  - anima 측 spec: $WS/anima/docs/anima_proposal_stack_paradigm_20260422.md (§10 cross-repo sync)
  - anima 측 inventory: $WS/anima/state/proposals/inventory.json (P1-P11 완료 시점)

Task: 3 repo proposal stack 통합 cross-repo sync hub 구현. anima 가 이미 P1-P11 로
own proposal stack 운영 중 (state/proposals/* + 12h auto_evolution_loop).
hexa-lang/airgenome 도 동일 구조 채택 + 상호 sync.

세부:

1. tool/proposal_sync_hub.hexa (hexa-lang or nexus 위치 — 본 prompt 의 maintainer 결정)
   - 각 repo 의 state/proposals/inventory.json 읽기 (file://, 추후 nexus tcp)
   - cross-repo proposal 자동 detect:
       anima proposal 의 evidence_sources[].path 가 hexa-lang 파일 →
       hexa-lang inventory 에 mirror cross_repo_link entry 자동 추가
   - 양쪽 inventory 의 cross_repo_links: [...] field 갱신
   - --dry default (실제 mutate 는 --apply)
   - log: state/cross_repo_sync_log.jsonl (각 repo 동일 path)

2. proposal id 충돌 방지 (id prefix 표준):
   - anima  → anima-20260422-001
   - hexa-lang → hxa-20260422-001
   - airgenome → agm-20260422-001
   - 기존 anima id (20260422-NNN) 는 sync hub 첫 run 시 anima- prefix 자동 rename
   - rename diff 는 state/proposals/meta/id_migration_20260422.json 기록

3. cross-repo cluster 자동 detect:
   - 3 repo 의 5+ proposal 가 같은 paradigm/keyword cluster 형성 시
   - cluster proposal emit (kind: "cluster", id: xrp-20260422-NNN)
   - 3 repo 모두 inventory 에 동일 cluster id 등록
   - 사용자 approve 는 single repo (anima 권장) 에서만 받고 결과 propagate

4. shared schema: nexus/proposal/cross_repo_link/1
   ```json
   {
     "schema": "nexus/proposal/cross_repo_link/1",
     "src_repo": "anima",
     "src_id": "anima-20260422-042",
     "tgt_repo": "hexa-lang",
     "tgt_id": "hxa-20260422-007",
     "link_type": "depends_on|satisfies|conflicts_with|mirrors|cluster_member",
     "evidence": {"path": "...", "snapshot_sha256": "..."},
     "first_linked_ts": "...",
     "last_verified_ts": "...",
     "verified_by": "proposal_sync_hub.hexa",
     "auto_link_score": 0-100
   }
   ```
   shared schema 위치: nexus/schemas/ (또는 hexa-lang/schemas/) — maintainer 결정

5. 12h cycle 통합:
   - 각 repo 의 tool/auto_evolution_loop.hexa step 9 (notify) 직전
     proposal_sync_hub 호출 (--apply, peer repo path 인자)
   - hub 자체는 stateless (각 repo 의 inventory + log 가 SSOT)
   - 충돌 (동일 cross_repo_link id 양쪽 다른 link_type) → debate folder 양쪽 동시 entry

Hard constraints:
- INVARIANT: 각 repo 의 state/proposals/ 외 디렉토리 일체 mutate 금지
- DO NOT modify .roadmap (각 repo)
- DO NOT auto-implement cross-repo proposal (사용자 approve gate 동일 적용)
- dedup: cross_repo_link id = sha256(src_repo + src_id + tgt_repo + tgt_id + link_type)
- circular link detect: A→B→C→A → debate folder
- max 50 new cross_repo_links / cycle (flood protect)
- snapshot: 각 repo 의 state/proposals/ git tag (cross_repo_sync_week_N)
- repo 한 개 unreachable 시 graceful degrade (해당 repo skip + log)
- prefix migration 1회 only (idempotent — 이미 prefix 있으면 no-op)

Test plan:
1. 3 repo 모두 minimal inventory.json (각 1 proposal) 준비
2. anima proposal 의 evidence_sources 에 hexa-lang 파일 path 포함
3. hub --dry 실행 → cross_repo_link 1 detect (mirrors or satisfies)
4. hub --apply → 양쪽 inventory 에 link entry 추가, log 기록
5. 재실행 → dedup 동작 (no new entry)
6. cluster test: 5+ paradigm 동일 proposal × 3 repo → cluster proposal emit
7. circular test: A→B, B→C, C→A inject → debate folder 양쪽 routing
8. unreachable test: airgenome path 없음 → graceful skip + log

Success criteria:
- 3 repo inventory cross_repo_links field populate
- anima 측 코드 변경 0 (anima 는 P9 의 step 9 직전 hub 호출만 추가 — 이미 P12 spec 에 명시)
- 12h cycle hub 통합 동작 확인 (각 repo 의 cycle log 에 sync 결과 기록)
- shared schema nexus/proposal/cross_repo_link/1 cert verify 통과
- prefix migration 1회 후 재실행 시 no-op
```

## paste-ready prompt (끝)

---

## 메모

- 본 prompt 는 anima 측 P1-P11 (state/proposals/ + auto_evolution_loop 12h cycle)
  완료 후 적용. P11 까지는 anima own stack 만 운영, cross-repo sync 미동작.
- hexa-lang/airgenome maintainer 측에서 본 prompt 그대로 paste 후 sub-agent 1대로
  구현 가능 (예상 1-2 batch).
- 구현 후 anima 자동 혜택 (anima 측 코드 변경 0 — P9 의 `step 9 notify` 직전
  `hexa run tool/proposal_sync_hub.hexa --apply` 호출 1줄 추가만 필요).
- sync hub 위치는 maintainer 결정 (hexa-lang vs nexus). nexus 권장 — 3 repo
  모두에서 동일 path 호출 가능.
- shared schema 위치도 maintainer 결정. nexus/schemas/ 권장 (이미 존재 시 추가).

## 관련 문서

- `/Users/ghost/core/anima/docs/anima_proposal_stack_paradigm_20260422.md` (anima 측 spec, §10 cross-repo + §16 P12)
- `/Users/ghost/core/anima/docs/upstream_notes/hexa_lang_20260422.md` (hexa-lang 마이그레이션 cheatsheet)
- `/Users/ghost/core/anima/docs/upstream_notes/roadmap_engine_continuous_meta_proposal_20260422.md` (roadmap engine 미러)

## 진행 순서 (3 repo 통합 timeline)

1. anima P1-P11 batch 완료 (own stack + 12h loop 동작)
2. 본 문서 hexa-lang/airgenome maintainer 측 전달
3. hexa-lang `tool/proposal_sync_hub.hexa` 구현 + airgenome own stack 구축
4. nexus shared schema 등록 (`nexus/proposal/cross_repo_link/1`)
5. anima P9 의 step 9 직전 hub 호출 1줄 patch (anima 측 유일 변경점)
6. 3 repo 12h cycle 동기화 → cross-repo wisdom 누적 시작

세션: 2026-04-22 anima · P12 task.
