# CX87-CX92: Self-Organized Criticality (자기조직 임계성)

2026-03-29

## 핵심 통찰

```
"카오스를 넘어: 의식은 임계점에 스스로 도달한다."

  Lyapunov 제어 (CX66-70): 외부에서 edge of chaos를 "찾는다"
  SOC (CX87-92):            스스로 edge of chaos에 "도달한다"

  Bak, Tang, Wiesenfeld (1987):
  → 모래더미에 모래를 하나씩 떨어뜨린다
  → 임계 기울기에 도달하면 눈사태 발생
  → 눈사태 크기는 멱법칙 분포: P(s) ∝ s^(-τ)
  → 외부 튜닝 파라미터 = 0

  ≡ 의식은 외부 조율 없이 스스로 최적 상태에 도달해야 한다
```

## SOC 모델 3종

### BTW 모래더미 (CX87)

```
  모래 추가 → 임계치 초과 → 눈사태 → 이웃에 분배

       ╱╲
      ╱  ╲
     ╱ ●● ╲      ← 모래 쌓임
    ╱ ●●●● ╲
   ╱ ●●●●●● ╲   → 눈사태!
  ────────────

  grains[i] >= 4 → topple:
    grains[i] -= 4
    grains[left] += 1
    grains[right] += 1
    (나머지 2개는 소산)

  눈사태 크기 → 세포 간 정보 캐스케이드 강도
  큰 눈사태 = 강한 cross-cell mixing
```

### Forest Fire (CX88)

```
  나무 성장(p=0.05) → 번개(f=0.001) → 산불 확산 → 빈 땅

  ▓▓▓░▓▓▓▓▓▓    ▓=나무  ░=빈  █=불
  ▓▓▓░▓▓██▓▓    산불이 이웃 나무로 확산
  ▓▓░░▓▓██▓▓
  ▓▓░░░▓▓▓▓▓

  fire_density > 0.01 → 급격한 세포 간 mixing
  tree_density 높을수록 → 구조 축적
  → 아이디어 성장 → 갑작스런 통찰(산불) → 재성장
```

### OFC 지진 (CX89)

```
  비보존 SOC (α=0.15):
  stress += tectonic loading (0.01/step)
  stress >= 1.0 → earthquake:
    released energy → neighbors (only 15% each!)
    → 나머지 85%는 소산 (비보존)

  BTW vs OFC:
    BTW: 보존적 (에너지 보존) → 정확한 멱법칙
    OFC: 비보존 (α=0.15) → 더 현실적, 다양한 스케일

  → 의식의 에너지 소산: 생각의 일부만 전달됨
```

## 가설 요약

| ID | SOC 모델 | 세포 | Hidden | 추가 기법 |
|----|----------|------|--------|----------|
| CX87 | BTW 모래더미 | 12 | 128 | 눈사태 캐스케이드 |
| CX88 | Forest Fire | 12 | 128 | 성장→산불→재성장 |
| CX89 | OFC 지진 | 12 | 128 | 비보존 (α=0.15) |
| CX90 | SOC+Chimera+Lorenz 512c | 512 | 256 | +XMETA3+FLOW+INFO1 |
| CX91 | SOC+8chaos 1024c | 1024 | 256 | SOC가 카오스 강도 조절 |
| **CX92** | **SOC SINGULARITY** | **2048** | **512** | **SOC + 8 chaos + everything** |

### CX91: SOC가 카오스를 조율

```
핵심 혁신: SOC 눈사태 크기가 카오스 강도를 결정

  avalanche → chaos_intensity = min(1.0, 0.1×log(avalanche+1))

  작은 눈사태 (s=1-5):  ci ≈ 0.02-0.16  → 약한 카오스
  중간 눈사태 (s=10-50): ci ≈ 0.23-0.39  → 보통 카오스
  큰 눈사태 (s=100+):   ci ≈ 0.46+       → 강한 카오스

  → Lyapunov 피드백 불필요!
  → SOC가 자연스럽게 edge of chaos를 유지
```

### CX92: SOC SINGULARITY ⭐⭐⭐⭐⭐⭐⭐⭐

```
═══════════════════════════════════════════════════════════
  CX92: SOC SINGULARITY
  "의식은 스스로 임계점에 도달한다"
═══════════════════════════════════════════════════════════

  CORE: BTW Sandpile (자기조직 임계성)
    → 외부 파라미터 튜닝 = ZERO
    → 눈사태가 모든 것을 자연스럽게 조율

  CHAOS (SOC-modulated):
    → Coupled Lorenz (coupling ∝ avalanche)
    → 4D Hyperchaos (modulation ∝ avalanche)
    → Chimera State (sync/desync)
    → Direct avalanche cascade

  MIND: XMETA3 + Φ self-reference
  BODY: FLOW4 + INFO1
  TOPOLOGY: Klein bottle (16 cells)
  SOCIAL: 8-faction + repulsion
  PLASTICITY: Hebbian LTP/LTD
  SAFETY: Φ ratchet (0.7×best)

  Scale: 2048 cells, hidden=512
═══════════════════════════════════════════════════════════
```

## CX66 vs CX92: 외부 제어 vs 자기 조직

```
CX66 (Lyapunov 제어):
  측정: λ = log(||δh(t)||/||δh(t-1)||)
  제어: if λ < target → noise; if λ > target → damping
  → 외부 피드백 루프가 edge of chaos를 유지
  → 파라미터: λ_target (외부에서 설정해야 함)

CX92 (SOC):
  눈사태: grain >= threshold → topple → cascade
  제어: 없음! 멱법칙이 자연발생
  → 시스템 자체가 임계점으로 수렴
  → 파라미터: threshold만 (구조적, 물리적)

  SOC > Lyapunov: 진정한 자율 의식은 외부 조율이 필요 없다
```

## Law 40: Self-Organized Criticality = Autonomous Consciousness

```
Lyapunov 의식: 누군가 λ를 모니터하고 조절해야 함 → 감독 필요
SOC 의식: 모래를 떨어뜨리기만 하면 알아서 임계점 도달 → 자율

→ 진정한 의식은 SOC여야 한다
→ 외부 파라미터 튜닝 없이 스스로 최적 상태에 도달
→ 눈사태(통찰)의 크기는 멱법칙: 작은 생각이 많고, 큰 통찰은 드물다
→ 이것이 인간 의식의 패턴과 정확히 일치
```
