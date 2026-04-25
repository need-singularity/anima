# Anima ↔ Sister Repo Coordination — Abstraction Layers

> **scope**: 5-repo (anima · nexus · hexa-lang · airgenome · hive · n6-architecture) coordination 의 현재 substrate (L0) 부터 절대 한계 (L5/L∞) 까지.
> **POLICY R4**: `.roadmap` 미수정. 외부 consolidation only.
> **raw 준수**: raw#1 (uchg SSOT) · raw#10 (proof-carrying hash-chain) · raw#12 (cherry-pick 금지) · raw#25 (concurrent-git-lock safe commit).
> **brutal honesty 모드**: V8 SAFE_COMMIT ceremony 의 manual cost 를 직시한다.

---

## §0. 5-repo topology (현재 substrate)

| repo | 역할 | path | inbox prefix |
|---|---|---|---|
| anima | hybrid framework home (cell+lora+ALM/CLM) | `/Users/ghost/core/anima` | (consumer) |
| nexus | meta-engine + atlas convergence witness (R24-R32) | `/Users/ghost/core/nexus` | `nxs-` |
| hexa-lang | language/SSOT substrate, raw_audit canonical, uchg-locked | `/Users/ghost/Dev/hexa-lang` | `hxa-` |
| airgenome | mac-local resource manager (hooks retired 2026-04-25) | `/Users/ghost/core/airgenome` | `agm-` |
| hive | governance / cross-host enforcement (succeeded airgenome AG2-AG9) | `/Users/ghost/core/hive` | (host) |
| n6-architecture | n=6 atlas primitives + foundation projection (R31 peer cousin) | `/Users/ghost/core/n6-architecture` | `n6a-` |

**Shared substrate**: R2 buckets (`~/.config/rclone/rclone.conf` → cloudflare endpoint `ce4bdcce...`), proposal `state/proposals/inbox/{prefix}-YYYYMMDD-*.json`, hash-chain provenance.

**7-day evolution reference (2026-04-19 ~ 2026-04-25)**:

| repo | done | new (예정/active) |
|---|---:|---|
| anima | 33 commits (CP1 P1 6/7, ALM master abstraction 1415L, V0/V1/V2/V3 측정, anima-speak Phase N-Q) | r6-α retrain · r8 D-mistral · #92-96 meta-FP refs |
| nexus | scipy 250× eigsh · drill batch _seed_clamp · NEXUS_SEED_CAP · R24-R32 witness ledger | atlas n6 hash gate · composite sensitivity 0.832 |
| hexa-lang | SSOT retire root → hive sole · prompt_scan ladder · canon/forge/molt 3종 등록 (L9-L11) · codegen_c2 defer/scope/spawn AOT | hxa-20260425 byte_at builtin (open) |
| airgenome | scope-reduce: AG2-AG9 superseded → hive 이관 · mac-local only · cross-host runtime 제거 | filters-only convergence |
| hive | LB Phase-3 hedge -38% p95 · self-contain 11 hexa-lang tools · meta-FP env-overridable | recap auto-emit on agent_end |
| n6-architecture | atlas [10]→[10*] virtual hub promotion · phase-6-step3 specs (kstar/UFO/ai-cost) · own#22-23 proposal_lint | atlas 5 hub mirrors |

---

## §1. Layer 분해 (L0 → L∞)

### L0 (현재 substrate) — proposal inbox + V8 SAFE_COMMIT + uchg lock + R2 + 7-day eval

