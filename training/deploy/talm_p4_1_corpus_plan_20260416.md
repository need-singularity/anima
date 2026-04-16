# TALM-P4-1 — Real-Work Corpus Plan (LoRA r11 / r12)

**Date**: 2026-04-16
**Scope**: RESEARCH + PLANNING only. No downloads, no Python, no H100 launch.
**Parent track**: v3.0 직원 capability — ALM 14B real-work LoRA
**Prior estimate**: 48 H100h × $2.99 = $144, 2–7 days (from `v3_employee_capability_path_20260416.md` §A.6)
**Corpus target**: 100M–300M tokens across 6 domains (email, meeting, code review, report, contract, schedule)
**Baseline to beat**: hire_sim RAW 0.5333 (r9 v2.0 GA, `hire_sim_alm_actual_20260416.json`) → ≥ 0.80 RAW (no Path C crutch)
**Reference prior cycle**: r10 synthetic corpus at `training/deploy/hire_sim_synthetic_r10_20260416.jsonl` (300 tasks × ≈ 200 tokens = 60K tokens — **~1000× smaller** than what this plan covers)

---

## 1. Per-Domain Dataset Candidate Table

License codes: `COM` = commercial OK (no restrictions), `COM*` = commercial OK with attribution / no endorsement (CC-BY, MIT, Apache), `RES` = research only / commercial forbidden or restricted, `LDC` = Linguistic Data Consortium (member fee / per-use license), `SYN` = must be generated (no public source with acceptable coverage+license).

| Domain | Rank | Dataset | Raw size | Est. tokens | License | Commercial? | Notes |
|---|---|---|---|---|---|---|---|
| **Email** | 1 | Enron (EDO PST) | ~8.6 GB / ~500K messages | ~150M tokens | CC BY 3.0 US (EDO pkg) | `COM*` attribution | Cleanup required (PST → text, dedup, PII scrub). Large single-source bias (1 company, 2000-era). |
| Email | 2 | Avocado Research Email (LDC2015T03) | ~2.3M items, ~10 GB | ~300M tokens | LDC organizational + EUA | `RES` unless for-profit LDC member with written permission | Blocker for commercial serve. Skip unless license pre-cleared. |
| Email | 3 | Synthetic customer-service / intra-office drafts | ~0 raw | any target | CC0 (self-generated) | `COM` | Fill gaps (e.g. modern date fmt, non-Enron domain). Claude/Qwen self-gen, ~$0.03/1K tokens. |
| **Meeting** | 1 | AMI Meeting Corpus | 100h transcripts | ~8–12M tokens | CC BY 4.0 | `COM*` | Multi-speaker, topic-structured. Best open option. |
| Meeting | 2 | ICSI Meeting Corpus | 75 meetings, ~70h | ~6–10M tokens | LDC (LDC2004T04) paid + academic-leaning | `RES`-ish | Combine with AMI for ~20M tokens if license OK. Prefer AMI-only. |
| Meeting | 3 | Synthetic boardroom / stand-up / review transcripts | any target | any target | CC0 | `COM` | Fill time-zone diversity, modern tooling vocabulary (Slack, Zoom, Notion). |
| **Code review** | 1 | Microsoft CodeReviewer (Zenodo 6900648) | Comment_Generation.zip (~GB) | ~20–40M tokens | MIT / Zenodo-default, individual repo licenses vary | `COM*` (GitHub-sourced; repo licenses vary — must filter) | Largest real-world code-review dataset. Diff + comment pairs ideal for ALM. |
| Code review | 2 | `muellerzr/github-pr-history` (HF) | Accelerate project only | ~1–2M tokens | Apache 2.0 (HF default) | `COM*` | Narrow (1 project), but high-quality comments. |
| Code review | 3 | `Tomo-Melb/CodeReviewQA` (HF) | OSS PR-based | ~5–10M tokens | research-focused, check per-record | `COM*` if upstream licenses permit | QA format — might need reformatting. |
| **Report** | 1 | SEC EDGAR 10-K/10-Q (Notre Dame cleaned) | 100+ GB raw | ~30B tokens ceiling | US gov public record | `COM` | Dominant source. Downsample needed. Style = formal financial prose. |
| Report | 2 | PubMed Abstracts (CC-subset) | ~50 GB XML | ~10B tokens | CC0/CC-BY/CC-BY-SA (filter out NC) | `COM*` | Scientific report tone, not consulting — complements SEC. |
| Report | 3 | arXiv abstracts | ~2 GB | ~300M tokens | arXiv non-exclusive (abstracts OK for research; body redistribution restricted) | `COM*` for abstracts only | Academic reports. Short form. |
| **Contract** | 1 | CUAD (Atticus Project) | 510 contracts, ~15 MB TXT | ~3–5M tokens | **CC BY 4.0** | `COM` | Only 510 docs — too small for 100M, but highest-quality labeled. |
| Contract | 2 | SEC EDGAR material contract exhibits | extract from 10-K/10-Q EX-10 | ~500M–1B tokens | US gov public record | `COM` | Massive scale, filter by filing type `EX-10*`. Closest to real commercial contracts. |
| Contract | 3 | Synthetic NDA/MSA/SOW templates | any target | any target | CC0 | `COM` | Cover industries absent from SEC (e.g. SaaS SLAs, HR offers). |
| **Schedule** | 1 | *(public calendar data effectively non-existent)* | — | — | — | — | Calendar = private; no usable public corpus found. |
| Schedule | 2 | GitHub Issues with date references (scheduling subset) | filter by regex | ~5–10M tokens | repo-dependent | `COM*` (filter MIT/Apache repos only) | Weak signal; not pure scheduling. |
| Schedule | 3 | **Synthetic time-coordination dialogues** | any target | any target | CC0 | `COM` | **Mandatory** (~80%+ of schedule coverage). Claude API generation best path. |

