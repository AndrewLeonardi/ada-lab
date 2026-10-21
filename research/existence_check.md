# Existence check: open arm-level outcome dataset for metastatic colorectal cancer (mCRC) RCTs

Checked on 2026-10-20. All PubMed counts come from NCBI E-utilities (esearch) run on that date. All PMIDs cited below were confirmed with esummary. Every resource listed was visited at the URL given. Where a page could not be read (paywall, HTTP 403, or JS-only rendering), this is stated.

## Verdict

**This does not exist as an open resource.** Some pieces exist, but they are fragments. No public dataset gives arm-level regimen, n, ORR, median PFS/OS with CIs, HRs and key toxicities for mCRC RCTs, links every number to a PMID and its source sentence, and is kept up to date. The closest open sources each cover only part of the problem:

1. **ClinicalTrials.gov results / AACT** is open, structured and arm-level. However, only 185 of the 731 registered randomized phase 2/3 mCRC trials (25%) have posted results. The data are not linked to publications or sentences, and pre-2008 trials are essentially absent.
2. **ESMO-MCBS scorecards** are free to view but copyrighted. They hold 29 colorectal scorecards covering 27 trials, of which 23 are randomized; most are pivotal approval trials. Each records control-arm median, gain and HR with CI as free text.
3. **KMDATA** is open. It holds reconstructed patient-level KM data from 32 colorectal publications, limited to 2014–2016, and is static.
4. One-off meta-analysis supplements, plus a few cross-tumour meta-research datasets (e.g., 415 phase III trials, trial-level HR only).

The large mCRC trial databases are all patient-level and access-controlled. These include ARCAD (67 trials, ~47,000 patients; analyses by proposal, and its MOUs prohibit comparing specific treatments), the NCTN Data Archive (dbGaP controlled access), Project Data Sphere (registration plus application), and Vivli/YODA (proposal review plus DUA). Commercial intelligence databases (Citeline Trialtrove, GlobalData, Cortellis) say they include trial results but are subscription-only; their contents could not be inspected.

On scope, PubMed contains roughly **1,500–2,200 RCT-tagged mCRC records**. Triangulating with ClinicalTrials.gov suggests about **600–800 distinct randomized phase 2/3 trials with a full journal report**, of which an estimated 250–350 are phase 3.

There is repeated, documented demand. At least 7 independent groups hand-extracted mCRC trial-level or arm-level outcomes for surrogate-endpoint or meta-research work, and none released a reusable, maintained dataset.

---

## 1. Evidence per resource

### 1a. Structured registries with arm-level results (open)

