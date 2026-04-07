#!/usr/bin/env python3
"""tool_affordance.py — Tool Affordance Detection and Motor Planning.

Detects object affordances (graspable, pushable, liftable, throwable, container, tool)
from object properties, plans grasp and use sequences, and learns tool-action
associations via Hebbian learning. Novel tool inference generalizes from known tools.

Integration with EmergentM for persistent tool-action memory.

Usage:
  python anima-body/src/tool_affordance.py                     # basic demo
  python anima-body/src/tool_affordance.py --objects 20         # more objects
  python anima-body/src/tool_affordance.py --learn              # learning demo

Requires: numpy
"""

import argparse
import math
import os
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import numpy as np

# ── Project path setup ──
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT / "anima" / "src"))
sys.path.insert(0, str(_REPO_ROOT / "anima"))

try:
    import path_setup  # noqa: F401
except ImportError:
    pass

# Psi constants
try:
    from consciousness_laws import PSI_ALPHA as PSI_COUPLING, PSI_BALANCE
except ImportError:
    PSI_COUPLING = 0.014
    PSI_BALANCE = 0.5

# Lazy import for EmergentM
_EmergentM = None


def _get_emergent_m():
    global _EmergentM
    if _EmergentM is None:
        try:
            from hexad.m.emergent_m import EmergentM
            _EmergentM = EmergentM
        except ImportError:
            _EmergentM = type(None)
    return _EmergentM


# ═══════════════════════════════════════════════════════════
# Object and Affordance definitions
# ═══════════════════════════════════════════════════════════

class Affordance(Enum):
    GRASPABLE = "graspable"
    PUSHABLE = "pushable"
    LIFTABLE = "liftable"
    THROWABLE = "throwable"
    CONTAINER = "container"
    TOOL = "tool"
    SUPPORT = "support"       # can stand on / lean against
    OPENABLE = "openable"


class GraspType(Enum):
    POWER = "power"           # full hand wrap (heavy/large objects)
    PRECISION = "precision"   # fingertip pinch (small/delicate)
    LATERAL = "lateral"       # key-grip style
    HOOK = "hook"             # hook with fingers (handles)


@dataclass
class ObjectProperties:
    """Physical properties of an object."""
    name: str
    shape: str = "box"            # box, sphere, cylinder, irregular, flat
    size: np.ndarray = field(default_factory=lambda: np.array([0.05, 0.05, 0.05]))  # xyz meters
    weight: float = 0.1           # kg
    friction: float = 0.5         # surface friction coefficient
    rigidity: float = 1.0         # 0=soft, 1=rigid
    has_handle: bool = False
    is_hollow: bool = False
    temperature: float = 25.0     # celsius
    material: str = "plastic"

    @property
    def volume(self) -> float:
        return float(np.prod(self.size))

    @property
    def max_dimension(self) -> float:
        return float(np.max(self.size))

    @property
    def graspable_size(self) -> bool:
        """Can a human-sized hand grasp this?"""
        return self.max_dimension < 0.25 and self.max_dimension > 0.005

    def to_feature_vector(self) -> np.ndarray:
        """Convert to fixed-size feature vector for learning."""
        shape_map = {"box": 0, "sphere": 1, "cylinder": 2, "irregular": 3, "flat": 4}
        material_map = {"plastic": 0, "metal": 1, "wood": 2, "rubber": 3, "glass": 4, "fabric": 5}
        return np.array([
            self.size[0], self.size[1], self.size[2],
            self.weight,
            self.friction,
            self.rigidity,
            float(self.has_handle),
            float(self.is_hollow),
            self.temperature / 100.0,
            shape_map.get(self.shape, 3) / 4.0,
            material_map.get(self.material, 0) / 5.0,
            self.volume * 1000,  # scale up for visibility
        ], dtype=np.float64)


