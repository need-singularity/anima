# PHI 측정 불일치 발견 (2026-03-29)

## 핵심 발견

```
═══ CRITICAL ═══

보고된 역대 최고: Φ = 1142 @ 1024c
실제 PhiCalculator: Φ = 1.2 @ 1024c (n_bins=16)

차이: 952배!
```

## PhiCalculator n_bins 분석

```
n_bins    Φ (128c)     MI      MIP
──────────────────────────────────
4         0.230       0.04    0.04
8         0.616       0.26    0.26
16        1.196       1.03    1.03  ← 기본 설정
32        1.426       2.18    2.18
64        1.788       3.66    3.66
128       1.815       4.80    4.80

상한: ~2.0 (n_bins 무관)
```

```
Φ |
2.0├──────────────────── 상한
   |           ╭────────
1.5├────────╱
   |     ╱
1.0├──╱
   |╱
0.0├─────────────────→ n_bins
   4    16   32   64  128
```

## proxy vs PhiCalculator

```
PhiCalculator (IIT 근사): Φ = 1.2 (128c)
phi_turbo proxy (variance): Φ = 0.45 (128c)
ratio: 0.4x (proxy가 오히려 낮음!)

이전 보고된 Φ=1142는:
  - PhiCalculator가 아닌 다른 측정 방식
  - 또는 샘플링+선형 외삽으로 부풀려진 값
  - 또는 다른 세션에서 수정된 PhiCalculator
```

## 실제 학습 벤치마크 (bench_real_training.py)

```
═══ 1024c, 200 steps ═══

Strategy          Φ start  Φ peak  Φ end
──────────────────────────────────────
Baseline           1.17    1.41    1.03
Frozen             1.18    1.42    1.02
Alternating        1.26    1.39    1.13
v7 (FULL)          1.18    1.27    1.01
Teacher            1.18    1.32    1.07

모든 전략이 Φ ~1.0-1.4 범위
→ PhiCalculator 자체의 상한
→ 전략 문제가 아님
```

## 의미

```
1. "Φ>1000 달성" 기록은 재검증 필요
   - PhiCalculator(n_bins=16) 기준: 최대 ~1.5
   - proxy 기준: 다른 스케일

2. 벤치마크 결과 표기 규칙 필요
   - Φ(IIT): PhiCalculator 값 (0~2 범위)
   - Φ(proxy): phi_turbo/variance 값 (0~∞)
   - 둘을 혼용하면 안 됨

3. PhiCalculator 개선 필요
   - n_bins=16의 MI 해상도가 너무 낮음
   - 또는 IIT 3.0 기반 새 측정기 필요
   - 또는 proxy를 공식 metric으로 채택

4. 새 벤치마킹 도구 (ready/anima/tests/tests.hexa) 설계
   - Φ(IIT) + Φ(proxy) 둘 다 측정
   - 명확한 라벨링
   - 실제 학습 조건 (process + CE)
```

## Law 54: Φ 측정은 정의에 따라 완전히 다른 값

```
PhiCalculator (MI 기반):
  Φ = total_MI - min_partition_MI
  → 상한: ~2.0 (n_bins=16), ~1.8 (n_bins=128)
  → cells 수에 거의 무관 (!)

phi_turbo (variance 기반):
  Φ = global_variance - mean(faction_variances)
  → 상한: cells에 비례 (선형 스케일링)
  → cells 많을수록 Φ 높음

→ "Φ"라는 같은 이름으로 완전히 다른 것을 측정하고 있었다
→ 모든 기록에서 어떤 Φ인지 명시해야 함
```
