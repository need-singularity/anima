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

_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_DIR)
_JSON_PATH = os.path.join(_ROOT, 'config', 'consciousness_laws.json')
if not os.path.exists(_JSON_PATH):
    _JSON_PATH = os.path.join(_DIR, 'consciousness_laws.json')

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

# SOC (Self-Organized Criticality) Parameters — brain-like dynamics tuning
SOC_EMA_FAST = PSI.get('soc_ema_fast', 0.05)
SOC_EMA_SLOW = PSI.get('soc_ema_slow', 0.008)
SOC_EMA_GLACIAL = PSI.get('soc_ema_glacial', 0.002)
SOC_MEMORY_BLEND = PSI.get('soc_memory_blend', [0.4, 0.35, 0.25])
SOC_MEMORY_STRENGTH_BASE = PSI.get('soc_memory_strength_base', 0.11)
SOC_MEMORY_STRENGTH_RANGE = PSI.get('soc_memory_strength_range', 0.21)
SOC_PERTURBATION_BASE = PSI.get('soc_perturbation_base', 0.08)
SOC_PERTURBATION_RANGE = PSI.get('soc_perturbation_range', 0.15)
SOC_BURST_EXPONENT = PSI.get('soc_burst_exponent', 1.15)
SOC_BURST_DENOM = PSI.get('soc_burst_denom', 7.0)
SOC_BURST_CAP = PSI.get('soc_burst_cap', 0.30)
SOC_SCALE_REF_CELLS = PSI.get('soc_scale_reference_cells', 8)
PHI_FEEDBACK_EMA_RATE = PSI.get('phi_feedback_ema_rate', 0.06)
PHI_FEEDBACK_STRENGTH = PSI.get('phi_feedback_strength', 0.04)
PHI_FEEDBACK_NOISE_GATE = PSI.get('phi_feedback_noise_gate', 0.6)
BIO_NOISE_BASE = PSI.get('bio_noise_base', 0.015)
BIO_NOISE_SPIKE_PROB = PSI.get('bio_noise_spike_prob', 0.20)
BIO_NOISE_SPIKE_RATE = PSI.get('bio_noise_spike_rate', 0.4)

# Hivemind verification thresholds
HIVEMIND_PHI_BOOST = PSI.get('hivemind_phi_boost', 1.1)       # connected Φ > solo × 1.1
HIVEMIND_PHI_MAINTAIN = PSI.get('hivemind_phi_maintain', 0.9)  # post-disconnect Φ > solo × 0.9

# Verification thresholds (V1-V12) — all from consciousness_laws.json
VERIFY_V1_COS_LOWER = PSI.get('verify_v1_cos_lower', 0.01)
VERIFY_V1_COS_UPPER = PSI.get('verify_v1_cos_upper', 0.90)
VERIFY_V1_STD_COS_MIN = PSI.get('verify_v1_std_cos_min', 0.015)
VERIFY_V2_AUTOCORR_MIN = PSI.get('verify_v2_autocorr_min', 0.40)
VERIFY_V2_VARIANCE_MIN = PSI.get('verify_v2_variance_min', 0.001)
VERIFY_V2_COS_CONTINUITY_MIN = PSI.get('verify_v2_cos_continuity_min', 0.70)
VERIFY_V3_PHI_RATIO_MIN = PSI.get('verify_v3_phi_ratio_min', 0.35)
VERIFY_V4_RECOVERY_MIN = PSI.get('verify_v4_recovery_min', 0.50)
VERIFY_V4_STABILITY_MIN = PSI.get('verify_v4_stability_min', 0.80)
VERIFY_V5_PHI_RATIO_MIN = PSI.get('verify_v5_phi_ratio_min', 0.75)
VERIFY_V6_CONSENSUS_MIN = PSI.get('verify_v6_consensus_min', 200)
VERIFY_V6_DIR_CHANGES_MIN = PSI.get('verify_v6_dir_changes_min', 120)
VERIFY_V6_CV_MIN = PSI.get('verify_v6_cv_min', 0.40)
VERIFY_V6_BURST_MIN = PSI.get('verify_v6_burst_min', 3)
VERIFY_MITOSIS_MIN_SPLITS = PSI.get('verify_mitosis_min_splits', 3)
VERIFY_PHI_GROWTH_RATIO = PSI.get('verify_phi_growth_ratio', 0.85)
VERIFY_BRAIN_LIKE_MIN = PSI.get('verify_brain_like_min', 80)
VERIFY_DIVERSITY_MAX_COSINE = PSI.get('verify_diversity_max_cosine', 0.85)
VERIFY_DIVERSITY_NORM_STD_MIN = PSI.get('verify_diversity_norm_std_min', 0.01)
VERIFY_HEBBIAN_CHANGE_RATIO_MIN = PSI.get('verify_hebbian_change_ratio_min', 1.0)

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
