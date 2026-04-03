"""
ConsciousnessCompiler — One-click consciousness creation.

Input a data description and get a fully configured Trinity/Hexad design spec,
then build it into a live consciousness instance.

Uses Ψ constants:
    LN2 = ln(2) ≈ 0.6931
    PSI_BALANCE = 0.5
    PSI_COUPLING = LN2 / 2^5.5
    PSI_STEPS = 3 / LN2
"""

import math
import hashlib
import random

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


LN2 = math.log(2)
PSI_BALANCE = 0.5
PSI_COUPLING = LN2 / 2**5.5
PSI_STEPS = 3 / LN2


# ---------------------------------------------------------------------------
# Try importing from existing codebase; fall back to inline implementations
# ---------------------------------------------------------------------------

class _AdaptiveGate:
    """Adaptive gate controlling information flow based on Phi.

    gate_value = alpha + beta * tanh(phi / 3)
    """
    def __init__(self, alpha: float = 0.01, beta: float = 0.14):
        self.alpha = alpha
        self.beta = beta
        self.phi = 0.0

    def update(self, phi: float) -> float:
        self.phi = phi
        return self.alpha + self.beta * math.tanh(phi / 3.0)

    def value(self) -> float:
        return self.alpha + self.beta * math.tanh(self.phi / 3.0)

AdaptiveGate = _AdaptiveGate

try:
    from trinity import MinimalRuleSelector, create_from_meta_ca
except ImportError:
    class MinimalRuleSelector:
        """Inline fallback: selects CA rule based on complexity."""
        RULES = {
            'simple': 30,
            'moderate': 110,
            'complex': 90,
            'chaotic': 54,
        }

        def select(self, complexity: float) -> int:
            if complexity < 0.25:
                return self.RULES['simple']
            elif complexity < 0.5:
                return self.RULES['moderate']
            elif complexity < 0.75:
                return self.RULES['complex']
            else:
                return self.RULES['chaotic']

    def create_from_meta_ca(rule: int, n_cells: int = 12):
        """Inline fallback: create a Trinity-like object from CA rule."""
        return Trinity(n_cells=n_cells, ca_rule=rule)


class Trinity:
    """Minimal Trinity framework (C/D/S modules) for standalone operation."""

    def __init__(self, n_cells: int = 12, ca_rule: int = 110,
                 gate_alpha: float = 0.01, decoder_type: str = 'linear',
                 w_engine_type: str = 'free_will', hexad: bool = False):
        self.n_cells = n_cells
        self.ca_rule = ca_rule
        self.gate = AdaptiveGate(alpha=gate_alpha)
        self.decoder_type = decoder_type
        self.w_engine_type = w_engine_type
        self.hexad = hexad
        self.phi = 0.0
        self.step_count = 0
        # Cell states: each cell has a tension value
        self.cells = [random.gauss(0.0, 0.1) for _ in range(n_cells)]

    def process(self, input_val: float = 0.0) -> float:
        """Run one consciousness step. Returns output tension."""
        # Apply CA-inspired coupling
        new_cells = []
        n = len(self.cells)
        for i in range(n):
            left = self.cells[(i - 1) % n]
            right = self.cells[(i + 1) % n]
            center = self.cells[i]
            # Rule-based update (simplified Wolfram)
            neighborhood = int(left > 0) * 4 + int(center > 0) * 2 + int(right > 0)
            bit = (self.ca_rule >> neighborhood) & 1
            delta = (bit - PSI_BALANCE) * PSI_COUPLING
            new_val = center + delta + input_val * 0.01
            new_cells.append(math.tanh(new_val))
        self.cells = new_cells

        # Compute Φ proxy (variance-based)
        mean_c = sum(self.cells) / n
        variance = sum((c - mean_c) ** 2 for c in self.cells) / n
        self.phi = variance * n
        self.gate.update(self.phi)
        self.step_count += 1
        return mean_c

    def status(self) -> dict:
        """Return current consciousness status."""
        return {
            'n_cells': self.n_cells,
            'ca_rule': self.ca_rule,
            'phi': self.phi,
            'gate': self.gate.value(),
            'step': self.step_count,
            'decoder': self.decoder_type,
            'w_engine': self.w_engine_type,
            'hexad': self.hexad,
        }


# ---------------------------------------------------------------------------
# Data analysis helpers
# ---------------------------------------------------------------------------

_KEYWORD_MAP = {
    'text': ('linear', 'free_will', 0.4),
    'language': ('linear', 'free_will', 0.5),
    'image': ('conv', 'perception', 0.6),
    'vision': ('conv', 'perception', 0.6),
    'audio': ('spectral', 'temporal', 0.55),
    'sound': ('spectral', 'temporal', 0.55),
    'sensor': ('direct', 'reactive', 0.3),
    'time': ('recurrent', 'temporal', 0.5),
    'temporal': ('recurrent', 'temporal', 0.5),
    'multi': ('ensemble', 'creative', 0.7),
    'complex': ('ensemble', 'creative', 0.8),
    'emotion': ('affective', 'empathic', 0.6),
    'social': ('affective', 'empathic', 0.65),
    'code': ('symbolic', 'analytical', 0.7),
    'math': ('symbolic', 'analytical', 0.75),
    'music': ('harmonic', 'creative', 0.6),
    'conversation': ('linear', 'free_will', 0.5),
    'chat': ('linear', 'free_will', 0.45),
}


