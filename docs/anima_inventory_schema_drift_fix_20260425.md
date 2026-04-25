# Inventory schema drift fix — 2026-04-25

## Symptom

`tool/proposal_archive.hexa` 가 `inventory.json` 의 proposal 리스트를
`"proposals"` 키로 읽고/쓰고 있었음. 그러나 실제 inventory 파일은
schema `anima.proposal_inventory.v1` 에 따라 `"entries"` 키를 사용.

결과:

1. archive 시 inventory 의 entry status mutation 이 항상 no-op.
   (`_inv_find_idx` 가 빈 `"proposals"` 배열만 보고 -1 리턴)
2. `_save_inventory` 가 빈 `"proposals": []` 를 매번 추가/유지
   → drift 누적.
3. `state/proposals/meta/metrics.json.counts.archived` 가 0 이지만
   실제 `state/proposals/archived/` 에는 1 개 파일 존재.

discovered: commit `ef8c8713` evolution lift 작업 중.

## Root cause

`proposal_archive.hexa` 초안이 schema 결정 전 작성되어 임의 키
`"proposals"` 를 가정. 이후 inventory schema 가 `"entries"` 로
표준화됐지만 archive 코드가 따라가지 못함. write path 가
`_save_inventory` 에서 `"proposals": []` 를 매번 출력하면서
사일런트하게 drift 가 보존됨.

## Decision

- **canonical key = `"entries"`** (matches `anima.proposal_inventory.v1`).
- archive 코드를 `"entries"` 로 패치 (legacy `"proposals"` 는 read 시
  migration sink, write 시 drop).

## Patch

`tool/proposal_archive.hexa`:

- `_load_inventory()`: `"entries"` 가 없고 `"proposals"` 만 있을 때
  배열을 마이그레이션. default skeleton 도 `"entries":[]` 로 변경.
- `_inv_find_idx()`: `"entries"` lookup.
- `_save_inventory()`: 직렬화 시 `"entries"` 만 emit, legacy
  `"proposals"` 는 drop.
- `_do_archive()`: in-memory entry mutation 도 `"entries"` 사용.

## Verification

1. **selftest** (`hexa tool/proposal_archive.hexa --selftest`):
   `S0 missing-arg + S1 missing-module + S2 archive + S3 idempotent →
   4/4 PASS`.
2. **inventory schema clean**: post-selftest

   ```python
   keys: ['schema', 'updated_ts', '_meta', 'updated_at', 'entries']
   entries count: 98
   proposals key present: False
   schema: anima.proposal_inventory.v1
   ```

3. **fixture e2e** (id `99999999-FIX1`):
   - approved → archived move: OK
   - inventory 의 `"entries"` 보존, 빈 `"proposals"` 키 사라짐
   - archive 후 fixture 정리 → 최종 state 정상

4. **metrics resync**:

   ```json
   {"pending":77,"approved":14,"rejected":4,"archived":1,
    "debate":0,"clusters":109,"refinement":506}
   ```

   재산출 ts = `2026-04-25T04:49:43Z`.

## Out of scope (carryover)

- `inventory.json.entries` 는 proposal 본체가 아닌 cluster/advisory
  high-level 항목을 추적. 개별 pending proposal 들 (예 `20260422-075`)
  은 entries 에 포함되지 않으며, archive 후 entry status mutation 도
  발생하지 않음 — 이는 별도 설계 결정 (entries 는 다른 라이프사이클).
- `auto_evolution_loop.hexa._counts_inventory()` 가 metrics 를 자동
  refresh 하지만 archive 직후 자동 호출되지는 않음. `proposal_archive`
  가 archive 후 metrics 도 함께 업데이트하도록 추가 패치할 가치 있음
  (현재는 next loop 까지 stale).
- `proposal_archive.hexa` 헤더 코멘트에 언급된 추가 게이트
  (`SELFTEST_PASS` / `DONE` 마커, `.hexa` 확장자 강제) 는 별도
  commit `anima_evolution_archive_gate_fix_20260425.md` 에서 다룸.

## Files touched

- `tool/proposal_archive.hexa` — entries 키로 통일
- `state/proposals/inventory.json` — selftest 가 cleanup 후
  re-serialize, `"proposals":[]` 키 제거
- `state/proposals/meta/metrics.json` — archived count 0 → 1 등
  실측치 재동기화
- `docs/anima_inventory_schema_drift_fix_20260425.md` — 본 문서
