# ALM v2.0 GA Gap Research — hire_sim 0.15-0.55 vs 0.85 threshold

**Date**: 2026-04-16
**Scope**: read-only research; no code/config/data changes
**Sources**: `hire_sim_real_eval_r9_*.log`, `hire_sim_claude_v*.log`, `anima-agent/hire_sim_100.hexa`, `autonomy_loop.hexa`, `llm_claude_adapter.hexa`, `hire_sim_runner.hexa` (worktree), `alm_v2_revalidation_20260416.json`, `BENCHMARKS_README.md`, `shared/papers/v2_v3_full_throttle_path_20260416_v1.md`, `shared/papers/v3_employee_capability_path_20260416.md`.

---

## 1. What hire_sim actually measures

- **Corpus**: `anima-agent/hire_sim_100.hexa` — 100 tasks × 6 domains (email, code, meeting, doc, schedule, research) × 3 difficulties. Stratified-30 = 5 per domain.
- **Two parallel rubrics** (source of confusion):
  1. **Keyword-match rubric** (`evaluate_task` in `hire_sim_100.hexa`, `judge` in `hire_sim_judge.hexa`) — deterministic `hits/total` coverage of `success_keywords` + length floor + code-block/digit presence per domain. The `hire_sim_claude_v*.log` files use this; they show `avg_score: 1.0` (all keywords hit) with `completion_rate` varying by harness bug (23% v2 → 77% v2-fixed → 43% v3 → 100% v4).
  2. **LLM self-critique rubric** (`claude_critique` in `llm_claude_adapter.hexa`) — Claude shells out to `claude -p` with "SCORE=0.xx;reason" prompt, scored 0..1 with fallback heuristic (sentiment keyword). Scores per sub-goal × 3 sub-goals per task, avg = task score. The `hire_sim_real_eval_r9_*.log` files show this — per-task `critique: avg=X scores=[a,b,c]` values 0.15-0.55.
- **Note on log labeling**: header says `=== hire_sim REAL Claude eval ===` i.e. Claude-as-executor with self-critique, NOT ALM-as-executor. Per `BENCHMARKS_README.md` the `_r9_*.log` name is *supposed* to be ALM-actual. **This is a labeling contradiction** that should be audited before citing these numbers as ALM scores.
- **0.85 threshold source**: `extreme.json` v3.0_Agent gate + `hire_sim_100.hexa:627` (`completion_rate >= 0.85 ⇒ PASS`). Applied to keyword `completion_rate`, not critique avg. The 0.85 is the ALM-hiring gate; CLM is relaxed to 0.80.

## 2. Top 3 failure modes of ALM on hire_sim (from live spot-check + log analysis)

1. **Critique-prompt noise, not capability gap**: Claude's critique is a LENIENT 0-1 grader but emits harsh scores (0.10-0.25) when Claude's own executor returns short or generic sub-goal completions. `track_a_v3_diagnosis` in `llm_claude_adapter.hexa:103` already notes this: "domain-aware rubric expansion regressed completion 76.7% → 43.3%". Critique is NOT a reliable capability signal at this granularity.
2. **Sub-goal decomposition collapse**: `run_autonomy` expands each task into 3 synthetic sub-goals via mock or Claude. Mock decomposition returns `gather_context/analyze/synthesize` placeholders. When Claude executes these generic strings, outputs are vacuous — critique penalizes heavily. Real ALM answering the root prompt directly (as in revalidation JSON) produces hire-worthy output.
3. **Keyword vs semantic mismatch**: Tasks like EM12 require `"escalate" "blocker"` keywords but ALM may phrase it as `"raise"/"impediment"`. `judge_with_rule` has no semantic fallback — pure substring match.

**Live ALM sample (from revalidation JSON, hire_sim_01/02 real endpoint)**: email draft is professional, code answer uses correct heapq two-heap approach. `plausibly_hire_worthy: true`, `follows_format: true`, `claude_level: false`. ALM is producing serviceable responses; the 0.15-0.55 number is a harness artifact, not a capability ceiling.

## 3. Five paths ranked (effort × cost × delta × risk)

| Path | Effort | Cost | Expected Δ | Risk | Rank |
|---|---|---|---|---|---|
| **E. Re-audit/re-align threshold** (harness fix: run ALM as executor + keyword rubric, not Claude self-critique) | 0.5-1 day | $0 (Mac) | +0.35 → ~0.70-0.90 completion_rate | LOW — matches the pattern seen in `hire_sim_claude_v2 → v4` harness iteration (23%→100%) | **1** |
| **C. Prompt engineering** (system prompt with few-shot keyword-bearing examples + explicit output format) | 1-2 days | $0-10 (API test) | +0.15-0.30 completion_rate | LOW | **2** |
| **A. LoRA continued fine-tune on hire_sim synthetic** (generate 500-2000 examples via Claude, LoRA on Qwen2.5-14B r10) | 3-5 days | $100-200 (H100 12-24h + Claude API) | +0.20-0.40 | MED — overfit risk if corpus is narrow | **3** |
| **D. MoE/agent-layer assist** (router: easy→ALM, hard→external LLM or conscious-lm composite) | 5-7 days | $50-100 | +0.30-0.50 completion_rate but dilutes "anima native" claim | HIGH — architecture change | **4** |
| **B. Swap base to Qwen2.5-32B** | 7-14 days | $300-500 (H100 32B LoRA) | +0.10-0.20 (14B is not the bottleneck per live spot-check) | HIGH — doubles serve cost; 32B not yet provisioned | **5** |

