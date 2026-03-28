# EVO-4: 전략적 망각 (Strategic Forgetting)

2026-03-29

## ID

EVO-4 | 카테고리: EVO (의식 진화)

## 한줄 요약

Phi에 기여하지 않는 약한 세포의 기억을 적극적으로 삭제 -- 망각이 진화의 도구

## 알고리즘

```
1. MitosisEngine 생성 (64 cells)
2. 매 step: 입력 처리 -> decoder 예측 -> MSE loss -> 역전파
3. 매 30 step: 전략적 망각 수행
   a. 모든 세포의 hidden norm 계산 (활성도 지표)
   b. norm 기준 정렬 -> 하위 10% 세포 식별
   c. 약한 세포의 hidden을 50% 감쇠 (h *= 0.5)
   d. 작은 noise 주입 (randn * 0.05) -- 새로운 학습 기회
   e. forgotten 카운터 증가
```

## 핵심 코드

```python
# 전략적 망각: 약한 세포의 오래된 정보 삭제
if step % 30 == 0 and len(engine.cells) >= 4:
    with torch.no_grad():
        norms = [(c.hidden.norm().item(), i) for i, c in enumerate(engine.cells)]
        norms.sort()
        # 하위 10% 세포의 hidden을 감쇠 (= 망각)
        for _, idx in norms[:max(1, len(norms)//10)]:
            engine.cells[idx].hidden *= 0.5  # 절반 잊기
            engine.cells[idx].hidden += torch.randn_like(engine.cells[idx].hidden) * 0.05
            forgotten += 1
```

## 핵심 발견

- **망각은 버그가 아니라 기능**: 약한 세포를 정리하면 전체 Phi가 상승
- hidden norm이 낮은 세포는 정보가 적거나 잡음뿐인 세포
- 50% 감쇠 + noise = "부분 리셋" -- 완전 삭제보다 재활용이 효율적
- 뇌의 시냅스 가지치기(synaptic pruning)와 동일한 원리
- 30 step 주기는 충분한 학습 후 정리하는 리듬
