"""ClinicalTrials.gov, for free: the missing-results tracker and the paper-versus-registry check.

Every randomized phase 2/3 trial in metastatic colorectal cancer registered on ClinicalTrials.gov is kept here.

1. Missing results. For each trial that finished (completed or stopped, with patients) at least two years
   ago, where are its results? In order: posted on the registry; a results publication linked in the registry;
   a PubMed record citing its registration number; a PubMed paper found by searching for the trial and
   confirmed by a model that reads both (the only paid step, a fraction of a cent). If none: missing.
   Searched again every month, since results can appear late.
2. Paper vs registry. For trials in Ada's dataset whose results are posted, code compares the published
   abstract with the registry: the registered primary outcome, the number of patients, and her verified
   numbers against the registry's results tables. Differences go to the auditor (some have good reasons,
   such as a later data cut-off).
"""

from __future__ import annotations

import json
import re
import time
import urllib.parse
from datetime import date

from . import db, sources

CT = "https://clinicaltrials.gov/api/v2/studies"
QUERY = {
    "query.cond": "metastatic colorectal cancer",
    "filter.advanced": "AREA[StudyType]INTERVENTIONAL AND AREA[DesignAllocation]RANDOMIZED AND AREA[Phase](PHASE2 OR PHASE3)",
}
FINISHED = ("COMPLETED", "TERMINATED")
DUE_MONTHS = 24  # results are looked for once a trial finished at least this long ago
RESEARCH_DAYS = 30  # trials without findable results are searched again after this

# endpoint families, for comparing a registered outcome with a published one
ENDPOINTS = [
    ("os", r"overall survival|\bos\b"), ("pfs", r"progression[- ]free|\bpfs\b"),
    ("orr", r"response rate|objective response|overall response|\borr\b"), ("dcr", r"disease control|\bdcr\b"),
    ("dfs", r"disease[- ]free|relapse[- ]free|recurrence[- ]free|event[- ]free|failure[- ]free|\b(dfs|rfs|efs|ffs)\b"),
    ("ttp", r"time to (tumou?r )?progression|\bttp\b"), ("duration", r"duration of (disease control|response)|\bddc\b"),
    ("safety", r"adverse|toxicit|safety|tolerab|dose[- ]limiting"), ("qol", r"quality of life|\bqol\b"),
    ("resection", r"resection|r0"),
]
MEASURE_FAMILY = {"os_median": "os", "os_hr": "os", "pfs_median": "pfs", "pfs_hr": "pfs", "orr": "orr"}


def families(text: str | None) -> set[str]:
    t = (text or "").lower()
    return {name for name, rx in ENDPOINTS if re.search(rx, t)}


def _months_ago(d: str | None) -> float | None:
    if not d or not d[:4].isdigit():
        return None
    y, m = int(d[:4]), int(d[5:7]) if len(d) >= 7 else 6
    today = date.today()
    return (today.year - y) * 12 + today.month - m


def _row(study: dict) -> dict:
    ps = study.get("protocolSection", {})
    ident, status = ps.get("identificationModule", {}), ps.get("statusModule", {})
    sponsor = ps.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {})
    design = ps.get("designModule", {})
    refs = [{"pmid": r.get("pmid"), "type": r.get("type")} for r in ps.get("referencesModule", {}).get("references", [])]
    return {"nct": ident.get("nctId"), "title": ident.get("officialTitle") or ident.get("briefTitle"),
            "acronym": ident.get("acronym"), "status": status.get("overallStatus"),
            "phase": "/".join(design.get("phases", [])), "sponsor": sponsor.get("name"), "sponsor_class": sponsor.get("class"),
            "enrollment": design.get("enrollmentInfo", {}).get("count"),
            "primary_completion": status.get("primaryCompletionDateStruct", {}).get("date"),
            "completion": status.get("completionDateStruct", {}).get("date"),
            "has_results": int(bool(study.get("hasResults"))), "refs": json.dumps(refs)}


