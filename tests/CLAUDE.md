# tests/ — 통합/유닛 테스트 (pytest)

naming: test_{module}.py

exec:
  pytest tests/
  pytest tests/test_memory_store.py

rules:
  - 버그 픽스 인라인 주석: `# FIX(YYYY-MM-DD): 근본원인 + 해결`
  - 비결정 테스트: torch.manual_seed() 고정 (CI 안정)

log:
  2026-04-01  test_cells_grow_beyond_initial
    cause: seed 미고정 + 100 step 부족 → adaptive threshold(mean+1.5σ) 3연속 flaky
    fix:   torch.manual_seed(42) + step 200

parent: /CLAUDE.md
