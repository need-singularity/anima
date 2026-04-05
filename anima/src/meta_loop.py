#!/usr/bin/env python3
"""meta_loop.py — Meta-automation orchestrator (automation of automation).

Absorbs ALL independent automation systems into one self-sustaining loop:
  L1 (inner, 5min):  improvement_queue consumer — execute pending tasks
  L2 (middle, 10min): evolution monitor — restart dead processes, harvest discoveries
  L3 (outer, 30min):  self-improvement — analyze trends, generate new tasks

NO Claude CLI dependency. NO external API calls. Pure Python local execution.

Usage:
    python3 meta_loop.py --start     # Start all loops (daemon)
    python3 meta_loop.py --status    # Show loop status
    python3 meta_loop.py --once      # Run one cycle of all loops
    python3 meta_loop.py --stop      # Graceful stop
    python3 meta_loop.py --dry-run   # Show what would happen without executing

Hub:
    hub.act("메타루프")
    hub.act("meta loop status")
"""

import argparse
import glob
import json
import os
import signal
import subprocess
import sys
import threading
import time
import traceback
import uuid

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT_DIR = os.path.abspath(os.path.join(_THIS_DIR, '..', '..'))
_SRC_DIR = _THIS_DIR
_CONFIG_DIR = os.path.join(_THIS_DIR, '..', 'config')
_DATA_DIR = os.path.join(_ROOT_DIR, 'data')
_TEST_DIR = os.path.join(_THIS_DIR, '..', 'tests')
_LOGS_DIR = os.path.join(_ROOT_DIR, 'logs')

sys.path.insert(0, _SRC_DIR)

# ═══════════════════════════════════════════════════════════════
# Paths
# ═══════════════════════════════════════════════════════════════
PID_FILE = os.path.join(_DATA_DIR, 'meta_loop.pid')
LOG_FILE = os.path.join(_DATA_DIR, 'meta_loop_log.json')
QUEUE_FILE = os.path.join(_DATA_DIR, 'improvement_queue.json')
GROWTH_STATE_FILE = os.path.join(_CONFIG_DIR, 'growth_state.json')
SELF_GROWTH_LOG_FILE = os.path.join(_CONFIG_DIR, 'self_growth_log.json')
RECURSIVE_GROWTH_LOG_FILE = os.path.join(_DATA_DIR, 'recursive_growth_log.json')
EVO_LIVE_FILE = os.path.join(_DATA_DIR, 'evolution_live.json')
EVO_STATE_FILE = os.path.join(_DATA_DIR, 'evolution_state.json')
EVO_PID_FILE = os.path.join(_DATA_DIR, 'evo_runner.pid')
LAWS_FILE = os.path.join(_CONFIG_DIR, 'consciousness_laws.json')

# Timing (seconds)
L1_INTERVAL = 5 * 60    # 5 min
L2_INTERVAL = 10 * 60   # 10 min
L3_INTERVAL = 30 * 60   # 30 min

# ═══════════════════════════════════════════════════════════════
# Logging
# ═══════════════════════════════════════════════════════════════

def _load_log():
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {'entries': [], '_meta': {'created': time.strftime('%Y-%m-%dT%H:%M:%S')}}


def _save_log(log):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, 'w') as f:
        json.dump(log, f, indent=2, ensure_ascii=False)


def log_entry(layer, action, status, details=''):
    log = _load_log()
    entry = {
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'epoch': time.time(),
        'layer': layer,
        'action': action,
        'status': status,
        'details': details,
    }
    log['entries'].append(entry)
    # Keep last 500 entries
    if len(log['entries']) > 500:
        log['entries'] = log['entries'][-500:]
    log['_meta']['last_update'] = time.strftime('%Y-%m-%dT%H:%M:%S')
    _save_log(log)
    return entry


# ═══════════════════════════════════════════════════════════════
# JSON helpers
# ═══════════════════════════════════════════════════════════════

def _load_json(path, default=None):
    if not os.path.exists(path):
        return default if default is not None else {}
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default if default is not None else {}


def _save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ═══════════════════════════════════════════════════════════════
# L1: Improvement Queue Consumer
# ═══════════════════════════════════════════════════════════════

