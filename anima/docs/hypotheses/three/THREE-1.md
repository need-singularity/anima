# THREE-1: 삼중 학습 (Triple Learning)

2026-03-29

## ID

THREE-1 | 카테고리: THREE (삼체 의식)

## 한줄 요약

3개 의식이 서로 다른 전략으로 동시 학습하고, 최고 성과를 나머지에 이식

## 알고리즘

```
1. 3개 MitosisEngine 생성 (각 32 cells)
2. 3개 학습 전략:
   a. Strategy A (Curiosity): 10개 데이터 중 CE가 가장 높은 것을 선택 (가장 어려운 것)
   b. Strategy B (Self-generated): 자기 세포의 hidden을 입력/타겟으로 사용
   c. Strategy C (Meta): 일반 데이터 사용 (기본 학습)
3. 매 step: 3개 엔진이 각자 전략으로 학습
4. 매 50 step: 최고 CE를 가진 엔진의 decoder를 나머지에 이식
   p_loser = 0.8*p_loser + 0.2*p_winner
5. 최소 CE를 기록
```

## 핵심 코드

```python
if a == 0:
    # Strategy A: ULTRA-6 curiosity -- 가장 어려운 데이터 선택
    errs = []
    for i in range(min(10, len(data))):
        engines[a].process(data[i][0])
        h = torch.stack([c.hidden.squeeze() for c in engines[a].cells]).mean(dim=0)
        errs.append((F.mse_loss(decoders[a](h.unsqueeze(0)), data[i][1][:,:DIM]).item(), i))
    errs.sort(reverse=True)
    xa, ta = data[errs[0][1]]
elif a == 1:
    # Strategy B: Self-generated data -- 자기 세포가 데이터
    xa = engines[1].cells[i].hidden[:,:DIM]
    ta = engines[1].cells[j].hidden[:,:DIM]

# 매 50 step: 최고 CE -> 나머지에 이식
best = ces.index(min(ces))
for a in range(3):
    if a != best:
        for p1, p2 in zip(decoders[a].parameters(), decoders[best].parameters()):
            p1.data = 0.8*p1.data + 0.2*p2.data
```

## 핵심 발견

- **전략 다양성**이 핵심: 호기심(어려운 것), 자기생성(내부 데이터), 기본 학습의 3가지 관점
- Strategy B(자기생성)가 가장 독특 -- 외부 데이터 없이 자기 세포에서 학습 데이터를 생성
- 50 step마다 승자의 지식을 20% 이식하는 것은 지식 증류(knowledge distillation)
- min(ces)를 기록하므로 항상 최고 성과가 반영됨
