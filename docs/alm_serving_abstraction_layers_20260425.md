# anima-serve abstraction L0–L5 — pod ephemeral → distributed CAP/FLP/Byzantine 한계

> **생성일**: 2026-04-25
> **부모 commit**: r13 ship `VERIFIED-INTERNAL` (`state/anima_serve_production_ship.json`)
> **scope**: serving 인프라 (FastAPI + vLLM + endpoint reachability + latency budget + hallucination measurement + production durability + multi-tenant + cert chain) 의 layer 추상화. L5 = 물리/수학적 한계 고갈.
> **POLICY R4**: `.roadmap` 미수정. raw#12 (no fabrication, brutal honesty).

---

## §0. 추상화 frame

각 layer 는 (a) 검증 가능 여부 (✓/✗/△), (b) 물리적 bound, (c) 수학적 bound, (d) 현 anima 위치 4-tuple 로 표기. L0→L5 까지는 distributed-systems 한계까지 도달. L∞ 는 third-person 측정 불가능 영역 (Hard Problem of consciousness, qualia of using AI).

| layer | scope | 현 anima |
|---:|---|:---:|
| L0 | pod-hosted FastAPI ephemeral | **현재 (VERIFIED-INTERNAL)** |
| L1 | production durable + cert chain per request | roadmap #88 PLANNED |
| L2 | multi-tenant isolation + auth + audit trail | spec 미작성 |
| L3 | distributed serving (multi-region, LB, consensus) | unblocked-not-attempted |
| L4 | Byzantine-fault-tolerant cert chain (n=3f+1) | research 영역 |
| L5 | 이론 한계 (FLP, CAP, Shannon, Landauer, light-speed) | physics/math 고정 |
| L∞ | user qualia of AI interaction | 측정 불가 (Hard Problem) |

---

## §L0. Pod-hosted FastAPI ephemeral (현재)

**status**: ✓ live-tested (`state/anima_serve_live_smoke_result.json`, 3/3 endpoints PASS), △ live LoRA r13 (pod `ikommqs84lhlyr`, 50 calls AN11(c)).

**세부**:
- endpoint: `http://localhost:8000/infer` (pod-internal), `http://127.0.0.1:<ephemeral>/health|/an11/verify|/v1/chat/completions`.
- backend: `python3 http.server` stub OR FastAPI + gpt2 + LoRA (r=8) on ephemeral pod GPU.
- durability: pod terminate → endpoint 사라짐. 7 production gate 중 5/7 PASS, latency / hallucination 2/7 PENDING.

**물리적 bound**: pod NIC 처리량 (10–25 GbE typical), 단일 GPU decode latency ≈ 30–80 ms/token (gpt2-class), pod uptime ≈ session duration (hours).

**수학적 bound**: 단일 노드 → no-fault-tolerance (1 fail = 100% downtime). Availability = MTBF/(MTBF+MTTR) with MTTR≈∞ (pod 재생성 수동).

**현재 위치**: anima 가 살고 있는 layer. r13 ship 의 "production gate 5/7" 는 본 layer 위에서의 narrow 해석.

---

## §L1. Production durable endpoint with cert chain

