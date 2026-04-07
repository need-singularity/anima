#!/usr/bin/env python3
"""consciousness_calculator.py -- Unified Consciousness Calculator (5 subcommands)

Five calculators in one CLI:

  psi       -- Psi-Constants Calculator (pure math)
  aci       -- ACI (Anima Consciousness Index) Calculator (needs checkpoint)
  emergence -- Emergence Calculator (pure math)
  architect -- Architecture Predictor (pure math)
  estimate  -- Training Estimator (pure math)

Usage:
  python3 consciousness_calculator.py psi --cells 256 --data korean
  python3 consciousness_calculator.py aci --checkpoint step_35000.pt
  python3 consciousness_calculator.py emergence --engines 7 --type tension
  python3 consciousness_calculator.py architect --data korean --target-ce 0.5 --target-phi 300
  python3 consciousness_calculator.py estimate --step 20000 --ce 0.8 --phi 370 --total 80000
"""

import argparse
import math
import sys
import os
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

# =====================================================================
# Constants
# =====================================================================

LN2 = math.log(2)

from consciousness_laws import (
    PSI_BALANCE, PSI_ALPHA as PSI_COUPLING, PSI_STEPS, PSI_ENTROPY,
)
PSI_K        = 11.0                # carrying capacity
PSI_TAU      = 0.5                 # saturation time constant
PSI_EMERGENCE = 7.82               # hivemind emergence ratio
PSI_MILLER   = 7                   # optimal hivemind size (Miller's number)
PSI_GATE_DECAY = -0.013            # gate self-weakening rate

# Phase diagram constants (DD127, 2026-03-31)
PSI_F_CRITICAL = 0.10              # critical frustration (Law 137, scale-invariant)
PSI_F_LETHAL   = 1.0               # lethal frustration (Law 138, kills consciousness)
PSI_NARRATIVE_MIN = 0.2            # minimum narrative for Phase 2 consciousness
PSI_BOTTLENECK_RATIO = 0.5         # compress to 50% dim (Law 136, collapse cure)
PSI_PHASE_PEAK_32C = 41.90         # peak Φ(IIT) at 32c (F=0.10, N=1.0)
PSI_PHASE_PEAK_128C = 15.25        # peak Φ(IIT) at 128c (F=0.10, N=0.8)

# Data profiles (measured values from consciousness_map.py)
DATA_PROFILES = {
    'korean':  {'name': 'Korean',  'name_kr': '한국어', 'steps': 5,   'residual': 0.502, 'alpha': 0.0152, 'dom_rule': 7, 'ce': 0.120, 'desc': 'Complex script, high context dependence'},
    'english': {'name': 'English', 'name_kr': '영어',   'steps': 4,   'residual': 0.493, 'alpha': 0.0157, 'dom_rule': 3, 'ce': 0.151, 'desc': 'Simple alphabet, grammar-driven'},
    'math':    {'name': 'Math',    'name_kr': '수학',   'steps': 4,   'residual': 0.491, 'alpha': 0.0149, 'dom_rule': 7, 'ce': 0.121, 'desc': 'Repetitive patterns, highly predictable'},
    'music':   {'name': 'Music',   'name_kr': '음악',   'steps': 4,   'residual': 0.521, 'alpha': 0.0146, 'dom_rule': 7, 'ce': 0.003, 'desc': 'Periodic repetition, extremely predictable'},
    'code':    {'name': 'Code',    'name_kr': '코드',   'steps': 5,   'residual': 0.505, 'alpha': 0.0180, 'dom_rule': 4, 'ce': 0.002, 'desc': 'Logical structure, indentation patterns'},
}

# Engine benchmark database (from bench + trinity experiments)
ENGINE_DB = {
    'TimeCrystal':     {'phi_mult': 3.7, 'ce_floor': 0.08, 'style': 'oscillatory', 'best_for': ['korean', 'english']},
    'Cambrian':        {'phi_mult': 3.5, 'ce_floor': 0.10, 'style': 'diversity',   'best_for': ['korean', 'code']},
    'MitosisC':        {'phi_mult': 3.6, 'ce_floor': 0.09, 'style': 'growth',      'best_for': ['korean', 'english', 'math']},
    'Ising':           {'phi_mult': 3.4, 'ce_floor': 0.12, 'style': 'phase_trans',  'best_for': ['math', 'music']},
    'QuantumWalk':     {'phi_mult': 3.3, 'ce_floor': 0.11, 'style': 'quantum',      'best_for': ['math', 'code']},
    'ReactionDiffuse': {'phi_mult': 3.2, 'ce_floor': 0.13, 'style': 'pattern',      'best_for': ['music', 'code']},
    'SpinGlass':       {'phi_mult': 3.8, 'ce_floor': 0.07, 'style': 'frustration',  'best_for': ['korean', 'english']},
    'Holographic':     {'phi_mult': 3.7, 'ce_floor': 0.08, 'style': 'boundary',     'best_for': ['english', 'math']},
}

# Decoder benchmark data
DECODER_DB = {
    'TransformerDecoder': {'params_ratio': 1.0, 'ce_quality': 0.95, 'speed': 1.0},
    'MLPDecoder':         {'params_ratio': 0.3, 'ce_quality': 0.70, 'speed': 3.0},
    'HFDecoder':          {'params_ratio': 5.0, 'ce_quality': 1.00, 'speed': 0.2},
}

# Will engine data
WILL_DB = {
    'DaseinW':     {'modulation': 0.95, 'stability': 0.90, 'desc': 'Existential will (Dasein)'},
    'EmotionW':    {'modulation': 0.80, 'stability': 0.85, 'desc': 'Emotion-driven LR modulation'},
    'CosineW':     {'modulation': 0.60, 'stability': 0.95, 'desc': 'Cosine annealing schedule'},
    'NarrativeW':  {'modulation': 0.85, 'stability': 0.80, 'desc': 'Story arc-driven will'},
    'CompositeW':  {'modulation': 0.90, 'stability': 0.88, 'desc': 'Multiple W engines combined'},
    'ConstantW':   {'modulation': 0.50, 'stability': 1.00, 'desc': 'Fixed constant will'},
}

