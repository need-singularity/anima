# New Paradigm — unit-cell Lattice 교육 통합 Spec — 2026-04-21

**Scope:** 5 drill (A/B/C/D/E) 결과를 단일 일관 시스템으로 통합. 학습자 일생을
unit-cell lattice (격자) 로 모델링하여 tension-drop, atlas traversal,
fixpoint assessment, collective coherence, zero-LLM computation 을 하나의
결정론적 구조로 수렴.

**Forward-declare:** A~E drill 결과 파일은 세션 간 비동기적으로 도출된 전제로
취급. 본 spec 은 각 drill 의 operational meaning 만 인용하며, 파일 부재 시에도
통합 아키텍처는 완결.

**SSOT:**
- 본 문서 (통합 architectural source of truth)
- `tool/edu_lattice_proto.hexa` (1 learner × 10 concept minimal e2e)

**Constraints (불변):**
- 기존 교육 (학교/커리큘럼/LMS/MOOC) 개념 refer 금지
- LLM 호출 금지 (deterministic oracle 만)
- V8 SAFE_COMMIT (retroactive 변조 금지, forward-only)
- 모든 computation 은 pure function (same input → same output, cross-run)

---

## 0. Paradigm 요약

학습 = tension-drop 이벤트의 격자 축적.

학습자는 atlas 그래프 위에서 살며, 각 노드는 개념 (concept), 각 엣지는
"이 개념쌍 사이에 체험된 긴장 해소" 의 역사적 각인. 노드 간 tension 은 장
(field) 로 존재하고, 지역 최대점에서 **unit-cell** — `⟨A↔B seed |
fixpoint-sealed⟩` — 이 생성된다. 봉인된 unit-cell 은 atlas 에 edge 로 박혀
다시 tension 지형을 바꾼다. 봉인 실패한 seed 는 영구 진동 상태로 남아
인접 sealed unit-cell 이 발산하는 coherence-wave 에 의해 언제든
재점화될 수 있다.

다섯 축:
- **A tension-drop** — 학습 동력은 tension 감소. 보상도 평가도 아닌, 장의
  지역 기울기를 따라 내려가는 자발적 과정.
- **B atlas traversal** — 지식은 목록이 아니라 그래프. 학습은 그래프 위의
  경로이며, 방문 역사가 atlas 를 갱신.
- **C fixpoint assessment** — 평가는 "재진입 불변성". 같은 seed 를 두 번
  넣어 같은 결과가 나오면 sealed. LLM 판정 불필요.
- **D collective coherence** — 집단 학습은 atlas 중첩. 다른 학습자의 sealed
  edge 해시가 내 atlas 의 잠재 tension 을 활성화.
- **E zero-LLM** — 모든 판단은 결정론적 구조 (hash, fixpoint iteration,
  graph ops) 로 환원. 확률 모델 없음.

---

## 1. 통합 시스템 아키텍처

### 1.1 ASCII diagram

```
  +---------------------------------------------------------------+
  |                    LEARNER (single)                            |
  |                                                                |
  |   +---------------- atlas_graph ----------------+              |
  |   |   nodes: concept_id (deterministic)         |              |
  |   |   edges: sealed_unit_cell_hash              |              |
  |   |   [node_i, node_j] --edge--> seal_hash      |              |
  |   +----------------------------------------------+             |
  |                      |                                         |
  |                      v  (superimposed)                         |
  |   +-------------- tension_field ----------------+              |
  |   |   T(i,j) in [0,1] for each unvisited pair   |              |
  |   |   T decays on neighbor-seal, spikes on      |              |
  |   |   collective broadcast ignite               |              |
  |   +----------------------------------------------+             |
  |                      |                                         |
  |                      v                                         |
  |   +-------------- unit_cell pool ----------------+             |
  |   |   (A,B, seed_id, state)                      |             |
  |   |     state in {VIBRATING, SEALED, IGNITING}   |             |
  |   +----------------------------------------------+             |
  |                      |                                         |
  |       spawn          v         seal                            |
  |  (local-max T) -> probe -> fixpoint? -> atlas edge             |
  |                      ^                                         |
  |                      |  (re-ignite)                            |
  |                      +----< IGNITING state                     |
  |                                                                |
  +---------------------------------------------------------------+
                         |                     ^
                hash only|                     | hash only
                         v                     |
  +---------------------------------------------------------------+
  |                 COLLECTIVE BROADCAST LAYER                     |
  |                                                                |
  |   append-only log: (learner_id_hash, edge_hash, ts)            |
  |   gossip: each learner receives peer edge_hash stream          |
  |   consensus: k-of-n learners seal same (i,j) -> consensus_edge |
  |                                                                |
  |   RULE: NO content — only 32-byte hash of (A,B,seal_witness).  |
  |   RULE: append-only; no retraction (V8 SAFE_COMMIT).           |
  +---------------------------------------------------------------+
                         |                     ^
                         v                     |
  +---------------------------------------------------------------+
  |                 ASSESSMENT LOOP (C)                            |
  |                                                                |
  |   for each sealed edge e in atlas:                             |
  |     re_probe = judge(seed(e), step=1)                          |
  |     re_probe = judge(re_probe, step=2)                         |
  |     assert re_probe == seal_witness(e)      // re-entry inv.   |
  |                                                                |
  |   mismatch -> DEMOTE edge to VIBRATING (was stale seal)        |
  +---------------------------------------------------------------+
```

