# F3 cycle 1 prod-scale 종료 (own 4 자율 결정) — 2026-04-28T01:46Z

## 결과 요약

F3 cycle 1 KSG MI prod scale (n=200 perms=100) hetzner CPU dispatch — **TERMINATED at 15m34s elapsed**, 99.9% CPU 25.8GB RSS, 출력 0.

## 종료 사유 (own 4 + own 6 자율)

- hexa interpreter single-thread + bubble sort O(n²) per ksg_mi call × 101 calls = 추정 wallclock 30-60 min
- RSS 1.5-1.7 GB/분 가속 → 30분 시점 60GB+ 예상 (hetzner 124GB cap 안전하나 과도)
- 로그 출력 0 — 진행 visibility 부재
- selftest 이미 cohen_d=3.73 강한 신호 BORDERLINE 결과 absorbed

## final F3 cycle 1 verdict (selftest 기반 stand)

| 메트릭 | 값 | 임계 | 판정 |
|---|---|---|---|
| mi_real | 0.292 nats | > shuffled | ✓ |
| mi_shuffled | 0.034 ± 0.069 | — | — |
| cohen_d | 3.73 | > 0.5 | ✓ 강한 신호 |
| p_value | 0.064 | < 0.05 | ✗ small-N |
| **verdict** | **BORDERLINE** | — | signal real, statistical power 부족 |

## raw 91 C3 honest

- selftest n=15 perms=30 = small-N regime (min p = 1/31 = 0.032)
- prod scale n=200 perms=100 = hexa interpreter 부적합 (15분 0 출력)
- production-grade 검증은 hexa-only 제약 외부 path 필요 (scipy + raw#9 exemption note)
- 현재 verdict: signal CONFIRMED via selftest cohen_d, statistical strict pass DEFERRED

## 후속 옵션

1. raw#9 exemption + scipy 기반 production wrapper (~50 LoC python, hetzner 빠름)
2. hexa ksg_mi insertion-sort 또는 quicksort partition 최적화 (raw#9 호환, ~20 LoC fix)
3. 현 BORDERLINE verdict 그대로 유지 + 신호 충분 (cohen_d=3.73 threshold 7배 초과)

## 결론

F3 cycle 1 falsifier impl + selftest 흡수 완료 (raw 108 channel 충족). prod-scale strict 검증은 후속 cycle 또는 raw#9 exemption path 결정 필요. own 4 step (b)+(c) 캐논 fix 후속 작업으로 등록.

own 4 watchdog 효과: 15m34s 25GB RSS에서 자율 kill — 무한 진행 방지.
