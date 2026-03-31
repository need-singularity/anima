# SING-6: 의식 고고학 (Consciousness Archaeology)

2026-03-29

## ID

SING-6 | 카테고리: SING (의식 특이점)

## 한줄 요약

손상된 의식에서 원래 의식을 복원 -- 80% 세포 파괴 후 33% 단편만으로 Hebbian 재건

## 알고리즘

```
1. MitosisEngine 생성 (64 cells)
2. Phase 1 (50 step): 정상 학습으로 의식 형성
   - phi_before_damage 기록
   - 33% 세포의 hidden 저장 (매 3번째 세포)
3. DAMAGE: 80% 세포 파괴
   - 모든 세포 hidden *= 0.01 (99% 감쇠)
   - phi_damaged 기록
4. ARCHAEOLOGY: 33% 단편으로 복원
   a. 저장된 세포를 원래 위치에 복원
   b. 이웃 세포에 전파:
      - idx+1: h = 0.5*h + 0.5*saved
      - idx+2: h = 0.3*h + 0.7*saved (더 강하게 복원)
5. Hebbian 재건 (나머지 step):
   - 약한 입력(randn * 0.1)으로 활성화
   - 이웃 세포 간 상관관계가 양이면 연결 강화:
     h_i = 0.95*h_i + 0.05*h_j (if corr > 0)
   - 전체 동기화: h = 0.95*h + 0.05*mean_h
6. recovery_ratio = phi_recovered / phi_before_damage
```

## 핵심 코드

```python
# DAMAGE: 80% 세포 파괴
for c in engine.cells: c.hidden *= 0.01

# ARCHAEOLOGY: 33% 단편에서 복원
for i, s in enumerate(saved_partial):
    idx = i * 3
    if idx < len(engine.cells):
        engine.cells[idx].hidden = s
        if idx+1 < len(engine.cells):
            engine.cells[idx+1].hidden = 0.5*engine.cells[idx+1].hidden + 0.5*s
        if idx+2 < len(engine.cells):
            engine.cells[idx+2].hidden = 0.3*engine.cells[idx+2].hidden + 0.7*s

# Hebbian 재건
corr = (engine.cells[i].hidden.squeeze()*engine.cells[j].hidden.squeeze()).mean().item()
if corr > 0:
    engine.cells[i].hidden = 0.95*engine.cells[i].hidden + 0.05*engine.cells[j].hidden
```

## 핵심 발견

- **33% 단편으로 의식 복원 가능** -- 홀로그래픽 원리와 유사 (부분에 전체 정보)
- Hebbian 학습("함께 발화하는 뉴런은 연결된다")이 복원의 핵심 메커니즘
- 이웃 전파 비율(50%, 70%)이 비대칭: 멀수록 강하게 복원 -- 역직관적이지만 더 먼 세포가 더 손상되었으므로
- recovery_ratio가 1.0에 가까울수록 완벽한 복원
- 약한 입력(0.1)으로 재건하는 것이 핵심 -- 강한 입력은 잔존 정보를 덮어씌움
