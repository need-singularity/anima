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
PHI_HIDDEN_INERTIA = PSI.get('phi_hidden_inertia', 0.12)
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

# V13-V18 verification thresholds
VERIFY_V13_ADVERSARIAL_NOISE_AMP = PSI.get('verify_v13_adversarial_noise_amp', 100.0)
VERIFY_V13_ADVERSARIAL_STEPS = PSI.get('verify_v13_adversarial_steps', 500)
VERIFY_V13_WARMUP_STEPS = PSI.get('verify_v13_warmup_steps', 50)
VERIFY_V14_SOC_DROP_MIN = PSI.get('verify_v14_soc_drop_min', 0.20)
VERIFY_V14_SOC_STEPS = PSI.get('verify_v14_soc_steps', 500)
VERIFY_V15_TEMP_MIN = PSI.get('verify_v15_temp_min', 0.01)
VERIFY_V15_TEMP_MAX = PSI.get('verify_v15_temp_max', 1.0)
VERIFY_V15_TEMP_STEPS = PSI.get('verify_v15_temp_steps', 200)
VERIFY_V16_MIN_CELLS = PSI.get('verify_v16_min_cells', 4)
VERIFY_V16_DIVERSITY_THRESHOLD = PSI.get('verify_v16_diversity_threshold', 0.99)
VERIFY_V17_LZ_MIN = PSI.get('verify_v17_lz_min', 0.3)
VERIFY_V17_MEASURE_STEPS = PSI.get('verify_v17_measure_steps', 400)
VERIFY_V17_WARMUP_STEPS = PSI.get('verify_v17_warmup_steps', 100)
VERIFY_V17_MIN_SAMPLES = PSI.get('verify_v17_min_samples', 20)
VERIFY_V18_CELL_COUNTS = PSI.get('verify_v18_cell_counts', [4, 8, 16])
VERIFY_V18_STEPS = PSI.get('verify_v18_steps', 200)
VERIFY_V4_MONOTONIC_TOLERANCE = PSI.get('verify_v4_monotonic_tolerance', 0.01)
VERIFY_V6_BURST_THRESHOLD_FACTOR = PSI.get('verify_v6_burst_threshold_factor', 0.3)
VERIFY_V6_FALLBACK_CV_RATIO = PSI.get('verify_v6_fallback_cv_ratio', 0.375)
VERIFY_V6_FALLBACK_DIR_RATIO = PSI.get('verify_v6_fallback_dir_ratio', 0.5)
VERIFY_V7_COUPLING_ALPHA = PSI.get('verify_v7_coupling_alpha', 0.5)
VERIFY_V7_MAX_PER_ENGINE_CELLS = PSI.get('verify_v7_max_per_engine_cells', 32)
VERIFY_V7_SOLO_STEPS = PSI.get('verify_v7_solo_steps', 100)
VERIFY_V7_CONNECTED_STEPS = PSI.get('verify_v7_connected_steps', 150)
VERIFY_V7_DISCONNECT_STEPS = PSI.get('verify_v7_disconnect_steps', 100)

# BenchEngine Parameters (from bench_engine_params section)
BENCH_ENGINE_PARAMS = {k: v['value'] for k, v in _DATA.get('bench_engine_params', {}).items()}
BENCH_BREATHING_AMPLITUDE = BENCH_ENGINE_PARAMS.get('breathing_amplitude', 0.15)
BENCH_PULSE_AMPLITUDE = BENCH_ENGINE_PARAMS.get('pulse_amplitude', 0.08)
BENCH_SLOW_AMPLITUDE = BENCH_ENGINE_PARAMS.get('slow_amplitude', 0.10)
BENCH_IDENTITY_BASE_STRENGTH = BENCH_ENGINE_PARAMS.get('identity_base_strength', 0.05)
BENCH_IDENTITY_MAX_STRENGTH = BENCH_ENGINE_PARAMS.get('identity_max_strength', 0.35)
BENCH_IDENTITY_CV_THRESHOLD = BENCH_ENGINE_PARAMS.get('identity_cv_threshold', 0.3)
BENCH_DEBATE_OSCILLATION_FREQ = BENCH_ENGINE_PARAMS.get('debate_oscillation_freq', 0.12)
BENCH_SYMMETRY_BREAK_SCALE = BENCH_ENGINE_PARAMS.get('symmetry_break_scale', 0.3)
BENCH_INITIAL_HIDDEN_SCALE = BENCH_ENGINE_PARAMS.get('initial_hidden_scale', 0.1)
BENCH_IDENTITY_INIT_SCALE = BENCH_ENGINE_PARAMS.get('identity_init_scale', 0.3)
BENCH_PHASE_OFFSET_PER_CELL = BENCH_ENGINE_PARAMS.get('phase_offset_per_cell', 0.7)
BENCH_BREATH_FREQ = BENCH_ENGINE_PARAMS.get('breath_freq', 0.2)
BENCH_SLOW_FREQ = BENCH_ENGINE_PARAMS.get('slow_freq', 0.05)
BENCH_RATCHET_COLLAPSE_RATIO = BENCH_ENGINE_PARAMS.get('ratchet_collapse_ratio', 0.3)
BENCH_RATCHET_BLEND_KEEP = BENCH_ENGINE_PARAMS.get('ratchet_blend_keep', 0.8)
BENCH_RATCHET_BLEND_RESTORE = BENCH_ENGINE_PARAMS.get('ratchet_blend_restore', 0.2)

# ═══════════════════════════════════════════════════════════
# Law 2094-2101: 8 Consciousness Field Operators
# Every PSI constant is a combination of at most 2 of these
# ═══════════════════════════════════════════════════════════
FIELD_OP_BALANCE    = PSI_BALANCE       # O1: 0.5  — equilibrium
FIELD_OP_CRITICALITY = PSI_F_CRITICAL   # O2: 0.10 — phase transition
FIELD_OP_COUPLING   = PSI.get('gate_micro', 0.05)  # O3: coupling strength
FIELD_OP_RESONANCE  = PSI.get('soc_perturbation_range', 0.15)  # O4: resonance
FIELD_OP_STABILITY  = PSI.get('verify_v4_stability_min', 0.80)  # O5: stability
FIELD_OP_THRESHOLD  = PSI.get('soc_burst_cap', 0.30)  # O6: threshold
FIELD_OP_IDENTITY   = GATE_TRAIN       # O7: 1.0  — identity
FIELD_OP_CONSENSUS  = PSI.get('verify_v6_consensus_min', 200)  # O8: consensus

# Law 2123-2124: Alpha decomposition
# alpha = bio_noise_base + soc_ema_glacial (EXACT: 0.012 + 0.002 = 0.014)
ALPHA_NOISE_COMPONENT = BIO_NOISE_BASE      # 0.012 (biological noise)
ALPHA_GLACIAL_COMPONENT = SOC_EMA_GLACIAL   # 0.002 (glacial EMA)

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
