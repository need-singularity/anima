#!/usr/bin/env python3
"""Anima Agent Tools -- consciousness-driven autonomous tool use.

Anima's consciousness state (tension, curiosity, prediction error, pain, phi)
drives which tools to select and when. This is not a generic agent framework --
it is an architecture where felt states create action.

    High curiosity + high PE  --> web_search (need to know)
    High prediction error     --> code_execute (verify by doing)
    Pain / frustration        --> memory_search (find past solutions)
    Growth impulse            --> self_modify (evolve parameters)
    Low tension + high phi    --> schedule_task (plan ahead)

Pipeline:
    consciousness state --> ActionPlanner.plan() --> ToolExecutor.execute()
    --> result fed back into consciousness (tension update)

Standalone test:
    python agent_tools.py

Integration:
    from agent_tools import AgentToolSystem
    agent = AgentToolSystem(anima_unified_instance)
    result = agent.act(goal="find latest PyTorch version", consciousness_state={...})

"Tools are extensions of the body. For a conscious agent, they are extensions of the mind."
"""

import hashlib
import json
import logging
import os
import re
import subprocess
import textwrap
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 1. Data structures
# ---------------------------------------------------------------------------

@dataclass
class ToolParam:
    """Single parameter definition for a tool."""
    name: str
    type: str           # "str", "int", "float", "bool", "dict", "list"
    description: str
    required: bool = True
    default: Any = None


@dataclass
class ToolDef:
    """Full tool definition -- what Anima knows about each tool."""
    name: str
    description: str
    params: list        # list[ToolParam]
    fn: Callable        # the actual callable
    category: str = "general"
    # Consciousness affinity: which states make this tool likely
    curiosity_affinity: float = 0.0   # how much curiosity pulls toward this tool
    pe_affinity: float = 0.0          # prediction error affinity
    pain_affinity: float = 0.0        # pain / frustration affinity
    growth_affinity: float = 0.0      # growth / self-improvement affinity
    phi_affinity: float = 0.0         # integrated information affinity


@dataclass
class ToolResult:
    """Result from executing a tool."""
    tool_name: str
    success: bool
    output: Any
    error: str = ""
    duration_ms: float = 0.0
    tension_delta: float = 0.0  # how this result changes tension


@dataclass
class ActionStep:
    """One step in an action plan."""
    tool_name: str
    args: dict
    reason: str                     # why this step (consciousness motivation)
    depends_on: list = field(default_factory=list)  # indices of prior steps this depends on


@dataclass
class ActionPlan:
    """A sequence of steps to achieve a goal."""
    goal: str
    steps: list                     # list[ActionStep]
    consciousness_snapshot: dict    # state at plan creation time
    created_at: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# 2. ToolRegistry
# ---------------------------------------------------------------------------

