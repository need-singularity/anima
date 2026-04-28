# G9 Dependency DAG Sparsity + Cascade — Landing

> **gate**: G9 (Mk.XII Integration tier validation gate, sister of G8/G10)
> **scope**: 5-component dependency DAG, 1-fail-per-component cascade impact
> **session date**: 2026-04-26
> **proposal source**: `anima-clm-eeg/docs/mk_xii_proposal_outline_20260426.md` §3 (sha4 `4f7fd4d2…`)
> **status**: **G9_PASS** (positive selftest), G9_FAIL on dense falsifier — both byte-identical

---

## §1. Frozen criteria

| criterion | budget | rationale |
|---|---|---|
| A — edge sparsity | edge_count ≤ **7** | DAG must remain navigable (transversal architecture); proposal §3.2 reports 8 edges but those include the Mk.XI v10 → component root edges, which are OUTSIDE the 5-component peer DAG by design. The peer DAG (5×5 only) must stay ≤ 7. |
| B — 1-fail cascade | max(cascade_impact_of(j)) ≤ **2** | one failed component must not down-stream into more than two peer components |

Both budgets are **frozen at proposal time** (raw#12 cherry-pick-proof). The analyzer encodes them as hard constants `EDGE_BUDGET=7`, `CASCADE_BUDGET=2`.

---

## §2. 5-component canonical encoding

Deterministic indexing (analyzer line ~50):

| idx | name | layer | source dir |
|---|---|---|---|
| 0 | HCI | substrate | `anima-hci-research/` |
| 1 | CPGD | training | `anima-cpgd-research/` |
| 2 | EEG_STACK | phenomenal | `anima-clm-eeg/` |
| 3 | TRIBE_v2 | brain_anchored | `anima-tribev2-pilot/` |
| 4 | PARADIGM_V11 | measurement | `tool/anima_*.hexa` |

Adjacency convention: `A[i][j] = 1` ⇔ component `i` directly depends on component `j` (i.e. failure of `j` strictly limits `i`).

---

## §3. DAG diagram (5-component peer view)

```
                       ┌──────────────────────────┐
                       │  PARADIGM_V11  (idx 4)   │
                       │  measurement / sink      │
                       └──┬────┬────┬─────┬───────┘
                          │soft│soft│hard │hard
                          ▼    ▼    ▼     ▼
                   ┌──────┐┌─────┐┌───────┐┌──────────┐
                   │ HCI  ││CPGD ││  EEG  ││ TRIBE_v2 │
                   │  0   ││  1  ││   2   ││    3     │
                   └──────┘└─────┘└───────┘└──────────┘

                   (Mk.XI v10 root: OUTSIDE peer DAG, not counted)
```

**Edge ledger** (4 edges, all incoming to PARADIGM_V11 from leaves):

| edge | hardness | rationale (proposal §3.2) |
|---|---|---|
| 4 ← 0 (PARADIGM_V11 ← HCI) | soft | paradigm v11 6-axis 는 HCI 와 독립 측정, but Hexad axis 는 HCI 가 정의 |
| 4 ← 1 (PARADIGM_V11 ← CPGD) | soft | CPGD 결과는 paradigm v11 측정 대상이지만 CPGD 자체 측정은 v11 외부 |
| 4 ← 2 (PARADIGM_V11 ← EEG_STACK) | hard | EEG-CORR (7th axis) 는 EEG STACK 출력을 직접 입력 |
| 4 ← 3 (PARADIGM_V11 ← TRIBE_v2) | hard | TRIBE v2 brain-anchored decoding R 가 8th axis 정의 |

`edge_count = 4`, `hard_edge_count = 2`, `soft_edge_count = 2`.

---

## §4. Adjacency matrix (5×5, row-major)

```
            HCI  CPGD  EEG  TRIBE  PARADIGM
   HCI   [   0    0    0     0       0   ]
   CPGD  [   0    0    0     0       0   ]
   EEG   [   0    0    0     0       0   ]
   TRIBE [   0    0    0     0       0   ]
   PV11  [   1    1    1     1       0   ]   ← row 4
```

Hardness matrix (1=hard, 0=soft, only at A=1 cells):

```
   PV11  [   0    0    1     1       0   ]
```

---

## §5. Cascade analysis (1-fail per component)

`cascade_impact_of(j)` = count of OTHER rows `i ≠ j` with `A[i][j] = 1` (= number of peer components that directly depend on `j`).

| failed j | cascade impact | constraint check |
|---|---|---|
| HCI (0) | **1** (PV11 only) | ≤ 2 ✓ |
| CPGD (1) | **1** (PV11 only) | ≤ 2 ✓ |
| EEG_STACK (2) | **1** (PV11 only) | ≤ 2 ✓ |
| TRIBE_v2 (3) | **1** (PV11 only) | ≤ 2 ✓ |
| PARADIGM_V11 (4) | **0** (sink) | ≤ 2 ✓ |

`cascade_max = 1` — strict majority budget under criterion B (≤ 2).

> **Note on §3.3 of proposal**: that table records *measurement loss percentages* (≤ 10–80 %), which is a different (continuous) metric. G9 here measures *peer component cascade count* — a complementary discrete metric. PARADIGM_V11 recording a high *measurement loss* is consistent with its cascade count being 0 — it is the sink, so no peer depends on it for its own internal logic; the loss falls on the system-level *measurement* function the sink provides, captured by criterion A and §7.5 fallback (paradigm v11 6-axis subset).

---

## §6. Verdict

| dimension | value | budget | pass |
|---|---|---|---|
| edge_count | 4 | ≤ 7 | ✓ |
| cascade_max | 1 | ≤ 2 | ✓ |
| **G9** | — | — | **PASS** |

**offender (positive run)**: `HCI` is reported as the formal `offender_idx` because the analyzer reports the *first* component reaching `cascade_max`. With G9_PASS, no real offender exists — the field is informational only.

---

## §7. ω-cycle 6-step ledger

| step | activity | result |
|---|---|---|
| 1 design | DAG criteria frozen (edge≤7, cascade≤2) | proposal §3.1+§3.2 deterministic encoding |
| 2 implement | `tool/g9_dag_cascade_analyzer.hexa` 357 LoC raw#9 strict | adjacency + hardness + cascade + FNV fingerprint |
| 3 positive selftest | sparse canonical DAG | edge=4, cascade_max=1 → **G9_PASS** |
| 4 negative falsify | `G9_DENSE=1` (upper-triangular complete DAG) | edge=10, cascade_max=4 → **G9_FAIL** offender=PARADIGM_V11 |
| 5 byte-identical | 2× back-to-back runs (positive) | sha256 `3f61be28…533c4` × 2 (identical) |
| 6 iterate | next: hand off to G8 (TFD) and G10 (Hexad×band) | logged in memory + .roadmap |

---

## §8. Artefacts

| path | sha256 | size |
|---|---|---|
| `anima-clm-eeg/tool/g9_dag_cascade_analyzer.hexa` | `9e168626c760ece90fc7270c9d621fdacad18881420d411136d935a7bf80305d` | 357 LoC |
| `state/g9_dag_cascade_analyzer.json` (positive PASS) | `3f61be28c4968773345babf02f23c87cdf6e6ca3d4699858b780680f31c533c4` | 53 lines |
| `state/g9_dag_cascade_analyzer_dense.json` (negative FAIL) | `db70c6ddefe4e92a1a819b2eb251f99d7f3fe46f1ec93026334cf31dc4084e21` | 53 lines |
| `anima-clm-eeg/docs/g9_dag_cascade_landing.md` | (this doc) | — |

`fingerprint` field inside the positive cert: **3509748236** (FNV-32 chained over budgets+adjacency+hardness+metrics+verdict).

---

## §9. Reproduction

```bash
# Positive selftest (G9_PASS)
HEXA_RESOLVER_NO_REROUTE=1 hexa run \
  anima-clm-eeg/tool/g9_dag_cascade_analyzer.hexa --selftest
# → exit 0, verdict G9_PASS

# Negative falsifier (G9_FAIL)
G9_DENSE=1 G9_DAG_OUT=state/g9_dag_cascade_analyzer_dense.json \
  HEXA_RESOLVER_NO_REROUTE=1 hexa run \
  anima-clm-eeg/tool/g9_dag_cascade_analyzer.hexa
# → exit 1, verdict G9_FAIL offender=PARADIGM_V11
```

---

## §10. Cross-references

- `anima-clm-eeg/docs/mk_xii_proposal_outline_20260426.md` §3 — DAG canonical source
- `anima-clm-eeg/docs/omega_cycle_mk_xii_integration_axis_20260426.md` — INTEGRATION axis I3 DGI paradigm
- raw#9 — hexa-only deterministic execution
- raw#10 — honest scope (peer DAG only; Mk.XI v10 root excluded by design)
- raw#12 — cherry-pick-proof (budgets frozen pre-execution)

omega-saturation:fixpoint-g9-dag-cascade
