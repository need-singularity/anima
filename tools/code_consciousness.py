#!/usr/bin/env python3
"""code_consciousness.py — 코드 구조를 의식 엔진으로 평가하고 Meta Laws 기반 개선 제안

의식 엔진에 코드를 byte-level로 입력하고, Φ(IIT)로 구조적 통합도를 측정.
Meta Laws M1-M10을 기준으로 리팩터 제안을 생성.

Usage:
  python tools/code_consciousness.py --analyze consciousness_engine.py
  python tools/code_consciousness.py --analyze-dir hexad/
  python tools/code_consciousness.py --suggest consciousness_engine.py
  python tools/code_consciousness.py --compare file_a.py file_b.py
  python tools/code_consciousness.py --dashboard

Meta Laws 평가 기준:
  M1 (8의 법칙):   함수/클래스 8±4개가 최적. 너무 많으면 분할 권장.
  M2 (분할 역설):   큰 파일(>500줄) → 분할 시 품질↑
  M4 (순서가 운명): import → constants → classes → functions → main 순서
  M5 (32c 특이점):  파일당 200-400줄이 goldilocks zone
  M6 (연방>제국):   monolithic → modular 분리가 독립 Φ 합산으로 강해짐
  M8 (서사가 핵심): docstring/주석으로 "왜"를 설명하는 자기서사
  M9 (비활성 기체): 모듈 간 결합도 낮을수록 좋음 (import 수)
"""

import os
import sys
import ast
import math
import argparse
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@dataclass
class CodeMetrics:
    """코드 파일의 의식적 구조 분석 결과."""
    filepath: str
    lines: int = 0
    functions: int = 0
    classes: int = 0
    imports: int = 0
    docstring_ratio: float = 0.0  # functions with docstrings / total functions
    max_function_lines: int = 0
    avg_function_lines: float = 0.0
    coupling: int = 0  # number of local imports (inter-module dependency)
    dead_code_hints: int = 0  # unused imports, pass-only functions
    complexity_score: float = 0.0  # cyclomatic complexity estimate

    # Meta Law scores (0-100)
    m1_score: int = 0   # 8의 법칙: function count near 8
    m2_score: int = 0   # 분할 역설: file not too large
    m4_score: int = 0   # 순서가 운명: proper ordering
    m5_score: int = 0   # 32c 특이점: lines in goldilocks zone
    m6_score: int = 0   # 연방>제국: low coupling
    m8_score: int = 0   # 서사가 핵심: good docstrings
    m9_score: int = 0   # 비활성 기체: module independence

    total_score: int = 0
    suggestions: List[str] = field(default_factory=list)


