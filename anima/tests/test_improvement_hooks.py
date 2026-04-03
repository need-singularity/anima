#!/usr/bin/env python3
"""Tests for improvement_hooks.py — improvement queue CRUD operations."""

import os
import sys
import json
import time
import tempfile
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from improvement_hooks import (
    ImprovementRecord,
    submit_improvement,
    get_pending_improvements,
    mark_in_progress,
    report_result,
    skip_improvement,
    get_queue_stats,
    clear_completed,
    VALID_TYPES,
    VALID_PRIORITIES,
    STATUS_PENDING,
    STATUS_IN_PROGRESS,
    STATUS_DONE,
    STATUS_FAILED,
    STATUS_SKIPPED,
    _load_queue,
    _save_queue,
)


# ── Fixtures ──────────────────────────────────────────────────

@pytest.fixture
def tmp_queue(tmp_path):
    """Return path to a temporary queue JSON file."""
    return str(tmp_path / "test_queue.json")


@pytest.fixture
def sample_data():
    return {
        "type": "add_tests",
        "target": "anima/tests/test_foo.py",
        "action": "Add tests for foo.py",
        "reason": "No test coverage",
        "priority": "high",
    }


# ── ImprovementRecord tests ──────────────────────────────────

class TestImprovementRecord:

    def test_create_with_defaults(self):
        rec = ImprovementRecord(
            id="test-1",
            type="implement",
            target="foo.py",
            action="Do something",
            reason="Because",
        )
        assert rec.priority == "medium"
        assert rec.status == STATUS_PENDING
        assert rec.result_success is None
        assert isinstance(rec.created_at, float)

    def test_to_dict(self):
        rec = ImprovementRecord(
            id="test-2",
            type="add_tests",
            target="bar.py",
            action="Add tests",
            reason="Coverage",
        )
        d = rec.to_dict()
        assert d["id"] == "test-2"
        assert d["type"] == "add_tests"
        assert isinstance(d["metadata"], dict)

    def test_from_dict(self):
        d = {
            "id": "test-3",
            "type": "optimize",
            "target": "baz.py",
            "action": "Speed up",
            "reason": "Slow",
            "priority": "critical",
            "status": STATUS_DONE,
        }
        rec = ImprovementRecord.from_dict(d)
        assert rec.id == "test-3"
        assert rec.priority == "critical"
        assert rec.status == STATUS_DONE

    def test_from_dict_ignores_unknown_keys(self):
        d = {
            "id": "test-4",
            "type": "fix",
            "target": "x.py",
            "action": "Fix bug",
            "reason": "Broken",
            "unknown_field": "should be ignored",
        }
        rec = ImprovementRecord.from_dict(d)
        assert rec.id == "test-4"

    def test_roundtrip(self):
        rec = ImprovementRecord(
            id="rt-1",
            type="refactor",
            target="module.py",
            action="Refactor code",
            reason="Messy",
            priority="low",
            metadata={"key": "value"},
        )
        d = rec.to_dict()
        rec2 = ImprovementRecord.from_dict(d)
        assert rec.id == rec2.id
        assert rec.type == rec2.type
        assert rec.metadata == rec2.metadata


# ── Queue I/O tests ───────────────────────────────────────────

class TestQueueIO:

    def test_load_empty_file(self, tmp_queue):
        result = _load_queue(tmp_queue)
        assert result == []

    def test_save_and_load(self, tmp_queue):
        records = [{"id": "1", "type": "implement", "status": "pending"}]
        _save_queue(records, tmp_queue)
        loaded = _load_queue(tmp_queue)
        assert len(loaded) == 1
        assert loaded[0]["id"] == "1"

    def test_load_corrupt_json(self, tmp_queue):
        with open(tmp_queue, 'w') as f:
            f.write("{invalid json")
        result = _load_queue(tmp_queue)
        assert result == []


# ── submit_improvement tests ──────────────────────────────────

