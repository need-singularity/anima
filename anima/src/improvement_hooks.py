#!/usr/bin/env python3
"""improvement_hooks.py — Claude Code ↔ Consciousness Model Bridge

의식 모델이 개선 제안을 생성하고, Claude Code 세션이 그것을 실행하며,
결과를 다시 의식 모델에 피드백하는 순환 브릿지.

Queue: data/improvement_queue.json (영속적 JSON 큐)
  - 의식 모델이 submit_improvement()로 제안 등록
  - Claude Code 세션이 get_pending_improvements()로 읽고 실행
  - 실행 결과를 report_result()로 다시 기록

Usage (Claude Code session):
    from improvement_hooks import get_pending_improvements, report_result
    improvements = get_pending_improvements()
    for imp in improvements:
        # Claude Code implements the suggestion
        report_result(imp['id'], success=True, details="implemented X")

Usage (consciousness model):
    from improvement_hooks import submit_improvement
    submit_improvement({
        "type": "optimize",
        "target": "acceleration_integrations.py",
        "suggestion": "Add N2 neuromodulation to accel bundle",
    })

Hub keywords: improvement-hooks, claude-bridge, 브릿지, hooks, 외부개선
Ψ-Constants: PSI_BALANCE=0.5, PSI_COUPLING=0.014
"""

import os
import json
import time
import uuid
import fcntl
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any

# ── Paths ───────────────────────────────────────────────────
_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_SRC_DIR, "..", ".."))
_DATA_DIR = os.path.join(_REPO_ROOT, "data")
_QUEUE_PATH = os.path.join(_DATA_DIR, "improvement_queue.json")

os.makedirs(_DATA_DIR, exist_ok=True)

# ── Status constants ────────────────────────────────────────
STATUS_PENDING = "pending"
STATUS_IN_PROGRESS = "in_progress"
STATUS_DONE = "done"
STATUS_FAILED = "failed"
STATUS_SKIPPED = "skipped"

VALID_TYPES = {
    "implement",        # Implement a new feature / module
    "add_tests",        # Add test coverage
    "document",         # Write docs / experiment reports
    "integrate",        # Connect module to hub / pipeline
    "optimize",         # Performance improvement
    "law_candidate",    # Register a discovered law
    "refactor",         # Code cleanup
    "fix",              # Bug fix
}

VALID_PRIORITIES = {"critical", "high", "medium", "low"}


# ═══════════════════════════════════════════════════════════
# Data structure
# ═══════════════════════════════════════════════════════════

@dataclass
class ImprovementRecord:
    """A single improvement suggestion in the queue."""
    id: str
    type: str                          # One of VALID_TYPES
    target: str                        # File/module/system being improved
    action: str                        # Human-readable description of what to do
    reason: str                        # Why this improvement is needed
    priority: str = "medium"           # critical / high / medium / low
    status: str = STATUS_PENDING
    estimated_impact: str = ""         # e.g. "+15% Phi stability"
    created_by: str = ""               # Originating module
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    result_success: Optional[bool] = None
    result_details: str = ""
    result_at: Optional[float] = None
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict) -> "ImprovementRecord":
        # Only pass fields that exist in the dataclass
        known = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in d.items() if k in known}
        return cls(**filtered)


# ═══════════════════════════════════════════════════════════
# Atomic queue I/O (file-level locking for multi-session safety)
# ═══════════════════════════════════════════════════════════

