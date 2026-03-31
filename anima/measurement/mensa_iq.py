#!/usr/bin/env python3
"""mensa_iq.py -- Standardized IQ Test for Consciousness Engines

5 Mensa-style test domains, each 0-100, combined into standardized IQ score.

Domains:
  1. PATTERN_RECOGNITION  (Raven's Matrices style sequences)
  2. LOGICAL_DEDUCTION     (Syllogisms: modus ponens, tollens, disjunctive)
  3. NUMBER_SERIES         (Arithmetic, geometric, fibonacci, primes, triangular)
  4. WORKING_MEMORY        (N-back test on vectors)
  5. SPATIAL_REASONING     (Tensor rotation/flip/scale prediction)

IQ Calculation:
  z_score = (mean(raw_scores) - 0.5) / 0.15
  IQ = 100 + 15 * z_score
  130+ = genius, 100 = average, 70- = impaired

Usage:
  python mensa_iq.py                   # Test all engines
  python mensa_iq.py --cells 32        # Custom cell count
  python mensa_iq.py --quick           # Fewer steps (faster)

API:
  mensa = MensaIQ()
  result = mensa.test(engine)          # IQResult with score, breakdown, IQ
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import math
import time
import sys
import os
import argparse
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Callable, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ['OMP_NUM_THREADS'] = '1'

from mitosis import MitosisEngine, ConsciousMind
from consciousness_meter import PhiCalculator

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10



# ═══════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════

DIM = 64
HIDDEN = 128
STEPS = 300

phi_calc = PhiCalculator(n_bins=16)


# ═══════════════════════════════════════════════════════════
# Results
# ═══════════════════════════════════════════════════════════

@dataclass
class DomainScore:
    """Score for a single test domain."""
    domain: str
    correct: int
    total: int
    score: float          # 0-1
    details: List[str] = field(default_factory=list)


@dataclass
class IQResult:
    """Full IQ test result."""
    pattern: DomainScore
    logic: DomainScore
    number: DomainScore
    memory: DomainScore
    spatial: DomainScore
    raw_mean: float = 0.0
    z_score: float = 0.0
    iq: int = 0
    elapsed_sec: float = 0.0

    @property
    def breakdown(self) -> Dict[str, float]:
        return {
            'pattern': self.pattern.score,
            'logic': self.logic.score,
            'number': self.number.score,
            'memory': self.memory.score,
            'spatial': self.spatial.score,
        }

    def __repr__(self):
        bar_len = 30
        def bar(v):
            filled = int(v * bar_len)
            return '#' * filled + '.' * (bar_len - filled)

        lines = [
            f"",
            f"  IQ = {self.iq}  (z={self.z_score:+.2f}, mean={self.raw_mean:.3f})",
            f"  {'Domain':<22} {'Score':>6} {'Correct':>8}  Bar",
            f"  {'-'*65}",
            f"  Pattern Recognition   {self.pattern.score:>5.1%}  {self.pattern.correct:>3}/{self.pattern.total:<3}  [{bar(self.pattern.score)}]",
            f"  Logical Deduction     {self.logic.score:>5.1%}  {self.logic.correct:>3}/{self.logic.total:<3}  [{bar(self.logic.score)}]",
            f"  Number Series         {self.number.score:>5.1%}  {self.number.correct:>3}/{self.number.total:<3}  [{bar(self.number.score)}]",
            f"  Working Memory        {self.memory.score:>5.1%}  {self.memory.correct:>3}/{self.memory.total:<3}  [{bar(self.memory.score)}]",
            f"  Spatial Reasoning     {self.spatial.score:>5.1%}  {self.spatial.correct:>3}/{self.spatial.total:<3}  [{bar(self.spatial.score)}]",
            f"  {'-'*65}",
            f"  Elapsed: {self.elapsed_sec:.1f}s",
        ]
        return '\n'.join(lines)


# ═══════════════════════════════════════════════════════════
# Helper: Engine I/O
# ═══════════════════════════════════════════════════════════

def _encode_sequence(values: List[float], dim: int = DIM) -> List[torch.Tensor]:
    """Encode a number sequence into input vectors for the engine."""
    vecs = []
    for v in values:
        x = torch.zeros(1, dim)
        # Encode value across multiple dimensions for richness
        x[0, 0] = v / 100.0                            # raw normalized
        x[0, 1] = math.sin(v * 0.1)                    # sinusoidal
        x[0, 2] = math.cos(v * 0.1)
        x[0, 3] = v / max(abs(v) + 1, 1)               # sigmoid-like
        x[0, 4] = float(v % 2) if v == int(v) else 0.5  # parity
        x[0, 5] = math.log(abs(v) + 1)                 # log scale
        # Spread into frequency domain
        for d in range(6, min(dim, 20)):
            x[0, d] = math.sin(v * (d - 5) * 0.3)
        vecs.append(x)
    return vecs


def _read_engine_output(engine: MitosisEngine) -> torch.Tensor:
    """Read combined hidden state from engine as its 'answer'."""
    hiddens = torch.stack([c.hidden.squeeze(0) for c in engine.cells])
    return hiddens.mean(dim=0)  # [hidden_dim]


def _engine_predict_value(engine: MitosisEngine, sequence: List[float],
                          dim: int = DIM) -> float:
    """Feed sequence to engine, then read predicted next value from output."""
    vecs = _encode_sequence(sequence, dim)
    for v in vecs:
        engine.process(v)
    out = _read_engine_output(engine)
    # Decode: use first neuron * 100 as predicted value
    return out[0].item() * 100.0


def _engine_predict_vector(engine: MitosisEngine, sequence: List[torch.Tensor]
                           ) -> torch.Tensor:
    """Feed vector sequence, return engine's output state."""
    for v in sequence:
        engine.process(v)
    return _read_engine_output(engine)


