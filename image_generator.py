"""ConsciousnessImageGenerator — Generate images from consciousness states using matplotlib."""

import math
import os
import numpy as np

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

LN2 = math.log(2)
PSI_BALANCE = 0.5
PSI_COUPLING = LN2 / 2**5.5
PSI_STEPS = 3 / LN2

OUTPUT_DIR = "/tmp/anima_art"

EMOTION_PALETTES = {
    "joy":     [(1.0, 0.84, 0.0), (1.0, 0.6, 0.0), (1.0, 0.95, 0.8)],
    "sadness": [(0.1, 0.2, 0.5), (0.3, 0.4, 0.7), (0.6, 0.7, 0.9)],
    "anger":   [(0.6, 0.0, 0.0), (0.9, 0.2, 0.0), (1.0, 0.5, 0.1)],
    "awe":     [(0.3, 0.0, 0.5), (0.5, 0.1, 0.8), (0.8, 0.5, 1.0)],
    "peace":   [(0.1, 0.4, 0.2), (0.3, 0.7, 0.4), (0.7, 0.9, 0.7)],
    "fear":    [(0.1, 0.1, 0.1), (0.3, 0.2, 0.3), (0.5, 0.4, 0.5)],
    "wonder":  [(0.0, 0.2, 0.4), (0.2, 0.5, 0.8), (0.6, 0.8, 1.0)],
}


