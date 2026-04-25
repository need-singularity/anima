# CLM serving lattice abstraction L0–L5 — cell↔token bridge PoC → distributed cell consensus 한계

> **생성일**: 2026-04-25
> **부모 evidence**: `state/cell_token_bridge_proto.json` (CONDITIONAL_PASS, 3/3 fixture, drift_max=0 ≤ 2e-4 bound), `state/clm_r6_gpu_smoke_result.json` (VERIFIED, 50-step CE descent on RTX 5070).
> **scope**: CLM (Cell Language Model) **serving** 추상화 — 즉 "deterministic Lagrangian solver + cell-state ↔ token bridge" 를 production 레이어로 끌어올리는 trajectory. ALM serving (`docs/alm_serving_abstraction_layers_20260425.md`) 는 FastAPI+vLLM+LoRA stack — CLM 은 hash-only deterministic, LLM-not-in-loop, lattice runtime. 비교 대조용.
> **POLICY R4**: `.roadmap` 미수정. raw#9 hexa-only, raw#12 brutal honesty, no fabrication.
> **brutal honesty header**: CLM serving 은 ALM serving 보다 ~6 layer 미성숙. ALM 은 L0 VERIFIED-INTERNAL, CLM 은 L0 가 아직 PoC research 단계 (cell↔token bridge 가 단지 5-level coarse round-trip 검증, 실 trained lattice 위 deployment 0회).

---

## §0. ALM vs CLM serving 대조