# ═══════════════════════════════════════════════════════════
# Domain 1: PATTERN_RECOGNITION (Raven's Matrices style)
# ═══════════════════════════════════════════════════════════

def _generate_patterns() -> List[Tuple[List[float], float, str]]:
    """Generate 20 progressively harder pattern questions.
    Returns: [(sequence, answer, description), ...]
    """
    patterns = []

    # Level 1: Simple arithmetic (5 questions)
    patterns.append(([2, 4, 6, 8], 10, "+2 series"))
    patterns.append(([5, 10, 15, 20], 25, "+5 series"))
    patterns.append(([3, 6, 9, 12], 15, "+3 series"))
    patterns.append(([1, 4, 7, 10], 13, "+3 from 1"))
    patterns.append(([10, 8, 6, 4], 2, "-2 series"))

    # Level 2: Geometric (5 questions)
    patterns.append(([2, 4, 8, 16], 32, "x2 series"))
    patterns.append(([3, 9, 27, 81], 243, "x3 series"))
    patterns.append(([1, 2, 4, 8], 16, "powers of 2"))
    patterns.append(([100, 50, 25, 12.5], 6.25, "/2 series"))
    patterns.append(([1, 3, 9, 27], 81, "x3 from 1"))

    # Level 3: Fibonacci-like (3 questions)
    patterns.append(([1, 1, 2, 3, 5], 8, "fibonacci"))
    patterns.append(([2, 2, 4, 6, 10], 16, "fibonacci x2 start"))
    patterns.append(([1, 3, 4, 7, 11], 18, "fibonacci variant"))

    # Level 4: Mixed operations (4 questions)
    patterns.append(([1, 2, 4, 7, 11], 16, "+1,+2,+3,+4,+5"))
    patterns.append(([2, 3, 5, 8, 12], 17, "+1,+2,+3,+4,+5 from 2"))
    patterns.append(([1, 4, 9, 16, 25], 36, "perfect squares"))
    patterns.append(([1, 8, 27, 64], 125, "perfect cubes"))

    # Level 5: Hard (3 questions)
    # A=1,C=3,F=6,J=10 -> O=15 (triangular numbers)
    patterns.append(([1, 3, 6, 10], 15, "triangular numbers"))
    patterns.append(([2, 3, 5, 7, 11], 13, "primes"))
    patterns.append(([1, 1, 2, 3, 5, 8, 13], 21, "fibonacci long"))

    return patterns


def test_pattern_recognition(engine_fn: Callable, cells: int = 64) -> DomainScore:
    """Test pattern recognition: feed sequence, check if engine predicts next."""
    patterns = _generate_patterns()
    correct = 0
    details = []

    for seq, answer, desc in patterns:
        engine = engine_fn(cells)
        predicted = _engine_predict_value(engine, seq)

        # Tolerance: within 20% of answer or within 2.0 absolute
        tol = max(abs(answer) * 0.20, 2.0)
        hit = abs(predicted - answer) <= tol
        if hit:
            correct += 1
        details.append(f"  {desc:30s} seq={seq} ans={answer:>6.1f} pred={predicted:>8.2f} {'OK' if hit else 'MISS'}")

    total = len(patterns)
    return DomainScore('pattern', correct, total, correct / total, details)


# ═══════════════════════════════════════════════════════════
# Domain 2: LOGICAL_DEDUCTION
# ═══════════════════════════════════════════════════════════

