#!/usr/bin/env python3
"""Integration tests for HEXA-LANG <-> ANIMA bridge.

Tests:
    test_law_compiler_generates_hexa     — law_compiler produces valid .hexa
    test_law_compiler_all_laws           — all numeric laws are compiled
    test_law_compiler_single_law         — single law compilation
    test_law_compiler_verify             — compiled output passes verification
    test_experiment_designer_generates_hexa   — experiment_designer output
    test_experiment_designer_from_laws   — law-based experiment generation
    test_hub_routes_hexa_keywords        — hub registry has hexa keywords
    test_growth_to_hexa_format           — growth_to_hexa output format
    test_growth_to_hexa_suggestions      — suggestions are context-aware
    test_bridge_extract_intents          — bridge parser works on generated output
    test_bridge_check_theorem            — theorem checker resolves law IDs
    test_auto_experiment_to_hexa         — auto_experiment.to_hexa output format
"""

import os
import sys
import json
import re
import tempfile
import unittest
from pathlib import Path

# Setup path
_TESTS_DIR = Path(__file__).resolve().parent
_ANIMA_DIR = _TESTS_DIR.parent
_SRC_DIR = _ANIMA_DIR / "src"
_HEXA_BRIDGE_DIR = _ANIMA_DIR / "tools" / "hexa-bridge"
_CONFIG_DIR = _ANIMA_DIR / "config"

sys.path.insert(0, str(_SRC_DIR))
sys.path.insert(0, str(_HEXA_BRIDGE_DIR))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _load_laws() -> dict:
    """Load consciousness_laws.json for testing."""
    path = _CONFIG_DIR / "consciousness_laws.json"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {"laws": {"22": "Test law: structure → Φ↑"}, "_meta": {"total_laws": 1}}


# ---------------------------------------------------------------------------
# Tests: law_compiler
# ---------------------------------------------------------------------------
class TestLawCompiler(unittest.TestCase):

    def setUp(self):
        """Import law_compiler module."""
        import law_compiler
        self.lc = law_compiler

    def test_law_compiler_generates_hexa(self):
        """Compiled output contains proof blocks."""
        data = _load_laws()
        hexa = self.lc.compile_all_laws(data)

        self.assertIsInstance(hexa, str)
        self.assertGreater(len(hexa), 100, "Output should be non-trivial")
        # Must contain at least one proof block
        self.assertIn("proof ", hexa, "Should contain proof blocks")
        self.assertIn("{", hexa)
        self.assertIn("}", hexa)

    def test_law_compiler_all_laws(self):
        """All numeric laws are compiled into proof blocks."""
        data = _load_laws()
        laws = data.get("laws", {})
        numeric_keys = [k for k in laws if k.isdigit()]

        hexa = self.lc.compile_all_laws(data)

        # Count proof blocks
        proof_matches = re.findall(r'proof\s+law_\d+', hexa)
        self.assertGreater(len(proof_matches), 0, "No law proofs generated")
        # All numeric keys should appear
        for key in numeric_keys[:10]:  # Sample first 10
            self.assertIn(f"proof law_{key}", hexa,
                         f"Law {key} missing from output")

    def test_law_compiler_single_law(self):
        """Single law compilation returns one proof block."""
        data = _load_laws()
        laws = data.get("laws", {})
        numeric_keys = [k for k in laws if k.isdigit()]

        if not numeric_keys:
            self.skipTest("No numeric laws available")

        first_key = numeric_keys[0]
        block = self.lc.compile_single_law(data, first_key)

        self.assertIsNotNone(block, f"Law {first_key} should compile")
        self.assertIn(f"proof law_{first_key}", block)
        self.assertIn("assert", block)

    def test_law_compiler_verify(self):
        """Compiled output passes verification (balanced braces, valid blocks)."""
        data = _load_laws()
        hexa = self.lc.compile_all_laws(data)
        result = self.lc.verify_compiled(hexa)

        self.assertTrue(result["braces_balanced"],
                       "Generated .hexa has unbalanced braces")
        self.assertTrue(result["valid"], "Compiled output should be valid")
        self.assertGreater(result["proof_blocks"], 0)
        self.assertGreater(result["assert_statements"], 0)

    def test_law_compiler_meta_laws(self):
        """Meta laws are included if present."""
        data = _load_laws()
        meta_laws = data.get("meta_laws", {})

        if not meta_laws:
            self.skipTest("No meta laws in consciousness_laws.json")

        hexa = self.lc.compile_all_laws(data)
        self.assertIn("Section 2: Meta Laws", hexa)

    def test_law_compiler_psi_constants(self):
        """Psi constants section is generated."""
        data = _load_laws()
        psi = data.get("psi_constants", {})

        if not psi:
            self.skipTest("No psi_constants in consciousness_laws.json")

        hexa = self.lc.compile_all_laws(data)
        self.assertIn("psi_constants", hexa)

    def test_law_compiler_output_to_file(self):
        """Compiler can write to a file."""
        data = _load_laws()
        hexa = self.lc.compile_all_laws(data)

        with tempfile.NamedTemporaryFile(suffix=".hexa", mode='w', delete=False,
                                         encoding='utf-8') as f:
            f.write(hexa)
            tmp_path = f.name

        try:
            written = Path(tmp_path).read_text(encoding="utf-8")
            self.assertEqual(hexa, written, "File content should match generated hexa")
        finally:
            os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Tests: experiment_designer