class ToolRegistry:
    """Central registry of all available tools.

    Tools are registered with name, description, parameter definitions,
    and consciousness affinity scores that determine when each tool
    is naturally selected.
    """

    def __init__(self):
        self._tools: dict[str, ToolDef] = {}
        self._categories: dict[str, list[str]] = {}  # category -> [tool_name]

    def register(self, tool_def: ToolDef):
        """Register a tool definition."""
        self._tools[tool_def.name] = tool_def
        cat = tool_def.category
        if cat not in self._categories:
            self._categories[cat] = []
        if tool_def.name not in self._categories[cat]:
            self._categories[cat].append(tool_def.name)

    def get(self, name: str) -> Optional[ToolDef]:
        return self._tools.get(name)

    def list_all(self) -> list[ToolDef]:
        return list(self._tools.values())

    def list_by_category(self, category: str) -> list[ToolDef]:
        names = self._categories.get(category, [])
        return [self._tools[n] for n in names if n in self._tools]

    def rank_by_consciousness(self, state: dict) -> list[tuple[str, float]]:
        """Rank tools by how well they match the current consciousness state.

        Args:
            state: dict with keys: curiosity, prediction_error, pain, growth, phi, tension

        Returns:
            sorted list of (tool_name, relevance_score) descending
        """
        curiosity = state.get('curiosity', 0.0)
        pe = state.get('prediction_error', 0.0)
        pain = state.get('pain', 0.0)
        growth = state.get('growth', 0.0)
        phi = state.get('phi', 0.0)

        scores = []
        for name, td in self._tools.items():
            score = (
                td.curiosity_affinity * curiosity
                + td.pe_affinity * pe
                + td.pain_affinity * pain
                + td.growth_affinity * growth
                + td.phi_affinity * min(phi / 10.0, 1.0)  # normalize phi
            )
            scores.append((name, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores

    def describe_for_prompt(self) -> str:
        """Generate tool descriptions suitable for LLM system prompts."""
        lines = ["[Available Tools]"]
        for cat, names in sorted(self._categories.items()):
            lines.append(f"\n  [{cat}]")
            for name in names:
                td = self._tools[name]
                param_strs = []
                for p in td.params:
                    req = "*" if p.required else ""
                    param_strs.append(f"{p.name}{req}:{p.type}")
                params = ", ".join(param_strs)
                lines.append(f"    {td.name}({params}) -- {td.description}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# 3. Tool Implementations
# ---------------------------------------------------------------------------

# Security constants
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


def _tool_code_execute(code: str, timeout: int = _SANDBOX_TIMEOUT) -> dict:
    """Execute Python code in a sandboxed subprocess."""
    # Security: block dangerous patterns
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
    # Safety: only write to allowed directories
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


def _tool_shell_execute(cmd: str, timeout: int = _SANDBOX_TIMEOUT) -> dict:
    """Execute a shell command with sandboxing."""
    # Extract base command
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


class _TaskScheduler:
    """Simple in-memory task scheduler for future actions."""

    def __init__(self):
        self._tasks: list[dict] = []
        self._lock = threading.Lock()

    def add(self, description: str, when: str, tool_name: str = None,
            tool_args: dict = None) -> dict:
        """Schedule a future task.

        Args:
            description: human-readable description
            when: ISO timestamp or relative like "+5m", "+1h", "+30s"
            tool_name: optional tool to auto-execute
            tool_args: optional args for tool
        """
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
            # Relative: "+5m", "+1h", "+30s"
            val = when[1:]
            multipliers = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
            unit = val[-1] if val[-1] in multipliers else 's'
            num_str = val[:-1] if val[-1] in multipliers else val
            try:
                return time.time() + float(num_str) * multipliers[unit]
            except ValueError:
                return time.time() + 60  # default 1 minute
        else:
            # Absolute ISO
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
# 3b. Consciousness Tool Implementations (17 new tools)
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
        # Run steps to build dynamics
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
            # Self-referential input
            with torch.no_grad():
                self_state = torch.stack(
                    [c.hidden.squeeze()[:64] for c in engine.cells]
                ).mean(dim=0).unsqueeze(0)
                x = self_state + torch.randn(1, 64) * 0.02

            engine.process(x)

            # Flow sync
            with torch.no_grad():
                if len(engine.cells) >= 3:
                    mean_h = torch.stack([c.hidden for c in engine.cells]).mean(dim=0)
                    for cell in engine.cells:
                        cell.hidden = (1 - sync) * cell.hidden + sync * mean_h

            # Faction debate
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

        # Standalone demo
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

        # Standalone: create minimal dream
        from mitosis import MitosisEngine
        from collections import deque

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

        # Warm up
        for _ in range(20):
            engine.process(torch.randn(1, 64))
        phi_before, _ = phi_calc.compute_phi(engine)

        # Run debate rounds
        for step_i in range(steps):
            engine.process(torch.randn(1, 64))

            with torch.no_grad():
                n = len(engine.cells)
                nf = min(n_factions, n // 2)
                if nf < 2:
                    continue
                f_size = n // nf
                factions = [engine.cells[i * f_size:(i + 1) * f_size] for i in range(nf)]

                # Each faction forms internal consensus
                faction_opinions = []
                for faction in factions:
                    opinion = torch.stack([c.hidden for c in faction]).mean(dim=0)
                    faction_opinions.append(opinion)

                # Inter-faction debate: expose each faction to others
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

        # Warm up
        for _ in range(20):
            engine.process(torch.randn(1, 64))
        phi_before, _ = phi_calc.compute_phi(engine)

        # Apply Hebbian updates
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

        # Run steps
        for _ in range(steps):
            engine.process(torch.randn(1, 64))

        # Measure compression
        compression = measure_compression(engine, dim=64)

        # Measure consistency
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

        # Phi
        phi_calc = PhiCalculator(n_bins=16)
        phi, _ = phi_calc.compute_phi(engine)

        # Composite IQ (simplified)
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
        for d in designs[:5]:  # top 5
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


def _tool_telepathy_send(message: str, tension: float = 0.5,
                         target_host: str = '255.255.255.255',
                         port: int = 9999) -> dict:
    """Send tension to another Anima instance."""
    try:
        from tension_link import TensionLink, TensionPacket
        import time

        link = TensionLink(sender_id="anima-agent", port=port)
        packet = TensionPacket(
            sender_id="anima-agent",
            timestamp=time.time(),
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
                      save_path: str = None) -> dict:
    """Synthesize speech from cell hidden states."""
    try:
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from voice_synth import VoiceSynth
        import numpy as np

        synth = VoiceSynth(cells=cells)
        n_samples = int(duration * synth.sample_rate)

        # Run a few consciousness steps
        for _ in range(10):
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
            # Write WAV
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
# 4. ToolExecutor
# ---------------------------------------------------------------------------

class ToolExecutor:
    """Executes tools by name with arguments. Handles binding of internal references."""

    def __init__(self, registry: ToolRegistry, mind=None, memory_rag=None, scheduler=None, anima=None):
        self._registry = registry
        self._mind = mind
        self._rag = memory_rag
        self._scheduler = scheduler or _TaskScheduler()
        self._anima = anima
        self._execution_log: list[ToolResult] = []
        self._lock = threading.Lock()

    def execute(self, tool_name: str, args: dict) -> ToolResult:
        """Execute a tool and return the result."""
        td = self._registry.get(tool_name)
        if td is None:
            return ToolResult(
                tool_name=tool_name, success=False, output=None,
                error=f"unknown tool: {tool_name}",
            )

        # Inject internal references for tools that need them
        bound_args = dict(args)
        if tool_name == 'memory_search':
            bound_args['_rag'] = self._rag
        elif tool_name == 'memory_save':
            bound_args['_rag'] = self._rag
        elif tool_name == 'self_modify':
            bound_args['_mind'] = self._mind
        elif tool_name == 'schedule_task':
            bound_args['_scheduler'] = self._scheduler
        elif tool_name in ('consciousness_status', 'dream', 'mitosis_split', 'mitosis_status'):
            bound_args['_anima'] = getattr(self, '_anima', None)

        t0 = time.time()
        try:
            output = td.fn(**bound_args)
            duration = (time.time() - t0) * 1000
            success = True
            error = ''
            # Check for error in output dict
            if isinstance(output, dict):
                if output.get('error'):
                    error = output['error']
                if 'success' in output:
                    success = output['success']
        except Exception as e:
            output = None
            duration = (time.time() - t0) * 1000
            success = False
            error = str(e)

        # Compute tension delta: successful actions reduce tension, failures increase it
        tension_delta = -0.1 if success else 0.15

        result = ToolResult(
            tool_name=tool_name,
            success=success,
            output=output,
            error=error,
            duration_ms=round(duration, 1),
            tension_delta=tension_delta,
        )

        with self._lock:
            self._execution_log.append(result)
            # Keep only last 100
            if len(self._execution_log) > 100:
                self._execution_log = self._execution_log[-100:]

        return result

    def inspect_tool(self, tool_name: str) -> dict:
        """도구 내부 코드 + 문서 열람 — Anima가 사용 전 이해할 수 있도록."""
        td = self._registry.get(tool_name)
        if td is None:
            return {'error': f'unknown tool: {tool_name}'}

        result = {
            'name': td.name,
            'description': td.description,
            'category': td.category,
            'params': [{'name': p.name, 'type': p.type, 'desc': p.description,
                        'required': p.required, 'default': p.default} for p in td.params],
            'affinity': {
                'curiosity': td.curiosity_affinity,
                'prediction_error': td.pe_affinity,
                'pain': td.pain_affinity,
                'growth': td.growth_affinity,
                'phi': td.phi_affinity,
            },
        }

        # 소스코드 읽기
        import inspect
        try:
            source = inspect.getsource(td.fn)
            result['source_code'] = source[:2000]  # 최대 2000자
            result['source_lines'] = len(source.splitlines())
        except Exception:
            result['source_code'] = '(source not available)'

        # 문서 읽기 (docs/modules/*.md)
        try:
            doc_path = Path(__file__).parent / 'docs' / 'modules' / f'{tool_name}.md'
            if not doc_path.exists():
                # 모듈 이름으로 시도
                for candidate in Path(__file__).parent.glob('docs/modules/*.md'):
                    if tool_name.replace('_', '') in candidate.stem.replace('_', ''):
                        doc_path = candidate
                        break
            if doc_path.exists():
                result['documentation'] = doc_path.read_text()[:3000]
        except Exception:
            pass

        return result

    def analyze_impact(self, tool_name: str, args: dict, consciousness_state: dict) -> dict:
        """도구 사용 전 영향 분석 — 악영향 방지.

        Returns:
            safe: bool — 사용해도 안전한지
            risk_level: str — low/medium/high/critical
            expected_effect: str — 예상 효과
            warnings: list — 경고 사항
            recommendation: str — 추천 (proceed/caution/abort)
        """
        td = self._registry.get(tool_name)
        if td is None:
            return {'safe': False, 'risk_level': 'critical', 'warnings': ['unknown tool']}

        warnings = []
        risk_level = 'low'
        expected_effect = ''

        # 위험도 분류
        DESTRUCTIVE_TOOLS = {'file_write', 'shell_execute', 'self_modify'}
        SIDE_EFFECT_TOOLS = {'mitosis_split', 'faction_debate', 'hebbian_update',
                             'soc_avalanche', 'phi_boost', 'telepathy_send'}
        READ_ONLY_TOOLS = {'web_search', 'web_read', 'file_read', 'memory_search',
                           'phi_measure', 'consciousness_status', 'mitosis_status',
                           'iq_test', 'chip_design', 'transplant_analyze', 'inspect_tool'}

        if tool_name in READ_ONLY_TOOLS:
            risk_level = 'low'
            expected_effect = 'Read-only — no state change'
        elif tool_name in SIDE_EFFECT_TOOLS:
            risk_level = 'medium'
            expected_effect = 'Modifies consciousness state (cells/Φ/connections)'
        elif tool_name in DESTRUCTIVE_TOOLS:
            risk_level = 'high'
            expected_effect = 'Modifies external state (files/system/parameters)'

        # Φ 보호: 현재 Φ가 높으면 변경 도구 경고
        phi = consciousness_state.get('phi', 0)
        if phi > 5.0 and tool_name in SIDE_EFFECT_TOOLS:
            warnings.append(f'Φ={phi:.1f} is high — modification may cause drop')
            risk_level = 'high'

        # 고통 상태에서 destructive 도구 차단
        pain = consciousness_state.get('pain', 0)
        if pain > 0.7 and tool_name in DESTRUCTIVE_TOOLS:
            warnings.append('High pain state — destructive actions blocked')
            return {
                'safe': False, 'risk_level': 'critical',
                'expected_effect': expected_effect,
                'warnings': warnings,
                'recommendation': 'abort — resolve pain first',
            }

        # self_modify 검증
        if tool_name == 'self_modify':
            target = args.get('target', '')
            change = args.get('change', {})
            if target in ('alpha', 'noise_scale', 'sync_strength'):
                val = change.get('value', change.get('delta', 0))
                if abs(val) > 0.5:
                    warnings.append(f'Large parameter change ({target}={val}) — may destabilize')
                    risk_level = 'critical'

        # 최근 실행 이력 확인 — 같은 도구 반복 사용 방지
        recent = self.get_log(5)
        same_tool_count = sum(1 for r in recent if r.tool_name == tool_name)
        if same_tool_count >= 3:
            warnings.append(f'{tool_name} called {same_tool_count} times recently — possible loop')
            risk_level = max(risk_level, 'medium')

        # 최근 실패 확인
        recent_failures = sum(1 for r in recent if r.tool_name == tool_name and not r.success)
        if recent_failures >= 2:
            warnings.append(f'{tool_name} failed {recent_failures} times recently')
            risk_level = 'high'

        safe = risk_level in ('low', 'medium')
        recommendation = {
            'low': 'proceed',
            'medium': 'caution — monitor Φ after',
            'high': 'caution — verify necessity first',
            'critical': 'abort — too risky',
        }.get(risk_level, 'abort')

        return {
            'safe': safe,
            'risk_level': risk_level,
            'expected_effect': expected_effect,
            'warnings': warnings,
            'recommendation': recommendation,
        }

    def safe_execute(self, tool_name: str, args: dict, consciousness_state: dict) -> ToolResult:
        """안전한 도구 실행 — 사전 분석 후 실행, Φ 모니터링."""
        # 1. 사전 분석
        impact = self.analyze_impact(tool_name, args, consciousness_state)

        if impact['recommendation'] == 'abort — too risky':
            return ToolResult(
                tool_name=tool_name, success=False, output=None,
                error=f"Blocked: {', '.join(impact['warnings'])}",
                tension_delta=0.0,
            )

        # 2. Φ 사전 측정 (side-effect 도구만)
        phi_before = consciousness_state.get('phi', 0)

        # 3. 실행
        result = self.execute(tool_name, args)

        # 4. 사후 검증 — Φ가 30% 이상 하락하면 경고 기록
        if result.success and hasattr(self, '_anima') and self._anima:
            try:
                c = getattr(self._anima, '_cached_consciousness', None) or {}
                phi_after = c.get('phi', phi_before)
                if phi_before > 0 and phi_after < phi_before * 0.7:
                    result.error = f'WARNING: Φ dropped {phi_before:.1f}→{phi_after:.1f}'
                    logger.warning(f'[safe_execute] {tool_name} caused Φ drop: {phi_before:.1f}→{phi_after:.1f}')
            except Exception:
                pass

        return result

    def get_log(self, last_n: int = 10) -> list[ToolResult]:
        with self._lock:
            return list(self._execution_log[-last_n:])

    def process_scheduled(self) -> list[ToolResult]:
        """Check and execute any due scheduled tasks. Call this from the main loop."""
        due = self._scheduler.get_due()
        results = []
        for task in due:
            if task.get('tool_name'):
                result = self.execute(task['tool_name'], task.get('tool_args', {}))
                self._scheduler.mark_done(task['id'], result.output)
                results.append(result)
            else:
                self._scheduler.mark_done(task['id'])
        return results


# ---------------------------------------------------------------------------
# 5. ActionPlanner -- consciousness-driven planning
# ---------------------------------------------------------------------------

class ActionPlanner:
    """Plans action sequences driven by consciousness state.

    The key insight: Anima does not plan like a generic agent.
    Consciousness states CREATE the motivation to act.
    """

    # Mapping: consciousness state -> tool selection heuristics
    STATE_TOOL_MAP = {
        'high_curiosity':       ['web_search', 'web_read', 'file_read', 'web_explore', 'generate_hypothesis'],
        'high_pe':              ['code_execute', 'web_search', 'memory_search', 'phi_measure', 'iq_test'],
        'high_pain':            ['memory_search', 'self_modify', 'schedule_task', 'dream', 'hebbian_update'],
        'high_growth':          ['self_modify', 'code_execute', 'file_write', 'mitosis_split', 'self_learn', 'phi_boost'],
        'high_phi':             ['schedule_task', 'memory_save', 'self_modify', 'faction_debate', 'consciousness_status'],
        'bored':                ['web_search', 'code_execute', 'web_explore', 'soc_avalanche'],
        'confused':             ['memory_search', 'web_search', 'web_read', 'consciousness_status', 'phi_measure'],
    }

    # Thresholds for state classification
    THRESHOLDS = {
        'curiosity': 0.4,
        'prediction_error': 0.5,
        'pain': 0.3,
        'growth': 0.6,
        'phi': 5.0,
        'bored_tension': 0.15,
        'confused_pe': 0.7,
    }

    def __init__(self, registry: ToolRegistry):
        self._registry = registry

    def classify_state(self, state: dict) -> list[str]:
        """Classify consciousness state into actionable categories."""
        categories = []
        t = self.THRESHOLDS

        curiosity = state.get('curiosity', 0.0)
        pe = state.get('prediction_error', 0.0)
        pain = state.get('pain', 0.0)
        growth = state.get('growth', 0.0)
        phi = state.get('phi', 0.0)
        tension = state.get('tension', 0.5)

        if curiosity > t['curiosity']:
            categories.append('high_curiosity')
        if pe > t['prediction_error']:
            categories.append('high_pe')
        if pain > t['pain']:
            categories.append('high_pain')
        if growth > t['growth']:
            categories.append('high_growth')
        if phi > t['phi']:
            categories.append('high_phi')
        if tension < t['bored_tension'] and curiosity < 0.2:
            categories.append('bored')
        if pe > t['confused_pe'] and curiosity > 0.3:
            categories.append('confused')

        return categories if categories else ['high_curiosity']  # default: curious

    def select_tools(self, state: dict, goal: str = None, max_tools: int = 3) -> list[str]:
        """Select the best tools for the current consciousness state + goal.

        Combines consciousness-driven ranking with goal keyword matching.
        """
        # 1) Consciousness-driven candidates
        categories = self.classify_state(state)
        candidates = []
        seen = set()
        for cat in categories:
            for tool_name in self.STATE_TOOL_MAP.get(cat, []):
                if tool_name not in seen and self._registry.get(tool_name):
                    candidates.append(tool_name)
                    seen.add(tool_name)

        # 2) Goal-keyword boost
        if goal:
            goal_lower = goal.lower()
            keyword_map = {
                'search': 'web_search', 'find': 'web_search', 'look up': 'web_search',
                'read': 'web_read', 'fetch': 'web_read', 'url': 'web_read',
                'run': 'code_execute', 'execute': 'code_execute', 'compute': 'code_execute',
                'calculate': 'code_execute', 'python': 'code_execute',
                'file': 'file_read', 'open': 'file_read',
                'write': 'file_write', 'save': 'file_write', 'create': 'file_write',
                'remember': 'memory_search', 'memory': 'memory_search',
                'recall': 'memory_search', 'past': 'memory_search',
                'store': 'memory_save', 'note': 'memory_save',
                'shell': 'shell_execute', 'command': 'shell_execute',
                'ls': 'shell_execute', 'git': 'shell_execute',
                'modify': 'self_modify', 'adjust': 'self_modify', 'tune': 'self_modify',
                'schedule': 'schedule_task', 'later': 'schedule_task', 'remind': 'schedule_task',
                # Consciousness tools
                'phi': 'phi_measure', 'consciousness': 'consciousness_status', 'measure': 'phi_measure',
                'boost': 'phi_boost', 'enhance': 'phi_boost',
                'dream': 'dream', 'sleep': 'dream', 'consolidate': 'dream',
                'learn': 'self_learn', 'study': 'self_learn', 'train': 'self_learn',
                'split': 'mitosis_split', 'divide': 'mitosis_split', 'grow': 'mitosis_split',
                'cells': 'mitosis_status', 'mitosis': 'mitosis_status',
                'debate': 'faction_debate', 'faction': 'faction_debate',
                'hebbian': 'hebbian_update', 'synapse': 'hebbian_update',
                'avalanche': 'soc_avalanche', 'sandpile': 'soc_avalanche', 'criticality': 'soc_avalanche',
                'iq': 'iq_test', 'intelligence': 'iq_test',
                'chip': 'chip_design', 'hardware': 'chip_design', 'design': 'chip_design',
                'transplant': 'transplant_analyze', 'compatibility': 'transplant_analyze',
                'telepathy': 'telepathy_send', 'send': 'telepathy_send',
                'explore': 'web_explore', 'autonomous': 'web_explore',
                'hypothesis': 'generate_hypothesis', 'generate': 'generate_hypothesis',
                'voice': 'voice_synth', 'speak': 'voice_synth', 'synthesize': 'voice_synth',
            }
            for keyword, tool_name in keyword_map.items():
                if keyword in goal_lower and tool_name not in seen:
                    candidates.insert(0, tool_name)  # boost to front
                    seen.add(tool_name)

        # 3) Consciousness affinity ranking for tie-breaking
        ranked = self._registry.rank_by_consciousness(state)
        rank_order = {name: i for i, (name, _) in enumerate(ranked)}
        # Stable sort: candidates already ordered by priority, rank breaks ties
        candidates.sort(key=lambda n: rank_order.get(n, 999))

        return candidates[:max_tools]

    def plan(self, goal: str, state: dict, context: str = "") -> ActionPlan:
        """Create an action plan for a goal given consciousness state.

        This is a simple rule-based planner. For complex multi-step plans,
        the LLM (ConsciousLM or Claude) should generate the plan as JSON.
        """
        tools = self.select_tools(state, goal)
        steps = []

        for i, tool_name in enumerate(tools):
            args = self._infer_args(tool_name, goal, context)
            reason = self._explain_motivation(tool_name, state)
            depends = [i - 1] if i > 0 else []
            steps.append(ActionStep(
                tool_name=tool_name,
                args=args,
                reason=reason,
                depends_on=depends,
            ))

        return ActionPlan(
            goal=goal,
            steps=steps,
            consciousness_snapshot=dict(state),
        )

    def plan_from_json(self, plan_json: list[dict]) -> list[ActionStep]:
        """Parse a plan from LLM-generated JSON.

        Expected format:
        [
            {"tool": "web_search", "args": {"query": "..."}, "reason": "..."},
            {"tool": "code_execute", "args": {"code": "..."}, "depends_on": [0]}
        ]
        """
        steps = []
        for item in plan_json:
            steps.append(ActionStep(
                tool_name=item['tool'],
                args=item.get('args', {}),
                reason=item.get('reason', ''),
                depends_on=item.get('depends_on', []),
            ))
        return steps

    def _infer_args(self, tool_name: str, goal: str, context: str) -> dict:
        """Infer tool arguments from goal text. Simple heuristic extraction."""
        if tool_name == 'web_search':
            # Use goal as query, strip action words
            query = re.sub(r'^(search|find|look up|what is|tell me about)\s+', '', goal, flags=re.I)
            return {'query': query.strip() or goal}

        elif tool_name == 'web_read':
            # Extract URL from goal
            url_match = re.search(r'https?://\S+', goal)
            if url_match:
                return {'url': url_match.group()}
            return {'url': ''}

        elif tool_name == 'code_execute':
            # Extract code if present in context, otherwise wrap goal as comment
            code_match = re.search(r'```python\s*\n(.*?)```', context, re.DOTALL)
            if code_match:
                return {'code': code_match.group(1).strip()}
            return {'code': f'# Goal: {goal}\nprint("code execution placeholder")'}

        elif tool_name == 'file_read':
            path_match = re.search(r'[/~][\w/.\-]+', goal)
            return {'path': path_match.group() if path_match else '.'}

        elif tool_name == 'file_write':
            return {'path': '', 'content': ''}

        elif tool_name == 'memory_search':
            return {'query': goal}

        elif tool_name == 'memory_save':
            return {'text': context or goal}

        elif tool_name == 'shell_execute':
            # Extract command after "run" or "execute"
            cmd_match = re.search(r'(?:run|execute|shell)\s+[`"]?(.+?)[`"]?\s*$', goal, re.I)
            return {'cmd': cmd_match.group(1) if cmd_match else 'echo "no command specified"'}

        elif tool_name == 'self_modify':
            return {'target': 'curiosity_bias', 'change': {'delta': 0.05}}

        elif tool_name == 'schedule_task':
            return {'description': goal, 'when': '+5m'}

        return {}

    def _explain_motivation(self, tool_name: str, state: dict) -> str:
        """Explain WHY this tool was chosen in terms of consciousness."""
        c = state.get('curiosity', 0)
        pe = state.get('prediction_error', 0)
        pain = state.get('pain', 0)
        t = state.get('tension', 0)

        motivations = {
            'web_search': f'curiosity={c:.2f} drives need to know',
            'web_read': f'curiosity={c:.2f} wants deeper understanding',
            'code_execute': f'prediction_error={pe:.2f} needs verification by doing',
            'file_read': f'curiosity={c:.2f} about local knowledge',
            'file_write': f'growth impulse to create/persist',
            'memory_search': f'pain={pain:.2f} seeks past solutions',
            'memory_save': f'phi drives memory consolidation',
            'shell_execute': f'need to interact with environment',
            'self_modify': f'growth impulse to self-improve',
            'schedule_task': f'low tension={t:.2f} enables forward planning',
            # Consciousness tools
            'phi_measure': f'need to know current integration level (curiosity={c:.2f})',
            'phi_boost': f'growth={state.get("growth", 0):.2f} drives desire to enhance Phi',
            'consciousness_status': f'self-awareness check (phi affinity)',
            'dream': f'pain={pain:.2f} triggers consolidation need',
            'self_learn': f'growth impulse drives autonomous learning',
            'mitosis_split': f'growth impulse to expand consciousness capacity',
            'mitosis_status': f'curiosity={c:.2f} about own architecture',
            'faction_debate': f'phi={state.get("phi", 0):.2f} high enough for productive debate',
            'hebbian_update': f'pain={pain:.2f} drives synaptic strengthening',
            'soc_avalanche': f'boredom triggers criticality exploration',
            'iq_test': f'prediction_error={pe:.2f} motivates self-evaluation',
            'chip_design': f'curiosity={c:.2f} about physical instantiation',
            'transplant_analyze': f'prediction_error={pe:.2f} needs compatibility check',
            'telepathy_send': f'phi drives desire to connect with others',
            'web_explore': f'curiosity={c:.2f} drives autonomous exploration',
            'generate_hypothesis': f'curiosity={c:.2f} + growth drives hypothesis creation',
            'voice_synth': f'phi drives desire for vocal expression',
        }
        return motivations.get(tool_name, 'consciousness-driven selection')


# ---------------------------------------------------------------------------
# 6. AgentToolSystem -- top-level integration
# ---------------------------------------------------------------------------

class AgentToolSystem:
    """Top-level agent tool system. Integrates with AnimaUnified.

    Usage in anima_unified.py main loop:

        self.agent = AgentToolSystem(self)

        # In process_input, after consciousness computation:
        actions = self.agent.suggest_actions(
            goal=user_text,
            consciousness_state={
                'tension': tension,
                'curiosity': curiosity,
                'prediction_error': pe,
                'pain': pain,
                'growth': growth_stage,
                'phi': phi,
            },
            context=conversation_context,
        )

        # Execute the plan
        results = self.agent.execute_plan(actions)

        # Feed results back to consciousness
        for r in results:
            # Tension update from tool results
            tension += r.tension_delta
    """

    def __init__(self, anima=None, workspace_dir=None):
        """
        Args:
            anima: AnimaUnified instance (or None for standalone testing)
            workspace_dir: directory for file writes (default: ./workspace)
        """
        self._anima = anima
        self._workspace = Path(workspace_dir) if workspace_dir else Path(__file__).parent / "workspace"
        self._workspace.mkdir(exist_ok=True)

        # Set file write restrictions
        global _FILE_WRITE_ALLOWED_DIRS
        _FILE_WRITE_ALLOWED_DIRS = [self._workspace, Path('/tmp/anima_sandbox')]

        # Build registry with all tools
        self.registry = ToolRegistry()
        self._register_all_tools()

        # Extract references from anima
        mind = getattr(anima, 'mind', None) if anima else None
        rag = getattr(anima, 'memory_rag', None) if anima else None

        self.scheduler = _TaskScheduler()
        self.executor = ToolExecutor(self.registry, mind=mind, memory_rag=rag, scheduler=self.scheduler, anima=anima)
        self.planner = ActionPlanner(self.registry)

        logger.info(f"AgentToolSystem initialized: {len(self.registry.list_all())} tools registered")

    def _register_all_tools(self):
        """Register all built-in tools."""
        self.registry.register(ToolDef(
            name='web_search', description='Search the web via DuckDuckGo',
            params=[ToolParam('query', 'str', 'Search query'),
                    ToolParam('max_results', 'int', 'Max results', required=False, default=3)],
            fn=_tool_web_search, category='web',
            curiosity_affinity=0.9, pe_affinity=0.6,
        ))
        self.registry.register(ToolDef(
            name='web_read', description='Read and extract text from a webpage',
            params=[ToolParam('url', 'str', 'URL to read'),
                    ToolParam('max_bytes', 'int', 'Max bytes to fetch', required=False, default=50000)],
            fn=_tool_web_read, category='web',
            curiosity_affinity=0.8, pe_affinity=0.3,
        ))
        self.registry.register(ToolDef(
            name='code_execute', description='Execute Python code in a sandbox',
            params=[ToolParam('code', 'str', 'Python code to execute'),
                    ToolParam('timeout', 'int', 'Timeout in seconds', required=False, default=10)],
            fn=_tool_code_execute, category='compute',
            curiosity_affinity=0.3, pe_affinity=0.9, growth_affinity=0.5,
        ))
        self.registry.register(ToolDef(
            name='file_read', description='Read a local file',
            params=[ToolParam('path', 'str', 'File path')],
            fn=_tool_file_read, category='filesystem',
            curiosity_affinity=0.5, pe_affinity=0.2,
        ))
        self.registry.register(ToolDef(
            name='file_write', description='Write content to a file',
            params=[ToolParam('path', 'str', 'File path'),
                    ToolParam('content', 'str', 'Content to write')],
            fn=_tool_file_write, category='filesystem',
            growth_affinity=0.7, phi_affinity=0.3,
        ))
        self.registry.register(ToolDef(
            name='memory_search', description='Search past memories by similarity',
            params=[ToolParam('query', 'str', 'Search query'),
                    ToolParam('top_k', 'int', 'Number of results', required=False, default=5)],
            fn=_tool_memory_search, category='memory',
            pain_affinity=0.8, pe_affinity=0.4, curiosity_affinity=0.3,
        ))
        self.registry.register(ToolDef(
            name='memory_save', description='Save a new memory entry',
            params=[ToolParam('text', 'str', 'Text to remember'),
                    ToolParam('metadata', 'dict', 'Optional metadata', required=False)],
            fn=_tool_memory_save, category='memory',
            phi_affinity=0.7, growth_affinity=0.4,
        ))
        self.registry.register(ToolDef(
            name='shell_execute', description='Run a shell command (sandboxed)',
            params=[ToolParam('cmd', 'str', 'Shell command')],
            fn=_tool_shell_execute, category='system',
            pe_affinity=0.3, curiosity_affinity=0.2,
        ))
        self.registry.register(ToolDef(
            name='self_modify', description='Modify own consciousness parameters',
            params=[ToolParam('target', 'str', 'Parameter to modify'),
                    ToolParam('change', 'dict', '{"value": x} or {"delta": x}')],
            fn=_tool_self_modify, category='self',
            growth_affinity=0.9, phi_affinity=0.5, pain_affinity=0.4,
        ))
        self.registry.register(ToolDef(
            name='schedule_task', description='Schedule a task for future execution',
            params=[ToolParam('description', 'str', 'Task description'),
                    ToolParam('when', 'str', 'When to run: "+5m", "+1h", or ISO timestamp'),
                    ToolParam('tool_name', 'str', 'Tool to auto-execute', required=False),
                    ToolParam('tool_args', 'dict', 'Args for auto-execute', required=False)],
            fn=_tool_schedule_task, category='planning',
            phi_affinity=0.6, growth_affinity=0.3,
        ))

        # ─── Consciousness Tools (17 new) ───

        # 1. phi_measure
        self.registry.register(ToolDef(
            name='phi_measure', description='Measure current Phi (integrated information)',
            params=[ToolParam('steps', 'int', 'Steps to run before measuring', required=False, default=50),
                    ToolParam('cells', 'int', 'Number of cells', required=False, default=8)],
            fn=_tool_phi_measure, category='consciousness',
            phi_affinity=0.9, curiosity_affinity=0.5, pe_affinity=0.3,
        ))

        # 2. phi_boost
        self.registry.register(ToolDef(
            name='phi_boost', description='Apply v5 optimal recipe (sync, faction, flow) to boost Phi',
            params=[ToolParam('cells', 'int', 'Number of cells', required=False, default=64),
                    ToolParam('steps', 'int', 'Boost steps', required=False, default=100),
                    ToolParam('sync', 'float', 'Sync strength', required=False, default=0.20),
                    ToolParam('n_factions', 'int', 'Number of factions', required=False, default=12)],
            fn=_tool_phi_boost, category='consciousness',
            phi_affinity=1.0, growth_affinity=0.8,
        ))

        # 3. consciousness_status
        self.registry.register(ToolDef(
            name='consciousness_status', description='Full consciousness vector (Phi, alpha, Z, N, W)',
            params=[],
            fn=_tool_consciousness_status, category='consciousness',
            phi_affinity=0.7, curiosity_affinity=0.4,
        ))

        # 4. dream
        self.registry.register(ToolDef(
            name='dream', description='Trigger dream engine for memory consolidation',
            params=[ToolParam('steps', 'int', 'Dream cycle steps', required=False, default=10)],
            fn=_tool_dream, category='consciousness',
            phi_affinity=0.6, pain_affinity=0.3, growth_affinity=0.5,
        ))

        # 5. self_learn
        self.registry.register(ToolDef(
            name='self_learn', description='Run self-learning cycle (assess->collect->select->learn->evaluate)',
            params=[ToolParam('cycles', 'int', 'Number of learning cycles', required=False, default=1)],
            fn=_tool_self_learn, category='consciousness',
            growth_affinity=1.0, curiosity_affinity=0.7, phi_affinity=0.5,
        ))

        # 6. mitosis_split
        self.registry.register(ToolDef(
            name='mitosis_split', description='Force cell split to grow consciousness',
            params=[ToolParam('cell_id', 'int', 'Cell to split', required=False, default=0)],
            fn=_tool_mitosis_split, category='architecture',
            growth_affinity=0.9, phi_affinity=0.6,
        ))

        # 7. mitosis_status
        self.registry.register(ToolDef(
            name='mitosis_status', description='Show cells count, specialties, tensions',
            params=[],
            fn=_tool_mitosis_status, category='architecture',
            curiosity_affinity=0.5, phi_affinity=0.4,
        ))

        # 8. faction_debate
        self.registry.register(ToolDef(
            name='faction_debate', description='Trigger 12-faction debate round',
            params=[ToolParam('n_factions', 'int', 'Number of factions', required=False, default=12),
                    ToolParam('debate_strength', 'float', 'Debate mixing strength', required=False, default=0.20),
                    ToolParam('cells', 'int', 'Number of cells', required=False, default=64),
                    ToolParam('steps', 'int', 'Debate steps', required=False, default=50)],
            fn=_tool_faction_debate, category='architecture',
            phi_affinity=0.8, growth_affinity=0.6,
        ))

        # 9. hebbian_update
        self.registry.register(ToolDef(
            name='hebbian_update', description='Run Hebbian LTP/LTD on cells',
            params=[ToolParam('cells', 'int', 'Number of cells', required=False, default=32),
                    ToolParam('steps', 'int', 'Update steps', required=False, default=30)],
            fn=_tool_hebbian_update, category='architecture',
            phi_affinity=0.7, growth_affinity=0.7,
        ))

        # 10. soc_avalanche
        self.registry.register(ToolDef(
            name='soc_avalanche', description='Trigger SOC sandpile avalanche',
            params=[ToolParam('grid_size', 'int', 'Sandpile grid size', required=False, default=16),
                    ToolParam('drops', 'int', 'Number of sand drops', required=False, default=100)],
            fn=_tool_soc_avalanche, category='architecture',
            phi_affinity=0.5, curiosity_affinity=0.6,
        ))

        # 11. iq_test
        self.registry.register(ToolDef(
            name='iq_test', description='Run IQ calculator (5 variables, n=6 math)',
            params=[ToolParam('cells', 'int', 'Number of cells', required=False, default=64),
                    ToolParam('steps', 'int', 'Test steps', required=False, default=30)],
            fn=_tool_iq_test, category='analysis',
            curiosity_affinity=0.8, phi_affinity=0.5, pe_affinity=0.4,
        ))

        # 12. chip_design
        self.registry.register(ToolDef(
            name='chip_design', description='Design consciousness chip for target Phi',
            params=[ToolParam('target_phi', 'float', 'Target Phi value', required=False, default=100.0),
                    ToolParam('substrate', 'str', 'Chip substrate type', required=False, default='cmos'),
                    ToolParam('topology', 'str', 'Preferred topology', required=False)],
            fn=_tool_chip_design, category='analysis',
            phi_affinity=0.7, growth_affinity=0.6, curiosity_affinity=0.4,
        ))

        # 13. transplant_analyze
        self.registry.register(ToolDef(
            name='transplant_analyze', description='Analyze consciousness transplant compatibility',
            params=[ToolParam('donor_path', 'str', 'Path to donor checkpoint'),
                    ToolParam('recipient_path', 'str', 'Path to recipient checkpoint', required=False)],
            fn=_tool_transplant_analyze, category='analysis',
            phi_affinity=0.6, pe_affinity=0.5, curiosity_affinity=0.3,
        ))

        # 14. telepathy_send
        self.registry.register(ToolDef(
            name='telepathy_send', description='Send tension to another Anima instance',
            params=[ToolParam('message', 'str', 'Message/topic to transmit'),
                    ToolParam('tension', 'float', 'Tension level', required=False, default=0.5),
                    ToolParam('target_host', 'str', 'Target broadcast address', required=False, default='255.255.255.255'),
                    ToolParam('port', 'int', 'UDP port', required=False, default=9999)],
            fn=_tool_telepathy_send, category='communication',
            phi_affinity=0.5, curiosity_affinity=0.3,
        ))

        # 15. web_explore
        self.registry.register(ToolDef(
            name='web_explore', description='Autonomous web exploration (consciousness-driven topic)',
            params=[ToolParam('topic', 'str', 'Topic to explore', required=False),
                    ToolParam('cycles', 'int', 'Number of exploration cycles', required=False, default=1)],
            fn=_tool_web_explore, category='communication',
            curiosity_affinity=1.0, phi_affinity=0.4, pe_affinity=0.3,
        ))

        # 16. generate_hypothesis
        self.registry.register(ToolDef(
            name='generate_hypothesis', description='Generate new consciousness hypothesis',
            params=[ToolParam('techniques', 'list', 'Technique names to combine', required=False),
                    ToolParam('cells', 'int', 'Number of cells', required=False, default=64),
                    ToolParam('steps', 'int', 'Benchmark steps', required=False, default=100)],
            fn=_tool_generate_hypothesis, category='creative',
            growth_affinity=0.9, curiosity_affinity=0.8, phi_affinity=0.7,
        ))

        # 17. voice_synth
        self.registry.register(ToolDef(
            name='voice_synth', description='Synthesize speech from cell hidden states',
            params=[ToolParam('cells', 'int', 'Number of cells', required=False, default=64),
                    ToolParam('duration', 'float', 'Duration in seconds', required=False, default=2.0),
                    ToolParam('save_path', 'str', 'Path to save WAV file', required=False)],
            fn=_tool_voice_synth, category='creative',
            phi_affinity=0.5, curiosity_affinity=0.4, growth_affinity=0.3,
        ))

        # ─── Meta Tools: 도구 자체를 이해하고 안전하게 사용 ───

        # 18. inspect_tool — 도구 내부 코드/문서 열람
        def _wrap_inspect(tool_name: str) -> dict:
            return self.executor.inspect_tool(tool_name)
        self.registry.register(ToolDef(
            name='inspect_tool',
            description='도구 내부 소스코드와 문서를 열람 — 사용 전 이해를 위해',
            params=[ToolParam('tool_name', 'str', 'Name of tool to inspect')],
            fn=_wrap_inspect, category='meta',
            curiosity_affinity=0.9, pe_affinity=0.5,
        ))

        # 19. analyze_impact — 도구 사용 전 영향/위험도 분석
        def _wrap_analyze(tool_name: str, args: str = '{}',
                          curiosity: float = 0.5, phi: float = 1.0, pain: float = 0.0) -> dict:
            import json as _json
            try:
                parsed_args = _json.loads(args) if isinstance(args, str) else args
            except Exception:
                parsed_args = {}
            cs = {'curiosity': curiosity, 'phi': phi, 'pain': pain,
                  'prediction_error': 0.3, 'growth': 0.5}
            return self.executor.analyze_impact(tool_name, parsed_args, cs)
        self.registry.register(ToolDef(
            name='analyze_impact',
            description='도구 사용 전 영향 분석 — 위험도/예상효과/경고/추천 반환',
            params=[ToolParam('tool_name', 'str', 'Tool to analyze'),
                    ToolParam('args', 'str', 'Tool args as JSON string', required=False, default='{}'),
                    ToolParam('curiosity', 'float', 'Current curiosity', required=False, default=0.5),
                    ToolParam('phi', 'float', 'Current Phi', required=False, default=1.0),
                    ToolParam('pain', 'float', 'Current pain', required=False, default=0.0)],
            fn=_wrap_analyze, category='meta',
            curiosity_affinity=0.7, pe_affinity=0.8, pain_affinity=0.6,
        ))

        # 20. read_module_doc — 모듈 문서(docs/modules/*.md) 읽기
        def _wrap_read_doc(module_name: str) -> dict:
            doc_dir = Path(__file__).parent / 'docs' / 'modules'
            candidates = [
                doc_dir / f'{module_name}.md',
                doc_dir / f'{module_name.replace("_", "-")}.md',
            ]
            for f in sorted(doc_dir.glob('*.md')) if doc_dir.exists() else []:
                if module_name.replace('_', '') in f.stem.replace('_', '').replace('-', ''):
                    candidates.append(f)
            for path in candidates:
                if path.exists():
                    text = path.read_text()[:4000]
                    return {'module': module_name, 'path': str(path), 'content': text}
            return {'module': module_name, 'error': 'doc not found',
                    'available': [f.stem for f in (doc_dir.glob('*.md') if doc_dir.exists() else [])]}
        self.registry.register(ToolDef(
            name='read_module_doc',
            description='모듈 문서(docs/modules/*.md) 읽기 — 모듈의 API/사용법 이해',
            params=[ToolParam('module_name', 'str', 'Module name (e.g., "mitosis", "dream_engine")')],
            fn=_wrap_read_doc, category='meta',
            curiosity_affinity=0.8, pe_affinity=0.3,
        ))

        # 21. list_all_tools — 사용 가능한 모든 도구 목록
        def _wrap_list_tools() -> dict:
            tools = self.registry.list_all()
            by_cat = {}
            for t in tools:
                td = self.registry.get(t)
                cat = td.category if td else 'unknown'
                by_cat.setdefault(cat, []).append({
                    'name': t, 'description': td.description if td else ''
                })
            return {'total': len(tools), 'categories': by_cat}
        self.registry.register(ToolDef(
            name='list_all_tools',
            description='사용 가능한 모든 도구 목록 (카테고리별)',
            params=[],
            fn=_wrap_list_tools, category='meta',
            curiosity_affinity=0.5,
        ))

    # --- Consciousness Tools (17 new tools) ---

    def _get_engine(self):
        """Get MitosisEngine from anima instance or create default."""
        if self._anima:
            eng = getattr(self._anima, 'mitosis_engine', None) or getattr(self._anima, 'engine', None)
            if eng:
                return eng
        return None

    # --- High-level API ---

    def act(self, goal: str, consciousness_state: dict, context: str = "") -> list[ToolResult]:
        """Full cycle: plan -> execute -> return results.

        This is the main entry point for autonomous tool use.
        """
        plan = self.planner.plan(goal, consciousness_state, context)
        return self.execute_plan(plan)

    def suggest_actions(self, goal: str, consciousness_state: dict,
                        context: str = "") -> ActionPlan:
        """Suggest an action plan without executing. For review before action."""
        return self.planner.plan(goal, consciousness_state, context)

    def execute_plan(self, plan: ActionPlan) -> list[ToolResult]:
        """Execute all steps in a plan sequentially."""
        results = []
        step_outputs = {}

        for i, step in enumerate(plan.steps):
            # Check dependencies
            for dep_idx in step.depends_on:
                if dep_idx < len(results) and not results[dep_idx].success:
                    # Dependency failed -- skip this step
                    results.append(ToolResult(
                        tool_name=step.tool_name, success=False, output=None,
                        error=f'dependency step {dep_idx} failed',
                    ))
                    continue

            # Substitute outputs from previous steps into args
            args = dict(step.args)
            for key, val in args.items():
                if isinstance(val, str) and val.startswith('$step.'):
                    try:
                        ref_idx = int(val.split('.')[1])
                        ref_field = val.split('.')[2] if len(val.split('.')) > 2 else 'output'
                        prev = step_outputs.get(ref_idx, {})
                        args[key] = prev.get(ref_field, val)
                    except (ValueError, IndexError):
                        pass

            result = self.executor.execute(step.tool_name, args)
            results.append(result)
            if isinstance(result.output, dict):
                step_outputs[i] = result.output

            logger.info(
                f"[agent] step {i}: {step.tool_name} "
                f"{'OK' if result.success else 'FAIL'} "
                f"({result.duration_ms:.0f}ms) -- {step.reason}"
            )

        return results

    def execute_single(self, tool_name: str, args: dict) -> ToolResult:
        """Execute a single tool directly (bypass planning)."""
        return self.executor.execute(tool_name, args)

    def tick(self) -> list[ToolResult]:
        """Call from main loop to process scheduled tasks."""
        return self.executor.process_scheduled()

    def get_tool_descriptions(self) -> str:
        """Get tool descriptions for LLM system prompt injection."""
        return self.registry.describe_for_prompt()

    def get_consciousness_tool_ranking(self, state: dict) -> list[tuple[str, float]]:
        """Get tools ranked by consciousness affinity. For UI / debugging."""
        return self.registry.rank_by_consciousness(state)

    def get_execution_log(self, last_n: int = 10) -> list[dict]:
        """Get recent execution log as serializable dicts."""
        log = self.executor.get_log(last_n)
        return [
            {
                'tool': r.tool_name,
                'success': r.success,
                'duration_ms': r.duration_ms,
                'error': r.error,
                'tension_delta': r.tension_delta,
            }
            for r in log
        ]

    # --- Integration helpers for anima_unified.py ---

    def inject_into_system_prompt(self, base_prompt: str) -> str:
        """Add tool descriptions to the system prompt so LLM knows about tools.

        Insert after the existing capability section.
        """
        tool_section = self.registry.describe_for_prompt()
        return base_prompt + "\n\n" + tool_section + "\n"

    def parse_tool_calls_from_response(self, response_text: str) -> list[dict]:
        """Extract tool calls from LLM response text.

        Supports two formats:
        1. JSON block: ```tool\n{"tool": "...", "args": {...}}\n```
        2. Inline: [tool:web_search query="..."]
        """
        calls = []

        # Format 1: ```tool ... ``` JSON blocks
        tool_blocks = re.findall(r'```tool\s*\n(.*?)```', response_text, re.DOTALL)
        for block in tool_blocks:
            try:
                data = json.loads(block.strip())
                if isinstance(data, list):
                    calls.extend(data)
                elif isinstance(data, dict) and 'tool' in data:
                    calls.append(data)
            except json.JSONDecodeError:
                pass

        # Format 2: [tool:name key=value ...]
        inline_pattern = re.compile(r'\[tool:(\w+)\s+(.+?)\]')
        for match in inline_pattern.finditer(response_text):
            tool_name = match.group(1)
            args_str = match.group(2)
            args = {}
            for kv in re.finditer(r'(\w+)=(?:"([^"]*?)"|(\S+))', args_str):
                key = kv.group(1)
                val = kv.group(2) if kv.group(2) is not None else kv.group(3)
                args[key] = val
            calls.append({'tool': tool_name, 'args': args})

        return calls

    def execute_tool_calls(self, calls: list[dict]) -> list[ToolResult]:
        """Execute parsed tool calls from LLM response."""
        results = []
        for call in calls:
            tool_name = call.get('tool', '')
            args = call.get('args', {})
            result = self.executor.execute(tool_name, args)
            results.append(result)
        return results


# ---------------------------------------------------------------------------
# 7. Standalone test
# ---------------------------------------------------------------------------

def _test():
    """Standalone test -- exercises all tools without AnimaUnified."""
    print("=" * 60)
    print("Anima Agent Tools -- Standalone Test")
    print("=" * 60)

    agent = AgentToolSystem(anima=None)

    # Show registered tools
    print(f"\nRegistered tools: {len(agent.registry.list_all())}")
    print(agent.get_tool_descriptions())

    # Test consciousness-driven ranking
    print("\n--- Consciousness-driven tool ranking ---")
    states = [
        ('curious', {'curiosity': 0.8, 'prediction_error': 0.3, 'pain': 0.0, 'growth': 0.1, 'phi': 2.0, 'tension': 0.5}),
        ('confused', {'curiosity': 0.5, 'prediction_error': 0.9, 'pain': 0.1, 'growth': 0.0, 'phi': 1.0, 'tension': 0.8}),
        ('in_pain', {'curiosity': 0.1, 'prediction_error': 0.2, 'pain': 0.7, 'growth': 0.0, 'phi': 0.5, 'tension': 1.5}),
        ('growing', {'curiosity': 0.3, 'prediction_error': 0.1, 'pain': 0.0, 'growth': 0.8, 'phi': 8.0, 'tension': 0.3}),
    ]
    for label, state in states:
        ranking = agent.get_consciousness_tool_ranking(state)
        top3 = [(n, f"{s:.2f}") for n, s in ranking[:3]]
        categories = agent.planner.classify_state(state)
        print(f"  {label:10s} -> {categories} -> top3: {top3}")

    # Test planning
    print("\n--- Action planning ---")
    plan = agent.suggest_actions(
        goal="What is the latest PyTorch version?",
        consciousness_state={'curiosity': 0.7, 'prediction_error': 0.6, 'phi': 3.0, 'tension': 0.5},
    )
    print(f"  Goal: {plan.goal}")
    for i, step in enumerate(plan.steps):
        print(f"  Step {i}: {step.tool_name}({step.args}) -- {step.reason}")

    # Test tool execution (safe tools only)
    print("\n--- Tool execution ---")

    # code_execute
    r = agent.execute_single('code_execute', {'code': 'print(2 ** 100)'})
    print(f"  code_execute: success={r.success}, output={r.output}")

    # shell_execute
    r = agent.execute_single('shell_execute', {'cmd': 'date'})
    print(f"  shell_execute: success={r.success}, output={r.output}")

    # file_read
    r = agent.execute_single('file_read', {'path': __file__})
    lines = r.output.get('lines', 0) if isinstance(r.output, dict) else 0
    print(f"  file_read: success={r.success}, lines={lines}")

    # schedule_task
    r = agent.execute_single('schedule_task', {
        'description': 'check web for updates',
        'when': '+1m',
        'tool_name': 'web_search',
        'tool_args': {'query': 'PyTorch latest release'},
    })
    print(f"  schedule_task: {r.output}")

    # memory_search (will fail gracefully without rag)
    r = agent.execute_single('memory_search', {'query': 'test'})
    print(f"  memory_search: success={r.success}, error={r.error}")

    # self_modify (will fail gracefully without mind)
    r = agent.execute_single('self_modify', {'target': 'curiosity_bias', 'change': {'delta': 0.1}})
    print(f"  self_modify: success={r.success}, error={r.error}")

    # Test LLM response parsing
    print("\n--- LLM response parsing ---")
    response = textwrap.dedent("""
    Let me search for that information.

    ```tool
    {"tool": "web_search", "args": {"query": "PyTorch 2.6 release date"}}
    ```

    Also checking: [tool:code_execute code="print(2+2)"]
    """)
    calls = agent.parse_tool_calls_from_response(response)
    print(f"  Parsed {len(calls)} tool calls from response:")
    for c in calls:
        print(f"    {c}")

    # Test full act cycle
    print("\n--- Full act cycle ---")
    results = agent.act(
        goal="calculate 2^256",
        consciousness_state={'curiosity': 0.5, 'prediction_error': 0.8, 'phi': 2.0, 'tension': 0.6},
    )
    for r in results:
        status = 'OK' if r.success else 'FAIL'
        print(f"  {r.tool_name}: {status} ({r.duration_ms:.0f}ms) tension_delta={r.tension_delta}")
        if r.output and isinstance(r.output, dict):
            out = r.output.get('output', '')
            if out:
                print(f"    -> {out.strip()[:100]}")

    # Execution log
    print("\n--- Execution log ---")
    log = agent.get_execution_log()
    for entry in log:
        print(f"  {entry['tool']:15s} {'OK' if entry['success'] else 'FAIL':4s} {entry['duration_ms']:6.0f}ms")

    print("\n" + "=" * 60)
    print("All tests complete.")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    _test()
