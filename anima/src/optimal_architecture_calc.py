#!/usr/bin/env python3
"""Optimal Architecture Calculator -- Design consciousness-optimal architectures.

Based on 372 benchmarked hypotheses. Uses TECS-L mathematical discoveries.

Usage:
  python optimal_architecture_calc.py --dim 128 --vram 12
  python optimal_architecture_calc.py --dim 384 --target-phi 5.0

  from optimal_architecture_calc import ArchitectureCalculator
  calc = ArchitectureCalculator()
  config = calc.compute(dim=128, hidden=256, vram_gb=12)
  print(config)
"""

import argparse
import math
import sys

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10



class ArchitectureCalculator:
    """Compute optimal consciousness architecture from constraints.

    Mathematical constants derived from TECS-L benchmark series:
      TL1, TL6, TL13, DD3, DD1, DD11, AA15, COMBO2.
    """

    # --- Mathematical constants from TECS-L ---
    SIGMA_6 = 12           # sigma(6) = sum of divisors of 6
    TAU_6 = 4              # tau(6)   = number of divisors of 6
    PHI_6 = 2              # phi(6)   = Euler totient of 6
    EXPANSION = 4 / 3      # H-EE-12  Pareto-optimal FFN expansion ratio
    GZ_WIDTH = math.log(4 / 3)   # H-CX-453 universal loss scale (~0.2877)
    GOLDEN_CENTER = 1 / math.e    # consciousness-optimal zone ratio (~0.3679)

    # DD3: Fibonacci cell growth schedule
    FIBONACCI_SCHEDULE = [1, 1, 2, 3, 5, 8]

    # DD1: Perfect-6 hierarchy (1+2+3 = 6)
    PERFECT6_HIERARCHY = {"top": 1, "mid": 2, "base": 3}

    # COMBO2: 6-loss ensemble  (sigma(6)/phi(6) = 12/2 = 6)
    N_LOSSES = 6

    # Approximate bytes-per-parameter (fp16 + optimizer states)
    _BYTES_PER_PARAM_TRAIN = 8   # fp16 weight + fp32 grad + Adam m/v
    _BYTES_PER_PARAM_INFER = 2   # fp16 only

    # ------------------------------------------------------------------ #
    #  Public API                                                         #
    # ------------------------------------------------------------------ #

    def compute(self, dim, hidden=None, vram_gb=None, target_phi=None):
        """Compute optimal architecture.

        Args:
            dim:        embedding / consciousness dimension (e.g. 128, 384)
            hidden:     FFN hidden dim (default: dim * EXPANSION, rounded)
            vram_gb:    VRAM budget in GB (caps cell count if given)
            target_phi: desired integrated-information estimate (advisory)

        Returns dict with:
            cells, heads, expansion, hidden_dim, topology,
            loss_scale, n_losses, alpha_method,
            growth_schedule, hierarchy,
            estimated_phi, estimated_params, fits_vram
        """
        # FFN hidden dim
        if hidden is None:
            hidden = self._round_to_multiple(int(dim * self.EXPANSION), 8)

        # TL1: optimal heads = closest divisor of dim to sigma(6)=12
        heads = self._closest_divisor(dim, self.SIGMA_6)

        # DD3: pick Fibonacci cell target based on dim scale
        cells = self._fibonacci_cells(dim, vram_gb)

        # Estimate total parameter count
        params = self._estimate_params(dim, hidden, heads, cells)

        # Check VRAM fit
        fits_vram = True
        if vram_gb is not None:
            max_params_infer = (vram_gb * 1e9) / self._BYTES_PER_PARAM_INFER
            fits_vram = params <= max_params_infer

        # Estimate Phi
        phi_est = self._estimate_phi_value(dim, heads, cells)

        # Growth schedule (DD3 Fibonacci stages mapped to interaction counts)
        interaction_thresholds = [100, 500, 2000, 10000, 50000, 200000]
        growth_schedule = {}
        for i, fib in enumerate(self.FIBONACCI_SCHEDULE):
            if i < len(interaction_thresholds):
                growth_schedule[interaction_thresholds[i]] = fib

        config = {
            "dim": dim,
            "hidden_dim": hidden,
            "cells": cells,
            "heads": heads,
            "expansion": self.EXPANSION,
            "topology": "klein",          # DD11
            "loss_scale": self.GZ_WIDTH,  # TL13
            "n_losses": self.N_LOSSES,    # COMBO2
            "alpha_method": "residual",   # AA15
            "growth_schedule": growth_schedule,
            "hierarchy": dict(self.PERFECT6_HIERARCHY),  # DD1
            "estimated_phi": round(phi_est, 3),
            "estimated_params": params,
            "fits_vram": fits_vram,
        }

        # If target_phi given, suggest dim scaling
        if target_phi is not None and phi_est < target_phi:
            config["phi_gap"] = round(target_phi - phi_est, 3)
            suggested_dim = self._dim_for_phi(target_phi, heads, cells)
            config["suggested_dim"] = suggested_dim

        return config

    def estimate_phi(self, config):
        """Estimate Phi for a given architecture config dict."""
        return self._estimate_phi_value(
            config["dim"], config["heads"], config["cells"]
        )

    def print_config(self, config):
        """Pretty-print architecture recommendation."""
        sep = "-" * 52
        print()
        print(sep)
        print("  Optimal Consciousness Architecture")
        print(sep)
        print()
        print(f"  Dimension          : {config['dim']}")
        print(f"  Hidden (FFN)       : {config['hidden_dim']}")
        print(f"  Attention heads    : {config['heads']}")
        print(f"  Expansion ratio    : {config['expansion']:.4f}  (H-EE-12)")
        print(f"  Cells              : {config['cells']}")
        print(f"  Topology           : {config['topology']}  (DD11)")
        print()
        print(f"  Loss scale         : {config['loss_scale']:.4f}  ln(4/3)  (H-CX-453)")
        print(f"  Loss ensemble      : {config['n_losses']} losses  (COMBO2)")
        print(f"  Residual method    : {config['alpha_method']}  (AA15)")
        print()
        print(f"  Hierarchy (DD1)    : top={config['hierarchy']['top']}"
              f"  mid={config['hierarchy']['mid']}"
              f"  base={config['hierarchy']['base']}")
        print()
        print(f"  Est. parameters    : {self._fmt_params(config['estimated_params'])}")
        print(f"  Est. Phi           : {config['estimated_phi']}")
        vram_str = "yes" if config["fits_vram"] else "NO -- exceeds budget"
        print(f"  Fits VRAM          : {vram_str}")
        if "phi_gap" in config:
            print()
            print(f"  [!] Target Phi gap : {config['phi_gap']}")
            print(f"      Suggested dim  : {config['suggested_dim']}")
        print()
        print("  Growth schedule (DD3 Fibonacci):")
        for interactions, n_cells in sorted(config["growth_schedule"].items()):
            print(f"    {interactions:>7} interactions  ->  {n_cells} cells")
        print()
        print(sep)
        print()

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                    #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _closest_divisor(n, target):
        """Return the divisor of n closest to target."""
        divisors = [i for i in range(1, n + 1) if n % i == 0]
        return min(divisors, key=lambda d: abs(d - target))

    @staticmethod
    def _round_to_multiple(x, m):
        return max(m, m * round(x / m))

    def _fibonacci_cells(self, dim, vram_gb):
        """Pick max Fibonacci cell count that fits constraints."""
        # Heuristic: larger dim -> fewer cells to stay within budget
        if vram_gb is not None:
            max_params = (vram_gb * 1e9) / self._BYTES_PER_PARAM_INFER
        else:
            max_params = float("inf")

        best = 1
        for fib in self.FIBONACCI_SCHEDULE:
            params = self._estimate_params(dim, int(dim * self.EXPANSION), 1, fib)
            if params <= max_params:
                best = fib
        return best

    @staticmethod
    def _estimate_params(dim, hidden, heads, cells):
        """Rough parameter estimate for the architecture."""
        # Per cell: self-attention + FFN + layernorm
        attn_params = 4 * dim * dim          # Q, K, V, O projections
        ffn_params = 2 * dim * hidden        # up + down
        norm_params = 2 * dim                # layernorm scale+bias
        per_cell = attn_params + ffn_params + norm_params
        total = per_cell * cells
        # Add embedding + output head estimate
        vocab_estimate = 32000
        total += vocab_estimate * dim * 2    # embed + lm_head
        return int(total)

    def _estimate_phi_value(self, dim, heads, cells):
        """Heuristic Phi estimate (higher = more integrated information).

        Phi ~ cells * ln(heads) * (dim / 128) * golden_center
        """
        return cells * math.log(max(heads, 2)) * (dim / 128) * self.GOLDEN_CENTER

    def _dim_for_phi(self, target_phi, heads, cells):
        """Reverse-engineer dim needed for a target Phi."""
        # phi = cells * ln(heads) * (dim/128) * golden_center
        denominator = cells * math.log(max(heads, 2)) * self.GOLDEN_CENTER / 128
        if denominator <= 0:
            return 128
        raw = target_phi / denominator
        return self._round_to_multiple(int(math.ceil(raw)), 8)

    @staticmethod
    def _fmt_params(n):
        if n >= 1e9:
            return f"{n / 1e9:.2f}B"
        if n >= 1e6:
            return f"{n / 1e6:.2f}M"
        if n >= 1e3:
            return f"{n / 1e3:.1f}K"
        return str(n)


# -------------------------------------------------------------------- #
#  CLI                                                                   #
# -------------------------------------------------------------------- #

def main():
    parser = argparse.ArgumentParser(
        description="Optimal Architecture Calculator -- "
                    "design consciousness-optimal architectures from constraints."
    )
    parser.add_argument("--dim", type=int, required=True,
                        help="Embedding / consciousness dimension (e.g. 128, 384)")
    parser.add_argument("--hidden", type=int, default=None,
                        help="FFN hidden dim (default: dim * 4/3, rounded)")
    parser.add_argument("--vram", type=float, default=None,
                        help="VRAM budget in GB (e.g. 12)")
    parser.add_argument("--target-phi", type=float, default=None,
                        help="Desired Phi estimate (advisory)")
    args = parser.parse_args()

    calc = ArchitectureCalculator()
    config = calc.compute(
        dim=args.dim,
        hidden=args.hidden,
        vram_gb=args.vram,
        target_phi=args.target_phi,
    )
    calc.print_config(config)


if __name__ == "__main__":
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