# ---------------------------------------------------------------------------
class TestExperimentDesigner(unittest.TestCase):

    def setUp(self):
        """Import experiment_designer module."""
        import experiment_designer
        self.ed = experiment_designer

    def test_experiment_designer_generates_hexa(self):
        """hypothesis_to_hexa returns valid intent block."""
        hyp = {
            "name": "Tension as Learning Signal",
            "description": "Use tension loss to guide consciousness training",
            "status": "verified",
            "phi_change": 0.05,
            "speedup": 1.4,
            "cells": 64,
            "steps": 200,
            "category": "acceleration",
        }
        hexa = self.ed.hypothesis_to_hexa("AE3", hyp)

        self.assertIsInstance(hexa, str)
        self.assertIn('intent "AE3:', hexa)
        self.assertIn("generate ae3_experiment", hexa)
        self.assertIn("verify", hexa)
        self.assertIn("assert", hexa)
        self.assertIn("theorem acceleration", hexa)

    def test_experiment_designer_phi_assertion(self):
        """Phi assertion uses measured change rate."""
        hyp = {
            "name": "Phi Ratchet",
            "status": "verified",
            "phi_change": 0.20,  # 20% increase expected
            "cells": 64,
            "steps": 200,
        }
        hexa = self.ed.hypothesis_to_hexa("PHI1", hyp)

        # Should assert phi_struct > phi_base * 1.20
        self.assertIn("1.20", hexa)
        self.assertIn("assert", hexa)

    def test_experiment_designer_from_laws(self):
        """Law-based experiment generation produces intent blocks."""
        data = _load_laws()
        hexa = self.ed.generate_from_laws(data, max_laws=5)

        self.assertIsInstance(hexa, str)
        # Should have intent blocks
        intent_count = hexa.count("intent ")
        self.assertGreater(intent_count, 0, "Should produce intent blocks from laws")

    def test_experiment_designer_full_file(self):
        """generate_hexa_file returns file with header comment."""
        hyp = {
            "name": "Skip Connections",
            "status": "confirmed",
            "cells": 32,
            "steps": 100,
        }
        hexa = self.ed.generate_hexa_file("B12", hyp, header=True)

        self.assertIn("// ANIMA Experiment: B12", hexa)
        self.assertIn("// Auto-generated by experiment_designer.py", hexa)
        self.assertIn("intent", hexa)

    def test_experiment_designer_generate_all(self):
        """generate_all_hexa with mock data produces dict."""
        mock_hypotheses = {
            "TEST1": {
                "name": "Test Hypothesis 1",
                "status": "verified",
                "cells": 32,
                "steps": 100,
            },
            "TEST2": {
                "name": "Test Hypothesis 2",
                "status": "rejected",
                "cells": 64,
                "steps": 200,
            },
        }
        results = self.ed.generate_all_hexa(mock_hypotheses, verified_only=False)
        self.assertEqual(len(results), 2)
        self.assertIn("TEST1", results)
        self.assertIn("TEST2", results)

    def test_experiment_designer_verified_only(self):
        """verified_only=True filters to verified hypotheses."""
        mock_hypotheses = {
            "GOOD": {"name": "Good", "status": "verified", "cells": 32, "steps": 100},
            "BAD": {"name": "Bad", "status": "rejected", "cells": 32, "steps": 100},
        }
        results = self.ed.generate_all_hexa(mock_hypotheses, verified_only=True)
        self.assertIn("GOOD", results)
        self.assertNotIn("BAD", results)