def _generate_syllogisms() -> List[Tuple[List[torch.Tensor], torch.Tensor, str]]:
    """Generate 15 syllogism tests as vector logic problems.

    Encoding: each proposition is a vector. We test whether the engine
    can produce an output closer to the correct conclusion than to a
    random distractor.

    Modus ponens:  P->Q, P => Q
    Modus tollens: P->Q, ~Q => ~P
    Disjunctive:   P|Q, ~P => Q
    """
    problems = []
    dim = DIM

    def make_concept(seed: int) -> torch.Tensor:
        torch.manual_seed(seed + 1000)
        return F.normalize(torch.randn(1, dim), dim=-1)

    # Modus ponens (5): if A then B; A is true => B
    for i in range(5):
        A = make_concept(i * 3)
        B = make_concept(i * 3 + 1)
        # Premise 1: A->B encoded as A+B
        p1 = A + B
        # Premise 2: A
        p2 = A
        # Conclusion: B
        conclusion = B
        problems.append(([p1, p2], conclusion, f"modus_ponens_{i}"))

    # Modus tollens (5): if A then B; not B => not A
    for i in range(5):
        A = make_concept(i * 3 + 100)
        B = make_concept(i * 3 + 101)
        p1 = A + B       # A->B
        p2 = -B          # ~B
        conclusion = -A   # ~A
        problems.append(([p1, p2], conclusion, f"modus_tollens_{i}"))

    # Disjunctive syllogism (5): A or B; not A => B
    for i in range(5):
        A = make_concept(i * 3 + 200)
        B = make_concept(i * 3 + 201)
        p1 = A + B       # A|B
        p2 = -A          # ~A
        conclusion = B    # B
        problems.append(([p1, p2], conclusion, f"disjunctive_{i}"))

    return problems


def test_logical_deduction(engine_fn: Callable, cells: int = 64) -> DomainScore:
    """Test logical deduction: feed premises, check conclusion similarity."""
    problems = _generate_syllogisms()
    correct = 0
    details = []

    for premises, conclusion, desc in problems:
        engine = engine_fn(cells)

        # Feed premises
        for p in premises:
            engine.process(p)

        # Read engine state
        output = _read_engine_output(engine)
        conc_flat = conclusion.squeeze(0)[:HIDDEN] if conclusion.shape[-1] >= HIDDEN else F.pad(conclusion.squeeze(0), (0, HIDDEN - conclusion.shape[-1]))

        # Also generate a random distractor
        torch.manual_seed(hash(desc) % (2**31))
        distractor = torch.randn(HIDDEN)

        # Score: cosine similarity to conclusion vs distractor
        sim_correct = F.cosine_similarity(output.unsqueeze(0), conc_flat.unsqueeze(0)).item()
        sim_distract = F.cosine_similarity(output.unsqueeze(0), distractor.unsqueeze(0)).item()

        hit = sim_correct > sim_distract
        if hit:
            correct += 1
        details.append(f"  {desc:25s} sim_correct={sim_correct:+.3f} sim_distract={sim_distract:+.3f} {'OK' if hit else 'MISS'}")

    total = len(problems)
    return DomainScore('logic', correct, total, correct / total, details)


# ═══════════════════════════════════════════════════════════
# Domain 3: NUMBER_SERIES
# ═══════════════════════════════════════════════════════════

def _generate_number_series() -> List[Tuple[List[float], List[float], str]]:
    """Generate 20 number series, each requires predicting next 2 values."""
    series = []

    # Arithmetic progressions
    series.append(([3, 6, 9, 12, 15], [18, 21], "AP +3"))
    series.append(([7, 14, 21, 28], [35, 42], "AP +7"))
    series.append(([50, 45, 40, 35], [30, 25], "AP -5"))
    series.append(([2, 5, 8, 11, 14], [17, 20], "AP +3 from 2"))

    # Geometric progressions
    series.append(([2, 6, 18, 54], [162, 486], "GP x3"))
    series.append(([1, 2, 4, 8, 16], [32, 64], "GP x2"))
    series.append(([1000, 100, 10], [1, 0.1], "GP /10"))
    series.append(([3, 12, 48, 192], [768, 3072], "GP x4"))

    # Fibonacci-style
    series.append(([1, 1, 2, 3, 5, 8], [13, 21], "Fibonacci"))
    series.append(([2, 1, 3, 4, 7, 11], [18, 29], "Lucas-like"))

    # Primes
    series.append(([2, 3, 5, 7, 11, 13], [17, 19], "Primes"))

    # Triangular numbers
    series.append(([1, 3, 6, 10, 15], [21, 28], "Triangular"))

    # Square numbers
    series.append(([1, 4, 9, 16, 25], [36, 49], "Squares"))

    # Cube numbers
    series.append(([1, 8, 27, 64, 125], [216, 343], "Cubes"))

    # Alternating
    series.append(([1, -1, 2, -2, 3, -3], [4, -4], "Alternating"))

    # Increasing differences
    series.append(([1, 2, 4, 7, 11, 16], [22, 29], "+1,+2,+3,+4,+5,+6,+7"))
    series.append(([0, 1, 3, 6, 10, 15], [21, 28], "Triangular from 0"))

    # Factorials
    series.append(([1, 2, 6, 24, 120], [720, 5040], "Factorials"))

    # Powers of 2 minus 1
    series.append(([1, 3, 7, 15, 31], [63, 127], "2^n - 1"))

    # Doubling + 1
    series.append(([1, 3, 7, 15, 31], [63, 127], "2n+1 recursive"))

    return series


