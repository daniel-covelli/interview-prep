# Grader for Monaco Problem 3 (monaco/p3_contact_dedup.py).
# SPOILER WARNING: this file enumerates edge cases and contains a full
# reference implementation. Run it, don't read it.
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from grader import (Suite, PerfConcern, Failure, load_fn, bench, fmt_s,
                    expect)

SEED = 0xDED0

_PRIORITY = {"manual": 2, "import": 1, "enrichment": 0}
_FIELDS = ("email", "phone", "name", "title")


def norm_email(e):
    return e.strip().lower() if e is not None else None


def norm_phone(p):
    if p is None:
        return None
    digits = re.sub(r"\D", "", p)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return digits


def oracle_dedupe(records):
    """Reference implementation: union-find on normalized keys, then
    per-field best-(priority, updated_at) merge."""
    parent = {r["id"]: r["id"] for r in records}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    owner = {}
    for r in records:
        for norm, field in ((norm_email, "email"), (norm_phone, "phone")):
            key = norm(r[field])
            if key is None or key == "":
                continue
            key = (field, key)
            if key in owner:
                union(r["id"], owner[key])
            else:
                owner[key] = r["id"]

    groups = {}
    for r in records:
        groups.setdefault(find(r["id"]), []).append(r)

    out = []
    for members in groups.values():
        rec = {"ids": sorted(m["id"] for m in members)}
        for field in _FIELDS:
            cands = [m for m in members if m[field] is not None]
            if not cands:
                rec[field] = None
                continue
            best = max(cands, key=lambda m: (_PRIORITY[m["source"]], m["updated_at"]))
            value = best[field]
            if field == "email":
                value = norm_email(value)
            elif field == "phone":
                value = norm_phone(value)
            rec[field] = value
        out.append(rec)
    out.sort(key=lambda rec: rec["ids"][0])
    return out


def strip_extras(result):
    """Project each output record onto the base-spec keys so extension 1
    (all_emails / all_phones) doesn't fail the base tests."""
    if not isinstance(result, list):
        return result
    keep = ("ids",) + _FIELDS
    return [{k: r[k] for k in keep if k in r} if isinstance(r, dict) else r
            for r in result]


def check_dedupe(dedupe, records, note=None, ctx=None):
    got = strip_extras(dedupe([dict(r) for r in records]))
    want = oracle_dedupe(records)
    if got != want:
        raise Failure(
            output=got,
            expected=want,
            note=(note or "") + (f"  [{ctx}]" if ctx else "") or None)


def rec(id, email=None, phone=None, name=None, title=None,
        source="import", updated_at=0):
    return {"id": id, "email": email, "phone": phone, "name": name,
            "title": title, "source": source, "updated_at": updated_at}


