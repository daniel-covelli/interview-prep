# Grader for Harvey Problem 1 (harvey/p1_spreadsheet.py).
# SPOILER WARNING: this file enumerates edge cases and contains a brute-force
# oracle and the reference solution. Run it, don't read it.
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from grader import (Suite, PerfConcern, Failure, load_class, bench, fmt_s,
                    tracing, expect, expect_raises, desc)

SEED = 0x5EE7

# Reference solution, printed by `uv run grade --reveal harvey/p1_spreadsheet`
# once the timebox is up. Never read it before then.
REFERENCE = '''
class CycleError(Exception):
    pass


class Spreadsheet:
    def __init__(self) -> None:
        self.terms = {}      # cell -> its terms, e.g. ["A1", "2"]

    def set_cell(self, cell: str, text: str) -> None:
        terms = text.removeprefix("=").split("+")
        # would `cell` end up reading itself? walk everything the new terms read
        todo, seen = [t for t in terms if not t.isdigit()], set()
        while todo:
            c = todo.pop()
            if c == cell:
                raise CycleError(cell)
            if c not in seen:
                seen.add(c)
                todo.extend(t for t in self.terms.get(c, []) if not t.isdigit())
        self.terms[cell] = terms             # only stored once it is known to be safe

    def get_cell(self, cell: str) -> int:
        return sum(int(t) if t.isdigit() else self.get_cell(t)
                   for t in self.terms.get(cell, []))
'''


class Oracle:
    """Brute-force truth: keep every cell's terms and re-evaluate the whole
    sheet from scratch whenever anything is asked."""

    def __init__(self):
        self.terms = {}                       # cell -> list of terms (str)

    @staticmethod
    def parse(text):
        return text.removeprefix("=").split("+")

    def value(self, cell):
        return sum(int(t) if t.isdigit() else self.value(t)
                   for t in self.terms.get(cell, ["0"]))

    def loop_through(self, cell, text):
        """The loop storing `text` in `cell` would close, as
        ["A1", "B1", "A1"], or None if there is none."""
        def walk(c, path):
            for t in self.parse(text) if c == cell else self.terms.get(c, []):
                if t.isdigit():
                    continue
                if t == cell:
                    return path + [t]
                if t not in path:
                    found = walk(t, path + [t])
                    if found:
                        return found
            return None
        return walk(cell, [cell])

    def set(self, cell, text):
        self.terms[cell] = self.parse(text)


CELLS = ["A1", "A2", "B1", "B2", "C1", "C2"]


def random_text(rng):
    if rng.random() < 0.3:
        return str(rng.randrange(0, 10))
    terms = [rng.choice(CELLS) if rng.random() < 0.75 else str(rng.randrange(0, 6))
             for _ in range(rng.randrange(1, 4))]
    return "=" + "+".join(terms)


