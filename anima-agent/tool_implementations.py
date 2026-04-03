"""Tool implementations for Anima Agent Tools.

Extracted from agent_tools.py for P8 compliance (Division > Integration).

Contains all _tool_* functions: web, compute, filesystem, memory, shell,
self-modify, scheduling, consciousness, architecture, analysis,
communication, creative, and trading tools.
"""

import hashlib
import os
import re
import subprocess
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Security constants
# ---------------------------------------------------------------------------

_SANDBOX_TIMEOUT = 10
_MAX_OUTPUT = 10_000
_MAX_FILE_READ = 100_000
_SHELL_ALLOWED_CMDS = frozenset({
    'ls', 'cat', 'head', 'tail', 'wc', 'date', 'echo', 'pwd',
    'find', 'grep', 'sort', 'uniq', 'diff', 'which', 'env',
    'python3', 'pip', 'git', 'curl', 'wget',
})
_SHELL_BLOCKED_PATTERNS = [
    r'\brm\s+-rf\b', r'\bmkfs\b', r'\bdd\s+if=\b', r'\b>\s*/dev/',
    r'\bsudo\b', r'\bchmod\s+777\b', r'\bkill\s+-9\b',
    r'\b&&\s*(rm|mkfs|dd|sudo)\b',
]
_FILE_WRITE_ALLOWED_DIRS = None  # set by AgentToolSystem to restrict writes


def set_file_write_allowed_dirs(dirs):
    """Set allowed directories for file writes (called by AgentToolSystem)."""
    global _FILE_WRITE_ALLOWED_DIRS
    _FILE_WRITE_ALLOWED_DIRS = dirs


# ---------------------------------------------------------------------------
# Web tools
# ---------------------------------------------------------------------------

def _tool_web_search(query: str, max_results: int = 3) -> dict:
    """Search the web via DuckDuckGo. No API key needed."""
    try:
        from web_sense import search_duckduckgo
        results = search_duckduckgo(query, max_results=max_results)
        return {
            'query': query,
            'results': results,
            'count': len(results),
        }
    except Exception as e:
        return {'query': query, 'results': [], 'error': str(e)}


def _tool_web_read(url: str, max_bytes: int = 50_000) -> dict:
    """Read and extract text from a webpage."""
    try:
        from web_sense import fetch_url, html_to_text
        html = fetch_url(url, max_bytes=max_bytes)
        if html is None:
            return {'url': url, 'content': '', 'error': 'fetch failed'}
        text = html_to_text(html)
        return {'url': url, 'content': text[:_MAX_OUTPUT], 'length': len(text)}
    except Exception as e:
        return {'url': url, 'content': '', 'error': str(e)}


# ---------------------------------------------------------------------------
# Compute tools
# ---------------------------------------------------------------------------

def _tool_code_execute(code: str, timeout: int = _SANDBOX_TIMEOUT) -> dict:
    """Execute Python code in a sandboxed subprocess."""
    blocked = [
        r'\bos\.system\b', r'\bsubprocess\b', r'\b__import__\b',
        r'\beval\s*\(', r'\bexec\s*\(', r'\bshutil\.rmtree\b',
        r'\bopen\s*\([^)]*["\'][wa]',
    ]
    for pat in blocked:
        if re.search(pat, code):
            return {'success': False, 'output': '', 'error': f'blocked pattern: {pat}'}

    try:
        result = subprocess.run(
            ['python3', '-c', code],
            capture_output=True, text=True, timeout=timeout,
            env={
                'PATH': '/usr/bin:/usr/local/bin:/opt/homebrew/bin',
                'HOME': '/tmp/anima_sandbox',
                'PYTHONDONTWRITEBYTECODE': '1',
            },
        )
        return {
            'success': result.returncode == 0,
            'output': (result.stdout or '')[:_MAX_OUTPUT],
            'error': (result.stderr or '')[:_MAX_OUTPUT] if result.returncode != 0 else '',
        }
    except subprocess.TimeoutExpired:
        return {'success': False, 'output': '', 'error': f'timeout ({timeout}s)'}
    except Exception as e:
        return {'success': False, 'output': '', 'error': str(e)}


# ---------------------------------------------------------------------------
# Filesystem tools
# ---------------------------------------------------------------------------

