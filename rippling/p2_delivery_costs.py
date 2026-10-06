"""
PROBLEM 2 — Delivery Cost Tracker
=================================
Difficulty: medium | Timebox: 45 min (hard stop) — phase 1 by minute 20 |
Interview frequency: very high (Rippling's signature phone-screen question, 2024–2026)

CONTEXT
-------
A food-delivery company pays tens of thousands of contract drivers
through Rippling. Each driver has an hourly rate; every delivery is
reported to the system the moment it completes. Accounting wants a
dashboard number — the total labor cost of all deliveries — that is
always up to date, and later a payout run that settles finished
deliveries. You are building the in-memory service behind that dashboard.

SPEC — PHASE 1 (live total)
---------------------------
    tracker = DeliveryTracker()
    tracker.add_driver(driver_id: str, rate_cents_per_hour: int) -> None
    tracker.record_delivery(driver_id: str, start: int, end: int) -> None
    tracker.total_cost() -> int

- `start`/`end` are integer Unix seconds with `start < end`. A delivery
  costs `rate_cents_per_hour * (end - start) / 3600` cents, exactly —
  a $10.00/h driver (rate 1000) earns 1500 cents for a 90-minute delivery.
- A driver may run several deliveries at once (overlapping intervals);
  each one is billed in full.
- `total_cost()` returns the exact sum of every delivery ever recorded,
  rounded half up to a whole cent (an exact .5 rounds up). Round once,
  when you report: fractions of a cent must survive between deliveries.

Examples:
    tracker = DeliveryTracker()
    tracker.add_driver("alice", 1000)              # $10.00 per hour
    tracker.record_delivery("alice", 0, 5400)      # 90 min -> 1500 cents
    tracker.total_cost()          -> 1500
    tracker.add_driver("bob", 1200)
    tracker.record_delivery("bob", 1000, 2800)     # 30 min -> 600
    tracker.record_delivery("bob", 2000, 5600)     # overlaps bob's other delivery: billed anyway, 1200
    tracker.total_cost()          -> 3300

    # tricky: rounding happens once, at report time
    tracker = DeliveryTracker()
    tracker.add_driver("carol", 1)                 # one cent per hour
    tracker.record_delivery("carol", 0, 1800)      # exactly half a cent
    tracker.total_cost()          -> 1             # .5 rounds up
    tracker.record_delivery("carol", 0, 1800)      # another half cent: the exact total is 1.0
    tracker.total_cost()          -> 1             # NOT 2 — never round per delivery

SPEC — PHASE 2 (payout runs)
----------------------------
    tracker.pay_up_to(pay_time: int) -> None
    tracker.unpaid_cost() -> int

- `pay_up_to(t)` settles every recorded, not-yet-paid delivery whose
  `end <= t`, in full — a delivery is never partly paid. Calling it
  again with the same or an earlier `t` pays nothing new; a delivery
  recorded AFTER a payout run stays unpaid until a later run covers it,
  even if it ended long before that run.
- `unpaid_cost()` returns the exact sum of the unpaid deliveries,
  rounded half up. `total_cost()` is unaffected by payouts. Each report
  rounds its OWN exact sum — unpaid is not "rounded total minus rounded
  paid".

Examples:
    tracker = DeliveryTracker()
    tracker.add_driver("alice", 1000)
    tracker.record_delivery("alice", 0, 3600)      # 1000 cents, ends at 3600
    tracker.record_delivery("alice", 3000, 6600)   # 1000 cents, ends at 6600
    tracker.unpaid_cost()         -> 2000
    tracker.pay_up_to(3600)                        # settles only the delivery that ended at 3600
    tracker.unpaid_cost()         -> 1000
    tracker.total_cost()          -> 2000          # payouts never change the total
    tracker.pay_up_to(3600)                        # again: nothing new to pay
    tracker.unpaid_cost()         -> 1000
    tracker.record_delivery("alice", 0, 1800)      # reported late; ended long ago: 500, unpaid
    tracker.unpaid_cost()         -> 1500
    tracker.pay_up_to(2000)                        # earlier than the last run, but 1800 <= 2000
    tracker.unpaid_cost()         -> 1000

    # tricky: every report rounds its own exact sum
    tracker = DeliveryTracker()
    tracker.add_driver("carol", 1)
    tracker.record_delivery("carol", 0, 1800)      # 0.5 cents, ends at 1800
    tracker.record_delivery("carol", 0, 5400)      # 1.5 cents, ends at 5400
    tracker.total_cost()          -> 2             # exact 2.0
    tracker.pay_up_to(1800)
    tracker.unpaid_cost()         -> 2             # exact 1.5 rounds up — not total 2 minus paid 1

ASSUMPTIONS DECIDED HERE (rehearse asking them)
-----------------------------------------------
- Money is integer cents in and out; rates are whole cents per hour.
  Costs may be fractional cents internally; only the two report calls
  round. Binary floating point is not exact enough for this service —
  the grader includes a total it gets wrong.
- Every `driver_id` passed to `record_delivery` was
  registered with `add_driver` first, and `add_driver` is called once
  per driver. Timestamps are non-negative integers.
- Deliveries are reported after they finish but not necessarily in
  order of `end` — a late report may end earlier than one already
  recorded (the payout examples rely on this).
- Deliveries are never edited or cancelled. Single process, single
  thread.

DISCUSS AFTERWARDS
------------------
- The interviewer asks why floating point is a bad idea for this
  service. Be able to give a concrete failing example and name the
  alternatives.
- Payroll wants `pay_up_to` to settle a delivery that straddles `t`
  pro rata instead of whole. What changes in your rounding story, and
  where could a cent get paid twice?

TARGET COMPLEXITY
-----------------
`total_cost()` and `unpaid_cost()` in O(1) — they back a live dashboard
and must not walk the delivery log. `record_delivery` in O(log n) or
better, and `pay_up_to` in O(k log n) for the k deliveries it settles:
its cost must not depend on how many deliveries were ever recorded.
"""
import math
import bisect

