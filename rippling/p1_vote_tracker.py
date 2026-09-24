"""
PROBLEM 1 — Article Vote Tracker
================================
Difficulty: medium | Timebox: 45 min (hard stop) — phase 1 by minute 20 |
Interview frequency: high (Rippling phone screen, 2025–2026)

CONTEXT
-------
Rippling's internal knowledge base lets employees upvote or downvote
posts (rollout guides, policy explainers). Product wants a live score
per post and, for a "changed my mind" analytics widget, the posts a
given employee most recently flipped their vote on. Everything lives in
one process's memory; there is no database in this exercise.

SPEC — PHASE 1 (votes and scores)
---------------------------------
    tracker = VoteTracker()
    tracker.vote(user_id: str, article_id: str, direction: str) -> None
    tracker.score(article_id: str) -> int

- `direction` is "up" or "down". Each user has at most ONE standing vote
  per article: voting again in the same direction changes nothing;
  voting in the other direction replaces the old vote (a "flip").
- `score(article_id)` is the number of standing "up" votes minus the
  number of standing "down" votes. An article nobody has voted on
  scores 0.

Examples:
    tracker = VoteTracker()
    tracker.vote("dan", "a1", "up")
    tracker.score("a1")             -> 1
    tracker.vote("dan", "a1", "up")             # same vote again: ignored
    tracker.score("a1")             -> 1
    tracker.vote("eve", "a1", "down")
    tracker.score("a1")             -> 0
    tracker.vote("dan", "a1", "down")           # dan flips: his +1 becomes -1
    tracker.score("a1")             -> -2
    tracker.score("never_voted_on") -> 0

SPEC — PHASE 2 (recent flips)
-----------------------------
    tracker.recent_flips(user_id: str) -> list[str]

- Returns the DISTINCT articles this user has flipped a vote on, most
  recent flip first, capped at the three most recent. A first vote on
  an article is not a flip; repeating a vote is not a flip.
- Flipping an article that is already in the user's list moves it to
  the front — each article appears at most once.
- A user who has never flipped (or never voted) gets [].

Examples:
    tracker = VoteTracker()
    tracker.vote("dan", "a1", "up")
    tracker.vote("dan", "a2", "up")
    tracker.vote("dan", "a3", "up")
    tracker.recent_flips("dan")     -> []                  # first votes are not flips
    tracker.vote("dan", "a1", "down")                      # flip
    tracker.vote("dan", "a2", "down")                      # flip
    tracker.vote("dan", "a2", "down")                      # repeat: not a flip
    tracker.recent_flips("dan")     -> ["a2", "a1"]        # most recent first
    tracker.vote("dan", "a3", "down")
    tracker.vote("dan", "a4", "up")
    tracker.vote("dan", "a4", "down")
    tracker.recent_flips("dan")     -> ["a4", "a3", "a2"]  # only the three most recent
    tracker.vote("dan", "a1", "up")                        # a1 flips again: back to the front
    tracker.recent_flips("dan")     -> ["a1", "a4", "a3"]
    tracker.recent_flips("nobody")  -> []

ASSUMPTIONS DECIDED HERE (rehearse asking them)
-----------------------------------------------
- `direction` is always exactly "up" or "down"; ids are case-sensitive
  strings. There is no "remove my vote" operation.
- Articles are not registered up front: the first vote on an id creates
  it, and `score` of an unknown id is 0.
- Calls arrive one at a time from a single thread; "most recent" means
  call order — there are no timestamps.
- The cap of three is fixed; `recent_flips` returns a fresh list the
  caller may mutate.

DISCUSS AFTERWARDS
------------------
- Product now wants the ten highest-scoring articles, live. What does
  that cost per vote with your layout, and what would you keep updated
  to make it cheap?
- Memory: what grows without bound here, and what would you cap or
  expire first?

TARGET COMPLEXITY
-----------------
O(1) per `vote` and per `score`; `recent_flips` in O(1) — its cost must
not depend on how many votes or flips the user has made in total.
"""
from collections import OrderedDict

class VoteTracker:
    def __init__(self) -> None:
        self.votes: dict[str, str] = {}
        self.scores: dict[str, int] = {}
        self.flips: dict[str, OrderedDict] = {}

    def _get_vote_key(self, user_id: str, article_id: str):
        return (user_id, article_id)

    def vote(self, user_id: str, article_id: str, direction: str) -> None:
        if article_id not in self.scores:
            self.scores[article_id] = 0

        

        vote_key = self._get_vote_key(user_id, article_id)

        if vote_key not in self.votes:
            if user_id not in self.flips:
                self.flips[user_id] = OrderedDict()
            self.scores[article_id] += -1 if direction == "down" else 1
        elif vote_key in self.votes and self.votes[vote_key] != direction:
            self.scores[article_id] += -2 if direction == "down" else 2

            if len(self.flips[user_id]) == 3 and article_id not in self.flips[user_id]:
                least_recent_key = next(iter(self.flips[user_id]))
                del self.flips[user_id][least_recent_key]

            if article_id in self.flips[user_id]:
                self.flips[user_id].move_to_end(article_id)
            else:
                self.flips[user_id][article_id] = None 

        self.votes[vote_key] = direction
            

    def score(self, article_id: str) -> int:
        if article_id not in self.scores: return 0

        return self.scores[article_id]

    def recent_flips(self, user_id: str) -> list[str]:
        if user_id not in self.flips:
            return []
        
        return list(reversed(self.flips[user_id]))
       


if __name__ == "__main__":
    from lib import run_test_cases, show

    test_cases = [
        [
            (VoteTracker),
            ("vote", ("dan", "a1", "up"), None),
            ("score", ("a1"), 1),
            ("vote", ("dan", "a1", "up"), None),
            ("score", ("a1"), 1),
            ("vote", ("eve", "a1", "down"), None),
            ("score", ("a1"), 0),
            ("vote", ("dan", "a1", "down"), None),
            ("score", ("a1"), -2),
            ("score", ("no votes"), 0),
        ],
        [
            (VoteTracker),
            ("vote", ("dan", "a1", "up"), None),
            ("vote", ("dan", "a2", "up"), None),
            ("vote", ("dan", "a3", "up"), None),
            ("recent_flips", ("dan"), []),
            ("vote", ("dan", "a1", "down"), None),
            ("vote", ("dan", "a2", "down"), None),
            ("vote", ("dan", "a2", "down"), None),
            ("recent_flips", ("dan"), ["a2", "a1"]),
        ]
        
    ]

    run_test_cases(test_cases)