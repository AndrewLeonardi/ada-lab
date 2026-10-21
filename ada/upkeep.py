"""Free upkeep for the dataset: later reports, corrections and retractions, and open full texts.

- Later reports: follow-up papers (updated survival, subgroup analyses) linked to their trial by a shared
  registration number.
- Notices: PubMed's correction links for every included paper, re-read weekly. A retraction, an erratum or an
  expression of concern is shown on the trial's page (and a retracted trial's numbers leave the download).
- Full texts: open-access full texts from PubMed Central, saved for later extraction (abstracts are all that is
  read today).
"""

from __future__ import annotations

import json
import time
import urllib.parse
import xml.etree.ElementTree as ET

from . import sources

NOTICE_TYPES = {"ErratumIn": "correction", "RetractionIn": "retraction", "ExpressionOfConcernIn": "concern",
                "RetractedandRepublishedIn": "retracted_and_republished", "UpdateIn": "update"}
BIOC = "https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_json/{}/unicode"


def _included(con) -> list[dict]:
    return [dict(r) for r in con.execute(
        "SELECT p.pmid, p.nct_ids FROM papers p JOIN screenings s ON s.pmid = p.pmid AND s.id = "
        "(SELECT MAX(id) FROM screenings WHERE pmid = p.pmid) WHERE s.decision = 'include'")]


def link_later_reports(con) -> int:
    """Secondary papers sharing a registration number with an included trial (database only)."""
    by_nct = {}
    for p in _included(con):
        for nct in json.loads(p["nct_ids"] or "[]"):
            by_nct.setdefault(nct, p["pmid"])
    n = 0
    for r in con.execute("SELECT p.pmid, p.nct_ids FROM papers p JOIN screenings s ON s.pmid = p.pmid AND s.id = "
                         "(SELECT MAX(id) FROM screenings WHERE pmid = p.pmid) WHERE s.decision = 'secondary'"):
        for nct in json.loads(r["nct_ids"] or "[]"):
            if nct in by_nct and by_nct[nct] != r["pmid"]:
                n += con.execute("INSERT OR IGNORE INTO notices(pmid, kind, other_pmid, at) VALUES(?,?,?,?)",
                                 (by_nct[nct], "later_report", r["pmid"], time.time())).rowcount
    con.commit()
    return n


def notices_step(con) -> int:
    """Re-read PubMed's correction links for every included paper (free; about 3 requests per 200 papers)."""
    pmids = [p["pmid"] for p in _included(con)]
    n = 0
    for i in range(0, len(pmids), 100):
        xml = sources._get(sources.EUTILS + "efetch.fcgi?" + urllib.parse.urlencode(
            {"db": "pubmed", "id": ",".join(pmids[i:i + 100]), "retmode": "xml"}), timeout=60)
        for art in ET.fromstring(xml).iter("PubmedArticle"):
            pmid = art.findtext(".//MedlineCitation/PMID")
            for cc in art.iter("CommentsCorrections"):
                kind = NOTICE_TYPES.get(cc.get("RefType", ""))
                other = cc.findtext("PMID")
                if kind and other:
                    n += con.execute("INSERT OR IGNORE INTO notices(pmid, kind, other_pmid, at) VALUES(?,?,?,?)",
                                     (pmid, kind, other, time.time())).rowcount
    con.commit()
    return n


def fulltext_step(con, limit: int = 5) -> int:
    """Save up to ``limit`` open-access full texts not fetched yet (free). Returns how many were tried."""
    have = {r[0] for r in con.execute("SELECT pmid FROM fulltexts")}
    todo = [p["pmid"] for p in _included(con) if p["pmid"] not in have][:limit]
    for pmid in todo:
        text, pmcid = "", None
        try:
            docs = json.loads(sources._get(BIOC.format(pmid), timeout=60))
            for coll in docs if isinstance(docs, list) else [docs]:
                for doc in coll.get("documents", []):
                    pmcid = pmcid or doc.get("id")
                    text += "\n\n".join(p.get("text", "") for p in doc.get("passages", []) if p.get("text"))
        except (ValueError, OSError):  # not in the open-access subset (the service answers with plain text)
            pass
        con.execute("INSERT OR REPLACE INTO fulltexts(pmid, pmcid, text, fetched_at) VALUES(?,?,?,?)",
                    (pmid, pmcid, text[:600_000] or None, time.time()))
        con.commit()
    return len(todo)
