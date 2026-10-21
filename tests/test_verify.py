"""The verification rules are what make Ada's numbers trustworthy; test them directly."""
from ada.verify import check_record, number_in

ABSTRACT = ("RESULTS: The response rate was 57.3% (95% CI, 51.6 to 62.8) with FOLFIRI plus cetuximab and 39·7% with "
            "FOLFIRI alone. Median progression-free survival was 9.9 months versus 8.4 months (hazard ratio, 0.696).")


def rec(**kw):
    base = {"arm": "A", "measure": "orr", "value": 57.3, "unit": "percent", "ci_low": 51.6, "ci_high": 62.8,
            "population": "overall", "detail": None, "comparator": None,
            "quote": "The response rate was 57.3% (95% CI, 51.6 to 62.8)"}
    base.update(kw)
    return base


def test_true_record_passes_all_checks():
    c = check_record(rec(), ABSTRACT, [rec()])
    assert all(c.values()), c


def test_invented_quote_fails():
    assert not check_record(rec(quote="The response rate was 57.3% in all patients"), ABSTRACT, None)["quote_found"]


def test_number_not_in_quote_fails():
    assert not check_record(rec(value=58.0), ABSTRACT, None)["value_in_quote"]


def test_lancet_middle_dot_decimal_is_handled():
    r = rec(value=39.7, ci_low=None, ci_high=None, quote="39·7% with FOLFIRI alone")
    c = check_record(r, ABSTRACT, None)
    assert c["quote_found"] and c["value_in_quote"]


def test_second_pass_disagreement_flags_record():
    c = check_record(rec(), ABSTRACT, [rec(value=57.0)])
    assert c["second_pass_agrees"] is False


def test_implausible_value_flagged():
    assert not check_record(rec(measure="pfs_hr", value=57.3, unit="ratio"), ABSTRACT, None)["plausible"]


def test_number_in():
    assert number_in("HR 0.696", 0.696) and not number_in("HR 0.696", 0.69) and number_in("1,234 patients", 1234)
