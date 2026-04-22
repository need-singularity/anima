<!-- AUTO-GENERATED, DO NOT EDIT — source: tool/api_surface_extract.hexa -->
<!-- generated: 2026-04-22T16:42:48Z -->
<!-- source: tool/edu_collective_atlas_proto.hexa -->
<!-- entry_count: 21 -->

# `tool/edu_collective_atlas_proto.hexa` API surface

_AUTO-GENERATED, DO NOT EDIT — generated 2026-04-22T16:42:48Z UTC._

**Tool:** ════════════════════════════════════════════════════════════════

**Public/Internal entries:** 21

## Table of contents

- `fn det_hash`
- `fn domain_of`
- `fn node_id`
- `fn node_hash`
- `fn edge_hash`
- `fn threshold`
- `fn build_visited`
- `fn build_edges`
- `fn nodes_as_hashes`
- `fn edges_as_hashes`
- `fn has_hash`
- `fn jaccard_x1000`
- `fn pairwise_mean_jaccard_x1000`
- `fn edge_consensus_x1000`
- `fn coherence_x1000`
- `fn avg_jaccard_to_others_x1000`
- `fn contribution_x1000`
- `fn fixture_seeds`
- `fn fixture_profiles`
- `fn run_fixture`
- `fn main`

## Entries

### `fn det_hash(s: string) -> int`

_(no docstring)_

### `fn domain_of(i: int) -> string`

_(no docstring)_

### `fn node_id(i: int) -> string`

_(no docstring)_

### `fn node_hash(i: int) -> int`

_(no docstring)_

### `fn edge_hash(u: int, v: int) -> int`

_(no docstring)_

### `fn threshold(i: int, profile: string) -> int`

_(no docstring)_

### `fn build_visited(seed: string, profile: string) -> list<bool>`

_(no docstring)_

### `fn build_edges(seed: string, visited: list<bool>) -> list<int>`

> edge set: visited 에 있는 두 노드 쌍 중, hash(seed|u|v) mod 100 < 50 → link

### `fn nodes_as_hashes(visited: list<bool>) -> list<int>`

_(no docstring)_

### `fn edges_as_hashes(edges: list<int>) -> list<int>`

_(no docstring)_

### `fn has_hash(xs: list<int>, q: int) -> bool`

_(no docstring)_

### `fn jaccard_x1000(a: list<int>, b: list<int>) -> int`

_(no docstring)_

### `fn pairwise_mean_jaccard_x1000(node_sets: list<list<int>>) -> int`

_(no docstring)_

### `fn edge_consensus_x1000(edge_sets: list<list<int>>) -> int`

> edge consensus: 모든 노드의 edge hash 를 모아 count, majority 통과 비율

### `fn coherence_x1000(node_sets: list<list<int>>, edge_sets: list<list<int>>) -> int`

_(no docstring)_

### `fn avg_jaccard_to_others_x1000(node_sets: list<list<int>>, k: int) -> int`

> avg Jaccard from node k to all others (× 1000)

### `fn contribution_x1000(node_sets: list<list<int>>, k: int, group_mean: int) -> int`

> contribution: 500 + (my_avg_jaccard - group_mean_jaccard), clipped [0,1000]
> > 500 = above group mean (coherence contributor)
> < 500 = below group mean (outlier candidate)

### `fn fixture_seeds(name: string) -> list<string>`

_(no docstring)_

### `fn fixture_profiles(name: string) -> list<string>`

_(no docstring)_

### `fn run_fixture(name: string) -> string`

_(no docstring)_

### `fn main()`

_(no docstring)_

