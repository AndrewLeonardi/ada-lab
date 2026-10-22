"""The hypothesis ledger: run each registered hypothesis's prespecified test (research/hypotheses/).

    ada hypotheses                      run every test now and print the results
    ada hypothesis-sample H001 [--n 30] draw the fixed-seed sample for hand verification (prints YAML)

A hypothesis file is never edited after registration; each result records the hash of the file it was tested
against. Tests are code: a language model never decides whether a hypothesis is supported. Results (with their
history) are kept in data/hypotheses.json and published on the website, failures included.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import random
import time

import yaml

from . import db
from .registry import crosscheck_todo, due
from .stats import fisher_exact, newcombe_diff, wilson

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC_DIR = ROOT / "research" / "hypotheses"
VERIFY_DIR = SPEC_DIR / "verification"
RESULTS = db.DATA_DIR / "hypotheses.json"
NO_RESULTS = ("not_found", "unclear")
FDAAA_RULE = "2017-01-18"


def load_specs() -> list[dict]:
    out = []
    for p in sorted(SPEC_DIR.glob("H*.yaml")):
        text = p.read_text()
        out.append({**yaml.safe_load(text), "file": f"research/hypotheses/{p.name}",
                    "spec_hash": hashlib.sha256(text.encode()).hexdigest()[:16]})
    return out


def _verification(hid: str) -> list[dict] | None:
    p = VERIFY_DIR / f"{hid}.yaml"
    return yaml.safe_load(p.read_text()).get("items", []) if p.exists() else None


def _pct(x: float) -> str:
    return f"{100 * x:.1f}%"


# ------------------------------------------------------------------ the pool shared by H001-H003
def _searched_pool(con) -> tuple[list[dict], int]:
    """Eligible finished trials with their verdict, and how many are still pending or unsearched."""
    verdicts = {r["nct"]: r["verdict"] for r in con.execute("SELECT nct, verdict FROM result_search")}
    trials = [{**t, "verdict": verdicts.get(t["nct"], "not_searched")} for t in due(con)]
    unresolved = sum(t["verdict"] in ("pending", "not_searched") for t in trials)
    return trials, unresolved


def _waiting(why: str, **numbers) -> dict:
    return {"status": "waiting", "summary": f"Waiting: {why}", "numbers": numbers}


def h001(con, spec) -> dict:
    trials, unresolved = _searched_pool(con)
    if unresolved:
        return _waiting(f"{unresolved} of {len(trials)} finished trials still pending or unsearched.",
                        eligible=len(trials), unresolved=unresolved)
    n, k = len(trials), sum(t["verdict"] in NO_RESULTS for t in trials)
    if not n:
        return _waiting("no eligible trials yet (the registry has not been synced).")
    p_auto, a_lo, a_hi = wilson(k, n)
    sample = _verification("H001")
    if sample is None:
        return _waiting(f"automated search done ({k} of {n} trials, {_pct(p_auto)}, with no results found); "
                        "the hand-checked sample has not been drawn yet.", eligible=n, no_results_found=k)
    judged = [s for s in sample if s.get("verdict") in ("truly_missing", "found_elsewhere", "unclear")]
    if len(judged) < len(sample) or not sample:
        return _waiting(f"auditor has judged {len(judged)} of {len(sample)} sampled trials.", eligible=n,
                        no_results_found=k)
    m = sum(s["verdict"] == "truly_missing" for s in judged)  # unclear counts as found (conservative)
    ppv, v_lo, v_hi = wilson(m, len(judged))
    est, lo, hi = p_auto * ppv, a_lo * v_lo, a_hi * v_hi
    status = "supported" if lo >= 0.10 else "refuted" if hi < 0.10 else "inconclusive"
    return {"status": status,
            "summary": f"An estimated {_pct(est)} of finished trials have no public results "
                       f"(95% bounds {_pct(lo)} to {_pct(hi)}): {k} of {n} had none found automatically, and "
                       f"{m} of {len(judged)} hand-checked were truly missing.",
            "numbers": {"eligible": n, "no_results_found": k, "p_auto": [p_auto, a_lo, a_hi], "sample": len(judged),
                        "truly_missing": m, "ppv": [ppv, v_lo, v_hi], "estimate": [est, lo, hi]}}


def _two_groups(con, split) -> tuple[dict, dict] | None:
    trials, unresolved = _searched_pool(con)
    if unresolved:
        return None
    g = {True: [0, 0], False: [0, 0]}  # group -> [no results, total]
    for t in trials:
        key = split(t)
        if key is None:
            continue
        g[key][0] += t["verdict"] in NO_RESULTS
        g[key][1] += 1
    return {"k": g[True][0], "n": g[True][1]}, {"k": g[False][0], "n": g[False][1]}


def _compare_summary(name1, a, name2, b) -> dict:
    p1, p2 = wilson(a["k"], a["n"]), wilson(b["k"], b["n"])
    d = newcombe_diff(a["k"], a["n"], b["k"], b["n"])
    return {"groups": {name1: {**a, "share": list(p1)}, name2: {**b, "share": list(p2)}}, "difference": list(d)}


def h002(con, spec) -> dict:
    def after(t):
        d = t["primary_completion"] or t["completion"]
        return None if not d else (d if len(d) > 7 else d + "-28") >= FDAAA_RULE
    groups = _two_groups(con, after)
    if groups is None:
        return _waiting("the automated search still has trials pending or unsearched.")
    later, earlier = groups
    if not (later["n"] and earlier["n"]):
        return _waiting("one of the two groups has no trials yet.")
    num = _compare_summary("completed on/after 2017-01-18", later, "completed before", earlier)
    p_less = fisher_exact(later["k"], later["n"] - later["k"], earlier["k"], earlier["n"] - earlier["k"], "less")
    p_more = fisher_exact(later["k"], later["n"] - later["k"], earlier["k"], earlier["n"] - earlier["k"], "greater")
    status = "supported" if p_less < 0.05 else "refuted" if p_more < 0.05 else "not_supported"
    num.update(p_one_sided=p_less, p_opposite=p_more)
    return {"status": status, "numbers": num,
            "summary": f"No results found for {_pct(later['k'] / max(1, later['n']))} of trials completed since the 2017 "
                       f"rule ({later['k']}/{later['n']}) vs {_pct(earlier['k'] / max(1, earlier['n']))} before "
                       f"({earlier['k']}/{earlier['n']}); one-sided p = {p_less:.3g}."}


def h003(con, spec) -> dict:
    groups = _two_groups(con, lambda t: t["sponsor_class"] == "INDUSTRY")
    if groups is None:
        return _waiting("the automated search still has trials pending or unsearched.")
    ind, other = groups
    if not (ind["n"] and other["n"]):
        return _waiting("one of the two groups has no trials yet.")
    num = _compare_summary("industry", ind, "other sponsors", other)
    p = fisher_exact(ind["k"], ind["n"] - ind["k"], other["k"], other["n"] - other["k"])
    num.update(p_two_sided=p)
    s1, s2 = ind["k"] / max(1, ind["n"]), other["k"] / max(1, other["n"])
    status = "supported" if p < 0.05 else "not_supported"
    direction = "" if status != "supported" else (" Industry trials more often have no results." if s1 > s2
                                                  else " Industry trials less often have no results.")
    return {"status": status, "numbers": num,
            "summary": f"No results found for {_pct(s1)} of industry trials ({ind['k']}/{ind['n']}) vs {_pct(s2)} of "
                       f"others ({other['k']}/{other['n']}); two-sided p = {p:.3g}.{direction}"}


def h004(con, spec) -> dict:
    todo = crosscheck_todo(con)
    if todo:
        return _waiting(f"{len(todo)} trials still to compare with their registry record.")
    rows = [dict(r) for r in con.execute("SELECT pmid, verdict FROM registry_checks WHERE check_name='primary_endpoint'")]
    n = len(rows)
    if not n:
        return _waiting("no trial has been compared with its registry record yet.")
    flagged = sorted({r["pmid"] for r in rows if r["verdict"] == "differs"})
    sample = {s["pmid"]: s for s in (_verification("H004") or [])}
    unjudged = [p for p in flagged if sample.get(p, {}).get("verdict") not in ("confirmed_switch", "explained", "not_a_switch")]
    if unjudged:
        return _waiting(f"the auditor has to check {len(unjudged)} of {len(flagged)} flagged trials "
                        f"({n} trials compared).", compared=n, flagged=len(flagged))
    k = sum(sample[p]["verdict"] == "confirmed_switch" for p in flagged)
    p, lo, hi = wilson(k, n)
    status = "supported" if lo >= 0.05 else "refuted" if hi < 0.05 else "inconclusive"
    return {"status": status, "numbers": {"compared": n, "flagged": len(flagged), "confirmed": k, "share": [p, lo, hi]},
            "summary": f"{k} of {n} trials ({_pct(p)}, 95% CI {_pct(lo)} to {_pct(hi)}) report a different primary "
                       f"endpoint than they registered "
                       + (f"({len(flagged)} flagged by code, each checked by the auditor)." if flagged
                          else "(code flagged none).")}


TESTS = {"h001": h001, "h002": h002, "h003": h003, "h004": h004}


def run_all(con) -> list[dict]:
    """Run every test; keep the history of results that changed. Returns the latest results."""
    old = json.loads(RESULTS.read_text()) if RESULTS.exists() else {}
    out, latest = {}, []
    for spec in load_specs():
        res = TESTS[spec["test_function"]](con, spec)
        res.update(id=spec["id"], spec_hash=spec["spec_hash"], tested=time.strftime("%Y-%m-%d"))
        prev = old.get(spec["id"], {})
        history = prev.get("history", [])
        last = prev.get("latest")
        if last and (last["status"], last.get("summary")) != (res["status"], res.get("summary")):
            history = history + [last]
        out[spec["id"]] = {"latest": res, "history": history[-20:]}
        latest.append(res)
    RESULTS.write_text(json.dumps(out, indent=1))
    return latest


def changed(before: dict, after: list[dict]) -> list[dict]:
    return [r for r in after if before.get(r["id"], {}).get("latest", {}).get("status") != r["status"]]


def sample_yaml(con, hid: str, n: int = 30) -> str:
    """Draw the fixed-seed sample to verify by hand, as a YAML file for research/hypotheses/verification/."""
    if hid == "H001":
        trials, unresolved = _searched_pool(con)
        if unresolved:  # the pool must be final before the sample is drawn
            raise SystemExit(f"H001: {unresolved} trials still pending or unsearched; draw the sample after they resolve")
        pool = sorted(t["nct"] for t in trials if t["verdict"] in NO_RESULTS)
        picked = sorted(random.Random("H001-v1").sample(pool, min(n, len(pool))))
        reg = {r["nct"]: r for r in con.execute("SELECT nct, acronym, title, sponsor, primary_completion FROM registry")}
        items = [{"nct": c, "trial": reg[c]["acronym"] or (reg[c]["title"] or "")[:90], "sponsor": reg[c]["sponsor"],
                  "completed": reg[c]["primary_completion"], "verdict": None, "where": None, "note": None} for c in picked]
        head = (f"# H001 verification sample: {len(picked)} of {len(pool)} trials with no results found, drawn with seed "
                f"H001-v1 on {time.strftime('%Y-%m-%d')}.\n# verdict: truly_missing | found_elsewhere | unclear; "
                "where: the source if found (PMID, DOI, URL, conference).\n")
    elif hid == "H004":
        flagged = sorted({r[0] for r in con.execute(
            "SELECT pmid FROM registry_checks WHERE check_name='primary_endpoint' AND verdict='differs'")})
        items = [{"pmid": p, "verdict": None, "note": None} for p in flagged]
        head = ("# H004 verification: every trial whose abstract's primary endpoint differs from its registered one.\n"
                "# verdict: confirmed_switch | explained | not_a_switch\n")
    else:
        raise SystemExit(f"{hid} has no hand verification")
    return head + yaml.safe_dump({"hypothesis": hid, "items": items}, sort_keys=False, width=120)
