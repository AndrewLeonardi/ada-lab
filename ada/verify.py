"""Stage 3, verification by code (free): can every number be traced to the source, exactly?

A record is VERIFIED only if:
  1. its quote occurs verbatim in the abstract (after normalizing whitespace, dashes and decimal points);
  2. its value (and confidence limits, if any) literally appear in that quote;
  3. the value is plausible for its measure, in a unit that fits it, exact (not "<0.5%"), and 95% confidence limits
     (not 80% or 90%) bracket it; a randomized count comes from a sentence about randomization; a disease control
     rate is named as one;
  4. a standard PFS/OS/TTP number is not about a non-standard endpoint (by its quote or its own detail);
  5. the independent second extraction pass recorded the same measure with the same value;
  6. it does not contradict the trial's other numbers (consistency.py).
Anything else is NEEDS_REVIEW (for the auditor) and is not published as verified.
"""

from __future__ import annotations

import json
import re
import time
import unicodedata

PLAUSIBLE = {
    "n_randomized": (2, 10000), "orr": (0, 100), "dcr": (0, 100), "pfs_median": (0.1, 200), "ttp_median": (0.1, 200),
    "os_median": (0.1, 300), "other_time_median": (0.1, 300), "pfs_hr": (0.05, 10), "os_hr": (0.05, 10), "grade3plus_ae_rate": (0, 100),
}


UNITS = {"n_randomized": {"count"}, "orr": {"percent"}, "dcr": {"percent"}, "grade3plus_ae_rate": {"percent"},
         "pfs_median": {"months", "weeks"}, "ttp_median": {"months", "weeks"}, "os_median": {"months", "weeks"},
         "other_time_median": {"months", "weeks"}, "pfs_hr": {"ratio"}, "os_hr": {"ratio"}}

# Phrases that mean a quote (or the record's own "detail") is about a non-standard time endpoint
# (found in audit 1: "second PFS" was recorded as ordinary PFS by both passes).
NONSTANDARD_TIME = re.compile(r"second[- ]line pfs|second progression|pfs ?2|pfsot|on[- ]treatment|time to (treatment|strategy) "
                              r"failure|failure[- ]free|duration of disease control|time to failure")


# Found in audit 2: "patients randomized" filled with counts of patients treated, evaluable or analysed; a
# stable-disease rate filed as disease control; an 80% interval recorded as a 95% one; "<0.5%" recorded as 0.5.
RANDOMIZED = re.compile(r"random|allocat|assign|intention[- ]to[- ]treat|intent[- ]to[- ]treat|\bitt\b|enrol")
NOT_RANDOMIZED = re.compile(r"assess|evaluab|analy[sz]ed|received|treated|included in the (safety|per)|per[- ]protocol|"
                            r"safety population|full analysis")
TIME_UNIT = {"months": re.compile(r"month|\bmo\b|\bmos\b"), "weeks": re.compile(r"week|\bwk")}
DISEASE_CONTROL = re.compile(r"disease control|\bdcr\b")
NOT_95 = re.compile(r"(?<![\d.])(50|80|90|99)\s?% ?(ci|confidence)")


def sentence(abstract: str, quote: str) -> str:
    """The sentence of the (normalized) abstract that contains the quote, or the quote itself if not found."""
    a, q = norm(abstract), norm(quote)
    i = a.find(q)
    if i < 0:
        return q
    end = a.find(". ", i + len(q))
    return a[max(a.rfind(". ", 0, i), 0): len(a) if end < 0 else end]


def randomized_count(abstract: str, quote: str) -> bool:
    """A per-arm count is a randomized count only if its sentence ties it to randomization: "Of 133 randomized
    patients, 128 were assessed for efficacy (82 and 46)" is not (the counts are of patients assessed)."""
    s, q = sentence(abstract, quote), norm(quote)
    if RANDOMIZED.search(q) and not NOT_RANDOMIZED.search(q):
        return True
    i = s.find(q)
    i = len(s) if i < 0 else i
    before = list(RANDOMIZED.finditer(s[:i]))
    if not before:  # "the experimental group (n = 60) was randomly assigned to ..."
        return bool(RANDOMIZED.search(s[i:])) and not NOT_RANDOMIZED.search(q)
    return not NOT_RANDOMIZED.search(s[before[-1].end():i] + q)


def exact_in(text: str, x: float) -> bool:
    """False if the number appears only as a bound ("<0.5%", "≥3")."""
    t = norm(text)
    hits = [m for m in re.finditer(r"(?<![\d.])\d[\d,]*(?:\.\d+)?", t) if abs(float(m.group().replace(",", "")) - x) < 1e-9]
    return not hits or any(not re.search(r"[<>≤≥]\s*$", t[:m.start()]) for m in hits)


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "")
    s = s.replace("·", ".").replace("−", "-").replace("–", "-").replace("—", "-").replace(" ", " ")
    return re.sub(r"\s+", " ", s).strip().lower()


