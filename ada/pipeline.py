"""Ada's work loop: find papers, screen them, extract outcomes twice, verify, publish.

Each step also emits events for the room (livinglab/web/src/world/protocol.ts), so what you
see her doing is what she is actually doing.
"""

from __future__ import annotations

import json
import pathlib
import time

import yaml

from . import db, sources
from .extract import extract_paper
from .llm import Budget, BudgetExceeded, Claude, Refused
from .screen import screen_paper
from .verify import verify_paper

PROFILES = yaml.safe_load((pathlib.Path(__file__).with_name("profiles.yaml")).read_text())
LINE_COLORS = {"first": "#e07a6a", "second": "#3f9a96", "third_or_later": "#7aa6c2", "maintenance": "#e3c46a",
               "mixed": "#c9787a", "unclear": "#b8c2c6"}


def log(con, text: str, kind: str = "action"):
    db.emit(con, {"type": "log", "entry": {"t": int(time.time() * 1000), "text": text, "kind": kind}})


def act(con, station: str, activity: str, mood: str, status: str, thought: str | None = None):
    db.emit(con, {"type": "goto", "station": station, "activity": activity})
    db.emit(con, {"type": "mood", "mood": mood})
    db.emit(con, {"type": "status", "text": status})
    db.emit(con, {"type": "thought", "text": thought})


# ------------------------------------------------------------------ stage 0: find papers (free)
def sync(con, limit: int | None = None, mindate: str | None = None) -> int:
    act(con, "desk", "type", "focused", "Searching PubMed for new randomized trials",
        "Any new colorectal cancer trials published?")
    count, ids = sources.search(mindate=mindate)
    have = {r[0] for r in con.execute("SELECT pmid FROM papers")}
    new = [i for i in ids if i not in have][: limit or None]
    db.emit(con, {"type": "screen", "screen": "computer", "content": {
        "app": "search", "source": "PubMed", "query": "randomized trials, metastatic colorectal cancer",
        "url": "pubmed.ncbi.nlm.nih.gov", "results": [{"title": f"{count} records match", "meta": f"{len(new)} new to Ada"}]}})
    for p in sources.fetch(new) if new else []:
        con.execute("INSERT OR IGNORE INTO papers(pmid, title, journal, year, authors, doi, abstract, pub_types, "
                    "nct_ids, found_by, fetched_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    (p["pmid"], p["title"], p["journal"], p["year"], p["authors"], p["doi"], p["abstract"],
                     json.dumps(p["pub_types"]), json.dumps(p["nct_ids"]), "pubmed-mcrc-rct-v1", time.time()))
    con.commit()
    log(con, f"PubMed: {count} records match the search; {len(new)} new added to the reading list")
    return len(new)


def _paper(row) -> dict:
    p = dict(row)
    p["pub_types"] = json.loads(p.get("pub_types") or "[]")
    p["nct_ids"] = json.loads(p.get("nct_ids") or "[]")
    return p


# ------------------------------------------------------------------ stage 1: screening
def screen_batch(con, claude: Claude, model: str, n: int = 25) -> int:
    rows = con.execute("SELECT * FROM papers WHERE pmid NOT IN (SELECT pmid FROM screenings) "
                       "ORDER BY year DESC LIMIT ?", (n,)).fetchall()
    if not rows:
        return 0
    papers = [_paper(r) for r in rows]
    act(con, "desk", "read_screen", "focused", f"Screening {len(papers)} abstracts",
        "Randomized? Metastatic? Outcomes per arm?")
    db.emit(con, {"type": "screen", "screen": "computer", "content": {
        "app": "search", "source": "Screening queue", "query": f"{len(papers)} abstracts to screen",
        "url": "ada://screening", "results": [{"title": p["title"], "meta": f"{p['journal']} {p['year']} - PMID {p['pmid']}"}
                                              for p in papers[:6]]}})
    inc = 0
    for p in papers:
        res = screen_paper(con, claude, model, p)
        inc += res["decision"] == "include"
    log(con, f"Screened {len(papers)} abstracts: {inc} randomized mCRC trials to extract")
    return len(papers)


