"""
PROBLEM 3 — Finish Time With Prerequisites
==========================================
Difficulty: medium | Timebox: 45 min (hard stop) |
Interview frequency: medium (Rippling SDE loops, 2025)

CONTEXT
-------
A project is a set of tasks, some of which can't start until others are
done. How long does the whole project take?

SPEC
----
    finish_time(durations: list[int], prereqs: list[tuple[int, int]]) -> int

- There are n = len(durations) tasks, numbered 0 to n - 1; task i takes
  durations[i] time units (always >= 1).
- (a, b) in prereqs means task b can't start until task a is finished.
- Any number of tasks may run at once. A task starts as soon as all of
  its prerequisites are finished (at time 0 if it has none).
- Return the time at which every task is finished (0 for no tasks), or
  -1 if the tasks can't all be finished because of circular
  prerequisites.

EXAMPLES
--------
    finish_time([2, 1, 3, 2, 1], [(1, 3), (0, 4), (1, 4), (2, 4)])   -> 4
        # 0 runs 0-2, 1 runs 0-1, 2 runs 0-3, 3 runs 1-3;
        # 4 waits for its slowest prerequisite (2, done at 3) and runs 3-4

    finish_time([3, 1], [])                       -> 3     # both start at 0
    finish_time([], [])                           -> 0
    finish_time([1, 1, 1], [(0, 1), (1, 2)])      -> 3     # a chain runs one after another
    finish_time([1, 1], [(0, 1), (1, 0)])         -> -1
    finish_time([1], [(0, 0)])                    -> -1

    # a cycle anywhere makes the whole project impossible
    finish_time([5, 1, 1], [(1, 2), (2, 1)])      -> -1

ASSUMPTIONS DECIDED HERE (rehearse asking them)
-----------------------------------------------
- Every task number in `prereqs` is between 0 and n - 1.
- Durations are positive integers.
- Up to 100,000 tasks, with a few prerequisites each.

DISCUSS AFTERWARDS
------------------
- Only three tasks can run at once. What has to be decided about which
  ready task starts first, and does the answer still have one right value?
- Which tasks would you speed up to finish the project sooner, and what
  happens after you speed one up?

TARGET COMPLEXITY
-----------------
O(n + p) for n tasks and p prerequisite pairs. Each task's finish time
must be computed once: recomputing it along every path that leads to the
task fails the perf check.
"""


def finish_time(durations: list[int], prereqs: list[tuple[int, int]]) -> int:
    raise NotImplementedError
