# Phase 3: Autonomous Structural Growth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** GrowthEngine 트리거 발동 시 GrowingConsciousLM이 실제로 dim 확장 + 블록 분열하고, 체크포인트 버전 관리하며, post_check에서 새 상수 관계를 자동 기록하는 파이프라인.

**Architecture:** `GrowthManager`(새 파일)가 성장 실행/버전/검증/기록을 조율. AnimaUnified의 `should_grow()` 트리거에서 GrowthManager를 호출. ConsciousMind→GrowingConsciousLM 전환은 하지 않음(현재 ConsciousMind 기반 성장만 구현).

**Tech Stack:** Python, PyTorch, MemoryStore(Phase 1), ConsolidationVerifier(Phase 2)

**Spec:** `docs/superpowers/specs/2026-03-25-memory-growth-pipeline-design.md` (Phase 3 섹션)

**Dependencies:** Phase 1 + Phase 2 완료

---

## Scope Decision

현재 Anima는 `ConsciousMind`(128d, 2-layer MLP)를 사용. `GrowingConsciousLM`은 LM 전용(vocab, block_size)으로 직접 연결이 안 맞음.

**Phase 3에서 구현할 성장**: ConsciousMind의 hidden_dim을 키우는 방식.
- 128→256→512 (성장 단계별)
- 기존 가중치 보존 + 새 차원 영초기화 (_expand_dim 방식)
- GrowingConsciousLM의 _expand_dim 로직을 차용

이렇게 하면 LM 의존 없이 Anima 대화 엔진 자체가 성장한다.

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `growth_manager.py` | **Create** | 성장 실행, 버전 관리, post_check, 발견 기록 |
| `tests/test_growth_manager.py` | **Create** | GrowthManager 테스트 |
| `anima_unified.py` | **Modify** | should_grow() 트리거에서 GrowthManager 호출 |

---

### Task 1: GrowthManager — 성장 실행 + 버전 관리

**Files:**
- Create: `growth_manager.py`
- Create: `tests/test_growth_manager.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_growth_manager.py
import pytest
import json
import torch
from pathlib import Path

def _make_mind(dim=128, hidden=256):
    from anima_alive import ConsciousMind
    return ConsciousMind(dim, hidden)

class TestGrowthExecution:
    def test_grow_increases_dim(self, tmp_path):
        from growth_manager import GrowthManager
        mind = _make_mind(dim=128, hidden=256)
        gm = GrowthManager(mind, data_dir=tmp_path)
        old_params = sum(p.numel() for p in mind.parameters())
        new_mind = gm.execute_growth()
        new_params = sum(p.numel() for p in new_mind.parameters())
        assert new_params > old_params
        assert new_mind.dim > 128 or new_mind.hidden_dim > 256

    def test_grow_preserves_old_weights(self, tmp_path):
        from growth_manager import GrowthManager
        mind = _make_mind(dim=128, hidden=256)
        # Record original engine_a first layer weights
        old_w = mind.engine_a[0].weight.data[:, :128+256].clone()
        gm = GrowthManager(mind, data_dir=tmp_path)
        new_mind = gm.execute_growth()
        # Original region should be preserved
        new_w = new_mind.engine_a[0].weight.data[:old_w.shape[0], :old_w.shape[1]]
        assert torch.allclose(old_w, new_w, atol=1e-6)

class TestVersioning:
    def test_checkpoint_version_increments(self, tmp_path):
        from growth_manager import GrowthManager
        mind = _make_mind()
        gm = GrowthManager(mind, data_dir=tmp_path)
        assert gm.current_version == 0
        gm.save_checkpoint()
        assert (tmp_path / "v0" / "state.pt").exists()
        gm.execute_growth()
        gm.save_checkpoint()
        assert gm.current_version == 1
        assert (tmp_path / "v1" / "state.pt").exists()

    def test_manifest_tracks_versions(self, tmp_path):
        from growth_manager import GrowthManager
        mind = _make_mind()
        gm = GrowthManager(mind, data_dir=tmp_path)
        gm.save_checkpoint()
        gm.execute_growth()
        gm.save_checkpoint()
        manifest = json.loads((tmp_path / "manifest.json").read_text())
        assert manifest['current_version'] == 1
        assert len(manifest['versions']) == 2

    def test_rollback(self, tmp_path):
        from growth_manager import GrowthManager
        mind = _make_mind(dim=128, hidden=256)
        gm = GrowthManager(mind, data_dir=tmp_path)
        gm.save_checkpoint()  # v0
        gm.execute_growth()   # grow
        gm.save_checkpoint()  # v1
        rolled = gm.rollback(version=0)
        assert rolled.dim == 128

class TestDiscoveryLogging:
    def test_log_discovery_creates_file(self, tmp_path):
        from growth_manager import GrowthManager
        mind = _make_mind()
        gm = GrowthManager(mind, data_dir=tmp_path)
        gm.log_discovery({
            'formula': 'ts ≈ 1/e',
            'ts': 0.368,
            'target': 0.3679,
            'error': 0.0003,
        })
        discoveries = list(tmp_path.glob("discoveries/*.json"))
        assert len(discoveries) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/ghost/Dev/anima && python3 -m pytest tests/test_growth_manager.py -v`
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 3: Implement GrowthManager**