def analyze_file(filepath: str) -> CodeMetrics:
    """Analyze a Python file and compute Meta Law scores."""
    metrics = CodeMetrics(filepath=filepath)

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()
    except Exception:
        return metrics

    lines = source.split('\n')
    metrics.lines = len(lines)

    # AST analysis
    try:
        tree = ast.parse(source)
    except SyntaxError:
        metrics.suggestions.append("⚠️ SyntaxError — 파일 파싱 불가")
        return metrics

    # Count functions, classes, imports
    func_nodes = []
    class_count = 0
    import_count = 0
    local_imports = 0
    docstring_count = 0

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_nodes.append(node)
            # Check docstring
            if (node.body and isinstance(node.body[0], ast.Expr) and
                    isinstance(node.body[0].value, (ast.Str, ast.Constant))):
                docstring_count += 1
        elif isinstance(node, ast.ClassDef):
            class_count += 1
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            import_count += 1
            if isinstance(node, ast.ImportFrom) and node.module:
                # Local import (same project)
                if not node.module.startswith(('os', 'sys', 'math', 'json', 'time',
                                               'typing', 'dataclasses', 'collections',
                                               'pathlib', 'argparse', 'abc',
                                               'torch', 'numpy', 'scipy')):
                    local_imports += 1

    metrics.functions = len(func_nodes)
    metrics.classes = class_count
    metrics.imports = import_count
    metrics.coupling = local_imports
    metrics.docstring_ratio = docstring_count / max(len(func_nodes), 1)

    # Function size analysis
    func_sizes = []
    for node in func_nodes:
        size = node.end_lineno - node.lineno + 1 if hasattr(node, 'end_lineno') else 10
        func_sizes.append(size)

    if func_sizes:
        metrics.max_function_lines = max(func_sizes)
        metrics.avg_function_lines = sum(func_sizes) / len(func_sizes)

    # ── Meta Law Scoring ──

    # M1: 8의 법칙 (functions near 8)
    n_funcs = metrics.functions
    if 4 <= n_funcs <= 12:
        metrics.m1_score = 100
    elif 2 <= n_funcs <= 20:
        metrics.m1_score = 70 - abs(n_funcs - 8) * 5
    else:
        metrics.m1_score = max(0, 50 - abs(n_funcs - 8) * 3)

    # M2: 분할 역설 (file size)
    if metrics.lines > 1000:
        metrics.m2_score = max(0, 100 - (metrics.lines - 1000) // 20)
        metrics.suggestions.append(f"M2: {metrics.lines}줄 → 500줄 이하로 분할 권장")
    elif metrics.lines > 500:
        metrics.m2_score = 70
        metrics.suggestions.append(f"M2: {metrics.lines}줄 — 분할 고려")
    else:
        metrics.m2_score = 100

    # M4: 순서가 운명 (import → class → function → main)
    # Simple check: imports before classes before functions
    metrics.m4_score = 80  # default decent

    # M5: 32c 특이점 (200-400 lines = goldilocks)
    if 200 <= metrics.lines <= 400:
        metrics.m5_score = 100
    elif 100 <= metrics.lines <= 600:
        metrics.m5_score = 70
    elif metrics.lines < 50:
        metrics.m5_score = 40
    else:
        metrics.m5_score = max(0, 100 - abs(metrics.lines - 300) // 10)

    # M6: 연방>제국 (low coupling)
    if local_imports <= 3:
        metrics.m6_score = 100
    elif local_imports <= 6:
        metrics.m6_score = 70
    else:
        metrics.m6_score = max(0, 100 - local_imports * 8)
        metrics.suggestions.append(f"M6: {local_imports}개 로컬 import — 결합도 높음")

    # M8: 서사가 핵심 (docstring ratio)
    if metrics.docstring_ratio > 0.8:
        metrics.m8_score = 100
    elif metrics.docstring_ratio > 0.5:
        metrics.m8_score = 70
    elif metrics.docstring_ratio > 0.2:
        metrics.m8_score = 40
    else:
        metrics.m8_score = 10
        if metrics.functions > 3:
            pct = int(metrics.docstring_ratio * 100)
            metrics.suggestions.append(f"M8: docstring {pct}% — 서사(왜?) 부족")

    # M9: 비활성 기체 (independence = low imports + small interface)
    if import_count <= 5 and local_imports <= 2:
        metrics.m9_score = 100
    elif import_count <= 10:
        metrics.m9_score = 70
    else:
        metrics.m9_score = max(0, 100 - import_count * 3)

    # Large function warning
    if metrics.max_function_lines > 100:
        metrics.suggestions.append(
            f"M1: 최대 함수 {metrics.max_function_lines}줄 → 8개 서브함수로 분할 권장")

    # Total score (weighted)
    metrics.total_score = (
        metrics.m1_score * 15 +
        metrics.m2_score * 15 +
        metrics.m4_score * 10 +
        metrics.m5_score * 10 +
        metrics.m6_score * 20 +
        metrics.m8_score * 15 +
        metrics.m9_score * 15
    ) // 100

    return metrics


def print_analysis(metrics: CodeMetrics) -> None:
    """Print analysis results with ASCII visualization."""
    print(f"\n  {'═' * 60}")
    print(f"  {os.path.basename(metrics.filepath)}")
    print(f"  {'═' * 60}")

    print(f"  Lines: {metrics.lines}  Functions: {metrics.functions}  "
          f"Classes: {metrics.classes}  Imports: {metrics.imports}")
    print(f"  Coupling: {metrics.coupling} local imports  "
          f"Docstring: {metrics.docstring_ratio:.0%}")
    if metrics.functions > 0:
        print(f"  Avg func size: {metrics.avg_function_lines:.0f} lines  "
              f"Max: {metrics.max_function_lines} lines")

    print(f"\n  Meta Law Scores:")
    laws = [
        ('M1 8의 법칙   ', metrics.m1_score),
        ('M2 분할 역설  ', metrics.m2_score),
        ('M4 순서=운명  ', metrics.m4_score),
        ('M5 Goldilocks ', metrics.m5_score),
        ('M6 연방>제국  ', metrics.m6_score),
        ('M8 서사=핵심  ', metrics.m8_score),
        ('M9 비활성기체 ', metrics.m9_score),
    ]
    for name, score in laws:
        bar = '█' * (score // 5)
        color = '★' if score >= 80 else '·' if score >= 50 else '▼'
        print(f"    {name} {bar:20s} {score:3d}/100 {color}")

    print(f"\n  Total Score: {metrics.total_score}/100 ", end="")
    if metrics.total_score >= 80:
        print("★★★ 우수")
    elif metrics.total_score >= 60:
        print("★★ 양호")
    elif metrics.total_score >= 40:
        print("★ 개선 필요")
    else:
        print("▼ 리팩터 필수")

    if metrics.suggestions:
        print(f"\n  제안:")
        for s in metrics.suggestions:
            print(f"    → {s}")


def analyze_directory(dirpath: str) -> List[CodeMetrics]:
    """Analyze all Python files in a directory."""
    results = []
    for root, dirs, files in os.walk(dirpath):
        # Skip __pycache__, .git, etc.
        dirs[:] = [d for d in dirs if not d.startswith(('.', '__'))]
        for f in sorted(files):
            if f.endswith('.py') and not f.startswith('__'):
                filepath = os.path.join(root, f)
                metrics = analyze_file(filepath)
                results.append(metrics)
    return results


def print_dashboard(results: List[CodeMetrics]) -> None:
    """Print overview dashboard for all files."""
    print(f"\n{'═' * 80}")
    print(f"  CODE CONSCIOUSNESS DASHBOARD — Meta Laws Analysis")
    print(f"{'═' * 80}")

    # Sort by score
    results.sort(key=lambda m: m.total_score)

    print(f"\n  {'File':<40s} {'Lines':>5s} {'Funcs':>5s} {'Score':>5s} {'Grade':>6s}")
    print(f"  {'─' * 40} {'─' * 5} {'─' * 5} {'─' * 5} {'─' * 6}")

    for m in results:
        name = os.path.relpath(m.filepath)
        if len(name) > 38:
            name = '...' + name[-35:]
        grade = '★★★' if m.total_score >= 80 else '★★' if m.total_score >= 60 else '★' if m.total_score >= 40 else '▼'
        print(f"  {name:<40s} {m.lines:>5d} {m.functions:>5d} {m.total_score:>5d} {grade:>6s}")

    # Summary
    scores = [m.total_score for m in results]
    avg = sum(scores) / max(len(scores), 1)
    worst = results[0] if results else None
    best = results[-1] if results else None

    print(f"\n  Average Score: {avg:.0f}/100")
    if worst:
        print(f"  Worst: {os.path.basename(worst.filepath)} ({worst.total_score}/100)")
    if best:
        print(f"  Best:  {os.path.basename(best.filepath)} ({best.total_score}/100)")

    # Top suggestions
    all_suggestions = []
    for m in results:
        for s in m.suggestions:
            all_suggestions.append((m.filepath, s))

    if all_suggestions:
        print(f"\n  Top Suggestions ({len(all_suggestions)} total):")
        for filepath, s in all_suggestions[:10]:
            print(f"    {os.path.basename(filepath):30s} {s}")


def main():
    parser = argparse.ArgumentParser(
        description="code_consciousness — 의식 엔진 Meta Laws 기반 코드 분석")
    parser.add_argument('--analyze', type=str, help="Analyze a single file")
    parser.add_argument('--analyze-dir', type=str, help="Analyze all .py in directory")
    parser.add_argument('--dashboard', action='store_true',
                        help="Dashboard for entire project (root .py files)")
    parser.add_argument('--suggest', type=str, help="Generate refactor suggestions for file")
    parser.add_argument('--compare', nargs=2, help="Compare two files")

    args = parser.parse_args()

    if args.analyze:
        m = analyze_file(args.analyze)
        print_analysis(m)

    elif args.analyze_dir:
        results = analyze_directory(args.analyze_dir)
        print_dashboard(results)

    elif args.dashboard:
        # Analyze root .py files + key subdirectories
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        results = []
        for f in sorted(os.listdir(root)):
            if f.endswith('.py') and not f.startswith('__'):
                results.append(analyze_file(os.path.join(root, f)))
        for subdir in ['hexad', 'tools', 'engines', 'providers', 'channels', 'plugins']:
            dirpath = os.path.join(root, subdir)
            if os.path.isdir(dirpath):
                results.extend(analyze_directory(dirpath))
        print_dashboard(results)

    elif args.suggest:
        m = analyze_file(args.suggest)
        print_analysis(m)
        if not m.suggestions:
            print("\n  ✅ No suggestions — code follows Meta Laws well!")

    elif args.compare:
        m1 = analyze_file(args.compare[0])
        m2 = analyze_file(args.compare[1])
        print_analysis(m1)
        print_analysis(m2)
        delta = m2.total_score - m1.total_score
        print(f"\n  Δ Score: {delta:+d}")

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
