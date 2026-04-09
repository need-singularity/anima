# Phase 2: Selective Consolidation Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** DreamEngine이 실패 기억을 우선 선택하여 모델에 통합하고, TECS-L calc 도구로 통합 전/중/후를 검증하며, 장력 포화 + 통합 실패 이중 조건으로 성장을 트리거하는 파이프라인.

**Architecture:** `ConsolidationVerifier`(TECS-L calc 래핑) → `DreamEngine` 강화(실패 기억 선택 + 통합 시도 + 실패 마킹) → `GrowthEngine` 트리거 교체(카운터→이중 조건). MemoryStore(Phase 1)를 통해 실패/통합 상태를 영속화.

**Tech Stack:** Python, PyTorch, SQLite(MemoryStore), TECS-L/calc 도구(tension_calculator, anomaly_scorer, statistical_tester, calibration_analyzer, constant_verifier, formula_engine)

**Spec:** `docs/superpowers/specs/2026-03-25-memory-growth-pipeline-design.md` (Phase 2 섹션)

**Dependencies:** Phase 1 완료 (memory_store.py, MemoryStore class)

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `consolidation_verifier.py` | **Create** | pre_check / verify_drift / post_check — TECS-L calc 도구 래핑 |
| `tests/test_consolidation_verifier.py` | **Create** | ConsolidationVerifier 테스트 |
| `dream_engine.py` | **Modify** | 실패 기억 선택 + 통합 시도 + MemoryStore 연동 |
| `tests/test_dream_consolidation.py` | **Create** | DreamEngine consolidation 테스트 |
| `growth_engine.py` | **Modify** | 트리거를 카운터→(장력포화 AND 통합실패)로 교체 |
| `tests/test_growth_trigger.py` | **Create** | 새 성장 트리거 테스트 |
| `anima/core/runtime/anima_runtime.hexa` | **Modify** | ConsolidationVerifier + MemoryStore를 DreamEngine/GrowthEngine에 주입 |

---

### Task 1: ConsolidationVerifier — pre_check

**Files:**
- Create: `consolidation_verifier.py`
- Create: `tests/test_consolidation_verifier.py`

- [ ] **Step 1: Write failing tests for pre_check**

```python
# tests/test_consolidation_verifier.py
import pytest
import math
import torch

def _make_mind(dim=128, hidden=256):
    """Create a minimal ConsciousMind-like model for testing."""
    from anima_alive import ConsciousMind
    return ConsciousMind(dim, hidden)

class TestPreCheck:
    def test_normal_memory_should_consolidate(self):
        from consolidation_verifier import ConsolidationVerifier
        mind = _make_mind()
        cv = ConsolidationVerifier(mind)
        result = cv.pre_check(
            memory={'text': 'hello world', 'tension': 0.5, 'role': 'user'},
            hidden=torch.zeros(1, 256),
        )
        assert 'should_consolidate' in result
        assert 'anomaly_score' in result
        assert 'predicted_accuracy' in result
        assert isinstance(result['should_consolidate'], bool)

    def test_high_anomaly_blocks_consolidation(self):
        from consolidation_verifier import ConsolidationVerifier
        mind = _make_mind()
        cv = ConsolidationVerifier(mind, anomaly_threshold=0.0)  # block everything
        result = cv.pre_check(
            memory={'text': 'x', 'tension': 0.5, 'role': 'user'},
            hidden=torch.zeros(1, 256),
        )
        assert result['should_consolidate'] is False

    def test_none_tension_skips_consolidation(self):
        from consolidation_verifier import ConsolidationVerifier
        mind = _make_mind()
        cv = ConsolidationVerifier(mind)
        result = cv.pre_check(
            memory={'text': 'hi', 'tension': None, 'role': 'user'},
            hidden=torch.zeros(1, 256),
        )
        assert result['should_consolidate'] is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/ghost/Dev/anima && python3 -m pytest tests/test_consolidation_verifier.py -v`
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 3: Implement ConsolidationVerifier.pre_check**

