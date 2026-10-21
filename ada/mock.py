"""A free, offline stand-in for the model, for testing the pipeline end to end.

Screening includes anything that mentions randomization. Extraction records the first percentage
it finds as a response rate, quoting the clause it came from. Its "science" is deliberately crude.
"""

from __future__ import annotations

import re


def mock(stage: str, user: str, schema: dict) -> dict:
    if stage == "screen":
        inc = "random" in user.lower()
        return {"decision": "include" if inc else "exclude", "reason": "mock decision", "trial_name": None}
    abstract = user.split("ABSTRACT:", 1)[-1]
    outcomes = []
    m = re.search(r"([^.;]*?(\d+(?:\.\d+)?)\s?%[^.;]*)", abstract)
    if m:
        outcomes.append({"arm": "Arm A", "comparator": None, "population": "overall", "measure": "orr", "detail": None,
                         "value": float(m.group(2)), "unit": "percent", "ci_low": None, "ci_high": None,
                         "quote": m.group(1).strip()})
    return {"trial": {"acronym": None, "phase": "3", "line": "first", "biomarker_selection": None,
                      "n_randomized_total": None, "primary_endpoint": None},
            "arms": [{"label": "Arm A", "regimen": "unknown"}], "outcomes": outcomes}
