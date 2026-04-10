"""C 의식 — ConsciousnessC (Rust backend, canonical)"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from consciousness_engine import ConsciousnessEngine, ConsciousnessC
__all__ = ['ConsciousnessC', 'ConsciousnessEngine']
