"""Free consistency checks: numbers from the same trial that cannot all be right.

Each check passed by every single number can still fail across numbers. When a paper reports
    - a hazard ratio and both arms' medians, they must point the same way;
    - median PFS and median OS for an arm, PFS cannot be longer (every progression-free time ends
      at or before death);
    - a response rate and a disease control rate for an arm, control includes response, so it is at least as large;
    - patients per arm, they cannot add up to more than the trial randomized;
    - a hazard ratio with its confidence interval, the ratio sits near the middle of the interval on a log scale.
A contradiction means one number is wrong, here or in the paper: the numbers involved go to the auditor.
"""

from __future__ import annotations

import json
import math
import time

HR_PAIRS = (("os_hr", "os_median"), ("pfs_hr", "pfs_median"))


def _pop(r: dict) -> str:
    return r["checks"].get("population") or "overall"


def find(records: list[dict], trial_total: int | None = None) -> list[dict]:
    """records: dicts with id, arm, measure, value, unit, ci_low, ci_high, comparator, checks (dict).
    Returns flags: {"check", "records": [ids], "note"}."""
    flags = []
    by = {}
    for r in records:
        by.setdefault((r["measure"], r["arm"], _pop(r)), []).append(r)

    def one(measure, arm, pop):
        rs = by.get((measure, arm, pop), [])
        return rs[0] if len(rs) == 1 else None  # ambiguous (several values) -> no check

    for hr_m, med_m in HR_PAIRS:
        for (m, arm, pop), rs in by.items():
            if m != hr_m:
                continue
            for h in rs:
                a, c = one(med_m, arm, pop), one(med_m, h["comparator"], pop) if h["comparator"] else None
                if not (a and c) or a["unit"] != c["unit"]:
                    continue
                if (h["value"] < 0.85 and a["value"] < c["value"]) or (h["value"] > 1.15 and a["value"] > c["value"]):
                    word = "better" if h["value"] < 1 else "worse"
                    flags.append({"check": "hr_direction", "records": [h["id"], a["id"], c["id"]],
                                  "note": f"{hr_m.split('_')[0].upper()} hazard ratio {h['value']:g} says {arm} did {word} "
                                          f"than {h['comparator']}, but the medians say the opposite "
                                          f"({a['value']:g} vs {c['value']:g} {a['unit']})."})
    for (m, arm, pop), rs in by.items():
        if m == "pfs_median":
            p, o = one("pfs_median", arm, pop), one("os_median", arm, pop)
            if p and o and p["unit"] == o["unit"] and p["value"] > o["value"] + 0.05:
                flags.append({"check": "pfs_exceeds_os", "records": [p["id"], o["id"]],
                              "note": f"Median PFS ({p['value']:g}) is longer than median OS ({o['value']:g}) for {arm}."})
        if m == "orr":
            r_, d = one("orr", arm, pop), one("dcr", arm, pop)
            if r_ and d and r_["value"] > d["value"] + 0.05:
                flags.append({"check": "orr_exceeds_dcr", "records": [r_["id"], d["id"]],
                              "note": f"Response rate ({r_['value']:g}%) is higher than disease control rate "
                                      f"({d['value']:g}%) for {arm}."})
        if m in ("os_hr", "pfs_hr"):
            for h in rs:
                lo, hi, v = h["ci_low"], h["ci_high"], h["value"]
                if lo and hi and v and lo > 0 and hi > lo and math.log(hi / lo) >= 0.15:
                    pos = math.log(v / lo) / math.log(hi / lo)
                    if not 0.3 <= pos <= 0.7:
                        flags.append({"check": "hr_ci_off_center", "records": [h["id"]],
                                      "note": f"Hazard ratio {v:g} is not near the middle of its interval {lo:g}-{hi:g} "
                                              "(on a log scale, where it normally sits)."})
    arms_n = [r for (m, _, pop), rs in by.items() if m == "n_randomized" and pop == "overall" for r in rs]
    if trial_total and arms_n and sum(r["value"] for r in arms_n) > trial_total * 1.01 + 1:
        flags.append({"check": "arms_exceed_total", "records": [r["id"] for r in arms_n],
                      "note": f"Patients per arm add up to {sum(r['value'] for r in arms_n):g}, more than the "
                              f"{trial_total} randomized."})
    return flags


def check_trial(con, pmid: str) -> list[dict]:
    """Re-run the checks for one trial: refresh its flags and the verified status of its numbers."""
    rows = [dict(r) for r in con.execute("SELECT * FROM records WHERE pmid=? AND status != 'rejected'", (pmid,))]
    for r in rows:
        r["checks"] = json.loads(r["checks"] or "{}")
        r["checks"].pop("consistent", None)
        r["checks"].pop("consistency_note", None)
    t = con.execute("SELECT n_randomized FROM trials WHERE pmid=?", (pmid,)).fetchone()
    flags = find(rows, t[0] if t else None)
    flagged = {}
    for f in flags:
        for rid in f["records"]:
            flagged.setdefault(rid, []).append(f["note"])
    con.execute("DELETE FROM consistency_flags WHERE pmid=?", (pmid,))
    for f in flags:
        con.execute("INSERT INTO consistency_flags(pmid, check_name, record_ids, note, found_at) VALUES(?,?,?,?,?)",
                    (pmid, f["check"], json.dumps(f["records"]), f["note"], time.time()))
    for r in rows:
        ch = r["checks"]
        if r["id"] in flagged:
            ch["consistent"] = False
            ch["consistency_note"] = " ".join(flagged[r["id"]])
        status = r["status"]
        if "audit" not in ch and status in ("verified", "needs_review"):  # auditor verdicts are never overridden
            status = "verified" if all(v for v in ch.values() if isinstance(v, bool)) else "needs_review"
        con.execute("UPDATE records SET status=?, checks=? WHERE id=?", (status, json.dumps(ch), r["id"]))
    con.commit()
    return flags
