# Anima Memory L2 — Merkle Tree Spec & Prototype (2026-04-25)

> **Goal / 목적**: Lift `.meta2-cert` chain from L1 *linked-list* (O(N) inclusion proof) to **L2 *Merkle tree*** (O(log N) inclusion proof) — closure of the L2 row in `docs/alm_memory_state_persistence_abstraction_20260425.md`.
> **Status / 상태**: prototype VERIFIED on real `.meta2-cert` (N=10) → root `0fc3ba90…3d1edb`, depth=4, proof size=4 hashes per leaf. Selftest 4/4 PASS. Hexa builder (`tool/meta2_merkle_build.hexa`) cross-checked by an independent python verifier — 10/10 inclusion proofs reproduce the root.
> **Cost**: 0 (local cpu, no GPU, no network).
> **POLICY**: raw#9 hexa-only · raw#10 proof-carrying · raw#11 snake_case · raw#15 no-hardcode.

---

## §1. Problem statement / 문제 정의

### EN
The current `.meta2-cert/index.json` chains entries via a single backward pointer:

```
entry[i].prev_index_sha = sha256(canonical(entry[i-1]))
```

This is a **linked list**. Verifying a single entry's inclusion in the canonical history requires walking the chain — **O(N) hashes** — and there is no compact commitment that an external auditor can use to prove a snapshot of the entire registry.

### KR
현재 `.meta2-cert/index.json` 는 단방향 포인터로 entry 를 잇는 **linked list** 구조다. 임의 entry 의 inclusion 을 증명하려면 chain 전체를 따라가야 하므로 O(N) 해시 연산이 필요하고, 외부 auditor 가 전체 registry 의 snapshot 을 한 값으로 commit 받을 방법이 없다. **Merkle tree** 로 lift 하면 inclusion proof 가 O(log N) 로 줄고, 단일 root hash 가 epoch 전체를 commit 한다.

---

## §2. Design / 설계

### 2.1 Tree shape

- **leaves**: one per `index.json.entries[*]`, ordered as in the file.
- **leaf hash**: `sha256( jq -S -c 'del(.current_hash)' <entry-file> )` — same canonical form as `tool/meta2_hashchain_verify.hexa` (sorted keys, compact, `current_hash` excised).
- **padding**: pad up to next power of two by **duplicating the last leaf** (Bitcoin / RFC 6962-lite convention). Padding count is recorded in the root document so verifiers can replay it deterministically.
- **parent hash**: `sha256( left_hex || right_hex )` — concatenation of hex strings, ASCII bytes. Deterministic, easy to reproduce in shell (`echo -n "$L$R" | shasum -a 256`).
- **root**: top-level single hash committing the whole epoch.
- **bounds**: depth = ⌈log₂ N⌉; proof size = depth hashes; verify cost = depth sha256 ops.

### 2.2 Proof format

```jsonc
{
  "leaf_index": <int>,
  "slug": "<entry slug>",
  "file": "<entry filename>",
  "leaf_hash": "<sha256 hex>",
  "proof": [
    { "sibling": "<sha256 hex>", "side": "L" | "R" },
    ...                         // length == depth
  ]
}
```

### 2.3 Verification protocol

```
h ← leaf_hash
for step in proof:
    if step.side == "L":  h ← sha256(step.sibling || h)
    else:                 h ← sha256(h || step.sibling)
assert h == merkle_root
```

### 2.4 Schema

- `state/meta2_merkle_root.json` → `anima.meta2.merkle.root.v1`: root, leaf_count, padded_count, tree_depth, algorithm strings, ts.
- `state/meta2_merkle_proofs.json` → `anima.meta2.merkle.proofs.v1`: per-leaf proofs.

---

## §3. Merkle-ize procedure / 변환 절차

```
INPUT:  .meta2-cert/index.json  (N entries)
OUTPUT: state/meta2_merkle_root.json    (root + meta)
        state/meta2_merkle_proofs.json  (N inclusion proofs)

1. load entries[]                                    # ordered by index.json
2. for each entry e_i:
       leaf_i = sha256(jq -S -c 'del(.current_hash)' e_i.file)
3. pad leaves[] up to next_pow2(N) by duplicating leaves[-1]
4. build levels:
       level_0 = padded leaves
       level_k+1[j] = sha256(level_k[2j].hex || level_k[2j+1].hex)
   stop when len(level)==1  → that is the root.
5. for each leaf i:
       walk from level_0 up; record sibling + side at each level.
6. emit JSON with schema tags above.
7. self-verify: every leaf must reproduce root via its proof.
```

This is a **pure additive** layer over L0/L1 — no existing artifacts mutate. The linked-list chain remains canonical for append; Merkle root is derived **on demand per epoch**. New entries can be folded in by recomputing the root (cheap: O(N log N) total work, dominated by I/O for ~10–10⁴ entries).

---

## §4. Prototype results (real walk, 2026-04-25)

