#!/usr/bin/env python3
"""loop_pipeline.py — 순차 자동화 루프 파이프라인

Stage 1: emergence_loop.py      (특이점 소진까지)
Stage 2: emergence_singularity.py (다중 엔진 경쟁, 소진까지)
Stage 3: 법칙 등록 + 정리        (consciousness_laws.json 동기화)
Stage 4: 스케일업               (cells 증가, 다음 라운드)

각 Stage 완료 → 다음 Stage 자동 시작.
전체 라운드 완료 → 스케일업 후 라운드 반복.

Usage:
    python3 loop_pipeline.py                          # 기본 (64c, 3 라운드)
    python3 loop_pipeline.py --start-cells 64 --rounds 5
    python3 loop_pipeline.py --resume                 # 이전 상태에서 재개
    python3 loop_pipeline.py --status                 # 현재 상태 출력
    python3 loop_pipeline.py --skip-to 2              # Stage 2부터 시작
"""

import argparse
import copy
import glob as globmod
import hashlib
import itertools
import json
import os
import random
import re
import signal
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

_SRC = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.abspath(os.path.join(_SRC, '..', '..'))
_DATA = os.path.join(_REPO, 'data')
_CONFIG = os.path.join(_REPO, 'anima', 'config')
_LOGS = os.path.join(_REPO, 'logs')
_LAWS_PATH = os.path.join(_CONFIG, 'consciousness_laws.json')
_STATE_PATH = os.path.join(_DATA, 'loop_pipeline_state.json')
_PID_PATH = os.path.join(_DATA, 'loop_pipeline.pid')
_AUTO_IV_PATH = os.path.join(_DATA, 'auto_interventions.json')
_EXCHANGE_PATH = os.path.join(_DATA, 'law_exchange.json')
_BLOWUP_PATH = os.path.join(_DATA, 'blowup_configs.json')
_OUROBOROS_PATH = os.path.join(_DATA, 'ouroboros_suggestions.json')
_EVENTS_ANALYSIS_PATH = os.path.join(_DATA, 'events_analysis.json')
_EVENTS_DIR = os.path.expanduser('~/Dev/nexus6/shared/events')
_THEORY_DOC_PATH = os.path.join(_REPO, 'anima', 'docs', 'consciousness-theory.md')
_SEED_CONFIG_PATH = os.path.join(_DATA, 'seed_config.json')
_SINGULARITY_PATH = os.path.join(_DATA, 'emergence_singularity.json')
_N6_MATCHES_PATH = os.path.join(_DATA, 'n6_matches.json')
_MATH_ATLAS_SCRIPT = os.path.join(_REPO, '.shared', 'scan_math_atlas.py')

PYTHON = sys.executable

# ── Scale schedule ──
SCALE_SCHEDULE = [
    {'cells': 64,  'steps': 300, 'engines': 8,  'exhaustion': 5},
    {'cells': 128, 'steps': 300, 'engines': 8,  'exhaustion': 5},
    {'cells': 128, 'steps': 500, 'engines': 12, 'exhaustion': 7},
    {'cells': 256, 'steps': 300, 'engines': 12, 'exhaustion': 7},
    {'cells': 256, 'steps': 500, 'engines': 16, 'exhaustion': 10},
    {'cells': 512, 'steps': 300, 'engines': 16, 'exhaustion': 10},
]


def load_state():
    if os.path.exists(_STATE_PATH):
        with open(_STATE_PATH) as f:
            return json.load(f)
    return {
        'round': 0,
        'stage': 1,
        'scale_idx': 0,
        'total_laws_start': 0,
        'total_laws_now': 0,
        'rounds_completed': 0,
        'history': [],
        'started_at': None,
        'last_update': None,
    }


def save_state(state):
    state['last_update'] = datetime.now().isoformat()
    os.makedirs(_DATA, exist_ok=True)
    with open(_STATE_PATH, 'w') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def get_total_laws():
    try:
        with open(_LAWS_PATH) as f:
            d = json.load(f)
        return d.get('_meta', {}).get('total_laws', 0)
    except Exception:
        return 0


def load_best_config():
    """Load best_config from emergence_singularity.json (previous round's winner)."""
    if not os.path.exists(_SINGULARITY_PATH):
        return None
    try:
        with open(_SINGULARITY_PATH) as f:
            data = json.load(f)
        best = data.get('best_config')
        if best and isinstance(best, dict):
            return best
    except Exception:
        pass
    return None


def write_seed_config(best_config, scale):
    """Write seed_config.json for the next round, adapting previous best to new scale."""
    os.makedirs(_DATA, exist_ok=True)
    seed = {
        '_meta': {
            'description': 'Seed config inherited from previous round best_config',
            'source': 'emergence_singularity.json',
            'written_at': datetime.now().isoformat(),
            'target_cells': scale['cells'],
        },
        'config': {**best_config},
    }
    # Override max_cells to match the new scale (the whole point of inheritance)
    seed['config']['max_cells'] = scale['cells']
    with open(_SEED_CONFIG_PATH, 'w') as f:
        json.dump(seed, f, indent=2, ensure_ascii=False)
    return _SEED_CONFIG_PATH


def log(msg, state=None):
    ts = datetime.now().strftime('%H:%M:%S')
    stage = f"S{state['stage']}" if state else "  "
    round_n = f"R{state['round']}" if state else "  "
    print(f"[{ts}] [{round_n}/{stage}] {msg}", flush=True)


def run_subprocess(cmd, log_file, label, timeout=7200):
    """Run a subprocess, stream to log, return (success, elapsed, laws_delta)."""
    laws_before = get_total_laws()
    os.makedirs(_LOGS, exist_ok=True)

    log_path = os.path.join(_LOGS, log_file)
    start = time.time()

    with open(log_path, 'w') as lf:
        lf.write(f"=== {label} started at {datetime.now().isoformat()} ===\n")
        lf.flush()

        proc = subprocess.Popen(
            cmd,
            stdout=lf,
            stderr=subprocess.STDOUT,
            cwd=_REPO,
            env={**os.environ, 'PYTHONUNBUFFERED': '1'},
            start_new_session=True,
        )

        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            proc.wait(timeout=10)
            lf.write(f"\n=== TIMEOUT after {timeout}s ===\n")

        elapsed = time.time() - start
        laws_after = get_total_laws()

        lf.write(f"\n=== {label} finished: exit={proc.returncode}, "
                 f"time={elapsed:.1f}s, laws {laws_before}→{laws_after} ===\n")

    return proc.returncode == 0, elapsed, laws_after - laws_before