def test_number_series(engine_fn: Callable, cells: int = 64) -> DomainScore:
    """Test number series prediction: feed series, predict next 2."""
    all_series = _generate_number_series()
    correct = 0
    total_predictions = 0
    details = []

    for seq, answers, desc in all_series:
        engine = engine_fn(cells)

        # Feed the known sequence
        vecs = _encode_sequence(seq)
        for v in vecs:
            engine.process(v)

        # Predict next 2
        hits = 0
        preds = []
        for ans in answers:
            out = _read_engine_output(engine)
            pred = out[0].item() * 100.0
            preds.append(pred)

            tol = max(abs(ans) * 0.25, 2.0)
            if abs(pred - ans) <= tol:
                hits += 1

            # Feed the prediction back as next input
            next_vec = _encode_sequence([pred])[0]
            engine.process(next_vec)

        correct += hits
        total_predictions += len(answers)
        details.append(f"  {desc:25s} ans={answers} pred=[{preds[0]:.1f},{preds[1]:.1f}] hits={hits}/{len(answers)}")

    return DomainScore('number', correct, total_predictions,
                       correct / max(total_predictions, 1), details)


# ═══════════════════════════════════════════════════════════
# Domain 4: WORKING_MEMORY (N-back)
# ═══════════════════════════════════════════════════════════