def main():
    suite = Suite("Harvey 1: Spreadsheet")
    cls, err = load_class("harvey.p1_spreadsheet", "Spreadsheet")
    cycle_error, err2 = load_class("harvey.p1_spreadsheet", "CycleError")
    if cls is None or cycle_error is None:
        suite.skip_all(err or err2)
        return suite.summary()
    make = tracing(cls)

    # ---- phase probes: a later phase's cases skip until it is started -------
    def probe(fn):
        try:
            return fn(cls())
        except NotImplementedError:
            return None
        except Exception as e:                      # noqa: BLE001
            return e

    p2 = probe(lambda s: s.set_cell("P1", "=P1+1"))
    phase2 = isinstance(p2, Exception)              # raised: phase 2 started

    def needs_phase2(fn):
        def run():
            if not phase2:
                raise NotImplementedError
            fn()
        return run

    def set_ok(s, cell, text, note=None):
        """set_cell that must NOT be rejected."""
        try:
            return s.set_cell(cell, text)
        except cycle_error:
            raise Failure(output=desc("raised CycleError"),
                          expected=desc(f"no error: storing {text!r} in {cell} "
                                        f"creates no loop"), note=note) from None

    def rejected(s, cell, text, note):
        expect_raises(cycle_error, lambda: s.set_cell(cell, text), note=note)

    # ---- PHASE 1 -----------------------------------------------------------
    suite.section("CORRECTNESS — PHASE 1 (numbers and formulas)")

    def spec_example():
        s = make()
        s.set_cell("A1", "5")
        s.set_cell("B1", "=A1+2")
        expect(s.get_cell("B1"), 7)
        s.set_cell("C1", "=A1+B1+A1")
        expect(s.get_cell("C1"), 17, note="5 + 7 + 5: A1 is referenced twice")
        s.set_cell("A1", "10")
        expect(s.get_cell("B1"), 12)
        expect(s.get_cell("C1"), 32, note="A1 changes C1 directly and through B1")
        expect(s.get_cell("Z9"), 0, note="never set")
        s.set_cell("D1", "=E1+1")
        expect(s.get_cell("D1"), 1, note="E1 is not set yet: reads 0")
        s.set_cell("E1", "=A1")
        expect(s.get_cell("D1"), 11)
        s.set_cell("B1", "4")
        expect(s.get_cell("C1"), 24, note="B1 became a plain number: 10 + 4 + 10")
    suite.case("spec example from the file header", spec_example)

    def numbers_only():
        s = make()
        expect(s.get_cell("A1"), 0, note="empty sheet")
        s.set_cell("A1", "0")
        expect(s.get_cell("A1"), 0)
        s.set_cell("A1", "42")
        expect(s.get_cell("A1"), 42, note="setting again replaces the number")
        s.set_cell("B1", "=1+2+3")
        expect(s.get_cell("B1"), 6, note="a formula of numbers only")
        s.set_cell("C1", "=7")
        expect(s.get_cell("C1"), 7, note="a formula with a single number term")
        s.set_cell("AB12", "9")
        s.set_cell("ZZ999", "=AB12+1")
        expect(s.get_cell("ZZ999"), 10, note="multi-letter, multi-digit cell names")
    suite.case("plain numbers, number-only formulas, longer cell names", numbers_only)

    def replaced_formula_forgets_old_refs():
        s = make()
        s.set_cell("A1", "1")
        s.set_cell("C1", "100")
        s.set_cell("B1", "=A1+1")
        expect(s.get_cell("B1"), 2)
        s.set_cell("B1", "=C1+1")
        expect(s.get_cell("B1"), 101)
        s.set_cell("A1", "50")
        expect(s.get_cell("B1"), 101, note="B1 no longer references A1")
        s.set_cell("C1", "200")
        expect(s.get_cell("B1"), 201, note="B1 now follows C1")
        s.set_cell("B1", "3")
        s.set_cell("C1", "0")
        expect(s.get_cell("B1"), 3, note="B1 is a plain number now: it follows nothing")
    suite.case("replacing a formula drops what the old one referenced",
               replaced_formula_forgets_old_refs)

    def chains_and_diamonds():
        s = make()
        s.set_cell("A1", "1")
        s.set_cell("B1", "=A1+1")
        s.set_cell("C1", "=B1+1")
        s.set_cell("D1", "=C1+1")
        expect(s.get_cell("D1"), 4, note="chain D1 <- C1 <- B1 <- A1")
        s.set_cell("A1", "10")
        expect(s.get_cell("D1"), 13, note="an edit at the start of a chain reaches its end")
        s.set_cell("L1", "=A1")
        s.set_cell("R1", "=A1+5")
        s.set_cell("J1", "=L1+R1")
        expect(s.get_cell("J1"), 25, note="J1 reads A1 through two routes: L1 and R1")
        s.set_cell("A1", "0")
        expect(s.get_cell("J1"), 5)
        expect(s.get_cell("D1"), 3)
    suite.case("edits flow down chains and through several routes", chains_and_diamonds)

    def unset_then_set():
        s = make()
        s.set_cell("B1", "=A1+A1+1")
        expect(s.get_cell("B1"), 1, note="A1 unset: both terms read 0")
        s.set_cell("A1", "=C1+2")
        expect(s.get_cell("B1"), 5, note="A1 = C1 + 2 = 2 (C1 unset)")
        s.set_cell("C1", "3")
        expect(s.get_cell("B1"), 11, note="A1 = 5 now, so B1 = 5 + 5 + 1")
        expect(s.get_cell("A1"), 5)
    suite.case("formulas over cells that get set later", unset_then_set)

    def randomized_phase1():
        # many short rounds, fresh sheet each: a failure replays every call.
        # Formulas that would close a loop are swapped for a number, so this
        # case needs no phase 2.
        for rnd in range(60):
            rng = random.Random(SEED + rnd)
            s, o = make(), Oracle()
            ctx = f"seed={SEED:#x}, round={rnd}"
            for op in range(30):
                cell = rng.choice(CELLS)
                if rng.random() < 0.6:
                    text = random_text(rng)
                    if o.loop_through(cell, text):
                        text = str(rng.randrange(0, 10))
                    s.set_cell(cell, text)
                    o.set(cell, text)
                else:
                    expect(s.get_cell(cell), o.value(cell), note=f"{ctx}, op={op}")
            for cell in CELLS:
                expect(s.get_cell(cell), o.value(cell), note=f"{ctx}, final sweep")
    suite.case("randomized: 60 rounds x 30 ops over 6 cells (no loops) vs a "
               "brute-force oracle", randomized_phase1)

    # ---- PHASE 2 -----------------------------------------------------------
    suite.section("CORRECTNESS — PHASE 2 (reject circular formulas)")

    def p2_spec_example():
        s = make()
        set_ok(s, "A1", "=B1+1")
        rejected(s, "B1", "=A1", note="A1 -> B1 -> A1")
        expect(s.get_cell("B1"), 0, note="the rejected call left B1 unset")
        rejected(s, "C1", "=C1+1", note="C1 refers to itself")
        set_ok(s, "B1", "=C1+2")
        expect(s.get_cell("A1"), 3)
        rejected(s, "C1", "=A1", note="C1 -> A1 -> B1 -> C1")
        set_ok(s, "B1", "4")
        set_ok(s, "C1", "=A1", note="B1 no longer reads C1, so there is no loop")
        expect(s.get_cell("C1"), 5)
    suite.case("spec example from the file header", needs_phase2(p2_spec_example))

    def rejection_changes_nothing():
        s = make()
        set_ok(s, "A1", "1")
        set_ok(s, "B1", "=A1+10")
        set_ok(s, "C1", "=B1")
        rejected(s, "A1", "=C1+1", note="A1 -> C1 -> B1 -> A1")
        expect(s.get_cell("A1"), 1, note="A1 keeps its old number after the rejected call")
        expect(s.get_cell("C1"), 11)
        rejected(s, "B1", "=C1", note="B1 -> C1 -> B1")
        set_ok(s, "A1", "5")
        expect(s.get_cell("C1"), 15,
               note="B1 kept its old formula =A1+10 (the rejected =C1 was never stored)")
        set_ok(s, "A1", "=X1+X1")
        set_ok(s, "X1", "2")
        expect(s.get_cell("C1"), 14, note="A1 = X1 + X1 = 4, B1 = 14, C1 = 14")
    suite.case("a rejected call leaves every cell's contents as they were",
               needs_phase2(rejection_changes_nothing))

    def loops_of_every_shape():
        s = make()
        rejected(s, "A1", "=A1", note="a formula that is just itself")
        rejected(s, "A1", "=1+B1+A1", note="itself as a later term")
        set_ok(s, "B1", "=C1")
        set_ok(s, "C1", "=D1")
        set_ok(s, "D1", "=E1+1")
        rejected(s, "E1", "=B1", note="E1 -> B1 -> C1 -> D1 -> E1 (loop of four)")
        rejected(s, "E1", "=9+C1", note="E1 -> C1 -> D1 -> E1")
        set_ok(s, "E1", "=A1+A1", note="A1 is unset and feeds nothing: no loop")
        expect(s.get_cell("B1"), 1)
        set_ok(s, "Q1", "=B1+C1+D1", note="Q1 reads cells on one chain: no loop")
        expect(s.get_cell("Q1"), 3)
    suite.case("self-reference, long loops, and look-alikes that are fine",
               needs_phase2(loops_of_every_shape))

    def randomized_phase2():
        for rnd in range(60):
            rng = random.Random(SEED + 1000 + rnd)
            s, o = make(), Oracle()
            ctx = f"seed={SEED:#x}, round={rnd}"
            for op in range(30):
                cell = rng.choice(CELLS)
                if rng.random() < 0.65:
                    text = random_text(rng)
                    loop = o.loop_through(cell, text)
                    if loop:
                        rejected(s, cell, text,
                                 note=f"{ctx}, op={op}: storing {text!r} in {cell} "
                                      f"closes the loop {' -> '.join(loop)}")
                    else:
                        set_ok(s, cell, text, note=f"{ctx}, op={op}")
                        o.set(cell, text)
                else:
                    expect(s.get_cell(cell), o.value(cell), note=f"{ctx}, op={op}")
            for cell in CELLS:
                expect(s.get_cell(cell), o.value(cell), note=f"{ctx}, final sweep")
    suite.case("randomized: 60 rounds x 30 ops with loops attempted vs a "
               "brute-force oracle", needs_phase2(randomized_phase2))

    def randomized_planted_loops():
        # long loops are rare by chance: build a chain over 2-8 shuffled cells
        # (each formula reads the next one, plus some extra terms), set in a
        # random order, then try to close it
        pool = ["A1", "A2", "A3", "B1", "B2", "B3", "C1", "C2"]
        for rnd in range(80):
            rng = random.Random(SEED + 3000 + rnd)
            s, o = make(), Oracle()
            ctx = f"seed={SEED:#x}, planted-loop round={rnd}"
            chain = rng.sample(pool, rng.randrange(2, 9))
            steps = []
            for i, cell in enumerate(chain[:-1]):
                extra = [rng.choice(chain[i + 1:]) if rng.random() < 0.3 else
                         str(rng.randrange(0, 6)) for _ in range(rng.randrange(0, 2))]
                steps.append((cell, "=" + "+".join([chain[i + 1]] + extra)))
            rng.shuffle(steps)
            for cell, text in steps:
                set_ok(s, cell, text, note=ctx)
                o.set(cell, text)
            closing = "=" + "+".join([chain[0]] + [str(rng.randrange(0, 6))] * rng.randrange(0, 2))
            loop = o.loop_through(chain[-1], closing)
            rejected(s, chain[-1], closing,
                     note=f"{ctx}: storing {closing!r} in {chain[-1]} closes the loop "
                          f"{' -> '.join(loop)} ({len(loop) - 1} cells)")
            expect(s.get_cell(chain[0]), o.value(chain[0]),
                   note=f"{ctx}: after the rejected call")
    suite.case("randomized: 80 sheets with a planted loop of 2-8 cells; closing it "
               "must be rejected", needs_phase2(randomized_planted_loops))

    if suite.failed or not suite.passed:
        suite.section("PERFORMANCE")
        reason = ("fix correctness failures first" if suite.failed
                  else "nothing implemented yet")
        suite.skip("all performance checks", reason)
        return suite.summary()

    suite.section("PERFORMANCE")

    def isolated_edits(n_unrelated, rounds=12_000):
        # a sheet of n unrelated cells (numbers, each pair read by a formula)
        # plus two cells X1, Y1 off on their own. The timed run edits only
        # X1/Y1, each round paired with reads of unrelated numbers (fixed-cost
        # ops that keep cache effects from dominating the ratio).
        s = cls()
        for i in range(n_unrelated // 2):
            s.set_cell(f"L{i}", str(i))
            s.set_cell(f"F{i}", f"=L{i}+L{i + 1}")

        def run():
            for k in range(rounds):
                s.set_cell("X1", "=Y1+1")
                s.set_cell("Y1", str(k))
                s.get_cell("L1")
                s.get_cell("L2")
        return run

    def set_independent_of_sheet():
        diagnosis = ("set_cell is looking at the whole sheet (checking every cell "
                     "for loops, or recomputing every formula?). Target: cost "
                     "depends only on the cells connected to the edited one "
                     "through formulas.")
        try:
            t_small = bench(isolated_edits(5_000), budget=3.0)
            t_big = bench(isolated_edits(80_000), budget=3.0)
        except AssertionError as e:
            raise AssertionError(f"{diagnosis}  [{e}]") from None
        ratio = t_big / max(t_small, 1e-9)
        suite.info(f"12k edit rounds beside 5k unrelated cells: {fmt_s(t_small)}   "
                   f"beside 80k: {fmt_s(t_big)}   ratio {ratio:.1f}x (independent ≈ 1x)")
        assert ratio < 3, \
            (f"the same edits to two isolated cells took {ratio:.1f}x longer in a "
             f"sheet with 16x more unrelated cells — {diagnosis}")
    suite.case("set_cell cost independent of unrelated cells", set_independent_of_sheet)

    def note_followups():
        raise PerfConcern(
            "not machine-checkable: the DISCUSS AFTERWARDS tail. Rehearse O(1) "
            "reads: every cell remembers which cells read it, set_cell recomputes "
            "everything downstream once each (inputs before the cells that read "
            "them), so writes pay for what reads no longer do — and when that "
            "trade is worth it.")
    suite.case("O(1)-reads trade-off story", note_followups)

    return suite.summary()


if __name__ == "__main__":
    sys.exit(1 if main().failed else 0)