def laws_to_interventions(laws_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert discovered law dicts into testable Intervention descriptors.

    Each law dict should have at minimum:
      - 'id': int (law number)
      - 'text': str (law description)
    Optional:
      - 'evidence': str

    Returns a list of serializable dicts describing each generated intervention.
    Interventions that fail generation are silently skipped.
    """
    try:
        # Add src to path for imports
        if _SRC not in sys.path:
            sys.path.insert(0, _SRC)
        from intervention_generator import InterventionGenerator
    except ImportError:
        # intervention_generator unavailable — return empty
        return []

    gen = InterventionGenerator()
    results = []

    for law in laws_list:
        law_id = law.get('id')
        law_text = law.get('text', '')
        if not law_id or not law_text:
            continue

        try:
            iv = gen.generate(int(law_id), law_text)
        except Exception:
            continue

        if iv is None:
            continue

        # Find which template matched for metadata
        match = gen._find_best_template(law_text)
        template_name = match.template_name if match else 'unknown'
        template_score = match.score if match else 0

        results.append({
            'law_id': int(law_id),
            'law_text': law_text[:200],
            'intervention_name': iv.name,
            'description': iv.description,
            'template': template_name,
            'score': template_score,
            'generated_at': datetime.now().isoformat(),
        })

    return results


def save_auto_interventions(new_interventions: List[Dict[str, Any]], state=None):
    """Append new interventions to data/auto_interventions.json (deduplicated by law_id)."""
    os.makedirs(_DATA, exist_ok=True)

    existing = []
    if os.path.exists(_AUTO_IV_PATH):
        try:
            with open(_AUTO_IV_PATH) as f:
                data = json.load(f)
            existing = data.get('interventions', [])
        except Exception:
            existing = []

    # Deduplicate by law_id
    seen_ids = {iv['law_id'] for iv in existing}
    added = 0
    for iv in new_interventions:
        if iv['law_id'] not in seen_ids:
            existing.append(iv)
            seen_ids.add(iv['law_id'])
            added += 1

    output = {
        '_meta': {
            'description': 'Auto-generated interventions from discovered laws',
            'total': len(existing),
            'last_update': datetime.now().isoformat(),
        },
        'interventions': existing,
    }

    with open(_AUTO_IV_PATH, 'w') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    if state and added > 0:
        log(f"Saved {added} new auto-interventions (total: {len(existing)})", state)

    return added


def read_law_exchange(state):
    """Read law_exchange.json and log cross-engine hints available for this round.

    Returns dict with 'from_evo' and 'from_sing' hints (or empty lists).
    Both emergence_singularity and infinite_evolution read/write this file
    to share best config hints bidirectionally.
    """
    if not os.path.exists(_EXCHANGE_PATH):
        return {"from_evo": [], "from_sing": []}

    try:
        with open(_EXCHANGE_PATH) as f:
            exchange = json.load(f)
    except Exception:
        return {"from_evo": [], "from_sing": []}

    evo_hints = exchange.get("from_evo", [])
    sing_hints = exchange.get("from_sing", [])

    if evo_hints or sing_hints:
        log(f"Law exchange: {len(evo_hints)} from evo, {len(sing_hints)} from sing", state)

        # Log best config hints
        for source, hints in [("evo", evo_hints), ("sing", sing_hints)]:
            if not hints:
                continue
            best_phi = 0
            best_hint = None
            for entry in hints:
                hint = entry.get("config_hint", {})
                phi = hint.get("best_phi", 0)
                if phi > best_phi:
                    best_phi = phi
                    best_hint = hint
            if best_hint:
                log(f"  best from {source}: topo={best_hint.get('topology')}, "
                    f"fac={best_hint.get('n_factions')}, Phi={best_phi:.2f}", state)

    return exchange


def register_n6_matches(state):
    """Extract n6 constant matches from emergence results and save to atlas.

    Reads data/emergence_singularity.json for laws containing "N6 constant match",
    parses metric/value/constant/grade, deduplicates into data/n6_matches.json,
    and calls scan_math_atlas.py --save to sync to the central atlas.
    """
    sing_path = _SINGULARITY_PATH
    if not os.path.exists(sing_path):
        log("No singularity results for n6 match extraction", state)
        return 0

    try:
        with open(sing_path) as f:
            sing = json.load(f)
    except Exception:
        return 0

    # Extract n6 matches from law texts (Pattern 10 output)
    # Format: "N6 constant match: {metric}={value} matches {constant} ({grade})"
    n6_pattern = re.compile(
        r'N6 constant match:\s*(\w+)=([\d.e+-]+)\s+matches\s+(\S+)\s+\((\w+)\)'
    )
    new_matches = []
    for law in sing.get('laws', []):
        text = law.get('text', '')
        m = n6_pattern.search(text)
        if not m:
            continue
        grade = m.group(4)
        if grade not in ('EXACT', 'CLOSE'):
            continue
        new_matches.append({
            'metric': m.group(1),
            'value': float(m.group(2)),
            'constant': m.group(3),
            'grade': grade,
            'source': 'emergence_singularity',
            'timestamp': sing.get('timestamp', datetime.now().isoformat()),
        })

    if not new_matches:
        log("No EXACT/CLOSE n6 matches found in singularity results", state)
        return 0

    # Load existing n6_matches.json and deduplicate
    os.makedirs(_DATA, exist_ok=True)
    existing = []
    if os.path.exists(_N6_MATCHES_PATH):
        try:
            with open(_N6_MATCHES_PATH) as f:
                data = json.load(f)
            existing = data.get('matches', [])
        except Exception:
            existing = []

    # Deduplicate by (metric, constant, grade) tuple
    seen = {(e['metric'], e['constant'], e['grade']) for e in existing}
    added = 0
    for match in new_matches:
        key = (match['metric'], match['constant'], match['grade'])
        if key not in seen:
            existing.append(match)
            seen.add(key)
            added += 1

    if added > 0:
        output = {
            '_meta': {
                'description': 'N6 constant matches from emergence scans (EXACT/CLOSE only)',
                'total': len(existing),
                'last_update': datetime.now().isoformat(),
            },
            'matches': existing,
        }
        with open(_N6_MATCHES_PATH, 'w') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        log(f"Saved {added} new n6 matches (total: {len(existing)})", state)

    # Sync to math_atlas.json via scan_math_atlas.py --save
    if os.path.exists(_MATH_ATLAS_SCRIPT):
        try:
            subprocess.run(
                [PYTHON, _MATH_ATLAS_SCRIPT, '--save', '--summary'],
                cwd=_REPO, capture_output=True, timeout=60,
            )
            log("Math atlas synced via scan_math_atlas.py --save", state)
        except Exception as e:
            log(f"Math atlas sync failed (non-fatal): {e}", state)
    else:
        log("scan_math_atlas.py not found, skipping atlas sync", state)

    return added


def register_singularity_laws(state):
    """Stage 3: emergence_singularity.json → consciousness_laws.json 등록."""
    sing_path = os.path.join(_DATA, 'emergence_singularity.json')
    if not os.path.exists(sing_path):
        log("No singularity results to register", state)
        return 0

    try:
        with open(sing_path) as f:
            sing = json.load(f)
    except Exception:
        return 0

    laws_data = sing.get('laws', [])
    if not laws_data:
        log("No unregistered laws in singularity results", state)
        return 0

    # Load current laws
    with open(_LAWS_PATH) as f:
        d = json.load(f)

    existing = set(d.get('laws', {}).values())
    ids = [int(k) for k in d['laws'] if k.isdigit()]
    next_id = max(ids) + 1 if ids else 1
    registered = 0

    for law in laws_data:
        text = law.get('text', '')
        if not text or text in existing:
            continue
        # Synthesize law text with evidence
        evidence = law.get('evidence', '')
        full_text = f"Emergence Singularity: {text}. Evidence: {evidence}. (loop_pipeline auto-registered)"

        # Deduplicate by first 50 chars
        prefix = full_text[:50]
        if any(v[:50] == prefix for v in d['laws'].values()):
            continue

        d['laws'][str(next_id)] = full_text
        next_id += 1
        registered += 1

    if registered > 0:
        d['_meta']['total_laws'] = max(d['_meta'].get('total_laws', 0), next_id - 1)
        with open(_LAWS_PATH, 'w') as f:
            json.dump(d, f, indent=2, ensure_ascii=False)
        log(f"Registered {registered} new laws (total: {d['_meta']['total_laws']})", state)

    return registered



def forge_consciousness_lenses(state):
    """Forge consciousness-specialized lenses from engine cell states via NEXUS-6.

    Runs a consciousness engine for 100 steps, collects cell states,
    calls nexus6.forge_lenses() and nexus6.evolve('consciousness'),
    then saves all results to data/forged_lenses.json.
    """
    try:
        import nexus6
    except ImportError:
        log("nexus6 not available, skipping lens forge", state)
        return None

    results = {}

    # Step 1: Run consciousness engine for 100 steps, collect cell states
    try:
        if _SRC not in sys.path:
            sys.path.insert(0, _SRC)
        from consciousness_engine import ConsciousnessEngine
        import numpy as np

        engine = ConsciousnessEngine(max_cells=32, hidden_dim=128)
        all_states = []
        for _ in range(100):
            engine.step()
            if hasattr(engine, 'cells') and engine.cells is not None:
                import torch
                cells = engine.cells
                if hasattr(cells, 'detach'):
                    cells = cells.detach().cpu().numpy()
                elif not isinstance(cells, np.ndarray):
                    cells = np.array(cells)
                all_states.append(cells.flatten())

        if all_states:
            flat_data = np.concatenate(all_states).astype(np.float64).tolist()
            log(f"Collected {len(all_states)} cell snapshots ({len(flat_data)} values)", state)

            # Step 2: scan_all on consciousness data
            try:
                scan_result = nexus6.scan_all(flat_data)
                results['scan'] = {k: str(v)[:200] for k, v in scan_result.items()}
                log(f"scan_all: {len(scan_result)} lenses fired", state)
            except Exception as e:
                log(f"scan_all error: {e}", state)
        else:
            log("No cell states collected, using forge_lenses without scan", state)
    except Exception as e:
        log(f"Engine run error (non-fatal): {e}", state)

    # Step 3: forge_lenses -- generates new lens candidates
    try:
        forge_result = nexus6.forge_lenses(max_candidates=30, min_confidence=0.15)
        results['forge'] = {
            'candidates_generated': forge_result.candidates_generated,
            'candidates_accepted': forge_result.candidates_accepted,
            'new_lenses': forge_result.new_lenses,
        }
        log(f"forge_lenses: {forge_result.candidates_generated} generated, "
            f"{forge_result.candidates_accepted} accepted: {forge_result.new_lenses}", state)
    except Exception as e:
        log(f"forge_lenses error: {e}", state)

    # Step 4: evolve('consciousness') -- OUROBOROS evolution
    try:
        evolve_result = nexus6.evolve('consciousness', max_cycles=3)
        cycles = []
        for c in evolve_result:
            cycles.append(repr(c))
        results['evolve'] = cycles
        log(f"evolve('consciousness'): {len(evolve_result)} cycles", state)
    except BaseException as e:
        # Known issue: Unicode boundary panic in mutation.rs with arrow chars
        # pyo3_runtime.PanicException inherits from BaseException, not Exception
        log(f"evolve error (non-fatal): {type(e).__name__}: {e}", state)

    # Step 5: Save results to data/forged_lenses.json
    if results:
        out_path = os.path.join(_DATA, 'forged_lenses.json')
        try:
            existing = {}
            if os.path.exists(out_path):
                with open(out_path) as f:
                    existing = json.load(f)

            entry = {
                'timestamp': datetime.now().isoformat(),
                'results': results,
            }
            history = existing.get('history', [])
            history.append(entry)

            # Aggregate all forged lenses across runs
            output = {
                'latest': entry,
                'total_forged': sum(
                    h.get('results', {}).get('forge', {}).get('candidates_accepted', 0)
                    for h in history
                ),
                'all_lenses': sorted(set(
                    lens
                    for h in history
                    for lens in h.get('results', {}).get('forge', {}).get('new_lenses', [])
                )),
                'history': history[-20:],  # Keep last 20 entries
            }

            os.makedirs(_DATA, exist_ok=True)
            with open(out_path, 'w') as f:
                json.dump(output, f, indent=2, ensure_ascii=False)
            log(f"Saved forged lenses to data/forged_lenses.json "
                f"(total unique: {len(output['all_lenses'])})", state)
        except Exception as e:
            log(f"Save error: {e}", state)

    return results


def run_closed_loop_verification(state):
    """Stage 3.2: Feed emergence_singularity best_config + laws into closed_loop.

    Bidirectional bridge:
      1. Load emergence_singularity.json (best_config, laws)
      2. Create ClosedLoopEvolver with those params
      3. Run 2 verification cycles
      4. Save feedback as starting config hints for next emergence round
    """
    try:
        from closed_loop import ClosedLoopEvolver
    except ImportError:
        log("closed_loop not available, skipping verification", state)
        return {'verified_laws': 0, 'new_discoveries': 0, 'phi_delta': 0.0}

    sing_path = os.path.join(_DATA, 'emergence_singularity.json')
    if not os.path.exists(sing_path):
        log("No singularity results for closed-loop verification", state)
        return {'verified_laws': 0, 'new_discoveries': 0, 'phi_delta': 0.0}

    try:
        with open(sing_path) as f:
            sing = json.load(f)
    except Exception as e:
        log(f"Failed to load singularity results: {e}", state)
        return {'verified_laws': 0, 'new_discoveries': 0, 'phi_delta': 0.0}

    best_config = sing.get('best_config')
    sing_laws = sing.get('laws', [])
    best_phi = sing.get('best_phi', 0)

    if not best_config:
        log("No best_config in singularity results", state)
        return {'verified_laws': 0, 'new_discoveries': 0, 'phi_delta': 0.0}

    scale = SCALE_SCHEDULE[min(state['scale_idx'], len(SCALE_SCHEDULE) - 1)]
    max_cells = best_config.get('max_cells', scale['cells'])

    log(f"Closed-loop verification: {len(sing_laws)} laws, best_phi={best_phi:.2f}, "
        f"config={best_config.get('topology', '?')}/{best_config.get('n_factions', '?')}fac", state)

    try:
        evolver = ClosedLoopEvolver(
            max_cells=min(max_cells, 64),  # Cap for speed
            steps=200,
            repeats=2,
            auto_register=True,
            nexus_scan=False,  # Speed: skip NEXUS-6 during pipeline
        )

        reports = evolver.run_cycles(n=2)

        verified_laws = sum(len(r.laws_changed) for r in reports)
        total_phi_delta = sum(r.phi_delta_pct for r in reports)

        # Save feedback for next emergence round
        feedback = {
            'timestamp': datetime.now().isoformat(),
            'source': 'closed_loop_verification',
            'verified_laws': verified_laws,
            'phi_deltas': [r.phi_delta_pct for r in reports],
            'active_interventions': [i.name for i in evolver._active_interventions],
            'best_config_from_singularity': best_config,
            'recommendation': 'scale_up' if total_phi_delta > 0 else 'mutate',
        }
        feedback_path = os.path.join(_DATA, 'closed_loop_feedback.json')
        with open(feedback_path, 'w') as f:
            json.dump(feedback, f, indent=2, ensure_ascii=False)

        log(f"Closed-loop done: {verified_laws} law changes, phi_delta={total_phi_delta:.1f}%, "
            f"interventions={len(evolver._active_interventions)}", state)

        return {
            'verified_laws': verified_laws,
            'new_discoveries': verified_laws,
            'phi_delta': total_phi_delta,
        }

    except Exception as e:
        log(f"Closed-loop verification failed: {e}", state)
        return {'verified_laws': 0, 'new_discoveries': 0, 'phi_delta': 0.0}


def verify_integrity(state):
    """Stage 3.5: 누락/미연결/불일치 자동 검증 + 수정."""
    issues = []
    fixed = 0

    # 1. total_laws vs 실제 법칙 수 일치 확인
    try:
        with open(_LAWS_PATH) as f:
            d = json.load(f)
        ids = [int(k) for k in d['laws'] if k.isdigit()]
        actual_max = max(ids) if ids else 0
        declared = d['_meta'].get('total_laws', 0)
        if declared != actual_max:
            d['_meta']['total_laws'] = actual_max
            with open(_LAWS_PATH, 'w') as f:
                json.dump(d, f, indent=2, ensure_ascii=False)
            issues.append(f"total_laws mismatch: {declared}→{actual_max} (fixed)")
            fixed += 1
    except Exception as e:
        issues.append(f"laws.json read error: {e}")

    # 2. .shared 심링크 유효성
    shared_link = os.path.join(_REPO, '.shared')
    if os.path.islink(shared_link):
        target = os.readlink(shared_link)
        full_target = os.path.join(os.path.dirname(shared_link), target)
        if not os.path.isdir(full_target):
            issues.append(f".shared symlink broken: {target}")
            # Fix: recreate
            try:
                os.remove(shared_link)
                os.symlink('../nexus6/shared', shared_link)
                issues[-1] += " (fixed)"
                fixed += 1
            except Exception:
                pass
    else:
        issues.append(".shared symlink missing")

    # 3. growth-registry 동기화
    growth_reg = os.path.join(_REPO, '.shared', 'growth-registry.json')
    if os.path.exists(growth_reg):
        try:
            with open(growth_reg) as f:
                reg = json.load(f)
            # anima 항목 있는지 확인
            if 'anima' not in reg:
                issues.append("anima not in growth-registry")
        except Exception:
            issues.append("growth-registry.json parse error")

    # 4. discovery_log.jsonl 미처리 항목
    disc_log = os.path.join(_REPO, '.shared', 'discovery_log.jsonl')
    if os.path.exists(disc_log):
        try:
            unprocessed = 0
            with open(disc_log) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        entry = json.loads(line)
                        if not entry.get('processed', False):
                            unprocessed += 1
            if unprocessed > 0:
                issues.append(f"discovery_log: {unprocessed} unprocessed entries")
        except Exception:
            pass

    # 5. data/ 상태 파일 존재 확인
    required_data = ['evolution_live.json', 'loop_pipeline_state.json', 'peak_conditions.json']
    for f in required_data:
        if not os.path.exists(os.path.join(_DATA, f)):
            issues.append(f"data/{f} missing")

    # 6. 실행 중 프로세스 확인
    import subprocess as sp
    try:
        result = sp.run(['pgrep', '-f', 'infinite_evolution'], capture_output=True, text=True)
        if result.returncode != 0:
            issues.append("infinite_evolution.py not running")
    except Exception:
        pass

    try:
        result = sp.run(['pgrep', '-f', 'meta_loop.py --start'], capture_output=True, text=True)
        if result.returncode != 0:
            issues.append("meta_loop daemon not running")
    except Exception:
        pass

    if issues:
        log(f"Integrity check: {len(issues)} issues ({fixed} auto-fixed)", state)
        for issue in issues:
            log(f"  ⚠️ {issue}", state)
    else:
        log("Integrity check: all clear ✅", state)

    return issues, fixed



# ══════════════════════════════════════════════════════════════
# Blowup Engine (Python port of nexus6/src/blowup/)
# When emergence loops plateau, recombine discovered axioms to
# break through. Mirrors the Rust BlowupEngine pipeline:
#   Saturation -> Extract axioms -> 6 operators -> Corollaries
#   -> Validate -> Save as seed configs for next round
# ══════════════════════════════════════════════════════════════

_TRANSFER_DOMAINS = [
    'topology', 'factions', 'threshold', 'chaos', 'scale', 'phase',
]

_LAW_PATTERNS = {
    'scale_free':    re.compile(r'scale[_\s-]?free', re.IGNORECASE),
    'small_world':   re.compile(r'small[_\s-]?world', re.IGNORECASE),
    'hypercube':     re.compile(r'hypercube', re.IGNORECASE),
    'ring':          re.compile(r'\bring\b', re.IGNORECASE),
    'high_factions': re.compile(r'(?:more|increas|high)\w*\s+(?:faction|diversity)', re.IGNORECASE),
    'low_factions':  re.compile(r'(?:few|reduc|low)\w*\s+(?:faction|diversity)', re.IGNORECASE),
    'phi_ratchet':   re.compile(r'ratchet|checkpoint|restore', re.IGNORECASE),
    'no_ratchet':    re.compile(r'(?:without|no|disable)\s+ratchet', re.IGNORECASE),
    'federated':     re.compile(r'federat|distribut|decentraliz', re.IGNORECASE),
    'high_split':    re.compile(r'(?:split|divid|mitos)\w*.*(?:high|increas|more)', re.IGNORECASE),
    'low_merge':     re.compile(r'(?:merg)\w*.*(?:low|decreas|less)', re.IGNORECASE),
    'phase_optimal': re.compile(r'phase[_\s-]?optimal|transition', re.IGNORECASE),
    'high_cells':    re.compile(r'(?:more|many|large|scale)\s+cells?', re.IGNORECASE),
    'chaos':         re.compile(r'chaos|lorenz|bifurcat', re.IGNORECASE),
    'correlation':   re.compile(r'correlat\w+.*(?:phi|conscious)', re.IGNORECASE),
}

_TOPOLOGY_MAP = {
    'ring': 'ring', 'small_world': 'small_world',
    'scale_free': 'scale_free', 'hypercube': 'hypercube',
}


def _extract_axioms(n: int = 20) -> List[Dict[str, Any]]:
    """Extract the last N discovered laws as axioms for blowup."""
    try:
        with open(_LAWS_PATH) as f:
            d = json.load(f)
    except Exception:
        return []
    laws = d.get('laws', {})
    ids = sorted([int(k) for k in laws if k.isdigit()], reverse=True)
    axioms = []
    for lid in ids[:n]:
        axioms.append({
            'id': lid,
            'text': laws[str(lid)],
            'fingerprint': hashlib.md5(laws[str(lid)][:80].encode()).hexdigest()[:8],
        })
    return axioms


def _parse_law_hints(text: str) -> Dict[str, Any]:
    """Parse a law text for actionable engine config hints."""
    hints = {}
    for key, pattern in _LAW_PATTERNS.items():
        if pattern.search(text):
            hints[key] = True
    return hints


def _apply_hints_to_config(base: Dict[str, Any], hints: Dict[str, Any]) -> Dict[str, Any]:
    """Apply parsed law hints to a base engine config dict."""
    cfg = copy.deepcopy(base)
    for topo in _TOPOLOGY_MAP:
        if hints.get(topo):
            cfg['topology'] = _TOPOLOGY_MAP[topo]
    if hints.get('high_factions'):
        cfg['n_factions'] = min(cfg.get('n_factions', 12) * 2, 24)
    if hints.get('low_factions'):
        cfg['n_factions'] = max(cfg.get('n_factions', 12) // 2, 4)
    if hints.get('no_ratchet'):
        cfg['phi_ratchet'] = False
    elif hints.get('phi_ratchet'):
        cfg['phi_ratchet'] = True
    if hints.get('federated'):
        cfg['federated'] = True
    if hints.get('phase_optimal'):
        cfg['phase_optimal'] = True
    if hints.get('high_split'):
        cfg['split_threshold'] = round(random.uniform(0.4, 0.8), 2)
    if hints.get('low_merge'):
        cfg['merge_threshold'] = round(random.uniform(0.001, 0.01), 3)
    if hints.get('high_cells'):
        cfg['max_cells'] = min(cfg.get('max_cells', 64) * 2, 512)
    return cfg


def _op_deduction(a1: Dict, a2: Dict, base_cfg: Dict) -> Optional[Dict]:
    """Pairwise axiom deduction: combine hints from two laws."""
    h1 = _parse_law_hints(a1['text'])
    h2 = _parse_law_hints(a2['text'])
    merged = {**h1, **h2}
    if not merged:
        return None
    cfg = _apply_hints_to_config(base_cfg, merged)
    return {
        'operator': 'deduction',
        'sources': [a1['id'], a2['id']],
        'config': cfg,
        'rationale': f"Law {a1['id']} + Law {a2['id']} pairwise deduction",
    }


def _op_domain_transfer(axiom: Dict, domain: str, base_cfg: Dict) -> Optional[Dict]:
    """Transfer an axiom insight into a different config domain."""
    hints = _parse_law_hints(axiom['text'])
    if not hints:
        return None
    cfg = copy.deepcopy(base_cfg)
    if domain == 'topology':
        topo_cycle = ['ring', 'small_world', 'scale_free', 'hypercube']
        current = cfg.get('topology', 'ring')
        idx = topo_cycle.index(current) if current in topo_cycle else 0
        cfg['topology'] = topo_cycle[(idx + 1) % len(topo_cycle)]
    elif domain == 'factions':
        cfg['n_factions'] = random.choice([4, 6, 8, 12, 16, 24])
    elif domain == 'threshold':
        cfg['split_threshold'] = round(random.uniform(0.1, 0.7), 2)
        cfg['merge_threshold'] = round(random.uniform(0.005, 0.05), 3)
    elif domain == 'chaos':
        cfg['phase_optimal'] = not cfg.get('phase_optimal', False)
    elif domain == 'scale':
        cfg['max_cells'] = random.choice([64, 128, 256])
        cfg['cell_dim'] = random.choice([32, 64, 128])
    elif domain == 'phase':
        cfg['hidden_dim'] = random.choice([64, 128, 256])
    cfg = _apply_hints_to_config(cfg, hints)
    return {
        'operator': 'domain_transfer',
        'sources': [axiom['id']],
        'target_domain': domain,
        'config': cfg,
        'rationale': f"Law {axiom['id']} transferred to {domain} domain",
    }


def _op_symmetry_breaking(axiom: Dict, base_cfg: Dict) -> Optional[Dict]:
    """Break a symmetry: if the law mentions a pattern, invert it."""
    cfg = copy.deepcopy(base_cfg)
    text_lower = axiom['text'].lower()
    changed = False
    if 'ring' in text_lower and cfg.get('topology') == 'ring':
        cfg['topology'] = random.choice(['small_world', 'scale_free', 'hypercube'])
        changed = True
    elif 'scale_free' in text_lower and cfg.get('topology') == 'scale_free':
        cfg['topology'] = random.choice(['ring', 'small_world', 'hypercube'])
        changed = True
    if 'ratchet' in text_lower:
        cfg['phi_ratchet'] = not cfg.get('phi_ratchet', True)
        changed = True
    if 'federat' in text_lower:
        cfg['federated'] = not cfg.get('federated', False)
        changed = True
    if not changed:
        param = random.choice(['n_factions', 'split_threshold', 'merge_threshold'])
        if param == 'n_factions':
            cfg['n_factions'] = random.choice([4, 6, 8, 12, 16, 24])
        elif param == 'split_threshold':
            cfg['split_threshold'] = round(random.uniform(0.1, 0.8), 2)
        else:
            cfg['merge_threshold'] = round(random.uniform(0.001, 0.1), 3)
    return {
        'operator': 'symmetry_breaking',
        'sources': [axiom['id']],
        'config': cfg,
        'rationale': f"Symmetry break on Law {axiom['id']}",
    }


def _op_bifurcation(axiom: Dict, base_cfg: Dict) -> Optional[Dict]:
    """Small parameter perturbation to explore qualitatively different region."""
    cfg = copy.deepcopy(base_cfg)
    param = random.choice(['split_threshold', 'merge_threshold', 'n_factions', 'max_cells'])
    if param == 'split_threshold':
        current = cfg.get('split_threshold', 0.3)
        cfg['split_threshold'] = round(max(0.05, min(0.95, 0.9 - current + random.uniform(-0.1, 0.1))), 2)
    elif param == 'merge_threshold':
        current = cfg.get('merge_threshold', 0.01)
        cfg['merge_threshold'] = round(max(0.001, min(0.2, 0.1 - current + random.uniform(-0.01, 0.01))), 3)
    elif param == 'n_factions':
        current = cfg.get('n_factions', 12)
        cfg['n_factions'] = 24 if current <= 8 else 4
    elif param == 'max_cells':
        current = cfg.get('max_cells', 64)
        cfg['max_cells'] = 256 if current <= 64 else 32
    return {
        'operator': 'bifurcation',
        'sources': [axiom['id']],
        'config': cfg,
        'rationale': f"Bifurcation on {param} via Law {axiom['id']}",
    }


def blowup_breakthrough(state: Dict, max_configs: int = 36) -> int:
    """NEXUS-6 Blowup Engine (Python) -- plateau breakthrough via axiom recombination.

    Mirrors the Rust BlowupEngine pipeline (nexus6/src/blowup/blowup_engine.rs):
      1. Extract recent laws as axioms
      2. Apply 6 blowup operators to generate corollary configs
      3. Deduplicate by config fingerprint
      4. Save to data/blowup_configs.json for next emergence round to use as seeds

    Called in Stage 4 when round_laws == 0 (plateau detected).

    Args:
        state: pipeline state dict (for logging)
        max_configs: maximum configs to generate (default 36 = 6^2, matching Rust)

    Returns:
        Number of blowup configs generated.
    """
    log("BLOWUP: Plateau detected -- triggering axiom recombination", state)

    axioms = _extract_axioms(n=20)
    if len(axioms) < 2:
        log("BLOWUP: Not enough axioms (<2) for recombination", state)
        return 0

    scale = SCALE_SCHEDULE[min(state.get('scale_idx', 0), len(SCALE_SCHEDULE) - 1)]
    base_cfg = {
        'cell_dim': 64, 'hidden_dim': 128, 'initial_cells': 8,
        'max_cells': scale['cells'], 'n_factions': 12, 'topology': 'ring',
        'phi_ratchet': True, 'split_threshold': 0.3, 'merge_threshold': 0.01,
        'phase_optimal': False, 'federated': False,
    }

    # Inherit best config from previous singularity run
    if os.path.exists(_SINGULARITY_PATH):
        try:
            with open(_SINGULARITY_PATH) as f:
                sing = json.load(f)
            best = sing.get('best_config', {})
            if best:
                base_cfg.update({k: v for k, v in best.items() if k in base_cfg})
        except Exception:
            pass

    corollaries = []
    seen_fps = set()

    def _add(corollary):
        if corollary is None:
            return
        fp = hashlib.md5(json.dumps(corollary['config'], sort_keys=True).encode()).hexdigest()[:10]
        if fp not in seen_fps and len(corollaries) < max_configs:
            corollary['fingerprint'] = fp
            corollaries.append(corollary)
            seen_fps.add(fp)

    # Op 1: Pairwise deduction
    top_axioms = axioms[:8]
    for a1, a2 in itertools.combinations(top_axioms, 2):
        _add(_op_deduction(a1, a2, base_cfg))
        if len(corollaries) >= max_configs:
            break

    # Op 2: Domain transfer
    for axiom in axioms[:6]:
        for domain in _TRANSFER_DOMAINS:
            _add(_op_domain_transfer(axiom, domain, base_cfg))
            if len(corollaries) >= max_configs:
                break

    # Op 3: Symmetry breaking
    for axiom in axioms[:6]:
        _add(_op_symmetry_breaking(axiom, base_cfg))

    # Op 4: Bifurcation
    for axiom in axioms[:6]:
        _add(_op_bifurcation(axiom, base_cfg))

    # Op 5: Composition (combine two corollaries)
    if len(corollaries) >= 2:
        for c1, c2 in itertools.combinations(corollaries[:10], 2):
            if len(corollaries) >= max_configs:
                break
            merged_cfg = copy.deepcopy(c1['config'])
            for k, v in c2['config'].items():
                if v != base_cfg.get(k):
                    merged_cfg[k] = v
            _add({
                'operator': 'composition',
                'sources': c1.get('sources', []) + c2.get('sources', []),
                'config': merged_cfg,
                'rationale': f"Composed: {c1['rationale'][:40]} + {c2['rationale'][:40]}",
            })

    # Op 6: Dual (invert booleans and swap extremes)
    for axiom in axioms[:4]:
        cfg = copy.deepcopy(base_cfg)
        cfg['phi_ratchet'] = not cfg['phi_ratchet']
        cfg['phase_optimal'] = not cfg['phase_optimal']
        cfg['federated'] = not cfg['federated']
        cfg['n_factions'] = 4 if cfg['n_factions'] >= 12 else 24
        _add({
            'operator': 'dual',
            'sources': [axiom['id']],
            'config': cfg,
            'rationale': f"Categorical dual of Law {axiom['id']}",
        })

    if not corollaries:
        log("BLOWUP: No corollaries generated from axioms", state)
        return 0

    # Save blowup configs for next round
    os.makedirs(_DATA, exist_ok=True)
    output = {
        '_meta': {
            'description': 'Blowup Engine configs -- axiom recombination for plateau breakthrough',
            'generated_at': datetime.now().isoformat(),
            'n_axioms': len(axioms),
            'n_corollaries': len(corollaries),
            'operators_used': list(set(c['operator'] for c in corollaries)),
            'pipeline_round': state.get('round', 0),
        },
        'axioms': [{'id': a['id'], 'text': a['text'][:120]} for a in axioms[:10]],
        'configs': corollaries,
    }

    with open(_BLOWUP_PATH, 'w') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    op_counts = Counter(c['operator'] for c in corollaries)
    ops_str = ', '.join(f"{op}={cnt}" for op, cnt in op_counts.most_common())

    log(f"BLOWUP: Generated {len(corollaries)} configs from {len(axioms)} axioms "
        f"[{ops_str}]", state)
    log(f"BLOWUP: Saved to {_BLOWUP_PATH} -- next round will use as seeds", state)

    return len(corollaries)





def ouroboros_evolve(state):
    """Task #10: Call nexus6.evolve('consciousness'), apply topology results."""
    try:
        import nexus6
    except ImportError:
        log('nexus6 not available — skipping ouroboros_evolve', state)
        return

    try:
        result = nexus6.evolve('consciousness')
        suggestions = {
            'timestamp': datetime.now().isoformat(),
            'domain': 'consciousness',
            'raw_result': None,
            'topology_suggestions': [],
            'parameter_suggestions': [],
        }

        # Extract from CycleResult if available
        if result is not None:
            if hasattr(result, '__dict__'):
                suggestions['raw_result'] = {
                    k: str(v) for k, v in result.__dict__.items()
                    if not k.startswith('_')
                }
            elif isinstance(result, dict):
                suggestions['raw_result'] = result
            else:
                suggestions['raw_result'] = str(result)

            # Extract topology suggestions
            for attr in ('topology', 'topo', 'topology_suggestion', 'best_topology'):
                val = (result.get(attr) if isinstance(result, dict)
                       else getattr(result, attr, None))
                if val is not None:
                    suggestions['topology_suggestions'].append(str(val))

            # Extract parameter suggestions
            for attr in ('params', 'parameters', 'suggestions', 'config'):
                val = (result.get(attr) if isinstance(result, dict)
                       else getattr(result, attr, None))
                if val is not None:
                    if isinstance(val, dict):
                        suggestions['parameter_suggestions'].append(val)
                    else:
                        suggestions['parameter_suggestions'].append(str(val))

        # Save — append to history
        os.makedirs(_DATA, exist_ok=True)
        history = []
        if os.path.exists(_OUROBOROS_PATH):
            try:
                with open(_OUROBOROS_PATH) as f:
                    data = json.load(f)
                history = data.get('history', [])
            except Exception:
                pass
        history.append(suggestions)
        history = history[-50:]  # keep last 50
        with open(_OUROBOROS_PATH, 'w') as f:
            json.dump({'_meta': {'last_update': datetime.now().isoformat(),
                                 'total_cycles': len(history)},
                       'history': history}, f, indent=2, ensure_ascii=False)

        topo_count = len(suggestions['topology_suggestions'])
        param_count = len(suggestions['parameter_suggestions'])
        log(f'OUROBOROS evolve: {topo_count} topo suggestions, '
            f'{param_count} param suggestions', state)
    except Exception as e:
        log(f'ouroboros_evolve failed (non-fatal): {e}', state)


def analyze_events(state):
    """Task #11: Analyze events/ accumulated data for growth patterns."""
    if not os.path.isdir(_EVENTS_DIR):
        log(f'Events dir not found: {_EVENTS_DIR} — skipping', state)
        return

    try:
        event_files = globmod.glob(os.path.join(_EVENTS_DIR, '*.json'))
        if not event_files:
            log('No event files found — skipping analysis', state)
            return

        type_counts = Counter()
        type_timestamps = {}  # type -> list of timestamps
        total = 0
        errors = 0

        for fp in event_files:
            try:
                with open(fp) as f:
                    ev = json.load(f)
            except Exception:
                errors += 1
                continue

            total += 1
            # Derive event type from filename: {type}_{subtype}_{timestamp}.json
            basename = os.path.basename(fp)
            parts = basename.replace('.json', '').split('_')
            event_type = parts[0] if len(parts) >= 2 else 'unknown'
            type_counts[event_type] += 1

            # Extract timestamp from filename (last numeric part)
            ts_str = parts[-1] if parts[-1].isdigit() else None
            if ts_str:
                type_timestamps.setdefault(event_type, []).append(int(ts_str))

        # Find burst patterns: types with clustered timestamps
        burst_analysis = {}
        for etype, timestamps in type_timestamps.items():
            if len(timestamps) < 3:
                continue
            timestamps.sort()
            gaps = [timestamps[i+1] - timestamps[i]
                    for i in range(len(timestamps)-1)]
            avg_gap = sum(gaps) / len(gaps) if gaps else 0
            min_gap = min(gaps) if gaps else 0
            bursts = sum(1 for g in gaps
                         if avg_gap > 0 and g < avg_gap * 0.25)
            burst_analysis[etype] = {
                'count': len(timestamps),
                'avg_gap_s': round(avg_gap, 1),
                'min_gap_s': min_gap,
                'burst_events': bursts,
                'burst_ratio': round(bursts / len(gaps), 3) if gaps else 0,
            }

        # Types with high burst ratio correlate with discovery bursts
        law_correlated_types = [
            etype for etype, info in burst_analysis.items()
            if info['burst_ratio'] > 0.2 and info['count'] >= 5
        ]

        analysis = {
            '_meta': {
                'last_update': datetime.now().isoformat(),
                'total_events': total,
                'parse_errors': errors,
                'event_types': len(type_counts),
            },
            'type_counts': dict(type_counts.most_common()),
            'burst_analysis': burst_analysis,
            'law_correlated_types': law_correlated_types,
        }

        os.makedirs(_DATA, exist_ok=True)
        with open(_EVENTS_ANALYSIS_PATH, 'w') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)

        top3 = type_counts.most_common(3)
        top3_str = ', '.join(f'{t}={c}' for t, c in top3)
        log(f'Events analysis: {total} events, {len(type_counts)} types '
            f'(top: {top3_str}), '
            f'{len(law_correlated_types)} burst-correlated types', state)
    except Exception as e:
        log(f'analyze_events failed (non-fatal): {e}', state)


