# LeetCode-style grader: runs your current implementations against the full
# correctness + performance suites.
#
#   uv run grade                     # all problems
#   uv run grade monaco/kv_store.py  # one problem (problem file or test file path)
#   uv run grade monaco              # one company's set (folder name)
#   uv run grade --reveal monaco/p4  # print the suite's REFERENCE solution
#                                    # (the timebox off-ramp — after the timer)
#
# ✓ pass    ✗ bug or scaling failure    ⚠ concern worth having an answer for
#
# Suites are auto-discovered: every <company>/tests/test_*.py is picked up —
# nothing to register here. Address one problem by path (the problem file or
# its test file, `.py` optional) and a company's whole set by its folder name.
import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _load(path):
    name = f"{path.parts[-3]}_{path.stem}"          # e.g. monaco_test_kv_store
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def discover():
    suites, folders, aliases = {}, {}, {}
    for f in sorted(ROOT.glob("*/tests/test_*.py")):
        company, prob = f.parts[-3], f.stem.removeprefix("test_")
        name = f"{company}/{prob}"
        suites[name] = _load(f)
        folders.setdefault(company, []).append(name)
        aliases[name] = name
        aliases[f"{company}/tests/{f.stem}"] = name
        for src in (ROOT / company).glob("*.py"):    # e.g. monaco/p2_kv_store.py
            if re.sub(r"^p\d+_", "", src.stem) == prob:
                aliases[f"{company}/{src.stem}"] = name
    return suites, folders, aliases


def run(suites, names):
    results = [suites[n].main() for n in names]
    failed = sum(s.failed for s in results)
    warned = sum(s.warned for s in results)
    passed = sum(s.passed for s in results)
    skipped = sum(s.skipped for s in results)
    print("\n" + "=" * 70)
    verdict = "ACCEPTED" if failed == 0 else "WRONG ANSWER / TLE"
    print(f" {verdict}: {passed} passed, {failed} failed, "
          f"{warned} concern(s), {skipped} skipped")
    print("=" * 70)
    return 1 if failed else 0


def reveal(suites, names):
    """Print each suite's REFERENCE solution: the off-ramp once the timebox
    is up. Suites that predate the convention say so instead."""
    for n in names:
        ref = getattr(suites[n], "REFERENCE", None)
        print(f"\n== reference solution: {n} " + "=" * max(1, 42 - len(n)))
        print(ref.strip("\n") if ref else "  (no reference recorded for this suite yet)")
    print()
    return 0


def main(argv=None):
    suites, folders, aliases = discover()
    args = sys.argv[1:] if argv is None else argv
    revealing = "--reveal" in args
    args = [a for a in args if a != "--reveal"]
    if revealing and not args:
        print("usage: grade --reveal <problem path>   (prints that suite's reference solution)")
        sys.exit(2)
    if not args:
        names = list(suites)
    else:
        names = []
        for a in args:
            norm = a.removeprefix("./").rstrip("/").removesuffix(".py")
            matched = folders.get(norm) or ([aliases[norm]] if norm in aliases else None)
            if matched is None:
                options = ", ".join(list(folders) + list(suites))
                print(f"unknown problem {a!r} — use one of: {options}")
                sys.exit(2)
            names.extend(n for n in matched if n not in names)
    sys.exit(reveal(suites, names) if revealing else run(suites, names))


if __name__ == "__main__":
    main()
