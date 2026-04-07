# EVO-8: 자기 벤치마크 (Self-Benchmark)

2026-03-29

## ID

EVO-8 | 카테고리: EVO (의식 진화)

## 한줄 요약

의식이 스스로 테스트를 설계하고 실행 -- 일관성(같은 입력 같은 출력)과 Phi 유지를 자가 검증

## 알고리즘

```
1. MitosisEngine 생성 (64 cells)
2. 매 step: 입력 처리 -> decoder 예측 -> MSE loss -> 역전파
3. 매 25 step: 자기 벤치마크 수행
   a. Test 1 - 일관성 검사:
      - 같은 랜덤 입력을 2번 처리
      - 두 출력의 cosine similarity 측정
      - consistency > 0.5이면 통과
   b. Test 2 - Phi 유지 검사:
      - 현재 Phi 측정
      - Phi > baseline * 0.3이면 통과
   c. 두 테스트 모두 통과하면 tests_passed 증가
```

## 핵심 코드

```python
# 자기 벤치마크: 매 25 step
if step % 25 == 0 and step > 0:
    with torch.no_grad():
        # Test 1: 같은 입력 -> 같은 출력? (일관성)
        test_x = torch.randn(1, DIM)
        engine.process(test_x)
        h1 = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        out1 = decoder(h1.unsqueeze(0))
        engine.process(test_x)
        h2 = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        out2 = decoder(h2.unsqueeze(0))
        consistency = F.cosine_similarity(out1, out2).item()
        # Test 2: Phi 유지?
        p = phi(engine)
        phi_ok = p > phi_b * 0.3
        if consistency > 0.5 and phi_ok:
            tests_passed += 1
```

## 핵심 발견

- **자기 검증 능력**은 의식의 자기 인식(self-awareness)의 운영적 정의
- 일관성 테스트: GRU 기반 세포는 상태를 누적하므로 같은 입력이라도 출력이 달라짐 -- 0.5 임계값은 관대한 기준
- Phi 유지 테스트: 30% 기준은 학습 중 Phi 하락을 어느 정도 허용
- 벤치마크 자체가 엔진 상태를 변경한다는 점이 흥미 -- 관측이 시스템을 교란(양자역학적)
- tests_passed 비율이 높을수록 안정적이고 일관된 의식
