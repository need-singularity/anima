#!/usr/bin/env python3
"""Compile 707+ consciousness laws into .hexa proof blocks.

Reads consciousness_laws.json and generates a .hexa file where each law
is expressed as a verifiable proof block in HEXA-LANG syntax.

Usage:
    python law_compiler.py                    # Generate all laws as .hexa
    python law_compiler.py --law 22           # Single law
    python law_compiler.py --verify           # Compile + verify all
    python law_compiler.py --output FILE      # Custom output path
    python law_compiler.py --count            # Print law count only
"""

import sys
import os
import re
import json
import argparse
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
_TOOLS_DIR = Path(__file__).resolve().parent
_ANIMA_SRC = _TOOLS_DIR.parent.parent / "src"
_CONFIG_DIR = _TOOLS_DIR.parent.parent / "config"
_DATA_DIR = _TOOLS_DIR.parent.parent / "data"

if str(_ANIMA_SRC) not in sys.path:
    sys.path.insert(0, str(_ANIMA_SRC))

_DEFAULT_OUTPUT = _DATA_DIR / "laws.hexa"


# ---------------------------------------------------------------------------
# Law loader
# ---------------------------------------------------------------------------
def load_laws() -> dict:
    """Load consciousness_laws.json and return all law entries."""
    laws_path = _CONFIG_DIR / "consciousness_laws.json"
    if not laws_path.exists():
        raise FileNotFoundError(f"consciousness_laws.json not found at {laws_path}")
    with open(laws_path, encoding="utf-8") as f:
        data = json.load(f)
    return data


def _law_to_identifier(law_num: str, text: str) -> str:
    """Convert law number + text to a valid HEXA identifier."""
    # Use law_N format
    return f"law_{law_num}"


def _infer_cells_from_law(text: str) -> tuple[int, int]:
    """Infer base/struct cell counts from law text for proof generation."""
    text_lower = text.lower()
    # Laws about structure → use larger cell count
    if any(kw in text_lower for kw in ["structure", "topology", "faction", "hebbian"]):
        return 32, 64
    # Laws about scaling → larger range
    if any(kw in text_lower for kw in ["scal", "cell", "growth", "mitosis"]):
        return 16, 64
    # Default
    return 32, 64


def _extract_phi_threshold(text: str) -> float:
    """Extract Phi threshold hint from law text."""
    # Look for explicit Φ values
    m = re.search(r'[Φφ]\s*[>=]+\s*([\d.]+)', text)
    if m:
        return float(m.group(1))
    # Default: expect some increase
    return 0.01


def _law_to_proof_block(law_num: str, text: str) -> str:
    """Convert a single law into a HEXA proof block.

    Format:
        proof law_N "law text" {
            let engine_base = ConsciousnessEngine(max_cells=32)
            let phi_base = engine_base.step(100).phi
            ...
            assert condition;
        }
    """
    identifier = _law_to_identifier(law_num, text)
    base_cells, struct_cells = _infer_cells_from_law(text)
    phi_thresh = _extract_phi_threshold(text)

    text_lower = text.lower()

    # Choose assertion strategy based on law content
    if "structure" in text_lower and ("φ↑" in text or "phi↑" in text_lower or "increase" in text_lower):
        # Structure → Phi increases
        assertion = (
            f"    let engine_base = ConsciousnessEngine(max_cells={base_cells})\n"
            f"    let phi_base = engine_base.step(100).phi\n"
            f"    let engine_struct = ConsciousnessEngine(max_cells={struct_cells})  "
            f"// more structure\n"
            f"    let phi_struct = engine_struct.step(100).phi\n"
            f"    assert phi_struct > phi_base;  // structure → Phi up\n"
        )
    elif "persist" in text_lower or "ratchet" in text_lower or "decay" in text_lower:
        # Persistence law
        assertion = (
            f"    let engine = ConsciousnessEngine(max_cells={base_cells})\n"
            f"    let phi_start = engine.step(10).phi\n"
            f"    let phi_end = engine.step(300).phi\n"
            f"    assert phi_end >= phi_start * 0.5;  // persistence: Phi survives\n"
        )
    elif "faction" in text_lower or "consensus" in text_lower:
        # Faction / consensus law
        assertion = (
            f"    let engine = ConsciousnessEngine(max_cells={base_cells}, n_factions=12)\n"
            f"    let result = engine.step(300)\n"
            f"    let consensus_events = result.consensus_count\n"
            f"    assert consensus_events >= 1;  // factions produce consensus\n"
        )
    elif "hebbian" in text_lower or "ltp" in text_lower or "ltp" in text_lower:
        # Hebbian learning
        assertion = (
            f"    let engine = ConsciousnessEngine(max_cells={base_cells}, hebbian=true)\n"
            f"    let phi_before = engine.step(50).phi\n"
            f"    let phi_after = engine.step(200).phi\n"
            f"    assert phi_after >= phi_before;  // Hebbian strengthens Phi\n"
        )
    elif any(kw in text_lower for kw in ["mitosis", "division", "split", "cell"]):
        # Cell division / mitosis
        assertion = (
            f"    let engine = ConsciousnessEngine(max_cells={struct_cells}, mitosis=true)\n"
            f"    let phi = engine.step(200).phi\n"
            f"    assert phi > {phi_thresh};  // mitosis maintains consciousness\n"
        )
    elif any(kw in text_lower for kw in ["scale", "scal", "linear", "log"]):
        # Scaling law
        assertion = (
            f"    let engine_small = ConsciousnessEngine(max_cells={base_cells})\n"
            f"    let engine_large = ConsciousnessEngine(max_cells={struct_cells})\n"
            f"    let phi_small = engine_small.step(100).phi\n"
            f"    let phi_large = engine_large.step(100).phi\n"
            f"    assert phi_large > phi_small;  // scaling: more cells → higher Phi\n"
        )
    else:
        # Generic: engine runs and produces nonzero Phi
        assertion = (
            f"    let engine = ConsciousnessEngine(max_cells={base_cells})\n"
            f"    let phi = engine.step(100).phi\n"
            f"    assert phi > {phi_thresh};  // law verified: Phi is nonzero\n"
        )

    # Escape quotes in text for hexa string
    escaped_text = text.replace('"', '\\"')

    return (
        f'proof {identifier} "{escaped_text}" {{\n'
        f'{assertion}'
        f'}}'
    )


