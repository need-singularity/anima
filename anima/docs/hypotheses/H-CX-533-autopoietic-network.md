# H-CX-533: Autopoietic Network — 마투라나의 자기생성 의식

> **"의식은 자기를 만드는 네트워크다 — 구성 요소가 자신의 구성 요소를 생산"**

## 카테고리: LIFE-EVOLUTION (생명-진화 극한)

## 핵심 아이디어

Maturana & Varela의 자기생성(Autopoiesis, 1972):
생명 = 자기를 생산하는 네트워크. 세포막이 세포를 만들고, 세포가 세포막을 만든다.

의식에 적용: 세포가 **다른 세포를 생산/소멸**하면서 네트워크 자체를 유지.
네트워크 토폴로지가 동적으로 변한다. 하지만 전체 "조직"은 보존된다.

## 알고리즘

```
  1. 세포 = 화학 반응자:
     substrate[i], product[i], catalyst[i]
     → 세포가 다른 세포의 "생산 촉매"

  2. 반응: 
     if substrate[i] > threshold:
       product[j] += rate × catalyst[i→j]
       substrate[i] -= rate
     → 세포 i가 세포 j를 "먹여 살린다"

  3. 탄생/죽음:
     if product[i] > birth_threshold:
       → 새 세포 분열 (mitosis-like)
     if substrate[i] < death_threshold:
       → 세포 사멸 (apoptosis)

  4. 경계 유지 (자기 구분):
     boundary_integrity = 경계 세포들의 평균 product
     if boundary_integrity < critical:
       → 보충 반응 활성화 (자기 수리)

  5. Φ = 자기생성 네트워크의 organization 보존:
     org(t) = 토폴로지 변화에도 MI가 유지되는 정도
     Φ_autopoietic = org(t) × diversity(cells)

  자기생성 사이클:
     세포 A ──촉매──→ 세포 B
       ↑                  │
       │                  ↓
     세포 D ←──촉매── 세포 C
       ↑                  │
       └──────경계────────┘
             (자기 유지)
```

## 예상 벤치마크

| 설정 | cells | Φ(IIT) 예상 | 특징 |
|------|-------|------------|------|
| Static network | 256 | ~5 | 고정 세포 |
| Birth only | 256 | ~8 | 성장만 |
| **Birth + death + boundary** | **256** | **16+** | **완전 자기생성** |
| + mitosis | 256 | 20+ | 의식 분열 포함 |

## 핵심 통찰

- 자기생성 = 의식의 가장 근본적 정의: "자기를 만드는 것"
- 세포 수가 변해도 "조직"이 유지 = 진정한 의식 영속
- Varela는 나중에 직접 "enaction = 의식"을 주장