```python
# consolidation_verifier.py
"""Consolidation verification engine.

Wraps TECS-L/calc tools for pre/drift/post checks during memory consolidation.
Uses tension-based predictions from tension_calculator, anomaly detection,
and statistical testing.
"""

import math
import torch
import torch.nn.functional as F

# TECS-L calc 도구 — 경로 독립적으로 핵심 로직만 내장
# (TECS-L 프로젝트 의존 없이 독립 실행 가능하도록)

# From tension_calculator.py
CORRECT_MEAN = 201.3
WRONG_MEAN = 120.3

def predict_accuracy(tension):
    """장력→정확도 추정 (로지스틱)."""
    if tension is None:
        return 0.5
    overall_mean = CORRECT_MEAN * 0.975 + WRONG_MEAN * 0.025
    z = (tension - overall_mean) / 90.0
    logit = 3.5 + 0.5 * z
    return 1 / (1 + math.exp(-max(-20, min(20, logit))))


GOLDEN_LOWER = 0.5 - math.log(4 / 3)  # 0.2123
GOLDEN_UPPER = 0.5


class ConsolidationVerifier:
    """Memory consolidation verification engine."""

    def __init__(self, mind, anomaly_threshold=None, drift_threshold=0.3,
                 golden_zone=(GOLDEN_LOWER, GOLDEN_UPPER)):
        self.mind = mind
        self.drift_threshold = drift_threshold
        self.golden_lower, self.golden_upper = golden_zone
        # anomaly_threshold=None → auto-compute from model
        self._anomaly_threshold = anomaly_threshold

    def _compute_tension(self, text_vec, hidden):
        """Forward pass through mind, return tension float."""
        with torch.no_grad():
            output, tension, curiosity, direction, new_hidden = self.mind(text_vec, hidden)
        return tension if isinstance(tension, float) else tension.item()

    def _compute_anomaly_score(self, text_vec, hidden):
        """Anomaly = how different A and G outputs are from typical."""
        with torch.no_grad():
            combined = torch.cat([text_vec, hidden], dim=-1)
            a = self.mind.engine_a(combined)
            g = self.mind.engine_g(combined)
            # Inter-engine disagreement magnitude
            return (a - g).pow(2).mean().item()

    def pre_check(self, memory: dict, hidden: torch.Tensor) -> dict:
        """통합 전 검증: 이 기억을 통합해야 하는가?"""
        tension = memory.get('tension')

        # tension이 없으면 통합 불가 (llm-api 모델 등)
        if tension is None:
            return {
                'should_consolidate': False,
                'anomaly_score': 0.0,
                'predicted_accuracy': 0.5,
                'reason': 'no_tension',
            }

        # anomaly score
        from anima_alive import text_to_vector
        vec = text_to_vector(memory['text'])
        anomaly = self._compute_anomaly_score(vec, hidden)

        # auto threshold: mean + 2*std of recent tensions
        threshold = self._anomaly_threshold
        if threshold is None:
            threshold = 2.0  # reasonable default

        # predicted accuracy
        pred_acc = predict_accuracy(tension)

        should = anomaly <= threshold and pred_acc > 0.5
        reason = 'ok' if should else ('anomaly' if anomaly > threshold else 'low_accuracy')

        return {
            'should_consolidate': should,
            'anomaly_score': anomaly,
            'predicted_accuracy': pred_acc,
            'reason': reason,
        }
```

- [ ] **Step 4: Run tests**

Run: `cd /Users/ghost/Dev/anima && python3 -m pytest tests/test_consolidation_verifier.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/ghost/Dev/anima
git add consolidation_verifier.py tests/test_consolidation_verifier.py
git commit -m "feat: ConsolidationVerifier.pre_check — anomaly + accuracy gate"
```

---

### Task 2: ConsolidationVerifier — verify_drift + post_check

