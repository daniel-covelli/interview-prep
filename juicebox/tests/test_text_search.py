# Grader for Problem 3 (text_search.py).
# SPOILER WARNING: this file enumerates edge cases. Run it, don't read it.
import random
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from grader import (Suite, PerfConcern, Failure, desc, load_class, bench,
                      fmt_s, short, tracing, expect, expect_set, expect_len)

SEED = 0x5EA2C4


def tokenize(text):
    """Reference tokenizer for the oracle: case-insensitive alphanumeric words."""
    return re.findall(r"[a-z0-9]+", text.lower())


def matching_docs(docs, query):
    """Brute-force truth for AND + whole-word matching. docs: {id: text}."""
    q = set(tokenize(query))
    if not q:
        return set()
    return {d for d, text in docs.items() if q <= set(tokenize(text))}


def check_search(result, matches, k, tf=None, ctx=None):
    """Validate a search result (list of doc ids) against the true match set.
    If tf is given (single-term queries), also validate the ranking, allowing
    any order among equal scores. On failure, one valid answer is shown as
    Expected."""
    want_len = min(k, len(matches))
    if tf is not None:
        want = sorted(matches, key=lambda d: (-tf[d], d))[:want_len]
        tied = len(set(tf[d] for d in matches)) < len(matches)
        expected = desc(short(want, 800)
                        + (" (docs with equal scores are interchangeable)" if tied else ""))
    elif want_len == len(matches):
        expected = desc(f"{short(sorted(matches), 800)} in any order")
    else:
        expected = desc(f"any {want_len} of {short(sorted(matches), 800)} "
                        f"(ranking is your scorer's call)")

    def fail(note):
        raise Failure(output=result, expected=expected,
                      note=note + (f"  [{ctx}]" if ctx else ""))

    if not isinstance(result, list):
        fail(f"expected a list of doc ids, got {type(result).__name__}")
    if len(result) != want_len:
        fail(f"expected {want_len} results (k={k}, {len(matches)} matching docs), "
             f"got {len(result)}")
    if len(set(result)) != len(result):
        fail("duplicate doc ids in result")
    bogus = [d for d in result if d not in matches]
    if bogus:
        fail(f"returned docs that don't match the query: {short(bogus)}")
    if tf is not None:
        scores = [tf[d] for d in result]
        if scores != sorted(scores, reverse=True):
            fail(f"single-term query not ranked by frequency desc: tf sequence {short(scores)}")
        best = sorted((tf[d] for d in matches), reverse=True)[:want_len]
        if scores != best:
            fail(f"tf sequence {short(scores)} != best possible {short(best)} "
                 f"— a heavier doc was omitted or outranked")


