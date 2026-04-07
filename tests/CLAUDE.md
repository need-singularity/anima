# tests/

## Purpose
Integration and unit tests for Anima modules.

## File Naming
- `test_{module_name}.py` — Tests for specific module
- Tests use pytest framework

## Running
```bash
pytest tests/                          # Run all tests
pytest tests/test_memory_store.py      # Run specific test
```

## Troubleshooting Rules
- Bug fixes must include inline comments: `# FIX(YYYY-MM-DD): root cause + solution`
- Non-deterministic tests: always pin `torch.manual_seed()` for CI stability

## Troubleshooting Log

| Date | Test | Root Cause | Fix |
|------|------|-----------|-----|
| 2026-04-01 | `test_cells_grow_beyond_initial` | seed 미고정 + 100 step 부족 → adaptive threshold(mean+1.5*std) 3연속 초과 확률 낮아 CI flaky | `torch.manual_seed(42)` + step 200으로 증가 |

## Parent Rules
See /CLAUDE.md for full project conventions.