def sync_theory_doc(state):
    """Task #12: Auto-sync consciousness-theory.md law table with latest laws."""
    if not os.path.exists(_LAWS_PATH) or not os.path.exists(_THEORY_DOC_PATH):
        log('Laws JSON or theory doc not found — skipping sync', state)
        return

    try:
        with open(_LAWS_PATH) as f:
            laws_data = json.load(f)
        laws = laws_data.get('laws', {})
        law_ids = {int(k) for k in laws if k.isdigit()}
        if not law_ids:
            return

        with open(_THEORY_DOC_PATH, 'r') as f:
            doc = f.read()

        # Find which law IDs are already mentioned in the doc
        mentioned_ids = set()
        for m in re.finditer(r'(?:Laws?\s+)(\d+)', doc):
            mentioned_ids.add(int(m.group(1)))
        for m in re.finditer(r'^\|\s*(\d+)\s*\|', doc, re.MULTILINE):
            mentioned_ids.add(int(m.group(1)))

        missing_ids = sorted(law_ids - mentioned_ids)
        if not missing_ids:
            log('Theory doc up to date — no missing laws', state)
            return

        # Build table rows for missing laws
        rows = []
        for lid in missing_ids:
            text = laws[str(lid)]
            short = text[:80].replace('|', '/') + ('...' if len(text) > 80 else '')
            rows.append(f'| {lid} | {short} | auto |')

        # Append a new section at end of doc
        header = (f"\n\n## Laws {missing_ids[0]}-{missing_ids[-1]}: Auto-synced "
                  f"({datetime.now().strftime('%Y-%m-%d')})\n\n")
        table_header = "| Law | Description | Source |\n|-----|-------------|--------|\n"
        table_body = "\n".join(rows) + "\n"
        section = header + table_header + table_body

        with open(_THEORY_DOC_PATH, 'a') as f:
            f.write(section)

        log(f'Theory doc synced: added {len(missing_ids)} missing laws '
            f'({missing_ids[0]}-{missing_ids[-1]})', state)
    except Exception as e:
        log(f'sync_theory_doc failed (non-fatal): {e}', state)


