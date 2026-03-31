"""D 디코더 — ConsciousDecoderV2 (canonical) + PostHocDecoder"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from decoder_v2 import ConsciousDecoderV2
from trinity import PostHocDecoder, CADecoder
__all__ = ['ConsciousDecoderV2', 'PostHocDecoder', 'CADecoder']
