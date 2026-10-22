"""The paper-versus-registry comparison, on a small registry record shaped like ClinicalTrials.gov's."""
from ada.registry import compare, families

STUDY = {
    "protocolSection": {"outcomesModule": {"primaryOutcomes": [{"measure": "Progression-Free Survival (PFS)"}]},
                        "designModule": {"enrollmentInfo": {"count": 200}}},
    "resultsSection": {"outcomeMeasuresModule": {"outcomeMeasures": [
        {"title": "Progression-Free Survival (PFS)", "paramType": "MEDIAN", "unitOfMeasure": "Months",
         "classes": [{"categories": [{"measurements": [{"groupId": "OG000", "value": "9.9"},
                                                       {"groupId": "OG001", "value": "8.4"}]}]}],
         "analyses": [{"paramType": "Hazard Ratio (HR)", "paramValue": "0.70"}]},
        {"title": "Overall Survival", "paramType": "MEDIAN", "unitOfMeasure": "Days",
         "classes": [{"categories": [{"measurements": [{"groupId": "OG000", "value": "608"}]}]}]},
    ]}},
}


def rec(measure, value, unit="months"):
    return {"id": measure, "measure": measure, "value": value, "unit": unit, "arm": "A"}


def verdicts(checks):
    return {c["check"]: c["verdict"] for c in checks}


def test_endpoint_families():
    assert families("Overall Survival (OS)") == {"os"}
    assert families("Progression-Free Survival (PFS) Rate at 18 Weeks") == {"pfs"}
    assert families("Failure-free survival") == {"dfs"}


def test_compare_with_registry():
    trial = {"primary_endpoint": "progression-free survival", "n_randomized": 198}
    v = verdicts(compare(trial, [rec("pfs_median", 9.9), rec("pfs_hr", 1.43, "ratio"), rec("os_median", 20.0)], STUDY))
    assert v["primary_endpoint"] == "agrees" and v["patients"] == "agrees"
    assert v["pfs_median"] == "agrees"
    assert v["pfs_hr"] == "agrees"  # registered the other way round: 1 / 0.70 = 1.43
    assert v["os_median"] == "agrees"  # 608 days is 20.0 months


def test_differences_are_reported():
    trial = {"primary_endpoint": "overall survival", "n_randomized": 120}
    v = verdicts(compare(trial, [rec("pfs_median", 7.2)], STUDY))
    assert v == {"primary_endpoint": "differs", "patients": "differs", "pfs_median": "differs"}


def test_rounding_and_whole_population_tables():
    study = {"protocolSection": {}, "resultsSection": {"outcomeMeasuresModule": {"outcomeMeasures": [
        {"title": "Objective Response Rate (ORR)", "paramType": "NUMBER", "unitOfMeasure": "percentage of participants",
         "classes": [{"categories": [{"measurements": [{"groupId": "OG000", "value": "60.6"}]}]}]},
        {"title": "Progression-Free Survival in Participants With Left-sided Tumors", "paramType": "MEDIAN",
         "unitOfMeasure": "Months", "classes": [{"categories": [{"measurements": [{"groupId": "OG000", "value": "13.7"}]}]}]},
        {"title": "Progression-Free Survival", "paramType": "MEDIAN", "unitOfMeasure": "Months",
         "classes": [{"categories": [{"measurements": [{"groupId": "OG000", "value": "12.2"}]}]}]},
    ]}}}
    v = verdicts(compare({}, [rec("orr", 61.0, "percent"), rec("pfs_median", 12.2)], study))
    assert v == {"orr": "agrees", "pfs_median": "agrees"}  # 61% is 60.6% rounded; the left-sided table is not used
    assert verdicts(compare({}, [rec("orr", 60.0, "percent")], study)) == {"orr": "differs"}  # 60.6 rounds to 61
