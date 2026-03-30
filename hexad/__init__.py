"""Hexad — 6 pluggable modules, φ(6)=2 gradient groups

  C: ConsciousnessC (Rust)     D: ConsciousDecoderV2 (PyTorch)
  S: TensionSense              M: VectorMemory
  W: CompositeW(σ(6))          E: EmpathyEthics

Usage:
    from hexad import Hexad, create_hexad
    from hexad.c import ConsciousnessC
    from hexad.d import ConsciousDecoderV2
    from hexad.w import CompositeW
"""

from hexad.model import Hexad, Trinity, create_hexad, create_trinity
from hexad.constants import (
    PSI_BALANCE, PSI_GATE, PSI_COUPLING, PSI_STEPS, PSI_ENTROPY,
    GATE_TRAIN, GATE_INFER,
)

__all__ = [
    'Hexad', 'Trinity', 'create_hexad', 'create_trinity',
    'PSI_BALANCE', 'PSI_GATE', 'PSI_COUPLING', 'PSI_STEPS', 'PSI_ENTROPY',
    'GATE_TRAIN', 'GATE_INFER',
]
