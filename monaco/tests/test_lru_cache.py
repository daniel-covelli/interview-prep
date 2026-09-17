# Grader for Monaco Problem 5 (monaco/p5_lru_cache.py).
# SPOILER WARNING: this file enumerates edge cases and contains a brute-force
# oracle. Run it, don't read it.
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from grader import (Suite, PerfConcern, load_class, bench, fmt_s, tracing,
                    expect)

SEED = 0xCAC4E


class Oracle:
    """Brute-force truth: a dict of values plus a plain list of keys in
    recency order (least recently used first). Every use moves the key to
    the end of the list; eviction pops the front. O(capacity) per op —
    exactly the naive design the perf section is built to catch."""

    def __init__(self, capacity):
        self.capacity = capacity
        self.values = {}
        self.order = []                     # least recently used first

    def _touch(self, key):
        if key in self.values:
            self.order.remove(key)
        self.order.append(key)

    def get(self, key):
        if key not in self.values:
            return None
        self._touch(key)
        return self.values[key]

    def put(self, key, value):
        if key not in self.values and len(self.values) >= self.capacity:
            del self.values[self.order.pop(0)]
        self._touch(key)
        self.values[key] = value

    def delete(self, key):
        if key not in self.values:
            return False
        self.order.remove(key)
        del self.values[key]
        return True


KEYS = [f"k{i}" for i in range(12)]