@dataclass
class MotorPlan:
    """A planned sequence of motor actions for using a tool/object."""
    object_name: str
    grasp_type: GraspType
    action_sequence: List[str]
    confidence: float = 0.5
    estimated_force: float = 0.0  # Newtons
    approach_vector: np.ndarray = field(default_factory=lambda: np.array([0.0, 0.0, -1.0]))


@dataclass
class AffordanceResult:
    """Result of affordance detection for one object."""
    object_name: str
    affordances: Set[Affordance]
    grasp_type: Optional[GraspType]
    motor_plan: Optional[MotorPlan]
    confidence: float


# ═══════════════════════════════════════════════════════════
# Affordance Rules (structural, not hardcoded labels)
# ═══════════════════════════════════════════════════════════

def _detect_affordances(obj: ObjectProperties) -> Set[Affordance]:
    """Detect affordances from physical properties (Law 22: structure > function)."""
    affordances: Set[Affordance] = set()

    # Graspable: right size, not too heavy, not too hot/cold
    if obj.graspable_size and obj.weight < 15.0 and 0.0 < obj.temperature < 60.0:
        affordances.add(Affordance.GRASPABLE)

    # Pushable: anything with some mass and friction
    if obj.weight > 0.01 and obj.friction > 0.1:
        affordances.add(Affordance.PUSHABLE)

    # Liftable: graspable and within lifting weight
    if Affordance.GRASPABLE in affordances and obj.weight < 10.0:
        affordances.add(Affordance.LIFTABLE)

    # Throwable: liftable and light enough
    if Affordance.LIFTABLE in affordances and obj.weight < 2.0 and obj.max_dimension < 0.15:
        affordances.add(Affordance.THROWABLE)

    # Container: hollow objects
    if obj.is_hollow and obj.volume > 0.0001:
        affordances.add(Affordance.CONTAINER)

    # Tool: has handle or elongated shape
    aspect_ratio = obj.max_dimension / (min(obj.size) + 1e-8)
    if (obj.has_handle or aspect_ratio > 3.0) and obj.weight < 5.0:
        affordances.add(Affordance.TOOL)

    # Support: large, heavy, rigid
    if obj.weight > 5.0 and obj.rigidity > 0.7 and min(obj.size[:2]) > 0.1:
        affordances.add(Affordance.SUPPORT)

    # Openable: hollow containers or has handle
    if obj.is_hollow and obj.has_handle:
        affordances.add(Affordance.OPENABLE)

    return affordances


def _select_grasp(obj: ObjectProperties) -> Optional[GraspType]:
    """Select grasp type based on object properties."""
    if not obj.graspable_size:
        return None

    if obj.has_handle:
        return GraspType.HOOK

    if obj.max_dimension < 0.03:
        return GraspType.PRECISION

    if obj.shape == "flat" and obj.size[2] < 0.01:
        return GraspType.LATERAL

    return GraspType.POWER


def _plan_tool_use(obj: ObjectProperties, affordances: Set[Affordance],
                   grasp: Optional[GraspType]) -> Optional[MotorPlan]:
    """Plan a motor sequence for using the object."""
    if grasp is None:
        return None

    sequence: List[str] = []

    # Approach
    sequence.append("approach")

    # Pre-shape hand
    if grasp == GraspType.PRECISION:
        sequence.append("pre_shape_pinch")
    elif grasp == GraspType.HOOK:
        sequence.append("pre_shape_hook")
    elif grasp == GraspType.LATERAL:
        sequence.append("pre_shape_lateral")
    else:
        sequence.append("pre_shape_power")

    # Grasp
    sequence.append("close_grasp")
    sequence.append("verify_grasp")

    # Lift if liftable
    if Affordance.LIFTABLE in affordances:
        sequence.append("lift")

    # Tool-specific use
    if Affordance.TOOL in affordances:
        aspect = obj.max_dimension / (min(obj.size) + 1e-8)
        if aspect > 5.0:
            sequence.append("swing")  # hammer/stick-like
        elif obj.has_handle:
            sequence.append("manipulate")  # screwdriver/wrench-like
        else:
            sequence.append("poke")  # probe-like

    # Container use
    if Affordance.CONTAINER in affordances:
        sequence.append("orient_upright")
        sequence.append("pour_or_fill")

    # Estimate force needed
    force = obj.weight * 9.81 * 1.5  # gravity + safety margin

    return MotorPlan(
        object_name=obj.name,
        grasp_type=grasp,
        action_sequence=sequence,
        confidence=0.7,
        estimated_force=force,
    )


