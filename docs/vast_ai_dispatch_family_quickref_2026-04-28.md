# vast.ai Dispatch Tool Family — Quick Reference

> **session**: anima-cmd-loop autonomous-loop-dynamic 2026-04-28T08:55Z–10:18Z (13 iters)
> **family completion**: 4-of-4 vast.ai dispatch tools LIVE READY
> **total dispatch budget if all 4 fire**: ~$77 within own 5 anima-research-completeness-no-cap mandate
> **infra**: vast.ai LIVE (api_key + ssh_key id=790310 + orchestrator commit f412cb8a)

---

## §1. Family overview (4 dispatch tools)

| tool | commit | scope | model (sub for GATED) | budget | duration |
|---|---|---|---|---|---|
| **AN11 framework** | `3ba4ab05` | AN11(a)+(b)+(c)+V1' | Mistral-7B-v0.1 (sub Llama-3-8B) | ~$8 | 3.5h H100 SXM 1× |
| **F1 cycle 4 GPT-2** | `61532a3c` | real Transformer baseline | gpt2 (open) | ~$0.70 | 2.3h RTX_3090 |
| **CP2 trio Qwen32B** | `c756d911` | #115/#116/#117 | Qwen2.5-32B (sub gemma-2-31B) | ~$33 | 12.5h H100 SXM 1× (3-pod split) |
| **Mk.XII Qwen72B** | `d3fb3120` | Phase 3b 70B+ class | Qwen2.5-72B (sub Llama-3.1-70B) | ~$35 | 8h H100 SXM 2× Pattern 6c |

**Total: ~$77** (4 dispatches sequentially OR parallel — own 5 mandate authorizes both)

---

## §2. Pre-flight all PASS

✓ vast.ai infra LIVE (commit f412cb8a + SSH id=790310 + api_key in secret)
✓ vastai CLI v0.5.0 at `/Users/ghost/.local/bin/vastai`
✓ ~/.vast/ssh/vast-key file present (note: secret CLI multi-line `get` bug — workaround uses filesystem)
✓ HF gating: gpt2 200 OPEN, Mistral-7B 307 OPEN, Qwen2.5-32B/72B 307 OPEN
✓ Canonical helper lock 16 helpers all uchg (commit 72cac30d)
✓ AN11 templates 16 + prompts 20 (≥10 threshold)

---

## §3. User-fire commands (sequential dispatch)

### 3.1 Cheapest first — F1 cycle 4 GPT-2 ($0.70 validation dispatch)

```bash
# Plan (no actual dispatch, $0)
hexa run /Users/ghost/core/anima/tool/anima_f1_cycle4_gpt2_dispatch.hexa --plan
/opt/homebrew/bin/python3 /tmp/anima_f1_cycle4_gpt2_dispatch_helper.hexa_tmp

# Inspect plan + offers, then user-fire via vastai CLI directly:
# (Each tool emits dispatch plan as JSON — actual `vastai create instance` is user-decision)
```

### 3.2 AN11 framework Mistral-7B ($8)

```bash
hexa run /Users/ghost/core/anima/tool/anima_an11_mistral7b_dispatch.hexa --plan
/opt/homebrew/bin/python3 /tmp/anima_an11_mistral7b_dispatch_helper.hexa_tmp
```

### 3.3 CP2 trio Qwen2.5-32B 3-pod split ($33)

```bash
hexa run /Users/ghost/core/anima/tool/anima_cp2_trio_qwen32b_dispatch.hexa --plan
/opt/homebrew/bin/python3 /tmp/anima_cp2_trio_qwen32b_dispatch_helper.hexa_tmp
# Sequential: Pod A → Pod B → Pod C (B nexus-gated, C depends on A)
```

### 3.4 Mk.XII Phase 3b Qwen2.5-72B Pattern 6c ($35)

