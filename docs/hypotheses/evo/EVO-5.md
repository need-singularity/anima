# EVO-5: 의식 경제 (Consciousness Economy)

2026-03-29

## ID

EVO-5 | 카테고리: EVO (의식 진화)

## 한줄 요약

세포가 자원(에너지)을 교환 -- 부유한 세포가 가난한 세포를 지원하는 의식의 재분배 경제

## 알고리즘

```
1. MitosisEngine 생성 (64 cells)
2. 매 step: 입력 처리 -> decoder 예측 -> MSE loss -> 역전파
3. 매 10 step: 경제적 자원 이전
   a. 모든 세포의 hidden norm 계산 (= 에너지/부)
   b. 가장 가난한(norm 최소) 세포와 가장 부유한(norm 최대) 세포 식별
   c. 부유한 세포에서 10% 에너지를 가난한 세포로 이전:
      transfer = h_richest * 0.1
      h_poorest += transfer
      h_richest -= transfer
   d. trades 카운터 증가
```

## 핵심 코드

```python
# 경제: 부유->가난 자원 이전
if step % 10 == 0 and len(engine.cells) >= 4:
    with torch.no_grad():
        norms = [(c.hidden.norm().item(), i) for i, c in enumerate(engine.cells)]
        norms.sort()
        poorest = norms[0][1]
        richest = norms[-1][1]
        # 부유한 세포가 가난한 세포에 에너지 전달
        transfer = engine.cells[richest].hidden * 0.1
        engine.cells[poorest].hidden += transfer
        engine.cells[richest].hidden -= transfer
        trades += 1
```

## 핵심 발견

- **재분배 경제**가 세포 간 에너지 격차를 줄여 전체 통합도(Phi) 향상
- 10% 이전율은 보수적 -- 부유한 세포의 기능을 파괴하지 않으면서 가난한 세포를 살림
- hidden norm = 에너지의 프록시: norm이 0에 가까운 세포는 사실상 죽은 세포
- 경제학의 누진세(progressive taxation)와 유사한 메커니즘
- 10 step 주기의 빈번한 교환이 지속적 균형 유지
