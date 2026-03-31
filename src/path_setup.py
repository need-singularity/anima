"""Add all source directories to sys.path for import compatibility."""
import sys
import os

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_dirs = ['src', 'benchmarks', 'training', 'tests', 'config', 'engines',
         'measurement', 'tools', 'experiments']

for d in _dirs:
    p = os.path.join(_root, d)
    if p not in sys.path and os.path.isdir(p):
        sys.path.insert(0, p)

# Root itself for legacy imports
if _root not in sys.path:
    sys.path.insert(0, _root)
