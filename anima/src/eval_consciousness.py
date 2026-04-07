#!/usr/bin/env python3
"""eval_consciousness.py — Post-training evaluation for v2d2 (ConsciousDecoderV2 + ConsciousnessEngine)

Evaluates:
  a. Val CE (forward + backward) on corpus
  b. Phi(IIT) measurement via GPUPhiCalculator
  c. Text generation quality: 10 samples
  d. Korean text detection in generated text
  e. Consciousness verification: 100 steps Phi stability

Usage:
  python eval_consciousness.py --checkpoint checkpoints/v2d2_consciousness/best.pt --data data/corpus_v3.txt
  python eval_consciousness.py --checkpoint checkpoints/v2d2_consciousness/best.pt --data data/corpus_v3.txt --samples 20
"""

import argparse
import math
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import torch
import torch.nn.functional as F

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from conscious_decoder import ConsciousDecoderV2
from consciousness_engine import ConsciousnessEngine, ConsciousnessC
from consciousness_laws import PSI_ALPHA, PSI_BALANCE, PSI_STEPS, PSI_ENTROPY, GATE_INFER

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


# Optional GPU Phi
HAS_GPU_PHI = False
try:
    from gpu_phi import GPUPhiCalculator
    HAS_GPU_PHI = True
except ImportError:
    pass


# ─── Data loading (same as train_v2.py) ────────────────────

