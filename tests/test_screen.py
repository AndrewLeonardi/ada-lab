"""Screening decisions must follow the checklist."""
from ada.screen import enforce


def res(**kw):
    base = {"population": "mCRC", "randomized": True, "metastatic": True, "per_arm_efficacy": True,
            "primary_report": True, "reason": "ok", "decision": "include", "trial_name": None}
    base.update(kw)
    return base


def test_include_kept_when_checklist_passes():
    assert enforce(res())["decision"] == "include"


def test_locally_advanced_include_is_excluded():
    # spot check 1: "Randomized phase 3 trial in locally advanced rectal cancer ..." was marked include
    assert enforce(res(metastatic=False))["decision"] == "exclude"


def test_follow_up_report_becomes_secondary():
    assert enforce(res(primary_report=False))["decision"] == "secondary"


def test_exclude_is_never_upgraded():
    assert enforce(res(decision="exclude"))["decision"] == "exclude"
