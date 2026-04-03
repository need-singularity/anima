"""Action planner for Anima Agent Tools.

Extracted from agent_tools.py for P8 compliance (Division > Integration).

ActionStep, ActionPlan: data structures for multi-step plans.
ActionPlanner: consciousness-driven planning (state -> tool selection -> plan).
"""

import re
import time
from dataclasses import dataclass, field
from typing import Optional

from tool_registry import ToolRegistry


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

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
# ActionPlanner
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
        self._growth = None  # Optional ToolGrowth instance

    def set_growth(self, growth):
        """Attach a ToolGrowth instance for self-evolving tool selection.

        When set, suggest() results override the static STATE_TOOL_MAP.
        """
        self._growth = growth

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

        # 1a) If ToolGrowth is attached, use learned rankings first
        if self._growth is not None:
            for cat in categories:
                grown_tools = self._growth.suggest(cat, max_tools)
                for t in grown_tools:
                    if t not in seen and self._registry.get(t):
                        candidates.append(t)
                        seen.add(t)
            if candidates:
                # Skip static map — growth suggestions are sufficient
                pass
            else:
                # No growth suggestions matched registry — fall through
                candidates = []
                seen = set()

        # 1b) Static STATE_TOOL_MAP fallback
        if not candidates:
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
        candidates.sort(key=lambda n: rank_order.get(n, 999))

        return candidates[:max_tools]

    def plan(self, goal: str, state: dict, context: str = "",
             allowed_tools: Optional[list] = None) -> ActionPlan:
        """Create an action plan for a goal given consciousness state.

        This is a simple rule-based planner. For complex multi-step plans,
        the LLM (ConsciousLM or Claude) should generate the plan as JSON.
        If allowed_tools is provided, only those tools are considered.
        """
        tools = self.select_tools(state, goal)
        if allowed_tools is not None:
            tools = [t for t in tools if t in allowed_tools]
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
            query = re.sub(r'^(search|find|look up|what is|tell me about)\s+', '', goal, flags=re.I)
            return {'query': query.strip() or goal}

        elif tool_name == 'web_read':
            url_match = re.search(r'https?://\S+', goal)
            if url_match:
                return {'url': url_match.group()}
            return {'url': ''}

        elif tool_name == 'code_execute':
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