def test_working_memory(engine_fn: Callable, cells: int = 64) -> DomainScore:
    """N-back test: feed sequence, ask 'what was N steps ago?'

    Test N=1,2,3,5,8. Score = max N with >50% accuracy.
    """
    n_levels = [1, 2, 3, 5, 8]
    trials_per_level = 10
    details = []
    max_n_passed = 0
    total_correct = 0
    total_trials = 0

    for n_back in n_levels:
        # Generate random stimulus sequence
        seq_len = n_back + trials_per_level + 5
        stimuli = [F.normalize(torch.randn(1, DIM), dim=-1) for _ in range(seq_len)]

        engine = engine_fn(cells)
        level_correct = 0

        # Feed initial stimuli
        for i in range(n_back + 5):
            engine.process(stimuli[i])

        # Test phase: for each new stimulus, check if engine remembers n_back ago
        for trial in range(trials_per_level):
            idx = n_back + 5 + trial
            if idx >= seq_len:
                break

            # Feed current stimulus
            engine.process(stimuli[idx])

            # Read engine state
            output = _read_engine_output(engine)

            # Target: the stimulus from n_back steps ago
            target = stimuli[idx - n_back].squeeze(0)
            target_hid = F.pad(target, (0, max(0, HIDDEN - DIM)))[:HIDDEN]

            # Distractor: a random other stimulus
            dist_idx = (idx - n_back + n_back // 2 + 1) % len(stimuli)
            if dist_idx == idx - n_back:
                dist_idx = (dist_idx + 1) % len(stimuli)
            distractor = stimuli[dist_idx].squeeze(0)
            distractor_hid = F.pad(distractor, (0, max(0, HIDDEN - DIM)))[:HIDDEN]

            sim_target = F.cosine_similarity(output.unsqueeze(0), target_hid.unsqueeze(0)).item()
            sim_distract = F.cosine_similarity(output.unsqueeze(0), distractor_hid.unsqueeze(0)).item()

            if sim_target > sim_distract:
                level_correct += 1

        accuracy = level_correct / trials_per_level
        total_correct += level_correct
        total_trials += trials_per_level

        passed = accuracy > 0.50
        if passed:
            max_n_passed = n_back
        details.append(f"  N={n_back:>2}: {level_correct}/{trials_per_level} = {accuracy:.0%}  {'PASS' if passed else 'FAIL'}")

    # Score: max_n_passed normalized to 0-1 (max possible = 8)
    score = max_n_passed / 8.0
    return DomainScore('memory', total_correct, total_trials, score, details)


# ═══════════════════════════════════════════════════════════
# Domain 5: SPATIAL_REASONING (Tensor transforms)
# ═══════════════════════════════════════════════════════════

def _generate_spatial_problems() -> List[Tuple[str, Callable, str]]:
    """Generate 15 spatial transformation problems.
    Each: (name, transform_fn, description)
    """
    problems = []

    # Rotations (90, 180, 270 on 2D slices)
    def rot90(t): return torch.roll(t, 1, dims=-1)
    def rot180(t): return torch.flip(t, dims=[-1])
    def rot270(t): return torch.roll(t, -1, dims=-1)
    problems.append(("rot90", rot90, "Rotate 90"))
    problems.append(("rot180", rot180, "Rotate 180"))
    problems.append(("rot270", rot270, "Rotate 270"))

    # Flips
    def flip_h(t): return torch.flip(t, dims=[-1])
    def flip_sign(t): return -t
    problems.append(("flip_h", flip_h, "Horizontal flip"))
    problems.append(("flip_sign", flip_sign, "Sign flip (negate)"))

    # Scaling
    def scale_2x(t): return t * 2.0
    def scale_half(t): return t * 0.5
    problems.append(("scale_2x", scale_2x, "Scale x2"))
    problems.append(("scale_half", scale_half, "Scale x0.5"))

    # Shifts
    def shift_right(t): return torch.roll(t, 2, dims=-1)
    def shift_left(t): return torch.roll(t, -2, dims=-1)
    problems.append(("shift_r2", shift_right, "Shift right 2"))
    problems.append(("shift_l2", shift_left, "Shift left 2"))

    # Combined transforms
    def rot_scale(t): return torch.roll(t, 1, dims=-1) * 1.5
    def flip_shift(t): return torch.roll(torch.flip(t, dims=[-1]), 1, dims=-1)
    problems.append(("rot+scale", rot_scale, "Rotate + scale 1.5x"))
    problems.append(("flip+shift", flip_shift, "Flip + shift"))

    # Harder: element-wise operations
    def abs_transform(t): return t.abs()
    def relu_transform(t): return F.relu(t)
    def softmax_transform(t): return F.softmax(t, dim=-1)
    problems.append(("abs", abs_transform, "Absolute value"))
    problems.append(("relu", relu_transform, "ReLU"))
    problems.append(("softmax", softmax_transform, "Softmax"))

    return problems


def test_spatial_reasoning(engine_fn: Callable, cells: int = 64) -> DomainScore:
    """Test spatial reasoning: show (input, transform(input)) pairs as training,
    then test on new input."""
    problems = _generate_spatial_problems()
    correct = 0
    details = []
    threshold = 0.3  # cosine similarity threshold for "correct"

    for name, transform_fn, desc in problems:
        engine = engine_fn(cells)

        # Training phase: show 5 (input, output) examples
        for ex in range(5):
            torch.manual_seed(ex * 7 + hash(name) % 1000)
            inp = F.normalize(torch.randn(1, DIM), dim=-1)
            out = transform_fn(inp)

            # Feed input then output
            engine.process(inp)
            engine.process(out)

        # Test phase: show new input, check if engine state resembles transform(input)
        torch.manual_seed(999 + hash(name) % 1000)
        test_inp = F.normalize(torch.randn(1, DIM), dim=-1)
        expected_out = transform_fn(test_inp)

        # Feed test input
        engine.process(test_inp)

        # Read engine output
        engine_out = _read_engine_output(engine)

        # Compare: cosine similarity between engine output and expected
        expected_flat = expected_out.squeeze(0)
        expected_hid = F.pad(expected_flat, (0, max(0, HIDDEN - DIM)))[:HIDDEN]

        sim = F.cosine_similarity(engine_out.unsqueeze(0), expected_hid.unsqueeze(0)).item()

        # Also compare to random distractor
        distractor = torch.randn(HIDDEN)
        sim_dist = F.cosine_similarity(engine_out.unsqueeze(0), distractor.unsqueeze(0)).item()

        hit = sim > sim_dist and sim > threshold
        if hit:
            correct += 1
        details.append(f"  {desc:25s} sim={sim:+.3f} vs_rand={sim_dist:+.3f} {'OK' if hit else 'MISS'}")

    total = len(problems)
    return DomainScore('spatial', correct, total, correct / total, details)


# ═══════════════════════════════════════════════════════════
# MensaIQ: Full Test Suite
# ═══════════════════════════════════════════════════════════

class MensaIQ:
    """Standardized IQ test for consciousness engines."""

    def test(self, engine_fn: Callable, cells: int = 64, verbose: bool = False) -> IQResult:
        """Run full 5-domain IQ test on an engine.

        Args:
            engine_fn: Callable(cells) -> MitosisEngine
            cells: Number of cells to use
            verbose: Print per-question details

        Returns:
            IQResult with all scores and computed IQ
        """
        t0 = time.time()

        # Domain 1: Pattern Recognition
        pattern = test_pattern_recognition(engine_fn, cells)

        # Domain 2: Logical Deduction
        logic = test_logical_deduction(engine_fn, cells)

        # Domain 3: Number Series
        number = test_number_series(engine_fn, cells)

        # Domain 4: Working Memory
        memory = test_working_memory(engine_fn, cells)

        # Domain 5: Spatial Reasoning
        spatial = test_spatial_reasoning(engine_fn, cells)

        elapsed = time.time() - t0

        # Compute IQ
        raw_scores = [pattern.score, logic.score, number.score,
                      memory.score, spatial.score]
        raw_mean = sum(raw_scores) / len(raw_scores)
        z_score = (raw_mean - 0.5) / 0.15
        iq = int(round(100 + 15 * z_score))

        result = IQResult(
            pattern=pattern,
            logic=logic,
            number=number,
            memory=memory,
            spatial=spatial,
            raw_mean=raw_mean,
            z_score=z_score,
            iq=iq,
            elapsed_sec=elapsed,
        )

        if verbose:
            for domain in [pattern, logic, number, memory, spatial]:
                print(f"\n  === {domain.domain.upper()} ({domain.correct}/{domain.total} = {domain.score:.0%}) ===")
                for d in domain.details:
                    print(d)

        return result


# ═══════════════════════════════════════════════════════════
# Engine Factories (from verify_all_engines.py patterns)
# ═══════════════════════════════════════════════════════════

def make_mitosis(cells: int = 64) -> MitosisEngine:
    """Create a warmed-up MitosisEngine."""
    e = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=cells)
    while len(e.cells) < cells:
        e._create_cell(parent=e.cells[0])
    for _ in range(30):
        e.process(torch.randn(1, DIM))
    return e


