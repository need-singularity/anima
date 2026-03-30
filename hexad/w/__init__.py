"""W 의지 — CompositeW(DaseinW+NarrativeW+EmotionW) (canonical)"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from trinity import CompositeW, DaseinW, NarrativeW, EmotionW
__all__ = ['CompositeW', 'DaseinW', 'NarrativeW', 'EmotionW']