def main():
    suite = Suite("Monaco 5: LRUCache")
    cls, err = load_class("monaco.p5_lru_cache", "LRUCache")
    if cls is None:
        suite.skip_all(err)
        return suite.summary()
    make = tracing(cls)

    suite.section("CORRECTNESS")

    def spec_example():
        c = make(2)
        c.put("a", 1)
        c.put("b", 2)
        expect(c.get("a"), 1, note='"a" is now the most recently used')
        c.put("c", 3)
        expect(c.get("b"), None,
               note='put("c") on a full cache evicts "b", the least recently used')
        expect(c.get("c"), 3)
        c.put("a", 10)
        expect(c.get("a"), 10,
               note="put on an existing key replaces the value — no eviction")
        expect(c.delete("c"), True)
        expect(c.delete("c"), False, note="second delete: already gone")
        c.put("d", 4)
        expect(c.get("a"), 10,
               note='delete("c") freed a slot, so put("d") evicted nothing')
        expect(c.get("d"), 4)
    suite.case("spec example from the file header", spec_example)

    def miss_is_not_a_use():
        c = make(2)
        c.put("a", 1)
        c.put("b", 2)
        expect(c.get("zzz"), None, note="miss on a key never inserted")
        c.put("c", 3)
        expect(c.get("a"), None,
               note='the miss on "zzz" must not touch recency: "a" was still '
                    'the LRU when put("c") evicted')
        expect(c.get("b"), 2)
        expect(c.get("a"), None, note="a miss on an evicted key is also not a use")
        c.put("d", 4)
        expect(c.get("c"), None,
               note='get("b") was a hit (a use), so "c" was the LRU when '
                    'put("d") evicted')
        expect(c.get("b"), 2)
        expect(c.get("d"), 4)
    suite.case("a get miss returns None and touches nothing", miss_is_not_a_use)

    def hit_refreshes_recency():
        c = make(3)
        c.put("a", 1)
        c.put("b", 2)
        c.put("c", 3)
        expect(c.get("a"), 1)
        c.put("d", 4)
        expect(c.get("b"), None,
               note='get("a") made "a" the most recent, so "b" was the LRU '
                    'when put("d") evicted')
        expect(c.get("c"), 3)
        c.put("e", 5)
        expect(c.get("a"), None,
               note='after get("c") the order oldest→newest was a, d, c: '
                    'put("e") evicts "a"')
        expect(c.get("d"), 4)
        expect(c.get("e"), 5)
        expect(c.get("c"), 3)
    suite.case("a get hit makes the key the most recently used", hit_refreshes_recency)

    def update_never_evicts():
        c = make(2)
        c.put("a", 1)
        c.put("b", 2)
        c.put("a", 100)
        c.put("c", 3)
        expect(c.get("b"), None,
               note='put("a", 100) was a use: "b" became the LRU and '
                    'put("c") evicted it')
        expect(c.get("a"), 100, note="the updated value is what comes back")
        c.put("c", 33)
        expect(c.get("a"), 100,
               note="updating a key while the cache is full evicts nothing")
        expect(c.get("c"), 33)
    suite.case("put on an existing key updates in place, refreshes it, never evicts",
               update_never_evicts)

    def strict_lru_order():
        c = make(3)
        c.put("a", 1)
        c.put("b", 2)
        c.put("c", 3)
        expect(c.get("b"), 2)
        expect(c.get("a"), 1)
        c.put("d", 4)
        c.put("e", 5)
        expect(c.get("c"), None,
               note="oldest→newest was c, b, a: the first eviction takes c")
        expect(c.get("b"), None, note="the second eviction takes b")
        expect(c.get("a"), 1,
               note='"a" was touched last of the originals and survives both')
        c.put("f", 6)
        expect(c.get("d"), None,
               note="oldest→newest was d, e, a: evictions go strictly oldest first")
        expect(c.get("e"), 5)
        expect(c.get("f"), 6)
        expect(c.get("a"), 1)
    suite.case("evictions follow the exact recency order, one at a time", strict_lru_order)

    def delete_semantics():
        c = make(3)
        c.put("a", 1)
        c.put("b", 2)
        c.put("c", 3)
        expect(c.delete("b"), True)
        expect(c.delete("b"), False, note="deleting an absent key -> False")
        expect(c.delete("zzz"), False, note="never-inserted key -> False")
        expect(c.get("b"), None, note="deleted keys are gone")
        c.put("d", 4)
        expect(c.get("a"), 1,
               note='delete("b") freed a slot, so put("d") must not evict "a"')
        c.put("e", 5)
        expect(c.get("c"), None,
               note='order oldest→newest was c, d, a (get("a") was a use): '
                    'put("e") evicts "c"')
        expect(c.delete("a"), True, note="deleting the most recently used key")
        c.put("a", 11)
        c.put("f", 6)
        expect(c.get("d"), None,
               note='re-put after delete is a fresh, most-recent entry: order '
                    'was d, e, a so put("f") evicts "d"')
        expect(c.get("a"), 11, note="the re-put key carries its new value")
        expect(c.get("e"), 5)
        expect(c.get("f"), 6)
    suite.case("delete: True/False, frees a slot, re-put is a fresh entry", delete_semantics)

    def delete_keeps_order():
        c = make(3)
        c.put("a", 1)
        c.put("b", 2)
        c.put("c", 3)
        expect(c.delete("c"), True)
        c.put("d", 4)
        c.put("e", 5)
        expect(c.get("a"), None,
               note='delete is not a use: after delete("c") the order was a, b, '
                    'then d — put("e") evicts "a"')
        expect(c.get("b"), 2)
        expect(c.get("d"), 4)
        expect(c.get("e"), 5)
        expect(c.delete("b"), True, note="delete the LRU key itself")
        c.put("f", 6)
        expect(c.get("d"), 4, note="the delete freed the slot: put(\"f\") evicted nothing")
        expect(c.get("e"), 5)
        expect(c.get("f"), 6)
    suite.case("delete leaves the remaining keys' order untouched", delete_keeps_order)

    def capacity_one():
        c = make(1)
        c.put("a", 1)
        expect(c.get("a"), 1)
        c.put("b", 2)
        expect(c.get("a"), None,
               note="capacity 1: every new key evicts the previous one")
        expect(c.get("b"), 2)
        c.put("b", 3)
        expect(c.get("b"), 3, note="update in place at capacity 1")
        expect(c.delete("b"), True)
        expect(c.get("b"), None)
        c.put("c", 4)
        expect(c.get("c"), 4)
        expect(c.delete("a"), False)
    suite.case("capacity of exactly 1", capacity_one)

    def values_and_keys():
        c = make(4)
        c.put("zero", 0)
        c.put("empty", "")
        c.put("list", [])
        c.put("rec", {"company": "Acme", "title": "VP Sales"})
        expect(c.get("zero"), 0,
               note="0 is a real value, not a miss — don't `or None` it away")
        expect(c.get("empty"), "", note='"" is a real value, not a miss')
        expect(c.get("list"), [], note="[] is a real value, not a miss")
        expect(c.get("rec"), {"company": "Acme", "title": "VP Sales"},
               note="values are arbitrary objects, returned as stored")
        c2 = make(2)
        c2.put("Key", "upper")
        c2.put("key", "lower")
        expect(c2.get("Key"), "upper", note="keys compare exactly (case-sensitive)")
        expect(c2.get("key"), "lower")
        expect(c2.delete("KEY"), False, note='"KEY" was never inserted')
    suite.case("falsy values are real values; keys compare exactly", values_and_keys)

    def run_random(c, oracle, rng, n_ops, cap, with_delete):
        ctx = ""
        for op in range(n_ops):
            key = rng.choice(KEYS)
            roll = rng.random()
            ctx = f"seed={SEED:#x}, cap={cap}, op={op}"
            if roll < 0.45:
                value = f"v{op}"
                c.put(key, value)
                oracle.put(key, value)
            elif roll < 0.85 or not with_delete:
                expect(c.get(key), oracle.get(key), note=f"{ctx}, get({key!r})")
            else:
                expect(c.delete(key), oracle.delete(key),
                       note=f"{ctx}, delete({key!r})")
        for key in KEYS:
            expect(c.get(key), oracle.get(key),
                   note=f"{ctx}, final sweep: get({key!r})")

    def randomized_get_put():
        rng = random.Random(SEED)
        for cap in (1, 2, 4):
            run_random(make(cap), Oracle(cap), rng, 2_000, cap, with_delete=False)
    suite.case("randomized: 2k get/put ops over 12 keys at capacity 1, 2 and 4 "
               "vs brute-force oracle", randomized_get_put)

    def randomized_with_deletes():
        rng = random.Random(SEED)
        for cap in (3, 7):
            run_random(make(cap), Oracle(cap), rng, 3_000, cap, with_delete=True)
    suite.case("randomized: 3k get/put/delete ops over 12 keys at capacity 3 and 7 "
               "vs brute-force oracle", randomized_with_deletes)

    if suite.failed or not suite.passed:
        suite.section("PERFORMANCE")
        reason = ("fix correctness failures first" if suite.failed
                  else "nothing implemented yet")
        suite.skip("all performance checks", reason)
        return suite.summary()

    suite.section("PERFORMANCE")

    def churn(capacity):
        # fill 3x over (2·capacity evictions once full), hit every resident
        # key once in shuffled order (each hit is a recency move), then miss
        # on `capacity` long-evicted keys
        keys = [f"k{i}" for i in range(3 * capacity)]
        hits = keys[2 * capacity:]
        random.Random(SEED).shuffle(hits)
        misses = keys[:capacity]

        def run():
            c = cls(capacity)
            for i, k in enumerate(keys):
                c.put(k, i)
            for k in hits:
                c.get(k)
            for k in misses:
                c.get(k)
        return run

    def op_scaling():
        t_small = bench(churn(2_000), repeat=2)
        t_big = bench(churn(8_000), repeat=2)
        ratio = t_big / max(t_small, 1e-9)
        suite.info(f"capacity 2k / 10k ops: {fmt_s(t_small)}   "
                   f"capacity 8k / 40k ops: {fmt_s(t_big)}   "
                   f"ratio {ratio:.1f}x (O(1) per op ≈ 4x)")
        assert ratio < 10, \
            (f"4x the capacity and 4x the ops took {ratio:.1f}x longer — "
             f"get/put is doing O(capacity) work per call. Is recency kept in "
             f"a plain list (remove / insert(0) / pop(0) walk or shift the "
             f"whole list), or does eviction scan every entry for the oldest "
             f"one? Target: O(1) per op — OrderedDict.move_to_end + "
             f"popitem(last=False), or a dict of nodes in a doubly-linked list.")
    suite.case("get/put cost stays O(1) as the cache grows", op_scaling)

    def timed_deletes(capacity, n_del=4_000, repeat=3):
        # best-of-N seconds for n_del (delete, re-put) pairs on keys spread
        # evenly across the recency order of a full cache. The re-put keeps
        # the cache full and adds a fixed O(1) cost per pair, so the ratio
        # reflects delete's dependence on cache size rather than cache-miss
        # noise from the bigger dict. Build time is not timed.
        stride = capacity // n_del
        targets = [f"k{i}" for i in range(0, capacity, stride)][:n_del]
        best = float("inf")
        for _ in range(repeat):
            c = cls(capacity)
            for i in range(capacity):
                c.put(f"k{i}", i)
            t0 = time.perf_counter()
            for k in targets:
                c.delete(k)
                c.put(k, 0)
            best = min(best, time.perf_counter() - t0)
        return best

    def delete_independence():
        t_small = timed_deletes(20_000)
        t_big = timed_deletes(80_000)
        ratio = t_big / max(t_small, 1e-9)
        suite.info(f"4k delete+re-put pairs in a 20k-entry cache: {fmt_s(t_small)}   "
                   f"in an 80k-entry cache: {fmt_s(t_big)}   ratio {ratio:.1f}x "
                   f"(O(1) ≈ 1x)")
        assert ratio < 3, \
            (f"the same 4k delete+re-put pairs took {ratio:.1f}x longer in a "
             f"cache 4x bigger — delete is walking the recency structure to "
             f"find the key (list.remove? a linked-list walk instead of the "
             f"dict lookup?). Target: O(1) — find the node through the dict "
             f"and unlink it, independent of how many other entries exist.")
    suite.case("delete cost independent of cache size", delete_independence)

    def note_followups():
        raise PerfConcern(
            "not machine-checkable: the DISCUSS AFTERWARDS tail. Rehearse the "
            "hand-rolled version (dict of nodes + doubly-linked list with "
            "sentinel head/tail — every op is unlink + push-to-back), TTL on "
            "top (lazy expiry on get; an expired entry is dropped even if it "
            "is the most recent), why O(1) LFU is harder (frequency buckets, "
            "each its own LRU list), why get is a WRITE in an LRU (it "
            "reorders, so one lock covers reads and writes), and whether to "
            "cache negative vendor results.")
    suite.case("hand-rolled DLL / TTL / LFU / locking / negative-caching story",
               note_followups)

    return suite.summary()


if __name__ == "__main__":
    sys.exit(1 if main().failed else 0)
