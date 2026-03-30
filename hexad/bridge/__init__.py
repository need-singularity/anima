"""Bridge — ThalamicBridge + TensionBridge"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from trinity import ThalamicBridge, TensionBridge
__all__ = ['ThalamicBridge', 'TensionBridge']
