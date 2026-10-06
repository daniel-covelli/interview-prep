# Grader for Harvey Problem 3 (harvey/p3_highlight.py).
# SPOILER WARNING: this file enumerates edge cases and contains a brute-force
# oracle and the reference solution. Run it, don't read it.
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from grader import Suite, PerfConcern, Failure, load_fn, bench, fmt_s, expect

SEED = 0xB01D

# Reference solution, printed by `uv run grade --reveal harvey/p3_highlight`
# once the timebox is up. Never read it before then.
REFERENCE = '''
def _regions(text, phrases):
    """[start, end, ids] per bolded run, left to right."""
    found = []
    for i, p in enumerate(phrases):
        at = text.find(p)
        while at != -1:                      # every occurrence, overlapping ones too
            found.append((at, at + len(p), i))
            at = text.find(p, at + 1)
    found.sort()
    regions = []
    for start, end, i in found:
        if regions and start <= regions[-1][1]:      # overlaps or touches
            regions[-1][1] = max(regions[-1][1], end)
            regions[-1][2].add(i)
        else:
            regions.append([start, end, {i}])
    return regions


def _render(text, regions, cite):
    out, pos = [], 0                         # pieces, joined once at the end
    for start, end, ids in regions:
        out += [text[pos:start], "<b>", text[start:end], "</b>"]
        if cite:
            out.append("[" + ",".join(map(str, sorted(ids))) + "]")
        pos = end
    out.append(text[pos:])
    return "".join(out)


def highlight(text: str, phrases: list[str]) -> str:
    return _render(text, _regions(text, phrases), cite=False)


def highlight_cited(text: str, sources: list[str]) -> str:
    return _render(text, _regions(text, sources), cite=True)
'''


def oracle(text, phrases, cite):
    """Brute-force truth: mark every covered character one by one, then
    walk the marks; a source is cited by the run its occurrence starts in."""
    covered = [False] * len(text)
    starts = []                                  # (position, id) of every occurrence
    for i in range(len(text)):
        for pid, p in enumerate(phrases):
            if text[i:i + len(p)] == p:
                starts.append((i, pid))
                for j in range(i, i + len(p)):
                    covered[j] = True
    out, i = [], 0
    while i < len(text):
        if not covered[i]:
            out.append(text[i])
            i += 1
            continue
        j = i
        while j < len(text) and covered[j]:
            j += 1
        out.append("<b>" + text[i:j] + "</b>")
        if cite:
            ids = sorted({pid for at, pid in starts if i <= at < j})
            out.append("[" + ",".join(map(str, ids)) + "]")
        i = j
    return "".join(out)


def outcome(fn, text, phrases):
    try:
        return fn(text, list(phrases))
    except NotImplementedError:
        raise                                    # a stub: the case is skipped
    except Exception as e:                       # noqa: BLE001 — report, don't hide
        return f"raised {type(e).__name__}: {e!r}"


def shrink(fn, text, phrases, cite):
    """Delta-debug a failing input to a minimal one that still mismatches:
    drop a phrase, drop a character of the text, drop a character of a
    phrase (phrases stay non-empty)."""
    def fails(t, ps):
        return outcome(fn, t, ps) != oracle(t, ps, cite)

    def reductions(t, ps):
        for i in range(len(ps)):
            yield t, ps[:i] + ps[i + 1:]
        for i in range(len(t)):
            yield t[:i] + t[i + 1:], ps
        for i, p in enumerate(ps):
            for j in range(len(p) if len(p) > 1 else 0):
                yield t, ps[:i] + [p[:j] + p[j + 1:]] + ps[i + 1:]

    progress = True
    while progress:
        progress = False
        for cand in reductions(text, phrases):
            if fails(*cand):
                text, phrases = cand
                progress = True
                break
    return text, phrases


def check(fn, text, phrases, cite, ctx):
    if outcome(fn, text, phrases) == oracle(text, phrases, cite):
        return
    t, ps = shrink(fn, text, phrases, cite)
    name = "highlight_cited" if cite else "highlight"
    raise Failure(output=outcome(fn, t, ps), expected=oracle(t, ps, cite),
                  note=f"MINIMAL REPRO: {name}({t!r}, {ps!r})  "
                       f"[shrunk from {ctx}: {len(text)} chars, {len(phrases)} phrases]")