class DeliveryTracker:
    def __init__(self) -> None:
        self.rates: dict[str, int] = {}
        self.unpaid: float = 0
        self.payed: float = 0
        self.unpaid_log: list[(int, float)] = []

    def add_driver(self, driver_id: str, rate_cents_per_hour: int) -> None:
        self.rates[driver_id] = rate_cents_per_hour

    def record_delivery(self, driver_id: str, start: int, end: int) -> None:
        if driver_id not in self.rates:
            raise KeyError("Driver has not been added yet")

        rate = self.rates[driver_id]
        unpaid = rate * (end - start) / 3600
        self.unpaid += unpaid

        bisect.insort(self.unpaid_log, (-end, unpaid))

    def total_cost(self) -> int:
        return math.ceil(self.unpaid + self.payed)

    def pay_up_to(self, pay_time: int) -> None:
        if not len(self.unpaid_log): return
        i = len(self.unpaid_log) - 1
        while i >= 0 and pay_time >= self.unpaid_log[i][0] * -1:
            _, unpaid_amount = self.unpaid_log[i]
            self.unpaid -= unpaid_amount
            self.payed += unpaid_amount
            self.unpaid_log.pop()
            i -= 1

    def unpaid_cost(self) -> int:
        return math.ceil(self.unpaid)


if __name__ == "__main__":
    from lib import run_test_cases, show

    test_cases = [
        [
            (DeliveryTracker),
            ("add_driver", ("alice", 1000), None),
            ("record_delivery", ("alice", 0, 5400), None),
            ("total_cost", (), 1500),
            ("add_driver", ("bob", 1200), None),
            ("record_delivery", ("bob", 1000, 2800), None),
            ("record_delivery", ("bob", 2000, 5600), None),
            ("total_cost", (), 3300),
        ],
        [
            (DeliveryTracker),
            ("add_driver", ("carol", 1), None),
            ("record_delivery", ("carol", 0, 1800), None),
            ("total_cost", (), 1),
            ("record_delivery", ("carol", 0, 1800), None),
            ("total_cost", (), 1),
        ],
        [
            (DeliveryTracker),
            ("add_driver", ("alice", 1000), None),
            ("record_delivery", ("alice", 0, 3600), None),
            ("record_delivery", ("alice", 3000, 6600), None),
            ("unpaid_cost", (), 2000),
            ("pay_up_to", (3600), None),
            ("unpaid_cost", (), 1000),
            ("total_cost", (), 2000),
            ("pay_up_to", (3600), None),
            ("unpaid_cost", (), 1000),
            ("record_delivery", ("alice", 0, 1800), None),
            ("unpaid_cost", (), 1500),
            ("pay_up_to", (2000), None),
            ("unpaid_cost", (), 1000),
        ],
        [
            (DeliveryTracker),
            ("add_driver", ("carol", 1), None),
            ("record_delivery", ("carol", 0, 1800), None),   
            ("record_delivery", ("carol", 0, 5400), None),  
            ("total_cost", (), 2),                          
            ("pay_up_to", (1800), None),
            ("unpaid_cost", (), 2),                         
        ],
    ]

    run_test_cases(test_cases)