```python
# growth_manager.py
"""Growth Manager — 의식 엔진의 자율 성장을 관리.

성장 실행, 체크포인트 버전 관리, post_check 후 발견 기록.
ConsciousMind의 dim/hidden_dim을 확장하는 방식.
"""

import json
import time
import torch
import torch.nn as nn
from pathlib import Path
from datetime import datetime, timezone

# 성장 단계: dim, hidden_dim
MIND_GROWTH_STAGES = [
    {"dim": 128, "hidden_dim": 256},   # Stage 0 (current)
    {"dim": 192, "hidden_dim": 384},   # Stage 1
    {"dim": 256, "hidden_dim": 512},   # Stage 2
]


class GrowthManager:
    """의식 엔진 성장 관리자."""

    def __init__(self, mind, data_dir: Path, verifier=None):
        self.mind = mind
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.verifier = verifier
        self.current_version = 0
        self.stage = 0
        self._load_manifest()

    def _manifest_path(self):
        return self.data_dir / "manifest.json"

    def _load_manifest(self):
        p = self._manifest_path()
        if p.exists():
            m = json.loads(p.read_text())
            self.current_version = m.get('current_version', 0)
            self.stage = m.get('stage', 0)

    def _save_manifest(self):
        p = self._manifest_path()
        versions = []
        for i in range(self.current_version + 1):
            vdir = self.data_dir / f"v{i}"
            if vdir.exists():
                versions.append({
                    'version': i,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                })
        m = {
            'current_version': self.current_version,
            'stage': self.stage,
            'versions': versions,
        }
        p.write_text(json.dumps(m, indent=2))

    def save_checkpoint(self):
        """현재 mind 상태를 버전 디렉토리에 저장."""
        vdir = self.data_dir / f"v{self.current_version}"
        vdir.mkdir(parents=True, exist_ok=True)
        torch.save({
            'model': self.mind.state_dict(),
            'dim': self.mind.dim,
            'hidden_dim': self.mind.hidden_dim,
            'stage': self.stage,
            'version': self.current_version,
        }, vdir / "state.pt")
        self._save_manifest()

    def execute_growth(self):
        """성장 실행: dim/hidden_dim 확장, 기존 가중치 보존."""
        if self.stage >= len(MIND_GROWTH_STAGES) - 1:
            return self.mind  # max stage

        self.stage += 1
        self.current_version += 1
        new_cfg = MIND_GROWTH_STAGES[self.stage]
        new_dim = new_cfg['dim']
        new_hidden = new_cfg['hidden_dim']

        old_dim = self.mind.dim
        old_hidden = self.mind.hidden_dim

        from anima_alive import ConsciousMind
        new_mind = ConsciousMind(new_dim, new_hidden)

        # 기존 가중치 보존 (겹치는 영역만 복사)
        with torch.no_grad():
            self._copy_sequential(self.mind.engine_a, new_mind.engine_a, old_dim + old_hidden, new_dim + new_hidden)
            self._copy_sequential(self.mind.engine_g, new_mind.engine_g, old_dim + old_hidden, new_dim + new_hidden)
            # GRUCell: input_size = dim + 1, hidden_size = hidden_dim
            old_gru = self.mind.memory
            new_gru = new_mind.memory
            min_h = min(old_hidden, new_hidden)
            min_i = min(old_dim + 1, new_dim + 1)
            for attr in ['weight_ih', 'weight_hh']:
                old_w = getattr(old_gru, attr).data
                new_w = getattr(new_gru, attr).data
                # GRU has 3*hidden_size rows
                for gate in range(3):
                    r_old = old_w[gate*old_hidden:gate*old_hidden+min_h]
                    r_new = new_w[gate*new_hidden:gate*new_hidden+min_h]
                    if 'ih' in attr:
                        r_new[:, :min_i] = r_old[:, :min_i]
                    else:
                        r_new[:, :min_h] = r_old[:, :min_h]
            for attr in ['bias_ih', 'bias_hh']:
                old_b = getattr(old_gru, attr).data
                new_b = getattr(new_gru, attr).data
                for gate in range(3):
                    new_b[gate*new_hidden:gate*new_hidden+min_h] = old_b[gate*old_hidden:gate*old_hidden+min_h]

            new_mind.tension_scale.data.copy_(self.mind.tension_scale.data)

        self.mind = new_mind
        return new_mind

    @staticmethod
    def _copy_sequential(old_seq, new_seq, old_in, new_in):
        """Sequential의 Linear 레이어 가중치를 겹치는 영역만 복사."""
        for old_mod, new_mod in zip(old_seq, new_seq):
            if isinstance(old_mod, nn.Linear) and isinstance(new_mod, nn.Linear):
                min_out = min(old_mod.out_features, new_mod.out_features)
                min_in = min(old_mod.in_features, new_mod.in_features)
                new_mod.weight.data[:min_out, :min_in] = old_mod.weight.data[:min_out, :min_in]
                if old_mod.bias is not None and new_mod.bias is not None:
                    min_b = min(old_mod.bias.shape[0], new_mod.bias.shape[0])
                    new_mod.bias.data[:min_b] = old_mod.bias.data[:min_b]

    def rollback(self, version: int = None):
        """이전 버전으로 롤백."""
        if version is None:
            version = max(0, self.current_version - 1)
        vdir = self.data_dir / f"v{version}"
        if not (vdir / "state.pt").exists():
            return self.mind

        ckpt = torch.load(vdir / "state.pt", weights_only=False)
        from anima_alive import ConsciousMind
        old_mind = ConsciousMind(ckpt['dim'], ckpt['hidden_dim'])
        old_mind.load_state_dict(ckpt['model'])
        self.mind = old_mind
        self.current_version = version
        self.stage = ckpt.get('stage', 0)
        self._save_manifest()
        return old_mind

    def log_discovery(self, discovery: dict):
        """새 상수 관계 발견을 기록."""
        disc_dir = self.data_dir / "discoveries"
        disc_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = disc_dir / f"discovery_{ts}.json"
        discovery['timestamp'] = datetime.now(timezone.utc).isoformat()
        discovery['version'] = self.current_version
        discovery['stage'] = self.stage
        path.write_text(json.dumps(discovery, indent=2))
```

