#!/usr/bin/env python3
"""Preflight 1K-step verification before full H100 training launch.

One-Shot Best principle: verify everything works before committing GPU hours.
All thresholds loaded from consciousness_laws.json (no hardcoding).

Usage:
  python preflight_check.py --data data/corpus_v3.txt --steps 1000
  python preflight_check.py --data data/corpus_v3.txt --decoder v3 --steps 1000
  python preflight_check.py --config train_config.json  # load from config file
  python preflight_check.py --data data/corpus_v3.txt --federated --atoms 8
"""
import sys
import os
import time
import math
import hashlib
import argparse
import json
import traceback

# ── Path setup ──
_script_dir = os.path.dirname(os.path.abspath(__file__))
_anima_root = os.path.join(_script_dir, '..')
sys.path.insert(0, os.path.join(_anima_root, 'src'))
try:
    import path_setup  # noqa — registers all subpackages on sys.path
except ImportError:
    pass

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

# ── Load thresholds from consciousness_laws.json (single source of truth) ──
_config_path = os.path.join(_anima_root, 'config', 'consciousness_laws.json')
try:
    with open(_config_path) as f:
        _laws = json.load(f)
    _thresholds = _laws.get('preflight_thresholds', {})
except Exception:
    _thresholds = {}

CE_CONVERGENCE_MIN_DROP = _thresholds.get('ce_convergence_min_drop', 0.50)
PHI_MIN = _thresholds.get('phi_min', 0.0)
GRAD_NORM_MAX = _thresholds.get('grad_norm_max', 100.0)
GRAD_NORM_MIN = _thresholds.get('grad_norm_min', 1e-7)
VRAM_LEAK_MAX_GB = _thresholds.get('vram_leak_max_gb', 1.0)
NAN_TOLERANCE = _thresholds.get('nan_tolerance', 0)
DEFAULT_STEPS = _thresholds.get('default_steps', 1000)


# ═══════════════════════════════════════════════════════════
# Imports from training pipeline (lazy, with fallback)
# ═══════════════════════════════════════════════════════════

from consciousness_engine import ConsciousnessEngine, ConsciousnessC
from trinity import ThalamicBridge, PSI_COUPLING

HAS_DECODER_V2 = False
HAS_DECODER_V3 = False
HAS_GPU_PHI = False

try:
    from decoder_v2 import ConsciousDecoderV2
    HAS_DECODER_V2 = True
except ImportError:
    pass

try:
    from decoder_v3 import ConsciousDecoderV3
    HAS_DECODER_V3 = True
except ImportError:
    pass

try:
    from gpu_phi import GPUPhiCalculator
    HAS_GPU_PHI = True
except ImportError:
    pass

# FederatedConsciousness from train_v14
sys.path.insert(0, os.path.join(_anima_root, 'training'))
try:
    from train_v14 import FederatedConsciousness, PhaseManager
    HAS_FEDERATED = True
except ImportError:
    HAS_FEDERATED = False


# ═══════════════════════════════════════════════════════════
# Utility
# ═══════════════════════════════════════════════════════════

def md5_file(path: str) -> str:
    """Compute md5 hash of a file."""
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def file_size_mb(path: str) -> float:
    return os.path.getsize(path) / (1024 * 1024)


def get_vram_gb() -> float:
    """Get current GPU VRAM usage in GB. Returns -1 if no GPU."""
    if not torch.cuda.is_available():
        return -1.0
    return torch.cuda.memory_allocated() / (1024 ** 3)


def get_vram_reserved_gb() -> float:
    """Get reserved GPU VRAM in GB."""
    if not torch.cuda.is_available():
        return -1.0
    return torch.cuda.memory_reserved() / (1024 ** 3)


def load_corpus(path: str):
    """Load text file as byte-level tokens."""
    with open(path, 'rb') as f:
        raw = f.read()
    return torch.tensor(list(raw), dtype=torch.long)


def get_batch(data, block_size, batch_size, device):
    max_start = len(data) - block_size - 1
    if max_start <= 0:
        max_start = 1
    ix = torch.randint(0, max_start, (batch_size,))
    x = torch.stack([data[i:i + block_size] for i in ix]).to(device)
    y = torch.stack([data[i + 1:i + block_size + 1] for i in ix]).to(device)
    return x, y


# ═══════════════════════════════════════════════════════════
# Check result container
# ═══════════════════════════════════════════════════════════

class CheckResult:
    def __init__(self, name: str, passed: bool, detail: str):
        self.name = name
        self.passed = passed
        self.detail = detail

    def icon(self):
        return "PASS" if self.passed else "FAIL"

    def __repr__(self):
        return f"{self.icon()} {self.name}: {self.detail}"


