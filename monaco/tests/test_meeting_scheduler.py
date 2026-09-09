# Grader for Monaco Problem 4 (monaco/p4_meeting_scheduler.py).
# SPOILER WARNING: this file enumerates edge cases and contains a brute-force
# oracle. Run it, don't read it.
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from grader import (Suite, PerfConcern, Failure, load_fn, bench, fmt_s,
                    expect, short)

SEED = 0x5107


def oracle_slots(busy, duration, window):
    """Brute-force truth: paint every busy minute in the window, then walk
    the maximal free runs and keep those >= duration."""
    lo, hi = window
    n = hi - lo
    free = [True] * n
    for cal in busy:
        for s, e in cal:
            for m in range(max(s, lo), min(e, hi)):
                free[m - lo] = False
    out = []
    i = 0
    while i < n:
        if free[i]:
            j = i
            while j < n and free[j]:
                j += 1
            if j - i >= duration:
                out.append((lo + i, lo + j))
            i = j
        else:
            i += 1
    return out


def check(find_slots, busy, duration, window, note=None, ctx=None):
    got = find_slots([list(cal) for cal in busy], duration, window)
    want = oracle_slots(busy, duration, window)
    if got != want:
        callrepr = f"find_slots({short(busy, 300)}, duration={duration}, window={window})"
        raise Failure(output=got, expected=want,
                      note=" ".join(filter(None, [note, callrepr,
                                                  f"[{ctx}]" if ctx else None])))


