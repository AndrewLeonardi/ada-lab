"""The free night shift: useful work that costs nothing, for the hours her paid budget is used up.

One small step at a time (a few seconds of work), most important first:
  1. weekly: refresh the ClinicalTrials.gov records; re-run the consistency checks on every trial;
     re-read PubMed's correction and retraction links. Daily: link follow-up papers to their trials.
  2. compare her trials with their registry records (paper vs registry);
  3. look for the results of finished trials (the missing-results tracker);
  4. save open-access full texts for later.
Everything runs on public data. The one paid step (a model confirming that a paper found by search
is the trial's results paper) only runs while the day's paid budget lasts; otherwise it waits.
"""

from __future__ import annotations

import time

from . import db, registry, upkeep
from .consistency import check_trial

DAY = 86400
PERIODIC = [("registry_sync", 7 * DAY), ("consistency", 7 * DAY), ("later_reports", DAY), ("notices", 7 * DAY)]


def _due(con, name: str, every: float) -> bool:
    r = con.execute("SELECT last_run FROM tasks WHERE name=?", (name,)).fetchone()
    return r is None or time.time() - (r[0] or 0) > every


def _done(con, name: str, note: str):
    con.execute("INSERT OR REPLACE INTO tasks(name, last_run, note) VALUES(?,?,?)", (name, time.time(), note))
    con.commit()


def step(con, claude=None) -> int:
    """Do one small piece of free work. Returns units done (0 when there is nothing left)."""
    from .pipeline import act, log  # (pipeline imports this module)

    for name, every in PERIODIC:
        if not _due(con, name, every):
            continue
        if name == "registry_sync":
            act(con, "desk", "read_screen", "focused", "Free shift: refreshing ClinicalTrials.gov",
                "Every registered randomized trial in metastatic colorectal cancer.")
            note = f"{registry.sync(con)} registry records"
        elif name == "consistency":
            act(con, "whiteboard", "write_board", "focused", "Free shift: cross-checking every trial's numbers",
                "Do the hazard ratios and the medians agree?")
            flags = sum(len(check_trial(con, pmid)) for (pmid,) in
                        con.execute("SELECT DISTINCT pmid FROM records").fetchall())
            note = f"{flags} contradictions flagged for the auditor"
        elif name == "later_reports":
            note = f"{upkeep.link_later_reports(con)} follow-up papers linked"
        else:
            act(con, "desk", "read_screen", "focused", "Free shift: checking for corrections and retractions", None)
            note = f"{upkeep.notices_step(con)} new notices"
        _done(con, name, note)
        log(con, f"Free shift: {note}", "action")
        return 1

    def comparing(pmid, nct):
        t = con.execute("SELECT acronym FROM trials WHERE pmid=?", (pmid,)).fetchone()
        act(con, "desk", "read_screen", "curious", f"Free shift: {(t and t[0]) or 'PMID ' + pmid} vs its registry record",
            "Does the paper report what the trial registered?")
        db.emit(con, {"type": "screen", "screen": "computer", "content": {
            "app": "search", "source": "ClinicalTrials.gov", "query": nct, "url": f"clinicaltrials.gov/study/{nct}",
            "results": [{"title": "Registered primary outcome, patients, results tables", "meta": f"vs PMID {pmid}"}]}})

    n = registry.crosscheck_step(con, limit=1, on_trial=comparing)
    if n:
        pmid = con.execute("SELECT pmid FROM registry_checks ORDER BY id DESC LIMIT 1").fetchone()[0]
        v = dict(con.execute("SELECT verdict, COUNT(*) FROM registry_checks WHERE pmid=? GROUP BY verdict", (pmid,)).fetchall())
        name = (con.execute("SELECT acronym FROM trials WHERE pmid=?", (pmid,)).fetchone() or [None])[0] or f"PMID {pmid}"
        log(con, f"{name} vs registry: {v.get('agrees', 0)} agree, {v.get('differs', 0)} differ",
            "finding" if v.get("differs") else "action")
        return n

    def searching(t):
        years = t["months"] // 12
        act(con, "desk", "read_screen", "focused", f"Free shift: where are the results of {t['acronym'] or t['nct']}?",
            f"Finished {years} years ago with {t['enrollment']} patients.")
        db.emit(con, {"type": "screen", "screen": "computer", "content": {
            "app": "search", "source": "ClinicalTrials.gov + PubMed", "query": t["nct"],
            "url": f"clinicaltrials.gov/study/{t['nct']}",
            "results": [{"title": (t["title"] or "")[:140], "meta": f"{t['sponsor']} - {t['status'].lower()}"}]}})

    before = {r[0] for r in con.execute("SELECT nct FROM result_search")}
    n = registry.search_step(con, claude, limit=1, on_trial=searching)
    if n:
        for r in con.execute("SELECT r.nct, r.verdict, g.acronym, g.enrollment FROM result_search r "
                             "JOIN registry g ON g.nct = r.nct ORDER BY r.searched_at DESC LIMIT 1"):
            name = r["acronym"] or r["nct"]
            if r["verdict"] == "not_found":
                db.emit(con, {"type": "mood", "mood": "puzzled"})
                log(con, f"{name}: no results found anywhere ({r['enrollment']} patients)", "finding")
            elif r["nct"] not in before or r["verdict"] != "pending":
                log(con, f"{name}: results {r['verdict'].replace('_', ' ')}", "action")
        return n

    n = upkeep.fulltext_step(con, limit=3)
    if n:
        act(con, "bookshelf", "browse_books", "curious", "Free shift: saving open-access full texts", None)
        return n
    return 0
