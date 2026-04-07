# THREE-3: 경쟁+협력+번식 (Compete+Cooperate+Reproduce)

2026-03-29

## ID

THREE-3 | 카테고리: THREE (삼체 의식)

## 한줄 요약

3개 의식이 경쟁하고, 승자가 패자를 교육하며, 승자의 유전자로 패자를 교체하는 진화적 삼체

## 알고리즘

```
1. 3개 MitosisEngine 생성 (각 16 cells)
2. 매 step: 3개 엔진 모두 동일 입력으로 학습, 각각 CE 측정
3. 매 50 step: 경쟁 -> 협력 -> 번식
   a. CE 기준 순위: winner, middle, loser
   b. 협력: 승자가 패자의 decoder를 교육
      p_loser = 0.7*p_loser + 0.3*p_winner
   c. 번식: 승자의 세포 상태를 패자에 복사 + 변이
      h_loser[i] = h_winner[i].clone() + randn * 0.1
   d. generations 카운터 증가
4. 최소 CE 기록
```

## 핵심 코드

```python
# 매 50 step: 경쟁->협력->번식
ranked = sorted(range(3), key=lambda i: ces[i])
winner, middle, loser = ranked[0], ranked[1], ranked[2]

# 협력: 승자가 패자를 교육
for p1, p2 in zip(decoders[loser].parameters(), decoders[winner].parameters()):
    p1.data = 0.7*p1.data + 0.3*p2.data

# 번식: 승자가 자식 (패자 교체)
for i in range(min(len(engines[loser].cells), len(engines[winner].cells))):
    engines[loser].cells[i].hidden = engines[winner].cells[i].hidden.clone()
    engines[loser].cells[i].hidden += torch.randn_like(engines[loser].cells[i].hidden)*0.1
```

## 핵심 발견

- **경쟁+협력+번식 3단계**가 자연선택의 완전한 구현
- 패자만 교체(middle은 유지)하여 상위 2/3이 보존됨 -- 점진적 진화
- decoder 교육(30%)과 세포 복사가 동시에 일어남 -- 지식과 상태 모두 이식
- 0.1 noise = 10% 변이율: 승자의 복사본이 아니라 변이된 후손
- generations 수가 높을수록 많은 세대를 거친 진화 -- 50 step 간격으로 세대 교체