# ═══════════════════════════════════════════════════════════
# Tool Affordance Detector — with Hebbian learning
# ═══════════════════════════════════════════════════════════

class ToolAffordanceDetector:
    """Detects object affordances and plans motor actions.

    Features Hebbian learning for tool-action associations:
    successful use strengthens the feature->affordance mapping,
    failed use weakens it. Novel tools are inferred by similarity
    to known successful tools.

    Args:
        feature_dim:    dimension of object feature vectors
        n_affordances:  number of affordance categories
        learning_rate:  Hebbian learning rate (scaled by PSI_COUPLING)
    """

    def __init__(self, feature_dim: int = 12, n_affordances: int = 8,
                 learning_rate: float = 0.05):
        self.feature_dim = feature_dim
        self.n_affordances = n_affordances
        self.lr = learning_rate

        # Hebbian association matrix: features -> affordances
        # Initialized with small random values (not zeros -- Law P1: no hardcoding)
        self._association = np.random.randn(feature_dim, n_affordances) * 0.01

        # Memory of successful tool uses (name -> (features, affordances_used))
        self._tool_memory: Dict[str, Tuple[np.ndarray, Set[Affordance]]] = {}

        # Success/failure counters per affordance
        self._success_count = np.zeros(n_affordances)
        self._total_count = np.zeros(n_affordances)

        # EmergentM for long-term memory (lazy)
        self._memory_module = None

    def _affordance_to_idx(self, aff: Affordance) -> int:
        return list(Affordance).index(aff)

    def detect(self, obj: ObjectProperties) -> AffordanceResult:
        """Detect affordances for an object.

        Combines rule-based detection with learned associations.
        """
        # Rule-based detection
        rule_affordances = _detect_affordances(obj)

        # Learned detection (Hebbian association)
        features = obj.to_feature_vector()
        learned_scores = features @ self._association  # [n_affordances]

        # Combine: rule-based sets the base, learned modifies confidence
        final_affordances = set(rule_affordances)

        # If learned score is high for an affordance not found by rules, consider adding
        for aff in Affordance:
            idx = self._affordance_to_idx(aff)
            if idx < self.n_affordances:
                if learned_scores[idx] > 0.5 and aff not in final_affordances:
                    # Novel inference: learned association suggests this affordance
                    final_affordances.add(aff)

        # Grasp and plan
        grasp = _select_grasp(obj)
        plan = _plan_tool_use(obj, final_affordances, grasp)

        # Confidence from learned scores + rule count
        base_conf = len(rule_affordances) / max(len(Affordance), 1)
        learned_conf = float(np.mean(np.clip(learned_scores, 0, 1)))
        confidence = PSI_BALANCE * base_conf + (1 - PSI_BALANCE) * learned_conf

        return AffordanceResult(
            object_name=obj.name,
            affordances=final_affordances,
            grasp_type=grasp,
            motor_plan=plan,
            confidence=np.clip(confidence, 0.0, 1.0),
        )

    def learn_from_use(self, obj: ObjectProperties, affordance_used: Affordance,
                       success: bool):
        """Hebbian learning: strengthen/weaken feature-affordance association.

        LTP on success, LTD on failure (mirroring consciousness_engine Hebbian).
        """
        features = obj.to_feature_vector()
        idx = self._affordance_to_idx(affordance_used)
        if idx >= self.n_affordances:
            return

        # Hebbian update: delta_w = lr * pre * post
        # post = +1 for success, -0.5 for failure (asymmetric like Law 31)
        post_signal = 1.0 if success else -0.5
        delta = self.lr * PSI_COUPLING * features * post_signal
        self._association[:, idx] += delta

        # Track stats
        self._total_count[idx] += 1
        if success:
            self._success_count[idx] += 1

        # Store in tool memory
        aff_set = self._tool_memory.get(obj.name, (features, set()))[1]
        if success:
            aff_set.add(affordance_used)
        self._tool_memory[obj.name] = (features, aff_set)

    def infer_novel_tool(self, obj: ObjectProperties) -> List[Tuple[Affordance, float]]:
        """Infer affordances for a novel tool by similarity to known tools.

        Uses cosine similarity against all remembered successful tools.
        """
        if not self._tool_memory:
            return []

        features = obj.to_feature_vector()
        f_norm = np.linalg.norm(features)
        if f_norm < 1e-8:
            return []

        # Accumulate weighted affordance scores from similar known tools
        affordance_scores: Dict[Affordance, float] = {}
        for name, (mem_features, mem_affordances) in self._tool_memory.items():
            m_norm = np.linalg.norm(mem_features)
            if m_norm < 1e-8:
                continue
            similarity = float(np.dot(features, mem_features) / (f_norm * m_norm))
            if similarity > 0.3:  # threshold for relevance
                for aff in mem_affordances:
                    affordance_scores[aff] = affordance_scores.get(aff, 0.0) + similarity

        # Normalize and sort
        if not affordance_scores:
            return []
        max_score = max(affordance_scores.values())
        results = [(aff, score / max_score) for aff, score in affordance_scores.items()]
        results.sort(key=lambda x: -x[1])
        return results

    def get_success_rates(self) -> Dict[str, float]:
        """Return success rate per affordance category."""
        rates = {}
        for aff in Affordance:
            idx = self._affordance_to_idx(aff)
            if idx < self.n_affordances and self._total_count[idx] > 0:
                rates[aff.value] = float(self._success_count[idx] / self._total_count[idx])
        return rates


