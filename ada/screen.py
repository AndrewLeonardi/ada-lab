"""Stage 1, screening: is this paper the primary report of a randomized trial in metastatic CRC?"""

from __future__ import annotations

import json
import time

from . import db

PROMPT_VERSION = "screen-v1"

SYSTEM = """You screen PubMed records for an open dataset of randomized controlled trials (RCTs) in \
metastatic or advanced (unresectable) colorectal cancer. Decide from the title and abstract only.

INCLUDE when all hold:
- patients were randomly assigned between two or more treatment arms (phase 2 or 3, any line of therapy, \
including maintenance and treatment-holiday strategies);
- the population is metastatic or unresectable advanced colorectal cancer (a mixed-tumor trial counts only \
if colorectal results are reported separately);
- the abstract reports at least one efficacy outcome per arm (response rate, PFS, OS, time to progression, \
or a hazard ratio).

EXCLUDE: non-randomized or single-arm studies; adjuvant/neoadjuvant trials in non-metastatic disease \
(resectable liver metastases with perioperative therapy count as metastatic: include); meta-analyses, \
reviews, pooled analyses, protocols, editorials, cost studies; pure quality-of-life, pharmacokinetic or \
biomarker-only reports.

Use "secondary" for a randomized-trial publication that is not the main efficacy report (updated survival, \
subgroup or biomarker analysis of an RCT). Use "uncertain" only when the abstract genuinely does not say."""

SCHEMA = {
    "type": "object",
    "properties": {
        "decision": {"type": "string", "enum": ["include", "secondary", "exclude", "uncertain"]},
        "reason": {"type": "string", "description": "One short sentence."},
        "trial_name": {"type": ["string", "null"], "description": "Acronym or name if stated, else null."},
    },
    "required": ["decision", "reason", "trial_name"],
    "additionalProperties": False,
}


def render(p: dict) -> str:
    return (f"PMID {p['pmid']} ({p.get('year')}, {p.get('journal')})\nPublication types: {p.get('pub_types')}\n"
            f"TITLE: {p['title']}\nABSTRACT:\n{p['abstract'] or '(no abstract)'}")


def screen_paper(con, claude, model: str, p: dict) -> dict:
    if not p.get("abstract"):
        res = {"decision": "exclude", "reason": "No abstract available.", "trial_name": None}
        usd = 0.0
    else:
        res, usd = claude.json(stage="screen", model=model, system=SYSTEM, user=render(p), schema=SCHEMA, effort="low",
                               max_tokens=400)
    con.execute("INSERT INTO screenings(pmid, decision, reason, detail, model, prompt_version, usd, at) "
                "VALUES(?,?,?,?,?,?,?,?)",
                (p["pmid"], res["decision"], res["reason"], json.dumps(res), model, PROMPT_VERSION, usd, time.time()))
    con.commit()
    return res
