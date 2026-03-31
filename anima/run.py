#!/usr/bin/env python3
"""Anima entry point — forwards to src/anima_unified.py."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
import path_setup  # noqa
from anima_unified import main
main()
