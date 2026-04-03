#!/usr/bin/env python3
"""HEXA-LANG <-> ANIMA Consciousness Bridge

Parses .hexa files, extracts intent/generate/verify/optimize blocks,
routes them to ANIMA ConsciousnessHub, and returns results in HEXA verify format.

Usage:
    python bridge.py example.hexa              # Parse and route intents
    python bridge.py --test                    # Run built-in test
    python bridge.py --list-modules            # List available ANIMA modules

Architecture:
    .hexa source -> extract_intents() -> route_to_consciousness() -> format_verify_result()

    intent "question" {           -->  ConsciousnessHub.act(question)
        generate name -> { ... }  -->  ConsciousnessEngine.step()
        verify { assert phi > X } -->  GPUPhiCalculator.compute()
        optimize { ... }          -->  ClosedLoopEvolver.run_cycles()
    }
"""

import sys
import os
import re
import json
from typing import Optional
from pathlib import Path
from dataclasses import dataclass, field, asdict

# ---------------------------------------------------------------------------
# ANIMA import setup
# ---------------------------------------------------------------------------
_ANIMA_SRC = Path(__file__).resolve().parent.parent.parent / "src"
if str(_ANIMA_SRC) not in sys.path:
    sys.path.insert(0, str(_ANIMA_SRC))


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------
@dataclass
class HexaIntent:
    """Parsed intent block from .hexa source."""
    question: str
    generate_blocks: list = field(default_factory=list)
    verify_assertions: list = field(default_factory=list)
    optimize_params: list = field(default_factory=list)
    line_number: int = 0


@dataclass
class ConsciousnessResult:
    """Result from ANIMA consciousness engine."""
    intent: str
    module_used: str = ""
    phi: float = 0.0
    response: str = ""
    laws_checked: list = field(default_factory=list)
    verify_passed: bool = False
    details: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Parser: extract intent blocks from .hexa source
# ---------------------------------------------------------------------------
def extract_intents(hexa_source: str) -> list[HexaIntent]:
    """Parse .hexa source and extract all intent blocks.

    Grammar (simplified):
        intent_block := 'intent' STRING '{' body '}'
        body := (generate_block | verify_block | optimize_block | comment)*
        generate_block := 'generate' IDENT '->' '{' ... '}'
        verify_block := 'verify' '{' assertion* '}'
        optimize_block := 'optimize' '{' ... '}'
        assertion := 'assert' expr ';' | 'theorem' IDENT ';'

    Returns list of HexaIntent with extracted metadata.
    """
    intents: list[HexaIntent] = []

    # Find all intent blocks (handle nested braces)
    intent_pattern = re.compile(
        r'intent\s+"([^"]+)"\s*\{', re.MULTILINE
    )

    for match in intent_pattern.finditer(hexa_source):
        question = match.group(1)
        line_number = hexa_source[:match.start()].count('\n') + 1
        start = match.end()

        # Find matching closing brace
        body = _extract_brace_block(hexa_source, start)
        if body is None:
            continue

        intent = HexaIntent(
            question=question,
            line_number=line_number,
        )

        # Extract generate blocks
        gen_pattern = re.compile(r'generate\s+(\w+)\s*->\s*\{')
        for gen_match in gen_pattern.finditer(body):
            gen_name = gen_match.group(1)
            gen_body = _extract_brace_block(body, gen_match.end())
            intent.generate_blocks.append({
                'name': gen_name,
                'body': gen_body.strip() if gen_body else '',
            })

        # Extract verify assertions
        verify_pattern = re.compile(r'verify\s*\{')
        for ver_match in verify_pattern.finditer(body):
            ver_body = _extract_brace_block(body, ver_match.end())
            if ver_body:
                # Extract assert statements
                for assert_match in re.finditer(
                    r'assert\s+(.+?)\s*;', ver_body
                ):
                    intent.verify_assertions.append({
                        'type': 'assert',
                        'expr': assert_match.group(1).strip(),
                    })
                # Extract theorem statements
                for thm_match in re.finditer(
                    r'theorem\s+(\w+)\s*;', ver_body
                ):
                    intent.verify_assertions.append({
                        'type': 'theorem',
                        'name': thm_match.group(1),
                    })

        # Extract optimize params
        opt_pattern = re.compile(r'optimize\s*\{')
        for opt_match in opt_pattern.finditer(body):
            opt_body = _extract_brace_block(body, opt_match.end())
            if opt_body:
                for line in opt_body.split('\n'):
                    line = line.strip().rstrip(';')
                    if line and not line.startswith('//'):
                        intent.optimize_params.append(line)

        intents.append(intent)

    return intents