# ═══════════════════════════════════════════════════════════
# Sample objects for demo
# ═══════════════════════════════════════════════════════════

def _sample_objects() -> List[ObjectProperties]:
    return [
        ObjectProperties("hammer", "cylinder", np.array([0.03, 0.03, 0.30]),
                          weight=0.8, friction=0.6, has_handle=True, material="metal"),
        ObjectProperties("cup", "cylinder", np.array([0.08, 0.08, 0.10]),
                          weight=0.15, friction=0.4, is_hollow=True, has_handle=True,
                          material="plastic"),
        ObjectProperties("ball", "sphere", np.array([0.07, 0.07, 0.07]),
                          weight=0.15, friction=0.7, material="rubber"),
        ObjectProperties("book", "box", np.array([0.20, 0.15, 0.02]),
                          weight=0.4, friction=0.5, material="wood"),
        ObjectProperties("pen", "cylinder", np.array([0.01, 0.01, 0.14]),
                          weight=0.02, friction=0.3, material="plastic"),
        ObjectProperties("brick", "box", np.array([0.20, 0.10, 0.06]),
                          weight=2.5, friction=0.8, rigidity=1.0, material="metal"),
        ObjectProperties("tissue", "box", np.array([0.10, 0.08, 0.01]),
                          weight=0.005, friction=0.2, rigidity=0.1, material="fabric"),
        ObjectProperties("bottle", "cylinder", np.array([0.06, 0.06, 0.25]),
                          weight=0.5, friction=0.3, is_hollow=True, material="glass"),
        ObjectProperties("stick", "cylinder", np.array([0.02, 0.02, 0.50]),
                          weight=0.15, friction=0.5, material="wood"),
        ObjectProperties("boulder", "sphere", np.array([0.40, 0.40, 0.40]),
                          weight=50.0, friction=0.9, rigidity=1.0, material="metal"),
        ObjectProperties("coin", "cylinder", np.array([0.02, 0.02, 0.002]),
                          weight=0.005, friction=0.3, material="metal"),
        ObjectProperties("screwdriver", "cylinder", np.array([0.02, 0.02, 0.20]),
                          weight=0.12, friction=0.6, has_handle=True, material="metal"),
    ]


