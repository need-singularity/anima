# CLAUDE.md — anima 프로젝트 사용자 정의

> 본 파일 = Honesty triad precondition-e fix (LLM agents indicator).
> Phase 3 supercycle / cross_repo_dashboard 가 .claude/agents/ OR CLAUDE.md OR
> AGENT.md 중 하나만 있어도 PASS 처리. 가장 가벼운 옵션 = 본 CLAUDE.md drop.

## 프로젝트 개요

anima 의 SSOT 위치 + 핵심 도구 + raw rule contract.

## SSOT
- atlas: `n6/atlas.n6` (또는 `atlas/atlas.n6`)
- design: `design/` (markdown + json witnesses)
- tool: `tool/` (실 도구)

## 적용 raw rules (hive .raw 참조)

- raw 0 root-ssot triad
- raw 1 chflags uchg (file lock)
- raw 9 hexa-only (.rs/.toml/.py/.sh ban)
- raw 12 silent-error 금지
- raw 23 schema-guard-mandatory
- raw 47 strategy-exploration-omega-cycle
- raw 68 fixpoint-byte-eq-closure
- raw 70 multi-axis-verify-grid (K≥4)
- raw 71 falsifier-retire-rule (≥3 falsifier)
- raw 73 structural-admissibility-paradigm
- raw 77 audit-append-only-ledger
- raw 81 default-model-top-tier-mandate

## Honesty triad (`scripts/quality/honesty_triad_linter.py` 또는 동등)

5 preconditions (Phase 3 supercycle):
- (a) git tracked SSOT
- (b) design/ + ≥1 .md
- (c) tool/ + ≥3 files
- (d) atlas SSOT 파일
- (e) **이 파일 (CLAUDE.md) — LLM agents indicator** ✅

## 본 파일 위치
- `~/core/anima/CLAUDE.md`

> 다음 `nexus hexa-sim dashboard` 실행 시 anima 의 honesty 5/5 = REPO_INVARIANT 도달.

__HONESTY_PRECONDITION_E_FIX__ emit-only repo=anima type=claude_md
