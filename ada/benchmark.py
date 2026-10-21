"""How accurate is Ada? Compare her extractions with trial results verified by hand.

The gold standard is livinglab/research/gold_trials.yaml (a copy of research/params_drugs_trials.yaml): arm-level results of real mCRC trials,
each checked against the publication by a research agent. Only gold numbers that actually appear
in the PubMed abstract count (Ada reads abstracts).
"""

from __future__ import annotations

import json
import pathlib
import time

import yaml

from . import db, sources
from .verify import number_in

LAB = pathlib.Path(__file__).resolve().parents[1]  # livinglab/
GOLD_FIELDS = {"response_rate_pct": ("orr", "percent"), "median_pfs_months": ("pfs_median", "months"),
               "median_os_months": ("os_median", "months"), "median_pfs_weeks": ("pfs_median", "weeks"),
               "n": ("n_randomized", "count")}


def gold_items() -> list[dict]:
    entries = yaml.safe_load((LAB / "research" / "gold_trials.yaml").read_text())
    items = []
    for e in entries:
        if e.get("kind") != "trial":
            continue
        pmid = str((e.get("source") or {}).get("pmid") or "")
        if not pmid.isdigit():
            continue
        for arm in e.get("arms") or []:
            for field, (measure, unit) in GOLD_FIELDS.items():
                v = arm.get(field)
                if isinstance(v, (int, float)):
                    items.append({"pmid": pmid, "trial": e["id"], "arm": arm.get("name"), "measure": measure,
                                  "unit": unit, "value": float(v)})
    return items


def run_benchmark(con, extract_fn) -> dict:
    """``extract_fn(pmid)`` must extract (and verify) one paper into the database."""
    items = gold_items()
    pmids = sorted({i["pmid"] for i in items})
    papers = {p["pmid"]: p for p in sources.fetch(pmids)}
    for p in papers.values():
        con.execute("INSERT OR IGNORE INTO papers(pmid, title, journal, year, authors, doi, abstract, pub_types, "
                    "nct_ids, found_by, fetched_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    (p["pmid"], p["title"], p["journal"], p["year"], p["authors"], p["doi"], p["abstract"],
                     json.dumps(p["pub_types"]), json.dumps(p["nct_ids"]), "benchmark", time.time()))
    con.commit()
    for pmid in pmids:
        if not con.execute("SELECT 1 FROM extractions WHERE pmid=?", (pmid,)).fetchone():
            extract_fn(pmid)
    rows = []
    for it in items:
        abstract = (papers.get(it["pmid"]) or {}).get("abstract", "")
        in_abstract = number_in(abstract, it["value"])
        recs = con.execute("SELECT status, value, unit FROM records WHERE pmid=? AND measure=?",
                           (it["pmid"], it["measure"])).fetchall()
        hit = [r for r in recs if abs(r["value"] - it["value"]) < 0.051 and r["unit"] == it["unit"]]
        rows.append({**it, "in_abstract": in_abstract,
                     "found_verified": any(r["status"] in ("verified", "corrected") for r in hit),
                     "found_any": bool(hit)})
    scorable = [r for r in rows if r["in_abstract"]]
    res = {
        "date": time.strftime("%Y-%m-%d"),
        "gold_numbers": len(rows),
        "gold_numbers_in_abstracts": len(scorable),
        "recall_verified": round(sum(r["found_verified"] for r in scorable) / max(1, len(scorable)), 3),
        "recall_any": round(sum(r["found_any"] for r in scorable) / max(1, len(scorable)), 3),
        "missed": [r for r in scorable if not r["found_any"]][:40],
    }
    (LAB / "data" / "benchmark.json").write_text(json.dumps(res, indent=1))
    return res
