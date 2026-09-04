#!/bin/sh
# One-time setup: create .venv (Python 3.13) with the repo root always
# importable, so `python run.py` and `python <company>/<problem>.py` both
# work after `source .venv/bin/activate`.
set -e
cd "$(dirname "$0")"
python3.13 -m venv .venv
pwd > "$(.venv/bin/python -c 'import site; print(site.getsitepackages()[0])')/interview_prep_root.pth"
echo "Done. Activate with: source .venv/bin/activate"
