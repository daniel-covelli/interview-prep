# Problem 1: Top-K Counter
#
# Design a class that keeps track of how many times items occur and can
# efficiently return the top k most frequent items, where k is a variable
# supplied at query time.
#
#   c.increment(item)   record one occurrence of item
#   c.count(item)       current count for item, 0 if never seen
#   c.top_k(k)          list of (item, count) pairs, highest count first
#
# k == 0 returns []; k < 0 raises ValueError; k larger than the number of
# distinct items returns everything (still sorted); items tied on count may
# come back in any order.
#
# Example:
#   c = TopKCounter()
#   for x in ["a", "b", "a", "c", "a", "b"]:
#       c.increment(x)
#   c.count("a")    -> 3
#   c.count("zzz")  -> 0
#   c.top_k(2)      -> [("a", 3), ("b", 2)]
#   c.top_k(10)     -> [("a", 3), ("b", 2), ("c", 1)]
#   c.top_k(0)      -> []
from prep_lib import run_test_cases
from collections import Counter 

class TopKCounter:
    def __init__(self):
        self.items = []
        self.pos = {}
        self.block_start = {}

    def increment(self, item: str):
        if item not in self.pos:
            self.items.append((item, 1))
            self.pos[item] = len(self.items) - 1
            self.block_start.setdefault(1, len(self.items) - 1)
            return

        p = self.pos[item]
        old = self.items[p][1]
        new = old + 1

        # swap with the leftmost element of the old-count block
        t = self.block_start[old]
        other = self.items[t][0]
        self.items[p], self.items[t] = self.items[t], self.items[p]
        self.pos[item], self.pos[other] = t, p

        self.items[t] = (item, new)

        # old block shrinks from the left; drop its entry if now empty
        self.block_start[old] += 1
        s = self.block_start[old]
        if s >= len(self.items) or self.items[s][1] != old:
            del self.block_start[old]

        # slot t now belongs to the new-count block
        self.block_start.setdefault(new, t)
    



    def count(self, item: str):
        if item not in self.pos: return 0

        return self.items[self.pos[item]][1]

    def top_k(self, k: int):
      if 0 > k: raise ValueError
      return self.items[:k]

if __name__ == "__main__":
    test_cases = [ 
        [
            ("increment", "a", None),
            ("increment", "a", None),
            ("increment", "c", None),
            ("increment", "b", None),
            ("increment", "b", None),
            ("increment", "b", None),
            ("increment", "b", None),
            ("increment", "c", None),
            ("increment", "c", None),
            ("count", "b", 4),
            ("top_k", (3,), [("b", 4), ("c", 3), ("a", 2)]), 
        ],
    ]

    run_test_cases(test_cases, TopKCounter, None)