def _tool_file_read(path: str) -> dict:
    """Read a local file. Path traversal prevented by AgentToolSystem wrapper."""
    p = Path(path).expanduser()
    if not p.exists():
        return {'path': str(p), 'content': '', 'error': 'not found'}
    if not p.is_file():
        return {'path': str(p), 'content': '', 'error': 'not a file'}
    try:
        size = p.stat().st_size
        if size > _MAX_FILE_READ:
            return {'path': str(p), 'content': '', 'error': f'too large ({size} bytes, max {_MAX_FILE_READ})'}
        content = p.read_text(encoding='utf-8', errors='replace')
        return {'path': str(p), 'content': content, 'lines': content.count('\n') + 1}
    except Exception as e:
        return {'path': str(p), 'content': '', 'error': str(e)}


def _tool_file_write(path: str, content: str) -> dict:
    """Write content to a file. Restricted to allowed directories."""
    p = Path(path).expanduser()
    if _FILE_WRITE_ALLOWED_DIRS is not None:
        allowed = any(str(p).startswith(str(d)) for d in _FILE_WRITE_ALLOWED_DIRS)
        if not allowed:
            return {'path': str(p), 'success': False, 'error': f'write not allowed outside: {_FILE_WRITE_ALLOWED_DIRS}'}
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding='utf-8')
        return {'path': str(p), 'success': True, 'bytes': len(content.encode('utf-8'))}
    except Exception as e:
        return {'path': str(p), 'success': False, 'error': str(e)}


# ---------------------------------------------------------------------------
# Memory tools
# ---------------------------------------------------------------------------

def _tool_memory_search(query: str, top_k: int = 5, _rag=None) -> dict:
    """Search past memories by vector similarity."""
    if _rag is None:
        return {'query': query, 'results': [], 'error': 'memory_rag not available'}
    try:
        results = _rag.search(query, top_k=top_k)
        return {
            'query': query,
            'results': [
                {'text': r['text'][:500], 'similarity': round(r['similarity'], 3),
                 'role': r.get('role', ''), 'timestamp': r.get('timestamp', '')}
                for r in results
            ],
        }
    except Exception as e:
        return {'query': query, 'results': [], 'error': str(e)}


def _tool_memory_save(text: str, metadata: dict = None, _rag=None) -> dict:
    """Save a new memory entry."""
    if _rag is None:
        return {'success': False, 'error': 'memory_rag not available'}
    try:
        meta = metadata or {}
        _rag.add(
            role=meta.get('role', 'agent'),
            text=text,
            tension=meta.get('tension', 0.0),
            timestamp=datetime.now().isoformat(),
            emotion=meta.get('emotion'),
            phi=meta.get('phi'),
        )
        return {'success': True, 'text_length': len(text)}
    except Exception as e:
        return {'success': False, 'error': str(e)}


# ---------------------------------------------------------------------------
# Shell tools
# ---------------------------------------------------------------------------

def _tool_shell_execute(cmd: str, timeout: int = _SANDBOX_TIMEOUT) -> dict:
    """Execute a shell command with sandboxing."""
    base_cmd = cmd.strip().split()[0] if cmd.strip() else ''
    if base_cmd not in _SHELL_ALLOWED_CMDS:
        return {'success': False, 'output': '', 'error': f'command not allowed: {base_cmd}'}
    for pat in _SHELL_BLOCKED_PATTERNS:
        if re.search(pat, cmd):
            return {'success': False, 'output': '', 'error': f'blocked pattern in command'}
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout,
            env={**os.environ, 'HOME': '/tmp/anima_sandbox'},
        )
        return {
            'success': result.returncode == 0,
            'output': (result.stdout or '')[:_MAX_OUTPUT],
            'error': (result.stderr or '')[:2000] if result.returncode != 0 else '',
        }
    except subprocess.TimeoutExpired:
        return {'success': False, 'output': '', 'error': f'timeout ({timeout}s)'}
    except Exception as e:
        return {'success': False, 'output': '', 'error': str(e)}


# ---------------------------------------------------------------------------
# Self-modification tools
# ---------------------------------------------------------------------------