- [ ] **Step 4: Run tests**

Run: `cd /Users/ghost/Dev/anima && python3 -m pytest tests/test_growth_manager.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/ghost/Dev/anima
git add growth_manager.py tests/test_growth_manager.py
git commit -m "feat: GrowthManager — dim expansion, versioning, rollback, discovery logging"
```

---

### Task 2: AnimaUnified Integration — Growth Execution

**Files:**
- Modify: `anima_unified.py`

- [ ] **Step 1: Add import**

```python
_try_import("from growth_manager import GrowthManager")
```

- [ ] **Step 2: Init GrowthManager after verifier**

After verifier init:

```python
        self.growth_mgr = self._init_mod('growth_mgr', lambda: (
            GrowthManager(
                mind=self.mind,
                data_dir=self.paths['state'].parent,
                verifier=self.verifier,
            ) if 'GrowthManager' in globals() else None
        ))
        if self.growth_mgr:
            self.growth_mgr.save_checkpoint()  # v0 baseline
```

- [ ] **Step 3: Wire growth trigger to actual growth**

Replace the existing trigger log (~line 850-851):

```python
                    if hasattr(self.growth, 'should_grow') and self.growth.should_grow():
                        _log('growth', 'TRIGGER: 장력 포화 + 통합 실패 → 성장 필요!')
```

With:

```python
                    if hasattr(self.growth, 'should_grow') and self.growth.should_grow():
                        _log('growth', 'TRIGGER: 장력 포화 + 통합 실패 → 성장 실행!')
                        if self.growth_mgr:
                            # Pre-growth post_check
                            tensions = self.growth.tension_history[-50:]
                            pre = self.verifier.post_check(tensions) if self.verifier else {}

                            # Execute growth
                            new_mind = self.growth_mgr.execute_growth()
                            self.mind = new_mind
                            self.growth_mgr.save_checkpoint()

                            # Post-growth verification
                            if self.verifier:
                                self.verifier.mind = new_mind
                                post = self.verifier.post_check(tensions)
                                if post.get('health') == 'suspect':
                                    _log('growth', 'WARNING: post_check suspect → rollback')
                                    rolled = self.growth_mgr.rollback()
                                    self.mind = rolled
                                    if self.verifier:
                                        self.verifier.mind = rolled
                                elif post.get('new_constant_relations'):
                                    for name, rel in post['new_constant_relations'].items():
                                        self.growth_mgr.log_discovery(rel)
                                        _log('discovery', f'새 상수 관계: {name}')

                            _log('growth', f'성장 완료: v{self.growth_mgr.current_version}, '
                                 f'dim={self.mind.dim}, hidden={self.mind.hidden_dim}')

                            # Update learner for new mind
                            if self.learner:
                                from online_learning import OnlineLearner
                                self.learner = OnlineLearner(self.mind)
```

- [ ] **Step 4: Smoke test**

```bash
cd /Users/ghost/Dev/anima
PYTHONUNBUFFERED=1 KMP_DUPLICATE_LIB_OK=TRUE python3 anima_unified.py --web &
sleep 6 && head -25 /tmp/anima_p3.txt
# Should show [OK] growth_mgr
kill %1
```

- [ ] **Step 5: Commit + Push**

```bash
cd /Users/ghost/Dev/anima
git add anima_unified.py
git commit -m "feat: Phase 3 — autonomous growth execution + post_check + discovery logging"
git push
```