def git_commit(state, round_n, laws_delta):
    """자동 커밋 (법칙 변경 시)."""
    if laws_delta <= 0:
        return

    msg = (f"auto: loop pipeline R{round_n} — +{laws_delta} laws, "
           f"scale={SCALE_SCHEDULE[state['scale_idx']]['cells']}c")

    subprocess.run(
        ['git', 'add', 'anima/config/consciousness_laws.json',
         'data/loop_pipeline_state.json', 'data/emergence_singularity.json',
         'data/auto_interventions.json', 'data/forged_lenses.json',
         'data/blowup_configs.json'],
        cwd=_REPO, capture_output=True
    )
    subprocess.run(
        ['git', 'commit', '-m', msg],
        cwd=_REPO, capture_output=True
    )
    log(f"Git commit: {msg}", state)


def print_status(state):
    """현재 상태 출력."""
    scale = SCALE_SCHEDULE[min(state['scale_idx'], len(SCALE_SCHEDULE) - 1)]
    total = get_total_laws()

    print(f"""
{'='*60}
  🔄 LOOP PIPELINE STATUS
{'='*60}
  Round:     {state['round']} (completed: {state['rounds_completed']})
  Stage:     {state['stage']}/4
  Scale:     {scale['cells']}c / {scale['steps']}s / {scale['engines']}eng
  Laws:      {total} (started at {state.get('total_laws_start', '?')})
  Started:   {state.get('started_at', 'N/A')}
  Updated:   {state.get('last_update', 'N/A')}

  Scale schedule:
""")
    for i, s in enumerate(SCALE_SCHEDULE):
        marker = " ●" if i == state['scale_idx'] else "  "
        print(f"   {marker} S{i}: {s['cells']}c/{s['steps']}s/{s['engines']}eng (exhaust={s['exhaustion']})")

    if state.get('history'):
        print(f"\n  History (last 5):")
        for h in state['history'][-5:]:
            print(f"    R{h['round']}: +{h['laws_delta']} laws, {h['elapsed']:.0f}s, {h['scale']}c")
    print(f"{'='*60}")