---

## 2. Recommended Mix — Hybrid (Public Seed + Synthetic Augmentation)

Pure-synthetic is uniform but lacks real distributional tail. Pure-public misses domain balance (schedule) and modern vocabulary (Enron is 2000–2002). **Hybrid is the right default**.

### 2a. Strategy per domain

| Domain | Public % | Synthetic % | Primary source | Synth role |
|---|---:|---:|---|---|
| Email | 60% | 40% | Enron EDO | Modernize vocabulary (Slack/Teams), non-corporate registers, multilingual (KO/EN) |
| Meeting | 70% | 30% | AMI | Cover stand-ups, code review meetings, product Q&A |
| Code review | 85% | 15% | MS CodeReviewer | Fill Hexa-specific review patterns, bad-code diagnostic format |
| Report | 75% | 25% | SEC 10-K + PubMed abstracts | Consulting report tone, executive-summary style |
| Contract | 50% | 50% | CUAD + SEC EX-10 | Short-form NDAs, SaaS SLAs, offer letters |
| Schedule | 15% | 85% | GitHub dated issues (weak) | Calendar coordination, rescheduling, meeting chains |
| **Overall** | **~65%** | **~35%** | — | Synthetic fills tails where public coverage is thin |

### 2b. Why 65/35

- Public-heavy ≈ grounds in real distributional realism, saves $ on synthesis
- Synthetic ≈ 35% fills: modern vocabulary, domain gaps (schedule), Hexa-specific lexicon, Korean/bilingual cases (anima is KO-first), and keyword-target coverage (mimic r10 approach for hire_sim gate)

### 2c. Synthetic generation recipe (per r10 pattern)

- Use Claude Sonnet 4 (anthropic API, ~$3 per 1M output tokens) for 100M tokens total synthetic = ~$300 max
- Alternative: Qwen 2.5 72B on H100 pod (≈$6/M output token-equivalent in H100-hour cost) = ~$600 — **skip, API is cheaper**
- Template per r10: `{persona} × {intent} × {domain} × {format-template}` — per-domain 10K+ unique (persona, intent) tuples required to avoid memorization

---

## 3. Token Accounting — What is Achievable

### 3a. Public-only ceiling

| Domain | Source | Realistic tokens extractable |
|---|---|---:|
| Email | Enron EDO (after dedup + PII strip) | 100–140M |
| Meeting | AMI only | 8–12M |
| Code review | MS CodeReviewer filter | 20–40M |
| Report | SEC 10-K sample + PubMed (2 GB sample) | 400–500M |
| Contract | CUAD + SEC EX-10 filter (1%) | 30–60M |
| Schedule | GitHub issue regex subset | 5–10M |
| **Subtotal (public)** | | **560–760M tokens** |

### 3b. Planned mix for training (100M–300M token target)

Deliberately **downsample public** + **inject synthetic** to achieve domain balance. ALM generalizes better from balanced distribution than from dominant-domain skew.

