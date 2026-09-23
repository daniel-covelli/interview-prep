# Grader for Rippling Problem 4 (rippling/p4_expense_rules.py).
# SPOILER WARNING: this file enumerates edge cases and contains a brute-force
# oracle and the reference solution. Run it, don't read it.
import random
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from grader import (Suite, PerfConcern, Failure, load_fn, bench, fmt_s,
                    expect, desc)

SEED = 0xE85E

# Reference solution, printed by `uv run grade --reveal rippling/p4_expense_rules`
# once the timebox is up. Never read it before then.
REFERENCE = '''
from decimal import Decimal
import operator

_OPS = {"==": operator.eq, "!=": operator.ne, ">": operator.gt,
        ">=": operator.ge, "<": operator.lt, "<=": operator.le}


def _dollars(v):
    return Decimal(str(v))                  # exact: "0.10" and 0.1 both become 0.10


def _matches(cond, expense):
    if "all" in cond:                        # phase 3: composite conditions
        return all(_matches(c, expense) for c in cond["all"])
    if "any" in cond:
        return any(_matches(c, expense) for c in cond["any"])
    if "not" in cond:
        return not _matches(cond["not"], expense)
    field = cond["field"]
    if field not in expense:                 # a missing field never matches
        return False
    actual, value = expense[field], cond["value"]
    if field == "amount_usd":
        actual, value = _dollars(actual), _dollars(value)
    return _OPS[cond["op"]](actual, value)


def flag_expenses(rules, expenses):
    return [(e["expense_id"], r["id"])
            for e in expenses
            for r in rules
            if all(_matches(c, e) for c in r["when"])]


def flag_trips(rules, expenses):
    trips = {}                               # trip_id -> its expenses, first-seen order
    for e in expenses:
        trips.setdefault(e["trip_id"], []).append(e)
    out = []
    for trip_id, items in trips.items():
        for r in rules:
            total = sum((_dollars(e["amount_usd"]) for e in items
                         if all(_matches(c, e) for c in r["where"])), Decimal(0))
            if total > _dollars(r["over"]):
                out.append((trip_id, r["id"]))
    return out
'''


# ---- brute-force oracle -------------------------------------------------------


def measure(fn, diagnosis, repeat=2):
    """bench() that attaches the case's diagnosis to a TLE, so a workload
    that never finishes still names the naive design being caught."""
    try:
        return bench(fn, repeat=repeat)
    except AssertionError as e:
        raise AssertionError(f"{diagnosis}  [{e}]") from None

def _dec(v):
    return Decimal(str(v))


def oracle_match(cond, e):
    if "all" in cond:
        return all(oracle_match(c, e) for c in cond["all"])
    if "any" in cond:
        return any(oracle_match(c, e) for c in cond["any"])
    if "not" in cond:
        return not oracle_match(cond["not"], e)
    f = cond["field"]
    if f not in e:
        return False
    a, v = e[f], cond["value"]
    if f == "amount_usd":
        a, v = _dec(a), _dec(v)
    op = cond["op"]
    if op == "==":
        return a == v
    if op == "!=":
        return a != v
    if op == ">":
        return a > v
    if op == ">=":
        return a >= v
    if op == "<":
        return a < v
    return a <= v


def oracle_expenses(rules, expenses):
    out = []
    for e in expenses:
        for r in rules:
            if all(oracle_match(c, e) for c in r["when"]):
                out.append((e["expense_id"], r["id"]))
    return out


def oracle_trips(rules, expenses):
    """Naive by design: re-scans every expense for each trip."""
    trip_ids = []
    for e in expenses:
        if e["trip_id"] not in trip_ids:
            trip_ids.append(e["trip_id"])
    out = []
    for trip in trip_ids:
        for r in rules:
            total = Decimal(0)
            for e in expenses:
                if e["trip_id"] == trip and all(oracle_match(c, e) for c in r["where"]):
                    total += _dec(e["amount_usd"])
            if total > _dec(r["over"]):
                out.append((trip, r["id"]))
    return out


# ---- shared fixtures ------------------------------------------------------------

def spec_expenses():
    return [
        {"expense_id": "e1", "trip_id": "t1", "amount_usd": "153.00",
         "expense_type": "meal", "vendor_type": "restaurant", "vendor_name": "Nopa"},
        {"expense_id": "e2", "trip_id": "t1", "amount_usd": "49.99",
         "expense_type": "meal", "vendor_type": "restaurant", "vendor_name": "Chipotle"},
        {"expense_id": "e3", "trip_id": "t2", "amount_usd": "1996.00",
         "expense_type": "airfare", "vendor_type": "airline", "vendor_name": "United"},
        {"expense_id": "e4", "trip_id": "t2", "amount_usd": "75.00",
         "expense_type": "meal", "vendor_type": "restaurant", "vendor_name": "Zuni"},
    ]


