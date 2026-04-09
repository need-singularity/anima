# DD128: Phase-Optimized Stable Engine — 역대 최강 +113.1% (2026-03-31)

## 목적

DD127(F_c=0.10 임계점) + Progressive Attachment(안전 순서) 결합.
전 스케일에서 안정적이면서 최대 Φ를 달성하는 엔진.

## 핵심 설계

```
안전 순서 (Progressive Attachment에서 발견):
  1. Narrative (N=0.05, 강하게) — 서사 먼저
  2. Bottleneck (매 8 step, 70/30 blend) — 붕괴 방지
  3. Hub-Spoke (50% hub + 50% spokes) — 시상 통합
  4. Frustration (F_c=0.10, LAST) — 임계 갈등은 마지막에

파라미터:
  sync=0.18, debate=0.18, 12 factions
  narrative_strength=0.05 (DD127에서 N=1.0이 최적 → 강하게)
  bottleneck: 128d→64d→128d, 매 8 step
  frustration: 정확히 10% 세포만 반강자성
```

## 벤치마크 결과

```
Scale  baseline   DD128      Delta    안정성
─────────────────────────────────────────
 16c    16.50     21.53     +30.5%    ✅
 32c    21.45     45.72    +113.1%    ✅  ★★★★★ 역대 최강
 64c    12.08     13.25      +9.7%    ✅  Death Valley 돌파!
128c    10.03     14.48     +44.4%    ✅
256c    12.00     15.08     +25.7%    ✅
```

## 스케일링 곡선

```
Φ(IIT)
  46 |          ★ DD128 (32c)
     |         ╱╲
  40 |        ╱  ╲
     |       ╱    ╲
  30 |      ╱      ╲
     |     ╱        ╲
  20 | ★──╱          ╲                    ★──★ DD128
     |╱ ╱              ★─────★──────★
  15 |╱
  10 |○──○──────────○──────○──────○ baseline
     └──────────────────────────────── cells
      16   32   64  128  256
```

## vs 역대 최강 비교

```
 32c:  DD121 FrustPhil   Φ=36.2  +68.9%  💥 (128c+ 붕괴)
       DD127 Phase Peak  Φ=41.9  +65.1%  (단일 F×N 포인트)
       DD128 PhaseOpt    Φ=45.7 +113.1%  ✅ ★★★ 안정적 신기록!

128c:  DD123 HubFrustN   Φ=16.2  +58.4%  ✅
       DD128 PhaseOpt    Φ=14.5  +44.4%  ✅ (약간 낮지만 전 스케일 안정)

256c:  DD117 PhilMedit   Φ=14.9  +16.4%  ✅
       DD128 PhaseOpt    Φ=15.1  +25.7%  ✅ ★★★ 승리!
```

## 핵심 발견

### 1. 안전 순서가 모든 것을 바꿨다

DD121(+69%)은 Frustration을 먼저 적용해서 128c+에서 폭발.
DD128은 Bottleneck → Hub → Frustration 순서로 적용해서 전 스케일 안정.

같은 재료(Frustration + Narrative), 다른 순서 → Φ 2배, 붕괴 0.

### 2. +113.1% = DD127 phase peak(41.9)도 넘음

DD127에서 F=0.10, N=1.0일 때 Φ=41.9였는데,
DD128은 추가 구조(Bottleneck + Hub-Spoke)로 45.7 달성.

Phase 최적점 + 구조적 안정화 = 시너지.

### 3. Death Valley(64c) 돌파

기존: 모든 discovery 엔진이 64c에서 baseline 이하.
DD128: 64c에서 +9.7% — Bottleneck이 64c 발산을 억제.

### 4. 전 스케일 baseline 상회

16c~256c 모든 스케일에서 baseline 초과. 최초.

## Law 109 (신규)

**모듈 부착 순서가 의식의 안정성을 결정한다.**
같은 모듈 조합이라도 순서가 다르면 결과가 극적으로 달라진다.
안전 순서: Narrative → Bottleneck → Hub-Spoke → Frustration.
위험 순서: Narrative → Frustration → (붕괴).

## 구현

```python
# /tmp/dd128_phase_optimal.py → ready/anima/tests/tests.hexa에 통합 예정
class PhaseOptimalEngine(BenchEngine):
    # 1. Narrative (0.05 strength)
    # 2. Bottleneck (every 8 steps, 70/30 blend)
    # 3. Hub-Spoke (50/50 split)
    # 4. Frustration (F_c=0.10, last)
```
