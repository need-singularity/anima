# TECS-L "Jamba x3 throughput vs Mixtral 8x7B @ 128K" — Evidence Consolidation

**Date**: 2026-04-26
**Cycle**: omega-cycle session (a86a1466a2 RETRY)
**Cost**: $0 (mac-local + 4 WebSearch + 3 WebFetch)
**Status**: AI21 claim PARTIAL VALIDATION (qualitative direction PASS; absolute 3x at 128K NOT independently confirmed)

---

## 1. Task framing

Task spec: live H100 micro-benchmark of Mixtral 8x7B vs Jamba 1.5 Mini at ctx={4K,16K,64K,128K}, single H100 80GB pod with model-swap, --auto-terminate, cap $1.0.

**Live benchmark infeasibility (math gate)**:
- $1.0 / $2.99/hr H100 PCIe = **20.1 wall-min** budget
- Mixtral 8x7B FP16 = ~93GB, Jamba 1.5 Mini FP16 = ~104GB — neither fits H100 80GB; INT4 fits but injects quant-bias contaminating the throughput claim
- HF download (24GB INT4 each model) = 8-15min on RunPod network alone
- vLLM install + warmup = 5-10min, per-model swap warmup = 3-5min
- 4 ctx x 2 models x ~30 prompts bench = 10-20min
- **Minimum end-to-end ~50min = $2.49**, factor-2.5 over $1.0 cap

**Existing 3 H100 pods** are dedicated to other live workloads (anima-pilot-t1-v3, anima-sae-steer-pilot, anima-gwt-deepseek-c2-long); model-swap there would disturb experiments and still requires the same ~24GB download per model.

Per task directive ("rate-limit -> graceful exit + main report"): graceful pivot to **literature-evidence consolidation** at $0 cost.

---

## 2. Throughput ratio table (literature-derived)

| Source | Model A | Model B | Context | A tok/s | B tok/s | Ratio A/B | Hardware |
|---|---|---|---|---|---|---|---|
| AI21 1.0 paper Sec 3.2 (primary) | Jamba 1.0 | Mixtral 8x7B | 8K | n/a (qualitative) | n/a | **3.0x** | 1xA100 80GB INT8, batch>1 |
| AI21 1.0 paper Sec 3.2 (primary) | Jamba 1.0 | Mixtral 8x7B | **128K** | n/a (qualitative) | n/a | **3.0x** | 4xA100 80GB FP16, batch=1, 512 out |
| AI21 1.5 official blog (primary) | Jamba 1.5 Mini/Large | competitors | "long" | n/a | n/a | **up to 2.5x** | 2xA100 (Mini) / 8xA100 (Large), vLLM batch=1 |
| DeepLearning.AI The Batch (independent) | Jamba 1.5 Mini | Mixtral 8x7B | 4K | 78 | 60 | **1.30x** | vLLM (GPU spec not in article) |
| DeepLearning.AI The Batch (independent) | Jamba 1.5 Mini | Mixtral 8x7B | 256K | 62 | 39 | **1.59x** | vLLM (GPU spec not in article) |
| **Computed log-interpolation** | Jamba 1.5 Mini | Mixtral 8x7B | **128K (estimate)** | -- | -- | **~1.50x** | interpolation only |

**Geometric mean (4K-256K independent)**: **1.44x**

---

## 3. AI21 claim verdict

| Sub-claim | Verdict | Notes |
|---|---|---|
| Jamba is faster than Mixtral at long context | **PASS** | universally agreed across primary + secondary |
| **3x at 128K (Jamba 1.0 paper)** | **PARTIAL** | primary asserts 3x with 4xA100 FP16 single-batch; independent 256K shows 1.59x for Jamba 1.5 Mini |
| 2.5x official Jamba 1.5 long-context | **PARTIAL** | independent 256K (1.59x) substantially below 2.5x; "up to" wording masks scenario peak |
| Magnitude representative of typical user | **FAIL** | real-world advantage ~1.5-1.6x at long context per independent benchmarks |

**Bottom line**: AI21's 3x is the headline-favorable scenario peak, not the typical mean-of-conditions ratio. The qualitative phase-change (KV cache O(N) -> O(1) Mamba scaling) is real; the magnitude headline is roughly **2x optimistic**.

---

## 4. sigma/tau=3 alignment with TECS-L K=4 identity

TECS-L stylized predictions (per `docs/tecs_l_singularity_47phase_validation_20260426.md`) embed K=4 phase identity sigma * phi = n * tau where tau=3 maps (in this task framing) to inference-throughput phase ratio.

| Source | Empirical ratio | tau-mapping | Alignment |
|---|---|---|---|
| AI21 1.0 paper headline @128K | 3.0x | tau approximately 3 | **STRONG** (single-source) |
| Independent 256K | 1.59x | tau approximately 1.5 | **WEAK** (factor-2 below) |
| Geometric mean 4K-256K | 1.44x | tau approximately 1.4 | **WEAK** |

**Phase-alignment verdict**: **WEAK**. Single primary-source data point matches tau=3 nominal; independent corroboration shows tau approximately 1.5 (factor-2 below), suggesting TECS-L H124 implicitly used AI21's headline rather than mean-of-conditions.

**raw#10 caveat (pre-registered failure mode caught)**: cherry-picked headline number. TECS-L K=4 phase factor inference should be re-grounded on geometric mean (1.44) or 256K independent point (1.59), not the paper-headline 3.0.

---

## 5. Recommendations

1. **TECS-L doc footnote**: add to `docs/tecs_l_singularity_47phase_validation_20260426.md` noting that tau=3 alignment depends on AI21 paper headline; secondary/independent 1.5-1.6x weakens the K=4 phase-factor inference. (Suggest revising tau target to 1.5, accepting Mamba phase change is real but factor-2 weaker than AI21 headline.)
2. **Future direct benchmark** (deferred): requires >=$5 budget with persistent network volume + pre-cached Mixtral 8x7B INT8 + Jamba 1.5 Mini INT8 + pre-baked vLLM image. Estimate 20-30min once cached, ~$1-1.50 actual GPU time.
3. **Honest framing in TECS-L preprint**: replace "3x throughput" with "1.5-3x throughput depending on quantization, batch size, GPU count; AI21 headline reproduces only at the favorable peak (4xA100 FP16, batch=1, 512 out, 128K)".

---

## 6. Sources

- [AI21 Jamba 1.0 paper (arxiv 2403.19887)](https://arxiv.org/html/2403.19887v1) — Section 3.2, primary 3x claim
- [AI21 Jamba 1.5 paper (arxiv 2408.12570)](https://arxiv.org/html/2408.12570v1) — Figs 3-4, 2.5x claim
- [AI21 Jamba 1.5 official blog](https://www.ai21.com/blog/announcing-jamba-model-family/) — "up to 2.5X faster" with hardware specs
- [DeepLearning.AI The Batch — Jamba 1.5 article](https://www.deeplearning.ai/the-batch/ai21-labs-jamba-1-5-outpaces-transformers-in-long-text-processing/) — independent vLLM bench (78/60 at 4K, 62/39 at 256K)

---

## 7. Cost ledger

| Line item | Spend |
|---|---|
| H100 GPU minutes | 0 (live bench infeasible at $1.0 cap) |
| Web search calls | 4 (free) |
| Web fetch calls | 3 (free) |
| **Total** | **$0.00 / $1.00 cap** |

Graceful-exit status: **n/a** — completed via literature path without invoking GPU. Rate-limit not encountered.