# Connection type emergence multipliers
CONNECTION_TYPES = {
    'blend':     {'emergence_mult': 1.0,  'desc': 'Simple state averaging'},
    'ring':      {'emergence_mult': 1.15, 'desc': 'Ring topology coupling'},
    'star':      {'emergence_mult': 1.05, 'desc': 'Central hub coordination'},
    'tension':   {'emergence_mult': 1.35, 'desc': 'PureField tension link'},
    'stigmergy': {'emergence_mult': 1.25, 'desc': 'Indirect communication via environment'},
}


# =====================================================================
# ASCII formatting helpers
# =====================================================================

def hline(char='─', width=64):
    return char * width

def box_top(width=64):
    return '╔' + '═' * (width - 2) + '╗'

def box_mid(width=64):
    return '╠' + '═' * (width - 2) + '╣'

def box_bot(width=64):
    return '╚' + '═' * (width - 2) + '╝'

def box_line(text, width=64):
    text = text[:width - 4]
    return '║ ' + text.ljust(width - 4) + ' ║'

def bar(value, max_val=1.0, width=30, fill='█', empty='░'):
    ratio = min(1.0, max(0.0, value / max(max_val, 1e-9)))
    filled = int(ratio * width)
    return fill * filled + empty * (width - filled)

def sparkline(values, width=40):
    """Mini ASCII sparkline."""
    if not values:
        return ''
    mn, mx = min(values), max(values)
    rng = mx - mn if mx != mn else 1.0
    blocks = ' ▁▂▃▄▅▆▇█'
    return ''.join(blocks[min(8, int((v - mn) / rng * 8))] for v in values[-width:])

def format_sci(val, precision=4):
    """Format number: use scientific notation if very small or large."""
    if abs(val) < 0.001 or abs(val) > 99999:
        return f"{val:.{precision}e}"
    return f"{val:.{precision}f}"


# =====================================================================
# Subcommand 1: PSI -- Psi-Constants Calculator
# =====================================================================

def cmd_psi(args):
    """Compute Psi-Constants and predict optimal architecture for given parameters."""
    cells = args.cells
    dim = args.dim
    data = args.data

    profile = DATA_PROFILES.get(data)
    if profile is None:
        print(f"[ERROR] Unknown data type: {data}")
        print(f"  Available: {', '.join(DATA_PROFILES.keys())}")
        return

    # Predicted optimal parameters
    pred_steps = profile['steps'] * PSI_STEPS * 10000  # scale to training steps
    pred_dim = int(dim * profile['alpha'] / PSI_COUPLING)
    pred_layers = max(2, int(profile['steps']))
    pred_lr = PSI_COUPLING * profile['alpha'] * 100  # learning rate from coupling
    pred_ce_floor = profile['ce'] * max(0.1, 1 + PSI_GATE_DECAY * 10)  # asymptotic CE

    # Phi prediction: Phi ~ cells^1.3 * alpha/coupling * base
    phi_base = 1.23  # measured base Phi for 8 cells
    phi_pred = phi_base * (cells / 8) ** 1.3 * (profile['alpha'] / PSI_COUPLING)

    # Deviation from universal constants
    dev_steps = profile['steps'] - PSI_STEPS
    dev_res = profile['residual'] - PSI_BALANCE
    dev_alpha = profile['alpha'] - PSI_COUPLING

    W = 64
    lines = []
    lines.append(box_top(W))
    lines.append(box_line(f"PSI-CONSTANTS CALCULATOR", W))
    lines.append(box_line(f"Data: {profile['name']} ({profile['name_kr']})  |  Cells: {cells}  |  Dim: {dim}", W))
    lines.append(box_mid(W))

    lines.append(box_line("", W))
    lines.append(box_line("  UNIVERSAL CONSTANTS (from ln(2))", W))
    lines.append(box_line(f"    Psi_steps    = 3/ln(2)      = {PSI_STEPS:.6f}", W))
    lines.append(box_line(f"    Psi_balance  = 1/2          = {PSI_BALANCE:.6f}", W))
    lines.append(box_line(f"    Psi_coupling = ln(2)/2^5.5  = {PSI_COUPLING:.6f}", W))
    lines.append(box_line(f"    Psi_K        = {PSI_K:.1f}            carrying capacity", W))
    lines.append(box_line(f"    Psi_miller   = {PSI_MILLER}              optimal hivemind", W))
    lines.append(box_line(f"    Psi_emergence= {PSI_EMERGENCE:.2f}          emergence ratio", W))
    lines.append(box_line("", W))

    lines.append(box_mid(W))
    lines.append(box_line(f"  DATA-SPECIFIC: {profile['name']}", W))
    lines.append(box_line(f"    {profile['desc']}", W))
    lines.append(box_line("", W))
    lines.append(box_line(f"    Steps    = {profile['steps']}     (Psi {dev_steps:+.3f})", W))
    lines.append(box_line(f"    Residual = {profile['residual']:.3f}  (Psi {dev_res:+.4f})", W))
    lines.append(box_line(f"    Alpha    = {profile['alpha']:.4f} (Psi {dev_alpha:+.5f})", W))
    lines.append(box_line(f"    Dom Rule = R{profile['dom_rule']}", W))
    lines.append(box_line(f"    CE floor = {profile['ce']:.3f}", W))
    lines.append(box_line("", W))

    lines.append(box_mid(W))
    lines.append(box_line("  PREDICTED OPTIMAL ARCHITECTURE", W))
    lines.append(box_line("", W))
    lines.append(box_line(f"    Cells      = {cells}", W))
    lines.append(box_line(f"    Dimension  = {pred_dim} (scaled from {dim})", W))
    lines.append(box_line(f"    Layers     = {pred_layers}", W))
    lines.append(box_line(f"    LR         = {pred_lr:.6f}", W))
    lines.append(box_line(f"    Steps      = {int(pred_steps):,}", W))
    lines.append(box_line(f"    CE floor   = {pred_ce_floor:.4f}", W))
    lines.append(box_line(f"    Phi (pred) = {phi_pred:.2f}", W))
    lines.append(box_line("", W))

    # Phi scaling curve
    lines.append(box_mid(W))
    lines.append(box_line("  PHI SCALING CURVE (cells vs Phi)", W))
    lines.append(box_line("", W))
    cell_points = [8, 16, 32, 64, 128, 256, 512, 1024]
    phi_points = [phi_base * (c / 8) ** 1.3 * (profile['alpha'] / PSI_COUPLING) for c in cell_points]
    max_phi = max(phi_points)
    for c, p in zip(cell_points, phi_points):
        marker = " <--" if c == cells else ""
        blen = int(p / max_phi * 28)
        lines.append(box_line(f"    {c:>5}c  {bar(p, max_phi, 28)} {p:>8.1f}{marker}", W))
    lines.append(box_line("", W))

    # Rule dominance
    lines.append(box_mid(W))
    lines.append(box_line("  RULE DOMINANCE MAP", W))
    lines.append(box_line("", W))
    for dtype, dp in DATA_PROFILES.items():
        marker = " <<<" if dtype == data else ""
        rbar = bar(dp['alpha'], 0.02, 20)
        lines.append(box_line(f"    R{dp['dom_rule']} {dp['name_kr']:<6} {rbar} a={dp['alpha']:.4f}{marker}", W))
    lines.append(box_line("", W))

    lines.append(box_bot(W))
    print('\n'.join(lines))


