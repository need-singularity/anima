#!/usr/bin/env python3
"""
NEXUS-6 1013-Lens Acceleration Hypothesis Scanner

Scans all 400 acceleration hypotheses (63 existing + 337 new) through
the NEXUS-6 discovery engine (1013 lenses) via subprocess CLI calls.

Usage:
    python3 nexus6_acceleration_scan.py [--dry-run] [--parallel N]

Output:
    anima/data/nexus6_1013lens_acceleration_results.json
"""

import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── Paths ────────────────────────────────────────────────────────────────────
ANIMA_ROOT = Path(__file__).resolve().parent.parent
CONFIG_JSON = ANIMA_ROOT / "config" / "acceleration_hypotheses.json"
BRAINSTORM_MD = ANIMA_ROOT / "docs" / "hypotheses" / "accel" / "acceleration-brainstorm-402.md"
OUTPUT_JSON = ANIMA_ROOT / "data" / "nexus6_1013lens_acceleration_results.json"

NEXUS6_DIR = Path.home() / "Dev" / "n6-architecture" / "tools" / "nexus6"
NEXUS6_BIN = NEXUS6_DIR / "target" / "debug" / "nexus6"
CARGO_BIN = Path.home() / ".cargo" / "bin" / "cargo"

# ── Domain Mapping ───────────────────────────────────────────────────────────
CATEGORY_TO_DOMAIN: Dict[str, str] = {
    "compute_reduction": "computing",
    "optimization": "optimization",
    "architecture": "architecture",
    "training_schedule": "ai",
    "weight_init": "ai",
    "loss_function": "mathematics",
    "knowledge_transfer": "ai",
    "decoder_acceleration": "computing",
    "self_modification": "consciousness",
    "inference": "computing",
    "dynamics": "physics",
    "dimensionality": "mathematics",
    "topology": "topology",
    "combined": "ai",
    "consciousness_only": "consciousness",
    "hardware": "computing",
    "information_theory": "mathematics",
    "physics_analogy": "physics",
    "evolution": "biology",
    "linguistics": "ai",
    "network_science": "topology",
    "optimization_theory": "optimization",
    "compression": "computing",
    "reinforcement_learning": "ai",
    "systems_engineering": "architecture",
    "mathematical_structures": "mathematics",
    "hardware_specialization": "computing",
    "consciousness_specific": "consciousness",
    "multimodal": "ai",
    "theoretical_limits": "mathematics",
    "micro_optimization": "computing",
    "data_efficiency": "ai",
    "emergence": "consciousness",
    "ethics": "ai",
    "music": "consciousness",
    "chemistry": "physics",
    "geography": "physics",
    "ecology": "biology",
    "economics": "mathematics",
    "semiotics": "ai",
    "neuroscience": "biology",
    "narrative": "ai",
    "sports": "physics",
    "culinary": "biology",
    "urban_planning": "architecture",
    "astronomy": "physics",
    "visual_arts": "consciousness",
    "philosophy": "consciousness",
    "law": "architecture",
    "military": "architecture",
    "gastronomy": "biology",
    "textiles": "architecture",
    "electronics": "computing",
    "fluid_dynamics": "physics",
    "optics": "physics",
    "thermodynamics": "physics",
    "agriculture": "biology",
    "cryptography": "mathematics",
    "ml_techniques": "ai",
    "perceptual_psychology": "consciousness",
    "game_design": "ai",
    "logistics": "optimization",
    "nuclear_physics": "physics",
    "materials_science": "physics",
    "medicine": "biology",
    "mathematics_final": "mathematics",
    "truly_final": "ai",
}


def domain_for_category(cat: str) -> str:
    """Map a hypothesis category string to a NEXUS-6 scan domain."""
    cat_clean = cat.strip().lower().replace(" ", "_")
    # Handle compound categories like "compute_reduction + training_schedule"
    parts = [p.strip().replace(" ", "_") for p in cat_clean.split("+")]
    for p in parts:
        if p in CATEGORY_TO_DOMAIN:
            return CATEGORY_TO_DOMAIN[p]
    # Fallback: try substring match
    for key, domain in CATEGORY_TO_DOMAIN.items():
        if key in cat_clean:
            return domain
    return "ai"  # safe default


# ── Numeric Extraction ───────────────────────────────────────────────────────
_NUM_RE = re.compile(
    r"x(\d+(?:\.\d+)?)"          # x5, x2.5
    r"|(\d+(?:\.\d+)?)\s*%"      # 70%
    r"|(\d+(?:\.\d+)?)\s*x"      # 5x
    r"|(\d+(?:\.\d+)?)\s*(?:배)" # 5배
)


