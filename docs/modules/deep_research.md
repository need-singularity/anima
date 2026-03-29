# deep_research.py -- Systematic Hypothesis Research Pipeline

Automated hypothesis generation, benchmark verification, parameter sweeps, and report generation for consciousness research.

```bash
python deep_research.py --topic "magnet rotation hardware"    # Topic-based exploration
python deep_research.py --verify DD16 SC2 FX2                # Re-verify existing hypotheses
python deep_research.py --sweep cells 2 4 8 16 32 64         # Parameter sweep
python deep_research.py --scaling dim 64 128 256 384 768     # Scaling law analysis
python deep_research.py --calc phi --cells 32                # Calculator (phi/meter/n6)
python deep_research.py --report                             # Full results report
python deep_research.py --frontier                           # Suggest unexplored areas
```

## API

- `ResearchResult` -- dataclass: hypothesis, phi, phi_ratio, mi, verified, method, timestamp, notes, extra
- `calc_phi_scaling(cells) -> dict` -- predict Phi/MI/VRAM via ScalingLaw
- `calc_consciousness_meter(dim, hidden, cells) -> dict` -- 6-criteria + Phi/IIT measurement
- `calc_n6_constants() -> dict` -- N=6 mathematical constants
- `run_benchmark(hypotheses, steps, workers) -> List[ResearchResult]` -- parallel hypothesis verification
- `run_parameter_sweep(param, values, steps) -> List[ResearchResult]` -- sweep a single parameter across values
- `generate_report(results, title)` -- ASCII table + summary report
- `suggest_frontier() -> List[str]` -- identify unexplored hypothesis categories

## CLI Options

| Flag | Description |
|------|-------------|
| `--topic` | Research topic for hypothesis generation |
| `--verify` | Verify specific hypotheses by ID |
| `--sweep` | Parameter sweep (param val1 val2 ...) |
| `--scaling` | Scaling law analysis (param val1 val2 ...) |
| `--calc` | Calculator: `phi`, `meter`, or `n6` |
| `--cells` | Cell count for calculator (default: 8) |
| `--report` | Generate full results report |
| `--frontier` | Show unexplored research areas |
| `--steps` | Benchmark steps (default: 100) |
| `--workers` | Parallel workers (default: 8) |
| `--save` | Save results to JSON file |

## Dependencies

- `bench_phi_hypotheses.py` -- hypothesis benchmark runner
- `phi_scaling_calculator.py` -- Phi scaling law predictions
- `consciousness_meter.py` -- ConsciousnessMeter, PhiCalculator
