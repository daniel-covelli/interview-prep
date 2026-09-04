# Package shim: put this folder on sys.path so problem files can use flat
# sibling imports (e.g. `from lib import ...`) whether they are imported by
# the grader as a package module or run directly as a script.
# New company folder? Copy this file in and everything is auto-discovered.
import sys as _sys
from pathlib import Path as _Path

_here = str(_Path(__file__).resolve().parent)
if _here not in _sys.path:
    _sys.path.append(_here)
