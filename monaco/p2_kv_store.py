"""
PROBLEM 2 — In-Memory KV Store with TTL, then Transactions
==========================================================
Difficulty: medium | Timebox: 45 min | Interview frequency: very high

CONTEXT
-------
Classic "start tiny, keep extending" interview problem. The interviewer
watches how your design survives each new requirement — code the phases
IN ORDER and resist building phase 2/3 machinery during phase 1.

SPEC — PHASE 1 (basic store)
----------------------------
    store = KVStore()
    store.set(key: str, value: str) -> None
    store.get(key: str) -> str | None      # None if absent
    store.delete(key: str) -> bool         # True if key existed

SPEC — PHASE 2 (TTL)
--------------------
    store.set(key, value, ttl_seconds: float | None = None, *, now: float = 0.0)
    store.get(key, *, now: float = 0.0)
    store.delete(key, *, now: float = 0.0)

- Time is passed in explicitly via `now` (a float; the caller's clock).
  Never call time.time() — it makes your behavior unverifiable.
- A key set with ttl_seconds=T at time t0 is alive for reads while
  now < t0 + T, and expired (treated exactly like an absent key) when
  now >= t0 + T.
- Re-setting a key replaces its TTL entirely (ttl_seconds=None → no expiry).
- Expiry may be lazy (checked on access); no background threads.

SPEC — PHASE 3 (transactions)
-----------------------------
    store.begin() -> None                  # open a nested transaction
    store.commit() -> None                 # merge innermost txn into parent
    store.rollback() -> None               # discard innermost txn

- Reads inside a transaction see that transaction's writes, then fall
  through to outer layers.
- commit/rollback with no open transaction raises TransactionError.
- Deletes inside a transaction must mask outer values (a get after a
  transactional delete returns None even though the base layer has the key).
- `delete` returns True iff the key was visible through the layers (and
  unexpired) just before the call — so a second delete of the same key
  inside a transaction returns False.

EXAMPLES
--------
    store.set("a", "1")
    store.begin()
    store.set("a", "2")
    store.get("a")            -> "2"
    store.begin()
    store.delete("a")
    store.get("a")            -> None
    store.rollback()
    store.get("a")            -> "2"
    store.commit()
    store.get("a")            -> "2"

    store.set("s", "x", ttl_seconds=10, now=0.0)
    store.get("s", now=9.9)   -> "x"
    store.get("s", now=10.0)  -> None

ASSUMPTIONS DECIDED HERE (rehearse asking them)
-----------------------------------------------
- Values are plain strings; keys are case-sensitive.
- `now` is monotonic non-decreasing across calls.
- TTL interacts with transactions naively: TTL metadata is just part of
  the value entry and commits/rolls back with it.
- An expired entry is absent IN ITS OWN LAYER: a read that finds an
  expired transactional entry falls through to outer layers, which may
  still hold a live value.

EXTENSIONS
----------
1. `keys(prefix: str, *, now: float = 0.0) -> list[str]` — alive keys
   starting with `prefix` ("" matches everything), lexicographically
   sorted, and seen through any open transactions: uncommitted writes
   are listed, transactionally-deleted keys are not. What's the cost,
   and how would a trie change it?
2. Make expired keys actually free memory eventually without a thread
   (hint: opportunistic sweep budget per call).
3. Discuss only: how would you support `get` at a past timestamp
   ("time travel read")? What does that do to your storage layout?

TARGET COMPLEXITY
-----------------
O(1) expected for get/set/delete; begin/commit/rollback O(size of
innermost layer) or better.
"""

from __future__ import annotations


class TransactionError(Exception):
    pass


class KVStore:
    def __init__(self) -> None:
        raise NotImplementedError

    def set(self, key: str, value: str, ttl_seconds: float | None = None, *, now: float = 0.0) -> None:
        raise NotImplementedError

    def get(self, key: str, *, now: float = 0.0) -> str | None:
        raise NotImplementedError

    def delete(self, key: str, *, now: float = 0.0) -> bool:
        raise NotImplementedError

    def begin(self) -> None:
        raise NotImplementedError

    def commit(self) -> None:
        raise NotImplementedError

    def rollback(self) -> None:
        raise NotImplementedError


if __name__ == "__main__":
    import sys

    results: list[bool] = []

    def check(label: str, actual: object, expected: object) -> None:
        ok = actual == expected
        results.append(ok)
        print(f"{'PASS' if ok else 'FAIL'}  {label}  (got {actual!r}, want {expected!r})")

    def scenario(name: str, fn) -> None:
        try:
            fn()
        except NotImplementedError:
            print(f"SKIP  {name}: not implemented yet")

    def phase1_basic() -> None:
        store = KVStore()
        store.set("a", "1")
        check('get("a")', store.get("a"), "1")
        check('delete("a")', store.delete("a"), True)
        check('get("a") after delete', store.get("a"), None)
        check('delete("a") again', store.delete("a"), False)

    def phase2_ttl() -> None:
        store = KVStore()
        store.set("s", "x", ttl_seconds=10, now=0.0)
        check('get("s", now=9.9)', store.get("s", now=9.9), "x")
        check('get("s", now=10.0)', store.get("s", now=10.0), None)

    def phase3_transactions() -> None:
        store = KVStore()
        store.set("a", "1")
        store.begin()
        store.set("a", "2")
        check('get("a") in txn', store.get("a"), "2")
        store.begin()
        store.delete("a")
        check('get("a") after txn delete', store.get("a"), None)
        store.rollback()
        check('get("a") after rollback', store.get("a"), "2")
        store.commit()
        check('get("a") after commit', store.get("a"), "2")
        try:
            store.commit()
            check("commit with no open txn", "no exception", "TransactionError")
        except TransactionError:
            check("commit with no open txn", "TransactionError", "TransactionError")

    scenario("phase 1 (basic store)", phase1_basic)
    scenario("phase 2 (TTL)", phase2_ttl)
    scenario("phase 3 (transactions)", phase3_transactions)

    if not results:
        print("\nNothing checked yet — implement the stubs, then re-run.")
        sys.exit(1)
    print(f"\n{sum(results)}/{len(results)} checks passed.")
    sys.exit(0 if all(results) else 1)