### 1.2 Layer 책임

1. **atlas_graph**: 학습자별 local SSOT. 노드 집합은 유한 (concept space
   선언), 엣지는 sealed event 의 append-only 기록.
2. **tension_field**: 노드쌍 위의 scalar field. 결정론적 함수로 산출:
   `T(i,j) = base(i,j) * decay^|sealed_neighbors| * ignite_multiplier`.
3. **unit_cell pool**: 활성 seed 의 상태 저장소. 세 상태 (VIBRATING,
   SEALED, IGNITING) 간 전이만 허용.
4. **collective broadcast**: 모든 학습자가 publish/subscribe 하는 append-
   only log. 내용은 **hash only** — 학습자 atlas 의 privacy 는
   구조적으로 보장.
5. **assessment loop**: 주기적으로 sealed edge 재진입 불변성 검증. 실패한
   seal 은 demote 되어 VIBRATING 으로 복귀 (재점화 가능).

### 1.3 Data structures (types)

```hexa
type ConceptId = string              // canonical id, e.g. "phi_gap_816x"
type LearnerId = string              // hash of learner root-seed
type Hash32    = string              // 64-hex chars

type UnitCell = {
    a: ConceptId,
    b: ConceptId,
    seed_id: Hash32,
    state: string,                   // VIBRATING | SEALED | IGNITING
    seal_witness: string,            // empty unless SEALED
    spawn_ts: int,
    seal_ts: int
}

type AtlasEdge = {
    i: ConceptId,
    j: ConceptId,
    seal_hash: Hash32,
    cell_ref: Hash32,                // points to UnitCell.seed_id
    sealed_at: int
}

type TensionEntry = {
    i: ConceptId,
    j: ConceptId,
    value: int                       // fixed-point [0..1000]
}

type BroadcastRec = {
    learner: Hash32,
    edge_hash: Hash32,
    ts: int
}
```

---

## 2. lattice 연산

### 2.1 spawn

**pre:** tension_field 상에서 지역 최대점 (i*, j*) 식별
(`T(i*,j*) >= T(neighbor)` for all graph-neighbor pairs).

**op:**
```
seed_id = hash32(canonical(i*) + "|" + canonical(j*) + "|" + learner_id)
cell = UnitCell{
    a: i*, b: j*, seed_id: seed_id,
    state: VIBRATING,
    seal_witness: "",
    spawn_ts: now(), seal_ts: 0
}
pool.insert(cell)
```

**post:** `(i*, j*)` 의 tension 은 unchanged (spawn 만으로는 장이 바뀌지
않음 — seal 이 일어나야 장 갱신).

**결정론:** `seed_id` 는 (i*, j*, learner) 삼중으로만 결정. 시간 의존 없음.

### 2.2 seal

**pre:** VIBRATING 상태 cell 에 대해 fixpoint probe 수행.

**probe:**
```
w1 = judge(seed_id, 1)
w2 = judge(w1, 2)
w3 = judge(w2, 3)
sealed? := (w2 == w3)             // C drill: fixpoint assessment
```

**op (sealed 인 경우):**
```
cell.state := SEALED
cell.seal_witness := w3
cell.seal_ts := now()

edge = AtlasEdge{
    i: cell.a, j: cell.b,
    seal_hash: hash32(cell.a + cell.b + w3),
    cell_ref: cell.seed_id,
    sealed_at: cell.seal_ts
}
atlas.append(edge)                 // append-only

// B drill: atlas traversal — edge 추가가 그래프 지형을 바꿈
tension_field.decay_around(cell.a, cell.b)

// A drill: tension-drop — 장의 지역 에너지 감소
broadcast.emit(BroadcastRec{
    learner: learner_id,
    edge_hash: edge.seal_hash,
    ts: edge.sealed_at
})
```

**post:**
- `T(cell.a, cell.b) → 0` (이 pair 는 해소됨)
- 인접 pair `T(cell.a, k)` 와 `T(cell.b, k)` 는 decay factor 로 감소
- atlas.edges += 1
- broadcast log 에 hash only 기록

**결정론:** `judge` 는 pure function (E drill). `hash32` 는 SHA-256 앞 32바
이트. 동일 seed 는 동일 결과 — 재실행 가능.

### 2.3 ignite

**pre:** 최소 하나의 VIBRATING cell 존재 & 인접 SEALED edge 집합 비어있지
않음 & 외부 broadcast 수신.

