"""Integration tests for MitosisEngine — Law 86 fix verification.

Verifies adaptive split threshold + autonomous dynamics ensure:
- Cells grow beyond initial count
- Phi increases with cell activity
- Adaptive threshold adjusts from initial value
- Lorenz perturbation creates cell diversity
- Splits are stable (no immediate merge-back)
- max_cells limit is respected
"""

import torch
import pytest
from mitosis import MitosisEngine, text_to_vector


# --- Shared small config for fast tests ---
SMALL_CFG = dict(
    input_dim=32,
    hidden_dim=64,
    output_dim=32,
    initial_cells=2,
    max_cells=4,
    split_patience=3,
    merge_patience=30,
    noise_scale=0.01,
)


def _run_steps(engine: MitosisEngine, n: int) -> list:
    """Run n steps with rotating synthetic inputs. Returns list of results."""
    topics = [
        "mathematics and abstract reasoning about numbers",
        "music harmony counterpoint and rhythm patterns",
        "programming algorithms data structures loops",
    ]
    results = []
    for i in range(n):
        vec = text_to_vector(topics[i % len(topics)], dim=engine.input_dim)
        result = engine.process(vec)
        results.append(result)
    return results


class TestMitosisLaw86:
    """Law 86 fix: adaptive split threshold + autonomous dynamics."""

    def test_cells_grow_beyond_initial(self):
        """Starting from 2 cells, cells should split within 200 steps.

        Law 86 fix ensures the adaptive threshold tracks actual tension
        values (~0.005-0.009) instead of using the impossible hardcoded 0.3.
        Combined with Lorenz perturbation, this guarantees splits occur.
        Seed fixed for CI determinism.
        """
        torch.manual_seed(42)
        engine = MitosisEngine(**SMALL_CFG)
        assert len(engine.cells) == 2, "Should start with 2 cells"

        _run_steps(engine, 200)

        status = engine.status()
        assert status["n_cells"] > 2, (
            f"Cells should grow beyond 2 within 200 steps, got {status['n_cells']}. "
            f"splits={status['splits']}, split_threshold={status['split_threshold']:.6f}"
        )

    def test_phi_increases_with_cells(self):
        """Phi (proxy) should be > 0 after 50 steps.

        Lorenz perturbation drives cells apart (diverse hidden states),
        which increases cosine distance and thus Phi(proxy).
        """
        engine = MitosisEngine(**SMALL_CFG)
        _run_steps(engine, 50)

        assert engine.phi > 0, (
            f"Phi should be > 0 after 50 steps, got {engine.phi:.6f}"
        )

    def test_adaptive_threshold(self):
        """split_threshold should change from initial value after 20 steps.

        The adaptive threshold updates as mean + 1.5 * std of observed
        tensions once >= 10 tension samples are collected.
        """
        engine = MitosisEngine(**SMALL_CFG)
        initial_threshold = engine.split_threshold  # 0.3 default

        _run_steps(engine, 20)

        assert engine.split_threshold != initial_threshold, (
            f"Adaptive threshold should differ from initial {initial_threshold}, "
            f"got {engine.split_threshold:.6f}"
        )
        # Adaptive threshold should have changed (direction depends on tension distribution)
        # With Lorenz chaos, tensions can exceed 0.3 in small configs

    def test_lorenz_perturbation(self):
        """Cell hidden states should differ after processing (not all identical).

        Autonomous Lorenz perturbation injects cell-specific chaos,
        breaking symmetry between cells even with identical inputs.
        """
        engine = MitosisEngine(**SMALL_CFG)
        _run_steps(engine, 10)

        hiddens = [c.hidden.squeeze(0) for c in engine.cells]
        # Check pairwise: at least one pair should differ
        all_identical = True
        for i in range(len(hiddens)):
            for j in range(i + 1, len(hiddens)):
                cos_sim = torch.nn.functional.cosine_similarity(
                    hiddens[i].unsqueeze(0), hiddens[j].unsqueeze(0)
                ).item()
                if cos_sim < 0.999:
                    all_identical = False
                    break
            if not all_identical:
                break

        assert not all_identical, (
            "Cell hidden states should not be identical after Lorenz perturbation"
        )

    def test_no_immediate_merge_back(self):
        """After a split, cells should not merge back within 10 steps.

        The noise_scale=0.1 (floor) on split ensures parent and child
        diverge enough to exceed the merge_threshold, plus merge_patience=30
        prevents premature merges.
        """
        engine = MitosisEngine(**SMALL_CFG)

        # Run until a split occurs (up to 100 steps)
        split_step = None
        cells_at_split = None
        for i in range(100):
            vec = text_to_vector(f"test input step {i}", dim=engine.input_dim)
            result = engine.process(vec)
            for event in result["events"]:
                if event["type"] == "split" and split_step is None:
                    split_step = engine.step
                    cells_at_split = result["n_cells"]
                    break
            if split_step is not None:
                break

        if split_step is None:
            pytest.skip("No split occurred within 100 steps (rare, non-deterministic)")

        # Run 10 more steps and verify no merge
        for i in range(10):
            vec = text_to_vector(f"post split step {i}", dim=engine.input_dim)
            result = engine.process(vec)

        assert len(engine.cells) >= cells_at_split, (
            f"Cells should not merge back within 10 steps after split. "
            f"Had {cells_at_split} at split, now {len(engine.cells)}"
        )

    def test_max_cells_respected(self):
        """Cells should never exceed max_cells even after many steps."""
        engine = MitosisEngine(**SMALL_CFG)  # max_cells=4
        _run_steps(engine, 200)

        assert len(engine.cells) <= engine.max_cells, (
            f"Cell count {len(engine.cells)} exceeds max_cells {engine.max_cells}"
        )

    def test_status_reports_correctly(self):
        """status() should return consistent data."""
        engine = MitosisEngine(**SMALL_CFG)
        _run_steps(engine, 30)

        status = engine.status()
        assert status["n_cells"] == len(engine.cells)
        assert status["max_cells"] == SMALL_CFG["max_cells"]
        assert status["step"] == 30
        assert "phi" in status
        assert "phi_best" in status
        assert "split_threshold" in status
        assert len(status["cells"]) == len(engine.cells)
