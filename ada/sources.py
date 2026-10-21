"""Free information: PubMed via NCBI E-utilities (no key needed, <= 3 requests/second)."""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
_last = [0.0]

# Randomized trials in metastatic/advanced colorectal cancer. Kept deliberately broad;
# screening decides what is really in scope.
MCRC_RCT_QUERY = (
    '("colorectal neoplasms"[MeSH Terms] OR colorectal cancer[tiab] OR colon cancer[tiab] OR rectal cancer[tiab]) '
    'AND (metastatic[tiab] OR advanced[tiab] OR "stage IV"[tiab]) '
    'AND (randomized controlled trial[pt] OR (randomi*[tiab] AND (phase[tiab] OR trial[tiab])))'
)


def _get(url: str, timeout: int = 30) -> bytes:
    wait = 0.36 - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    req = urllib.request.Request(url, headers={"User-Agent": "ada-research-lab/0.1 (open dataset of mCRC trial outcomes)"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = r.read()
            _last[0] = time.time()
            return data
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("unreachable")


def search(query: str = MCRC_RCT_QUERY, retmax: int = 10000, mindate: str | None = None) -> tuple[int, list[str]]:
    params = {"db": "pubmed", "term": query, "retmax": retmax, "retmode": "json", "sort": "pub_date"}
    if mindate:
        params.update({"datetype": "edat", "mindate": mindate, "maxdate": "3000"})
    r = json.loads(_get(EUTILS + "esearch.fcgi?" + urllib.parse.urlencode(params)))["esearchresult"]
    return int(r["count"]), list(r.get("idlist", []))


def _text(el) -> str:
    return "".join(el.itertext()).strip() if el is not None else ""


def fetch(pmids: list[str]) -> list[dict]:
    """Title, abstract (with section labels), journal, year, authors, DOI, publication types, NCT IDs."""
    out = []
    for i in range(0, len(pmids), 100):
        chunk = pmids[i:i + 100]
        xml = _get(EUTILS + "efetch.fcgi?" + urllib.parse.urlencode(
            {"db": "pubmed", "id": ",".join(chunk), "retmode": "xml"}), timeout=60)
        root = ET.fromstring(xml)
        for art in root.findall(".//PubmedArticle"):
            pmid = _text(art.find(".//PMID"))
            a = art.find(".//Article")
            parts = []
            for ab in a.findall(".//Abstract/AbstractText") if a is not None else []:
                label = ab.get("Label")
                txt = _text(ab)
                parts.append(f"{label}: {txt}" if label else txt)
            year = _text(art.find(".//Article/Journal/JournalIssue/PubDate/Year")) or \
                _text(art.find(".//Article/Journal/JournalIssue/PubDate/MedlineDate"))[:4]
            authors = []
            for au in art.findall(".//AuthorList/Author")[:3]:
                last, ini = _text(au.find("LastName")), _text(au.find("Initials"))
                if last:
                    authors.append(f"{last} {ini}".strip())
            n_auth = len(art.findall(".//AuthorList/Author"))
            doi = ""
            for aid in art.findall(".//ArticleIdList/ArticleId"):
                if aid.get("IdType") == "doi":
                    doi = _text(aid)
            nct = sorted({_text(x) for x in art.findall(".//DataBank/AccessionNumberList/AccessionNumber")
                          if _text(x).startswith("NCT")})
            out.append({
                "pmid": pmid,
                "title": _text(a.find("ArticleTitle")) if a is not None else "",
                "journal": _text(art.find(".//Journal/ISOAbbreviation")) or _text(art.find(".//Journal/Title")),
                "year": int(year) if year[:4].isdigit() else None,
                "authors": ", ".join(authors) + (", et al." if n_auth > 3 else ""),
                "doi": doi,
                "abstract": "\n".join(parts),
                "pub_types": [_text(p) for p in art.findall(".//PublicationTypeList/PublicationType")],
                "nct_ids": nct,
            })
    return out