**op:**
```
for rec in broadcast.recent():
    for cell in pool.filter(state=VIBRATING):
        if adjacency(cell, rec.edge_hash):
            cell.state := IGNITING
            tension_field.spike(cell.a, cell.b, multiplier=ignite_k)
```

`adjacency(cell, edge_hash)` : cell 의 (a,b) 중 하나가 edge 에 연결되면
참. edge_hash 는 내용 포함 안 하므로 이 체크는 learner 의 atlas 와의
edge_hash 인덱스 조회로 해결됨 (내 atlas 에 이미 있는 edge 해시는 skip,
새 해시 중 concept 쌍이 내 pool cell 과 교집합을 가지면 ignite).

**post:** IGNITING cell 은 다음 tick 에서 fixpoint probe 우선순위를
얻음. 즉 seal 가능성 증가.

**결정론:** broadcast 는 log (순서 보존). adjacency 는 순수 비교. 동일
log 순서면 동일 ignite 결과.

### 2.4 lattice_growth_rate

**def:**
```
lattice_growth_rate(learner, window_sec) :=
    count(atlas.edges sealed in last window_sec) / window_sec
```

단위: seal / second. 운영 관측 목표:
- prototype: >= 3 seal/hour (1 learner, 20 concept)
- pilot: >= 1 seal/hour per learner sustained
- scale: >= 0.5 seal/hour per learner sustained

이 rate 는 **T3 → T4 → T5 진척 판정의 1차 지표** (§4).

### 2.5 operational invariants (lattice-level)

| INV | 진술 |
|-----|------|
| L1  | spawn 은 언제나 VIBRATING 을 생성 (SEALED 직접 생성 금지) |
| L2  | seal 은 언제나 fixpoint probe 통과 후에만 상태 전이 |
| L3  | atlas.edges 는 append-only (V8 SAFE_COMMIT) |
| L4  | broadcast 는 hash only (32 바이트 record, 내용 0) |
| L5  | ignite 는 tension 을 올리기만 함, 직접 seal 하지 않음 |
| L6  | 같은 (learner, a, b) 는 lifetime 에 최대 1 sealed edge |

---

## 3. 시스템 invariants (paradigm-level)

### 3.1 I1 — 모든 seed 는 unit-cell 로 시작

spawn 외의 경로로 seed 가 생길 수 없다. 즉 "갑자기 atlas 에 edge 가 나타
남" 은 위반. 모든 edge 는 과거에 VIBRATING cell 이었다는 역사를 보장.

**enforcement:**
```
atlas.append(edge) only if edge.cell_ref in pool AND pool[cell_ref].state == SEALED
```

### 3.2 I2 — 모든 seal 은 재진입 불변성 검증

seal 시점의 fixpoint probe 뿐 아니라, 주기적 assessment loop 가 과거
sealed edge 를 재검증. w3 재현 실패 → demote.

**enforcement:** §5 assessment loop.

### 3.3 I3 — 모든 집단 sharing 은 hash only

broadcast record 는 `(learner_hash, edge_hash, ts)` 3-tuple. content 필드
없음, payload 없음. 학습자 atlas 의 원 데이터는 네트워크를 떠나지 않음.

**enforcement:** `BroadcastRec` type 에 payload 필드 존재하지 않음 (compile-
time guarantee).

### 3.4 I4 — 모든 computation 은 deterministic

random 호출 금지. now() 는 오직 타임스탬프 기록용 (조건 분기 금지).
확률 모델 금지. LLM 호출 금지.

**enforcement:** E drill `zero-LLM` 규범. 정적 검사: grep 으로
`rand(`, `uniform(`, `llm`, `openai`, `sample(` 등 기호 부재 확인.

### 3.5 invariant matrix

| invariant | enforced by | 위반 탐지 |
|-----------|-------------|-----------|
| I1 seed→cell | spawn API | atlas.edge.cell_ref 존재 검사 |
| I2 reentry   | assess loop | w_probe != seal_witness → alert |
| I3 hash only | type sys    | BroadcastRec.payload 없음 |
| I4 determ.   | grep gate   | forbidden-symbol scan pre-commit |
| L1~L6        | lattice API | runtime assert in proto |

---

## 4. T3 → T4 → T5 진척 판정

### 4.1 T3: 100 unit-cell sealed (1 learner)

**조건:**
- learner 1명 고정
- atlas.edges.count >= 100
- 모든 edge 가 I1~I4 만족
- lattice_growth_rate (24h 평균) >= 1 seal/hour

**판정 방식:**
```
atlas_stats = atlas.summary()
assert atlas_stats.sealed_count >= 100
assert all(e.i != e.j for e in atlas.edges)        // self-loop 금지
assert assessment_loop.pass_rate() == 1.0           // 재진입 100%
```