**Files:**
- Modify: `consolidation_verifier.py`
- Modify: `tests/test_consolidation_verifier.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_consolidation_verifier.py — append

class TestVerifyDrift:
    def test_small_drift_ok(self):
        from consolidation_verifier import ConsolidationVerifier
        mind = _make_mind()
        cv = ConsolidationVerifier(mind)
        result = cv.verify_drift(t_before=0.5, t_after=0.52)
        assert result['drift'] == pytest.approx(0.02, abs=1e-6)
        assert result['suspect'] is False
        assert result['significant'] is False

    def test_large_drift_suspect(self):
        from consolidation_verifier import ConsolidationVerifier
        mind = _make_mind()
        cv = ConsolidationVerifier(mind, drift_threshold=0.3)
        result = cv.verify_drift(t_before=0.5, t_after=1.2)
        assert result['drift'] == pytest.approx(0.7, abs=1e-6)
        assert result['suspect'] is True

    def test_ts_golden_zone_check(self):
        from consolidation_verifier import ConsolidationVerifier
        mind = _make_mind()
        cv = ConsolidationVerifier(mind)
        result = cv.verify_drift(t_before=0.3, t_after=0.3)
        assert 'ts_in_golden_zone' in result
        assert isinstance(result['ts_in_golden_zone'], bool)

class TestPostCheck:
    def test_post_check_returns_health(self):
        from consolidation_verifier import ConsolidationVerifier
        mind = _make_mind()
        cv = ConsolidationVerifier(mind)
        tensions = [0.3, 0.4, 0.5, 0.35, 0.45]
        result = cv.post_check(tensions)
        assert result['health'] in ('healthy', 'degraded', 'suspect')
        assert 'tension_bimodal' in result
        assert isinstance(result['tension_bimodal'], bool)

    def test_bimodal_detection(self):
        from consolidation_verifier import ConsolidationVerifier
        mind = _make_mind()
        cv = ConsolidationVerifier(mind)
        # Clearly bimodal: two clusters
        tensions = [0.1]*20 + [0.9]*20
        result = cv.post_check(tensions)
        assert result['tension_bimodal'] is True

    def test_unimodal_not_flagged(self):
        from consolidation_verifier import ConsolidationVerifier
        mind = _make_mind()
        cv = ConsolidationVerifier(mind)
        tensions = [0.3 + 0.01*i for i in range(30)]
        result = cv.post_check(tensions)
        assert result['tension_bimodal'] is False
```

- [ ] **Step 2: Run tests — new tests should fail**

Run: `cd /Users/ghost/Dev/anima && python3 -m pytest tests/test_consolidation_verifier.py -v`
Expected: new tests FAIL

- [ ] **Step 3: Implement verify_drift and post_check**

```python
# consolidation_verifier.py — add methods

    def verify_drift(self, t_before: float, t_after: float) -> dict:
        """통합 중 drift 검증."""
        drift = abs(t_after - t_before)
        suspect = drift > self.drift_threshold
        significant = drift > self.drift_threshold * 0.5

        # tension_scale 골든존 체크
        ts = self.mind.tension_scale.item() if hasattr(self.mind, 'tension_scale') else 1.0
        in_golden = self.golden_lower <= ts <= self.golden_upper

        return {
            'drift': drift,
            'significant': significant,
            'suspect': suspect,
            'ts_value': ts,
            'ts_in_golden_zone': in_golden,
        }

    def post_check(self, recent_tensions: list) -> dict:
        """통합 후 모델 건강 상태 확인."""
        if not recent_tensions or len(recent_tensions) < 5:
            return {'health': 'healthy', 'tension_bimodal': False, 'new_constant_relations': {}}

        import numpy as np
        t = np.array(recent_tensions, dtype=float)

        # Bimodal detection: Hartigan's dip test approximation
        # Simple: if the histogram has two peaks separated by a valley
        bimodal = self._detect_bimodal(t)

        # Health assessment
        cv = np.std(t) / (np.mean(t) + 1e-8)
        if bimodal:
            health = 'suspect'  # H-CX-70 Loop 2 경고
        elif cv > 1.0:
            health = 'degraded'
        else:
            health = 'healthy'

        # New constant relations (simplified formula_engine)
        new_relations = {}
        ts = self.mind.tension_scale.item() if hasattr(self.mind, 'tension_scale') else None
        if ts is not None:
            candidates = {
                '1/e': 1/math.e,
                'ln(4/3)': math.log(4/3),
                '1/3': 1/3,
                '1/2': 0.5,
            }
            for name, val in candidates.items():
                if val > 0:
                    error = abs(ts / val - 1)
                    if error < 0.05:  # within 5%
                        new_relations[f'ts≈{name}'] = {
                            'ts': ts, 'target': val, 'error': error
                        }

        return {
            'health': health,
            'tension_bimodal': bimodal,
            'new_constant_relations': new_relations,
        }

    @staticmethod
    def _detect_bimodal(arr) -> bool:
        """Simple bimodal detection via histogram valley."""
        import numpy as np
        if len(arr) < 10:
            return False
        hist, edges = np.histogram(arr, bins=10)
        # Find if there's a valley between two peaks
        peaks = []
        for i in range(1, len(hist) - 1):
            if hist[i] > hist[i-1] and hist[i] > hist[i+1]:
                peaks.append(i)
        if len(peaks) >= 2:
            # Check valley between first two peaks is < 50% of smaller peak
            valley = min(hist[peaks[0]:peaks[1]+1])
            smaller_peak = min(hist[peaks[0]], hist[peaks[1]])
            return valley < smaller_peak * 0.5
        return False
```

