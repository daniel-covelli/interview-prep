"""
PROBLEM 3 — Onboarding Task Scheduler
=====================================
Difficulty: medium | Timebox: 45 min (hard stop) |
Interview frequency: medium (Rippling SDE loops, 2025)

CONTEXT
-------
A new hire's onboarding is a checklist of tasks — provision the laptop,
create accounts, enroll in payroll, ship the welcome kit — each with a
duration in days, some of which can't start until others finish.
Every task starts the moment its prerequisites are done (different
teams work in parallel), so a plan's length is not the sum of its
tasks. HR wants to know how many days onboarding takes and the order
in which the tasks will get finished.

SPEC
----
    schedule(
        tasks: list[tuple[str, int]],     # (task_id, duration in days), duration >= 1
        deps: list[tuple[str, str]],      # (before, after): `after` can't start until `before` is finished
    ) -> tuple[int, list[str]]

- A task with no prerequisites starts on day 0. Every other task starts
  the moment the LAST of its prerequisites finishes, and finishes
  `duration` days later. Any number of tasks may run at the same time.
- Return `(total, order)`: `total` is the day the last task finishes
  (0 when there are no tasks), and `order` lists every task id by
  finish day, earliest first; tasks finishing on the same day are
  listed in ascending id order.
- If the prerequisites can never all be satisfied — some task must,
  directly or through others, finish before itself — raise
  `CycleError` (defined below) instead.

EXAMPLES
--------
    tasks = [("laptop", 2), ("accounts", 1), ("badge", 3), ("payroll", 2), ("welcome", 1)]
    deps = [("accounts", "payroll"), ("laptop", "welcome"),
            ("accounts", "welcome"), ("badge", "welcome")]
    schedule(tasks, deps)
    -> (4, ["accounts", "laptop", "badge", "payroll", "welcome"])
       # accounts 0-1, laptop 0-2, badge 0-3, payroll 1-3, welcome 3-4;
       # badge and payroll both finish on day 3: ascending id order

    schedule([("a", 3), ("b", 1)], [])              -> (3, ["b", "a"])   # no prerequisites: all start on day 0
    schedule([], [])                                -> (0, [])
    schedule([("a", 1), ("b", 1), ("c", 1)],
             [("a", "b"), ("b", "c"), ("a", "b")])  -> (3, ["a", "b", "c"])   # a repeated pair changes nothing
    schedule([("a", 1), ("b", 1)], [("a", "b"), ("b", "a")])   -> raises CycleError
    schedule([("a", 1)], [("a", "a")])                          -> raises CycleError

    # tricky: the longest chain sets the total, not the biggest task
    schedule([("a", 1), ("b", 1), ("c", 1), ("big", 2)],
             [("a", "b"), ("b", "c")])              -> (3, ["a", "b", "big", "c"])
       # a 0-1, b 1-2, big 0-2, c 2-3: b and big both finish on day 2

ASSUMPTIONS DECIDED HERE (rehearse asking them)
-----------------------------------------------
- Task ids are unique, non-empty strings, ordered as plain strings
  ("t10" comes before "t2"); every id in `deps` appears in `tasks`.
  `deps` may contain the same pair more than once.
- Durations are positive integers (days). Nothing is fractional.
- Inputs can be large: up to 100,000 tasks, and a chain of
  prerequisites can be thousands of tasks long.
- Only the finish ORDER is reported, not start days; the caller does
  not need per-task times.

DISCUSS AFTERWARDS
------------------
- Only three people are available, so at most three tasks can run at
  once. Before coding anything: what has to be decided about which
  ready task goes first, and does the finish-order tie-break still make
  sense?
- Which tasks would you tell HR to speed up to shorten onboarding — how
  do you find them, and what happens after you shorten one?

TARGET COMPLEXITY
-----------------
O((T + D) log T) for T tasks and D dependencies — one pass over the
dependencies plus the final ordering. Each task's finish day must be
computed once: re-deriving it for every path that leads there fails the
perf check, and so does re-scanning all tasks to find the next ready one.
"""


class CycleError(Exception):
    """Raised by `schedule` when the dependencies contain a cycle."""


def schedule(tasks: list[tuple[str, int]], deps: list[tuple[str, str]]) -> tuple[int, list[str]]:
    raise NotImplementedError