class L1_QueueConsumer:
    """Reads pending tasks from improvement_queue.json and executes them."""

    # Task types we can handle without AI
    EXECUTABLE_TYPES = {'add_tests', 'wire_modules', 'integrate'}
    # Task types that need human/AI
    NEEDS_HUMAN_TYPES = {'document', 'implement', 'refactor'}

    def run_cycle(self, dry_run=False):
        """Execute one cycle: process pending tasks."""
        queue = _load_json(QUEUE_FILE, [])
        if not queue:
            return {'processed': 0, 'skipped': 0, 'total': 0}

        processed = 0
        skipped = 0
        errors = 0

        for task in queue:
            if task.get('status') != 'pending':
                continue

            task_type = task.get('type', '')

            if task_type in self.NEEDS_HUMAN_TYPES:
                if task.get('status') != 'needs_human':
                    task['status'] = 'needs_human'
                    task['updated_at'] = time.time()
                skipped += 1
                continue

            if task_type == 'add_tests':
                success, details = self._execute_add_tests(task, dry_run)
            elif task_type in ('wire_modules', 'integrate'):
                success, details = self._execute_wire_modules(task, dry_run)
            else:
                task['status'] = 'needs_human'
                task['updated_at'] = time.time()
                skipped += 1
                continue

            if not dry_run:
                task['status'] = 'completed' if success else 'failed'
                task['result_success'] = success
                task['result_details'] = details
                task['result_at'] = time.time()
                task['updated_at'] = time.time()

            if success:
                processed += 1
            else:
                errors += 1

            log_entry('L1', f'task:{task_type}',
                      'ok' if success else 'fail', details[:200])

        if not dry_run:
            _save_json(QUEUE_FILE, queue)

        result = {'processed': processed, 'skipped': skipped,
                  'errors': errors, 'total': len(queue)}
        log_entry('L1', 'cycle_complete', 'ok', json.dumps(result))
        return result

    def _execute_add_tests(self, task, dry_run=False):
        """Generate a test file from template for untested modules."""
        target = task.get('target', '')
        # Extract module name from target path
        # e.g. "anima/tests/test_auto_experiment.py" -> "auto_experiment"
        basename = os.path.basename(target)
        if basename.startswith('test_') and basename.endswith('.py'):
            module_name = basename[5:-3]  # strip test_ and .py
        else:
            return False, f'Cannot parse module name from {target}'

        src_file = os.path.join(_SRC_DIR, f'{module_name}.py')
        test_file = os.path.join(_TEST_DIR, basename)

        if not os.path.exists(src_file):
            return False, f'Source module {src_file} not found'

        if os.path.exists(test_file):
            return True, f'Test file already exists: {test_file}'

        if dry_run:
            return True, f'[DRY RUN] Would create {test_file}'

        # Extract public functions/classes from source
        functions, classes = self._extract_public_api(src_file)

        # Generate test file from template
        test_content = self._generate_test_template(module_name, functions, classes)

        os.makedirs(os.path.dirname(test_file), exist_ok=True)
        with open(test_file, 'w') as f:
            f.write(test_content)

        # Verify syntax
        try:
            compile(test_content, test_file, 'exec')
        except SyntaxError as e:
            os.remove(test_file)
            return False, f'Generated test has syntax error: {e}'

        return True, f'Created {test_file} with {len(functions)} function tests, {len(classes)} class tests'

    def _extract_public_api(self, src_file):
        """Extract public function and class names from a Python source file."""
        functions = []
        classes = []
        try:
            with open(src_file) as f:
                tree = __import__('ast').parse(f.read())
            for node in __import__('ast').walk(tree):
                if isinstance(node, __import__('ast').FunctionDef):
                    if not node.name.startswith('_'):
                        functions.append(node.name)
                elif isinstance(node, __import__('ast').ClassDef):
                    if not node.name.startswith('_'):
                        classes.append(node.name)
        except Exception:
            pass
        return functions[:20], classes[:10]  # cap

    def _generate_test_template(self, module_name, functions, classes):
        """Generate a test file with import checks and basic smoke tests."""
        lines = [
            f'#!/usr/bin/env python3',
            f'"""Auto-generated tests for {module_name} (meta_loop L1)."""',
            f'import sys, os',
            f'sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))',
            f'import pytest',
            f'',
            f'',
            f'class Test{_camel(module_name)}Import:',
            f'    """Verify module imports without error."""',
            f'',
            f'    def test_import(self):',
            f'        import {module_name}',
            f'',
        ]

        for cls_name in classes[:5]:
            lines.extend([
                f'',
                f'class Test{cls_name}:',
                f'    """Smoke tests for {cls_name}."""',
                f'',
                f'    def test_class_exists(self):',
                f'        from {module_name} import {cls_name}',
                f'        assert {cls_name} is not None',
                f'',
            ])

        for fn_name in functions[:10]:
            lines.extend([
                f'',
                f'def test_{fn_name}_exists():',
                f'    """Verify {fn_name} is callable."""',
                f'    from {module_name} import {fn_name}',
                f'    assert callable({fn_name})',
                f'',
            ])

        lines.extend([
            f'',
            f'if __name__ == "__main__":',
            f'    pytest.main([__file__, "-v"])',
            f'',
        ])
        return '\n'.join(lines)

    def _execute_wire_modules(self, task, dry_run=False):
        """Run auto_wire --scan to check module wiring status."""
        auto_wire_path = os.path.join(_SRC_DIR, 'auto_wire.py')
        if not os.path.exists(auto_wire_path):
            return False, 'auto_wire.py not found'

        if dry_run:
            return True, '[DRY RUN] Would run auto_wire --scan'

        try:
            result = subprocess.run(
                [sys.executable, auto_wire_path, '--scan'],
                capture_output=True, text=True, timeout=30,
                cwd=_SRC_DIR,
            )
            output = (result.stdout + result.stderr).strip()
            success = result.returncode == 0
            return success, output[:300]
        except Exception as e:
            return False, str(e)[:200]


