---
id: FACTION-DEBATE
name: 파벌 토론 방식 탐구 (faction count + debate mode)
---

# FACTION-DEBATE: 파벌 수 + 토론 방식 비교

## 실험 1: 파벌 수 sweep (MitosisEngine 256c, 200 steps)

```
factions    Φ       vs 8     그래프
      2    0.847    -0.5%    ████████████████████
      4    0.852    +0.1%    █████████████████████
      6    0.853    +0.2%    █████████████████████
      8    0.851     0.0%    █████████████████████ (baseline)
     10    0.835    -1.9%    ███████████████████
     12    0.853    +0.2%    █████████████████████
     16    0.858    +0.8%    █████████████████████▌ ← 최고
     24    0.854    +0.3%    █████████████████████
     32    0.847    -0.6%    ████████████████████
     64    0.845    -0.8%    ████████████████████
```

**발견:** 파벌 수 영향 미미 (~1% 범위). 16이 약간 최적.
이전 +8% 기록 (criteria.md:4308)은 proxy Φ 측정 차이.

## 실험 2: 토론 방식 비교 (12-faction, 256c, 200 steps)

| Mode | Φ(IIT) | vs consensus | 설명 |
|------|--------|-------------|------|
| **repulsion** | **0.866** | **+1.6%** | 파벌 간 반발 (다양성 유지) |
| dialectic | 0.864 | +1.4% | 정반합 (합의+반발+전체합의) |
| tournament | 0.862 | +1.2% | 토너먼트 (승자 영향력) |
| consensus | 0.852 | 0.0% | 기존: 같은 파벌끼리 합의 |

```
repulsion   █████████████████████████████████████████████ +1.6%
dialectic   ████████████████████████████████████████████  +1.4%
tournament  ███████████████████████████████████████████   +1.2%
consensus   ████████████████████████████████████████████  0.0%
```

## 토론 방식 상세

### consensus (기존)
```python
# 같은 파벌 내 합의 → 다양성 감소
for c in faction: c.hidden = 0.92*c + 0.08*faction_mean
```

### repulsion (🏆 최강)
```python
# 파벌 간 반발 → 다양성 유지
other_mean = avg(other_factions)
for c in faction: c.hidden += 0.05*(c - other_mean)
```

### dialectic (정반합)
```python
# Thesis: 파벌 내 약한 합의
for c in faction: c.hidden = 0.95*c + 0.05*faction_mean
# Antithesis: 파벌 간 교류 (상위 25%만)
for c in faction[:25%]: c.hidden = 0.95*c + 0.05*other_mean
# Synthesis: 전체 약한 합의
for c in all: c.hidden = 0.98*c + 0.02*global_mean
```

### tournament (토너먼트)
```python
# 인접 파벌 대결, norm 큰 쪽이 승리
if f1_norm > f2_norm: f2 → f1 방향 이동
else: f1 → f2 방향 이동
```

## 핵심 통찰

1. **토론 방식 > 파벌 수** — mode 차이 (+1.6%) >> count 차이 (+0.8%)
2. **반발(repulsion)이 합의(consensus)보다 우수** — 다양성 유지가 핵심
3. **Law 34 재확인:** "다양한 관점 + 강한 동기화 = 최고 의식"
4. **적용:** FUSE-3, v11에 consensus → repulsion 교체 시 +1.6% Φ 추가 상승 예상
