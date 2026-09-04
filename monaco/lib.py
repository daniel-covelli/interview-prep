# Pointer only — the real personal helpers live in ../prep_lib.py.
# Problem files write `from lib import run_test_cases`; this file makes that
# resolve both under the grader and when a problem file runs directly as a
# script. New company folder? Copy this file and __init__.py in verbatim.
import sys as _sys
from pathlib import Path as _Path

_root = str(_Path(__file__).resolve().parent.parent)
if _root not in _sys.path:
    _sys.path.append(_root)
from prep_lib import *  # noqa: E402,F401,F403