def sync(con) -> int:
    """Fetch every matching registry record (a few pages; free). Full results are fetched later, per trial."""
    token, n = None, 0
    while True:
        q = dict(QUERY, pageSize="200", format="json", fields="protocolSection,hasResults",
                 **({"pageToken": token} if token else {}))
        page = json.loads(sources._get(CT + "?" + urllib.parse.urlencode(q), timeout=60))
        for s in page.get("studies", []):
            r = _row(s)
            con.execute(
                "INSERT INTO registry(nct, title, acronym, status, phase, sponsor, sponsor_class, enrollment, "
                "primary_completion, completion, has_results, refs, data, fetched_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?) "
                "ON CONFLICT(nct) DO UPDATE SET title=excluded.title, acronym=excluded.acronym, status=excluded.status, "
                "phase=excluded.phase, sponsor=excluded.sponsor, sponsor_class=excluded.sponsor_class, "
                "enrollment=excluded.enrollment, primary_completion=excluded.primary_completion, "
                "completion=excluded.completion, has_results=excluded.has_results, refs=excluded.refs, "
                # keep a stored copy that includes the results tables (fetched per trial by crosscheck_step)
                "data=CASE WHEN registry.data LIKE '%\"resultsSection\"%' THEN registry.data ELSE excluded.data END, "
                "fetched_at=excluded.fetched_at",
                (*r.values(), json.dumps(s), time.time()))
            n += 1
        con.commit()
        token = page.get("nextPageToken")
        if not token:
            return n


def due(con) -> list[dict]:
    """Finished trials whose results should be public by now."""
    out = []
    for r in con.execute("SELECT * FROM registry WHERE status IN (?, ?)", FINISHED):
        months = _months_ago(r["primary_completion"] or r["completion"])
        if months is not None and months >= DUE_MONTHS and (r["enrollment"] or 0) > 0:
            out.append({**dict(r), "months": months})
    return out


# ------------------------------------------------------------------ 1. where are the results?
CONFIRM_SYSTEM = """You check whether a journal article reports the results of a specific registered clinical \
trial. Compare the registry record with the article: interventions, disease and setting, design, size, sponsor or \
investigators, and dates. Answer "yes" only if the article reports results (main or secondary) of this exact trial, \
"no" if it is a different trial or only a protocol, and "unclear" if you cannot tell."""
CONFIRM_SCHEMA = {"type": "object", "properties": {"match": {"type": "string", "enum": ["yes", "no", "unclear"]},
                                                   "reason": {"type": "string"}},
                  "required": ["match", "reason"], "additionalProperties": False}
PROTOCOL = re.compile(r"protocol|study design|rationale and design|trial in progress", re.I)


def _interventions(trial: dict) -> list[str]:
    arms = json.loads(trial["data"] or "{}").get("protocolSection", {}).get("armsInterventionsModule", {})
    return [i.get("name", "") for i in arms.get("interventions", []) if i.get("name")]


def _candidates(trial: dict) -> list[str]:
    """PubMed records that might be this trial's results paper, found without its registration number."""
    year = (trial["primary_completion"] or trial["completion"] or "2000")[:4]
    since = f'("{int(year) - 1}"[dp] : "3000"[dp])'
    queries = []
    if trial["acronym"] and len(trial["acronym"]) >= 3:
        queries.append(f'"{trial["acronym"]}"[tiab] AND (colorectal[tiab] OR colon[tiab] OR rectal[tiab])')
    drugs = [w for w in _interventions(trial) if len(w) > 3][:3]
    if drugs:
        queries.append("(" + " AND ".join(f'"{d}"[tiab]' for d in drugs) + ") AND (colorectal[tiab] OR colon[tiab]) "
                       "AND random*[tiab] AND " + since)
    found = []
    for q in queries:
        _, ids = sources.search(q, retmax=5)
        found += [i for i in ids if i not in found]
    return found[:6]


def _registry_card(trial: dict) -> str:
    return (f"Registry {trial['nct']}: {trial['title']} (acronym {trial['acronym'] or 'none'}). Sponsor: {trial['sponsor']}. "
            f"Phase {trial['phase']}, {trial['enrollment']} patients, status {trial['status']}, primary completion "
            f"{trial['primary_completion']}. Interventions: {', '.join(_interventions(trial)) or 'not listed'}.")