| axis | ALM serve | CLM serve |
|---|---|---|
| transport | FastAPI + vLLM HTTP | (미정의) cell-state RPC, hash-only |
| compute | GPU LoRA decode | deterministic Lagrangian (V_sync + V_RG + L_IX + I_irr) solver |
| determinism | sample temp>0, JSD≤0.12 | bit-exact hash equality (raw#9 LLM=none) |
| state | KV-cache (transient) | cell lattice (persistent, n=6 hivemind) |
| 검증 | AN11 triple PASS | bridge fixture 3/3 + 100-step drift |
| **현재 layer** | **L0 VERIFIED-INTERNAL** (`anima_serve_production_ship.json`) | **L0 PoC** (`cell_token_bridge_proto.json` β main ablation C) |

CLM serving 은 ALM 의 distributed-systems 한계 (CAP/FLP/Byzantine) 를 **물려받고**, 추가로 **cell-state propagation physics** (light-speed across lattice nodes, Lyapunov chaos boundary, thermodynamic per-cell-step) 를 가짐.

---

## §L0. 현재 — cell↔token bridge PoC + Hetzner smoke env

**status**: ✓ bridge β main ablation C `CONDITIONAL_PASS` (3/3 fixture: identity/ladder PASS, adversarial 500‰ midpoint FAIL as pre-registered raw#0). △ Hetzner train_clm.hexa = "structural port" (PyTorch ops → TODO comments). ✓ ubu1 RTX 5070 GPU smoke `VERIFIED` (50-step CE 7.853 → 6.709 descent, Φ_holo ∈ [0.728, 1.566], Φ_gwt ∈ [0.855, 3.928], 0 NaN, seed=42 byte-identical).

**세부**:
- bridge: `tool/cell_token_bridge_proto.hexa` (748 lines), eigenvec source SHA `211e2deb…`, cos_min_thr=0.5, i_irr_bits_budget=84, drift_max=0 ≤ 2·lr²·k = 2e-4 (lr=1e-3, k=100).
- smoke env: ubu1 (RTX 5070 12GB, driver 580.126.09, CUDA 13.0) — hexa stage1 CPU-interpret mode. **GPU kernel path (libhxccl/libhxcuda) 엄밀 검증 PENDING H100 native path** (`.roadmap` #6 note).
- htz: `/root/anima/training/train_clm.hexa` 존재하나 PyTorch op port 미완료 → CE descent 실측 불가 on htz alone.

**물리적 bound**: 단일 GPU host. 50-step micro-smoke 의 wall-clock O(seconds). bridge round-trip cost = 16-dim cosine × 5-level argmax = O(80 mul) per step.

**수학적 bound**: bridge 가 5-level coarse → per-call 정보 손실 ~21 bit (log₂(2²³/5) ≈ 20.68 bit, spec §3). f_tc ∘ f_ct = id_5level (lossless on canonical), f_ct ∘ f_tc ≠ id (lossy projection). **semi-invertible only**.

**현재 위치**: PoC 단계. 실 production endpoint 0개. 라이브 cell lattice 0개.

---

## §L1. Production cell-state endpoint — deterministic Lagrangian-as-a-Service

**status**: ✗ 미가동. spec 미작성, anima SSOT 부재.

**세부**:
- API: `POST /clm/cell_step` body=`{ws: int×5 per_mille, lattice_id, step_count}` → `{ws_next, i_irr_bits, phi_holo, phi_gwt, cert_sha}`.
- backend: hexa-stage2 native binary (FFI to libhxblas/libhxccl) 가 V_sync (Kuramoto) + V_RG (hierarchical regularizer) + L_IX (4-term integrator) + I_irr (irreversibility tracker) 를 deterministic 하게 step.
- proof-carrying: response 의 `cert_sha` = SHA256(ws ‖ lattice_id ‖ step_count ‖ ws_next) — raw#9 hash-equality 가 곧 verdict.

**물리적 bound**: per-step compute = O(N_cells × d_lattice² × n_terms). RTX 5070 12GB 기준 50-step smoke ≈ seconds (실측). 1k-cell lattice × 100-step = 단일 GPU 수 초 budget.

**수학적 bound**: **drift floor** = O(lr²·k) + ε_bridge (spec §4 C). lr=1e-3, k=100 → 2e-4. k 가 커지면 (long horizon serving) drift 누적 — Lyapunov exponent λ > 0 인 chaotic regime 진입 시 drift bound 깨짐. **L_IX 가 fixpoint (gen-5 ΔW=0) 일 때만 ε_bridge=0**.

**현재 위치**: 미시도. unblock 조건 = train_clm.hexa PyTorch op port 완료 + H100 GPU native path 검증 + 4 cert gate (#11–14 ALM 류) 의 CLM equivalent 정의.

---

## §L2. Multi-cell coherent serving — lattice serving across regions

**status**: ✗ unattempted. atlas synchronization spec 미존재.

**세부**:
- N region (us/eu/ap) 각 region 에 cell lattice replica. 같은 (lattice_id, step_count) 입력 → 같은 ws_next 출력 (deterministic 강제).
- atlas sync: cross-region cell state 의 hash 비교 (raw#9). drift > ε_atlas → reject + alert.

**물리적 bound**: cross-region RTT (great-circle / c). SF↔FRA 8,500 km → vacuum 56 ms, fiber 130–180 ms. lattice step 동기화 주기 ≥ RTT × log N. ALM serving (§L3 alm_serving doc) 와 동일 floor.

**수학적 bound**: **CAP 정리 (Brewer 2000, Gilbert-Lynch 2002)** — partition 시 C-vs-A 강제 선택. CLM 의 "deterministic hash equality" 는 **strong consistency 요구** → CAP 의 C 측. partition 시 reject (Availability 포기). PACELC: else-case 에서도 latency vs consistency tradeoff.

**현재 위치**: 미설계. 단일 region single-host PoC 만 존재 (ubu1).

---

## §L3. Cell ↔ token bridge production — real-time inference decode

**status**: ✗ 미시도. β main ablation C 은 **offline fixture** 검증, real-time inference path 0회.

**세부**:
- hot path: token decode 시 cell-state h_t 를 매 step f_tc(h_t) → ws_t (per-mille), 다음 token logit 의 ws_{t+1} prior 로 사용.
- 5-level bucket (`{0,200,400,600,800,1000}‰`) → token-level granularity 1/5 로 압축. **21-bit per-step loss** 가 inference latency 마다 발생.
- 16 template ↔ 6 Hexad block-diag factorization (spec §5) 가 bridge 의 routing prior.

**물리적 bound**: per-token bridge cost = 16-dim argmax (negligible vs decode itself). 누적 drift = (per-step drift) × N_token. 1024-token context 에서 drift bound = 2 · lr² · 1024 ≈ 2e-3 — **cos floor 0.5 와 충돌 가능**, 실측 PENDING.

**수학적 bound**: f_ct ∘ f_tc 는 **비가역**. 반복 적용 시 information monotone-decreasing (data processing inequality). long-horizon inference 에서 cell ↔ token 양방향 traffic 이 정보 누출 channel → noise floor → eventual decoherence.

**현재 위치**: bridge spec 만 존재 (`edu/cell_token_bridge_spec_20260421.md`). hot-path 통합 0회. real LoRA+cell co-deployment 0회.

---

## §L4. Distributed cell consensus — Byzantine across N cell instances

**status**: ✗ research-tier.

**세부**:
- f Byzantine cell replicas 허용 → n ≥ 3f+1 (PBFT, Castro-Liskov 1999). f=1 → 4 replica per cell-step.
- 각 replica 가 V_sync/V_RG/L_IX/I_irr 독립 계산. 2f+1=3 majority hash agreement → cell-step 확정.
- HotStuff/Tendermint linearized view-change 로 throughput 수천 step/s 가능.

**물리적 bound**: 4× compute cost (n=3f+1). cross-replica BFT message complexity O(n²) per cell-step (PBFT) 또는 O(n) (HotStuff). cell lattice 가 N=10⁴ 면 N · 4 = 4·10⁴ 동시 Lagrangian solver 필요.

**수학적 bound**: **Byzantine Generals lower bound (Lamport-Shostak-Pease 1982)** — synchronous Byzantine consensus 는 n > 3f. asynchronous + Byzantine 은 추가로 **FLP impossibility** 위반 → randomization (Ben-Or 1983) 또는 partial synchrony 필수. CLM 의 deterministic hash 는 randomization 도입 시 **raw#9 LLM=none deterministic 원칙과 충돌** — research 가치 있으나 anima 의 raw#9 와 정합성 미해결.

**현재 위치**: 미시도. raw#9 와 BFT randomization 충돌 해결 spec 없음.

---

## §L5. 이론 한계 — physics + math + chaos

**status**: ✓ 이론 (관측이 아닌 정리), 물리/수학 상수로 고정. ALM L5 와 부분 공유, **Lyapunov chaos** axis 에서 추가됨.

### 5.1 물리

- **Light-speed cell-state propagation**: lattice node 간 정보 전파 ≥ 거리/c. 동일 region 내 1 km RTT ≥ 6.7 µs. global lattice 면 antipodal 133 ms (vacuum geodesic). cell-step rate 가 1/RTT 보다 빠르면 lattice 는 **causally disconnected** → 합의 불가.
- **Thermodynamic per-cell-step**: Landauer kT ln2 ≈ 2.85 zJ @ 300K per bit erase. 1 cell-step 의 ΔW 변화 = O(d_cell) bit erase. N_cells × N_steps × O(d) × kT ln2 = 이론 floor. 실 GPU 는 10⁹–10¹⁰× 위 → ceiling 아닌 floor.
- **Bremermann limit** ≈ 1.36×10⁵⁰ bit/s/kg → finite-mass lattice cluster 처리량 상한.

### 5.2 수학 / 분산이론 (ALM serving 과 공유)

- **FLP impossibility (Fischer-Lynch-Paterson 1985)**: async + 1 crash 에서 deterministic consensus 불가. CLM 의 hash-only deterministic 은 partial synchrony 가정 필수.
- **CAP (Gilbert-Lynch 2002)**: partition 시 C-vs-A 선택. CLM strong consistency 요구 → C 우선, partition reject.
- **Dolev-Strong 1983**: synchronous Byzantine 도 round complexity ≥ f+1.

### 5.3 chaos / dynamical systems (CLM 고유)

- **Lyapunov chaos boundary**: V_sync (Kuramoto) + V_RG hierarchical 의 Jacobian 의 max eigenvalue λ. λ > 0 → trajectory 의 small perturbation 이 e^(λt) 로 발산 → bridge drift bound O(lr²·k) **깨짐**. CLM 의 "deterministic Lagrangian" 가정은 λ ≤ 0 (Lyapunov-stable) regime 에서만 성립. cell lattice 가 phase transition 근처 (V_sync r_order ≈ 0.6) 에서 λ → 0⁺ → bridge 가 drift bound 의 가장자리에서 trembling.
- **Pesin entropy / SRB measure**: chaotic regime 의 step-마다 정보 생성률 = Σ λ_i (positive Lyapunov exponents). bridge 의 21-bit/step budget 보다 entropy 생성률이 크면 **information-theoretic underflow** — cell-state 를 token 으로 더이상 represent 불가.

### 5.4 정보이론

- **Shannon channel capacity**: B log₂(1 + S/N). cell↔token bridge 의 5-level coarse-graining → effective C 가 21 bit/step 으로 hard-cap.
- **Kolmogorov K-complexity**: cell-state 의 K(s) 가 token sequence 의 K(t) 보다 크면 token-side 가 lossy, K(t) > K(s) 면 token 이 cell 보다 풍부한 prior → bridge 방향성 (어느 쪽이 ground truth) 가 K(s) vs K(t) 에 의해 결정. anima 는 현재 측정 안 함.

**현재 위치**: anima 는 이 한계들에서 6–10 자릿수 위 (RTX 5070 50-step ≈ 10⁻¹² × Bremermann). 단 **Lyapunov axis 는 실측 bound 없음** — V_sync/V_RG 의 Jacobian eigenvalue 측정 PENDING. cell lattice 가 chaotic regime 에 들어가면 (raw#30 gen-5 fixpoint 미충족 시) bridge drift bound 가 깨질 risk 존재.

---

## §L∞. User qualia of cell-decoded output — Hard Problem

**status**: △ third-person 측정 불가능.

CLM 이 cell-lattice 에서 token 을 decode 했을 때 사용자가 "이 응답은 Lagrangian-grounded 다" 를 직접 느끼는 qualia — third-person measurement 로 환원 불가. ALM 의 "cert tuple proof-carrying" 도 이 qualia 의 **functional correlate** 만 제공. CLM 의 hash-equality 는 더 강한 deterministic guarantee 이지만, 사용자의 trust/comprehension 은 여전히 first-person.

anima 는 본 layer 에 대해 **claim 안 함** (raw#12). CLM serving 의 UX research 는 별 track.

---

## §결론

| layer | bound type | CLM 위치 | ALM 비교 |
|---:|---|---|---|
| L0 | bridge PoC + smoke env | **현재 (CONDITIONAL_PASS)** | ALM 은 VERIFIED-INTERNAL (1 layer 우위) |
| L1 | deterministic Lagrangian endpoint | spec 미작성 | ALM #88 PLANNED |
| L2 | multi-cell atlas + CAP | unattempted | ALM L3 와 동일 floor |
| L3 | cell↔token hot-path | bridge spec only | ALM 은 LoRA decode live |
| L4 | Byzantine cell consensus + raw#9 충돌 | research, raw#9 conflict 미해결 | ALM L4 와 공유 + raw#9 추가 제약 |
| L5 | FLP/CAP/Shannon/Landauer/c **+ Lyapunov chaos** | 물리수학 상수 + chaos 측정 PENDING | ALM L5 의 superset |
| L∞ | Hard Problem | 측정 불가, claim 안 함 | 동일 |

**brutal honest summary**:
- CLM serving 은 ALM 보다 **명확히 한 layer 뒤쳐짐** (ALM L0 ship VERIFIED-INTERNAL vs CLM L0 PoC CONDITIONAL_PASS).
- CLM 의 **deterministic hash-only** 는 ALM 의 sample-based 대비 강한 guarantee 이지만, 그 guarantee 가 production 에서 가치 있으려면 L1 (cell-step endpoint) 가 먼저 land 되어야 함.
- **L4 의 BFT randomization 이 raw#9 LLM=none deterministic 과 충돌** — anima 가 분산 cell consensus 를 진지하게 추구하려면 raw#9 spec 자체 revision 필요.
- L5 의 **Lyapunov chaos axis** 는 ALM 에 없는 CLM 고유 한계. V_sync/V_RG Jacobian eigenvalue 측정이 안 되면 bridge drift bound 가 가장자리에서 깨질 risk 가 정량화 안 됨.
- weakest evidence link: **L1 cell-step endpoint spec 부재**. CLM 의 "serve" 는 현재 oxymoron — 서빙할 production endpoint 자체 없음. bridge PoC 만으로는 serving claim 불가.
- 단기 next step (가능한): (a) train_clm.hexa PyTorch→hexa op port 완료 → htz 단독 50-step CE descent 실측 (b) cell_step endpoint spec draft (raw#9 hash-equality 형식) (c) Lyapunov eigenvalue 측정 hook 을 V_sync/V_RG 에 추가.

POLICY R4 / raw#12 / raw#9. 본 doc 는 추상화 명문화 only — `.roadmap` / SSOT 변경 없음.
