"""Daily recaps for the website: what Ada did each day (UTC), computed from her records by code.

No AI writes these and nothing is inferred: counts, the trials she added with their headline verified numbers,
why numbers were held for review, auditor corrections and what she spent.
"""

from __future__ import annotations

import json
from collections import Counter

HEADLINE = ["os_hr", "pfs_hr", "os_median", "pfs_median", "orr"]  # the first one a trial has verified
HELD_BECAUSE = {
    "second_pass_agrees": "the two independent extractions disagreed",
    "quote_found": "the quote was not found word for word",
    "value_in_quote": "the number was not in its quote",
    "ci_in_quote": "the confidence limits were not in the quote",
    "plausible": "the value was implausible",
    "ci_brackets_value": "the interval did not contain the value",
    "standard_endpoint": "it described a non-standard endpoint",
}


def _name(con, pmid: str) -> str:
    t = con.execute("SELECT acronym FROM trials WHERE pmid=?", (pmid,)).fetchone()
    if t and t[0]:
        return t[0]
    s = con.execute("SELECT detail FROM screenings WHERE pmid=? ORDER BY id DESC LIMIT 1", (pmid,)).fetchone()
    if s and s[0] and json.loads(s[0]).get("trial_name"):
        return json.loads(s[0])["trial_name"]
    p = con.execute("SELECT title FROM papers WHERE pmid=?", (pmid,)).fetchone()
    title = p[0] if p and p[0] else f"PMID {pmid}"
    return title if len(title) <= 90 else title[:87] + "…"


def _headline(con, pmid: str) -> dict | None:
    from .export import MEASURE_LABEL
    recs = con.execute("SELECT * FROM records WHERE pmid=? AND status IN ('verified','corrected') ORDER BY arm",
                       (pmid,)).fetchall()
    for m in HEADLINE:
        rs = [r for r in recs if r["measure"] == m]
        overall = [r for r in rs if json.loads(r["checks"] or "{}").get("population") in (None, "overall")]
        rs = overall or rs
        if rs:
            return {"label": MEASURE_LABEL[m], "items": [
                {"arm": r["arm"], "comparator": r["comparator"], "value": r["value"], "unit": r["unit"],
                 "ci_low": r["ci_low"], "ci_high": r["ci_high"],
                 "population": json.loads(r["checks"] or "{}").get("population")} for r in rs[:3]]}
    return None


def daily(con, days: int = 30) -> list[dict]:
    final = {r[0]: r[1] for r in con.execute(
        "SELECT pmid, decision FROM screenings WHERE id IN (SELECT MAX(id) FROM screenings GROUP BY pmid)")}
    dates = sorted({r[0] for r in con.execute(
        "SELECT date(at, 'unixepoch') FROM screenings UNION SELECT date(at, 'unixepoch') FROM extractions "
        "UNION SELECT date(at, 'unixepoch') FROM corrections") if r[0]}, reverse=True)  # days she did work
    out = []
    for d in dates[:days]:
        that_day = {}
        for pmid, dec in con.execute("SELECT pmid, decision FROM screenings WHERE date(at, 'unixepoch')=? ORDER BY id",
                                     (d,)):
            that_day[pmid] = dec
        decisions = Counter(that_day.values())
        extracted, held = [], Counter()
        for (pmid,) in con.execute("SELECT pmid FROM extractions WHERE pass=1 GROUP BY pmid "
                                   "HAVING date(MIN(at), 'unixepoch')=? ORDER BY MIN(at)", (d,)).fetchall():
            if final.get(pmid) != "include":  # test-set or screened-out papers are not part of the dataset
                continue
            recs = con.execute("SELECT status, checks FROM records WHERE pmid=?", (pmid,)).fetchall()
            for status, checks in recs:
                if status == "needs_review":
                    held.update(k for k, v in json.loads(checks or "{}").items() if v is False and k in HELD_BECAUSE)
            extracted.append({"pmid": pmid, "name": _name(con, pmid),
                              "verified": sum(r[0] in ("verified", "corrected") for r in recs),
                              "review": sum(r[0] == "needs_review" for r in recs), "headline": _headline(con, pmid)})
        out.append({
            "date": d,
            "spend_usd": round(con.execute("SELECT COALESCE(SUM(usd), 0) FROM spend WHERE day=?", (d,)).fetchone()[0], 4),
            "screened": len(that_day),
            "included": decisions["include"], "secondary": decisions["secondary"], "excluded": decisions["exclude"],
            "extracted": extracted,
            "verified_numbers": sum(t["verified"] for t in extracted),
            "review_numbers": sum(t["review"] for t in extracted),
            "held_because": [{"reason": HELD_BECAUSE[k], "n": n} for k, n in held.most_common()],
            "corrections": con.execute("SELECT COUNT(DISTINCT record_id) FROM corrections WHERE date(at, 'unixepoch')=?",
                                       (d,)).fetchone()[0],
        })
    return out