def number_in(text: str, x: float) -> bool:
    """Does the number x appear in text, as written (any common formatting)?"""
    t = norm(text)
    nums = [float(n.replace(",", "")) for n in re.findall(r"(?<![\d.])\d[\d,]*(?:\.\d+)?", t)]
    return any(abs(n - x) < 1e-9 for n in nums)


def check_record(o: dict, abstract: str, other_pass: list[dict] | None) -> dict:
    a = norm(abstract)
    q = norm(o["quote"])
    checks = {
        "quote_found": bool(q) and q in a,
        "value_in_quote": number_in(o["quote"], o["value"]),
        "ci_in_quote": all(number_in(o["quote"], v) for v in (o.get("ci_low"), o.get("ci_high")) if v is not None),
        "plausible": PLAUSIBLE[o["measure"]][0] <= o["value"] <= PLAUSIBLE[o["measure"]][1],
        "unit_fits": o["unit"] in UNITS[o["measure"]],  # e.g. a "median PFS" in percent is a misfiled rate
        "randomized_count": o["measure"] != "n_randomized" or randomized_count(abstract, o["quote"]),
        "dcr_named": o["measure"] != "dcr" or bool(DISEASE_CONTROL.search(q)),
        "ci_is_95": o.get("ci_low") is None or not NOT_95.search(q),
        "exact_value": exact_in(o["quote"], o["value"]),
        # a median's unit must be the one its sentence uses ("200 and 502 d" was recorded as weeks, audit 2)
        "unit_in_source": o["unit"] not in TIME_UNIT or bool(TIME_UNIT[o["unit"]].search(sentence(abstract, o["quote"]))),
        "ci_brackets_value": (o.get("ci_low") is None or o.get("ci_high") is None
                              or o["ci_low"] <= o["value"] <= o["ci_high"]),
        "standard_endpoint": not (o["measure"] in ("pfs_median", "os_median", "ttp_median")
                                  and NONSTANDARD_TIME.search(q + " " + norm(o.get("detail")))),
    }
    if other_pass is not None:
        checks["second_pass_agrees"] = any(
            x["measure"] == o["measure"] and abs(x["value"] - o["value"]) < 1e-9 and x.get("population") == o.get("population")
            for x in other_pass)
    return checks


def record_id(pmid: str, o: dict) -> str:
    key = f"{o['arm']}|{o['measure']}|{o.get('population')}|{o.get('detail') or ''}|{o.get('comparator') or ''}"
    return f"{pmid}:{re.sub(r'[^a-z0-9|+]+', '-', key.lower())[:120]}"


def verify_paper(con, p: dict, pass1: dict, pass2: dict | None) -> dict:
    """Write records (and the trial row) for one paper; return counts by status."""
    counts = {"verified": 0, "needs_review": 0}
    other = pass2["outcomes"] if pass2 else None
    now = time.time()
    for o in pass1["outcomes"]:
        c = check_record(o, p["abstract"], other)
        status = "verified" if all(c.values()) else "needs_review"
        counts[status] += 1
        rid = record_id(p["pmid"], o)
        # an auditor's verdict (confirmed, corrected or rejected) wins over a re-extraction or re-check
        prev = con.execute("SELECT status, checks FROM records WHERE id=?", (rid,)).fetchone()
        if prev and (prev["status"] in ("corrected", "rejected") or "audit" in json.loads(prev["checks"] or "{}")):
            continue
        con.execute(
            "INSERT OR REPLACE INTO records(id, pmid, arm, measure, value, ci_low, ci_high, unit, quote, status, "
            "checks, comparator, updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (rid, p["pmid"], o["arm"], o["measure"], o["value"], o.get("ci_low"), o.get("ci_high"), o["unit"],
             o["quote"], status, json.dumps({**c, "population": o.get("population"), "detail": o.get("detail")}),
             o.get("comparator"), now))
    t = pass1["trial"]
    con.execute(
        "INSERT OR REPLACE INTO trials(pmid, acronym, phase, line, setting, biomarker, n_randomized, primary_endpoint, "
        "registry_ids, arms, status, updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
        (p["pmid"], t.get("acronym"), t.get("phase"), t.get("line"), None, t.get("biomarker_selection"),
         t.get("n_randomized_total"), t.get("primary_endpoint"), json.dumps(p.get("nct_ids") or []),
         json.dumps(pass1["arms"]), "extracted", now))
    con.commit()
    # numbers that pass on their own can still contradict each other: re-count after the consistency checks
    from .consistency import check_trial
    check_trial(con, p["pmid"])
    counts = {"verified": 0, "needs_review": 0}
    for status, n in con.execute("SELECT status, COUNT(*) FROM records WHERE pmid=? GROUP BY status", (p["pmid"],)):
        if status in counts:
            counts[status] = n
    return counts
