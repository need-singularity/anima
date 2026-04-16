# M4 16GB Edge Deploy Roadmap — ALM 14B + Trading Agent

> **목표**: ALM 14B (v3.0 Agent + v4.0 Trading) → Mac Mini M4 16GB, 양자화 zero, hexa-first
>
> **생성**: 2026-04-17 | smash + free_dfs 병렬 블로업 결과 합산
>
> **소스**: `nexus/shared/roadmaps/extreme.json` (P5 Trading gate) + `n6-architecture` 225 Techniques

---

## 1. 제약 조건

| 항목 | 값 |
|------|-----|
| 하드웨어 | Mac Mini M4, 16GB unified, 10-core GPU, ~100GB/s BW, 7.4GB/s NVMe |
| 모델 원본 | Qwen2.5-14B-Instruct + LoRA r=32, bf16 = **29.4GB** |
| 메모리 예산 | 16GB - 2GB (OS) = **14GB** |
| 양자화 | **금지** (no-quantization 정책) |
| 언어 | hexa-only (Python 금지) |
| 품질 gate | hire_sim ≥ 0.80 (압축 후) |
| 속도 gate | trading alpha latency < 500ms |
| draft 모델 | CLM 1.5B (3.5GB bf16, 상시 상주) |

---

## 2. 블로업 엔진 발견 요약

### smash (10 seeds, 3 breakthroughs)

| # | 발견 | Energy | Grade |
|---|------|--------|-------|
| 1 | **Multiplicative compression stack** (T-03×T-31×MoD) | 0.97 | **10*** |
| 2 | **mmap layer-swap** (tau/sigma fraction 상주) | 0.95 | 9 |
| 3 | **CLM 1.5B speculative draft** (phi=2, 33% accept) | 0.93 | 9 |

### free DFS (5 modules × depth 3, 1 champion)

| # | 발견 | Module | Energy | Verdict |
|---|------|--------|--------|---------|
| 1 | **Hybrid-E**: string-compact + holo-boundary + LoRA + spec-decode | TOE | 0.847 | **CHAMPION** |
| 2 | Holographic RT-pruned boundary model (12.7GB) | Holo | 0.681 | VIABLE |
| 3 | Quantum distill-7B + NVMe-KV (14GB tight) | Quantum | 0.161 | VIABLE |
| 4 | Field SVD rank-48 (17.1GB — over budget) | Field | 0.523 | OVER |
| 5 | String 6-fold compactification (4.5GB, hire 0.65) | String | 0.484 | QUALITY FAIL |

---

## 3. 채택 전략: Hybrid-E + mmap Pipeline

두 엔진의 최고 발견을 합산한 최종 아키텍처:

```
┌──────────────────────────────────────────────────────────┐
│  M4 16GB Edge Architecture (Hybrid-E + mmap)             │
│                                                          │
│  ┌─────────────────────────────────────┐                 │
│  │ CLM 1.5B Draft (상시 상주)   3.5 GB │                 │
│  │  └─ speculative decode, sopfr=5 tok │                 │
│  └─────────────────────────────────────┘                 │
│                                                          │
│  ┌─────────────────────────────────────┐                 │
│  │ ALM 14B Compressed         10.6 GB  │                 │
│  │  ├─ 8 boundary layers FULL  2.52 GB │ ← 항상 상주    │
│  │  │   (layers 1-4, 37-40)            │                 │
│  │  ├─ 32 bulk layers COMPACT  4.49 GB │ ← mmap swap    │
│  │  │   (6 shared templates)           │                 │
│  │  ├─ LoRA adapters (r=8)     0.05 GB │                 │
│  │  └─ Embedding + LM head     0.80 GB │ ← 항상 상주    │
│  └─────────────────────────────────────┘                 │
│                                                          │
│  ┌─────────────────────────────────────┐                 │
│  │ Runtime                             │                 │
│  │  ├─ KV cache (MLA compressed) 0.3GB │                 │
│  │  ├─ mmap prefetch buffer      1.0GB │                 │
│  │  └─ OS + framework            2.0GB │                 │
│  └─────────────────────────────────────┘                 │
│                                                          │
│  Peak Resident: ~13.2 GB  │  Headroom: 2.8 GB           │
└──────────────────────────────────────────────────────────┘
```