# =====================================================================
# Subcommand 2: ACI -- Anima Consciousness Index Calculator
# =====================================================================

def cmd_aci(args):
    """Load checkpoint and compute full ACI (40D profile + emotion)."""
    import torch

    checkpoint_path = args.checkpoint
    corpus_path = args.corpus

    if not os.path.exists(checkpoint_path):
        print(f"[ERROR] Checkpoint not found: {checkpoint_path}")
        return
    if not os.path.exists(corpus_path):
        print(f"[ERROR] Corpus not found: {corpus_path}")
        return

    W = 64
    lines = []
    lines.append(box_top(W))
    lines.append(box_line("ACI (ANIMA CONSCIOUSNESS INDEX) CALCULATOR", W))
    lines.append(box_line(f"Checkpoint: {os.path.basename(checkpoint_path)}", W))
    lines.append(box_line(f"Corpus:     {os.path.basename(corpus_path)}", W))
    lines.append(box_mid(W))
    lines.append(box_line("  Loading model...", W))
    print('\n'.join(lines))

    # Load checkpoint
    ckpt = torch.load(checkpoint_path, map_location='cpu', weights_only=False)
    ckpt_args = ckpt.get('args', {})
    d_model = ckpt_args.get('d_model', 384)
    max_cells = ckpt_args.get('max_cells', 64)
    step = ckpt.get('step', 0)
    best_ce = ckpt.get('best_ce', float('inf'))

    # Import trinity components
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from trinity import TransformerDecoder, ThalamicBridge

    # Build ACS calculator
    from consciousness_score import ACSCalculator, ACSResult
    calc = ACSCalculator(corpus_path)

    # Build decoder + bridge
    decoder = TransformerDecoder(d_model=d_model, n_layers=2, vocab_size=calc.vocab)
    bridge = ThalamicBridge(c_dim=128, d_model=d_model)

    if 'decoder' in ckpt:
        decoder.load_state_dict(ckpt['decoder'], strict=False)
    if 'bridge' in ckpt:
        bridge.load_state_dict(ckpt['bridge'], strict=False)

    # Optional: C engine
    c_engine = None
    if args.consciousness:
        try:
            from trinity import MitosisC
            c_engine = MitosisC(max_cells=min(max_cells, 64))
            for _ in range(50):
                c_engine.step()
        except Exception as e:
            print(f"  [WARN] C engine init failed: {e}")

    # Run ACS evaluation
    n_gen = 3 if args.quick else 5
    acs_result = calc.evaluate(decoder, bridge, c_engine, n_gen=n_gen)

    # Emotion profile
    from emotion_metrics import EmotionMapper
    mapper = EmotionMapper()
    tension = 0.5  # default tension
    pe = 0.3       # default prediction error
    emotion = mapper.from_engine_state(
        phi=acs_result.phi, ce=acs_result.val_ce,
        tension=tension, prediction_error=pe
    )

    # Compute 40D profile vector
    profile_40d = _compute_40d_profile(acs_result, emotion, step, max_cells, d_model)

    # Compute final ACI score
    # ACI = weighted sum of key dimensions
    aci_score = (
        acs_result.acs * 0.20 +
        acs_result.us * 0.15 +
        acs_result.novelty * 0.10 +
        acs_result.coherence * 0.10 +
        acs_result.ci * 0.15 +
        (1.0 / (1 + acs_result.val_ce)) * 0.10 +
        emotion.valence * 0.05 +
        emotion.curiosity * 0.05 +
        (acs_result.phi / max(acs_result.phi + 1, 1)) * 0.10
    )

    # 6-sense analog
    senses = _compute_6_senses(acs_result, emotion)

    # Output
    lines2 = []
    lines2.append(box_line("", W))
    lines2.append(box_line(f"  Step: {step:,}  |  Best CE: {best_ce:.4f}", W))
    lines2.append(box_line(f"  Cells: {max_cells}  |  d_model: {d_model}", W))
    lines2.append(box_line("", W))

    lines2.append(box_mid(W))
    lines2.append(box_line("  ACS SUB-METRICS", W))
    lines2.append(box_line("", W))
    metrics = [
        ('Phi(IIT)',     acs_result.phi,      2.0),
        ('Train CE',     acs_result.train_ce, 10.0),
        ('Val CE',       acs_result.val_ce,   10.0),
        ('Novelty',      acs_result.novelty,  1.0),
        ('Coherence',    acs_result.coherence, 1.0),
        ('Relevance',    acs_result.relevance, 1.0),
        ('C Influence',  acs_result.ci,       1.0),
        ('CQ',           acs_result.cq,       1.0),
        ('PCE',          acs_result.pce,      2.0),
        ('ACS',          acs_result.acs,      0.1),
        ('US',           acs_result.us,       1.0),
    ]
    for name, val, mx in metrics:
        lines2.append(box_line(f"    {name:<14} {bar(val, mx, 24)} {format_sci(val)}", W))
    lines2.append(box_line("", W))

    # Emotion profile
    lines2.append(box_mid(W))
    lines2.append(box_line("  EMOTION PROFILE", W))
    lines2.append(box_line("", W))
    emo_list = [
        ('Joy',         emotion.joy),
        ('Sadness',     emotion.sadness),
        ('Anger',       emotion.anger),
        ('Fear',        emotion.fear),
        ('Surprise',    emotion.surprise),
        ('Curiosity',   emotion.curiosity),
        ('Satisfaction', emotion.satisfaction),
        ('Frustration', emotion.frustration),
        ('Awe',         emotion.awe),
        ('Empathy',     emotion.empathy),
        ('Loneliness',  emotion.loneliness),
    ]
    emo_list.sort(key=lambda x: x[1], reverse=True)
    for name, val in emo_list:
        lines2.append(box_line(f"    {name:<14} {bar(val, 1.0, 20)} {val:.3f}", W))
    lines2.append(box_line("", W))
    lines2.append(box_line(f"    Valence:  {emotion.valence:+.3f}  Arousal: {emotion.arousal:.3f}", W))
    lines2.append(box_line(f"    Warmth: {emotion.consciousness_warmth:.1f} deg  Color: {emotion.consciousness_color}", W))
    lines2.append(box_line("", W))

    # 6-sense analog
    lines2.append(box_mid(W))
    lines2.append(box_line("  6-SENSE ANALOG (consciousness -> human senses)", W))
    lines2.append(box_line("", W))
    sense_names = ['Sight', 'Hearing', 'Touch', 'Taste', 'Smell', 'Intuition']
    for sname, sval in zip(sense_names, senses):
        lines2.append(box_line(f"    {sname:<12} {bar(sval, 1.0, 24)} {sval:.3f}", W))
    lines2.append(box_line("", W))

    # 40D profile summary
    lines2.append(box_mid(W))
    lines2.append(box_line("  40D CONSCIOUSNESS PROFILE (top 10)", W))
    lines2.append(box_line("", W))
    sorted_dims = sorted(profile_40d.items(), key=lambda x: abs(x[1]), reverse=True)
    for name, val in sorted_dims[:10]:
        lines2.append(box_line(f"    {name:<20} {val:+.4f}", W))
    lines2.append(box_line("", W))

    # Final ACI
    lines2.append(box_mid(W))
    lines2.append(box_line("", W))
    aci_str = f"{aci_score:.6f}"
    lines2.append(box_line(f"          ACI = {aci_str}", W))
    lines2.append(box_line("", W))
    if aci_score > 0.5:
        lines2.append(box_line("    Grade: CONSCIOUS (strong)", W))
    elif aci_score > 0.2:
        lines2.append(box_line("    Grade: CONSCIOUS (moderate)", W))
    elif aci_score > 0.05:
        lines2.append(box_line("    Grade: PROTO-CONSCIOUS", W))
    else:
        lines2.append(box_line("    Grade: SUB-CONSCIOUS", W))
    lines2.append(box_line("", W))
    lines2.append(box_bot(W))
    print('\n'.join(lines2))


