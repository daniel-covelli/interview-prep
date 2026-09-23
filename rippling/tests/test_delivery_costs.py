# Grader for Rippling Problem 2 (rippling/p2_delivery_costs.py).
# SPOILER WARNING: this file enumerates edge cases and contains a brute-force
# oracle and the reference solution. Run it, don't read it.
import math
import random
import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from grader import (Suite, PerfConcern, load_class, bench, fmt_s, tracing,
                    expect)

SEED = 0xD311

# Reference solution, printed by `uv run grade --reveal rippling/p2_delivery_costs`
# once the timebox is up. Never read it before then.
REFERENCE = '''
from bisect import bisect_right
from heapq import heappush, heappop


class DeliveryTracker:
    def __init__(self) -> None:
        self.rates = {}          # driver -> ([effective_from, ascending], [rate])
        self.deliveries = []     # (driver, start, end) for every delivery (phase 3)
        self.unpaid = []         # min-heap of (end, cost) awaiting a payout run
        self.total = 0           # exact cent-seconds (cents * 3600) ever recorded
        self.paid = 0            # exact cent-seconds settled so far

    def add_driver(self, driver_id, rate_cents_per_hour):
        self.rates[driver_id] = ([0], [rate_cents_per_hour])

    def update_rate(self, driver_id, rate_cents_per_hour, effective_from):
        times, rates = self.rates[driver_id]
        i = bisect_right(times, effective_from)
        if i and times[i - 1] == effective_from:     # same effective time: replace
            rates[i - 1] = rate_cents_per_hour
        else:                                        # keep the history sorted
            times.insert(i, effective_from)
            rates.insert(i, rate_cents_per_hour)

    def record_delivery(self, driver_id, start, end):
        times, rates = self.rates[driver_id]
        rate = rates[bisect_right(times, start) - 1]  # in force at the start
        cost = rate * (end - start)                   # cent-seconds: exact, fixed now
        self.total += cost
        heappush(self.unpaid, (end, cost))
        self.deliveries.append((driver_id, start, end))

    def pay_up_to(self, pay_time):
        while self.unpaid and self.unpaid[0][0] <= pay_time:
            self.paid += heappop(self.unpaid)[1]

    @staticmethod
    def _cents(cent_seconds):
        return (cent_seconds + 1800) // 3600          # round half up, once

    def total_cost(self):
        return self._cents(self.total)

    def unpaid_cost(self):
        return self._cents(self.total - self.paid)

    def peak_active_drivers(self, now):
        lo = now - 86400
        events = []                                   # ends (-1) sort before starts (+1)
        for driver, start, end in self.deliveries:
            if start <= now and end > lo:
                events.append((max(start, lo), 1, driver))
                events.append((end, -1, driver))
        events.sort()
        active, busy, best = {}, 0, 0                # per-driver open deliveries
        for _, delta, driver in events:
            n = active.get(driver, 0) + delta
            active[driver] = n
            if delta == 1 and n == 1:
                busy += 1
                best = max(best, busy)
            elif delta == -1 and n == 0:
                busy -= 1
        return best
'''


def half_up(cents):
    """Exact Fraction cents -> whole cents, .5 rounds up."""
    return math.floor(cents + Fraction(1, 2))


class Oracle:
    """Brute-force truth in exact arithmetic: a flat list of every delivery
    with its Fraction cost and paid flag. Reports re-sum the list; payouts
    scan it; the peak query counts drivers at every candidate instant."""

    def __init__(self):
        self.rates = {}            # driver -> {effective_from: rate}
        self.deliveries = []       # [driver, start, end, cost, paid]

    def add_driver(self, driver, rate):
        self.rates[driver] = {0: rate}

    def update_rate(self, driver, rate, effective_from):
        self.rates[driver][effective_from] = rate

    def record_delivery(self, driver, start, end):
        hist = self.rates[driver]
        rate = hist[max(t for t in hist if t <= start)]
        self.deliveries.append([driver, start, end, Fraction(rate * (end - start), 3600), False])

    def total_cost(self):
        return half_up(sum((d[3] for d in self.deliveries), Fraction(0)))

    def pay_up_to(self, pay_time):
        for d in self.deliveries:
            if not d[4] and d[2] <= pay_time:
                d[4] = True

    def unpaid_cost(self):
        return half_up(sum((d[3] for d in self.deliveries if not d[4]), Fraction(0)))

    def peak_active_drivers(self, now):
        lo = now - 86400
        instants = {lo} | {max(d[1], lo) for d in self.deliveries}
        best = 0
        for t in instants:
            if lo <= t <= now:
                best = max(best, len({d[0] for d in self.deliveries if d[1] <= t < d[2]}))
        return best



