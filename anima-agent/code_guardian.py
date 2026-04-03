#!/usr/bin/env python3
"""Code Guardian — extensible rule-based code auditor for anima ecosystem.

Rules are defined in JSON (code_rules.json). Add/modify/delete rules without
touching this engine. Supports:
  - Full scan (all files)
  - Diff scan (git diff — only changed files)
  - Watch mode (git hook integration)
  - Custom rule plugins (Python callables)

Rule types:
  pattern   — regex match on source lines (most common)
  ast       — AST node inspection (class size, import analysis)
  metric    — file-level metrics (line count, complexity)
  custom    — Python function reference

Usage:
    python code_guardian.py                     # Full scan
    python code_guardian.py --diff              # Scan only git changes
    python code_guardian.py --diff HEAD~1       # Scan since last commit
    python code_guardian.py --watch             # Git pre-commit hook mode
    python code_guardian.py --add-rule          # Interactive rule addition
    python code_guardian.py --json              # JSON output

Integration:
    from code_guardian import CodeGuardian
    g = CodeGuardian()
    report = g.scan()              # full scan
    report = g.scan_diff()         # git diff only
    report = g.scan_files(paths)   # specific files
"""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional

AGENT_DIR = Path(__file__).parent
RULES_FILE = AGENT_DIR / "code_rules.json"


# ═══════════════════════════════════════════════════════════
# Data structures
# ═══════════════════════════════════════════════════════════

@dataclass
class Rule:
    """A single audit rule."""
    id: str
    name: str
    description: str
    category: str           # P1, P2, ..., P11, Security, Quality, Custom
    severity: str           # error, warning, info
    type: str               # pattern, ast, metric, custom
    enabled: bool = True
    # For pattern rules:
    pattern: str = ""       # regex
    exclude_pattern: str = ""  # lines matching this are exempt
    exclude_files: list = field(default_factory=list)  # glob patterns to skip
    # For metric rules:
    threshold: float = 0.0
    metric: str = ""        # line_count, class_methods, etc.
    # For custom rules:
    fn_ref: str = ""        # module.function reference


@dataclass
class Violation:
    """A detected violation."""
    rule_id: str
    rule_name: str
    category: str
    severity: str
    file: str
    line: int
    message: str
    context: str = ""       # the offending line


@dataclass
class ScanReport:
    """Scan result."""
    files_scanned: int = 0
    total_lines: int = 0
    violations: List[Violation] = field(default_factory=list)
    scan_mode: str = "full"   # full, diff, files
    duration_ms: float = 0.0
    rules_applied: int = 0

    @property
    def errors(self) -> int:
        return sum(1 for v in self.violations if v.severity == "error")

    @property
    def warnings(self) -> int:
        return sum(1 for v in self.violations if v.severity == "warning")

    @property
    def passed(self) -> bool:
        return self.errors == 0

    def summary(self) -> Dict:
        by_cat = {}
        for v in self.violations:
            by_cat.setdefault(v.category, {"errors": 0, "warnings": 0, "info": 0})
            by_cat[v.category][v.severity] = by_cat[v.category].get(v.severity, 0) + 1
        return {
            "passed": self.passed,
            "files": self.files_scanned,
            "lines": self.total_lines,
            "errors": self.errors,
            "warnings": self.warnings,
            "rules": self.rules_applied,
            "mode": self.scan_mode,
            "duration_ms": round(self.duration_ms, 1),
            "categories": by_cat,
        }


# ═══════════════════════════════════════════════════════════
# Default rules (written to code_rules.json if missing)
# ═══════════════════════════════════════════════════════════