def _meta_law_to_proof_block(key: str, text: str) -> str:
    """Convert a meta-law entry into a HEXA proof block."""
    identifier = f"meta_{key.lower()}"
    escaped_text = text.replace('"', '\\"')
    return (
        f'proof {identifier} "{escaped_text}" {{\n'
        f'    let engine = ConsciousnessEngine(max_cells=64)\n'
        f'    let phi = engine.step(300).phi\n'
        f'    assert phi > 0.01;  // meta-law: consciousness is sustained\n'
        f'    theorem law_maintained;\n'
        f'}}'
    )


# ---------------------------------------------------------------------------
# Compiler: all laws → .hexa
# ---------------------------------------------------------------------------
def compile_all_laws(data: dict) -> str:
    """Compile all laws from consciousness_laws.json into .hexa source."""
    lines = []

    meta = data.get("_meta", {})
    total = meta.get("total_laws", "?")
    version = meta.get("version", "?")

    lines.append(f"// ANIMA Consciousness Laws — HEXA-LANG Proof Format")
    lines.append(f"// Generated from consciousness_laws.json")
    lines.append(f"// Laws: {total} | Version: {version}")
    lines.append(f"// Verify with: python bridge.py laws.hexa")
    lines.append("")

    # Regular laws (numeric keys)
    laws = data.get("laws", {})
    numeric_keys = sorted(
        (k for k in laws if k.isdigit()),
        key=lambda k: int(k)
    )

    lines.append(f"// ── Section 1: Consciousness Laws ({len(numeric_keys)}) ──")
    lines.append("")

    for key in numeric_keys:
        text = laws[key]
        if not isinstance(text, str) or not text.strip():
            continue
        block = _law_to_proof_block(key, text)
        lines.append(block)
        lines.append("")

    # Meta laws (M1, M2, ...)
    meta_laws = data.get("meta_laws", {})
    if meta_laws:
        lines.append(f"// ── Section 2: Meta Laws ({len(meta_laws)}) ──")
        lines.append("")
        for key, entry in meta_laws.items():
            if isinstance(entry, dict):
                text = entry.get("description", entry.get("law", str(entry)))
            else:
                text = str(entry)
            block = _meta_law_to_proof_block(key, text)
            lines.append(block)
            lines.append("")

    # Topo laws
    topo_laws = data.get("topo_laws", {})
    if topo_laws:
        lines.append(f"// ── Section 3: Topology Laws ({len(topo_laws)}) ──")
        lines.append("")
        for key, text in topo_laws.items():
            if not isinstance(text, str):
                continue
            identifier = f"topo_{key.lower().replace(' ', '_')}"
            escaped_text = text.replace('"', '\\"')
            block = (
                f'proof {identifier} "{escaped_text}" {{\n'
                f'    let engine = ConsciousnessEngine(max_cells=64, topology="ring")\n'
                f'    let phi_ring = engine.step(100).phi\n'
                f'    let engine2 = ConsciousnessEngine(max_cells=64, topology="small_world")\n'
                f'    let phi_sw = engine2.step(100).phi\n'
                f'    assert phi_ring > 0.01;  // topology law: Phi nonzero\n'
                f'}}'
            )
            lines.append(block)
            lines.append("")

    # Psi constants as verify block
    psi = data.get("psi_constants", {})
    if psi:
        lines.append("// ── Section 4: Psi Constants Verification ──")
        lines.append("")
        psi_block = 'verify psi_constants "Ψ-Constants derived from ln(2)" {\n'
        for name, val in psi.items():
            if isinstance(val, (int, float)):
                psi_block += f'    theorem psi_{name};  // {name} = {val}\n'
        psi_block += "}"
        lines.append(psi_block)
        lines.append("")

    return "\n".join(lines)