class TestSubmitImprovement:

    def test_submit_basic(self, tmp_queue, sample_data):
        rec = submit_improvement(sample_data, path=tmp_queue)
        assert rec.type == "add_tests"
        assert rec.priority == "high"
        assert rec.status == STATUS_PENDING
        assert len(rec.id) > 0

        # Verify persisted
        queue = _load_queue(tmp_queue)
        assert len(queue) == 1

    def test_submit_auto_id(self, tmp_queue, sample_data):
        rec = submit_improvement(sample_data, path=tmp_queue)
        assert len(rec.id) == 36  # UUID4 format

    def test_submit_explicit_id(self, tmp_queue, sample_data):
        sample_data["id"] = "my-custom-id"
        rec = submit_improvement(sample_data, path=tmp_queue)
        assert rec.id == "my-custom-id"

    def test_submit_deduplicates(self, tmp_queue, sample_data):
        sample_data["id"] = "dedup-test"
        submit_improvement(sample_data, path=tmp_queue)
        submit_improvement(sample_data, path=tmp_queue)
        queue = _load_queue(tmp_queue)
        assert len(queue) == 1

    def test_submit_unknown_type_normalized(self, tmp_queue):
        data = {
            "type": "nonexistent_type",
            "target": "x.py",
            "action": "Do something",
            "reason": "Unknown",
        }
        rec = submit_improvement(data, path=tmp_queue)
        assert rec.type == "implement"  # normalized

    def test_submit_invalid_priority_normalized(self, tmp_queue, sample_data):
        sample_data["priority"] = "ultra_high"
        rec = submit_improvement(sample_data, path=tmp_queue)
        assert rec.priority == "medium"

    def test_submit_multiple(self, tmp_queue):
        for i in range(5):
            submit_improvement({
                "type": "implement",
                "target": f"mod{i}.py",
                "action": f"Do {i}",
                "reason": f"Reason {i}",
            }, path=tmp_queue)
        queue = _load_queue(tmp_queue)
        assert len(queue) == 5


# ── get_pending_improvements tests ────────────────────────────

class TestGetPending:

    def test_get_empty(self, tmp_queue):
        result = get_pending_improvements(path=tmp_queue)
        assert result == []

    def test_get_pending_only(self, tmp_queue):
        # Submit 2 pending, mark 1 done
        r1 = submit_improvement({"type": "implement", "target": "a", "action": "a", "reason": "a"}, path=tmp_queue)
        r2 = submit_improvement({"type": "fix", "target": "b", "action": "b", "reason": "b"}, path=tmp_queue)
        report_result(r1.id, success=True, path=tmp_queue)

        pending = get_pending_improvements(path=tmp_queue)
        assert len(pending) == 1
        assert pending[0].id == r2.id

    def test_filter_by_type(self, tmp_queue):
        submit_improvement({"type": "add_tests", "target": "a", "action": "a", "reason": "a"}, path=tmp_queue)
        submit_improvement({"type": "implement", "target": "b", "action": "b", "reason": "b"}, path=tmp_queue)

        tests_only = get_pending_improvements(path=tmp_queue, imp_type="add_tests")
        assert len(tests_only) == 1
        assert tests_only[0].type == "add_tests"

    def test_filter_by_priority(self, tmp_queue):
        submit_improvement({"type": "implement", "target": "a", "action": "a", "reason": "a", "priority": "high"}, path=tmp_queue)
        submit_improvement({"type": "implement", "target": "b", "action": "b", "reason": "b", "priority": "low"}, path=tmp_queue)

        high_only = get_pending_improvements(path=tmp_queue, priority="high")
        assert len(high_only) == 1
        assert high_only[0].priority == "high"

    def test_sorted_by_priority(self, tmp_queue):
        submit_improvement({"type": "implement", "target": "low", "action": "a", "reason": "a", "priority": "low"}, path=tmp_queue)
        submit_improvement({"type": "implement", "target": "critical", "action": "a", "reason": "a", "priority": "critical"}, path=tmp_queue)
        submit_improvement({"type": "implement", "target": "high", "action": "a", "reason": "a", "priority": "high"}, path=tmp_queue)

        pending = get_pending_improvements(path=tmp_queue)
        assert pending[0].priority == "critical"
        assert pending[1].priority == "high"
        assert pending[2].priority == "low"

    def test_limit(self, tmp_queue):
        for i in range(10):
            submit_improvement({"type": "implement", "target": f"m{i}", "action": "a", "reason": "a"}, path=tmp_queue)
        limited = get_pending_improvements(path=tmp_queue, limit=3)
        assert len(limited) == 3


# ── State transition tests ────────────────────────────────────

