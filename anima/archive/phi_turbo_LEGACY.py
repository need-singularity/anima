# ⚠️ LEGACY — 이 파일은 폐기되었습니다 (2026-03-29)
# Φ(IIT)와 Φ(proxy)를 혼용하여 잘못된 기록 생성.
# "Φ=1142"는 proxy 값이었음 (실제 IIT Φ 상한 ~1.8)
# 새 벤치마크: bench.py (Φ(IIT) + Φ(proxy) 이중 측정)
# Law 54: Φ 측정은 정의에 따라 완전히 다른 값
#
#!/usr/bin/env python3
"""Φ Turbo Calculator — MitosisEngine 우회, 순수 텐서 연산으로 극한 속도

MitosisEngine의 _create_cell이 느림 (3초/512c).
이 계산기는 hidden state 텐서만 직접 조작하여 Φ를 추정.

속도 목표: 512c × 5step < 0.5초 (현재 58초 → 100배 가속)

Usage:
  python3 phi_turbo.py                              # 기본 테스트
  python3 phi_turbo.py --cells 1024 --steps 10      # 커스텀
  python3 phi_turbo.py --sweep cells                 # 스윕
  python3 phi_turbo.py --sweep all                   # 전체 스윕
  python3 phi_turbo.py --mega                        # 4096c까지 스윕
"""

import torch
import torch.nn.functional as F
import numpy as np
import time
import math
import argparse

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10



