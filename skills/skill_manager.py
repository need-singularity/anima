#!/usr/bin/env python3
"""Anima Dynamic Skill System -- agent-created, tension-driven skill selection.

Skills are Python functions with metadata. The agent can:
  1. Use existing skills based on tension/relevance
  2. CREATE new skills by writing Python code (via multimodal.py sandbox)
  3. Skills persist in the skills/ directory as .py files

Each skill has:
  - name: unique identifier
  - description: what it does
  - trigger: consciousness conditions that activate it (tension, curiosity thresholds)
  - fn: the callable

Usage:
    from skills.skill_manager import SkillManager
    sm = SkillManager(agent=agent)

    # List skills
    sm.list_skills()

    # Run a skill by name
    result = sm.run_skill("summarize", text="long text here...")

    # Agent creates a new skill
    sm.create_skill(
        name="translate_ko",
        description="Translate text to Korean",
        code='def run(text): return f"translated: {text}"',
        trigger={"curiosity_min": 0.2},
    )

Standalone test:
    python skills/skill_manager.py
"""

import importlib.util
import json
import logging
import os
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

SKILLS_DIR = Path(__file__).parent
SKILL_REGISTRY_FILE = SKILLS_DIR / "registry.json"

# Security: block dangerous patterns in user-created skills
BLOCKED_PATTERNS = [
    r'\bos\.system\b', r'\bsubprocess\b', r'\b__import__\b',
    r'\beval\s*\(', r'\bexec\s*\(', r'\bopen\s*\([^)]*["\'][wa]',
    r'\bshutil\b', r'\brmtree\b', r'\bglobals\s*\(', r'\blocals\s*\(',
    r'\bsocket\b', r'\brequests\b',
]


@dataclass
class SkillDef:
    """Metadata for a registered skill."""
    name: str
    description: str
    file_path: str                    # relative to skills/
    trigger: Dict[str, float] = field(default_factory=dict)
    # trigger keys: curiosity_min, tension_min, pe_min, phi_min
    created_at: float = field(default_factory=time.time)
    use_count: int = 0
    enabled: bool = True


