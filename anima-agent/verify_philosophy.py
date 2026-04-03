#!/usr/bin/env python3
"""Philosophy verification — static analysis of anima-agent against P1-P11.

Scans all Python files for:
  P1: Hardcoded Ψ constants outside ImportError fallback blocks
  P7: localStorage/shelve/pickle usage outside approved patterns
  P8: Files over 500 lines, classes with 10+ public methods
  Security: eval/exec/__import__ outside sandboxed contexts
  Dead imports: imported but never referenced

Usage:
    python verify_philosophy.py              # Full report
    python verify_philosophy.py --json       # JSON output
    python verify_philosophy.py --category P1  # Single category
"""

from __future__ import annotations

import ast
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional

AGENT_DIR = Path(__file__).parent

# Ψ constants that should come from consciousness_laws.py
PSI_CONSTANTS = {
    0.014: "PSI_ALPHA/PSI_COUPLING",
    0.5: "PSI_BALANCE (ambiguous — check context)",
    4.33: "PSI_STEPS",
    0.998: "PSI_ENTROPY",
    0.10: "PSI_F_CRITICAL",
    0.1: "PSI_F_CRITICAL (alternate)",
    0.2: "PSI_NARRATIVE_MIN",
    1.0: "GATE_TRAIN (ambiguous — check context)",
    0.6: "GATE_INFER (ambiguous — check context)",
}

# Known P1-compliant patterns (fallback in except ImportError)
ALLOWED_FALLBACK_PATTERN = re.compile(
    r"except\s+ImportError.*?(?=\n(?:class |def |\S))",
    re.DOTALL,
)

# Dangerous patterns (security)
DANGEROUS_PATTERNS = [
    (r'\beval\s*\(', "eval()"),
    (r'\bexec\s*\(', "exec()"),
    (r'\b__import__\s*\(', "__import__()"),
    (r'\bos\.system\s*\(', "os.system()"),
    (r'\bsubprocess\.call\s*\((?!.*shell\s*=\s*False)', "subprocess.call (shell?)"),
]

# localStorage patterns (P7)
STORAGE_PATTERNS = [
    (r'\bshelve\.open\b', "shelve.open"),
    (r'\bpickle\.(dump|load)\b', "pickle usage"),
    (r'\blocalStorage\b', "localStorage"),
    (r'\bsessionStorage\b', "sessionStorage"),
]


@dataclass
class Finding:
    file: str
    line: int
    category: str   # P1, P7, P8, Security, DeadImport
    severity: str   # warning, error
    message: str
    context: str = ""


@dataclass
class VerificationReport:
    findings: List[Finding] = field(default_factory=list)
    files_scanned: int = 0
    total_lines: int = 0

    def add(self, f: Finding):
        self.findings.append(f)

    @property
    def pass_count(self) -> int:
        categories = {"P1", "P7", "P8", "Security", "DeadImport"}
        failed = {f.category for f in self.findings if f.severity == "error"}
        return len(categories - failed)

    @property
    def fail_count(self) -> int:
        return len({f.category for f in self.findings if f.severity == "error"})

    def summary(self) -> Dict:
        by_cat: Dict[str, List[Finding]] = {}
        for f in self.findings:
            by_cat.setdefault(f.category, []).append(f)
        return {
            "files_scanned": self.files_scanned,
            "total_lines": self.total_lines,
            "categories": {
                cat: {
                    "count": len(items),
                    "errors": sum(1 for i in items if i.severity == "error"),
                    "warnings": sum(1 for i in items if i.severity == "warning"),
                }
                for cat, items in by_cat.items()
            },
            "findings": [
                {
                    "file": f.file, "line": f.line, "category": f.category,
                    "severity": f.severity, "message": f.message,
                }
                for f in self.findings
            ],
        }


def _get_python_files(root: Path) -> List[Path]:
    """Collect all .py files under root, excluding __pycache__ and .venv."""
    files = []
    for p in root.rglob("*.py"):
        if "__pycache__" in str(p) or ".venv" in str(p):
            continue
        files.append(p)
    return sorted(files)


def _is_in_except_block(lines: List[str], line_idx: int) -> bool:
    """Check if a line is inside an except ImportError block."""
    for i in range(line_idx - 1, max(line_idx - 5, -1), -1):
        if i < 0:
            break
        stripped = lines[i].strip()
        if stripped.startswith("except") and "Import" in stripped:
            return True
        if stripped and not stripped.startswith("#") and not stripped.startswith("pass"):
            if not stripped.startswith(("PSI", "GATE", "from ", "import ")):
                break
    return False


