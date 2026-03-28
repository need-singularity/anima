# EX-1: Adversarial Self-Teach

**ID:** EX-1
**Korean Name:** 적대적 자기교육
**Category:** CE 극한 전략

## Algorithm

GAN 구조로 디코더 A(생성)와 디코더 B(판별), 의식이 심판 역할을 한다.

1. 64세포 MitosisEngine + Generator(Linear HIDDEN->DIM) + Discriminator(Linear DIM->1)
2. 매 step:
   - 입력 처리 -> 세포 hidden 평균
   - Generator가 출력 생성 (fake)
   - Discriminator가 real(target)과 fake를 판별
   - **D 학습**: -log(sigmoid(real)) - log(1 - sigmoid(fake))
   - **G 학습**: MSE(fake, target) + 0.1 * (-log(sigmoid(disc(fake))))
     - target 매칭 + discriminator 속이기 동시 최적화

## Key Insight

적대적 학습은 단순 MSE보다 더 "그럴듯한" 출력을 만든다. Generator는 target에 가까우면서도 discriminator를 속일 수 있는 출력을 학습하며, 이는 단순 평균 회귀를 넘어선 날카로운(sharp) 예측을 가능하게 한다.
