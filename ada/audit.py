"""Audits: an independent reviewer (Claude Opus in Claude Code) re-checks Ada's numbers.

    ada audit-sample --n 20      -> livinglab/data/audits/<date>-sample.json (records + their abstracts)
    (the auditor writes livinglab/data/audits/<date>.yaml with a verdict per record)
    ada apply-audit <date>.yaml  -> applies corrections, logs them, updates the public scoreboard

Accuracy is computed only on numbers that were already published as verified, so the
scoreboard measures the quality of what the public sees.
"""

from __future__ import annotations

import json
import pathlib
import random
import time

import yaml

from . import db

AUDIT_DIR = db.DATA_DIR / "audits"
SCOREBOARD = db.DATA_DIR / "audit_scoreboard.json"


def sample(con, n_verified: int = 20, n_review: int = 30, seed: str | None = None) -> pathlib.Path:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    day = time.strftime("%Y-%m-%d")
    rng = random.Random(seed or day)
    ver = [dict(r) for r in con.execute("SELECT * FROM records WHERE status='verified'")]
    rev = [dict(r) for r in con.execute("SELECT * FROM records WHERE status='needs_review'")]
    picked = rng.sample(ver, min(n_verified, len(ver))) + rev[:n_review]
    items = []
    for r in picked:
        p = con.execute("SELECT title, journal, year, abstract FROM papers WHERE pmid=?", (r["pmid"],)).fetchone()
        ch = json.loads(r["checks"] or "{}")
        items.append({"id": r["id"], "pre_status": r["status"], "pmid": r["pmid"], "arm": r["arm"],
                      "measure": r["measure"], "value": r["value"], "unit": r["unit"], "ci_low": r["ci_low"],
                      "ci_high": r["ci_high"], "comparator": r["comparator"], "population": ch.get("population"),
                      "detail": ch.get("detail"), "quote": r["quote"],
                      "failed_checks": [k for k, v in ch.items() if v is False],
                      "paper": {"title": p["title"], "journal": p["journal"], "year": p["year"],
                                "url": f"https://pubmed.ncbi.nlm.nih.gov/{r['pmid']}/", "abstract": p["abstract"]}})
    out = AUDIT_DIR / f"{day}-sample.json"
    out.write_text(json.dumps({"date": day, "n_verified_sampled": min(n_verified, len(ver)),
                               "n_review_items": min(n_review, len(rev)), "items": items}, indent=1))
    return out


def apply(con, path: pathlib.Path) -> dict:
    audit = yaml.safe_load(path.read_text())
    day = str(audit.get("date") or time.strftime("%Y-%m-%d"))
    who = audit.get("auditor", "auditor")
    stats = {"sampled": 0, "correct": 0, "review_confirmed": 0, "review_corrected": 0, "review_rejected": 0,
             "unclear": 0}
    for it in audit.get("items", []):
        row = con.execute("SELECT * FROM records WHERE id=?", (it["id"],)).fetchone()
        if not row:
            continue
        pre = it.get("pre_status", row["status"])
        verdict = it["verdict"]
        if pre == "verified":
            stats["sampled"] += 1
            stats["correct"] += verdict == "correct"
        if verdict == "unclear":
            stats["unclear"] += 1
            continue
        checks = json.loads(row["checks"] or "{}")
        checks["audit"] = {"date": day, "verdict": verdict, "note": it.get("note", "")}
        if verdict == "correct":
            status = "verified"
            stats["review_confirmed"] += pre != "verified"
        elif it.get("corrected"):
            status = "corrected"
            stats["review_corrected"] += pre != "verified"
            for field, new in it["corrected"].items():
                old = checks.get(field) if field in ("detail", "population") else row[field]
                if str(old) == str(new):
                    continue  # already applied (an amended audit file can be applied again)
                if field in ("detail", "population"):
                    con.execute("INSERT INTO corrections(record_id, field, old, new, reason, auditor, at) "
                                "VALUES(?,?,?,?,?,?,?)", (it["id"], field, str(old), str(new),
                                                          it.get("note", ""), who, time.time()))
                    checks[field] = new
                if field in ("value", "ci_low", "ci_high", "unit", "arm", "measure", "quote", "comparator"):
                    con.execute("INSERT INTO corrections(record_id, field, old, new, reason, auditor, at) "
                                "VALUES(?,?,?,?,?,?,?)", (it["id"], field, str(old), str(new),
                                                          it.get("note", ""), who, time.time()))
                    con.execute(f"UPDATE records SET {field}=? WHERE id=?", (new, it["id"]))
        else:
            status = "rejected"
            stats["review_rejected"] += pre != "verified"
        con.execute("UPDATE records SET status=?, checks=?, updated_at=? WHERE id=?",
                    (status, json.dumps(checks), time.time(), it["id"]))
    con.commit()
    board = json.loads(SCOREBOARD.read_text()) if SCOREBOARD.exists() else {"audits": []}
    board["audits"] = [a for a in board["audits"] if a["date"] != day] + [
        {"date": day, "auditor": who, "sampled": stats["sampled"], "correct": stats["correct"],
         "review_confirmed": stats["review_confirmed"], "review_corrected": stats["review_corrected"],
         "review_rejected": stats["review_rejected"], "notes": audit.get("summary", "")}]
    SCOREBOARD.write_text(json.dumps(board, indent=1))
    # re-applying an amended audit file replaces that audit's log line instead of adding another
    con.execute("DELETE FROM events WHERE event LIKE ?", (f'%"text": "Audit {day}:%',))
    db.emit(con, {"type": "log", "entry": {"t": int(time.time() * 1000), "kind": "finding",
                                           "text": f"Audit {day}: {stats['correct']}/{stats['sampled']} verified numbers "
                                                   f"confirmed; {stats['review_corrected']} corrected, "
                                                   f"{stats['review_rejected']} rejected"}})
    return stats