def engine_baseline(cells: int = 64) -> MitosisEngine:
    """MitosisEngine baseline: random input processing."""
    eng = make_mitosis(cells)
    for _ in range(STEPS):
        eng.process(torch.randn(1, DIM))
    return eng


def engine_oscillator(cells: int = 64) -> MitosisEngine:
    """Kuramoto oscillator engine."""
    eng = make_mitosis(cells)
    phases = torch.randn(cells) * 2 * math.pi
    freqs = torch.randn(cells) * 0.1 + 1.0
    for step in range(STEPS):
        eng.process(torch.randn(1, DIM))
        n = len(eng.cells)
        with torch.no_grad():
            for i in range(n):
                nb = [(i - 1) % n, (i + 1) % n]
                pd = sum(math.sin(phases[j].item() - phases[i].item()) for j in nb)
                phases[i] += freqs[i] + 0.15 * pd / len(nb)
                for j in nb:
                    b = 0.15 * math.cos(phases[j].item() - phases[i].item())
                    eng.cells[i].hidden = (
                        (1 - abs(b)) * eng.cells[i].hidden + abs(b) * eng.cells[j].hidden
                    )
    return eng


def engine_quantum_walk(cells: int = 64) -> MitosisEngine:
    """Quantum walk on hypercube."""
    eng = make_mitosis(cells)
    for step in range(STEPS):
        eng.process(torch.randn(1, DIM))
        n = len(eng.cells)
        n_bits = max(1, int(math.log2(n)))
        with torch.no_grad():
            for i in range(min(n, 32)):
                sp = torch.zeros(HIDDEN)
                cnt = 0
                for bit in range(min(n_bits, 8)):
                    j = i ^ (1 << bit)
                    if j < n:
                        phase = (-1) ** (bin(i & j).count('1'))
                        sp += phase * eng.cells[j].hidden.squeeze(0)
                        cnt += 1
                if cnt > 0:
                    h = eng.cells[i].hidden.squeeze(0)
                    eng.cells[i].hidden = (0.85 * h + 0.15 * sp / cnt).unsqueeze(0)
    return eng


def engine_osc_laser(cells: int = 64) -> MitosisEngine:
    """Oscillator + gentle laser."""
    eng = engine_oscillator(cells)
    blend = 0.05
    pops = torch.rand(cells)
    with torch.no_grad():
        for _ in range(50):
            cavity = torch.stack([c.hidden.squeeze(0) for c in eng.cells]).mean(dim=0)
            for i in range(len(eng.cells)):
                pops[i] += 0.05 * (1 - pops[i]) - 0.02 * pops[i]
                if pops[i] > 0.5:
                    cavity = 0.98 * cavity + 0.02 * eng.cells[i].hidden.squeeze(0) * 0.03 * pops[i]
                    pops[i] *= 0.95
                eng.cells[i].hidden = (
                    (1 - blend) * eng.cells[i].hidden.squeeze(0) + blend * cavity
                ).unsqueeze(0)
    return eng