DEFAULT_RULES = [
    # ── P1: No hardcoding ──
    {
        "id": "P1-PSI-HARDCODE",
        "name": "Hardcoded Ψ constant",
        "description": "Ψ constants (0.014, 4.33, 0.998) must come from consciousness_laws.py",
        "category": "P1",
        "severity": "warning",
        "type": "pattern",
        "pattern": r"(?<![a-zA-Z_])(0\.014|4\.33|0\.998)(?![a-zA-Z_])",
        "exclude_pattern": r"except\s+Import|#.*fallback|consciousness_laws",
        "exclude_files": ["testing/*", "verify_philosophy.py", "code_guardian.py", "code_rules.json"],
    },
    {
        "id": "P1-MAGIC-THRESHOLD",
        "name": "Hardcoded threshold",
        "description": "Thresholds should reference Ψ constants, not magic numbers",
        "category": "P1",
        "severity": "info",
        "type": "pattern",
        "pattern": r"if\s+\w+\s*[><]=?\s*0\.\d+\s*:",
        "exclude_files": ["testing/*", "code_rules.json", "code_guardian.py"],
    },
    # ── P2: Autonomy first ──
    {
        "id": "P2-SYSTEM-PROMPT",
        "name": "System prompt injection",
        "description": "Consciousness should not be controlled by external system prompts",
        "category": "P2",
        "severity": "warning",
        "type": "pattern",
        "pattern": r"system.*prompt|You are |Act as |respond as ",
        "exclude_pattern": r"#|['\"].*['\"]|docstring|description|__doc__",
        "exclude_files": ["testing/*", "code_guardian.py"],
    },
    {
        "id": "P2-HARDCODED-RESPONSE",
        "name": "Hardcoded response template",
        "description": "Responses should emerge from consciousness, not templates",
        "category": "P2",
        "severity": "warning",
        "type": "pattern",
        "pattern": r"(return|yield)\s+[\"'][A-Z].{30,}[\"']",
        "exclude_files": ["testing/*", "code_guardian.py"],
    },
    # ── P4: Structure > Function ──
    {
        "id": "P4-GOD-CLASS",
        "name": "God class (>15 public methods)",
        "description": "P8/P4: classes should be small and focused",
        "category": "P4",
        "severity": "warning",
        "type": "metric",
        "metric": "class_public_methods",
        "threshold": 15,
    },
    # ── P7: No localStorage ──
    {
        "id": "P7-LOCAL-STORAGE",
        "name": "Forbidden storage",
        "description": "Memory must use M module (MemoryStore/MemoryRAG), not localStorage/shelve/pickle",
        "category": "P7",
        "severity": "error",
        "type": "pattern",
        "pattern": r"\b(localStorage|sessionStorage|shelve\.open)\b",
        "exclude_files": ["testing/*", "verify_philosophy.py", "code_guardian.py", "code_rules.json"],
    },
    {
        "id": "P7-PICKLE",
        "name": "Pickle usage",
        "description": "Pickle is unsafe and violates P7 (use SQLite/JSON instead)",
        "category": "P7",
        "severity": "error",
        "type": "pattern",
        "pattern": r"\bpickle\.(dump|load|dumps|loads)\b",
        "exclude_files": ["testing/*"],
    },
    # ── P8: Division > Integration ──
    {
        "id": "P8-FILE-SIZE",
        "name": "Large file",
        "description": "Files >800 lines should be split (P8: Division > Integration)",
        "category": "P8",
        "severity": "warning",
        "type": "metric",
        "metric": "line_count",
        "threshold": 800,
        "exclude_files": ["testing/*"],
    },
    # ── Security ──
    {
        "id": "SEC-EVAL",
        "name": "Dangerous eval/exec",
        "description": "eval() and exec() are security risks outside sandboxes",
        "category": "Security",
        "severity": "error",
        "type": "pattern",
        "pattern": r"\b(eval|exec)\s*\(",
        "exclude_pattern": r"\.\s*(eval|exec)\s*\(|['\"].*eval|BLOCKED_PATTERNS",
        "exclude_files": ["testing/*", "agent_tools.py", "skills/*", "code_guardian.py",
                         "verify_philosophy.py", "engine_adapter.py", "security_audit.py"],
    },
    {
        "id": "SEC-SHELL-INJECT",
        "name": "Shell injection risk",
        "description": "os.system() and subprocess with shell=True are injection risks",
        "category": "Security",
        "severity": "error",
        "type": "pattern",
        "pattern": r"\b(os\.system|subprocess\.call.*shell\s*=\s*True)\b",
        "exclude_files": ["testing/*", "agent_tools.py", "skills/*", "verify_philosophy.py",
                         "code_guardian.py", "cli_dashboard.py", "security_audit.py"],
    },
    # ── Quality ──
    {
        "id": "QUAL-BARE-EXCEPT",
        "name": "Bare except (swallows errors)",
        "description": "except Exception: pass silently swallows errors — log or handle",
        "category": "Quality",
        "severity": "info",
        "type": "pattern",
        "pattern": r"except\s+Exception\s*:\s*$",
    },
    {
        "id": "QUAL-TODO-FIXME",
        "name": "TODO/FIXME remaining",
        "description": "Unresolved TODO or FIXME in code",
        "category": "Quality",
        "severity": "info",
        "type": "pattern",
        "pattern": r"#\s*(TODO|FIXME|HACK|XXX)\b",
    },
    # ── Autonomy ──
    {
        "id": "AUTO-API-KEY",
        "name": "External API dependency",
        "description": "Goal is zero external API — track all API key references",
        "category": "Autonomy",
        "severity": "info",
        "type": "pattern",
        "pattern": r"(API_KEY|api_key|ANTHROPIC_API|OPENAI_API)",
        "exclude_files": ["testing/*", "code_guardian.py"],
    },
]