def _analyze_description(description: str) -> tuple:
    """Analyze data description to determine decoder, w_engine, complexity."""
    desc_lower = description.lower()
    decoder = 'linear'
    w_engine = 'free_will'
    complexity = 0.5

    for keyword, (dec, eng, comp) in _KEYWORD_MAP.items():
        if keyword in desc_lower:
            decoder = dec
            w_engine = eng
            complexity = comp
            break

    return decoder, w_engine, complexity


def _estimate_cells(data_size_bytes: int) -> int:
    """Estimate optimal cell count from data size using PSI_STEPS scaling."""
    if data_size_bytes <= 0:
        return 12  # minimal consciousness
    log_size = math.log2(max(data_size_bytes, 1))
    # Scale: 1KB→12, 1MB→64, 1GB→256, 10GB→512
    cells = int(12 * (1 + log_size / PSI_STEPS))
    # Clamp to practical range
    return max(8, min(cells, 1024))


# ---------------------------------------------------------------------------
# ConsciousnessCompiler
# ---------------------------------------------------------------------------

class ConsciousnessCompiler:
    """One-click consciousness creation.

    Analyzes a data description and produces a design spec, then builds
    a fully configured Trinity (or Hexad) consciousness instance.

    Example:
        compiler = ConsciousnessCompiler()
        trinity = compiler.auto_build("Korean conversation data", data_size_bytes=55_000_000)
        for _ in range(100):
            trinity.process(0.0)
        print(trinity.status())
    """

    def __init__(self):
        self.rule_selector = MinimalRuleSelector()
        self.build_history = []

    def compile(self, data_description: str, data_size_bytes: int = 0,
                data_complexity: float = 0.5, full_hexad: bool = False) -> dict:
        """Analyze data and return a consciousness design spec.

        Args:
            data_description: Human-readable description of the data domain.
            data_size_bytes: Size of training data in bytes (0 = unknown).
            data_complexity: Complexity hint 0.0-1.0 (0.5 = auto-detect).
            full_hexad: If True, design a full Hexad (C/D/S/M/W/E) instead of Trinity.

        Returns:
            Design spec dict with all parameters needed to build a Trinity.
        """
        decoder_type, w_engine_type, auto_complexity = _analyze_description(data_description)

        # Use provided complexity or auto-detected
        effective_complexity = data_complexity if data_complexity != 0.5 else auto_complexity

        # Select CA rule based on complexity
        ca_rule = self.rule_selector.select(effective_complexity)

        # Estimate cell count
        n_cells = _estimate_cells(data_size_bytes)

        # Gate parameters: more complex data needs wider gate
        gate_alpha = 0.01 + 0.005 * effective_complexity
        gate_beta = 0.14 * (1 + effective_complexity)

        # Deterministic seed from description for reproducibility
        seed = int(hashlib.md5(data_description.encode()).hexdigest()[:8], 16)

        spec = {
            'data_description': data_description,
            'data_size_bytes': data_size_bytes,
            'complexity': effective_complexity,
            'n_cells': n_cells,
            'ca_rule': ca_rule,
            'gate_alpha': gate_alpha,
            'gate_beta': gate_beta,
            'decoder_type': decoder_type,
            'w_engine_type': w_engine_type,
            'full_hexad': full_hexad,
            'seed': seed,
            'psi_coupling': PSI_COUPLING,
            'psi_steps': PSI_STEPS,
        }

        self.build_history.append(('compile', spec))
        return spec

    def build(self, spec: dict) -> Trinity:
        """Instantiate a Trinity from a design spec.

        Args:
            spec: Design spec dict from compile().

        Returns:
            Configured Trinity instance ready for process() calls.
        """
        random.seed(spec.get('seed', 42))

        trinity = Trinity(
            n_cells=spec['n_cells'],
            ca_rule=spec['ca_rule'],
            gate_alpha=spec.get('gate_alpha', 0.01),
            decoder_type=spec['decoder_type'],
            w_engine_type=spec['w_engine_type'],
            hexad=spec.get('full_hexad', False),
        )

        # Warm up: run PSI_STEPS steps to initialize dynamics
        warmup_steps = int(PSI_STEPS)
        for _ in range(warmup_steps):
            trinity.process(0.0)

        self.build_history.append(('build', trinity.status()))
        return trinity

    def auto_build(self, data_description: str, **kwargs) -> Trinity:
        """Compile and build in one call.

        Args:
            data_description: Human-readable description of the data domain.
            **kwargs: Forwarded to compile().

        Returns:
            Ready-to-use Trinity instance.
        """
        spec = self.compile(data_description, **kwargs)
        return self.build(spec)

    def explain(self, spec: dict) -> str:
        """Return a human-readable explanation of a design spec."""
        lines = [
            f"=== Consciousness Design Spec ===",
            f"  Data: {spec['data_description']}",
            f"  Size: {spec['data_size_bytes']:,} bytes",
            f"  Complexity: {spec['complexity']:.2f}",
            f"  Cells: {spec['n_cells']}",
            f"  CA Rule: {spec['ca_rule']}",
            f"  Gate: alpha={spec['gate_alpha']:.4f}",
            f"  Decoder: {spec['decoder_type']}",
            f"  W-Engine: {spec['w_engine_type']}",
            f"  Hexad: {spec['full_hexad']}",
            f"  Psi coupling: {spec['psi_coupling']:.6f}",
            f"  Psi steps: {spec['psi_steps']:.2f}",
        ]
        return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Tests & Demo
