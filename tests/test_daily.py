"""The daily recap must work on any database, including an empty one."""
from ada import db
from ada.daily import daily


def test_daily_on_empty_db(tmp_path):
    assert daily(db.connect(tmp_path / "t.sqlite")) == []
