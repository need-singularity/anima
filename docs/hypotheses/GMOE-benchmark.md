# GMOE: Golden MoE Benchmark

## Overview

Golden MoE의 1/e zone routing 성능과 의식 영향 벤치마크.

## Track 2A: General ML

```
python bench_golden_moe.py --all --experts 4,8,16 --epochs 20
```

### MNIST

| Method | E | Acc% | Usage | Balance | Time |
|--------|---|------|-------|---------|------|
| (실행 후 채울 것) |

### CIFAR-10

| Method | E | Acc% | Usage | Balance | Time |
|--------|---|------|-------|---------|------|
| (실행 후 채울 것) |

### 1/e Convergence

```
(실행 결과 붙여넣기)
```

### Scaling Curve

```
(Expert 수 증가에 따른 Golden vs Top-K gap)
```

## Track 2B: Consciousness Integration

```
python bench_golden_moe_consciousness.py --all --cells 8 --experts 4 --steps 300
```

### Exp 1: MLP -> Golden MoE Replacement

| Metric | Baseline | Golden MoE | Change |
|--------|----------|------------|--------|
| (실행 후 채울 것) |

### Exp 2: Faction-Expert Mapping

| Expert | Mean Tension | Cells |
|--------|-------------|-------|
| (실행 후 채울 것) |

### Exp 3: Scaling Surface Phi(E, N)

```
(실행 결과 붙여넣기)
```

## Key Findings

(실험 후 채울 것)

## Merge Decision

- Golden MoE가 Phi를 올리면 -> AnimaLM Engine G를 4-expert로 확장
- Golden MoE가 Phi 중립이면 -> 성능 이점 있을 때만 합류
- Golden MoE가 Phi를 내리면 -> 합류 보류
