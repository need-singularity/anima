# bench/ — 가설 벤치마크

metrics: Φ(IIT), Φ(proxy), CE

naming:
  bench_{domain}_engines.py   도메인 엔진 (algebra/evolution/physics ...)
  bench_{name}_LEGACY.py      폐기 (Φ proxy/IIT 혼동기)
  bench_v8_*.py               V8 아키텍처
  bench_trinity*.py           Trinity/Hexad

canonical: ready/anima/tests/tests.hexa (dual Φ, CLAUDE.md 참조)

exec:
  python bench/bench_algebra_engines.py
  python ready/anima/tests/tests.hexa --verify

parent: /CLAUDE.md
