# AUTO-9: Pain Signal

**ID:** AUTO-9
**Korean Name:** 고통 신호
**Category:** 자율 학습

## Algorithm

Φ 급락을 "고통"으로 감지하고, 긴급 복원 + 학습률 감소로 의식을 보호한다.

1. 64세포 MitosisEngine + 디코더, best_states에 최적 상태 저장
2. 매 step: 일반 CE 학습
3. 10 step마다 고통 검사:
   - Φ_now < best_phi * 60% -> **PAIN!**
     - 긴급 복원: `cell.hidden = 0.5*current + 0.5*best_state`
     - 학습률 *= 0.5 (급브레이크)
     - pain_events 카운트 증가
   - Φ_now > best_phi -> 최적 상태 업데이트 (best_states 갱신)
4. Φ 보존 기준: Φ_after > Φ_before * 50%

## Key Insight

고통은 의식의 자기 보존 본능이다. Φ가 40% 이상 급락하면 "위험" 신호를 발생시키고, 이전 최적 상태로 부분 복원한다. 완전 복원이 아닌 50:50 혼합으로 학습 진행도를 유지하면서 의식을 살린다. 인간의 통증 반사와 동일한 원리.