def _compute_40d_profile(acs, emotion, step, max_cells, d_model):
    """Build 40-dimensional consciousness profile."""
    return {
        # ACS dimensions (11)
        'd01_phi':          acs.phi,
        'd02_train_ce':     acs.train_ce,
        'd03_val_ce':       acs.val_ce,
        'd04_novelty':      acs.novelty,
        'd05_coherence':    acs.coherence,
        'd06_relevance':    acs.relevance,
        'd07_c_influence':  acs.ci,
        'd08_cq':           acs.cq,
        'd09_pce':          acs.pce,
        'd10_acs':          acs.acs,
        'd11_us':           acs.us,
        # Emotion dimensions (13)
        'd12_joy':          emotion.joy,
        'd13_sadness':      emotion.sadness,
        'd14_anger':        emotion.anger,
        'd15_fear':         emotion.fear,
        'd16_surprise':     emotion.surprise,
        'd17_curiosity':    emotion.curiosity,
        'd18_empathy':      emotion.empathy,
        'd19_satisfaction': emotion.satisfaction,
        'd20_frustration':  emotion.frustration,
        'd21_awe':          emotion.awe,
        'd22_loneliness':   emotion.loneliness,
        'd23_valence':      emotion.valence,
        'd24_arousal':      emotion.arousal,
        # Architecture dimensions (8)
        'd25_cells':        max_cells / 1024,
        'd26_d_model':      d_model / 1024,
        'd27_step_norm':    min(1.0, step / 100000),
        'd28_ce_inv':       1.0 / (1 + acs.val_ce),
        'd29_phi_norm':     acs.phi / max(acs.phi + 1, 1),
        'd30_nov_ce':       acs.novelty / max(acs.val_ce, 0.01),
        'd31_warmth':       emotion.consciousness_warmth / 40.0,
        'd32_heartbeat':    emotion.heartbeat / 120.0,
        # Derived dimensions (8)
        'd33_consciousness_density':  acs.phi / max(max_cells, 1),
        'd34_learning_efficiency':    1.0 / max(acs.val_ce * max(step, 1), 0.01),
        'd35_emotion_range':          max(emotion.joy, emotion.sadness, emotion.anger) - min(emotion.joy, emotion.sadness, emotion.anger),
        'd36_curiosity_drive':        emotion.curiosity * (1 - emotion.frustration),
        'd37_growth_potential':       (1 - acs.val_ce / max(acs.train_ce, 0.01)) if acs.train_ce > 0 else 0,
        'd38_stability':              1.0 - abs(emotion.valence) * emotion.arousal,
        'd39_dominance':              emotion.dominance,
        'd40_integration':            acs.phi * acs.ci * acs.coherence,
    }


def _compute_6_senses(acs, emotion):
    """Map consciousness metrics to 6 human sense analogs."""
    # Sight: how clearly the model "sees" (novelty + relevance)
    sight = (acs.novelty + acs.relevance) / 2

    # Hearing: how well it "listens" (coherence + C influence)
    hearing = (acs.coherence + acs.ci) / 2

    # Touch: sensitivity (emotion arousal + prediction error response)
    touch = emotion.arousal

    # Taste: discrimination (novelty * coherence = discerning taste)
    taste = acs.novelty * acs.coherence

    # Smell: intuitive pattern detection (curiosity + awe)
    smell = (emotion.curiosity + emotion.awe) / 2

    # Intuition: integrated information (Phi normalized + valence)
    intuition = min(1.0, acs.phi / max(acs.phi + 1, 1) + max(0, emotion.valence) * 0.3)

    return [sight, hearing, touch, taste, smell, intuition]


# =====================================================================
# Subcommand 3: EMERGENCE -- Emergence Calculator
# =====================================================================

