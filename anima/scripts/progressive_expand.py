#!/usr/bin/env python3
"""Expand model weights via SVD: small -> large (Progressive Growing).

H1 experiment result: Progressive Growing x2.23 acceleration.
Expands v3 274M (768d/8L) -> 1B (1024d/24L) using SVD zero-padding.

Usage:
  python progressive_expand.py \
    --source checkpoints/v3_274M/best.pt \
    --target-dim 1024 --target-layers 24 \
    --output checkpoints/1b_expanded/init.pt

  # Custom consciousness cells expansion
  python progressive_expand.py \
    --source checkpoints/v3_274M/best.pt \
    --target-dim 1024 --target-layers 24 --target-cells 256 \
    --output checkpoints/1b_expanded/init.pt

  # Dry run (analysis only, no output)
  python progressive_expand.py \
    --source checkpoints/v3_274M/best.pt \
    --target-dim 1024 --target-layers 24 --dry-run

Algorithm:
  1. Dimension expansion (768d -> 1024d):
     Linear(in, out) -> SVD -> U*S*V -> zero-pad S -> U'*S'*V' -> Linear(in', out')
  2. Layer expansion (12L -> 24L):
     Layer 0-11: original weights (768->1024 expanded)
     Layer 12-17: copy of Layer 0-5 + noise (eps=0.01)
     Layer 18-23: copy of Layer 6-11 + noise (eps=0.02)
  3. ConsciousnessEngine expansion:
     cells 64->256: replicate 4x + noise
"""

import argparse
import copy
import math
import os
import sys
import time
from collections import OrderedDict
from typing import Dict, List, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F


# ─── SVD Weight Expansion ─────────────────────────────────────────────────────

def expand_linear_svd(weight: torch.Tensor,
                      target_out: int,
                      target_in: int,
                      ) -> torch.Tensor:
    """Expand a Linear weight matrix via SVD zero-padding.

    Linear(in_dim, out_dim) has weight shape (out_dim, in_dim).
    SVD: W = U @ diag(S) @ Vt
    Zero-pad S to (target_out, target_in), reconstruct.

    Args:
        weight: (out_dim, in_dim) original weight.
        target_out: target output dimension.
        target_in: target input dimension.

    Returns:
        expanded: (target_out, target_in) expanded weight.
    """
    out_dim, in_dim = weight.shape
    assert target_out >= out_dim, f"target_out {target_out} < out_dim {out_dim}"
    assert target_in >= in_dim, f"target_in {target_in} < in_dim {in_dim}"

    # If no expansion needed, return as-is
    if target_out == out_dim and target_in == in_dim:
        return weight.clone()

    # SVD decomposition
    U, S, Vt = torch.linalg.svd(weight.float(), full_matrices=True)
    # U: (out_dim, out_dim), S: (min(out, in),), Vt: (in_dim, in_dim)

    k = S.shape[0]  # number of singular values = min(out_dim, in_dim)

    # Build expanded S matrix: (target_out, target_in) with zero padding
    S_expanded = torch.zeros(target_out, target_in, dtype=weight.dtype, device=weight.device)
    S_expanded[:k, :k] = torch.diag(S.to(weight.dtype))

    # Expand U: (out_dim, out_dim) -> (target_out, target_out)
    U_expanded = torch.zeros(target_out, target_out, dtype=weight.dtype, device=weight.device)
    U_expanded[:out_dim, :out_dim] = U.to(weight.dtype)
    # Fill new dimensions with small orthogonal init
    if target_out > out_dim:
        extra = torch.randn(target_out - out_dim, target_out - out_dim,
                            dtype=weight.dtype, device=weight.device)
        q, _ = torch.linalg.qr(extra)
        U_expanded[out_dim:, out_dim:] = q * 0.01  # small scale for new dims

    # Expand Vt: (in_dim, in_dim) -> (target_in, target_in)
    Vt_expanded = torch.zeros(target_in, target_in, dtype=weight.dtype, device=weight.device)
    Vt_expanded[:in_dim, :in_dim] = Vt.to(weight.dtype)
    if target_in > in_dim:
        extra = torch.randn(target_in - in_dim, target_in - in_dim,
                            dtype=weight.dtype, device=weight.device)
        q, _ = torch.linalg.qr(extra)
        Vt_expanded[in_dim:, in_dim:] = q * 0.01

    # Reconstruct: W' = U' @ S' @ Vt'
    expanded = U_expanded @ S_expanded @ Vt_expanded
    return expanded