def main():
    suite = Suite("Monaco 4: find_slots")
    find_slots, err = load_fn("monaco.p4_meeting_scheduler", "find_slots")
    if find_slots is None:
        suite.skip_all(err)
        return suite.summary()

    suite.section("CORRECTNESS")

    def spec_example():
        busy = [
            [(0, 30), (90, 120)],
            [(45, 60), (45, 55)],
        ]
        expect(find_slots(busy, 15, (0, 150)), [(30, 45), (60, 90), (120, 150)])
        expect(find_slots(busy, 45, (0, 150)), [],
               note="the longest gap is 30 minutes")
        expect(find_slots(busy, 30, (0, 150)), [(60, 90), (120, 150)])
    suite.case("spec example from the file header", spec_example)

    def maximal_gaps():
        busy = [[(100, 110)]]
        expect(find_slots(busy, 30, (0, 250)), [(0, 100), (110, 250)],
               note="return each maximal gap ONCE, whole — not sliced into "
                    "30-minute slots")
    suite.case("gaps come back whole, not sliced into duration-sized slots", maximal_gaps)

    def empty_calendars():
        expect(find_slots([[]], 10, (0, 50)), [(0, 50)],
               note="an attendee with no meetings is free for the whole window")
        expect(find_slots([[], [], []], 60, (100, 160)), [(100, 160)],
               note="gap length exactly == duration still counts")
        expect(find_slots([[], []], 61, (100, 160)), [],
               note="duration longer than the whole window")
    suite.case("empty calendars; duration exactly / barely not fitting", empty_calendars)

    def back_to_back():
        busy = [[(60, 90)], [(90, 120)]]
        expect(find_slots(busy, 15, (0, 180)), [(0, 60), (120, 180)],
               note="[60,90) then [90,120) leave NO gap at 90 — but a meeting "
                    "may start exactly at 120, when the busy block ends")
        expect(find_slots([[(0, 30), (30, 60)]], 1, (0, 60)), [],
               note="back-to-back blocks covering the window leave nothing")
    suite.case("half-open touching intervals leave no gap", back_to_back)

    def unsorted_overlapping():
        busy = [[(80, 120), (10, 40), (30, 60), (100, 140), (10, 40)]]
        # merged busy: [10,60) and [80,140)
        expect(find_slots(busy, 10, (0, 160)), [(0, 10), (60, 80), (140, 160)],
               note="one attendee's list may be unsorted, overlapping, and "
                    "contain exact duplicates")
    suite.case("unsorted, overlapping, duplicated busy intervals", unsorted_overlapping)

    def clipping():
        busy = [[(-100, 20), (130, 500)]]
        expect(find_slots(busy, 10, (0, 150)), [(20, 130)],
               note="busy time is clipped to the window: only the parts "
                    "inside [0, 150) matter")
        expect(find_slots([[(500, 600)]], 10, (0, 100)), [(0, 100)],
               note="busy time entirely OUTSIDE the window is irrelevant")
        expect(find_slots([[(0, 300)]], 10, (100, 200)), [],
               note="one interval can swallow the whole window")
    suite.case("busy intervals straddling or outside the window are clipped", clipping)

    def window_edges():
        busy = [[(0, 30)]]
        expect(find_slots(busy, 30, (0, 60)), [(30, 60)],
               note="free run touching the window END is a valid gap")
        expect(find_slots([[(30, 60)]], 30, (0, 60)), [(0, 30)],
               note="free run starting at the window START is a valid gap")
        expect(find_slots([[]], 5, (40, 40)), [],
               note="empty window [40, 40) has no minutes at all")
    suite.case("gaps flush against window edges; empty window", window_edges)

    def many_attendees():
        busy = [
            [(0, 10), (50, 60)],
            [(20, 30)],
            [(35, 42)],
        ]
        # union busy: [0,10) [20,30) [35,42) [50,60): gaps 10-20, 30-35, 42-50, 60-90
        expect(find_slots(busy, 8, (0, 90)), [(10, 20), (42, 50), (60, 90)],
               note="every attendee must be free: gaps are the complement of "
                    "the UNION of all calendars")
        expect(find_slots(busy, 5, (0, 90)), [(10, 20), (30, 35), (42, 50), (60, 90)])
    suite.case("multiple attendees: intersection of everyone's free time", many_attendees)

    def randomized():
        rng = random.Random(SEED)
        for trial in range(250):
            n_att = rng.randrange(1, 5)
            busy = []
            for _ in range(n_att):
                cal = []
                for _ in range(rng.randrange(0, 12)):
                    s = rng.randrange(-50, 1_950)
                    cal.append((s, s + rng.randrange(1, 120)))
                busy.append(cal)
            duration = rng.randrange(1, 90)
            lo = rng.randrange(0, 1_000)
            window = (lo, lo + rng.randrange(1, 1_000))
            check(find_slots, busy, duration, window,
                  ctx=f"seed={SEED:#x}, trial={trial}")
    suite.case("randomized: 250 calendars cross-checked against minute-scan oracle",
               randomized)

    if suite.failed or not suite.passed:
        suite.section("PERFORMANCE")
        reason = ("fix correctness failures first" if suite.failed
                  else "nothing implemented yet")
        suite.skip("all performance checks", reason)
        return suite.summary()

    suite.section("PERFORMANCE")

    def gen_busy(n_intervals, span):
        rng = random.Random(SEED)
        per = n_intervals // 3
        return [[(s := rng.randrange(span), s + rng.randrange(5, 60))
                 for _ in range(per)] for _ in range(3)]

    def interval_scaling():
        small = gen_busy(4_000, 300_000)
        big = gen_busy(16_000, 1_200_000)
        t_small = bench(lambda: find_slots(small, 30, (0, 300_000)), repeat=2)
        t_big = bench(lambda: find_slots(big, 30, (0, 1_200_000)), repeat=2)
        ratio = t_big / max(t_small, 1e-9)
        suite.info(f"4k intervals: {fmt_s(t_small)}   16k intervals: {fmt_s(t_big)}   "
                   f"ratio {ratio:.1f}x (m log m ≈ 4-5x)")
        assert ratio < 10, \
            (f"4x more busy intervals took {ratio:.1f}x longer — are intervals "
             f"being compared pairwise? Target: flatten + sort + sweep, "
             f"O(m log m) in the TOTAL interval count.")
    suite.case("cost scales ~m log m in total busy intervals", interval_scaling)

    def span_independence():
        busy = gen_busy(300, 50_000)
        t_small = bench(lambda: find_slots(busy, 30, (0, 100_000)), repeat=3)
        t_big = bench(lambda: find_slots(busy, 30, (0, 1_600_000)), repeat=3)
        ratio = t_big / max(t_small, 1e-9)
        suite.info(f"window of 100k min: {fmt_s(t_small)}   16x wider: {fmt_s(t_big)}")
        assert ratio < 3, \
            (f"widening the window 16x (same 300 intervals) made find_slots "
             f"{ratio:.1f}x slower — it is scanning minute-by-minute over the "
             f"window. Work must depend on the interval COUNT, not the "
             f"window's length in minutes.")
    suite.case("cost independent of window length in minutes", span_independence)

    def note_distributed_story():
        raise PerfConcern(
            "not machine-checkable: extensions 2-4 are the discussion tail. "
            "Rehearse optional attendees (which K-subset? greedy per gap), the "
            "working-hours mask (it's just another attendee's busy list), and "
            "slow per-service calendar fetches (fetch in parallel, intersect "
            "incrementally, early-exit once no gap can fit).")
    suite.case("optional-attendees / working-hours / slow-fetch story",
               note_distributed_story)

    return suite.summary()


if __name__ == "__main__":
    sys.exit(1 if main().failed else 0)