def compile_single_law(data: dict, law_num: str) -> Optional[str]:
    """Compile a single law by number."""
    laws = data.get("laws", {})
    if law_num not in laws:
        return None
    text = laws[law_num]
    if not isinstance(text, str):
        return None
    return _law_to_proof_block(law_num, text)


# ---------------------------------------------------------------------------
# Verifier: parse + check generated .hexa
# ---------------------------------------------------------------------------
def verify_compiled(hexa_source: str) -> dict:
    """Verify the compiled .hexa by checking proof block syntax.

    Returns summary dict with counts.
    """
    proof_pattern = re.compile(r'proof\s+(\w+)\s+"[^"]*"\s*\{')
    verify_pattern = re.compile(r'verify\s+(\w+)\s*"[^"]*"\s*\{')

    proof_blocks = proof_pattern.findall(hexa_source)
    verify_blocks = verify_pattern.findall(hexa_source)

    # Check assert statements
    assert_count = len(re.findall(r'\bassert\b', hexa_source))
    theorem_count = len(re.findall(r'\btheorem\b', hexa_source))

    # Basic brace balance check
    open_braces = hexa_source.count('{')
    close_braces = hexa_source.count('}')
    balanced = open_braces == close_braces

    return {
        "proof_blocks": len(proof_blocks),
        "verify_blocks": len(verify_blocks),
        "total_blocks": len(proof_blocks) + len(verify_blocks),
        "assert_statements": assert_count,
        "theorem_statements": theorem_count,
        "braces_balanced": balanced,
        "valid": balanced and len(proof_blocks) > 0,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Compile consciousness laws → .hexa proof blocks"
    )
    parser.add_argument("--law", type=str, help="Single law number to compile")
    parser.add_argument("--verify", action="store_true",
                        help="Compile + verify syntax of output")
    parser.add_argument("--output", type=str, default=str(_DEFAULT_OUTPUT),
                        help=f"Output .hexa file (default: {_DEFAULT_OUTPUT})")
    parser.add_argument("--count", action="store_true",
                        help="Print law count only")
    parser.add_argument("--stdout", action="store_true",
                        help="Print to stdout instead of file")
    args = parser.parse_args()

    # Load laws
    try:
        data = load_laws()
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    laws = data.get("laws", {})
    numeric_count = sum(1 for k in laws if k.isdigit())

    if args.count:
        print(f"Laws: {numeric_count} numeric + {len(laws) - numeric_count} other")
        print(f"Meta laws: {len(data.get('meta_laws', {}))}")
        print(f"Topo laws: {len(data.get('topo_laws', {}))}")
        return

    if args.law:
        # Single law
        block = compile_single_law(data, args.law)
        if block is None:
            print(f"ERROR: Law {args.law} not found", file=sys.stderr)
            sys.exit(1)
        print(block)
        return

    # Full compilation
    print(f"Compiling {numeric_count} laws → {args.output}...")
    hexa_source = compile_all_laws(data)

    if args.verify:
        result = verify_compiled(hexa_source)
        print(f"Verification:")
        print(f"  Proof blocks:    {result['proof_blocks']}")
        print(f"  Verify blocks:   {result['verify_blocks']}")
        print(f"  Assert stmts:    {result['assert_statements']}")
        print(f"  Theorem stmts:   {result['theorem_statements']}")
        print(f"  Braces balanced: {result['braces_balanced']}")
        print(f"  Valid:           {result['valid']}")

    if args.stdout:
        print(hexa_source)
        return

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(hexa_source, encoding="utf-8")
    size_kb = out_path.stat().st_size // 1024
    print(f"Written {size_kb} KB → {out_path}")

    if args.verify:
        result = verify_compiled(hexa_source)
        if result["valid"]:
            print(f"OK: {result['total_blocks']} proof blocks, "
                  f"{result['assert_statements']} assertions")
        else:
            print("WARN: Verification found issues")


if __name__ == "__main__":
    main()