**ClinicalTrials.gov results database / AACT**: open, partial coverage.
- AACT (https://aact.ctti-clinicaltrials.org/) is CTTI's relational copy of everything on ClinicalTrials.gov, including posted results (outcome and adverse-event tables). The site describes it as "Open" and it is refreshed daily. Cloud access and downloads need an account to get credentials.
- ClinicalTrials.gov API v2 queries, run 2026-10-20 with `query.cond=metastatic colorectal cancer`:

| Filter (`filter.advanced`) | Studies |
|---|---|
| `AREA[StudyType]INTERVENTIONAL` | 2,648 |
| + `AREA[DesignAllocation]RANDOMIZED` | 917 |
| + `(AREA[Phase]PHASE2 OR AREA[Phase]PHASE3)` | **731** |
| …of which include PHASE3 (incl. phase 2/3) | 295 |
| …of which status COMPLETED / TERMINATED / ACTIVE_NOT_RECRUITING | 436 (COMPLETED 289, TERMINATED 93, ANR 54; UNKNOWN 130, RECRUITING 96) |
| randomized phase 2/3 **with posted results** (`AREA[HasResults]true`) | **185 (25%)** |

- I parsed the `resultsSection` of those 185 trials:
  - 162 post a PFS outcome measure, 153 an OS measure and 131 an ORR measure.
  - 146 post a median PFS/OS by arm; 126 of these include a 95% CI.
  - 89 post a statistical analysis (e.g., HR) for PFS/OS.
  - All 185 post adverse-event tables by arm.
  - 128 of the 185 are industry-sponsored.
- **Assessment:** This is the only open, structured, arm-level source of any size. However, it covers about a quarter of registered trials, is skewed to industry trials, has almost no pre-2008 trials, and is not linked to the published numbers or sentences. Posted values can also differ from the publication's cut-off.
- In a random sample of 40 of the 731 registry hits, about 36–38 were mCRC trials. The off-target hits were anal cancer, a liver-cancer supplement trial and a supportive-care trial.
- Related: Pellat et al. 2022 (PMID 35404939; dataset CC-BY at https://zenodo.org/records/5883227) studied 763 CRC interventional studies completed 2013–2020. They found that 37% had no results anywhere, and only 2% had results posted on ClinicalTrials.gov within 12 months.

### 1b. Open or free trial-level compilations (partial overlap)

**ESMO-MCBS scorecards**: free to view, copyrighted, small mCRC coverage.
- URL: https://www.esmo.org/guidelines/esmo-mcbs/esmo-mcbs-for-solid-tumours/esmo-mcbs-scorecards (JS-rendered). Example colorectal scorecard: `?scorecard=485` (CheckMate 8HW).
- The page loads its data from a JSON file: https://dam.esmo.org/raw/upload/v1792162085/untitled_content_item_66b19ca.json. That file held **547 scorecards** on 2026-10-20.
- **29 are colorectal, covering 27 trials.** BREAKWATER and CheckMate 142 each have 2 scorecards. 23 of the 27 are randomized; CheckMate 142, KEYNOTE-158, KEYNOTE-164 and MOUNTAINEER are single-arm. The colorectal trials include 20020408, 20050181, PRIME, CRYSTAL, EPIC, CO.17, AVF2107g, E3200, NO16966, ML18147, VELOUR, RAISE, TRIBE, CORRECT, RECOURSE, SUNLIGHT, FRESCO, FRESCO-2, BEACON, BREAKWATER (2 scorecards), CodeBreaK 300, KEYNOTE-177, CheckMate 8HW, CheckMate 142 (2), KEYNOTE-158/164 and MOUNTAINEER.
- Fields include control-arm median, gain, `osHr`/`pfsHr` as free text with CI, ORR, toxicity comments, reference and NCT. There are no arm n values, no sentence provenance and no non-pivotal trials.
- The site states "All rights reserved" and the data are governed by the ESMO-MCBS Terms of Use. **Not an open-licensed dataset.**

**KMDATA** (Fell et al., Database 2021, PMID 34169314): open, static, narrow time window.
- URLs: https://github.com/raredd/kmdata (licence field "NOASSERTION"; last push 2025-05) and https://pmc.ncbi.nlm.nih.gov/articles/PMC8234134/ (the Excel master file is on figshare, doi 10.6084/m9.figshare.14642247).
- Contents: 304 reconstructed KM datasets from 153 phase III publications (breast, lung, prostate, colorectal), **published 2014–2016 only**. Study-level metadata include arms, sample size and reported HR/p.
- From the package's `R/data.R`, **32 publications / 70 KM pairs are colorectal**. Some of these are adjuvant or rectal trials (e.g., QUASAR2, PETACC8, NSABP R-04), so mCRC is roughly 20.
- Reconstructed IPD, not curated arm-level summaries; no sentence links; not updated.

**Sherry et al. 2024, JCO Precision Oncology** (PMID 39348660; https://pmc.ncbi.nlm.nih.gov/articles/PMC11444522/).
- 415 phase III oncology RCTs published 2004–2020. Data are **trial-level primary-endpoint HR with 95% CI only**, available in the journal Data Supplement.
- 66 trials are gastrointestinal; there is no separate colorectal count. No arm-level medians, ORR or toxicity.

**Ribnikar et al. 2021, Sci Rep** (PMID 34035370; https://pmc.ncbi.nlm.nih.gov/articles/PMC8149406/).
- 143 phase 3 solid-tumour RCTs, 21 of them colorectal. Includes HRs and grade 3/4 AEs by arm, double-extracted by hand.
- Data "available from the corresponding author upon reasonable request". **Not open.**

**CEIT-Cancer** (Ladanie et al., Trials 2018, PMID 30231912; https://pmc.ncbi.nlm.nih.gov/articles/PMC6146631/).
- Covers trials supporting FDA cancer-drug approvals 2000–2016. Its schema captures per-arm n/events and median with CI.
- Data "not publicly available… on reasonable request". **Not open**, and limited to approval trials.

**One-off mCRC network meta-analyses** (static snapshots):
- Keshavarzi et al., Heliyon 2024 (PMID 39253267; https://pmc.ncbi.nlm.nih.gov/articles/PMC11381762/): 46 first-line RCTs. The statement says "All data… are included in this published article"; R code is in the supplement.
- Figshare items attached to NMAs, all CC BY:
  - The 2015 PLOS ONE first-line biologics NMA (https://api.figshare.com/v2/articles/1578376) holds figures and text only.
  - The 2024 later-line NMA of survival curves (https://api.figshare.com/v2/articles/26062598; 10 trials) is a single .odt supplement.
- None of these is maintained or machine-readable at arm level with provenance.

**Surrogate R package, `colorectal` dataset** (https://search.r-project.org/CRAN/refmans/Surrogate/html/colorectal.html): patient-level data from 26 historical advanced-CRC RCTs (3,943 observations; anonymised trial IDs; response/OS only). Not linked to publications.

### 1c. Patient-level, application-based platforms (not open; different product)

**ARCAD database** (Fondation ARCAD / Mayo Clinic / NCC Japan).
- URLs: https://www.fondationarcad.org/en/a-r-ca-d-databases/, https://www.ncc.go.jp/en/information/press_release/20220804/index.html and https://www.ncc.go.jp/en/information/press_release/2025/0131/index.html.
- Size: **67 trials, ~47,000 CRC patients as of Dec 2024** (56 trials / ~43,000 in 2022). Individual patient data.
- **Access is by proposal, not open.** Sargent et al., Oncologist 2012 (PMID 22302228; https://pmc.ncbi.nlm.nih.gov/articles/PMC3286167) says proposals "will be considered by a panel" and that contributing groups are consulted and can withhold their data.
- The 2024 analysis-proposal template (https://www.ncc.go.jp/jp/ncce/division/arcadasia/activity/ARCAD_analysis_proposal_template_2024_pro.doc) asks for aims, data items, statistics, publication plan and budget. It states that "performing comparisons of specific treatments is prohibited according to ARCAD MOUs".
- The foundation's website gives no open download.

**NCI NCTN/NCORP Data Archive** (https://dctd.cancer.gov/research/networks/nctn/data-archive; trial list at https://dctd.cancer.gov/research/networks/nctn/data-archive-trials.xlsx).
- 40 trials / 47,057 patients as of 2026-10-16, de-identified patient-level data. Access is through dbGaP controlled access.
- Metastatic CRC trials in the list: **N9741 and CALGB/SWOG C80405**. The other colorectal entries are adjuvant or rectal trials (N0147, E5204, C9581, CALGB 80702, N1048/PROSPECT, ACOSOG Z6051).

**Project Data Sphere** (https://www.projectdatasphere.org → https://data.projectdatasphere.org/).
- Patient-level oncology trial data, mainly comparator arms. Access needs registration plus "a brief application… and agreement to terms of use" (Green et al., Oncologist 2015, PMID 25876994).
- mCRC data are on the platform. For example, Abdel-Rahman 2019 pooled 5 mCRC RCTs from PDS (PMID 31492988), and Chen 2024 used PDS mCRC data (PMID 38834016).
- The catalogue is a JS app that I could not enumerate, so the **exact number of mCRC datasets was not determined**.

**Vivli** (https://vivli.org/; process at https://vivli.org/resources/requestdata/).
- 8,600+ trials. A request goes through an administrative check, a contributor feasibility check and an independent review panel. Requesters sign a non-negotiable DUA and work in a secure cloud workspace with fees after the free period.
- Some mCRC sponsor trials (e.g., Daiichi Sankyo, Takeda) route IPD requests through Vivli, according to their ClinicalTrials.gov records.

**YODA Project** (https://yoda.yale.edu/): data partners are J&J, Kenvue, Medtronic, QMUL and SI-BONE. Application with review and DUA. No colorectal trials were apparent.

### 1d. Commercial databases (for contrast; contents not inspectable)

- **Citeline Trialtrove(+)** (https://citeline.com/products-services/trialtrove/): 555,000+ trials, 70,000+ sources and 350+ diseases, updated daily. It describes coverage "from objectives and endpoints through to reported results". Pricing is by contact. **Depth of arm-level numeric results could not be verified.**
- **GlobalData Clinical Trials** (https://www.globaldata.com/company-profile/loxo-oncology-inc/premium-data/clinical-trials/): a premium product listing "Trial results, as reported in the public domain". Not inspectable.
- **Clarivate Cortellis Clinical Trials Intelligence**: the product pages returned HTTP 403 to automated fetch. The 2020 press release (https://ir.clarivate.com/news-events/press-releases/news-details/2020/Clarivate-Enhances-Cortellis-Clinical-Trials-Intelligence-with-New-Site-Selection-Analytics/default.aspx) describes 380,000+ trials with "protocol, biomarker, patient segmentation, endpoint, and site data". **Results content not verifiable.**

None of these are open. None advertises sentence-level provenance.

### 1e. General data repositories (searched 2026-10-20)

- **Zenodo** (REST API `https://zenodo.org/api/records?type=dataset&q=…`, 6 queries): nothing relevant to mCRC RCT arm-level outcomes. Hits were omics datasets, single-centre cohorts and single-trial source data. The nearest items were:
  - https://zenodo.org/records/12250590: 600 oncology RCTs labelled localized vs metastatic (eligibility text, not outcomes).
  - https://zenodo.org/records/4288605: reconstructed NSCLC KM data.
  - https://zenodo.org/records/5883227: the Pellat CRC results-availability dataset.
- **Figshare** (API `POST https://api.figshare.com/v2/articles/search`, 4 queries): only journal supplements of individual meta-analyses (Frontiers/T&F/PLOS docx/odt tables, typically 5–60 trials each, unmaintained).
- **Dryad** (API `https://datadryad.org/api/v2/search`): 6 hits for "metastatic colorectal". None are trial-outcome compilations; one is a cetuximab cost-effectiveness model input.
- **GitHub** (search API / `gh search repos`, 14 queries): no mCRC trial-outcome dataset. Related but different:
  - HINT/TOP clinical trial outcome-prediction benchmark (https://github.com/futianfan/clinical-trial-outcome-prediction): binary approval labels.
  - kmdata (above).
- **Kaggle** (public list API `https://www.kaggle.com/api/v1/datasets/list?search=…`, 5 queries; the web UI did not render): nothing relevant.
- **Mendeley Data** (https://data.mendeley.com/research-data/?query=…, viewed in browser): only individual meta-analysis supplements and single-cohort datasets.
- **Data descriptor journals**: PubMed search `("Sci Data"[ta] OR "Data Brief"[ta]) AND (colorectal[tiab] OR colon[tiab]) AND (trial*[tiab] OR survival[tiab])` returned 11 records, none relevant. A broader oncology-trials descriptor query returned 10 records. The nearest were:
  - KMDATA (PMID 34169314).
  - Geifman 2016 Sci Data, prostate IPD from 8 trials (PMID 27163794).
  - Fountzilas 2023 Data Brief, phase I/II immunotherapy trials (PMID 38020439).

  No data descriptor covers mCRC RCT outcomes.

### 1f. Named "living" / open oncology evidence resources

- **LIvE (Living Interactive Evidence) synthesis, Mayo Clinic (Riaz IB et al.)**: background at https://newsnetwork.mayoclinic.org/discussion/whats-the-best-treatment-for-this-condition-the-knowledge-synthesis-team-can-help/.
  - Published living interactive SR/NMAs cover first-line metastatic RCC (PMID 33824031), cancer-associated thrombosis (PMID 34172290), adjuvant RCC (PMID 35537621), PARP inhibitors in mCRPC (PMID 39848867) and mHSPC (PMID 41193370).
  - **No colorectal LIvE review was found.** PubMed `Riaz IB[au] AND living[ti] AND (colorectal[tiab] OR gastrointestinal[tiab])` returned 0.
  - I did not find a public bulk download of the extracted data.
- **Living SR/NMA in mCRC**: PubMed `"living"[ti] AND (systematic review[ti] OR meta-analysis[ti] OR "evidence synthesis"[ti] OR network[ti]) AND (colorectal[tiab] OR colon[tiab])` returned 10 records, none of them a living review of mCRC treatment. Web search found only one-off NMAs (e.g., PMID 39253267).
- **metaEvidence** (https://www.metaevidence.org): the page returned no readable content, so its status could not be determined.
- **"CancerRCT", "OncoTrials"**: web searches found no resource by these names. I cannot confirm they exist.
- **CTOD / CTO benchmark** (https://chufangao.github.io/CTOD/; Gao et al., arXiv 2406.10292): about 125,000 trials with **binary success/failure labels**, MIT licence, on Hugging Face. No arm-level numbers.
- **Trialstreamer** (Marshall et al., JAMIA 2020, PMID 32940710): living database of RCT reports with PICO/sample-size extraction, not numeric arm results. The listed portal host (trialstreamer.ieai.robotreviewer.net) did **not resolve** on 2026-10-20.
- **Yun et al. 2024**, "Automatically Extracting Numerical Results from RCTs with LLMs" (PMLR v252; https://proceedings.mlr.press/v252/yun24a.html): a released, general-domain (not oncology-specific) evaluation set of RCT reports annotated with numerical results. Relevant as an extraction benchmark, not as an mCRC dataset.

---

## 2. Scope: how many mCRC RCTs?

### PubMed counts (esearch, 2026-10-20)

**A. Query specified in the brief:**
```
("colorectal neoplasms"[MeSH] OR colorectal cancer[tiab]) AND (metastatic[tiab] OR advanced[tiab]) AND randomized controlled trial[pt]
```
= **2,229**

| Sub-filter added to A | Count |
|---|---|
| `AND clinical trial, phase iii[pt]` | 618 |
| `AND clinical trial, phase ii[pt]` | 477 |
| `AND (clinical trial, phase ii[pt] OR clinical trial, phase iii[pt])` | 1,057 |
| `AND english[la]` | 2,153 |
| `AND ("locally advanced rectal"[tiab])` (off-target) | 230 |
| `AND (adenoma[tiab] OR screening[tiab] OR colonoscopy[tiab])` (off-target) | 310 |
| `AND ("locally advanced rectal"[tiab] OR adenoma[tiab] OR screening[tiab] OR adjuvant[ti])` (off-target) | 594 |
| by publication date: ≤1989 / 1990s / 2000s / 2010s / 2020+ | 97 / 228 / 434 / 849 / 642 |

Query A is sensitive but noisy. About 27% of hits are clearly off-target: "advanced adenoma" screening trials, locally advanced rectal cancer and adjuvant trials.

**B. Tighter mCRC phrasing:**
```
("metastatic colorectal"[tiab] OR "advanced colorectal"[tiab] OR mCRC[tiab] OR "metastatic colon"[tiab] OR "metastatic rectal"[tiab] OR "unresectable colorectal"[tiab] OR "colorectal liver metastases"[tiab] OR "colorectal cancer liver metastases"[tiab]) AND randomized controlled trial[pt]
```
= **1,519**

| Sub-filter added to B | Count |
|---|---|
| `AND clinical trial, phase iii[pt]` | 518 |
| `AND clinical trial, phase ii[pt]` | 375 |
| by date: ≤1999 / 2000s / 2010s / 2020+ | 233 / 309 / 598 / 393 |
| `AND hasabstract` | 1,497 |
| `AND pubmed pmc[sb]` (full text in PMC) | 480 |
| `AND pubmed pmc open access[filter]` | 359 |
| `NOT ("post hoc" OR "secondary analysis" OR "exploratory analysis" OR "subgroup analysis" OR "pooled analysis" OR "cost-effectiveness"[tiab] OR "quality of life"[ti] OR biomarker*[ti] OR pharmacokinetic*[ti])` | 1,296 |

- Union of A and B: 2,370.
- Records with "randomized/randomised" in the title that are **not tagged** RCT[pt]: **152**, and about one third of a 40-record sample were primary trial reports. Query: B's phrase block `AND ((randomized[ti] OR randomised[ti]) AND (trial[ti] OR study[ti] OR phase[ti])) NOT randomized controlled trial[pt] NOT (meta-analysis[pt] OR review[pt] OR systematic review[pt] OR comment[pt] OR editorial[pt] OR letter[pt])`.
- For publication dates 2024 onward, only 148 B-phrased records carry RCT[pt]. By contrast, 461 records match `RCT[pt] OR randomized[tiab] OR randomised[tiab]`, though that set also includes reviews and secondary analyses. **Recent literature is under-counted by the [pt] filter.**
- Context: B combined with `("meta-analysis"[pt] OR "network meta-analysis"[tiab])` returns 675 records, and B with `"network meta-analysis"[tiab]` returns 65.

### From publications to distinct trials

- **Hand-classified random sample of 100 records from B** (seed 42), read by title:
  - **~49%** are efficacy reports of a randomized anticancer intervention in metastatic/advanced CRC, including 2 updated or final analyses.
  - About 30% are secondary analyses of RCTs (biomarker, QoL, PK, cost-effectiveness, post hoc).
  - About 20% are off-target (screening, adjuvant, supportive care, phase I, protocols, methods).
  - This gives about 700–750 primary or updated efficacy reports in B. After removing duplicate reports of the same trial (estimated around 10–15%), that leaves about **600–650 distinct trials**.
  - Adding un-indexed recent reports (~50) and trials described only with other phrasing gives **~650–800 distinct randomized trials with a full PubMed-indexed report**. Roughly 120–180 of these predate 2000 (233 B records ≤1999); supportive-care and locoregional RCTs are a minority.
- **ClinicalTrials.gov cross-check:** 731 registered randomized phase 2/3 mCRC trials (295 phase 3), about 1999 onward. Of these, 566 are closed or have unknown status.
  - Only 238 of the 731 NCT IDs appear in any PubMed record (searched as `NCTxxxxxxxx[si] OR NCTxxxxxxxx[tiab]`; 470 PubMed records). This is a lower bound, because many reports omit the NCT number in indexed fields.
  - Many Asian trials are registered elsewhere (UMIN, ChiCTR, JapicCTI), and pre-2000 trials are unregistered.
- **Best estimate:** **~600–800 distinct randomized phase 2/3 mCRC trials with a peer-reviewed full report**, of which roughly **250–350 are phase 3**. That is about 1,500–2,000 arms. A further unquantified set exists only as ASCO/ESMO conference abstracts, which are not in PubMed.
- **Practical note for provenance:** 1,497 of 1,519 records have a PubMed abstract, but only 480 (32%) have PMC full text (359 in the open-access filter). Sentence-level provenance for CIs, toxicities and arm n will often need non-PMC full text or the abstract alone.

---

## 3. Evidence of demand (groups that had to hand-extract mCRC trial outcomes)

All PMIDs below were verified via esummary.

1. **Tang PA et al., J Clin Oncol 2007, PMID 17876010.** "Surrogate end points for median overall survival in mCRC: literature-based analysis from 39 RCTs of first-line chemotherapy." Hand-extracted 39 trials / **87 treatment arms** to correlate PFS/TTP/RR with OS. This is directly the arm-level use case.
2. **Giessen C et al., Clin Cancer Res 2013, PMID 23149819.** PFS as surrogate for median OS in mCRC; literature-based analysis of **50 randomized first-line trials (22,736 patients)**. The authors note that "a larger set of trials is needed" for antibody trials.
3. **Chirila C et al., Int J Colorectal Dis 2012, PMID 22076612.** Meta-analysis of PFS vs OS across **62 mCRC phase 2/3 articles (23,527 patients)**, including within-arm correlation of medians (arm-level).
4. **Petrelli F & Barni S, Ann Oncol 2013, PMID 22898038.** Correlation of PFS and post-progression survival with OS across **34 randomized first-line trials**.
5. **Ciani O et al., J Clin Epidemiol 2015, PMID 25863582.** Systematic review of aCRC drug RCTs from 2003–2013, extracting HRs/ORs and median differences for PFS, TTP, TR and OS. The same extraction was reused by **Elia EG et al., Cancer Epidemiol 2020, PMID 31911395** (33 trials), showing the value of a shared extracted dataset.

Further examples:
- **Colloca GA, Int J Clin Oncol 2019, PMID 31289956**: response endpoints vs OS, 12 RCTs, 2 arms per trial.
- **Grothey A et al., J Clin Oncol 2004, PMID 15051767**: arm-level exposure vs median OS across 7 phase III trials.
- **Del Paggio JC et al., JAMA Oncol 2021, PMID 33764385**: trends in oncology RCT design and results; 298 RCTs including 55 colorectal, data "extracted from the published RCT report".
- **Ribnikar D et al., Sci Rep 2021, PMID 34035370**: 21 CRC phase 3 trials double-extracted; data only on request.
- **Sherry AD et al., JCO Precis Oncol 2024, PMID 39348660**: Bayesian prior from 415 phase III HRs.

**Control-arm benchmarking / external controls (trial-design use case):**
- **Yoshino T et al., Nat Med 2023, PMID 37507606**: synthetic control arm for refractory mCRC.
- **Raeisi M et al., J Natl Cancer Inst 2026, PMID 42633557**: ARCAD-derived external control arms to reproduce mCRC RCT OS.

Both rely on access-controlled IPD, which an open arm-level benchmark could complement but not replace.

**Pattern:** Each group re-extracted overlapping trial sets by hand. Where data availability is stated, it is "on request" (Ribnikar; CEIT-Cancer) or a static supplement (Sherry; Keshavarzi). I found no public release for the surrogate-endpoint papers 1–5, though I did not check each paper's supplement exhaustively.

---

## 4. Limits of this check

- Project Data Sphere's catalogue (JS app) and Cortellis (HTTP 403) could not be enumerated. Commercial database contents are known only from vendor descriptions.
- metaEvidence.org returned no readable content.
- Kaggle was searched only through its public list API.
- The distinct-trial estimate rests on a 100-record title-level sample and registry triangulation. Treat it as ±25%.
- Conference-abstract-only trials are not counted.