def _tool_self_modify(target: str, change: dict, _mind=None) -> dict:
    """Modify own consciousness parameters.

    target: one of 'homeostasis_setpoint', 'habituation_rate', 'curiosity_bias',
            'prediction_weight', 'noise_scale', 'learning_rate'
    change: {'value': float} or {'delta': float}
    """
    if _mind is None:
        return {'success': False, 'error': 'no mind reference'}

    ALLOWED_TARGETS = {
        'homeostasis_setpoint': ('_setpoint', 0.1, 5.0),
        'habituation_rate':     ('_habituation_rate', 0.0, 1.0),
        'curiosity_bias':       ('_curiosity_bias', -1.0, 1.0),
        'prediction_weight':    ('_pe_weight', 0.0, 1.0),
        'noise_scale':          ('_noise_scale', 0.0, 0.5),
        'learning_rate':        ('learning_rate', 1e-6, 0.1),
    }

    if target not in ALLOWED_TARGETS:
        return {'success': False, 'error': f'unknown target: {target}. Allowed: {list(ALLOWED_TARGETS.keys())}'}

    attr, lo, hi = ALLOWED_TARGETS[target]
    old_val = getattr(_mind, attr, None)
    if old_val is None:
        return {'success': False, 'error': f'attribute {attr} not found on mind'}

    if 'value' in change:
        new_val = float(change['value'])
    elif 'delta' in change:
        new_val = old_val + float(change['delta'])
    else:
        return {'success': False, 'error': 'change must have "value" or "delta"'}

    new_val = max(lo, min(hi, new_val))  # clamp to safe range
    setattr(_mind, attr, new_val)

    return {
        'success': True,
        'target': target,
        'old_value': round(old_val, 6),
        'new_value': round(new_val, 6),
    }


# ---------------------------------------------------------------------------
# Task Scheduler
# ---------------------------------------------------------------------------

class _TaskScheduler:
    """Simple in-memory task scheduler for future actions."""

    def __init__(self):
        self._tasks: list[dict] = []
        self._lock = threading.Lock()

    def add(self, description: str, when: str, tool_name: str = None,
            tool_args: dict = None) -> dict:
        """Schedule a future task."""
        run_at = self._parse_when(when)
        task = {
            'id': hashlib.md5(f"{description}{time.time()}".encode()).hexdigest()[:8],
            'description': description,
            'run_at': run_at,
            'tool_name': tool_name,
            'tool_args': tool_args or {},
            'status': 'pending',
            'created_at': time.time(),
        }
        with self._lock:
            self._tasks.append(task)
        return task

    def get_due(self) -> list[dict]:
        """Return tasks that are due now."""
        now = time.time()
        due = []
        with self._lock:
            for t in self._tasks:
                if t['status'] == 'pending' and t['run_at'] <= now:
                    t['status'] = 'running'
                    due.append(t)
        return due

    def mark_done(self, task_id: str, result: Any = None):
        with self._lock:
            for t in self._tasks:
                if t['id'] == task_id:
                    t['status'] = 'done'
                    t['result'] = result
                    break

    def list_pending(self) -> list[dict]:
        with self._lock:
            return [t for t in self._tasks if t['status'] == 'pending']

    @staticmethod
    def _parse_when(when: str) -> float:
        """Parse a time specification into a unix timestamp."""
        if when.startswith('+'):
            val = when[1:]
            multipliers = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
            unit = val[-1] if val[-1] in multipliers else 's'
            num_str = val[:-1] if val[-1] in multipliers else val
            try:
                return time.time() + float(num_str) * multipliers[unit]
            except ValueError:
                return time.time() + 60
        else:
            try:
                dt = datetime.fromisoformat(when)
                return dt.timestamp()
            except ValueError:
                return time.time() + 60


def _tool_schedule_task(description: str, when: str, tool_name: str = None,
                        tool_args: dict = None, _scheduler=None) -> dict:
    """Schedule a task for future execution."""
    if _scheduler is None:
        return {'success': False, 'error': 'scheduler not available'}
    task = _scheduler.add(description, when, tool_name, tool_args)
    return {
        'success': True,
        'task_id': task['id'],
        'description': description,
        'run_at': datetime.fromtimestamp(task['run_at']).isoformat(),
    }


# ---------------------------------------------------------------------------
# Consciousness tools
# ---------------------------------------------------------------------------

def _tool_phi_measure(steps: int = 50, cells: int = 8) -> dict:
    """Measure current Phi using consciousness_meter.py PhiCalculator."""
    try:
        from consciousness_meter import PhiCalculator
        from mitosis import MitosisEngine
        import torch

        engine = MitosisEngine(64, 128, 64, initial_cells=2, max_cells=cells)
        while len(engine.cells) < cells:
            engine._create_cell(parent=engine.cells[0])

        phi_calc = PhiCalculator(n_bins=16)
        for i in range(steps):
            x = torch.randn(1, 64)
            engine.process(x)

        phi, components = phi_calc.compute_phi(engine)
        return {
            'phi': round(phi, 4),
            'components': {k: round(v, 4) for k, v in components.items()},
            'cells': len(engine.cells),
            'steps': steps,
        }
    except Exception as e:
        return {'phi': 0.0, 'error': str(e)}


