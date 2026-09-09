# Grader for Monaco Problem 2 (monaco/p2_kv_store.py).
# SPOILER WARNING: this file enumerates edge cases. Run it, don't read it.
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from grader import (Suite, PerfConcern, load_class, bench, fmt_s, tracing,
                      expect, expect_raises)

SEED = 0x5EED2


_DELETED = object()


class Oracle:
    """Brute-force truth: a stack of dict layers. Each entry is
    (value, expires_at | None) or the _DELETED tombstone. Reads walk
    top-down; an expired entry counts as absent IN THAT LAYER (the
    randomized generator only writes TTLs at the base layer, so the
    ambiguous expired-shadow-over-live-value case never arises)."""

    def __init__(self):
        self.layers = [{}]

    def set(self, key, value, ttl_seconds=None, *, now=0.0):
        expires = None if ttl_seconds is None else now + ttl_seconds
        self.layers[-1][key] = (value, expires)

    def _lookup(self, key, now):
        for layer in reversed(self.layers):
            if key in layer:
                entry = layer[key]
                if entry is _DELETED:
                    return None
                value, expires = entry
                if expires is not None and now >= expires:
                    continue
                return value
        return None

    def get(self, key, *, now=0.0):
        return self._lookup(key, now)

    def delete(self, key, *, now=0.0):
        existed = self._lookup(key, now) is not None
        if len(self.layers) == 1:
            self.layers[0].pop(key, None)
        else:
            self.layers[-1][key] = _DELETED
        return existed

    def begin(self):
        self.layers.append({})

    def commit(self):
        top = self.layers.pop()
        parent = self.layers[-1]
        for key, entry in top.items():
            if entry is _DELETED and len(self.layers) == 1:
                parent.pop(key, None)
            else:
                parent[key] = entry

    def rollback(self):
        self.layers.pop()

    @property
    def depth(self):
        return len(self.layers) - 1