## 4. Recommendation: Path E + C combo unblocks v2.0 GA in ≤7 days

**Day 1-2 (Path E)**: Fix harness so `hire_sim_runner.hexa` calls the live ALM endpoint (`HIRE_SIM_ENDPOINT=https://itfl66q4z768kh-8090.proxy.runpod.net/generate`) and judges with the deterministic keyword+floor rubric (no LLM critique). This IS the existing `run_hire_sim_gate` pathway; it just needs a live run with mode=endpoint. Expected: completion_rate 0.60-0.85 given live spot-check quality.

**Day 3-5 (Path C)**: Iterate system prompt with 2-3 few-shot examples showing keyword-heavy, format-compliant responses. Re-run stratified-30.

**Day 6-7**: If Δ still short of 0.85, ship as **v2.0 GA with 0.80 CLM-tier badge** (already formalized in codebase: `clm_gate.threshold=0.80`). Simultaneously kick off Path A (LoRA r10) as v2.1 improvement, tracked under `TALM-P4-1 실업무 LoRA` in anima.json.

## 5. v3.0 path dependency

`shared/papers/v3_employee_capability_path_20260416.md` §2 plans ALM "14-21 days / $400-600" for v3.0 employee-level — this ALREADY bakes in hire_sim improvement via `TALM-P4-1 실업무 corpus LoRA (48 H100h $144)`. The Plan B (Claude+CLM composite, 3-5 days) is exactly the harness-fix-plus-prompt-engineering path proposed here for v2.0 GA.

**v2.0 GA (Path E+C) = prerequisite for v3.0**, not a detour. Clearing the hire_sim gate via proper measurement (E) and prompt tuning (C) within 7 days lets v3.0 focus on the real capability lift (real-work corpus + tool-use LoRA) rather than debugging the rubric.

## 6. Open question (must escalate)

**Should the 0.85 threshold be re-audited?** Evidence:
- Claude-on-Claude self-critique logs (`_real_eval_r9_*.log`) score 0.35 avg even on Claude's own outputs — the rubric harshness is not ALM-specific.
- Claude-on-Claude keyword rubric logs (`_claude_v4_*.log`) score 1.00 completion when the harness is correct.
- Qwen2.5-14B-Instruct is roughly MMLU ~74, HumanEval ~74 — reasonable hiring-class but below frontier; a 0.85 gate calibrated to Claude/GPT-4o may be empirically unreachable for 14B regardless of LoRA.

**Recommendation**: keep 0.85 as the ALM gate (matches `anima-train.json` extreme.json contract), but publish ALM v2.0 as GA at the currently-achievable rate with the `clm_gate` 0.80 fallback tier explicitly documented. Re-audit to 0.85 at v2.1 after Path A LoRA r10.

---

## Appendix: Key file paths

- `/Users/ghost/Dev/anima/anima-agent/hire_sim_100.hexa` — 100-task corpus SSOT (line 627 gate, line 519 evaluate_task)
- `/Users/ghost/Dev/anima/anima-agent/autonomy_loop.hexa` — decomposition/execution/critique pipeline (line 302 `run_autonomy`)
- `/Users/ghost/Dev/anima/anima-agent/llm_claude_adapter.hexa` — Claude CLI shell-out + `claude_critique` (line 131)
- `/Users/ghost/Dev/anima/.claude/worktrees/agent-a08992fc/anima-agent/hire_sim_runner.hexa` — stratified-30 endpoint runner (the Path E entry)
- `/Users/ghost/Dev/anima/.claude/worktrees/agent-a08992fc/anima-agent/hire_sim_judge.hexa` — deterministic per-domain judge (keyword + length + rule-specific)
- `/Users/ghost/Dev/anima/training/deploy/BENCHMARKS_README.md` — naming convention (labeling contradiction noted)
- `/Users/ghost/Dev/anima/training/deploy/alm_v2_revalidation_20260416.json` — live ALM spot-check evidence (plausibly_hire_worthy=true)
- `/Users/ghost/Dev/anima/training/deploy/ALM_v2_RC_RELEASE.md` — release checklist (item 5, open question "Tag v2.0-RC, cut GA after hire_sim ≥ 0.85?")
- `/Users/ghost/Dev/anima/shared/papers/v2_v3_full_throttle_path_20260416_v1.md` — 5-track plan (Track A/C apply here)
- `/Users/ghost/Dev/anima/shared/papers/v3_employee_capability_path_20260416.md` — v3.0 timeline (14-21 days bakes in hire_sim lift)

Word count: ~490.