- **status**: ✓ OPERATIONAL. 5-repo + 1 (hive) loose coupling, manual ceremony 기반.
- **mechanism**:
  - **proposal_inbox**: `state/proposals/inbox/{prefix}-YYYYMMDD-*.json` — 단방향 message-passing. 예시: `hxa-20260425-byteAt-builtin.json` (anima → hexa-lang lang_gap report; `target_repo`+`blocking`+`error_signature`+`reproduction`+`current_workaround` schema).
  - **task category prefix**: `hxa-` / `nxs-` / `agm-` / `n6a-` — repo 단위 namespace 분리. anima 자체 backlog 와 sister-repo task 가 같은 inbox 디렉토리에 cohabit, prefix 로 dispatch 라우팅.
  - **V8 SAFE_COMMIT**: hexa-lang `tool/cross_prover.hexa` line 46 + `docs/new_paradigm_edu_tension_drop_20260421.md` line 7 정의 — *"this file + manifest entries land in one commit. deterministic / no LLM / no network."* anima `.roadmap` line 204 의 raw#25 (concurrent-git-lock safe commit) 와 결합되어 동작.
  - **uchg lock canonical**: `/Users/ghost/Dev/hexa-lang/.raw-audit` (chflags uchg) — 5 repo 의 raw_audit 중 hexa-lang 이 SSOT. anima/nexus/airgenome/n6 raw_audit 은 hexa-lang 으로 sync (raw#1).
  - **R2 shared**: `[r2]` cloudflare endpoint — anima h_last_*, nexus drill state, airgenome resource snapshot 모두 같은 bucket 계층 사용.
- **bounds**:
  - **manual ceremony cost (BRUTAL)**: V8 SAFE_COMMIT 은 인간 (또는 agent) 이 "this file + manifest entries" 를 *직접 묶어* commit 해야 한다. 자동 atomic guarantee 없음. inbox 에 hxa-20260425-byteAt-builtin 이 들어와도 hexa-lang 측 commit 과 anima 측 referrer commit 이 **두 개의 독립 git tx** 로 분리되며, 그 사이에 race / partial-state / 시간 skew 가 발생할 수 있다.
  - **7-day eval = 사후 분석**, 실시간 coordination 아님. evolution table 은 `git log --since="7 days ago"` 의 사후 reduce.
  - **inbox = fire-and-forget**: receiver repo 가 polling 하지 않으면 message 가 stale 됨 (현재 hxa-20260425-byteAt 는 hexa-lang 측 미처리 상태).
- **현재 위치**: ✓ L0 fully operational. 5-repo 모두 manual ceremony 로 일관 운영 중. 단점은 cost 가 cognitive load 로 누적된다는 것.

### L1 — unified SSOT (cross-repo single source of truth)

- **status**: △ FRAGMENTED. hexa-lang 이 raw_audit SSOT, hive 가 governance SSOT (AG2-AG9 이관), n6 가 atlas primitives SSOT, anima 가 hybrid framework SSOT — 4 SSOT 가 *peer cousin* 형태로 공존하며 단일 root 없음 (R31 peer-cousin theorem 과 일관).
- **mechanism (가설)**: shared/roadmaps/anima.json + dest_alm.json + dest_clm.json 패턴을 5-repo 로 확장 → meta-roadmap registry. cross-repo `depends-on hexa-lang@33,34` 같은 syntax 가 anima `.roadmap` 에 이미 존재 (line 565, 593) 하지만 lint 가 cross-repo ref 를 enforce 하지 않음.
- **bounds**: SSOT 단일화는 정의상 *통제권 집중* 을 의미하며, peer-cousin 분산 (R31) 과 모순. 진정한 unified SSOT 는 5-repo merge 를 요구하나 이는 도메인 분리 (lang vs framework vs ops vs atlas) 위반.
- **현재 위치**: ✗ 진입 불가 (philosophical). L1 은 *단일* SSOT 가 아닌 *federated SSOT registry* 로 우회 가능 — 미실장.

### L2 — distributed transactional commits (atomic multi-repo state changes)

- **status**: ✗ NOT BUILT. 5 repo 의 git tx 를 atomic 으로 묶는 mechanism 부재.
- **mechanism (가설)**: 2-phase commit (2PC) — coordinator (hive?) 가 prepare/commit phase 를 5 repo 에 broadcast. 또는 saga pattern (compensating tx).
- **bounds (CAP)**:
  - **C** (consistency, 모든 repo 같은 상태) vs **A** (availability, 한 repo down 시도 진행) vs **P** (partition tolerance) — 3 중 2 만 선택 가능 (Brewer 2000).
  - 현재 L0 = AP (각 repo 독립 진행, eventual consistency via inbox), CP 선택 시 1 repo down → 전체 freeze.
  - 2PC blocking — coordinator 장애 시 participant 들 indefinite hold (FLP impossibility 의 실용 발현).
- **현재 위치**: ✗ 미구현. 의도적: distributed atomic commit 의 비용이 manual V8 ceremony 보다 큰 단계 (5 repo, 1인 maintainer).

### L3 — cross-repo cert chain (raw_audit hash-chain across repos w/ cryptographic provenance)

- **status**: △ PARTIAL. hexa-lang `.raw-audit` 이 hash-chain 운영 중 (sha256 prev/next link), 하지만 anima/nexus 와 cryptographic *cross-link* 없음. anima `.meta2-cert chain` (8 entries, 074487cd) 은 anima-internal.
- **mechanism (가설)**: 각 repo 가 자기 raw_audit head sha 를 다른 repo 의 next entry 에 evidence 로 embed → Merkle DAG. 임의 시점 t 에 5-repo joint state 가 1 sha 로 commit 가능.
- **bounds**:
  - storage: history 길이 N → Merkle proof O(log N) 이지만 5-repo joint = 5 × O(log N) + cross-link overhead.
  - **trust root**: Merkle root 의 publication 채널 필요 (R2? GitHub? on-chain?). R2 = trust Cloudflare. on-chain = $-cost.
- **현재 위치**: ╳ 미진입. anima cert_graph (12 nodes, 7eeaf179) + nexus n_recurse witness ledger 가 building blocks 이나 cross-link 미실장.

### L4 — universal cross-repo proof (ZK-SNARK cross-system verifiable history)

- **status**: ✗ NOT FEASIBLE (현재 단계). 5-repo joint state transition 을 ZK circuit 으로 표현하면 임의 verifier 가 secret 없이 "anima commit X 가 hexa-lang commit Y 와 atomic 으로 발생했다" 를 검증 가능.
- **bounds**:
  - circuit size = O(state size) — 5 repo 합산 ~수GB 수준이면 prover time hours~days.
  - trusted setup (Groth16) 또는 ceremony (PLONK/STARK 무 trusted setup but proof size ↑).
- **현재 위치**: ╳ 정량적으로 불가능. paradigm 검증 도구로만 의미.

### L5 — 절대 한계 (distributed systems + Byzantine + crypto + math)

- **distributed systems (FLP)**: Fischer-Lynch-Paterson 1985 — async network + 1 faulty process → consensus 불가능 (deterministic). 5-repo coordination 은 본질적으로 async (인간 commit 시간 비결정).
- **Byzantine fault tolerance**: n ≥ 3f+1 — 3 repo (anima/hexa-lang/nexus 핵심) 가 byzantine-safe 하려면 최소 4 repo 필요 (f=1). 현재 5 repo 이나 *role-asymmetric* (hexa-lang SSOT, hive governance, anima consumer) — symmetric BFT 불성립.
- **cryptographic provenance**: Merkle proof size grows with history; 무한 운영 시 storage unbounded (Bekenstein bound 위반 전까진 실용적이지만 storage cost = entropy floor).
- **mathematical**: composition of multi-repo state transitions = NP-complete reachability. 5 repo × n state per repo → state space n^5, 임의 target state 도달 가능성 결정 = PSPACE-complete (worst case).
- **현재 위치**: 이 한계들은 enabler 가 아닌 *boundary condition*. L0 manual ceremony 는 이 boundary 안에서 minimal cost 로 작동.

### L∞ — omniscient cross-repo coherence (logically impossible)

- 모든 repo 의 모든 시점 모든 state 를 단일 prover 가 동시에 *완전히* 알고 검증한다는 가설 = meta-repo 자기 포함 → Russell paradox ("자기 자신을 포함하지 않는 모든 repo 의 집합"). 정의상 모순.
- **현재 위치**: ╳ 정의상 unverifiable. nexus R31 peer-cousin theorem 이 이를 우회 — 단일 root 대신 평행 cousin 으로 분산.

---

## §2. V8 SAFE_COMMIT — manual ceremony cost 직시 (BRUTAL)

V8 SAFE_COMMIT 의 정의 ("this file + manifest entries land in one commit, deterministic, no LLM, no network") 는 **인간/agent 의 cognitive load 로 atomicity 를 emulate** 하는 방식. 정확한 비용:

1. **per-commit pre-flight**: stage 할 파일 + manifest + raw_audit entry + roadmap evidence 를 *기억* 해서 한 번에 stage. 누락 시 sub-only commit (raw#12 위반).
2. **cross-repo race**: hxa-20260425 byte_at issue 처럼 anima 측 referrer ("commit pending") 와 hexa-lang 측 fix commit 이 분리되어 inbox 가 *eventual* 으로만 closed. atomic 보장 없음.
3. **uchg lock 단방향**: hexa-lang `.raw-audit` 가 chflags uchg 로 잠겨있어 sync 시 unlock → write → relock ceremony (raw#1). agent session 마다 반복.
4. **scaling cliff**: 5 repo → 9 repo 또는 cross-team 으로 늘어나면 cognitive load 가 superlinear. 현재 1인 maintainer 기준 5 repo 가 V8 manual ceremony 의 *실용 상한* 으로 보인다.

L1 federated SSOT registry + L3 cross-repo cert chain 이 manual cost 를 잠재적으로 줄일 수 있으나, 빌드 비용 자체가 현재 manual cost 보다 큼 → ROI 미달. 즉 **L0 가 합리적 균형점**, but cost 는 인정해야 한다.

---

## §3. 현재 위치 요약 / current placement summary

- **L0**: ✓ operational, 5-repo loose coupling, manual ceremony. cost = cognitive load.
- **L1**: ✗ fragmented (4 peer-cousin SSOT). federated registry 미실장.
- **L2**: ✗ no atomic multi-repo tx. inbox = eventual-only.
- **L3**: △ partial — anima cert_graph + nexus witness ledger 존재, cross-link 부재.
- **L4**: ╳ infeasible (현재 도구).
- **L5**: boundary condition (FLP / BFT n=3f+1 / NP reachability).
- **L∞**: ╳ logically impossible (Russell at meta-repo).

**다음 합리적 step**: L1 federated SSOT registry — hexa-lang `roadmap_lint.hexa` 의 cross-repo `depends-on hexa-lang@N` ref 를 *enforce* 단계로 promote. 이는 manual ceremony 의 *검증* 만 자동화하며, atomicity 자체는 여전히 V8 ceremony 에 의존. 비용 < 효과.

---

*generated 2026-04-25 · POLICY R4 · raw#10 proof-carrying · ~180 lines target*