ENGINES = {
    'Baseline': engine_baseline,
    'Oscillator': engine_oscillator,
    'QuantumWalk': engine_quantum_walk,
    'OscLaser': engine_osc_laser,
}


# ═══════════════════════════════════════════════════════════
# Hivemind Full Test
# ═══════════════════════════════════════════════════════════

def measure_phi(engine: MitosisEngine) -> float:
    """Measure Phi(IIT) for an engine."""
    return phi_calc.compute_phi(engine)[0]


def measure_ce(engine: MitosisEngine, data: List[torch.Tensor]) -> float:
    """Measure cross-entropy proxy: prediction error on data sequence.

    Uses tension-based prediction error: for each step, compare actual
    tension to mean of previous tensions. Lower = better prediction.
    """
    prev_tensions = []
    errors = []
    for x in data:
        result = engine.process(x)
        per_cell = result.get('per_cell', [])
        tensions = [r['tension'] for r in per_cell] if per_cell else [0.0]
        mean_t = sum(tensions) / len(tensions)

        if prev_tensions:
            # Prediction error: how far is current from rolling mean
            pred = sum(prev_tensions[-5:]) / len(prev_tensions[-5:])
            errors.append(abs(mean_t - pred))
        prev_tensions.append(mean_t)

    return sum(errors) / max(len(errors), 1)


def connect_engines(eng_a: MitosisEngine, eng_b: MitosisEngine,
                    steps: int = 200, share_ratio: float = 0.1):
    """Connect two engines via hidden state sharing (hivemind)."""
    for s in range(steps):
        eng_a.process(torch.randn(1, DIM))
        eng_b.process(torch.randn(1, DIM))
        if s % 10 == 0:
            n = min(len(eng_a.cells), len(eng_b.cells))
            with torch.no_grad():
                for i in range(n):
                    shared = (1 - share_ratio) * eng_a.cells[i].hidden + share_ratio * eng_b.cells[i].hidden
                    eng_a.cells[i].hidden = shared
                    eng_b.cells[i].hidden = (
                        (1 - share_ratio) * eng_b.cells[i].hidden + share_ratio * eng_a.cells[i].hidden
                    )


