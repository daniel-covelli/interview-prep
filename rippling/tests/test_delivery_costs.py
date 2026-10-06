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
from heapq import heappush, heappop


class DeliveryTracker:
    def __init__(self) -> None:
        self.rates = {}          # driver -> cents per hour
        self.unpaid = []         # min-heap of (end, cost) awaiting a payout run
        self.total = 0           # exact cent-seconds (cents * 3600) ever recorded
        self.paid = 0            # exact cent-seconds settled so far

    def add_driver(self, driver_id, rate_cents_per_hour):
        self.rates[driver_id] = rate_cents_per_hour

    def record_delivery(self, driver_id, start, end):
        cost = self.rates[driver_id] * (end - start)  # cent-seconds: exact
        self.total += cost
        heappush(self.unpaid, (end, cost))

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

'''


def half_up(cents):
    """Exact Fraction cents -> whole cents, .5 rounds up."""
    return math.floor(cents + Fraction(1, 2))


class Oracle:
    """Brute-force truth in exact arithmetic: a flat list of every delivery
    with its Fraction cost and paid flag. Reports re-sum the list; payouts
    scan it."""

    def __init__(self):
        self.rates = {}            # driver -> rate
        self.deliveries = []       # [driver, start, end, cost, paid]

    def add_driver(self, driver, rate):
        self.rates[driver] = rate

    def record_delivery(self, driver, start, end):
        rate = self.rates[driver]
        self.deliveries.append([driver, start, end, Fraction(rate * (end - start), 3600), False])

    def total_cost(self):
        return half_up(sum((d[3] for d in self.deliveries), Fraction(0)))

    def pay_up_to(self, pay_time):
        for d in self.deliveries:
            if not d[4] and d[2] <= pay_time:
                d[4] = True

    def unpaid_cost(self):
        return half_up(sum((d[3] for d in self.deliveries if not d[4]), Fraction(0)))




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

    # ---- randomized rounds, one per phase reach ------------------------------

    def run_rounds(rounds, ops, phases, base):
        # timestamps on a one-minute grid so same-end deliveries and exact
        # boundary coincidences (end == a payout time) actually happen
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
        getattr(t, method)(0)

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
