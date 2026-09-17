"""
PROBLEM 5 — LRU Cache
=====================
Difficulty: warm-up | Timebox: 20 min | Interview frequency: very high

CONTEXT
-------
Monaco enriches every new contact by calling a third-party vendor
(email -> company, title, LinkedIn URL). The vendor bills per lookup and
takes ~300 ms to answer, while a campaign hits the same few hundred
accounts over and over. You are building the in-process cache that sits
in front of the vendor client: fixed capacity, keep whatever was used
most recently, forget the rest.

SPEC
----
Implement `LRUCache`:

    cache = LRUCache(capacity=100)
    cache.get(key: str) -> object | None
    cache.put(key: str, value: object) -> None
    cache.delete(key: str) -> bool

- The cache holds at most `capacity` entries (`capacity` >= 1). Keys are
  strings, compared exactly. Values are arbitrary objects and never
  None, so None from `get` always means "not in the cache"; falsy values
  such as 0 or "" are ordinary values and come back as-is.
- A "use" of a key is a `get` that hits, or any `put` (insert or
  update). Each use makes that key the single most recently used one;
  the relative order of every other key is unchanged. The key whose
  last use is oldest is the least recently used (LRU) one.
- `get(key)`: return the stored value (a use). A miss returns None and
  changes nothing — not even recency.
- `put(key, value)` for a key already present: replace the value (a
  use). Never evicts — the size doesn't change.
- `put(key, value)` for a new key when the cache is full: first evict
  exactly one entry, the LRU one, then insert; the new key is now the
  most recently used.
- `delete(key)`: remove the key and return True if it is present;
  return False if it isn't. Not a use — the other keys keep their
  order — and it frees a slot for later puts.

EXAMPLES
--------
    cache = LRUCache(capacity=2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.get("a")        -> 1        # "a" is now the most recently used
    cache.put("c", 3)                 # full: evicts "b", the least recently used
    cache.get("b")        -> None
    cache.get("c")        -> 3
    cache.put("a", 10)                # update: new value, "a" most recent again, NO eviction
    cache.get("a")        -> 10
    cache.delete("c")     -> True
    cache.delete("c")     -> False    # already gone
    cache.put("d", 4)                 # a slot is free: nothing evicted
    cache.get("a")        -> 10
    cache.get("d")        -> 4

    # tricky: a miss is not a use
    cache = LRUCache(capacity=2)
    cache.put("a", 1)
    cache.put("b", 2)
    cache.get("zzz")      -> None     # miss: "a" is still the least recently used
    cache.put("c", 3)                 # evicts "a", not "b"
    cache.get("a")        -> None
    cache.get("b")        -> 2

ASSUMPTIONS DECIDED HERE (rehearse asking them)
-----------------------------------------------
- `capacity` is at least 1 and never changes after construction.
- Values are never None (so a None return is unambiguous); falsy values
  are real values. Keys are case-sensitive strings.
- Single process, single thread — no locking.
- Any standard-library structure is fair game, `collections.OrderedDict`
  included. Be ready to explain — or write, if the interviewer asks —
  the classic dict + doubly-linked-list version; the grader accepts
  either.
- The vendor call itself is out of scope: the cache is a plain
  container and never fetches anything on a miss.

DISCUSS AFTERWARDS
------------------
- Without OrderedDict: which pair of structures gives O(1) for all three
  operations, and why do sentinel head/tail nodes remove most of the
  edge cases?
- Vendor data goes stale. How would you add a per-entry TTL without a
  background thread, and what should happen to an expired entry that is
  also the most recently used one?
- A few accounts are looked up constantly. When would LFU beat LRU
  here, and what makes O(1) LFU harder than O(1) LRU?
- Ten worker threads share this cache. Why is `get` not a read-only
  operation in an LRU, and what does that imply for locking?
- Should negative results ("vendor has never heard of this email") be
  cached as well? What could go wrong if they are — or aren't?

TARGET COMPLEXITY
-----------------
O(1) per `get`, `put` and `delete`; O(capacity) memory.
"""


class LRUCache:
    def __init__(self, capacity: int) -> None:
        raise NotImplementedError

    def get(self, key: str) -> object | None:
        raise NotImplementedError

    def put(self, key: str, value: object) -> None:
        raise NotImplementedError

    def delete(self, key: str) -> bool:
        raise NotImplementedError