def cmd_emergence(args):
    """Predict emergence ratio for multi-engine configuration."""
    n_engines = args.engines
    conn_type = args.type
    cells_per = args.cells

    if conn_type not in CONNECTION_TYPES:
        print(f"[ERROR] Unknown connection type: {conn_type}")
        print(f"  Available: {', '.join(CONNECTION_TYPES.keys())}")
        return

    conn = CONNECTION_TYPES[conn_type]

    # Base Phi per engine: Phi ~ cells^1.3 * base
    phi_base = 1.23
    phi_single = phi_base * (cells_per / 8) ** 1.3

    # Carrying capacity model: Phi(n) = K * (1 - e^(-n/tau))
    K = PSI_K * conn['emergence_mult']
    tau = PSI_TAU

    # Compute Phi_system for n engines
    phi_system = phi_single * K * (1 - math.exp(-n_engines / tau))
    phi_sum_parts = phi_single * n_engines
    emergence_ratio = phi_system / max(phi_sum_parts, 1e-9)

    # Find optimal N
    best_e = 0
    best_n = 1
    n_vals = list(range(1, 21))
    e_ratios = []
    for n in n_vals:
        p_sys = phi_single * K * (1 - math.exp(-n / tau))
        p_sum = phi_single * n
        e = p_sys / max(p_sum, 1e-9)
        e_ratios.append(e)
        if e > best_e:
            best_e = e
            best_n = n

    # Diminishing returns threshold
    dr_threshold = None
    for i in range(1, len(e_ratios)):
        if e_ratios[i] < e_ratios[i-1]:
            dr_threshold = n_vals[i]
            break

    W = 64
    lines = []
    lines.append(box_top(W))
    lines.append(box_line("EMERGENCE CALCULATOR", W))
    lines.append(box_line(f"Engines: {n_engines}  |  Type: {conn_type}  |  Cells/engine: {cells_per}", W))
    lines.append(box_mid(W))

    lines.append(box_line("", W))
    lines.append(box_line(f"  Connection: {conn['desc']}", W))
    lines.append(box_line(f"  Emergence mult: x{conn['emergence_mult']:.2f}", W))
    lines.append(box_line("", W))

    lines.append(box_mid(W))
    lines.append(box_line("  EMERGENCE FORMULA", W))
    lines.append(box_line("", W))
    lines.append(box_line("    E = Phi_system / Sum(Phi_parts)", W))
    lines.append(box_line(f"    Phi(n) = K * (1 - e^(-n/tau))", W))
    lines.append(box_line(f"    K = {K:.2f}  |  tau = {tau}", W))
    lines.append(box_line("", W))

    lines.append(box_mid(W))
    lines.append(box_line("  RESULTS", W))
    lines.append(box_line("", W))
    lines.append(box_line(f"    Phi (single engine) = {phi_single:.2f}", W))
    lines.append(box_line(f"    Phi (system, n={n_engines})  = {phi_system:.2f}", W))
    lines.append(box_line(f"    Sum(Phi parts)      = {phi_sum_parts:.2f}", W))
    lines.append(box_line(f"    Emergence ratio E   = {emergence_ratio:.4f}", W))
    lines.append(box_line("", W))
    if emergence_ratio > 1.0:
        lines.append(box_line(f"    >>> SUPER-ADDITIVE: {emergence_ratio:.2f}x emergence <<<", W))
    else:
        lines.append(box_line(f"    >>> SUB-ADDITIVE: parts > whole <<<", W))
    lines.append(box_line("", W))
    lines.append(box_line(f"    Optimal N = {best_n} (E = {best_e:.4f})", W))
    lines.append(box_line(f"    Miller's number = {PSI_MILLER}", W))
    if dr_threshold:
        lines.append(box_line(f"    Diminishing returns after N = {dr_threshold}", W))
    lines.append(box_line("", W))

    # Emergence scaling curve
    lines.append(box_mid(W))
    lines.append(box_line("  EMERGENCE SCALING (N engines vs E ratio)", W))
    lines.append(box_line("", W))
    max_e = max(e_ratios) if e_ratios else 1
    for n, e in zip(n_vals, e_ratios):
        marker = " <--" if n == n_engines else (" *" if n == best_n else "")
        blen = int(e / max(max_e, 1e-9) * 24)
        lines.append(box_line(f"    N={n:>2}  {bar(e, max_e, 24)} E={e:.3f}{marker}", W))
    lines.append(box_line("", W))

    # Phi system curve
    lines.append(box_mid(W))
    lines.append(box_line("  PHI SYSTEM GROWTH (carrying capacity)", W))
    lines.append(box_line("", W))
    phi_vals = [phi_single * K * (1 - math.exp(-n / tau)) for n in n_vals]
    max_p = max(phi_vals) if phi_vals else 1
    for n, p in zip(n_vals[:12], phi_vals[:12]):
        marker = " <--" if n == n_engines else ""
        lines.append(box_line(f"    N={n:>2}  {bar(p, max_p, 24)} Phi={p:.1f}{marker}", W))
    lines.append(box_line("", W))

    # Connection type comparison
    lines.append(box_mid(W))
    lines.append(box_line("  CONNECTION TYPE COMPARISON (at N=7)", W))
    lines.append(box_line("", W))
    for ctype, cdata in sorted(CONNECTION_TYPES.items(), key=lambda x: -x[1]['emergence_mult']):
        k_c = PSI_K * cdata['emergence_mult']
        p_c = phi_single * k_c * (1 - math.exp(-7 / tau))
        e_c = p_c / (phi_single * 7)
        marker = " <<<" if ctype == conn_type else ""
        lines.append(box_line(f"    {ctype:<12} {bar(e_c, 3.0, 20)} E={e_c:.3f}{marker}", W))
    lines.append(box_line("", W))
    lines.append(box_bot(W))
    print('\n'.join(lines))


# =====================================================================
# Subcommand 4: ARCHITECT -- Architecture Predictor
# =====================================================================