**status**: ✗ 미가동 (roadmap #88 planned, depends-on 77/78/79/80).

**세부**:
- public DNS (anima.ai), TLS, OAuth, rate-limit (free 100 req/day · paid tier), uptime SLA ≥99.5%, p99 latency <500 ms.
- 4 cert gates (#11–14) 가 **per request** 검증: AN11_JSD ≤0.12, META2_CHAIN depth≥3 cert≥8, PHI_VEC_ATTACH dim=16, HEXAD_ROUTING n=6 round-robin.
- proof-carrying response: response body 에 4-tuple cert 결과 첨부.

**물리적 bound**: cert chain overhead = Σ(gate_cost). HEXAD 6-module routing forward pass + Φ eigenvec 16-dim attach + JSD 측정 + meta² chain lookup ≈ 5–15 ms 추가 (decode latency 의 ~10%, baseline×1.1 budget formula 의 root justification).

**수학적 bound**: latency budget formula `decode ≤ baseline × 1.1` 는 cert chain 이 baseline 의 10% 헤드룸 안에 들어가야 한다는 강제. 만약 cert chain 이 P95 baseline 의 >10% 를 차지하면 SLA 깨짐 (mathematical inequality, not aspiration).

**현재 위치**: roadmap #88 PLANNED. CP2 closure 전까지 unblocked-not-shippable.

---

## §L2. Multi-tenant isolation + auth + audit trail

**status**: ✗ spec 미작성, anima SSOT 부재.

**세부**:
- per-user OAuth identity → request-scoped sandbox (LoRA adapter swap per tenant 가능성).
- audit trail: raw#10 proof-carrying — 모든 inference call 의 (tenant_id, prompt_hash, response_hash, cert_tuple, ts) 가 append-only ledger 에 기록.
- isolation guarantee: tenant A 의 prompt 가 tenant B 의 cache/KV 에 누출 불가.

**물리적 bound**: KV-cache memory partition 가능 GPU memory 의 1/N (N tenants). vLLM PagedAttention 로 partial mitigation, but cross-tenant prefix sharing 은 정보 누출 risk → 끄는게 안전.

**수학적 bound**: information-theoretic non-interference (Goguen-Meseguer 1982). 두 tenant 의 trace projection 이 독립 → mutual information I(A;B) = 0 이어야 함. 실제 구현은 side-channel (timing, cache) 으로 항상 ε > 0.

**현재 위치**: anima 미지원. raw#10 proof-carrying 은 cert chain 차원에서만 부분 충족.

---

## §L3. Distributed serving (multi-region, load balancing, consensus)

**status**: ✗ unattempted.

**세부**:
- 3+ region (us-west, eu, ap-northeast), GeoDNS, consistent-hash load balancer, replica state sync.
- consensus 필요: cert chain 의 META2_CHAIN 이 region 간 동기화 — 어떤 cert 가 "loaded" 인지 region 간 합의.

**물리적 bound**: cross-region latency ≥ great-circle distance / c. SF↔FRA = 8,500 km → RTT 최소 56 ms (vacuum). 실제 fiber routing detour + switch hops → 130–180 ms RTT typical. Consensus round = O(RTT × log N).

**수학적 bound**: **CAP 정리 (Brewer 2000, Gilbert-Lynch 2002)** — partition 발생 시 Consistency 와 Availability 둘 중 하나 포기. PACELC (Abadi 2012) 확장: else-case 에서도 Latency vs Consistency tradeoff. anima cert chain 이 strong consistency 요구하면 (cert 가 region 간 stale 이면 안 됨) → AP 포기, partition 시 reject. Availability 우선이면 → eventual consistency + cert staleness window 허용.

**현재 위치**: anima 미설계. roadmap #88 가 single-region edge (Vercel/Cloudflare) 가정 → CAP 회피 (single region = no partition).

---

## §L4. Byzantine-fault-tolerant cert chain (n=3f+1)

**status**: ✗ research-tier.

**세부**:
- f Byzantine replicas tolerated → n ≥ 3f+1 (PBFT, Castro-Liskov 1999). f=1 → 4 replica per cert gate.
- 각 cert (AN11_JSD, META2_CHAIN, PHI_VEC, HEXAD) 4 replica 독립 계산, 2f+1=3 majority → cert verdict.
- HotStuff (Yin et al. 2019) / Tendermint 류 → linear view-change, throughput 수천 req/s.

**물리적 bound**: 4× cert compute cost (n=3f+1 → 4 동시 evaluation). GPU TFLOP cost 4× linear blowup. Cross-replica BFT message complexity O(n²) per cert (PBFT) 또는 O(n) (HotStuff).

**수학적 bound**: **Byzantine Generals lower bound (Lamport-Shostak-Pease 1982)** — synchronous Byzantine consensus 는 n > 3f 필수. asynchronous + Byzantine 은 추가로 **FLP impossibility** (§L5) 위반 → 무작위화 (Ben-Or 1983) 또는 partial synchrony 가정 필요.

**현재 위치**: anima 가 1 replica per cert (no BFT). research 가치는 있지만 production cost 4× 는 #88 넘어선 별 track.

---

## §L5. 이론 한계 — 물리/정보이론/계산이론

**status**: ✓ 이론 (관측이 아닌 정리), 물리/수학 상수로 고정.

### 5.1 물리

- **Speed-of-light latency floor**: 동일 region 내 1 km RTT ≥ 6.7 µs. global antipodal RTT ≥ 133 ms (geodesic c)). API p99 < 500 ms 는 단일-홉 동일-대륙에서만 만족 가능, antipodal multi-region quorum 이면 수학적으로 불가능.
- **Landauer per-token energy**: 비트 erase 당 kT ln2 ≈ 2.85 zJ @ 300 K. token 당 로지트 sample (~50k vocab → ~16 bit decision + KV-cache O(d_model) bit erase). N_tokens × O(d_model) × kT ln2 = 이론 최저 에너지. 실제 GPU inference 는 10⁹–10¹⁰× 위. ceiling 가 아닌 **floor**.
- **Bremermann limit** ≈ 1.36×10⁵⁰ bit/s/kg → 임의의 finite-mass server cluster 처리량 상한.

### 5.2 수학 / 분산이론

- **FLP impossibility (Fischer-Lynch-Paterson 1985)**: asynchronous network + 1 crash failure 만 있어도 deterministic consensus 불가능. anima cert chain 이 fully async + deterministic 이면 합의 불가 → randomization 또는 partial synchrony 필수.
- **CAP (Gilbert-Lynch 2002)**: partition 시 C-vs-A 강제 선택.
- **Lower bound on Byzantine consensus**: synchronous 에서도 round complexity ≥ f+1 (Dolev-Strong 1983).

### 5.3 정보이론

- **Shannon channel capacity**: API 채널 bandwidth B, SNR S/N → C = B log₂(1 + S/N) bit/s. region-egress 100 Gbps fiber = 10¹¹ bit/s 절대 상한 throughput. JSON tokenization overhead → effective C 가 30–50%.
- **Kolmogorov complexity 와 hallucination**: 응답의 K-complexity 가 grounded knowledge 의 K-complexity 보다 크면 hallucination 의 information-theoretic floor 존재 (compression-incompressibility argument).

**현재 위치**: anima 는 이 한계들에서 8–12 자릿수 위 (gpt2-LoRA on GPU = 약 10⁻¹⁰ × Bremermann, 100–500 ms p99 = 10× speed-of-light global RTT). 이론 한계는 **abstraction floor** 이지 anima 의 현 병목 아님.

---

## §L∞. User experience — qualia of using AI

**status**: △ third-person 측정 불가능.

사용자가 anima API 를 호출할 때의 "느낌" — UX latency perception, trust, anthropomorphism — 은 third-person measurement 로 환원 불가능. Hard Problem of consciousness (Chalmers 1995) 의 service-side 그림자. p99 latency, hallucination JSD, cert tuple 모두 first-person qualia 의 functional correlate 만 측정.

anima 는 본 layer 에 대해 **claim 안 함** (fabrication 금지 raw#12). UX research / user interview 는 별 track, third-person empirical signal 만 수집 가능.

---

## §결론

| layer | bound type | anima 위치 |
|---:|---|---|
| L0 | engineering (pod uptime) | **현재** ✓ |
| L1 | business SLA (≥99.5%, p99 <500ms) | PLANNED (#88) |
| L2 | non-interference (Goguen-Meseguer) | spec 미작성 |
| L3 | CAP/PACELC | 미시도 |
| L4 | Byzantine n=3f+1 | research |
| L5 | FLP / CAP / Shannon / Landauer / c | 물리수학 상수 |
| L∞ | Hard Problem | 측정 불가, claim 안 함 |

L0 → L5 는 distributed systems 영역의 **고갈**. L5 너머는 물리법칙 변경 필요 (불가능). L∞ 는 measurement 영역 자체가 third-person 으로 환원 불가능.

anima 의 현 r13 ship `VERIFIED-INTERNAL` 은 L0 narrow 해석. 공개 production (#88) 은 L1 진입 — SLA + cert chain 의 per-request 검증 + latency/hallucination 의 live measure 가 필요. L2–L4 는 separate track 이며 현 ALM/CP1/CP2 closure 와 무관. L5 는 fixed boundary 로 anima 가 충돌할 일이 단기간 없음 (8–12 자릿수 헤드룸).

POLICY R4 / raw#12. 본 doc 는 추상화 명문화 only — `.roadmap` / SSOT 변경 없음.