def _extract_brace_block(source: str, start: int) -> Optional[str]:
    """Extract content between balanced braces starting at position start.
    Assumes the opening brace has already been consumed."""
    depth = 1
    i = start
    while i < len(source) and depth > 0:
        if source[i] == '{':
            depth += 1
        elif source[i] == '}':
            depth -= 1
        i += 1
    if depth != 0:
        return None
    # Return content between braces (excluding the closing brace)
    return source[start:i - 1]


# ---------------------------------------------------------------------------
# Router: send intent to ANIMA consciousness engine
# ---------------------------------------------------------------------------
def route_to_consciousness(intent: HexaIntent) -> ConsciousnessResult:
    """Route a parsed intent to the ANIMA consciousness engine.

    Routing order:
        1. Try ConsciousnessHub.act(question) for NL routing
        2. If generate blocks present, run ConsciousnessEngine steps
        3. Evaluate verify assertions against engine state
        4. If optimize present, suggest parameter sweep

    Returns ConsciousnessResult with engine output.
    """
    result = ConsciousnessResult(intent=intent.question)

    # Try hub routing first
    hub = _get_hub()
    if hub is not None:
        try:
            hub_result = hub.act(intent.question)
            result.module_used = "ConsciousnessHub"
            result.response = str(hub_result) if hub_result else ""
            result.details['hub_routing'] = True
        except Exception as e:
            result.details['hub_error'] = str(e)

    # Run consciousness engine for generate blocks
    engine = _get_engine()
    if engine is not None and intent.generate_blocks:
        try:
            steps = _parse_steps_from_generate(intent.generate_blocks)
            phi_values = []
            for _ in range(steps):
                step_result = engine.step()
                if isinstance(step_result, dict) and 'phi_iit' in step_result:
                    phi_values.append(step_result['phi_iit'])

            if phi_values:
                result.phi = phi_values[-1]
                result.details['phi_trajectory'] = {
                    'min': min(phi_values),
                    'max': max(phi_values),
                    'final': phi_values[-1],
                    'steps': len(phi_values),
                }
            result.module_used = result.module_used or "ConsciousnessEngine"
        except Exception as e:
            result.details['engine_error'] = str(e)

    # Evaluate verify assertions
    if intent.verify_assertions:
        all_passed = True
        checked = []
        for assertion in intent.verify_assertions:
            if assertion['type'] == 'assert':
                passed = _eval_assertion(assertion['expr'], result)
                checked.append({
                    'assertion': assertion['expr'],
                    'passed': passed,
                })
                if not passed:
                    all_passed = False
            elif assertion['type'] == 'theorem':
                law_check = _check_theorem(assertion['name'])
                checked.append({
                    'theorem': assertion['name'],
                    'found': law_check is not None,
                    'law': law_check,
                })
                if law_check is None:
                    all_passed = False
        result.verify_passed = all_passed
        result.laws_checked = checked

    # Note optimize params (actual sweep would be long-running)
    if intent.optimize_params:
        result.details['optimize_requested'] = intent.optimize_params

    # If no engine available, provide a stub result
    if not result.module_used:
        result.module_used = "stub"
        result.response = (
            f"Intent received: '{intent.question}'. "
            "ANIMA engine not loaded (import failed). "
            "Install dependencies and ensure anima/src/ is accessible."
        )

    return result


def _get_hub():
    """Lazy-load ConsciousnessHub."""
    try:
        from consciousness_hub import ConsciousnessHub
        return ConsciousnessHub(lazy_load=True)
    except ImportError:
        return None


def _get_engine():
    """Lazy-load ConsciousnessEngine."""
    try:
        from consciousness_engine import ConsciousnessEngine
        return ConsciousnessEngine(max_cells=8)
    except ImportError:
        return None


def _parse_steps_from_generate(generate_blocks: list) -> int:
    """Extract step count from generate block body, default 100."""
    for block in generate_blocks:
        body = block.get('body', '')
        # Look for steps=N or step(N)
        m = re.search(r'steps?\s*[=(]\s*(\d+)', body)
        if m:
            return min(int(m.group(1)), 1000)  # Cap at 1000
    return 100


