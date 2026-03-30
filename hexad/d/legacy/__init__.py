"""⚠️ LEGACY D decoders — use ConsciousDecoderV2 instead"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from trinity import TransformerDecoder, MLPDecoder, HFDecoder
from conscious_lm import ConsciousLM
__all__ = ['TransformerDecoder', 'MLPDecoder', 'HFDecoder', 'ConsciousLM']
