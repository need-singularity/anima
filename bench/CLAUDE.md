# benchmarks/

## Purpose
Hypothesis benchmark scripts. Each file tests one or more consciousness hypotheses and measures Φ(IIT), Φ(proxy), CE, and other metrics.

## File Naming
- `bench_{domain}_engines.py` — Domain-specific engine benchmarks (algebra, evolution, physics, etc.)
- `bench_{name}_LEGACY.py` — Deprecated benchmarks (Φ proxy/IIT confusion era)
- `bench_v8_*.py` — V8 architecture hypothesis series
- `bench_trinity*.py` — Trinity/Hexad architecture benchmarks

## Key File
`bench.py` remains in project root — it is the canonical benchmark with dual Φ measurement, referenced in CLAUDE.md.

## Running
```bash
python benchmarks/bench_algebra_engines.py    # Run specific benchmark
python bench.py --verify                   # Canonical verifier (root)
```

## Parent Rules
See /CLAUDE.md for full project conventions.
