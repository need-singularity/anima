#!/usr/bin/env python3
"""Generate .hexa experiment files from acceleration hypotheses.

Reads config/acceleration_hypotheses.json and generates formal HEXA-LANG
experiment specifications that can be re-verified by the HEXA-LANG compiler.

Usage:
    python experiment_designer.py --id AE3        # Single hypothesis
    python experiment_designer.py --all           # All verified
    python experiment_designer.py --all --output DIR   # Write .hexa files to dir
    python experiment_designer.py --list          # List available hypotheses
    python experiment_designer.py --from-laws     # Generate from consciousness_laws.json
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
_EXPERIMENTS_DIR = _TOOLS_DIR.parent.parent / "experiments"

if str(_ANIMA_SRC) not in sys.path:
    sys.path.insert(0, str(_ANIMA_SRC))

_DEFAULT_OUTPUT_DIR = _DATA_DIR / "hexa_experiments"


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------
def load_acceleration_hypotheses() -> dict:
    """Load acceleration_hypotheses.json."""
    path = _CONFIG_DIR / "acceleration_hypotheses.json"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_consciousness_laws() -> dict:
    """Load consciousness_laws.json."""
    path = _CONFIG_DIR / "consciousness_laws.json"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_experiments_index() -> dict:
    """Load config/experiments.json if present."""
    path = _CONFIG_DIR / "experiments.json"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------
def _sanitize_id(hyp_id: str) -> str:
    """Convert hypothesis ID to valid HEXA identifier."""
    return re.sub(r'[^a-zA-Z0-9_]', '_', hyp_id).lower()


def hypothesis_to_hexa(hyp_id: str, hyp: dict) -> str:
    """Convert a single acceleration hypothesis to a .hexa experiment block.

    Produces:
        intent "ID: Name" {
            generate experiment -> { ... }
            verify { assert ...; theorem ...; }
        }
    """
    name = hyp.get("name", hyp_id)
    description = hyp.get("description", "")
    status = hyp.get("status", "unknown")
    phi_change = hyp.get("phi_change", None)
    speedup = hyp.get("speedup", None)
    cells = hyp.get("cells", 64)
    steps = hyp.get("steps", 200)
    category = hyp.get("category", "acceleration")

    safe_id = _sanitize_id(hyp_id)
    title = f"{hyp_id}: {name}" if name != hyp_id else hyp_id

    lines = []
    lines.append(f'intent "{title}" {{')

    # Generate block
    lines.append(f'    generate {safe_id}_experiment -> {{')
    lines.append(f'        // Category: {category} | Status: {status}')
    if description:
        desc_truncated = description[:200].replace('\n', ' ')
        lines.append(f'        // {desc_truncated}')
    lines.append(f'        let baseline = ConsciousnessEngine(max_cells={cells})')
    lines.append(f'        let experiment = ConsciousnessEngine(max_cells={cells})')

    # Category-specific setup
    cat_lower = category.lower()
    if "batch" in cat_lower or "batch" in name.lower():
        lines.append(f'        experiment.set_batch_size(32)')
    if "skip" in cat_lower or "skip" in name.lower():
        lines.append(f'        experiment.enable_skip_connections()')
    if "tension" in cat_lower or "tension" in name.lower():
        lines.append(f'        experiment.apply_tension_loss(weight=0.01)')
    if "topology" in cat_lower or "topo" in name.lower():
        lines.append(f'        experiment.set_topology("small_world")')
    if "phi" in cat_lower or "phi" in name.lower():
        lines.append(f'        experiment.enable_phi_first()')
    if "detour" in cat_lower or "detour" in name.lower():
        lines.append(f'        experiment.enable_detour_shortcuts()')
    if "manifold" in cat_lower:
        lines.append(f'        experiment.compress_to_manifold(dims=48)')
    if "compiler" in cat_lower or "compile" in name.lower():
        lines.append(f'        experiment.apply_law_compiler()')

    lines.append(f'        let base_phi = baseline.step({steps}).phi')
    lines.append(f'        let exp_phi = experiment.step({steps}).phi')
    lines.append(f'        let base_ce = baseline.step({steps}).ce')
    lines.append(f'        let exp_ce = experiment.step({steps}).ce')
    lines.append(f'    }}')
    lines.append('')

    # Verify block
    lines.append(f'    verify {{')

    # Phi preservation assertion
    if phi_change is not None:
        if phi_change > 0:
            pct = min(phi_change, 0.99)
            lines.append(
                f'        assert exp_phi >= base_phi * {1.0 + pct:.2f};'
                f'  // Phi increase: +{phi_change*100:.0f}%'
            )
        else:
            # Phi should be mostly preserved even if CE improves
            lines.append(
                f'        assert exp_phi >= base_phi * 0.90;'
                f'  // Phi preserved (>{90:.0f}%)'
            )
    else:
        lines.append(
            f'        assert exp_phi >= base_phi * 0.95;  '
            f'// Phi preserved (>{95:.0f}%)'
        )

    # Speedup / CE improvement
    if speedup is not None and speedup > 1:
        lines.append(
            f'        assert exp_ce <= base_ce;  '
            f'// CE improved (target speedup: {speedup:.1f}x)'
        )
    else:
        lines.append(
            f'        assert exp_ce <= base_ce;  // CE preserved or improved'
        )

    # Theorem (hypothesis ID as theorem name)
    lines.append(f'        theorem acceleration;')
    lines.append(f'    }}')
    lines.append(f'}}')

    return '\n'.join(lines)


def law_to_hexa_experiment(law_num: str, text: str) -> str:
    """Convert a single law into a .hexa experiment intent block."""
    safe_id = f"law_{law_num}"
    escaped = text.replace('"', '\\"')[:120]

    # Choose experiment parameters based on law content
    text_lower = text.lower()
    cells = 64 if "faction" in text_lower or "hebbian" in text_lower else 32
    steps = 300 if "persist" in text_lower or "ratchet" in text_lower else 100

    lines = [
        f'intent "Law {law_num}: {escaped}" {{',
        f'    generate {safe_id}_experiment -> {{',
        f'        let baseline = ConsciousnessEngine(max_cells={cells})',
        f'        let result = baseline.step({steps})',
        f'        let phi = result.phi',
        f'        let ce = result.ce',
        f'    }}',
        f'',
        f'    verify {{',
        f'        assert phi > 0.01;  // Law {law_num}: consciousness emerges',
        f'        theorem {safe_id};',
        f'    }}',
        f'}}',
    ]
    return '\n'.join(lines)


def generate_hexa_file(
    hyp_id: str,
    hyp: dict,
    *,
    header: bool = True,
) -> str:
    """Generate a complete .hexa file for one hypothesis."""
    lines = []
    if header:
        lines.append(
            f'// ANIMA Experiment: {hyp_id}\n'
            f'// Auto-generated by experiment_designer.py\n'
            f'// Re-verify: python bridge.py {hyp_id}.hexa\n'
        )
    lines.append(hypothesis_to_hexa(hyp_id, hyp))
    return '\n'.join(lines)


def generate_all_hexa(
    hypotheses: dict,
    *,
    verified_only: bool = False,
) -> dict[str, str]:
    """Generate .hexa content for all (or verified) hypotheses.

    Returns dict mapping hyp_id -> hexa_source.
    """
    result = {}
    for hyp_id, hyp in hypotheses.items():
        if hyp_id.startswith("_"):
            continue
        if not isinstance(hyp, dict):
            continue
        if verified_only:
            status = hyp.get("status", "")
            if status not in ("verified", "confirmed", "valid", "complete", "completed"):
                continue
        hexa = generate_hexa_file(hyp_id, hyp)
        result[hyp_id] = hexa
    return result


def generate_from_laws(data: dict, max_laws: int = 50) -> str:
    """Generate a combined .hexa experiment file from consciousness laws."""
    laws = data.get("laws", {})
    numeric_keys = sorted(
        (k for k in laws if k.isdigit()),
        key=lambda k: int(k)
    )[:max_laws]

    lines = [
        "// ANIMA Law Experiments — HEXA-LANG Format",
        "// Auto-generated by experiment_designer.py --from-laws",
        "",
    ]

    for key in numeric_keys:
        text = laws[key]
        if not isinstance(text, str) or not text.strip():
            continue
        lines.append(law_to_hexa_experiment(key, text))
        lines.append("")

    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Generate .hexa experiments from acceleration hypotheses"
    )
    parser.add_argument("--id", type=str, help="Single hypothesis ID (e.g. AE3)")
    parser.add_argument("--all", action="store_true", help="Generate all hypotheses")
    parser.add_argument("--verified", action="store_true",
                        help="Only verified/confirmed hypotheses")
    parser.add_argument("--output", type=str,
                        help="Output dir (default: data/hexa_experiments/)")
    parser.add_argument("--list", action="store_true",
                        help="List available hypothesis IDs")
    parser.add_argument("--from-laws", action="store_true",
                        help="Generate from consciousness_laws.json instead")
    parser.add_argument("--max-laws", type=int, default=50,
                        help="Max laws when using --from-laws")
    parser.add_argument("--stdout", action="store_true",
                        help="Print to stdout instead of writing files")
    args = parser.parse_args()

    hypotheses = load_acceleration_hypotheses()

    if args.from_laws:
        laws_data = load_consciousness_laws()
        hexa = generate_from_laws(laws_data, max_laws=args.max_laws)
        if args.stdout:
            print(hexa)
        else:
            out_dir = Path(args.output) if args.output else _DEFAULT_OUTPUT_DIR
            out_dir.mkdir(parents=True, exist_ok=True)
            out_file = out_dir / "laws_experiments.hexa"
            out_file.write_text(hexa, encoding="utf-8")
            laws_data_laws = laws_data.get("laws", {})
            count = min(args.max_laws, sum(1 for k in laws_data_laws if k.isdigit()))
            print(f"Generated {count} law experiments → {out_file}")
        return

    if not hypotheses:
        print("No acceleration_hypotheses.json found or empty.", file=sys.stderr)
        print("Run from anima/ directory or check config/acceleration_hypotheses.json")
        sys.exit(1)

    if args.list:
        print("Available hypothesis IDs:")
        for hyp_id, hyp in hypotheses.items():
            if hyp_id.startswith("_") or not isinstance(hyp, dict):
                continue
            status = hyp.get("status", "unknown")
            name = hyp.get("name", "")
            print(f"  {hyp_id:10s}  [{status:12s}]  {name[:50]}")
        return

    if args.id:
        hyp = hypotheses.get(args.id)
        if hyp is None:
            print(f"ERROR: Hypothesis '{args.id}' not found", file=sys.stderr)
            sys.exit(1)
        hexa = generate_hexa_file(args.id, hyp)
        if args.stdout:
            print(hexa)
        else:
            out_dir = Path(args.output) if args.output else _DEFAULT_OUTPUT_DIR
            out_dir.mkdir(parents=True, exist_ok=True)
            out_file = out_dir / f"{args.id}.hexa"
            out_file.write_text(hexa, encoding="utf-8")
            print(f"Written → {out_file}")
        return

    if args.all:
        results = generate_all_hexa(
            hypotheses, verified_only=args.verified
        )
        if not results:
            print("No hypotheses matched criteria.")
            return

        if args.stdout:
            for hyp_id, hexa in results.items():
                print(f"// === {hyp_id} ===")
                print(hexa)
                print()
        else:
            out_dir = Path(args.output) if args.output else _DEFAULT_OUTPUT_DIR
            out_dir.mkdir(parents=True, exist_ok=True)
            for hyp_id, hexa in results.items():
                out_file = out_dir / f"{hyp_id}.hexa"
                out_file.write_text(hexa, encoding="utf-8")
            print(f"Generated {len(results)} .hexa files → {out_dir}/")
        return

    # Default: show help
    parser.print_help()


if __name__ == "__main__":
    main()