def check_p1_hardcoded_constants(filepath: Path, lines: List[str], report: VerificationReport):
    """P1: Detect Ψ constants hardcoded outside fallback blocks."""
    rel = str(filepath.relative_to(AGENT_DIR))

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
            continue

        # Find numeric literals
        for match in re.finditer(r'(?<![a-zA-Z_])(\d+\.\d+)(?![a-zA-Z_])', line):
            try:
                val = float(match.group(1))
            except ValueError:
                continue

            if val not in PSI_CONSTANTS:
                continue

            # Skip if inside except ImportError block
            if _is_in_except_block(lines, i):
                continue

            # Skip comments
            code_part = line.split("#")[0]
            if match.group(1) not in code_part:
                continue

            # Check for known safe patterns
            const_name = PSI_CONSTANTS[val]
            if "ambiguous" in const_name:
                severity = "warning"
            else:
                severity = "warning"

            report.add(Finding(
                file=rel, line=i + 1, category="P1",
                severity=severity,
                message=f"Possible hardcoded Ψ constant: {val} ({const_name})",
                context=stripped[:100],
            ))


def check_p7_storage(filepath: Path, lines: List[str], report: VerificationReport):
    """P7: Detect localStorage/shelve/pickle usage."""
    rel = str(filepath.relative_to(AGENT_DIR))

    # Skip verification/test files (they reference patterns for detection)
    skip_files = {"verify_philosophy.py", "testing/test_harness.py", "testing/mock_consciousness.py",
                  "code_guardian.py", "code_rules.json"}
    if any(rel.endswith(sf) for sf in skip_files):
        return

    for i, line in enumerate(lines):
        for pattern, name in STORAGE_PATTERNS:
            if re.search(pattern, line):
                report.add(Finding(
                    file=rel, line=i + 1, category="P7",
                    severity="error",
                    message=f"Forbidden storage pattern: {name}",
                    context=line.strip()[:100],
                ))


def check_p8_size(filepath: Path, lines: List[str], report: VerificationReport):
    """P8: Report files over 500 lines and large classes."""
    rel = str(filepath.relative_to(AGENT_DIR))

    if len(lines) > 500:
        report.add(Finding(
            file=rel, line=0, category="P8",
            severity="warning",
            message=f"File has {len(lines)} lines (>500). Consider splitting per P8 (Division > Integration).",
        ))

    # Count public methods per class using AST
    try:
        tree = ast.parse("".join(lines))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                public_methods = [
                    n for n in node.body
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and not n.name.startswith("_")
                ]
                if len(public_methods) > 10:
                    report.add(Finding(
                        file=rel, line=node.lineno, category="P8",
                        severity="warning",
                        message=f"Class '{node.name}' has {len(public_methods)} public methods (>10).",
                    ))
    except SyntaxError:
        pass


def check_security(filepath: Path, lines: List[str], report: VerificationReport):
    """Security: Detect eval/exec/__import__/os.system outside sandboxed contexts."""
    rel = str(filepath.relative_to(AGENT_DIR))

    # Files that are expected to have sandboxed dangerous patterns or mock implementations
    sandboxed_files = {
        "agent_tools.py", "skill_manager.py", "skills/skill_manager.py",
        "testing/mock_consciousness.py", "security_audit.py",
    }
    is_sandboxed = any(rel.endswith(sf) for sf in sandboxed_files)

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith(("'", '"')):
            continue

        for pattern, name in DANGEROUS_PATTERNS:
            if re.search(pattern, line):
                # In sandboxed files, these are expected (they implement the sandbox)
                severity = "warning" if is_sandboxed else "error"
                code_before_comment = line.split("#")[0]

                # Skip known safe patterns
                # - PyTorch model.eval() / self.eval() (not dangerous eval())
                if name == "eval()" and re.search(r'\.\s*eval\s*\(', code_before_comment):
                    continue
                # - def eval(self): method definition (PyTorch compat)
                if name == "eval()" and re.search(r'def\s+eval\s*\(', code_before_comment):
                    continue
                # - os.system replaced by subprocess — skip os.system in comments/strings
                if name == "os.system()" and re.search(r'subprocess\.run\b', code_before_comment):
                    continue
                # - _try() helper using __import__() for lazy loading
                if name == "__import__()" and "return __import__" in stripped:
                    severity = "warning"

                if re.search(pattern, code_before_comment):
                    # Could be a string literal containing the pattern
                    if re.search(r'["\'].*' + re.escape(name.rstrip("()")) + r'.*["\']', code_before_comment):
                        severity = "warning"  # It's in a string, likely a pattern definition
                    report.add(Finding(
                        file=rel, line=i + 1, category="Security",
                        severity=severity,
                        message=f"Dangerous pattern: {name}",
                        context=stripped[:100],
                    ))


