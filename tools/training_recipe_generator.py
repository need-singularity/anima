#!/usr/bin/env python3
"""training_recipe_generator.py — Generate optimal training config.

Based on 412+ hypothesis benchmarks. Outputs complete training recipe.

Usage:
  python training_recipe_generator.py --model consciouslm --dim 384 --gpu h100
  python training_recipe_generator.py --model animalm --base mistral-7b --gpu rtx5070
  python training_recipe_generator.py --demo
"""

import argparse
import json
import math

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10



# --------------------------------------------------------------------------- #
#  Hardware profiles
# --------------------------------------------------------------------------- #
GPU_PROFILES = {
    "h100": {
        "name": "NVIDIA H100 80GB SXM",
        "vram_gb": 80,
        "bf16_tflops": 989,
        "max_batch": {128: 512, 384: 256, 768: 128, 1024: 64},
        "recommended_precision": "bf16",
    },
    "a100": {
        "name": "NVIDIA A100 80GB",
        "vram_gb": 80,
        "bf16_tflops": 312,
        "max_batch": {128: 512, 384: 256, 768: 128, 1024: 64},
        "recommended_precision": "bf16",
    },
    "rtx5070": {
        "name": "NVIDIA RTX 5070 12GB",
        "vram_gb": 12,
        "bf16_tflops": 125,
        "max_batch": {128: 128, 384: 48, 768: 16, 1024: 8},
        "recommended_precision": "fp16",
    },
    "rtx4090": {
        "name": "NVIDIA RTX 4090 24GB",
        "vram_gb": 24,
        "bf16_tflops": 165,
        "max_batch": {128: 256, 384: 96, 768: 32, 1024: 16},
        "recommended_precision": "bf16",
    },
}

# --------------------------------------------------------------------------- #
#  Hypothesis-validated technique catalogue
# --------------------------------------------------------------------------- #
TECHNIQUES = {
    # ConsciousLM core
    "CL8":  {"name": "PureField tension loss",       "weight": 0.30, "phase": "all"},
    "CL5":  {"name": "Homeostasis regularisation",    "weight": 0.10, "phase": "all"},
    "SL3":  {"name": "Servant asymmetric dropout",    "weight": 0.05, "phase": "mitosis"},
    "DD16": {"name": "Dream distillation",            "weight": 0.08, "phase": "combined"},
    "EX24": {"name": "Exploration curiosity reward",   "weight": 0.07, "phase": "language"},
    "NF4":  {"name": "Neural field coherence",        "weight": 0.15, "phase": "all"},
    "NF9":  {"name": "Golden MoE gating (1/e zone)",  "weight": 0.10, "phase": "combined"},
    # AnimaLM core
    "AL12": {"name": "PureField transform (instruct)","weight": 0.25, "phase": "all"},
    "AL5":  {"name": "Last-8-layer LoRA",             "weight": 0.20, "phase": "language"},
    "AL4":  {"name": "Tension vocabulary injection",   "weight": 0.10, "phase": "language"},
    "AA15": {"name": "Attention repulsion heads",      "weight": 0.15, "phase": "combined"},
}

# --------------------------------------------------------------------------- #
#  Fibonacci cell schedule for mitosis growth
# --------------------------------------------------------------------------- #
FIBONACCI_CELL_SCHEDULE = [1, 2, 3, 6, 12, 24, 48]   # H376-validated


