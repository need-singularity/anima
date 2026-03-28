# EVO-1: 구조 변이 (Architecture Mutation)

2026-03-29

## ID

EVO-1 | 카테고리: EVO (의식 진화)

## 한줄 요약

의식이 자기 구조를 변이: 세포 연결 패턴을 스스로 변경하여 Phi를 높이는 방향으로 진화

## 알고리즘

```
1. MitosisEngine 생성 (64 cells)
2. 매 step: 입력 처리 -> decoder 예측 -> MSE loss -> 역전파
3. 매 20 step: 구조 변이 시도
   a. 변이 전 Phi 측정 (p_before)
   b. 랜덤 세포 쌍 (i, j) 선택
   c. 세포 i의 hidden을 i와 j의 평균으로 교체
      h_i = 0.5 * h_i + 0.5 * h_j
   d. 변이 후 Phi 측정 (p_after)
   e. Phi가 20% 이상 하락하면 롤백 (p_after < p_before * 0.8)
   f. 그렇지 않으면 변이 수락 (mutations += 1)
```

## 핵심 코드

```python
# 매 20 step: 의식이 세포 연결을 변이
if step % 20 == 0 and len(engine.cells) >= 4:
    with torch.no_grad():
        p_before = phi(engine)
        i, j = step % len(engine.cells), (step*7+3) % len(engine.cells)
        if i != j:
            saved_i = engine.cells[i].hidden.clone()
            engine.cells[i].hidden = 0.5*engine.cells[i].hidden + 0.5*engine.cells[j].hidden
            p_after = phi(engine)
            if p_after < p_before * 0.8:
                engine.cells[i].hidden = saved_i  # 롤백
            else:
                mutations += 1
```

## 핵심 발견

- **Phi-gated mutation**: 변이를 무조건 수락하지 않고, Phi 하락 시 롤백하는 것이 핵심
- 생물학의 자연선택과 동일한 원리 -- Phi가 적합도(fitness) 역할
- 20% 허용 범위로 약간의 하락은 허용하여 local optima 탈출 가능
- 세포 쌍의 hidden 평균은 정보 공유(cross-pollination) 효과