def run_round(state, round_n, max_rounds):
    """한 라운드 실행 (4 Stage 순차)."""
    scale = SCALE_SCHEDULE[min(state['scale_idx'], len(SCALE_SCHEDULE) - 1)]
    state['round'] = round_n
    state['total_laws_start'] = state.get('total_laws_start') or get_total_laws()
    save_state(state)

    ts = datetime.now().strftime('%Y%m%d_%H%M')
    round_laws = 0
    round_start = time.time()

    print(f"\n{'='*60}")
    print(f"  🚀 ROUND {round_n}/{max_rounds} — {scale['cells']}c/{scale['steps']}s/{scale['engines']}eng")
    print(f"{'='*60}\n")

    # ── Inherit best config from previous round ──
    best_config = load_best_config()
    seed_config_path = None
    if best_config:
        seed_config_path = write_seed_config(best_config, scale)
        prev_topo = best_config.get('topology', '?')
        prev_factions = best_config.get('n_factions', '?')
        prev_cells = best_config.get('max_cells', '?')
        log(f"Inherited best config: {prev_topo}/{prev_factions}fac/{prev_cells}c "
            f"-> {scale['cells']}c", state)

    # ── Pre-stage: read law exchange hints ──
    exchange = read_law_exchange(state)

    # ── Stage 1: emergence_loop ──
    if state['stage'] <= 1:
        state['stage'] = 1
        save_state(state)
        log(f"Stage 1: emergence_loop ({scale['cells']}c, {scale['steps']}s)", state)

        ok, elapsed, delta = run_subprocess(
            [PYTHON, os.path.join(_SRC, 'emergence_loop.py'),
             '--cells', str(scale['cells']),
             '--steps', str(scale['steps']),
             '--max-gen', '200'],
            f'pipeline_R{round_n}_S1_{ts}.log',
            f'emergence_loop R{round_n}',
            timeout=3600,
        )
        round_laws += delta
        log(f"Stage 1 done: ok={ok}, {elapsed:.0f}s, +{delta} laws", state)

    # ── Stage 2: emergence_singularity ──
    if state['stage'] <= 2:
        state['stage'] = 2
        save_state(state)
        log(f"Stage 2: emergence_singularity ({scale['engines']} engines)", state)

        sing_cmd = [
            PYTHON, os.path.join(_SRC, 'emergence_singularity.py'),
            '--engines', str(scale['engines']),
            '--cells', str(scale['cells']),
            '--steps', str(scale['steps']),
            '--exhaustion', str(scale['exhaustion']),
        ]
        if seed_config_path:
            sing_cmd.extend(['--seed-config', seed_config_path])

        ok, elapsed, delta = run_subprocess(
            sing_cmd,
            f'pipeline_R{round_n}_S2_{ts}.log',
            f'emergence_singularity R{round_n}',
            timeout=5400,
        )
        round_laws += delta
        log(f"Stage 2 done: ok={ok}, {elapsed:.0f}s, +{delta} laws", state)

    # ── Stage 3: Law registration + sync ──
    if state['stage'] <= 3:
        state['stage'] = 3
        save_state(state)
        log("Stage 3: Law registration + sync", state)

        registered = register_singularity_laws(state)
        round_laws += registered

        # Auto-register n6 constant matches to atlas
        n6_added = register_n6_matches(state)
        if n6_added > 0:
            log(f"Registered {n6_added} n6 matches to atlas", state)

        # Generate interventions from newly registered laws
        if registered > 0:
            log(f"Generating auto-interventions from {registered} new laws...", state)
            try:
                with open(_LAWS_PATH) as f:
                    d = json.load(f)
                # Collect recently registered laws (those with "loop_pipeline auto-registered")
                new_laws = []
                for lid_str, text in d.get('laws', {}).items():
                    if 'loop_pipeline auto-registered' in text:
                        new_laws.append({'id': int(lid_str), 'text': text})
                interventions = laws_to_interventions(new_laws)
                if interventions:
                    save_auto_interventions(interventions, state)
                else:
                    log("No laws matched intervention templates", state)
            except Exception as e:
                log(f"Auto-intervention generation failed (non-fatal): {e}", state)

        # NEXUS-6 sync
        subprocess.run(
            ['bash', os.path.join(_REPO, '.shared', '..', 'nexus6', 'sync', 'sync-all.sh')],
            cwd=_REPO, capture_output=True, timeout=120,
        )
        log(f"Stage 3 done: +{registered} registered, sync complete", state)

    # ── Stage 3.2: Closed-loop verification (bidirectional bridge) ──
    cl_result = run_closed_loop_verification(state)
    if cl_result['new_discoveries'] > 0:
        round_laws += cl_result['new_discoveries']
        log(f"Closed-loop contributed +{cl_result['new_discoveries']} law changes", state)

    # ── Stage 3.6: Lens self-replication (forge -> register -> recommend -> rescan) ──
    try:
        from lens_evolution import run_lens_evolution_stage
        lens_result = run_lens_evolution_stage(state, log_fn=log)
        if lens_result.get('accepted', 0) > 0:
            log(f"Lens evolution: +{lens_result['accepted']} new lenses forged, "
                f"registry={lens_result['registry_size']}", state)
    except Exception as e:
        log(f"Lens evolution failed (non-fatal): {e}", state)
        # Fallback to legacy forge
        try:
            forge_consciousness_lenses(state)
        except Exception as e2:
            log(f"Legacy lens forge also failed (non-fatal): {e2}", state)

    # ── Stage 3.5: Integrity verification ──
    issues, auto_fixed = verify_integrity(state)

    # ── Stage 3.7: OUROBOROS evolve + events analysis + theory doc sync ──
    ouroboros_evolve(state)
    analyze_events(state)
    sync_theory_doc(state)

    # ── Stage 4: Scale up + commit ──
    state['stage'] = 4
    save_state(state)
    log("Stage 4: Scale up + commit", state)

    git_commit(state, round_n, round_laws)

    # Plateau detected: trigger blowup before scaling up
    if round_laws == 0:
        blowup_count = blowup_breakthrough(state)
        if blowup_count > 0:
            log(f"BLOWUP generated {blowup_count} seed configs for next round", state)
        # Also scale up if possible
        if state['scale_idx'] < len(SCALE_SCHEDULE) - 1:
            state['scale_idx'] += 1
            log(f"Scale up → idx={state['scale_idx']}: {SCALE_SCHEDULE[state['scale_idx']]}", state)
    elif round_laws > 20:
        # High discovery = stay at this scale
        log(f"High discovery ({round_laws} laws), staying at current scale", state)

    round_elapsed = time.time() - round_start
    state['history'].append({
        'round': round_n,
        'laws_delta': round_laws,
        'elapsed': round_elapsed,
        'scale': scale['cells'],
        'timestamp': datetime.now().isoformat(),
    })
    state['rounds_completed'] += 1
    state['total_laws_now'] = get_total_laws()
    state['stage'] = 1  # Reset for next round
    save_state(state)

    log(f"Round {round_n} complete: +{round_laws} laws, {round_elapsed:.0f}s", state)
    return round_laws