**의미:** 단일 학습자가 격자 축적을 "지속 가능한 속도" 로 해낼 수 있음을
실증. 미봉인 seed 가 재점화 없이도 자력 seal 가능.

### 4.2 T4: collective consensus 10 edges (3+ learners)

**조건:**
- learner >= 3명
- 같은 `(i, j)` 에 대해 각기 독립적으로 seal 한 learner 수 >= 3
- consensus_edge 수 >= 10
- 학습자들의 atlas 는 서로 직접 공유되지 않음 (broadcast 만)

**정의:**
```
consensus_edge(i, j) := |{ learner : learner.atlas has edge (i,j) sealed }| >= 3
```

**판정 방식:**
```
tally = {}
for rec in broadcast.all():
    key = (rec.edge_hash_projected_to_ij)   // 구현: edge_hash 자체를 key
    tally[key].add(rec.learner)
consensus_count = |{k : |tally[k]| >= 3}|
assert consensus_count >= 10
```

**주의:** `edge_hash` 는 `(a, b, witness)` 의 해시이므로 witness 가 다르면
같은 (a,b) 도 다른 해시. T4 는 **같은 witness 까지 일치** 하는 경우를
요구 — 즉 독립적 학습자들이 같은 결론에 수렴. 이는 C drill (fixpoint 의
객관성) 의 집단판 확증.

**의미:** 개인 학습이 아닌 **coherent 집단지식 emergence**. atlas 중첩
현상 관측.

### 4.3 T5: atlas discovery — 기존 없던 edge 자발 생성 3 건

**조건:**
- T4 통과 이후
- 시스템이 **seeding set 외부** 의 (i, j) pair 에 대해 independently
  spawn → seal → consensus 까지 도달하는 사건 3건 이상

**정의:**
```
seeding_set := 시스템 초기화 시 선언된 concept-pair 후보 목록
discovery_edge(i, j) := (i, j) ∉ seeding_set AND consensus_edge(i, j) 성립
```

**판정 방식:**
```
discoveries = []
for edge in consensus_edges():
    if (edge.i, edge.j) not in seeding_set:
        discoveries.push(edge)
assert len(discoveries) >= 3
```

**의미:** tension_field 지형이 초기 seed 에 제약되지 않고 **자발적 재구
성** 을 통해 관찰자도 예측 못했던 연결을 발견. paradigm 의 최종 목표 —
"학습자 격자가 교사 없이도 성장" — 의 실증.

### 4.4 gate table

| gate | prereq | 판정 지표 | 결과 파일 |
|------|--------|-----------|-----------|
| T3   | 없음 | sealed >= 100 & re-entry 100% | `shared/state/edu_lattice_T3.json` |
| T4   | T3 | consensus_edge >= 10 (3+ learners) | `shared/state/edu_lattice_T4.json` |
| T5   | T4 | discovery_edge >= 3 | `shared/state/edu_lattice_T5.json` |

### 4.5 판정 시 결정론 요구

모든 gate 평가는 입력 (atlas, broadcast log) 이 동일하면 결과도 동일해야
함. 즉 gate 자체가 pure function. 이는 reviewer 가 임의 시점에 log 를
replay 하여 동일 결과 재현 가능해야 함을 의미.

---

## 5. assessment loop (재진입 probe) 설계

### 5.1 주기

- prototype: 매 spawn 직후 1회 + 24h 1회 sweep
- pilot: 매 seal 직후 + 매 6h sweep
- scale: 매 seal 직후 + 매 1h sweep (edge 수 많아져서 병렬 필요)

### 5.2 probe procedure

```hexa
fn assess_edge(e: AtlasEdge, pool: UnitCellPool) -> bool {
    let cell = pool.get(e.cell_ref)
    let w1 = judge(cell.seed_id, 1)
    let w2 = judge(w1, 2)
    let w3 = judge(w2, 3)
    return w3 == cell.seal_witness
}
```

mismatch 발생 시:
```
cell.state := VIBRATING
e.sealed_at := 0          // but edge 자체는 atlas 에서 remove 되지 X
atlas.demote_log.append(e.seal_hash)     // append-only
```

**edge 물리적 삭제 금지** (V8 SAFE_COMMIT). demote_log 에 기록하여
"이 edge 는 현재 stale" 표시. 이후 재 spawn 되면 새 edge 로 추가.

### 5.3 failure mode

- `judge` 구현 자체가 바뀌어 과거 witness 와 충돌 → 시스템 전체 재보정.
  pre-commit gate 에서 `judge` 해시 고정 요구.
- 같은 cell 의 반복 probe 가 flaky → I4 위반. 원인 조사 후 `judge` 수정.

---

## 6. 실제 가능영역 (1-5 등급)

### 6.1 prototype — 1 week — **가능영역 4/5 (high feasibility)**