| Field | Value |
|---|---|
| `cert_root` | `.meta2-cert` |
| `leaf_count` | **10** |
| `padded_count` | **6** (10 → next_pow2 = 16) |
| `tree_depth` | **4** |
| `merkle_root` | `0fc3ba903f63cbff4485267be6d1c4be755e4b07d451b624c54efca51d3d1edb` |
| `proof_size_per_leaf` | **4 hashes** (matches ⌈log₂ 16⌉) |

Selftest (`hexa run tool/meta2_merkle_build.hexa --selftest`):

- **T1** 4-leaf perfect tree (depth=2) — PASS, root `bf257e702c8cf344…`
- **T2** 13-leaf padded tree (depth=4, pad=3) — PASS, root `327e983c358039b4…`
- **T3** tamper detection (mutate 1 leaf, proof rejected against original root) — PASS
- **T4** real `.meta2-cert` round-trip (N=10) — PASS, root `0fc3ba903f63cbff…`

Cross-verification: an independent python re-implementation of the verify protocol (just `hashlib.sha256` + the proof walk) reproduces the root from every one of the 10 leaves — **10/10 leaves verify**. This is exactly the property an external auditor needs: only the JSON outputs and the protocol from §2.3 are required, no shared code.

> Note: the parent abstraction doc cites "13 entries"; current `index.json` carries 10. The builder is N-agnostic. T2 explicitly covers the 13-leaf case as a synthetic check.

Artifacts:

- `tool/meta2_merkle_build.hexa` — hexa builder + verifier (raw#9 strict).
- `state/meta2_merkle_root.json` — root document (510 B).
- `state/meta2_merkle_proofs.json` — 10 inclusion proofs (6779 B).

---

## §5. Bounds (Bekenstein / Shannon / sha256) / 한계

| Bound | Value at current N=10 | Headroom |
|---|---|---|
| sha256 second-preimage | 2¹²⁸ ops | astronomical |
| proof size | 4 hashes × 32 B = 128 B per leaf | trivial |
| root storage | 32 B | trivial |
| **scaling**: at N=10⁶ (cosmic-scale registry) | depth=20, proof = 640 B | still trivial |
| Bekenstein for 1 root (32 B = 256 bits) in any macroscopic device | ≪ 10⁴³ bits | **~40 orders of magnitude** below the physical floor |
| Shannon: leaf hashes are uniformly distributed → cannot compress further | — | tight (information-theoretic optimum) |

**Conclusion**: at any N realistic for `.meta2-cert` (≤10⁴ this decade), Merkle-tree commitment is **far** from any physical/information-theoretic limit. The genuine remaining limit is **single-root key management** (L2→L4 path: post-quantum signatures over the root, addressed in `alm_memory_state_persistence_abstraction_20260425.md` §3 L4).

---

## §6. Policy notes / 정책 메모

- **raw#9 (hexa-only)**: builder is `tool/meta2_merkle_build.hexa`, modeled on `tool/meta2_hashchain_verify.hexa`. No `.py` artifact ships. (Python was used only as a one-shot independent cross-check for the §4 verification claim.)
- **raw#10 (proof-carrying)**: every leaf carries `(slug, file, leaf_hash, prev_index_sha, proof)`; root document carries `(leaf_count, padded_count, tree_depth, merkle_root, algo strings, ts)`. Verification is local, deterministic, no oracle.
- **raw#11 (snake_case)**: all identifiers are snake_case.
- **raw#15 (no-hardcode)**: cert root and both output paths are CLI args (`--root`, `--out-root`, `--out-proofs`); defaults are repo-relative.
- **roadmap policy R4**: `.roadmap` not modified by this work.

---

## §7. Next steps / 다음 단계

1. **Daemon hook** — append a Merkle root recompute step to `tool/cert_watch.hexa` so each new entry triggers a root refresh.
2. **Sign the root** — Ed25519 now, Dilithium later (closes part of L4 from the parent abstraction doc).
3. **Publish** — copy `state/meta2_merkle_root.json` to R2 (`anima-logs/meta2_merkle_root_<epoch>.json`) so external auditors can pull a single ~510-byte file and verify any entry with 4 sibling hashes.
4. **Append-only proof history** — once a root is signed/published, archive it; subsequent epochs chain via `prev_root_hash` to keep an audit log of root rotations.
5. **Verifier hexa script** — separate `tool/meta2_merkle_verify.hexa` that takes `(state/meta2_merkle_root.json, state/meta2_merkle_proofs.json)` and re-runs the §2.3 protocol independently of the builder (defense-in-depth).

---

## §8. Verdict / 판정

**L2 PASS (prototype)**: Merkle root computed, inclusion proofs generated, tamper-detection demonstrated, all four selftests green. The L2 row in `docs/alm_memory_state_persistence_abstraction_20260425.md` flips from **0% → prototype-VERIFIED**. Production hardening (hexa port + signing + R2 publish) is queued in §7; none of those steps require additional research — they are pure engineering.

— end —