# ------------------------------------------------------------------ stage 2+3: extraction and verification
def extract_one(con, claude: Claude, models: list[str], pmid: str) -> dict | None:
    row = con.execute("SELECT * FROM papers WHERE pmid=?", (pmid,)).fetchone()
    if not row:
        return None
    p = _paper(row)
    short = p["title"] if len(p["title"]) < 90 else p["title"][:87] + "..."
    act(con, "desk", "read_screen", "focused", f"Extracting outcomes: PMID {pmid}", f"Reading: {short}")
    db.emit(con, {"type": "screen", "screen": "computer", "content": {
        "app": "paper", "source": "PubMed", "url": f"pubmed.ncbi.nlm.nih.gov/{pmid}", "title": p["title"],
        "authors": p["authors"] or "", "journal": f"{p['journal']} {p['year']} - PMID {pmid}",
        "body": "Extracting arm-level outcomes. Every number must come with the exact sentence it was taken from; "
                "a second, independent pass must agree before a number counts as verified."}})
    r1 = extract_paper(con, claude, models[0], p, 1)
    r2 = extract_paper(con, claude, models[1], p, 2)
    counts = verify_paper(con, p, r1, r2)
    t = r1["trial"]
    name = t.get("acronym") or f"PMID {pmid}"
    total = counts["verified"] + counts["needs_review"]
    mood = "happy" if total and counts["needs_review"] == 0 else "puzzled" if counts["needs_review"] else "neutral"
    if counts["verified"]:
        db.emit(con, {"type": "book", "book": {
            "id": f"pmid-{pmid}", "title": p["title"], "kind": "paper", "source": f"{p['journal']} {p['year']} - PMID {pmid}",
            "note": f"{name}: {counts['verified']} numbers verified, {counts['needs_review']} for review.",
            "color": LINE_COLORS.get(t.get("line") or "unclear", "#b8c2c6")}})
    db.emit(con, {"type": "mood", "mood": mood})
    log(con, f"{name} (PMID {pmid}): {counts['verified']} numbers verified, {counts['needs_review']} need review",
        "finding" if counts["verified"] else "action")
    return counts


def extract_batch(con, claude: Claude, models: list[str], n: int = 5) -> int:
    rows = con.execute(
        "SELECT s.pmid FROM screenings s WHERE s.id IN (SELECT MAX(id) FROM screenings GROUP BY pmid) "
        "AND s.decision='include' AND s.pmid NOT IN (SELECT pmid FROM extractions) LIMIT ?", (n,)).fetchall()
    for r in rows:
        extract_one(con, claude, models, r["pmid"])
    return len(rows)


def board_update(con):
    """The whiteboard shows the dataset's state and the review queue."""
    n_trials = con.execute("SELECT COUNT(*) FROM trials").fetchone()[0]
    n_ver = con.execute("SELECT COUNT(*) FROM records WHERE status IN ('verified','corrected')").fetchone()[0]
    n_rev = con.execute("SELECT COUNT(*) FROM records WHERE status='needs_review'").fetchone()[0]
    n_left = con.execute("SELECT COUNT(*) FROM screenings s WHERE s.id IN (SELECT MAX(id) FROM screenings GROUP BY pmid) "
                         "AND decision='include' AND pmid NOT IN (SELECT pmid FROM extractions)").fetchone()[0]
    for hid, status, text in (
        ("dataset", "supported", f"Dataset: {n_trials} trials, {n_ver} verified numbers"),
        ("queue", "testing", f"{n_rev} numbers waiting for the auditor"),
        ("backlog", "open", f"{n_left} included trials still to extract"),
    ):
        db.emit(con, {"type": "hypothesis", "hypothesis": {"id": hid, "status": status, "text": text}})


# ------------------------------------------------------------------ the loop
def run(profile: str = "balanced", hours: float | None = None, mock=None, screen_batch_size: int = 25,
        idle_seconds: int = 600, log_fn=print):
    prof = PROFILES[profile]
    con = db.connect()
    claude = Claude(con, Budget(prof["daily_usd"], prof["total_usd"]), mock=mock)
    stop_at = time.time() + hours * 3600 if hours else None
    last_sync = 0.0
    log(con, f"Ada starts work (profile: {profile})", "system")
    while stop_at is None or time.time() < stop_at:
        try:
            if time.time() - last_sync > 24 * 3600:
                sync(con)
                last_sync = time.time()
            did = screen_batch(con, claude, prof["screen_model"], screen_batch_size)
            did += extract_batch(con, claude, prof["extract_models"], 3)
            board_update(con)
            from .export import export
            export(con)
            if not did:
                act(con, "coffee", "drink_coffee", "happy", "Backlog clear - waiting for new papers",
                    "All caught up. I'll check PubMed again later.")
                time.sleep(idle_seconds)
        except BudgetExceeded as e:
            act(con, "desk", "sleep", "tired", "Daily budget used - resting until tomorrow", None)
            log(con, f"Pausing: {e}", "system")
            from .export import export
            export(con)
            log_fn(f"[ada] {e}; sleeping 30 min")
            time.sleep(1800)
        except Refused as e:
            log(con, f"A request was declined by a safety filter: {e}", "system")
        except Exception as e:  # keep the lab alive; record the problem
            log(con, f"Error: {type(e).__name__}: {str(e)[:200]}", "system")
            log_fn(f"[ada] error: {e!r}")
            time.sleep(60)
