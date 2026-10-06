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
        self.files = {}          # stored path -> content
        self.copies = {}         # path as given to add_file -> how many times added

    def add_file(self, path: str, content: str) -> str:
        n = self.copies.get(path, 0)
        self.copies[path] = n + 1
        final = path if n == 0 else f"{path}({n})"
        self.files[final] = content
        return final

    def get_file(self, path: str) -> str | None:
        return self.files.get(path)

    def list_files(self, path: str) -> list[str]:
        prefix = path.rstrip("/") + "/"      # the "/" keeps /pq out of /p
        return [p for p in self.files if p.startswith(prefix)]
'''


class Oracle:
    """Brute-force truth: a plain list of (path, content) pairs; every
    question is answered by walking the whole list."""

    def __init__(self):
        self.files = []                          # (path, content), in add order

    def _taken(self, path):
        return any(p == path for p, _ in self.files)

    def add_file(self, path, content):
        final, k = path, 1
        while self._taken(final):
            final = f"{path}({k})"
            k += 1
        self.files.append((final, content))
        return final

    def get_file(self, path):
        return next((c for p, c in self.files if p == path), None)

    def list_files(self, path):
        prefix = path.rstrip("/") + "/"
        return [p for p, _ in self.files if p.startswith(prefix)]

    def names_in(self, folder):
        """Names (files and sub-folders) directly inside `folder`."""
        prefix = folder.rstrip("/") + "/"
        return sorted({p[len(prefix):].split("/")[0] for p, _ in self.files
                       if p.startswith(prefix)})


FOLDERS = ["", "/a", "/b", "/a/b", "/a/a"]
FOLDER_PATHS = ["/", "/a", "/b", "/a/b", "/a/a", "/c"]
NAMES = ["m", "n", "q"]


def main():
    suite = Suite("Harvey 4: FileSystem")
    cls, err = load_class("harvey.p4_file_system", "FileSystem")
    if cls is None:
        suite.skip_all(err)
        return suite.summary()
    make = tracing(cls)

    suite.section("CORRECTNESS")

    def spec_example():
        fs = make()
        expect(fs.add_file("/cases/acme/memo", "v1"), "/cases/acme/memo")
        expect(fs.add_file("/cases/acme/memo", "v2"), "/cases/acme/memo(1)")
        expect(fs.add_file("/cases/acme/memo", "v3"), "/cases/acme/memo(2)")
        expect(fs.add_file("/cases/beta/memo", "b1"), "/cases/beta/memo",
               note="a different folder: no clash")
        expect(fs.add_file("/notes", "n"), "/notes")
        expect(fs.get_file("/cases/acme/memo(1)"), "v2")
        expect(fs.get_file("/cases/acme/memo(9)"), None)
        acme = ["/cases/acme/memo", "/cases/acme/memo(1)", "/cases/acme/memo(2)"]
        expect_set(fs.list_files("/cases/acme"), acme)
        expect_set(fs.list_files("/cases"), acme + ["/cases/beta/memo"])
        expect_set(fs.list_files("/"), acme + ["/cases/beta/memo", "/notes"])
        expect(fs.list_files("/missing"), [])
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

    def random_ops(rng, fs, o, n_ops, ctx):
        for op in range(n_ops):
            folder = rng.choice(FOLDERS)
            path = f"{folder}/{rng.choice(NAMES)}"
            roll = rng.random()
            if roll < 0.5:
                content = f"c{op}"
                taken = o.names_in(folder or "/")
                expect(fs.add_file(path, content), o.add_file(path, content),
                       note=f"{ctx}, op={op}; files already in {folder or '/'}: {taken}")
            elif roll < 0.8:
                if rng.random() < 0.3:
                    path += f"({rng.randrange(1, 4)})"
                expect(fs.get_file(path), o.get_file(path), note=f"{ctx}, op={op}")
            else:
                where = rng.choice(FOLDER_PATHS)
                expect_set(fs.list_files(where), o.list_files(where),
                           note=f"{ctx}, op={op}")

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

    def randomized():
        # many short rounds, fresh instance each: a failure replays every call
        for rnd in range(120):
            rng = random.Random(SEED + rnd)
            random_ops(rng, make(), Oracle(), 30, f"seed={SEED:#x}, round={rnd}")
    suite.case("randomized: 120 rounds x 30 add/get/list ops vs a brute-force oracle",
               randomized)

    if suite.failed or not suite.passed:
        suite.section("PERFORMANCE")
        reason = ("fix correctness failures first" if suite.failed
                  else "nothing implemented yet")
        suite.skip("all performance checks", reason)
        return suite.summary()

    suite.section("PERFORMANCE")

    def many_files(n):
        # n distinct files across 100 folders, each read back once
        paths = [f"/d{i % 100}/f{i}" for i in range(n)]

        def run():
            for _ in range(8):                     # timing floor: >= ~10 ms
                fs = cls()
                for p in paths:
                    fs.add_file(p, "x")
                for p in paths:
                    fs.get_file(p)
        return run

    def scaling():
        diagnosis = ("add_file or get_file looks through the files stored so far "
                     "(paths kept in a list and searched?). Target: each call costs "
                     "about the same however many files exist.")
        try:
            t_small = bench(many_files(10_000), repeat=2, budget=5.0)
            t_big = bench(many_files(40_000), repeat=2, budget=5.0)
        except AssertionError as e:
            raise AssertionError(f"{diagnosis}  [{e}]") from None
        ratio = t_big / max(t_small, 1e-9)
        suite.info(f"8 x 10k adds + gets: {fmt_s(t_small)}   8 x 40k: {fmt_s(t_big)}   "
                   f"ratio {ratio:.1f}x (≈ 4x)")
        assert ratio < 10, f"4x the files took {ratio:.1f}x longer — {diagnosis}"
    suite.case("add/get cost doesn't grow with the number of files", scaling)

    def note_followups():
        raise PerfConcern(
            "not machine-checkable: the DISCUSS AFTERWARDS tail. Rehearse deletes: "
            "should a freed number be reused (the smallest-free rule says yes), and "
            "would users expect that? Also: what would listing a small folder cost "
            "in a system with millions of files, and how would you make it cheap?")
    suite.case("deletes vs duplicate-numbering story", note_followups)

    return suite.summary()


if __name__ == "__main__":
    sys.exit(1 if main().failed else 0)
