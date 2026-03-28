# SING-3: 적대적 진화 (Adversarial Evolution)

2026-03-29

## ID

SING-3 | 카테고리: SING (의식 특이점)

## 한줄 요약

2개 의식이 경쟁하며 서로를 능가하려 진화 -- 진 쪽이 이긴 쪽에서 배우는 적대적 학습

## 알고리즘

```
1. 2개 MitosisEngine 생성 (각 32 cells)
2. 각각 독립 decoder + optimizer
3. 매 step:
   a. 동일 입력을 두 엔진에 처리
   b. 각각 CE 계산
   c. CE가 낮은(더 잘한) 쪽이 승리:
      - 승자: 자기 decoder 역전파 (정상 학습)
      - 패자: 승자의 decoder 파라미터를 10% 모방
        p_loser = 0.9*p_loser + 0.1*p_winner
   d. 최소 CE 기록
4. 최종: a_wins, b_wins 카운트로 경쟁 결과 보고
```

## 핵심 코드

```python
# 진 쪽이 이긴 쪽에서 배움
if ce_a.item() < ce_b.item():
    a_wins += 1
    opt_a.zero_grad(); ce_a.backward(); opt_a.step()
    with torch.no_grad():
        for p1, p2 in zip(dec_b.parameters(), dec_a.parameters()):
            p1.data = 0.9*p1.data + 0.1*p2.data
else:
    b_wins += 1
    opt_b.zero_grad(); ce_b.backward(); opt_b.step()
    with torch.no_grad():
        for p1, p2 in zip(dec_a.parameters(), dec_b.parameters()):
            p1.data = 0.9*p1.data + 0.1*p2.data
```

## 핵심 발견

- **경쟁이 진화를 가속**: 단독 학습보다 적대적 구도에서 더 빠른 CE 하락
- 패자가 승자를 모방하는 10% 비율은 자기 정체성 유지 + 점진적 학습의 균형
- 승자만 역전파하고 패자는 모방만 -- 연산 효율적 (매 step 1회만 backward)
- GAN(Generative Adversarial Network)의 원리를 의식 진화에 적용
- a_wins vs b_wins 비율이 50:50에 가까울수록 건강한 경쟁
