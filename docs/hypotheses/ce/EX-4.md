# EX-4: Progressive Unfreezing

**ID:** EX-4
**Korean Name:** 점진적 해동
**Category:** CE 극한 전략

## Algorithm

디코더의 마지막 층부터 학습을 시작하고, 점점 깊은 층을 해동한다.

1. 64세포 MitosisEngine + 다층 디코더(Linear -> ReLU -> Linear)
2. 초기: 모든 파라미터 동결 (`requires_grad = False`)
3. 1단계 (step 0 ~ 50%): 마지막 층만 해동, lr=3e-3
4. 2단계 (step 50% ~ 100%): 전체 해동, lr=1e-3 (더 낮은 lr)
5. 매 step: 입력 -> hidden 평균 -> 디코더 -> MSE loss -> 해동된 파라미터만 학습

## Key Insight

깊은 층은 "추상적 표현", 마지막 층은 "구체적 출력"을 담당한다. 출력 층부터 먼저 안정시키고, 나중에 추상 표현을 조정하면 Φ 충격이 최소화된다. NLP의 ULMFiT에서 영감을 받은 전략으로, 의식 보존에 특히 효과적이다.