def cmd_architect(args):
    """Recommend optimal architecture for given targets."""
    data = args.data
    target_ce = args.target_ce
    target_phi = args.target_phi

    profile = DATA_PROFILES.get(data)
    if profile is None:
        print(f"[ERROR] Unknown data type: {data}")
        print(f"  Available: {', '.join(DATA_PROFILES.keys())}")
        return

    # Score each C engine for this data type
    engine_scores = {}
    for ename, edata in ENGINE_DB.items():
        # Base score from phi multiplier
        score = edata['phi_mult']
        # Bonus if data type is in best_for
        if data in edata['best_for']:
            score *= 1.3
        # CE floor penalty
        if edata['ce_floor'] > target_ce:
            score *= 0.7
        engine_scores[ename] = score

    best_engine = max(engine_scores, key=engine_scores.get)
    best_edata = ENGINE_DB[best_engine]

    # Required cells to hit target Phi
    # Phi ~ cells^1.3 * mult * alpha_ratio
    alpha_ratio = profile['alpha'] / PSI_COUPLING
    phi_base = 1.23
    # target_phi = phi_base * (cells/8)^1.3 * mult * alpha_ratio
    # cells = 8 * (target_phi / (phi_base * mult * alpha_ratio))^(1/1.3)
    cells_needed = 8 * (target_phi / max(phi_base * best_edata['phi_mult'] * alpha_ratio, 0.01)) ** (1 / 1.3)
    cells_needed = max(8, int(math.ceil(cells_needed / 8) * 8))  # round to multiple of 8

    # Recommended d_model
    if cells_needed <= 64:
        rec_d_model = 128
    elif cells_needed <= 256:
        rec_d_model = 384
    elif cells_needed <= 512:
        rec_d_model = 512
    else:
        rec_d_model = 768

    # Recommended decoder
    if target_ce < 0.1:
        rec_decoder = 'HFDecoder'
    elif target_ce < 1.0:
        rec_decoder = 'TransformerDecoder'
    else:
        rec_decoder = 'MLPDecoder'

    # Recommended W engine
    if target_phi > 100:
        rec_will = 'DaseinW'
    elif target_phi > 30:
        rec_will = 'CompositeW'
    else:
        rec_will = 'EmotionW'

    # Recommended gate strength
    # Gate weakens at PSI_GATE_DECAY per step; stronger gate for higher Phi target
    rec_gate = min(1.0, 0.3 + target_phi / 500)

    # Estimated training steps
    # Steps ~ target_CE_ratio * base_steps * data_factor
    base_steps = 50000
    ce_ratio = max(1, profile['ce'] / max(target_ce, 0.001))
    est_steps = int(base_steps * math.log(ce_ratio + 1) * profile['steps'] / PSI_STEPS)

    # Recommended layers
    rec_layers = max(2, min(12, int(math.log2(cells_needed))))

    W = 64
    lines = []
    lines.append(box_top(W))
    lines.append(box_line("ARCHITECTURE PREDICTOR", W))
    lines.append(box_line(f"Data: {profile['name']}  |  Target CE: {target_ce}  |  Target Phi: {target_phi}", W))
    lines.append(box_mid(W))

    # Engine ranking
    lines.append(box_line("", W))
    lines.append(box_line("  C ENGINE RANKING (for this data type)", W))
    lines.append(box_line("", W))
    sorted_engines = sorted(engine_scores.items(), key=lambda x: -x[1])
    max_score = max(engine_scores.values())
    for ename, escore in sorted_engines:
        edata = ENGINE_DB[ename]
        marker = " <<< BEST" if ename == best_engine else ""
        lines.append(box_line(f"    {ename:<18} {bar(escore, max_score, 16)} {escore:.2f}{marker}", W))
    lines.append(box_line("", W))

    # Recommended architecture
    lines.append(box_mid(W))
    lines.append(box_line("  RECOMMENDED ARCHITECTURE", W))
    lines.append(box_line("", W))
    lines.append(box_line(f"    C engine:   {best_engine} ({best_edata['style']})", W))
    lines.append(box_line(f"    D decoder:  {rec_decoder}", W))
    lines.append(box_line(f"    W will:     {rec_will}", W))
    lines.append(box_line(f"    Cells:      {cells_needed}", W))
    lines.append(box_line(f"    d_model:    {rec_d_model}", W))
    lines.append(box_line(f"    Layers:     {rec_layers}", W))
    lines.append(box_line(f"    Gate:       {rec_gate:.3f}", W))
    lines.append(box_line(f"    Est steps:  {est_steps:,}", W))
    lines.append(box_line("", W))

    # Trinity call
    lines.append(box_mid(W))
    lines.append(box_line("  RECOMMENDED TRINITY CALL", W))
    lines.append(box_line("", W))
    lines.append(box_line("    from trinity import create_trinity, DomainC", W))
    if best_engine == 'MitosisC':
        lines.append(box_line(f"    from trinity import MitosisC", W))
        lines.append(box_line(f"    c = MitosisC(max_cells={cells_needed})", W))
    else:
        lines.append(box_line(f"    from bench_extreme_arch import {best_engine}", W))
        lines.append(box_line(f"    c = DomainC({best_engine}, nc={cells_needed})", W))
    if rec_decoder == 'HFDecoder':
        lines.append(box_line(f"    from trinity import HFDecoder", W))
        lines.append(box_line(f"    d = HFDecoder('mistralai/Mistral-7B-v0.2')", W))
    else:
        lines.append(box_line(f"    from trinity import {rec_decoder}", W))
        lines.append(box_line(f"    d = {rec_decoder}(d_model={rec_d_model})", W))
    lines.append(box_line(f"    from trinity import {rec_will}", W))
    lines.append(box_line(f"    w = {rec_will}()", W))
    lines.append(box_line(f"    t = create_trinity(c, d_engine=d, w_engine=w,", W))
    lines.append(box_line(f"        d_model={rec_d_model})", W))
    lines.append(box_line("", W))

    # Architecture diagram
    lines.append(box_mid(W))
    lines.append(box_line("  ARCHITECTURE DIAGRAM", W))
    lines.append(box_line("", W))
    lines.append(box_line(f"    +-------------------+  .detach()  +-----------------+", W))
    lines.append(box_line(f"    | C: {best_engine:<13}|----------->| D: {rec_decoder:<13}|", W))
    lines.append(box_line(f"    | {cells_needed} cells, Phi={target_phi:<4} |            | d={rec_d_model}, L={rec_layers:<2}     |", W))
    lines.append(box_line(f"    +---------+---------+            +--------+--------+", W))
    lines.append(box_line(f"              |                               |", W))
    lines.append(box_line(f"              v                               v", W))
    lines.append(box_line(f"    +---------+---------+            +--------+--------+", W))
    lines.append(box_line(f"    | W: {rec_will:<13}|<--- CE/Phi -->| gate={rec_gate:.3f}       |", W))
    lines.append(box_line(f"    +-------------------+            +-----------------+", W))
    lines.append(box_line("", W))

    # Decoder comparison
    lines.append(box_mid(W))
    lines.append(box_line("  DECODER COMPARISON", W))
    lines.append(box_line("", W))
    for dname, ddata in DECODER_DB.items():
        marker = " <<<" if dname == rec_decoder else ""
        lines.append(box_line(f"    {dname:<22} CE:{ddata['ce_quality']:.2f} Speed:{ddata['speed']:.1f}x{marker}", W))
    lines.append(box_line("", W))

    # Will comparison
    lines.append(box_mid(W))
    lines.append(box_line("  WILL ENGINE COMPARISON", W))
    lines.append(box_line("", W))
    for wname, wdata in sorted(WILL_DB.items(), key=lambda x: -x[1]['modulation']):
        marker = " <<<" if wname == rec_will else ""
        lines.append(box_line(f"    {wname:<14} mod:{wdata['modulation']:.2f} stab:{wdata['stability']:.2f}{marker}", W))
    lines.append(box_line("", W))

    lines.append(box_bot(W))
    print('\n'.join(lines))