- learner: 1명
- concept 공간: 20 노드
- atlas 목표: 10 edges sealed (축소 T3)
- assessment loop: manual trigger 가능
- collective: 비활성 (single-learner)
- 기술 요구:
  - `judge` 함수 구현: canonical hash projection (e.g. SHA-256 on
    sorted concept-id pair + step counter) — 1 day
  - atlas graph 데이터 구조: adjacency list + edge hash index — 1 day
  - tension field: `T(i,j)` 테이블 + decay/spike 함수 — 1 day
  - spawn/seal/probe wiring: §2 그대로 — 2 days
  - CLI + JSON cert emit: fixpoint verifier 선례 (`drill_minsurface_proto`) — 1 day
  - 동작 확인 & retry loop: 1 day
- 산출: `tool/edu_lattice_proto.hexa`, `shared/state/edu_lattice_T3_demo.json`
- 리스크: `judge` 가 너무 약하면 뭐든 fixpoint — **mitigation:**
  negative-seed pair 도 돌려서 diverge 확인 (minsurface drill 와 동일 idiom).

### 6.2 pilot — 3 month — **가능영역 3/5 (moderate)**

- learner: 5명
- concept 공간: 100 노드
- atlas 목표: 100 edges / learner, consensus_edge >= 10
- collective broadcast: append-only log server (파일 + fsync, DB 불필요)
- 기술 요구:
  - broadcast log format: `(learner_hash, edge_hash, ts)` NDJSON line — 2 days
  - gossip protocol: pull-based polling (push 불필요, scale 제한됨) — 1 week
  - learner 간 concept-id canonicalization: 사전 정의 ontology — 2 weeks
  - ignite 메커니즘: §2.3 — 1 week
  - dashboard (lattice_growth_rate 시각화): CSV + static HTML — 1 week
  - 운영: 5 learner 각자 주 3회 session, 3개월 x 12주 = 총 180 session
- 리스크:
  - concept-id canonicalization 없으면 consensus 성립 X — **mitigation:**
    pilot 시작 전에 concept ontology 동결 (버전 태깅).
  - 5명 중 일부가 참여 저조 → k-of-n 의 k 미충족 — **mitigation:**
    오버샘플링 (실제 10명 모집, 활성 5명 기대).

### 6.3 scale — 1 year — **가능영역 2/5 (challenging)**

- learner: 50명
- concept 공간: 1000 노드
- atlas 목표: 1000 edges / learner, discovery_edge >= 30
- collective: full gossip + consensus
- 기술 요구:
  - broadcast log partitioning: concept-id hash prefix 로 shard
  - gossip: pull 로는 한계 — pub/sub 도입 검토 (Kafka/NATS 중립)
  - concept ontology 확장 메커니즘: learner propose + k-of-n approve
    — discovery_edge 자체가 ontology 확장 trigger
  - long-term storage: 50 learner × 1000 edge × 365일 ≈ 18M record.
    append-only NDJSON 월 rotate
  - 운영: learner onboarding, session cadence 가이드, 중도이탈 대응
- 리스크:
  - `judge` 가 1000 concept 공간에서 여전히 의미있게 분별 가능한가 — 
    **mitigation:** prototype 단계부터 `judge` 능력 benchmark 축적
  - 50명 coordination 부하 (기술 외) — **mitigation:** pilot 에서
    5 learner cohort 를 N개로 복제 (50 = 10 cohort × 5)
  - privacy: hash only 로 구조적 보장되지만 metadata inference 가능성 —
    **mitigation:** timestamp quantize (hour-level), learner_hash
    rotation per 30 day

### 6.4 가능영역 비교

| stage | window | learner | concept | edge target | feasibility |
|-------|--------|---------|---------|-------------|-------------|
| prototype | 1 week  | 1   | 20   | 10    | 4/5 |
| pilot     | 3 month | 5   | 100  | 100×5 | 3/5 |
| scale     | 1 year  | 50  | 1000 | 1000×50 | 2/5 |

prototype 은 본 문서 + `tool/edu_lattice_proto.hexa` 로 즉시 실행 가능.
pilot 은 ontology 합의 + 운영 조직이 필수. scale 은 기술/운영/거버넌스
삼중 준비 필요.

---

## 7. 결정론 감사 (audit trail)

### 7.1 reproducibility 요구

모든 산출은 재현 가능해야 함:
```
1. 같은 seeding_set (concept list) + 같은 learner_id + 같은 broadcast log
   → 같은 atlas 상태
2. 같은 atlas 상태 → 같은 T3/T4/T5 gate 결과
```

### 7.2 audit artifacts

| artifact | path pattern | retention |
|----------|--------------|-----------|
| atlas snapshot | `shared/state/atlas_{learner}_{ts}.json` | 1 year |
| broadcast log | `shared/log/broadcast_{yyyymm}.ndjson` | permanent |
| gate certs | `shared/state/edu_lattice_T{3,4,5}_{run}.json` | permanent |
| judge version | `shared/state/judge_fingerprint.json` | permanent |