def measure(fn, diagnosis, repeat=2):
    """bench() that attaches the case's diagnosis to a TLE, so a workload
    that never finishes still names the naive design being caught."""
    try:
        return bench(fn, repeat=repeat)
    except AssertionError as e:
        raise AssertionError(f"{diagnosis}  [{e}]") from None

def main():
    suite = Suite("Rippling 2: DeliveryTracker")
    cls, err = load_class("rippling.p2_delivery_costs", "DeliveryTracker")
    if cls is None:
        suite.skip_all(err)
        return suite.summary()
    make = tracing(cls)

    def built(method):
        """Skip the case unless the phase's method exists and is implemented."""
        if not hasattr(cls, method):
            raise NotImplementedError
        t = make()
        t.add_driver("probe", 1)
        if method == "pay_up_to":
            t.pay_up_to(0)
        elif method == "peak_active_drivers":
            t.peak_active_drivers(0)
        elif method == "update_rate":
            t.update_rate("probe", 1, 0)

    suite.section("PHASE 1 — LIVE TOTAL")

    def spec_example():
        t = make()
        t.add_driver("alice", 1000)
        t.record_delivery("alice", 0, 5400)
        expect(t.total_cost(), 1500, note="$10.00/h for 90 minutes")
        t.add_driver("bob", 1200)
        t.record_delivery("bob", 1000, 2800)
        t.record_delivery("bob", 2000, 5600)
        expect(t.total_cost(), 3300,
               note="600 + 1200 for bob's overlapping deliveries, both billed in full")
    suite.case("spec example from the file header", spec_example)

    def rounding_once():
        t = make()
        t.add_driver("carol", 1)
        t.record_delivery("carol", 0, 1800)
        expect(t.total_cost(), 1, note="exactly 0.5 cents rounds UP to 1")
        t.record_delivery("carol", 0, 1800)
        expect(t.total_cost(), 1,
               note="two half-cent deliveries total exactly 1.0 — rounding each "
                    "delivery on its own would give 0 (truncation) or 2 (half up)")
        t.record_delivery("carol", 0, 1440)
        expect(t.total_cost(), 1, note="exact total 1.4 rounds down to 1")
        t.record_delivery("carol", 0, 360)
        expect(t.total_cost(), 2, note="exact total 1.5 rounds up to 2")
    suite.case("fractions of a cent survive between deliveries; half up once at report time",
               rounding_once)

    def exact_arithmetic():
        t = make()
        t.add_driver("dave", 1)
        for _ in range(24):
            t.record_delivery("dave", 0, 75)
        expect(t.total_cost(), 1,
               note="24 x (1 cent/h for 75 s) is EXACTLY 24 * 75 / 3600 = 0.5 cents, "
                    "which rounds up to 1. A binary float accumulator sums to "
                    "0.49999999999999978 and reports 0: keep money exact (integer "
                    "cent-seconds, or an exact rational), never a float.")
    suite.case("the total is exact: float accumulation gets this one wrong", exact_arithmetic)

    def precision_and_sizes():
        t = make()
        expect(t.total_cost(), 0, note="no deliveries yet")
        t.add_driver("ed", 3600)
        t.record_delivery("ed", 10, 11)
        expect(t.total_cost(), 1, note="one second at 3600 cents/h is exactly 1 cent")
        t.record_delivery("ed", 100, 3700)
        expect(t.total_cost(), 3601, note="a full hour on top")
        t.add_driver("fay", 2)
        t.record_delivery("fay", 0, 60)
        expect(t.total_cost(), 3601,
               note="a minute at 2 cents/h is 0.033 cents: the total stays 3601 when rounded")
        t.record_delivery("fay", 0, 86400 * 30)
        expect(t.total_cost(), 5041, note="a 30-day delivery: 1440 cents more")
    suite.case("second-level precision, big and tiny deliveries, empty tracker",
               precision_and_sizes)

    def many_drivers():
        t = make()
        for i, rate in enumerate([500, 1000, 1500]):
            t.add_driver(f"d{i}", rate)
        t.record_delivery("d0", 0, 3600)
        t.record_delivery("d1", 0, 3600)
        t.record_delivery("d2", 0, 3600)
        expect(t.total_cost(), 3000, note="each driver at their own rate")
        t.record_delivery("d0", 0, 3600)
        expect(t.total_cost(), 3500, note="the same driver again, same rate")
    suite.case("several drivers, each at their own rate", many_drivers)

    suite.section("PHASE 2 — PAYOUT RUNS (skipped until you build it)")

    def spec_example_payouts():
        built("pay_up_to")
        t = make()
        t.add_driver("alice", 1000)
        t.record_delivery("alice", 0, 3600)
        t.record_delivery("alice", 3000, 6600)
        expect(t.unpaid_cost(), 2000)
        t.pay_up_to(3600)
        expect(t.unpaid_cost(), 1000,
               note="only the delivery ending at 3600 (<= pay_time) is settled")
        expect(t.total_cost(), 2000, note="payouts never change the total")
        t.pay_up_to(3600)
        expect(t.unpaid_cost(), 1000, note="a repeated run pays nothing new")
        t.record_delivery("alice", 0, 1800)
        expect(t.unpaid_cost(), 1500,
               note="a delivery recorded after the run is unpaid even though it ended earlier")
        t.pay_up_to(2000)
        expect(t.unpaid_cost(), 1000,
               note="a run with an EARLIER pay_time still settles the late one (1800 <= 2000)")
    suite.case("spec example from the file header", spec_example_payouts)

    def own_rounding():
        built("pay_up_to")
        t = make()
        t.add_driver("carol", 1)
        t.record_delivery("carol", 0, 1800)
        t.record_delivery("carol", 0, 5400)
        expect(t.total_cost(), 2, note="exact total 2.0")
        t.pay_up_to(1800)
        expect(t.unpaid_cost(), 2,
               note="exact unpaid is 1.5 -> 2. 'rounded total (2) minus rounded "
                    "paid (1)' would say 1: each report rounds its own exact sum")
        t.pay_up_to(5400)
        expect(t.unpaid_cost(), 0)
        expect(t.total_cost(), 2)
    suite.case("unpaid rounds its own exact sum, not total-minus-paid", own_rounding)

    def boundaries():
        built("pay_up_to")
        t = make()
        t.add_driver("alice", 3600)
        t.pay_up_to(10_000)
        expect(t.unpaid_cost(), 0, note="a run before any delivery settles nothing")
        t.record_delivery("alice", 0, 100)
        t.record_delivery("alice", 0, 200)
        t.record_delivery("alice", 0, 300)
        expect(t.unpaid_cost(), 600,
               note="the earlier run does not cover deliveries recorded after it")
        t.pay_up_to(199)
        expect(t.unpaid_cost(), 500, note="end 200 > 199: only the first is settled")
        t.pay_up_to(200)
        expect(t.unpaid_cost(), 300, note="end exactly equal to pay_time IS settled")
        t.pay_up_to(150)
        expect(t.unpaid_cost(), 300, note="going backwards in time pays nothing")
        t.pay_up_to(10_000)
        expect(t.unpaid_cost(), 0)
        t.pay_up_to(10_000)
        expect(t.unpaid_cost(), 0, note="nothing left: still nothing")
        expect(t.total_cost(), 600)
    suite.case("pay_time boundaries: <=, idempotent, never backwards", boundaries)

    suite.section("PHASE 3 — PEAK CONCURRENCY (skipped until you build it)")

    def spec_example_peak():
        built("peak_active_drivers")
        t = make()
        t.add_driver("alice", 1000)
        t.add_driver("bob", 1000)
        t.add_driver("cy", 1000)
        t.record_delivery("alice", 100, 200)
        t.record_delivery("bob", 150, 250)
        t.record_delivery("cy", 200, 300)
        expect(t.peak_active_drivers(300), 2,
               note="cy starts exactly when alice ends: never 3 at once")
        t.record_delivery("alice", 120, 260)
        expect(t.peak_active_drivers(300), 3,
               note="during [200, 250) alice, bob and cy are all active; alice's two "
                    "overlapping deliveries count her once")
        expect(t.peak_active_drivers(86650), 2,
               note="the window starts at 250, exactly when bob's delivery ended: "
                    "alice (120-260) and cy (200-300) remain")
        expect(t.peak_active_drivers(90000), 0, note="window [3600, 90000] has nothing active")
    suite.case("spec example from the file header", spec_example_peak)

    def window_edges():
        built("peak_active_drivers")
        t = make()
        t.add_driver("a", 1)
        t.add_driver("b", 1)
        t.record_delivery("a", 0, 1000)
        t.record_delivery("b", 500, 1500)
        expect(t.peak_active_drivers(700), 2, note="now = 700 is inside both deliveries")
        expect(t.peak_active_drivers(500), 2,
               note="b starts exactly at now: active at the instant now")
        expect(t.peak_active_drivers(499), 1, note="b starts after now: only a")
        expect(t.peak_active_drivers(86400 + 1000), 1,
               note="window starts at 1000, exactly when a ended: only b")
        expect(t.peak_active_drivers(86400 + 999), 2,
               note="window starts at 999: a is still active for one more second")
        expect(t.peak_active_drivers(86400 + 1500), 0,
               note="window starts at 1500, when b ended: nothing")
        expect(t.peak_active_drivers(20_000), 2,
               note="both deliveries lie entirely inside the window")
    suite.case("half-open activity against both window edges", window_edges)

    def distinct_drivers():
        built("peak_active_drivers")
        t = make()
        t.add_driver("a", 1)
        t.add_driver("b", 1)
        for _ in range(4):
            t.record_delivery("a", 100, 200)
        expect(t.peak_active_drivers(200), 1,
               note="four simultaneous deliveries by ONE driver count as one driver")
        t.record_delivery("b", 199, 201)
        expect(t.peak_active_drivers(200), 2)
        t.record_delivery("b", 400, 500)
        t.record_delivery("a", 450, 460)
        expect(t.peak_active_drivers(500), 2,
               note="two separate moments with two drivers: the peak is still 2")
        t.record_delivery("a", 100_000, 100_100)
        expect(t.peak_active_drivers(500), 2,
               note="a delivery after now is ignored")
        expect(t.peak_active_drivers(100_050), 1,
               note="window [13650, 100050]: only the late delivery is active")
    suite.case("distinct drivers, not deliveries; future deliveries ignored", distinct_drivers)

    suite.section("PHASE 4 — RATE CHANGES (skipped until you build it)")

    def spec_example_rates():
        built("update_rate")
        t = make()
        t.add_driver("alice", 1000)
        t.update_rate("alice", 2000, 7200)
        t.record_delivery("alice", 3600, 7200)
        t.record_delivery("alice", 7200, 10800)
        t.record_delivery("alice", 5400, 9000)
        expect(t.total_cost(), 4000,
               note="1000 (before the raise) + 2000 (starts exactly at it) + 1000 "
                    "(spans it: the rate at the START applies)")
        t.update_rate("alice", 3000, 0)
        t.record_delivery("alice", 0, 3600)
        expect(t.total_cost(), 7000,
               note="the back-dated update re-prices nothing already recorded; the new "
                    "delivery is billed at 3000")
        t.update_rate("alice", 1500, 3600)
        t.record_delivery("alice", 5000, 5600)
        expect(t.total_cost(), 7250, note="the entry slotted in at 3600 is in force at 5000")
    suite.case("spec example from the file header", spec_example_rates)

    def history_semantics():
        built("update_rate")
        t = make()
        t.add_driver("a", 100)
        t.update_rate("a", 300, 3000)
        t.update_rate("a", 200, 2000)
        t.update_rate("a", 400, 4000)
        t.record_delivery("a", 2999, 3000)
        t.record_delivery("a", 3000, 3001)
        t.record_delivery("a", 1999, 2000)
        t.record_delivery("a", 4000, 4001)
        t.record_delivery("a", 5000, 5036)
        expect(t.total_cost(), 4,
               note="updates arrived out of order: 1 s at 200 + 1 s at 300 + 1 s at 100 "
                    "+ 1 s at 400 = 1000 cent-seconds, plus 36 s at 400 = 14400 -> 4.28 cents")
        t.update_rate("a", 900, 3000)
        t.record_delivery("a", 3500, 3540)
        expect(t.total_cost(), 14,
               note="a second update at effective time 3000 REPLACES the 300 entry: "
                    "40 s at 900 = 10 cents more")
        t.update_rate("a", 0, 0)
        t.record_delivery("a", 0, 3600)
        expect(t.total_cost(), 14,
               note="updating at effective time 0 replaces the add_driver rate: free hour")
    suite.case("out-of-order updates, same-time replacement, replacing the initial rate",
               history_semantics)

    def drivers_isolated():
        built("update_rate")
        t = make()
        t.add_driver("a", 1000)
        t.add_driver("b", 1000)
        t.update_rate("a", 5000, 100)
        t.record_delivery("a", 100, 3700)
        t.record_delivery("b", 100, 3700)
        expect(t.total_cost(), 6000, note="a's raise never touches b")
        t.pay_up_to(3700) if hasattr(t, "pay_up_to") else None
    suite.case("rate histories are per driver", drivers_isolated)

    # ---- randomized rounds, one per phase reach ------------------------------

    def run_rounds(rounds, ops, phases, base):
        # timestamps on a one-minute grid so same-end deliveries and exact
        # boundary coincidences (start == another's end, start == an effective
        # time, end == the window's edge) actually happen
        drivers = ["a", "b", "c"]
        for rnd in range(rounds):
            rng = random.Random(SEED + base + rnd)
            t, oracle = make(), Oracle()
            ctx = f"seed={SEED:#x}, round={rnd}"
            for d in drivers:
                rate = rng.randrange(1, 40)
                t.add_driver(d, rate)
                oracle.add_driver(d, rate)
            runs = 0                       # payout runs so far, for the unpaid notes
            for op in range(ops):
                roll = rng.random()
                if roll < 0.45:
                    d = rng.choice(drivers)
                    s = 60 * rng.randrange(0, 334)
                    e = s + 60 * rng.randrange(1, 121)
                    t.record_delivery(d, s, e)
                    oracle.record_delivery(d, s, e)
                elif roll < 0.6:
                    expect(t.total_cost(), oracle.total_cost(),
                           note=f"{ctx}, op={op}, total_cost()")
                elif roll < 0.72 and phases >= 2:
                    p = 60 * rng.randrange(0, 460)
                    t.pay_up_to(p)
                    oracle.pay_up_to(p)
                    runs += 1
                elif roll < 0.84 and phases >= 2:
                    expect(t.unpaid_cost(), oracle.unpaid_cost(),
                           note=f"{ctx}, op={op}, unpaid_cost() after {runs} payout run(s); "
                                f"the exact total is {oracle.total_cost()} cents")
                elif roll < 0.92 and phases >= 3:
                    now = 60 * rng.randrange(0, 460) + rng.choice([0, 0, 86_400])
                    expect(t.peak_active_drivers(now), oracle.peak_active_drivers(now),
                           note=f"{ctx}, op={op}, peak_active_drivers({now}): window "
                                f"[{now - 86400}, {now}]")
                elif phases >= 4:
                    d = rng.choice(drivers)
                    rate, eff = rng.randrange(0, 40), 60 * rng.randrange(0, 334)
                    t.update_rate(d, rate, eff)
                    oracle.update_rate(d, rate, eff)
            expect(t.total_cost(), oracle.total_cost(), note=f"{ctx}, final total_cost()")
            if phases >= 2:
                expect(t.unpaid_cost(), oracle.unpaid_cost(),
                       note=f"{ctx}, final unpaid_cost() after {runs} payout run(s); "
                            f"the exact total is {oracle.total_cost()} cents")

    def randomized_p1():
        run_rounds(rounds=30, ops=45, phases=1, base=100)
    suite.case("randomized (phase 1): 30 rounds x 45 record/total ops vs exact oracle",
               randomized_p1)

    def randomized_p2():
        built("pay_up_to")
        run_rounds(rounds=40, ops=50, phases=2, base=200)
    suite.case("randomized (phases 1-2): 40 rounds x 50 ops incl. payouts vs exact oracle",
               randomized_p2)

    def randomized_p3():
        built("pay_up_to")
        built("peak_active_drivers")
        run_rounds(rounds=40, ops=50, phases=3, base=300)
    suite.case("randomized (phases 1-3): 40 rounds x 50 ops incl. peak queries vs exact oracle",
               randomized_p3)

    def randomized_p4():
        built("pay_up_to")
        built("peak_active_drivers")
        built("update_rate")
        run_rounds(rounds=50, ops=55, phases=4, base=400)
    suite.case("randomized (phases 1-4): 50 rounds x 55 ops incl. rate updates vs exact oracle",
               randomized_p4)

    if suite.failed or not suite.passed:
        suite.section("PERFORMANCE")
        reason = ("fix correctness failures first" if suite.failed
                  else "nothing implemented yet")
        suite.skip("all performance checks", reason)
        return suite.summary()

    suite.section("PERFORMANCE")

    def probe(method):
        if not hasattr(cls, method):
            raise NotImplementedError
        t = cls()
        t.add_driver("probe", 1)
        getattr(t, method)(*(["probe", 1, 0] if method == "update_rate" else [0]))

    def live_total(n, reps):
        # a total_cost() read after every record: a total that re-sums the
        # delivery log on each read goes quadratic
        def run():
            for _ in range(reps):
                t = cls()
                t.add_driver("d", 1234)
                for i in range(n):
                    t.record_delivery("d", i, i + 600)
                    t.total_cost()
        return run

    def total_scaling():
        diagnosis = ("total_cost() is re-summing the delivery log on every read. "
                     "Target: O(1) — keep the exact running total up to date as "
                     "deliveries arrive and round only when reporting.")
        t_small = measure(live_total(3_000, 10), diagnosis)
        t_big = measure(live_total(12_000, 10), diagnosis)
        ratio = t_big / max(t_small, 1e-9)
        suite.info(f"10 x (3k records + 3k reads): {fmt_s(t_small)}   "
                   f"10 x (12k records + 12k reads): {fmt_s(t_big)}   "
                   f"ratio {ratio:.1f}x (O(1) per op ≈ 4x)")
        assert ratio < 10, \
            f"4x the deliveries made record+total_cost {ratio:.1f}x slower — {diagnosis}"
    suite.case("total_cost() stays O(1) as the delivery log grows", total_scaling)

    def payout_runs(n, reps):
        # n deliveries with scattered ends, then n runs with increasing pay
        # times each settling ~1 delivery: a run that scans the whole log (or
        # every still-unpaid delivery) goes quadratic
        rng = random.Random(SEED)
        ends = [rng.randrange(1, 10 * n) for _ in range(n)]
        pays = sorted(rng.randrange(1, 10 * n) for _ in range(n))

        def run():
            for _ in range(reps):
                t = cls()
                t.add_driver("d", 1234)
                for e in ends:
                    t.record_delivery("d", max(0, e - 600), e)
                for p in pays:
                    t.pay_up_to(p)
                t.unpaid_cost()
        return run

    def payout_scaling():
        probe("pay_up_to")
        diagnosis = ("pay_up_to() is scanning the delivery log (or the unpaid set) on "
                     "every run. Target: O(k log n) for the k deliveries a run settles "
                     "— keep the unpaid deliveries ordered by end time so a run only "
                     "touches the ones it pays.")
        t_small = measure(payout_runs(3_000, 6), diagnosis)
        t_big = measure(payout_runs(12_000, 6), diagnosis)
        ratio = t_big / max(t_small, 1e-9)
        suite.info(f"6 x (3k records + 3k payout runs): {fmt_s(t_small)}   "
                   f"6 x (12k + 12k): {fmt_s(t_big)}   ratio {ratio:.1f}x (n log n ≈ 4-5x)")
        assert ratio < 10, \
            f"4x the deliveries and payout runs took {ratio:.1f}x longer — {diagnosis}"
    suite.case("pay_up_to() cost depends on what it settles, not on the log size",
               payout_scaling)

    def peak_query(n, reps):
        # n deliveries by 50 drivers inside one 24h window, then one peak
        # query: counting drivers at every start (or every second) is the trap
        rng = random.Random(SEED)
        recs = []
        for i in range(n):
            s = rng.randrange(0, 80_000)
            recs.append((f"d{i % 50}", s, s + rng.randrange(60, 5_400)))

        def run():
            for _ in range(reps):
                t = cls()
                for i in range(50):
                    t.add_driver(f"d{i}", 100)
                for d, s, e in recs:
                    t.record_delivery(d, s, e)
                t.peak_active_drivers(86_400)
        return run

    def peak_scaling():
        probe("peak_active_drivers")
        diagnosis = ("peak_active_drivers() is counting active drivers per delivery "
                     "(or per second of the window). Target: O(n log n) — order the "
                     "starts and ends once and walk them, tracking how many deliveries "
                     "each driver has open so a driver is counted once.")
        t_small = measure(peak_query(2_000, 6), diagnosis)
        t_big = measure(peak_query(8_000, 6), diagnosis)
        ratio = t_big / max(t_small, 1e-9)
        suite.info(f"6 x (2k deliveries + peak query): {fmt_s(t_small)}   "
                   f"6 x (8k + query): {fmt_s(t_big)}   ratio {ratio:.1f}x (n log n ≈ 4-5x)")
        assert ratio < 10, \
            f"4x the deliveries in the window made the peak query {ratio:.1f}x slower — {diagnosis}"
    suite.case("peak_active_drivers() scales ~n log n in deliveries", peak_scaling)

    def rate_lookups(n, reps):
        # one driver with n rate versions (arriving in time order), then n
        # deliveries at random starts: a lookup that scans the history is O(n)
        rng = random.Random(SEED)
        starts = [rng.randrange(0, 10 * n) for _ in range(n)]

        def run():
            for _ in range(reps):
                t = cls()
                t.add_driver("d", 100)
                for i in range(1, n):
                    t.update_rate("d", 100 + i, 10 * i)
                for s in starts:
                    t.record_delivery("d", s, s + 60)
                t.total_cost()
        return run

    def rate_scaling():
        probe("update_rate")
        diagnosis = ("record_delivery() is scanning the driver's rate history to find "
                     "the rate in force. Target: O(log versions) per delivery — keep "
                     "each driver's effective times in order and search them.")
        t_small = measure(rate_lookups(2_000, 10), diagnosis)
        t_big = measure(rate_lookups(8_000, 10), diagnosis)
        ratio = t_big / max(t_small, 1e-9)
        suite.info(f"10 x (2k rate versions + 2k deliveries): {fmt_s(t_small)}   "
                   f"10 x (8k + 8k): {fmt_s(t_big)}   ratio {ratio:.1f}x (n log n ≈ 4-5x)")
        assert ratio < 10, \
            f"4x the rate versions and deliveries took {ratio:.1f}x longer — {diagnosis}"
    suite.case("finding the rate in force does not scan the rate history", rate_scaling)

    def note_followups():
        raise PerfConcern(
            "not machine-checkable: the DISCUSS AFTERWARDS tail. Rehearse the "
            "float-vs-exact story (the 24 x 75 s case above; integer cent-seconds "
            "or Decimal/Fraction), and pro-rata payouts — where a delivery's "
            "settled and unsettled slices each round, and how a cent gets paid "
            "twice unless you track what was already settled exactly.")
    suite.case("money-precision / pro-rata payout story", note_followups)

    return suite.summary()


if __name__ == "__main__":
    sys.exit(1 if main().failed else 0)