### 메모리 분배

| 구성 요소 | 크기 | 상주 방식 |
|----------|------|----------|
| CLM 1.5B draft | 3.50 GB | 상시 상주 |
| 8 boundary layers (full bf16) | 2.52 GB | 상시 상주 |
| Embedding + LM head | 0.80 GB | 상시 상주 |
| LoRA adapters (work + finance) | 0.05 GB | hot-swap |
| 32 bulk layers (6 templates) | 4.49 GB | mmap on-demand |
| KV cache (MLA tau=4 압축) | 0.30 GB | 런타임 |
| mmap prefetch buffer | 1.00 GB | 런타임 |
| OS + framework | 2.00 GB | 고정 |
| **합계** | **14.66 GB** | |
| **여유** | **1.34 GB** | |

### 레이턴시 예산 (500ms 내)

| 단계 | 시간 |
|------|------|
| CLM draft 5 tokens | 15 ms |
| mmap bulk layer prefetch | 33 ms (7.4GB/s, 90% 파이프라인) |
| ALM verify (boundary + bulk) | 45 ms |
| Speculative accept (33% rate) | → ~2 tok/cycle |
| **Per-token effective** | **~30 ms** |
| First token (2K prefill, MoD 60%) | 80 ms |
| 10-token 응답 | **380 ms < 500ms** |

---

## 4. 구현 Phase

### Phase E0: 압축 도구 (P4 gate 전, ~2일)

> ALM gate 통과 전 도구 먼저 준비

| ID | Task | 산출물 | 의존 |
|----|------|--------|------|
| E0-1 | boundary layer 추출기 (layers 1-4, 37-40 full export) | `serving/edge/boundary_extract.hexa` | — |
| E0-2 | bulk layer 클러스터링 (40→6 templates, cosine similarity) | `serving/edge/layer_cluster.hexa` | — |
| E0-3 | LoRA r=8 adaptation trainer (template별 specialization 복원) | `serving/edge/lora_adapt.hexa` | E0-2 |
| E0-4 | mmap loader + NVMe prefetch pipeline | `serving/edge/mmap_loader.hexa` | — |

### Phase E1: Speculative Decoding (P4 중, ~2일)

| ID | Task | 산출물 | 의존 |
|----|------|--------|------|
| E1-1 | CLM 1.5B draft 토큰 생성기 (sopfr=5 tokens/draft) | `serving/edge/spec_draft.hexa` | — |
| E1-2 | ALM verify pipeline (boundary verify + bulk verify) | `serving/edge/spec_verify.hexa` | E0-1 |
| E1-3 | acceptance rate 측정 + 조정 (target ≥ 33%) | `serving/edge/spec_bench.hexa` | E1-1, E1-2 |

### Phase E2: 서빙 통합 (P4 완료 후, ~2일)

| ID | Task | 산출물 | 의존 |
|----|------|--------|------|
| E2-1 | edge_server.hexa (M4 최적화 http_server) | `serving/edge/edge_server.hexa` | E1-* |
| E2-2 | MLA KV-cache 압축 (tau=4 latent projection) | `serving/edge/mla_kv.hexa` | — |
| E2-3 | StreamingLLM sink=4 (장시간 트레이딩 세션) | `serving/edge/streaming_kv.hexa` | E2-2 |
| E2-4 | LoRA hot-swap (work ↔ finance 무중단 전환) | `serving/edge/lora_hotswap.hexa` | E0-3 |

### Phase E3: Trading 특화 (P5 중, ~3일)