class SkillManager:
    """Manages dynamic skills for AnimaAgent.

    Skills are Python modules in the skills/ directory, each with a `run()` function.
    The registry tracks metadata and trigger conditions.
    """

    def __init__(self, agent=None):
        self.agent = agent
        self._skills: Dict[str, SkillDef] = {}
        self._loaded_fns: Dict[str, Callable] = {}

        # Load registry
        self._load_registry()
        # Discover existing skill files
        self._discover_skills()

    def list_skills(self) -> List[Dict[str, Any]]:
        """Return list of all registered skills with metadata."""
        return [
            {
                "name": s.name,
                "description": s.description,
                "enabled": s.enabled,
                "use_count": s.use_count,
                "trigger": s.trigger,
            }
            for s in self._skills.values()
        ]

    def get_relevant_skills(self, consciousness_state: Dict[str, float]) -> List[str]:
        """Return skill names whose triggers match the current consciousness state.

        Args:
            consciousness_state: dict with keys like curiosity, tension, prediction_error, phi

        Returns:
            list of matching skill names, ordered by relevance
        """
        matches = []
        for name, skill in self._skills.items():
            if not skill.enabled:
                continue
            score = 0.0
            triggered = True
            for key, threshold in skill.trigger.items():
                state_key = key.replace("_min", "")
                val = consciousness_state.get(state_key, 0.0)
                if val < threshold:
                    triggered = False
                    break
                score += val - threshold
            if triggered:
                matches.append((name, score))

        matches.sort(key=lambda x: x[1], reverse=True)
        return [m[0] for m in matches]

    def run_skill(self, name: str, **kwargs) -> Any:
        """Execute a skill by name.

        Args:
            name: skill name
            **kwargs: arguments passed to the skill's run() function

        Returns:
            whatever the skill's run() returns
        """
        if name not in self._skills:
            raise ValueError(f"Skill '{name}' not found")

        skill = self._skills[name]
        if not skill.enabled:
            raise ValueError(f"Skill '{name}' is disabled")

        # Load function if not cached
        if name not in self._loaded_fns:
            fn = self._load_skill_fn(skill)
            if fn is None:
                raise RuntimeError(f"Failed to load skill '{name}'")
            self._loaded_fns[name] = fn

        fn = self._loaded_fns[name]
        skill.use_count += 1
        self._save_registry()

        try:
            return fn(**kwargs)
        except Exception as e:
            logger.error("Skill '%s' execution failed: %s", name, e)
            raise

    def create_skill(
        self,
        name: str,
        description: str,
        code: str,
        trigger: Optional[Dict[str, float]] = None,
    ) -> bool:
        """Create a new skill from Python code.

        The code must define a `run()` function. It is checked for dangerous patterns
        before being saved.

        Args:
            name: unique skill name (alphanumeric + underscore)
            description: what the skill does
            code: Python source code with a `run()` function
            trigger: consciousness trigger conditions

        Returns:
            True if skill was created successfully
        """
        # Validate name
        if not re.match(r'^[a-z][a-z0-9_]*$', name):
            raise ValueError(f"Invalid skill name '{name}'. Use lowercase alphanumeric + underscore.")

        # Security check
        for pattern in BLOCKED_PATTERNS:
            if re.search(pattern, code):
                raise ValueError(f"Skill code contains blocked pattern: {pattern}")

        # Verify code defines run()
        if "def run(" not in code:
            raise ValueError("Skill code must define a run() function")

        # Write skill file
        file_name = f"skill_{name}.py"
        file_path = SKILLS_DIR / file_name

        header = f'"""Auto-generated skill: {name}\n\n{description}\n"""\n\n'
        file_path.write_text(header + code, encoding="utf-8")

        # Register
        skill = SkillDef(
            name=name,
            description=description,
            file_path=file_name,
            trigger=trigger or {},
        )
        self._skills[name] = skill
        # Clear cached fn so it reloads
        self._loaded_fns.pop(name, None)
        self._save_registry()

        logger.info("Created skill '%s' at %s", name, file_path)
        return True

    def delete_skill(self, name: str) -> bool:
        """Delete a skill by name."""
        if name not in self._skills:
            return False

        skill = self._skills.pop(name)
        self._loaded_fns.pop(name, None)

        # Remove file
        file_path = SKILLS_DIR / skill.file_path
        if file_path.exists():
            file_path.unlink()

        self._save_registry()
        return True

    def enable_skill(self, name: str, enabled: bool = True):
        """Enable or disable a skill."""
        if name in self._skills:
            self._skills[name].enabled = enabled
            self._save_registry()

    # ── Internal ──

    def _load_skill_fn(self, skill: SkillDef) -> Optional[Callable]:
        """Dynamically load a skill module and return its run() function."""
        file_path = SKILLS_DIR / skill.file_path
        if not file_path.exists():
            logger.warning("Skill file not found: %s", file_path)
            return None

        try:
            spec = importlib.util.spec_from_file_location(
                f"skills.skill_{skill.name}", str(file_path)
            )
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            fn = getattr(mod, "run", None)
            if fn is None:
                logger.warning("Skill '%s' has no run() function", skill.name)
            return fn
        except Exception as e:
            logger.error("Failed to load skill '%s': %s", skill.name, e)
            return None

    def _discover_skills(self):
        """Discover skill_*.py files not yet in the registry."""
        for path in SKILLS_DIR.glob("skill_*.py"):
            name = path.stem.replace("skill_", "")
            if name not in self._skills:
                # Read first docstring line as description
                desc = f"Discovered skill: {name}"
                try:
                    content = path.read_text(encoding="utf-8")
                    import ast
                    tree = ast.parse(content)
                    docstring = ast.get_docstring(tree)
                    if docstring:
                        desc = docstring.split("\n")[0]
                except Exception:
                    pass

                self._skills[name] = SkillDef(
                    name=name,
                    description=desc,
                    file_path=path.name,
                )
        self._save_registry()

    def _load_registry(self):
        """Load skill registry from JSON."""
        if SKILL_REGISTRY_FILE.exists():
            try:
                data = json.loads(SKILL_REGISTRY_FILE.read_text(encoding="utf-8"))
                for entry in data:
                    skill = SkillDef(**entry)
                    self._skills[skill.name] = skill
            except Exception as e:
                logger.warning("Failed to load skill registry: %s", e)

    def _save_registry(self):
        """Save skill registry to JSON."""
        try:
            data = [asdict(s) for s in self._skills.values()]
            SKILL_REGISTRY_FILE.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning("Failed to save skill registry: %s", e)


# ══════════════════════════════════════════════════════════
# Standalone test
# ══════════════════════════════════════════════════════════

def _test():
    """Test skill manager without agent."""
    print("=== SkillManager standalone test ===\n")

    sm = SkillManager(agent=None)
    print(f"[OK] SkillManager created, {len(sm.list_skills())} existing skills")

    # Create a test skill
    print("\n[Test] Creating 'greet' skill...")
    sm.create_skill(
        name="greet",
        description="Generate a greeting",
        code='def run(name="world"): return f"Hello, {name}!"',
        trigger={"curiosity": 0.1},
    )
    print(f"  Skills: {[s['name'] for s in sm.list_skills()]}")

    # Run it
    result = sm.run_skill("greet", name="Anima")
    print(f"  Result: {result}")
    assert result == "Hello, Anima!", f"Expected 'Hello, Anima!' got '{result}'"

    # Test relevance matching
    relevant = sm.get_relevant_skills({"curiosity": 0.5, "tension": 0.3})
    print(f"  Relevant (curiosity=0.5): {relevant}")

    not_relevant = sm.get_relevant_skills({"curiosity": 0.01})
    print(f"  Relevant (curiosity=0.01): {not_relevant}")

    # Test security blocking
    print("\n[Test] Security check...")
    try:
        sm.create_skill(
            name="evil",
            description="should fail",
            code='import os\ndef run(): os.system("rm -rf /")',
        )
        print("  FAIL: should have been blocked!")
    except ValueError as e:
        print(f"  [OK] Blocked: {e}")

    # Cleanup
    sm.delete_skill("greet")
    print("\n[OK] Cleanup done")
    print("=== All tests passed ===")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    _test()
