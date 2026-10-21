"""Publish Ada's work as static files for her website (livinglab/web/public/data/).

- dataset.json / dataset.csv: every trial and every extracted number, with its quote and status.
  Only VERIFIED (or auditor-CORRECTED) numbers count as part of the dataset; others are shown as pending.
- stats.json: counts, spend, benchmark and audit scores
- events.json: her recent real activity, replayed by the 3D lab on the website
- notes.json: approved lab notes (drafts are never published without approval)
"""

from __future__ import annotations

import csv
import json
import pathlib
import time

from . import db

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "web" / "public" / "data"
NOTES = ROOT / "data" / "notes"
MEASURE_LABEL = {
    "n_randomized": "Patients randomized", "orr": "Objective response rate", "dcr": "Disease control rate",
    "pfs_median": "Median PFS", "ttp_median": "Median time to progression", "os_median": "Median OS", "other_time_median": "Other median time",
    "pfs_hr": "PFS hazard ratio", "os_hr": "OS hazard ratio", "grade3plus_ae_rate": "Grade >=3 adverse events",
}


def _notes() -> list[dict]:
    out = []
    for p in sorted((NOTES / "published").glob("*.md"), reverse=True):
        text = p.read_text()
        meta, body = {}, text
        if text.startswith("---"):
            _, fm, body = text.split("---", 2)
            for line in fm.strip().splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip()
        out.append({"slug": p.stem, "title": meta.get("title", p.stem), "date": meta.get("date", ""),
                    "author": meta.get("author", "Ada"), "summary": meta.get("summary", ""), "body": body.strip()})
    return out


def export(con=None, out: pathlib.Path = OUT) -> dict:
    con = con or db.connect()
    out.mkdir(parents=True, exist_ok=True)
    trials = []
    # Only papers whose latest screening says "randomized trial in metastatic CRC" are published.
    # (Benchmark extractions of other papers stay private until screening includes them.)
    for t in con.execute("SELECT t.*, p.title, p.journal, p.year, p.authors, p.doi, p.nct_ids FROM trials t "
                         "JOIN papers p ON p.pmid = t.pmid "
                         "JOIN screenings s ON s.pmid = t.pmid AND s.id = (SELECT MAX(id) FROM screenings WHERE pmid = t.pmid) "
                         "WHERE s.decision = 'include' ORDER BY p.year DESC, t.pmid"):
        recs = []
        for r in con.execute("SELECT * FROM records WHERE pmid=? ORDER BY arm, measure", (t["pmid"],)):
            ch = json.loads(r["checks"] or "{}")
            recs.append({"id": r["id"], "arm": r["arm"], "measure": r["measure"], "label": MEASURE_LABEL[r["measure"]],
                         "value": r["value"], "unit": r["unit"], "ci_low": r["ci_low"], "ci_high": r["ci_high"],
                         "comparator": r["comparator"], "population": ch.get("population"),
                         "detail": ch.get("detail"), "quote": r["quote"], "status": r["status"],
                         "failed_checks": [] if r["status"] == "corrected" else [k for k, v in ch.items() if v is False],
                         "audit_note": (ch.get("audit") or {}).get("note")})
        trials.append({"pmid": t["pmid"], "title": t["title"], "journal": t["journal"], "year": t["year"],
                       "authors": t["authors"], "doi": t["doi"], "nct_ids": json.loads(t["nct_ids"] or "[]"),
                       "acronym": t["acronym"], "phase": t["phase"], "line": t["line"], "biomarker": t["biomarker"],
                       "n_randomized": t["n_randomized"], "primary_endpoint": t["primary_endpoint"],
                       "arms": json.loads(t["arms"] or "[]"), "records": recs})
    good = ("verified", "corrected")
    counts = {
        "candidates": con.execute("SELECT COUNT(*) FROM papers").fetchone()[0],
        "screened": con.execute("SELECT COUNT(DISTINCT pmid) FROM screenings").fetchone()[0],
        "included": con.execute("SELECT COUNT(*) FROM screenings WHERE id IN (SELECT MAX(id) FROM screenings GROUP BY pmid) "
                                "AND decision='include'").fetchone()[0],
        "trials": len(trials),
        "verified_numbers": sum(1 for t in trials for r in t["records"] if r["status"] in good),
        "pending_numbers": sum(1 for t in trials for r in t["records"] if r["status"] == "needs_review"),
        "corrected_numbers": sum(1 for t in trials for r in t["records"] if r["status"] == "corrected"),
    }
    version = time.strftime("%Y-%m-%d")
    (out / "dataset.json").write_text(json.dumps({"name": "Open Metastatic Colorectal Cancer Trial Outcomes",
                                                  "version": version, "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
                                                  "counts": counts, "trials": trials}, indent=1))
    with open(out / "dataset.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pmid", "trial", "year", "line", "biomarker_selection", "arm", "comparator", "population",
                    "measure", "value", "unit", "ci_low", "ci_high", "detail", "status", "source_quote"])
        for t in trials:
            for r in t["records"]:
                if r["status"] in good:
                    w.writerow([t["pmid"], t["acronym"] or "", t["year"], t["line"], t["biomarker"] or "", r["arm"],
                                r["comparator"] or "", r["population"] or "", r["measure"], r["value"], r["unit"],
                                r["ci_low"], r["ci_high"], r["detail"] or "", r["status"], r["quote"]])
    extras = {}
    for name in ("benchmark.json", "audit_scoreboard.json"):
        p = ROOT / "data" / name
        if p.exists():
            extras[name.removesuffix(".json")] = json.loads(p.read_text())
    stats = {"version": version, "updated": time.strftime("%Y-%m-%d %H:%M"), "counts": counts,
             "spend_usd_total": round(db.spent(con), 4), "spend_usd_today": round(db.spent(con, version), 4),
             **extras}
    (out / "stats.json").write_text(json.dumps(stats, indent=1))
    ev = [{"at": r["at"], **json.loads(r["event"])} for r in
          con.execute("SELECT * FROM (SELECT * FROM events ORDER BY id DESC LIMIT 400) ORDER BY id")]
    (out / "events.json").write_text(json.dumps(ev))
    (out / "notes.json").write_text(json.dumps(_notes(), indent=1))
    return counts