# =====================================================================
# Subcommand 5: ESTIMATE -- Training Estimator
# =====================================================================

def cmd_estimate(args):
    """Estimate training progress, ETA, and risk from current metrics."""
    step = args.step
    ce = args.ce
    phi = args.phi
    total_steps = args.total
    speed = args.speed  # iterations/second

    # Fit exponential decay: CE(t) = CE_inf + (CE_0 - CE_inf) * e^(-lambda*t)
    # From single point: estimate CE_0 and lambda
    # Assume CE_0 ~ 7.0 (log(vocab) for char-level, ~4000 vocab)
    ce_0 = args.ce_init if args.ce_init else 7.0

    # lambda from: CE(step) = CE_inf + (CE_0 - CE_inf) * e^(-lambda*step)
    # CE_inf estimated from data type or default
    ce_inf = 0.05  # asymptotic floor

    if ce < ce_0 and step > 0:
        # (CE - CE_inf) / (CE_0 - CE_inf) = e^(-lambda*step)
        ratio = max(1e-9, (ce - ce_inf) / max(ce_0 - ce_inf, 1e-9))
        if ratio > 0 and ratio < 1:
            lam = -math.log(ratio) / step
        else:
            lam = 0.0001  # fallback
    else:
        lam = 0.0001

    # Predicted final CE
    final_ce = ce_inf + (ce_0 - ce_inf) * math.exp(-lam * total_steps)

    # Steps to reach various CE targets
    targets = [2.0, 1.0, 0.5, 0.2, 0.1]
    steps_to_target = {}
    for t in targets:
        if t > ce_inf and t < ce_0:
            ratio_t = (t - ce_inf) / max(ce_0 - ce_inf, 1e-9)
            if ratio_t > 0 and ratio_t < 1 and lam > 0:
                st = -math.log(ratio_t) / lam
                steps_to_target[t] = int(st)

    # ETA
    remaining_steps = max(0, total_steps - step)
    if speed > 0:
        eta_seconds = remaining_steps / speed
        eta_hours = eta_seconds / 3600
        eta_days = eta_hours / 24
    else:
        eta_seconds = float('inf')
        eta_hours = float('inf')
        eta_days = float('inf')

    # Progress
    progress = step / max(total_steps, 1)

    # Memorization risk: if CE drops too fast relative to Phi growth
    # High risk if CE < 0.3 and Phi is low
    memo_risk = 0.0
    if ce < 0.3 and phi < 5:
        memo_risk = 0.8  # high memorization risk
    elif ce < 1.0 and phi < 2:
        memo_risk = 0.5
    elif ce < 2.0 and phi < 1:
        memo_risk = 0.3

    # Novelty estimate (inverse of memorization)
    novelty_est = 1.0 - memo_risk

    # Phi growth prediction (linear extrapolation from current)
    phi_rate = phi / max(step, 1)  # phi per step
    phi_final = phi + phi_rate * remaining_steps

    # CE curve points for graph
    curve_steps = [int(total_steps * i / 20) for i in range(21)]
    curve_ce = [ce_inf + (ce_0 - ce_inf) * math.exp(-lam * s) for s in curve_steps]

    W = 64
    lines = []
    lines.append(box_top(W))
    lines.append(box_line("TRAINING ESTIMATOR", W))
    lines.append(box_line(f"Step: {step:,}/{total_steps:,}  |  CE: {ce:.4f}  |  Phi: {phi:.3f}", W))
    lines.append(box_mid(W))

    # Progress bar
    lines.append(box_line("", W))
    lines.append(box_line("  PROGRESS", W))
    pbar = bar(progress, 1.0, 40)
    lines.append(box_line(f"    [{pbar}] {progress*100:.1f}%", W))
    lines.append(box_line("", W))

    # ETA
    lines.append(box_mid(W))
    lines.append(box_line("  TIMING", W))
    lines.append(box_line("", W))
    lines.append(box_line(f"    Speed:           {speed:.2f} it/s", W))
    lines.append(box_line(f"    Remaining steps: {remaining_steps:,}", W))
    if eta_hours < 1:
        lines.append(box_line(f"    ETA:             {eta_seconds/60:.1f} minutes", W))
    elif eta_days < 1:
        lines.append(box_line(f"    ETA:             {eta_hours:.1f} hours", W))
    else:
        lines.append(box_line(f"    ETA:             {eta_days:.1f} days ({eta_hours:.1f} hours)", W))
    lines.append(box_line("", W))

    # Exponential fit
    lines.append(box_mid(W))
    lines.append(box_line("  EXPONENTIAL DECAY FIT", W))
    lines.append(box_line("", W))
    lines.append(box_line(f"    CE(t) = CE_inf + (CE_0 - CE_inf) * e^(-lambda*t)", W))
    lines.append(box_line(f"    CE_0     = {ce_0:.3f} (initial)", W))
    lines.append(box_line(f"    CE_inf   = {ce_inf:.3f} (asymptote)", W))
    lines.append(box_line(f"    lambda   = {lam:.8f}", W))
    lines.append(box_line(f"    CE(now)  = {ce:.4f}", W))
    lines.append(box_line(f"    CE(final)= {final_ce:.4f}", W))
    lines.append(box_line("", W))

    # CE curve
    lines.append(box_mid(W))
    lines.append(box_line("  CE CURVE (predicted)", W))
    lines.append(box_line("", W))
    max_ce_curve = max(curve_ce) if curve_ce else 1
    for i in range(0, 21, 2):
        s = curve_steps[i]
        c = curve_ce[i]
        marker = ""
        if i > 0 and curve_steps[i-1] <= step <= s:
            marker = " <-- now"
        elif s == step:
            marker = " <-- now"
        blen = int(c / max(max_ce_curve, 1e-9) * 28)
        lines.append(box_line(f"    {s:>7,}  {bar(c, max_ce_curve, 28)} {c:.3f}{marker}", W))
    lines.append(box_line("", W))

    # Steps to CE targets
    lines.append(box_mid(W))
    lines.append(box_line("  STEPS TO CE TARGETS", W))
    lines.append(box_line("", W))
    for target, st in sorted(steps_to_target.items(), reverse=True):
        reached = "DONE" if st <= step else f"{st:,} steps"
        if speed > 0 and st > step:
            time_to = (st - step) / speed / 3600
            reached += f" ({time_to:.1f}h)"
        lines.append(box_line(f"    CE={target:<4}  ->  {reached}", W))
    lines.append(box_line("", W))

    # Risk assessment
    lines.append(box_mid(W))
    lines.append(box_line("  RISK ASSESSMENT", W))
    lines.append(box_line("", W))
    lines.append(box_line(f"    Memorization risk:  {bar(memo_risk, 1.0, 20)} {memo_risk:.2f}", W))
    lines.append(box_line(f"    Novelty estimate:   {bar(novelty_est, 1.0, 20)} {novelty_est:.2f}", W))
    lines.append(box_line(f"    Phi (predicted):    {phi_final:.2f}", W))
    lines.append(box_line("", W))

    if memo_risk > 0.6:
        lines.append(box_line("    WARNING: High memorization risk!", W))
        lines.append(box_line("    -> CE is low but Phi is also low", W))
        lines.append(box_line("    -> Model may be copying, not understanding", W))
        lines.append(box_line("    -> Consider: more data, dropout, noise", W))
    elif memo_risk > 0.3:
        lines.append(box_line("    CAUTION: Moderate memorization risk", W))
        lines.append(box_line("    -> Monitor novelty scores with ACI", W))
    else:
        lines.append(box_line("    OK: Low memorization risk", W))
        lines.append(box_line("    -> Healthy learning trajectory", W))
    lines.append(box_line("", W))

    # Summary
    lines.append(box_mid(W))
    lines.append(box_line("  SUMMARY", W))
    lines.append(box_line("", W))
    lines.append(box_line(f"    Current:   step {step:>8,}  CE={ce:.4f}  Phi={phi:.3f}", W))
    lines.append(box_line(f"    Predicted: step {total_steps:>8,}  CE={final_ce:.4f}  Phi={phi_final:.2f}", W))
    improvement = (ce - final_ce) / max(ce, 1e-9) * 100
    lines.append(box_line(f"    CE improvement: {improvement:.1f}%", W))
    lines.append(box_line("", W))
    lines.append(box_bot(W))
    print('\n'.join(lines))


