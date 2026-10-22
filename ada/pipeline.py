"""Ada's work loop: find papers, screen them, extract outcomes twice, verify, publish.

Each step also emits events for the room (livinglab/web/src/world/protocol.ts), so what you
see her doing is what she is actually doing.
"""

from __future__ import annotations

import json
import os
import pathlib
import time

import yaml

from . import db, nightshift, sources
from .extract import extract_paper, record as record_extraction, request as extraction_request
from .llm import Budget, BudgetExceeded, Claude, Refused
from .screen import screen_paper
from .verify import verify_paper

# What she does in the lounge while the day's budget is used up, in turn, about 20 minutes each.
REST = [
    ("listen_music", "happy", "Off the clock: listening to records", "Good day's work. Time for some music."),
    ("read_book", "curious", "Off the clock: reading for fun", None),
    ("nap", "tired", "Napping until her budget resets", None),
    ("listen_music", "happy", "Off the clock: listening to records", None),
    ("nap", "tired", "Napping until her budget resets", None),
    ("nap", "tired", "Napping until her budget resets", None),
]
REST_SECONDS = 1200

# Her current state ("working", "resting", "idle"), read by export for the website's budget meter.
STATE_FILE = db.DB_PATH.with_name("state.json")
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
def _announce(con, p: dict):
    pmid = p["pmid"]
    short = p["title"] if len(p["title"]) < 90 else p["title"][:87] + "..."
    act(con, "desk", "read_screen", "focused", f"Extracting outcomes: PMID {pmid}", f"Reading: {short}")
    db.emit(con, {"type": "screen", "screen": "computer", "content": {
        "app": "paper", "source": "PubMed", "url": f"pubmed.ncbi.nlm.nih.gov/{pmid}", "title": p["title"],
        "authors": p["authors"] or "", "journal": f"{p['journal']} {p['year']} - PMID {pmid}",
        "body": "Extracting arm-level outcomes. Every number must come with the exact sentence it was taken from; "
                "a second, independent pass must agree before a number counts as verified."}})


def _verify_and_report(con, p: dict, r1: dict, r2: dict) -> dict:
    pmid = p["pmid"]
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


def extract_one(con, claude: Claude, models: list[str], pmid: str) -> dict | None:
    """Extract one paper now, at full price (the benchmark, and papers a batch could not do)."""
    row = con.execute("SELECT * FROM papers WHERE pmid=?", (pmid,)).fetchone()
    if not row:
        return None
    p = _paper(row)
    _announce(con, p)
    r1 = extract_paper(con, claude, models[0], p, 1)
    r2 = extract_paper(con, claude, models[1], p, 2)
    return _verify_and_report(con, p, r1, r2)


# Papers are read in half-price batches (Message Batches API). One batch at a time keeps spending in step
# with the daily cap; the estimate per paper is her measured cost (both passes) at half price, plus a margin.
BATCH_SIZE = 40
BATCH_EST_USD = 0.0176 * 0.5 * 1.25
BATCH_POLL_SECONDS = 60
_last_poll = [0.0]


def pending_batch(con):
    return con.execute("SELECT * FROM batches WHERE status='submitted' ORDER BY submitted_at LIMIT 1").fetchone()