def main():
    suite = Suite("Problem 3: SearchEngine")
    cls, err = load_class("juicebox.text_search", "SearchEngine")
    if cls is None:
        suite.skip_all(err)
        return suite.summary()
    make = tracing(cls)

    suite.section("CORRECTNESS")

    def spec_engine():
        se = make()
        se.add_document("d1", "Fresh juice daily")
        se.add_document("d2", "Juice juice juice - the juice catalog")
        se.add_document("d3", "A catalog of cats")
        return se

    def spec_example():
        se = spec_engine()
        expect(se.search("juice"), ["d2", "d1"])
        expect(se.search("juice fresh"), ["d1"])
        expect(se.search("cat"), [],
               note='"catalog" and "cats" must NOT match the whole word "cat"')
        expect(se.search("juice", k=1), ["d2"])
    suite.case("spec example from the file header", spec_example)

    def case_insensitive():
        se = make()
        se.add_document("d1", "JUICE Bar downtown")
        se.add_document("d2", "juice bar")
        expect_set(se.search("Juice BAR"), {"d1", "d2"},
                   note="mixed-case query against mixed-case docs")
    suite.case("case-insensitive on both document and query side", case_insensitive)

    def punctuation():
        se = make()
        se.add_document("d1", "Drink juice!")
        se.add_document("d2", "juice, fresh-squeezed. (daily)")
        expect_set(se.search("juice"), {"d1", "d2"},
                   note='"juice!" and "juice," contain the word juice — is '
                        'punctuation glued onto tokens (str.split-style tokenizing)?')
        expect_set(se.search("daily"), {"d2"},
                   note='"(daily)" should match query "daily"')
    suite.case("words adjacent to punctuation still match", punctuation)

    def numbers():
        se = make()
        se.add_document("d1", "error 404 page not found")
        se.add_document("d2", "error page")
        expect(se.search("404"), ["d1"], note="numeric tokens must be searchable")
    suite.case("numeric tokens are searchable", numbers)

    def empty_and_unknown():
        se = spec_engine()
        expect(se.search(""), [])
        expect(se.search("   "), [])
        expect(se.search("zebra"), [])
        expect(se.search("juice zebra"), [],
               note="AND semantics: one unknown term must kill the whole query")
    suite.case("empty query, unknown term, known+unknown -> []", empty_and_unknown)

    def and_semantics():
        se = make()
        se.add_document("d1", "apple banana cherry")
        se.add_document("d2", "apple banana")
        se.add_document("d3", "apple cherry")
        expect(se.search("apple banana cherry"), ["d1"],
               note="only d1 contains all three terms")
        expect_set(se.search("apple banana"), {"d1", "d2"})
    suite.case("multi-term AND: every query word must appear", and_semantics)

    def k_rules():
        se = make()
        for i in range(15):
            se.add_document(f"d{i}", "common word " + "extra " * i)
        expect_len(se.search("common"), 10,
                   note="15 docs match and k defaults to 10")
        expect(se.search("common", k=0), [])
        expect_len(se.search("common", k=3), 3)
        expect_len(se.search("common", k=100), 15,
                   note="k > matches returns all 15")
    suite.case("k: default 10, k=0 -> [], k respected, k > matches", k_rules)

    def freshness():
        se = make()
        se.add_document("noise", "wind turbine farm")  # keeps "solar" non-ubiquitous
        se.add_document("d1", "solar power")
        expect(se.search("solar"), ["d1"])
        se.add_document("d2", "solar solar solar panels")
        expect(se.search("solar"), ["d2", "d1"],
               note="a doc added AFTER a search must be indexed and can outrank — stale index?")
    suite.case("documents added after searches are found and ranked", freshness)

    def single_term_ranking():
        se = make()
        se.add_document("noise1", "soda pop fizz")   # docs without "grape" so the
        se.add_document("noise2", "fizz fizz pop")   # term is not in every doc
        se.add_document("light", "grape")
        se.add_document("mid", "grape grape grape juice")
        se.add_document("heavy", "grape grape grape grape grape soda")
        expect(se.search("grape"), ["heavy", "mid", "light"],
               note="frequency must drive single-term ranking")
    suite.case("single-term ranking follows term frequency", single_term_ranking)

    def duplicate_query_words():
        se = spec_engine()
        expect_set(se.search("juice juice"), {"d1", "d2"},
                   note="repeated query words must not change which docs match")
    suite.case("repeated word in query behaves like the word once", duplicate_query_words)

    def randomized():
        rng = random.Random(SEED)
        vocab = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot",
                 "golf", "hotel", "india", "juliet", "kilo", "lima"]
        se = make()
        docs = {}
        for i in range(120):
            doc_id = f"doc{i}"
            text = " ".join(rng.choice(vocab) for _ in range(rng.randrange(3, 25)))
            se.add_document(doc_id, text)
            docs[doc_id] = text
            if i % 10 == 0:
                # single-term query: membership AND ranking checked
                term = rng.choice(vocab)
                matches = matching_docs(docs, term)
                if len(matches) < len(docs):
                    tf = {d: Counter(tokenize(t))[term] for d, t in docs.items() if d in matches}
                else:
                    # term appears in EVERY doc: an idf-weighted scorer gives it
                    # score 0 everywhere, so any order is defensible — check
                    # membership only
                    tf = None
                k = rng.choice([1, 5, 10, 200])
                check_search(se.search(term, k=k), matches, k, tf=tf,
                             ctx=f"seed={SEED:#x}, after {i+1} docs, search({term!r}, k={k})")
                # two-term query: membership only (scoring choice is yours)
                q = f"{rng.choice(vocab)} {rng.choice(vocab)}"
                matches = matching_docs(docs, q)
                check_search(se.search(q, k=10), matches, 10,
                             ctx=f"seed={SEED:#x}, after {i+1} docs, search({q!r})")
    suite.case("randomized: 120 docs cross-checked against brute-force oracle", randomized)

    suite.section("RANKING QUALITY")

    def idf_probe():
        se = make()
        # "the" appears in every doc; "cedar" is rare
        se.add_document("stuffed", "the the the the the the the cedar")
        se.add_document("focused", "cedar cedar cedar the")
        for i in range(8):
            se.add_document(f"filler{i}", "the quick brown fox " + "the " * i)
        got = se.search("the cedar")
        expect_set(got, {"stuffed", "focused"},
                   note="AND matching broken in probe setup")
        if got[0] != "focused":
            raise PerfConcern(
                'query "the cedar": the doc stuffed with "the" (a word every '
                'doc contains) outranked the doc heavy in the rare word '
                '"cedar". Pure term-frequency scoring does this. Expect the '
                'interviewer to probe why rare words should carry more '
                'signal — be ready to justify your scoring or upgrade it.')
    suite.case("rare query words outweigh ubiquitous ones", idf_probe)

    if suite.failed:
        suite.section("PERFORMANCE")
        suite.skip("all performance checks", "fix correctness failures first")
        return suite.summary()

    suite.section("PERFORMANCE")

    FILLER_VOCAB = [f"filler{i}" for i in range(400)]

    def build(n_filler):
        rng = random.Random(SEED)
        se = cls()
        for i in range(n_filler):
            se.add_document(f"f{i}", " ".join(rng.choice(FILLER_VOCAB) for _ in range(30)))
        for i in range(30):
            se.add_document(f"needle{i}", "quartz " * (i + 1) + "mineral sample")
        return se

    def add_scaling():
        t_small = bench(lambda: build(1_000), repeat=2)
        t_big = bench(lambda: build(4_000), repeat=2)
        ratio = t_big / max(t_small, 1e-9)
        suite.info(f"index 1k docs: {fmt_s(t_small)}   4k docs: {fmt_s(t_big)}   ratio {ratio:.1f}x (linear ≈ 4x)")
        assert ratio < 10, \
            (f"4x more documents took {ratio:.1f}x longer to index — "
             f"add_document should be O(words in that doc), independent of "
             f"corpus size")
    suite.case("add_document cost stays O(doc length)", add_scaling)

    def search_independence():
        se_small = build(1_500)
        se_big = build(6_000)
        t_small = bench(lambda: [se_small.search("quartz mineral") for _ in range(20)], repeat=3)
        t_big = bench(lambda: [se_big.search("quartz mineral") for _ in range(20)], repeat=3)
        suite.info(f"search among 1.5k non-matching docs: {fmt_s(t_small / 20)}   "
                   f"among 6k: {fmt_s(t_big / 20)}")
        ratio = t_big / max(t_small, 1e-9)
        assert ratio < 3, \
            (f"quadrupling docs that DON'T match the query made search "
             f"{ratio:.1f}x slower — the query is scanning the corpus instead "
             f"of only touching docs that contain the query terms. Target: "
             f"cost proportional to matched posting lists, independent of "
             f"corpus size.")
    suite.case("search cost independent of non-matching corpus size", search_independence)

    return suite.summary()


if __name__ == "__main__":
    sys.exit(1 if main().failed else 0)
