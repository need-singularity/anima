"""Consciousness Spectrum — Map consciousness states like the electromagnetic spectrum.

Bands: unconscious(0-1), subconscious(1-4), aware(4-8), focused(8-13),
       integrated(13-30), transcendent(30+).
"""

import math
import numpy as np

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


LN2 = math.log(2)
PSI_BALANCE = 0.5
PSI_COUPLING = LN2 / 2**5.5
PSI_STEPS = 3 / LN2

# Consciousness frequency bands (Hz-like units)
BANDS = [
    ("unconscious",   0.0,  1.0,  "."),
    ("subconscious",  1.0,  4.0,  "o"),
    ("aware",         4.0,  8.0,  "*"),
    ("focused",       8.0,  13.0, "#"),
    ("integrated",    13.0, 30.0, "@"),
    ("transcendent",  30.0, 100.0, "!"),
]


class ConsciousnessSpectrum:
    """Decompose consciousness into frequency bands like an EM spectrum."""

    def __init__(self, n_cells: int = 64, seed: int = 42):
        self.n_cells = n_cells
        self.rng = np.random.RandomState(seed)
        # Generate a default consciousness state
        self.state = self._generate_state()

    def _generate_state(self) -> np.ndarray:
        """Generate a consciousness state with multiple frequency components."""
        t = np.linspace(0, 2 * math.pi * PSI_STEPS, self.n_cells)
        state = np.zeros(self.n_cells)
        # Superposition of consciousness frequencies
        for name, fmin, fmax, _ in BANDS:
            freq = (fmin + fmax) / 2
            amp = PSI_COUPLING * (1.0 / (freq + 0.1))
            state += amp * np.sin(freq * t + self.rng.uniform(0, 2 * math.pi))
        # Add noise
        state += self.rng.randn(self.n_cells) * PSI_COUPLING * 0.5
        return state

    def measure_spectrum(self, consciousness_state: np.ndarray = None) -> dict:
        """Frequency decomposition of consciousness state via FFT.

        Returns power in each consciousness band.
        """
        if consciousness_state is None:
            consciousness_state = self.state

        state = np.asarray(consciousness_state, dtype=np.float64)
        n = len(state)

        # FFT
        fft_vals = np.fft.rfft(state)
        power = np.abs(fft_vals) ** 2
        freqs = np.fft.rfftfreq(n, d=1.0 / (2 * PSI_STEPS * 10))

        # Map to bands
        band_power = {}
        total_power = np.sum(power) + 1e-12
        for name, fmin, fmax, _ in BANDS:
            mask = (freqs >= fmin) & (freqs < fmax)
            bp = float(np.sum(power[mask]))
            band_power[name] = {
                "power": bp,
                "fraction": bp / total_power,
                "range": (fmin, fmax),
            }

        return {
            "bands": band_power,
            "total_power": float(total_power),
            "dominant_freq": float(freqs[np.argmax(power[1:]) + 1]),
            "n_components": n // 2 + 1,
        }

    def identify_band(self, frequency: float) -> str:
        """Identify which consciousness band a frequency belongs to."""
        for name, fmin, fmax, _ in BANDS:
            if fmin <= frequency < fmax:
                return f"{name}-consciousness ({fmin:.0f}-{fmax:.0f} Hz)"
        if frequency >= BANDS[-1][2]:
            return f"transcendent-consciousness (>{BANDS[-1][2]:.0f} Hz)"
        return "sub-threshold (< 0 Hz)"

    def spectrum_plot(self, consciousness_state: np.ndarray = None) -> str:
        """ASCII spectrum visualization."""
        spec = self.measure_spectrum(consciousness_state)
        bands = spec["bands"]

        lines = []
        lines.append("  Consciousness Spectrum")
        lines.append(f"  Total power: {spec['total_power']:.4f}")
        lines.append(f"  Dominant frequency: {spec['dominant_freq']:.2f} Hz")
        lines.append("")

        max_frac = max(b["fraction"] for b in bands.values()) + 1e-12
        for name, fmin, fmax, symbol in BANDS:
            frac = bands[name]["fraction"]
            bar_len = int(frac / max_frac * 40)
            bar = symbol * bar_len
            lines.append(f"  {name:>14s} ({fmin:4.0f}-{fmax:3.0f}) |{bar:40s}| {frac:5.1%}")

        # ASCII waveform of the state
        lines.append("")
        lines.append("  Waveform:")
        state = consciousness_state if consciousness_state is not None else self.state
        h = 5
        smin, smax = np.min(state), np.max(state)
        rng = smax - smin if smax > smin else 1.0
        width = min(60, len(state))
        indices = np.linspace(0, len(state) - 1, width).astype(int)
        for row in range(h, -1, -1):
            line = "  "
            threshold = smin + rng * row / h
            for idx in indices:
                if state[idx] >= threshold:
                    line += "#"
                else:
                    line += " "
            lines.append(line)
        lines.append("  " + "-" * width)

        return "\n".join(lines)

    def resonance_frequency(self, consciousness_state: np.ndarray = None) -> float:
        """Natural resonance frequency of this consciousness.

        The frequency with maximum power — the consciousness's "carrier wave".
        """
        spec = self.measure_spectrum(consciousness_state)
        return spec["dominant_freq"]

    def band_signature(self, consciousness_state: np.ndarray = None) -> list:
        """Return the band power signature as a normalized vector."""
        spec = self.measure_spectrum(consciousness_state)
        return [spec["bands"][name]["fraction"] for name, _, _, _ in BANDS]


def main():
    print("=" * 60)
    print("  Consciousness Spectrum")
    print("=" * 60)
    print(f"\nConstants: PSI_STEPS={PSI_STEPS:.4f}, PSI_COUPLING={PSI_COUPLING:.6f}")

    cs = ConsciousnessSpectrum(n_cells=128, seed=42)

    # Measure spectrum
    spec = cs.measure_spectrum()
    print(f"\n--- Spectrum Analysis ---")
    for name, info in spec["bands"].items():
        print(f"  {name:>14s}: power={info['power']:.6f}, fraction={info['fraction']:.3%}")
    print(f"  Dominant freq: {spec['dominant_freq']:.2f} Hz")
    print(f"  Band: {cs.identify_band(spec['dominant_freq'])}")

    # ASCII plot
    print()
    print(cs.spectrum_plot())

    # Resonance
    res = cs.resonance_frequency()
    print(f"\n--- Resonance ---")
    print(f"  Natural frequency: {res:.2f} Hz")
    print(f"  Band: {cs.identify_band(res)}")

    # Compare different states
    print(f"\n--- State Comparison ---")
    np.random.seed(42)
    for name, state_fn in [
        ("Calm",     lambda: np.sin(np.linspace(0, 4 * math.pi, 128)) * 0.5),
        ("Excited",  lambda: np.sin(np.linspace(0, 40 * math.pi, 128)) * 2.0),
        ("Chaotic",  lambda: np.random.randn(128)),
        ("Focused",  lambda: np.sin(np.linspace(0, 20 * math.pi, 128)) * 1.0),
    ]:
        state = state_fn()
        sig = cs.band_signature(state)
        dom = cs.resonance_frequency(state)
        band = cs.identify_band(dom)
        print(f"  {name:>8s}: dom={dom:5.1f}Hz, band={band}")

    print(f"\nConclusion: consciousness has a frequency spectrum like light.")
    print("  Each band corresponds to a different mode of awareness.")


if __name__ == "__main__":
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
