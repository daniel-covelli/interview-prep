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
    finish_time(durations: dict[str, int], prereqs: list[tuple[str, str]]) -> int

- `durations` maps each task's name to how long it takes (always >= 1).
- ("a", "b") in prereqs means task "b" can't start until task "a" is
  finished.
- Any number of tasks may run at once. A task starts as soon as all of
  its prerequisites are finished (at time 0 if it has none).
- Return the time at which every task is finished (0 for no tasks), or
  -1 if the tasks can't all be finished because of circular
  prerequisites.

EXAMPLES
--------
    durations = {"design": 2, "setup": 1, "write": 3, "build": 2, "ship": 1}
    prereqs = [("setup", "build"), ("design", "ship"), ("setup", "ship"), ("write", "ship")]
    finish_time(durations, prereqs)                        -> 4
        # design runs 0-2, setup 0-1, write 0-3, build 1-3;
        # ship waits for its slowest prerequisite (write, done at 3) and runs 3-4

    finish_time({"a": 3, "b": 1}, [])                      -> 3     # both start at 0
    finish_time({}, [])                                    -> 0
    finish_time({"a": 1, "b": 1, "c": 1}, [("a", "b"), ("b", "c")])   -> 3   # a chain
    finish_time({"a": 1, "b": 1}, [("a", "b"), ("b", "a")])           -> -1
    finish_time({"a": 1}, [("a", "a")])                               -> -1

    # a cycle anywhere makes the whole project impossible
    finish_time({"a": 5, "b": 1, "c": 1}, [("b", "c"), ("c", "b")])   -> -1

ASSUMPTIONS DECIDED HERE (rehearse asking them)
-----------------------------------------------
- Every task named in `prereqs` is a key of `durations`.
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


def finish_time(durations: dict[str, int], prereqs: list[tuple[str, str]]) -> int:
    task_children = {task: [] for task in durations.keys()}
    dep_counts = {task: 0 for task in durations.keys()}
    task_start = {task: 0 for task in durations.keys()}

    for preq, task in prereqs:
        task_children[preq].append(task)
        dep_counts[task] += 1

    ready_tasks = [t for t, c in dep_counts.items() if c == 0]

    result = 0
    seen = 0

    while len(ready_tasks):
        task = ready_tasks.pop()

        task_end = task_start[task] + durations[task]
        for child in task_children[task]:
            dep_counts[child] -= 1
            task_start[child] = max(task_start[child], task_end)
            if dep_counts[child] == 0:
                ready_tasks.append(child)

        seen += 1
        result = max(result, task_end)

    if seen != len(durations):
        return -1

    return result

if __name__ == "__main__":
    from lib import run_test_cases, show

    durations = {"design": 2, "setup": 1, "write": 3, "build": 2, "ship": 1, "docs": 3}
    prereqs = [("setup", "build"), ("design", "ship"), ("setup", "ship"), ("write", "ship"), ("ship", "docs")]
    test_cases = [
        [
            (finish_time, (durations, prereqs), 7),
        ],
        [
            (finish_time, ({"a": 1, "b": 2}, [("a", "b"), ("b", "a")]), -1),
            (finish_time, ({"a": 1}, [("a", "a")]), -1)
        ]
        
    ]

    run_test_cases(test_cases)