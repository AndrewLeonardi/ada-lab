"""Stage 2, extraction: arm-level outcomes, each with the exact sentence it came from.

Two independent passes with differently worded instructions (and optionally different models).
Nothing is computed or inferred: only numbers stated in the abstract, each with a verbatim quote.
"""

from __future__ import annotations

import json
import time

from . import db
from .screen import render

PROMPT_VERSION = "extract-v3"  # v2: non-standard time endpoints separated (audit 1); v3: counts, DCR, CIs (audit 2)

MEASURES = ["n_randomized", "orr", "dcr", "pfs_median", "ttp_median", "os_median", "other_time_median", "pfs_hr",
            "os_hr", "grade3plus_ae_rate"]

COMMON = """You extract data for an open, auditable dataset of randomized trials in metastatic colorectal \
cancer. Use ONLY the title and abstract given. Never compute, convert, round or infer a number: record a value \
only if the abstract states it.

For every value, "quote" must be copied EXACTLY, character for character, from the abstract: a short \
contiguous span (ideally one clause) that contains the number. A script will search for your quote in the \
abstract; a quote that is not found makes the record invalid.

Measures (use these names):
- n_randomized: patients randomly assigned to that arm (count). Counts of patients who were treated, received \
treatment, were evaluable, were analysed, were included in an analysis set, or had a biomarker tested are NOT \
randomized counts: do not record them. Record each arm's own count; never put the trial's total under an arm.
- orr: objective response rate (percent)
- dcr: disease control rate (percent), only when the abstract states it; a stable-disease percentage alone is not a \
disease control rate
- pfs_median / ttp_median / os_median: median progression-free survival / time to progression / overall \
survival, in the unit stated (months or weeks; a median given in days is not recorded). A survival rate at a time \
point ("10-month PFS was 59.9%") is not a median: do not record it. pfs_median means time from randomization to the FIRST progression \
or death, nothing else.
- other_time_median: any other median time-to-event endpoint, such as second progression-free survival (PFS2), PFS \
on treatment, time to treatment failure, time to strategy failure, or duration of disease control. Name the \
endpoint exactly in "detail".
- pfs_hr / os_hr: hazard ratio of this arm versus the comparator arm; put the comparator's label in \
"comparator" (unit "ratio"). "arm" is the group in the numerator: a ratio below 1 means "arm" did better. Check the \
direction against the reported medians: if the medians favour one group, a ratio below 1 belongs to that group as \
"arm" (abstracts often report control versus experimental)
- grade3plus_ae_rate: percent of patients with grade 3 or worse adverse events, overall or for a named event \
(name it in "detail")
Include 95% confidence limits only when stated (otherwise null; never record an 80% or 90% interval). Record only \
exact values: a value given as a bound ("<0.5%", ">20 months") is not recorded. If the abstract reports a subgroup (for \
example KRAS wild-type), put it in "population"; use "overall" for the full trial population."""

PASS_INSTRUCTIONS = {
    1: "Work arm by arm: first list the arms, then every stated outcome for each arm.",
    2: "Work outcome by outcome: go through the results sentence by sentence and record every number that belongs "
       "to one of the measures, then attach it to its arm.",
}

SCHEMA = {
    "type": "object",
    "properties": {
        "trial": {
            "type": "object",
            "properties": {
                "acronym": {"type": ["string", "null"]},
                "phase": {"type": "string", "enum": ["2", "3", "2/3", "unclear"]},
                "line": {"type": "string", "enum": ["first", "second", "third_or_later", "maintenance",
                                                     "mixed", "unclear"]},
                "biomarker_selection": {"type": ["string", "null"],
                                        "description": "e.g. 'KRAS exon 2 wild-type', or null if unselected"},
                "n_randomized_total": {"type": ["integer", "null"]},
                "primary_endpoint": {"type": ["string", "null"]},
            },
            "required": ["acronym", "phase", "line", "biomarker_selection", "n_randomized_total", "primary_endpoint"],
            "additionalProperties": False,
        },
        "arms": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"label": {"type": "string"}, "regimen": {"type": "string"}},
                "required": ["label", "regimen"],
                "additionalProperties": False,
            },
        },
        "outcomes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "arm": {"type": "string"},
                    "comparator": {"type": ["string", "null"]},
                    "population": {"type": "string"},
                    "measure": {"type": "string", "enum": MEASURES},
                    "detail": {"type": ["string", "null"]},
                    "value": {"type": "number"},
                    "unit": {"type": "string", "enum": ["count", "percent", "months", "weeks", "ratio"]},
                    "ci_low": {"type": ["number", "null"]},
                    "ci_high": {"type": ["number", "null"]},
                    "quote": {"type": "string"},
                },
                "required": ["arm", "comparator", "population", "measure", "detail", "value", "unit", "ci_low",
                             "ci_high", "quote"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["trial", "arms", "outcomes"],
    "additionalProperties": False,
}


def request(model: str, p: dict, pass_no: int) -> dict:
    """The extraction request for one pass, as used directly or in a batch."""
    return {"stage": f"extract{pass_no}", "model": model, "system": COMMON + "\n\n" + PASS_INSTRUCTIONS[pass_no],
            "user": render(p), "schema": SCHEMA, "effort": "low", "max_tokens": 6000}


def record(con, pmid: str, pass_no: int, model: str, res: dict, usd: float):
    con.execute("INSERT INTO extractions(pmid, pass, model, prompt_version, result, usd, at) VALUES(?,?,?,?,?,?,?)",
                (pmid, pass_no, model, PROMPT_VERSION, json.dumps(res), usd, time.time()))
    con.commit()


def extract_paper(con, claude, model: str, p: dict, pass_no: int) -> dict:
    res, usd = claude.json(**request(model, p, pass_no))
    record(con, p["pmid"], pass_no, model, res, usd)
    return res