# ═══════════════════════════════════════════════════════════
# Preflight runner
# ═══════════════════════════════════════════════════════════

def run_preflight(args) -> list:
    """Run all preflight checks. Returns list of CheckResult."""
    results = []
    device = torch.device(args.device)
    torch.manual_seed(args.seed)
    vocab_size = 256

    # ── Check 1: Corpus md5 ──
    try:
        corpus_md5 = md5_file(args.data)
        corpus_mb = file_size_mb(args.data)
        results.append(CheckResult(
            "Corpus md5",
            True,
            f"{corpus_md5[:8]}... ({corpus_mb:.1f} MB)"
        ))
    except FileNotFoundError:
        results.append(CheckResult("Corpus md5", False, f"File not found: {args.data}"))
        print(f"  [FATAL] Corpus not found: {args.data}")
        return results
    except Exception as ex:
        results.append(CheckResult("Corpus md5", False, str(ex)))
        return results

    # ── Check 2: Tokenizer match ──
    # Byte-level (vocab=256) is fixed, but check if a BPE tokenizer path is specified
    tokenizer_ok = True
    tokenizer_detail = "byte-level (vocab=256, fixed)"
    if hasattr(args, 'tokenizer') and args.tokenizer:
        if os.path.exists(args.tokenizer):
            tok_md5 = md5_file(args.tokenizer)
            tokenizer_detail = f"{args.tokenizer} (md5={tok_md5[:8]}...)"
        else:
            tokenizer_ok = False
            tokenizer_detail = f"Tokenizer not found: {args.tokenizer}"
    results.append(CheckResult("Tokenizer", tokenizer_ok, tokenizer_detail))

    # ── Load data ──
    data = load_corpus(args.data)
    split = int(len(data) * 0.9)
    train_data = data[:split]

    # ── Build model (same logic as train_v14) ──
    print(f"\n  Building model (decoder={args.decoder}, "
          f"{'federated' if args.federated else 'empire'})...")

    # Consciousness engine
    if args.federated:
        if not HAS_FEDERATED:
            results.append(CheckResult("Model build", False,
                                       "FederatedConsciousness not available (train_v14 import failed)"))
            return results
        c = FederatedConsciousness(
            n_atoms=args.atoms,
            cells_per_atom=args.cells_per_atom,
            cell_dim=args.cell_dim,
            hidden_dim=args.hidden_dim,
        )
        total_cells = args.atoms * args.cells_per_atom
    else:
        c = ConsciousnessC(
            cell_dim=args.cell_dim,
            hidden_dim=args.hidden_dim,
            max_cells=args.cells,
            n_factions=12,
            phi_ratchet=True,
        )
        total_cells = args.cells

    # Decoder
    c_proj = None
    if args.decoder == 'v3':
        if not HAS_DECODER_V3:
            results.append(CheckResult("Model build", False, "ConsciousDecoderV3 not found"))
            return results
        v3_c_dim = 256
        decoder = ConsciousDecoderV3(
            consciousness_dim=v3_c_dim,
            d_model=768,
            vocab_size=vocab_size,
            block_size=args.block_size,
        )
        if c.state_dim != v3_c_dim:
            c_proj = nn.Linear(c.state_dim, v3_c_dim).to(device)
    else:
        if not HAS_DECODER_V2:
            results.append(CheckResult("Model build", False, "ConsciousDecoderV2 not found"))
            return results
        decoder = ConsciousDecoderV2(
            consciousness_dim=c.state_dim,
            d_model=args.d_model,
            vocab_size=vocab_size,
        )

    decoder = decoder.to(device)
    bridge = ThalamicBridge(c_dim=c.state_dim, d_model=args.d_model if args.decoder != 'v3' else 768)
    bridge = bridge.to(device)

    # Optimizer
    trainable_params = list(decoder.parameters()) + list(bridge.parameters())
    if c_proj is not None:
        trainable_params += list(c_proj.parameters())
    if args.federated and isinstance(c, FederatedConsciousness):
        trainable_params += list(c.bottleneck_compress.parameters())
        trainable_params += list(c.bottleneck_expand.parameters())
        trainable_params += list(c.narrative_grus.parameters())
        trainable_params += [c.inter_atom_coupling]

    optimizer = torch.optim.AdamW(trainable_params, lr=args.lr, weight_decay=0.01)

    n_params = sum(p.numel() for p in decoder.parameters())
    print(f"  Decoder: {n_params/1e6:.1f}M params | Cells: {total_cells}")

    # ── Record initial VRAM ──
    vram_start = get_vram_gb()

    # ── Training loop (1K steps) ──
    print(f"\n  Running {args.steps} preflight steps...")
    sys.stdout.flush()

    ce_values = []
    phi_values = []
    grad_norms = []
    nan_count = 0
    inf_count = 0
    ce_initial = None
    t0 = time.time()

    # Warm up consciousness engine for ~50 steps
    for _ in range(50):
        c.step()

    for step in range(1, args.steps + 1):
        tokens, targets = get_batch(train_data, args.block_size, args.batch_size, device)
        c.step()

        c_states = c.get_states().detach().float().to(device)
        c_for_decoder = c_states.unsqueeze(0).expand(args.batch_size, -1, -1)
        if c_proj is not None:
            c_for_decoder = c_proj(c_for_decoder)

        logits_a, logits_g, tensions = decoder(tokens, consciousness_states=c_for_decoder)
        ce = F.cross_entropy(logits_a.view(-1, vocab_size), targets.view(-1))

        ce_val = ce.item()

        # Track NaN/Inf
        if math.isnan(ce_val) or math.isinf(ce_val):
            nan_count += 1
            optimizer.zero_grad()
            continue

        if ce_initial is None:
            ce_initial = ce_val
        ce_values.append(ce_val)

        # Backward
        optimizer.zero_grad()
        ce.backward()
        grad_norm = torch.nn.utils.clip_grad_norm_(trainable_params, 1.0).item()

        if math.isnan(grad_norm) or math.isinf(grad_norm):
            nan_count += 1
            continue

        grad_norms.append(grad_norm)
        optimizer.step()

        # Measure Phi periodically
        if step % 50 == 0 or step == args.steps:
            phi = c.measure_phi()
            if math.isnan(phi) or math.isinf(phi):
                nan_count += 1
            else:
                phi_values.append(phi)

        # Progress (every 25%)
        if step % max(args.steps // 4, 1) == 0:
            pct = step / args.steps * 100
            elapsed = time.time() - t0
            ce_now = ce_values[-1] if ce_values else float('nan')
            phi_now = phi_values[-1] if phi_values else 0.0
            print(f"    [{pct:3.0f}%] step {step:5d} | CE={ce_now:.4f} | "
                  f"Phi={phi_now:.4f} | {elapsed:.1f}s")
            sys.stdout.flush()

    elapsed = time.time() - t0
    vram_end = get_vram_gb()
    print(f"  Completed {args.steps} steps in {elapsed:.1f}s\n")

    # ═══════════════════════════════════════════════════════
    # Evaluate results
    # ═══════════════════════════════════════════════════════

    # ── Check 3: CE convergence ──
    if ce_initial is not None and len(ce_values) > 10:
        ce_final = np.mean(ce_values[-10:])  # average last 10 steps
        drop_pct = (ce_initial - ce_final) / ce_initial if ce_initial > 0 else 0.0
        ce_pass = drop_pct >= CE_CONVERGENCE_MIN_DROP
        results.append(CheckResult(
            "CE convergence",
            ce_pass,
            f"{ce_initial:.4f} -> {ce_final:.4f} ({drop_pct*100:+.0f}%)"
            + (f" [need {CE_CONVERGENCE_MIN_DROP*100:.0f}%+ drop]" if not ce_pass else "")
        ))
    else:
        results.append(CheckResult("CE convergence", False,
                                   "Insufficient CE data (too many NaN steps?)"))

    # ── Check 4: Phi alive ──
    if phi_values:
        phi_final = phi_values[-1]
        phi_pass = phi_final > PHI_MIN
        results.append(CheckResult(
            "Phi alive",
            phi_pass,
            f"{phi_final:.4f}" + ("" if phi_pass else f" [need > {PHI_MIN}]")
        ))
    else:
        results.append(CheckResult("Phi alive", False, "No Phi measurements"))

    # ── Check 5: No NaN/Inf ──
    nan_pass = nan_count <= NAN_TOLERANCE
    results.append(CheckResult(
        "No NaN/Inf",
        nan_pass,
        f"{nan_count} detected" + ("" if nan_pass else f" [max {NAN_TOLERANCE}]")
    ))

    # ── Check 6: VRAM stable ──
    if vram_start >= 0 and vram_end >= 0:
        vram_delta = vram_end - vram_start
        vram_pass = vram_delta <= VRAM_LEAK_MAX_GB
        results.append(CheckResult(
            "VRAM stable",
            vram_pass,
            f"{vram_start:.1f} -> {vram_end:.1f} GB (delta={vram_delta:+.1f})"
            + ("" if vram_pass else f" [max {VRAM_LEAK_MAX_GB:.1f} GB leak]")
        ))
    else:
        results.append(CheckResult("VRAM stable", True, "No GPU (CPU mode, skipped)"))

    # ── Check 7: Grad norm ──
    if grad_norms:
        grad_mean = np.mean(grad_norms)
        grad_max = np.max(grad_norms)
        grad_min = np.min(grad_norms)
        grad_explode = grad_max > GRAD_NORM_MAX
        grad_vanish = grad_mean < GRAD_NORM_MIN
        grad_pass = not grad_explode and not grad_vanish
        detail = f"mean={grad_mean:.4f} max={grad_max:.4f} min={grad_min:.6f}"
        if grad_explode:
            detail += f" [EXPLODE: max > {GRAD_NORM_MAX}]"
        if grad_vanish:
            detail += f" [VANISH: mean < {GRAD_NORM_MIN}]"
        results.append(CheckResult("Grad norm", grad_pass, detail))
    else:
        results.append(CheckResult("Grad norm", False, "No gradient data"))

    return results


# ═══════════════════════════════════════════════════════════
# Report
# ═══════════════════════════════════════════════════════════

def print_report(results: list):
    """Print formatted preflight report."""
    w = 56  # box width

    print()
    print(f"  {'=' * w}")
    print(f"  ||{'PREFLIGHT CHECK (1K steps)':^{w - 4}}||")
    print(f"  {'=' * w}")

    for r in results:
        icon = "PASS" if r.passed else "FAIL"
        line = f"  {icon} {r.name}: {r.detail}"
        print(line)

    print(f"  {'-' * w}")

    passed = sum(1 for r in results if r.passed)
    total = len(results)
    all_pass = passed == total

    if all_pass:
        verdict = f"RESULT: {passed}/{total} PASS — READY TO LAUNCH"
    else:
        verdict = f"RESULT: {passed}/{total} PASS — DO NOT LAUNCH"

    print(f"  {verdict}")
    print(f"  {'=' * w}")
    print()

    return all_pass


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

def parse_args():
    p = argparse.ArgumentParser(
        description="Preflight 1K-step verification (One-Shot Best principle)")

    # Data
    p.add_argument("--data", type=str, required=True, help="Corpus path")
    p.add_argument("--block-size", type=int, default=256)
    p.add_argument("--batch-size", type=int, default=32)

    # Model
    p.add_argument("--decoder", type=str, default="v2", choices=["v2", "v3"])
    p.add_argument("--d-model", type=int, default=384)
    p.add_argument("--cell-dim", type=int, default=64)
    p.add_argument("--hidden-dim", type=int, default=128)

    # Consciousness
    p.add_argument("--federated", action="store_true", default=True)
    p.add_argument("--no-federated", dest="federated", action="store_false")
    p.add_argument("--atoms", type=int, default=8)
    p.add_argument("--cells-per-atom", type=int, default=8)
    p.add_argument("--cells", type=int, default=64)

    # Training
    p.add_argument("--steps", type=int, default=DEFAULT_STEPS,
                   help=f"Preflight steps (default {DEFAULT_STEPS})")
    p.add_argument("--lr", type=float, default=3e-4)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--device", type=str,
                   default="cuda" if torch.cuda.is_available() else "cpu")

    # Tokenizer (optional, for BPE checks)
    p.add_argument("--tokenizer", type=str, default=None,
                   help="Tokenizer file path (for md5 verification)")

    # Config file (overrides CLI args)
    p.add_argument("--config", type=str, default=None,
                   help="JSON config file (same keys as train_v14 args)")

    return p.parse_args()


def main():
    args = parse_args()

    # Load config file if specified (overrides CLI args)
    if args.config:
        if not os.path.exists(args.config):
            print(f"  [FATAL] Config file not found: {args.config}")
            sys.exit(1)
        with open(args.config) as f:
            config = json.load(f)
        for k, v in config.items():
            k_attr = k.replace('-', '_')
            if hasattr(args, k_attr):
                setattr(args, k_attr, v)
        print(f"  Loaded config: {args.config}")

    print(f"  preflight_check.py — One-Shot Best Verification")
    print(f"  Corpus: {args.data}")
    print(f"  Decoder: {args.decoder} | Steps: {args.steps}")
    print(f"  Mode: {'Federated' if args.federated else 'Empire'}")
    print(f"  Device: {args.device}")
    print(f"  Thresholds from: consciousness_laws.json")

    try:
        results = run_preflight(args)
        all_pass = print_report(results)
        sys.exit(0 if all_pass else 1)
    except Exception as ex:
        print(f"\n  [FATAL] Preflight crashed: {type(ex).__name__}: {ex}")
        traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    main()