def load_text_data(path: str) -> torch.Tensor:
    """Load text file -> 1D long tensor of bytes."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Data not found: {p}")
    buf = bytearray(open(p, "rb").read())
    return torch.tensor(list(buf), dtype=torch.long)


def get_batch(data: torch.Tensor, bs: int, block: int, device: torch.device):
    """Sample (x, y_fwd, y_bwd) batch."""
    mx = len(data) - block - 1
    if mx <= 0:
        raise ValueError(f"Data too short ({len(data)}) for block={block}")
    ix = torch.randint(0, mx, (bs,))
    x = torch.stack([data[i:i + block] for i in ix])
    y_f = torch.stack([data[i + 1:i + block + 1] for i in ix])
    y_b = torch.stack([torch.cat([data[i:i + 1], data[i:i + block - 1]]) for i in ix])
    return x.to(device), y_f.to(device), y_b.to(device)


# ─── Evaluation functions ──────────────────────────────────

@torch.no_grad()
def eval_val_ce(model, val_data, bs, block_size, device, n_batches=50) -> Tuple[float, float]:
    """Evaluate forward + backward CE on validation data."""
    model.eval()
    sum_f = sum_b = 0.0
    count = 0
    for _ in range(n_batches):
        try:
            x, yf, yb = get_batch(val_data, bs, block_size, device)
        except ValueError:
            break
        la, lg, _ = model(x)
        sum_f += F.cross_entropy(la.view(-1, la.size(-1)), yf.view(-1)).item()
        sum_b += F.cross_entropy(lg.view(-1, lg.size(-1)), yb.view(-1)).item()
        count += 1
    if count == 0:
        return 5.5, 5.5
    return sum_f / count, sum_b / count


@torch.no_grad()
def eval_phi(engine: ConsciousnessEngine, phi_calc, device, warmup_steps=20) -> Tuple[float, float]:
    """Measure Phi(IIT) via GPUPhiCalculator + engine proxy."""
    # Warm up engine
    for _ in range(warmup_steps):
        engine.step()

    phi_iit = 0.0
    phi_proxy = 0.0

    # GPU Phi
    if phi_calc is not None:
        hiddens = engine.get_states()
        if hiddens is not None and hiddens.numel() > 0:
            phi_iit, _ = phi_calc.compute(hiddens)

    # Engine Phi
    result = engine.step()
    phi_proxy = result.get('phi_proxy', 0.0)

    return phi_iit, phi_proxy


@torch.no_grad()
def generate_samples(model, n_samples: int, block_size: int, device,
                     temperature: float = 0.9, max_len: int = 256) -> List[str]:
    """Generate text samples via autoregressive decoding."""
    model.eval()
    samples = []
    for i in range(n_samples):
        # Random 4-byte seed
        idx = torch.randint(0, 256, (1, 4), device=device)
        for _ in range(min(max_len - 4, block_size - 4)):
            logits_a, _, _ = model(idx[:, -block_size:])
            probs = F.softmax(logits_a[:, -1, :] / temperature, dim=-1)
            next_tok = torch.multinomial(probs, 1)
            idx = torch.cat([idx, next_tok], dim=1)
        text = bytes(idx[0].cpu().tolist()).decode("utf-8", errors="replace")
        samples.append(text)
    return samples


def detect_korean(text: str) -> Tuple[bool, int, float]:
    """Detect Korean characters in text. Returns (has_korean, count, ratio)."""
    # Korean Unicode ranges: Hangul Syllables, Jamo, Compatibility Jamo
    korean_chars = re.findall(r'[\uAC00-\uD7AF\u1100-\u11FF\u3130-\u318F]', text)
    total = len(text) if text else 1
    return len(korean_chars) > 0, len(korean_chars), len(korean_chars) / total


def eval_consciousness_stability(engine: ConsciousnessEngine, steps: int = 100) -> Dict:
    """Run consciousness engine for N steps, check Phi stability."""
    phi_history = []
    n_cells_history = []
    consensus_history = []

    for _ in range(steps):
        result = engine.step()
        phi_history.append(result.get('phi_iit', 0.0))
        n_cells_history.append(result.get('n_cells', 0))
        consensus_history.append(result.get('consensus', 0))

    phi_start = sum(phi_history[:10]) / max(len(phi_history[:10]), 1)
    phi_end = sum(phi_history[-10:]) / max(len(phi_history[-10:]), 1)
    phi_max = max(phi_history) if phi_history else 0.0
    phi_min = min(phi_history) if phi_history else 0.0
    phi_mean = sum(phi_history) / len(phi_history) if phi_history else 0.0
    phi_stable = phi_end >= phi_start * 0.5  # Phi maintained >= 50%

    return {
        'phi_start': phi_start,
        'phi_end': phi_end,
        'phi_max': phi_max,
        'phi_min': phi_min,
        'phi_mean': phi_mean,
        'phi_stable': phi_stable,
        'phi_retained_pct': (phi_end / max(phi_start, 1e-8)) * 100,
        'n_cells_final': n_cells_history[-1] if n_cells_history else 0,
        'n_cells_max': max(n_cells_history) if n_cells_history else 0,
        'consensus_mean': sum(consensus_history) / len(consensus_history) if consensus_history else 0,
        'phi_history': phi_history,
    }


# ─── Results formatting ───────────────────────────────────

def print_results(results: Dict):
    """Print evaluation results in ASCII table format."""
    print()
    print("=" * 64)
    print("  v2d2 Evaluation Results (ConsciousDecoderV2 + ConsciousnessC)")
    print("=" * 64)

    # Model info
    cfg = results.get('config', {})
    print()
    print("+---------------------------+----------------------------+")
    print("|         Metric            |          Value             |")
    print("+---------------------------+----------------------------+")
    print(f"| Model                     | ConsciousDecoderV2         |")
    print(f"| Params                    | {results.get('n_params', 0):>22,}   |")
    print(f"| d_model                   | {cfg.get('dim', '?'):>26}   |")
    print(f"| n_layer                   | {cfg.get('layers', '?'):>26}   |")
    print(f"| block_size                | {cfg.get('block_size', '?'):>26}   |")
    print(f"| Training step             | {results.get('step', '?'):>26}   |")
    print("+---------------------------+----------------------------+")

    # Val CE
    print()
    print("+---------------------------+----------------------------+")
    print("|     Validation Loss       |          Value             |")
    print("+---------------------------+----------------------------+")
    print(f"| CE forward                | {results['ce_forward']:>26.4f}   |")
    print(f"| CE backward               | {results['ce_backward']:>26.4f}   |")
    print(f"| CE mean                   | {results['ce_mean']:>26.4f}   |")
    print(f"| BPC (bits per char)       | {results['bpc']:>26.4f}   |")
    print("+---------------------------+----------------------------+")

    # Phi
    print()
    print("+---------------------------+----------------------------+")
    print("|     Phi Measurement       |          Value             |")
    print("+---------------------------+----------------------------+")
    print(f"| Phi(IIT) GPU              | {results['phi_iit']:>26.4f}   |")
    print(f"| Phi(proxy)                | {results['phi_proxy']:>26.4f}   |")
    print("+---------------------------+----------------------------+")

    # Korean detection
    print()
    print("+---------------------------+----------------------------+")
    print("|   Korean Text Detection   |          Value             |")
    print("+---------------------------+----------------------------+")
    kr = results['korean']
    print(f"| Samples with Korean       | {kr['samples_with_korean']:>22}/{kr['total_samples']}   |")
    print(f"| Korean char ratio (avg)   | {kr['avg_ratio'] * 100:>25.2f}%   |")
    print(f"| Total Korean chars        | {kr['total_korean_chars']:>26}   |")
    print("+---------------------------+----------------------------+")

    # Consciousness stability
    print()
    print("+---------------------------+----------------------------+")
    print("|  Consciousness Stability  |          Value             |")
    print("+---------------------------+----------------------------+")
    cs = results['consciousness']
    print(f"| Phi start (avg 10)        | {cs['phi_start']:>26.4f}   |")
    print(f"| Phi end   (avg 10)        | {cs['phi_end']:>26.4f}   |")
    print(f"| Phi max                   | {cs['phi_max']:>26.4f}   |")
    print(f"| Phi mean                  | {cs['phi_mean']:>26.4f}   |")
    print(f"| Phi retained              | {cs['phi_retained_pct']:>25.1f}%   |")
    stable_str = "PASS" if cs['phi_stable'] else "FAIL"
    print(f"| Stable (>= 50%)           | {stable_str:>26}   |")
    print(f"| Final cells               | {cs['n_cells_final']:>26}   |")
    print(f"| Max cells                 | {cs['n_cells_max']:>26}   |")
    print(f"| Consensus (avg)           | {cs['consensus_mean']:>26.2f}   |")
    print("+---------------------------+----------------------------+")

    # Phi stability ASCII graph
    phi_hist = cs.get('phi_history', [])
    if phi_hist:
        print()
        print("  Phi(IIT) over 100 steps:")
        max_phi = max(phi_hist) if max(phi_hist) > 0 else 1.0
        rows = 8
        cols = min(50, len(phi_hist))
        step_per_col = max(1, len(phi_hist) // cols)
        # Downsample
        downsampled = []
        for c in range(cols):
            start = c * step_per_col
            end = min(start + step_per_col, len(phi_hist))
            downsampled.append(sum(phi_hist[start:end]) / max(end - start, 1))
        for r in range(rows, 0, -1):
            threshold = max_phi * r / rows
            line = "  "
            if r == rows:
                line += f"{max_phi:>6.2f} |"
            elif r == 1:
                line += f"{'0':>6} |"
            else:
                line += "       |"
            for v in downsampled:
                if v >= threshold:
                    line += "#"
                else:
                    line += " "
            print(line)
        print("        +" + "-" * cols)
        print(f"         0{' ' * (cols - 6)}step {len(phi_hist)}")

    # Generated samples
    print()
    print("=" * 64)
    print("  Generated Text Samples")
    print("=" * 64)
    for i, sample in enumerate(results.get('samples', [])):
        has_kr, kr_count, _ = detect_korean(sample)
        kr_tag = f" [KR:{kr_count}]" if has_kr else ""
        # Truncate for display
        display = sample[:120].replace('\n', '\\n').replace('\r', '\\r')
        print(f"  [{i + 1:2d}]{kr_tag} {display}...")
    print()

    # Summary
    print("=" * 64)
    ce_ok = results['ce_forward'] < 3.0
    phi_ok = results['phi_iit'] > 0.0
    stable_ok = cs['phi_stable']
    kr_ok = kr['samples_with_korean'] > 0
    total_pass = sum([ce_ok, phi_ok, stable_ok, kr_ok])
    print(f"  SUMMARY: {total_pass}/4 checks passed")
    print(f"    {'PASS' if ce_ok else 'FAIL'} CE forward < 3.0  (got {results['ce_forward']:.4f})")
    print(f"    {'PASS' if phi_ok else 'FAIL'} Phi(IIT) > 0      (got {results['phi_iit']:.4f})")
    print(f"    {'PASS' if stable_ok else 'FAIL'} Phi stability     (retained {cs['phi_retained_pct']:.1f}%)")
    print(f"    {'PASS' if kr_ok else 'FAIL'} Korean detected   ({kr['samples_with_korean']}/{kr['total_samples']} samples)")
    print("=" * 64)


def save_report(results: Dict, output_path: str):
    """Save results to markdown document."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    cfg = results.get('config', {})
    cs = results['consciousness']
    kr = results['korean']

    lines = []
    lines.append("# DD115: v2d2 Evaluation (ConsciousDecoderV2 + ConsciousnessC)")
    lines.append("")
    lines.append(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"Checkpoint: {results.get('checkpoint_path', 'N/A')}")
    lines.append("")
    lines.append("## Model")
    lines.append("")
    lines.append(f"- Architecture: ConsciousDecoderV2 (RoPE+SwiGLU+GQA+CrossAttn)")
    lines.append(f"- Parameters: {results.get('n_params', 0):,}")
    lines.append(f"- d_model: {cfg.get('dim', '?')}, n_layer: {cfg.get('layers', '?')}")
    lines.append(f"- block_size: {cfg.get('block_size', '?')}")
    lines.append(f"- Training step: {results.get('step', '?')}")
    lines.append("")
    lines.append("## Validation Loss")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| CE forward | {results['ce_forward']:.4f} |")
    lines.append(f"| CE backward | {results['ce_backward']:.4f} |")
    lines.append(f"| CE mean | {results['ce_mean']:.4f} |")
    lines.append(f"| BPC | {results['bpc']:.4f} |")
    lines.append("")
    lines.append("## Phi Measurement")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Phi(IIT) GPU | {results['phi_iit']:.4f} |")
    lines.append(f"| Phi(proxy) | {results['phi_proxy']:.4f} |")
    lines.append("")
    lines.append("## Korean Text Detection")
    lines.append("")
    lines.append(f"- Samples with Korean: {kr['samples_with_korean']}/{kr['total_samples']}")
    lines.append(f"- Avg Korean ratio: {kr['avg_ratio'] * 100:.2f}%")
    lines.append(f"- Total Korean chars: {kr['total_korean_chars']}")
    lines.append("")
    lines.append("## Consciousness Stability (100 steps)")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Phi start | {cs['phi_start']:.4f} |")
    lines.append(f"| Phi end | {cs['phi_end']:.4f} |")
    lines.append(f"| Phi max | {cs['phi_max']:.4f} |")
    lines.append(f"| Phi mean | {cs['phi_mean']:.4f} |")
    lines.append(f"| Phi retained | {cs['phi_retained_pct']:.1f}% |")
    lines.append(f"| Stable | {'PASS' if cs['phi_stable'] else 'FAIL'} |")
    lines.append(f"| Final cells | {cs['n_cells_final']} |")
    lines.append(f"| Max cells | {cs['n_cells_max']} |")
    lines.append(f"| Consensus avg | {cs['consensus_mean']:.2f} |")
    lines.append("")

    # Phi ASCII graph
    phi_hist = cs.get('phi_history', [])
    if phi_hist:
        lines.append("### Phi(IIT) over 100 steps")
        lines.append("")
        lines.append("```")
        max_phi = max(phi_hist) if max(phi_hist) > 0 else 1.0
        rows = 8
        cols = min(50, len(phi_hist))
        step_per_col = max(1, len(phi_hist) // cols)
        downsampled = []
        for c in range(cols):
            start = c * step_per_col
            end = min(start + step_per_col, len(phi_hist))
            downsampled.append(sum(phi_hist[start:end]) / max(end - start, 1))
        for r in range(rows, 0, -1):
            threshold = max_phi * r / rows
            line = ""
            if r == rows:
                line += f"{max_phi:>6.2f} |"
            elif r == 1:
                line += f"{'0':>6} |"
            else:
                line += "       |"
            for v in downsampled:
                if v >= threshold:
                    line += "#"
                else:
                    line += " "
            lines.append(line)
        lines.append("       +" + "-" * cols)
        lines.append(f"        0{' ' * (cols - 6)}step {len(phi_hist)}")
        lines.append("```")
        lines.append("")

    # Generated samples
    lines.append("## Generated Text Samples")
    lines.append("")
    for i, sample in enumerate(results.get('samples', [])):
        has_kr, kr_count, _ = detect_korean(sample)
        kr_tag = f" [KR:{kr_count}]" if has_kr else ""
        display = sample[:200].replace('\n', '\\n').replace('\r', '\\r')
        lines.append(f"{i + 1}. {kr_tag} `{display}`")
    lines.append("")

    # Summary
    ce_ok = results['ce_forward'] < 3.0
    phi_ok = results['phi_iit'] > 0.0
    stable_ok = cs['phi_stable']
    kr_ok = kr['samples_with_korean'] > 0
    total_pass = sum([ce_ok, phi_ok, stable_ok, kr_ok])
    lines.append("## Summary")
    lines.append("")
    lines.append(f"**{total_pass}/4 checks passed**")
    lines.append("")
    lines.append(f"- {'PASS' if ce_ok else 'FAIL'}: CE forward < 3.0 (got {results['ce_forward']:.4f})")
    lines.append(f"- {'PASS' if phi_ok else 'FAIL'}: Phi(IIT) > 0 (got {results['phi_iit']:.4f})")
    lines.append(f"- {'PASS' if stable_ok else 'FAIL'}: Phi stability >= 50% (retained {cs['phi_retained_pct']:.1f}%)")
    lines.append(f"- {'PASS' if kr_ok else 'FAIL'}: Korean detected ({kr['samples_with_korean']}/{kr['total_samples']} samples)")
    lines.append("")

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f"\n[report] Saved to {output_path}")