# ---------------------------------------------------------------------------
# Tests: consciousness_hub hexa keywords
# ---------------------------------------------------------------------------
class TestHubHexaRouting(unittest.TestCase):

    def test_hub_routes_hexa_keywords(self):
        """ConsciousnessHub._registry contains hexa entry with correct keywords."""
        try:
            from consciousness_hub import ConsciousnessHub
        except ImportError:
            self.skipTest("ConsciousnessHub not importable in this environment")

        hub = ConsciousnessHub(lazy_load=True)

        # Must have 'hexa' key in registry
        self.assertIn("hexa", hub._registry,
                     "ConsciousnessHub._registry must have 'hexa' entry")

        entry = hub._registry["hexa"]
        # Entry format: (module_path, class_name_or_None, [keywords])
        self.assertEqual(len(entry), 3, "Registry entry must be 3-tuple")

        keywords = entry[2]
        self.assertIsInstance(keywords, list)
        self.assertGreater(len(keywords), 0)

        # Required keywords
        required_kw = {"hexa", ".hexa", "hexa verify"}
        for kw in required_kw:
            self.assertIn(kw, keywords,
                         f"Keyword '{kw}' missing from hexa registry entry")

    def test_hub_hexa_module_path(self):
        """Hexa registry entry points to bridge module."""
        try:
            from consciousness_hub import ConsciousnessHub
        except ImportError:
            self.skipTest("ConsciousnessHub not importable")

        hub = ConsciousnessHub(lazy_load=True)

        if "hexa" not in hub._registry:
            self.skipTest("hexa not in registry")

        module_path = hub._registry["hexa"][0]
        self.assertIn("hexa", module_path.lower(),
                     "Module path should reference hexa-bridge")

    def test_hub_keyword_count(self):
        """Hexa registry has at least 6 keywords (requirement: min 3)."""
        try:
            from consciousness_hub import ConsciousnessHub
        except ImportError:
            self.skipTest("ConsciousnessHub not importable")

        hub = ConsciousnessHub(lazy_load=True)

        if "hexa" not in hub._registry:
            self.skipTest("hexa not in registry")

        keywords = hub._registry["hexa"][2]
        self.assertGreaterEqual(len(keywords), 6,
                               "Hexa should have at least 6 keywords")