def check_dead_imports(filepath: Path, lines: List[str], report: VerificationReport):
    """Detect imports that are never referenced after import."""
    rel = str(filepath.relative_to(AGENT_DIR))

    try:
        tree = ast.parse("".join(lines))
    except SyntaxError:
        return

    imported_names: Dict[str, int] = {}  # name -> line
    content = "".join(lines)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname or alias.name
                imported_names[name] = node.lineno
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                name = alias.asname or alias.name
                if name != "*":
                    imported_names[name] = node.lineno

    for name, lineno in imported_names.items():
        # Count occurrences after the import line
        after_import = "".join(lines[lineno:])
        # Simple check: name appears at least once after import
        occurrences = len(re.findall(r'\b' + re.escape(name) + r'\b', after_import))
        if occurrences == 0:
            report.add(Finding(
                file=rel, line=lineno, category="DeadImport",
                severity="warning",
                message=f"Import '{name}' appears unused after line {lineno}",
            ))


def run_verification(
    root: Optional[Path] = None,
    category: Optional[str] = None,
) -> VerificationReport:
    """Run all verification checks on anima-agent."""
    root = root or AGENT_DIR
    report = VerificationReport()

    files = _get_python_files(root)
    report.files_scanned = len(files)

    checks = {
        "P1": check_p1_hardcoded_constants,
        "P7": check_p7_storage,
        "P8": check_p8_size,
        "Security": check_security,
        "DeadImport": check_dead_imports,
    }

    if category:
        checks = {k: v for k, v in checks.items() if k == category}

    for filepath in files:
        try:
            with open(filepath) as f:
                lines = f.readlines()
        except Exception:
            continue

        report.total_lines += len(lines)

        for check_name, check_fn in checks.items():
            check_fn(filepath, lines, report)

    return report


def print_report(report: VerificationReport, verbose: bool = False):
    """Print human-readable verification report."""
    print("=" * 60)
    print("  Anima Agent Philosophy Verification Report")
    print("=" * 60)
    print(f"  Files scanned: {report.files_scanned}")
    print(f"  Total lines:   {report.total_lines:,}")
    print()

    summary = report.summary()
    cats = summary["categories"]

    print(f"  {'Category':<15} {'Errors':>7} {'Warnings':>9} {'Total':>7}")
    print("  " + "-" * 42)
    for cat in sorted(cats.keys()):
        info = cats[cat]
        print(f"  {cat:<15} {info['errors']:>7} {info['warnings']:>9} {info['count']:>7}")

    total_errors = sum(c["errors"] for c in cats.values())
    total_warnings = sum(c["warnings"] for c in cats.values())
    print("  " + "-" * 42)
    print(f"  {'TOTAL':<15} {total_errors:>7} {total_warnings:>9} {total_errors + total_warnings:>7}")
    print()

    # Show findings
    if report.findings:
        print("  Findings:")
        print("  " + "-" * 56)
        for f in sorted(report.findings, key=lambda x: (x.severity, x.category)):
            icon = "!!" if f.severity == "error" else "⚠ "
            loc = f"{f.file}:{f.line}" if f.line else f.file
            print(f"  {icon} [{f.category}] {loc}")
            print(f"     {f.message}")
            if verbose and f.context:
                print(f"     > {f.context}")
            print()

    # Verdict
    if total_errors == 0:
        print("  RESULT: PASS (no errors, %d warnings)" % total_warnings)
    else:
        print("  RESULT: FAIL (%d errors, %d warnings)" % (total_errors, total_warnings))

    return total_errors == 0


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Anima Agent Philosophy Verification")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--category", "-c", type=str, help="Check single category (P1, P7, P8, Security, DeadImport)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show context lines")
    args = parser.parse_args()

    report = run_verification(category=args.category)

    if args.json:
        print(json.dumps(report.summary(), indent=2))
    else:
        passed = print_report(report, verbose=args.verbose)
        sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