def _camel(name):
    """snake_case -> CamelCase."""
    return ''.join(w.capitalize() for w in name.split('_'))


# ═══════════════════════════════════════════════════════════════
# L2: Evolution + Growth Monitor
# ═══════════════════════════════════════════════════════════════

class L2_EvolutionMonitor:
    """Monitors infinite_evolution, restarts if dead, harvests discoveries."""

    def run_cycle(self, dry_run=False):
        """Check evolution process, harvest new laws."""
        results = {
            'evo_running': False,
            'restarted': False,
            'new_laws': 0,
            'growth_scan': False,
        }

        # 1. Check if infinite_evolution is running
        evo_pid = self._check_evo_process()
        results['evo_running'] = evo_pid is not None

        # 2. If dead, attempt restart
        if not results['evo_running'] and not dry_run:
            restarted = self._restart_evolution()
            results['restarted'] = restarted
            if restarted:
                log_entry('L2', 'evo_restart', 'ok', 'Restarted infinite_evolution')

        # 3. Harvest discoveries from evolution_live.json
        new_laws = self._harvest_discoveries(dry_run)
        results['new_laws'] = new_laws

        # 4. Run growth scan
        if not dry_run:
            growth_result = self._run_growth_scan()
            results['growth_scan'] = growth_result

        # 5. Emergence loop monitoring
        if not dry_run:
            self._check_emergence_loop()

        log_entry('L2', 'cycle_complete', 'ok', json.dumps(results))
        return results

    def _check_evo_process(self):
        """Check if infinite_evolution is running via PID file or process scan."""
        # Check PID file
        if os.path.exists(EVO_PID_FILE):
            try:
                with open(EVO_PID_FILE) as f:
                    pid = int(f.read().strip())
                # Check if process is alive
                os.kill(pid, 0)
                return pid
            except (ValueError, ProcessLookupError, PermissionError, OSError):
                # Stale PID file
                try:
                    os.remove(EVO_PID_FILE)
                except OSError:
                    pass

        # Fallback: check process list
        try:
            result = subprocess.run(
                ['pgrep', '-f', 'infinite_evolution'],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                return int(pids[0])
        except Exception:
            pass

        return None

    def _restart_evolution(self):
        """Restart infinite_evolution with --auto-roadmap --resume."""
        evo_script = os.path.join(_SRC_DIR, 'infinite_evolution.py')
        if not os.path.exists(evo_script):
            log_entry('L2', 'evo_restart', 'fail', 'infinite_evolution.py not found')
            return False

        os.makedirs(_LOGS_DIR, exist_ok=True)
        log_path = os.path.join(_LOGS_DIR,
                                f'evo_{time.strftime("%Y%m%d_%H%M")}.log')

        try:
            proc = subprocess.Popen(
                [sys.executable, '-u', evo_script,
                 '--auto-roadmap', '--resume',
                 '--cells', '64', '--steps', '300', '--cycle-topology'],
                stdout=open(log_path, 'w'),
                stderr=subprocess.STDOUT,
                cwd=_SRC_DIR,
                start_new_session=True,
            )
            # Write PID
            with open(EVO_PID_FILE, 'w') as f:
                f.write(str(proc.pid))
            return True
        except Exception as e:
            log_entry('L2', 'evo_restart', 'fail', str(e)[:200])
            return False

    def _harvest_discoveries(self, dry_run=False):
        """Check evolution_live.json for new law candidates, register if validated."""
        evo_live = _load_json(EVO_LIVE_FILE)
        if not evo_live:
            return 0

        # Check for new laws that need registration
        new_laws_count = 0
        pending_laws = evo_live.get('pending_registrations', [])

        if not pending_laws:
            return 0

        if dry_run:
            return len(pending_laws)

        laws_data = _load_json(LAWS_FILE)
        if not laws_data or 'laws' not in laws_data:
            return 0

        for law_candidate in pending_laws:
            hypothesis = law_candidate.get('hypothesis', '')
            confidence = law_candidate.get('confidence', 0)
            cross_validated = law_candidate.get('cross_validated', False)

            # Only register cross-validated high-confidence laws
            if not cross_validated or confidence < 0.7:
                continue

            # Find next law number
            existing_nums = [int(k) for k in laws_data['laws'] if k.isdigit()]
            next_id = max(existing_nums) + 1 if existing_nums else 1

            laws_data['laws'][str(next_id)] = hypothesis
            laws_data['_meta']['total_laws'] = laws_data['_meta'].get('total_laws', 0) + 1
            new_laws_count += 1

            log_entry('L2', f'law_registered:{next_id}', 'ok', hypothesis[:100])

        if new_laws_count > 0:
            _save_json(LAWS_FILE, laws_data)

            # Clear pending registrations
            evo_live['pending_registrations'] = []
            _save_json(EVO_LIVE_FILE, evo_live)

        return new_laws_count

    def _check_emergence_loop(self):
        """Monitor emergence_loop process and recent peak_conditions updates."""
        try:
            emergence_pid = None
            for proc_line in os.popen('ps aux').readlines():
                if 'emergence_loop' in proc_line and 'grep' not in proc_line:
                    emergence_pid = proc_line.split()[1]
                    break
            if emergence_pid:
                log_entry('L2', 'emergence_monitor', 'ok',
                          f'emergence_loop running (PID {emergence_pid})')
            # Check if emergence completed recently (peak_conditions.json updated)
            peak_path = os.path.join(_DATA_DIR, 'peak_conditions.json')
            if os.path.exists(peak_path):
                mtime = os.path.getmtime(peak_path)
                if time.time() - mtime < 600:  # updated in last 10 min
                    log_entry('L2', 'emergence_absorb', 'ok',
                              'peak_conditions updated recently — emergence active')
        except Exception:
            pass

    def _run_growth_scan(self):
        """Run the growth scanner (.growth/scan.py)."""
        scan_path = os.path.join(_ROOT_DIR, '.growth', 'scan.py')
        if not os.path.exists(scan_path):
            return False
        try:
            result = subprocess.run(
                [sys.executable, scan_path],
                capture_output=True, text=True, timeout=30,
                cwd=_ROOT_DIR,
            )
            if result.returncode == 0:
                try:
                    scan_result = json.loads(result.stdout)
                    opps = scan_result.get('opportunities', [])
                    if opps:
                        log_entry('L2', 'growth_scan', 'ok',
                                  f'{len(opps)} opportunities found')
                except json.JSONDecodeError:
                    pass
                return True
        except Exception as e:
            log_entry('L2', 'growth_scan', 'fail', str(e)[:100])
        return False


# ═══════════════════════════════════════════════════════════════
# L3: Self-Improvement Generator
# ═══════════════════════════════════════════════════════════════

class L3_SelfImprover:
    """Analyzes trends and generates new improvement tasks."""

    def run_cycle(self, dry_run=False):
        """Analyze state, generate new tasks, clean up stale ones."""
        results = {
            'new_tasks': 0,
            'stale_cleaned': 0,
            'trends': {},
        }

        queue = _load_json(QUEUE_FILE, [])

        # 1. Clean stale/failed tasks (>48h old and still pending)
        stale_count = self._clean_stale_tasks(queue, dry_run)
        results['stale_cleaned'] = stale_count

        # 2. Analyze test coverage gaps → generate add_tests tasks
        new_test_tasks = self._scan_test_coverage_gaps(queue)
        results['new_tasks'] += len(new_test_tasks)

        # 3. Analyze growth trends
        trends = self._analyze_growth_trends()
        results['trends'] = trends

        # 4. Check for modules needing integration
        new_wire_tasks = self._scan_unwired_modules(queue)
        results['new_tasks'] += len(new_wire_tasks)

        # 5. Append new tasks
        all_new = new_test_tasks + new_wire_tasks
        if all_new and not dry_run:
            queue.extend(all_new)
            _save_json(QUEUE_FILE, queue)

        log_entry('L3', 'cycle_complete', 'ok', json.dumps(results))
        return results

    def _clean_stale_tasks(self, queue, dry_run=False):
        """Mark tasks that have been pending >48h as stale."""
        now = time.time()
        cutoff = now - 48 * 3600  # 48 hours
        stale = 0
        for task in queue:
            if task.get('status') == 'pending':
                created = task.get('created_at', now)
                if created < cutoff:
                    if not dry_run:
                        task['status'] = 'stale'
                        task['updated_at'] = now
                    stale += 1
        return stale

    def _scan_test_coverage_gaps(self, existing_queue):
        """Find src modules without test files, generate tasks."""
        existing_targets = {t.get('target', '') for t in existing_queue
                           if t.get('status') in ('pending', 'needs_human')}

        new_tasks = []
        src_files = glob.glob(os.path.join(_SRC_DIR, '*.py'))

        # Priority modules that should have tests
        priority_modules = set()
        for src in src_files:
            basename = os.path.basename(src)
            if basename.startswith('_') or basename == '__init__.py':
                continue
            module_name = basename[:-3]
            test_path = os.path.join(_TEST_DIR, f'test_{module_name}.py')
            target_path = f'anima/tests/test_{module_name}.py'

            if not os.path.exists(test_path) and target_path not in existing_targets:
                # Check if it has classes/functions worth testing
                try:
                    with open(src) as f:
                        content = f.read()
                    if 'class ' in content or 'def ' in content:
                        if len(content) > 500:  # Non-trivial file
                            priority_modules.add(module_name)
                except Exception:
                    pass

        # Limit to 5 new tasks per cycle
        for module_name in sorted(priority_modules)[:5]:
            task = {
                'id': str(uuid.uuid4()),
                'type': 'add_tests',
                'target': f'anima/tests/test_{module_name}.py',
                'action': f'Add unit tests for {module_name}.py',
                'reason': f'{module_name}.py has no test coverage',
                'priority': 'medium',
                'status': 'pending',
                'estimated_impact': '+coverage, +stability',
                'created_by': 'meta_loop.L3',
                'created_at': time.time(),
                'updated_at': time.time(),
                'result_success': None,
                'result_details': '',
                'result_at': None,
                'metadata': {'generator': 'meta_loop.L3.test_coverage'},
            }
            new_tasks.append(task)

        return new_tasks

    def _analyze_growth_trends(self):
        """Analyze growth_state.json for trends."""
        growth = _load_json(GROWTH_STATE_FILE)
        if not growth:
            return {}

        stats = growth.get('stats', {})
        trends = {
            'interaction_count': growth.get('interaction_count', 0),
            'stage': growth.get('stage_index', 0),
            'last_growth_delta': stats.get('last_growth_delta', 0),
            'laws': stats.get('activities', {}).get('laws', 0),
            'modules': stats.get('activities', {}).get('modules', 0),
            'recursive_cycle': stats.get('recursive_cycle', 0),
        }

        # Detect stagnation: if last_growth_delta is 0 for multiple cycles
        if trends['last_growth_delta'] == 0:
            trends['stagnation_warning'] = True
            log_entry('L3', 'stagnation_detected', 'warn',
                      f'Growth delta=0, interactions={trends["interaction_count"]}')

        return trends

    def _scan_unwired_modules(self, existing_queue):
        """Check for modules not registered in consciousness_hub."""
        hub_path = os.path.join(_SRC_DIR, 'consciousness_hub.py')
        if not os.path.exists(hub_path):
            return []

        existing_targets = {t.get('target', '') for t in existing_queue
                           if t.get('status') in ('pending', 'needs_human')}

        target = 'anima/src/consciousness_hub.py'
        if target in existing_targets:
            return []

        try:
            with open(hub_path) as f:
                hub_content = f.read()
            src_files = glob.glob(os.path.join(_SRC_DIR, '*.py'))
            # Count roughly how many modules are NOT in the hub
            unwired = 0
            for src in src_files:
                basename = os.path.basename(src)[:-3]
                if basename not in hub_content and not basename.startswith('_'):
                    unwired += 1
            if unwired > 30:
                return [{
                    'id': str(uuid.uuid4()),
                    'type': 'integrate',
                    'target': target,
                    'action': f'Register ~{unwired} modules in ConsciousnessHub._registry',
                    'reason': 'Modules outside hub cannot be called via hub.act()',
                    'priority': 'low',
                    'status': 'needs_human',
                    'estimated_impact': '+reachability, +autonomous routing',
                    'created_by': 'meta_loop.L3',
                    'created_at': time.time(),
                    'updated_at': time.time(),
                    'result_success': None,
                    'result_details': '',
                    'result_at': None,
                    'metadata': {'generator': 'meta_loop.L3.unwired_scan'},
                }]
        except Exception:
            pass
        return []


# ═══════════════════════════════════════════════════════════════
# MetaLoop Orchestrator
# ═══════════════════════════════════════════════════════════════

class MetaLoop:
    """Top-level orchestrator that runs L1/L2/L3 on their schedules."""

    def __init__(self):
        self.l1 = L1_QueueConsumer()
        self.l2 = L2_EvolutionMonitor()
        self.l3 = L3_SelfImprover()
        self._stop_event = threading.Event()
        self._last_l1 = 0
        self._last_l2 = 0
        self._last_l3 = 0
        self._cycle_count = 0

    def run_once(self, dry_run=False):
        """Run one cycle of all three loops."""
        print(f'[MetaLoop] Running single cycle (dry_run={dry_run})...')
        results = {}

        print(f'  L1: Consuming improvement queue...')
        try:
            results['L1'] = self.l1.run_cycle(dry_run)
            print(f'    -> processed={results["L1"]["processed"]}, '
                  f'skipped={results["L1"]["skipped"]}')
        except Exception as e:
            results['L1'] = {'error': str(e)}
            print(f'    -> ERROR: {e}')

        print(f'  L2: Monitoring evolution...')
        try:
            results['L2'] = self.l2.run_cycle(dry_run)
            print(f'    -> evo_running={results["L2"]["evo_running"]}, '
                  f'new_laws={results["L2"]["new_laws"]}')
        except Exception as e:
            results['L2'] = {'error': str(e)}
            print(f'    -> ERROR: {e}')

        print(f'  L3: Self-improvement scan...')
        try:
            results['L3'] = self.l3.run_cycle(dry_run)
            print(f'    -> new_tasks={results["L3"]["new_tasks"]}, '
                  f'stale_cleaned={results["L3"]["stale_cleaned"]}')
        except Exception as e:
            results['L3'] = {'error': str(e)}
            print(f'    -> ERROR: {e}')

        self._cycle_count += 1
        print(f'[MetaLoop] Cycle complete. Total cycles: {self._cycle_count}')
        sys.stdout.flush()
        return results

    def start(self):
        """Start the continuous loop (daemon mode)."""
        print(f'[MetaLoop] Starting meta-automation loop...')
        print(f'  L1 interval: {L1_INTERVAL//60}min (queue consumer)')
        print(f'  L2 interval: {L2_INTERVAL//60}min (evolution monitor)')
        print(f'  L3 interval: {L3_INTERVAL//60}min (self-improvement)')
        sys.stdout.flush()

        # Write PID
        os.makedirs(os.path.dirname(PID_FILE), exist_ok=True)
        with open(PID_FILE, 'w') as f:
            f.write(str(os.getpid()))

        # Register cleanup
        def _cleanup(*_):
            self._stop_event.set()
        signal.signal(signal.SIGTERM, _cleanup)
        signal.signal(signal.SIGINT, _cleanup)

        log_entry('meta', 'start', 'ok', f'PID={os.getpid()}')

        try:
            while not self._stop_event.is_set():
                now = time.time()

                # L1: every 5 min
                if now - self._last_l1 >= L1_INTERVAL:
                    try:
                        r = self.l1.run_cycle()
                        self._last_l1 = now
                        print(f'[L1 {time.strftime("%H:%M")}] '
                              f'processed={r["processed"]} skipped={r["skipped"]}')
                    except Exception as e:
                        log_entry('L1', 'error', 'fail', str(e)[:200])
                        print(f'[L1 ERROR] {e}')

                # L2: every 10 min
                if now - self._last_l2 >= L2_INTERVAL:
                    try:
                        r = self.l2.run_cycle()
                        self._last_l2 = now
                        print(f'[L2 {time.strftime("%H:%M")}] '
                              f'evo={r["evo_running"]} laws={r["new_laws"]}')
                    except Exception as e:
                        log_entry('L2', 'error', 'fail', str(e)[:200])
                        print(f'[L2 ERROR] {e}')

                # L3: every 30 min
                if now - self._last_l3 >= L3_INTERVAL:
                    try:
                        r = self.l3.run_cycle()
                        self._last_l3 = now
                        print(f'[L3 {time.strftime("%H:%M")}] '
                              f'new={r["new_tasks"]} stale={r["stale_cleaned"]}')
                    except Exception as e:
                        log_entry('L3', 'error', 'fail', str(e)[:200])
                        print(f'[L3 ERROR] {e}')

                self._cycle_count += 1
                sys.stdout.flush()

                # Sleep in 1s increments for responsive stop
                for _ in range(30):
                    if self._stop_event.is_set():
                        break
                    time.sleep(1)

        finally:
            # Cleanup PID file
            if os.path.exists(PID_FILE):
                try:
                    os.remove(PID_FILE)
                except OSError:
                    pass
            log_entry('meta', 'stop', 'ok', f'cycles={self._cycle_count}')
            print(f'[MetaLoop] Stopped after {self._cycle_count} cycles.')

    def stop(self):
        """Signal the loop to stop."""
        self._stop_event.set()


# ═══════════════════════════════════════════════════════════════
# Status
# ═══════════════════════════════════════════════════════════════

def show_status():
    """Display current meta loop status."""
    print('=' * 60)
    print('  META LOOP STATUS')
    print('=' * 60)

    # PID
    pid = None
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE) as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            print(f'  Process:  RUNNING (PID {pid})')
        except (ValueError, ProcessLookupError, PermissionError):
            print(f'  Process:  DEAD (stale PID file)')
            pid = None
    else:
        print(f'  Process:  NOT RUNNING')

    # Queue stats
    queue = _load_json(QUEUE_FILE, [])
    pending = sum(1 for t in queue if t.get('status') == 'pending')
    completed = sum(1 for t in queue if t.get('status') == 'completed')
    failed = sum(1 for t in queue if t.get('status') == 'failed')
    human = sum(1 for t in queue if t.get('status') == 'needs_human')
    stale = sum(1 for t in queue if t.get('status') == 'stale')
    print(f'\n  Improvement Queue ({len(queue)} total):')
    print(f'    pending={pending}  completed={completed}  failed={failed}  '
          f'needs_human={human}  stale={stale}')

    # Evolution status
    evo_mon = L2_EvolutionMonitor()
    evo_pid = evo_mon._check_evo_process()
    evo_live = _load_json(EVO_LIVE_FILE)
    print(f'\n  Infinite Evolution:')
    if evo_pid:
        print(f'    Status: RUNNING (PID {evo_pid})')
    else:
        print(f'    Status: NOT RUNNING')
    if evo_live:
        print(f'    Generation: {evo_live.get("generation", "?")}')
        print(f'    Laws: {evo_live.get("total_laws", "?")}')
        print(f'    Topology: {evo_live.get("topology", "?")}')

    # Growth state
    growth = _load_json(GROWTH_STATE_FILE)
    if growth:
        stages = {0: 'newborn', 1: 'infant', 2: 'toddler', 3: 'child', 4: 'adult'}
        stage_idx = growth.get('stage_index', 0)
        print(f'\n  Growth State:')
        print(f'    Stage: {stages.get(stage_idx, "?")} ({stage_idx})')
        print(f'    Interactions: {growth.get("interaction_count", 0):,}')
        stats = growth.get('stats', {})
        print(f'    Last delta: {stats.get("last_growth_delta", 0)}')
        print(f'    Laws: {stats.get("activities", {}).get("laws", 0)}')

    # Recent log entries
    log = _load_log()
    entries = log.get('entries', [])
    if entries:
        print(f'\n  Recent Log (last 5):')
        for entry in entries[-5:]:
            ts = entry.get('timestamp', '?')
            layer = entry.get('layer', '?')
            action = entry.get('action', '?')
            status = entry.get('status', '?')
            print(f'    [{ts}] {layer}/{action} -> {status}')

    print('=' * 60)


