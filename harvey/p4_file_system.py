"""
PROBLEM 4 — In-Memory File System
=================================
Difficulty: medium | Timebox: 45 min (hard stop) |
Interview frequency: high (Harvey phone screens and onsites, 2025–2026)

CONTEXT
-------
Store files by absolute path, give a duplicate the next free numbered
name instead of overwriting, and list everything inside a folder.

SPEC
----
    fs = FileSystem()
    fs.add_file(path: str, content: str) -> str
    fs.get_file(path: str) -> str | None
    fs.list_files(path: str) -> list[str]

- Paths are absolute: "/" followed by names joined by "/"
  ("/cases/acme/memo"). The last name is the file; the ones before it
  are its folders, which exist as soon as a file is added inside them.
- Adding a name that already exists in the folder never overwrites:
  the second file called `name` there is stored as `name(1)`, the third
  as `name(2)`, and so on. `add_file` returns the path the file was
  actually stored under.
- `get_file` returns the content stored at `path`, or None if there is
  no file there.
- `list_files` returns the full path of every file inside the folder at
  `path`, at any depth, in any order. "/" is the top-level folder; a
  folder that doesn't exist gives [].

EXAMPLES
--------
    fs = FileSystem()
    fs.add_file("/cases/acme/memo", "v1")    -> "/cases/acme/memo"
    fs.add_file("/cases/acme/memo", "v2")    -> "/cases/acme/memo(1)"
    fs.add_file("/cases/acme/memo", "v3")    -> "/cases/acme/memo(2)"
    fs.add_file("/cases/beta/memo", "b1")    -> "/cases/beta/memo"    # other folder
    fs.add_file("/notes", "n")               -> "/notes"
    fs.get_file("/cases/acme/memo(1)")       -> "v2"
    fs.get_file("/cases/acme/memo(9)")       -> None
    fs.list_files("/cases/acme")
        -> ["/cases/acme/memo", "/cases/acme/memo(1)", "/cases/acme/memo(2)"]  # any order
    fs.list_files("/cases")    -> the four files under /cases, any order
    fs.list_files("/")         -> all five files, any order
    fs.list_files("/missing")  -> []

ASSUMPTIONS DECIDED HERE (rehearse asking them)
-----------------------------------------------
- Paths are well-formed: no trailing "/", no empty names, no "." or
  "..". Names never contain "/".
- `add_file` is only ever given a file's plain path, never a numbered
  copy like "/cases/acme/memo(1)".
- Folder names and file names never collide: no folder is ever called
  `memo` or `memo(1)` where a file `memo` lives.
- No delete or rename. Single process, single thread.

DISCUSS AFTERWARDS
------------------
- Files can now be deleted. Does the duplicate naming need to change,
  and what should happen to the numbers that free up?

TARGET COMPLEXITY
-----------------
`add_file` and `get_file` must not slow down as the total number of
files grows. `list_files` may look at every file.
"""
from typing import Union

class FileSystem:
    def __init__(self) -> None:
        self.index: dict[tuple, dict[Union[int, str], Union[str, int]]] = {} # { (cases, acme, memo) : {count: 0, 0: v1, 1: v2, ...}, ...}

    def add_file(self, path: str, content: str) -> str:
        p_parts = tuple(path[1:].split("/"))

        if p_parts not in self.index:
            self.index[p_parts] = {"count": 1, 0: content}
            return path

        count = self.index[p_parts]["count"]
        self.index[p_parts]["count"] += 1
        self.index[p_parts][count] = content
        
        return f'{path}({count})'

    def get_file(self, path: str) -> str | None:
        if not path.endswith(")"):
            p_parts = tuple(path[1:].split("/"))
            if p_parts not in self.index: return None
            return self.index[p_parts][0]

        left, right = path[1:].rsplit("(")

        path_index = int(right.replace(")", "")) 
        p_parts = tuple(left.split("/"))

        if p_parts not in self.index: return None
        if path_index not in self.index[p_parts]: return None
        

        return self.index[p_parts][path_index]

    def list_files(self, path: str) -> list[str]:
        results = []

        p_parts = tuple(path[1:].split("/"))
        for key, value in self.index.items():
            if tuple(key[:len(p_parts)]) != p_parts and path != "/": continue

            key_str = "/" + "/".join(key)

            results += [key_str if i == 0 else f'{key_str}({i})' for i in range(value["count"])]
            
        return results    


fs = FileSystem()
r1 =  fs.add_file("/cases/acme/memo", "v1")
print(f'R1 {r1}')
r2 =  fs.add_file("/cases/acme/memo", "v1")
print(f'r2 {r2}')

r3 = fs.list_files("/cases/acme")
print(f'r3 {r3}')

r4 = fs.get_file("/cases/acme/memo(1)")
print(f'r4 {r4}')