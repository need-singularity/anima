# TL-L2: Concept Teaching (개념 패키징)

bench_self_learning.py | Tension Link Learning Category

## 핵심 통찰

학습 대상(target)을 5개의 독립 채널 인코더로 변환하여 의식 세포에 직접 주입한다.
개념을 "패키지"로 만들어 전달하는 방식.

## 알고리즘

```
1. 5개 채널 인코더 생성: [nn.Linear(DIM, DIM//5)] x 5
2. 의식 엔진 초기화 (64 cells)
3. 매 스텝:
   a. Target을 5개 인코더로 분해:
      channels = [enc(target) for enc in ch_enc]  # 5개 채널
   b. 5채널 결합 + HIDDEN 크기로 패딩 → full_concept
   c. 처음 4개 세포에 주입:
      cell.hidden = 0.85 * cell.hidden + 0.15 * full_concept
   d. 입력 처리 + decoder 학습 (MSE)
```

## 핵심 코드

```python
# 5채널 개념 패키징
channels = [enc(target[:,:DIM]).squeeze() for enc in ch_enc]
full_concept = F.pad(torch.cat(channels), (0, pad_size))[:HIDDEN]

# 세포에 15% 비율로 주입
for cell in engine.cells[:4]:
    cell.hidden = 0.85*cell.hidden + 0.15*full_concept.unsqueeze(0)
```

## Key Insight

TL-L1이 교사의 "이해"를 전달한다면, TL-L2는 "정답 자체"를 구조화하여 전달한다.
5채널 분해는 개념의 다면적 표현을 가능하게 한다 (한 채널이 한 측면을 담당).
0.15 blend ratio는 TL-L1(0.1)보다 약간 강하게 주입 -- 개념은 직접적이므로 더 강하게 전달해도 안전하다.