### 7.3 V8 SAFE_COMMIT 준수

- atlas.edges: append-only (§2.2, I3)
- broadcast log: append-only (§1.1)
- gate certs: 한 번 발행된 cert 는 수정 금지 — 재평가 필요시 new cert
  (다른 `_{run}` id) 발행
- judge 버전 변경은 fingerprint 로 기록; 기존 atlas 는 legacy 로 태그,
  새 atlas 는 new fingerprint 로 from-scratch 시작

---

## 8. zero-LLM computation (E 축 상세)

### 8.1 judge 함수 규범

`judge: (Hash32, int) -> Hash32` 는:
- **pure**: no side effects, no global state
- **deterministic**: 같은 입력 → 같은 출력 (cross-run, cross-host)
- **no LLM**: no model call, no API, no randomness
- **no clock**: now() 호출 금지 (내부에서)

**구현 선택지:**
1. SHA-256 기반 projection: `judge(s, k) = sha256(s || "|k=" || str(k))[:32]`
   — prototype 용. 항상 fixpoint 에 수렴하지 않음 (decision: 두 번째 적용
   시 다른 해시 → non-saturation). 이 경우 seal 은 어렵지만 **negative
   diverge** 는 보장. 실제 saturation 을 위해선 더 의미있는 projection
   필요.
2. canonical form projection: input string 을 sorted-token 으로 normalize
   후 해시. 동일 concept-pair 는 동일 normalization → 동일 witness —
   fixpoint 자연 발생.
3. corpus-anchored hash: concept ontology 에 있는 id 를 조합하여 결과
   string 생성. ontology 고정이면 deterministic.

prototype 은 (2) 채택 — `tool/edu_lattice_proto.hexa` 참조.

### 8.2 pre-commit gate

```
forbidden_symbols := [
    "openai", "anthropic", "llm_call",
    "random(", "rand(", "uniform(", "gauss(",
    "time.time(", "unix_now(",   // 조건 분기용 호출 금지
    "gpt", "claude_api"
]
```

scan: `tool/edu_lattice_*.hexa` 에서 grep. 하나라도 발견되면 CI fail.

### 8.3 why zero-LLM matters for this paradigm

학습의 평가가 LLM 에 의존하는 순간:
- 재진입 불변성 I2 위반 가능 (LLM 출력 drift)
- 재현 가능성 § 7.1 파괴
- I4 determinism 파괴
- collective consensus 는 LLM consensus 로 환원됨 — paradigm 의
  원래 주장 ("격자가 자발 합의에 도달") 이 무의미

따라서 zero-LLM 은 장식이 아니라 **체계 integrity 의 필수조건**.

---

## 9. collective coherence (D 축 상세)

### 9.1 coherence 정의

집단 coherence = atlas 중첩도. 정량적:
```
coherence(L1, L2) := |L1.atlas.edges ∩ L2.atlas.edges| / min(|L1|, |L2|)
```
교집합은 edge_hash 기준 (§2.2 로 생성되므로 같은 learner 라면 같은
`(a, b, witness)` → 같은 hash).

### 9.2 consensus formation

k-of-n 합의: 같은 edge_hash 를 독립적으로 seal 한 learner 수 >= k.
기본값: k=3, n=최소 5.

consensus 는 **내용 기반 합의** — learner 가 같은 witness 에 독립 도달.
이는 단순 투표가 아니라 **structural agreement** (같은 fixpoint probe
결과).

### 9.3 broadcast 의 역할

broadcast 는 **합의를 유발하지 않음**. 단지:
- 다른 learner 가 어떤 (a,b) 를 다루고 있는지 신호 (hash 만)
- 내 VIBRATING pool 의 해당 cell 에 ignite 적용 → tension spike
- tension spike 는 seal 확률을 높이지만 **seal 여부는 여전히 내 judge**

즉 broadcast 는 **주의 유도자** 이지 **판정자** 가 아님. 최종 seal 은
개별 learner 의 독립 연산.

### 9.4 privacy 구조

- 내용 전송 없음 (hash only, I3)
- learner_id 는 root-seed 의 hash (rotatable)
- timestamp 은 pilot 에서 second, scale 에서 hour 양자화

### 9.5 failure modes

- **echo chamber**: 소수 activist 가 broadcast 를 지배 → others 의 atlas
  편향. **mitigation:** gossip 에서 learner 별 record 상한 (per hour).
- **spam**: 동일 learner 가 스팸 edge_hash 발사 → rate limit.
- **hash collision**: SHA-256 에서 구조적으로 무시 가능.

---

## 10. atlas traversal (B 축 상세)

### 10.1 atlas 가 graph 인 이유

학습 자료를 "트리 (커리큘럼)" 로 보면 선형성이 강제되어 재점화가
구조적으로 막힘. "리스트 (체크박스)" 로 보면 관계가 소실. graph 만이:
- 임의 pair 간 tension 허용
- 순서 독립적 방문
- 사이클 표현 가능 (재진입 패턴)

