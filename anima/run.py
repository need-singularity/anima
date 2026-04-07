#!/usr/bin/env python3
"""Anima entry point — forwards to anima_unified (moved to core/runtime/)."""
import sys, os
_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_here, 'core', 'runtime'))
import path_setup  # noqa: F401  (sets up all sys.path entries)
from anima_unified import main
main()
