#!/usr/bin/env python3
"""mi_gpu_ref.py — Numerical reference + offline GPU microbenchmark for
Mutual Information batch kernel (hexa-lang perf attack #5).

NON-AUTHORITATIVE. This file exists ONLY to (a) verify the log-bin MI
estimator in training/phi_auto_measure.hexa against a second implementation,
and (b) gather wall-clock numbers for the hexa_perf_gpu_mi.md paper on
machines where the hexa GPU toolchain is remote (H100 on RunPod). The
production kernel is training/mi_gpu_batch.hexa (pure hexa + cuda_ffi +
NVRTC). Do NOT import this from any .hexa file.

Usage:
    python3 mi_gpu_ref.py --batch 110 --n 1024
    python3 mi_gpu_ref.py --batch 5   --n 1024   # PoC
"""

from __future__ import annotations
import argparse
import math
import time
import numpy as np

MI_BINS = 8


# ---------------------------------------------------------------------------
# Reference #1 — byte-identical reproduction of phi_auto_measure.hexa
# ---------------------------------------------------------------------------

def _bin_index(x: float, lo: float, hi: float, nb: int) -> int:
    if hi <= lo:
        return 0
    t = (x - lo) / (hi - lo)
    idx = int(t * nb)
    if idx < 0:
        idx = 0
    if idx >= nb:
        idx = nb - 1
    return idx


def cpu_mi_scalar(a: np.ndarray, b: np.ndarray) -> float:
    """Matches phi_auto_measure.hexa:mutual_info exactly."""
    n = a.size
    if n == 0:
        return 0.0
    lo = min(float(a.min()), float(b.min()))
    hi = max(float(a.max()), float(b.max()))
    nb = MI_BINS
    ha = [0] * nb
    hb = [0] * nb
    hj = [0] * (nb * nb)
    for i in range(n):
        ia = _bin_index(float(a[i]), lo, hi, nb)
        ib = _bin_index(float(b[i]), lo, hi, nb)
        ha[ia] += 1
        hb[ib] += 1
        hj[ia * nb + ib] += 1
    inv_n = 1.0 / n
    H_a = sum(-(c * inv_n) * math.log(c * inv_n) for c in ha if c > 0)
    H_b = sum(-(c * inv_n) * math.log(c * inv_n) for c in hb if c > 0)
    H_ab = sum(-(c * inv_n) * math.log(c * inv_n) for c in hj if c > 0)
    mi = H_a + H_b - H_ab
    return max(0.0, mi)


# ---------------------------------------------------------------------------
# Reference #2 — vectorized numpy (speed-only, same math)
# ---------------------------------------------------------------------------

def cpu_mi_numpy(a: np.ndarray, b: np.ndarray) -> float:
    lo = min(a.min(), b.min())
    hi = max(a.max(), b.max())
    if hi <= lo:
        return 0.0
    nb = MI_BINS
    t_a = np.clip(((a - lo) / (hi - lo) * nb).astype(np.int64), 0, nb - 1)
    t_b = np.clip(((b - lo) / (hi - lo) * nb).astype(np.int64), 0, nb - 1)
    ha = np.bincount(t_a, minlength=nb)
    hb = np.bincount(t_b, minlength=nb)
    hj = np.bincount(t_a * nb + t_b, minlength=nb * nb)
    n = a.size
    def H(c):
        p = c[c > 0] / n
        return float(-(p * np.log(p)).sum())
    mi = H(ha) + H(hb) - H(hj)
    return max(0.0, mi)


# ---------------------------------------------------------------------------
# Reference #3 — vectorized batched numpy (for 110-engine comparison)
# ---------------------------------------------------------------------------

