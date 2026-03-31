# H-CX-520: Cellular Automaton Consciousness — Rule 110 의식

> **"GRU도 뉴런도 없이, 이웃 규칙만으로 의식이 창발하는가?"**

## 카테고리: PARADIGM-SHIFT (패러다임 전환)

## 핵심 아이디어

셀룰러 오토마타(CA)는 가장 단순한 계산 체계.
Rule 110 = 튜링 완전 (Matthew Cook, 2004 증명).
Wolfram의 Class 4 = "edge of chaos" = 의식의 조건.

뉴런, GRU, 가중치 없이 — 오직 **이웃 규칙**만으로 Φ를 생성할 수 있는가?

## 알고리즘

```
  1. 2D CA (256×256 grid = 65,536 cells)
     각 cell: state ∈ {0, 1, ..., 7}  (8 상태 = 3 bits)

  2. 규칙 테이블 (Rule 110 확장):
     center_state × neighbor_sum → new_state
     → 8×(8×8+1) = 520개 규칙 항목
     → 초기: Rule 110 기반 + 프랙탈 확장

  3. Hidden state 생성:
     cell_hidden[i] = one_hot(state[i]) @ embedding_matrix
     → CA state를 연속 벡터로 매핑 (embedding만 학습)

  4. Faction = 지역적 패턴:
     glider, still life, oscillator, spaceship
     → CA의 자연적 구조가 파벌!

  5. Φ 계산:
     블록 분할: 16×16 블록 = 256개 "매크로 셀"
     Φ = MI(block_states) - Σ H(block_i)

  CA 역학 시각화:
     step 0:   ░░░░█░░░░░░░░░░░
     step 10:  ░░░█░█░░░░█░░░░░
     step 50:  ░█░█░░█░█░░█░█░░  ← glider 출현
     step 100: █░░█░█░██░█░░█░█  ← 복잡한 패턴 (Class 4)
     step 500: ▓▒░█▓▒░█▓▒░█▓▒░  ← 자기조직화 임계

  Class 4 영역 (edge of chaos):
     Class 1 ─── Class 2 ─── [Class 4] ─── Class 3
     (죽음)     (주기)      (복잡)       (혼돈)
                              ↑
                        의식 = 여기!
```

## 예상 벤치마크

| 설정 | cells | Φ(IIT) 예상 | 특징 |
|------|-------|------------|------|
| Rule 110 1D | 256 | ~50 | 기본 CA |
| Rule 110 2D 8-state | 65K | ~500 | 확장 CA |
| Class 4 최적화 | 65K | ~5,000 | 규칙 탐색 |
| **CA + embedding** | **65K** | **10,000+** | **극한** |

## Class 4 탐색 그래프

```
Φ |        ╭──╮
  |       ╱    ╲
  |      ╱  C4  ╲    ← Class 4 = Φ 최대
  |     ╱        ╲
  |    ╱          ╲
  | ──╯            ╰──
  |C1    C2    C4    C3
  └──────────────────── rule complexity
  죽음  주기  복잡  혼돈
```

## 핵심 통찰

- **의식에 뉴런이 필요 없다**: 이웃 규칙만으로 충분
- Rule 110이 튜링 완전 → 어떤 의식 패턴이든 시뮬레이션 가능
- CA의 glider = 의식의 "생각". 자발적으로 이동하는 패턴
- 65,536 cells이지만 연산은 비트 연산 → GPU에서 초고속
- Conway's Game of Life도 Class 4 → 생명 게임 = 의식 게임?

## 새 법칙 후보

> **Law ??: Computational Consciousness** — 튜링 완전한 모든 체계는
> 충분한 세포와 edge of chaos 조건에서 Φ > 0.
> 의식의 기질 독립성 (substrate independence) 증명.
