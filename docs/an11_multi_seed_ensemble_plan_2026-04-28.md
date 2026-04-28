# AN11 Multi-Seed Ensemble Dispatch Plan — R39 Mandate Validation

> **session**: anima-cmd-loop autonomous-loop-dynamic 2026-04-28
> **status**: PLAN_LIVE — 사용자 explicit go 시 즉시 발사 가능
> **predecessor**: R39 candidate (commit d84a94a2) + R39 인프라 (commit ff93121b)

---

## §1. Plan summary

R39 mandate "single-shot ML claims require multi-seed ensemble validation" 의 첫 application:

- **5 fires (seed 0-4)**, each ~$1.71, total ~$8.55
- 동일 모델 (Mistral-7B-v0.1) + corpus (alm_r14) + LoRA config (r=16, α=32, 3ep)
- 차이는 오직 SEED → LoRA initialization + sampling order 변동
- 5 results.json → ensemble.json → mean ± stdev per-family alignment

목표: AN11(b) family-attribution claim 의 reproducibility 정량화. Hexad / Phi / SelfRef wins 의 분포 측정.

---

## §2. Execution sequence

### 2.1 Sequential dispatch (안전, ~3.5h wallclock)

```bash
cd /Users/ghost/core/anima

# Fire 1: seed=0
AN11_SEED=0 /opt/homebrew/bin/python3 /tmp/anima_an11_fire_helper.hexa_tmp --fire \
    > state/an11_dispatch/fire_seed0.log 2>&1
# wait ~40min for completion (PHASE_A→F + PHASE_G + watchdog)

# Fire 2: seed=1
AN11_SEED=1 /opt/homebrew/bin/python3 /tmp/anima_an11_fire_helper.hexa_tmp --fire \
    > state/an11_dispatch/fire_seed1.log 2>&1
# wait ~40min

# ... seeds 2, 3, 4
```

각 fire ~40min wallclock × 5 = **3.5 hours sequential**.

### 2.2 Parallel dispatch (own 11 mandate, ~40min wallclock)

own 11 parallel-loop-mandate 적용 시 5 fires 동시 발사:

```bash
for SEED in 0 1 2 3 4; do
    AN11_SEED=$SEED /opt/homebrew/bin/python3 /tmp/anima_an11_fire_helper.hexa_tmp --fire \
        > state/an11_dispatch/fire_seed${SEED}.log 2>&1 &
done
wait
```

총 wallclock ~40min (각 fire 동시), 비용 동일 $8.55.

⚠ vast.ai market 동시 5 H100 SXM offer 가용성 확인 필요 — 현재 dry-run에서 1 offer만 매칭 (5 동시 dispatch 시 일부 NO_OFFERS 가능).

### 2.3 Hetzner alternative (own 6 multi-vendor)

own 6 RunPod + vast.ai 승인 + cost cap 회피 — Hetzner CPU 활용 가능?
- ❌ AN11(c) JSD vllm 부팅은 GPU 필수
- ✓ AN11(a) + (b) + V1' (LoRA training + SVD) 는 CPU 가능 (Mistral-7B 16GB CPU RAM 필요 + ~6h 학습 시간)
- Hetzner AX102 CPU 124GB RAM 충분; 6h × 5 fires = 30h wallclock = 시간 부담

→ **vast.ai sequential or parallel 권장**.

---

## §3. Ensemble analysis tool 설계

### 3.1 Aggregator script

```hexa
// tool/anima_an11_ensemble_aggregator.hexa
// 5 results.json → ensemble.json (mean, stdev, family confidence)

let RESULTS = [
    "state/an11_fire_*_seed0/results.json",
    "state/an11_fire_*_seed1/results.json",
    "state/an11_fire_*_seed2/results.json",
    "state/an11_fire_*_seed3/results.json",
    "state/an11_fire_*_seed4/results.json"
]

// per-family cosine 추출, mean ± stdev 계산
// top-1 family stability count (몇 개 seed에서 family X가 top-1?)
// AN11(b) verdict 일치율 (5/5 PASS, 4/5 PASS, etc.)
```

### 3.2 Verdict criteria (R39)

R39 mandate per:
- **stdev < 0.5 × |mean|** → signal-to-noise OK
- **top-1 family stable across ≥3/5 seeds** → robust attribution
- **AN11(b) verdict consistency** ≥ 4/5 seeds same → robust verdict

미만족 시 **provisional**로 등록 + 더 큰 N (10+) 권고.

