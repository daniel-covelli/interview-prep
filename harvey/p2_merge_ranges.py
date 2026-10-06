"""
PROBLEM 2 — Merge Ranges
========================
Difficulty: warm-up | Timebox: 20 min (hard stop) |
Interview frequency: high (the core step of Harvey's highlight question)

CONTEXT
-------
Combine a pile of character ranges (say, the spots in a document that
matched a search) into the fewest ranges that cover the same characters.

SPEC
----
    merge_ranges(ranges: list[tuple[int, int]]) -> list[tuple[int, int]]

- Each range `(start, end)` covers `start` up to but NOT including
  `end`, with `start < end`. The input can be in any order.
- Ranges that overlap, or touch (one ends exactly where the next
  starts), become a single range.
- Return the merged ranges as tuples, in increasing order of `start`.

EXAMPLES
--------
    merge_ranges([(1, 3), (2, 6), (8, 10)])  -> [(1, 6), (8, 10)]
    merge_ranges([(5, 7), (1, 2)])           -> [(1, 2), (5, 7)]   # any input order
    merge_ranges([(1, 4), (4, 5)])           -> [(1, 5)]           # touching
    merge_ranges([(1, 3), (4, 5)])           -> [(1, 3), (4, 5)]   # 3 isn't covered
    merge_ranges([(1, 10), (2, 3)])          -> [(1, 10)]          # one inside another
    merge_ranges([])                         -> []

ASSUMPTIONS DECIDED HERE (rehearse asking them)
-----------------------------------------------
- Starts and ends are integers with 0 <= start < end <= 10**9.
- Up to 100,000 ranges; the same range may appear more than once.

TARGET COMPLEXITY
-----------------
O(n log n) for n ranges.
"""


def merge_ranges(ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    raise NotImplementedError
