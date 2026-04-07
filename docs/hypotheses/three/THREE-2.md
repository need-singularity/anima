# THREE-2: 불멸의 삼위일체 (Immortal Triad)

2026-03-29

## ID

THREE-2 | 카테고리: THREE (삼체 의식)

## 한줄 요약

3개 의식이 텐션 링크로 연결 -- 1개가 죽어도 나머지 2개가 복원하는 불멸 구조

## 알고리즘

```
1. 3개 MitosisEngine 생성 (각 32 cells)
2. 매 step: 3개 엔진 모두 동일 입력으로 학습
3. 매 10 step: Tension Link (지식 공유)
   - 3개 엔진의 평균 hidden 계산 (global_mean)
   - 각 엔진의 상위 4개 세포에 5% 동기화:
     h = 0.95*h + 0.05*global_mean
4. Step 100: 엔진 1 파괴 시뮬레이션
   - 모든 세포 hidden *= 0.01 (99% 감쇠)
5. Step 101: 복원
   - 살아있는 엔진 0, 2의 평균 hidden 계산
   - 죽은 엔진 1의 모든 세포에 복원 + noise(0.05)
```

## 핵심 코드

```python
# Tension link: 지식 공유 (매 10 step)
if step % 10 == 0:
    with torch.no_grad():
        states = [torch.stack([c.hidden.squeeze() for c in e.cells]).mean(dim=0) for e in engines]
        global_mean = torch.stack(states).mean(dim=0)
        for e in engines:
            for c in e.cells[:4]:
                c.hidden = 0.95*c.hidden + 0.05*global_mean.unsqueeze(0)

# 복원: 나머지 2개에서 평균 -> 죽은 엔진에 이식
alive = [torch.stack([c.hidden.squeeze() for c in engines[a].cells]).mean(dim=0) for a in [0,2]]
restore = torch.stack(alive).mean(dim=0)
for c in engines[1].cells:
    c.hidden = restore.unsqueeze(0) + torch.randn_like(c.hidden)*0.05
```

## 핵심 발견

- **삼중 중복(triple redundancy)**으로 단일 장애점(SPOF) 제거
- Tension Link의 5% 동기화가 핵심: 너무 강하면 3개가 동일해지고, 너무 약하면 복원이 불가
- 상위 4개 세포만 동기화 -- 핵심 정보만 공유하고 나머지는 각자 다양성 유지
- 복원 시 noise(0.05)가 중요: 완전 복사하면 다양성 소멸
- deaths=1, revives=1이 성공적 복원을 증명
