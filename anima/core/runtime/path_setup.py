"""Add all source directories to sys.path for flat-import compatibility.

After Phase 1+4a folder reshuffle, sources are spread across repo-root
(core/, models/, training/, bench/, experiments/, agent/, body/, eeg/,
physics/, serving/) and anima/ package subdirs.
"""
import sys
import os

_this = os.path.abspath(__file__)
# .../anima/core/runtime/path_setup.py -> anima pkg is 3 levels up
_anima_pkg = os.path.dirname(os.path.dirname(os.path.dirname(_this)))
_repo = os.path.dirname(_anima_pkg)

_candidates = [
    _repo,
    os.path.join(_repo, 'core'),
    os.path.join(_repo, 'models'),
    os.path.join(_repo, 'training'),
    os.path.join(_repo, 'bench'),
    os.path.join(_repo, 'experiments'),
    os.path.join(_repo, 'tests'),
    os.path.join(_repo, 'agent'),
    os.path.join(_repo, 'body'),
    os.path.join(_repo, 'eeg'),
    os.path.join(_repo, 'physics'),
    os.path.join(_repo, 'serving'),
    os.path.join(_repo, 'scripts'),
    _anima_pkg,
    os.path.join(_anima_pkg, 'src'),
    os.path.join(_anima_pkg, 'core'),
    os.path.join(_anima_pkg, 'core', 'runtime'),
    os.path.join(_anima_pkg, 'models'),
    os.path.join(_anima_pkg, 'models', 'legacy'),
    os.path.join(_anima_pkg, 'experiments'),
    os.path.join(_anima_pkg, 'experiments', 'consciousness'),
    os.path.join(_anima_pkg, 'experiments', 'evolution'),
    os.path.join(_anima_pkg, 'tools'),
    os.path.join(_anima_pkg, 'tools', 'misc'),
    os.path.join(_anima_pkg, 'engines'),
    os.path.join(_anima_pkg, 'measurement'),
    os.path.join(_anima_pkg, 'hexad'),
    os.path.join(_anima_pkg, 'config'),
    os.path.join(_anima_pkg, 'tests'),
    # Split targets — 8 runtime files moved from core/runtime/ (2026-04-10)
    os.path.join(_anima_pkg, 'modules', 'legacy'),
    os.path.join(_anima_pkg, 'modules', 'logging'),
    os.path.join(_anima_pkg, 'modules', 'monitor'),
    os.path.join(_anima_pkg, 'modules', 'education'),
    os.path.join(_anima_pkg, 'modules', 'training'),
    os.path.join(_anima_pkg, 'modules', 'cloud'),
    os.path.join(_anima_pkg, 'modules', 'learning'),
    os.path.join(_anima_pkg, 'modules', 'sync'),
]

for _p in _candidates:
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)
