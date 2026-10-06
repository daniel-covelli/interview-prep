# Grader for Harvey Problem 4 (harvey/p4_file_system.py).
# SPOILER WARNING: this file enumerates edge cases and contains a brute-force
# oracle and the reference solution. Run it, don't read it.
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from grader import (Suite, PerfConcern, load_class, bench, fmt_s, tracing,
                    expect, expect_set)

SEED = 0xF11E

# Reference solution, printed by `uv run grade --reveal harvey/p4_file_system`
# once the timebox is up. Never read it before then.
REFERENCE = '''
class FileSystem:
    def __init__(self) -> None:
        self.root = {}         # a folder: name -> sub-folder (dict) or file content (str)
        self.next_try = {}     # (folder path, name) -> first suffix not yet ruled out

    def _folder(self, parts, create):
        node = self.root
        for p in parts:
            if p not in node:
                if not create:
                    return None
                node[p] = {}
            node = node[p]
        return node if isinstance(node, dict) else None

    def add_file(self, path: str, content: str) -> str:
        *dirs, name = path.split("/")[1:]
        folder = self._folder(dirs, create=True)
        if name in folder:
            key = (tuple(dirs), name)
            k = self.next_try.get(key, 1)
            while f"{name}({k})" in folder:      # each k is ruled out at most once
                k += 1
            self.next_try[key] = k + 1
            name = f"{name}({k})"
        folder[name] = content
        return "/".join(["", *dirs, name])

    def get_file(self, path: str) -> str | None:
        *dirs, name = path.split("/")[1:]
        folder = self._folder(dirs, create=False)
        content = folder.get(name) if folder is not None else None
        return content if isinstance(content, str) else None

    def list_files(self, path: str) -> list[str]:
        parts = [p for p in path.split("/") if p]
        folder = self._folder(parts, create=False)
        out, todo = [], [("/".join(["", *parts]), folder)] if folder is not None else []
        while todo:
            prefix, node = todo.pop()
            for name, child in node.items():
                if isinstance(child, dict):
                    todo.append((f"{prefix}/{name}", child))
                else:
                    out.append(f"{prefix}/{name}")
        return out
'''


class Oracle:
    """Brute-force truth: one flat dict of full path -> content; suffixes
    found by counting up from 1; listing scans every stored path."""

    def __init__(self):
        self.files = {}

    def add_file(self, path, content):
        final, k = path, 1
        while final in self.files:
            final = f"{path}({k})"
            k += 1
        self.files[final] = content
        return final

    def get_file(self, path):
        return self.files.get(path)

    def list_files(self, path):
        prefix = path.rstrip("/") + "/"
        return [p for p in self.files if p.startswith(prefix)]

    def names_in(self, folder):
        """Names (files and sub-folders) directly inside `folder`."""
        prefix = folder.rstrip("/") + "/"
        return sorted({p[len(prefix):].split("/")[0] for p in self.files
                       if p.startswith(prefix)})


FOLDERS = ["", "/a", "/b", "/a/b", "/a/a"]
FOLDER_PATHS = ["/", "/a", "/b", "/a/b", "/a/a", "/c"]
NAMES = ["m", "n", "m(1)"]