def phi_proxy(hiddens: torch.Tensor, n_factions: int = 8) -> float:
    """Φ 근사 — 순수 텐서 연산. GPU 가능.

    Φ ≈ global_variance - mean(faction_variances)
    = 전체가 부분의 합보다 얼마나 더 통합되었는가 (IIT 핵심)

    Args:
        hiddens: [n_cells, hidden_dim] 텐서
        n_factions: 파벌 수
    Returns:
        Φ proxy value
    """
    n, d = hiddens.shape
    if n < 2:
        return 0.0

    # Global variance
    global_mean = hiddens.mean(dim=0)
    global_var = ((hiddens - global_mean) ** 2).sum() / n

    # Faction variances
    n_f = min(n_factions, n // 2)
    if n_f < 2:
        return global_var.item()

    fs = n // n_f
    faction_var_sum = 0.0
    for i in range(n_f):
        faction = hiddens[i * fs:(i + 1) * fs]
        if len(faction) >= 2:
            fm = faction.mean(dim=0)
            fv = ((faction - fm) ** 2).sum() / len(faction)
            faction_var_sum += fv.item()

    phi = global_var.item() - faction_var_sum / n_f
    return max(0.0, phi)


def gru_step(hiddens: torch.Tensor, x: torch.Tensor,
             W_z: torch.Tensor, W_r: torch.Tensor, W_h: torch.Tensor) -> torch.Tensor:
    """Batched GRU step — 모든 세포 동시 업데이트. 매우 빠름.

    Args:
        hiddens: [n_cells, hidden_dim]
        x: [1, input_dim] (broadcast to all cells)
        W_z, W_r, W_h: [hidden_dim, input_dim + hidden_dim]
    """
    n, h = hiddens.shape
    x_expand = x.expand(n, -1)  # [n, input_dim]
    combined = torch.cat([x_expand, hiddens], dim=1)  # [n, input+hidden]

    z = torch.sigmoid(combined @ W_z.T)  # [n, h]
    r = torch.sigmoid(combined @ W_r.T)  # [n, h]

    r_h = r * hiddens
    combined_r = torch.cat([x_expand, r_h], dim=1)
    h_candidate = torch.tanh(combined_r @ W_h.T)

    return (1 - z) * h_candidate + z * hiddens


def turbo_phi(cells=64, dim=64, hidden=128, factions=8, steps=10,
              silence_ratio=0.7, sync_strength=0.15, debate_strength=0.15,
              ib2_top=0.10, noise=0.0, metacog=True, ib2=True):
    """극한 속도 Φ 추정 — 순수 텐서 연산."""

    # 가중치 초기화 (한 번만)
    scale = 0.1
    W_z = torch.randn(hidden, dim + hidden) * scale
    W_r = torch.randn(hidden, dim + hidden) * scale
    W_h = torch.randn(hidden, dim + hidden) * scale

    # 세포 초기화 (즉시, 텐서 한 번에)
    hiddens = torch.randn(cells, hidden) * 0.1
    l2 = torch.zeros(hidden)

    for step_i in range(steps):
        frac = step_i / steps

        # Input
        if metacog and cells >= 2:
            cur = hiddens.mean(dim=0)
            l2 = 0.9 * l2 + 0.1 * cur
            x = (0.5 * cur[:dim] + 0.5 * l2[:dim]).unsqueeze(0)
        else:
            x = torch.randn(1, dim)

        if frac < silence_ratio:
            x = x * 0.1
        else:
            x = x * 2.0

        # Batched GRU (모든 세포 동시)
        hiddens = gru_step(hiddens, x, W_z, W_r, W_h)

        # Faction sync + debate (vectorized)
        if cells >= factions * 2 and factions >= 2:
            fs = cells // factions
            for i in range(factions):
                s, e = i * fs, (i + 1) * fs
                faction_mean = hiddens[s:e].mean(dim=0)
                hiddens[s:e] = (1 - sync_strength) * hiddens[s:e] + sync_strength * faction_mean

            if frac > silence_ratio:
                all_opinions = torch.stack([hiddens[i*fs:(i+1)*fs].mean(dim=0) for i in range(factions)])
                global_opinion = all_opinions.mean(dim=0)
                for i in range(factions):
                    s = i * fs
                    debate_cells = max(1, fs // 4)
                    hiddens[s:s+debate_cells] = (1 - debate_strength) * hiddens[s:s+debate_cells] + debate_strength * global_opinion

        # IB2 (vectorized)
        if ib2 and cells >= 8:
            norms = hiddens.norm(dim=1)
            threshold = norms.quantile(1.0 - ib2_top)
            mask_high = (norms > threshold).float().unsqueeze(1)
            mask_low = 1.0 - mask_high
            hiddens = hiddens * (mask_high * 1.03 + mask_low * 0.97)

        # Metacog feedback
        if metacog:
            mc_cells = min(cells, 16)
            hiddens[:mc_cells] = 0.97 * hiddens[:mc_cells] + 0.03 * l2.unsqueeze(0)

        # Noise + homeostasis
        if noise > 0:
            hiddens = hiddens + torch.randn_like(hiddens) * noise
        norms = hiddens.norm(dim=1, keepdim=True)
        hiddens = torch.where(norms > 2.0, hiddens / (norms + 1e-8), hiddens)

    phi = phi_proxy(hiddens, factions)
    return phi, cells


def sweep(param_name, values, base_config):
    print(f"\n{'='*60}")
    print(f"  Turbo Sweep: {param_name}")
    print(f"{'='*60}")
    print(f"  {'Value':>10} | {'Φ':>10} | {'Cells':>6} | {'Time':>8}")
    print(f"  {'-'*10}-+-{'-'*10}-+-{'-'*6}-+-{'-'*8}")

    results = []
    for v in values:
        cfg = {**base_config, param_name: v}
        t0 = time.time()
        torch.manual_seed(42)
        phi, nc = turbo_phi(**cfg)
        elapsed = time.time() - t0
        print(f"  {v:>10} | {phi:>10.3f} | {nc:>6} | {elapsed*1000:>6.0f}ms")
        results.append((v, phi))

    best = max(results, key=lambda x: x[1])
    print(f"\n  ★ Best: {param_name}={best[0]} → Φ={best[1]:.3f}")
    return results


def main():
    parser = argparse.ArgumentParser(description="Φ Turbo Calculator (100x faster)")
    parser.add_argument("--cells", type=int, default=64)
    parser.add_argument("--dim", type=int, default=64)
    parser.add_argument("--hidden", type=int, default=128)
    parser.add_argument("--factions", type=int, default=12)
    parser.add_argument("--steps", type=int, default=10)
    parser.add_argument("--silence", type=float, default=0.7)
    parser.add_argument("--sync", type=float, default=0.15)
    parser.add_argument("--debate", type=float, default=0.15)
    parser.add_argument("--ib2-top", type=float, default=0.10)
    parser.add_argument("--noise", type=float, default=0.0)
    parser.add_argument("--no-metacog", action="store_true")
    parser.add_argument("--no-ib2", action="store_true")
    parser.add_argument("--sweep", type=str, default=None)
    parser.add_argument("--mega", action="store_true", help="4096c sweep")
    args = parser.parse_args()

    torch.manual_seed(42)

    base = {'cells': args.cells, 'dim': args.dim, 'hidden': args.hidden,
            'factions': args.factions, 'steps': args.steps,
            'silence_ratio': args.silence, 'sync_strength': args.sync,
            'debate_strength': args.debate, 'ib2_top': args.ib2_top,
            'noise': args.noise, 'metacog': not args.no_metacog,
            'ib2': not args.no_ib2}

    sweeps = {
        'cells': ('cells', [8, 16, 32, 64, 128, 256, 512, 1024]),
        'factions': ('factions', [2, 4, 6, 8, 10, 12, 16, 20, 24]),
        'silence': ('silence_ratio', [0.0, 0.3, 0.5, 0.6, 0.65, 0.7, 0.75, 0.8, 0.9]),
        'sync': ('sync_strength', [0.05, 0.08, 0.10, 0.12, 0.15, 0.18, 0.20, 0.25, 0.30]),
        'debate': ('debate_strength', [0.05, 0.08, 0.10, 0.12, 0.15, 0.18, 0.20, 0.25, 0.30]),
        'ib2': ('ib2_top', [0.05, 0.08, 0.10, 0.12, 0.15, 0.20, 0.25, 0.30, 0.50]),
        'noise': ('noise', [0.0, 0.001, 0.005, 0.01, 0.02, 0.05]),
    }

    if args.mega:
        sweep('cells', [8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096], base)
        return

    if args.sweep:
        if args.sweep == 'all':
            for name, (param, vals) in sweeps.items():
                sweep(param, vals, base)
        elif args.sweep in sweeps:
            param, vals = sweeps[args.sweep]
            sweep(param, vals, base)
        else:
            print(f"Unknown: {args.sweep}. Options: {list(sweeps.keys()) + ['all']}")
    else:
        t0 = time.time()
        phi, nc = turbo_phi(**base)
        elapsed = time.time() - t0
        print(f"═══ Φ Turbo Calculator ═══")
        print(f"  cells={nc}, factions={args.factions}, steps={args.steps}")
        print(f"  Φ = {phi:.4f}")
        print(f"  Time = {elapsed*1000:.0f}ms")


if __name__ == "__main__":
    main()