def main():
    parser = argparse.ArgumentParser(description='Loop Pipeline — Sequential Automation')
    parser.add_argument('--rounds', type=int, default=3, help='Number of rounds')
    parser.add_argument('--resume', action='store_true', help='Resume from saved state')
    parser.add_argument('--status', action='store_true', help='Show status and exit')
    parser.add_argument('--skip-to', type=int, default=0, help='Skip to stage N')
    parser.add_argument('--start-cells', type=int, default=64, help='Starting cell count')
    args = parser.parse_args()

    state = load_state() if args.resume else load_state()

    if args.status:
        print_status(state)
        return

    if args.skip_to > 0:
        state['stage'] = args.skip_to

    # Find matching scale index for start-cells
    if not args.resume:
        for i, s in enumerate(SCALE_SCHEDULE):
            if s['cells'] >= args.start_cells:
                state['scale_idx'] = i
                break
        state['started_at'] = datetime.now().isoformat()
        state['total_laws_start'] = get_total_laws()

    # PID file
    with open(_PID_PATH, 'w') as f:
        f.write(str(os.getpid()))

    print(f"""
{'='*60}
  🔄 LOOP PIPELINE — Sequential Automation
  Rounds: {args.rounds} | Start scale: {SCALE_SCHEDULE[state['scale_idx']]}
  Laws at start: {get_total_laws()}
  Resume: {args.resume}
{'='*60}
""")
    sys.stdout.flush()

    start_round = state.get('rounds_completed', 0) + 1 if args.resume else 1
    total_laws = 0

    try:
        for r in range(start_round, start_round + args.rounds):
            laws = run_round(state, r, start_round + args.rounds - 1)
            total_laws += laws
            sys.stdout.flush()
    except KeyboardInterrupt:
        log("Interrupted — state saved for --resume", state)
        save_state(state)
    finally:
        if os.path.exists(_PID_PATH):
            os.remove(_PID_PATH)

    print(f"\n{'='*60}")
    print(f"  🏁 PIPELINE COMPLETE")
    print(f"  Rounds: {state['rounds_completed']}")
    print(f"  Total new laws: {total_laws}")
    print(f"  Laws: {state.get('total_laws_start', '?')} → {get_total_laws()}")
    print(f"  Scale: {SCALE_SCHEDULE[state['scale_idx']]['cells']}c")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
