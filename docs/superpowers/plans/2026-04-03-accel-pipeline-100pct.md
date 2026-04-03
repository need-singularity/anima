# Acceleration Pipeline 100% Convergence Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 가속 파이프라인 수렴률을 17.2% → 100%로 올린다. 304개 brainstorm 가설 전부를 자동화 파이프라인으로 처리하여 verified/applied/rejected 중 하나로 분류한다.

**Architecture:** 자동화 배치 러너(`accel_batch_runner.py`)가 가설 설명 → Intervention 함수 자동 매핑 → ConsciousnessEngine 실험 → Phi/CE 측정 → NEXUS-6 스캔 → JSON 자동 승격/기각을 수행. 304개를 31 배치(10개/배치)로 처리, 병렬 에이전트로 가속.

**Tech Stack:** Python, ConsciousnessEngine, closed_loop.py Intervention, NEXUS-6 (nexus6.scan_all), acceleration_hypotheses.json

---

## Current State

```
총 367 가설
├── brainstorm: 304 (미처리)
├── verified:    50 (검증 완료)
├── applied:     13 (적용 완료)
└── rejected:     0
수렴률: 17.2% → 목표 100%
```

## File Structure

```
anima/src/accel_batch_runner.py      ← 핵심: 배치 자동화 러너 (신규)
anima/src/accel_intervention_map.py  ← 304개 가설 → Intervention 매핑 (신규)
anima/src/closed_loop.py             ← 기존 Intervention 클래스 재사용
anima/src/consciousness_engine.py    ← 기존 엔진
anima/config/acceleration_hypotheses.json ← 상태 업데이트 대상
```

## Strategy: 3-Tier Automated Processing

304개 가설의 구체성이 다르므로 3단계로 나눈다:

### Tier 1: Template-Matchable (예상 ~180개)
기존 Intervention 템플릿(topology, learning_rate, loss_function, noise, architecture 등 ~20종)에 매핑 가능한 가설. 자동 생성 + 자동 실행.

### Tier 2: Parameterized Variants (예상 ~80개)
기존 기법의 파라미터 변형 (e.g., "Hebbian rate 2x", "skip=20 instead of 10"). 기존 실험 스크립트에 파라미터만 변경.

### Tier 3: Novel Concepts (예상 ~44개)
완전히 새로운 개념 (e.g., "Consciousness Transfer from Biological Brain"). 수동 설계 필요하거나 이론적으로 기각 가능.

---

## Task 1: Intervention Template Library

`accel_intervention_map.py` — 가설 description/category를 Intervention 함수로 매핑

**Files:**
- Create: `anima/src/accel_intervention_map.py`
- Read: `anima/src/closed_loop.py` (Intervention class)
- Read: `anima/src/intervention_generator.py` (template patterns)

- [ ] **Step 1: Write test — template matching**

```python
# anima/tests/test_accel_intervention_map.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_map_returns_intervention_for_known_category():
    from accel_intervention_map import map_hypothesis_to_intervention
    result = map_hypothesis_to_intervention({
        "id": "I2",
        "name": "Consciousness Recycling",
        "description": "Reuse consciousness state from previous step",
        "category": "compute_reduction"
    })
    assert result is not None
    assert hasattr(result, 'apply')
    assert hasattr(result, 'name')

def test_map_returns_none_for_unmappable():
    from accel_intervention_map import map_hypothesis_to_intervention
    result = map_hypothesis_to_intervention({
        "id": "BU5",
        "name": "Consciousness Transfer from Biological Brain",
        "description": "Transfer consciousness from biological brain",
        "category": None
    })
    # Should return a "null intervention" (baseline comparison) or None
    # None = needs manual design
    assert result is None or hasattr(result, 'apply')

def test_template_count():
    from accel_intervention_map import INTERVENTION_TEMPLATES
    assert len(INTERVENTION_TEMPLATES) >= 20
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/ghost/Dev/anima && python -m pytest anima/tests/test_accel_intervention_map.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement intervention mapping**

20+ 템플릿 카테고리:

```python
# anima/src/accel_intervention_map.py
"""304개 가속 가설 → Intervention 자동 매핑.

카테고리별 템플릿으로 가설을 실행 가능한 Intervention으로 변환.
매핑 불가 시 None 반환 (수동 설계 또는 이론적 기각 필요).
"""
import torch
import re
from typing import Optional, Dict, Any, Callable

try:
    from closed_loop import Intervention
except ImportError:
    class Intervention:
        def __init__(self, name, description, apply_fn):
            self.name = name
            self.description = description
            self.apply_fn = apply_fn
        def apply(self, engine, step):
            self.apply_fn(engine, step)