def main():
    suite = Suite("Harvey 4: FileSystem")
    cls, err = load_class("harvey.p4_file_system", "FileSystem")
    if cls is None:
        suite.skip_all(err)
        return suite.summary()
    make = tracing(cls)

    suite.section("CORRECTNESS — PHASE 1 (add and get)")

    def spec_example():
        fs = make()
        expect(fs.add_file("/cases/acme/memo", "v1"), "/cases/acme/memo")
        expect(fs.add_file("/cases/acme/memo", "v2"), "/cases/acme/memo(1)")
        expect(fs.add_file("/cases/acme/memo", "v3"), "/cases/acme/memo(2)")
        expect(fs.add_file("/cases/beta/memo", "b1"), "/cases/beta/memo",
               note="a different folder: no clash")
        expect(fs.get_file("/cases/acme/memo(1)"), "v2")
        expect(fs.get_file("/cases/acme/memo(9)"), None)
        expect(fs.get_file("/nowhere/memo"), None)
        fs = make()
        expect(fs.add_file("/a", "x"), "/a")
        expect(fs.add_file("/a(1)", "y"), "/a(1)", note="an ordinary new name")
        expect(fs.add_file("/a", "z"), "/a(2)", note="a(1) is already taken")
        expect(fs.add_file("/a(1)", "w"), "/a(1)(1)")
    suite.case("spec example from the file header", spec_example)

    def get_returns_what_was_stored():
        fs = make()
        fs.add_file("/x/y/z/deep", "d")
        fs.add_file("/top", "t")
        fs.add_file("/x/y/z/deep", "d2")
        expect(fs.get_file("/x/y/z/deep"), "d", note="the first file keeps its name and content")
        expect(fs.get_file("/x/y/z/deep(1)"), "d2")
        expect(fs.get_file("/top"), "t", note="a file directly in the top-level folder")
        expect(fs.get_file("/x/y/z/other"), None, note="existing folder, missing file")
        expect(fs.get_file("/x/q/deep"), None, note="missing folder partway down")
        expect(fs.get_file("/topx"), None)
    suite.case("deep paths, top-level files, and misses", get_returns_what_was_stored)

    def suffixes_are_per_folder_and_name():
        fs = make()
        expect(fs.add_file("/f/memo", "1"), "/f/memo")
        expect(fs.add_file("/f/note", "2"), "/f/note")
        expect(fs.add_file("/f/memo", "3"), "/f/memo(1)")
        expect(fs.add_file("/f/note", "4"), "/f/note(1)",
               note="each name counts its own copies")
        expect(fs.add_file("/f/g/memo", "5"), "/f/g/memo",
               note="a sub-folder is a different folder")
        expect(fs.add_file("/g/memo", "6"), "/g/memo")
        expect(fs.add_file("/f/g/memo", "7"), "/f/g/memo(1)")
        expect(fs.add_file("/f/memo", "8"), "/f/memo(2)")
    suite.case("suffixes count per folder and per name", suffixes_are_per_folder_and_name)

    def suffix_skips_taken_numbers():
        fs = make()
        fs.add_file("/d/r", "a")
        fs.add_file("/d/r(1)", "b")
        fs.add_file("/d/r(2)", "c")
        fs.add_file("/d/r(4)", "d")
        expect(fs.add_file("/d/r", "e"), "/d/r(3)", note="r(1), r(2) taken; r(3) is free")
        expect(fs.add_file("/d/r", "f"), "/d/r(5)", note="r(4) taken too")
        expect(fs.add_file("/d/r(1)", "g"), "/d/r(1)(1)")
        expect(fs.add_file("/d/r(1)", "h"), "/d/r(1)(2)")
        fs.add_file("/d/r(7)", "i")
        expect(fs.add_file("/d/r", "j"), "/d/r(6)")
        expect(fs.add_file("/d/r", "k"), "/d/r(8)", note="r(7) was added by name")
        expect(fs.get_file("/d/r(3)"), "e")
        expect(fs.get_file("/d/r(1)(2)"), "h")
    suite.case("the suffix skips numbers already taken by name", suffix_skips_taken_numbers)

    def random_ops(rng, fs, o, n_ops, ctx, with_list):
        for op in range(n_ops):
            folder = rng.choice(FOLDERS)
            path = f"{folder}/{rng.choice(NAMES)}"
            roll = rng.random()
            if roll < 0.5:
                content = f"c{op}"
                taken = o.names_in(folder or "/")
                expect(fs.add_file(path, content), o.add_file(path, content),
                       note=f"{ctx}, op={op}; names already in {folder or '/'}: {taken}")
            elif roll < 0.8 or not with_list:
                if rng.random() < 0.3:
                    path += f"({rng.randrange(1, 4)})"
                expect(fs.get_file(path), o.get_file(path), note=f"{ctx}, op={op}")
            else:
                where = rng.choice(FOLDER_PATHS)
                expect_set(fs.list_files(where), o.list_files(where),
                           note=f"{ctx}, op={op}")

    def randomized_phase1():
        # many short rounds, fresh instance each: a failure replays every call
        for rnd in range(80):
            rng = random.Random(SEED + rnd)
            random_ops(rng, make(), Oracle(), 30, f"seed={SEED:#x}, round={rnd}",
                       with_list=False)
    suite.case("randomized: 80 rounds x 30 add/get ops vs a brute-force oracle",
               randomized_phase1)

    suite.section("CORRECTNESS — PHASE 2 (list a folder)")

    def p2_spec_example():
        fs = make()
        fs.add_file("/cases/acme/memo", "v1")
        fs.add_file("/cases/acme/memo", "v2")
        fs.add_file("/cases/acme/2024/brief", "b")
        fs.add_file("/notes", "n")
        expect_set(fs.list_files("/cases/acme"),
                   ["/cases/acme/memo", "/cases/acme/memo(1)", "/cases/acme/2024/brief"])
        expect_set(fs.list_files("/"), ["/cases/acme/memo", "/cases/acme/memo(1)",
                                        "/cases/acme/2024/brief", "/notes"])
        expect(fs.list_files("/missing"), [])
    suite.case("spec example from the file header", p2_spec_example)

    def listing_shapes():
        fs = make()
        expect(fs.list_files("/"), [], note="nothing stored yet")
        fs.add_file("/p/q/r/s", "1")
        expect_set(fs.list_files("/p"), ["/p/q/r/s"],
                   note="a folder holding only folders still lists the file deep inside")
        expect_set(fs.list_files("/p/q/r"), ["/p/q/r/s"])
        fs.add_file("/pq/t", "2")
        expect_set(fs.list_files("/p"), ["/p/q/r/s"],
                   note="/pq is a different folder from /p, not something inside it")
        expect(fs.list_files("/p/q/x"), [], note="missing folder under an existing one")
    suite.case("folders of folders, look-alike names, missing folders", listing_shapes)

    def randomized_phase2():
        for rnd in range(80):
            rng = random.Random(SEED + 1000 + rnd)
            random_ops(rng, make(), Oracle(), 30, f"seed={SEED:#x}, round={rnd}",
                       with_list=True)
    suite.case("randomized: 80 rounds x 30 add/get/list ops vs a brute-force oracle",
               randomized_phase2)

    if suite.failed or not suite.passed:
        suite.section("PERFORMANCE")
        reason = ("fix correctness failures first" if suite.failed
                  else "nothing implemented yet")
        suite.skip("all performance checks", reason)
        return suite.summary()

    suite.section("PERFORMANCE")

    def same_name(n):
        def run():
            for _ in range(8):                     # timing floor: >= ~10 ms
                fs = cls()
                for i in range(n):
                    fs.add_file("/inbox/memo", "x")
        return run

    def suffix_scaling():
        diagnosis = ("finding the suffix counts up from 1 every time, re-testing "
                     "every number already taken (n adds of one name = O(n²)). "
                     "Target: O(n) in total — each number is ruled out at most once.")
        try:
            t_small = bench(same_name(2_000), repeat=2, budget=5.0)
            t_big = bench(same_name(8_000), repeat=2, budget=5.0)
        except AssertionError as e:
            raise AssertionError(f"{diagnosis}  [{e}]") from None
        ratio = t_big / max(t_small, 1e-9)
        suite.info(f"8 x 2k adds of one name: {fmt_s(t_small)}   8 x 8k: "
                   f"{fmt_s(t_big)}   ratio {ratio:.1f}x (≈ 4x)")
        assert ratio < 10, f"4x the adds took {ratio:.1f}x longer — {diagnosis}"
    suite.case("adding one name n times costs O(n) in total", suffix_scaling)

    def small_listing(n_elsewhere, reps=6_000):
        # n files elsewhere plus a small folder of 10; the timed run lists
        # the small folder, each listing paired with a fixed-cost lookup
        fs = cls()
        for i in range(n_elsewhere):
            fs.add_file(f"/bulk/d{i % 100}/f{i}", "x")
        for i in range(10):
            fs.add_file(f"/small/s{i % 2}/f{i}", "x")

        def run():
            for _ in range(reps):
                fs.list_files("/small")
                fs.get_file("/small/s0/f0")
        return run

    def listing_independence():
        try:
            fs = cls()
            fs.add_file("/p/f", "x")
            fs.list_files("/p")
        except NotImplementedError:
            raise                                   # phase 2 not started: skip
        diagnosis = ("list_files looks at every file in the system (a scan of all "
                     "stored paths for a matching prefix?). Target: cost "
                     "proportional to what is inside the listed folder.")
        try:
            t_small = bench(small_listing(5_000), budget=5.0)
            t_big = bench(small_listing(80_000), budget=5.0)
        except AssertionError as e:
            raise AssertionError(f"{diagnosis}  [{e}]") from None
        ratio = t_big / max(t_small, 1e-9)
        suite.info(f"6k listings of a 10-file folder beside 5k other files: "
                   f"{fmt_s(t_small)}   beside 80k: {fmt_s(t_big)}   "
                   f"ratio {ratio:.1f}x (independent ≈ 1x)")
        assert ratio < 3, \
            f"16x more files elsewhere made the same listing {ratio:.1f}x slower — {diagnosis}"
    suite.case("list_files cost independent of files outside the folder",
               listing_independence)

    def note_followups():
        raise PerfConcern(
            "not machine-checkable: the DISCUSS AFTERWARDS tail. Rehearse deletes: "
            "whether a freed number should be reused (smallest free k means the "
            "remembered next-number can now be too high), what that costs, and "
            "whether users would expect reuse at all.")
    suite.case("deletes vs duplicate-numbering story", note_followups)

    return suite.summary()


if __name__ == "__main__":
    sys.exit(1 if main().failed else 0)
