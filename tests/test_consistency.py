"""Numbers from one trial that cannot all be right must be caught."""
from ada.consistency import find


def rec(id, measure, arm, value, unit="months", comparator=None, ci_low=None, ci_high=None, population="overall"):
    return {"id": id, "measure": measure, "arm": arm, "value": value, "unit": unit, "comparator": comparator,
            "ci_low": ci_low, "ci_high": ci_high, "checks": {"population": population}}


def names(flags):
    return sorted(f["check"] for f in flags)


def test_hazard_ratio_against_medians():
    # found in her data: OS HR 1.3 for A vs B, but A's median OS is longer
    rs = [rec("h", "os_hr", "A", 1.3, "ratio", comparator="B"), rec("a", "os_median", "A", 40.4),
          rec("b", "os_median", "B", 34.4)]
    assert names(find(rs)) == ["hr_direction"]
    rs[0]["value"] = 0.77  # consistent
    assert find(rs) == []


def test_pfs_cannot_exceed_os_and_orr_cannot_exceed_dcr():
    rs = [rec("p", "pfs_median", "A", 14.0), rec("o", "os_median", "A", 12.0),
          rec("r", "orr", "A", 60.0, "percent"), rec("d", "dcr", "A", 55.0, "percent")]
    assert names(find(rs)) == ["orr_exceeds_dcr", "pfs_exceeds_os"]


def test_hazard_ratio_off_centre_and_arm_totals():
    rs = [rec("h", "pfs_hr", "A", 0.96, "ratio", comparator="B", ci_low=0.58, ci_high=0.98),
          rec("n1", "n_randomized", "A", 120, "count"), rec("n2", "n_randomized", "B", 119, "count")]
    assert names(find(rs, trial_total=200)) == ["arms_exceed_total", "hr_ci_off_center"]
    rs[0]["value"] = 0.75  # centred on the log scale
    assert names(find(rs, trial_total=239)) == []


def test_subgroups_are_not_mixed_with_the_overall_population():
    rs = [rec("p", "pfs_median", "A", 14.0, population="KRAS wild-type"), rec("o", "os_median", "A", 12.0)]
    assert find(rs) == []