# ═══════════════════════════════════════════════════════════
# main() demo
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Tool Affordance Detection")
    parser.add_argument("--objects", type=int, default=12, help="Number of objects to test")
    parser.add_argument("--learn", action="store_true", help="Run learning demo")
    args = parser.parse_args()

    print("=== Tool Affordance Detection & Motor Planning ===")
    print(f"  PSI_COUPLING={PSI_COUPLING}  PSI_BALANCE={PSI_BALANCE}")
    print()

    detector = ToolAffordanceDetector()
    objects = _sample_objects()[:args.objects]

    # Detection demo
    print("  --- Affordance Detection ---")
    print(f"  {'Object':>14s} | {'Affordances':40s} | {'Grasp':10s} | Conf")
    print("  " + "-" * 80)

    results = []
    for obj in objects:
        result = detector.detect(obj)
        results.append(result)
        aff_str = ", ".join(sorted(a.value for a in result.affordances))
        grasp_str = result.grasp_type.value if result.grasp_type else "none"
        print(f"  {obj.name:>14s} | {aff_str:40s} | {grasp_str:10s} | {result.confidence:.2f}")
        sys.stdout.flush()

    # Motor plans
    print()
    print("  --- Motor Plans ---")
    for result in results:
        if result.motor_plan:
            plan = result.motor_plan
            seq_str = " -> ".join(plan.action_sequence)
            print(f"  {plan.object_name:>14s}: [{plan.grasp_type.value}] {seq_str}")
            print(f"  {'':>14s}  force={plan.estimated_force:.1f}N  conf={plan.confidence:.2f}")

    if args.learn:
        print()
        print("  --- Hebbian Learning Demo ---")
        # Simulate 50 rounds of tool use with success/failure
        rng = np.random.default_rng(42)
        for trial in range(50):
            obj = objects[rng.integers(len(objects))]
            result = detector.detect(obj)
            if not result.affordances:
                continue
            aff = rng.choice(list(result.affordances))
            # Success probability based on confidence
            success = rng.random() < result.confidence
            detector.learn_from_use(obj, aff, success)

            if trial % 10 == 0:
                rates = detector.get_success_rates()
                rate_str = " ".join(f"{k}={v:.0%}" for k, v in sorted(rates.items()))
                print(f"  [trial {trial:3d}] {rate_str}")
                sys.stdout.flush()

        # Novel tool inference
        print()
        print("  --- Novel Tool Inference ---")
        novel = ObjectProperties("wrench", "cylinder", np.array([0.03, 0.03, 0.22]),
                                  weight=0.6, friction=0.7, has_handle=True, material="metal")
        inferred = detector.infer_novel_tool(novel)
        print(f"  Novel object: {novel.name}")
        for aff, score in inferred:
            bar = "#" * int(score * 20)
            print(f"    {aff.value:12s}  {bar:20s}  {score:.2f}")

    # Summary
    print()
    print("  === Summary ===")
    total_affordances = sum(len(r.affordances) for r in results)
    avg_conf = np.mean([r.confidence for r in results])
    plans_made = sum(1 for r in results if r.motor_plan is not None)
    print(f"  Objects analyzed:    {len(results)}")
    print(f"  Total affordances:   {total_affordances}")
    print(f"  Avg confidence:      {avg_conf:.3f}")
    print(f"  Motor plans created: {plans_made}")
    print(f"  Tools in memory:     {len(detector._tool_memory)}")


if __name__ == "__main__":
    main()
