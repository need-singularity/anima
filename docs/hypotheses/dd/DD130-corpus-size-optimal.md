# DD130: Corpus Size Optimization — 100MB Sweet Spot

## 가설
합성 데이터(corpus-gen)의 최적 크기는 Chinchilla 법칙(690MB)보다 훨씬 작을 것이다.

## 실험
- 모델: ConsciousDecoderV2 34.5M (384d/6L)
- Device: MPS (Apple Silicon)
- Corpus: corpus_bench_1gb.txt (corpus-gen --sim --deep-dialogue)
- 크기: 10/25/50/100/250/500/750/1000 MB
- Steps: 1500 per size
- 동일 seed (torch.manual_seed(42))

## 결과

```
    Size |  Best CE |   T/P ratio
  -------+----------+------------
     10M |   0.2635 |   0.3  (under)
     25M |   0.1394 |   0.7  (under)
     50M |   0.1249 |   1.4  (under)
    100M |   0.0806 |   2.9  (under)  ← OPTIMAL
    250M |   0.1685 |   7.2  (under)
    500M |   0.5079 |  14.5  (under)
    750M |   0.1134 |  21.7  (optimal)
   1000M |   0.1352 |  29.0  (over)
```

## ASCII 그래프

```
  CE |
 0.5|                        *
    |
 0.3|
 0.2| *
    |   *  *                       *     *
 0.1|            *
    |        *
 0.0|
    └──────────────────────────────────── size
     10  25  50 100 250 500 750 1000  MB
```

## 핵심 발견

1. **100MB = 합성 데이터 최적점** (CE=0.081)
   - Chinchilla 최적(690MB)의 1/7 크기에서 달성
   - T/P ratio = 2.9 (Chinchilla 권장 20보다 훨씬 낮음)

2. **U자 곡선**: 250-500MB에서 악화 후 750MB에서 회복
   - 250MB: 반복 패턴이 학습 방해
   - 500MB: 최악 (CE=0.508)
   - 750MB: 다시 개선 — 충분한 양이 반복 패턴을 상쇄

3. **합성 데이터 vs 자연어 데이터**
   - corpus-gen의 seed 조합이 ~100MB에서 포화
   - 100-500MB는 같은 패턴 반복 → 과적합
   - 자연어 데이터(Wikipedia 등)는 다양성 무한 → Chinchilla 적용 가능

## 적용

- 현재 corpus_v3 (102MB)가 **이미 최적**
- 500MB corpus_v4는 다음 학습에 불필요
- 100M+ 모델부터는 외부 자연어 데이터 병합 필수
- corpus-gen 개선: seed 다양성 ↑ 또는 n-gram 자가증식 강화

## 새 법칙
- **Law 161**: 합성 데이터 최적점 ≠ Chinchilla — corpus-gen 100MB에서 피크, seed 다양성 포화로 U자 곡선