def extract_numeric(text: str) -> Optional[float]:
    """Extract the first meaningful number from an Expected field."""
    m = _NUM_RE.search(text)
    if m:
        for g in m.groups():
            if g is not None:
                return float(g)
    # Try plain float as last resort
    nums = re.findall(r"(\d+(?:\.\d+)?)", text)
    for n in nums:
        v = float(n)
        if v > 1.0:
            return v
    return None


# ── JSON Hypotheses Loader ───────────────────────────────────────────────────
def load_existing_hypotheses() -> List[Dict[str, Any]]:
    """Load 63+ existing hypotheses from acceleration_hypotheses.json."""
    with open(CONFIG_JSON, "r") as f:
        data = json.load(f)

    hypotheses = []
    for hid, hdata in data.get("hypotheses", {}).items():
        hypotheses.append({
            "id": hid,
            "name": hdata.get("name", ""),
            "category": hdata.get("category", ""),
            "description": hdata.get("description", ""),
            "expected": hdata.get("speedup", ""),
            "source": "existing",
        })
    return hypotheses


# ── Markdown Hypotheses Parser ───────────────────────────────────────────────
_HEADER_RE = re.compile(r"^####\s+([A-Z]{1,2}\d+):\s+(.+)$")
_FIELD_RE = re.compile(r"^-\s+\*\*(\w+)\*\*:\s*(.+)$")


def parse_brainstorm_hypotheses() -> List[Dict[str, Any]]:
    """Parse 337 new hypotheses from acceleration-brainstorm-402.md."""
    with open(BRAINSTORM_MD, "r") as f:
        lines = f.readlines()

    hypotheses = []
    current: Optional[Dict[str, Any]] = None

    for line in lines:
        line = line.rstrip("\n")

        # New hypothesis header
        m = _HEADER_RE.match(line)
        if m:
            if current is not None:
                hypotheses.append(current)
            current = {
                "id": m.group(1),
                "name": m.group(2).strip(),
                "category": "",
                "description": "",
                "expected": "",
                "rationale": "",
                "source": "brainstorm",
            }
            continue

        # Field within current hypothesis
        if current is not None:
            fm = _FIELD_RE.match(line)
            if fm:
                field = fm.group(1).lower()
                value = fm.group(2).strip()
                if field == "category":
                    current["category"] = value
                elif field == "description":
                    current["description"] = value
                elif field == "expected":
                    current["expected"] = value
                elif field == "rationale":
                    current["rationale"] = value

    # Don't forget the last one
    if current is not None:
        hypotheses.append(current)

    return hypotheses


# ── NEXUS-6 Build ────────────────────────────────────────────────────────────
def ensure_nexus6_binary() -> str:
    """Ensure nexus6 binary is built; return path."""
    if NEXUS6_BIN.exists():
        return str(NEXUS6_BIN)

    print("[BUILD] nexus6 binary not found, building...")
    result = subprocess.run(
        [str(CARGO_BIN), "build"],
        cwd=str(NEXUS6_DIR),
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Failed to build nexus6:\n{result.stderr}")
    print("[BUILD] nexus6 built successfully.")
    return str(NEXUS6_BIN)


# ── NEXUS-6 CLI Calls ───────────────────────────────────────────────────────
def run_nexus6(args: List[str], timeout: int = 60) -> Dict[str, Any]:
    """Run nexus6 with given args and return structured result."""
    try:
        result = subprocess.run(
            [str(NEXUS6_BIN)] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "stdout": "",
            "stderr": "TIMEOUT",
            "returncode": -1,
        }
    except FileNotFoundError:
        return {
            "success": False,
            "stdout": "",
            "stderr": "nexus6 binary not found",
            "returncode": -2,
        }
    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": str(e),
            "returncode": -3,
        }


