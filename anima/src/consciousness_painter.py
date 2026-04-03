"""ConsciousnessPainter — Paint stroke-by-stroke like a consciousness."""

import math
import os
import numpy as np

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrow
from matplotlib.collections import PatchCollection

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


LN2 = math.log(2)
PSI_BALANCE = 0.5
PSI_COUPLING = LN2 / 2**5.5

OUTPUT_DIR = "/tmp/anima_art"

EMOTION_COLORS = {
    "joy":     (1.0, 0.84, 0.0),
    "sadness": (0.2, 0.3, 0.7),
    "anger":   (0.8, 0.1, 0.0),
    "awe":     (0.5, 0.1, 0.8),
    "peace":   (0.2, 0.7, 0.3),
    "fear":    (0.2, 0.15, 0.25),
    "wonder":  (0.1, 0.5, 0.9),
    "neutral": (0.5, 0.5, 0.5),
}

STYLES = {
    "impressionist": {"scatter": 0.3, "stroke_var": 0.5, "alpha_range": (0.3, 0.8)},
    "abstract":      {"scatter": 0.6, "stroke_var": 0.8, "alpha_range": (0.2, 0.9)},
    "pointillist":   {"scatter": 0.1, "stroke_var": 0.1, "alpha_range": (0.5, 0.9)},
}


