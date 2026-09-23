"""
PROBLEM 2 — Delivery Cost Tracker
=================================
Difficulty: medium-hard | Timebox: 75 min (hard stop) — phases 1–2 by minute 30,
phase 3 by minute 50; phase 4 is the stretch |
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

SPEC — PHASE 3 (peak concurrency)
---------------------------------
    tracker.peak_active_drivers(now: int) -> int

- The largest number of DISTINCT drivers who were delivering at the
  same instant, over the 24 hours ending at `now` (instants t with
  now - 86400 <= t <= now). A delivery is active on [start, end): it
  counts at its start and no longer counts at its end, so a delivery
  ending exactly when another starts never overlaps it.
- A driver running two overlapping deliveries counts once. Deliveries
  entirely outside the window are ignored; one that straddles the
  window's edge counts for the part inside. 0 when nothing was active.

Examples:
    tracker = DeliveryTracker()
    tracker.add_driver("alice", 1000)
    tracker.add_driver("bob", 1000)
    tracker.add_driver("cy", 1000)
    tracker.record_delivery("alice", 100, 200)
    tracker.record_delivery("bob", 150, 250)
    tracker.record_delivery("cy", 200, 300)        # starts exactly when alice's ends
    tracker.peak_active_drivers(300)      -> 2     # alice+bob during [150, 200); bob+cy during [200, 250)
    tracker.record_delivery("alice", 120, 260)     # alice again, overlapping her own delivery
    tracker.peak_active_drivers(300)      -> 3     # during [200, 250): alice, bob, cy — alice counts once
    tracker.peak_active_drivers(86650)    -> 2     # window starts at 250: bob's delivery ended exactly then
    tracker.peak_active_drivers(90000)    -> 0     # window [3600, 90000]: nothing active

SPEC — PHASE 4 (rate changes)
-----------------------------
    tracker.update_rate(driver_id: str, rate_cents_per_hour: int, effective_from: int) -> None

- A driver's rate becomes a history: `add_driver` sets the rate in
  force from time 0, and each `update_rate` adds a rate in force from
  `effective_from` until the next later effective time. Updates may
  arrive in any order (a raise can be back-dated); an update whose
  `effective_from` is already in the history replaces that entry.
- A delivery is billed at the rate in force at its `start`, even if the
  rate changes mid-delivery. Its cost is fixed when recorded: a later
  or back-dated `update_rate` never re-prices it.

Examples:
    tracker = DeliveryTracker()
    tracker.add_driver("alice", 1000)              # 1000/h from time 0
    tracker.update_rate("alice", 2000, 7200)       # 2000/h from t = 7200
    tracker.record_delivery("alice", 3600, 7200)   # starts before the raise: 1000
    tracker.record_delivery("alice", 7200, 10800)  # starts exactly at the raise: 2000
    tracker.record_delivery("alice", 5400, 9000)   # spans the raise: the rate at its START applies: 1000
    tracker.total_cost()          -> 4000
    tracker.update_rate("alice", 3000, 0)          # back-dated: replaces the rate in force from time 0
    tracker.record_delivery("alice", 0, 3600)      # recorded after the update: 3000
    tracker.total_cost()          -> 7000          # the three earlier deliveries keep their costs
    tracker.update_rate("alice", 1500, 3600)       # in force from 3600 until the 7200 entry
    tracker.record_delivery("alice", 5000, 5600)   # in force at 5000: the 1500/h entry -> 250
    tracker.total_cost()          -> 7250

ASSUMPTIONS DECIDED HERE (rehearse asking them)
-----------------------------------------------
- Money is integer cents in and out; rates are whole cents per hour.
  Costs may be fractional cents internally; only the two report calls
  round. Binary floating point is not exact enough for this service —
  the grader includes a total it gets wrong.
- Every `driver_id` passed to `record_delivery`/`update_rate` was
  registered with `add_driver` first, and `add_driver` is called once
  per driver. Timestamps are non-negative integers.
- Deliveries are reported after they finish but not necessarily in
  order of `end` — a late report may end earlier than one already
  recorded (the payout examples rely on this).
- Deliveries are never edited or cancelled. `now` in phase 3 is any
  timestamp; only what was active at instants up to `now` counts.
  Single process, single thread.

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
`peak_active_drivers` in O(n log n) for the n recorded deliveries — it
must not step through the window second by second. Phase 4: finding the
rate in force at a delivery's start must not scan the driver's whole
rate history (O(log versions) per delivery).
"""


class DeliveryTracker:
    def __init__(self) -> None:
        raise NotImplementedError

    def add_driver(self, driver_id: str, rate_cents_per_hour: int) -> None:
        raise NotImplementedError

    def record_delivery(self, driver_id: str, start: int, end: int) -> None:
        raise NotImplementedError

    def total_cost(self) -> int:
        raise NotImplementedError

    def pay_up_to(self, pay_time: int) -> None:
        raise NotImplementedError

    def unpaid_cost(self) -> int:
        raise NotImplementedError

    def peak_active_drivers(self, now: int) -> int:
        raise NotImplementedError

    def update_rate(self, driver_id: str, rate_cents_per_hour: int, effective_from: int) -> None:
        raise NotImplementedError