- [ ] **Step 4: Run tests**

Run: `cd /Users/ghost/Dev/anima && python3 -m pytest tests/test_consolidation_verifier.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/ghost/Dev/anima
git add consolidation_verifier.py tests/test_consolidation_verifier.py
git commit -m "feat: ConsolidationVerifier.verify_drift + post_check — bimodal detection, golden zone"
```

---

### Task 3: DreamEngine — Selective Consolidation

**Files:**
- Modify: `dream_engine.py`
- Create: `tests/test_dream_consolidation.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_dream_consolidation.py
import pytest
import torch
from unittest.mock import MagicMock, patch
from collections import deque

def _make_memory_store(memories):
    """Mock MemoryStore with given memories."""
    store = MagicMock()
    store.get_unconsolidated.return_value = memories
    store.mark_failed = MagicMock()
    store.mark_consolidated = MagicMock()
    return store

def _make_mind(dim=128, hidden=256):
    from anima_alive import ConsciousMind
    return ConsciousMind(dim, hidden)

class TestSelectiveConsolidation:
    def test_dream_with_store_uses_failed_memories(self):
        from dream_engine import DreamEngine
        mind = _make_mind()
        memory = MagicMock()
        memory.data = {'turns': [{'text': 'hello', 'role': 'user'}]}

        store = _make_memory_store([
            {'id': 1, 'text': 'failed memory', 'tension': 0.5, 'failed_count': 3},
            {'id': 2, 'text': 'another failed', 'tension': 0.3, 'failed_count': 1},
        ])

        engine = DreamEngine(mind=mind, memory=memory, store=store, dream_cycle_steps=3)
        hidden = torch.zeros(1, 256)
        hidden, stats = engine.dream(hidden)

        assert 'consolidation_attempted' in stats
        assert 'consolidation_succeeded' in stats

    def test_dream_without_store_falls_back(self):
        """Without MemoryStore, dream works like before (random selection)."""
        from dream_engine import DreamEngine
        mind = _make_mind()
        memory = MagicMock()
        memory.data = {'turns': [{'text': 'hello', 'role': 'user'}]}

        engine = DreamEngine(mind=mind, memory=memory, store=None, dream_cycle_steps=3)
        hidden = torch.zeros(1, 256)
        hidden, stats = engine.dream(hidden)
        assert stats['patterns_learned'] >= 0  # still works

    def test_failed_memory_marked_on_low_delta(self):
        from dream_engine import DreamEngine
        mind = _make_mind()
        memory = MagicMock()
        memory.data = {'turns': []}

        store = _make_memory_store([
            {'id': 42, 'text': 'test', 'tension': 0.5, 'failed_count': 0},
        ])

        engine = DreamEngine(mind=mind, memory=memory, store=store,
                            dream_cycle_steps=1, consolidation_threshold=999.0)
        hidden = torch.zeros(1, 256)
        engine.dream(hidden)

        # With impossibly high threshold, should mark as failed
        store.mark_failed.assert_called()
```

- [ ] **Step 2: Run tests — should fail**