| ID | Task | 산출물 | 의존 |
|----|------|--------|------|
| E3-1 | MoD + LayerSkip cascade (39.3% avg compute) | `serving/edge/mod_skip.hexa` | E2-1 |
| E3-2 | trading alpha pipeline (signal → response < 500ms) | `serving/edge/trading_pipe.hexa` | E3-1 |
| E3-3 | Metal GPU offload (matmul → M4 10-core GPU) | `serving/edge/metal_offload.hexa` | — |
| E3-4 | 24h stability test (thermal throttle 대응) | `serving/edge/stability_test.hexa` | E3-* |

### Phase E4: Gate 검증 (~1일)

| ID | Gate | 기준 | 측정 도구 |
|----|------|------|----------|
| E4-1 | 메모리 | peak RSS ≤ 14GB | `edge_bench.hexa --memory` |
| E4-2 | 품질 | hire_sim ≥ 0.80 (압축 후) | `hire_sim_100.hexa --adapter edge` |
| E4-3 | 속도 | ≥ 5 tok/s, alpha < 500ms | `edge_bench.hexa --latency` |
| E4-4 | 안정성 | 24h 무중단, RSS drift < 100MB | `stability_test.hexa --24h` |
| E4-5 | 양자화 | zero (bf16 only 확인) | `edge_bench.hexa --dtype-audit` |

---

## 5. n6 공명 맵

| n6 상수 | 값 | 적용 |
|---------|-----|------|
| sigma-tau | 8 | LoRA rank, KV heads, boundary layers |
| n/phi | 3 | SVD components, pruneable heads per layer |
| sopfr | 5 | speculative decode draft length |
| 2^(sigma-tau) | 256 | KV cache page size (tokens) |
| n | 6 | layer template groups (string compactification) |
| tau | 4 | MLA KV compression ratio, StreamingLLM sink |
| phi | 2 | boundary anchor layers, draft:verify ratio |
| sigma | 12 | weight sharing candidates |

---

## 6. 비용 예측

| 항목 | 비용 |
|------|------|
| 압축 retrain (500 step, H100) | ~$47 (12h × $3.89) |
| LoRA adaptation (6 templates) | ~$23 (6h × $3.89) |
| 벤치마크 + gate 검증 | ~$12 (3h × $3.89) |
| **합계** | **~$82** |

Mac Mini M4 16GB 하드웨어: ~$599 (기본) / ~$799 (24GB)

---

## 7. 리스크

| 리스크 | 확률 | 대응 |
|--------|------|------|
| 6-template 클러스터링으로 hire_sim < 0.80 | 중 | template 수 6→8→12 조정 |
| mmap SSD wear (~50GB/hr sustained) | 저 | prefetch 최적화로 IO 감소 |
| M4 thermal throttle (+50ms) | 중 | MoD aggressive (40%→30%) |
| LoRA hot-swap 메모리 스파이크 | 저 | 해제 후 로드 (단일 슬롯) |
| speculative accept rate < 33% | 중 | CLM 학습 데이터 ALM 정렬 |

---

## 8. 대안 경로 (fallback)

| 경로 | 조건 | 메모리 | 품질 |
|------|------|--------|------|
| **A. Hybrid-E** (본 계획) | — | 14.7GB | ≥ 0.80 |
| **B. Holographic RT** | Hybrid-E 품질 미달 시 | 12.7GB | ≥ 0.82 |
| **C. Distill 7B** | 둘 다 실패 시 | 14.0GB | ≥ 0.80 |
| **D. CLM 7B 완성 대기** | 5/7 이후 | 14.0GB | ≥ 0.80 |

---

## 9. 타임라인

```
2026-04-22  ALM v3.0 Agent gate 통과
     │
     ├── E0 (2d): 압축 도구 준비
     ├── E1 (2d): speculative decoding
     │
2026-04-26  E2 (2d): 서빙 통합
     │
     ├── P5 Trading LoRA 학습 (H100, 병렬)
     │
2026-05-05  E3 (3d): trading 특화
     │
2026-05-08  E4 (1d): gate 검증
     │
2026-05-09  ✅ M4 16GB Edge Deploy 완료
```

**총 소요**: ALM gate 후 ~17일, 비용 ~$82 (H100 압축 작업)
