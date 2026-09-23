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

Examples:
    store = KVStore()
    store.set("a", "1")
    store.get("a")            -> "1"
    store.get("missing")      -> None
    store.delete("a")         -> True
    store.get("a")            -> None
    store.delete("a")         -> False

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

Examples:
    store = KVStore()
    store.set("s", "x", ttl_seconds=10, now=0.0)
    store.get("s", now=9.9)   -> "x"
    store.get("s", now=10.0)  -> None      # expired exactly at t0 + T
    store.set("s", "y", now=11.0)          # re-set: ttl_seconds=None → no expiry
    store.get("s", now=1e9)   -> "y"

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

Examples:
    store = KVStore()
    store.set("a", "1")
    store.begin()
    store.set("a", "2")
    store.get("a")            -> "2"
    store.begin()
    store.delete("a")         -> True
    store.delete("a")         -> False     # already masked in this txn
    store.get("a")            -> None      # delete masks the outer "2"
    store.rollback()
    store.get("a")            -> "2"
    store.commit()
    store.get("a")            -> "2"
    store.commit()            -> raises TransactionError (no open txn)

ASSUMPTIONS DECIDED HERE (rehearse asking them)
-----------------------------------------------
- Values are plain strings; keys are case-sensitive.
- `now` is monotonic non-decreasing across calls.
- TTL interacts with transactions naively: TTL metadata is just part of
  the value entry and commits/rolls back with it.
- An expired entry is absent IN ITS OWN LAYER: a read that finds an
  expired transactional entry falls through to outer layers, which may
  still hold a live value.

DISCUSS AFTERWARDS
------------------
- Prefix scans: how would you support a `keys(prefix)` that respects
  TTLs and open transactions? What does it cost with your current
  layout, and what would you change to make it cheap?
- How do expired keys actually free memory without a background thread
  (hint: opportunistic sweep budget per call)?
- How would you support `get` at a past timestamp ("time travel read")?
  What does that do to your storage layout?

TARGET COMPLEXITY
-----------------
O(1) expected for get/set/delete; begin/commit/rollback O(size of
innermost layer) or better.
"""

from __future__ import annotations


class TransactionError(Exception):
    pass

type KVIndex = dict[str, str | tuple[str, float, float]]

class KVStore:
    def __init__(self) -> None:
        self.index: KVIndex = {}
        self.transactions: list[list] = []

    def set(self, key: str, value: str, ttl_seconds: float | None = None, *, now: float = 0.0) -> None:
        if len(self.transactions):
            operation = ("delete", (key,)) if key not in self.index else ("set", (key, self.index[key]))
            self.transactions[-1].append(operation)
        
        self.index[key] = value if ttl_seconds is None else (value, now, now + ttl_seconds)
        
    def _is_key_expired(self, key: str, now: float = 0.0):
        return (
            isinstance(self.index[key], tuple) 
            and (now < self.index[key][1] or now >= self.index[key][2])
        )

    def get(self, key: str, *, now: float = 0.0) -> str | None:
        if key not in self.index: return 
        if self._is_key_expired(key, now): return 
        
        return self.index[key][0] if isinstance(self.index[key], tuple) else self.index[key]

    def delete(self, key: str, *, now: float = 0.0) -> bool:
        if key not in self.index: return False 
        if self._is_key_expired(key, now): return False

        if len(self.transactions):
            self.transactions[-1].append(("set", (key, self.index[key])))

        del self.index[key]
        return True

    def begin(self) -> None:
        self.transactions.append([])

    def commit(self) -> None:
        if not len(self.transactions): raise TransactionError
        old = self.transactions.pop()
        if len(self.transactions):
            self.transactions[-1].extend(old)

    def rollback(self) -> None:
        if not len(self.transactions): raise TransactionError
        for operation, (key, *rest) in reversed(self.transactions.pop()):
            if operation == "set":
                self.index[key] = tuple(rest) if len(rest) > 1 else rest[0]
            else:
                del self.index[key]


if __name__ == "__main__":
    from lib import run_test_cases

    test_cases = [
        [
            (KVStore),
            ("set", ("a", "1"), None),
            ("get", "a", "1"),
            ("get", "b", None ),
            ("delete", "b", False),
            ("delete", "a", True)
        ],
        [
            (KVStore),
            ("set", ("a", "1", 10.0), {"now": 5.0}, None),
            ("get", "a", {"now": 3.0}, None),
            ("get", "a", {"now": 7.0}, "1"),
            ("delete", "a", {"now": 0.0}, False),
            ("delete", "a", {"now": 10.0}, True)
        ],
        [
            (KVStore),
            ("set", ("a", "1"), None),
            ("begin", (), None),
            ("set", ("a", "2"), None),
            ("get", ("a"), "2"),
            ("begin", (), None),
            ("delete", ("a"), True),
            ("get", ("a"), None),
            ("rollback", (), None),
            ("get", ("a"), "2"),
            ("commit", (), None),
            ("get", ("a"), "2")
        ],
        [
            (KVStore),
            ("set", ("a", "1"), None),
            ("begin", (), None),
            ("set", ("a", "2"), None),
            ("begin", (), None),
            ("delete", ("a"), True),
            ("rollback", (), None),
            ("rollback", (), None),
            ("get", ("a"), "1")
        ],
        [
            (KVStore),
            ("begin", (), None),
            ("set", ("k5", "9"), None),
            ("rollback", (), None),
            ("get", "k5", None)
        ],
        [
            (KVStore),
            ("set", ("k2", "v1"), None),
            ("begin", (), None),
            ("delete", ("k2",), True),
            ("set", ("k2", "v2"), None),
            ("rollback", (), None),
            ("get", "k2", "v1")
        ],
        [
            (KVStore),
            ("set", ("k7", "v1"), None),
            ("begin", (), None),
            ("begin", (), None),
            ("set", ("k7", "v2"), None),
            ("commit", (), None),
            ("rollback", (), None),
            ("get", "k7", "v1")
        ]
    ]

    run_test_cases(test_cases)