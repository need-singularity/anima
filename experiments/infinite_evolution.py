#!/usr/bin/env python3
"""DEPRECATED — use anima/src/infinite_evolution.py instead.

This file was a simplified 242-line wrapper. The full version (5982 lines)
with --auto-roadmap, --resume, --cycle-topology, PatternRegistry,
cross-validation, and 13-stage roadmap lives in src/.

Usage:
    python3 anima/src/infinite_evolution.py --auto-roadmap --resume
"""
import sys
import os

print("⚠️  DEPRECATED: use anima/src/infinite_evolution.py instead")
print("   Redirecting...")
print()

# Forward to the real script
src_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'infinite_evolution.py')
os.execv(sys.executable, [sys.executable, src_path] + sys.argv[1:])
