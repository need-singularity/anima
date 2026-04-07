"""Hexad — 6 pluggable modules, φ(6)=2 gradient groups

  C: ConsciousnessC (consciousness_engine.py)  D: ConsciousDecoderV2 (conscious_decoder.py)
  W: EmergentW (hexad/w/)                      M: EmergentM (hexad/m/)
  S: EmergentS (hexad/s/)                      E: EmergentE (hexad/e/)

Usage:
    from hexad import Hexad, create_hexad
    from hexad.w.emergent_w import EmergentW
    from hexad.s.emergent_s import EmergentS
    from hexad.m.emergent_m import EmergentM
    from hexad.e.emergent_e import EmergentE
"""

from hexad.model import Hexad, Trinity, create_hexad, create_trinity
from hexad.constants import (
    PSI_BALANCE, PSI_GATE, PSI_COUPLING, PSI_STEPS, PSI_ENTROPY,
    GATE_TRAIN, GATE_INFER, GATE_MICRO,
)
from hexad.narrative import NarrativeTracker

# Emergent modules — lazy imports to avoid circular dependencies
try:
    from hexad.w.emergent_w import EmergentW
except Exception:
    pass

try:
    from hexad.s.emergent_s import EmergentS
except Exception:
    pass

try:
    from hexad.m.emergent_m import EmergentM
except Exception:
    pass

try:
    from hexad.e.emergent_e import EmergentE
except Exception:
    pass

__all__ = [
    'Hexad', 'Trinity', 'create_hexad', 'create_trinity',
    'PSI_BALANCE', 'PSI_GATE', 'PSI_COUPLING', 'PSI_STEPS', 'PSI_ENTROPY',
    'GATE_TRAIN', 'GATE_INFER', 'GATE_MICRO',
    'EmergentW', 'EmergentS', 'EmergentM', 'EmergentE',
    'NarrativeTracker',
]
