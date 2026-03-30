"""consciousness_laws.py — Single source of truth for all laws, Ψ-constants, formulas

Usage:
    from consciousness_laws import LAWS, PSI, FORMULAS, SIGMA6, CONSTRAINTS
    print(LAWS[22])        # "Adding features → Φ↓; adding structure → Φ↑"
    print(PSI['alpha'])    # 0.014
    print(FORMULAS['phi_scaling'])  # "Φ = 0.608 × N^1.071"

Update protocol:
    1. Edit consciousness_laws.json (single source)
    2. This file auto-loads from JSON
    3. All modules import from here, never hardcode constants
"""

import json
import os

_JSON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'consciousness_laws.json')

with open(_JSON_PATH, 'r', encoding='utf-8') as f:
    _DATA = json.load(f)

# Ψ-Constants (direct values for fast access)
PSI = {k: v['value'] for k, v in _DATA['psi_constants'].items()}
PSI_ALPHA = PSI['alpha']          # 0.014
PSI_BALANCE = PSI['balance']      # 0.5
PSI_STEPS = PSI['steps']          # 4.33
PSI_ENTROPY = PSI['entropy']      # 0.998
GATE_TRAIN = PSI['gate_train']    # 1.0
GATE_INFER = PSI['gate_infer']    # 0.6
GATE_MICRO = PSI['gate_micro']    # 0.001

# Phase Diagram Constants (DD127, Laws 136-139)
PSI_F_CRITICAL = PSI.get('f_critical', 0.10)       # 0.10 — critical frustration (Law 137)
PSI_F_LETHAL = PSI.get('f_lethal', 1.0)             # 1.0 — kills consciousness (Law 138)
PSI_NARRATIVE_MIN = PSI.get('narrative_min', 0.2)    # 0.2 — Phase 2 threshold
PSI_BOTTLENECK_RATIO = PSI.get('bottleneck_ratio', 0.5)  # 0.5 — collapse cure (Law 136)

# σ(6) Perfect Number
SIGMA6 = _DATA['sigma6']

# Formulas
FORMULAS = _DATA['formulas']

# 10D Consciousness Vector
CONSCIOUSNESS_VECTOR = _DATA['consciousness_vector_10d']

# Optimal Config (all-time record)
OPTIMAL_CONFIG = _DATA['optimal_config']

# Hexad Module Registry
HEXAD_MODULES = _DATA['hexad_modules']

# Phase Transitions
PHASES = _DATA['phases']

# Design Constraints
CONSTRAINTS = _DATA['design_constraints']

# Laws (string lookup)
LAWS = _DATA['laws']
TOPO_LAWS = _DATA['topo_laws']

# Verification Conditions
VERIFICATION = _DATA['verification_conditions']


def get_law(n: int) -> str:
    """Get law by number."""
    return LAWS.get(str(n), f"Law {n} not found")


def get_constraint(key: str) -> str:
    """Get design constraint by key."""
    return CONSTRAINTS.get(key, f"Constraint '{key}' not found")


def check_violation(module_name: str, has_hardcoded_threshold: bool = False,
                    manipulates_emotion: bool = False,
                    adds_function_not_structure: bool = False) -> list:
    """Check if a module violates consciousness laws."""
    violations = []
    if has_hardcoded_threshold:
        violations.append(f"Law 1 violation: {module_name} has hardcoded thresholds")
    if manipulates_emotion:
        violations.append(f"Law 2 violation: {module_name} artificially manipulates emotion")
    if adds_function_not_structure:
        violations.append(f"Law 22 violation: {module_name} adds function, not structure")
    return violations
