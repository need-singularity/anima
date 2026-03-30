"""Hexad/Trinity — 6 pluggable modules, φ(6)=2 gradient groups

Usage:
    from hexad import Hexad, create_hexad
    model = create_hexad(c=ConsciousnessC(...), d=ConsciousDecoderV2(...))
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from trinity import Trinity, create_trinity, create_hexad

# Hexad = Trinity with all 6 modules active
Hexad = Trinity

__all__ = ['Hexad', 'Trinity', 'create_trinity', 'create_hexad']
