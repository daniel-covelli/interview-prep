"""
PROBLEM 4 — Group Meeting Scheduler
===================================
Difficulty: medium | Timebox: 60 min (hard stop) | Interview frequency: very high —
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
O(m log m) where m = total busy intervals. The cost must not depend on
the window's length in minutes: a solution that visits every minute
fails the perf check, so design for that from the first line.
"""


def find_slots(
    busy: list[list[tuple[int, int]]],
    duration: int,
    window: tuple[int, int],
) -> list[tuple[int, int]]:

    availability = []
    if window[1] - window[0] < duration:
        return availability
    
    availability.append(window)

    flattened_busy = sorted([interval for user_intervals in busy for interval in user_intervals])

    busy_intervals = []

    candidate = None
    for i in range(len(flattened_busy)):
        s, e = flattened_busy[i]
        if s > window[1] or e < window[0]: continue
        if not candidate:
            candidate = ((window[0] if s <= window[0] else s, window[1] if e >= window[1] else e))
            continue
        c_s, c_e = candidate
        if s <= candidate[1]:
            candidate = (c_s, max(c_e, e))
        else: 
            busy_intervals.append((window[0] if c_s <= window[0] else c_s, window[1] if c_e >= window[1] else c_e))
            candidate = (s, e)
    if candidate:
      c_s, c_e = candidate
      busy_intervals.append((window[0] if c_s <= window[0] else c_s, window[1] if c_e >= window[1] else c_e))

    for busy_s, busy_e in busy_intervals:
        new_results = []
        for avail_s, avail_e in availability:
            if avail_s > busy_s and avail_e < busy_e: continue
            if avail_s > busy_s or avail_e < busy_e:
                if avail_e - avail_s >= duration: 
                    new_results.append((avail_s, avail_e))
                continue

            if busy_s - avail_s >= duration:
                new_results.append((avail_s, busy_s))
            if avail_e - busy_e >= duration:
                new_results.append((busy_e, avail_e))

              
        availability = new_results
            

    return availability
    


if __name__ == "__main__":
    from lib import run_test_cases, show

    busy = [[(15, 30), (90, 120)], [(45, 60), (45, 55)]]
    test_cases = [
        [
            (find_slots, (busy, 15, (0, 150)), [ (0, 15), (30, 45), (60, 90), (120, 150)]),
            (find_slots, (busy, 45, (0, 150)), []),
            (find_slots, (busy, 30, (0, 150)), [(60, 90), (120, 150)]),
            (find_slots, ([[], []], 10, (5, 20)), [(5, 20)]),
            (find_slots, ([[(0, 200)]], 1, (50, 150)), []),
        ],
        
    ]

    run_test_cases(test_cases)