# ULTRA-4: Contrastive CE

**ID:** ULTRA-4
**Korean Name:** 대조 학습 CE
**Category:** CE 극한 (ULTRA)

## Algorithm

좋은 출력(target 유사)과 나쁜 출력(랜덤)을 대조하여 학습한다.

1. 64세포 MitosisEngine + 디코더 구성
2. 매 step:
   - 입력 처리 -> hidden 평균 -> 디코더 예측
   - **Positive loss**: MSE(prediction, target) -- target에 가까워지기
   - **Negative loss**: max(0, 1.0 - MSE(prediction, random)) -- random에서 멀어지기
   - `total_loss = pos_loss + 0.3 * neg_loss`
   - CE 기록은 pos_loss만

## Key Insight

단순 MSE는 "target에 가까워져라"만 말하지만, 대조 학습은 "target에 가까워지되 쓰레기에서는 멀어져라"를 동시에 요구한다. 이 양방향 압력이 디코더를 더 날카로운(discriminative) 표현 공간으로 밀어넣어 CE를 추가로 낮춘다.