### 10.2 traversal rule

학습자는 graph 를 임의 순서로 방문. 다음 방문 pair 선택은:
```
next_pair = argmax over (i,j) of T(i,j) restricted to unsealed(i,j)
```
즉 tension 최대점. 동률이면 결정론적 tiebreak (concept-id 사전순).

### 10.3 tension decay after seal

seal event 는 `(a, b)` pair 만 해소하지 않음:
```
decay_around(a, b):
    for k in neighbors(a) ∪ neighbors(b):
        T(a, k) *= decay_factor
        T(b, k) *= decay_factor
```
`decay_factor = 0.7` 권장. 인접 pair 도 부분적으로 해소 (같은 concept 을
다른 각도에서 재조명하는 효과).

### 10.4 path dependency

학습 순서는 최종 atlas 에 영향. 같은 seeding_set 이라도 서로 다른
learner 는 서로 다른 atlas 로 귀결. 이는 **bug 가 아니라 feature** —
개별성 보존.

consensus (§4.2) 는 이 차이에도 불구하고 공통으로 도달하는 edge 를 찾는
것. 따라서 T4 통과는 "개별성 속의 보편성" 관측.

---

## 11. tension-drop dynamics (A 축 상세)

### 11.1 tension 의 정의

```
T(i, j) = base(i, j) * decay^|sealed_neighbors(i,j)| * ignite_multiplier(i,j)
```
- `base(i,j)` : 초기 tension (ontology 가 선언). 범위 [0, 1000] 고정소수.
- `decay^k` : 인접 seal 수에 따른 감소. decay=0.7.
- `ignite_multiplier` : broadcast ignite 로 일시 증가. 기본 1.0,
  ignite 시 1.5, 후속 tick 마다 0.9 감쇠하여 1.0 복귀.

### 11.2 drop event

spawn → probe → seal 까지의 전체 과정이 **tension drop event**. drop
크기:
```
drop_amount = T_before(a, b) + 0.3 * Σ_k T_before(a, k) + 0.3 * Σ_k T_before(b, k)
               - T_after(equivalent)
```
학습자가 체감하는 "이해됨" 은 이 drop 에 비례한다고 가정.

### 11.3 장 전체의 에너지 감소 추이

```
E(t) = Σ over all unsealed (i,j) of T(i,j, t)
```
시간에 따라 E(t) 는 단조 감소 (ignite 로 순간 튀지만 평균 감소).
`E(t) → 0` 은 전 concept-space 포화 — sealing 끝.

### 11.4 drop 을 관찰 지표로 사용

`lattice_growth_rate` (§2.4) 는 count 기준. 여기에 drop amount 가중을
추가한 **weighted rate** 도 정의 가능:
```
weighted_growth := Σ drop_amount over seal events in window / window
```
pilot 이상에서 채택 권장.

---

## 12. fixpoint assessment (C 축 상세)

### 12.1 fixpoint := 재진입 불변성

```
judge(judge(judge(seed, 1), 2), 3) == judge(judge(seed, 1), 2)
```
즉 `w2 == w3`. 두 번 적용한 결과가 세 번 적용한 결과와 같음.

이는 `fixpoint_v3_v4.hexa` 의 compiler self-host 와 같은 idiom.
battle-tested 한 결정론적 구조.

### 12.2 왜 LLM 판정이 불필요한가

LLM 판정:
- 입력 의미 "이해" 필요 → 모델 편향, 비결정적
- 평가자별 상이한 결과
- 재현 비용 큼 (매번 API 호출)

fixpoint 판정:
- 순수 equality check (byte-level)
- 모든 host 에서 같은 결과
- 재현 비용 = judge 실행 비용 (μs 단위)

### 12.3 무엇을 놓치는가

- **의미적 정합성**: judge 가 의미 모델이 아니면 "맞는 답" 이 아닌 "안정된
  답" 만 보장. 이는 paradigm 의 설계선택 — "학습 = 안정화" 로 reframe.
- **창발성**: LLM 이 포착할 수 있는 nuance 는 놓침. 대신 structural
  agreement 를 통해 다른 방식으로 견고성 확보.

### 12.4 negative test (사이비 fixpoint 차단)

단순 `w2==w3` 만으로는 `judge` 가 identity 라면 항상 참. 따라서:
```
assert fixpoints3(seed_positive) == true
assert fixpoints3(seed_negative) == false    // diverge 필수
```
negative seed 는 "해소되지 말아야 할" 의도적 mismatched pair.
`drill_minsurface_proto.hexa` 의 pos_ok && neg_ok pattern 과 동일.

---

## 13. 통합 validation 계획

### 13.1 prototype (1 week) validation