def find_results(con, trial: dict, claude=None, model: str = "claude-haiku-5-5") -> dict:
    refs = json.loads(trial["refs"] or "[]")
    if trial["has_results"]:
        return {"verdict": "posted", "pmids": [], "detail": "Results posted on ClinicalTrials.gov."}
    linked = [r["pmid"] for r in refs if r.get("type") == "RESULT" and r.get("pmid")]
    if linked:
        return {"verdict": "linked", "pmids": linked, "detail": "Results publication linked in the registry."}
    _, ids = sources.search(f"{trial['nct']}[si] OR {trial['nct']}[tiab]", retmax=20)
    papers = sources.fetch(ids) if ids else []
    reports = [p["pmid"] for p in papers if not PROTOCOL.search(p["title"] or "")
               and "Clinical Trial Protocol" not in (p.get("pub_types") or [])]
    if reports:
        return {"verdict": "found_by_number", "pmids": reports, "detail": "PubMed records cite its registration number."}
    cands = [c for c in _candidates(trial) if c not in ids]
    if not cands:
        return {"verdict": "not_found", "pmids": [], "detail": "No posted results, no linked or citing publication, "
                "and no candidate paper in PubMed."}
    if claude is None:
        return {"verdict": "pending", "pmids": [], "candidates": cands, "detail": "Candidate papers await checking."}
    yes, unclear = [], []
    for p in sources.fetch(cands):
        res, _ = claude.json(stage="registry_match", model=model, system=CONFIRM_SYSTEM,
                             user=f"{_registry_card(trial)}\n\nARTICLE (PMID {p['pmid']}, {p['year']}, {p['journal']}):\n"
                                  f"{p['title']}\n{p['abstract'] or '(no abstract)'}", schema=CONFIRM_SCHEMA, max_tokens=400)
        (yes if res["match"] == "yes" else unclear if res["match"] == "unclear" else []).append(p["pmid"])
    if yes:
        return {"verdict": "found_by_search", "pmids": yes, "candidates": cands,
                "detail": "Found by searching PubMed; a model confirmed the paper matches the registry record."}
    if unclear:
        return {"verdict": "unclear", "pmids": unclear, "candidates": cands, "detail": "Possible match, needs a human look."}
    return {"verdict": "not_found", "pmids": [], "candidates": cands,
            "detail": "No posted results or linked publication; candidate papers in PubMed were other trials."}


def search_step(con, claude=None, limit: int = 4, on_trial=None) -> int:
    """Look for the results of up to ``limit`` due trials not searched yet (or not found, a month ago)."""
    known = {r["nct"]: r for r in con.execute("SELECT * FROM result_search")}
    todo = []
    for t in sorted(due(con), key=lambda t: -t["months"]):
        k = known.get(t["nct"])
        if k is None or (k["verdict"] in ("not_found", "unclear", "pending")
                         and time.time() - (k["searched_at"] or 0) > RESEARCH_DAYS * 86400
                         or k["verdict"] == "pending" and claude is not None):
            todo.append(t)
    for t in todo[:limit]:
        if on_trial:
            on_trial(t)
        r = find_results(con, t, claude)
        con.execute("INSERT OR REPLACE INTO result_search(nct, verdict, pmids, detail, candidates, searched_at) "
                    "VALUES(?,?,?,?,?,?)", (t["nct"], r["verdict"], json.dumps(r["pmids"]), r["detail"],
                                            json.dumps(r.get("candidates", [])), time.time()))
        con.commit()
    return min(limit, len(todo))


# ------------------------------------------------------------------ 2. paper vs registry
def _num(s) -> float | None:
    try:
        return float(str(s).replace(",", ""))
    except (TypeError, ValueError):
        return None


TO_MONTHS = {"month": 1.0, "week": 12 / 52.18, "day": 12 / 365.25}


def _unit_factor(unit: str | None) -> float | None:
    u = (unit or "").lower()
    return next((f for k, f in TO_MONTHS.items() if k in u), None)


def registry_values(study: dict, family: str, kind: str) -> list[tuple[float, str]]:
    """Numbers the registry reports for an endpoint family. kind: "median" (in months), "percent", or "hr"."""
    out = []
    for om in study.get("resultsSection", {}).get("outcomeMeasuresModule", {}).get("outcomeMeasures", []):
        if family not in families(om.get("title")):
            continue
        label = om.get("title", "")[:120]
        if kind == "hr":
            for a in om.get("analyses", []) or []:
                if "hazard" in (a.get("paramType") or "").lower() and _num(a.get("paramValue")) is not None:
                    out.append((_num(a["paramValue"]), label))
            continue
        unit = (om.get("unitOfMeasure") or "").lower()
        if kind == "median" and (om.get("paramType") or "").upper() == "MEDIAN" and _unit_factor(unit):
            f = _unit_factor(unit)
        elif kind == "percent" and "percent" in unit:
            f = 1.0
        else:
            continue
        for c in om.get("classes", []) or []:
            for cat in c.get("categories", []) or []:
                for m in cat.get("measurements", []) or []:
                    v = _num(m.get("value"))
                    if v is not None:
                        out.append((round(v * f, 3), label))
    return out


