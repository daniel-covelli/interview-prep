"""
PROBLEM 4 — Expense Policy Rules Engine
=======================================
Difficulty: medium-hard | Timebox: 60 min (hard stop) — phases 1–2 by minute 35;
phase 3 is the stretch |
Interview frequency: high (Rippling onsite / design-flavored coding round, 2025–2026)

CONTEXT
-------
Rippling Spend issues corporate cards. Finance managers write expense
policies ("no restaurant meal over $75", "a trip may not exceed $2,000")
and every card swipe is checked against them so that violations land in
a review queue — nothing is declined in real time. Companies keep
hundreds of rules and add new ones through an API without an engineer
in the loop, so rules are DATA the engine interprets, never code.

SPEC — PHASE 1 (per-expense rules)
----------------------------------
    flag_expenses(rules: list[dict], expenses: list[dict]) -> list[tuple[str, str]]

- An expense is a dict of string keys to string values. The fields in
  play: "expense_id", "trip_id", "amount_usd" (decimal dollars as text,
  e.g. "49.99"), "expense_type", "vendor_type", "vendor_name".
- A condition is a dict `{"field": <name>, "op": <op>, "value": <v>}`
  with `op` one of "==", "!=", ">", ">=", "<", "<=". "amount_usd" is
  compared as a number — `value` is then dollars, an int or float —
  and every other field as an exact string. An expense that lacks the
  field never matches the condition, whatever the op.
- A rule is `{"id": <rule id>, "when": [<condition>, ...]}` with one or
  more conditions. An expense VIOLATES the rule when every condition in
  `when` matches it.
- Return one `(expense_id, rule_id)` pair per violation: expenses in
  the order given, and for one expense the rules in the order given.
  An expense may violate several rules.

Examples:
    expenses = [
        {"expense_id": "e1", "trip_id": "t1", "amount_usd": "153.00",
         "expense_type": "meal", "vendor_type": "restaurant", "vendor_name": "Nopa"},
        {"expense_id": "e2", "trip_id": "t1", "amount_usd": "49.99",
         "expense_type": "meal", "vendor_type": "restaurant", "vendor_name": "Chipotle"},
        {"expense_id": "e3", "trip_id": "t2", "amount_usd": "1996.00",
         "expense_type": "airfare", "vendor_type": "airline", "vendor_name": "United"},
        {"expense_id": "e4", "trip_id": "t2", "amount_usd": "75.00",
         "expense_type": "meal", "vendor_type": "restaurant", "vendor_name": "Zuni"},
    ]
    rules = [
        {"id": "meal-cap", "when": [{"field": "vendor_type", "op": "==", "value": "restaurant"},
                                    {"field": "amount_usd", "op": ">", "value": 75}]},
        {"id": "no-airfare", "when": [{"field": "expense_type", "op": "==", "value": "airfare"}]},
        {"id": "single-cap", "when": [{"field": "amount_usd", "op": ">", "value": 250}]},
    ]
    flag_expenses(rules, expenses)
    -> [("e1", "meal-cap"), ("e3", "no-airfare"), ("e3", "single-cap")]
       # e4 is exactly $75.00: not OVER 75. e1's "153.00" is more than 75 as a
       # number even though "153.00" < "75" as text.

SPEC — PHASE 2 (per-trip rules)
-------------------------------
    flag_trips(rules: list[dict], expenses: list[dict]) -> list[tuple[str, str]]

- A trip rule is `{"id": <rule id>, "where": [<condition>, ...], "over": <dollars>}`.
  For each trip (the expenses sharing a "trip_id"), add up "amount_usd"
  over the expenses matching EVERY condition in `where` (an empty
  `where` matches all of the trip's expenses). The trip violates the
  rule when that sum is strictly more than `over`.
- Return `(trip_id, rule_id)` pairs: trips in order of their first
  expense in the input, and for one trip the rules in the order given.
- Sums are exact decimal dollars: a trip whose meals add up to exactly
  the limit is not over it, whatever binary floating point makes of
  0.10 + 0.20.

Examples:
    trip_rules = [
        {"id": "trip-cap", "where": [], "over": 2000},
        {"id": "meal-budget", "where": [{"field": "expense_type", "op": "==", "value": "meal"}],
         "over": 200},
    ]
    flag_trips(trip_rules, expenses)              # the four expenses from phase 1
    -> [("t1", "meal-budget"), ("t2", "trip-cap")]
       # t1: meals 153.00 + 49.99 = 202.99 > 200; its total 202.99 is under 2000
       # t2: total 2071.00 > 2000; its meals (75.00) are under 200

    coffees = [{"expense_id": f"c{i}", "trip_id": "t9", "amount_usd": "0.10",
                "expense_type": "meal"} for i in range(3)]
    flag_trips([{"id": "tiny", "where": [], "over": 0.30}], coffees)  -> []       # exactly 0.30 is not over
    flag_trips([{"id": "tiny", "where": [], "over": 0.29}], coffees)  -> [("t9", "tiny")]

SPEC — PHASE 3 (composite conditions)
-------------------------------------
- Anywhere a condition is accepted (a rule's `when`, a trip rule's
  `where`), it may now also be `{"all": [<condition>, ...]}`,
  `{"any": [<condition>, ...]}` or `{"not": <condition>}`, nested to any
  depth. `all` matches when every member matches, `any` when at least
  one member does, `not` when its member does not. `when` and `where`
  lists keep their meaning: every listed condition must match.

Examples:
    rule = {"id": "meal-cap-2", "when": [
        {"field": "amount_usd", "op": ">", "value": 75},
        {"any": [{"field": "expense_type", "op": "==", "value": "meal"},
                 {"field": "vendor_type", "op": "==", "value": "restaurant"}]},
        {"not": {"field": "vendor_name", "op": "==", "value": "Cafeteria"}},
    ]}
    flag_expenses([rule], expenses)               # the four expenses from phase 1
    -> [("e1", "meal-cap-2")]                     # e3 is airfare from an airline; e4 is not over 75
    cafeteria = dict(expenses[0], expense_id="e5", vendor_name="Cafeteria")
    flag_expenses([rule], [cafeteria])            -> []
    flag_trips([{"id": "food", "over": 100, "where": [
        {"any": [{"field": "expense_type", "op": "==", "value": "meal"},
                 {"field": "vendor_type", "op": "==", "value": "restaurant"}]}]}], expenses)
    -> [("t1", "food")]                           # t1's food: 202.99; t2's: 75.00

ASSUMPTIONS DECIDED HERE (rehearse asking them)
-----------------------------------------------
- "amount_usd" always parses as a non-negative decimal with at most two
  places; the ordering ops (">", "<", ...) are only ever applied to it.
  Rule `value`s for it and `over` are ints or floats with at most two
  decimals.
- Ids ("expense_id", "trip_id", rule "id") are unique within their
  kind; every expense has an "expense_id", and every expense handed to
  `flag_trips` has a "trip_id". Other fields may be missing.
- Strings compare exactly (case-sensitive, no trimming). Rules are
  well-formed: the engine never has to validate them.
- Evaluate every rule against every expense: there is no "first match
  wins", and nothing short-circuits the review queue.

DISCUSS AFTERWARDS
------------------
- The grader fixes the return type; the interviewer will not. What
  would a violation record carry so that a reviewer, an audit log and a
  notification service can all consume it, and how do you keep phase
  2's trip violations backward-compatible with phase 1's consumers?
- Tens of thousands of rules against millions of expenses a day: which
  rules can be skipped for a given expense without evaluating them, and
  what would you precompute per trip as expenses stream in?
- Managers want a rule forbidding two expense types on the same trip
  ("no rental car AND rideshare"). Is that a `where` filter, a new rule
  kind, or something else — and what does that say about your data
  model?

TARGET COMPLEXITY
-----------------
O(E * R * C) for E expenses, R rules and C conditions per rule — each
expense is examined once per rule. `flag_trips` must group each expense
into its trip in one pass: re-scanning every expense for every trip is
the naive approach the perf check fails.
"""


def flag_expenses(rules: list[dict], expenses: list[dict]) -> list[tuple[str, str]]:
    raise NotImplementedError


def flag_trips(rules: list[dict], expenses: list[dict]) -> list[tuple[str, str]]:
    raise NotImplementedError
