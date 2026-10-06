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
    to_bold = set(phrases)
    start = None
    results = []
    results_to_bold = set()

    text = text + " "
    for end in range(len(text)):
        if start == None: 
            start = end
            continue

        if text[end] is not " ": continue

        candidate = text[start:end]
        start = None

        if candidate not in to_bold:
            results.append(candidate)
            continue

        last = len(results) - 1
        if last not in results_to_bold:
            results.append(candidate)
            results_to_bold.add(len(results) - 1)
            continue
            
        results[last] = f'{results[last]} {candidate}'

    return " ".join([f'<b>{results[i]}</b>' if i in results_to_bold else results[i] for i in range(len(results))])

def highlight_cited(text: str, sources: list[str]) -> str:
    citations = {sources[i]: i for i in range(len(sources))}
    start = None
    results = []
    results_to_bold = {}

    text = text + " "
    for end in range(len(text)):
        if start == None: 
            start = end
            continue

        if text[end] is not " ": continue

        candidate = text[start:end]
        start = None
        last = len(results) - 1
        lookback = f'{results[last]} {candidate}' if len(results) else None

        if lookback in citations:
            results[last] = lookback
            if last not in results_to_bold: 
                results_to_bold[last] = [citations[lookback]]
                continue

            results_to_bold[last].append(citations[lookback])
            continue

        
        if candidate not in citations:
            results.append(candidate)
            continue
        
        if last not in results_to_bold:
            results.append(candidate)
            results_to_bold[len(results) - 1] = [citations[candidate]]
            continue

        result = f'{results[last]} {candidate}'

        if result in citations: results_to_bold[last].append(citations[candidate])

        results[last] = result


    result = ""

    for i in range(len(results)):
        result += " "
        if i not in results_to_bold:
            result += results[i]
            continue
        
        group_citations = f'[{",".join(map(str, results_to_bold[i]))}]'
        result += f'<b>{results[i]}</b>{group_citations}'

    return result

if __name__ == "__main__":
    from lib import run_test_cases, show

    test_cases = [
        [
            (highlight, ("the quick brown fox", ["quick", "fox"]), "the <b>quick</b> brown <b>fox</b>"),
            (highlight, ("the cat and the hat", ["cat", "and"]), "the <b>cat and</b> the hat"),
        ],
        [
            (highlight_cited, ("the quick brown fox", ["fox", "quick", "quick brown"]), "the <b>quick brown</b>[1,2] <b>fox</b>[0]"),
        ]
        
    ]

    run_test_cases(test_cases)