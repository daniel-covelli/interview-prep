"""
PROBLEM 4 — Group Meeting Scheduler
===================================
Difficulty: medium | Timebox: 40 min | Interview frequency: very high —
and Monaco's product literally schedules meetings.

CONTEXT
-------
Given several attendees' existing calendars, find times when everyone
can meet. All times are integer minutes from an arbitrary epoch
(no datetimes, no time zones — say out loud that you're glad about that).

SPEC
----
    find_slots(
        busy: list[list[tuple[int, int]]],   # busy[i] = attendee i's busy intervals
        duration: int,                        # required meeting length, minutes
        window: tuple[int, int],              # search only inside [start, end)
    ) -> list[tuple[int, int]]

- Each busy interval is half-open [start, end), start < end. An
  attendee's own list may be unsorted AND may contain overlapping
  intervals (double-booking happens).
- Return ALL maximal free gaps within `window` where every attendee is
  free for at least `duration` contiguous minutes. Return the full gap
  (e.g. a 90-min gap for a 30-min request is returned once as the whole
  gap, not as many 30-min slots), sorted ascending.
- Back-to-back busy intervals ([60,90) then [90,120)) leave no gap:
  meetings may start exactly when a busy block ends.

EXAMPLE
-------
    busy = [
        [(0, 30), (90, 120)],              # attendee 0
        [(45, 60), (45, 55)],              # attendee 1 (overlapping entries)
    ]
    find_slots(busy, duration=15, window=(0, 150))
    -> [(30, 45), (60, 90), (120, 150)]
    find_slots(busy, duration=45, window=(0, 150))
    -> []                                   # longest gap is 30 minutes
    find_slots(busy, duration=30, window=(0, 150))
    -> [(60, 90), (120, 150)]

ASSUMPTIONS DECIDED HERE (rehearse asking them)
-----------------------------------------------
- Half-open intervals everywhere; touching ≠ overlapping.
- An attendee with an empty busy list is free for the whole window.
- Busy time outside `window` still matters only where it intersects the
  window (clip it).

EXTENSIONS
----------
1. `first_slot(...) -> tuple[int, int] | None` — earliest valid
   [start, start+duration); can you beat recomputing everything?
2. Optional attendees: meeting is valid if all required + at least K of
   the optional attendees are free. Return slots with the attending set.
3. Working hours: each attendee also has a daily availability mask
   (e.g. free only within [540, 1020) each 1440-min day, across a
   multi-day window). Fold it in without special-casing.
4. Discuss only: attendees' calendars live in different services and
   each fetch is a slow network call. How does the algorithm change?

TARGET COMPLEXITY
-----------------
O(m log m) where m = total busy intervals (flatten, sort, merge, walk gaps).
"""


def find_slots(
    busy: list[list[tuple[int, int]]],
    duration: int,
    window: tuple[int, int],
) -> list[tuple[int, int]]:
    raise NotImplementedError


if __name__ == "__main__":
    import sys

    results: list[bool] = []

    def check(label: str, actual: object, expected: object) -> None:
        ok = actual == expected
        results.append(ok)
        print(f"{'PASS' if ok else 'FAIL'}  {label}  (got {actual!r}, want {expected!r})")

    def scenario(name: str, fn) -> None:
        try:
            fn()
        except NotImplementedError:
            print(f"SKIP  {name}: not implemented yet")

    def docstring_example() -> None:
        busy = [
            [(0, 30), (90, 120)],
            [(45, 60), (45, 55)],
        ]
        check("duration=15", find_slots(busy, duration=15, window=(0, 150)),
              [(30, 45), (60, 90), (120, 150)])
        check("duration=45", find_slots(busy, duration=45, window=(0, 150)), [])
        check("duration=30", find_slots(busy, duration=30, window=(0, 150)),
              [(60, 90), (120, 150)])

    scenario("docstring example", docstring_example)

    if not results:
        print("\nNothing checked yet — implement the stubs, then re-run.")
        sys.exit(1)
    print(f"\n{sum(results)}/{len(results)} checks passed.")
    sys.exit(0 if all(results) else 1)
