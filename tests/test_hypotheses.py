"""Every registered hypothesis has a test, and the ledger runs on an empty database (everything waits)."""
from ada import db, hypotheses


def test_every_registered_hypothesis_has_a_test():
    specs = hypotheses.load_specs()
    assert {s["id"] for s in specs} >= {"H001", "H002", "H003", "H004"}
    for s in specs:
        assert s["test_function"] in hypotheses.TESTS
        assert s["decision"] and s["disclosure"] and s["registered"]


def test_ledger_on_empty_database(tmp_path, monkeypatch):
    monkeypatch.setattr(hypotheses, "RESULTS", tmp_path / "h.json")
    results = hypotheses.run_all(db.connect(tmp_path / "t.sqlite"))
    assert {r["status"] for r in results} == {"waiting"}  # no verdict without data
    assert all(r["spec_hash"] for r in results)