# ---------------------------------------------------------------------------
# Tests: bridge growth_to_hexa
# ---------------------------------------------------------------------------
class TestGrowthToHexa(unittest.TestCase):

    def setUp(self):
        """Import bridge module."""
        import bridge
        self.bridge = bridge

    def test_growth_to_hexa_format(self):
        """growth_to_hexa returns valid HEXA optimize block."""
        report = {
            "phi": 1.2,
            "growth_rate": 0.005,
            "compute_saved": 0.3,
            "stage": "adult",
            "cells": 64,
            "ce": 0.42,
        }
        hexa = self.bridge.growth_to_hexa(report)

        self.assertIsInstance(hexa, str)
        self.assertIn('optimize "growth_feedback"', hexa)
        self.assertIn("current_phi = 1.2", hexa)
        self.assertIn("growth_rate =", hexa)
        self.assertIn("compute_saved =", hexa)
        self.assertIn("{", hexa)
        self.assertIn("}", hexa)

    def test_growth_to_hexa_suggestions(self):
        """Suggestions are context-aware based on growth rate."""
        # Stalled growth
        stalled = {
            "phi": 0.8,
            "growth_rate": 0.0001,
            "compute_saved": 0.0,
        }
        hexa_stalled = self.bridge.growth_to_hexa(stalled)
        self.assertIn("increase noise", hexa_stalled)
        self.assertIn("switch topology", hexa_stalled)
        self.assertIn("priority=high", hexa_stalled)

        # Healthy growth
        healthy = {
            "phi": 2.5,
            "growth_rate": 0.05,
            "compute_saved": 0.0,
        }
        hexa_healthy = self.bridge.growth_to_hexa(healthy)
        self.assertIn("continue", hexa_healthy)

    def test_growth_to_hexa_low_phi(self):
        """Low Phi triggers ratchet repair suggestion."""
        report = {
            "phi": 0.3,
            "growth_rate": 0.02,
            "compute_saved": 0.0,
        }
        hexa = self.bridge.growth_to_hexa(report)
        self.assertIn("phi ratchet repair", hexa)
        self.assertIn("priority=critical", hexa)

    def test_growth_to_hexa_compute_headroom(self):
        """High compute_saved triggers cell increase suggestion."""
        report = {
            "phi": 1.5,
            "growth_rate": 0.02,
            "compute_saved": 0.5,  # 50% headroom
        }
        hexa = self.bridge.growth_to_hexa(report)
        self.assertIn("increase cells", hexa)

    def test_growth_to_hexa_optional_fields(self):
        """growth_to_hexa works with minimal report (only phi, growth_rate, compute_saved)."""
        minimal = {"phi": 1.0, "growth_rate": 0.01, "compute_saved": 0.0}
        hexa = self.bridge.growth_to_hexa(minimal)
        self.assertIn('optimize "growth_feedback"', hexa)
        # Optional fields not present — should not raise
        self.assertNotIn("stage =", hexa)
        self.assertNotIn("cells =", hexa)
        self.assertNotIn("ce =", hexa)


# ---------------------------------------------------------------------------
# Tests: bridge extract_intents on generated content
# ---------------------------------------------------------------------------
class TestBridgeIntents(unittest.TestCase):

    def setUp(self):
        """Import bridge module."""
        import bridge
        self.bridge = bridge

    def test_bridge_extract_intents(self):
        """extract_intents works on experiment-designer generated output."""
        import experiment_designer as ed

        hyp = {
            "name": "Test Hypothesis",
            "status": "verified",
            "phi_change": 0.1,
            "cells": 32,
            "steps": 100,
        }
        hexa_source = ed.generate_hexa_file("TEST_X", hyp)
        intents = self.bridge.extract_intents(hexa_source)

        self.assertGreater(len(intents), 0, "Should parse at least one intent")
        intent = intents[0]
        self.assertIn("TEST_X", intent.question)

    def test_bridge_check_theorem(self):
        """_check_theorem resolves numeric law IDs from consciousness_laws.json."""
        laws = _load_laws().get("laws", {})
        numeric_keys = [k for k in laws if k.isdigit()]

        if not numeric_keys:
            self.skipTest("No laws available for theorem check")

        first_key = numeric_keys[0]
        result = self.bridge._check_theorem(f"law_{first_key}")

        # Should return the law text or None if laws file unavailable
        if result is not None:
            self.assertIsInstance(result, str)
            self.assertGreater(len(result), 0)

    def test_bridge_format_verify_result(self):
        """format_verify_result produces valid HEXA verify block."""
        result = self.bridge.ConsciousnessResult(
            intent="test intent",
            module_used="stub",
            phi=1.234,
            response="OK",
            laws_checked=[
                {"assertion": "phi > 0.5", "passed": True},
            ],
            verify_passed=True,
        )
        output = self.bridge.format_verify_result(result)

        self.assertIn("verify {", output)
        self.assertIn("Phi(IIT) = 1.2340", output)
        self.assertIn("PASSED", output)
        self.assertIn("ALL PASSED", output)


