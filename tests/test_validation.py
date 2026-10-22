"""Human validation: a fixed-seed sample without Ada's values, and an honest agreement report."""
import json

import pytest

from ada import db, validation


def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(validation, "DIR", tmp_path / "validation")
    con = db.connect(tmp_path / "t.sqlite")
    con.execute("INSERT INTO papers(pmid, title) VALUES('1', 'A trial')")
    con.execute("INSERT INTO screenings(pmid, decision) VALUES('1', 'include')")
    for i, v in enumerate([9.9, 8.4, 0.7]):
        con.execute("INSERT INTO records(id, pmid, arm, measure, value, unit, quote, status, checks) VALUES(?,?,?,?,?,?,?,?,?)",
                    (f"r{i}", "1", "A", "os_median", v, "months", "q", "verified", json.dumps({"population": "overall"})))
    con.commit()
    return con


def test_sample_hides_values_and_is_never_redrawn(tmp_path, monkeypatch):
    con = setup(tmp_path, monkeypatch)
    s = validation.draw(con, "pilot", 2)
    assert len(s["items"]) == 2 and all("value" not in it for it in s["items"])
    with pytest.raises(SystemExit):
        validation.draw(con, "pilot", 2)


def test_report(tmp_path, monkeypatch):
    con = setup(tmp_path, monkeypatch)
    s = validation.draw(con, "pilot", 3)
    vals = {"r0": 9.9, "r1": 8.4, "r2": 0.7}
    answers = {it["id"]: {"value": vals[it["id"]]} for it in s["items"]}
    answers[s["items"][0]["id"]] = {"not_stated": True, "note": "not in the abstract"}
    r = validation.report(con, {"sample": "pilot", "validator": "test", "answers": answers})
    assert r["answered"] == 3 and r["agree"] == 2 and len(r["disagreements"]) == 1