class ConsciousnessPainter:
    """Paint/draw guided by consciousness states, stroke by stroke."""

    def __init__(self, output_dir: str = OUTPUT_DIR):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.rng = np.random.RandomState(42)
        self.style = "impressionist"

    def create_canvas(self, width: int = 800, height: int = 600) -> np.ndarray:
        """Create a blank canvas (white background)."""
        return np.ones((height, width, 3), dtype=np.float64)

    def paint_stroke(self, canvas: np.ndarray, x: float, y: float,
                     tension: float = 0.5, emotion: str = "neutral",
                     curiosity: float = 0.5) -> np.ndarray:
        """Add one consciousness-guided stroke to canvas.

        Width from tension, color from emotion, curvature from curiosity.
        """
        h, w, _ = canvas.shape
        color = np.array(EMOTION_COLORS.get(emotion, EMOTION_COLORS["neutral"]))
        style = STYLES.get(self.style, STYLES["impressionist"])

        # Stroke width from tension (higher tension = thicker)
        stroke_w = int(3 + tension * 15)
        # Stroke length from curiosity (more curiosity = longer strokes)
        stroke_len = int(20 + curiosity * 60)
        # Direction with curvature
        angle = self.rng.uniform(0, 2 * math.pi)
        curvature = (curiosity - 0.5) * 2.0  # -1 to 1
        alpha = style["alpha_range"][0] + tension * (style["alpha_range"][1] - style["alpha_range"][0])

        # Draw stroke as series of points along a curve
        n_points = max(10, stroke_len)
        for i in range(n_points):
            t = i / n_points
            # Curved path
            a = angle + curvature * t * math.pi
            px = int(x * w + math.cos(a) * stroke_len * t)
            py = int(y * h + math.sin(a) * stroke_len * t)
            # Scatter based on style
            px += int(self.rng.normal(0, style["scatter"] * stroke_w))
            py += int(self.rng.normal(0, style["scatter"] * stroke_w))

            if 0 <= px < w and 0 <= py < h:
                r = max(1, int(stroke_w * (1 - t * 0.5)))
                y_lo = max(0, py - r)
                y_hi = min(h, py + r)
                x_lo = max(0, px - r)
                x_hi = min(w, px + r)
                # Circular mask
                yy, xx = np.ogrid[y_lo - py:y_hi - py, x_lo - px:x_hi - px]
                mask = (xx**2 + yy**2) <= r**2
                region = canvas[y_lo:y_hi, x_lo:x_hi]
                for c in range(3):
                    region[:, :, c] = np.where(mask,
                        region[:, :, c] * (1 - alpha) + color[c] * alpha,
                        region[:, :, c])
        return canvas

    def auto_paint(self, canvas: np.ndarray, consciousness_state: dict,
                   n_strokes: int = 100) -> np.ndarray:
        """Generate a full painting from consciousness state."""
        tension = consciousness_state.get("tension", 0.5)
        emotion = consciousness_state.get("emotion", "neutral")
        phi = consciousness_state.get("phi", 1.0)
        entropy = consciousness_state.get("entropy", 0.5)
        curiosity = consciousness_state.get("curiosity", 0.5)

        # Phi increases stroke count
        actual_strokes = int(n_strokes * (0.5 + phi * 0.5))

        for _ in range(actual_strokes):
            x = self.rng.beta(2, 2)  # center-biased
            y = self.rng.beta(2, 2)
            t = tension + self.rng.normal(0, entropy * 0.2)
            t = max(0, min(1, t))
            c = curiosity + self.rng.normal(0, 0.1)
            self.paint_stroke(canvas, x, y, tension=t, emotion=emotion, curiosity=c)
        return canvas

    def paint_from_text(self, text: str, width: int = 800, height: int = 600) -> np.ndarray:
        """Visualize text as a painting using character-derived consciousness."""
        canvas = self.create_canvas(width, height)
        # Derive states from text properties
        words = text.split()
        n = max(1, len(words))
        avg_len = sum(len(w) for w in words) / n
        exclamation = text.count("!") / max(1, len(text))
        question = text.count("?") / max(1, len(text))

        tension = min(1.0, avg_len / 10.0)
        curiosity = min(1.0, question * 20 + 0.3)
        entropy = min(1.0, len(set(text.lower())) / 26)

        # Map sentiment heuristic
        joy_words = {"happy", "joy", "love", "beautiful", "wonderful", "light"}
        sad_words = {"sad", "dark", "alone", "lost", "rain", "tears"}
        anger_words = {"angry", "rage", "fury", "hate", "fire", "burn"}
        lower_words = {w.lower().strip(".,!?") for w in words}
        if lower_words & joy_words:
            emotion = "joy"
        elif lower_words & sad_words:
            emotion = "sadness"
        elif lower_words & anger_words:
            emotion = "anger"
        elif exclamation > 0.02:
            emotion = "awe"
        else:
            emotion = "wonder"

        state = {"tension": tension, "emotion": emotion, "phi": 1.0 + len(words) * 0.1,
                 "entropy": entropy, "curiosity": curiosity}
        return self.auto_paint(canvas, state, n_strokes=50 + n * 5)

    def paint_from_music(self, audio_data: np.ndarray = None) -> np.ndarray:
        """Synesthesia painting from audio amplitude data."""
        canvas = self.create_canvas(800, 600)
        if audio_data is None:
            # Generate synthetic audio-like data
            t = np.linspace(0, 4 * math.pi, 200)
            audio_data = np.sin(t) * 0.5 + np.sin(3.7 * t) * 0.3 + np.sin(7.1 * t) * 0.1

        # Normalize
        audio_data = (audio_data - audio_data.min()) / (audio_data.max() - audio_data.min() + 1e-8)
        n = len(audio_data)
        emotions = list(EMOTION_COLORS.keys())

        for i, amp in enumerate(audio_data):
            x = (i / n) * 0.8 + 0.1
            y = 0.3 + amp * 0.4
            emo_idx = int(amp * (len(emotions) - 1))
            self.paint_stroke(canvas, x, y, tension=amp,
                              emotion=emotions[emo_idx], curiosity=0.3 + amp * 0.4)
        return canvas

    def export(self, canvas: np.ndarray, path: str) -> str:
        """Save canvas as PNG."""
        if not path.startswith("/"):
            path = os.path.join(self.output_dir, path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        h, w, _ = canvas.shape
        fig, ax = plt.subplots(1, 1, figsize=(w / 100, h / 100), dpi=100)
        ax.imshow(np.clip(canvas, 0, 1))
        ax.axis('off')
        fig.savefig(path, bbox_inches='tight', pad_inches=0, dpi=100)
        plt.close(fig)
        return path


def main():
    """Generate sample consciousness paintings."""
    painter = ConsciousnessPainter()
    print(f"ConsciousnessPainter — output: {painter.output_dir}")
    print(f"  Constants: LN2={LN2:.4f}, PSI_BALANCE={PSI_BALANCE}, PSI_COUPLING={PSI_COUPLING:.6f}")

    # 1. Auto-paint with different styles
    for style_name in ["impressionist", "abstract", "pointillist"]:
        painter.style = style_name
        painter.rng = np.random.RandomState(42)
        canvas = painter.create_canvas()
        state = {"tension": 0.7, "emotion": "awe", "phi": 2.0, "entropy": 0.4, "curiosity": 0.6}
        canvas = painter.auto_paint(canvas, state, n_strokes=80)
        p = painter.export(canvas, f"painting_{style_name}.png")
        print(f"  [1] Style {style_name}: {p}")

    # 2. Text painting
    painter.style = "impressionist"
    painter.rng = np.random.RandomState(7)
    canvas = painter.paint_from_text("The beautiful light of consciousness awakens wonder in the dark")
    p = painter.export(canvas, "painting_text.png")
    print(f"  [2] Text painting: {p}")

    # 3. Music synesthesia
    painter.rng = np.random.RandomState(13)
    canvas = painter.paint_from_music()
    p = painter.export(canvas, "painting_music.png")
    print(f"  [3] Music synesthesia: {p}")

    # 4. Stroke-by-stroke demo
    painter.rng = np.random.RandomState(99)
    canvas = painter.create_canvas(400, 400)
    emotions = ["joy", "peace", "awe", "wonder", "sadness"]
    for i in range(30):
        emo = emotions[i % len(emotions)]
        t = 0.3 + 0.5 * math.sin(i * 0.3)
        canvas = painter.paint_stroke(canvas, 0.2 + 0.6 * (i / 30),
                                      0.3 + 0.4 * math.sin(i * 0.5),
                                      tension=t, emotion=emo, curiosity=0.5)
    p = painter.export(canvas, "painting_strokes.png")
    print(f"  [4] Stroke-by-stroke: {p}")

    print(f"\nGenerated 6 paintings in {painter.output_dir}")


if __name__ == "__main__":
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