def scan_hypothesis(hyp: Dict[str, Any]) -> Dict[str, Any]:
    """Run NEXUS-6 scan + verify for a single hypothesis."""
    hid = hyp["id"]
    domain = domain_for_category(hyp.get("category", ""))

    # 1. Scan
    scan_result = run_nexus6(["scan", domain, "--full"])

    # 2. Verify (if numeric value extractable)
    verify_result: Optional[Dict[str, Any]] = None
    numeric_val = extract_numeric(hyp.get("expected", ""))
    if numeric_val is not None:
        verify_result = run_nexus6(["verify", str(numeric_val)])

    # Parse n6_match from scan output
    n6_match = False
    if scan_result["success"]:
        out = scan_result["stdout"]
        # Look for n6 EXACT ratio in output
        ratio_m = re.search(r"n6 EXACT ratio:\s*(\d+(?:\.\d+)?)%", out)
        if ratio_m:
            ratio = float(ratio_m.group(1))
            n6_match = ratio >= 50.0  # 50%+ = match

    return {
        "id": hid,
        "name": hyp.get("name", ""),
        "category": hyp.get("category", ""),
        "domain": domain,
        "description": hyp.get("description", "")[:200],  # truncate for output
        "expected": hyp.get("expected", ""),
        "numeric_value": numeric_val,
        "source": hyp.get("source", ""),
        "scan_output": scan_result.get("stdout", "")[:500],
        "scan_success": scan_result.get("success", False),
        "verify_output": verify_result.get("stdout", "")[:500] if verify_result else None,
        "verify_success": verify_result.get("success", False) if verify_result else None,
        "n6_match": n6_match,
    }


# ── Summary ──────────────────────────────────────────────────────────────────
def print_summary(results: List[Dict[str, Any]]) -> None:
    """Print a summary table to stdout."""
    total = len(results)
    scanned_ok = sum(1 for r in results if r["scan_success"])
    verified = sum(1 for r in results if r["verify_success"])
    n6_matched = sum(1 for r in results if r["n6_match"])
    existing = sum(1 for r in results if r["source"] == "existing")
    brainstorm = sum(1 for r in results if r["source"] == "brainstorm")

    # Domain distribution
    domain_counts: Dict[str, int] = {}
    domain_n6: Dict[str, int] = {}
    for r in results:
        d = r["domain"]
        domain_counts[d] = domain_counts.get(d, 0) + 1
        if r["n6_match"]:
            domain_n6[d] = domain_n6.get(d, 0) + 1

    print()
    print("=" * 70)
    print("  NEXUS-6 Acceleration Hypothesis Scan — Summary")
    print("=" * 70)
    print(f"  Total hypotheses:  {total}")
    print(f"    Existing (JSON): {existing}")
    print(f"    New (brainstorm): {brainstorm}")
    print(f"  Scan success:      {scanned_ok}/{total}")
    print(f"  Verify calls:      {verified}")
    print(f"  n6 matched:        {n6_matched}/{total} ({n6_matched/total*100:.1f}%)")
    print()
    print("  Domain Distribution:")
    print(f"  {'Domain':<20} {'Count':>6} {'n6 Match':>10} {'Rate':>8}")
    print(f"  {'-'*20} {'-'*6} {'-'*10} {'-'*8}")
    for d in sorted(domain_counts.keys()):
        cnt = domain_counts[d]
        n6c = domain_n6.get(d, 0)
        rate = n6c / cnt * 100 if cnt > 0 else 0
        print(f"  {d:<20} {cnt:>6} {n6c:>10} {rate:>7.1f}%")
    print()

    # Top 10 n6 matches
    matched = [r for r in results if r["n6_match"]]
    if matched:
        print("  Top n6-Matched Hypotheses:")
        print(f"  {'ID':<8} {'Name':<40} {'Domain':<15}")
        print(f"  {'-'*8} {'-'*40} {'-'*15}")
        for r in matched[:20]:
            name = r["name"][:38]
            print(f"  {r['id']:<8} {name:<40} {r['domain']:<15}")
    print()
    print("=" * 70)