def cond(field, op, value):
    return {"field": field, "op": op, "value": value}


def rule(rid, *conds):
    return {"id": rid, "when": list(conds)}


def trip_rule(rid, over, *conds):
    return {"id": rid, "where": list(conds), "over": over}


TYPES = ["meal", "airfare", "lodging", "taxi", "office"]
VENDOR_TYPES = ["restaurant", "airline", "hotel", "rideshare", "retail"]
VENDORS = ["Nopa", "United", "Marriott", "Uber", "Staples", "Cafeteria"]
FIELDS = ["amount_usd", "expense_type", "vendor_type", "vendor_name"]


def random_expense(rng, i, trips):
    e = {"expense_id": f"e{i}", "trip_id": rng.choice(trips),
         "amount_usd": f"{rng.randrange(0, 30_000) / 100:.2f}"}
    for field, pool in (("expense_type", TYPES), ("vendor_type", VENDOR_TYPES),
                        ("vendor_name", VENDORS)):
        if rng.random() < 0.85:             # some fields are missing on purpose
            e[field] = rng.choice(pool)
    return e


def random_leaf(rng):
    field = rng.choice(FIELDS)
    if field == "amount_usd":
        op = rng.choice(["==", "!=", ">", ">=", "<", "<="])
        value = rng.choice([rng.randrange(0, 300), rng.randrange(0, 30_000) / 100])
    else:
        op = rng.choice(["==", "!="])
        pool = {"expense_type": TYPES, "vendor_type": VENDOR_TYPES, "vendor_name": VENDORS}[field]
        value = rng.choice(pool + ["nope"])
    return cond(field, op, value)


def random_cond(rng, depth=0):
    roll = rng.random()
    if depth >= 2 or roll < 0.55:
        return random_leaf(rng)
    if roll < 0.7:
        return {"all": [random_cond(rng, depth + 1) for _ in range(rng.randrange(1, 3))]}
    if roll < 0.85:
        return {"any": [random_cond(rng, depth + 1) for _ in range(rng.randrange(1, 3))]}
    return {"not": random_cond(rng, depth + 1)}


# ---- function-shaped checking with shrinking ------------------------------------

def run(fn, rules, expenses):
    """Call the solution on private copies; a crash reads as a mismatch."""
    try:
        return fn([dict(r) for r in rules], [dict(e) for e in expenses])
    except NotImplementedError:
        raise                                    # a stub: the case is skipped, not failed
    except Exception as e:                       # noqa: BLE001 — report, don't hide
        return desc(f"raised {type(e).__name__}: {e}")


def shrink(fn, oracle, rules, expenses, key):
    """Delta-debug a failing input down to a minimal one that still
    mismatches: drop expenses, then rules, then single conditions."""
    def fails(rs, es):
        return run(fn, rs, es) != oracle(rs, es)

    def reductions(rs, es):
        for i in range(len(es)):
            yield rs, es[:i] + es[i + 1:]
        for i in range(len(rs)):
            yield rs[:i] + rs[i + 1:], es
        for i, r in enumerate(rs):
            conds = r[key]
            for j in range(len(conds)):
                if key == "where" or len(conds) > 1:
                    yield rs[:i] + [dict(r, **{key: conds[:j] + conds[j + 1:]})] + rs[i + 1:], es

    progress = True
    while progress:
        progress = False
        for cand in reductions(rules, expenses):
            if fails(*cand):
                rules, expenses = cand
                progress = True
                break
    return rules, expenses


def check(fn, oracle, rules, expenses, key, ctx):
    got = run(fn, rules, expenses)
    want = oracle(rules, expenses)
    if got == want:
        return
    n_r, n_e = len(rules), len(expenses)
    sr, se = shrink(fn, oracle, rules, expenses, key)
    raise Failure(output=run(fn, sr, se), expected=oracle(sr, se),
                  note=f"MINIMAL REPRO: {fn.__name__}({sr!r}, {se!r})  "
                       f"[shrunk from {ctx}: {n_r} rules, {n_e} expenses]")