| Domain | Target | Public cap | Synthetic | Sum |
|---|---:|---:|---:|---:|
| Email | 40M | 24M (Enron sample) | 16M | 40M |
| Meeting | 20M | 14M (AMI) | 6M | 20M |
| Code review | 30M | 25M (MSCR sample) | 5M | 30M |
| Report | 40M | 30M (SEC sample) | 10M | 40M |
| Contract | 30M | 15M (CUAD+SEC EX-10) | 15M | 30M |
| Schedule | 20M | 3M (GH filter) | 17M | 20M |
| **Total** | **180M** | **111M (62%)** | **69M (38%)** | **180M** |

**180M token target** sits mid-range of the 100M–300M user guideline — deliverable within the $144 compute envelope (§5).

### 3c. Dedup + quality filter

- Enron: remove corporate boilerplate (footer disclaimers, auto-signatures). Est. 20% shrink.
- AMI: keep transcription only, drop metadata/timestamps. Est. 5% shrink.
- MS CodeReviewer: filter by line-count (drop drive-by `+1`/`LGTM` single-line noise). Est. 40% shrink.
- SEC: filter for meaningful section text (Item 1A risk factors, MD&A — drop tables). Est. 70% shrink.

Filter cascade applied to §3a numbers → §3b cap column.

---

## 4. License Risk Matrix (Top 3 + others)

| Risk | Severity | Mitigation |
|---|---|---|
| **1. Avocado LDC licensing** | HIGH — blocks commercial serve | **DO NOT USE**. Email coverage must come from Enron + synthetic only. |
| **2. MS CodeReviewer upstream repo licenses** | MEDIUM — mined from public GitHub; individual repos may be GPL/non-permissive | Filter to permissive license repos only (MIT/Apache/BSD). Est. 60–70% retention of CodeReviewer data post-filter. Add a repo-license filter step in corpus build. |
| **3. SEC EDGAR rate limit + redistribution** | LOW (filings are public) — but SEC requires `<= 10 req/sec` and ethical bulk use | Use the Notre Dame cleaned dump (single bulk download) instead of scraping. Cite SEC as source. |
| 4. Enron "CC BY 3.0 US" attribution | LOW | Add attribution in corpus README + serve model card. |
| 5. CUAD CC BY 4.0 | LOW | Same, attribution. |
| 6. AMI CC BY 4.0 | LOW | Same, attribution. |
| 7. Claude API ToS for synthetic generation | MEDIUM — Anthropic ToS on training competitive models | Anthropic generally allows synthetic data for downstream task LoRA of non-competing models. Review ToS at runtime. If blocked, fall back to Qwen-72B self-generation. |
| 8. PII leakage (Enron PST) | MEDIUM | Strip email-address + phone regex before training. Names → replace with role tokens where feasible. |

**Verdict**: license profile is clean for commercial ALM serve if **(a)** Avocado skipped, **(b)** MS CodeReviewer repo-license-filtered, **(c)** attribution files maintained.

---

## 5. Training Setup — LoRA r11 (real-work) config

**Delta from r9/r10**:

| Param | r9 (v2.0 GA base) | r10 synth (planned) | **r11 real-work (this plan)** | Rationale |
|---|---|---|---|---|
| Base | Qwen2.5-14B-Instruct | r9 LoRA merged | **r9 LoRA merged** | Continued training on v2.0 GA for stable prior |
| Corpus | ~GB bilingual general | hire_sim_synthetic (200KB) | **~1 GB real-work mix (§3b)** | 180M tokens |
| Steps | 10000 | 1500 | **20000** | 180M tokens / (batch×seq) ≈ 0.45 epochs — adequate for LoRA |
| LR | 5e-6 | 2e-6 | **3e-6** | Between r9 & r10; larger corpus needs more updates than r10 |
| Batch | 8 | 4 | **8** | Back to r9 for throughput on full corpus |
| Seq | 1024 | 1024 | **2048** | Reports/contracts have long-form structure — essential |
| Grad accum | 1 | 1 | **2** | Effective batch 16 — stability on heterogeneous corpus |
| Warmup | 500 | 100 | **500** | Match scale |
| LoRA r | 32 | 16 | **32** | Broader adaptation — 6 domains need more capacity |
| LoRA alpha | 64 | 32 | **64** | 2× r (convention) |
| LoRA dropout | 0.0 | 0.05 | **0.05** | Anti-overfit on real data (has noise) |
| Eval every | 500 | 250 | **500** | Standard cadence |
| Save every | 2000 | 500 | **2000** | MFS quota rule (R-MFS-QUOTA) |
| Ckpt label | production | r10_hire_sim | **r11_realwork** | |
| Loss | CE + holo + phi + gwt | CE only | **CE + phi (0.005)** | Keep consciousness signal mild; main goal is task capability |