def main():
    suite = Suite("Monaco 2: KVStore")
    cls, err = load_class("monaco.p2_kv_store", "KVStore")
    if cls is None:
        suite.skip_all(err)
        return suite.summary()
    TransactionError, terr = load_class("monaco.p2_kv_store", "TransactionError")
    if TransactionError is None:
        suite.skip_all(terr)
        return suite.summary()
    make = tracing(cls)

    suite.section("PHASE 1 — BASIC STORE")

    def basics():
        st = make()
        st.set("a", "1")
        expect(st.get("a"), "1")
        expect(st.get("missing"), None, note="absent key reads as None")
        st.set("a", "2")
        expect(st.get("a"), "2", note="set overwrites")
        expect(st.delete("a"), True, note="deleting an existing key -> True")
        expect(st.get("a"), None)
        expect(st.delete("a"), False, note="deleting an absent key -> False")
    suite.case("set / get / overwrite / delete", basics)

    def case_sensitive():
        st = make()
        st.set("Key", "upper")
        st.set("key", "lower")
        expect(st.get("Key"), "upper")
        expect(st.get("key"), "lower")
        expect(st.delete("KEY"), False, note="keys are case-sensitive")
    suite.case("keys are case-sensitive", case_sensitive)

    suite.section("PHASE 2 — TTL")

    def ttl_boundary():
        st = make()
        st.set("s", "x", ttl_seconds=10, now=0.0)
        expect(st.get("s", now=0.0), "x", note="alive at its own set time")
        expect(st.get("s", now=9.9), "x", note="alive while now < t0 + ttl")
        expect(st.get("s", now=10.0), None,
               note="expired exactly AT now == t0 + ttl (>= is dead)")
        expect(st.get("s", now=50.0), None)
    suite.case("expiry boundary is exactly now >= t0 + ttl", ttl_boundary)

    def ttl_none_lives_forever():
        st = make()
        st.set("k", "v", now=0.0)
        expect(st.get("k", now=1e12), "v",
               note="ttl_seconds=None means no expiry")
    suite.case("no TTL means no expiry", ttl_none_lives_forever)

    def reset_replaces_ttl():
        st = make()
        st.set("k", "v1", ttl_seconds=10, now=0.0)
        st.set("k", "v2", now=5.0)
        expect(st.get("k", now=1000.0), "v2",
               note="re-set with ttl_seconds=None must clear the old TTL entirely")
        st.set("k", "v3", ttl_seconds=10, now=1000.0)
        expect(st.get("k", now=1009.9), "v3",
               note="new TTL counts from the new set time")
        expect(st.get("k", now=1010.0), None)
    suite.case("re-setting a key replaces its TTL entirely", reset_replaces_ttl)

    def expired_is_absent():
        st = make()
        st.set("k", "v", ttl_seconds=5, now=0.0)
        expect(st.delete("k", now=5.0), False,
               note="deleting an expired key behaves like deleting an absent key")
        st.set("k", "fresh", now=6.0)
        expect(st.get("k", now=100.0), "fresh",
               note="a key can be re-set after expiring")
        st2 = make()
        st2.set("d", "v", ttl_seconds=5, now=0.0)
        expect(st2.delete("d", now=4.9), True,
               note="deleting a still-alive TTL key -> True")
        expect(st2.get("d", now=4.95), None)
    suite.case("an expired key is exactly like an absent key", expired_is_absent)

    suite.section("PHASE 3 — TRANSACTIONS")

    def spec_example():
        st = make()
        st.set("a", "1")
        st.begin()
        st.set("a", "2")
        expect(st.get("a"), "2")
        st.begin()
        st.delete("a")
        expect(st.get("a"), None,
               note="a transactional delete must MASK the outer value")
        st.rollback()
        expect(st.get("a"), "2", note="rollback restores the outer layer's view")
        st.commit()
        expect(st.get("a"), "2")
    suite.case("spec example from the file header", spec_example)

    def reads_fall_through():
        st = make()
        st.set("base", "b")
        st.begin()
        st.set("mid", "m")
        st.begin()
        expect(st.get("base"), "b",
               note="reads fall through every open layer to the base")
        expect(st.get("mid"), "m")
        expect(st.get("nope"), None)
    suite.case("reads fall through nested layers", reads_fall_through)

    def commit_merges_into_parent():
        st = make()
        st.begin()
        st.set("a", "outer")
        st.begin()
        st.set("a", "inner")
        st.commit()
        expect(st.get("a"), "inner",
               note="inner commit merges into the OUTER TXN, not the base")
        st.rollback()
        expect(st.get("a"), None,
               note="rolling back the outer txn must discard the committed "
                    "inner write too — it never reached the base")
    suite.case("commit merges into the parent layer, not the base", commit_merges_into_parent)

    def rollback_discards_deletes():
        st = make()
        st.set("a", "1")
        st.begin()
        expect(st.delete("a"), True,
               note="delete of a key visible from an outer layer -> True")
        expect(st.delete("a"), False,
               note="second delete: the key is now masked, so it 'doesn't exist'")
        st.rollback()
        expect(st.get("a"), "1")
    suite.case("rollback discards transactional deletes", rollback_discards_deletes)

    def committed_delete_propagates():
        st = make()
        st.set("a", "1")
        st.begin()
        st.delete("a")
        st.commit()
        expect(st.get("a"), None,
               note="a committed delete must keep masking / remove the base key")
        expect(st.delete("a"), False)
        st.set("a", "again")
        expect(st.get("a"), "again")
    suite.case("committed deletes reach the base store", committed_delete_propagates)

    def txn_errors():
        st = make()
        expect_raises(TransactionError, lambda: st.commit(),
                      note="commit with no open transaction")
        expect_raises(TransactionError, lambda: st.rollback(),
                      note="rollback with no open transaction")
        st.begin()
        st.commit()
        expect_raises(TransactionError, lambda: st.commit(),
                      note="the earlier begin was already committed")
        st.begin()
        st.rollback()
        expect_raises(TransactionError, lambda: st.rollback(),
                      note="the earlier begin was already rolled back")
    suite.case("commit/rollback with no open txn raise TransactionError", txn_errors)

    def ttl_inside_txn():
        st = make()
        st.set("k", "base", now=0.0)
        st.begin()
        st.set("k", "tx", ttl_seconds=10, now=0.0)
        expect(st.get("k", now=5.0), "tx")
        st.rollback()
        expect(st.get("k", now=5.0), "base",
               note="the TTL write rolled back with its layer; the base "
                    "entry (no TTL) is untouched")
        st.begin()
        st.set("t2", "x", ttl_seconds=10, now=5.0)
        st.commit()
        expect(st.get("t2", now=14.9), "x",
               note="TTL metadata must survive the commit merge")
        expect(st.get("t2", now=15.0), None)
    suite.case("TTL metadata commits and rolls back with its layer", ttl_inside_txn)

    def randomized():
        rng = random.Random(SEED)
        st = make()
        oracle = Oracle()
        now = 0.0
        keys = [f"k{i}" for i in range(12)]
        for op in range(4_000):
            now += rng.choice([0.0, 0.0, 0.5, 2.0])
            ctx = f"seed={SEED:#x}, op={op}, now={now}"
            roll = rng.random()
            key = rng.choice(keys)
            if roll < 0.35:
                value = f"v{op}"
                # TTLs only at the base layer (see Oracle docstring)
                ttl = rng.choice([None, None, 1.0, 5.0, 30.0]) if oracle.depth == 0 else None
                st.set(key, value, ttl_seconds=ttl, now=now)
                oracle.set(key, value, ttl_seconds=ttl, now=now)
            elif roll < 0.65:
                expect(st.get(key, now=now), oracle.get(key, now=now),
                       note=f"{ctx}, get({key!r})")
            elif roll < 0.8:
                expect(st.delete(key, now=now), oracle.delete(key, now=now),
                       note=f"{ctx}, delete({key!r})")
            elif roll < 0.9 and oracle.depth < 4:
                st.begin()
                oracle.begin()
            elif oracle.depth > 0:
                if rng.random() < 0.5:
                    st.commit()
                    oracle.commit()
                else:
                    st.rollback()
                    oracle.rollback()
    suite.case("randomized: 4k mixed ops cross-checked against oracle", randomized)

    if suite.failed or not suite.passed:
        suite.section("PERFORMANCE")
        reason = ("fix correctness failures first" if suite.failed
                  else "nothing implemented yet")
        suite.skip("all performance checks", reason)
        return suite.summary()

    suite.section("PERFORMANCE")

    def churn(n_ops):
        # keep `now` monotone across all three loops (the spec grants it)
        # and TTLs long enough that every access stays on the hit path
        st = cls()
        for i in range(n_ops):
            st.set(f"k{i}", "v", ttl_seconds=(10.0 * n_ops if i % 3 else None),
                   now=float(i))
        for i in range(n_ops):
            st.get(f"k{i}", now=float(n_ops + i))
        for i in range(0, n_ops, 2):
            st.delete(f"k{i}", now=float(2 * n_ops))

    def crud_scaling():
        t_small = bench(lambda: churn(15_000), repeat=2)
        t_big = bench(lambda: churn(60_000), repeat=2)
        ratio = t_big / max(t_small, 1e-9)
        suite.info(f"15k keys: {fmt_s(t_small)}   60k keys: {fmt_s(t_big)}   "
                   f"ratio {ratio:.1f}x (linear ≈ 4x)")
        assert ratio < 10, \
            (f"4x more keys made set/get/delete {ratio:.1f}x slower — "
             f"they must stay O(1) expected per call")
    suite.case("set/get/delete cost stays O(1) as the store grows", crud_scaling)

    def txn_independent_of_base():
        def base_store(n):
            st = cls()
            for i in range(n):
                st.set(f"base{i}", "v")
            return st

        def small_txns(st):
            for i in range(150):
                st.begin()
                st.set(f"hot{i % 7}", "x")
                if i % 2:
                    st.commit()
                else:
                    st.rollback()

        st_small = base_store(30_000)
        st_big = base_store(120_000)
        t_small = bench(lambda: small_txns(st_small), repeat=3)
        t_big = bench(lambda: small_txns(st_big), repeat=3)
        ratio = t_big / max(t_small, 1e-9)
        suite.info(f"150 tiny txns over 30k-key base: {fmt_s(t_small)}   "
                   f"over 120k-key base: {fmt_s(t_big)}")
        assert ratio < 3, \
            (f"quadrupling the BASE store made tiny transactions {ratio:.1f}x "
             f"slower — begin/commit/rollback is copying or scanning the whole "
             f"store (snapshot-per-begin?). Target: O(size of the innermost "
             f"layer), independent of everything beneath it.")
    suite.case("begin/commit/rollback cost independent of base-store size",
               txn_independent_of_base)

    def note_expired_memory():
        raise PerfConcern(
            "not machine-checkable: lazily-expired entries that are never read "
            "again sit in memory forever (extension 2). Have the opportunistic "
            "sweep story ready — a bounded number of random/iterated entries "
            "checked per write, no background threads.")
    suite.case("expired-key memory / sweep story", note_expired_memory)

    return suite.summary()


if __name__ == "__main__":
    sys.exit(1 if main().failed else 0)
