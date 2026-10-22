"""Human validation (dataset protocol section 10): a person re-extracts a random sample of published numbers, blind.

    ada validation-sample --name pilot --n 30      draw a fixed-seed sample (data/validation/<name>.json)
    ada validation-report <answers.json>          compare a validator's answers with Ada's numbers

The sample holds what to look for (trial, arm, measure, population) but not Ada's values; the website's Validate
page shows her value only after the person's answer is saved, and lets them download their answers.
Agreement is reported with a Wilson 95% interval; every disagreement is then judged by reading the source.
"""

from __future__ import annotations

import json
import random
import time

from . import db
from .export import MEASURE_LABEL
from .stats import wilson

DIR = db.DATA_DIR / "validation"


def draw(con, name: str, n: int, seed: str | None = None) -> dict:
    DIR.mkdir(parents=True, exist_ok=True)
    path = DIR / f"{name}.json"
    if path.exists():
        raise SystemExit(f"{path} exists: a drawn sample is never redrawn (choose another name)")
    rows = [dict(r) for r in con.execute(
        "SELECT r.*, t.acronym, p.title FROM records r JOIN papers p ON p.pmid = r.pmid LEFT JOIN trials t ON "
        "t.pmid = r.pmid JOIN screenings s ON s.pmid = r.pmid AND s.id = (SELECT MAX(id) FROM screenings WHERE "
        "pmid = r.pmid) WHERE s.decision = 'include' AND r.status IN ('verified', 'corrected') ORDER BY r.id")]
    picked = random.Random(seed or f"validation-{name}").sample(rows, min(n, len(rows)))
    items = []
    for r in picked:
        ch = json.loads(r["checks"] or "{}")
        items.append({"id": r["id"], "pmid": r["pmid"], "trial": r["acronym"] or None, "title": r["title"],
                      "arm": r["arm"], "comparator": r["comparator"], "measure": r["measure"],
                      "label": MEASURE_LABEL[r["measure"]], "population": ch.get("population") or "overall",
                      "detail": ch.get("detail"), "unit": r["unit"]})
    sample = {"name": name, "seed": seed or f"validation-{name}", "drawn": time.strftime("%Y-%m-%d"),
              "pool": len(rows), "items": items}
    path.write_text(json.dumps(sample, indent=1))
    return sample


def report(con, answers: dict) -> dict:
    """answers: {"sample": name, "validator": ..., "answers": {record_id: {"value": float|None, "not_stated": bool}}}"""
    sample = json.loads((DIR / f"{answers['sample']}.json").read_text())
    agree, rows = 0, []
    for it in sample["items"]:
        a = answers["answers"].get(it["id"])
        if a is None:
            continue
        r = con.execute("SELECT value, unit, quote FROM records WHERE id=?", (it["id"],)).fetchone()
        same = (not a.get("not_stated")) and a.get("value") is not None and abs(float(a["value"]) - r["value"]) < 1e-6
        agree += same
        if not same:
            rows.append({"id": it["id"], "pmid": it["pmid"], "measure": it["measure"], "arm": it["arm"],
                         "ada": r["value"], "validator": None if a.get("not_stated") else a.get("value"),
                         "note": a.get("note"), "quote": r["quote"]})
    n = sum(1 for it in sample["items"] if it["id"] in answers["answers"])
    p, lo, hi = wilson(agree, n)
    out = {"sample": sample["name"], "validator": answers.get("validator"), "answered": n, "of": len(sample["items"]),
           "agree": agree, "agreement": [p, lo, hi], "disagreements": rows, "reported": time.strftime("%Y-%m-%d")}
    (DIR / f"{sample['name']}-results.json").write_text(json.dumps(out, indent=1))
    return out


def summary() -> list[dict]:
    """Samples and any results, for the website (no values)."""
    out = []
    for p in sorted(DIR.glob("*.json")) if DIR.exists() else []:
        if p.name.endswith("-results.json"):
            continue
        s = json.loads(p.read_text())
        res = DIR / f"{s['name']}-results.json"
        out.append({**s, "results": json.loads(res.read_text()) if res.exists() else None})
    return out
