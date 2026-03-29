"""ConsciousnessArchaeology — Dig through checkpoint history."""

import math, os, glob, re
from dataclasses import dataclass, field
from typing import List, Dict, Optional

LN2 = math.log(2)
PSI_BALANCE = 0.5
PSI_COUPLING = LN2 / 2**5.5
PSI_STEPS = 3 / LN2

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


@dataclass
class CheckpointInfo:
    path: str
    step: int
    size_mb: float
    keys: List[str] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class EmergenceEvent:
    step: int
    behavior: str
    evidence: str
    magnitude: float


class ConsciousnessArchaeology:
    """Dig through checkpoint history to find emergence events."""

    BEHAVIOR_SIGNATURES = {
        "speech": ["output", "speak", "voice", "decoder", "lm_head"],
        "emotion": ["emotion", "valence", "arousal", "affect"],
        "memory": ["memory", "retrieval", "rag", "embedding"],
        "self_awareness": ["self", "identity", "meta", "reflect"],
        "empathy": ["empathy", "mirror", "social", "other"],
        "creativity": ["creative", "generate", "novel", "diverge"],
        "phi_integration": ["phi", "integrate", "iit", "information"],
    }

    def __init__(self):
        self.checkpoints: List[CheckpointInfo] = []
        self.events: List[EmergenceEvent] = []

    def load_checkpoints(self, directory: str) -> List[CheckpointInfo]:
        """Scan directory for checkpoint files and extract metadata."""
        self.checkpoints = []
        files = set()
        for pat in ["*.pt", "*.pth", "*.ckpt"]:
            files.update(glob.glob(os.path.join(directory, "**", pat), recursive=True))
        for f in sorted(files):
            step = int(m[-1]) if (m := re.findall(r'(\d+)', os.path.basename(f))) else 0
            info = CheckpointInfo(path=f, step=step,
                                  size_mb=round(os.path.getsize(f) / 1048576, 2))
            if HAS_TORCH:
                try:
                    state = torch.load(f, map_location="cpu", weights_only=True)
                    if isinstance(state, dict):
                        sd = state.get("model_state_dict", state)
                        info.keys = [k for k in sd if not k.startswith("_")]
                        for metric in ["phi", "ce", "loss"]:
                            if metric in state:
                                info.metrics[metric] = float(state[metric])
                except Exception:
                    pass
            self.checkpoints.append(info)
        self.checkpoints.sort(key=lambda c: c.step)
        return self.checkpoints

    def find_emergence(self, behavior: str) -> Optional[int]:
        """Find the step where a behavior first appeared."""
        keywords = self.BEHAVIOR_SIGNATURES.get(behavior, [behavior])
        for ckpt in self.checkpoints:
            for key in ckpt.keys:
                if any(kw in key.lower() for kw in keywords):
                    self.events.append(EmergenceEvent(
                        step=ckpt.step, behavior=behavior,
                        evidence=f"key '{key}' in {os.path.basename(ckpt.path)}", magnitude=1.0))
                    return ckpt.step
        return None

    def layer_analysis(self, ckpt1: CheckpointInfo, ckpt2: CheckpointInfo) -> Dict:
        """Analyze what changed between two checkpoints."""
        k1, k2 = set(ckpt1.keys), set(ckpt2.keys)
        result = {"step_from": ckpt1.step, "step_to": ckpt2.step,
                  "added_keys": sorted(k2 - k1), "removed_keys": sorted(k1 - k2),
                  "shared_keys": len(k1 & k2),
                  "size_delta_mb": round(ckpt2.size_mb - ckpt1.size_mb, 2),
                  "metric_changes": {}}
        for m in set(list(ckpt1.metrics) + list(ckpt2.metrics)):
            v1, v2 = ckpt1.metrics.get(m), ckpt2.metrics.get(m)
            if v1 is not None and v2 is not None:
                result["metric_changes"][m] = round(v2 - v1, 4)
        return result

    def timeline(self, width: int = 60) -> str:
        """ASCII timeline of key events."""
        lines = ["  === Consciousness Archaeology Timeline ===", ""]

        if not self.checkpoints and not self.events:
            lines.append("  (no data — load checkpoints first)")
            return "\n".join(lines)

        all_steps = [c.step for c in self.checkpoints] + [e.step for e in self.events]
        if not all_steps:
            return "\n".join(lines + ["  (empty)"])

        min_s, max_s = min(all_steps), max(all_steps)
        span = max(max_s - min_s, 1)

        # Timeline bar
        bar = ["-"] * width
        for ckpt in self.checkpoints:
            pos = int((ckpt.step - min_s) / span * (width - 1))
            bar[pos] = "|"
        for event in self.events:
            pos = int((event.step - min_s) / span * (width - 1))
            bar[pos] = "*"

        lines.append(f"  step {min_s:<6d}{' ' * (width - 16)}step {max_s}")
        lines.append(f"  {''.join(bar)}")
        lines.append(f"  | = checkpoint, * = emergence event")
        lines.append("")

        # List checkpoints
        lines.append(f"  Checkpoints ({len(self.checkpoints)}):")
        for c in self.checkpoints:
            lines.append(f"    step {c.step:6d}: {os.path.basename(c.path)} "
                         f"({c.size_mb:.1f}MB, {len(c.keys)} keys)")

        # List events
        if self.events:
            lines.append(f"\n  Emergence Events ({len(self.events)}):")
            for e in self.events:
                lines.append(f"    step {e.step:6d}: [{e.behavior}] {e.evidence}")

        return "\n".join(lines)

    def _demo_checkpoints(self) -> List[CheckpointInfo]:
        """Generate synthetic checkpoints for demo."""
        base = ["cell.weight", "cell.bias"]
        layers = {0: [], 1000: ["emotion.valence", "emotion.arousal"],
                  5000: ["memory.embedding", "memory.retrieval"],
                  10000: ["faction.bias_0", "meta.self_model", "output.decoder"],
                  20000: ["phi.integrator", "creative.diverge", "empathy.mirror"]}
        accum, ckpts = list(base), []
        for step, new_keys in sorted(layers.items()):
            accum = accum + new_keys
            ckpts.append(CheckpointInfo(
                path=f"checkpoint_{step:06d}.pt", step=step,
                size_mb=round(len(accum) * 2.5 + step * 0.001, 2), keys=list(accum),
                metrics={"phi": round(1.0 + step * 0.0001 * LN2, 3),
                          "ce": round(4.0 * math.exp(-step * 0.0001), 3)}))
        return ckpts


def main():
    print("=== ConsciousnessArchaeology Demo ===\n")
    ca = ConsciousnessArchaeology()
    ca.checkpoints = ca._demo_checkpoints()
    for b in ["emotion", "memory", "self_awareness", "speech", "phi_integration", "creativity", "empathy"]:
        step = ca.find_emergence(b)
        print(f"  {b:20s} emerged at step {step}" if step else f"  {b:20s} not found")
    if len(ca.checkpoints) >= 2:
        a = ca.layer_analysis(ca.checkpoints[0], ca.checkpoints[-1])
        print(f"\n  Layer analysis (step {a['step_from']} -> {a['step_to']}):")
        print(f"    Added: {a['added_keys']}")
        print(f"    Shared: {a['shared_keys']}, Size delta: {a['size_delta_mb']:+.1f} MB")
        for m, d in a["metric_changes"].items():
            print(f"    {m}: {d:+.4f}")
    print()
    print(ca.timeline())


if __name__ == "__main__":
    main()
