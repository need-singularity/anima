#!/usr/bin/env python3
"""update_progress.py — Refresh config/progress.json from project sources.

Reads:
  - config/consciousness_laws.json  (total_laws, meta_laws, topo_laws)
  - config/training_runs.json       (latest training status)
  - git rev-list --count HEAD       (commit count)
  - anima/src/*.py count            (python file count)
  - bench_v2 --verify last known    (from progress.json, not re-run)

Usage:
  python3 anima/scripts/update_progress.py          # update progress.json
  python3 anima/scripts/update_progress.py --dry     # preview without writing
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
REPO_ROOT = os.path.abspath(os.path.join(ROOT, '..'))
CONFIG = os.path.join(ROOT, 'config')
PROGRESS_PATH = os.path.join(CONFIG, 'progress.json')
LAWS_PATH = os.path.join(CONFIG, 'consciousness_laws.json')
TRAINING_PATH = os.path.join(CONFIG, 'training_runs.json')
SRC_DIR = os.path.join(ROOT, 'src')
BENCH_DIR = os.path.join(ROOT, 'benchmarks')


def load_json(path):
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"  WARN: {path}: {e}")
        return None


def get_laws_metrics():
    """Read law counts from consciousness_laws.json."""
    data = load_json(LAWS_PATH)
    if not data:
        return {}
    meta = data.get('_meta', {})
    return {
        'laws': meta.get('total_laws', 0),
        'meta_laws': meta.get('total_meta', 0),
        'topo_laws': meta.get('total_topo', 0),
    }


def get_training_status():
    """Read latest training runs from training_runs.json."""
    data = load_json(TRAINING_PATH)
    if not data:
        return {}
    runs = data.get('runs', {})
    result = {}
    for name, info in runs.items():
        result[name] = {
            'status': info.get('status', 'unknown'),
            'ce_best': info.get('ce_best'),
            'val_ce_best': info.get('val_ce_best'),
            'phi_best': info.get('phi_best'),
            'cells': info.get('cells'),
            'decoder': info.get('decoder'),
            'steps': info.get('steps'),
        }
        # Strip None values
        result[name] = {k: v for k, v in result[name].items() if v is not None}
    return result


def get_commit_count():
    """Get total commit count via git."""
    try:
        out = subprocess.check_output(
            ['git', 'rev-list', '--count', 'HEAD'],
            cwd=REPO_ROOT, stderr=subprocess.DEVNULL, text=True
        )
        return int(out.strip())
    except (subprocess.CalledProcessError, ValueError):
        return None


def count_python_files():
    """Count .py files in src/ and benchmarks/."""
    counts = {'src': 0, 'benchmarks': 0, 'total': 0}
    for d, key in [(SRC_DIR, 'src'), (BENCH_DIR, 'benchmarks')]:
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            if f.endswith('.py'):
                counts[key] += 1
    counts['total'] = counts['src'] + counts['benchmarks']
    return counts


def get_rust_loc():
    """Count Rust LOC in anima-rs/."""
    rs_dir = os.path.join(ROOT, 'anima-rs')
    if not os.path.isdir(rs_dir):
        return None
    total = 0
    for dirpath, _, filenames in os.walk(rs_dir):
        for f in filenames:
            if f.endswith('.rs'):
                try:
                    with open(os.path.join(dirpath, f), 'r') as fh:
                        total += sum(1 for line in fh if line.strip())
                except Exception:
                    pass
    return total


def count_hypothesis_docs():
    """Count hypothesis markdown files."""
    hyp_dir = os.path.join(ROOT, 'docs', 'hypotheses')
    if not os.path.isdir(hyp_dir):
        return 0
    count = 0
    for dirpath, _, filenames in os.walk(hyp_dir):
        count += sum(1 for f in filenames if f.endswith('.md'))
    return count


def update_progress(dry_run=False):
    """Main: gather metrics and update progress.json."""
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    # Load existing progress.json or start fresh
    progress = load_json(PROGRESS_PATH) or {}

    # -- Gather metrics --
    laws = get_laws_metrics()
    training = get_training_status()
    commits = get_commit_count()
    py_counts = count_python_files()
    rust_loc = get_rust_loc()
    hyp_docs = count_hypothesis_docs()

    # -- Update metrics section --
    metrics = progress.get('metrics', {})
    if laws:
        metrics['laws'] = laws['laws']
        metrics['meta_laws'] = laws['meta_laws']
        metrics['topo_laws'] = laws['topo_laws']
    if commits is not None:
        metrics['total_commits'] = commits
    metrics['python_files_src'] = py_counts['src']
    metrics['benchmark_files'] = py_counts['benchmarks']
    if rust_loc is not None:
        metrics['rust_loc'] = rust_loc
    metrics['hypothesis_docs'] = hyp_docs
    progress['metrics'] = metrics

    # -- Update training section --
    if training:
        progress['training'] = training

    # -- Timestamp --
    progress['last_updated'] = now
    meta = progress.get('_meta', {})
    meta['updated'] = now
    meta.setdefault('description', 'Project progress -- auto-updated by update_progress.py')
    meta.setdefault('format_version', 1)
    progress['_meta'] = meta

    # -- Report --
    print(f"  progress.json update @ {now}")
    print(f"  ─────────────────────────────────────")
    if laws:
        print(f"  Laws: {laws['laws']} | Meta: {laws['meta_laws']} | Topo: {laws['topo_laws']}")
    if commits is not None:
        print(f"  Commits: {commits}")
    print(f"  Python: {py_counts['src']} src + {py_counts['benchmarks']} bench")
    if rust_loc is not None:
        print(f"  Rust LOC: {rust_loc:,}")
    print(f"  Hypothesis docs: {hyp_docs}")
    active_training = [
        f"    {k}: {v.get('status', '?')}"
        for k, v in training.items() if 'progress' in v.get('status', '') or 'in_' in v.get('status', '')
    ]
    if active_training:
        print(f"  Active training:")
        for line in active_training:
            print(line)

    if dry_run:
        print(f"\n  --dry: skipped writing {PROGRESS_PATH}")
    else:
        with open(PROGRESS_PATH, 'w') as f:
            json.dump(progress, f, indent=2, ensure_ascii=False)
        print(f"\n  Written: {PROGRESS_PATH}")


if __name__ == '__main__':
    dry = '--dry' in sys.argv
    update_progress(dry_run=dry)
