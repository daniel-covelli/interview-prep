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
    -> [(60, 90), (120, 150)]               # (60, 90) fits duration exactly
    find_slots([[], []], duration=10, window=(5, 20))
    -> [(5, 20)]                            # empty calendars: whole window free
    find_slots([[(0, 200)]], duration=1, window=(50, 150))
    -> []                                   # busy outside the window still clips it

ASSUMPTIONS DECIDED HERE (rehearse asking them)
-----------------------------------------------
- Half-open intervals everywhere; touching ≠ overlapping.
- An attendee with an empty busy list is free for the whole window.
- Busy time outside `window` still matters only where it intersects the
  window (clip it).
- `duration` is at least 1; the window may be empty (start == end).

DISCUSS AFTERWARDS
------------------
- Optional attendees: meeting is valid if all required + at least K of
  the optional attendees are free. Deliberately underspecified — what
  would you pin down with the interviewer before coding it (does a gap
  split when the free optional set changes mid-gap? which K-subset is
  reported)?
- Working hours: each attendee also has a daily availability mask (e.g.
  free only within [540, 1020) each 1440-min day, across a multi-day
  window). How would you fold it in without special-casing?
- Attendees' calendars live in different services and each fetch is a
  slow network call. How does the algorithm change?

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