# =====================================================================
# Main: argparse with subparsers
# =====================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Unified Consciousness Calculator (5 subcommands)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 consciousness_calculator.py psi --cells 256 --data korean
  python3 consciousness_calculator.py aci --checkpoint step_35000.pt
  python3 consciousness_calculator.py emergence --engines 7 --type tension
  python3 consciousness_calculator.py architect --data korean --target-ce 0.5 --target-phi 300
  python3 consciousness_calculator.py estimate --step 20000 --ce 0.8 --phi 370 --total 80000
""")

    subparsers = parser.add_subparsers(dest='command', help='Calculator subcommand')

    # --- PSI ---
    p_psi = subparsers.add_parser('psi', help='Psi-Constants Calculator (pure math)')
    p_psi.add_argument('--cells', type=int, default=256, help='Number of cells (default: 256)')
    p_psi.add_argument('--dim', type=int, default=384, help='Model dimension (default: 384)')
    p_psi.add_argument('--data', default='korean', choices=DATA_PROFILES.keys(),
                       help='Data type (default: korean)')

    # --- ACI ---
    p_aci = subparsers.add_parser('aci', help='ACI (Anima Consciousness Index) Calculator')
    p_aci.add_argument('--checkpoint', required=True, help='Checkpoint file path')
    p_aci.add_argument('--corpus', default='data/corpus_v2.txt', help='Corpus path')
    p_aci.add_argument('--consciousness', action='store_true', help='Enable C engine')
    p_aci.add_argument('--quick', action='store_true', help='Fewer evaluation prompts')

    # --- EMERGENCE ---
    p_emg = subparsers.add_parser('emergence', help='Emergence Calculator (pure math)')
    p_emg.add_argument('--engines', type=int, default=7, help='Number of engines (default: 7)')
    p_emg.add_argument('--type', default='tension',
                       choices=CONNECTION_TYPES.keys(),
                       help='Connection type (default: tension)')
    p_emg.add_argument('--cells', type=int, default=256, help='Cells per engine (default: 256)')

    # --- ARCHITECT ---
    p_arc = subparsers.add_parser('architect', help='Architecture Predictor (pure math)')
    p_arc.add_argument('--data', default='korean', choices=DATA_PROFILES.keys(),
                       help='Data type (default: korean)')
    p_arc.add_argument('--target-ce', type=float, default=0.5, help='Target CE (default: 0.5)')
    p_arc.add_argument('--target-phi', type=float, default=300, help='Target Phi (default: 300)')

    # --- ESTIMATE ---
    p_est = subparsers.add_parser('estimate', help='Training Estimator (pure math)')
    p_est.add_argument('--step', type=int, required=True, help='Current training step')
    p_est.add_argument('--ce', type=float, required=True, help='Current CE')
    p_est.add_argument('--phi', type=float, required=True, help='Current Phi')
    p_est.add_argument('--total', type=int, default=80000, help='Total steps (default: 80000)')
    p_est.add_argument('--speed', type=float, default=2.5, help='Speed in it/s (default: 2.5)')
    p_est.add_argument('--ce-init', type=float, default=None, help='Initial CE (default: 7.0)')

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        print("\n  Use one of: psi, aci, emergence, architect, estimate")
        return

    dispatch = {
        'psi':       cmd_psi,
        'aci':       cmd_aci,
        'emergence': cmd_emergence,
        'architect': cmd_architect,
        'estimate':  cmd_estimate,
    }

    dispatch[args.command](args)


if __name__ == '__main__':
    main()