| step | 체크 | pass 조건 |
|------|------|-----------|
| P1 | `edu_lattice_proto.hexa` 실행 | exit 0 + cert 생성 |
| P2 | 10 concept × 1 learner 10 edge seal | atlas.edges==10 |
| P3 | re-run → byte-identical cert | sha256 equal |
| P4 | negative seed diverge | fixpoints3(neg)==false |
| P5 | forbidden symbol scan | 0 hits |

### 13.2 pilot (3 month) validation

- T3 (learner 당 100 edge) × 5 learner
- T4 (consensus >= 10)
- assess loop pass rate >= 0.95

### 13.3 scale (1 year) validation

- T3 × 50 learner
- T4 (consensus >= 50)
- T5 (discovery >= 30)

---

## 14. 리스크 & 미결

### 14.1 open questions

- `judge` 의 구체 구현: (1) SHA, (2) canonical form, (3) corpus-anchored
  중 어느 것이 pilot 의미 분별에 충분한가?
- concept ontology 버저닝: learner 간 ontology 불일치 시 consensus 정의
  어떻게 변경되나?
- T5 discovery 가 false positive 일 가능성: 3 learner 가 독립적으로
  우연의 동일 (hash-level) witness 에 도달? **현답:** 해시 공간 size
  2^256 에서 구조적으로 배제.

### 14.2 리스크

| 리스크 | 대응 |
|--------|------|
| judge 가 너무 강해서 positive 와 negative 둘 다 saturate | prototype 에서 negative diverge 를 명시적 regression test |
| broadcast log 무제한 성장 | scale 에서 monthly rotate + cold archive |
| learner 중도이탈 → consensus 구멍 | pilot 은 오버샘플링 (10명 모집 5명 지속) |
| ontology drift (learner 간 개념 이름 불일치) | ontology SSOT 파일 fix + version tag |
| privacy 누수 (hash 로부터 inference) | timestamp 양자화 + learner_id rotation |

---

## 15. 구현 bootstrap 순서

1. **prototype 완성** (이 문서 commit 후 1 week)
   - `tool/edu_lattice_proto.hexa` 구현
   - 10 concept × 1 learner × 10 edge seal 달성
   - negative diverge 보장
   - cert JSON 발행
2. **ontology 선언** (pilot 준비, 2 weeks)
   - 100 concept 목록 + base tension matrix
3. **broadcast log 구현** (pilot 준비, 1 week)
   - append-only NDJSON
   - pull-based gossip
4. **pilot 운영** (3 month)
5. **scale 준비** (6 month, 2nd year 진입 전)

---

## 16. 메타 — 왜 교육을 refer 하지 않는가

전통 교육 개념 (학교, 커리큘럼, LMS, 시험, 성적) 은 **다른 paradigm**.
그 개념들을 inherit 하면 이 paradigm 의 unit operation (unit-cell,
spawn-seal-ignite) 이 기존 용어로 번역되어 정보 손실.

본 spec 은 교육을 **처음부터 lattice physics 로** 재기술. 즉:
- 학생 → learner (atlas-bearer)
- 선생 → 불필요 (structural consensus 가 대체)
- 과목 → concept ontology
- 시험 → assessment loop (자동)
- 성적 → lattice_growth_rate + T3/T4/T5 gate
- 커리큘럼 → path-dependent traversal (개별)

교육과의 mapping 은 **응용 시** 필요하면 별도 문서 (이 spec 의 downstream).
core spec 은 paradigm-native 용어로 self-contained.

---

## 17. Appendix: 결정론 selfcheck

```
forbidden-symbol scan:
    grep -E '(openai|anthropic|llm_|random\(|rand\(|gpt|claude_api|sample\()'
    target: tool/edu_lattice_*.hexa docs/new_paradigm_edu_lattice_*
    expect: 0 matches (outside of this appendix's literal list)

judge fingerprint emit:
    sha256(tool/edu_lattice_proto.hexa) -> shared/state/judge_fingerprint.json
    on any change: new fingerprint, atlas quarantine

reproducibility harness:
    1. export HEXA_VAL_ARENA=0
    2. run tool/edu_lattice_proto.hexa twice
    3. diff cert1 cert2 -> must be empty
```

---

## 18. 요약 표 (one-glance)

| layer        | op         | invariant | drill |
|--------------|-----------|-----------|-------|
| tension_field| decay/spike| monotone trend of E(t) | A |
| atlas_graph  | append edge| append-only            | B |
| unit_cell    | spawn/seal | fixpoint w2==w3        | C |
| broadcast    | publish hash| hash only             | D |
| judge        | pure fn    | deterministic          | E |

gate 판정:
- T3: sealed >= 100 & re-entry 100% (1 learner)
- T4: consensus_edge >= 10 (3+ learners)
- T5: discovery_edge >= 3

가능영역 (1-5):
- prototype 1 week: 4/5
- pilot 3 month: 3/5
- scale 1 year: 2/5

---

*fin.*