def extract_step(con, claude: Claude, models: list[str], collect_only: bool = False) -> int:
    """Collect a finished batch, or (unless collect_only) send the next one. Returns papers sent or verified."""
    b = pending_batch(con)
    if b:
        if time.time() - _last_poll[0] < BATCH_POLL_SECONDS and not claude.mock:
            return 0
        _last_poll[0] = time.time()
        if not claude.batch_done(b["id"]):
            return 0
        pmids = json.loads(b["items"])
        stages = {f"{pm}-{k}": (f"extract{k}", models[k - 1]) for pm in pmids for k in (1, 2)}
        results = claude.batch_results(b["id"], stages)
        act(con, "desk", "read_screen", "excited", f"Batch back: {len(pmids)} papers to verify",
            "The reading service is done. Checking every number against its source.")
        done = usd = 0
        for pmid in pmids:
            row = con.execute("SELECT * FROM papers WHERE pmid=?", (pmid,)).fetchone()
            r1, r2 = results.get(f"{pmid}-1"), results.get(f"{pmid}-2")
            if not row or con.execute("SELECT 1 FROM extractions WHERE pmid=?", (pmid,)).fetchone():
                continue
            p = _paper(row)
            if r1 is None or r2 is None:
                try:  # retry directly once, at full price; if that fails too, it waits for the auditor
                    extract_one(con, claude, models, pmid)
                except BudgetExceeded:
                    pass  # no budget left today: it goes into a later batch
                except (Refused, RuntimeError, ValueError) as e:
                    con.execute("INSERT INTO extractions(pmid, pass, model, prompt_version, result, usd, at) "
                                "VALUES(?,?,?,?,?,?,?)", (pmid, 0, models[0], "failed", json.dumps({"error": str(e)[:300]}),
                                                          0.0, time.time()))
                    con.commit()
                continue
            for k, (res, cost) in ((1, r1), (2, r2)):
                record_extraction(con, pmid, k, models[k - 1], res, cost)
                usd += cost
            _announce(con, p)
            _verify_and_report(con, p, r1[0], r2[0])
            done += 1
            if not claude.mock:
                time.sleep(2)  # one paper at a time on the lab's screen
        con.execute("UPDATE batches SET status='ended', ended_at=?, usd=? WHERE id=?", (time.time(), usd, b["id"]))
        con.commit()
        return done
    if collect_only:
        return 0
    rows = con.execute(
        "SELECT s.pmid FROM screenings s WHERE s.id IN (SELECT MAX(id) FROM screenings GROUP BY pmid) "
        "AND s.decision='include' AND s.pmid NOT IN (SELECT pmid FROM extractions) LIMIT ?", (BATCH_SIZE,)).fetchall()
    if not rows:
        return 0
    claude.budget.check(con, len(rows) * BATCH_EST_USD)  # raises if the batch could break today's cap
    papers = [_paper(con.execute("SELECT * FROM papers WHERE pmid=?", (r["pmid"],)).fetchone()) for r in rows]
    items = [{"custom_id": f"{p['pmid']}-{k}", **extraction_request(models[k - 1], p, k)} for p in papers for k in (1, 2)]
    bid = claude.submit_batch(items)
    con.execute("INSERT INTO batches(id, kind, items, submitted_at, status) VALUES(?,?,?,?,?)",
                (bid, "extract", json.dumps([p["pmid"] for p in papers]), time.time(), "submitted"))
    con.commit()
    act(con, "desk", "type", "focused", f"Sent {len(papers)} papers to the reading service (half price)",
        "Two independent readings of each. Results usually within the hour.")
    log(con, f"Sent {len(papers)} papers for extraction in a half-price batch", "action")
    return len(papers)


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
    # On the server, publish to the website every N hours (set in the service), and soon after she starts or
    # stops working, so the site's budget meter is current. Elsewhere publishing is manual.
    publish_every = float(os.environ.get("ADA_PUBLISH_HOURS") or 0) * 3600
    last_publish, publish_pending = 0.0, False
    state = None  # "working", "free_work" (paid budget used, free tasks), "resting" (nothing left) or "idle"
    rest_i = 0

    def become(new: str) -> bool:
        """Record a change of state for the website; True if it changed (so it's shown once, not every loop)."""
        nonlocal state
        if new == state:
            return False
        state = new
        STATE_FILE.write_text(json.dumps({"state": new, "since": time.time(), "profile": profile,
                                          "daily_usd": prof["daily_usd"], "total_usd": prof["total_usd"]}))
        return True

    def maybe_publish(soon: bool = False):
        nonlocal last_publish, publish_pending
        publish_pending = publish_pending or soon
        gap = time.time() - last_publish
        if not publish_every or not (gap > publish_every or (publish_pending and gap > 1200)):
            return
        last_publish, publish_pending = time.time(), False
        try:
            from .publish import publish
            msg = publish(con)
            log(con, f"Website updated: {msg}" if msg else "Website already up to date", "system")
        except Exception as e:  # a failed publish must not stop the work; it is retried next interval
            log(con, f"Publishing failed: {type(e).__name__}: {str(e)[:200]}", "system")
            log_fn(f"[ada] publish failed: {e!r}")

    log(con, f"Ada starts work (profile: {profile})", "system")
    over: BudgetExceeded | None = None  # set while the day's paid budget is used up
    last_export = 0.0
    while stop_at is None or time.time() < stop_at:
        if state:  # the first publish waits until she knows whether she is working or resting
            maybe_publish()
        paid = free = 0
        try:
            if time.time() - last_sync > 24 * 3600:  # new papers from PubMed (free)
                sync(con)
                last_sync = time.time()
            paid += extract_step(con, claude, prof["extract_models"], collect_only=True)  # already paid for
            claude.budget.check(con)  # raises while the day's budget is used up
            over = None
            if state in (None, "resting", "free_work") and become("working"):  # tell the website now
                maybe_publish(soon=True)
            paid += screen_batch(con, claude, prof["screen_model"], screen_batch_size)
            paid += extract_step(con, claude, prof["extract_models"])
        except BudgetExceeded as e:
            over = e
        except Refused as e:
            log(con, f"A request was declined by a safety filter: {e}", "system")
        except Exception as e:  # keep the lab alive; record the problem
            log(con, f"Error: {type(e).__name__}: {str(e)[:200]}", "system")
            log_fn(f"[ada] error: {e!r}")
            time.sleep(60)
        # one small step of free work every round, also between paid batches (found in audit 2: candidate papers
        # waited for a model check that only ran when no paid work was going on). Its few cheap model calls
        # (confirming a paper matches a trial) may use whatever is left of today's budget, even when a whole batch
        # no longer fits; each call is still checked against the cap.
        under_cap = db.spent(con, db.budget_day()) < prof["daily_usd"]
        try:
            free = nightshift.step(con, claude if under_cap else None)
        except Exception as e:  # network trouble etc.: try again later
            log(con, f"Free shift error: {type(e).__name__}: {str(e)[:200]}", "system")
            log_fn(f"[ada] free shift error: {e!r}")
            time.sleep(60)
        if paid or time.time() - last_export > 300:
            board_update(con)
            from .export import export
            export(con)
            last_export = time.time()
        waiting = pending_batch(con) is not None
        if over is None and (paid or free or waiting):
            if become("working"):
                maybe_publish(soon=True)
            if not paid:
                time.sleep(5 if free else 30)  # between free steps, or while a batch is being read
        elif free:  # paid budget used up: the free night shift
            if become("free_work"):
                log(con, f"Paid budget used ({over}): starting the free night shift", "system")
                maybe_publish(soon=True)
            time.sleep(5)
        elif over is not None:  # no free work left either: the lounge
            if become("resting"):
                log(con, f"Pausing: {over}", "system")
                rest_i = 0
                maybe_publish(soon=True)
            activity, mood, status, thought = REST[rest_i % len(REST)]
            if "total cap" in str(over):
                status = "Paused: her total budget is used up"
            act(con, "couch", activity, mood, status, thought)
            rest_i += 1
            log_fn(f"[ada] {over}; resting {REST_SECONDS // 60} min")
            time.sleep(REST_SECONDS)
        else:  # budget left but nothing to do: caught up
            if become("idle"):
                act(con, "coffee", "drink_coffee", "happy", "Backlog clear - waiting for new papers",
                    "All caught up. I'll check PubMed again later.")
                maybe_publish(soon=True)
            time.sleep(idle_seconds)
