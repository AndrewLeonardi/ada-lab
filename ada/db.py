"""Ada's lab database: everything she reads, decides, extracts and checks, with provenance.

SQLite, one file (``livinglab/data/ada.sqlite``). Nothing is ever deleted: decisions
and extractions are appended, and the latest one wins. That keeps a full audit trail.
"""

from __future__ import annotations

import json
import os
import pathlib
import sqlite3
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

DATA_DIR = pathlib.Path(__file__).resolve().parents[1] / "data"
DB_PATH = pathlib.Path(os.environ.get("ADA_DB", DATA_DIR / "ada.sqlite"))  # ADA_DB: use another file (tests)

# Ada's working day runs from 9:00 to 9:00 US Eastern: her daily budget resets at 9 AM, when it can be watched.
DAY_TZ = ZoneInfo("America/New_York")
DAY_STARTS_HOUR = 9


def budget_day(ts: float | None = None) -> str:
    """The working day (YYYY-MM-DD, named after the date it starts) that contains this moment."""
    t = datetime.fromtimestamp(time.time() if ts is None else ts, DAY_TZ) - timedelta(hours=DAY_STARTS_HOUR)
    return t.strftime("%Y-%m-%d")


def next_day_start(ts: float | None = None) -> float:
    """When the next working day (and daily budget) starts, as a Unix time."""
    now = datetime.fromtimestamp(time.time() if ts is None else ts, DAY_TZ)
    start = now.replace(hour=DAY_STARTS_HOUR, minute=0, second=0, microsecond=0)
    return (start if now < start else start + timedelta(days=1)).timestamp()

SCHEMA = """
CREATE TABLE IF NOT EXISTS papers (
  pmid TEXT PRIMARY KEY,
  title TEXT, journal TEXT, year INTEGER, authors TEXT, doi TEXT,
  abstract TEXT, pub_types TEXT, nct_ids TEXT,
  found_by TEXT, fetched_at REAL
);
CREATE TABLE IF NOT EXISTS screenings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  pmid TEXT, decision TEXT, reason TEXT, detail TEXT,
  model TEXT, prompt_version TEXT, usd REAL, at REAL
);
CREATE TABLE IF NOT EXISTS extractions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  pmid TEXT, pass INTEGER, model TEXT, prompt_version TEXT, result TEXT, usd REAL, at REAL
);
CREATE TABLE IF NOT EXISTS records (
  id TEXT PRIMARY KEY,            -- pmid:arm:measure
  pmid TEXT, arm TEXT, measure TEXT,
  value REAL, ci_low REAL, ci_high REAL, unit TEXT,
  quote TEXT, status TEXT, checks TEXT, comparator TEXT,
  updated_at REAL
);
CREATE TABLE IF NOT EXISTS trials (
  pmid TEXT PRIMARY KEY,
  acronym TEXT, phase TEXT, line TEXT, setting TEXT, biomarker TEXT,
  n_randomized INTEGER, primary_endpoint TEXT, registry_ids TEXT, arms TEXT,
  status TEXT, updated_at REAL
);
CREATE TABLE IF NOT EXISTS spend (
  day TEXT, model TEXT, stage TEXT, usd REAL, calls INTEGER,
  PRIMARY KEY (day, model, stage)
);
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT, at REAL, event TEXT
);
CREATE TABLE IF NOT EXISTS corrections (
  id INTEGER PRIMARY KEY AUTOINCREMENT, record_id TEXT, field TEXT, old TEXT, new TEXT,
  reason TEXT, auditor TEXT, at REAL
);
"""


def connect(path: pathlib.Path = DB_PATH) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def add_spend(con: sqlite3.Connection, model: str, stage: str, usd: float):
    day = budget_day()
    con.execute(
        "INSERT INTO spend(day, model, stage, usd, calls) VALUES(?,?,?,?,1) "
        "ON CONFLICT(day, model, stage) DO UPDATE SET usd = usd + excluded.usd, calls = calls + 1",
        (day, model, stage, usd),
    )
    con.commit()


def spent(con: sqlite3.Connection, day: str | None = None) -> float:
    if day:
        r = con.execute("SELECT COALESCE(SUM(usd),0) FROM spend WHERE day=?", (day,)).fetchone()
    else:
        r = con.execute("SELECT COALESCE(SUM(usd),0) FROM spend").fetchone()
    return float(r[0])


def emit(con: sqlite3.Connection, event: dict):
    """Record an event for the room (same protocol as livinglab/web/src/world/protocol.ts)."""
    con.execute("INSERT INTO events(at, event) VALUES(?, ?)", (time.time(), json.dumps(event)))
    con.commit()