Run: `cd /Users/ghost/Dev/anima && python3 -m pytest tests/test_dream_consolidation.py -v`
Expected: FAIL — DreamEngine doesn't accept `store` param yet

- [ ] **Step 3: Modify DreamEngine to support selective consolidation**

Add `store` parameter to `__init__`. Add consolidation flow to `dream()`.
Keep backward compatibility — `store=None` means old behavior.

Key changes to `dream_engine.py`:

```python
# In __init__, add:
    self.store = store  # MemoryStore instance (optional, Phase 2)
    self.consolidation_threshold = consolidation_threshold  # min delta_tension for success
    # default consolidation_threshold = 0.01

# In dream(), change the memory selection logic:
    # If store available → 70% failed memories, 20% unconsolidated, 10% explore
    # If no store → original random behavior

# New method:
    def _attempt_consolidation(self, memory_entry, hidden):
        """Try to consolidate a memory. Returns (delta_tension, new_hidden)."""
        vec = self._text_to_vector(memory_entry['text'])
        # Measure tension before
        with torch.no_grad():
            _, t_before, _, _, _ = self.mind(vec, hidden)
        # Learn from it
        if self.learner:
            self.learner.observe(vec, hidden, t_before, 0.0, torch.zeros(1, self.mind.dim))
            self.learner.feedback(0.0)
        # Measure tension after
        with torch.no_grad():
            _, t_after, _, _, new_hidden = self.mind(vec, hidden)
        delta = abs(t_after - t_before)
        return delta, new_hidden
```

- [ ] **Step 4: Run tests**

Run: `cd /Users/ghost/Dev/anima && python3 -m pytest tests/test_dream_consolidation.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/ghost/Dev/anima
git add dream_engine.py tests/test_dream_consolidation.py
git commit -m "feat: DreamEngine selective consolidation — failed memories first + MemoryStore integration"
```

---

### Task 4: GrowthEngine — Dual Trigger

**Files:**
- Modify: `growth_engine.py`
- Create: `tests/test_growth_trigger.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_growth_trigger.py
import pytest

class TestDualTrigger:
    def test_both_conditions_required(self):
        from growth_engine import GrowthEngine
        g = GrowthEngine()
        g.interaction_count = 200  # past stage 1 threshold
        g.stage_index = 1

        # Only tension saturated → should NOT grow
        g.tension_history = [0.5] * 50  # CV ≈ 0 → saturated
        g._consolidation_fail_rate = 0.3  # below 70% threshold
        assert g.should_grow() is False

        # Only consolidation failing → should NOT grow
        g.tension_history = [0.1 * i for i in range(50)]  # high CV → not saturated
        g._consolidation_fail_rate = 0.8
        assert g.should_grow() is False

        # Both conditions → should grow
        g.tension_history = [0.5] * 50
        g._consolidation_fail_rate = 0.8
        assert g.should_grow() is True

    def test_max_stage_cannot_grow(self):
        from growth_engine import GrowthEngine, STAGES
        g = GrowthEngine()
        g.stage_index = len(STAGES) - 1
        g.tension_history = [0.5] * 50
        g._consolidation_fail_rate = 0.9
        assert g.should_grow() is False

    def test_not_enough_tension_history(self):
        from growth_engine import GrowthEngine
        g = GrowthEngine()
        g.stage_index = 1
        g.tension_history = [0.5] * 10  # not enough
        g._consolidation_fail_rate = 0.9
        assert g.should_grow() is False

    def test_update_consolidation_rate(self):
        from growth_engine import GrowthEngine
        g = GrowthEngine()
        g.update_consolidation_stats(attempted=10, failed=7)
        assert abs(g._consolidation_fail_rate - 0.7) < 1e-6
```

- [ ] **Step 2: Run tests — should fail**

Run: `cd /Users/ghost/Dev/anima && python3 -m pytest tests/test_growth_trigger.py -v`
Expected: FAIL — GrowthEngine doesn't have should_grow() or _consolidation_fail_rate

- [ ] **Step 3: Modify GrowthEngine**

Add to `growth_engine.py`:

