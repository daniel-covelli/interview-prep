"""
PROBLEM 1 — Spreadsheet Formulas
================================
Difficulty: medium-hard | Timebox: 75 min (hard stop) — phase 1 by minute 20; phase 2 is the hard part |
Interview frequency: very high (Harvey's most-reported coding question, 2025–2026)

CONTEXT
-------
A tiny spreadsheet: each cell holds a number or a formula that adds up
other cells, and every read reflects the latest edits.

SPEC — PHASE 1 (numbers and formulas)
-------------------------------------
    sheet = Spreadsheet()
    sheet.set_cell(cell: str, text: str) -> None
    sheet.get_cell(cell: str) -> int

- Cell names are uppercase letters followed by digits ("A1", "B12").
- `text` is either a non-negative integer ("7") or a formula: "="
  followed by one or more terms joined by "+", each term a cell name or
  a non-negative integer ("=A1+B2+3"). No spaces.
- `get_cell` returns the cell's current value: its number, or the sum of
  its formula's terms using the referenced cells' CURRENT values. A cell
  that was never set reads 0.
- `set_cell` replaces whatever the cell held before. Every cell that
  depends on it, directly or through other cells, reflects the change.

Examples:
    sheet = Spreadsheet()
    sheet.set_cell("A1", "5")
    sheet.set_cell("B1", "=A1+2")
    sheet.get_cell("B1")   -> 7
    sheet.set_cell("C1", "=A1+B1+A1")
    sheet.get_cell("C1")   -> 17      # 5 + 7 + 5: a cell may appear twice
    sheet.set_cell("A1", "10")
    sheet.get_cell("B1")   -> 12
    sheet.get_cell("C1")   -> 32      # A1 changed it directly and through B1
    sheet.get_cell("Z9")   -> 0       # never set
    sheet.set_cell("D1", "=E1+1")     # E1 isn't set yet: it reads 0
    sheet.get_cell("D1")   -> 1
    sheet.set_cell("E1", "=A1")
    sheet.get_cell("D1")   -> 11
    sheet.set_cell("B1", "4")         # a formula cell can become a plain number
    sheet.get_cell("C1")   -> 24

SPEC — PHASE 2 (reject circular formulas)
-----------------------------------------
    class CycleError(Exception)       # already defined below

- If storing `text` in `cell` would make any cell's value depend on
  itself (directly or through other cells), `set_cell` raises
  `CycleError` and changes nothing: every cell keeps its previous
  contents.

Examples:
    sheet = Spreadsheet()
    sheet.set_cell("A1", "=B1+1")
    sheet.set_cell("B1", "=A1")       -> raises CycleError   # A1 -> B1 -> A1
    sheet.get_cell("B1")   -> 0       # still never set
    sheet.set_cell("C1", "=C1+1")     -> raises CycleError   # refers to itself
    sheet.set_cell("B1", "=C1+2")     # fine: C1 is unset, no loop
    sheet.get_cell("A1")   -> 3
    sheet.set_cell("C1", "=A1")       -> raises CycleError   # C1 -> A1 -> B1 -> C1
    sheet.set_cell("B1", "4")
    sheet.set_cell("C1", "=A1")       # B1 no longer reads C1: fine now
    sheet.get_cell("C1")   -> 5

ASSUMPTIONS DECIDED HERE (rehearse asking them)
-----------------------------------------------
- `text` is always well-formed as described above.
- Up to 100,000 cells; a formula has a handful of terms; formulas chain
  at most a few hundred cells deep.
- No delete operation. Single process, single thread.

DISCUSS AFTERWARDS
------------------
- Reads recompute everything below the cell. What would it take to
  make `get_cell` O(1), and what does that cost on every `set_cell`?

TARGET COMPLEXITY
-----------------
- `set_cell`: its cost depends only on the cells connected to `cell`
  through formulas, never on the rest of the sheet: 100,000 unrelated
  cells must not slow it down.
- `get_cell` may recompute the value on every read.
"""
class CycleError(Exception):
    pass


def is_integer(val):
    try:
        int(val)
        return True
    except ValueError:
        return False

class Spreadsheet:
    def __init__(self) -> None:
        self.cell_vals = {}

    def _dfs_check(self, cell: str, seen: set) -> None:
        if cell in seen:
            raise CycleError()

        if cell not in self.cell_vals:
            return

        if is_integer(self.cell_vals[cell]):
            return

        for x in list(set(x for x in self.cell_vals[cell][1:].split("+") if not is_integer(x))):
            self._dfs_check(x, seen | {cell})
        

    def set_cell(self, cell: str, text: str) -> None:
        if text[0] != "=":
            self.cell_vals[cell] = text
            return

        old = None if cell not in self.cell_vals else self.cell_vals[cell]
        self.cell_vals[cell] = text

        try:
          self._dfs_check(cell, set())
          return
        except CycleError:
          if old is None:
              del self.cell_vals[cell]
          else:
            self.cell_vals[cell] = old
          raise CycleError()

    def get_cell(self, cell: str) -> int:
        if cell not in self.cell_vals:
            return 0

        if self.cell_vals[cell][0] != "=":
            return int(self.cell_vals[cell])

        total = 0
        cache = {}
        for elm in self.cell_vals[cell].split("+"):
             elm = elm if elm[0] != "=" else elm[1:]
             if elm in cache:
                 total += cache[elm]
                 continue

             if not is_integer(elm):
                 value = self.get_cell(elm)
                 cache[elm] = value
             else:
                 value = int(elm)

             total += value

        return total

        

        
if __name__ == "__main__":
    from lib import run_test_cases, show

    test_cases = [
        [
            (Spreadsheet),
            ("set_cell", ("A1", "5"), None),
            ("set_cell", ("B1", "=A1+2"), None),
            ("get_cell", ("B1"), 7),
            ("set_cell", ("C1", "=A1+B1+A1"), None),
            ("get_cell", ("C1"), 17),
            ("set_cell", ("A1", "10"), None),
            ("get_cell", ("B1"), 12),
            ("get_cell", ("C1"), 32),
            ("get_cell", ("Z9"), 0),
            ("set_cell", ("D1", "=E1+1"), None),
            ("get_cell", ("D1"), 1),
        ],
        [
            (Spreadsheet),
            ("set_cell", ("A1", "=B1+1"), None),
            ("set_cell", ("B1", "=A1"), CycleError),
            ("get_cell", ("B1"), 0),
            ("set_cell", ("C1", "=C1+1"), CycleError),
            ("set_cell", ("B1", "=C1+2"), None),
            ("get_cell", ("A1"), 3),
            ("set_cell", ("C1", "=A1"), CycleError),
        ]
    ]

    run_test_cases(test_cases)