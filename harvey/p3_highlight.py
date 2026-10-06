"""
PROBLEM 3 — Highlight Source Matches
====================================
Difficulty: medium | Timebox: 60 min (hard stop) — phase 1 by minute 35 |
Interview frequency: high (Harvey phone screens and onsites, 2025–2026)

CONTEXT
-------
Bold every part of a passage that quotes one of a list of source
phrases, then say which sources each bolded part came from.

SPEC — PHASE 1 (highlight)
--------------------------
    highlight(text: str, phrases: list[str]) -> str

- A character of `text` is covered if it lies inside some occurrence of
  some phrase. Occurrences are exact, case-sensitive substring matches,
  and occurrences of the same phrase may overlap each other.
- Return `text` with every maximal run of covered characters wrapped in
  one "<b>" ... "</b>" pair. Two occurrences that overlap or touch end
  to end therefore share one pair of tags.

Examples:
    highlight("the quick brown fox", ["quick", "fox"])
        -> "the <b>quick</b> brown <b>fox</b>"
    highlight("abcdef", ["abc", "cde"])      -> "<b>abcde</b>f"      # overlap
    highlight("abcdef", ["ab", "cd"])        -> "<b>abcd</b>ef"      # touching
    highlight("ababa", ["aba"])              -> "<b>ababa</b>"       # matches at 0 and 2
    highlight("no match here", ["xyz"])      -> "no match here"
    highlight("anything", [])                -> "anything"

SPEC — PHASE 2 (citations)
--------------------------
    highlight_cited(text: str, sources: list[str]) -> str

- Same highlighting as phase 1, where a phrase's id is its index in
  `sources`. Right after each "</b>", add the ids of every source that
  has at least one occurrence inside that bolded run, in increasing
  order, as "[0,2]" (comma-separated, no spaces).

Examples:
    highlight_cited("the quick brown fox", ["fox", "quick", "quick brown"])
        -> "the <b>quick brown</b>[1,2] <b>fox</b>[0]"
    highlight_cited("abcdef", ["cde", "abc", "zz"])  -> "<b>abcde</b>[0,1]f"
    highlight_cited("a cat, a cat", ["cat"])         -> "a <b>cat</b>[0], a <b>cat</b>[0]"
    highlight_cited("abc", ["abc", "b"])             -> "<b>abc</b>[0,1]"   # one inside another

ASSUMPTIONS DECIDED HERE (rehearse asking them)
-----------------------------------------------
- Every phrase is non-empty; the same phrase may appear twice in the
  list (phase 2: then both ids are cited wherever it occurs).
- No escaping: text never contains "<", ">", "[" or "]".
- Up to 200,000 characters of text and a few dozen phrases.

DISCUSS AFTERWARDS
------------------
- With thousands of phrases instead of a few dozen, which part of your
  solution becomes the bottleneck, and what property would you want from
  a faster way to find the matches?

TARGET COMPLEXITY
-----------------
Roughly linear in the length of the text for a fixed list of phrases
(times a log factor at most). Building the result by inserting tags one
at a time into a copy of the whole text — so every bolded run costs a
pass over the text — fails the check, as does (phase 2) comparing every
bolded run against every occurrence.
"""


def highlight(text: str, phrases: list[str]) -> str:
    raise NotImplementedError


def highlight_cited(text: str, sources: list[str]) -> str:
    raise NotImplementedError