class TestStateTransitions:

    def test_mark_in_progress(self, tmp_queue, sample_data):
        rec = submit_improvement(sample_data, path=tmp_queue)
        ok = mark_in_progress(rec.id, path=tmp_queue)
        assert ok is True

        # Not returned as pending anymore
        pending = get_pending_improvements(path=tmp_queue)
        assert len(pending) == 0

    def test_report_success(self, tmp_queue, sample_data):
        rec = submit_improvement(sample_data, path=tmp_queue)
        ok = report_result(rec.id, success=True, details="Done well", path=tmp_queue)
        assert ok is True

        queue = _load_queue(tmp_queue)
        item = next(r for r in queue if r["id"] == rec.id)
        assert item["status"] == STATUS_DONE
        assert item["result_success"] is True
        assert item["result_details"] == "Done well"

    def test_report_failure(self, tmp_queue, sample_data):
        rec = submit_improvement(sample_data, path=tmp_queue)
        ok = report_result(rec.id, success=False, details="Crashed", path=tmp_queue)
        assert ok is True

        queue = _load_queue(tmp_queue)
        item = next(r for r in queue if r["id"] == rec.id)
        assert item["status"] == STATUS_FAILED
        assert item["result_success"] is False

    def test_skip_improvement(self, tmp_queue, sample_data):
        rec = submit_improvement(sample_data, path=tmp_queue)
        ok = skip_improvement(rec.id, reason="Not needed", path=tmp_queue)
        assert ok is True

        queue = _load_queue(tmp_queue)
        item = next(r for r in queue if r["id"] == rec.id)
        assert item["status"] == STATUS_SKIPPED

    def test_update_nonexistent_record(self, tmp_queue):
        ok = report_result("nonexistent-id", success=True, path=tmp_queue)
        assert ok is False


# ── Queue stats and maintenance ───────────────────────────────

class TestQueueStats:

    def test_stats_empty(self, tmp_queue):
        stats = get_queue_stats(path=tmp_queue)
        assert stats["total"] == 0

    def test_stats_counts(self, tmp_queue):
        r1 = submit_improvement({"type": "add_tests", "target": "a", "action": "a", "reason": "a", "priority": "high"}, path=tmp_queue)
        r2 = submit_improvement({"type": "implement", "target": "b", "action": "b", "reason": "b"}, path=tmp_queue)
        report_result(r1.id, success=True, path=tmp_queue)

        stats = get_queue_stats(path=tmp_queue)
        assert stats["total"] == 2
        assert stats["by_status"][STATUS_DONE] == 1
        assert stats["by_status"][STATUS_PENDING] == 1
        assert stats["by_type"]["add_tests"] == 1
        assert stats["by_type"]["implement"] == 1

    def test_clear_completed(self, tmp_queue):
        r = submit_improvement({"type": "fix", "target": "a", "action": "a", "reason": "a"}, path=tmp_queue)
        report_result(r.id, success=True, path=tmp_queue)

        # Force old timestamp
        queue = _load_queue(tmp_queue)
        queue[0]["updated_at"] = time.time() - 30 * 86400  # 30 days ago
        _save_queue(queue, tmp_queue)

        removed = clear_completed(path=tmp_queue, keep_days=7.0)
        assert removed == 1
        assert len(_load_queue(tmp_queue)) == 0

    def test_clear_completed_keeps_recent(self, tmp_queue):
        r = submit_improvement({"type": "fix", "target": "a", "action": "a", "reason": "a"}, path=tmp_queue)
        report_result(r.id, success=True, path=tmp_queue)

        removed = clear_completed(path=tmp_queue, keep_days=7.0)
        assert removed == 0
        assert len(_load_queue(tmp_queue)) == 1


# ── Constants tests ───────────────────────────────────────────

class TestConstants:

    def test_valid_types(self):
        assert "implement" in VALID_TYPES
        assert "add_tests" in VALID_TYPES
        assert "fix" in VALID_TYPES
        assert "refactor" in VALID_TYPES
        assert len(VALID_TYPES) >= 7

    def test_valid_priorities(self):
        assert "critical" in VALID_PRIORITIES
        assert "high" in VALID_PRIORITIES
        assert "medium" in VALID_PRIORITIES
        assert "low" in VALID_PRIORITIES
