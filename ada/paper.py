"""How ready the dataset is for its paper: measured from the data, plus the steps only a person can do
(research/paper/readiness.yaml). Published as paper.json for the website's Paper page."""

from __future__ import annotations

import json
import pathlib

import yaml

from . import db

ROOT = pathlib.Path(__file__).resolve().parents[1]


def readiness(con) -> dict:
    from .adjudicate import disputed
    from .validation import summary
    one = lambda q: con.execute(q).fetchone()[0]  # noqa: E731
    latest = "SELECT pmid, decision FROM screenings WHERE id IN (SELECT MAX(id) FROM screenings GROUP BY pmid)"
    candidates, screened = one("SELECT COUNT(*) FROM papers"), one("SELECT COUNT(DISTINCT pmid) FROM screenings")
    included = one(f"SELECT COUNT(*) FROM ({latest}) WHERE decision='include'")
    extracted = one(f"SELECT COUNT(*) FROM ({latest}) l WHERE decision='include' AND pmid IN (SELECT pmid FROM extractions)")
    public = (f"SELECT r.status FROM records r JOIN ({latest}) l ON l.pmid = r.pmid WHERE l.decision = 'include'")
    verified = one(f"SELECT COUNT(*) FROM ({public}) WHERE status IN ('verified','corrected')")
    review = one(f"SELECT COUNT(*) FROM ({public}) WHERE status='needs_review'")
    waiting = disputed(con)
    judged = one("SELECT COUNT(*) FROM adjudications")
    board = db.DATA_DIR / "audit_scoreboard.json"
    audits = json.loads(board.read_text())["audits"] if board.exists() else []
    protocols = sorted((ROOT / "research" / "protocol").glob("dataset-protocol-v*.md"))
    validation = summary()
    manual = yaml.safe_load((ROOT / "research" / "paper" / "readiness.yaml").read_text())["items"]

    def step(name, status, detail, progress=None):
        return {"name": name, "status": status, "detail": detail, "progress": progress}

    n_wait = sum(len(v) for v in waiting.values())
    res = next((v["results"] for v in reversed(validation) if v.get("results")), None)
    steps = [
        step("Protocol registered", "done" if protocols else "todo",
             f"{protocols[-1].name} (committed before the first release)" if protocols else "Not written yet."),
        step("Every candidate paper screened", "done" if screened >= candidates else "doing",
             f"{screened:,} of {candidates:,} PubMed records screened.", screened / max(1, candidates)),
        step("Every included trial extracted", "done" if extracted >= included else "doing",
             f"{extracted:,} of {included:,} included papers extracted (two independent readings each).",
             extracted / max(1, included)),
        step("Disagreements settled by a third reading", "done" if not n_wait else "doing" if judged else "todo",
             f"{judged:,} numbers judged by a third reading; {n_wait:,} waiting (in {len(waiting)} trials).",
             judged / max(1, judged + n_wait)),
        step("Review queue resolved or clearly flagged", "doing",
             f"{verified:,} numbers verified; {review:,} in review (published flagged, not as verified)."),
        step("Independent audits", "doing" if audits else "todo",
             (f"{len(audits)} audits; latest {audits[-1]['date']}: {audits[-1]['correct']} of {audits[-1]['sampled']} "
              "sampled numbers correct.") if audits else "None yet."),
        step("Human validation (150 numbers, blind)",
             "done" if res and res["of"] >= 150 and res["answered"] >= res["of"] else "doing" if validation else "todo",
             (f"Sample '{res['sample']}': {res['agree']} of {res['answered']} agree." if res else
              f"Sample '{validation[-1]['name']}' drawn ({len(validation[-1]['items'])} numbers); waiting for a validator."
              if validation else "Drawn at release 1.0 (a pilot can run earlier).")),
    ] + [step(m["name"], m["status"], m["note"]) for m in manual]
    done = sum(s["status"] == "done" for s in steps)
    return {"steps": steps, "done": done, "total": len(steps),
            "counts": {"candidates": candidates, "screened": screened, "included": included, "extracted": extracted,
                       "verified": verified, "review": review}}
