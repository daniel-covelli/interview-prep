# Grader for Rippling Problem 1 (rippling/p1_vote_tracker.py).
# SPOILER WARNING: this file enumerates edge cases and contains a brute-force
# oracle and the reference solution. Run it, don't read it.
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from grader import (Suite, PerfConcern, load_class, bench, fmt_s, tracing,
                    expect)

SEED = 0x0F11

# Reference solution, printed by `uv run grade --reveal rippling/p1_vote_tracker`
# once the timebox is up. Never read it before then.
REFERENCE = '''
class VoteTracker:
    def __init__(self) -> None:
        self.votes = {}      # (user_id, article_id) -> "up" | "down"
        self.scores = {}     # article_id -> standing ups minus standing downs
        self.flips = {}      # user_id -> up to 3 article ids, most recent flip first

    def vote(self, user_id, article_id, direction):
        key = (user_id, article_id)
        prev = self.votes.get(key)
        if prev == direction:
            return                                   # same vote again: nothing changes
        self.votes[key] = direction
        delta = 1 if direction == "up" else -1
        # a first vote adds delta; a flip also cancels the old vote, so 2 * delta
        self.scores[article_id] = self.scores.get(article_id, 0) + (delta if prev is None else 2 * delta)
        if prev is not None:                         # a flip: move to the front, keep three
            recent = self.flips.setdefault(user_id, [])
            if article_id in recent:
                recent.remove(article_id)
            recent.insert(0, article_id)
            del recent[3:]

    def score(self, article_id):
        return self.scores.get(article_id, 0)

    def recent_flips(self, user_id):
        return list(self.flips.get(user_id, ()))     # never longer than 3: O(1)
'''


class Oracle:
    """Brute-force truth: an append-only log of accepted vote events plus the
    standing vote per (user, article). score() scans every standing vote;
    recent_flips() walks the user's whole history and dedups keeping the
    latest — exactly the naive designs the perf section catches."""

    def __init__(self):
        self.log = []                  # (user, article, was_flip)
        self.standing = {}

    def vote(self, user, article, direction):
        prev = self.standing.get((user, article))
        if prev == direction:
            return
        self.standing[(user, article)] = direction
        self.log.append((user, article, prev is not None))

    def score(self, article):
        return sum((1 if d == "up" else -1)
                   for (_, a), d in self.standing.items() if a == article)

    def recent_flips(self, user):
        seen = []
        for u, a, flip in reversed(self.log):
            if u == user and flip and a not in seen:
                seen.append(a)
        return seen[:3]



def measure(fn, diagnosis, repeat=2):
    """bench() that attaches the case's diagnosis to a TLE, so a workload
    that never finishes still names the naive design being caught."""
    try:
        return bench(fn, repeat=repeat)
    except AssertionError as e:
        raise AssertionError(f"{diagnosis}  [{e}]") from None

USERS = ["dan", "eve", "kim", "raj"]
ARTICLES = [f"a{i}" for i in range(5)]