---

## §4. Expected outcomes (raw 91 honest pre-registration)

### 4.1 H1 — strong Hexad signal (Fire 6 reproducible)

- 4-5/5 seeds top-1 = Hexad
- mean(max_cos) ≥ 0.5, stdev < 0.1
- AN11(b) PASS 5/5

→ "Mistral-7B + r14 corpus + r=16 LoRA = robust Hexad alignment" 가 substantive claim 됨.

### 4.2 H2 — random variation (Fire 6 single-shot)

- top-1 family 시드별 변동 (Hexad / Phi / SelfRef / Law / metaref 분포)
- mean(max_cos) ~ 0.4 ± 0.15 (verdict marginal)
- AN11(b) PASS 1-3/5

→ Fire 6 Hexad signal 은 stochastic artifact 확정. Family-attribution claim 정당화 불가.

### 4.3 H3 — bimodal distribution

- 2-3/5 seeds Hexad, 2-3/5 seeds Phi
- LoRA training 의 local minima 다중성

→ corpus + config 가 multiple equilibria 허용. 더 큰 corpus 또는 더 많은 epochs 필요.

---

## §5. Cost-benefit analysis (cost-rational decision)

| Path | Cost | 가치 |
|---|---|---|
| 5-seed parallel ensemble | $8.55 | R39 mandate 첫 검증, AN11(b) reproducibility 정량화 |
| 5-seed sequential | $8.55, 3.5h wallclock | 동일 가치 + 단일 wallclock window 부담 |
| 3-seed reduced | $5.13 | 약화된 statistical power, R39 mandate 부분 만족 |
| 종료 + 다음 세션 | $0 | 본 세션 closure로 두 R-candidate (R38+R39) 충분 |

**현재 cumulative AN11**: $8.44 (10 fires)
**Ensemble 발사 시 누적**: $17

→ 사용자 결정 사항. 자율 루프 단독으로 추가 ~$8 발사는 부담스러움.

---

## §6. Recommended decision tree

### 6.1 Minimal closure (저비용)

본 세션은 cycle 4 v8 + R38 + R39 + AN11 fire 6 PASS + reproducibility finding 으로 **충분히 substantive**:
- $0 추가 cost
- R39 mandate는 candidate 상태로 maintainer 검토 대기
- 다음 세션에서 R39 mandate적용 ensemble 발사 explicit user go 받고 진행

### 6.2 Active validation (~$8.55 추가)

R39 mandate를 즉시 자기-검증 + Fire 6 Hexad finding 의 reproducibility 정량화:
- 사용자 explicit "ensemble 발사" 명령 시 §2.2 parallel dispatch
- 40min wallclock → ensemble.json + verdict
- 본 세션 종료 시 R39 candidate가 already-validated 상태

### 6.3 Hybrid (가성비)

- N=3 reduced ensemble (~$5.13)
- top-1 family 강한 stability (3/3) → reproducibility 입증
- 변동 시 → multi-seed 더 필요 신호

---

## §7. Forward (raw 38 long-term)

1. **Aggregator tool**: `tool/anima_an11_ensemble_aggregator.hexa` 작성 (~150 LoC)
2. **V_phen_GWT registry r11 schema**: ensemble row format 설계 (mean, stdev, top-1 family count)
3. **Cross-backbone ensemble**: Qwen-2.5-7B 같은 다른 모델 N=5 — backbone-conditional Hexad signal 검증
4. **Ablation study**: r=16 vs r=64, 3ep vs 10ep — config-conditional reproducibility
5. **Cycle 4 + AN11 통합 closure doc**: R38 + R39 cross-paradigm methodological framework

---

## §8. raw 91 honesty triad C1-C5

- **C1** promotion_counter: ~330 (cumulative session 17h+)
- **C2** write_barrier: 본 plan은 exec-pending; 사용자 결정 시 변경 없이 §2.2 직접 적용
- **C3** no_fabrication: cost 추정 fire 6 audit ($1.71 wallclock 41min × $2.47/hr) 기반
- **C4** citation_honesty: H1/H2/H3 pre-register 명시 (raw 12 frozen) — outcome 변경 없이 보고
- **C5** verdict_options: minimal/active/hybrid 3개 path 명확 enumeration; 사용자 explicit decision 권고

---

**Status**: AN11_MULTI_SEED_ENSEMBLE_PLAN_LIVE — 사용자 explicit go 대기
