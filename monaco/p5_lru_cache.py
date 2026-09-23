"""
PROBLEM 5 — LRU Cache
=====================
Difficulty: warm-up | Timebox: 25 min (hard stop) | Interview frequency: very high

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
- Standard library only. The grader checks behavior and the complexity
  bar, not which structures you picked.
- The vendor call itself is out of scope: the cache is a plain
  container and never fetches anything on a miss.

DISCUSS AFTERWARDS
------------------
- If the interviewer bans whatever standard-library shortcut you used:
  how do you still get O(1) for all three operations from primitives,
  and where do the edge cases hide?
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
from __future__ import annotations

class Node:
    def __init__(self, key: str, value: object, left: Node | None = None, right: Node | None = None):
        self.key = key
        self.value = value
        self.left = left
        self.right = right

class LRUCache:
    def __init__(self, capacity: int) -> None:
        self.capacity: int = capacity
        self.index: dict[str, Node] = {}
        self.start: Node | None = None
        self.end: Node | None = None
        self.count: int = 0
    
    def get(self, key: str) -> object | None:
        if key not in self.index: return None

        if self.index[key] == self.start:
             return self.index[key].value

        left = self.index[key].left
        left.right = self.index[key].right

        if self.index[key] == self.end:
            self.end = left
        else: 
            self.index[key].right.left = left
        
        prev_start = self.start
        self.index[key].right = prev_start
        self.index[key].left = None
        self.start = self.index[key]

        prev_start.left = self.index[key]

        return self.index[key].value

    def put(self, key: str, value: object) -> None:
        if key in self.index:
            self.get(key)
            self.index[key].value = value
            return
        
        if self.count == self.capacity:
          self.get(self.end.key)

          prev_key = self.start.key
          self.start.key = key
          del self.index[prev_key]

          self.start.value = value
          self.index[key] = self.start
          return 

        node = Node(key, value)

        if not self.start and not self.end:
          self.start = node
          self.end = node
        else:
          node.right = self.start
          self.start.left = node
          self.start = node
            
        self.index[key] = node
        self.count += 1
        
            
    def get_all(self):
        results = []
        next = self.start 
        while next:
            results.append((next.key, next.value))
            next = next.right
        return results 

    def delete(self, key: str) -> bool:
        if key not in self.index: return False

        dead_node = self.index[key]
        if dead_node.left and dead_node.right:
            dead_node.left.right = dead_node.right
            dead_node.right.left = dead_node.left
        if not dead_node.right and not dead_node.left:
            self.start = None
            self.end = None
        elif not dead_node.right:
            self.end = dead_node.left
            dead_node.left.right = None
        elif not dead_node.left:
            self.start = dead_node.right
            dead_node.right.left = None

        self.count -= 1
        del self.index[key]
        return True

if __name__ == "__main__":
    from lib import run_test_cases, show

    test_cases = [
        [
            (LRUCache, (2,)),
            ("put", ("mbox_a", {"amount": 1.0}), None),
            ("put", ("mbox_b", {"meep": "morp"}), None),
            ("get_all", (), [("mbox_b", {"meep": "morp"}), ("mbox_a", {"amount": 1.0})] ),
            ("put", ("mbox_c", {"action": "bye A"}), None),
            ("get_all", (), [("mbox_c", {"action": "bye A"}), ("mbox_b", {"meep": "morp"})] ),
            ("put", ("mbox_b", {"hello": "world"}), None),
        ],
        [
            (LRUCache, (1,)),
            ("put", ("mbox_a", {"amount": 1.0}), None),
            ("put", ("mbox_b", {"meep": "morp"}), None),
            ("get_all", (), [("mbox_b", {"meep": "morp"})] ),
            ("get", ("mbox_a"), None)
        ],
        [
            (LRUCache, (2,)),
            ("put", ("mbox_a", {"amount": 1.0}), None),
            ("put", ("mbox_b", {"meep": "morp"}), None),
            ("delete", ("mbox_b"), True ),
            ("get_all", (), [ ("mbox_a", {"amount": 1.0})] ),
            ("put", ("mbox_b", {"meep": "morp"}), None),
            ("delete", ("mbox_a"), True ),
            ("get_all", (), [ ("mbox_b", {"meep": "morp"})] ),
        ],
        [
            (LRUCache, (2,)),
            ("put", ("mbox_a", {"amount": 1.0}), None),
            ("put", ("mbox_b", {"meep": "morp"}), None),
            ("get", ("mbox_a"), {"amount": 1.0}),
            ("get_all", (), [("mbox_a", {"amount": 1.0}), ("mbox_b", {"meep": "morp"})] ),
        ],
        [
            (LRUCache, (2,)),
            ("put", ("a", 1), None),
            ("put", ("b", 2), None),
            ("get", ("a"), 1),
            ("get_all", (), [("a", 1), ("b", 2)] ),
            ("put", ("c", 3), None),
            ("get_all", (), [("c", 3), ("a", 1)] ),
        ],
        [
            (LRUCache, (1,)),
            ("put", ("a", 1), None),
            ("get", ("a"), 1),
            ("put", ("b", 2), None)
        ],
        [
            (LRUCache, (3,)),
            ("put", ("a", 1), None),
            ("put", ("b", 2), None),
            ("put", ("c", 3), None),
            ("get", ("a"), 1),
            ("put", ("d", 4), None),
            ("get", ("b"), None),
            ("get", ("c"), 3)
        ],
        [
            (LRUCache, (1,)),
            ("put", ("b", 3), None),
            ("delete", ("b"), True),
        ],
    ]

    run_test_cases(test_cases)