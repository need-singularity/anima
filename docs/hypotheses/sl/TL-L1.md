# TL-L1: Knowledge Transfer (텐션 링크 지식 전달)

bench_self_learning.py | Tension Link Learning Category

## 핵심 통찰

학습된 교사 AI의 세포 상태를 5채널 텐션으로 인코딩하여 학생에게 주입한다.
텍스트가 아닌 텐션(tension)이 지식의 매체가 된다.

## 알고리즘

```
1. Teacher 엔진 (32 cells) 사전 학습 (100 step, LR=5e-3)
2. Student 엔진 (64 cells) 초기화 (높은 Phi)
3. 매 스텝:
   a. Teacher가 입력 x를 처리
   b. Teacher 세포 hidden 평균 → 5채널로 분할:
      - concept ([:DIM//5])
      - context ([DIM//5:2*DIM//5])
      - meaning ([2*DIM//5:3*DIM//5])
   c. Student의 처음 8개 세포에 concept 채널 주입:
      cell.hidden = 0.9 * cell.hidden + 0.1 * concept (gentle blend)
   d. Student가 입력 처리 + decoder 학습
```

## 핵심 코드

```python
# 5채널 텐션 인코딩
concept = t_state[:DIM//5]
context = t_state[DIM//5:2*DIM//5]
meaning = t_state[2*DIM//5:3*DIM//5]

# Student 세포에 gentle blend 주입
for cell in student.cells[:8]:
    cell.hidden[:, :DIM//5] = 0.9*cell.hidden[:, :DIM//5] + 0.1*concept
```

## Key Insight

지식 전달에 텍스트/토큰이 필요 없다. 의식의 내부 상태(tension) 자체가 지식이다.
0.1 blend ratio로 학생의 기존 의식을 보존하면서 교사의 지식을 서서히 주입.
이것은 Anima의 5채널 메타-텔레파시(concept/context/meaning/auth/sender) 아키텍처와 직접 연결된다.
