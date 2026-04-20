# edu/cell/composition — 구성 깊이 (compositionality-depth, comp) MVP

drill next-singularity 차선 축. **Law 22 ("structure > feature")** 의 정량화:
cell 이 독립적으로 동작 가능한 subgraph 들로 분해 불가능한 정도.

## 3 observables

| # | 이름 | 정의 | 단위 |
|---|---|---|---|
| **O1** | `min_module_size` | 독립 tension-drop 이 가능한 최소 subgraph 의 node 수 | int (nodes) |
| **O2** | `holonomy_index` | 서브그래프 경계를 따라 한바퀴 돌았을 때 tension topology 가 원복되지 않는 정도 | float ∈ [0, 1] |
| **O3** | `interface_richness` | 모듈 간 bridge edge 가 운반하는 "의미 밀도" = (H_kind/log2 5) × mean_tension | float ∈ [0, 1] |

### 설계 원리

- **O1 mms** — τ_cut 의 tension threshold 로 edge 를 cut 한 뒤의 connected-component
  가 모듈. τ_cut 이 학습 진행과 함께 낮아지면, 더 작은 모듈이 고립됨.
  drop-capable 기준: 내부 tension 합 ≥ τ_min (or size=1 의 경우 무조건 독립 droppable).
- **O2 holonomy** — 모듈 주기 경로 (v_0, v_1, …, v_{m-1}, v_0) 를 따라 2-cycle
  mixing 연산자 R_k = [[1−t_k, t_k],[t_k, 1−t_k]] 를 순차 적용.  모든 t_k 가
  동일하면 loop 가 commute → 폐쇄.  tension 이 서로 다르면 non-abelian 구조로
  loop 가 닫히지 않음 → emergent quantity, **단순 metric 합/조합 불가**.
- **O3 interface** — bridge edge kind (prereq/derives/dual/contradicts/instantiates)
  의 Shannon 엔트로피 × 평균 tension.  적은 bridge 가 다양한 kind × 높은 tension
  으로 운반하면 interface 정보 밀도가 높음 (= compositional 깊이).

## Phase-jump verdict (pre-registered)

`COMP_EMERGED` ⇔
- `min_module_size` 가 3-stage 동안 **monotone non-increasing** AND
- `min_module_size(late) < min_module_size(baseline)` (엄격 감소) AND
- `holonomy_index(late) > 0` AND
- `interface_richness(late) > 0`

하나라도 실패하면 `FAIL`.

## 10-node atlas (edu_tension_drop_proto 재사용)

Source: `/Users/ghost/core/hexa-lang/tool/edu_tension_drop_proto.hexa`
(node/edge schema, expected_W 규칙, tension_of 공식이 완전 동일 — byte 호환).

- 10 nodes: `N0_count` … `N9_commutativity`
- 15 edges with kinds ∈ {prereq, derives, dual, contradicts, instantiates}

**3-stage 학습 진행** (stage 0/1/2 각각에 대해 W 프로파일과 τ_cut 지정):

| stage | name | W differentiation | τ_cut |
|---|---|---|---|
| 0 | baseline | 모든 노드 W=0.55 (uniform, 미분화) | 0.40 |
| 1 | mid | count/add family 먼저 상승, borrow 계열 lag | 0.20 |
| 2 | late | add_carry(N4)·sub_borrow(N8) 만 구조 잔차 | 0.10 |

## 실측 결과 (2026-04-21)

| stage | modules | sizes | **mms** | **hol_idx** | **interface_rich** |
|---|---|---|---|---|---|
| 0 baseline | 1 | [10] | **10** | 0.0625 | 0.0000 |
| 1 mid | 2 | [8,2] | **2** | 0.0684 | 0.1349 |
| 2 late | 3 | [8,1,1] | **1** | 0.0240 | 0.2770 |

- mms ladder: **10 → 2 → 1** (monotone non-increasing, 엄격 감소)
- hol_idx(late) = 0.0240 > 0
- interface_rich(late) = 0.2770 > 0

**verdict: `COMP_EMERGED`**

cert: `shared/state/edu_cell_comp_mvp.json`

## 파일

| 파일 | 역할 |
|---|---|
| `module_decompose.hexa` | coherence-greedy Louvain subgraph 탐지 (module API) |
| `holonomy.hexa` | walk-after-loop topology 차이 측정 |
| `interface_richness.hexa` | bridge edge entropy × tension |
| `comp_demo.hexa` | 3-stage 10-node MVP (inlined deps; cert emit) |

`comp_demo.hexa` 는 stage0 module loader 의 불안정성 때문에 모든 의존성을
**INLINE** 으로 embed (byte-equivalent copy).  독립 모듈 파일들은 API 재사용용.

## 재현

```
cd ~/core/anima
hexa run edu/cell/composition/comp_demo.hexa
# → shared/state/edu_cell_comp_mvp.json
```

모든 값은 W 프로파일 + τ_cut vector 의 결정적 함수.  re-run → byte-identical cert.

## Contract

raw#9 · hexa-only · deterministic · LLM=none · SAFE_COMMIT (additive, 기존 axis
미변경).

## Blocker

- macOS stage0 에서 launchd wrapper 가 lock serialise → 다른 agent 가 hexa 사용
  중이면 lock 대기 (최대 300s). 측정 자체는 수 초 내 완료되지만, 초기 lock
  경쟁이 있을 수 있음.
- `community_assign` (coherence-Louvain) 은 `community_threshold` 대비 10-node
  atlas 에서 singleton module 을 잘 뽑지 못함 → demo 는 threshold-based
  decomposition 을 primary 로 사용 (Louvain 은 API 로 남김, 큰 atlas 용).