def main():
    suite = Suite("Rippling 4: expense rules")
    flag_expenses, err = load_fn("rippling.p4_expense_rules", "flag_expenses")
    if flag_expenses is None:
        suite.skip_all(err)
        return suite.summary()
    flag_trips, terr = load_fn("rippling.p4_expense_rules", "flag_trips")

    def trips_or_skip():
        if flag_trips is None:
            raise NotImplementedError
        return flag_trips

    def composite_or_skip(fn):
        """Phase 3 is the same function: probe it with a `not` condition. A
        KeyError (phase 1-2 code reading cond['field']) or a probe that comes
        back empty (a composite silently read as 'no match') means not built."""
        try:
            got = fn([rule("probe", {"not": cond("expense_id", "==", "zzz")})],
                     [{"expense_id": "x", "trip_id": "t"}])
        except KeyError:
            raise NotImplementedError from None
        if got == []:
            raise NotImplementedError

    suite.section("PHASE 1 — PER-EXPENSE RULES")

    def spec_example():
        rules = [rule("meal-cap", cond("vendor_type", "==", "restaurant"), cond("amount_usd", ">", 75)),
                 rule("no-airfare", cond("expense_type", "==", "airfare")),
                 rule("single-cap", cond("amount_usd", ">", 250))]
        expect(flag_expenses(rules, spec_expenses()),
               [("e1", "meal-cap"), ("e3", "no-airfare"), ("e3", "single-cap")],
               note="e4 is exactly 75.00 (not over); e1's 153.00 is over 75 as a number")
    suite.case("spec example from the file header", spec_example)

    def numeric_not_lexicographic():
        es = [{"expense_id": "a", "amount_usd": "153.00"},
              {"expense_id": "b", "amount_usd": "9.99"},
              {"expense_id": "c", "amount_usd": "10.00"},
              {"expense_id": "d", "amount_usd": "1000.50"}]
        expect(flag_expenses([rule("r", cond("amount_usd", ">", 75))], es),
               [("a", "r"), ("d", "r")],
               note='as text "153.00" < "75" and "9.99" > "10.00": amounts compare as numbers')
        expect(flag_expenses([rule("r", cond("amount_usd", "<", 10))], es), [("b", "r")])
        expect(flag_expenses([rule("r", cond("amount_usd", "==", 1000.5))], es), [("d", "r")],
               note="a float value equal to the text amount matches with ==")
    suite.case("amount_usd compares numerically, never as text", numeric_not_lexicographic)

    def every_op():
        es = [{"expense_id": "lo", "amount_usd": "74.99", "vendor_type": "restaurant"},
              {"expense_id": "eq", "amount_usd": "75.00", "vendor_type": "airline"},
              {"expense_id": "hi", "amount_usd": "75.01", "vendor_type": "restaurant"}]
        for op, want in [(">", ["hi"]), (">=", ["eq", "hi"]), ("<", ["lo"]),
                         ("<=", ["lo", "eq"]), ("==", ["eq"]), ("!=", ["lo", "hi"])]:
            expect(flag_expenses([rule("r", cond("amount_usd", op, 75))], es),
                   [(x, "r") for x in want], note=f"amount_usd {op} 75 at the boundary")
        expect(flag_expenses([rule("r", cond("vendor_type", "==", "restaurant"))], es),
               [("lo", "r"), ("hi", "r")])
        expect(flag_expenses([rule("r", cond("vendor_type", "!=", "restaurant"))], es),
               [("eq", "r")])
        expect(flag_expenses([rule("r", cond("vendor_type", "==", "Restaurant"))], es), [],
               note="strings compare exactly: case matters")
    suite.case("every op at the boundary; string fields compare exactly", every_op)

    def missing_fields():
        es = [{"expense_id": "bare", "trip_id": "t"},
              {"expense_id": "full", "trip_id": "t", "amount_usd": "5.00", "vendor_name": "Uber"}]
        expect(flag_expenses([rule("r", cond("vendor_name", "!=", "Nopa"))], es), [("full", "r")],
               note="an expense without the field never matches — not even with !=")
        expect(flag_expenses([rule("r", cond("amount_usd", "<", 100))], es), [("full", "r")])
        expect(flag_expenses([rule("r", cond("vendor_name", "==", "Uber"),
                                   cond("amount_usd", "<=", 5))], es), [("full", "r")],
               note="every condition in `when` must match; 'bare' matches neither")
    suite.case("a missing field never matches, whatever the op", missing_fields)

    def output_order_and_multiples():
        es = [{"expense_id": "x", "amount_usd": "500.00", "expense_type": "airfare"},
              {"expense_id": "y", "amount_usd": "20.00", "expense_type": "meal"},
              {"expense_id": "z", "amount_usd": "300.00", "expense_type": "airfare"}]
        rules = [rule("cap", cond("amount_usd", ">", 250)),
                 rule("air", cond("expense_type", "==", "airfare")),
                 rule("both", cond("expense_type", "==", "airfare"), cond("amount_usd", ">", 400))]
        expect(flag_expenses(rules, es),
               [("x", "cap"), ("x", "air"), ("x", "both"), ("z", "cap"), ("z", "air")],
               note="grouped by expense in input order; within an expense, rules in rule order")
        expect(flag_expenses([], es), [], note="no rules: nothing is flagged")
        expect(flag_expenses(rules, []), [], note="no expenses: nothing is flagged")
    suite.case("output order: by expense, then by rule; several violations per expense",
               output_order_and_multiples)

    def randomized_expenses():
        rng = random.Random(SEED)
        for trial in range(200):
            trips = [f"t{i}" for i in range(rng.randrange(1, 4))]
            es = [random_expense(rng, i, trips) for i in range(rng.randrange(0, 8))]
            rules = [rule(f"r{i}", *[random_leaf(rng) for _ in range(rng.randrange(1, 4))])
                     for i in range(rng.randrange(0, 4))]
            check(flag_expenses, oracle_expenses, rules, es, "when",
                  ctx=f"seed={SEED:#x}, trial={trial}")
    suite.case("randomized: 200 rule sets x expense lists vs brute-force oracle",
               randomized_expenses)

    suite.section("PHASE 2 — PER-TRIP RULES (skipped until you build it)")

    def spec_example_trips():
        ft = trips_or_skip()
        trip_rules = [trip_rule("trip-cap", 2000),
                      trip_rule("meal-budget", 200, cond("expense_type", "==", "meal"))]
        expect(ft(trip_rules, spec_expenses()), [("t1", "meal-budget"), ("t2", "trip-cap")],
               note="t1: meals 202.99 > 200, total under 2000; t2: total 2071.00 > 2000")
        coffees = [{"expense_id": f"c{i}", "trip_id": "t9", "amount_usd": "0.10",
                    "expense_type": "meal"} for i in range(3)]
        expect(ft([trip_rule("tiny", 0.30)], coffees), [],
               note="0.10 + 0.10 + 0.10 is EXACTLY 0.30, not over 0.30 — binary floats "
                    "say 0.30000000000000004 and flag it")
        expect(ft([trip_rule("tiny", 0.29)], coffees), [("t9", "tiny")])
    suite.case("spec example from the file header", spec_example_trips)

    def exact_sums():
        ft = trips_or_skip()
        es = [{"expense_id": f"e{i}", "trip_id": "t", "amount_usd": a}
              for i, a in enumerate(["0.10", "0.20", "0.70", "1000.00"])]
        expect(ft([trip_rule("r", 1001)], es), [], note="sum is exactly 1001.00: not over")
        expect(ft([trip_rule("r", 1000.99)], es), [("t", "r")])
        expect(ft([trip_rule("r", 1.00, cond("amount_usd", "<", 1))], es), [],
               note="filtered sum 0.10 + 0.20 + 0.70 is exactly 1.00")
        expect(ft([trip_rule("r", 0.99, cond("amount_usd", "<", 1))], es), [("t", "r")])
    suite.case("trip sums are exact decimal dollars", exact_sums)

    def trip_order_and_filters():
        ft = trips_or_skip()
        es = [{"expense_id": "1", "trip_id": "t2", "amount_usd": "50.00", "expense_type": "meal"},
              {"expense_id": "2", "trip_id": "t1", "amount_usd": "80.00", "expense_type": "taxi"},
              {"expense_id": "3", "trip_id": "t2", "amount_usd": "60.00", "expense_type": "meal"},
              {"expense_id": "4", "trip_id": "t1", "amount_usd": "70.00", "expense_type": "meal"},
              {"expense_id": "5", "trip_id": "t3", "amount_usd": "1.00"}]
        rules = [trip_rule("total", 100),
                 trip_rule("meals", 65, cond("expense_type", "==", "meal")),
                 trip_rule("taxis", 0, cond("expense_type", "==", "taxi"))]
        expect(ft(rules, es), [("t2", "total"), ("t2", "meals"), ("t1", "total"), ("t1", "meals"),
                               ("t1", "taxis")],
               note="trips in order of FIRST appearance (t2 before t1); t3's 1.00 is under "
                    "every limit; t3 has no taxi, so 0 is not over 0")
        expect(ft([trip_rule("none", 0, cond("expense_type", "==", "lodging"))], es), [],
               note="a filter nothing matches sums to 0")
        expect(ft([], es), [], note="no rules")
        expect(ft(rules, []), [], note="no expenses: no trips")
    suite.case("trips ordered by first appearance; `where` filters the sum", trip_order_and_filters)

    def randomized_trips():
        ft = trips_or_skip()
        rng = random.Random(SEED + 1)
        for trial in range(200):
            trips = [f"t{i}" for i in range(rng.randrange(1, 4))]
            es = [random_expense(rng, i, trips) for i in range(rng.randrange(0, 9))]
            rules = [trip_rule(f"r{i}", rng.choice([rng.randrange(0, 600), rng.randrange(0, 60_000) / 100]),
                               *[random_leaf(rng) for _ in range(rng.randrange(0, 3))])
                     for i in range(rng.randrange(0, 4))]
            check(ft, oracle_trips, rules, es, "where", ctx=f"seed={SEED:#x}, trial={trial}")
    suite.case("randomized: 200 trip-rule sets x expense lists vs brute-force oracle",
               randomized_trips)

    suite.section("PHASE 3 — COMPOSITE CONDITIONS (skipped until you build it)")

    def spec_example_composite():
        composite_or_skip(flag_expenses)
        r = {"id": "meal-cap-2", "when": [
            cond("amount_usd", ">", 75),
            {"any": [cond("expense_type", "==", "meal"), cond("vendor_type", "==", "restaurant")]},
            {"not": cond("vendor_name", "==", "Cafeteria")}]}
        es = spec_expenses()
        expect(flag_expenses([r], es), [("e1", "meal-cap-2")],
               note="e3 is airfare from an airline (fails `any`); e4 is not over 75")
        cafeteria = dict(es[0], expense_id="e5", vendor_name="Cafeteria")
        expect(flag_expenses([r], [cafeteria]), [], note="the `not` excludes the cafeteria")
        ft = trips_or_skip()
        food = trip_rule("food", 100, {"any": [cond("expense_type", "==", "meal"),
                                               cond("vendor_type", "==", "restaurant")]})
        expect(ft([food], es), [("t1", "food")], note="t1's food: 202.99; t2's: 75.00")
    suite.case("spec example from the file header", spec_example_composite)

    def nesting():
        composite_or_skip(flag_expenses)
        es = [{"expense_id": "a", "amount_usd": "10.00", "expense_type": "meal", "vendor_name": "Nopa"},
              {"expense_id": "b", "amount_usd": "10.00", "expense_type": "taxi", "vendor_name": "Uber"},
              {"expense_id": "c", "amount_usd": "90.00", "expense_type": "meal"}]
        deep = {"all": [{"not": {"any": [cond("expense_type", "==", "taxi"),
                                         cond("amount_usd", ">=", 50)]}},
                        {"any": [cond("vendor_name", "==", "Nopa"), {"not": cond("amount_usd", ">", 5)}]}]}
        expect(flag_expenses([rule("deep", deep)], es), [("a", "deep")],
               note="a: not(taxi or >=50) and (Nopa or not >5) -> True; b is a taxi; c is >= 50")
        expect(flag_expenses([rule("nn", {"not": {"not": cond("expense_type", "==", "meal")}})], es),
               [("a", "nn"), ("c", "nn")], note="a double negation")
        expect(flag_expenses([rule("miss", {"not": cond("vendor_name", "==", "Uber")})], es),
               [("a", "miss"), ("c", "miss")],
               note="c has no vendor_name: the leaf never matches, so its `not` DOES")
        expect(flag_expenses([rule("mix", cond("amount_usd", "<", 50),
                                   {"any": [cond("vendor_name", "==", "Uber"), cond("expense_type", "==", "meal")]})], es),
               [("a", "mix"), ("b", "mix")],
               note="a leaf and a composite side by side in `when`: both must match")
    suite.case("nested all/any/not, double negation, `not` over a missing field", nesting)

    def randomized_composite():
        composite_or_skip(flag_expenses)
        rng = random.Random(SEED + 2)
        for trial in range(200):
            trips = [f"t{i}" for i in range(rng.randrange(1, 3))]
            es = [random_expense(rng, i, trips) for i in range(rng.randrange(0, 7))]
            rules = [rule(f"r{i}", *[random_cond(rng) for _ in range(rng.randrange(1, 3))])
                     for i in range(rng.randrange(0, 4))]
            check(flag_expenses, oracle_expenses, rules, es, "when",
                  ctx=f"seed={SEED:#x}, composite trial={trial}")
            if flag_trips is not None:
                trules = [trip_rule(f"g{i}", rng.randrange(0, 400),
                                    *[random_cond(rng) for _ in range(rng.randrange(0, 3))])
                          for i in range(rng.randrange(0, 3))]
                check(flag_trips, oracle_trips, trules, es, "where",
                      ctx=f"seed={SEED:#x}, composite trip trial={trial}")
    suite.case("randomized: 200 composite rule sets (and trip rules) vs brute-force oracle",
               randomized_composite)

    if suite.failed or not suite.passed:
        suite.section("PERFORMANCE")
        reason = ("fix correctness failures first" if suite.failed
                  else "nothing implemented yet")
        suite.skip("all performance checks", reason)
        return suite.summary()

    suite.section("PERFORMANCE")
    raw_expenses = flag_expenses.__wrapped__

    def big_expenses(n, n_trips):
        rng = random.Random(SEED)
        trips = [f"t{i}" for i in range(n_trips)]
        return [random_expense(rng, i, trips) for i in range(n)]

    def trip_scaling():
        if flag_trips is None:
            raise NotImplementedError
        raw_trips = flag_trips.__wrapped__
        diagnosis = ("flag_trips is re-scanning the whole expense list for every "
                     "trip. Target: O(E * R) — group the expenses by trip in ONE "
                     "pass, then evaluate each trip's rules over just its own expenses.")
        rules = [trip_rule("cap", 5000), trip_rule("meals", 300, cond("expense_type", "==", "meal")),
                 trip_rule("air", 1000, cond("vendor_type", "==", "airline"))]
        small, big = big_expenses(2_000, 500), big_expenses(8_000, 2_000)
        t_small = measure(lambda: [raw_trips(rules, small) for _ in range(4)], diagnosis)
        t_big = measure(lambda: [raw_trips(rules, big) for _ in range(4)], diagnosis)
        ratio = t_big / max(t_small, 1e-9)
        suite.info(f"4 x (2k expenses / 500 trips): {fmt_s(t_small)}   "
                   f"4 x (8k expenses / 2k trips): {fmt_s(t_big)}   "
                   f"ratio {ratio:.1f}x (linear ≈ 4x)")
        assert ratio < 10, \
            f"4x the expenses (and trips) made flag_trips {ratio:.1f}x slower — {diagnosis}"
    suite.case("flag_trips groups in one pass: cost stays linear in expenses x rules",
               trip_scaling)

    def expense_scaling():
        diagnosis = ("each expense must be examined once per rule and nothing else "
                     "should grow with the list. Target: O(E * R * C).")
        rules = [rule(f"r{i}", cond("amount_usd", ">", 50 * i), cond("expense_type", "==", TYPES[i % 5]))
                 for i in range(10)]
        small, big = big_expenses(2_000, 100), big_expenses(8_000, 100)
        t_small = measure(lambda: [raw_expenses(rules, small) for _ in range(2)], diagnosis)
        t_big = measure(lambda: [raw_expenses(rules, big) for _ in range(2)], diagnosis)
        ratio = t_big / max(t_small, 1e-9)
        suite.info(f"2 x (2k expenses x 10 rules): {fmt_s(t_small)}   "
                   f"2 x (8k x 10): {fmt_s(t_big)}   ratio {ratio:.1f}x (linear ≈ 4x)")
        assert ratio < 10, \
            f"4x the expenses made flag_expenses {ratio:.1f}x slower — {diagnosis}"
    suite.case("flag_expenses cost is linear in expenses x rules", expense_scaling)

    def note_followups():
        raise PerfConcern(
            "not machine-checkable: the DISCUSS AFTERWARDS tail. Rehearse the "
            "return-type design (rule id, expense/trip id, actual vs limit, "
            "contributing expense ids, a message — additive fields keep phase 1 "
            "consumers working), skipping rules cheaply (group rules by the "
            "fields they test; most never match an expense's type), per-trip "
            "running sums as expenses stream in, and the 'no A and B on one "
            "trip' rule (a new aggregate kind, not a `where` filter).")
    suite.case("return-type / rule-indexing / streaming-aggregation story", note_followups)

    return suite.summary()


if __name__ == "__main__":
    sys.exit(1 if main().failed else 0)
