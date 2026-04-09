#!/usr/bin/env python3
"""
convert_to_hexaw.py — Convert PyTorch .pt weights to HEXAW binary format.

HEXAW format (matches load_weights_bin / mmap_weights in hexa-lang):
  Header:  b"HEXAW\0" (6B) + version:u32 LE (4B) + n_tensors:u32 LE (4B)
  Per tensor:
    name_len:u32 LE + name:bytes
    ndim:u32 LE + shape:u32 LE * ndim
    data:f32 LE * product(shape)

Usage:
  # From .pt checkpoint (default: decoder state dict)
  python3 convert_to_hexaw.py best.pt weights_v14.hexaw

  # From .pt with custom state dict key
  python3 convert_to_hexaw.py best.pt weights_v14.hexaw --key model

  # From JSON weights directory (created by load_weights.hexa workflow)
  python3 convert_to_hexaw.py weights_dir/ weights_v14.hexaw --json

  # Skip tensors with dim > 2 (default behavior for .pt mode)
  # Include all tensors:
  python3 convert_to_hexaw.py best.pt weights_v14.hexaw --all-dims
"""

import argparse
import json
import os
import struct
import sys
from pathlib import Path


def write_hexaw(tensors: list[tuple[str, list[int], list[float]]], out_path: str):
    """Write tensors to HEXAW binary format.

    Args:
        tensors: list of (name, shape, flat_data_f32)
        out_path: output file path
    """
    n = len(tensors)
    with open(out_path, "wb") as f:
        # Header
        f.write(b"HEXAW\0")
        f.write(struct.pack("<I", 1))  # version = 1
        f.write(struct.pack("<I", n))  # n_tensors

        total_params = 0
        for name, shape, data in tensors:
            name_bytes = name.encode("utf-8")
            f.write(struct.pack("<I", len(name_bytes)))
            f.write(name_bytes)
            f.write(struct.pack("<I", len(shape)))
            for s in shape:
                f.write(struct.pack("<I", s))
            # Write f32 LE data
            f.write(struct.pack(f"<{len(data)}f", *data))
            total_params += len(data)

    file_size = os.path.getsize(out_path)
    print(f"Wrote {out_path}")
    print(f"  {n} tensors, {total_params:,} params")
    print(f"  {file_size:,} bytes ({file_size / 1024 / 1024:.1f} MB)")


def load_from_pt(pt_path: str, key: str | None = None, max_dim: int = 2) -> list[tuple[str, list[int], list[float]]]:
    """Load tensors from a PyTorch checkpoint."""
    import torch

    ckpt = torch.load(pt_path, map_location="cpu", weights_only=False)

    # Find state dict
    if key:
        state = ckpt[key]
    elif isinstance(ckpt, dict):
        # Try common keys
        for k in ["decoder", "model", "state_dict", "model_state_dict"]:
            if k in ckpt:
                state = ckpt[k]
                print(f"  Using state dict key: '{k}'")
                break
        else:
            # Maybe the checkpoint IS the state dict
            state = ckpt
    else:
        state = ckpt

    tensors = []
    skipped = 0
    for name, tensor in state.items():
        if not hasattr(tensor, "dim"):
            continue
        if max_dim and tensor.dim() > max_dim:
            skipped += 1
            continue
        shape = list(tensor.shape)
        data = tensor.float().detach().flatten().tolist()
        tensors.append((name, shape, data))

    if skipped:
        print(f"  Skipped {skipped} tensors with dim > {max_dim}")
    print(f"  Found {len(tensors)} tensors")
    return tensors


def load_from_json(dir_path: str) -> list[tuple[str, list[int], list[float]]]:
    """Load tensors from JSON weight directory (with _manifest.json)."""
    manifest_path = os.path.join(dir_path, "_manifest.json")
    with open(manifest_path) as f:
        manifest = json.load(f)

    tensors = []
    for name, info in manifest.items():
        filepath = os.path.join(dir_path, info["file"])
        shape = info["shape"]
        with open(filepath) as f:
            data = json.load(f)
        tensors.append((name, shape, data))
        if len(tensors) <= 5 or len(tensors) % 50 == 0:
            print(f"  [{len(tensors)}/{len(manifest)}] {name}: {info['numel']} params")

    print(f"  Found {len(tensors)} tensors")
    return tensors


def main():
    parser = argparse.ArgumentParser(description="Convert weights to HEXAW binary format")
    parser.add_argument("input", help="Path to .pt file or JSON weights directory")
    parser.add_argument("output", help="Output .hexaw file path")
    parser.add_argument("--key", help="State dict key in checkpoint (auto-detected if omitted)")
    parser.add_argument("--json", action="store_true", help="Input is a JSON weights directory")
    parser.add_argument("--all-dims", action="store_true", help="Include tensors of any dimensionality")
    args = parser.parse_args()

    print(f"Converting {args.input} -> {args.output}")

    if args.json:
        tensors = load_from_json(args.input)
    else:
        max_dim = 0 if args.all_dims else 2
        tensors = load_from_pt(args.input, key=args.key, max_dim=max_dim)

    write_hexaw(tensors, args.output)
    print("Done.")


if __name__ == "__main__":
    main()