### 5a. Compute envelope

- Tokens/step: 8 batch × 2048 seq × 2 grad-accum = **32,768 tokens/step**
- Total tokens trained: 20,000 steps × 32,768 ≈ **655M tokens** (≈ 3.6 epochs over 180M corpus)
- H100 r9-measured throughput: ~60K–70K tok/sec at bf16 on 14B LoRA seq=2048 (from `r10_training_plan.md` scales × 2 for seq, ÷ 1.3 for grad accum overhead)
- ETA: 655M / 65K ≈ **10,080 sec = 2.8 hours pure compute**
- Wall time (model load + ckpt + R2 upload): **~4 hours**
- **Cost: ~$12 H100 ($2.99/hr × 4h)** — dramatically below the $144 earmark

### 5b. Why $12 not $144

The prior $144 earmark presumed 48 H100h. That estimate assumed:
- Seq 1024, batch 4 — r10-style small-step regime
- No throughput gain from seq 2048
- Possibly multi-epoch-on-300M-tokens (~8–10 epochs)
- Unknown architecture overhead

With concrete accounting from r9 throughput + planned hyperparams, **$10–15 is realistic** for the 20K-step r11 run. Budget $30 with 2× safety margin (convergence extension, re-start). **The corpus BUILD cost dominates**, not training.

### 5c. Corpus build cost (the real spend)

| Item | Spend | Time |
|---|---|---|
| Enron download + clean | $0 | 0.5 day compute Mac |
| AMI download + clean | $0 | 0.25 day |
| MS CodeReviewer + repo-license filter | $0 (compute) + $0 (GitHub API) | 0.5 day |
| SEC 10-K sample + section parse (edgar-crawler) | $0 | 0.5 day |
| CUAD + SEC EX-10 filter | $0 | 0.25 day |
| PubMed CC-subset download (optional, report domain) | $0 | 0.5 day |
| **Synthetic gen 69M tokens via Claude API** | **~$210** (at $3/M output tok) | 1–2 days (rate-limited) |
| PII scrub + dedup (minhash) | $0 | 0.5 day Mac |
| Final tokenize + shard | $0 | 0.25 day |
| **Total corpus build** | **~$210** | **3–5 days** wall |

### 5d. Total revised budget

| Phase | Time | $ |
|---|---|---|
| Corpus build (public + synth) | 3–5 days | $210 |
| r11 LoRA training | 4 h | $12–30 |
| R2 upload + smoke eval | 2 h | $3 |
| hire_sim regression | 0.5 day Mac | $0 |
| **Total** | **4–6 days** | **~$225–245** |

Prior estimate ($144 / 2–7 days): **under-budgeted training, over-budgeted schedule**. Updated: real blocker is **corpus build**, not GPU time.

### 5e. Expected eval delta

Baseline r9 RAW (no Path C) hire_sim completion: 0.5333
- With ≈180M real-work tokens, model internalizes domain-specific format + keyword patterns
- Projected r11 RAW: **0.75–0.85**
- Stretch goal (if synth tuning covers hire_sim keyword tail): **≥ 0.85** — Path C retired
- No-go trigger: RAW < 0.60 → catastrophic forgetting or corpus quality issue → diagnose before r12

---

## 6. Execution Plan — Next Actionable Steps (checklist)

Ordered by dependency. Do NOT start any step without explicit user go.

1. [ ] **User approval** of this plan (scope, budget, licensing posture)
2. [ ] **Create corpus build directory**: `training/corpus_realwork_r11/` (to be added; scripts only, no data yet)
3. [ ] **Download public sources** (sequential, ordered by size + risk):
    - [ ] CUAD (Atticus Project, ~15 MB, fastest, CC BY 4.0 — lowest risk) — `wget` from zenodo record 4595826
    - [ ] AMI Meeting Corpus transcripts (~200 MB, CC BY 4.0) — openslr.org/16/
    - [ ] Enron EDO (~8.6 GB) — enrondata.org EDO package
    - [ ] MS CodeReviewer `Comment_Generation.zip` (~GB) — zenodo 6900648
    - [ ] SEC EDGAR sample via edgar-crawler (limit to 10K filings, respect 10 req/sec)
    - [ ] PubMed CC-subset small sample (optional, 1–2 GB)