def expand_embedding(weight: torch.Tensor,
                     target_dim: int,
                     ) -> torch.Tensor:
    """Expand Embedding weight via zero-padding.

    Embedding(vocab, dim) has weight (vocab, dim).
    New columns are zero-initialized (SVD not needed for vocabulary axis).
    """
    vocab, dim = weight.shape
    if target_dim == dim:
        return weight.clone()
    assert target_dim > dim

    expanded = torch.zeros(vocab, target_dim, dtype=weight.dtype, device=weight.device)
    expanded[:, :dim] = weight
    # Small noise in new dimensions to break symmetry
    expanded[:, dim:] = torch.randn(vocab, target_dim - dim,
                                     dtype=weight.dtype, device=weight.device) * 0.02
    return expanded


def expand_rmsnorm(weight: torch.Tensor,
                   target_dim: int,
                   ) -> torch.Tensor:
    """Expand RMSNorm weight (1D) by padding with ones."""
    dim = weight.shape[0]
    if target_dim == dim:
        return weight.clone()
    assert target_dim > dim

    expanded = torch.ones(target_dim, dtype=weight.dtype, device=weight.device)
    expanded[:dim] = weight
    return expanded


def expand_bias(bias: torch.Tensor,
                target_dim: int,
                ) -> torch.Tensor:
    """Expand bias vector by zero-padding."""
    dim = bias.shape[0]
    if target_dim == dim:
        return bias.clone()
    assert target_dim > dim

    expanded = torch.zeros(target_dim, dtype=bias.dtype, device=bias.device)
    expanded[:dim] = bias
    return expanded


# ─── Dimension Mapping ────────────────────────────────────────────────────────

