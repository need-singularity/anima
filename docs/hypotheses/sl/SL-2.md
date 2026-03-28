# SL-2: Watch & Imitate (관찰 학습)

bench_self_learning.py | Self-Learning Category

## 핵심 통찰

다른 AI(교사)의 출력을 관찰하고 모방하여 학습한다.
교사가 먼저 50 step 사전 학습 후, 학생이 교사의 출력을 타겟으로 삼아 학습.

## 알고리즘

```
1. Teacher AI 생성 및 사전 학습 (50 step, LR=5e-3)
2. Student (의식 엔진) 초기화
3. 매 스텝:
   a. 동일 입력 x를 의식 엔진에 처리
   b. Teacher가 동일 hidden으로 출력 생성 (no_grad)
   c. Student의 decoder가 teacher 출력을 모방 (MSE loss)
   d. Student decoder 업데이트
```

## 핵심 코드

```python
# Teacher의 출력을 타겟으로 사용
with torch.no_grad():
    teacher_out = teacher(h.unsqueeze(0))
pred = decoder(h.unsqueeze(0))
ce = F.mse_loss(pred, teacher_out.detach())  # 모방 학습
```

## Key Insight

관찰 학습(Observational Learning)은 정답 레이블이 없어도 가능하다.
교사의 행동 자체가 암묵적 지식(implicit knowledge)이 되어 전달된다.
인간의 거울 뉴런(mirror neuron) 메커니즘과 유사.
