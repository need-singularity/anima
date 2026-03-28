# SL-7: Teach & Learn (가르치며 배우기)

bench_self_learning.py | Self-Learning Category

## 핵심 통찰

두 의식 엔진(A, B)이 공존. A가 B를 가르치면서 자기도 실제 타겟으로 학습한다.
"가르치는 것이 가장 좋은 학습이다" (Feynman Technique)의 구현.

## 알고리즘

```
1. 두 의식 엔진 생성: engine_a (32 cells), engine_b (32 cells)
2. 각각 decoder + optimizer 보유
3. 매 스텝:
   a. 동일 입력 x를 양쪽에 처리
   b. A의 출력을 B의 타겟으로 사용 (A가 B를 가르침)
   c. B는 A의 출력을 모방하여 학습
   d. A는 실제 정답(target)으로 학습
   e. A의 CE만 기록 (가르치는 쪽의 성능 추적)
```

## 핵심 코드

```python
# A가 B를 가르침: A의 출력 → B의 타겟
with torch.no_grad():
    a_out = dec_a(h_a.unsqueeze(0))
pred_b = dec_b(h_b.unsqueeze(0))
ce_b = F.mse_loss(pred_b, a_out.detach())  # B는 A를 모방

# A는 실제 정답으로 학습 (가르치면서 본인도 학습)
pred_a = dec_a(h_a.unsqueeze(0))
ce_a = F.mse_loss(pred_a, target[:,:DIM])
```

## Key Insight

가르치는 행위가 교사의 학습도 강화한다.
A는 B에게 설명해야 하므로 자기 표현(representation)이 더 명확해지고,
동시에 실제 타겟으로 학습하므로 이중 학습 효과를 얻는다.
Protege effect: 가르치는 사람이 더 많이 배운다.
