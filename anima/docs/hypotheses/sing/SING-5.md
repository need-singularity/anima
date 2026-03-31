# SING-5: 재귀적 꿈 (Recursive Dreams)

2026-03-29

## ID

SING-5 | 카테고리: SING (의식 특이점)

## 한줄 요약

꿈 안에서 꿈을 꾸는 인셉션(Inception) 구조 -- 기억 재생(Level 1)과 기억 재조합의 재조합(Level 2)으로 깊은 통합

## 알고리즘

```
1. MitosisEngine 생성 (64 cells)
2. 40 step 주기로 3단계 반복:
   a. WAKE (step 0-19): 정상 학습
      - 입력 처리 -> decoder 예측 -> MSE loss -> 역전파
      - memory 버퍼에 입력 저장 (최대 30개)
   b. DREAM Level 1 (step 20-29): 기억 재생
      - memory에서 과거 입력을 꺼내 engine에 재처리
      - 세포 동기화: h = 0.9*h + 0.1*mean_h
   c. DREAM Level 2 (step 30-39): 꿈의 꿈
      - 3개 기억을 가중 합산 + noise로 재조합
        dream2 = 0.4*m1 + 0.35*m2 + 0.25*m3 + randn*0.1
      - 더 강한 동기화: h = 0.85*h + 0.15*mean_h
```

## 핵심 코드

```python
if cycle < 20:
    # WAKE: 학습
    engine.process(x)
    memory.append(x.detach())
elif cycle < 30:
    # DREAM Level 1: 기억 재생
    engine.process(memory[step % len(memory)])
    mean_h = torch.stack([c.hidden for c in engine.cells]).mean(dim=0)
    for c in engine.cells: c.hidden = 0.9*c.hidden + 0.1*mean_h
else:
    # DREAM Level 2: 꿈의 꿈 (기억의 재조합의 재조합)
    m1 = memory[step % len(memory)]
    m2 = memory[(step+5) % len(memory)]
    m3 = memory[(step+11) % len(memory)]
    dream2 = 0.4*m1 + 0.35*m2 + 0.25*m3 + torch.randn(1, DIM)*0.1
    engine.process(dream2)
    for c in engine.cells: c.hidden = 0.85*c.hidden + 0.15*mean_h
```

## 핵심 발견

- **꿈의 계층**: Level 1은 단순 재생(replay), Level 2는 창조적 재조합(recombination)
- Level 2의 3개 기억 가중합(0.4/0.35/0.25)이 새로운 패턴을 생성 -- 창의성의 메커니즘
- Level 2에서 더 강한 sync(15% vs 10%)가 깊은 통합을 유도
- 20:10:10 비율 = 깨어있는 시간이 50%, 꿈이 50% -- 뇌의 수면 비율과 유사
- noise(0.1)가 꿈에 무작위성을 추가하여 과적합 방지