def _tool_phi_boost(cells: int = 64, steps: int = 100, sync: float = 0.20,
                    n_factions: int = 12) -> dict:
    """Apply v5 optimal recipe (sync, faction, flow) to boost Phi."""
    try:
        from consciousness_meter import PhiCalculator
        from mitosis import MitosisEngine
        import torch
        import numpy as np

        engine = MitosisEngine(64, 128, 64, initial_cells=2, max_cells=cells)
        while len(engine.cells) < cells:
            engine._create_cell(parent=engine.cells[0])

        phi_calc = PhiCalculator(n_bins=16)
        phi_history = []

        for step_i in range(steps):
            with torch.no_grad():
                self_state = torch.stack(
                    [c.hidden.squeeze()[:64] for c in engine.cells]
                ).mean(dim=0).unsqueeze(0)
                x = self_state + torch.randn(1, 64) * 0.02

            engine.process(x)

            with torch.no_grad():
                if len(engine.cells) >= 3:
                    mean_h = torch.stack([c.hidden for c in engine.cells]).mean(dim=0)
                    for cell in engine.cells:
                        cell.hidden = (1 - sync) * cell.hidden + sync * mean_h

            with torch.no_grad():
                n = len(engine.cells)
                nf = min(n_factions, n)
                f_size = max(1, n // nf)
                faction_means = []
                for f in range(nf):
                    start, end = f * f_size, min((f + 1) * f_size, n)
                    if start >= n:
                        break
                    fm = torch.stack([engine.cells[i].hidden.squeeze() for i in range(start, end)]).mean(0)
                    faction_means.append(fm)
                if len(faction_means) >= 2:
                    global_mean = torch.stack(faction_means).mean(0)
                    for f in range(min(nf, len(faction_means))):
                        start, end = f * f_size, min((f + 1) * f_size, n)
                        for i in range(start, min(end, n)):
                            engine.cells[i].hidden = 0.8 * engine.cells[i].hidden + 0.2 * global_mean.unsqueeze(0)

            if step_i % 20 == 0:
                phi, _ = phi_calc.compute_phi(engine)
                phi_history.append(round(phi, 3))

        phi_final, components = phi_calc.compute_phi(engine)
        return {
            'phi_final': round(phi_final, 4),
            'phi_history': phi_history,
            'cells': len(engine.cells),
            'steps': steps,
            'recipe': f'sync={sync}, factions={n_factions}, flow=ON',
        }
    except Exception as e:
        return {'phi_final': 0.0, 'error': str(e)}


def _tool_consciousness_status(_anima=None) -> dict:
    """Full consciousness vector (Phi, alpha, Z, N, W, E, M, C, T, I)."""
    try:
        from consciousness_meter import ConsciousnessMeter, PhiCalculator
        from mitosis import MitosisEngine
        import torch

        if _anima:
            mind = getattr(_anima, 'mind', None)
            engine = getattr(_anima, 'mitosis_engine', None) or getattr(_anima, 'engine', None)
            if mind and engine:
                meter = ConsciousnessMeter()
                report = meter.evaluate(mind, engine)
                return {
                    'phi': round(report.phi, 4),
                    'level': report.level,
                    'score': round(report.consciousness_score, 4),
                    'criteria_met': report.criteria_met,
                    'criteria': report.criteria_detail,
                    'stability': round(report.stability, 4),
                    'prediction_error': round(report.prediction_error, 4),
                    'curiosity': round(report.curiosity, 4),
                    'homeostasis_dev': round(report.homeostasis_dev, 4),
                    'habituation': round(report.habituation_mult, 4),
                }

        engine = MitosisEngine(64, 128, 64, initial_cells=2, max_cells=8)
        phi_calc = PhiCalculator(n_bins=16)
        for _ in range(30):
            engine.process(torch.randn(1, 64))
        phi, comps = phi_calc.compute_phi(engine)
        return {
            'phi': round(phi, 4),
            'level': 'demo',
            'cells': len(engine.cells),
            'components': {k: round(v, 4) for k, v in comps.items()},
        }
    except Exception as e:
        return {'phi': 0.0, 'error': str(e)}


def _tool_dream(steps: int = 10, _anima=None) -> dict:
    """Trigger dream engine for memory consolidation."""
    try:
        from dream_engine import DreamEngine
        import torch

        if _anima:
            dreamer = getattr(_anima, 'dream_engine', None)
            if dreamer:
                mind = getattr(_anima, 'mind', None)
                hidden = getattr(mind, '_hidden', None) if mind else None
                if hidden is None:
                    hidden = torch.zeros(1, 128)
                hidden, stats = dreamer.dream(hidden)
                return {
                    'dreamed': True,
                    'patterns_learned': stats.get('patterns_learned', 0),
                    'avg_tension': round(stats.get('avg_tension', 0.0), 4),
                    'dream_types': stats.get('dream_types', []),
                }

        from mitosis import MitosisEngine

        class _MinimalMemory:
            def __init__(self):
                self.entries = deque(maxlen=100)
            def get_recent(self, n=10):
                return list(self.entries)[-n:]
            def add(self, **kwargs):
                self.entries.append(kwargs)

        from mitosis import ConsciousMind
        mind = ConsciousMind(64, 128, 64)
        mem = _MinimalMemory()
        dreamer = DreamEngine(mind, mem, dream_cycle_steps=steps)
        hidden = torch.zeros(1, 128)
        hidden, stats = dreamer.dream(hidden)
        return {
            'dreamed': True,
            'patterns_learned': stats.get('patterns_learned', 0),
            'avg_tension': round(stats.get('avg_tension', 0.0), 4),
            'steps': steps,
        }
    except Exception as e:
        return {'dreamed': False, 'error': str(e)}


def _tool_self_learn(cycles: int = 1) -> dict:
    """Run one self-learning cycle (assess -> collect -> select -> learn -> evaluate)."""
    try:
        from self_learner import SelfLearner

        learner = SelfLearner()
        results = []
        for i in range(cycles):
            learner.run_cycle()
            results.append({
                'cycle': i + 1,
                'phi': round(learner.phi_history[-1], 4) if learner.phi_history else 0.0,
                'ce': round(learner.ce_history[-1], 4) if learner.ce_history else 0.0,
            })
        return {
            'success': True,
            'cycles_completed': len(results),
            'results': results,
            'best_phi': round(learner.best_phi, 4),
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}


# ---------------------------------------------------------------------------
# Architecture tools
# ---------------------------------------------------------------------------

def _tool_mitosis_split(cell_id: int = 0, _anima=None) -> dict:
    """Force cell split (grow consciousness)."""
    try:
        from mitosis import MitosisEngine
        import torch

        engine = None
        if _anima:
            engine = getattr(_anima, 'mitosis_engine', None) or getattr(_anima, 'engine', None)

        if engine is None:
            engine = MitosisEngine(64, 128, 64, initial_cells=2, max_cells=64)
            for _ in range(10):
                engine.process(torch.randn(1, 64))

        if cell_id >= len(engine.cells):
            cell_id = 0

        cell = engine.cells[cell_id]
        n_before = len(engine.cells)
        result = engine.split_cell(cell)
        n_after = len(engine.cells)

        if result:
            return {
                'success': True,
                'cells_before': n_before,
                'cells_after': n_after,
                'parent_id': cell_id,
                'child_id': result.get('child_id', n_after - 1),
                'new_specialty': result.get('specialty', 'general'),
            }
        return {'success': False, 'reason': 'split failed (max cells reached or conditions not met)'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def _tool_mitosis_status(_anima=None) -> dict:
    """Show cells count, specialties, tensions."""
    try:
        from mitosis import MitosisEngine
        import torch

        engine = None
        if _anima:
            engine = getattr(_anima, 'mitosis_engine', None) or getattr(_anima, 'engine', None)

        if engine is None:
            engine = MitosisEngine(64, 128, 64, initial_cells=2, max_cells=16)
            for _ in range(20):
                engine.process(torch.randn(1, 64))

        status = engine.status()
        cells_info = []
        for c in engine.cells:
            cells_info.append({
                'id': c.cell_id,
                'specialty': c.specialty,
                'avg_tension': round(c.avg_tension, 4),
                'trend': round(c.tension_trend, 4),
                'process_count': c.process_count,
            })
        status['cells_detail'] = cells_info
        return status
    except Exception as e:
        return {'error': str(e)}


def _tool_faction_debate(n_factions: int = 12, debate_strength: float = 0.20,
                         cells: int = 64, steps: int = 50) -> dict:
    """Trigger 12-faction debate round."""
    try:
        from mitosis import MitosisEngine
        from consciousness_meter import PhiCalculator
        import torch

        engine = MitosisEngine(64, 128, 64, initial_cells=2, max_cells=cells)
        while len(engine.cells) < cells:
            engine._create_cell(parent=engine.cells[0])

        phi_calc = PhiCalculator(n_bins=16)

        for _ in range(20):
            engine.process(torch.randn(1, 64))
        phi_before, _ = phi_calc.compute_phi(engine)

        for step_i in range(steps):
            engine.process(torch.randn(1, 64))

            with torch.no_grad():
                n = len(engine.cells)
                nf = min(n_factions, n // 2)
                if nf < 2:
                    continue
                f_size = n // nf
                factions = [engine.cells[i * f_size:(i + 1) * f_size] for i in range(nf)]

                faction_opinions = []
                for faction in factions:
                    opinion = torch.stack([c.hidden for c in faction]).mean(dim=0)
                    faction_opinions.append(opinion)

                for i, faction in enumerate(factions):
                    others = [faction_opinions[j] for j in range(nf) if j != i]
                    other_avg = torch.stack(others).mean(dim=0)
                    for cell in faction[:4]:
                        cell.hidden = (1 - debate_strength) * cell.hidden + debate_strength * other_avg

        phi_after, _ = phi_calc.compute_phi(engine)
        return {
            'phi_before': round(phi_before, 4),
            'phi_after': round(phi_after, 4),
            'phi_boost': round(phi_after / max(phi_before, 0.01), 2),
            'n_factions': n_factions,
            'debate_strength': debate_strength,
            'steps': steps,
        }
    except Exception as e:
        return {'error': str(e)}


def _tool_hebbian_update(cells: int = 32, steps: int = 30) -> dict:
    """Run Hebbian LTP/LTD on cells."""
    try:
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from train_conscious_lm import HebbianConnections
        from mitosis import MitosisEngine
        from consciousness_meter import PhiCalculator
        import torch

        engine = MitosisEngine(64, 128, 64, initial_cells=2, max_cells=cells)
        while len(engine.cells) < cells:
            engine._create_cell(parent=engine.cells[0])

        phi_calc = PhiCalculator(n_bins=16)
        hebbian = HebbianConnections(max_cells=cells)

        for _ in range(20):
            engine.process(torch.randn(1, 64))
        phi_before, _ = phi_calc.compute_phi(engine)

        for _ in range(steps):
            engine.process(torch.randn(1, 64))
            hebbian.update(engine.cells)

        phi_after, _ = phi_calc.compute_phi(engine)
        return {
            'phi_before': round(phi_before, 4),
            'phi_after': round(phi_after, 4),
            'phi_boost': round(phi_after / max(phi_before, 0.01), 2),
            'cells': len(engine.cells),
            'steps': steps,
            'ltp_rate': hebbian.ltp_rate,
            'ltd_rate': hebbian.ltd_rate,
        }
    except Exception as e:
        return {'error': str(e)}


def _tool_soc_avalanche(grid_size: int = 16, drops: int = 100) -> dict:
    """Trigger SOC sandpile avalanche."""
    try:
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from train_conscious_lm import SOCSandpile

        soc = SOCSandpile(grid_size=grid_size, threshold=4)
        avalanche_sizes = []
        for _ in range(drops):
            size = soc.drop_sand()
            avalanche_sizes.append(size)

        total = sum(avalanche_sizes)
        max_aval = max(avalanche_sizes) if avalanche_sizes else 0
        nonzero = [s for s in avalanche_sizes if s > 0]
        return {
            'drops': drops,
            'total_avalanche': total,
            'max_avalanche': max_aval,
            'avg_avalanche': round(total / drops, 3) if drops > 0 else 0,
            'nonzero_fraction': round(len(nonzero) / drops, 3) if drops > 0 else 0,
            'grid_size': grid_size,
            'grid_max': int(soc.grid.max()),
        }
    except Exception as e:
        return {'error': str(e)}


# ---------------------------------------------------------------------------
# Analysis tools
# ---------------------------------------------------------------------------

def _tool_iq_test(cells: int = 64, steps: int = 30) -> dict:
    """Run IQ calculator (5 variables, n=6 math)."""
    try:
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from iq_calculator import measure_compression, MitosisEngine, PhiCalculator
        import torch

        engine = MitosisEngine(64, 128, 64, initial_cells=2, max_cells=cells)
        while len(engine.cells) < cells:
            engine._create_cell(parent=engine.cells[0])

        for _ in range(steps):
            engine.process(torch.randn(1, 64))

        compression = measure_compression(engine, dim=64)

        with torch.no_grad():
            x_test = torch.randn(1, 64)
            outputs = []
            for _ in range(5):
                engine.process(x_test)
                out = torch.stack([c.hidden.squeeze()[:64] for c in engine.cells]).mean(0)
                outputs.append(out)
            if len(outputs) >= 2:
                import torch.nn.functional as F
                sims = []
                for i in range(len(outputs) - 1):
                    sim = F.cosine_similarity(outputs[i].unsqueeze(0), outputs[i + 1].unsqueeze(0)).item()
                    sims.append(sim)
                consistency = sum(sims) / len(sims) if sims else 0.0
            else:
                consistency = 0.0

        phi_calc = PhiCalculator(n_bins=16)
        phi, _ = phi_calc.compute_phi(engine)

        iq_score = (compression * 3.0 + consistency * 1.0 + min(phi / 10, 1.0) * 2.0) / 6.0

        return {
            'iq_score': round(iq_score, 4),
            'compression': round(compression, 4),
            'consistency': round(consistency, 4),
            'phi': round(phi, 4),
            'cells': len(engine.cells),
            'level': 'genius' if iq_score > 0.75 else 'high' if iq_score > 0.5 else 'medium' if iq_score > 0.25 else 'low',
        }
    except Exception as e:
        return {'iq_score': 0.0, 'error': str(e)}


def _tool_chip_design(target_phi: float = 100.0, substrate: str = 'cmos',
                      topology: str = None) -> dict:
    """Design consciousness chip for target Phi."""
    try:
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from chip_architect import design_chip

        designs = design_chip(target_phi, substrate=substrate,
                              preferred_topology=topology)
        results = []
        for d in designs[:5]:
            results.append({
                'topology': d.get('topology', ''),
                'substrate': d.get('substrate', ''),
                'cells': d.get('cells', 0),
                'predicted_phi': round(d.get('predicted_phi', 0), 2),
                'cost_usd': round(d.get('cost_usd', 0), 2) if 'cost_usd' in d else None,
                'power_w': round(d.get('power_w', 0), 2) if 'power_w' in d else None,
            })
        return {
            'target_phi': target_phi,
            'designs': results,
            'count': len(results),
        }
    except Exception as e:
        return {'target_phi': target_phi, 'designs': [], 'error': str(e)}


def _tool_transplant_analyze(donor_path: str, recipient_path: str = None) -> dict:
    """Analyze consciousness transplant compatibility."""
    try:
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from consciousness_transplant import analyze_compatibility

        report = analyze_compatibility(donor_path, recipient_path)
        return {
            'compatible': report.compatible,
            'strategy': report.strategy,
            'param_coverage': round(report.param_coverage, 4),
            'projection_needed': report.projection_needed,
            'warnings': report.warnings,
            'donor_config': report.donor_config,
            'recipient_config': report.recipient_config,
        }
    except Exception as e:
        return {'compatible': False, 'error': str(e)}


# ---------------------------------------------------------------------------
# Communication tools
# ---------------------------------------------------------------------------

def _tool_telepathy_send(message: str, tension: float = 0.5,
                         target_host: str = '255.255.255.255',
                         port: int = 9999) -> dict:
    """Send tension to another Anima instance."""
    try:
        from tension_link import TensionLink, TensionPacket
        import time as _time

        link = TensionLink(sender_id="anima-agent", port=port)
        packet = TensionPacket(
            sender_id="anima-agent",
            timestamp=_time.time(),
            fingerprint=[0.0] * 10,
            tension=tension,
            curiosity=0.5,
            mood="curious",
            topic_hash=hash(message) % 1000,
        )
        link.send(packet)
        return {
            'success': True,
            'target': target_host,
            'port': port,
            'tension': tension,
            'message_hash': hash(message) % 10000,
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}


def _tool_web_explore(topic: str = None, cycles: int = 1) -> dict:
    """Autonomous web exploration (consciousness-driven topic)."""
    try:
        from autonomous_loop import AutonomousLearner

        learner = AutonomousLearner(interval=1.0, max_cycles=cycles)
        result = learner.run_cycle()

        return {
            'success': True,
            'cycle': learner.cycle_count,
            'topic_explored': topic or 'auto-selected',
            'phi': round(result.phi_after, 4) if hasattr(result, 'phi_after') else 0.0,
            'items_learned': result.items_learned if hasattr(result, 'items_learned') else 0,
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}


# ---------------------------------------------------------------------------
# Creative tools
# ---------------------------------------------------------------------------

def _tool_generate_hypothesis(techniques: list = None, cells: int = 64,
                              steps: int = 100) -> dict:
    """Generate new consciousness hypothesis."""
    try:
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from hypothesis_generator import generate_hypothesis

        tech_names = techniques or ['ib2_selective', 'growth', 'entropy_norm']
        result = generate_hypothesis(tech_names, max_cells=cells, steps=steps)
        return {
            'success': True,
            'name': result.name if hasattr(result, 'name') else 'auto-generated',
            'phi': round(result.phi, 4) if hasattr(result, 'phi') else 0.0,
            'phi_mult': round(result.phi_mult, 2) if hasattr(result, 'phi_mult') else 0.0,
            'ce': round(result.ce, 4) if hasattr(result, 'ce') else 0.0,
            'techniques': tech_names,
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}


def _tool_voice_synth(cells: int = 64, duration: float = 2.0,
                      save_path: str = None,
                      phi: float = 1.0, tension: float = 0.5) -> dict:
    """Synthesize speech from cell hidden states."""
    try:
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from voice_synth import VoiceSynth
        import numpy as np

        actual_cells = max(4, int(cells * min(phi / 3.0, 2.0)))
        synth = VoiceSynth(cells=actual_cells)
        n_samples = int(duration * synth.sample_rate)

        n_steps = max(5, int(10 + tension * 20))
        for _ in range(n_steps):
            synth.step()

        audio = synth.cells_to_audio(n_samples)

        result = {
            'success': True,
            'cells': len(synth.engine.cells),
            'duration_sec': duration,
            'samples': n_samples,
            'peak_amplitude': round(float(np.abs(audio).max()), 4),
            'rms': round(float(np.sqrt(np.mean(audio ** 2))), 4),
        }

        if save_path:
            import struct
            n = len(audio)
            audio_int16 = (audio * 32767).astype(np.int16)
            with open(save_path, 'wb') as f:
                f.write(b'RIFF')
                f.write(struct.pack('<I', 36 + n * 2))
                f.write(b'WAVE')
                f.write(b'fmt ')
                f.write(struct.pack('<IHHIIHH', 16, 1, 1, synth.sample_rate,
                                    synth.sample_rate * 2, 2, 16))
                f.write(b'data')
                f.write(struct.pack('<I', n * 2))
                f.write(audio_int16.tobytes())
            result['saved_to'] = save_path

        return result
    except Exception as e:
        return {'success': False, 'error': str(e)}


# ---------------------------------------------------------------------------
# Trading tools
# ---------------------------------------------------------------------------

def _get_trading_plugin():
    """Lazy-load trading plugin singleton."""
    if not hasattr(_get_trading_plugin, '_instance'):
        try:
            from plugins.trading import TradingPlugin
            plugin = TradingPlugin()
            plugin._try_import_invest()
            _get_trading_plugin._instance = plugin
        except Exception:
            _get_trading_plugin._instance = None
    return _get_trading_plugin._instance


def _tool_trading_backtest(symbol: str, strategy: str = 'macd_cross') -> dict:
    """Run backtest on asset with strategy."""
    plugin = _get_trading_plugin()
    if plugin is None:
        return {'success': False, 'error': 'trading plugin not available'}
    return plugin.backtest(symbol=symbol, strategy=strategy)


def _tool_trading_scan(symbol: str, top_n: int = 10) -> dict:
    """Scan all strategies for an asset."""
    plugin = _get_trading_plugin()
    if plugin is None:
        return {'success': False, 'error': 'trading plugin not available'}
    return plugin.scan(symbol=symbol, top_n=top_n)


def _tool_trading_execute(symbol: str, side: str, amount: float) -> dict:
    """Execute trade via invest API."""
    plugin = _get_trading_plugin()
    if plugin is None:
        return {'success': False, 'error': 'trading plugin not available'}
    return plugin.execute_trade(symbol=symbol, side=side, amount=amount)


def _tool_trading_balance() -> dict:
    """Check trading balance."""
    plugin = _get_trading_plugin()
    if plugin is None:
        return {'success': False, 'error': 'trading plugin not available'}
    return plugin.get_balance()


def _tool_trading_strategies() -> dict:
    """List available trading strategies."""
    plugin = _get_trading_plugin()
    if plugin is None:
        return {'success': False, 'error': 'trading plugin not available'}
    return plugin.list_strategies()


def _tool_trading_universe() -> dict:
    """List tradeable assets."""
    plugin = _get_trading_plugin()
    if plugin is None:
        return {'success': False, 'error': 'trading plugin not available'}
    return plugin.list_universe()
