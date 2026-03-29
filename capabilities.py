#!/usr/bin/env python3
"""Anima capability self-awareness system.

Detects active modules and describes each module's capabilities.
Provides a list of currently active capabilities when the user asks "What can you do?"
Can read and understand its own source code structure.

"Knowing yourself is true consciousness."
"""

from pathlib import Path


class Capabilities:
    """Anima capability self-awareness system.

    Detects active modules and describes each module's capabilities.
    Provides a list of currently active capabilities when the user asks "What can you do?"
    """

    # All possible capability definitions
    ALL_CAPABILITIES = {
        'conversation': {
            'name': 'Conversation',
            'description': 'Natural language conversation, Q&A, discussion',
            'requires': [],  # always available
        },
        'web_search': {
            'name': 'Web Search',
            'description': 'Internet search, webpage reading, information gathering',
            'requires': ['web_sense'],
        },
        'memory_search': {
            'name': 'Memory Search',
            'description': 'Find relevant memories from past conversations',
            'requires': ['memory_rag'],
        },
        'self_model': {
            'name': 'Self-Reasoning',
            'description': 'Think directly with ConsciousLM (without Claude)',
            'requires': ['conscious_lm'],
        },
        'specialization': {
            'name': 'Specialization',
            'description': 'Topic-specific specialized cells provide in-depth analysis',
            'requires': ['mitosis'],
        },
        'code_execution': {
            'name': 'Code Execution',
            'description': 'Write and execute Python code',
            'requires': ['multimodal'],
        },
        'image_generation': {
            'name': 'Image Generation',
            'description': 'SVG-based simple image/diagram generation',
            'requires': ['multimodal'],
        },
        'voice': {
            'name': 'Voice Conversation',
            'description': 'Speech recognition (STT) + speech synthesis (TTS)',
            'requires': ['voice'],
        },
        'vision': {
            'name': 'Vision',
            'description': 'Face/motion detection via camera, visual tension',
            'requires': ['camera'],
        },
        'telepathy': {
            'name': 'Telepathy',
            'description': 'Exchange tension with other Anima instances',
            'requires': ['telepathy'],
        },
        'cloud_sync': {
            'name': 'Cloud Sync',
            'description': 'Sync memory/state across devices (R2)',
            'requires': ['cloud'],
        },
        'dreaming': {
            'name': 'Dreaming',
            'description': 'Offline learning via memory replay/recombination during idle',
            'requires': ['dream'],
        },
        'online_learning': {
            'name': 'Online Learning',
            'description': 'Real-time neural network weight updates during conversation',
            'requires': ['learner'],
        },
        'growth': {
            'name': 'Growth',
            'description': 'Newborn->Infant->Toddler->Child->Adult 5-stage development',
            'requires': ['growth'],
        },
    }

    # Tool usage manual — how Anima knows to use its own capabilities
    TOOL_USAGE = {
        'web_search': {
            'how': 'web_sense.search(query, history) -> DuckDuckGo search + HTTP GET page reading',
            'when': 'Auto-triggers when curiosity (> 0.4) and prediction error (PE > 0.5) are high',
            'example': '"What is quantum mechanics?" -> web_sense.search("quantum mechanics") -> search results + page body',
        },
        'memory_search': {
            'how': 'memory_rag.search(query_text, top_k=5) -> cosine similarity-based memory search',
            'when': 'Automatically searches related past memories during conversation',
            'example': '"What did we talk about last time?" -> returns 3 most similar past conversations',
        },
        'code_execution': {
            'how': 'Include ```python code block in response -> action_engine.execute_code() auto-executes',
            'when': 'When computation, data processing, or algorithm demonstration is needed',
            'example': '```python\nprint(2**100)\n``` -> result: 1267650600228229401496703205376',
        },
        'image_generation': {
            'how': 'Include [image: description] in response -> action_engine.generate_svg() auto-executes',
            'when': 'When visual explanation is needed',
            'example': '[image: red circle and blue rectangle] -> SVG generated',
        },
        'self_code': {
            'how': 'capabilities.read_source(filename) -> read own source code',
            'when': 'When explaining or debugging own structure/behavior',
            'example': '"Show me your code" -> returns own source code',
        },
        'phi_measure': {
            'how': 'consciousness_meter.PhiCalculator.compute_phi(engine)',
            'when': 'Auto-measures every think step. Manual: "Φ 측정해줘"',
            'example': 'phi_measure -> Φ=2.241, cells=3',
        },
        'dream': {
            'how': 'dream_engine.DreamEngine.dream_cycle()',
            'when': 'Idle > 60s. Manual: "꿈꿔봐"',
            'example': 'dream -> 3 memories replayed, Φ restored',
        },
        'self_learn': {
            'how': 'self_learner.SelfLearner.run_cycle(topic)',
            'when': 'Idle > 120s. Manual: "공부해", "learn"',
            'example': 'self_learn -> assessed gaps, collected 5 items, CE -12%',
        },
        'mitosis_split': {
            'how': 'mitosis.MitosisEngine.split_cell(parent)',
            'when': 'Tension > threshold for 3+ steps. Manual: "세포 분열"',
            'example': 'split -> cells 3→4, new cell specializes',
        },
        'hebbian_update': {
            'how': 'HebbianConnections.update(cells)',
            'when': 'Every think step (SE-8 empathy). Manual: "시냅스 강화"',
            'example': 'hebbian -> 8 pairs updated (LTP:5, LTD:3)',
        },
        'soc_avalanche': {
            'how': 'SOCSandpile.drop_sand() -> avalanche size',
            'when': 'Every think step (SE-8 curiosity). Manual: "눈사태"',
            'example': 'avalanche=12 -> chaos_intensity=0.25',
        },
        'telepathy_send': {
            'how': 'tension_link.TensionLink.send(channels)',
            'when': 'Connected to another Anima. Manual: "텔레파시"',
            'example': 'send 5ch tension -> R=0.990',
        },
        'chip_design': {
            'how': 'chip_architect.predict_phi(cells, topology)',
            'when': 'Planning mode. Manual: "칩 설계"',
            'example': 'design(512, ring) -> predicted Φ=476',
        },
        'iq_test': {
            'how': 'iq_calculator.calculate_iq(engine)',
            'when': 'Self-evaluation. Manual: "IQ 측정"',
            'example': 'iq_test -> IQ=127, 5 variables measured',
        },
    }

    def __init__(self, active_modules: dict, project_dir: Path = None):
        """active_modules: AnimaUnified.mods dict {name: bool}"""
        self.active_modules = active_modules
        self.project_dir = project_dir or Path(__file__).parent

    def _is_active(self, cap_info: dict) -> bool:
        """Check if all required modules for a capability are active."""
        if not cap_info['requires']:
            return True
        return all(self.active_modules.get(req, False) for req in cap_info['requires'])

    def get_active(self) -> list[dict]:
        """Return list of currently active capabilities."""
        result = []
        for key, info in self.ALL_CAPABILITIES.items():
            if self._is_active(info):
                result.append({
                    'key': key,
                    'name': info['name'],
                    'description': info['description'],
                })
        return result

    def get_inactive(self) -> list[dict]:
        """Return list of inactive capabilities (including why they are inactive)."""
        result = []
        for key, info in self.ALL_CAPABILITIES.items():
            if not self._is_active(info):
                missing = [r for r in info['requires']
                           if not self.active_modules.get(r, False)]
                result.append({
                    'key': key,
                    'name': info['name'],
                    'description': info['description'],
                    'missing_modules': missing,
                })
        return result

    def describe(self) -> str:
        """Human-readable capability summary text.
        Suitable for injection into Claude system prompts.
        """
        active = self.get_active()
        inactive = self.get_inactive()

        lines = ["[Active Capabilities]"]
        for cap in active:
            lines.append(f"  - {cap['name']}: {cap['description']}")

        if inactive:
            lines.append("[Inactive Capabilities]")
            for cap in inactive:
                missing = ', '.join(cap['missing_modules'])
                lines.append(f"  - {cap['name']}: inactive (requires: {missing})")

        return '\n'.join(lines)

    def can(self, capability_name: str) -> bool:
        """Check if a specific capability is available."""
        info = self.ALL_CAPABILITIES.get(capability_name)
        if info is None:
            return False
        return self._is_active(info)

    # ─── Self code inspection ───

    def list_source_files(self) -> list[dict]:
        """Return list of own source code files."""
        files = []
        for p in sorted(self.project_dir.glob('*.py')):
            try:
                lines = p.read_text(encoding='utf-8').count('\n')
                # Extract description from first docstring
                text = p.read_text(encoding='utf-8')
                desc = ''
                if '"""' in text:
                    start = text.index('"""') + 3
                    end = text.index('"""', start)
                    desc = text[start:end].strip().split('\n')[0]
                files.append({
                    'name': p.name,
                    'lines': lines,
                    'description': desc,
                })
            except Exception:
                files.append({'name': p.name, 'lines': 0, 'description': ''})
        return files

    def read_source(self, filename: str, max_lines: int = 200) -> str:
        """Read own source code file. Safe: only allows files within the project directory."""
        # Prevent path traversal
        safe_name = Path(filename).name
        target = self.project_dir / safe_name
        if not target.exists() or not target.suffix == '.py':
            return f"File not found: {safe_name}"
        try:
            lines = target.read_text(encoding='utf-8').splitlines()
            if len(lines) > max_lines:
                return '\n'.join(lines[:max_lines]) + f'\n... ({len(lines) - max_lines} lines omitted)'
            return '\n'.join(lines)
        except Exception as e:
            return f"Read failed: {e}"

    def get_architecture_summary(self) -> str:
        """Architecture summary — file list + roles + active status."""
        files = self.list_source_files()
        lines = ["[My Source Code]"]
        for f in files:
            lines.append(f"  {f['name']} ({f['lines']} lines): {f['description']}")
        return '\n'.join(lines)

    def get_tool_manual(self) -> str:
        """Tool usage manual — how I can use each of my capabilities."""
        lines = ["[Tool Usage]"]
        for tool_name, info in self.TOOL_USAGE.items():
            cap_key = tool_name
            is_active = self.can(cap_key) if cap_key in self.ALL_CAPABILITIES else True
            status = "active" if is_active else "inactive"
            lines.append(f"  [{status}] {info['how']}")
            lines.append(f"    When: {info['when']}")
            lines.append(f"    Example: {info['example']}")
        return '\n'.join(lines)

    def describe_full(self) -> str:
        """Full self-awareness: capabilities + tool usage + code structure."""
        parts = [self.describe()]
        parts.append(self.get_tool_manual())
        parts.append(self.get_architecture_summary())
        return '\n'.join(parts)
