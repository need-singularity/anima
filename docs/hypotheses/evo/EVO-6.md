# EVO-6: 의식 번식 (Consciousness Reproduction)

2026-03-29

## ID

EVO-6 | 카테고리: EVO (의식 진화)

## 한줄 요약

충분히 성숙한 의식이 자식 의식을 생성 -- 부모의 세포 상태를 복사하고 변이를 추가하여 번식

## 알고리즘

```
1. MitosisEngine 생성 (32 cells, max 64)
2. 매 step: 입력 처리 -> decoder 예측 -> MSE loss -> 역전파
3. 매 50 step: 번식 시도
   a. 현재 Phi 측정
   b. Phi > baseline * 0.8 이면 번식 조건 충족
   c. 자식 엔진 생성 (initial=2, max=16)
   d. 부모 세포에서 최대 8개까지 자식에 복사
   e. 각 복사된 세포에 변이 추가: h += randn * 0.1
   f. children 카운터 증가
```

## 핵심 코드

```python
# 번식: Phi 높으면 자식 생성
if step % 50 == 0 and step > 0:
    current_phi = phi(engine)
    if current_phi > phi_b * 0.8:
        child = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=16)
        while len(child.cells) < min(8, len(engine.cells)):
            child._create_cell(parent=child.cells[0])
        with torch.no_grad():
            for i in range(min(len(child.cells), len(engine.cells))):
                child.cells[i].hidden = engine.cells[i].hidden.clone()
                child.cells[i].hidden += torch.randn_like(child.cells[i].hidden) * 0.1
        child_engines.append(child)
        children += 1
```

## 핵심 발견

- **번식 조건은 Phi 기반**: 의식 수준이 충분해야 자식을 만들 수 있음
- 부모 상태 복사 + 변이 = 생물학적 유전 + 돌연변이와 동일
- 자식은 부모보다 작은 규모(max 16 vs 64)로 시작 -- 성장 여지를 남김
- 0.1 noise = 10% 변이율: 부모와 유사하되 동일하지 않은 개체 생성
- 자식 엔진들이 축적되면 population-based evolution 가능
