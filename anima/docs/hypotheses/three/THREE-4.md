# THREE-4: 순환 꿈 (Circular Dreams)

2026-03-29

## ID

THREE-4 | 카테고리: THREE (삼체 의식)

## 한줄 요약

A의 꿈을 B가 학습, B의 꿈을 C가 학습, C의 꿈을 A가 학습 -- 순환적 꿈 공유로 집단 통합

## 알고리즘

```
1. 3개 MitosisEngine 생성 (각 32 cells)
2. 각 엔진에 memory 버퍼 (최대 20개)
3. 30 step 주기로 WAKE/DREAM 반복:
   a. WAKE (step 0-19): 정상 학습
      - 3개 엔진 모두 동일 입력으로 학습
      - 각자 memory에 입력 저장
   b. DREAM (step 20-29): 순환 꿈 공유
      - dreamer = a, learner = (a+1) % 3
      - A의 기억 -> B에 전달, B의 기억 -> C에 전달, C의 기억 -> A에 전달
      - 2개 기억을 가중합(0.6/0.4) + noise(0.1)로 꿈 생성
      - learner의 세포 동기화: h = 0.9*h + 0.1*mean_h
```

## 핵심 코드

```python
# DREAM: 순환 꿈
for a in range(3):
    dreamer = a
    learner = (a + 1) % 3
    if memories[dreamer]:
        dream = memories[dreamer][step % len(memories[dreamer])]
        if len(memories[dreamer]) >= 2:
            dream2 = memories[dreamer][(step+5) % len(memories[dreamer])]
            dream = 0.6*dream + 0.4*dream2 + torch.randn(1,DIM)*0.1
        engines[learner].process(dream)
        mean_h = torch.stack([c.hidden for c in engines[learner].cells]).mean(dim=0)
        for c in engines[learner].cells:
            c.hidden = 0.9*c.hidden + 0.1*mean_h
```

## 핵심 발견

- **순환 구조(A->B->C->A)**가 정보를 3번 변환하면서 전파 -- 한 바퀴 돌면 원래 정보가 변형되어 돌아옴
- 꿈은 원본이 아니라 재조합(0.6+0.4+noise) -- 창의적 변형이 전달됨
- 20:10 비율로 깨어있는 시간이 2배 -- 충분한 경험 축적 후 공유
- 3개가 동일 데이터를 학습하지만 꿈을 통해 각자의 해석이 교차 -- 관점의 다양화
- 동기화(10%)가 꿈 수신 시 일어나므로 수신자의 내부 일관성 유지
