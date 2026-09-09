"""
PROBLEM 1 — Sliding-Window Rate Limiter
=======================================
Difficulty: warm-up → medium | Timebox: 35 min | Interview frequency: very high

CONTEXT
-------
An outbound-email platform must cap how many emails each connected mailbox
sends, or providers start flagging the domain. You are building the
in-process rate limiter that the send path consults before every send.

SPEC
----
Implement `RateLimiter`:

    limiter = RateLimiter(max_requests=100, window_seconds=60.0)
    limiter.allow(key: str, timestamp: float) -> bool

- `allow` returns True and RECORDS the request if `key` has made fewer
  than `max_requests` requests in the half-open window
  `(timestamp - window_seconds, timestamp]`; otherwise returns False and
  records nothing (denied requests do not count against the caller).
- Timestamps for a given key arrive in non-decreasing order. Different
  keys are independent.
- Use a true sliding window (per-request timestamps), not fixed buckets:
  the count at time T considers exactly the requests in the last
  `window_seconds` before T.

EXAMPLES
--------
    limiter = RateLimiter(max_requests=2, window_seconds=10.0)
    limiter.allow("mbox_a", 1.0)   -> True
    limiter.allow("mbox_a", 2.0)   -> True
    limiter.allow("mbox_a", 3.0)   -> False   # 2 already in (‑7.0, 3.0]
    limiter.allow("mbox_a", 11.1)  -> True    # request at 1.0 has aged out
    limiter.allow("mbox_b", 3.0)   -> True    # independent key

EXAMPLES — EXTENSION 1 (remaining)
----------------------------------
    limiter = RateLimiter(max_requests=2, window_seconds=10.0)
    limiter.allow("mbox_a", 1.0)      -> True
    limiter.remaining("mbox_a", 1.0)  -> 1
    limiter.allow("mbox_a", 2.0)      -> True
    limiter.remaining("mbox_a", 2.0)  -> 0
    limiter.remaining("mbox_a", 11.5) -> 2    # both requests aged out
    limiter.remaining("never_seen", 0.0) -> 2

EXAMPLES — EXTENSION 3 (overrides)
----------------------------------
    limiter = RateLimiter(max_requests=2, window_seconds=10.0,
                          overrides={"vip_mbox": 3})
    limiter.allow("vip_mbox", 1.0) -> True
    limiter.allow("vip_mbox", 1.1) -> True
    limiter.allow("vip_mbox", 1.2) -> True    # third allowed by override
    limiter.allow("vip_mbox", 1.3) -> False
    limiter.allow("other", 2.0)    -> True
    limiter.allow("other", 2.1)    -> True
    limiter.allow("other", 2.2)    -> False   # default cap of 2 still applies

ASSUMPTIONS YOU'D NORMALLY HAVE TO ASK ABOUT (decided here)
-----------------------------------------------------------
- Denied requests are not recorded (no penalty).
- Window is half-open: a request exactly `window_seconds` old no longer counts.
- Single process, single thread. Memory should stay O(active requests),
  so evict aged-out timestamps as you go.
- Extension 2 only: assume timestamps are globally non-decreasing across
  keys (one real clock). The base spec guarantees ordering per key only —
  the EXAMPLES block even goes backwards globally — but cross-key idle
  cleanup needs a shared notion of "now" to be well-defined.

PRACTICE NOTE: in the real interview, items in this section arrive as
YOUR clarifying questions. Rehearse asking them out loud before coding.

EXTENSIONS (attempt in order after the base version passes your own
manual checks; each is a typical live follow-up)
----------------------------------------------------------------
1. `remaining(key, timestamp) -> int` — how many sends are left right now.
2. Idle-key cleanup: after the base version, `allow` must also fully
   forget keys with no requests in the current window. What's the
   worst-case memory now?
3. Per-key overrides: `RateLimiter(..., overrides={"vip_mbox": 1000})` —
   each value is that key's max_requests, replacing the default cap for
   that key only. window_seconds is never overridden; keys not listed
   keep the constructor's max_requests.
4. Discuss only (write a short comment block, no code): what changes if
   this must work across 10 API servers? Where does the state live, and
   what race appears?

TARGET COMPLEXITY
-----------------
Amortized O(1) per `allow` call; O(requests in window) memory per key.
"""
from collections import deque

class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: float, overrides: dict[str, int] = {}) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.overrides: dict[str, int] = overrides
        self.index = {}

    def allow(self, key: str, timestamp: float) -> bool:
        self._sync(key, timestamp)
        if key not in self.index:
            self.index[key] = deque([timestamp])
            return True
        
        if len(self.index[key]) >= (self.overrides[key] if key in self.overrides else self.max_requests):
            return False

        self.index[key].append(timestamp)
        return True


    def _sync(self, key: str, timestamp: float) -> None:
        keys_to_del = []
        for k in self.index.keys():
            while len(self.index[k]) and self.index[k][0] <= timestamp - self.window_seconds:
                self.index[k].popleft()
            if k != key and not len(self.index[k]):
                keys_to_del.append(k)

        for k in keys_to_del:
            del self.index[k]


    def remaining(self, key: str, timestamp: float) -> int:
        if key not in self.index: 
            return self.max_requests

        self._sync(key, timestamp)
        
        if len(self.index[key]) >= self.max_requests:
            return 0
        
        return self.max_requests - len(self.index[key])

if __name__ == "__main__":
    from lib import run_test_cases

    test_cases = [
        [
            (RateLimiter, (2, 10.0)),
            ("allow", ("mbox_a", 1.0), True),
            ("allow", ("mbox_a", 2.0), True),
            ("allow", ("mbox_a", 3.0), False),
            ("allow", ("mbox_a", 11.1), True),
            ("allow", ("mbox_b", 3.0), True),
        ],
        [
            (RateLimiter, (2, 10.0, {"mbox_a": 3})),
            ("allow", ("mbox_a", 1.0), True),
            ("allow", ("mbox_a", 2.0), True),
            ("allow", ("mbox_a", 3.0), True),
            ("allow", ("mbox_a", 11.1), True),
            ("allow", ("mbox_b", 22), True),
        ],
    ]

    run_test_cases(test_cases)
