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

ASSUMPTIONS YOU'D NORMALLY HAVE TO ASK ABOUT (decided here)
-----------------------------------------------------------
- Denied requests are not recorded (no penalty).
- Window is half-open: a request exactly `window_seconds` old no longer counts.
- Single process, single thread. Memory should stay O(active requests),
  so evict aged-out timestamps as you go.

PRACTICE NOTE: in the real interview, items in this section arrive as
YOUR clarifying questions. Rehearse asking them out loud before coding.

EXTENSIONS (attempt in order after the base version passes your own
manual checks; each is a typical live follow-up)
----------------------------------------------------------------
1. `remaining(key, timestamp) -> int` — how many sends are left right now.
2. Idle-key cleanup: after the base version, `allow` must also fully
   forget keys with no requests in the current window. What's the
   worst-case memory now?
3. Per-key overrides: `RateLimiter(..., overrides={"vip_mbox": 1000})`.
4. Discuss only (write a short comment block, no code): what changes if
   this must work across 10 API servers? Where does the state live, and
   what race appears?

TARGET COMPLEXITY
-----------------
Amortized O(1) per `allow` call; O(requests in window) memory per key.
"""


class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: float) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    def allow(self, key: str, timestamp: float) -> bool:
        raise NotImplementedError