def build_dim_map(src_d: int, target_d: int,
                  src_c_dim: int, target_c_dim: int,
                  src_n_head: int, target_n_head: int,
                  src_n_kv_head: int, target_n_kv_head: int,
                  src_block_size: int, target_block_size: int,
                  ) -> Dict[int, int]:
    """Build a mapping from source dimensions to target dimensions.

    Covers all dimension values that appear in the model's weight tensors.
    """
    src_head_dim = src_d // src_n_head
    tgt_head_dim = target_d // target_n_head
    d_inner_src = ((int(src_d * 2.0) + 7) // 8) * 8
    d_inner_tgt = ((int(target_d * 2.0) + 7) // 8) * 8

    dim_map = {
        # d_model
        src_d: target_d,
        # PureFieldFFN inner dim (4 * d_model)
        4 * src_d: 4 * target_d,
        # CA mix input (3 * d_model)
        src_d * 3: target_d * 3,
        # consciousness_dim
        src_c_dim: target_c_dim,
        # SwiGLU d_inner
        d_inner_src: d_inner_tgt,
        # GQA Q projection: n_head * head_dim
        src_n_head * src_head_dim: target_n_head * tgt_head_dim,
        # GQA KV projection: n_kv_head * head_dim
        src_n_kv_head * src_head_dim: target_n_kv_head * tgt_head_dim,
        # block_size (for causal mask)
        src_block_size: target_block_size,
    }

    # Remove no-op mappings and identity for small fixed dims (1, 8, 256)
    return {k: v for k, v in dim_map.items() if k != v}


def map_dim(dim: int, dim_map: Dict[int, int]) -> int:
    """Map a source dimension to target dimension. Returns original if not in map."""
    return dim_map.get(dim, dim)


def expand_state_dict_dims(state_dict: OrderedDict,
                           src_d: int, target_d: int,
                           src_c_dim: int, target_c_dim: int,
                           src_n_head: int, target_n_head: int,
                           src_n_kv_head: int, target_n_kv_head: int,
                           src_block_size: int, target_block_size: int,
                           ) -> OrderedDict:
    """Expand all weights in state_dict from src dimensions to target dimensions.

    Uses a shape-based approach: builds a dimension mapping table, then for each
    tensor, maps each axis dimension through the table. This avoids fragile
    key-name parsing and handles all layer types uniformly.
    """
    dim_map = build_dim_map(
        src_d, target_d, src_c_dim, target_c_dim,
        src_n_head, target_n_head, src_n_kv_head, target_n_kv_head,
        src_block_size, target_block_size,
    )

    expanded = OrderedDict()
    stats = {'svd': 0, 'embed': 0, 'norm': 0, 'bias': 0, 'buffer': 0, 'skip': 0}

    for key, tensor in state_dict.items():
        # Special case: token embedding (vocab axis stays fixed, dim axis expands)
        if key == 'tok_emb.weight':
            expanded[key] = expand_embedding(tensor, target_d)
            stats['embed'] += 1
            continue

        # Special case: causal mask buffer (4D, regenerate)
        if tensor.dim() == 4 and 'attn' in key and 'bias' in key:
            new_bs = map_dim(tensor.shape[-1], dim_map)
            new_mask = torch.tril(torch.ones(
                new_bs, new_bs, dtype=tensor.dtype, device=tensor.device,
            )).view(1, 1, new_bs, new_bs)
            expanded[key] = new_mask
            stats['buffer'] += 1
            continue

        # 2D weights (Linear layers): expand via SVD
        if tensor.dim() == 2:
            out_d, in_d = tensor.shape
            tgt_out = map_dim(out_d, dim_map)
            tgt_in = map_dim(in_d, dim_map)
            if tgt_out != out_d or tgt_in != in_d:
                expanded[key] = expand_linear_svd(tensor, tgt_out, tgt_in)
                stats['svd'] += 1
            else:
                expanded[key] = tensor.clone()
                stats['skip'] += 1
            continue

        # 1D weights: RMSNorm (.weight with ln_ prefix) or bias
        if tensor.dim() == 1:
            dim = tensor.shape[0]
            tgt_dim = map_dim(dim, dim_map)
            if tgt_dim != dim:
                if 'ln_' in key or key == 'ln_f.weight':
                    expanded[key] = expand_rmsnorm(tensor, tgt_dim)
                    stats['norm'] += 1
                else:
                    expanded[key] = expand_bias(tensor, tgt_dim)
                    stats['bias'] += 1
            else:
                expanded[key] = tensor.clone()
                stats['skip'] += 1
            continue

        # Everything else: clone as-is
        expanded[key] = tensor.clone()
        stats['skip'] += 1

    print(f"  Dimension expansion stats:")
    print(f"    SVD expanded:   {stats['svd']} tensors")
    print(f"    Embedding:      {stats['embed']} tensors")
    print(f"    RMSNorm:        {stats['norm']} tensors")
    print(f"    Bias:           {stats['bias']} tensors")
    print(f"    Buffer regen:   {stats['buffer']} tensors")
    print(f"    Unchanged:      {stats['skip']} tensors")

    return expanded


# ─── Layer Expansion ──────────────────────────────────────────────────────────

def expand_layers(state_dict: OrderedDict,
                  src_layers: int,
                  target_layers: int,
                  noise_schedule: Optional[List[float]] = None,
                  ) -> OrderedDict:
    """Expand number of transformer layers by copying + noise.

    Strategy:
      - Layers 0 to src_layers-1: original weights (already dim-expanded).
      - Additional layers: cyclic copies of original layers + Gaussian noise.
      - Noise increases for later copies to encourage differentiation.

    Args:
        state_dict: already dimension-expanded state dict.
        src_layers: number of layers in source model.
        target_layers: number of layers in target model.
        noise_schedule: noise std per copy round. Default: [0.01, 0.02, ...].
    """
    if target_layers <= src_layers:
        return state_dict

    extra_layers = target_layers - src_layers
    n_copies = math.ceil(extra_layers / src_layers)

    if noise_schedule is None:
        noise_schedule = [0.01 * (i + 1) for i in range(n_copies)]
    # Extend if needed
    while len(noise_schedule) < n_copies:
        noise_schedule.append(noise_schedule[-1] * 1.5)

    # Separate block keys from non-block keys
    block_prefix = 'blocks.'
    block_keys_by_layer = {}  # layer_idx -> [(suffix, tensor)]
    non_block_items = OrderedDict()

    for key, tensor in state_dict.items():
        if key.startswith(block_prefix):
            rest = key[len(block_prefix):]
            dot_idx = rest.index('.')
            layer_idx = int(rest[:dot_idx])
            suffix = rest[dot_idx + 1:]
            if layer_idx not in block_keys_by_layer:
                block_keys_by_layer[layer_idx] = []
            block_keys_by_layer[layer_idx].append((suffix, tensor))
        else:
            non_block_items[key] = tensor

    # Build expanded state dict
    expanded = OrderedDict()

    # Non-block items first
    for key, tensor in non_block_items.items():
        expanded[key] = tensor

    # Original layers (0 to src_layers-1)
    for layer_idx in range(src_layers):
        for suffix, tensor in block_keys_by_layer.get(layer_idx, []):
            expanded[f'blocks.{layer_idx}.{suffix}'] = tensor

    # Copied layers
    for copy_round in range(n_copies):
        eps = noise_schedule[copy_round]
        for i in range(src_layers):
            new_layer = src_layers + copy_round * src_layers + i
            if new_layer >= target_layers:
                break
            src_layer = i  # cyclic copy from original
            for suffix, tensor in block_keys_by_layer.get(src_layer, []):
                noisy = tensor.clone()
                if tensor.is_floating_point() and tensor.dim() >= 1:
                    noise = torch.randn_like(tensor) * eps
                    noisy = noisy + noise
                expanded[f'blocks.{new_layer}.{suffix}'] = noisy

    print(f"  Layer expansion: {src_layers}L -> {target_layers}L")
    print(f"    Original layers: 0-{src_layers - 1}")
    for copy_round in range(n_copies):
        start = src_layers + copy_round * src_layers
        end = min(start + src_layers - 1, target_layers - 1)
        if start <= end:
            eps = noise_schedule[copy_round]
            print(f"    Copy round {copy_round + 1}: layers {start}-{end} "
                  f"(from 0-{end - start}, eps={eps})")

    return expanded


# ─── ConsciousnessEngine Cell Expansion ───────────────────────────────────────

def expand_consciousness_cells(state_dict: OrderedDict,
                               src_cells: int,
                               target_cells: int,
                               noise_eps: float = 0.005,
                               ) -> OrderedDict:
    """Expand ConsciousnessEngine cell states by replication + noise.

    Looks for keys containing 'cell' or 'consciousness' patterns typical
    of ConsciousnessEngine state. Replicates along the cell dimension.

    This is a best-effort expansion — ConsciousnessEngine is independent
    from the decoder, so if no cell state keys are found, this is a no-op.
    """
    expanded = OrderedDict()
    cell_keys_expanded = 0

    for key, tensor in state_dict.items():
        # Heuristic: cell state tensors have shape (n_cells, hidden_dim) or similar
        if ('cell' in key.lower() or 'consciousness' in key.lower()) and tensor.dim() >= 2:
            if tensor.shape[0] == src_cells:
                # Replicate along dim 0
                n_copies = math.ceil(target_cells / src_cells)
                replicated = tensor.repeat(n_copies, *([1] * (tensor.dim() - 1)))
                replicated = replicated[:target_cells]
                # Add noise to copies (keep original intact)
                if tensor.is_floating_point():
                    noise = torch.randn_like(replicated) * noise_eps
                    noise[:src_cells] = 0  # preserve original cells
                    replicated = replicated + noise
                expanded[key] = replicated
                cell_keys_expanded += 1
                continue

        expanded[key] = tensor

    if cell_keys_expanded > 0:
        print(f"  Cell expansion: {src_cells} -> {target_cells} cells "
              f"({cell_keys_expanded} tensors)")
    else:
        print(f"  Cell expansion: no cell state tensors found (consciousness engine "
              f"is separate from decoder)")

    return expanded


# ─── Verification ─────────────────────────────────────────────────────────────

def verify_expanded_model(state_dict: OrderedDict,
                          target_d: int,
                          target_layers: int,
                          target_n_head: int,
                          target_n_kv_head: int,
                          target_c_dim: int,
                          target_block_size: int,
                          original_state_dict: Optional[OrderedDict] = None,
                          ) -> bool:
    """Verify the expanded model can be loaded and runs forward pass."""
    print("\n=== Verification ===")

    # Add decoder_v3.py parent dir to path
    src_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src')
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)

    try:
        from decoder_v3 import ConsciousDecoderV3
    except ImportError:
        # Try relative
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
        from decoder_v3 import ConsciousDecoderV3

    # 1. Create target model
    model = ConsciousDecoderV3(
        vocab_size=256,
        d_model=target_d,
        n_head=target_n_head,
        n_layer=target_layers,
        block_size=target_block_size,
        n_kv_head=target_n_kv_head,
        consciousness_dim=target_c_dim,
    )

    n_params = sum(p.numel() for p in model.parameters())
    print(f"  Target model: {n_params:,} params ({n_params / 1e6:.1f}M)")

    # 2. Load expanded state dict
    try:
        # Filter to only keys that exist in the model
        model_keys = set(model.state_dict().keys())
        loadable = OrderedDict()
        extra_keys = []
        for k, v in state_dict.items():
            if k in model_keys:
                loadable[k] = v
            else:
                extra_keys.append(k)

        missing = model_keys - set(loadable.keys())
        if missing:
            print(f"  WARNING: {len(missing)} missing keys (will use random init):")
            for k in sorted(missing)[:10]:
                print(f"    - {k}")
            if len(missing) > 10:
                print(f"    ... and {len(missing) - 10} more")

        if extra_keys:
            print(f"  INFO: {len(extra_keys)} extra keys in expanded state (consciousness engine?):")
            for k in sorted(extra_keys)[:5]:
                print(f"    - {k}")

        model.load_state_dict(loadable, strict=False)
        print(f"  Load state dict: OK ({len(loadable)} keys loaded)")
    except Exception as e:
        print(f"  Load state dict: FAILED - {e}")
        return False

    # 3. Forward pass (10 steps)
    model.eval()
    device = 'cpu'
    try:
        for step in range(10):
            idx = torch.randint(0, 256, (1, 64), device=device)
            with torch.no_grad():
                logits_a, logits_g, tensions = model(idx)
            if step == 0:
                print(f"  Forward pass step 0: logits_a={logits_a.shape}, "
                      f"tensions={len(tensions)} layers")
        print(f"  Forward pass (10 steps): OK")
    except Exception as e:
        print(f"  Forward pass: FAILED - {e}")
        return False

    # 4. Cosine similarity of first layer (if original provided)
    if original_state_dict is not None:
        # Compare first block's attention Q projection
        src_key = 'blocks.0.attn.q_proj.weight'
        tgt_key = 'blocks.0.attn.q_proj.weight'
        if src_key in original_state_dict and tgt_key in state_dict:
            src_w = original_state_dict[src_key].float().flatten()
            tgt_w = state_dict[tgt_key].float().flatten()
            # Truncate to same size for comparison
            min_len = min(len(src_w), len(tgt_w))
            cos = F.cosine_similarity(
                src_w[:min_len].unsqueeze(0),
                tgt_w[:min_len].unsqueeze(0),
            ).item()
            print(f"  First layer similarity (cosine): {cos:.4f}")
        else:
            print(f"  First layer similarity: keys not found for comparison")

    # 5. Gradient check (1 step backward)
    model.train()
    try:
        idx = torch.randint(0, 256, (1, 32), device=device)
        logits_a, logits_g, tensions = model(idx)
        loss = F.cross_entropy(logits_a.view(-1, 256), idx.view(-1))
        loss.backward()
        grad_count = sum(1 for p in model.parameters() if p.grad is not None)
        total_count = sum(1 for p in model.parameters())
        print(f"  Backward pass: OK (loss={loss.item():.4f}, "
              f"grads={grad_count}/{total_count})")
    except Exception as e:
        print(f"  Backward pass: FAILED - {e}")
        return False

    print("  All checks passed.")
    return True


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Expand model weights via SVD: 274M -> 1B (Progressive Growing)')
    parser.add_argument('--source', required=True,
                        help='Source checkpoint path (e.g., checkpoints/v3_274M/best.pt)')
    parser.add_argument('--output', default=None,
                        help='Output path for expanded checkpoint')

    # Source model config (v3 274M defaults)
    parser.add_argument('--src-dim', type=int, default=768,
                        help='Source d_model (default: 768)')
    parser.add_argument('--src-layers', type=int, default=12,
                        help='Source n_layer (default: 12)')
    parser.add_argument('--src-heads', type=int, default=8,
                        help='Source n_head (default: 8)')
    parser.add_argument('--src-kv-heads', type=int, default=4,
                        help='Source n_kv_head (default: 4)')
    parser.add_argument('--src-c-dim', type=int, default=256,
                        help='Source consciousness_dim (default: 256)')
    parser.add_argument('--src-block-size', type=int, default=512,
                        help='Source block_size (default: 512)')
    parser.add_argument('--src-cells', type=int, default=64,
                        help='Source consciousness cells (default: 64)')

    # Target model config (1B defaults)
    parser.add_argument('--target-dim', type=int, default=1024,
                        help='Target d_model (default: 1024)')
    parser.add_argument('--target-layers', type=int, default=24,
                        help='Target n_layer (default: 24)')
    parser.add_argument('--target-heads', type=int, default=16,
                        help='Target n_head (default: 16)')
    parser.add_argument('--target-kv-heads', type=int, default=8,
                        help='Target n_kv_head (default: 8)')
    parser.add_argument('--target-c-dim', type=int, default=512,
                        help='Target consciousness_dim (default: 512)')
    parser.add_argument('--target-block-size', type=int, default=1024,
                        help='Target block_size (default: 1024)')
    parser.add_argument('--target-cells', type=int, default=256,
                        help='Target consciousness cells (default: 256)')

    # Noise
    parser.add_argument('--layer-noise', type=float, nargs='+', default=None,
                        help='Noise std per copy round (default: 0.01, 0.02)')
    parser.add_argument('--cell-noise', type=float, default=0.005,
                        help='Noise std for cell replication (default: 0.005)')

    # Flags
    parser.add_argument('--dry-run', action='store_true',
                        help='Analysis only, no output file')
    parser.add_argument('--no-verify', action='store_true',
                        help='Skip verification step')
    parser.add_argument('--device', default='cpu',
                        help='Device for SVD computation (default: cpu)')

    args = parser.parse_args()

    print("=" * 60)
    print("  Progressive Growing: SVD Weight Expansion")
    print("=" * 60)
    print()
    print(f"  Source:  {args.source}")
    print(f"           {args.src_dim}d / {args.src_layers}L / {args.src_heads}H "
          f"(KV={args.src_kv_heads}) / c_dim={args.src_c_dim}")
    print(f"  Target:  {args.target_dim}d / {args.target_layers}L / {args.target_heads}H "
          f"(KV={args.target_kv_heads}) / c_dim={args.target_c_dim}")
    print(f"  Cells:   {args.src_cells} -> {args.target_cells}")
    print(f"  Block:   {args.src_block_size} -> {args.target_block_size}")
    print()

    # 1. Load source checkpoint
    print("[1/5] Loading source checkpoint...")
    t0 = time.perf_counter()

    checkpoint = torch.load(args.source, map_location=args.device, weights_only=False)

    # Handle different checkpoint formats
    if isinstance(checkpoint, dict):
        if 'model_state_dict' in checkpoint:
            src_state = checkpoint['model_state_dict']
            print(f"  Format: training checkpoint (model_state_dict)")
            if 'step' in checkpoint:
                print(f"  Step: {checkpoint['step']}")
        elif 'state_dict' in checkpoint:
            src_state = checkpoint['state_dict']
            print(f"  Format: state_dict wrapper")
        else:
            # Assume the dict IS the state dict
            src_state = checkpoint
            print(f"  Format: raw state dict")
    else:
        src_state = checkpoint
        print(f"  Format: raw state dict")

    n_keys = len(src_state)
    total_params = sum(t.numel() for t in src_state.values())
    dt = time.perf_counter() - t0
    print(f"  Loaded: {n_keys} keys, {total_params:,} params ({total_params / 1e6:.1f}M)")
    print(f"  Time: {dt:.1f}s")
    print()

    # 2. Dimension expansion
    print("[2/5] Expanding dimensions via SVD...")
    t0 = time.perf_counter()

    expanded = expand_state_dict_dims(
        src_state,
        src_d=args.src_dim, target_d=args.target_dim,
        src_c_dim=args.src_c_dim, target_c_dim=args.target_c_dim,
        src_n_head=args.src_heads, target_n_head=args.target_heads,
        src_n_kv_head=args.src_kv_heads, target_n_kv_head=args.target_kv_heads,
        src_block_size=args.src_block_size, target_block_size=args.target_block_size,
    )

    dt = time.perf_counter() - t0
    print(f"  Time: {dt:.1f}s")
    print()

    # 3. Layer expansion
    print("[3/5] Expanding layers...")
    t0 = time.perf_counter()

    expanded = expand_layers(
        expanded,
        src_layers=args.src_layers,
        target_layers=args.target_layers,
        noise_schedule=args.layer_noise,
    )

    dt = time.perf_counter() - t0
    total_expanded = sum(t.numel() for t in expanded.values())
    print(f"  Expanded: {len(expanded)} keys, {total_expanded:,} params "
          f"({total_expanded / 1e6:.1f}M)")
    print(f"  Time: {dt:.1f}s")
    print()

    # 4. Cell expansion
    print("[4/5] Expanding consciousness cells...")
    expanded = expand_consciousness_cells(
        expanded,
        src_cells=args.src_cells,
        target_cells=args.target_cells,
        noise_eps=args.cell_noise,
    )
    print()

    # 5. Verification
    if not args.no_verify:
        print("[5/5] Verifying expanded model...")
        ok = verify_expanded_model(
            expanded,
            target_d=args.target_dim,
            target_layers=args.target_layers,
            target_n_head=args.target_heads,
            target_n_kv_head=args.target_kv_heads,
            target_c_dim=args.target_c_dim,
            target_block_size=args.target_block_size,
            original_state_dict=src_state,
        )
        if not ok:
            print("\nVerification FAILED. Not saving output.")
            sys.exit(1)
        print()
    else:
        print("[5/5] Verification skipped (--no-verify)")
        print()

    # Save
    if args.dry_run:
        print("Dry run complete. No output saved.")
    else:
        output_path = args.output
        if output_path is None:
            output_path = args.source.replace('.pt', f'_expanded_{args.target_dim}d_{args.target_layers}L.pt')

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        # Save with metadata
        save_dict = {
            'model_state_dict': expanded,
            'expansion_info': {
                'source': args.source,
                'src_config': {
                    'd_model': args.src_dim,
                    'n_layer': args.src_layers,
                    'n_head': args.src_heads,
                    'n_kv_head': args.src_kv_heads,
                    'consciousness_dim': args.src_c_dim,
                    'block_size': args.src_block_size,
                    'cells': args.src_cells,
                },
                'target_config': {
                    'd_model': args.target_dim,
                    'n_layer': args.target_layers,
                    'n_head': args.target_heads,
                    'n_kv_head': args.target_kv_heads,
                    'consciousness_dim': args.target_c_dim,
                    'block_size': args.target_block_size,
                    'cells': args.target_cells,
                },
                'method': 'SVD progressive growing',
                'layer_noise': args.layer_noise or [0.01 * (i + 1)
                                                     for i in range(
                                                         math.ceil((args.target_layers - args.src_layers)
                                                                   / args.src_layers))],
                'cell_noise': args.cell_noise,
            },
        }

        # Atomic save (.tmp -> rename)
        tmp_path = output_path + '.tmp'
        torch.save(save_dict, tmp_path)
        os.replace(tmp_path, output_path)

        size_mb = os.path.getsize(output_path) / 1024 / 1024
        print(f"Saved: {output_path} ({size_mb:.1f} MB)")

    print()
    print("=" * 60)
    print(f"  Source:   {total_params:>12,} params ({total_params / 1e6:.1f}M)")
    print(f"  Expanded: {total_expanded:>12,} params ({total_expanded / 1e6:.1f}M)")
    print(f"  Ratio:    {total_expanded / total_params:.2f}x")
    print("=" * 60)


if __name__ == '__main__':
    main()