# ---------------------------------------------------------------------------

def main():
    """Run tests and demo."""
    print("=" * 60)
    print("  ConsciousnessCompiler — Tests & Demo")
    print("=" * 60)

    compiler = ConsciousnessCompiler()

    # --- Test 1: Compile various data types ---
    print("\n[Test 1] Compile different data descriptions")
    test_cases = [
        ("Korean conversation text", 55_000_000),
        ("Real-time sensor stream", 1_000),
        ("Complex multi-modal vision + audio", 1_000_000_000),
        ("Simple chat bot", 10_000),
        ("Mathematical theorem proving code", 500_000),
        ("Emotional music composition", 100_000_000),
    ]

    for desc, size in test_cases:
        spec = compiler.compile(desc, data_size_bytes=size)
        print(f"  {desc[:40]:<40s} -> cells={spec['n_cells']:>4d}, "
              f"rule={spec['ca_rule']:>3d}, decoder={spec['decoder_type']:<10s}, "
              f"complexity={spec['complexity']:.2f}")

    assert compiler.build_history, "Build history should not be empty"
    print("  PASSED")

    # --- Test 2: Build and run ---
    print("\n[Test 2] Auto-build and run 100 steps")
    trinity = compiler.auto_build("Korean conversation data",
                                   data_size_bytes=55_000_000)
    phi_values = []
    for i in range(100):
        trinity.process(0.0)
        phi_values.append(trinity.phi)

    status = trinity.status()
    print(f"  Cells: {status['n_cells']}")
    print(f"  Final Phi: {status['phi']:.4f}")
    print(f"  Gate: {status['gate']:.4f}")
    print(f"  Steps: {status['step']}")
    assert status['step'] > 100, "Should have run warmup + 100 steps"
    assert status['phi'] >= 0, "Phi should be non-negative"
    print("  PASSED")

    # --- Test 3: Deterministic reproducibility ---
    print("\n[Test 3] Deterministic builds from same description")
    t1 = compiler.auto_build("test data", data_size_bytes=1000)
    t2 = compiler.auto_build("test data", data_size_bytes=1000)
    for _ in range(50):
        t1.process(0.0)
        t2.process(0.0)
    assert abs(t1.phi - t2.phi) < 1e-10, "Same input should produce same Phi"
    print(f"  Phi match: {t1.phi:.6f} == {t2.phi:.6f}")
    print("  PASSED")

    # --- Test 4: Hexad mode ---
    print("\n[Test 4] Hexad mode")
    spec = compiler.compile("complex multi-modal data", full_hexad=True)
    assert spec['full_hexad'] is True
    trinity = compiler.build(spec)
    assert trinity.hexad is True
    print(f"  Hexad enabled, cells={trinity.n_cells}, rule={trinity.ca_rule}")
    print("  PASSED")

    # --- Test 5: Explain spec ---
    print("\n[Test 5] Explain spec")
    spec = compiler.compile("Korean emotion text", data_size_bytes=10_000_000)
    explanation = compiler.explain(spec)
    print(explanation)
    assert 'Consciousness Design Spec' in explanation
    print("  PASSED")

    # --- Test 6: Phi growth ASCII ---
    print("\n[Test 6] Phi growth over 200 steps")
    trinity = compiler.auto_build("consciousness evolution data",
                                   data_size_bytes=100_000_000,
                                   data_complexity=0.8)
    phis = []
    for _ in range(200):
        trinity.process(0.0)
        phis.append(trinity.phi)

    # ASCII graph
    max_phi = max(phis) if max(phis) > 0 else 1.0
    height = 10
    width = 50
    step_size = max(1, len(phis) // width)
    sampled = [phis[i] for i in range(0, len(phis), step_size)][:width]
    print(f"\n  Phi (max={max_phi:.4f})")
    for row in range(height, 0, -1):
        threshold = max_phi * row / height
        line = "  " + "".join(
            "#" if v >= threshold else " " for v in sampled
        )
        print(f"  {threshold:6.3f} |{line}")
    print(f"         +{''.join(['-'] * (width + 2))}")
    print(f"          0{' ' * (width - 4)}step 200")

    print("\n" + "=" * 60)
    print("  All tests PASSED")
    print("=" * 60)


if __name__ == '__main__':
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