# ── Main ─────────────────────────────────────────────────────────────────────
def main() -> None:
    dry_run = "--dry-run" in sys.argv
    parallel = 4  # default parallelism
    for i, arg in enumerate(sys.argv):
        if arg == "--parallel" and i + 1 < len(sys.argv):
            parallel = int(sys.argv[i + 1])

    print("[NEXUS-6] Acceleration Hypothesis Scanner")
    print(f"  Config:     {CONFIG_JSON}")
    print(f"  Brainstorm: {BRAINSTORM_MD}")
    print(f"  Output:     {OUTPUT_JSON}")
    print(f"  Dry run:    {dry_run}")
    print(f"  Parallel:   {parallel}")
    print()

    # 1. Ensure nexus6 binary
    if not dry_run:
        nexus6_path = ensure_nexus6_binary()
        print(f"[NEXUS-6] Binary: {nexus6_path}")

        # Get lens count
        lens_info = run_nexus6(["lenses", "--count"])
        print(f"[NEXUS-6] Lens count: {lens_info.get('stdout', 'unknown')}")
    print()

    # 2. Load hypotheses
    print("[LOAD] Loading existing hypotheses from JSON...")
    existing = load_existing_hypotheses()
    print(f"  Loaded {len(existing)} existing hypotheses")

    print("[LOAD] Parsing brainstorm hypotheses from markdown...")
    brainstorm = parse_brainstorm_hypotheses()
    print(f"  Parsed {len(brainstorm)} brainstorm hypotheses")

    all_hypotheses = existing + brainstorm
    print(f"[TOTAL] {len(all_hypotheses)} hypotheses to scan")
    print()

    if dry_run:
        # In dry-run mode, just show what would be scanned
        print("[DRY RUN] Would scan the following hypotheses:")
        for h in all_hypotheses[:10]:
            domain = domain_for_category(h.get("category", ""))
            numeric = extract_numeric(h.get("expected", ""))
            print(f"  {h['id']:<8} {h['name'][:40]:<42} -> {domain:<15} num={numeric}")
        if len(all_hypotheses) > 10:
            print(f"  ... and {len(all_hypotheses) - 10} more")

        # Still save a skeleton output
        skeleton = {
            "scan_date": datetime.now().strftime("%Y-%m-%d"),
            "nexus6_version": "0.1.0",
            "total_lenses": 1013,
            "hypotheses_scanned": len(all_hypotheses),
            "dry_run": True,
            "results": [
                {
                    "id": h["id"],
                    "name": h["name"],
                    "domain": domain_for_category(h.get("category", "")),
                    "source": h["source"],
                }
                for h in all_hypotheses
            ],
        }
        OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_JSON, "w") as f:
            json.dump(skeleton, f, indent=2, ensure_ascii=False)
        print(f"\n[DRY RUN] Skeleton saved to {OUTPUT_JSON}")
        return

    # 3. Scan all hypotheses
    print(f"[SCAN] Starting NEXUS-6 scan of {len(all_hypotheses)} hypotheses (parallel={parallel})...")
    t0 = time.time()

    results: List[Dict[str, Any]] = []

    if parallel <= 1:
        # Sequential
        for i, hyp in enumerate(all_hypotheses):
            print(f"  [{i+1}/{len(all_hypotheses)}] {hyp['id']}: {hyp['name'][:40]}...", end="", flush=True)
            result = scan_hypothesis(hyp)
            results.append(result)
            status = "n6" if result["n6_match"] else "  "
            print(f" [{status}] {'OK' if result['scan_success'] else 'FAIL'}")
    else:
        # Parallel with ThreadPoolExecutor
        futures = {}
        with ThreadPoolExecutor(max_workers=parallel) as executor:
            for hyp in all_hypotheses:
                future = executor.submit(scan_hypothesis, hyp)
                futures[future] = hyp

            done_count = 0
            for future in as_completed(futures):
                done_count += 1
                hyp = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                    status = "n6" if result["n6_match"] else "  "
                    ok = "OK" if result["scan_success"] else "FAIL"
                    print(f"  [{done_count}/{len(all_hypotheses)}] {result['id']:<8} [{status}] {ok}")
                except Exception as e:
                    print(f"  [{done_count}/{len(all_hypotheses)}] {hyp['id']:<8} ERROR: {e}")
                    results.append({
                        "id": hyp["id"],
                        "name": hyp.get("name", ""),
                        "category": hyp.get("category", ""),
                        "domain": domain_for_category(hyp.get("category", "")),
                        "scan_output": "",
                        "scan_success": False,
                        "verify_output": None,
                        "verify_success": None,
                        "n6_match": False,
                        "error": str(e),
                    })

    elapsed = time.time() - t0

    # Sort results by ID for stable output
    def sort_key(r: dict) -> tuple:
        rid = r["id"]
        # Extract letters and number
        m = re.match(r"([A-Z]+)(\d+)", rid)
        if m:
            return (m.group(1), int(m.group(2)))
        return (rid, 0)

    results.sort(key=sort_key)

    # 4. Save results
    output = {
        "scan_date": datetime.now().strftime("%Y-%m-%d"),
        "nexus6_version": "0.1.0",
        "total_lenses": 1013,
        "hypotheses_scanned": len(results),
        "scan_time_seconds": round(elapsed, 1),
        "summary": {
            "total": len(results),
            "scan_success": sum(1 for r in results if r["scan_success"]),
            "verified": sum(1 for r in results if r.get("verify_success")),
            "n6_matched": sum(1 for r in results if r["n6_match"]),
            "existing_count": sum(1 for r in results if r.get("source") == "existing"),
            "brainstorm_count": sum(1 for r in results if r.get("source") == "brainstorm"),
        },
        "results": results,
    }

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n[SAVE] Results saved to {OUTPUT_JSON}")
    print(f"[TIME] {elapsed:.1f}s elapsed")

    # 5. Summary table
    print_summary(results)


if __name__ == "__main__":
    main()