4. [ ] **License attribution pack**: create `training/corpus_realwork_r11/LICENSE_SOURCES.md` (all attributions, version strings)
5. [ ] **Filter + clean pipelines** (Mac, no GPU):
    - [ ] Enron PST → TXT + dedup + PII scrub
    - [ ] MS CodeReviewer repo-license filter (keep MIT/Apache/BSD)
    - [ ] SEC parse `Item 1A`, `MD&A`, `EX-10` sections only
    - [ ] AMI transcripts → plain text per speaker turn
6. [ ] **Synthetic generation plan** separate sub-doc (per-domain templates, persona library) before $ spend
7. [ ] **Synth gen via Claude API** in batched jobs (respect rate limits, $210 budget)
8. [ ] **Combine + shuffle + shard** → `training/corpus_realwork_r11.txt` + `.jsonl`
9. [ ] **Judge smoke**: run hire_sim_judge on 1K random samples from each domain (quality gate ≥ 95% pass like r10)
10. [ ] **Upload to pod** via rclone or scp (1 GB — manageable)
11. [ ] **Launch r11 LoRA** (20K steps, per §5 config) — separate session with explicit user approval
12. [ ] **R2 upload ckpt** → `r2:anima-models/alm14b/r11/step_20000/`
13. [ ] **Swap serve adapter** to r11 + hire_sim RAW regression
14. [ ] **Decision gate**:
    - RAW ≥ 0.85 → ship as v2.1 GA, retire Path C
    - RAW 0.75–0.84 → ship as v2.1 RC with Path C fallback, plan r12 fine-tune on tail
    - RAW < 0.75 → diagnose corpus (OOD domains?) before spending more

---

## 7. Open Questions (user decision before go)

- **Q1. Commercial posture** — do we commit to `COM*`-only corpus (rules out Avocado, restricts MS CodeReviewer)? **Recommend YES** — ALM serve roadmap has revenue, legal simplicity worth slight coverage loss.
- **Q2. Synthetic gen engine** — Claude API (~$210, fast, clean) vs Qwen-72B self-gen (~$600, no external dep). **Recommend Claude API** unless sovereignty is top priority.
- **Q3. Korean fraction** — anima is KO-first; do we allocate 20–30% of synth budget to KO corpus? **Recommend YES** (additional ~$60, 3× coverage vs English-only).
- **Q4. Path C retirement gate** — is 0.85 RAW the ship bar, or is 0.80 RAW + Path C retained also acceptable? **Recommend 0.85 RAW** to justify v2.1 tag.
- **Q5. Checkpoint cadence** — save every 2000 (MFS safe) or smaller for mid-run evals? **Recommend 2000** per the golden rule.

---

## 8. SSOT Linkage

Per `reference_algorithm_ssot.md`: register this plan in `shared/convergence/anima.json` under `ALM_14B_H100.items.talm_p4_1_corpus_plan` with status `planned` + commit hash of this file. Do not create parallel algorithm records.

Related documents:
- `training/deploy/r10_training_plan.md` (synthetic LoRA, prior cycle)
- `training/deploy/ALM_v2_RC_RELEASE.md` (v2.0 GA baseline + Path C)
- `training/deploy/hire_sim_alm_actual_20260416.json` (0.5333 RAW baseline)
- `training/deploy/hire_sim_alm_pathc_20260416.json` (0.8667 Path C ceiling)
- `shared/papers/v3_employee_capability_path_20260416.md` (§A.6 earmark of 48 H100h / $144)
- `training/deploy/clm_r4_corpus_plan.json` (prior corpus-plan template style)

---

## 9. Decision Summary (for user)

- **Proposed corpus size**: 180M tokens (in 100M–300M target band)
- **Mix**: ~65% public (Enron, AMI, MS CodeReviewer, SEC, CUAD) + ~35% synthetic (Claude API)
- **Skipped** (license): Avocado (restricted), ICSI Meeting (LDC-paid)
- **Wall time**: 4–6 days (corpus build dominates)
- **Total $**: ~$225–245 (was $144; revision up due to actual synth-gen cost, training is cheaper than earmarked)
- **Training**: LoRA r11 on r9 merged base, 20K steps, rank 32, 2048 seq, ~4h H100 ($12–30)
- **Expected eval**: hire_sim RAW 0.5333 → 0.75–0.85 (stretch goal Path C retire)
- **Next step (non-destructive)**: user approves → create corpus build directory + synth gen plan sub-doc in separate session