def compare(trial: dict, records: list[dict], study: dict) -> list[dict]:
    """trial: Ada's trial row (primary_endpoint, n_randomized); records: her verified numbers; study: full registry JSON."""
    ps = study.get("protocolSection", {})
    checks = []
    registered = [o.get("measure", "") for o in ps.get("outcomesModule", {}).get("primaryOutcomes", [])]
    reg_f, pub_f = set().union(*(families(m) for m in registered)) if registered else set(), families(trial.get("primary_endpoint"))
    if reg_f and pub_f:
        same = bool(reg_f & pub_f)
        checks.append({"check": "primary_endpoint", "verdict": "agrees" if same else "differs",
                       "detail": f"Registered primary outcome: {'; '.join(registered)[:300]}. "
                                 f"Primary endpoint in the abstract: {trial.get('primary_endpoint')}."})
    enrolled = ps.get("designModule", {}).get("enrollmentInfo", {}).get("count")
    n = trial.get("n_randomized")
    if enrolled and n:
        close = abs(enrolled - n) <= 0.1 * max(enrolled, n)
        checks.append({"check": "patients", "verdict": "agrees" if close else "differs",
                       "detail": f"Registry: {enrolled} enrolled. Abstract: {n} randomized."})
    for r in records:
        fam = MEASURE_FAMILY.get(r["measure"])
        if not fam:
            continue
        kind = "hr" if r["measure"].endswith("_hr") else "percent" if r["measure"] == "orr" else "median"
        reg = registry_values(study, fam, kind)
        if not reg:
            continue
        value = r["value"] * (1.0 if kind != "median" else (_unit_factor(r["unit"]) or 1.0))
        tol = 0.051 if kind != "median" or r["unit"] == "months" else max(0.06, 0.03 * value)
        # a hazard ratio may be registered the other way round (B vs A): 1/HR then matches
        match = any(abs(v - value) <= tol or (kind == "hr" and v > 0 and abs(1 / v - value) <= 0.012) for v, _ in reg)
        checks.append({"check": r["measure"], "verdict": "agrees" if match else "differs", "record": r["id"],
                       "detail": f"Abstract: {r['value']:g} {r['unit']} ({r['arm']}). Registry values for "
                                 f"{reg[0][1]}: {', '.join(f'{v:g}' for v, _ in reg[:6])}."})
    return checks


def crosscheck_step(con, limit: int = 3, on_trial=None) -> int:
    """Compare up to ``limit`` of Ada's trials (with registry results) that have not been compared yet."""
    done = {r[0] for r in con.execute("SELECT DISTINCT pmid FROM registry_checks")}
    todo = []
    for p in con.execute("SELECT p.pmid, p.nct_ids FROM papers p JOIN trials t ON t.pmid = p.pmid JOIN screenings s "
                         "ON s.pmid = p.pmid AND s.id = (SELECT MAX(id) FROM screenings WHERE pmid = p.pmid) "
                         "WHERE s.decision = 'include'"):
        if p["pmid"] in done:
            continue
        for nct in json.loads(p["nct_ids"] or "[]"):
            reg = con.execute("SELECT * FROM registry WHERE nct=?", (nct,)).fetchone()
            if reg and reg["has_results"]:
                todo.append((p["pmid"], nct))
                break
    for pmid, nct in todo[:limit]:
        if on_trial:
            on_trial(pmid, nct)
        study = json.loads(sources._get(f"{CT}/{nct}?format=json", timeout=60))
        con.execute("UPDATE registry SET data=? WHERE nct=?", (json.dumps(study), nct))
        trial = dict(con.execute("SELECT * FROM trials WHERE pmid=?", (pmid,)).fetchone())
        records = [dict(r) for r in con.execute(
            "SELECT * FROM records WHERE pmid=? AND status IN ('verified','corrected')", (pmid,))]
        for c in compare(trial, records, study) or [{"check": "none", "verdict": "not_comparable",
                                                     "detail": "Nothing comparable in the registry results."}]:
            con.execute("INSERT INTO registry_checks(pmid, nct, check_name, verdict, detail, at) VALUES(?,?,?,?,?,?)",
                        (pmid, nct, c["check"], c["verdict"], c["detail"], time.time()))
        con.commit()
    return min(limit, len(todo))
