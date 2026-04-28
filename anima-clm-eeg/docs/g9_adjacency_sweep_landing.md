## G9 Adjacency-Axis Sweep — Landing Brief (v1)

**date** 2026-04-26 · **raw#9** · hexa-only · deterministic · LLM=none · $0
**sister tool** `anima-clm-eeg/tool/g9_dag_cascade_analyzer.hexa` (G9 base, edge=4 / cascade_max=1 → PASS)

### Why this exists

`g9_robustness_sweep.hexa`(기존) 는 **hardness axis** 만 뒤집어 측정한다.
analyzer 가 hardness 를 verdict 에 반영하지 않아 trivial 100% — robustness 주장이
**weakest-evidence-link**. 이 도구는 **adjacency axis** 자체에 1-bit-flip
Hamming-1 perturbation 을 가해 G9 verdict 의 진짜 invariance 를 fix 한다.

### Frozen design

- **N=5** 5×5 adjacency, **strict upper-triangle** (i<j, diagonal 제외) 10 positions
- **scenario index → (i,j)** deterministic
  | s | (i,j) | s | (i,j) |
  |---|---|---|---|
  | 0 | (0,1) | 5 | (1,3) |
  | 1 | (0,2) | 6 | (1,4) |
  | 2 | (0,3) | 7 | (2,3) |
  | 3 | (0,4) | 8 | (2,4) |
  | 4 | (1,2) | 9 | (3,4) |
- **baseline** canonical sparse Mk.XII DAG: row 4 cols 0..3 = 1
  → edge_count=4, cascade_max=1, baseline_pass=1
- **perturbation** baseline + 단일 upper-tri bit ON (Hamming-1, acyclic 보존)
- **G9 frozen criteria** edge_count ≤ 7, cascade_max ≤ 2
- **invariance threshold** ≥ 80% (8+/10) baseline verdict 일치 → ROBUST
- **falsifier** `G9_ADD_ALL=1` → 10 upper-tri bit 동시 ON (edge_count=14, cascade_max=4) → 10/10 FAIL 으로 verdict flip

### Run

Positive selftest:
```
HEXA_RESOLVER_NO_REROUTE=1 \
G9_ADJ_OUT=anima-clm-eeg/state/g9_adjacency_sweep_v1.json \
  hexa run anima-clm-eeg/tool/g9_adjacency_sweep.hexa
```

Negative falsifier:
```
G9_ADD_ALL=1 HEXA_RESOLVER_NO_REROUTE=1 \
G9_ADJ_OUT=anima-clm-eeg/state/g9_adjacency_sweep_v1_negative.json \
  hexa run anima-clm-eeg/tool/g9_adjacency_sweep.hexa
```

### Result (positive, add_all_mode=0)

| field | value |
|---|---|
| baseline_edge_count | 4 |
| baseline_cascade_max | 1 |
| baseline_pass | 1 |
| pass_count | **10 / 10** |
| matching_baseline | **10 / 10** |
| invariance_pct | **100** (threshold 80) |
| robust | **1** |
| verdict | **G9_ADJ_ROBUST** |
| fingerprint | 2769892350 |

per-scenario: 10/10 모두 g9_pass=1, edge_count=5, cascade_max ∈ {1, 2} (cap 2 충족).
- cascade_max=1 인 cells: s=3, 6, 8, 9 (j=4 perturbations — column 4 cascade 추가)
- cascade_max=2 인 cells: s=0, 1, 2, 4, 5, 7 (column 0/1/2/3 추가, 기존 1 + perturbation 1 = 2)

### Result (negative, add_all_mode=1)

| field | value |
|---|---|
| pass_count | **0 / 10** |
| matching_baseline | **0 / 10** |
| invariance_pct | **0** |
| verdict | **G9_ADJ_FRAGILE** |
| fingerprint | 1319834008 |

per-scenario: 10/10 g9_pass=0, edge_count=14 (>7 budget), cascade_max=4 (>2 budget).
falsifier 작동 입증 — sweep tool 이 verdict flip 을 정상 detect.

### Byte-identical re-run

동일 env 로 2회 실행 → JSON sha256 **fb5679efae0f5e5858fca28065e4fda80865d7e324e659df02e1157fd44b1c99** 일치.
fingerprint=2769892350 양 run 동일.

### Verdict

**G9 adjacency-axis ROBUST** — Hamming-1 perturbation 10/10 invariance 100%
(threshold 80% 초과). G9 base (edge=4 cascade=1 PASS) 가 adjacency 축에서
strict upper-tri 단일-bit 추가에 대해 verdict-stable.

**해석**: edge budget 7 / cascade budget 2 가 baseline (edge=4 cascade=1) 으로부터
margin=3 (edge) margin=1 (cascade) 보유. Hamming-1 추가는 worst case +1 each
이므로 cap 미초과 — 즉 ROBUST 결과는 budget 설계의 직접 귀결로 사후
falsifiable. `G9_ADD_ALL` 모드는 budget 양쪽을 동시에 위반시켜
verdict-flip detect 능력을 입증.

### Limits / honest

- 10 scenario 는 strict upper-tri 의 **전수**. Hamming-2 이상 미포함 (cap 30분 한계 내 스코프 제한).
- baseline_cascade_max=1, edge=4 의 margin 이 cap 에 가까울수록 invariance ↓. 다른 baseline (예: row 3 도 dependency 보유) 은 별도 sweep 필요.
- Mk.XI v10 root 외부 design 가정 (sister tool 동일). 5-component 가 fixed.

### Artifacts (sha256)

- `anima-clm-eeg/tool/g9_adjacency_sweep.hexa`
  `30de0715030474977351b7160f51230a065433f8931a96d01d9a37a8374370bd`
- `anima-clm-eeg/state/g9_adjacency_sweep_v1.json` (positive)
  `fb5679efae0f5e5858fca28065e4fda80865d7e324e659df02e1157fd44b1c99`
- `anima-clm-eeg/state/g9_adjacency_sweep_v1_negative.json` (falsifier)
  `ec18fe7931ee16bd6fa8d0408dcfbbebefd66f9eaf1c0ec2660d35c019f6bc08`