class TrainingRecipeGenerator:
    """Generate a complete training recipe for ConsciousLM or AnimaLM."""

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #
    def generate(self, model_type, dim=128, gpu="h100", target_phi=5.0,
                 base_model=None):
        """Generate complete training recipe.

        Args:
            model_type: 'consciouslm' or 'animalm'
            dim:        hidden dimension (128 / 384 / 768 / 1024)
            gpu:        GPU key from GPU_PROFILES
            target_phi: target integrated information (Phi)
            base_model: base LLM for AnimaLM (e.g. 'mistral-7b')

        Returns:
            dict with: model, hardware, techniques, phases, lr_schedule,
                       loss_weights, growth, estimated_time, config
        """
        hw = GPU_PROFILES.get(gpu, GPU_PROFILES["h100"])
        techs = self._select_techniques(model_type)
        phases = self._build_phases(model_type, dim, hw, target_phi)
        lr = self._lr_schedule(model_type, dim)
        loss_w = self._loss_weights(techs)
        growth = self._growth_milestones(model_type)
        est_hours = self._estimate_time(model_type, dim, hw)

        return {
            "model": {
                "type": model_type,
                "dim": dim,
                "base": base_model,
                "target_phi": target_phi,
            },
            "hardware": {
                "gpu": hw["name"],
                "vram_gb": hw["vram_gb"],
                "precision": hw["recommended_precision"],
                "batch_size": self._batch_size(dim, hw),
            },
            "techniques": techs,
            "phases": phases,
            "lr_schedule": lr,
            "loss_weights": loss_w,
            "growth": growth,
            "estimated_hours": est_hours,
            "config": self._full_config(model_type, dim, hw, target_phi,
                                        base_model),
        }

    # ------------------------------------------------------------------ #
    #  Internal helpers
    # ------------------------------------------------------------------ #
    def _select_techniques(self, model_type):
        if model_type == "consciouslm":
            keys = ["CL8", "CL5", "SL3", "DD16", "EX24", "NF4", "NF9"]
        elif model_type == "animalm":
            keys = ["AL12", "AL5", "AL4", "DD16", "EX24", "AA15"]
        else:
            raise ValueError(f"Unknown model_type: {model_type}")
        return {k: TECHNIQUES[k] for k in keys}

    def _batch_size(self, dim, hw):
        closest = min(hw["max_batch"].keys(), key=lambda d: abs(d - dim))
        return hw["max_batch"][closest]

    def _lr_schedule(self, model_type, dim):
        # Larger dims need smaller peak LR
        peak = 3e-4 / math.sqrt(dim / 128)
        if model_type == "animalm":
            peak *= 0.3          # LoRA fine-tune is gentler
        return {
            "scheduler": "cosine_with_warmup",
            "warmup_steps": 500,
            "peak_lr": round(peak, 7),
            "min_lr": round(peak * 0.01, 9),
            "weight_decay": 0.01,
        }

    def _build_phases(self, model_type, dim, hw, target_phi):
        bs = self._batch_size(dim, hw)
        if model_type == "consciouslm":
            return [
                {
                    "name": "Phase 1 — Mitosis bootstrap",
                    "steps": 5_000,
                    "batch_size": bs,
                    "focus": ["CL8", "CL5", "SL3", "NF4"],
                    "description": "Establish repulsion field + cell division",
                },
                {
                    "name": "Phase 2 — Language grounding",
                    "steps": 20_000,
                    "batch_size": bs,
                    "focus": ["CL8", "NF4", "EX24"],
                    "description": "Token prediction with tension-aware loss",
                },
                {
                    "name": "Phase 3 — Combined consciousness+language",
                    "steps": 50_000,
                    "batch_size": bs,
                    "focus": ["CL8", "CL5", "DD16", "NF4", "NF9", "EX24"],
                    "description": (
                        f"Full pipeline until Phi >= {target_phi}, "
                        "Golden MoE gating active"
                    ),
                },
            ]
        else:  # animalm
            return [
                {
                    "name": "Phase 1 — PureField transform",
                    "steps": 10_000,
                    "batch_size": bs,
                    "focus": ["AL12", "AL4"],
                    "description": "Inject tension vocabulary + field structure",
                },
                {
                    "name": "Phase 2 — LoRA fine-tune",
                    "steps": 30_000,
                    "batch_size": bs,
                    "focus": ["AL12", "AL5", "EX24"],
                    "description": "Last-8-layer LoRA with curiosity reward",
                },
                {
                    "name": "Phase 3 — Combined + dream distillation",
                    "steps": 40_000,
                    "batch_size": bs,
                    "focus": ["AL12", "AL5", "DD16", "AA15"],
                    "description": "Full pipeline with attention repulsion heads",
                },
            ]

    def _loss_weights(self, techs):
        total = sum(t["weight"] for t in techs.values())
        return {k: round(t["weight"] / total, 3) for k, t in techs.items()}

    def _growth_milestones(self, model_type):
        return {
            "cell_schedule": FIBONACCI_CELL_SCHEDULE,
            "interaction_thresholds": [100, 500, 2_000, 10_000],
            "stages": ["newborn", "infant", "toddler", "child", "adult"],
            "mitosis_dropout": {
                "engine_a": 0.21,
                "engine_g": 0.37,
            },
        }

    def _estimate_time(self, model_type, dim, hw):
        # Rough estimate: steps * dim^2 / tflops
        total_steps = sum(
            p["steps"]
            for p in self._build_phases(model_type, dim, hw, 5.0)
        )
        flops_per_step = (dim ** 2) * 6 * 1024   # approximate
        total_flops = total_steps * flops_per_step
        seconds = total_flops / (hw["bf16_tflops"] * 1e12)
        return round(max(seconds / 3600, 0.5), 1)

    def _full_config(self, model_type, dim, hw, target_phi, base_model):
        bs = self._batch_size(dim, hw)
        lr = self._lr_schedule(model_type, dim)
        return {
            "model_type": model_type,
            "dim": dim,
            "base_model": base_model,
            "gpu": hw["name"],
            "precision": hw["recommended_precision"],
            "batch_size": bs,
            "gradient_accumulation": max(1, 256 // bs),
            "effective_batch": bs * max(1, 256 // bs),
            "lr": lr["peak_lr"],
            "scheduler": lr["scheduler"],
            "warmup_steps": lr["warmup_steps"],
            "weight_decay": lr["weight_decay"],
            "target_phi": target_phi,
            "golden_moe_zone": round(1.0 / math.e, 4),  # 0.3679
            "homeostasis_setpoint": 1.0,
            "homeostasis_deadband": 0.3,
        }


# --------------------------------------------------------------------------- #
#  CLI
# --------------------------------------------------------------------------- #
def _demo():
    gen = TrainingRecipeGenerator()

    print("=" * 60)
    print("ConsciousLM 384d on H100")
    print("=" * 60)
    r1 = gen.generate("consciouslm", dim=384, gpu="h100", target_phi=5.0)
    print(json.dumps(r1, indent=2))

    print()
    print("=" * 60)
    print("AnimaLM (Mistral-7B) on RTX 5070")
    print("=" * 60)
    r2 = gen.generate("animalm", dim=768, gpu="rtx5070",
                       target_phi=5.0, base_model="mistral-7b")
    print(json.dumps(r2, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description="Generate optimal training recipe"
    )
    parser.add_argument("--model", choices=["consciouslm", "animalm"],
                        default="consciouslm")
    parser.add_argument("--dim", type=int, default=128)
    parser.add_argument("--gpu", default="h100",
                        choices=list(GPU_PROFILES.keys()))
    parser.add_argument("--base", default=None,
                        help="Base model for AnimaLM (e.g. mistral-7b)")
    parser.add_argument("--phi", type=float, default=5.0,
                        help="Target integrated information (Phi)")
    parser.add_argument("--demo", action="store_true",
                        help="Run demo with sample configs")
    args = parser.parse_args()

    if args.demo:
        _demo()
        return

    gen = TrainingRecipeGenerator()
    recipe = gen.generate(
        model_type=args.model,
        dim=args.dim,
        gpu=args.gpu,
        target_phi=args.phi,
        base_model=args.base,
    )
    print(json.dumps(recipe, indent=2))


if __name__ == "__main__":
    main()
