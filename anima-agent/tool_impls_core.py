"""Core tool implementations — web, code, file, memory, shell, schedule.

Extracted from agent_tools.py for P8 compliance (Division > Integration).
"""

__all__ = [
    "_tool_web_search", "_tool_web_read", "_tool_code_execute",
    "_tool_file_read", "_tool_file_write", "_tool_memory_search",
    "_tool_memory_save", "_tool_shell_execute", "_tool_self_modify",
    "_tool_schedule_task", "_TaskScheduler",
    "_SANDBOX_TIMEOUT", "_MAX_OUTPUT", "_MAX_FILE_READ",
    "_SHELL_ALLOWED_CMDS", "_FILE_WRITE_ALLOWED_DIRS",
]

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


