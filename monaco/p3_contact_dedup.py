"""
PROBLEM 3 — Contact Record Deduplication & Merge
================================================
Difficulty: medium-hard | Timebox: 45 min | Interview frequency: high at
data/CRM/enrichment companies — this one is squarely in Monaco's domain.

CONTEXT
-------
A CRM ingests contact records from many sources (CSV imports, email
scraping, an enrichment vendor). The same human shows up as several
records. Collapse them into one golden record per person.

SPEC
----
    dedupe_contacts(records: list[dict]) -> list[dict]

Each input record has this shape (any value may be None except id/source/updated_at):
    {
      "id": "r1",                       # unique per record
      "email": "Jane@Acme.com",
      "phone": "(415) 555-0100",
      "name": "Jane Doe",
      "title": "VP Sales",
      "source": "enrichment",           # one of: "manual", "import", "enrichment"
      "updated_at": 1725000000,          # int epoch seconds
    }

MATCHING — two records refer to the same person if they share a
normalized email OR a normalized phone. Matching is transitive:
if A~B and B~C, then {A, B, C} is one person, even if A and C share
nothing directly.
- Email normalization: lowercase, strip whitespace.
- Phone normalization: keep digits only; if 11 digits starting with "1",
  drop the leading "1". "(415) 555-0100" ≡ "14155550100" ≡ "415-555-0100".
- None never matches None.

MERGING — one output record per group. For EACH FIELD independently
(email, phone, name, title), pick the value from the record with the
best (source_priority, updated_at) among records where that field is
non-None. source_priority: manual > import > enrichment; updated_at
(newer wins) breaks ties within a priority level.
Output record: {"ids": [...all merged record ids, sorted...], "email": ...,
"phone": ..., "name": ..., "title": ...} with email/phone in normalized
form. Output list sorted by the smallest id in each group.

EXAMPLE
-------
    r1 = {"id": "r1", "email": "jane@acme.com", "phone": None,
          "name": "Jane D.", "title": None,
          "source": "import", "updated_at": 100}
    r2 = {"id": "r2", "email": "JANE@acme.com ", "phone": "415-555-0100",
          "name": "Jane Doe", "title": "VP Sales",
          "source": "enrichment", "updated_at": 200}
    r3 = {"id": "r3", "email": None, "phone": "(415) 555-0100",
          "name": None, "title": "VP of Sales",
          "source": "manual", "updated_at": 50}

    dedupe_contacts([r1, r2, r3]) ->
    [{
      "ids": ["r1", "r2", "r3"],        # r1~r2 via email, r2~r3 via phone
      "email": "jane@acme.com",
      "phone": "4155550100",
      "name": "Jane D.",                 # import(100) beats enrichment(200)
      "title": "VP of Sales",            # manual(50) beats enrichment(200)
    }]

ASSUMPTIONS DECIDED HERE (rehearse asking them)
-----------------------------------------------
- A group may end up with records containing DIFFERENT emails (chained
  through phone). Field-merge rules above still decide the winner; the
  losing email is dropped, not kept as an alias.
- Input fits in memory; no streaming.
- Names are never used for matching (too fuzzy).

EXTENSIONS
----------
1. Keep the losers: add "all_emails" / "all_phones" (sorted, normalized,
   deduped) to each output record.
2. Batch API: `dedupe_contacts` is called nightly with yesterday's
   golden records + today's new raw records. What changes?
3. Discuss only: at 50M records, exact in-memory grouping dies. Sketch
   the shard-by-normalized-key approach and where transitivity hurts.

TARGET COMPLEXITY
-----------------
O(n α(n)) with union-find, or O(n) average with a key→group index built
in one pass. Either is acceptable; be able to say which you chose and why.
"""

from __future__ import annotations


def normalize_email(email: str | None) -> str | None:
    raise NotImplementedError


def normalize_phone(phone: str | None) -> str | None:
    raise NotImplementedError


def dedupe_contacts(records: list[dict]) -> list[dict]:
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

    def normalization() -> None:
        check('normalize_email("JANE@acme.com ")', normalize_email("JANE@acme.com "), "jane@acme.com")
        check("normalize_email(None)", normalize_email(None), None)
        check('normalize_phone("(415) 555-0100")', normalize_phone("(415) 555-0100"), "4155550100")
        check('normalize_phone("14155550100")', normalize_phone("14155550100"), "4155550100")
        check('normalize_phone("415-555-0100")', normalize_phone("415-555-0100"), "4155550100")
        check("normalize_phone(None)", normalize_phone(None), None)

    def docstring_example() -> None:
        r1 = {"id": "r1", "email": "jane@acme.com", "phone": None,
              "name": "Jane D.", "title": None,
              "source": "import", "updated_at": 100}
        r2 = {"id": "r2", "email": "JANE@acme.com ", "phone": "415-555-0100",
              "name": "Jane Doe", "title": "VP Sales",
              "source": "enrichment", "updated_at": 200}
        r3 = {"id": "r3", "email": None, "phone": "(415) 555-0100",
              "name": None, "title": "VP of Sales",
              "source": "manual", "updated_at": 50}
        expected = [{
            "ids": ["r1", "r2", "r3"],
            "email": "jane@acme.com",
            "phone": "4155550100",
            "name": "Jane D.",
            "title": "VP of Sales",
        }]
        check("dedupe_contacts([r1, r2, r3])", dedupe_contacts([r1, r2, r3]), expected)

    scenario("normalization", normalization)
    scenario("docstring example", docstring_example)

    if not results:
        print("\nNothing checked yet — implement the stubs, then re-run.")
        sys.exit(1)
    print(f"\n{sum(results)}/{len(results)} checks passed.")
    sys.exit(0 if all(results) else 1)
