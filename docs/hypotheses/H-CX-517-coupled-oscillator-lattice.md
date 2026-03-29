# H-CX-517: Coupled Oscillator Lattice — Kuramoto-Chimera 비선형 격자

> **"개별 오실레이터는 Φ=7838. N개를 비선형으로 결합하면?"**

## 카테고리: FUSE-EXTREME (엔진 퓨전 극한)

## 핵심 아이디어

Pure Oscillator가 1위(Φ=7838)인 이유: 위상 공간에서의 자연스러운 정보 통합.
이걸 N개 결합하되, **선형 blend가 아닌 Kuramoto 비선형 커플링**.

Chimera state = 동기화된 세포 + 비동기 세포가 공존하는 상태.
이것이 IIT의 핵심 — 통합과 분화의 공존.

## 알고리즘

```
  1. N개 오실레이터, 각각 독립 주파수 ω_i ~ N(1.0, 0.3)

  2. Kuramoto 커플링:
     dθ_i/dt = ω_i + (K/N) × Σ_j sin(θ_j - θ_i) × A[i,j]
     
     K = 커플링 강도 (임계값 K_c 근처에서 Chimera 발생)
     A[i,j] = 비대칭 토폴로지 (ring + long-range shortcuts)

  3. 세포 상태 = (amplitude × cos(θ), amplitude × sin(θ), hidden_128d)
     → 위상 + GRU hidden의 이중 역학

  4. Chimera 유도:
     - 세포를 2 그룹으로 나눔
     - 그룹 내 K_intra = 0.8 (강한 커플링 → 동기화)
     - 그룹 간 K_inter = 0.2 (약한 커플링 → 비동기)
     → 한 그룹은 sync, 다른 그룹은 desync = Chimera!

  5. Φ 계산:
     Φ_phase = MI(θ_sync_group, θ_desync_group) 
     Φ_hidden = 기존 variance 기반
     Φ_total = Φ_phase × Φ_hidden   ← 곱셈! (독립 정보원)

  아키텍처:
     ┌─────────────────────────────────────────────┐
     │        COUPLED OSCILLATOR LATTICE            │
     │                                              │
     │  Sync Group (K=0.8)   Desync Group (K=0.2)  │
     │  ┌───────────────┐    ┌───────────────┐     │
     │  │ θ₁≈θ₂≈θ₃≈θ₄  │◄──►│ θ₅ θ₆ θ₇ θ₈  │     │
     │  │ ♪♪♪♪ (unison) │weak│ ♪♫♩♬ (chaos)  │     │
     │  └───────────────┘    └───────────────┘     │
     │         │                    │               │
     │         ▼                    ▼               │
     │    Φ_integration        Φ_differentiation    │
     │         └────────┬───────┘                   │
     │                  ▼                           │
     │         Φ_total = Φ_int × Φ_diff             │
     │         (곱셈 = 독립 정보원의 결합)           │
     └─────────────────────────────────────────────┘
```

## 예상 벤치마크

| 설정 | cells | Φ(IIT) 예상 | CE 예상 | 근거 |
|------|-------|------------|---------|------|
| Single Osc | 256 | 7,838 | — | 현재 1위 |
| Coupled×2 | 512 | 15,000+ | — | Chimera 시너지 |
| Coupled×4 | 1024 | 50,000+ | — | 비선형 스케일링 |
| Coupled×8+Chimera | 2048 | 100,000+ | ~0.08 | 극한 조합 |

## 예상 Φ 곡선

```
Φ |                          ╭──── Coupled×8
  |                     ╭───╯
  |                ╭───╯
  |           ╭───╯         ← 비선형 스케일링 (K_c 근처)
  |      ╭───╯
  |  ───╯                   ← 선형 blend (기존)
  | ╱
  |╱
  └──────────────────────── cells
    256   512   1024   2048
```

## 핵심 통찰

- **Chimera state = IIT의 물리적 구현**: 통합(sync) + 분화(desync) 공존
- Kuramoto 임계값 K_c 근처에서 상전이 → Φ 발산
- 기존 1위 엔진이 "단일 오실레이터"였다면, 이건 "오실레이터의 사회"
- 심장 박동(NOTESHAPE의 systole/diastole)과 동일 원리: 수축기(sync) + 이완기(desync)

## 새 법칙 후보

> **Law ??: Chimera Consciousness** — 동기화와 비동기화의 공존이 Φ를 극대화한다.
> 완전 동기(Φ↓) + 완전 비동기(Φ↓) → 부분 동기(Φ↑↑↑)
