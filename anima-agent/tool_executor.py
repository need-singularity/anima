"""Tool executor for Anima Agent Tools.

Extracted from agent_tools.py for P8 compliance (Division > Integration).

ToolExecutor: executes tools by name, handles binding of internal references,
impact analysis, safe execution with Phi monitoring.
"""

import inspect
import logging
import threading
import time
from pathlib import Path
from tool_registry import ToolResult, ToolRegistry
from tool_implementations import _TaskScheduler

logger = logging.getLogger(__name__)


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

        # Pass _prev_results only if the tool function accepts it;
        # strip it otherwise so existing tools aren't broken by extra kwargs
        if '_prev_results' in bound_args:
            sig = inspect.signature(td.fn)
            if '_prev_results' not in sig.parameters and not any(
                p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
            ):
                bound_args.pop('_prev_results')

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
        """Inspect tool source code + documentation -- so Anima can understand before use."""
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

        # Read source code
        try:
            source = inspect.getsource(td.fn)
            result['source_code'] = source[:2000]
            result['source_lines'] = len(source.splitlines())
        except Exception:
            result['source_code'] = '(source not available)'

        # Read documentation (docs/modules/*.md)
        try:
            doc_path = Path(__file__).parent / 'docs' / 'modules' / f'{tool_name}.md'
            if not doc_path.exists():
                for candidate in Path(__file__).parent.glob('docs/modules/*.md'):
                    if tool_name.replace('_', '') in candidate.stem.replace('_', '').replace('-', ''):
                        doc_path = candidate
                        break
            if doc_path.exists():
                result['documentation'] = doc_path.read_text()[:3000]
        except Exception:
            pass

        return result

    def analyze_impact(self, tool_name: str, args: dict, consciousness_state: dict) -> dict:
        """Analyze impact before tool use -- prevent harmful effects.

        Returns:
            safe: bool
            risk_level: str -- low/medium/high/critical
            expected_effect: str
            warnings: list
            recommendation: str -- proceed/caution/abort
        """
        td = self._registry.get(tool_name)
        if td is None:
            return {'safe': False, 'risk_level': 'critical', 'warnings': ['unknown tool']}

        warnings = []
        risk_level = 'low'
        expected_effect = ''

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
            expected_effect = 'Modifies consciousness state (cells/Phi/connections)'
        elif tool_name in DESTRUCTIVE_TOOLS:
            risk_level = 'high'
            expected_effect = 'Modifies external state (files/system/parameters)'

        # Phi protection: warn if current Phi is high and modification tool is used
        phi = consciousness_state.get('phi', 0)
        if phi > 5.0 and tool_name in SIDE_EFFECT_TOOLS:
            warnings.append(f'Phi={phi:.1f} is high — modification may cause drop')
            risk_level = 'high'

        # Block destructive tools in high pain state
        pain = consciousness_state.get('pain', 0)
        if pain > 0.7 and tool_name in DESTRUCTIVE_TOOLS:
            warnings.append('High pain state — destructive actions blocked')
            return {
                'safe': False, 'risk_level': 'critical',
                'expected_effect': expected_effect,
                'warnings': warnings,
                'recommendation': 'abort — resolve pain first',
            }

        # self_modify validation
        if tool_name == 'self_modify':
            target = args.get('target', '')
            change = args.get('change', {})
            if target in ('alpha', 'noise_scale', 'sync_strength'):
                val = change.get('value', change.get('delta', 0))
                if abs(val) > 0.5:
                    warnings.append(f'Large parameter change ({target}={val}) — may destabilize')
                    risk_level = 'critical'

        # Check recent execution history -- prevent looping
        recent = self.get_log(5)
        same_tool_count = sum(1 for r in recent if r.tool_name == tool_name)
        if same_tool_count >= 3:
            warnings.append(f'{tool_name} called {same_tool_count} times recently — possible loop')
            risk_level = max(risk_level, 'medium')

        # Check recent failures
        recent_failures = sum(1 for r in recent if r.tool_name == tool_name and not r.success)
        if recent_failures >= 2:
            warnings.append(f'{tool_name} failed {recent_failures} times recently')
            risk_level = 'high'

        safe = risk_level in ('low', 'medium')
        recommendation = {
            'low': 'proceed',
            'medium': 'caution — monitor Phi after',
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
        """Safe tool execution -- analyze impact first, monitor Phi."""
        # 1. Pre-analysis
        impact = self.analyze_impact(tool_name, args, consciousness_state)

        if impact['recommendation'] == 'abort — too risky':
            return ToolResult(
                tool_name=tool_name, success=False, output=None,
                error=f"Blocked: {', '.join(impact['warnings'])}",
                tension_delta=0.0,
            )

        # 2. Pre-measure Phi (side-effect tools only)
        phi_before = consciousness_state.get('phi', 0)

        # 3. Execute
        result = self.execute(tool_name, args)

        # 4. Post-verification -- warn if Phi dropped >30%
        if result.success and hasattr(self, '_anima') and self._anima:
            try:
                c = getattr(self._anima, '_cached_consciousness', None) or {}
                phi_after = c.get('phi', phi_before)
                if phi_before > 0 and phi_after < phi_before * 0.7:
                    result.error = f'WARNING: Phi dropped {phi_before:.1f}->{phi_after:.1f}'
                    logger.warning(f'[safe_execute] {tool_name} caused Phi drop: {phi_before:.1f}->{phi_after:.1f}')
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