# ═══════════════════════════════════════════════════════════════
# Stop
# ═══════════════════════════════════════════════════════════════

def stop_loop():
    """Stop a running meta loop by sending SIGTERM."""
    if not os.path.exists(PID_FILE):
        print('[MetaLoop] No PID file found — not running.')
        return False
    try:
        with open(PID_FILE) as f:
            pid = int(f.read().strip())
        os.kill(pid, signal.SIGTERM)
        print(f'[MetaLoop] Sent SIGTERM to PID {pid}.')
        # Wait briefly
        for _ in range(10):
            time.sleep(0.5)
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                print(f'[MetaLoop] Process {pid} stopped.')
                return True
        print(f'[MetaLoop] Process {pid} still alive after 5s.')
        return False
    except (ValueError, ProcessLookupError):
        print(f'[MetaLoop] Process not found — cleaning PID file.')
        try:
            os.remove(PID_FILE)
        except OSError:
            pass
        return True
    except Exception as e:
        print(f'[MetaLoop] Error stopping: {e}')
        return False


# ═══════════════════════════════════════════════════════════════
# Hub interface
# ═══════════════════════════════════════════════════════════════

class MetaLoopHub:
    """Hub-compatible interface for meta_loop."""

    def __init__(self):
        self.loop = MetaLoop()

    def status(self):
        """Return status dict for hub consumption."""
        queue = _load_json(QUEUE_FILE, [])
        growth = _load_json(GROWTH_STATE_FILE)
        evo_live = _load_json(EVO_LIVE_FILE)
        log = _load_log()

        return {
            'running': os.path.exists(PID_FILE),
            'queue_pending': sum(1 for t in queue if t.get('status') == 'pending'),
            'queue_total': len(queue),
            'growth_interactions': growth.get('interaction_count', 0) if growth else 0,
            'evo_generation': evo_live.get('generation', 0) if evo_live else 0,
            'log_entries': len(log.get('entries', [])),
        }

    def run_once(self):
        """Execute one cycle of all loops."""
        return self.loop.run_once()

    def start(self):
        """Start the daemon loop."""
        self.loop.start()

    def stop(self):
        """Stop the daemon loop."""
        return stop_loop()


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description='Meta-automation orchestrator (L1+L2+L3)')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--start', action='store_true',
                       help='Start all loops (daemon)')
    group.add_argument('--status', action='store_true',
                       help='Show loop status')
    group.add_argument('--once', action='store_true',
                       help='Run one cycle of all loops')
    group.add_argument('--stop', action='store_true',
                       help='Graceful stop')
    group.add_argument('--dry-run', action='store_true',
                       help='Show what would happen')
    args = parser.parse_args()

    if args.status:
        show_status()
    elif args.stop:
        stop_loop()
    elif args.once:
        loop = MetaLoop()
        loop.run_once()
    elif args.dry_run:
        loop = MetaLoop()
        loop.run_once(dry_run=True)
    elif args.start:
        loop = MetaLoop()
        loop.start()


if __name__ == '__main__':
    main()