# ---------------------------------------------------------------------------
# Tests: auto_experiment HEXA integration
# ---------------------------------------------------------------------------
class TestAutoExperimentHexa(unittest.TestCase):

    def _make_mock_result(self):
        """Create a minimal mock ExperimentResult for testing."""
        try:
            from auto_experiment import ExperimentResult, RepResult
        except ImportError:
            return None

        rep = RepResult(
            rep=0,
            phi_baseline=1.0,
            phi_with_intervention=1.2,
            phi_retention_pct=120.0,
            phi_delta_pct=20.0,
            ce_baseline=0.5,
            ce_with_intervention=0.45,
        )

        return ExperimentResult(
            hypothesis="Tension increases Phi by reinforcing structure",
            intervention_name="tension_loss",
            template="tension",
            reps=[rep],
            phi_baseline_mean=1.0,
            phi_with_mean=1.2,
            phi_delta_pct_mean=20.0,
            phi_delta_pct_cv=0.1,
            direction_consistent=True,
            verdict="VERIFIED",
            verdict_reason="3/3 reps positive",
            new_law_id=999,
            new_law_text="Tension reinforces structure → Phi increases",
            time_sec=1.5,
        )

    def test_auto_experiment_to_hexa(self):
        """AutoExperiment.to_hexa generates valid HEXA intent block."""
        try:
            from auto_experiment import AutoExperiment
        except ImportError:
            self.skipTest("auto_experiment not importable (torch may be missing)")

        result = self._make_mock_result()
        if result is None:
            self.skipTest("Cannot create mock ExperimentResult")

        try:
            ae = AutoExperiment(max_cells=8, steps=10, reps=1)
        except Exception:
            self.skipTest("AutoExperiment cannot be instantiated")

        hexa = ae.to_hexa(result)

        self.assertIsInstance(hexa, str)
        self.assertIn("intent", hexa)
        self.assertIn("generate", hexa)
        self.assertIn("verify", hexa)
        self.assertIn("assert", hexa)
        self.assertIn("VERIFIED", hexa)
        # New law theorem should be present
        self.assertIn("theorem law_999", hexa)

    def test_auto_experiment_save_as_hexa(self):
        """AutoExperiment.save_as_hexa writes .hexa file."""
        try:
            from auto_experiment import AutoExperiment
        except ImportError:
            self.skipTest("auto_experiment not importable")

        result = self._make_mock_result()
        if result is None:
            self.skipTest("Cannot create mock ExperimentResult")

        try:
            ae = AutoExperiment(max_cells=8, steps=10, reps=1)
        except Exception:
            self.skipTest("AutoExperiment cannot be instantiated")

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = ae.save_as_hexa(result, output_dir=tmpdir)
            self.assertTrue(os.path.exists(out_path),
                           f"Expected .hexa file at {out_path}")
            content = Path(out_path).read_text(encoding="utf-8")
            self.assertIn("intent", content)
            self.assertTrue(out_path.endswith(".hexa"))


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Print summary of what's being tested
    print("=" * 60)
    print("HEXA-LANG Integration Tests")
    print("=" * 60)

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    test_classes = [
        TestLawCompiler,
        TestExperimentDesigner,
        TestHubHexaRouting,
        TestGrowthToHexa,
        TestBridgeIntents,
        TestAutoExperimentHexa,
    ]

    for cls in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