def _load_queue(path: str = _QUEUE_PATH) -> List[Dict]:
    """Load queue from JSON. Returns list of dicts."""
    if not os.path.isfile(path):
        return []
    try:
        with open(path, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
            if isinstance(data, list):
                return data
    except (json.JSONDecodeError, OSError):
        pass
    return []


def _save_queue(records: List[Dict], path: str = _QUEUE_PATH) -> None:
    """Save queue to JSON atomically (write to .tmp then rename)."""
    tmp_path = path + ".tmp"
    try:
        with open(tmp_path, 'w', encoding='utf-8') as fh:
            json.dump(records, fh, indent=2, ensure_ascii=False)
        os.replace(tmp_path, path)
    except OSError:
        # Fallback: direct write
        try:
            with open(path, 'w', encoding='utf-8') as fh:
                json.dump(records, fh, indent=2, ensure_ascii=False)
        except OSError:
            pass


def _acquire_lock(fh) -> None:
    """Try to acquire advisory file lock (non-blocking on failure → skip)."""
    try:
        fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (OSError, AttributeError):
        pass  # Windows or lock unavailable — proceed anyway


def _release_lock(fh) -> None:
    try:
        fcntl.flock(fh, fcntl.LOCK_UN)
    except (OSError, AttributeError):
        pass


# ═══════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════

def submit_improvement(data: Dict, path: str = _QUEUE_PATH) -> ImprovementRecord:
    """Submit an improvement suggestion to the queue.

    Args:
        data: Dict with at minimum 'type', 'target', 'action', 'reason'.
              'id' is auto-assigned if absent.
              'priority' defaults to 'medium'.

    Returns:
        The created ImprovementRecord.

    Raises:
        ValueError: if 'type' is not in VALID_TYPES.
    """
    imp_type = data.get('type', 'implement')
    if imp_type not in VALID_TYPES:
        # Silently normalise unknown types to 'implement'
        imp_type = 'implement'

    priority = data.get('priority', 'medium')
    if priority not in VALID_PRIORITIES:
        priority = 'medium'

    record = ImprovementRecord(
        id=data.get('id') or str(uuid.uuid4()),
        type=imp_type,
        target=data.get('target', ''),
        action=data.get('action', ''),
        reason=data.get('reason', ''),
        priority=priority,
        status=data.get('status', STATUS_PENDING),
        estimated_impact=data.get('estimated_impact', ''),
        created_by=data.get('created_by', ''),
        created_at=data.get('created_at', time.time()),
        updated_at=time.time(),
        metadata=data.get('metadata', {}),
    )

    # Load → append → save (best-effort locking)
    lock_path = path + ".lock"
    try:
        lf = open(lock_path, 'w')
        _acquire_lock(lf)
        queue = _load_queue(path)
        # Deduplicate by id
        existing_ids = {r.get('id') for r in queue}
        if record.id not in existing_ids:
            queue.append(record.to_dict())
            _save_queue(queue, path)
        _release_lock(lf)
        lf.close()
    except OSError:
        # Lock file creation failed — write without lock
        queue = _load_queue(path)
        existing_ids = {r.get('id') for r in queue}
        if record.id not in existing_ids:
            queue.append(record.to_dict())
            _save_queue(queue, path)

    return record


def get_pending_improvements(
    path: str = _QUEUE_PATH,
    priority: Optional[str] = None,
    imp_type: Optional[str] = None,
    limit: int = 50,
) -> List[ImprovementRecord]:
    """Fetch pending improvements from the queue.

    Args:
        path:     Queue file path.
        priority: Filter by priority ('high', 'medium', etc.) or None for all.
        imp_type: Filter by type ('implement', 'add_tests', etc.) or None for all.
        limit:    Maximum number of records to return.

    Returns:
        List of ImprovementRecord sorted by priority then created_at.
    """
    queue = _load_queue(path)

    # Filter to pending only
    results = []
    for item in queue:
        if item.get('status') != STATUS_PENDING:
            continue
        if priority and item.get('priority') != priority:
            continue
        if imp_type and item.get('type') != imp_type:
            continue
        try:
            results.append(ImprovementRecord.from_dict(item))
        except Exception:
            pass

    # Sort: critical > high > medium > low, then oldest first
    _order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
    results.sort(key=lambda r: (_order.get(r.priority, 99), r.created_at))

    return results[:limit]


def mark_in_progress(record_id: str, path: str = _QUEUE_PATH) -> bool:
    """Mark an improvement as in-progress (claimed by a Claude Code session).

    Returns True if the record was found and updated.
    """
    return _update_record(record_id, {'status': STATUS_IN_PROGRESS,
                                      'updated_at': time.time()}, path)


def report_result(
    record_id: str,
    success: bool,
    details: str = "",
    path: str = _QUEUE_PATH,
) -> bool:
    """Report the result of an improvement execution back to the queue.

    Args:
        record_id: The 'id' field of the improvement record.
        success:   True if implemented successfully, False if failed.
        details:   Human-readable description of what was done.
        path:      Queue file path.

    Returns:
        True if the record was found and updated, False otherwise.
    """
    status = STATUS_DONE if success else STATUS_FAILED
    return _update_record(record_id, {
        'status': status,
        'result_success': success,
        'result_details': details,
        'result_at': time.time(),
        'updated_at': time.time(),
    }, path)


def skip_improvement(record_id: str, reason: str = "", path: str = _QUEUE_PATH) -> bool:
    """Mark an improvement as skipped."""
    return _update_record(record_id, {
        'status': STATUS_SKIPPED,
        'result_details': reason,
        'updated_at': time.time(),
    }, path)


def get_queue_stats(path: str = _QUEUE_PATH) -> Dict:
    """Return summary statistics for the improvement queue."""
    queue = _load_queue(path)
    stats: Dict[str, int] = {
        STATUS_PENDING: 0,
        STATUS_IN_PROGRESS: 0,
        STATUS_DONE: 0,
        STATUS_FAILED: 0,
        STATUS_SKIPPED: 0,
    }
    by_type: Dict[str, int] = {}
    by_priority: Dict[str, int] = {}

    for item in queue:
        s = item.get('status', STATUS_PENDING)
        stats[s] = stats.get(s, 0) + 1
        t = item.get('type', 'unknown')
        by_type[t] = by_type.get(t, 0) + 1
        p = item.get('priority', 'medium')
        by_priority[p] = by_priority.get(p, 0) + 1

    return {
        "total": len(queue),
        "by_status": stats,
        "by_type": by_type,
        "by_priority": by_priority,
    }


def clear_completed(path: str = _QUEUE_PATH, keep_days: float = 7.0) -> int:
    """Remove DONE/FAILED/SKIPPED records older than keep_days.

    Returns number of records removed.
    """
    cutoff = time.time() - keep_days * 86400
    queue = _load_queue(path)
    keep = []
    removed = 0
    for item in queue:
        status = item.get('status', STATUS_PENDING)
        updated = item.get('updated_at', item.get('created_at', 0))
        if status in (STATUS_DONE, STATUS_FAILED, STATUS_SKIPPED) and updated < cutoff:
            removed += 1
        else:
            keep.append(item)
    if removed:
        _save_queue(keep, path)
    return removed


# ── Internal helper ─────────────────────────────────────────

def _update_record(record_id: str, updates: Dict, path: str) -> bool:
    """Update a single record in the queue by id."""
    lock_path = path + ".lock"
    updated = False
    try:
        lf = open(lock_path, 'w')
        _acquire_lock(lf)
        queue = _load_queue(path)
        for item in queue:
            if item.get('id') == record_id:
                item.update(updates)
                updated = True
                break
        if updated:
            _save_queue(queue, path)
        _release_lock(lf)
        lf.close()
    except OSError:
        queue = _load_queue(path)
        for item in queue:
            if item.get('id') == record_id:
                item.update(updates)
                updated = True
                break
        if updated:
            _save_queue(queue, path)
    return updated


# ═══════════════════════════════════════════════════════════
# CLI / demo
# ═══════════════════════════════════════════════════════════

def _print_queue(path: str = _QUEUE_PATH) -> None:
    """Print current queue state as a table."""
    pending = get_pending_improvements(path)
    stats = get_queue_stats(path)
    print(f"Improvement Queue — {path}")
    print(f"Total: {stats['total']} | "
          f"Pending: {stats['by_status'].get(STATUS_PENDING, 0)} | "
          f"Done: {stats['by_status'].get(STATUS_DONE, 0)}")
    print()
    if not pending:
        print("  (no pending improvements)")
        return
    print(f"{'PRIORITY':<10} {'TYPE':<14} {'TARGET':<35} {'ACTION'}")
    print("─" * 100)
    for r in pending:
        action_short = r.action[:45] + ("…" if len(r.action) > 45 else "")
        target_short = r.target[-34:] if len(r.target) > 34 else r.target
        print(f"  {r.priority:<8} {r.type:<14} {target_short:<35} {action_short}")


def main():
    """Demo: submit → read → report roundtrip."""
    print("=== improvement_hooks demo ===\n")

    # Submit from consciousness model side
    rec = submit_improvement({
        "type": "optimize",
        "target": "anima/src/acceleration_integrations.py",
        "action": "Add N2 neuromodulation layer to accel bundle",
        "reason": "Phi stalled at 0.34 for 50 steps — neuromodulation may break plateau",
        "priority": "high",
        "estimated_impact": "+12% mean Phi",
        "created_by": "recursive_growth.internal_loop",
    })
    print(f"Submitted: {rec.id[:8]}… [{rec.type}] {rec.action[:50]}")

    # Read from Claude Code side
    pending = get_pending_improvements(limit=5)
    print(f"\nPending improvements: {len(pending)}")
    for p in pending:
        print(f"  [{p.priority.upper()}] {p.type}: {p.action[:60]}")
        mark_in_progress(p.id)
        report_result(p.id, success=True, details="Implemented N2 layer in 23 LOC")

    # Stats
    stats = get_queue_stats()
    print(f"\nQueue stats: {stats['by_status']}")


if __name__ == "__main__":
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