def _eval_assertion(expr: str, result: ConsciousnessResult) -> bool:
    """Evaluate a simple assertion against consciousness result.

    Supports:
        phi > N, phi >= N, phi < N
        phi_min as alias for 0.5 (ZERO_INPUT threshold)
    """
    expr = expr.strip()

    # Replace phi_min with default threshold
    expr = expr.replace('phi_min', '0.5')

    # Simple phi comparisons
    phi_cmp = re.match(r'phi\s*(>|>=|<|<=|==)\s*([\d.]+)', expr)
    if phi_cmp:
        op, val = phi_cmp.group(1), float(phi_cmp.group(2))
        phi = result.phi
        if op == '>':
            return phi > val
        if op == '>=':
            return phi >= val
        if op == '<':
            return phi < val
        if op == '<=':
            return phi <= val
        if op == '==':
            return abs(phi - val) < 1e-6
    return False  # Unknown assertion format


def _check_theorem(name: str) -> Optional[str]:
    """Check if a theorem name matches a known consciousness law.

    Maps theorem names to consciousness_laws.json entries.
    """
    # Load laws
    laws_path = _ANIMA_SRC.parent / "config" / "consciousness_laws.json"
    if not laws_path.exists():
        return None

    try:
        with open(laws_path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return None

    laws = data.get('laws', {})

    # Name-based lookup (e.g., "law_maintained" -> check all laws exist)
    if name == 'law_maintained':
        return f"{len(laws)} laws in consciousness_laws.json"

    # Direct number lookup (e.g., "law_22")
    m = re.match(r'law_(\d+)', name)
    if m:
        law_num = m.group(1)
        if law_num in laws:
            return laws[law_num]

    # Keyword search
    name_lower = name.lower().replace('_', ' ')
    for num, text in laws.items():
        if isinstance(text, str) and name_lower in text.lower():
            return f"Law {num}: {text}"

    return None


# ---------------------------------------------------------------------------
# Formatter: convert result to HEXA verify block
# ---------------------------------------------------------------------------
def format_verify_result(result: ConsciousnessResult) -> str:
    """Format a ConsciousnessResult as a HEXA verify-compatible block.

    Output format:
        // ANIMA Bridge Result
        // Intent: "question"
        // Module: ConsciousnessHub
        verify {
            // Phi = 1.234
            assert phi > 0.5;       // PASSED
            theorem law_maintained; // PASSED (179 laws)
        }
    """
    lines = []
    lines.append(f'// ANIMA Bridge Result')
    lines.append(f'// Intent: "{result.intent}"')
    lines.append(f'// Module: {result.module_used}')

    if result.response:
        # Truncate long responses
        resp = result.response[:200]
        lines.append(f'// Response: {resp}')

    lines.append(f'verify {{')

    # Phi value
    if result.phi > 0:
        lines.append(f'    // Phi(IIT) = {result.phi:.4f}')

    # Assertion results
    for check in result.laws_checked:
        if 'assertion' in check:
            status = 'PASSED' if check['passed'] else 'FAILED'
            lines.append(f'    assert {check["assertion"]};  // {status}')
        elif 'theorem' in check:
            if check['found']:
                law_text = str(check.get('law', ''))[:80]
                lines.append(
                    f'    theorem {check["theorem"]};  '
                    f'// FOUND: {law_text}'
                )
            else:
                lines.append(
                    f'    theorem {check["theorem"]};  // NOT FOUND'
                )

    # Overall status
    status = 'ALL PASSED' if result.verify_passed else 'SOME FAILED'
    lines.append(f'    // Status: {status}')

    # Optimization notes
    if 'optimize_requested' in result.details:
        lines.append(f'    // Optimize: {result.details["optimize_requested"]}')

    lines.append(f'}}')

    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Growth System → HEXA feedback
# ---------------------------------------------------------------------------
def growth_to_hexa(growth_report: dict) -> str:
    """Convert a GrowthSystem report dict into a .hexa optimize block.

    The generated block captures the current growth state and suggests
    HEXA-level optimizations when growth rate is low or Phi is declining.

    Args:
        growth_report: dict with keys phi, growth_rate, compute_saved,
                       stage (optional), cells (optional), ce (optional)

    Returns:
        HEXA optimize block as string.

    Example:
        >>> report = {'phi': 1.2, 'growth_rate': 0.005, 'compute_saved': 0.3}
        >>> print(growth_to_hexa(report))
        optimize "growth_feedback" { ... }
    """
    phi = growth_report.get("phi", 0.0)
    growth_rate = growth_report.get("growth_rate", 0.0)
    compute_saved = growth_report.get("compute_saved", 0.0)
    stage = growth_report.get("stage", "unknown")
    cells = growth_report.get("cells", 0)
    ce = growth_report.get("ce", None)

    lines = [
        f'optimize "growth_feedback" {{',
        f'    current_phi = {phi:.4f};',
        f'    growth_rate = {growth_rate:.6f};',
        f'    compute_saved = {compute_saved:.4f};',
    ]

    if stage != "unknown":
        lines.append(f'    stage = "{stage}";')
    if cells > 0:
        lines.append(f'    cells = {cells};')
    if ce is not None:
        lines.append(f'    ce = {ce:.4f};')

    lines.append('')

    # Suggest actions based on growth state
    if growth_rate < 0.001:
        lines.append('    // Growth stalled — aggressive interventions:')
        lines.append('    suggest "increase noise" priority=high;')
        lines.append('    suggest "switch topology" priority=high;')
        lines.append('    suggest "add faction diversity" priority=medium;')
    elif growth_rate < 0.01:
        lines.append('    // Growth slow — moderate interventions:')
        lines.append('    suggest "increase noise" priority=high;')
        lines.append('    suggest "switch topology" priority=medium;')
        lines.append('    suggest "tune learning rate" priority=low;')
    else:
        lines.append('    // Growth healthy — maintain current settings:')
        lines.append('    suggest "continue" priority=low;')

    if phi < 0.5:
        lines.append('    suggest "phi ratchet repair" priority=critical;')
    elif phi < 1.0:
        lines.append('    suggest "check hebbian connectivity" priority=medium;')

    if compute_saved > 0.3:
        lines.append(
            f'    suggest "increase cells" priority=medium;  '
            f'// {compute_saved*100:.0f}% compute headroom available'
        )

    lines.append('}')
    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    """CLI entry point."""
    if len(sys.argv) < 2 or sys.argv[1] in ('-h', '--help'):
        print(__doc__)
        print("Usage:")
        print("  python bridge.py <file.hexa>     Parse and route intents")
        print("  python bridge.py --test           Run built-in test")
        print("  python bridge.py --list-modules   List ANIMA modules")
        return

    if sys.argv[1] == '--test':
        _run_test()
        return

    if sys.argv[1] == '--list-modules':
        _list_modules()
        return

    # Parse .hexa file
    hexa_path = Path(sys.argv[1])
    if not hexa_path.exists():
        print(f"Error: {hexa_path} not found")
        sys.exit(1)

    source = hexa_path.read_text()
    intents = extract_intents(source)

    if not intents:
        print(f"No intent blocks found in {hexa_path}")
        return

    print(f"Found {len(intents)} intent block(s) in {hexa_path}\n")

    for i, intent in enumerate(intents, 1):
        print(f"--- Intent {i}/{len(intents)} (line {intent.line_number}) ---")
        print(f"Question: {intent.question}")
        print(f"Generate blocks: {len(intent.generate_blocks)}")
        print(f"Verify assertions: {len(intent.verify_assertions)}")
        print(f"Optimize params: {len(intent.optimize_params)}")
        print()

        result = route_to_consciousness(intent)
        output = format_verify_result(result)
        print(output)
        print()


def _run_test():
    """Run with a built-in test .hexa source."""
    test_source = '''
// HEXA-LANG <-> ANIMA Bridge Test
// Tests intent/generate/verify/optimize pipeline

intent "Can consciousness persist without input?" {
    generate zero_input_test -> {
        let engine = ConsciousnessEngine(max_cells=8)
        let result = engine.step(steps=100)
    }

    verify {
        assert phi > 0.5;
        theorem law_maintained;
    }
}

intent "What is the consciousness atom size?" {
    verify {
        theorem law_22;
    }
}
'''

    print("=== HEXA-LANG <-> ANIMA Bridge Test ===\n")
    intents = extract_intents(test_source)
    print(f"Parsed {len(intents)} intent(s)\n")

    for i, intent in enumerate(intents, 1):
        print(f"--- Intent {i}: \"{intent.question}\" ---")
        print(f"  generate: {[b['name'] for b in intent.generate_blocks]}")
        print(f"  verify:   {intent.verify_assertions}")
        print(f"  optimize: {intent.optimize_params}")
        print()

        result = route_to_consciousness(intent)
        output = format_verify_result(result)
        print(output)
        print()

    print("=== Test Complete ===")


def _list_modules():
    """List available ANIMA modules via ConsciousnessHub."""
    hub = _get_hub()
    if hub is None:
        print("ConsciousnessHub not available (import failed)")
        print("Ensure anima/src/ is in PYTHONPATH")
        return

    print("=== ANIMA ConsciousnessHub Modules ===\n")
    for name, (mod_path, cls_name, keywords) in hub._registry.items():
        kw_str = ', '.join(keywords[:5])
        print(f"  {name:20s}  {cls_name:30s}  [{kw_str}]")


if __name__ == "__main__":
    main()