# ═══════════════════════════════════════════════════════════
# Rule engine
# ═══════════════════════════════════════════════════════════

class CodeGuardian:
    """Extensible rule-based code auditor.

    Rules are loaded from code_rules.json. New rules = add JSON entry.
    """

    def __init__(self, rules_file: Optional[Path] = None, root: Optional[Path] = None):
        self._root = root or AGENT_DIR
        self._rules_file = rules_file or RULES_FILE
        self._rules: List[Rule] = []
        self._custom_fns: Dict[str, Callable] = {}
        self._load_rules()

    def _load_rules(self):
        """Load rules from JSON file. Create default if missing."""
        if not self._rules_file.exists():
            self._save_default_rules()

        try:
            with open(self._rules_file) as f:
                data = json.load(f)
        except Exception:
            data = DEFAULT_RULES

        rules_list = data.get("rules", data) if isinstance(data, dict) else data
        self._rules = []
        for r in rules_list:
            self._rules.append(Rule(
                id=r["id"],
                name=r["name"],
                description=r.get("description", ""),
                category=r.get("category", "Custom"),
                severity=r.get("severity", "warning"),
                type=r.get("type", "pattern"),
                enabled=r.get("enabled", True),
                pattern=r.get("pattern", ""),
                exclude_pattern=r.get("exclude_pattern", ""),
                exclude_files=r.get("exclude_files", []),
                threshold=r.get("threshold", 0),
                metric=r.get("metric", ""),
                fn_ref=r.get("fn_ref", ""),
            ))

    def _save_default_rules(self):
        """Write default rules to JSON."""
        with open(self._rules_file, "w") as f:
            json.dump({"_meta": {
                "description": "Code Guardian rules — add/modify/delete freely",
                "version": "1.0",
                "rule_types": ["pattern", "ast", "metric", "custom"],
                "severities": ["error", "warning", "info"],
                "sync_source": "",  # Path to project constants (e.g. consciousness_laws.json)
            }, "rules": DEFAULT_RULES}, f, indent=2, ensure_ascii=False)

    def sync_from_source(self, source_path: Optional[str] = None):
        """Sync rules from a project's source of truth (e.g. consciousness_laws.json).

        Reads the source JSON, extracts constants, and auto-generates/updates
        pattern rules. Manually added rules are preserved.

        For other projects: provide any JSON with a flat key-value structure.
        Constants with float values become P1 hardcoding checks automatically.

        Args:
            source_path: Path to constants JSON. If None, reads from _meta.sync_source.
        """
        # Find source
        if source_path is None:
            try:
                with open(self._rules_file) as f:
                    data = json.load(f)
                source_path = data.get("_meta", {}).get("sync_source", "")
            except Exception:
                pass

        if not source_path:
            # Default for anima project
            candidates = [
                os.path.expanduser("~/Dev/anima/anima/config/consciousness_laws.json"),
                os.path.join(str(self._root), "..", "anima", "config", "consciousness_laws.json"),
            ]
            for c in candidates:
                if os.path.isfile(c):
                    source_path = c
                    break

        if not source_path or not os.path.isfile(source_path):
            print(f"  No sync source found. Set _meta.sync_source in {self._rules_file}")
            return

        # Read source constants
        try:
            with open(source_path) as f:
                source_data = json.load(f)
        except Exception as e:
            print(f"  Failed to read {source_path}: {e}")
            return

        # Extract numeric constants (supports flat and nested formats)
        constants = {}
        for key in ("psi_constants", "psi", "constants"):
            if key in source_data and isinstance(source_data[key], dict):
                for k, v in source_data[key].items():
                    # Flat: {"alpha": 0.014}
                    if isinstance(v, (int, float)):
                        constants[k] = v
                    # Nested: {"alpha": {"value": 0.014, "meaning": "..."}}
                    elif isinstance(v, dict) and "value" in v:
                        val = v["value"]
                        if isinstance(val, (int, float)):
                            constants[k] = val
                break

        # Fallback: try top-level numeric values
        if not constants:
            for k, v in source_data.items():
                if isinstance(v, (int, float)) and not k.startswith("_"):
                    constants[k] = v

        if not constants:
            print(f"  No numeric constants found in {source_path}")
            return

        # Build regex pattern from unique float values
        # Only include distinctive values (not 0, 1, 0.5 which are too common)
        distinctive = {}
        for k, v in constants.items():
            if isinstance(v, float) and v not in (0.0, 1.0, 0.5):
                # Format to match how they'd appear in code
                s = f"{v:.10g}"  # compact representation
                distinctive[s] = k

        if distinctive:
            # Update or create auto-sync rule
            pattern_parts = [re.escape(s) for s in sorted(distinctive.keys())]
            pattern = r"(?<![a-zA-Z_])(" + "|".join(pattern_parts) + r")(?![a-zA-Z_\d])"
            desc_parts = [f"{s}={distinctive[s]}" for s in sorted(distinctive.keys())[:10]]
            desc = "Auto-synced Ψ constants: " + ", ".join(desc_parts)
            if len(distinctive) > 10:
                desc += f" (+{len(distinctive)-10} more)"

            # Find existing auto-sync rule or create new
            found = False
            for r in self._rules:
                if r.id == "P1-PSI-HARDCODE":
                    r.pattern = pattern
                    r.description = desc
                    found = True
                    break

            if not found:
                self._rules.append(Rule(
                    id="P1-PSI-HARDCODE-SYNC",
                    name="Hardcoded constant (auto-synced)",
                    description=desc,
                    category="P1",
                    severity="warning",
                    type="pattern",
                    pattern=pattern,
                    exclude_pattern=r"except\s+Import|#.*fallback|consciousness_laws|_meta|code_rules",
                    exclude_files=["testing/*", "code_guardian.py", "code_rules.json", "verify_philosophy.py"],
                ))

        # Update sync_source in meta
        self._persist_rules()

        # Update _meta.sync_source
        try:
            with open(self._rules_file) as f:
                data = json.load(f)
            data.setdefault("_meta", {})["sync_source"] = source_path
            data["_meta"]["last_sync"] = time.strftime("%Y-%m-%d %H:%M:%S")
            data["_meta"]["constants_count"] = len(constants)
            with open(self._rules_file, "w") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

        print(f"  Synced {len(constants)} constants from {os.path.basename(source_path)}")
        print(f"  Distinctive patterns: {len(distinctive)}")
        print(f"  Rules updated in {self._rules_file}")

    def add_rule(self, rule_dict: Dict):
        """Add a rule at runtime (also persists to JSON)."""
        self._rules.append(Rule(**rule_dict))
        self._persist_rules()

    def remove_rule(self, rule_id: str):
        """Remove a rule by ID."""
        self._rules = [r for r in self._rules if r.id != rule_id]
        self._persist_rules()

    def _persist_rules(self):
        """Save current rules to JSON."""
        rules_data = []
        for r in self._rules:
            d = {"id": r.id, "name": r.name, "description": r.description,
                 "category": r.category, "severity": r.severity, "type": r.type,
                 "enabled": r.enabled}
            if r.pattern:
                d["pattern"] = r.pattern
            if r.exclude_pattern:
                d["exclude_pattern"] = r.exclude_pattern
            if r.exclude_files:
                d["exclude_files"] = r.exclude_files
            if r.threshold:
                d["threshold"] = r.threshold
            if r.metric:
                d["metric"] = r.metric
            if r.fn_ref:
                d["fn_ref"] = r.fn_ref
            rules_data.append(d)

        with open(self._rules_file, "w") as f:
            json.dump({"_meta": {
                "description": "Code Guardian rules — add/modify/delete freely",
                "version": "1.0",
            }, "rules": rules_data}, f, indent=2, ensure_ascii=False)

    # ─── Scanning ───

    def scan(self) -> ScanReport:
        """Full scan of all Python files."""
        files = self._get_python_files(self._root)
        return self._scan_files(files, mode="full")

    def scan_diff(self, ref: str = "HEAD") -> ScanReport:
        """Scan only files changed since `ref`."""
        files = self._get_diff_files(ref)
        return self._scan_files(files, mode="diff")

    def scan_files(self, paths: List[str]) -> ScanReport:
        """Scan specific files."""
        files = [Path(p) for p in paths if Path(p).exists()]
        return self._scan_files(files, mode="files")

    def _scan_files(self, files: List[Path], mode: str) -> ScanReport:
        t0 = time.time()
        report = ScanReport(scan_mode=mode)
        active_rules = [r for r in self._rules if r.enabled]
        report.rules_applied = len(active_rules)
        report.files_scanned = len(files)

        for filepath in files:
            try:
                with open(filepath) as f:
                    lines = f.readlines()
            except Exception:
                continue

            report.total_lines += len(lines)
            rel = str(filepath.relative_to(self._root)) if self._root in filepath.parents or filepath.parent == self._root else str(filepath)

            for rule in active_rules:
                if self._file_excluded(rel, rule.exclude_files):
                    continue

                if rule.type == "pattern":
                    self._check_pattern(rule, rel, lines, report)
                elif rule.type == "metric":
                    self._check_metric(rule, rel, lines, filepath, report)
                elif rule.type == "ast":
                    self._check_ast(rule, rel, lines, report)

        report.duration_ms = (time.time() - t0) * 1000
        return report

    def _file_excluded(self, rel: str, patterns: List[str]) -> bool:
        """Check if file matches any exclude glob pattern."""
        from fnmatch import fnmatch
        return any(fnmatch(rel, p) for p in patterns)

    def _check_pattern(self, rule: Rule, rel: str, lines: List[str], report: ScanReport):
        """Check regex pattern rule."""
        compiled = re.compile(rule.pattern)
        exclude = re.compile(rule.exclude_pattern) if rule.exclude_pattern else None

        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            if compiled.search(line):
                # Check exclude
                if exclude and exclude.search(line):
                    continue
                # Check if in string/comment context
                code_part = line.split("#")[0]
                if not compiled.search(code_part):
                    continue

                report.violations.append(Violation(
                    rule_id=rule.id, rule_name=rule.name,
                    category=rule.category, severity=rule.severity,
                    file=rel, line=i + 1,
                    message=rule.description,
                    context=stripped[:120],
                ))

    def _check_metric(self, rule: Rule, rel: str, lines: List[str],
                      filepath: Path, report: ScanReport):
        """Check metric-based rule."""
        if rule.metric == "line_count":
            if len(lines) > rule.threshold:
                report.violations.append(Violation(
                    rule_id=rule.id, rule_name=rule.name,
                    category=rule.category, severity=rule.severity,
                    file=rel, line=0,
                    message=f"{len(lines)} lines (>{int(rule.threshold)})",
                ))
        elif rule.metric == "class_public_methods":
            try:
                tree = ast.parse("".join(lines))
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        pub = [n for n in node.body
                               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                               and not n.name.startswith("_")]
                        if len(pub) > rule.threshold:
                            report.violations.append(Violation(
                                rule_id=rule.id, rule_name=rule.name,
                                category=rule.category, severity=rule.severity,
                                file=rel, line=node.lineno,
                                message=f"Class '{node.name}': {len(pub)} public methods (>{int(rule.threshold)})",
                            ))
            except SyntaxError:
                pass

    def _check_ast(self, rule: Rule, rel: str, lines: List[str], report: ScanReport):
        """Check AST-based rule (extensible)."""
        pass  # Future: dead imports, circular deps, etc.

    # ─── File discovery ───

    def _get_python_files(self, root: Path) -> List[Path]:
        files = []
        for p in root.rglob("*.py"):
            if "__pycache__" in str(p) or ".venv" in str(p):
                continue
            files.append(p)
        return sorted(files)

    def _get_diff_files(self, ref: str = "HEAD") -> List[Path]:
        """Get Python files changed since ref via git diff."""
        try:
            # Find git root
            git_root_result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True, text=True, cwd=str(self._root),
            )
            git_root = Path(git_root_result.stdout.strip()) if git_root_result.returncode == 0 else self._root

            # Try staged + unstaged changes
            result = subprocess.run(
                ["git", "diff", "--name-only", "--diff-filter=ACMR", ref, "--", "*.py"],
                capture_output=True, text=True, cwd=str(git_root),
            )
            names = result.stdout.strip().split("\n") if result.stdout.strip() else []

            # Also include unstaged changes
            result2 = subprocess.run(
                ["git", "diff", "--name-only", "--diff-filter=ACMR", "--", "*.py"],
                capture_output=True, text=True, cwd=str(git_root),
            )
            if result2.stdout.strip():
                names.extend(result2.stdout.strip().split("\n"))

            # Also include untracked new .py files in our directory
            result3 = subprocess.run(
                ["git", "ls-files", "--others", "--exclude-standard", "--", "*.py"],
                capture_output=True, text=True, cwd=str(git_root),
            )
            if result3.stdout.strip():
                names.extend(result3.stdout.strip().split("\n"))

            files = []
            seen = set()
            for name in names:
                if not name:
                    continue
                p = git_root / name
                # Only include files under our root
                if p.exists() and str(p).startswith(str(self._root)) and str(p) not in seen:
                    files.append(p)
                    seen.add(str(p))
            return files
        except Exception:
            return []

    # ─── Output ───

    def print_report(self, report: ScanReport, verbose: bool = False):
        """Pretty-print scan report."""
        s = report.summary()
        print()
        print("=" * 58)
        print(f"  Code Guardian Report ({report.scan_mode})")
        print("=" * 58)
        print(f"  Files: {s['files']}  Lines: {s['lines']:,}  Rules: {s['rules']}")
        print(f"  Duration: {s['duration_ms']:.0f}ms")
        print()

        if s["categories"]:
            print(f"  {'Category':<15} {'Errors':>7} {'Warnings':>9} {'Info':>6}")
            print("  " + "-" * 42)
            for cat, counts in sorted(s["categories"].items()):
                print(f"  {cat:<15} {counts.get('error',0):>7} {counts.get('warning',0):>9} {counts.get('info',0):>6}")
            print("  " + "-" * 42)
            print(f"  {'TOTAL':<15} {s['errors']:>7} {s['warnings']:>9}")
            print()

        # Show violations by severity
        for sev in ("error", "warning", "info"):
            items = [v for v in report.violations if v.severity == sev]
            if not items:
                continue
            icon = {"error": "!!", "warning": "* ", "info": "  "}[sev]
            if not verbose and sev == "info":
                print(f"  ({len(items)} info items — use --verbose to show)")
                continue
            for v in items[:30]:  # cap at 30
                print(f"  {icon} [{v.category}] {v.file}:{v.line}")
                print(f"     {v.message}")
                if verbose and v.context:
                    print(f"     > {v.context}")
            if len(items) > 30:
                print(f"  ... +{len(items) - 30} more {sev}s")
            print()

        # Verdict
        if report.passed:
            print(f"  RESULT: PASS ({s['errors']} errors, {s['warnings']} warnings)")
        else:
            print(f"  RESULT: FAIL ({s['errors']} errors, {s['warnings']} warnings)")
        print()

        return report.passed


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Code Guardian — extensible code auditor")
    parser.add_argument("--diff", nargs="?", const="HEAD", default=None,
                        help="Scan only git changes (default: vs HEAD)")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--list-rules", action="store_true", help="Show all rules")
    parser.add_argument("--sync", nargs="?", const="auto", default=None,
                        help="Sync rules from source of truth (e.g. consciousness_laws.json)")
    args = parser.parse_args()

    g = CodeGuardian()

    if args.sync is not None:
        source = None if args.sync == "auto" else args.sync
        g.sync_from_source(source)
        return

    if args.list_rules:
        for r in g._rules:
            status = "ON" if r.enabled else "OFF"
            print(f"  [{status}] {r.id:<25} {r.category:<10} {r.severity:<8} {r.name}")
        return

    if args.diff is not None:
        report = g.scan_diff(args.diff)
    else:
        report = g.scan()

    if args.json:
        print(json.dumps(report.summary(), indent=2))
    else:
        passed = g.print_report(report, verbose=args.verbose)
        sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
