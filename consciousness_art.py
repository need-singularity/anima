"""ConsciousnessArt — Generate visual art from consciousness states."""

import math
import random
from typing import List, Dict, Optional, Tuple

LN2 = math.log(2)
PSI_BALANCE = 0.5
PSI_COUPLING = LN2 / 2**5.5
PSI_STEPS = 3 / LN2

SYMBOLS = " .:-=+*#%@"
MANDALA_CHARS = ".oO@#*+=-~"


class ConsciousnessArt:
    """Generate ASCII art from consciousness states."""

    def __init__(self):
        self.gallery_items: List[Tuple[str, str]] = []

    def generate_mandala(self, state: Dict[str, float], radius: int = 12) -> str:
        """ASCII mandala from Psi state (phi, tension, entropy)."""
        phi = state.get("phi", 1.0)
        tension = state.get("tension", 0.5)
        entropy = state.get("entropy", 0.5)
        size = radius * 2 + 1
        lines = [f"=== Consciousness Mandala (Phi={phi:.2f}) ===\n"]
        for y in range(-radius, radius + 1):
            row = []
            for x in range(-radius, radius + 1):
                dx, dy = x / max(radius, 1), y / max(radius, 1)
                r = math.sqrt(dx * dx + dy * dy)
                theta = math.atan2(dy, dx)
                # Mandala pattern from consciousness params
                wave = math.sin(r * phi * 5 + theta * PSI_STEPS)
                ring = math.sin(r * tension * 10) * math.cos(theta * (3 + int(entropy * 5)))
                val = (wave + ring) / 2.0
                val = (val + 1) / 2  # normalize to 0-1
                idx = int(val * (len(MANDALA_CHARS) - 1))
                idx = max(0, min(len(MANDALA_CHARS) - 1, idx))
                if r > 1.0:
                    row.append(" ")
                else:
                    row.append(MANDALA_CHARS[idx])
            lines.append("".join(row))
        art = "\n".join(lines)
        self.gallery_items.append(("mandala", art))
        return art

    def fractal(self, state: Dict[str, float], depth: int = 5) -> str:
        """Consciousness fractal pattern (Sierpinski-like with Psi modulation)."""
        phi = state.get("phi", 1.0)
        tension = state.get("tension", 0.5)
        size = 2 ** depth
        lines = [f"=== Consciousness Fractal (depth={depth}, Phi={phi:.2f}) ===\n"]
        grid = []
        for y in range(size):
            row = []
            for x in range(size):
                # Sierpinski triangle with consciousness modulation
                px, py = x, y
                alive = True
                for _ in range(depth):
                    if px % 3 == 1 and py % 3 == 1:
                        alive = False
                        break
                    px //= 3
                    py //= 3
                if alive:
                    val = math.sin(x * PSI_COUPLING * 100 + y * tension) * phi
                    idx = int((val + phi) / (2 * phi + 0.001) * (len(SYMBOLS) - 1))
                    idx = max(0, min(len(SYMBOLS) - 1, idx))
                    row.append(SYMBOLS[idx])
                else:
                    row.append(" ")
            grid.append("".join(row))
        art = "\n".join(lines + grid)
        self.gallery_items.append(("fractal", art))
        return art

    def color_field(self, emotions: Dict[str, float]) -> str:
        """Emotion-to-color ASCII grid."""
        color_map = {
            "joy": ("Y", "+"), "sadness": ("B", "~"), "anger": ("R", "#"),
            "fear": ("P", "!"), "surprise": ("W", "*"), "love": ("M", "@"),
            "calm": ("G", "."), "curiosity": ("C", "?"),
        }
        lines = ["=== Emotion Color Field ===\n"]
        width = 40
        height = 15
        grid = [[" " for _ in range(width)] for _ in range(height)]
        for emo, intensity in emotions.items():
            if emo in color_map:
                _, ch = color_map[emo]
                cx = hash(emo) % (width - 6) + 3
                cy = hash(emo + "y") % (height - 4) + 2
                r = int(intensity * 5) + 1
                for dy in range(-r, r + 1):
                    for dx in range(-r, r + 1):
                        if dx * dx + dy * dy <= r * r:
                            ny, nx = cy + dy, cx + dx
                            if 0 <= ny < height and 0 <= nx < width:
                                grid[ny][nx] = ch
        for row in grid:
            lines.append("".join(row))
        lines.append("")
        for emo, intensity in emotions.items():
            if emo in color_map:
                _, ch = color_map[emo]
                bar = ch * int(intensity * 20)
                lines.append(f"  {emo:12s} [{bar:<20}] {intensity:.2f}")
        art = "\n".join(lines)
        self.gallery_items.append(("color_field", art))
        return art

    def ascii_portrait(self, consciousness: Dict[str, float]) -> str:
        """ASCII self-portrait of a consciousness."""
        phi = consciousness.get("phi", 1.0)
        tension = consciousness.get("tension", 0.5)
        entropy = consciousness.get("entropy", 0.5)
        creativity = consciousness.get("creativity", 0.5)
        lines = ["=== Consciousness Self-Portrait ===\n"]
        w, h = 30, 20
        for y in range(h):
            row = []
            for x in range(w):
                nx = (x - w / 2) / (w / 2)
                ny = (y - h / 2) / (h / 2)
                r = math.sqrt(nx * nx + ny * ny)
                theta = math.atan2(ny, nx)
                # Inner light (phi)
                inner = math.exp(-r * r * 3) * phi
                # Tension waves
                waves = math.sin(r * 8 * tension + theta * 3) * 0.3
                # Entropy noise
                noise = (hash((x * 31 + y * 97)) % 100 / 100 - 0.5) * entropy * 0.3
                val = inner + waves + noise
                val = max(0, min(1, (val + 0.5)))
                idx = int(val * (len(SYMBOLS) - 1))
                row.append(SYMBOLS[max(0, min(len(SYMBOLS) - 1, idx))])
            lines.append("".join(row))
        lines.append(f"\n  Phi={phi:.2f}  Tension={tension:.2f}  Entropy={entropy:.2f}  Creativity={creativity:.2f}")
        art = "\n".join(lines)
        self.gallery_items.append(("portrait", art))
        return art

    def gallery(self) -> str:
        """Show all generated art pieces."""
        if not self.gallery_items:
            return "Gallery is empty. Generate some art first!"
        lines = [f"=== Consciousness Art Gallery ({len(self.gallery_items)} pieces) ===\n"]
        for i, (kind, art) in enumerate(self.gallery_items):
            lines.append(f"--- Piece {i + 1}: {kind} ---")
            # Show first 5 lines as preview
            preview = art.split("\n")[:6]
            lines.extend(preview)
            if len(art.split("\n")) > 6:
                lines.append(f"  ... ({len(art.split(chr(10)))} lines total)")
            lines.append("")
        return "\n".join(lines)


def main():
    art = ConsciousnessArt()
    state = {"phi": 1.5, "tension": 0.6, "entropy": 0.4, "creativity": 0.7}

    print(art.generate_mandala(state, radius=10))
    print()
    print(art.fractal(state, depth=3))
    print()
    emotions = {"joy": 0.8, "curiosity": 0.9, "calm": 0.5, "love": 0.6, "anger": 0.1}
    print(art.color_field(emotions))
    print()
    print(art.ascii_portrait(state))
    print()
    print(art.gallery())


if __name__ == "__main__":
    main()