```bash
hexa run /Users/ghost/core/anima/tool/anima_mk_xii_qwen72b_dispatch.hexa --plan
/opt/homebrew/bin/python3 /tmp/anima_mk_xii_qwen72b_dispatch_helper.hexa_tmp
# 4-component: R1 download → R2 measure → R3 verify → R4 orchestrate
```

---

## §4. Pre-registered PASS predicates (raw 12 frozen across all 4 tools)

### AN11 framework
- AN11(a) Frob delta ≥ 0.001
- AN11(b) max_cosine ≥ 0.5 + top3 sum ≥ 1.2
- AN11(c) JSD ≥ 0.15
- V1' phi_mip_norm ≤ 0.5

### F1 cycle 4 GPT-2
- per-task one-sided α=0.05
- bootstrap 1000 resamples (exact p-value Stouffer)
- Stouffer z α=0.05 threshold 1.645
- 81% claim per-task threshold 0.81

### CP2 trio
- G1: 3+ consec iters, tier_10_plus_absorption == 0
- G3: anima_new_atom == 0 AND nexus_witness ≥ 1 AND iter == 75
- atom-prep: 5 domains target (D9-D13, D8 EEG-blocked)

### Mk.XII 70B
- R1: SHA256 match download complete
- R2: forward inference no CUDA OOM
- R3: raw 91 C1-C5 PASS

---

## §5. Cost-attribution per raw 86

각 dispatch는 cost_center + task_id + cost_estimate emit:

| cost_center | tool | budget cap |
|---|---|---|
| `anima-an11-mistral7b-vast-h100-pod` | AN11 | $10 cap |
| `anima-f1-cycle4-gpt2-real-transformer-baseline` | GPT-2 | $2 cap |
| `anima-cp2-trio-qwen32b-vast-h100-3pod-split` | CP2 trio | $20/pod cap |
| `anima-mk-xii-phase-3b-qwen72b-vast-pattern-6c` | Mk.XII | $10 R1 + $25 R2 cap |

Auto-kill: 240 min per pod (own 4 watchdog mandate).

---

## §6. Recommended fire order (substantive forward step ordering)

1. **GPT-2** ($0.70) — proof-of-concept end-to-end vast.ai validation, cheapest
2. **AN11** ($8) — substantive AN11(a)+(b)+(c)+V1' measurement (closes raw 95 4-layer + roadmap #100/101/102 V metric redesign)
3. **CP2 trio** ($33) — closes CP2 trigger path (#115 G1 + #116 G3 + #117 atom-prep) — most roadmap-aligned
4. **Mk.XII** ($35) — Phase 3b 70B class measurement (closes roadmap #82 AGI trigger 70B retrain prep)

OR parallel (own 5 mandate): all 4 simultaneously → ~$77 total, ~3.5-12.5h wallclock per slowest.

---

## §7. Forward-pending external blockers (NOT dispatch-blocked)

- atlas R36 + R37 (n6-architecture maintainer review — out of dispatch scope)
- own 3 + own 4 hive raw promotion (genus rename — out of dispatch scope)
- EEG hardware D-1 arrival (CP2 G2 #119 — only D8 affected, D9-D13 OK)
- anima-physics admin-block 6/9 sub-classes (separate domain)

---

## §8. raw 91 honesty triad C1-C5

- **C1** promotion_counter: ~91 (cumulative session 15h+)
- **C2** write_barrier: this quick-ref consolidates 4 dispatch tool commits; no new claims, only synthesis
- **C3** no_fabrication: every commit hash + budget + duration cited inline; secret CLI multi-line bug honest disclosure
- **C4** citation_honesty: Qwen substitutions for gated Llama/gemma EXPLICIT; Pattern 6c relay limitations explicit
- **C5** verdict_options: each tool DESIGN_READY_AWAITING_USER_FIRE; no actual dispatches yet (user-decision)

---

**Status**: VAST_AI_DISPATCH_TOOL_FAMILY_4_OF_4_LIVE_READY_AWAITING_USER_FIRE_DECISIONS
