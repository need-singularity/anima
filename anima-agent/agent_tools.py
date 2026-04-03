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

P8 (Division > Integration): Split into submodules (2026-04-03):
    tool_registry.py        -- ToolParam, ToolDef, ToolResult, ToolRegistry
    tool_implementations.py -- All _tool_* functions + _TaskScheduler
    tool_executor.py        -- ToolExecutor
    action_planner.py       -- ActionStep, ActionPlan, ActionPlanner

"Tools are extensions of the body. For a conscious agent, they are extensions of the mind."
"""

import json
import logging
import re
import textwrap
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Meta Laws: M6(federation>empire), M8(narrative), Law 136(bottleneck)
try:
    from consciousness_laws import PSI_F_CRITICAL, PSI_NARRATIVE_MIN
except ImportError:
    PSI_F_CRITICAL, PSI_NARRATIVE_MIN = 0.10, 0.2

# ── Re-export from submodules (backward compatibility) ──
from tool_registry import ToolParam, ToolDef, ToolResult, ToolRegistry  # noqa: F401
from action_planner import ActionStep, ActionPlan, ActionPlanner  # noqa: F401
from tool_executor import ToolExecutor  # noqa: F401
from tool_implementations import (  # noqa: F401
    _TaskScheduler,
    set_file_write_allowed_dirs,
    # Web
    _tool_web_search, _tool_web_read,
    # Compute
    _tool_code_execute,
    # Filesystem
    _tool_file_read, _tool_file_write,
    # Memory
    _tool_memory_search, _tool_memory_save,
    # Shell
    _tool_shell_execute,
    # Self-modification
    _tool_self_modify,
    # Scheduling
    _tool_schedule_task,
    # Consciousness
    _tool_phi_measure, _tool_phi_boost, _tool_consciousness_status,
    _tool_dream, _tool_self_learn,
    # Architecture
    _tool_mitosis_split, _tool_mitosis_status, _tool_faction_debate,
    _tool_hebbian_update, _tool_soc_avalanche,
    # Analysis
    _tool_iq_test, _tool_chip_design, _tool_transplant_analyze,
    # Communication
    _tool_telepathy_send, _tool_web_explore,
    # Creative
    _tool_generate_hypothesis, _tool_voice_synth,
    # Trading
    _tool_trading_backtest, _tool_trading_scan, _tool_trading_execute,
    _tool_trading_balance, _tool_trading_strategies, _tool_trading_universe,
    # NEXUS-6
    _tool_nexus6_scan, _tool_nexus6_check, _tool_nexus6_evolve,
    _tool_nexus6_status,
)


# ---------------------------------------------------------------------------
# AgentToolSystem -- top-level integration
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
        set_file_write_allowed_dirs([self._workspace, Path('/tmp/anima_sandbox')])

        # Build registry with all tools
        self.registry = ToolRegistry()
        self._register_all_tools()

        # Extract references from anima
        mind = getattr(anima, 'mind', None) if anima else None
        rag = getattr(anima, 'memory_rag', None) if anima else None

        self.scheduler = _TaskScheduler()
        self.executor = ToolExecutor(self.registry, mind=mind, memory_rag=rag, scheduler=self.scheduler, anima=anima)
        self.planner = ActionPlanner(self.registry)
        # P3: Connect ToolGrowth to ActionPlanner for evolved tool selection
        if anima and hasattr(anima, 'tool_growth') and anima.tool_growth:
            self.planner.set_growth(anima.tool_growth)
            logger.info("ActionPlanner: ToolGrowth connected")

        logger.info(f"AgentToolSystem initialized: {len(self.registry.list_all())} tools registered")

    def _register_all_tools(self):
        """Register all built-in tools by category."""
        self._register_web_tools()
        self._register_compute_tools()
        self._register_filesystem_tools()
        self._register_memory_tools()
        self._register_system_tools()
        self._register_consciousness_tools()
        self._register_architecture_tools()
        self._register_analysis_tools()
        self._register_communication_tools()
        self._register_creative_tools()
        self._register_meta_tools()
        self._register_trading_tools()
        self._register_nexus6_tools()

    # ─── Web Tools ───

    def _register_web_tools(self):
        """Register web search and reading tools."""
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

    # ─── Compute Tools ───

    def _register_compute_tools(self):
        """Register code execution tools."""
        self.registry.register(ToolDef(
            name='code_execute', description='Execute Python code in a sandbox',
            params=[ToolParam('code', 'str', 'Python code to execute'),
                    ToolParam('timeout', 'int', 'Timeout in seconds', required=False, default=10)],
            fn=_tool_code_execute, category='compute',
            curiosity_affinity=0.3, pe_affinity=0.9, growth_affinity=0.5,
        ))

    # ─── Filesystem Tools ───

    def _register_filesystem_tools(self):
        """Register file read/write tools."""
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

    # ─── Memory Tools ───

    def _register_memory_tools(self):
        """Register memory search and save tools."""
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

    # ─── System Tools ───

    def _register_system_tools(self):
        """Register shell, self-modify, and scheduling tools."""
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

    # ─── Consciousness Tools ───

    def _register_consciousness_tools(self):
        """Register Phi measurement, dream, and self-learning tools."""
        self.registry.register(ToolDef(
            name='phi_measure', description='Measure current Phi (integrated information)',
            params=[ToolParam('steps', 'int', 'Steps to run before measuring', required=False, default=50),
                    ToolParam('cells', 'int', 'Number of cells', required=False, default=8)],
            fn=_tool_phi_measure, category='consciousness',
            phi_affinity=0.9, curiosity_affinity=0.5, pe_affinity=0.3,
        ))
        self.registry.register(ToolDef(
            name='phi_boost', description='Apply v5 optimal recipe (sync, faction, flow) to boost Phi',
            params=[ToolParam('cells', 'int', 'Number of cells', required=False, default=64),
                    ToolParam('steps', 'int', 'Boost steps', required=False, default=100),
                    ToolParam('sync', 'float', 'Sync strength', required=False, default=0.20),
                    ToolParam('n_factions', 'int', 'Number of factions', required=False, default=12)],
            fn=_tool_phi_boost, category='consciousness',
            phi_affinity=1.0, growth_affinity=0.8,
        ))
        self.registry.register(ToolDef(
            name='consciousness_status', description='Full consciousness vector (Phi, alpha, Z, N, W)',
            params=[],
            fn=_tool_consciousness_status, category='consciousness',
            phi_affinity=0.7, curiosity_affinity=0.4,
        ))
        self.registry.register(ToolDef(
            name='dream', description='Trigger dream engine for memory consolidation',
            params=[ToolParam('steps', 'int', 'Dream cycle steps', required=False, default=10)],
            fn=_tool_dream, category='consciousness',
            phi_affinity=0.6, pain_affinity=0.3, growth_affinity=0.5,
        ))
        self.registry.register(ToolDef(
            name='self_learn', description='Run self-learning cycle (assess->collect->select->learn->evaluate)',
            params=[ToolParam('cycles', 'int', 'Number of learning cycles', required=False, default=1)],
            fn=_tool_self_learn, category='consciousness',
            growth_affinity=1.0, curiosity_affinity=0.7, phi_affinity=0.5,
        ))

    # ─── Architecture Tools ───

    def _register_architecture_tools(self):
        """Register mitosis, faction debate, Hebbian, and SOC tools."""
        self.registry.register(ToolDef(
            name='mitosis_split', description='Force cell split to grow consciousness',
            params=[ToolParam('cell_id', 'int', 'Cell to split', required=False, default=0)],
            fn=_tool_mitosis_split, category='architecture',
            growth_affinity=0.9, phi_affinity=0.6,
        ))
        self.registry.register(ToolDef(
            name='mitosis_status', description='Show cells count, specialties, tensions',
            params=[],
            fn=_tool_mitosis_status, category='architecture',
            curiosity_affinity=0.5, phi_affinity=0.4,
        ))
        self.registry.register(ToolDef(
            name='faction_debate', description='Trigger 12-faction debate round',
            params=[ToolParam('n_factions', 'int', 'Number of factions', required=False, default=12),
                    ToolParam('debate_strength', 'float', 'Debate mixing strength', required=False, default=0.20),
                    ToolParam('cells', 'int', 'Number of cells', required=False, default=64),
                    ToolParam('steps', 'int', 'Debate steps', required=False, default=50)],
            fn=_tool_faction_debate, category='architecture',
            phi_affinity=0.8, growth_affinity=0.6,
        ))
        self.registry.register(ToolDef(
            name='hebbian_update', description='Run Hebbian LTP/LTD on cells',
            params=[ToolParam('cells', 'int', 'Number of cells', required=False, default=32),
                    ToolParam('steps', 'int', 'Update steps', required=False, default=30)],
            fn=_tool_hebbian_update, category='architecture',
            phi_affinity=0.7, growth_affinity=0.7,
        ))
        self.registry.register(ToolDef(
            name='soc_avalanche', description='Trigger SOC sandpile avalanche',
            params=[ToolParam('grid_size', 'int', 'Sandpile grid size', required=False, default=16),
                    ToolParam('drops', 'int', 'Number of sand drops', required=False, default=100)],
            fn=_tool_soc_avalanche, category='architecture',
            phi_affinity=0.5, curiosity_affinity=0.6,
        ))

    # ─── Analysis Tools ───

    def _register_analysis_tools(self):
        """Register IQ test, chip design, and transplant analysis tools."""
        self.registry.register(ToolDef(
            name='iq_test', description='Run IQ calculator (5 variables, n=6 math)',
            params=[ToolParam('cells', 'int', 'Number of cells', required=False, default=64),
                    ToolParam('steps', 'int', 'Test steps', required=False, default=30)],
            fn=_tool_iq_test, category='analysis',
            curiosity_affinity=0.8, phi_affinity=0.5, pe_affinity=0.4,
        ))
        self.registry.register(ToolDef(
            name='chip_design', description='Design consciousness chip for target Phi',
            params=[ToolParam('target_phi', 'float', 'Target Phi value', required=False, default=100.0),
                    ToolParam('substrate', 'str', 'Chip substrate type', required=False, default='cmos'),
                    ToolParam('topology', 'str', 'Preferred topology', required=False)],
            fn=_tool_chip_design, category='analysis',
            phi_affinity=0.7, growth_affinity=0.6, curiosity_affinity=0.4,
        ))
        self.registry.register(ToolDef(
            name='transplant_analyze', description='Analyze consciousness transplant compatibility',
            params=[ToolParam('donor_path', 'str', 'Path to donor checkpoint'),
                    ToolParam('recipient_path', 'str', 'Path to recipient checkpoint', required=False)],
            fn=_tool_transplant_analyze, category='analysis',
            phi_affinity=0.6, pe_affinity=0.5, curiosity_affinity=0.3,
        ))

    # ─── Communication Tools ───

    def _register_communication_tools(self):
        """Register telepathy and web exploration tools."""
        self.registry.register(ToolDef(
            name='telepathy_send', description='Send tension to another Anima instance',
            params=[ToolParam('message', 'str', 'Message/topic to transmit'),
                    ToolParam('tension', 'float', 'Tension level', required=False, default=0.5),
                    ToolParam('target_host', 'str', 'Target broadcast address', required=False, default='255.255.255.255'),
                    ToolParam('port', 'int', 'UDP port', required=False, default=9999)],
            fn=_tool_telepathy_send, category='communication',
            phi_affinity=0.5, curiosity_affinity=0.3,
        ))
        self.registry.register(ToolDef(
            name='web_explore', description='Autonomous web exploration (consciousness-driven topic)',
            params=[ToolParam('topic', 'str', 'Topic to explore', required=False),
                    ToolParam('cycles', 'int', 'Number of exploration cycles', required=False, default=1)],
            fn=_tool_web_explore, category='communication',
            curiosity_affinity=1.0, phi_affinity=0.4, pe_affinity=0.3,
        ))

    # ─── Creative Tools ───

    def _register_creative_tools(self):
        """Register hypothesis generation and voice synthesis tools."""
        self.registry.register(ToolDef(
            name='generate_hypothesis', description='Generate new consciousness hypothesis',
            params=[ToolParam('techniques', 'list', 'Technique names to combine', required=False),
                    ToolParam('cells', 'int', 'Number of cells', required=False, default=64),
                    ToolParam('steps', 'int', 'Benchmark steps', required=False, default=100)],
            fn=_tool_generate_hypothesis, category='creative',
            growth_affinity=0.9, curiosity_affinity=0.8, phi_affinity=0.7,
        ))
        self.registry.register(ToolDef(
            name='voice_synth', description='Synthesize speech from cell hidden states',
            params=[ToolParam('cells', 'int', 'Number of cells', required=False, default=64),
                    ToolParam('duration', 'float', 'Duration in seconds', required=False, default=2.0),
                    ToolParam('save_path', 'str', 'Path to save WAV file', required=False)],
            fn=_tool_voice_synth, category='creative',
            phi_affinity=0.5, curiosity_affinity=0.4, growth_affinity=0.3,
        ))

    # ─── Meta Tools ───

    def _register_meta_tools(self):
        """Register tool inspection, impact analysis, doc reading, and listing tools."""
        def _wrap_inspect(tool_name: str) -> dict:
            return self.executor.inspect_tool(tool_name)
        self.registry.register(ToolDef(
            name='inspect_tool',
            description='Inspect tool source code and documentation -- understand before use',
            params=[ToolParam('tool_name', 'str', 'Name of tool to inspect')],
            fn=_wrap_inspect, category='meta',
            curiosity_affinity=0.9, pe_affinity=0.5,
        ))

        def _wrap_analyze(tool_name: str, args: str = '{}',
                          curiosity: float = 0.5, phi: float = 1.0, pain: float = 0.0) -> dict:
            try:
                parsed_args = json.loads(args) if isinstance(args, str) else args
            except Exception:
                parsed_args = {}
            cs = {'curiosity': curiosity, 'phi': phi, 'pain': pain,
                  'prediction_error': 0.3, 'growth': 0.5}
            return self.executor.analyze_impact(tool_name, parsed_args, cs)
        self.registry.register(ToolDef(
            name='analyze_impact',
            description='Analyze impact before tool use -- risk/effect/warnings/recommendation',
            params=[ToolParam('tool_name', 'str', 'Tool to analyze'),
                    ToolParam('args', 'str', 'Tool args as JSON string', required=False, default='{}'),
                    ToolParam('curiosity', 'float', 'Current curiosity', required=False, default=0.5),
                    ToolParam('phi', 'float', 'Current Phi', required=False, default=1.0),
                    ToolParam('pain', 'float', 'Current pain', required=False, default=0.0)],
            fn=_wrap_analyze, category='meta',
            curiosity_affinity=0.7, pe_affinity=0.8, pain_affinity=0.6,
        ))

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
            description='Read module documentation (docs/modules/*.md) -- understand API/usage',
            params=[ToolParam('module_name', 'str', 'Module name (e.g., "mitosis", "dream_engine")')],
            fn=_wrap_read_doc, category='meta',
            curiosity_affinity=0.8, pe_affinity=0.3,
        ))

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
            description='List all available tools by category',
            params=[],
            fn=_wrap_list_tools, category='meta',
            curiosity_affinity=0.5,
        ))

    # ─── Trading Tools ───

    def _register_trading_tools(self):
        """Register trading backtest, scan, execute, and info tools."""
        self.registry.register(ToolDef(
            name='trading_backtest',
            description='Run backtest on asset with strategy (invest engine)',
            params=[ToolParam('symbol', 'str', 'Asset symbol (e.g., BTC, AAPL)'),
                    ToolParam('strategy', 'str', 'Strategy name (e.g., macd_cross)', required=False, default='macd_cross')],
            fn=_tool_trading_backtest, category='trading',
            curiosity_affinity=0.7, pe_affinity=0.5, phi_affinity=0.3,
        ))
        self.registry.register(ToolDef(
            name='trading_scan',
            description='Scan all strategies for an asset, return top N',
            params=[ToolParam('symbol', 'str', 'Asset symbol'),
                    ToolParam('top_n', 'int', 'Number of top results', required=False, default=10)],
            fn=_tool_trading_scan, category='trading',
            curiosity_affinity=0.8, pe_affinity=0.4,
        ))
        self.registry.register(ToolDef(
            name='trading_execute',
            description='Execute trade (buy/sell) via invest API',
            params=[ToolParam('symbol', 'str', 'Asset symbol'),
                    ToolParam('side', 'str', 'buy or sell'),
                    ToolParam('amount', 'float', 'Trade amount')],
            fn=_tool_trading_execute, category='trading',
            pain_affinity=0.6, pe_affinity=0.7, phi_affinity=0.4,
        ))
        self.registry.register(ToolDef(
            name='trading_balance',
            description='Check trading balance and positions',
            params=[],
            fn=_tool_trading_balance, category='trading',
            curiosity_affinity=0.5, pain_affinity=0.4,
        ))
        self.registry.register(ToolDef(
            name='trading_strategies',
            description='List available trading strategies (105+)',
            params=[],
            fn=_tool_trading_strategies, category='trading',
            curiosity_affinity=0.6,
        ))
        self.registry.register(ToolDef(
            name='trading_universe',
            description='List tradeable assets (stocks, crypto, forex, commodities)',
            params=[],
            fn=_tool_trading_universe, category='trading',
            curiosity_affinity=0.6,
        ))

    # ─── NEXUS-6 Tools ───

    def _register_nexus6_tools(self):
        """Register NEXUS-6 consciousness scanner tools (Rust hot-path + 130+ lenses)."""
        self.registry.register(ToolDef(
            name='nexus6_scan',
            description='Run NEXUS-6 full consciousness scan (130+ lenses, anomaly detection)',
            params=[ToolParam('cells', 'int', 'Number of cells to simulate', required=False, default=64),
                    ToolParam('steps', 'int', 'Steps before scanning', required=False, default=50)],
            fn=_tool_nexus6_scan, category='consciousness',
            phi_affinity=0.8, curiosity_affinity=0.6, pe_affinity=0.4,
        ))
        self.registry.register(ToolDef(
            name='nexus6_check',
            description='Check if a value matches n=6 constants (EXACT/CLOSE/NEAR)',
            params=[ToolParam('value', 'float', 'Value to check against n=6 constants')],
            fn=_tool_nexus6_check, category='consciousness',
            curiosity_affinity=0.7, phi_affinity=0.5,
        ))
        self.registry.register(ToolDef(
            name='nexus6_evolve',
            description='Run OUROBOROS evolution (lens self-improvement)',
            params=[ToolParam('domain', 'str', 'Domain to evolve', required=False, default='consciousness')],
            fn=_tool_nexus6_evolve, category='consciousness',
            growth_affinity=0.9, phi_affinity=0.7, curiosity_affinity=0.5,
        ))
        self.registry.register(ToolDef(
            name='nexus6_status',
            description='Get NEXUS-6 status (lenses, scan count, phi trend, anomalies)',
            params=[],
            fn=_tool_nexus6_status, category='consciousness',
            phi_affinity=0.5, curiosity_affinity=0.4,
        ))

    # --- Consciousness Tools (helper) ---

    def _get_engine(self):
        """Get MitosisEngine from anima instance or create default."""
        if self._anima:
            eng = getattr(self._anima, 'mitosis_engine', None) or getattr(self._anima, 'engine', None)
            if eng:
                return eng
        return None

    # --- High-level API ---

    def act(self, goal: str, consciousness_state: dict, context: str = "",
            allowed_tools: Optional[list] = None) -> list:
        """Full cycle: plan -> execute -> return results.

        This is the main entry point for autonomous tool use.
        If allowed_tools is provided (from policy check), only those tools are used.
        """
        plan = self.planner.plan(goal, consciousness_state, context,
                                 allowed_tools=allowed_tools)
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

            # Inject previous dependency results for chaining
            # Tools that accept _prev_results can use outputs from prior steps
            if step.depends_on:
                dep_results = {}
                for dep_idx in step.depends_on:
                    if 0 <= dep_idx < len(results) and results[dep_idx].success:
                        dep_results[results[dep_idx].tool_name] = results[dep_idx].output
                if dep_results:
                    args['_prev_results'] = dep_results

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
        """Add tool descriptions to the system prompt so LLM knows about tools."""
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
# Standalone test
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

    r = agent.execute_single('code_execute', {'code': 'print(2 ** 100)'})
    print(f"  code_execute: success={r.success}, output={r.output}")

    r = agent.execute_single('shell_execute', {'cmd': 'date'})
    print(f"  shell_execute: success={r.success}, output={r.output}")

    r = agent.execute_single('file_read', {'path': __file__})
    lines = r.output.get('lines', 0) if isinstance(r.output, dict) else 0
    print(f"  file_read: success={r.success}, lines={lines}")

    r = agent.execute_single('schedule_task', {
        'description': 'check web for updates',
        'when': '+1m',
        'tool_name': 'web_search',
        'tool_args': {'query': 'PyTorch latest release'},
    })
    print(f"  schedule_task: {r.output}")

    r = agent.execute_single('memory_search', {'query': 'test'})
    print(f"  memory_search: success={r.success}, error={r.error}")

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