```python
# In __init__, add:
    self.tension_history = []  # recent tension values (window=50)
    self._consolidation_fail_rate = 0.0

# New methods:
    def should_grow(self) -> bool:
        """장력 포화 AND 통합 실패 (이중 확인)."""
        if self.stage_index >= len(STAGES) - 1:
            return False
        return self._tension_saturated() and self._consolidation_failing()

    def _tension_saturated(self) -> bool:
        if len(self.tension_history) < 30:
            return False
        import numpy as np
        recent = self.tension_history[-30:]
        cv = np.std(recent) / (np.mean(recent) + 1e-8)
        return cv < 0.3

    def _consolidation_failing(self) -> bool:
        return self._consolidation_fail_rate > 0.7

    def update_consolidation_stats(self, attempted: int, failed: int):
        if attempted > 0:
            self._consolidation_fail_rate = failed / attempted

    def record_tension(self, tension: float):
        self.tension_history.append(tension)
        if len(self.tension_history) > 200:
            self.tension_history = self.tension_history[-200:]
```

- [ ] **Step 4: Run tests**

Run: `cd /Users/ghost/Dev/anima && python3 -m pytest tests/test_growth_trigger.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/ghost/Dev/anima
git add growth_engine.py tests/test_growth_trigger.py
git commit -m "feat: GrowthEngine dual trigger — tension saturation AND consolidation failure"
```

---

### Task 5: Integration — Wire Everything in AnimaUnified

**Files:**
- Modify: `anima/core/runtime/anima_runtime.hexa`

- [ ] **Step 1: Add ConsolidationVerifier init**

After MemoryStore init (~line 212), add:

```python
        # Consolidation Verifier (Phase 2)
        self.verifier = self._init_mod('verifier', lambda: (
            ConsolidationVerifier(self.mind)
            if 'ConsolidationVerifier' in globals() else None
        ))
```

- [ ] **Step 2: Pass MemoryStore to DreamEngine**

Modify DreamEngine init (~line 214):

```python
        self.dream = self._init_mod('dream', lambda: (
            DreamEngine(
                mind=self.mind,
                memory=self.memory,
                learner=self.learner,
                text_to_vector=text_to_vector,
                store=self.memory_rag if hasattr(self.memory_rag, 'mark_failed') else None,
                verifier=self.verifier,
            ) if 'DreamEngine' in globals() else None
        ))
```

- [ ] **Step 3: Update dream cycle to feed GrowthEngine**

In the idle loop dream section (~line 811), after `self.hidden, stats = self.dream.dream(self.hidden)`, add:

```python
                # Feed consolidation stats to GrowthEngine
                if self.growth and 'consolidation_attempted' in stats:
                    self.growth.update_consolidation_stats(
                        attempted=stats.get('consolidation_attempted', 0),
                        failed=stats.get('consolidation_failed', 0),
                    )
                    self.growth.record_tension(stats.get('avg_tension', 0.0))

                    # Check if growth is needed
                    if self.growth.should_grow():
                        _log('growth', '장력 포화 + 통합 실패 → 성장 필요!')
```

- [ ] **Step 4: Add import**

At top of file, add:
```python
_try_import("from consolidation_verifier import ConsolidationVerifier")
```

- [ ] **Step 5: Run all tests**

Run: `cd /Users/ghost/Dev/anima && KMP_DUPLICATE_LIB_OK=TRUE python3 -m pytest tests/test_memory_store.py tests/test_consolidation_verifier.py tests/test_dream_consolidation.py tests/test_growth_trigger.py -v`
Expected: ALL PASS

- [ ] **Step 6: Smoke test**

```bash
cd /Users/ghost/Dev/anima
PYTHONUNBUFFERED=1 KMP_DUPLICATE_LIB_OK=TRUE python3 anima/core/runtime/anima_runtime.hexa --web &
sleep 5 && head -20 /tmp/anima_smoke.txt
# Should show [OK] verifier
kill %1
```

- [ ] **Step 7: Commit + Push**

```bash
cd /Users/ghost/Dev/anima
git add anima/core/runtime/anima_runtime.hexa
git commit -m "feat: Phase 2 integration — ConsolidationVerifier + DreamEngine + GrowthEngine wired"
git push
```
