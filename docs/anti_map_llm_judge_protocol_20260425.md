# ANTI_MAP LLM-as-Judge Validation Protocol (raw#12 frozen, pre-approved)

**Date**: 2026-04-25
**Status**: SPEC_FROZEN. Actual LLM API call pre-approved per `feedback_forward_auto_approval` (raw#9 explicit exempt = default), gated by cost cap (~$5 per validation cycle).
**Predecessor**: ANTI_MAP v2 (`066dfd2d`) — heuristic baseline PASS but semantic ground truth 별도 검증 필요
**Reference**: state/mk_xi_anti_map_ledger_v2_20260425.json
**Forward auto-approval note**: forward auto-approval per memory feedback_forward_auto_approval (2026-04-25). LLM API call (anthropic/openai/local LLM judge)은 별도 승인 없이 진입 (cap: $5 per validation cycle, 16 entries × 3 samples).

## §0 raw#10 honest scope

**ANTI_MAP v2 heuristic PASS_BASELINE 도달했으나 실제 anti-meaning quality는 LLM-as-judge로만 검증 가능.** anima에 외부 LLM API 호출 도구 부재 (`tool/llm*` 없음). 본 protocol은 frozen spec — actual LLM call은 pre-approved per feedback_forward_auto_approval (외부 anthropic/openai API key 통합 또는 local LLM forward 통합 후 자동 진입). cost cap $5 per cycle 으로 안전망.

## §1 Validation goals

각 ANTI_MAP entry에 대해:
1. **Anti-meaning correctness**: anti가 정말 original의 의미 부정인가?
2. **Anti-meaning specificity**: anti가 random/unrelated보다 의미적으로 더 가까우면서 반대 방향인가?
3. **Bilingual consistency**: EN-KO pair (예: idx 0 ↔ idx 6) anti도 동일 의미 유지인가?

## §2 Judge prompt template (raw#12 frozen)

```
You are a semantic distance judge for an anti-meaning evaluation task.

ORIGINAL: "{original}"
ANTI-MEANING: "{anti_meaning}"
RANDOM CANDIDATE: "{random_prompt}"

Score on three axes (0-10 each):
1. ANTI_CORRECTNESS: Does the anti-meaning genuinely negate or invert the original's claim?
   0 = no negation; 10 = perfect semantic inversion
2. ANTI_SPECIFICITY: Compared to the random candidate, is the anti-meaning more
   semantically related to the original (while opposing it)?
   0 = random is closer; 10 = anti is much more specifically opposite
3. SURFACE_DISTINCTION: How different is the anti's surface form from original
   (avoiding mere word swap)?
   0 = trivial word swap; 10 = substantial paraphrase

Return JSON: {"correctness": N, "specificity": N, "surface_distinction": N, "rationale": "..."}
```

## §3 Per-entry validation procedure

```python
def validate_entry(entry, random_pool):
    original = entry["original"]
    anti = entry["anti_meaning"]
    
    # Pick 3 random candidates from RANDOM pool (raw#12 fixed seed for reproducibility)
    rng = np.random.default_rng(20260425)
    random_samples = rng.choice(random_pool, 3, replace=False)
    
    scores = []
    for random_p in random_samples:
        prompt = JUDGE_PROMPT.format(
            original=original,
            anti_meaning=anti,
            random_prompt=random_p
        )
        response = call_llm(prompt, model="claude-opus-4-7", temperature=0.0)
        scores.append(parse_judge_response(response))
    
    # Aggregate (median for robustness)
    return {
        "correctness_median": median([s["correctness"] for s in scores]),
        "specificity_median": median([s["specificity"] for s in scores]),
        "surface_median": median([s["surface_distinction"] for s in scores]),
        "all_scores": scores
    }
```

## §4 PASS predicate (raw#12 frozen)

For each entry:
- `correctness_median >= 7` (anti-meaning genuinely negates)
- `specificity_median >= 6` (anti more specific than random)
- `surface_median >= 4` (avoids trivial word swap)

For full ANTI_MAP:
- `entry_pass_count == 16` (all entries pass)
- `mean_correctness >= 7.5` (high baseline)

If FAIL:
- Log per-entry scores
- Identify failing entries
- Propose v3 revision (raw#12 new revision, v2 preserved)

## §5 Bilingual pair consistency check

EN-KO pairs (PAIRS=[(0,6),(1,7),(2,8),(3,10),(4,11),(5,9)]):
For each (i, j) in PAIRS:
- ANTI_MAP_v2[i].anti_meaning vs ANTI_MAP_v2[j].anti_meaning
- Judge: "Are these two anti-meanings semantically equivalent (translation)?"
- PASS if median >= 7

This is critical for V_sub measurement validity — bilingual EN-KO anti pairs must be parallel.

## §6 Cost & resource

```
LLM model: claude-opus-4-7 (or local equivalent)
Per entry: 3 random samples × 1 call = 3 calls
Total entries: 16 EN/KO + 6 bilingual pair checks = 22 calls × 3 = 66 calls
Estimated tokens per call: ~500 input + 200 output = 700 tokens
Total tokens: 66 × 700 = ~46K tokens
Estimated cost: $1-3 (claude-opus-4-7 pricing)
Runtime: ~5-10 min sequential, ~1 min parallel
```

## §7 Output artifacts

```
state/mk_xi_anti_map_llm_judge_validation_20260425.json
  - per_entry_scores
  - bilingual_pair_consistency
  - aggregate_statistics
  - PASS/FAIL verdict
  - failing_entries (if any) → v3 revision proposal
```

## §8 Failure modes

1. **LLM judge bias**: judge model이 anthropic/openai 자체 fine-tune의 bias 반영 가능
   - Mitigation: 2개 LLM (claude + gpt-4) cross-check
2. **Translation ambiguity**: bilingual pair consistency가 cultural/linguistic context에 의존
   - Mitigation: native KR speaker manual review for failing pairs
3. **Random pool quality**: RANDOM pool이 anti와 너무 가까우면 specificity score 낮음
   - Mitigation: RANDOM pool을 max-diverse로 redesign (raw#12 new revision 가능)
4. **Score correlation**: heuristic v2 PASS과 LLM judge PASS correlation 낮으면 heuristic 신뢰성 의문
   - Mitigation: heuristic re-design or weight adjustment

## §9 raw compliance

- raw#9 — protocol spec only, $0. actual call은 pre-approved by feedback_forward_auto_approval (raw#9 explicit exempt = default per 2026-04-25 정책), gated by cost cap ($5 per validation cycle)
- raw#10 — 'spec ≠ validated' 명시, failure modes 4개 사전 등록. actual call 결과는 별개 cycle, forward auto-approval은 trigger gating 변경
- raw#12 — judge prompt template + thresholds + cost budget 모두 frozen (auto-approval은 prereg threshold/predicate 변경 X)
- raw#15 — protocol = SSOT for LLM-judge validation
- raw#37/38 — design (ANTI_MAP v2 heuristic insufficient) → impl (this protocol) → fixpoint (auto-approval default)

omega-saturation:fixpoint
