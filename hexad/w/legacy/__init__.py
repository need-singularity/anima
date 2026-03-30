"""⚠️ LEGACY W engines — use CompositeW instead"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from trinity import CosineW, ConstantW
__all__ = ['CosineW', 'ConstantW']
