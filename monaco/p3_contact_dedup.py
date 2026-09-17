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

Examples:
    normalize_email("  JANE@Acme.com ")  -> "jane@acme.com"
    normalize_email(None)                -> None
    normalize_phone("(415) 555-0100")    -> "4155550100"
    normalize_phone("14155550100")       -> "4155550100"
    normalize_phone("415-555-0100")      -> "4155550100"
    normalize_phone("5550100")           -> "5550100"      # <11 digits: untouched
    normalize_phone("21234567890")       -> "21234567890"  # 11 digits, no leading 1: keep all
    normalize_phone(None)                -> None

MERGING — one output record per group. For EACH FIELD independently
(email, phone, name, title), pick the value from the record with the
best (source_priority, updated_at) among records where that field is
non-None. source_priority: manual > import > enrichment; updated_at
(newer wins) breaks ties within a priority level.
Output record: {"ids": [...all merged record ids, sorted...], "email": ...,
"phone": ..., "name": ..., "title": ...} with email/phone in normalized
form and name/title verbatim from their winning records. All five keys
are always present; a field that no record in the group has stays None.
Output list sorted by the smallest id in each group (plain string
comparison — ids are strings).

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
    r4 = {"id": "r2", "email": "daniel@acme.com ", "phone": "415-555-0100",
              "name": "Jane Doe", "title": "VP Sales",
              "source": "enrichment", "updated_at": 200}

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
- A value that normalizes to the empty string (e.g. a phone with no
  digits) matches nothing, same as None.
- Two candidates for a field never tie exactly on
  (source_priority, updated_at); don't design for it.

DISCUSS AFTERWARDS
------------------
- Batch API: `dedupe_contacts` is called nightly with yesterday's golden
  records + today's new raw records. What changes?
- At 50M records, exact in-memory grouping dies. Sketch the
  shard-by-normalized-key approach and where transitivity hurts.

TARGET COMPLEXITY
-----------------
O(n α(n)) with union-find, or O(n) average with a key→group index built
in one pass. Either is acceptable; be able to say which you chose and why.
"""

from __future__ import annotations


def normalize_email(email: str | None) -> str | None:
    if email is None:
        return None
    return email.strip().lower()


def normalize_phone(phone: str | None) -> str | None:
    if phone is None:
        return None
    digits = "".join(char for char in phone if char.isdigit())
    if len(digits) == 11 and digits[0] == "1":
        return digits[1:]
    return digits


SOURCE_PRIORITY = {"manual": 3, "import": 2, "enrichment": 1}


def dedupe_contacts(records: list[dict]) -> list[dict]:
    parent = {record["id"]: record["id"] for record in records}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]  # path compression
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        parent[find(a)] = find(b)

    first_owner: dict[str, str] = {}  # normalized key -> id of first record with it
    for record in records:
        keys = [normalize_email(record["email"]), normalize_phone(record["phone"])]
        for key in keys:
            if not key:  # None or "" matches nothing
                continue
            if key in first_owner:
                union(record["id"], first_owner[key])
            else:
                first_owner[key] = record["id"]

    groups: dict[str, list[dict]] = {}
    for record in records:
        root = find(record["id"])
        groups.setdefault(root, []).append(record)

    def best_value(group: list[dict], field: str):
        candidates = [r for r in group if r[field] is not None]
        if not candidates:
            return None
        winner = max(
            candidates,
            key=lambda r: (SOURCE_PRIORITY[r["source"]], r["updated_at"]),
        )
        return winner[field]

    merged = []
    for group in groups.values():
        merged.append({
            "ids": sorted(r["id"] for r in group),
            "email": normalize_email(best_value(group, "email")),
            "phone": normalize_phone(best_value(group, "phone")),
            "name": best_value(group, "name"),
            "title": best_value(group, "title"),
        })
        
    merged.sort(key=lambda g: g["ids"][0])
    return merged


if __name__ == "__main__":
    from lib import run_test_cases

    test_cases = [
        [
          (normalize_email, "  JANE@Acme.com ", "jane@acme.com"),
          (normalize_email, None, None),
          (normalize_phone, "(415) 555-0100", "4155550100"),
          (normalize_phone, "14155550100", "4155550100")
        ]
    ]

    run_test_cases(test_cases)