def main():
    suite = Suite("Rippling 1: VoteTracker")
    cls, err = load_class("rippling.p1_vote_tracker", "VoteTracker")
    if cls is None:
        suite.skip_all(err)
        return suite.summary()
    make = tracing(cls)

    suite.section("PHASE 1 — VOTES AND SCORES")

    def spec_example():
        t = make()
        t.vote("dan", "a1", "up")
        expect(t.score("a1"), 1)
        t.vote("dan", "a1", "up")
        expect(t.score("a1"), 1, note="the same vote again is ignored")
        t.vote("eve", "a1", "down")
        expect(t.score("a1"), 0)
        t.vote("dan", "a1", "down")
        expect(t.score("a1"), -2,
               note="dan flipped up -> down: his +1 became -1, a swing of 2")
        expect(t.score("never_voted_on"), 0, note="unknown article scores 0")
    suite.case("spec example from the file header", spec_example)

    def repeats_ignored():
        t = make()
        for _ in range(3):
            t.vote("dan", "a1", "up")
        expect(t.score("a1"), 1, note="three identical up votes count once")
        for _ in range(2):
            t.vote("eve", "a1", "down")
        expect(t.score("a1"), 0, note="two identical down votes count once")
    suite.case("repeating a vote never changes the score", repeats_ignored)

    def flip_swings_by_two():
        t = make()
        t.vote("dan", "a1", "down")
        expect(t.score("a1"), -1)
        t.vote("dan", "a1", "up")
        expect(t.score("a1"), 1, note="down -> up: -1 becomes +1")
        t.vote("dan", "a1", "down")
        expect(t.score("a1"), -1, note="up -> down again: +1 becomes -1")
        t.vote("dan", "a1", "down")
        expect(t.score("a1"), -1, note="repeat after a flip: still one standing vote")
    suite.case("a flip replaces the standing vote (swing of 2), never adds one", flip_swings_by_two)

    def independence():
        t = make()
        t.vote("dan", "a1", "up")
        t.vote("dan", "a2", "down")
        t.vote("eve", "a1", "up")
        t.vote("kim", "a1", "up")
        t.vote("eve", "a2", "down")
        expect(t.score("a1"), 3, note="three different users, one up vote each")
        expect(t.score("a2"), -2)
        t.vote("eve", "a1", "down")
        expect(t.score("a1"), 1, note="only eve's vote on a1 flipped")
        expect(t.score("a2"), -2, note="eve's flip on a1 must not touch a2")
        expect(t.score("a3"), 0)
    suite.case("users and articles are independent", independence)

    def randomized_phase1():
        # many short seeded rounds with a fresh instance each, so a failing
        # round replays every call in full
        for rnd in range(40):
            rng = random.Random(SEED + rnd)
            t, oracle = make(), Oracle()
            ctx = f"seed={SEED:#x}, round={rnd}"
            for op in range(50):
                user, art = rng.choice(USERS), rng.choice(ARTICLES)
                if rng.random() < 0.7:
                    d = rng.choice(["up", "down"])
                    t.vote(user, art, d)
                    oracle.vote(user, art, d)
                else:
                    expect(t.score(art), oracle.score(art),
                           note=f"{ctx}, op={op}, score({art!r})")
            for art in ARTICLES:
                expect(t.score(art), oracle.score(art),
                       note=f"{ctx}, final sweep: score({art!r})")
    suite.case("randomized: 40 rounds x 50 vote/score ops over 4 users x 5 articles "
               "vs brute-force oracle", randomized_phase1)

    suite.section("PHASE 2 — RECENT FLIPS (skipped until you build it)")

    def spec_example_flips():
        t = make()
        t.vote("dan", "a1", "up")
        t.vote("dan", "a2", "up")
        t.vote("dan", "a3", "up")
        expect(t.recent_flips("dan"), [], note="first votes are not flips")
        t.vote("dan", "a1", "down")
        t.vote("dan", "a2", "down")
        t.vote("dan", "a2", "down")
        expect(t.recent_flips("dan"), ["a2", "a1"],
               note="most recent flip first; the repeated a2 vote is not a flip")
        t.vote("dan", "a3", "down")
        t.vote("dan", "a4", "up")
        t.vote("dan", "a4", "down")
        expect(t.recent_flips("dan"), ["a4", "a3", "a2"],
               note="only the three most recent distinct articles")
        t.vote("dan", "a1", "up")
        expect(t.recent_flips("dan"), ["a1", "a4", "a3"],
               note="a1 flipped again: it moves to the front, a2 falls off")
        expect(t.recent_flips("nobody"), [])
    suite.case("spec example from the file header", spec_example_flips)

    def one_article_back_and_forth():
        t = make()
        t.vote("dan", "a1", "up")
        for d in ["down", "up", "down", "up"]:
            t.vote("dan", "a1", d)
        expect(t.recent_flips("dan"), ["a1"],
               note="four flips on the same article: it appears once")
        t.vote("dan", "a2", "up")
        t.vote("dan", "a2", "up")
        expect(t.recent_flips("dan"), ["a1"],
               note="a2 was only ever voted up: no flip")
    suite.case("the same article flipped repeatedly appears once", one_article_back_and_forth)

    def move_to_front_when_full():
        t = make()
        for a in ["a1", "a2", "a3", "a4"]:
            t.vote("dan", a, "up")
        for a in ["a1", "a2", "a3"]:
            t.vote("dan", a, "down")
        expect(t.recent_flips("dan"), ["a3", "a2", "a1"])
        t.vote("dan", "a1", "up")
        expect(t.recent_flips("dan"), ["a1", "a3", "a2"],
               note="re-flipping the OLDEST entry moves it to the front")
        t.vote("dan", "a1", "down")
        expect(t.recent_flips("dan"), ["a1", "a3", "a2"],
               note="re-flipping the newest entry leaves the order as is")
        t.vote("dan", "a4", "down")
        expect(t.recent_flips("dan"), ["a4", "a1", "a3"],
               note="a fourth distinct article pushes out a2, the oldest")
        t.vote("dan", "a2", "up")
        expect(t.recent_flips("dan"), ["a2", "a4", "a1"],
               note="a2 flips again after falling off: back at the front")
    suite.case("re-flips move to the front; a fourth article evicts the oldest",
               move_to_front_when_full)

    def per_user():
        t = make()
        t.vote("dan", "a1", "up")
        t.vote("eve", "a1", "up")
        t.vote("dan", "a1", "down")
        t.vote("eve", "a2", "up")
        t.vote("eve", "a2", "down")
        expect(t.recent_flips("dan"), ["a1"], note="eve's flip on a2 is not dan's")
        expect(t.recent_flips("eve"), ["a2"], note="dan's flip on a1 is not eve's")
        expect(t.recent_flips("kim"), [], note="kim never voted")
        expect(t.score("a1"), 0, note="phase 1 still holds: dan -1, eve +1")
        got = t.recent_flips("dan")
        got.append("junk")
        expect(t.recent_flips("dan"), ["a1"],
               note="the returned list is a copy: mutating it must not change the tracker")
    suite.case("flip history is per user; the result is a fresh list", per_user)

    def randomized_phase2():
        if not hasattr(cls, "recent_flips"):
            raise NotImplementedError
        make().recent_flips("probe")   # NotImplementedError here -> skip
        for rnd in range(60):
            rng = random.Random(SEED + 1000 + rnd)
            t, oracle = make(), Oracle()
            ctx = f"seed={SEED:#x}, round={rnd}"
            for op in range(60):
                user, art = rng.choice(USERS[:2]), rng.choice(ARTICLES)
                roll = rng.random()
                if roll < 0.65:
                    d = rng.choice(["up", "down"])
                    t.vote(user, art, d)
                    oracle.vote(user, art, d)
                elif roll < 0.8:
                    expect(t.score(art), oracle.score(art),
                           note=f"{ctx}, op={op}, score({art!r})")
                else:
                    expect(t.recent_flips(user), oracle.recent_flips(user),
                           note=f"{ctx}, op={op}, recent_flips({user!r})")
            for user in USERS[:2]:
                expect(t.recent_flips(user), oracle.recent_flips(user),
                       note=f"{ctx}, final sweep: recent_flips({user!r})")
    suite.case("randomized: 60 rounds x 60 vote/score/recent_flips ops over 2 users x "
               "5 articles vs brute-force oracle", randomized_phase2)

    if suite.failed or not suite.passed:
        suite.section("PERFORMANCE")
        reason = ("fix correctness failures first" if suite.failed
                  else "nothing implemented yet")
        suite.skip("all performance checks", reason)
        return suite.summary()

    suite.section("PERFORMANCE")

    def hot_article(n, reps):
        # n users vote on ONE article, a score() read after every vote: a
        # score that counts the article's votes on demand goes quadratic
        def run():
            for _ in range(reps):
                t = cls()
                for i in range(n):
                    t.vote(f"u{i}", "hot", "up" if i % 3 else "down")
                    t.score("hot")
        return run

    def score_scaling():
        diagnosis = ("score() is counting the article's standing votes on every "
                     "call. Target: O(1) — keep each article's score up to date as "
                     "votes arrive and adjust it by the swing of each flip.")
        t_small = measure(hot_article(1_000, 32), diagnosis)
        t_big = measure(hot_article(4_000, 32), diagnosis)
        ratio = t_big / max(t_small, 1e-9)
        suite.info(f"32 x (1k votes + 1k reads): {fmt_s(t_small)}   "
                   f"32 x (4k votes + 4k reads): {fmt_s(t_big)}   "
                   f"ratio {ratio:.1f}x (O(1) per op ≈ 4x)")
        assert ratio < 10, \
            f"4x the votes on one article made vote+score {ratio:.1f}x slower — {diagnosis}"
    suite.case("score() cost stays O(1) as an article's vote count grows", score_scaling)

    def flip_churn(n, reps):
        # one user flips n distinct articles, reading recent_flips after each:
        # a per-user history that is walked or deduped on read goes quadratic
        def run():
            for _ in range(reps):
                t = cls()
                for i in range(n):
                    a = f"a{i}"
                    t.vote("dan", a, "up")
                    t.vote("dan", a, "down")
                    t.recent_flips("dan")
        return run

    def flips_scaling():
        if not hasattr(cls, "recent_flips"):
            raise NotImplementedError
        cls().recent_flips("probe")    # NotImplementedError here -> skip
        diagnosis = ("recent_flips() is walking (or sorting/deduping) the user's "
                     "whole flip history on every read. Target: O(1) — only the "
                     "three most recent distinct articles ever need to be kept per "
                     "user, so maintain exactly those as flips happen.")
        t_small = measure(flip_churn(1_000, 16), diagnosis)
        t_big = measure(flip_churn(4_000, 16), diagnosis)
        ratio = t_big / max(t_small, 1e-9)
        suite.info(f"16 x (1k flips + 1k reads): {fmt_s(t_small)}   "
                   f"16 x (4k flips + 4k reads): {fmt_s(t_big)}   "
                   f"ratio {ratio:.1f}x (O(1) per op ≈ 4x)")
        assert ratio < 10, \
            f"4x the flips by one user made vote+recent_flips {ratio:.1f}x slower — {diagnosis}"
    suite.case("recent_flips() cost independent of the user's flip history", flips_scaling)

    def note_followups():
        raise PerfConcern(
            "not machine-checkable: the DISCUSS AFTERWARDS tail. Rehearse the "
            "live top-10 (what a single vote changes and what stays sorted), "
            "and the memory story — the standing-vote table grows with "
            "users x articles while flip history is bounded per user.")
    suite.case("top-10 / memory story", note_followups)

    return suite.summary()


if __name__ == "__main__":
    sys.exit(1 if main().failed else 0)