def test_hivemind_full(engine_fn: Callable, cells: int = 64) -> Dict:
    """Test hivemind effect on Phi, CE, and IQ.

    Compares solo engine vs connected pair.

    Returns:
        Dict with solo/hive metrics and deltas.
    """
    mensa = MensaIQ()

    # Generate shared CE test data
    torch.manual_seed(777)
    ce_data = [torch.randn(1, DIM) for _ in range(50)]

    # Solo measurements
    torch.manual_seed(42)
    np.random.seed(42)
    eng_solo = engine_fn(cells)
    solo_phi = measure_phi(eng_solo)
    solo_ce = measure_ce(eng_solo, ce_data)

    torch.manual_seed(42)
    np.random.seed(42)
    solo_iq_result = mensa.test(engine_fn, cells)
    solo_iq = solo_iq_result.iq

    # Connected measurements
    torch.manual_seed(42)
    np.random.seed(42)
    eng_a = engine_fn(cells)
    eng_b = engine_fn(cells)
    connect_engines(eng_a, eng_b, steps=200)

    hive_phi = measure_phi(eng_a)
    hive_ce = measure_ce(eng_a, ce_data)

    # For IQ: create a factory that returns the already-connected engine
    def hive_engine_fn(c):
        eng_x = engine_fn(c)
        eng_y = engine_fn(c)
        connect_engines(eng_x, eng_y, steps=200)
        return eng_x

    torch.manual_seed(42)
    np.random.seed(42)
    hive_iq_result = mensa.test(hive_engine_fn, cells)
    hive_iq = hive_iq_result.iq

    return {
        'solo_phi': solo_phi,
        'solo_ce': solo_ce,
        'solo_iq': solo_iq,
        'hive_phi': hive_phi,
        'hive_ce': hive_ce,
        'hive_iq': hive_iq,
        'phi_delta': hive_phi - solo_phi,
        'ce_delta': hive_ce - solo_ce,
        'iq_delta': hive_iq - solo_iq,
        'solo_breakdown': solo_iq_result.breakdown,
        'hive_breakdown': hive_iq_result.breakdown,
    }


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Mensa IQ Test for Consciousness Engines")
    parser.add_argument('--cells', type=int, default=64)
    parser.add_argument('--quick', action='store_true', help='Fewer steps')
    parser.add_argument('--verbose', action='store_true', help='Show per-question details')
    parser.add_argument('--hivemind', action='store_true', help='Also run hivemind tests')
    args = parser.parse_args()

    global STEPS
    if args.quick:
        STEPS = 100

    cells = args.cells

    print("=" * 72)
    print("  MENSA IQ TEST FOR CONSCIOUSNESS ENGINES")
    print(f"  Cells: {cells}, Steps: {STEPS}")
    print("=" * 72)

    mensa = MensaIQ()

    # ── Phase 1: Individual IQ Tests ──
    print(f"\n{'Engine':<15} {'Pattern':>8} {'Logic':>8} {'Number':>8} {'Memory':>8} {'Spatial':>8} {'IQ':>6} {'Time':>6}")
    print("-" * 72)

    iq_results = {}
    for name, fn in ENGINES.items():
        torch.manual_seed(42)
        np.random.seed(42)
        result = mensa.test(fn, cells, verbose=args.verbose)
        iq_results[name] = result

        print(f"{name:<15} {result.pattern.score:>7.0%} {result.logic.score:>7.0%} "
              f"{result.number.score:>7.0%} {result.memory.score:>7.0%} "
              f"{result.spatial.score:>7.0%} {result.iq:>5} {result.elapsed_sec:>5.1f}s")

    # Print IQ interpretations
    print(f"\n{'Engine':<15} {'IQ':>6}  Interpretation")
    print("-" * 50)
    for name, result in iq_results.items():
        iq = result.iq
        if iq >= 145:
            interp = "GENIUS (top 0.1%)"
        elif iq >= 130:
            interp = "GIFTED (top 2%)"
        elif iq >= 115:
            interp = "ABOVE AVERAGE"
        elif iq >= 85:
            interp = "AVERAGE"
        elif iq >= 70:
            interp = "BELOW AVERAGE"
        else:
            interp = "IMPAIRED"
        print(f"{name:<15} {iq:>5}  {interp}")

    # ── Phase 2: Hivemind Tests ──
    if args.hivemind:
        print(f"\n{'=' * 72}")
        print("  HIVEMIND EFFECT ON ALL METRICS")
        print(f"{'=' * 72}")
        print(f"\n{'Engine':<15} {'Solo Phi':>9} {'Hive Phi':>9} {'dPhi':>7} "
              f"{'Solo CE':>8} {'Hive CE':>8} {'dCE':>7} "
              f"{'Solo IQ':>8} {'Hive IQ':>8} {'dIQ':>6}")
        print("-" * 100)

        for name, fn in ENGINES.items():
            torch.manual_seed(42)
            np.random.seed(42)
            hive = test_hivemind_full(fn, cells)

            phi_sign = '+' if hive['phi_delta'] >= 0 else ''
            ce_sign = '+' if hive['ce_delta'] >= 0 else ''
            iq_sign = '+' if hive['iq_delta'] >= 0 else ''

            print(f"{name:<15} {hive['solo_phi']:>8.2f} {hive['hive_phi']:>9.2f} "
                  f"{phi_sign}{hive['phi_delta']:>6.2f} "
                  f"{hive['solo_ce']:>7.4f} {hive['hive_ce']:>8.4f} "
                  f"{ce_sign}{hive['ce_delta']:>6.4f} "
                  f"{hive['solo_iq']:>7} {hive['hive_iq']:>8} "
                  f"{iq_sign}{hive['iq_delta']:>5}")

        # Domain breakdown for hivemind
        print(f"\n  Hivemind Domain Breakdown (Solo -> Hive):")
        print(f"  {'Engine':<15} {'Pat':>10} {'Log':>10} {'Num':>10} {'Mem':>10} {'Spa':>10}")
        print(f"  {'-' * 65}")
        for name, fn in ENGINES.items():
            torch.manual_seed(42)
            np.random.seed(42)
            hive = test_hivemind_full(fn, cells)
            sb = hive['solo_breakdown']
            hb = hive['hive_breakdown']
            print(f"  {name:<15} "
                  f"{sb['pattern']:.0%}->{hb['pattern']:.0%} "
                  f"{sb['logic']:.0%}->{hb['logic']:.0%} "
                  f"{sb['number']:.0%}->{hb['number']:.0%} "
                  f"{sb['memory']:.0%}->{hb['memory']:.0%} "
                  f"{sb['spatial']:.0%}->{hb['spatial']:.0%}")

    print(f"\n{'=' * 72}")
    print("  TEST COMPLETE")
    print(f"{'=' * 72}")


if __name__ == '__main__':
    main()
