"""Stage 1, screening: is this paper the primary report of a randomized trial in metastatic CRC?"""

from __future__ import annotations

import json
import re
import time

from . import db

PROMPT_VERSION = "screen-v3"  # v2: checklist enforced by code (spot check 1); v3: anal cancer is out (night shift)

SYSTEM = """You screen PubMed records for an open dataset of randomized controlled trials (RCTs) in \
metastatic colorectal cancer. Decide from the title and abstract only. Answer the checklist first, then decide.

Checklist:
- randomized: patients were randomly assigned between two or more arms (phase 2 or 3, any line, including \
maintenance and treatment-holiday strategies). Phase 1, single-arm and non-randomized studies: false.
- metastatic: the trial population has DISTANT metastases (stage IV), or recurrent or advanced disease that \
cannot be treated with curative intent. Resected or resectable liver or lung metastases with perioperative \
therapy count: true. Locally advanced colon or rectal cancer without distant metastases (neoadjuvant, \
chemoradiotherapy, total neoadjuvant therapy, surgery, adjuvant) is NOT metastatic: false, even when it is \
called "advanced", "high-risk" or "unresectable". Screening, polyps and early cancer: false. Anal canal cancer \
(including squamous cell carcinoma of the anus) is not colorectal cancer: false. A mixed-tumor trial counts only if \
colorectal results are reported separately.
- per_arm_efficacy: the abstract reports at least one efficacy outcome for each arm (response rate, PFS, OS, \
time to progression, disease-free or recurrence-free survival, or a hazard ratio). Protocols and designs \
without results: false.
- primary_report: this is the main results publication of one trial, not an updated survival report, \
subgroup, biomarker, quality-of-life or post hoc analysis, and not a review, meta-analysis or pooled \
analysis of several trials.

Decision: "include" only if all four are true. "secondary" for a publication of a randomized trial in \
metastatic colorectal cancer that is not its primary report. "uncertain" only when the abstract genuinely \
does not say. Otherwise "exclude"."""

CHECKS = ("randomized", "metastatic", "per_arm_efficacy", "primary_report")

SCHEMA = {
    "type": "object",
    "properties": {
        "population": {"type": "string", "description": "Who was randomized, in a few words."},
        **{c: {"type": "boolean"} for c in CHECKS},
        "reason": {"type": "string", "description": "One short sentence."},
        "decision": {"type": "string", "enum": ["include", "secondary", "exclude", "uncertain"]},
        "trial_name": {"type": ["string", "null"], "description": "Acronym or name if stated, else null."},
    },
    "required": ["population", *CHECKS, "reason", "decision", "trial_name"],
    "additionalProperties": False,
}


ANAL = re.compile(r"\banal (canal|cancer|carcinoma|squamous)|\bof the anus\b|\bscac\b", re.I)
COLORECTAL = re.compile(r"colorectal|\bcolon\b|\brectal\b|\bcrc\b", re.I)


def enforce(res: dict, text: str = "") -> dict:
    """The decision must follow the checklist (screening found includes whose own reasons said 'not metastatic').
    text (title and abstract): anal cancer is not colorectal cancer (the night shift found anal trials included)."""
    if res["decision"] == "include" and ANAL.search(text) and not COLORECTAL.search(text):
        res["decision"] = "exclude"
        res["reason"] = f"[excluded: anal cancer is not colorectal cancer] {res['reason']}"
    if res["decision"] == "include" and not all(res[c] for c in CHECKS):
        res["decision"] = "secondary" if res["randomized"] and res["metastatic"] and not res["primary_report"] else "exclude"
        res["reason"] = f"[downgraded by checklist] {res['reason']}"
    return res


def render(p: dict) -> str:
    return (f"PMID {p['pmid']} ({p.get('year')}, {p.get('journal')})\nPublication types: {p.get('pub_types')}\n"
            f"TITLE: {p['title']}\nABSTRACT:\n{p['abstract'] or '(no abstract)'}")


def screen_paper(con, claude, model: str, p: dict) -> dict:
    if not p.get("abstract"):
        res = {"decision": "exclude", "reason": "No abstract available.", "trial_name": None}
        usd = 0.0
    else:
        res, usd = claude.json(stage="screen", model=model, system=SYSTEM, user=render(p), schema=SCHEMA, effort="low",
                               max_tokens=500)
        res = enforce(res, f"{p['title']} {p['abstract']}")
    con.execute("INSERT INTO screenings(pmid, decision, reason, detail, model, prompt_version, usd, at) "
                "VALUES(?,?,?,?,?,?,?,?)",
                (p["pmid"], res["decision"], res["reason"], json.dumps(res), model, PROMPT_VERSION, usd, time.time()))
    con.commit()
    return res


def apply_rules(con) -> list[str]:
    """Re-apply the code rules to the latest "include" decisions, using the stored answers (free, no model call)."""
    changed = []
    for r in con.execute("SELECT s.*, p.title, p.abstract FROM screenings s JOIN papers p ON p.pmid = s.pmid WHERE "
                         "s.id IN (SELECT MAX(id) FROM screenings GROUP BY pmid) AND s.decision = 'include'").fetchall():
        res = json.loads(r["detail"])
        if not all(c in res for c in CHECKS):
            continue
        new = enforce(dict(res), f"{r['title']} {r['abstract']}")
        if new["decision"] != "include":
            con.execute("INSERT INTO screenings(pmid, decision, reason, detail, model, prompt_version, usd, at) "
                        "VALUES(?,?,?,?,?,?,?,?)", (r["pmid"], new["decision"], new["reason"], json.dumps(new), "rules",
                                                    f"{r['prompt_version']}+rules", 0.0, time.time()))
            changed.append(r["pmid"])
    con.commit()
    return changed