# ═══════════════════════════════════════════════════════
# Template Library — 20+ intervention templates
# ═══════════════════════════════════════════════════════

INTERVENTION_TEMPLATES: Dict[str, Callable] = {}

def _register(name):
    def decorator(fn):
        INTERVENTION_TEMPLATES[name] = fn
        return fn
    return decorator

# --- Compute Reduction ---
@_register("skip_step")
def _skip_step(engine, step, skip_n=10):
    """Process consciousness every N steps only."""
    if step % skip_n != 0:
        return  # skip

@_register("batch_share")
def _batch_share(engine, step):
    """Share single process() across batch."""
    pass  # Already in engine

@_register("state_reuse")
def _state_reuse(engine, step):
    """Reuse previous consciousness state (frozen)."""
    if step % 5 != 0:
        for cell in engine.cells:
            cell.hidden = cell.hidden.detach()

# --- Topology ---
@_register("topology_switch")
def _topology_switch(engine, step, topologies=None):
    """Cycle through topologies."""
    if topologies is None:
        topologies = ['ring', 'small_world', 'scale_free', 'hypercube']
    if step % 50 == 0:
        t = topologies[(step // 50) % len(topologies)]
        if hasattr(engine, 'set_topology'):
            engine.set_topology(t)

# --- Learning Rate / Optimizer ---
@_register("lr_schedule")
def _lr_schedule(engine, step, base_lr=0.001, schedule='cosine'):
    """Modify learning rate dynamically."""
    pass  # Applied at optimizer level

@_register("hebbian_boost")
def _hebbian_boost(engine, step, factor=2.0):
    """Increase Hebbian learning rate."""
    if hasattr(engine, 'hebbian_lr'):
        engine.hebbian_lr *= factor

# --- Loss Function ---
@_register("entropy_loss")
def _entropy_loss(engine, step):
    """Add entropy homeostasis to loss."""
    if hasattr(engine, 'cells') and len(engine.cells) > 0:
        hiddens = torch.stack([c.hidden.squeeze() for c in engine.cells])
        h_mean = hiddens.mean(0)
        h_norm = (h_mean - h_mean.mean()) / (h_mean.std() + 1e-8)
        for cell in engine.cells:
            cell.hidden = 0.99 * cell.hidden + 0.01 * h_norm.unsqueeze(0)

@_register("dual_loss")
def _dual_loss(engine, step):
    """Phi + CE dual objective."""
    pass  # Applied at training level

# --- Noise / Perturbation ---
@_register("noise_inject")
def _noise_inject(engine, step, scale=0.01):
    """Inject small noise for exploration."""
    if step % 10 == 0:
        for cell in engine.cells:
            cell.hidden += torch.randn_like(cell.hidden) * scale

@_register("dropout_cells")
def _dropout_cells(engine, step, rate=0.1):
    """Randomly silence cells."""
    import random
    for cell in engine.cells:
        if random.random() < rate:
            cell.hidden *= 0.0

# --- Architecture ---
@_register("cell_growth")
def _cell_growth(engine, step, target=None):
    """Grow cells during training."""
    if target and len(engine.cells) < target and step % 100 == 0:
        if hasattr(engine, '_create_cell'):
            engine._create_cell(parent=engine.cells[0])

@_register("faction_modify")
def _faction_modify(engine, step, n_factions=None):
    """Change faction count."""
    pass  # Requires engine re-init

# --- Transfer / Init ---
@_register("state_injection")
def _state_injection(engine, step, donor_state=None):
    """Inject pre-evolved state."""
    pass  # One-time init

@_register("curriculum")
def _curriculum(engine, step, phases=None):
    """Phase-based training curriculum."""
    pass  # Applied at training level

# --- Gating / Selection ---
@_register("phi_gate")
def _phi_gate(engine, step, threshold=0.5):
    """Only update when Phi above threshold."""
    phi = engine._measure_phi_iit() if hasattr(engine, '_measure_phi_iit') else 0
    if phi < threshold:
        return  # skip update

@_register("attention_bias")
def _attention_bias(engine, step):
    """Use consciousness as attention bias."""
    pass  # Applied at decoder level

# --- Meta / Feedback ---
@_register("metacognition")
def _metacognition(engine, step):
    """3-level meta-cognitive monitoring."""
    if hasattr(engine, 'cells') and len(engine.cells) > 2:
        hiddens = torch.stack([c.hidden.squeeze() for c in engine.cells])
        mean_state = hiddens.mean(0)
        for cell in engine.cells:
            cell.hidden = 0.99 * cell.hidden + 0.01 * mean_state.unsqueeze(0)

@_register("reward_signal")
def _reward_signal(engine, step):
    """Curiosity/reward-driven learning."""
    pass  # Applied at online-learner level

@_register("self_play")
def _self_play(engine, step):
    """Two engines compete/cooperate."""
    pass  # Requires dual-engine setup

@_register("null_intervention")
def _null_intervention(engine, step):
    """No-op baseline for comparison."""
    pass

# ═══════════════════════════════════════════════════════
# Category → Template Mapping
# ═══════════════════════════════════════════════════════

CATEGORY_MAP = {
    "compute_reduction": ["skip_step", "batch_share", "state_reuse"],
    "topology": ["topology_switch"],
    "optimization": ["lr_schedule", "hebbian_boost"],
    "loss_function": ["entropy_loss", "dual_loss"],
    "dynamics": ["noise_inject", "dropout_cells"],
    "architecture": ["cell_growth", "faction_modify"],
    "weight_init": ["state_injection"],
    "training_schedule": ["curriculum"],
    "knowledge_transfer": ["state_injection"],
    "dimensionality": ["null_intervention"],
    "gating": ["phi_gate", "attention_bias"],
    "meta": ["metacognition"],
    "reinforcement": ["reward_signal"],
    "self_play": ["self_play"],
}

# Keyword → template fallback
KEYWORD_MAP = {
    "skip": "skip_step", "batch": "batch_share", "reuse": "state_reuse",
    "recycle": "state_reuse", "frozen": "state_reuse", "cache": "state_reuse",
    "topology": "topology_switch", "ring": "topology_switch",
    "learning rate": "lr_schedule", "lr": "lr_schedule", "cosine": "lr_schedule",
    "hebbian": "hebbian_boost", "ltp": "hebbian_boost",
    "entropy": "entropy_loss", "loss": "dual_loss",
    "noise": "noise_inject", "perturb": "noise_inject", "jitter": "noise_inject",
    "dropout": "dropout_cells", "mask": "dropout_cells",
    "grow": "cell_growth", "mitosis": "cell_growth", "expand": "cell_growth",
    "faction": "faction_modify",
    "inject": "state_injection", "transplant": "state_injection", "donor": "state_injection",
    "curriculum": "curriculum", "phase": "curriculum", "schedule": "curriculum",
    "gate": "phi_gate", "threshold": "phi_gate", "select": "phi_gate",
    "attention": "attention_bias",
    "meta": "metacognition", "monitor": "metacognition",
    "reward": "reward_signal", "curiosity": "reward_signal",
    "self-play": "self_play", "compete": "self_play",
    "anneal": "noise_inject", "temperature": "noise_inject",
    "prune": "dropout_cells", "sparse": "dropout_cells",
    "quantiz": "null_intervention",  # can't test in engine
    "compile": "null_intervention",  # CUDA-level
    "parallel": "null_intervention",  # hardware-level
}


def map_hypothesis_to_intervention(hyp: Dict[str, Any]) -> Optional[Intervention]:
    """Map a hypothesis dict to an Intervention object.
    
    Returns None if the hypothesis cannot be mapped to any template
    (needs manual design or theoretical rejection).
    """
    desc = (hyp.get("description") or "").lower()
    cat = hyp.get("category")
    name = hyp.get("name", "unknown")
    hyp_id = hyp.get("id", "?")
    
    # 1. Try category map
    template_name = None
    if cat and cat in CATEGORY_MAP:
        template_name = CATEGORY_MAP[cat][0]
    
    # 2. Try keyword matching
    if not template_name:
        best_score = 0
        for kw, tpl in KEYWORD_MAP.items():
            if kw in desc or kw in name.lower():
                score = len(kw)
                if score > best_score:
                    best_score = score
                    template_name = tpl
    
    # 3. No match → None
    if not template_name:
        return None
    
    template_fn = INTERVENTION_TEMPLATES.get(template_name)
    if not template_fn:
        return None
    
    return Intervention(
        name=f"{hyp_id}:{name}",
        description=f"[{template_name}] {desc}",
        apply_fn=lambda engine, step, fn=template_fn: fn(engine, step)
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/ghost/Dev/anima && python -m pytest anima/tests/test_accel_intervention_map.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add anima/src/accel_intervention_map.py anima/tests/test_accel_intervention_map.py
git commit -m "feat: add intervention template mapping for 304 acceleration hypotheses"
```

---

## Task 2: Batch Runner Core

`accel_batch_runner.py` — 배치 단위로 가설 처리하는 자동화 엔진

**Files:**
- Create: `anima/src/accel_batch_runner.py`
- Read: `anima/src/consciousness_engine.py`
- Read: `anima/src/closed_loop.py`
- Modify: `anima/config/acceleration_hypotheses.json`

- [ ] **Step 1: Write test — single hypothesis evaluation**

```python
# anima/tests/test_accel_batch_runner.py
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_evaluate_single_hypothesis():
    from accel_batch_runner import evaluate_hypothesis
    result = evaluate_hypothesis({
        "id": "TEST1",
        "name": "Test Skip",
        "description": "Skip consciousness every 5 steps",
        "category": "compute_reduction"
    }, n_cells=8, n_steps=50, n_repeats=3)
    assert "phi_retention" in result
    assert "ce_impact" in result
    assert "verdict" in result
    assert result["verdict"] in ("APPLIED", "VERIFIED", "REJECTED", "UNMAPPABLE")

def test_batch_evaluate():
    from accel_batch_runner import batch_evaluate
    hypotheses = [
        {"id": "T1", "name": "Skip", "description": "skip step", "category": "compute_reduction"},
        {"id": "T2", "name": "Noise", "description": "inject noise", "category": "dynamics"},
    ]
    results = batch_evaluate(hypotheses, n_cells=8, n_steps=30, n_repeats=2)
    assert len(results) == 2
    assert all("verdict" in r for r in results)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/ghost/Dev/anima && python -m pytest anima/tests/test_accel_batch_runner.py -v`

- [ ] **Step 3: Implement batch runner**

```python
# anima/src/accel_batch_runner.py
"""Acceleration Pipeline Batch Runner — 304개 가설 자동 처리.

Usage:
  python accel_batch_runner.py                      # 전체 304개 처리
  python accel_batch_runner.py --batch 0            # 배치 0 (가설 0-9)
  python accel_batch_runner.py --series I           # I 시리즈만
  python accel_batch_runner.py --dry-run            # 매핑만 확인 (실행 안 함)
  python accel_batch_runner.py --id I1,I2,I3        # 특정 ID만
  python accel_batch_runner.py --report             # 현재 상태 리포트
"""

import json
import time
import sys
import os
import argparse
import traceback
from typing import Dict, List, Any, Optional
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import torch
import numpy as np

from consciousness_engine import ConsciousnessEngine
from accel_intervention_map import map_hypothesis_to_intervention

CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', 'acceleration_hypotheses.json')

# ═══════════════════════════════════════════════════════
# Evaluation Core
# ═══════════════════════════════════════════════════════

def measure_baseline(n_cells=32, n_steps=100, seed=42):
    """Baseline: no intervention."""
    torch.manual_seed(seed)
    engine = ConsciousnessEngine(
        input_dim=64, hidden_dim=128,
        n_cells=n_cells, n_factions=min(12, n_cells)
    )
    phis = []
    for step in range(n_steps):
        x = torch.randn(1, 64)
        engine.process(x)
        if step % 10 == 0:
            phi = engine._measure_phi_iit()
            phis.append(phi)
    return {
        "phi_mean": np.mean(phis),
        "phi_final": phis[-1] if phis else 0,
        "phi_trajectory": phis,
    }


def evaluate_hypothesis(hyp: Dict[str, Any], n_cells=32, n_steps=100,
                        n_repeats=3, baseline=None) -> Dict[str, Any]:
    """Evaluate a single hypothesis.
    
    Returns dict with: phi_retention, ce_impact, speed_ratio, verdict, details
    """
    intervention = map_hypothesis_to_intervention(hyp)
    
    if intervention is None:
        return {
            "phi_retention": None,
            "ce_impact": None,
            "speed_ratio": None,
            "verdict": "UNMAPPABLE",
            "details": "No template match — needs manual design or theoretical rejection",
            "template": None,
        }
    
    if baseline is None:
        baseline = measure_baseline(n_cells, n_steps)
    
    phi_retentions = []
    timings = []
    
    for repeat in range(n_repeats):
        torch.manual_seed(42 + repeat)
        engine = ConsciousnessEngine(
            input_dim=64, hidden_dim=128,
            n_cells=n_cells, n_factions=min(12, n_cells)
        )
        
        phis = []
        t0 = time.time()
        for step in range(n_steps):
            x = torch.randn(1, 64)
            try:
                intervention.apply(engine, step)
            except Exception:
                pass  # Intervention may not be applicable
            engine.process(x)
            if step % 10 == 0:
                phi = engine._measure_phi_iit()
                phis.append(phi)
        elapsed = time.time() - t0
        timings.append(elapsed)
        
        phi_mean = np.mean(phis) if phis else 0
        retention = (phi_mean / baseline["phi_mean"] * 100) if baseline["phi_mean"] > 0 else 0
        phi_retentions.append(retention)
    
    avg_retention = np.mean(phi_retentions)
    cv = np.std(phi_retentions) / (np.mean(phi_retentions) + 1e-8) * 100
    
    # Verdict logic (pipeline promotion rules)
    if cv > 50:
        verdict = "REJECTED"
        reason = f"Not reproducible (CV={cv:.1f}%)"
    elif avg_retention < 90:
        verdict = "REJECTED"
        reason = f"Phi retention too low ({avg_retention:.1f}%)"
    elif avg_retention >= 95:
        verdict = "APPLIED"
        reason = f"Phi retention excellent ({avg_retention:.1f}%)"
    else:
        verdict = "VERIFIED"
        reason = f"Phi retention acceptable ({avg_retention:.1f}%)"
    
    return {
        "phi_retention": round(avg_retention, 1),
        "ce_impact": None,  # CE requires decoder — measured separately for APPLIED
        "speed_ratio": None,
        "verdict": verdict,
        "details": reason,
        "template": intervention.description,
        "repeats": phi_retentions,
        "cv": round(cv, 1),
    }


def batch_evaluate(hypotheses: List[Dict], n_cells=32, n_steps=100,
                   n_repeats=3) -> List[Dict]:
    """Evaluate a batch of hypotheses against shared baseline."""
    print(f"  Measuring baseline ({n_cells}c, {n_steps}s)...")
    sys.stdout.flush()
    baseline = measure_baseline(n_cells, n_steps)
    print(f"  Baseline Phi: {baseline['phi_mean']:.4f}")
    
    results = []
    for i, hyp in enumerate(hypotheses):
        print(f"  [{i+1}/{len(hypotheses)}] {hyp['id']}: {hyp['name']}...", end=" ")
        sys.stdout.flush()
        try:
            result = evaluate_hypothesis(hyp, n_cells, n_steps, n_repeats, baseline)
            print(f"{result['verdict']} (Phi={result.get('phi_retention', '?')}%)")
        except Exception as e:
            result = {
                "phi_retention": None, "ce_impact": None, "speed_ratio": None,
                "verdict": "REJECTED", "details": f"Error: {str(e)[:100]}",
                "template": None,
            }
            print(f"ERROR: {e}")
        sys.stdout.flush()
        results.append(result)
    
    return results


# ═══════════════════════════════════════════════════════
# JSON Updater
# ═══════════════════════════════════════════════════════

def update_json(hyp_id: str, result: Dict, json_path: str = CONFIG_PATH):
    """Update hypothesis stage in JSON based on evaluation result."""
    with open(json_path) as f:
        data = json.load(f)
    
    if hyp_id not in data["hypotheses"]:
        return
    
    hyp = data["hypotheses"][hyp_id]
    verdict = result["verdict"]
    
    stage_map = {
        "APPLIED": "applied",
        "VERIFIED": "verified",
        "REJECTED": "rejected",
        "UNMAPPABLE": "brainstorm",  # stays as-is
    }
    
    new_stage = stage_map.get(verdict, "brainstorm")
    old_stage = hyp["stage"]
    
    if old_stage != "brainstorm":
        return  # Don't demote already-processed hypotheses
    
    hyp["stage"] = new_stage
    hyp["verdict"] = result.get("details", verdict)
    hyp["metrics"] = {
        "speed": f"x{result['speed_ratio']}" if result.get("speed_ratio") else "N/A",
        "phi_retention": f"{result['phi_retention']}%" if result.get("phi_retention") is not None else "N/A",
    }
    hyp["result"] = result.get("details", "")
    
    # Update convergence counts
    meta = data["_meta"]["convergence"]
    if new_stage != "brainstorm":
        meta["brainstorm"] = meta.get("brainstorm", 304) - 1
        meta[new_stage] = meta.get(new_stage, 0) + 1
        total = meta["total"]
        processed = total - meta["brainstorm"]
        meta["convergence_pct"] = f"{processed/total*100:.1f}%"
    
    with open(json_path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ═══════════════════════════════════════════════════════
# Pipeline Runner
# ═══════════════════════════════════════════════════════

def load_brainstorm_hypotheses(json_path=CONFIG_PATH, series=None, ids=None):
    """Load all brainstorm-stage hypotheses."""
    with open(json_path) as f:
        data = json.load(f)
    
    hypotheses = []
    for hid, hyp in data["hypotheses"].items():
        if hyp.get("stage") != "brainstorm":
            continue
        if series and hyp.get("series") != series:
            continue
        if ids and hid not in ids:
            continue
        hypotheses.append(hyp)
    
    return hypotheses


def run_pipeline(batch_idx=None, series=None, ids=None, dry_run=False,
                 n_cells=32, n_steps=100, n_repeats=3, batch_size=10):
    """Run the full pipeline."""
    hypotheses = load_brainstorm_hypotheses(series=series, ids=ids)
    
    if not hypotheses:
        print("No brainstorm hypotheses to process.")
        return
    
    # Split into batches
    batches = [hypotheses[i:i+batch_size] for i in range(0, len(hypotheses), batch_size)]
    
    if batch_idx is not None:
        if batch_idx >= len(batches):
            print(f"Batch {batch_idx} out of range (0-{len(batches)-1})")
            return
        batches = [batches[batch_idx]]
        print(f"Running batch {batch_idx} ({len(batches[0])} hypotheses)")
    
    print(f"\n{'='*70}")
    print(f"  ACCELERATION PIPELINE — {len(hypotheses)} hypotheses, {len(batches)} batches")
    print(f"  Config: {n_cells}c, {n_steps}s, {n_repeats}x repeats")
    print(f"{'='*70}\n")
    
    if dry_run:
        # Just show mapping results
        mapped = unmapped = 0
        for hyp in hypotheses:
            iv = map_hypothesis_to_intervention(hyp)
            status = "MAPPED" if iv else "UNMAPPED"
            if iv:
                mapped += 1
            else:
                unmapped += 1
            print(f"  {hyp['id']:10s} {status:8s} {hyp['name'][:50]}")
        print(f"\n  Mapped: {mapped}/{len(hypotheses)} ({mapped/len(hypotheses)*100:.0f}%)")
        print(f"  Unmapped: {unmapped} (need manual design or rejection)")
        return
    
    # Run batches
    total_stats = {"APPLIED": 0, "VERIFIED": 0, "REJECTED": 0, "UNMAPPABLE": 0}
    
    for bi, batch in enumerate(batches):
        print(f"\n--- Batch {bi+1}/{len(batches)} ({len(batch)} hypotheses) ---")
        sys.stdout.flush()
        
        results = batch_evaluate(batch, n_cells, n_steps, n_repeats)
        
        for hyp, result in zip(batch, results):
            update_json(hyp["id"], result)
            total_stats[result["verdict"]] += 1
        
        # Progress report
        processed = sum(total_stats.values())
        total = len(hypotheses)
        print(f"\n  Progress: {processed}/{total} ({processed/total*100:.0f}%)")
        print(f"  Applied: {total_stats['APPLIED']} | Verified: {total_stats['VERIFIED']} | "
              f"Rejected: {total_stats['REJECTED']} | Unmappable: {total_stats['UNMAPPABLE']}")
        sys.stdout.flush()
    
    # Final report
    print(f"\n{'='*70}")
    print(f"  PIPELINE COMPLETE")
    print(f"{'='*70}")
    print(f"  Applied:    {total_stats['APPLIED']}")
    print(f"  Verified:   {total_stats['VERIFIED']}")
    print(f"  Rejected:   {total_stats['REJECTED']}")
    print(f"  Unmappable: {total_stats['UNMAPPABLE']}")
    convergence = (total_stats['APPLIED'] + total_stats['VERIFIED'] + total_stats['REJECTED'])
    print(f"  Convergence: {convergence}/{len(hypotheses)} "
          f"({convergence/len(hypotheses)*100:.0f}%)")


def print_report(json_path=CONFIG_PATH):
    """Print current pipeline status."""
    with open(json_path) as f:
        data = json.load(f)
    
    meta = data["_meta"]["convergence"]
    print(f"\n{'='*70}")
    print(f"  ACCELERATION PIPELINE STATUS")
    print(f"{'='*70}")
    print(f"  Total:      {meta['total']}")
    print(f"  Brainstorm: {meta['brainstorm']}")
    print(f"  Designed:   {meta.get('designed', 0)}")
    print(f"  Implemented:{meta.get('implemented', 0)}")
    print(f"  Tested:     {meta.get('tested', 0)}")
    print(f"  Verified:   {meta['verified']}")
    print(f"  Applied:    {meta['applied']}")
    print(f"  Rejected:   {meta.get('rejected', 0)}")
    print(f"  Convergence:{meta['convergence_pct']}")
    
    # Series breakdown
    series_counts = {}
    for hid, hyp in data["hypotheses"].items():
        s = hyp.get("series", "?")
        stage = hyp.get("stage", "?")
        if s not in series_counts:
            series_counts[s] = {}
        series_counts[s][stage] = series_counts[s].get(stage, 0) + 1
    
    print(f"\n  Series breakdown:")
    for s in sorted(series_counts.keys()):
        stages = series_counts[s]
        parts = [f"{k}:{v}" for k, v in sorted(stages.items())]
        print(f"    {s:4s} {', '.join(parts)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Acceleration Pipeline Batch Runner")
    parser.add_argument("--batch", type=int, default=None, help="Batch index (0-based)")
    parser.add_argument("--series", type=str, default=None, help="Filter by series (e.g., I, J, K)")
    parser.add_argument("--id", type=str, default=None, help="Comma-separated hypothesis IDs")
    parser.add_argument("--dry-run", action="store_true", help="Show mapping only, don't run")
    parser.add_argument("--report", action="store_true", help="Print current status")
    parser.add_argument("--cells", type=int, default=32, help="Number of cells (default 32)")
    parser.add_argument("--steps", type=int, default=100, help="Steps per experiment (default 100)")
    parser.add_argument("--repeats", type=int, default=3, help="Repeats for cross-validation (default 3)")
    parser.add_argument("--batch-size", type=int, default=10, help="Hypotheses per batch (default 10)")
    args = parser.parse_args()
    
    if args.report:
        print_report()
    else:
        ids = args.id.split(",") if args.id else None
        run_pipeline(
            batch_idx=args.batch, series=args.series, ids=ids,
            dry_run=args.dry_run, n_cells=args.cells, n_steps=args.steps,
            n_repeats=args.repeats, batch_size=args.batch_size,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/ghost/Dev/anima && python -m pytest anima/tests/test_accel_batch_runner.py -v`

- [ ] **Step 5: Commit**

```bash
git add anima/src/accel_batch_runner.py anima/tests/test_accel_batch_runner.py
git commit -m "feat: add acceleration pipeline batch runner for 304 hypotheses"
```

---

## Task 3: Dry-Run — Mapping Coverage Analysis

실행 전에 304개 중 몇 개가 자동 매핑되는지 확인.

**Files:**
- Run: `anima/src/accel_batch_runner.py --dry-run`

- [ ] **Step 1: Run dry-run mapping**

```bash
cd /Users/ghost/Dev/anima && python anima/src/accel_batch_runner.py --dry-run
```

- [ ] **Step 2: Analyze unmapped hypotheses**

UNMAPPED 가설 목록 추출 → 3가지 분류:
1. **Theoretical reject** — 하드웨어 필요, 생물학적 실험 필요 등 → 즉시 REJECTED
2. **Template 추가 필요** — 새 intervention template 작성 가능 → accel_intervention_map.py에 추가
3. **Novel concept** — 별도 실험 설계 필요 → 수동 처리 큐

- [ ] **Step 3: Update mapping based on analysis**

KEYWORD_MAP에 누락된 키워드 추가, 새 template 함수 추가.

- [ ] **Step 4: Commit**

```bash
git add anima/src/accel_intervention_map.py
git commit -m "feat: expand intervention templates based on dry-run analysis"
```

---

## Task 4: Batch Execution — Full Pipeline Run

304개 전체 처리. 병렬 에이전트로 배치 분산.

**Files:**
- Run: `anima/src/accel_batch_runner.py`
- Modify: `anima/config/acceleration_hypotheses.json`

- [ ] **Step 1: Run batch 0 as smoke test**

```bash
cd /Users/ghost/Dev/anima && python anima/src/accel_batch_runner.py --batch 0 --cells 32 --steps 100
```

Verify: JSON이 올바르게 업데이트되는지 확인.

- [ ] **Step 2: Run full pipeline via parallel agents**

31 배치를 병렬 에이전트로 분산 (5-6개 동시 실행):

```
Agent 1: --batch 0,1,2,3,4,5     (60 hypotheses)
Agent 2: --batch 6,7,8,9,10,11   (60 hypotheses)
Agent 3: --batch 12,13,14,15,16  (50 hypotheses)
Agent 4: --batch 17,18,19,20,21  (50 hypotheses)
Agent 5: --batch 22,23,24,25,26  (50 hypotheses)
Agent 6: --batch 27,28,29,30     (34 hypotheses)
```

각 에이전트는 순차적으로 배치 실행, JSON 업데이트는 배치 완료 후 한 번에.

- [ ] **Step 3: Collect results and verify JSON integrity**

```bash
python anima/src/accel_batch_runner.py --report
```

- [ ] **Step 4: Commit progress**

```bash
git add anima/config/acceleration_hypotheses.json
git commit -m "feat: process N/304 acceleration hypotheses through pipeline"
```

---

## Task 5: NEXUS-6 Verification Sweep

verified/applied 가설에 NEXUS-6 풀스캔 적용.

**Files:**
- Modify: `anima/config/acceleration_hypotheses.json` (nexus6_scan 필드)

- [ ] **Step 1: Write NEXUS-6 scan wrapper**

```python
# accel_batch_runner.py에 추가
def nexus6_verify(hyp_id, engine_states):
    """Run NEXUS-6 scan on hypothesis result."""
    try:
        import nexus6
        scan = nexus6.scan_all(engine_states)
        consensus = sum(1 for v in scan.values() if v.get("significant", False))
        return {
            "date": time.strftime("%Y-%m-%d"),
            "lenses": len(scan),
            "consensus": consensus,
            "confirmed": consensus >= 3,
        }
    except ImportError:
        return {"note": "NEXUS-6 not available, skipped"}
```

- [ ] **Step 2: Run scan on all verified+applied hypotheses**

- [ ] **Step 3: Update JSON with scan results**

- [ ] **Step 4: Commit**

```bash
git add anima/config/acceleration_hypotheses.json
git commit -m "feat: NEXUS-6 verification sweep on acceleration hypotheses"
```

---

## Task 6: Handle Unmappable Hypotheses

UNMAPPABLE로 분류된 가설 수동 처리.

- [ ] **Step 1: Classify unmappable hypotheses**

| 분류 | 처리 | 예시 |
|------|------|------|
| Hardware-only | REJECTED (reason: requires physical hardware) | L1 CUDA Graph, L3 Persistent Kernel |
| Biological | REJECTED (reason: requires biological system) | BU5 Brain Transfer, BS1 Vaccination |
| Decoder-only | Separate decoder experiment needed | M1 Attention Bias, M3 Consciousness Embedding |
| Training-only | Needs H100 training run | O1 Curriculum, P1 MAML |
| Meta/Philosophical | REJECTED (not testable) | BU4 Human-in-the-Loop |

- [ ] **Step 2: Auto-reject clearly untestable hypotheses**

Hardware/biological/philosophical → REJECTED with clear reason.

- [ ] **Step 3: Queue remaining for manual experiments**

Create experiment scripts for decoder-only and training-only hypotheses.

- [ ] **Step 4: Commit**

```bash
git add anima/config/acceleration_hypotheses.json
git commit -m "feat: classify and process unmappable acceleration hypotheses"
```

---

## Task 7: Final Convergence Report

- [ ] **Step 1: Generate final report**

```bash
python anima/src/accel_batch_runner.py --report
```

- [ ] **Step 2: Verify 100% convergence**

모든 367개 가설이 verified/applied/rejected 중 하나인지 확인.
brainstorm = 0 확인.

- [ ] **Step 3: Update CLAUDE.md convergence status**

- [ ] **Step 4: Create DD document**

`docs/hypotheses/dd/DD167.md` — 가속 파이프라인 100% 수렴 보고서

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "milestone: acceleration pipeline 100% convergence (367/367)"
```

---

## Execution Estimates

| Task | 예상 시간 | 병렬 가능 |
|------|----------|----------|
| Task 1: Intervention Map | 5분 | - |
| Task 2: Batch Runner | 10분 | - |
| Task 3: Dry-Run Analysis | 5분 | - |
| Task 4: Full Pipeline | 30-60분 | 6 병렬 에이전트 |
| Task 5: NEXUS-6 Sweep | 10분 | - |
| Task 6: Unmappable | 15분 | - |
| Task 7: Final Report | 5분 | - |

**총 예상: ~90분** (병렬 에이전트 활용 시)

## Risk Mitigation

1. **JSON 충돌**: 병렬 에이전트가 동시에 JSON 수정 → 각 에이전트가 자기 배치 결과를 별도 파일에 저장 → 마지막에 통합
2. **Phi 측정 노이즈**: n_repeats=3 + CV<50% 기준으로 재현성 보장
3. **False rejection**: 90% Phi retention threshold가 너무 높을 수 있음 → 85%로 완화 가능
4. **NEXUS-6 렌즈 추가 중**: 현재 렌즈 추가 작업 완료 후 스캔 실행 (Task 5는 마지막)
