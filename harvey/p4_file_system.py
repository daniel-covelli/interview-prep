"""
PROBLEM 4 — In-Memory File System
=================================
Difficulty: medium-hard | Timebox: 70 min (hard stop) — phase 1 by minute 45; phase 2 is the stretch |
Interview frequency: high (Harvey phone screens and onsites, 2025–2026)

CONTEXT
-------
Store files by absolute path, give a duplicate the next free numbered
name instead of overwriting, and list everything inside a folder.

SPEC — PHASE 1 (add and get)
----------------------------
    fs = FileSystem()
    fs.add_file(path: str, content: str) -> str
    fs.get_file(path: str) -> str | None

- Paths are absolute: "/" followed by names joined by "/"
  ("/cases/acme/memo"). The last name is the file; the ones before it are
  folders. `add_file` creates any missing folders along the way.
- If the folder already holds something called `name`, the file is
  stored as `name(k)` instead, for the smallest k >= 1 such that
  `name(k)` isn't taken in that folder. `add_file` returns the path the
  file was actually stored under.
- `get_file` returns the content stored at `path`, or None if there is
  no file there.

Examples:
    fs = FileSystem()
    fs.add_file("/cases/acme/memo", "v1")    -> "/cases/acme/memo"
    fs.add_file("/cases/acme/memo", "v2")    -> "/cases/acme/memo(1)"
    fs.add_file("/cases/acme/memo", "v3")    -> "/cases/acme/memo(2)"
    fs.add_file("/cases/beta/memo", "b1")    -> "/cases/beta/memo"    # other folder
    fs.get_file("/cases/acme/memo(1)")       -> "v2"
    fs.get_file("/cases/acme/memo(9)")       -> None
    fs.get_file("/nowhere/memo")             -> None

    fs = FileSystem()
    fs.add_file("/a", "x")                   -> "/a"
    fs.add_file("/a(1)", "y")                -> "/a(1)"     # an ordinary new name
    fs.add_file("/a", "z")                   -> "/a(2)"     # a(1) is taken
    fs.add_file("/a(1)", "w")                -> "/a(1)(1)"

SPEC — PHASE 2 (list a folder)
------------------------------
    fs.list_files(path: str) -> list[str]

- Return the full path of every file inside the folder at `path`, at any
  depth, in any order. "/" is the top-level folder. A folder that doesn't
  exist returns [].

Examples:
    fs = FileSystem()
    fs.add_file("/cases/acme/memo", "v1")
    fs.add_file("/cases/acme/memo", "v2")
    fs.add_file("/cases/acme/2024/brief", "b")
    fs.add_file("/notes", "n")
    fs.list_files("/cases/acme")
        -> ["/cases/acme/memo", "/cases/acme/memo(1)", "/cases/acme/2024/brief"]   # any order
    fs.list_files("/")         -> all four paths, any order
    fs.list_files("/missing")  -> []

ASSUMPTIONS DECIDED HERE (rehearse asking them)
-----------------------------------------------
- Paths are well-formed: no trailing "/", no empty names, no "." or
  "..". Names never contain "/".
- A path never runs through a file as if it were a folder, and a file is
  never added under a name that an existing folder already uses.
  `list_files` is only given folder paths (or paths that don't exist).
- No delete or rename. Single process, single thread.

DISCUSS AFTERWARDS
------------------
- Files can now be deleted. Does the duplicate naming need to change,
  and what should happen to the numbers that free up?

TARGET COMPLEXITY
-----------------
- `add_file` and `get_file`: proportional to the path's length. Adding
  the same name n times to one folder must cost O(n) in total, so
  finding the suffix must not re-test every number already taken.
- `list_files`: proportional to what is inside the folder being listed,
  never to how many files the whole system holds.
"""


class FileSystem:
    def __init__(self) -> None:
        raise NotImplementedError

    def add_file(self, path: str, content: str) -> str:
        raise NotImplementedError

    def get_file(self, path: str) -> str | None:
        raise NotImplementedError

    def list_files(self, path: str) -> list[str]:
        raise NotImplementedError