def main():
    suite = Suite("Monaco 3: dedupe_contacts")
    dedupe, err = load_fn("monaco.p3_contact_dedup", "dedupe_contacts")
    if dedupe is None:
        suite.skip_all(err)
        return suite.summary()
    ne, _ = load_fn("monaco.p3_contact_dedup", "normalize_email")
    np, _ = load_fn("monaco.p3_contact_dedup", "normalize_phone")

    suite.section("NORMALIZATION")

    def email_norm():
        if ne is None:
            raise NotImplementedError
        expect(ne("JANE@acme.com "), "jane@acme.com",
               note='normalize_email("JANE@acme.com ")')
        expect(ne("  Bob@X.IO"), "bob@x.io", note='normalize_email("  Bob@X.IO")')
        expect(ne(None), None, note="normalize_email(None)")
    suite.case("email: lowercase + strip whitespace, None passes through", email_norm)

    def phone_norm():
        if np is None:
            raise NotImplementedError
        for raw in ["(415) 555-0100", "415-555-0100", "4155550100",
                    "14155550100", "+1 415 555 0100", "1-415-555-0100"]:
            expect(np(raw), "4155550100", note=f"normalize_phone({raw!r})")
        expect(np("5550100"), "5550100",
               note="7 digits: nothing to strip, keep as-is")
        expect(np("19995550100"), "9995550100",
               note="11 digits starting with 1 -> drop the leading 1")
        expect(np("21234567890"), "21234567890",
               note="11 digits NOT starting with 1 -> keep all 11")
        expect(np(None), None, note="normalize_phone(None)")
    suite.case("phone: digits only, leading country-code 1 dropped", phone_norm)

    suite.section("CORRECTNESS")

    def docstring_example():
        r1 = rec("r1", email="jane@acme.com", name="Jane D.",
                 source="import", updated_at=100)
        r2 = rec("r2", email="JANE@acme.com ", phone="415-555-0100",
                 name="Jane Doe", title="VP Sales",
                 source="enrichment", updated_at=200)
        r3 = rec("r3", phone="(415) 555-0100", title="VP of Sales",
                 source="manual", updated_at=50)
        expect(strip_extras(dedupe([r1, r2, r3])), [{
            "ids": ["r1", "r2", "r3"],
            "email": "jane@acme.com",
            "phone": "4155550100",
            "name": "Jane D.",
            "title": "VP of Sales",
        }], note="the worked example from the file header")
    suite.case("spec example from the file header", docstring_example)

    def transitive_chain():
        # a~b share email1, b~c share phone, c~d share email2: one group of 4
        a = rec("a", email="x@x.com", updated_at=1)
        b = rec("b", email="X@X.COM", phone="415-555-0100", updated_at=2)
        c = rec("c", phone="4155550100", email=None, updated_at=3)
        c2 = dict(c, email="deep@chain.io")
        d = rec("d", email="DEEP@chain.io", updated_at=4)
        got = strip_extras(dedupe([a, b, c2, d]))
        expect([g["ids"] for g in got], [["a", "b", "c", "d"]],
               note="a~b (email), b~c (phone), c~d (second email): "
                    "transitivity must chain all four")
    suite.case("matching is transitive across different keys", transitive_chain)

    def none_never_matches():
        a = rec("a", email=None, phone="111-222-3333", name="Anon A")
        b = rec("b", email=None, phone="444-555-6666", name="Anon B")
        c = rec("c", email=None, phone=None, name="Anon A")
        d = rec("d", email=None, phone=None, name="Anon A")
        got = strip_extras(dedupe([a, b, c, d]))
        expect([g["ids"] for g in got], [["a"], ["b"], ["c"], ["d"]],
               note="None email/phone must never match another None — "
                    "identical names don't matter (names never match)")
    suite.case("None never matches None; names never match", none_never_matches)

    def field_independence():
        # each field's winner is a DIFFERENT record
        a = rec("a", email="p@x.com", name="Newest Name",
                source="import", updated_at=300)
        b = rec("b", email="P@x.com", title="Manual Title", name=None,
                source="manual", updated_at=10)
        c = rec("c", email="p@x.com", phone="415-555-0100", name="Enriched Name",
                source="enrichment", updated_at=999)
        expect(strip_extras(dedupe([a, b, c])), [{
            "ids": ["a", "b", "c"],
            "email": "p@x.com",
            "phone": "4155550100",      # only c has a phone
            "name": "Newest Name",       # import(300) beats enrichment(999); b has None
            "title": "Manual Title",     # manual wins even at updated_at=10
        }], note="every field is merged independently over records where "
                 "that field is non-None")
    suite.case("per-field merge picks winners independently", field_independence)

    def priority_and_ties():
        a = rec("a", email="t@x.com", name="Old Manual",
                source="manual", updated_at=1)
        b = rec("b", email="t@x.com", name="New Import",
                source="import", updated_at=999_999)
        got = strip_extras(dedupe([a, b]))
        expect(got[0]["name"], "Old Manual",
               note="source priority beats recency: manual(1) > import(999999)")
        c = rec("c", email="u@x.com", name="Manual Older",
                source="manual", updated_at=100)
        d = rec("d", email="u@x.com", name="Manual Newer",
                source="manual", updated_at=200)
        got = strip_extras(dedupe([c, d]))
        expect(got[0]["name"], "Manual Newer",
               note="within the same priority level, newer updated_at wins")
    suite.case("manual > import > enrichment; updated_at breaks ties", priority_and_ties)

    def output_shape():
        b = rec("b", email=" ZED@z.com", phone="+1 (999) 888-7777",
                source="manual", updated_at=5)
        a = rec("a", email="zed@Z.COM", source="import", updated_at=9)
        z = rec("z", email="solo@only.io", source="import", updated_at=1)
        got = strip_extras(dedupe([b, z, a]))
        expect(got, [
            {"ids": ["a", "b"], "email": "zed@z.com", "phone": "9998887777",
             "name": None, "title": None},
            {"ids": ["z"], "email": "solo@only.io", "phone": None,
             "name": None, "title": None},
        ], note="ids sorted inside each group; groups sorted by smallest id; "
                "email/phone in NORMALIZED form; all-None fields stay None")
    suite.case("output shape: sorted ids, sorted groups, normalized values", output_shape)

    def singletons_and_empty():
        expect(dedupe([]), [], note="no records -> no groups")
        r = rec("only", email="A@B.co", phone="1-222-333-4444",
                name="N", title="T", source="enrichment", updated_at=7)
        expect(strip_extras(dedupe([r])), [
            {"ids": ["only"], "email": "a@b.co", "phone": "2223334444",
             "name": "N", "title": "T"}
        ], note="a record matching nobody still comes out normalized")
    suite.case("empty input and singleton groups", singletons_and_empty)

    def randomized():
        rng = random.Random(SEED)
        emails = [f"user{i}@dom{i % 7}.com" for i in range(60)]
        phones = [f"{rng.randrange(200, 999)}555{i:04d}" for i in range(60)]

        def dress_email(e):
            e = e.upper() if rng.random() < 0.3 else e
            return e + " " if rng.random() < 0.2 else e

        def dress_phone(p):
            style = rng.randrange(4)
            if style == 0:
                return f"({p[:3]}) {p[3:6]}-{p[6:]}"
            if style == 1:
                return f"{p[:3]}-{p[3:6]}-{p[6:]}"
            if style == 2:
                return "1" + p
            return p

        records = []
        stamps = rng.sample(range(1_000_000), 400)   # unique -> no merge ties
        for i in range(400):
            records.append(rec(
                f"r{i:04d}",
                email=dress_email(rng.choice(emails)) if rng.random() < 0.7 else None,
                phone=dress_phone(rng.choice(phones)) if rng.random() < 0.6 else None,
                name=f"Name {rng.randrange(50)}" if rng.random() < 0.8 else None,
                title=f"Title {rng.randrange(20)}" if rng.random() < 0.5 else None,
                source=rng.choice(["manual", "import", "enrichment"]),
                updated_at=stamps[i]))
        check_dedupe(dedupe, records,
                     ctx=f"seed={SEED:#x}, 400 records — rerun a smaller slice "
                         f"by hand if this is hard to see")
    suite.case("randomized: 400 messy records cross-checked against oracle", randomized)

    if suite.failed or not suite.passed:
        suite.section("PERFORMANCE")
        reason = ("fix correctness failures first" if suite.failed
                  else "nothing implemented yet")
        suite.skip("all performance checks", reason)
        return suite.summary()

    suite.section("PERFORMANCE")

    def build_batch(n):
        rng = random.Random(SEED)
        records = []
        for i in range(n):
            # chains of 3: i%3==0 starts a person, the next two link via
            # shared email / shared phone
            person = i // 3
            role = i % 3
            email = f"p{person}@corp.com" if role in (0, 1) else None
            phone = f"415{person:07d}" if role in (1, 2) else None
            records.append(rec(f"r{i:07d}", email=email, phone=phone,
                               name=f"P {person}",
                               source=rng.choice(["manual", "import", "enrichment"]),
                               updated_at=i))
        rng.shuffle(records)
        return records

    def dedupe_scaling():
        small, big = build_batch(1_500), build_batch(6_000)
        t_small = bench(lambda: dedupe(small), repeat=2)
        t_big = bench(lambda: dedupe(big), repeat=2)
        ratio = t_big / max(t_small, 1e-9)
        suite.info(f"1.5k records: {fmt_s(t_small)}   6k records: {fmt_s(t_big)}   "
                   f"ratio {ratio:.1f}x (linear ≈ 4x)")
        assert ratio < 10, \
            (f"4x more records took {ratio:.1f}x longer — are you comparing "
             f"records pairwise (O(n²))? Target: one pass building a "
             f"normalized-key index, or union-find (≈ O(n)).")
    suite.case("dedupe cost stays ~linear in record count", dedupe_scaling)

    def note_scale_story():
        raise PerfConcern(
            "not machine-checkable: extensions 2 and 3 are discussion "
            "questions. Rehearse the nightly-batch answer (carry golden "
            "records forward, only re-cluster touched groups) and the "
            "50M-records answer (shard by normalized key; transitive chains "
            "that cross shards need a second union pass).")
    suite.case("batch-mode / 50M-record sharding story", note_scale_story)

    return suite.summary()


if __name__ == "__main__":
    sys.exit(1 if main().failed else 0)
