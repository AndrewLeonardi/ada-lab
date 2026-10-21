"""The daily recap must work on any database, including an empty one."""
from datetime import datetime
from zoneinfo import ZoneInfo

from ada import db
from ada.daily import daily


def test_daily_on_empty_db(tmp_path):
    assert daily(db.connect(tmp_path / "t.sqlite")) == []


def test_working_day_starts_at_9_eastern():
    et = ZoneInfo("America/New_York")
    assert db.budget_day(datetime(2026, 10, 21, 8, 59, tzinfo=et).timestamp()) == "2026-10-20"
    assert db.budget_day(datetime(2026, 10, 21, 9, 0, tzinfo=et).timestamp()) == "2026-10-21"
    # across the DST change (1 Nov 2026), the reset stays at 9:00 local time
    start = db.next_day_start(datetime(2026, 10, 31, 20, 0, tzinfo=et).timestamp())
    assert datetime.fromtimestamp(start, et).strftime("%Y-%m-%d %H:%M") == "2026-11-01 09:00"
