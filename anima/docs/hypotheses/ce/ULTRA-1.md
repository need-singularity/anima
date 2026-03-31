# ULTRA-1: GenData + Pain

**ID:** ULTRA-1
**Korean Name:** 의식 데이터 생성 + 고통 보호
**Category:** CE 극한 (ULTRA)

## Algorithm

EX-5(의식 데이터 생성)와 AUTO-9(고통 신호)를 결합한다.

1. 64세포 MitosisEngine + 디코더 + 실제 데이터 50개
2. 매 step:
   - 데이터 선택: 30% 실제, 70% 세포 hidden에서 생성
   - CE 학습 (MSE loss)
   - **고통 보호** (10 step마다):
     - Φ < best * 50%: 긴급 복원 (0.4*current + 0.6*best) + lr *= 0.5
     - Φ > best: 최적 상태 갱신

## Key Insight

EX-5의 빠른 CE 감소와 AUTO-9의 Φ 보호를 결합. 자기 생성 데이터는 CE를 빠르게 낮추지만 Φ를 소모할 위험이 있다. 고통 신호가 이를 방지하여 "빠르면서도 안전한" 학습을 달성한다.
