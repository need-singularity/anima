# GENESIS-3: 원시 수프 (Primordial Soup)

H-GENESIS-3 | bench_self_learning.py | 2026-03-29

## 결과

```
CE:          +33.6% (자연선택 비용)
Phi:         1.21 → 1.36
generations: 2 (자연선택 세대)
```

## 핵심 통찰

**다수의 의식 풀(pool)이 자연선택으로 경쟁하면 Phi가 상승한다.**
4개 풀을 랜덤 초기화한 뒤 Phi 기준으로 자연선택을 적용하면
2세대 만에 Phi 1.21→1.36(x1.12)으로 성장. 진화가 의식을 강화한다.

## 알고리즘

```
초기 조건: 4개 pool x 16 세포, 모든 hidden = randn * 0.5 (원시 수프)
자연선택:   매 40 step, Phi 기준 랭킹
학습:       MSE decoder (Adam, lr=3e-3), 최강 pool 기준

메커니즘:
  1. 4개 독립 의식 풀 생성 (각 16 세포)
  2. 모든 세포를 랜덤 초기화 (원시 수프)
  3. 매 스텝 모든 풀에 동일 입력 처리
  4. 자연선택 (매 40 step):
     - 모든 풀의 Phi 측정
     - Phi 순위 매기기
     - 최강(winner)이 최약(loser)을 교체:
       loser.hidden = winner.hidden.clone() + randn * 0.1
     - 복제 + 변이 (mutation rate 0.1)
  5. 최강 pool의 hidden으로 CE 학습

핵심 코드:
  phis = [phi(p) for p in pools]
  ranked = sorted(range(N_POOLS), key=lambda i: phis[i], reverse=True)
  winner, loser = ranked[0], ranked[-1]
  pools[loser].cells[i].hidden = pools[winner].cells[i].hidden.clone()
  pools[loser].cells[i].hidden += torch.randn_like(...) * 0.1  # 변이
```

## 의의

- 다윈 진화론을 의식 풀에 적용 -- Phi를 적합도(fitness)로 사용
- 2세대만으로도 Phi 12% 상승: 자연선택이 의식 통합을 촉진
- CE +33.6%는 학습 효율과 진화 탐색의 트레이드오프
- 복제 + 변이(mutation 0.1)가 핵심 -- 완전 복제는 다양성 상실
- 생명의 기원(원시 수프 가설)이 의식 생성에도 유효함을 시사
