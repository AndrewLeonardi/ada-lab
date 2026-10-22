"""Third reading (dataset protocol section 8): when the two extraction passes disagree, a stronger model settles it.

For each published trial with numbers held back only because the passes disagreed (every other check passes),
one request shows the abstract and the disputed numbers. The model judges each one correct, wrong or unclear,
with a reason. It cannot add numbers or change values: a confirmed number still has to pass every code check,
and verification then counts it as agreed. Verdicts are stored in the adjudications table.
Runs in half-price batches after the extraction backlog, within the daily budget.
"""

from __future__ import annotations

import json
import time

from .extract import COMMON

MODEL = "claude-opus-5-5"
PROMPT_VERSION = "adjudicate-v1"
BATCH_SIZE = 30
EST_USD = 0.03 * 0.5 * 1.25  # per trial: Opus at half price, plus a margin

SYSTEM = """You are the third, independent reader for an open dataset of randomized trials in metastatic \
colorectal cancer. Two earlier readings of this abstract disagreed about the numbers listed below. Judge each \
listed number from the abstract alone:
- "correct": the abstract states this value for this arm, this measure and this population, as described \
(including the comparator and direction of a hazard ratio);
- "wrong": anything is off (another arm, measure, population or time point; a hazard ratio the other way round; \
a count that is not of randomized patients; a value that is not of this kind);
- "unclear": the abstract does not let you decide.
Give a one-sentence reason for each. The definitions the dataset uses:

""" + COMMON.split("Measures (use these names):", 1)[1]

SCHEMA = {
    "type": "object",
    "properties": {"verdicts": {"type": "array", "items": {
        "type": "object",
        "properties": {"id": {"type": "string"}, "verdict": {"type": "string", "enum": ["correct", "wrong", "unclear"]},
                       "reason": {"type": "string"}},
        "required": ["id", "verdict", "reason"], "additionalProperties": False}}},
    "required": ["verdicts"], "additionalProperties": False,
}


def disputed(con) -> dict[str, list[dict]]:
    """Published trials' numbers held back only by the passes' disagreement, not yet adjudicated or audited."""
    out = {}
    for r in con.execute(
            "SELECT r.* FROM records r JOIN screenings s ON s.pmid = r.pmid AND s.id = (SELECT MAX(id) FROM screenings "
            "WHERE pmid = r.pmid) WHERE s.decision = 'include' AND r.status = 'needs_review' "
            "AND r.id NOT IN (SELECT record_id FROM adjudications) ORDER BY r.pmid, r.id"):
        ch = json.loads(r["checks"] or "{}")
        failed = [k for k, v in ch.items() if v is False]
        if failed == ["second_pass_agrees"] and "audit" not in ch:
            out.setdefault(r["pmid"], []).append({**dict(r), "checks": ch})
    return out


def request(con, pmid: str, records: list[dict]) -> dict:
    p = con.execute("SELECT title, abstract FROM papers WHERE pmid=?", (pmid,)).fetchone()
    lines = []
    for i, r in enumerate(records, 1):
        ci = f" (95% CI {r['ci_low']}-{r['ci_high']})" if r["ci_low"] is not None else ""
        vs = f" versus {r['comparator']}" if r["comparator"] else ""
        detail = f"; {r['checks'].get('detail')}" if r["checks"].get("detail") else ""
        lines.append(f"N{i}: arm \"{r['arm']}\"{vs}; measure {r['measure']}{detail}; population "
                     f"{r['checks'].get('population') or 'overall'}; value {r['value']:g} {r['unit']}{ci}; "
                     f"source sentence: \"{r['quote']}\"")
    user = f"TITLE: {p['title']}\nABSTRACT:\n{p['abstract']}\n\nNUMBERS TO JUDGE:\n" + "\n".join(lines)
    return {"stage": "adjudicate", "model": MODEL, "system": SYSTEM, "user": user, "schema": SCHEMA, "effort": "low",
            "max_tokens": 8000}


def store(con, pmid: str, records: list[dict], result: dict | None):
    """Save the verdicts (missing or failed answers become 'unclear', so they are not asked again)."""
    by = {v["id"]: v for v in (result or {}).get("verdicts", [])}
    for i, r in enumerate(records, 1):
        v = by.get(f"N{i}", {"verdict": "unclear", "reason": "no answer from the third reading"})
        con.execute("INSERT OR REPLACE INTO adjudications(record_id, verdict, reason, model, prompt_version, at) "
                    "VALUES(?,?,?,?,?,?)", (r["id"], v["verdict"], v["reason"][:500], MODEL, PROMPT_VERSION, time.time()))
    con.commit()