def cpu_mi_batch(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    """A, B : (batch, N) float32."""
    batch = A.shape[0]
    out = np.empty(batch, dtype=np.float32)
    for i in range(batch):
        out[i] = cpu_mi_numpy(A[i], B[i])
    return out


# ---------------------------------------------------------------------------
# GPU MI batch — torch.bincount fallback (only if cuda available)
# ---------------------------------------------------------------------------

def gpu_mi_batch_torch(A: np.ndarray, B: np.ndarray, warmup: int = 3,
                       trials: int = 10) -> tuple[np.ndarray, float, float]:
    """Numerical twin of the hexa CUDA kernel, running on whatever GPU torch sees.
    Returns (mi_values, steady_wall_ms, first_call_ms). If torch/cuda unavailable,
    raises RuntimeError. Warmup runs are discarded to measure steady-state, since
    the hexa NVRTC path also has one-time PTX compilation + module load."""
    try:
        import torch
    except ImportError as e:
        raise RuntimeError("torch not installed") from e
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA not available")
    device = torch.device("cuda")
    nb = MI_BINS
    A_t = torch.from_numpy(A).to(device)
    B_t = torch.from_numpy(B).to(device)

    def _run() -> tuple[np.ndarray, float]:
        torch.cuda.synchronize()
        t0 = time.perf_counter()
        lo = torch.minimum(A_t.min(dim=1).values, B_t.min(dim=1).values)
        hi = torch.maximum(A_t.max(dim=1).values, B_t.max(dim=1).values)
        denom = (hi - lo).clamp_min(1e-12).unsqueeze(1)
        lo_e = lo.unsqueeze(1)
        ia = torch.clamp(((A_t - lo_e) / denom * nb).long(), 0, nb - 1)
        ib = torch.clamp(((B_t - lo_e) / denom * nb).long(), 0, nb - 1)
        batch, n = A_t.shape
        rng = torch.arange(batch, device=device).unsqueeze(1)
        joint = rng * (nb * nb) + ia * nb + ib
        hj = torch.bincount(joint.flatten(), minlength=batch * nb * nb).view(batch, nb, nb).float()
        ha = hj.sum(dim=2)
        hb = hj.sum(dim=1)
        inv_n = 1.0 / n
        def H(c):
            p = c * inv_n
            mask = p > 0
            return torch.where(mask, -p * torch.log(p.clamp_min(1e-30)), torch.zeros_like(p)).sum(dim=-1)
        mi = H(ha) + H(hb) - H(hj.view(batch, -1))
        mi = mi.clamp_min(0)
        torch.cuda.synchronize()
        t1 = time.perf_counter()
        return mi.cpu().numpy(), (t1 - t0) * 1000.0

    vals, first_ms = _run()
    for _ in range(max(0, warmup - 1)):
        _run()
    # steady-state: median of `trials`
    ts = []
    for _ in range(trials):
        _, t = _run()
        ts.append(t)
    return vals, float(np.median(ts)), first_ms


# ---------------------------------------------------------------------------
# Main benchmark
# ---------------------------------------------------------------------------

def det_rand(n: int, seed: int) -> np.ndarray:
    """Matches phi_auto_measure.hexa:det_rand bit-for-bit (LCG)."""
    out = np.empty(n, dtype=np.float32)
    s = seed
    for i in range(n):
        s = (s * 1103515245 + 12345) % 2147483648
        out[i] = (s % 1000000) / 1000000.0 * 2.0 - 1.0
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=int, default=110)
    ap.add_argument("--n", type=int, default=1024)
    ap.add_argument("--poc", action="store_true")
    args = ap.parse_args()
    batch, n = args.batch, args.n
    print(f"[mi_gpu_ref] batch={batch} N={n}")
    A = np.stack([det_rand(n, 1337 + e * 7)  for e in range(batch)]).astype(np.float32)
    B = np.stack([det_rand(n, 9001 + e * 11) for e in range(batch)]).astype(np.float32)

    # --- CPU scalar (byte-identical to .hexa) ---
    t0 = time.perf_counter()
    cpu_scalar = np.array([cpu_mi_scalar(A[i], B[i]) for i in range(batch)])
    t_cpu_scalar = (time.perf_counter() - t0) * 1000.0
    print(f"[cpu-scalar ] {batch}× serial: {t_cpu_scalar:8.2f} ms  "
          f"(per-engine {t_cpu_scalar/batch:6.3f} ms)")

    # --- CPU numpy vectorized (same math, faster impl) ---
    t0 = time.perf_counter()
    cpu_np = cpu_mi_batch(A, B)
    t_cpu_np = (time.perf_counter() - t0) * 1000.0
    print(f"[cpu-numpy  ] {batch}× numpy:  {t_cpu_np:8.2f} ms  "
          f"(per-engine {t_cpu_np/batch:6.3f} ms)")

    # consistency: scalar vs numpy
    err_cpu = float(np.abs(cpu_scalar - cpu_np).max())
    print(f"[consistency] max|scalar - numpy| = {err_cpu:.3e}")
    assert err_cpu < 1e-5, "numpy reference drifted from scalar"

    # --- GPU (if available) ---
    try:
        gpu_vals, t_gpu, t_gpu_first = gpu_mi_batch_torch(A, B)
        err_gpu = float(np.abs(cpu_scalar - gpu_vals).max())
        print(f"[gpu-torch  ] {batch}× batched (first-call): {t_gpu_first:8.2f} ms (JIT+alloc)")
        print(f"[gpu-torch  ] {batch}× batched (steady   ):  {t_gpu:8.2f} ms  "
              f"(per-engine {t_gpu*1000/batch:6.1f} us)")
        print(f"[accuracy   ] max|cpu - gpu|  = {err_gpu:.3e}")
        print(f"[speedup    ] CPU/GPU (scalar, steady) = {t_cpu_scalar / max(t_gpu, 1e-6):.1f}x")
        print(f"[speedup    ] CPU/GPU (numpy,  steady) = {t_cpu_np    / max(t_gpu, 1e-6):.1f}x")
    except RuntimeError as e:
        print(f"[gpu-torch  ] skipped: {e}")
        print("            (hexa CUDA kernel target; run on H100 for production numbers)")


if __name__ == "__main__":
    main()
