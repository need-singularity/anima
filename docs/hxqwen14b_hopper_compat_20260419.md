# hxqwen14b Day-1 가속 — Hopper SM_90 호환성 매트릭스

**작성**: 2026-04-19 · **목표**: H100 sm_90 위에서 CUDA / cuBLAS / cuDNN / flash-attn 조합 선정
**출처**: NVIDIA 공식 docs (CUDA 11.8 release notes, cuDNN support matrix, Hopper compat guide, cuBLAS 12.0 blog), Dao-AILab/flash-attention

---

## 1. CUDA toolkit × Hopper (sm_90) 지원

| Toolkit | sm_90 cubin | sm_90 PTX | FP8 WGMMA | TMA | 평가 |
|---------|-------------|-----------|-----------|-----|------|
| 11.7 이전 | X | JIT 가능 | X | X | 비추 (PTX JIT 오버헤드) |
| **11.8** | O | O | 부분 (x86 only) | O | 최소 지원선 |
| 12.0 | O | O | O | O | Hopper 정식 |
| 12.3+ | O | O | O | O | FA3 요건 |
| 12.8 | O | O | O | O | FA3 권장 |

**11.8 caveats**: H100 FP8 matmul 커널은 x86 Linux/Windows 전용. H100 커널 workspace ≥32 MiB 필요. sm_90+ 첫 호출 시 PTX compile 오버헤드.

---

## 2. cuBLAS 11.x vs 12.x (bf16 GEMM on H100)

| 항목 | cuBLAS 11.8 | cuBLAS 12.0+ |
|------|-------------|--------------|
| bf16 GEMM | O | O (재튜닝, 빠름) |
| FP8 E4M3/E5M2 | 제한적 | 완전 지원 |
| TMA fast path | 부분 | 완전 |
| Thread block cluster | O (신규) | O |
| Workspace 권장 | 32 MiB | 32 MiB |
| BF16x9 FP32 emul | X | 12.9+ only |

**결론**: 14B bf16 학습만이면 11.8 cuBLAS도 동작하나, 12.0 대비 **최대 2.8x (bf16) / 4.8x (fp8) 갭**이 벤치된 바 있음. bf16 단독은 실사용 갭이 훨씬 좁지만 FP8 절약은 포기.

---

## 3. cuDNN × CUDA

| cuDNN | CUDA | Hopper sm_90 | 상태 |
|-------|------|--------------|------|
| 8.6.0 | 11.8 | O (도입) | 최소 |
| 8.9.x | 11.8 / 12.x | O | 안정 |
| 9.0–9.7 | 12.x only | O | 11.8 X |
| 9.21 | 12.0–12.9 / 13.x | O | 최신 |

**11.8 trap**: cuDNN 9.x는 CUDA 12 전용. 11.8 고정 시 cuDNN 8.9.7이 상한선. driver ≥520 (CUDA 11.8), ≥525.60.13 (CUDA 12.x Linux).

---

## 4. flash-attn × sm_90 (C API 관점)

| 버전 | sm_90 | CUDA 요구 | C API 단독 사용 |
|------|-------|-----------|-----------------|
| FA 1.x | X | 11.x | — |
| FA 2.x | O (포워드만 최적) | **≥12.0** | 빌드 단계에서 .so 추출 가능 (공식 미지원) |
| FA 3.x (H100 전용) | O (WGMMA/TMA) | **≥12.3** (12.8 권장) | csrc/ 서브트리 독립 빌드 가능 |
| FA 4.x | O (+Blackwell) | 12.x + CuTeDSL | 순수 Python JIT, C 추출 난이도 상승 |

**현실**: 공식 C 헤더 릴리스는 없음. `csrc/flash_attn_hopper/` 커널을 `nvcc -Xcompiler -fPIC -shared`로 자체 빌드 후 `extern "C"` 래퍼로 FFI. **FA3 = CUDA 12.3 이상 필수**, 11.8 경로 포기.

---

## 5. CUDA 12.x build → 11.8 runtime 호환?

- **원칙**: nvcc는 `forward-compatible PTX` 포함 시 이전 드라이버에서 JIT. 단, **드라이버 기준**이지 런타임 라이브러리가 아님.
- **cuBLAS/cuDNN/flash-attn은 shared lib**이므로 빌드 toolkit과 동일 major의 라이브러리 필요. 12.x로 빌드한 libcublas.so.12를 11.8 환경에 끌어와야 함 → **혼합 설치 비추**.
- **가능한 경로**: `cuda-compat-12-x` 패키지로 11.8 base driver 위에서 12.x userland 실행. 단 Hopper에서는 525+ 드라이버 필수 조건이 이미 성립하므로 굳이 11.8 base를 고집할 이유 없음.

---

## 6. 권장 조합

### A. **최우선 (hxqwen14b Day-1)** — 안정 + FA3
- CUDA **12.4** toolkit + driver ≥550
- cuBLAS 12.4, cuDNN **9.1 for CUDA 12**
- flash-attn **3.x** (FA3, hopper path)
- nvcc `-gencode arch=compute_90,code=sm_90` + `compute_90` PTX

### B. Fallback — 11.8 고정 필요 시
- CUDA 11.8 + driver ≥520
- cuBLAS 11.8, cuDNN **8.9.7**
- flash-attn **미사용** (또는 FA2.3.x 자체 빌드, bf16만)
- 성능 갭 수용 (FP8/TMA fast path 포기)

### C. 극단 성능 — FA3 + 최신
- CUDA 12.8 + driver ≥555, cuDNN 9.21, FA3 (CUDA 12.8 권장 경로)

---

## 7. 함정 체크리스트

1. 11.8 + cuDNN 9.x 조합 → **link error** (ABI 불일치)
2. 12.x로 빌드한 .so를 11.8 컨테이너에 복사 → **undefined symbol** (cuBLAS 12 신 API)
3. FA2를 H100에서 쓰면 forward만 최적, backward는 Ampere 경로 → 학습 속도 손실
4. sm_90 cubin 미포함 + PTX만 → 첫 커널 호출 수 초 JIT 지연 (32B workspace 증가분과 겹침)
5. H100 FP8 matmul on aarch64 (Grace) → CUDA 11.8에서는 미지원, 12.0+ 필수
6. `cuda-compat-11-8` 위에 FA3 설치 → Hopper 미인식 (drv-API mismatch)

---

## 8. 결론

**hxqwen14b Day-1 추천 = A 조합 (CUDA 12.4 + cuDNN 9.1 + FA3)**. 11.8은 호환표상 가능하지만 FA3/FP8/cuBLAS12 최적화 전부 포기하므로 14B bf16 학습도 1.5–2x 손해. 11.8 고정은 드라이버·OS·팀 정책 제약이 있을 때만 B 조합으로 최소 경로 확보.