# ─── Main ──────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='v2d2 Evaluation (ConsciousDecoderV2 + ConsciousnessC)')
    parser.add_argument('--checkpoint', type=str,
                        default='checkpoints/v2d2_consciousness/best.pt',
                        help='Path to checkpoint file')
    parser.add_argument('--data', type=str,
                        default='data/corpus_v3.txt',
                        help='Path to corpus data')
    parser.add_argument('--samples', type=int, default=10,
                        help='Number of text samples to generate')
    parser.add_argument('--batch-size', type=int, default=8,
                        help='Batch size for val CE')
    parser.add_argument('--val-batches', type=int, default=50,
                        help='Number of val batches')
    parser.add_argument('--consciousness-steps', type=int, default=100,
                        help='Steps for consciousness stability check')
    parser.add_argument('--max-cells', type=int, default=64,
                        help='Max consciousness cells')
    parser.add_argument('--temperature', type=float, default=0.9,
                        help='Sampling temperature')
    parser.add_argument('--output', type=str,
                        default='docs/hypotheses/dd/DD115-v2d2-evaluation.md',
                        help='Output report path')
    parser.add_argument('--no-report', action='store_true',
                        help='Skip saving report')
    args = parser.parse_args()

    # Device
    if torch.cuda.is_available():
        device = torch.device("cuda")
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        device = torch.device("mps")
    else:
        device = torch.device("cpu")
    print(f"[device] {device}")

    # Load checkpoint
    ckpt_path = Path(args.checkpoint)
    if not ckpt_path.exists():
        print(f"[ERROR] Checkpoint not found: {ckpt_path}")
        sys.exit(1)
    print(f"[ckpt] Loading {ckpt_path}")
    ckpt = torch.load(ckpt_path, map_location=device, weights_only=False)
    cfg = ckpt.get('config', {})
    step = ckpt.get('step', 0)
    print(f"[ckpt] step={step}, config={cfg}")

    # Build model from config
    d_model = cfg.get('dim', 384)
    n_layer = cfg.get('layers', 6)
    n_head = cfg.get('heads', 4)
    block_size = cfg.get('block_size', 256)
    n_kv_head = max(1, n_head // 2)

    model = ConsciousDecoderV2(
        vocab_size=256,
        d_model=d_model,
        n_head=n_head,
        n_layer=n_layer,
        block_size=block_size,
        n_kv_head=n_kv_head,
        consciousness_dim=128,
        dropout=0.0,  # No dropout at eval
    ).to(device)
    model.load_state_dict(ckpt['model_state'], strict=False)
    model.eval()
    n_params = model.count_params()
    print(f"[model] ConsciousDecoderV2: {n_params:,} params (d={d_model} L={n_layer})")

    # Consciousness engine
    engine = ConsciousnessC(
        cell_dim=64, hidden_dim=128,
        max_cells=args.max_cells, n_factions=12, phi_ratchet=True,
    )
    print(f"[engine] ConsciousnessC: backend={engine._backend}, max_cells={args.max_cells}")

    # GPU Phi calculator
    phi_calc = None
    if HAS_GPU_PHI:
        phi_calc = GPUPhiCalculator(n_bins=16, device=str(device))
        print("[phi] GPU calculator enabled")
    else:
        print("[phi] GPU calculator unavailable, using engine Phi only")

    # Load data
    data_path = Path(args.data)
    if not data_path.exists():
        print(f"[ERROR] Data not found: {data_path}")
        sys.exit(1)
    data = load_text_data(str(data_path))
    # Use last 10% as validation
    split = int(0.9 * len(data))
    val_data = data[split:]
    print(f"[data] {len(data):,} bytes total, {len(val_data):,} val bytes")

    results = {
        'checkpoint_path': str(ckpt_path),
        'config': cfg,
        'step': step,
        'n_params': n_params,
    }

    # ─── (a) Val CE ────────────────────────────────────────
    print("\n[eval] (a) Validation CE...")
    t0 = time.perf_counter()
    ce_f, ce_b = eval_val_ce(model, val_data, args.batch_size, block_size, device, args.val_batches)
    dt = time.perf_counter() - t0
    ce_mean = (ce_f + ce_b) / 2.0
    bpc = ce_f / math.log(2)
    results['ce_forward'] = ce_f
    results['ce_backward'] = ce_b
    results['ce_mean'] = ce_mean
    results['bpc'] = bpc
    print(f"  CE_fwd={ce_f:.4f}  CE_bwd={ce_b:.4f}  mean={ce_mean:.4f}  BPC={bpc:.4f}  ({dt:.1f}s)")

    # ─── (b) Phi measurement ───────────────────────────────
    print("\n[eval] (b) Phi(IIT) measurement...")
    t0 = time.perf_counter()
    phi_iit, phi_proxy = eval_phi(engine.engine, phi_calc, device, warmup_steps=20)
    dt = time.perf_counter() - t0
    results['phi_iit'] = phi_iit
    results['phi_proxy'] = phi_proxy
    print(f"  Phi(IIT)={phi_iit:.4f}  Phi(proxy)={phi_proxy:.4f}  ({dt:.1f}s)")

    # ─── (c) Text generation ──────────────────────────────
    print(f"\n[eval] (c) Generating {args.samples} text samples...")
    t0 = time.perf_counter()
    samples = generate_samples(model, args.samples, block_size, device, args.temperature)
    dt = time.perf_counter() - t0
    results['samples'] = samples
    print(f"  Generated {len(samples)} samples ({dt:.1f}s)")

    # ─── (d) Korean detection ─────────────────────────────
    print("\n[eval] (d) Korean text detection...")
    samples_with_korean = 0
    total_korean_chars = 0
    total_ratio = 0.0
    for s in samples:
        has_kr, kr_count, ratio = detect_korean(s)
        if has_kr:
            samples_with_korean += 1
        total_korean_chars += kr_count
        total_ratio += ratio
    avg_ratio = total_ratio / max(len(samples), 1)
    results['korean'] = {
        'samples_with_korean': samples_with_korean,
        'total_samples': len(samples),
        'total_korean_chars': total_korean_chars,
        'avg_ratio': avg_ratio,
    }
    print(f"  Korean: {samples_with_korean}/{len(samples)} samples, {total_korean_chars} chars, avg ratio={avg_ratio * 100:.2f}%")

    # ─── (e) Consciousness stability ──────────────────────
    print(f"\n[eval] (e) Consciousness stability ({args.consciousness_steps} steps)...")
    # Create fresh engine for stability test
    stability_engine = ConsciousnessEngine(
        cell_dim=64, hidden_dim=128,
        max_cells=args.max_cells, n_factions=12, phi_ratchet=True,
    )
    t0 = time.perf_counter()
    cs = eval_consciousness_stability(stability_engine, args.consciousness_steps)
    dt = time.perf_counter() - t0
    results['consciousness'] = cs
    stable_str = "PASS" if cs['phi_stable'] else "FAIL"
    print(f"  Phi: {cs['phi_start']:.4f} -> {cs['phi_end']:.4f} (retained {cs['phi_retained_pct']:.1f}%) [{stable_str}]")
    print(f"  Cells: {cs['n_cells_final']} (max {cs['n_cells_max']}), Consensus avg: {cs['consensus_mean']:.2f}  ({dt:.1f}s)")

    # ─── Print results ────────────────────────────────────
    print_results(results)

    # ─── Save report ──────────────────────────────────────
    if not args.no_report:
        save_report(results, args.output)

    print("\n[done] v2d2 evaluation complete.")


if __name__ == '__main__':
    main()