def random_input(rng):
    """A short text over a tiny alphabet; about half the phrases quote a piece
    of the text itself, so long matches with shorter ones inside them (and
    more matches right after) are common."""
    text = "".join(rng.choice("aab ") for _ in range(rng.randrange(0, 22)))
    phrases = []
    for _ in range(rng.randrange(0, 6)):
        if text and rng.random() < 0.5:
            i = rng.randrange(len(text))
            piece = text[i:i + rng.randrange(1, 7)]
            if piece.strip():
                phrases.append(piece)
                continue
        phrases.append("".join(rng.choice("ab") for _ in range(rng.randrange(1, 4))))
    return text, phrases


def main():
    suite = Suite("Harvey 3: highlight")
    highlight, err = load_fn("harvey.p3_highlight", "highlight")
    cited, err2 = load_fn("harvey.p3_highlight", "highlight_cited")
    if highlight is None or cited is None:
        suite.skip_all(err or err2)
        return suite.summary()

    suite.section("CORRECTNESS — PHASE 1 (highlight)")

    def spec_example():
        expect(highlight("the quick brown fox", ["quick", "fox"]),
               "the <b>quick</b> brown <b>fox</b>")
        expect(highlight("abcdef", ["abc", "cde"]), "<b>abcde</b>f",
               note="overlapping matches share one pair of tags")
        expect(highlight("abcdef", ["ab", "cd"]), "<b>abcd</b>ef",
               note="matches that touch end to end share one pair of tags")
        expect(highlight("ababa", ["aba"]), "<b>ababa</b>",
               note="aba occurs at 0 and at 2; together they cover everything")
        expect(highlight("no match here", ["xyz"]), "no match here")
        expect(highlight("anything", []), "anything")
    suite.case("spec example from the file header", spec_example)

    def edges_of_the_text():
        expect(highlight("", ["a"]), "", note="empty text")
        expect(highlight("abc", ["abc"]), "<b>abc</b>", note="the whole text")
        expect(highlight("abc", ["a"]), "<b>a</b>bc", note="a match at the very start")
        expect(highlight("abc", ["c"]), "ab<b>c</b>", note="a match at the very end")
        expect(highlight("ab", ["abc"]), "ab", note="a phrase longer than the text")
    suite.case("matches at the edges; empty text; phrase longer than text",
               edges_of_the_text)

    def runs_and_gaps():
        expect(highlight("a a a", ["a"]), "<b>a</b> <b>a</b> <b>a</b>",
               note="one character between matches keeps them apart")
        expect(highlight("aaaa", ["a"]), "<b>aaaa</b>",
               note="four touching single-character matches form one run")
        expect(highlight("xabcdefx", ["bcd", "abcdef"]), "x<b>abcdef</b>x",
               note="one match entirely inside another")
        expect(highlight("abcabc", ["abc", "abc"]), "<b>abcabc</b>",
               note="the same phrase listed twice")
        expect(highlight("Fox fox", ["fox"]), "Fox <b>fox</b>",
               note="matching is case-sensitive")
        expect(highlight("abcdefgh", ["gh", "ab", "ef", "cd"]), "<b>abcdefgh</b>",
               note="a chain of touching matches, phrases listed out of text order")
    suite.case("touching vs separated runs; nested and repeated phrases", runs_and_gaps)

    def randomized_phase1():
        rng = random.Random(SEED)
        for trial in range(400):
            text, phrases = random_input(rng)
            check(highlight, text, phrases, cite=False,
                  ctx=f"seed={SEED:#x}, trial={trial}")
    suite.case("randomized: 400 small texts vs a brute-force oracle", randomized_phase1)

    suite.section("CORRECTNESS — PHASE 2 (citations)")

    def p2_spec_example():
        expect(cited("the quick brown fox", ["fox", "quick", "quick brown"]),
               "the <b>quick brown</b>[1,2] <b>fox</b>[0]")
        expect(cited("abcdef", ["cde", "abc", "zz"]), "<b>abcde</b>[0,1]f",
               note="source 2 (zz) never occurs, so it is cited nowhere")
        expect(cited("a cat, a cat", ["cat"]), "a <b>cat</b>[0], a <b>cat</b>[0]")
        expect(cited("abc", ["abc", "b"]), "<b>abc</b>[0,1]",
               note="b's occurrence lies inside abc's run, so both are cited")
    suite.case("spec example from the file header", p2_spec_example)

    def citation_shapes():
        expect(cited("plain", []), "plain", note="no sources")
        expect(cited("abcd", ["cd", "ab"]), "<b>abcd</b>[0,1]",
               note="touching matches merge, and ids come out in increasing order")
        expect(cited("ab ab", ["ab", "b", "ab"]), "<b>ab</b>[0,1,2] <b>ab</b>[0,1,2]",
               note="a phrase listed twice is cited under both ids")
        expect(cited("xy zy", ["y", "x"]), "<b>xy</b>[0,1] z<b>y</b>[0]",
               note="each run cites only the sources that occur inside it")
    suite.case("ids per run, increasing, duplicates cited twice", citation_shapes)

    def randomized_phase2():
        rng = random.Random(SEED + 1)
        for trial in range(400):
            text, phrases = random_input(rng)
            check(cited, text, phrases, cite=True,
                  ctx=f"seed={SEED:#x}, trial={trial}")
    suite.case("randomized: 400 small texts with citations vs a brute-force oracle",
               randomized_phase2)

    if suite.failed or not suite.passed:
        suite.section("PERFORMANCE")
        reason = ("fix correctness failures first" if suite.failed
                  else "nothing implemented yet")
        suite.skip("all performance checks", reason)
        return suite.summary()

    suite.section("PERFORMANCE")
    phrases = ["ab", "cd", "efg", "xyz", "b c"]

    def passage(n):
        rng = random.Random(SEED)
        return "".join(rng.choice("abcdefgxyz  ") for _ in range(n))

    def scaling(fn, what, diagnosis):
        small, big = passage(40_000), passage(160_000)
        try:
            t_small = bench(lambda: [fn(small, phrases) for _ in range(20)],
                            repeat=2, budget=5.0)
            t_big = bench(lambda: [fn(big, phrases) for _ in range(20)],
                          repeat=2, budget=5.0)
        except AssertionError as e:
            raise AssertionError(f"{diagnosis}  [{e}]") from None
        ratio = t_big / max(t_small, 1e-9)
        suite.info(f"{what}: 20 x 40k chars: {fmt_s(t_small)}   20 x 160k chars: "
                   f"{fmt_s(t_big)}   ratio {ratio:.1f}x (≈ 4x)")
        assert ratio < 10, f"4x the text took {ratio:.1f}x longer — {diagnosis}"

    def phase1_scaling():
        scaling(highlight.__wrapped__, "highlight",
                "every bolded run costs a pass over the whole text (tags inserted "
                "one at a time into a fresh copy of the string, or a scan from the "
                "start for each run?). Target: roughly linear in the text for a "
                "fixed list of phrases — build the result once, left to right.")
    suite.case("highlight cost scales ~linearly with the text", phase1_scaling)

    def phase2_scaling():
        scaling(cited.__wrapped__, "highlight_cited",
                "each bolded run is being compared against every occurrence in the "
                "text (or the text is re-scanned per run). Target: roughly linear "
                "in the text — collect a run's ids while forming the run.")
    suite.case("highlight_cited cost scales ~linearly with the text", phase2_scaling)

    def note_followups():
        raise PerfConcern(
            "not machine-checkable: the DISCUSS AFTERWARDS tail. Rehearse what "
            "breaks with thousands of phrases: one scan of the text per phrase "
            "becomes the bottleneck; you'd want every phrase found in ONE pass "
            "over the text, with work per character independent of the number of "
            "phrases.")
    suite.case("thousands-of-phrases story", note_followups)

    return suite.summary()


if __name__ == "__main__":
    sys.exit(1 if main().failed else 0)
