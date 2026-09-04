# LeetCode-style grader: runs your current implementations against the full
# correctness + performance suites.
#
#   uv run grade                    # all problems
#   uv run grade m1                 # just one
#   uv run grade monaco             # one company's set (folder name or key prefix)
#
# ✓ pass    ✗ bug or scaling failure    ⚠ concern worth having an answer for
#
# Suites are auto-discovered: every <company>/tests/test_*.py that declares a
# KEY (e.g. KEY = "m5") is picked up — nothing to register here. A company's
# whole set runs via its folder name or the key's letter prefix.
import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def _load(path):
    name = f"{path.parts[-3]}_{path.stem}"          # e.g. monaco_test_kv_store
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def discover():
    problems, folders = {}, {}
    for f in sorted(ROOT.glob("*/tests/test_*.py")):
        mod = _load(f)
        key = getattr(mod, "KEY", None)
        if key is None:
            print(f'warning: {f} has no KEY = "..." declaration — skipping it')
            continue
        if key in problems:
            print(f"error: KEY {key!r} declared by two test files")
            sys.exit(2)
        problems[key] = mod
        folders.setdefault(f.parts[-3], []).append(key)

    def sort_key(k):
        m = re.fullmatch(r"([a-z]+)(\d+)", k)
        return (m.group(1), int(m.group(2))) if m else (k, 0)

    problems = dict(sorted(problems.items(), key=lambda kv: sort_key(kv[0])))
    groups = {co: sorted(ks, key=sort_key) for co, ks in folders.items()}
    for k in problems:                               # "m" works like "monaco"
        groups.setdefault(k.rstrip("0123456789"), []).append(k)
    return problems, groups


def run(problems, keys):
    suites = [problems[k].main() for k in keys]
    failed = sum(s.failed for s in suites)
    warned = sum(s.warned for s in suites)
    passed = sum(s.passed for s in suites)
    skipped = sum(s.skipped for s in suites)
    print("\n" + "=" * 70)
    verdict = "ACCEPTED" if failed == 0 else "WRONG ANSWER / TLE"
    print(f" {verdict}: {passed} passed, {failed} failed, "
          f"{warned} concern(s), {skipped} skipped")
    print("=" * 70)
    return 1 if failed else 0


def cli(argv=None):
    problems, groups = discover()
    args = sys.argv[1:] if argv is None else argv
    if not args:
        keys = list(problems)
    else:
        keys = []
        for a in args:
            matched = groups.get(a, [a] if a in problems else None)
            if matched is None:
                options = ", ".join(list(problems) + list(groups))
                print(f"unknown problem {a!r} — use one of: {options}")
                sys.exit(2)
            keys.extend(k for k in matched if k not in keys)
    sys.exit(run(problems, keys))


if __name__ == "__main__":
    cli()