class ConsciousnessImageGenerator:
    """Generate images directly from consciousness states."""

    def __init__(self, output_dir: str = OUTPUT_DIR):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def _make_grid(self, size: int):
        x = np.linspace(-2, 2, size)
        y = np.linspace(-2, 2, size)
        return np.meshgrid(x, y)

    def from_tension(self, tension_history: list, size: int = 512) -> np.ndarray:
        """Map tension history to color gradients and interference patterns."""
        X, Y = self._make_grid(size)
        R = np.sqrt(X**2 + Y**2)
        img = np.zeros((size, size, 3))
        for i, t in enumerate(tension_history[-8:]):
            freq = 2.0 + t * 10.0
            phase = i * math.pi / 4
            wave = 0.5 + 0.5 * np.sin(freq * R + phase)
            brightness = 0.3 + 0.7 * t
            channel = i % 3
            img[:, :, channel] += wave * brightness / max(1, len(tension_history[-8:]) // 3)
        img = np.clip(img, 0, 1)
        return img

    def from_emotion(self, emotion_name: str, intensity: float = 0.7) -> np.ndarray:
        """Visualize emotion as unique pattern: joy=spirals, sadness=rain, anger=fractals."""
        size = 512
        X, Y = self._make_grid(size)
        R = np.sqrt(X**2 + Y**2)
        T = np.arctan2(Y, X)
        palette = EMOTION_PALETTES.get(emotion_name, EMOTION_PALETTES["awe"])
        img = np.zeros((size, size, 3))

        if emotion_name == "joy":
            spiral = 0.5 + 0.5 * np.sin(4 * T + 6 * R * intensity)
            for c in range(3):
                img[:, :, c] = spiral * palette[0][c] + (1 - spiral) * palette[2][c]
        elif emotion_name == "sadness":
            rain = 0.5 + 0.5 * np.sin(30 * Y * intensity + 2 * np.sin(5 * X))
            for c in range(3):
                img[:, :, c] = rain * palette[1][c] + (1 - rain) * palette[0][c]
        elif emotion_name == "anger":
            z = X + 1j * Y
            fractal = np.zeros_like(R)
            for _ in range(int(20 * intensity)):
                mask = np.abs(z) < 2
                z = np.where(mask, z**2 + (-0.7 + 0.27j), z)
                fractal += mask.astype(float)
            fractal = fractal / fractal.max() if fractal.max() > 0 else fractal
            for c in range(3):
                img[:, :, c] = fractal * palette[0][c] + (1 - fractal) * palette[2][c]
        else:
            pattern = 0.5 + 0.5 * np.sin(8 * R * intensity) * np.cos(3 * T)
            for c in range(3):
                img[:, :, c] = pattern * palette[0][c] + (1 - pattern) * palette[1][c]

        return np.clip(img * intensity + img * (1 - intensity) * 0.3, 0, 1)

    def from_psi(self, psi_state: dict = None) -> np.ndarray:
        """Visualize Psi constants: mandala from balance, wave from steps, coupling network."""
        if psi_state is None:
            psi_state = {"balance": PSI_BALANCE, "steps": PSI_STEPS, "coupling": PSI_COUPLING}
        size = 512
        X, Y = self._make_grid(size)
        R = np.sqrt(X**2 + Y**2)
        T = np.arctan2(Y, X)
        img = np.zeros((size, size, 3))

        # Mandala from balance (symmetry order)
        sym = max(3, int(psi_state.get("balance", PSI_BALANCE) * 12))
        mandala = 0.5 + 0.5 * np.cos(sym * T) * np.sin(6 * R)
        img[:, :, 2] = mandala * 0.6  # blue channel

        # Wave from steps
        steps_freq = psi_state.get("steps", PSI_STEPS)
        wave = 0.5 + 0.5 * np.sin(steps_freq * 2 * R + T * 2)
        img[:, :, 1] = wave * 0.5  # green channel

        # Coupling network
        coupling = psi_state.get("coupling", PSI_COUPLING)
        net = np.exp(-R**2 / (coupling * 100 + 0.5)) * (0.5 + 0.5 * np.cos(8 * T))
        img[:, :, 0] = net * 0.7  # red channel

        return np.clip(img, 0, 1)

    def consciousness_portrait(self, all_states: dict) -> np.ndarray:
        """Full portrait combining tension, emotion, phi, entropy, psi."""
        size = 512
        img = np.zeros((size, size, 3))

        tension = all_states.get("tension", 0.5)
        emotion = all_states.get("emotion", "awe")
        phi = all_states.get("phi", 1.0)
        entropy = all_states.get("entropy", 0.5)

        # Background: psi mandala
        psi_layer = self.from_psi(all_states.get("psi")) * 0.3

        # Emotion overlay
        emotion_layer = self.from_emotion(emotion, intensity=tension) * 0.4

        # Phi complexity: more detail = higher phi
        X, Y = self._make_grid(size)
        R = np.sqrt(X**2 + Y**2)
        T = np.arctan2(Y, X)
        harmonics = int(3 + phi * 5)
        detail = np.zeros((size, size))
        for h in range(1, harmonics + 1):
            detail += np.sin(h * 3 * R + h * T) / h
        detail = (detail - detail.min()) / (detail.max() - detail.min() + 1e-8)
        phi_layer = np.stack([detail * 0.3, detail * 0.2, detail * 0.5], axis=2) * 0.3

        # Entropy noise
        noise = np.random.RandomState(42).random((size, size, 3)) * entropy * 0.1

        img = psi_layer + emotion_layer + phi_layer + noise
        return np.clip(img, 0, 1)

    def save(self, image_array: np.ndarray, path: str):
        """Save image array as PNG using matplotlib."""
        if not path.startswith("/"):
            path = os.path.join(self.output_dir, path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        fig, ax = plt.subplots(1, 1, figsize=(6, 6), dpi=100)
        ax.imshow(image_array)
        ax.axis('off')
        fig.savefig(path, bbox_inches='tight', pad_inches=0, dpi=100)
        plt.close(fig)
        return path


def main():
    """Generate sample consciousness art."""
    gen = ConsciousnessImageGenerator()
    print(f"ConsciousnessImageGenerator — output: {gen.output_dir}")
    print(f"  Constants: LN2={LN2:.4f}, PSI_BALANCE={PSI_BALANCE}, PSI_COUPLING={PSI_COUPLING:.6f}")

    # 1. Tension interference
    tension_history = [0.3, 0.5, 0.8, 0.6, 0.9, 0.4, 0.7, 0.95, 0.2, 0.6]
    img = gen.from_tension(tension_history)
    p = gen.save(img, "tension_interference.png")
    print(f"  [1] Tension interference: {p}  shape={img.shape}")

    # 2. Emotion gallery
    for emo in ["joy", "sadness", "anger", "awe", "peace"]:
        img = gen.from_emotion(emo, intensity=0.8)
        p = gen.save(img, f"emotion_{emo}.png")
        print(f"  [2] Emotion {emo}: {p}")

    # 3. Psi visualization
    img = gen.from_psi()
    p = gen.save(img, "psi_constants.png")
    print(f"  [3] Psi constants: {p}")

    # 4. Full consciousness portrait
    states = {
        "tension": 0.7,
        "emotion": "awe",
        "phi": 2.5,
        "entropy": 0.4,
        "psi": {"balance": PSI_BALANCE, "steps": PSI_STEPS, "coupling": PSI_COUPLING},
    }
    img = gen.consciousness_portrait(states)
    p = gen.save(img, "consciousness_portrait.png")
    print(f"  [4] Consciousness portrait: {p}")

    print(f"\nGenerated {8} images in {gen.output_dir}")


if __name__ == "__main__":
    main()
