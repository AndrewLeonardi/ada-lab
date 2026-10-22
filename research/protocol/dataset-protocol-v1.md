---
title: "Open Metastatic Colorectal Cancer Trial Outcomes: dataset protocol"
version: 1.0
registered: 2026-10-22
status: registered before the first frozen release
maintainer: Andrew Leonardi
---

# Dataset protocol, version 1.0

This protocol fixes how the dataset is built, checked and released, **before** its first frozen release. Its
commit date on GitHub is the registration date. Changes are made only by a new version of this file, listed in
the change log at the bottom with the reason. The code that implements each step is named alongside it.

## 1. Objective
An open, continuously updated dataset of **arm-level results of randomized trials in metastatic colorectal
cancer**, in which every number is traceable to the exact sentence of its source. It is meant for meta-analysis,
trial design, modelling and research on research.

## 2. Eligibility
A publication is included when all of the following hold. They are judged from the title and abstract.
- **Design:** patients were randomly assigned between two or more arms (phase 2 or 3, any line of therapy,
  including maintenance and treatment-holiday strategies).
- **Population:** metastatic colorectal cancer, meaning distant metastases (stage IV) or recurrent or advanced
  disease that cannot be treated with curative intent. Resected or resectable liver or lung metastases with
  perioperative therapy count.
  - Locally advanced colon or rectal cancer without distant metastases does not count.
  - Anal cancer does not count.
  - A mixed-tumor trial counts only if colorectal results are reported separately.
- **Results:** at least one efficacy outcome is reported for each arm (response, PFS, OS, time to progression,
  disease-free or recurrence-free survival, or a hazard ratio).
- **Report type:** the main results publication of the trial. Updated analyses, subgroup, biomarker,
  quality-of-life and post hoc reports are classed as *secondary* and linked to the trial, not extracted.
  Reviews, meta-analyses, pooled analyses and protocols are excluded.

## 3. Sources and search
- **PubMed**, searched daily through NCBI E-utilities (`ada/sources.py`, `MCRC_RCT_QUERY`), no date limits:
  `("colorectal neoplasms"[MeSH Terms] OR colorectal cancer[tiab] OR colon cancer[tiab] OR rectal cancer[tiab]) AND
  (metastatic[tiab] OR advanced[tiab] OR "stage IV"[tiab]) AND (randomized controlled trial[pt] OR (randomi*[tiab]
  AND (phase[tiab] OR trial[tiab])))`
- **ClinicalTrials.gov**, the registry records of randomized phase 2/3 interventional trials with the condition
  "metastatic colorectal cancer" (`ada/registry.py`). These are used for cross-checks, linking and the
  missing-results analysis; registry numbers are not added to the dataset.

## 4. Screening
- A language model (Claude Haiku) answers four yes/no questions per abstract, before deciding: randomized,
  metastatic, per-arm efficacy, primary report.
- Code enforces the answers: "include" requires all four, and anal-cancer abstracts not concerning colon or rectal
  cancer are excluded (`ada/screen.py`, prompt `screen-v3`).
- Every decision is stored with its reason, model and prompt version.
- A screening change is applied to earlier decisions by re-screening (`ada rescreen`), never by hand.

## 5. Data items
For each arm, only numbers stated in the abstract:

| Field | Definition |
|---|---|
| `n_randomized` | patients randomly assigned to the arm (not treated, evaluable or analysed counts; never the trial total) |
| `orr`, `dcr` | objective response rate, disease control rate (percent; a DCR only when stated as such) |
| `pfs_median`, `os_median`, `ttp_median` | medians from randomization, in months or weeks as stated (PFS = to the first progression or death) |
| `other_time_median` | any other median time endpoint, named (second PFS, PFS on treatment, failure-free survival, ...) |
| `pfs_hr`, `os_hr` | hazard ratio of the arm versus its named comparator, with 95% confidence limits when stated |
| `grade3plus_ae_rate` | percent of patients with grade 3 or worse adverse events, overall or for a named event |

Each record also carries:
- **population:** overall, or a named subgroup;
- **detail:** the endpoint or event named;
- **the verbatim source sentence.**

Each trial carries its acronym, phase, line, biomarker selection, total randomized, primary endpoint, arms, and
registration numbers.

Nothing is computed, converted or rounded. Values given as bounds ("<0.5%"), landmark rates ("10-month PFS
59.9%") and medians in days are not recorded.

## 6. Extraction
- Two independent passes per abstract, with differently worded instructions and different models: pass 1 is Claude
  Haiku, pass 2 is Claude Sonnet (`ada/extract.py`, prompt `extract-v3`).
- Batched at half price through the Message Batches API. Each pass is stored with its model and prompt version.

## 7. Verification
A number is **verified** only if every code check passes (`ada/verify.py`, `ada/consistency.py`):
1. The quote occurs word for word in the abstract.
2. The value and its confidence limits appear in the quote.
3. The value is plausible for its measure, in a unit that fits it, and stated exactly rather than as a bound.
4. Only 95% intervals are recorded, and they bracket the value.
5. A median's unit is the unit its sentence uses.
6. A randomized count comes from a sentence about randomization.
7. A disease control rate is named as such.
8. A median PFS, OS or TTP is not about a non-standard endpoint.
9. The second pass recorded the same measure and value for the same population, or a third reading confirmed it
   (section 8).
10. It does not contradict the trial's other numbers:
    - hazard ratio direction vs medians;
    - PFS ≤ OS;
    - ORR ≤ DCR;
    - arm sizes add up to no more than the total;
    - the hazard ratio sits near the centre of its interval.

Everything else is `needs_review` and is published flagged, not as verified.

## 8. Third reading (adjudication)
When the two passes disagree on a number that passes every other check, a third, stronger model reads the abstract
together with the disputed numbers and judges each one correct, wrong or unclear.
- A number becomes verified only if the third reading confirms it and every code check passes.
- Third-reading verdicts are stored and shown (`ada/adjudicate.py`).

## 9. Audit
An independent AI auditor (Claude Opus, outside Ada's pipeline) audits regularly:
- a random sample of 20 published verified numbers, which measures public accuracy;
- a random sample of 30 from the review queue;
- every consistency contradiction.

Corrections and rejections are logged with reasons and are protected from automatic changes. Each audit's accuracy
is published (`ada/audit.py`; the website's Methods page).

## 10. Human validation (before each major release)
- **Sample:** 150 numbers drawn at random by code (fixed seed `validation-v1`) from the published verified numbers
  of the release being validated.
- **Method:** a person who has not seen Ada's value extracts each number independently from the source (the PubMed
  abstract), using the definitions in section 5. The validation form hides Ada's value until the person's answer is
  saved (website: Validate).
- **Agreement:** the same value (and the same arm, measure and population). Disagreements are adjudicated by
  reading the source, and each is classed as an error by Ada, an error by the validator, or a genuinely ambiguous
  source.
- **Reported:** agreement with a Wilson 95% interval, and accuracy after adjudication.
- **Target:** a lower bound of at least 90% for accuracy after adjudication. A release that misses it is not
  submitted, and the causes are fixed first.

## 11. Trials and publications
- One trial may have several publications. The primary publication carries the arm-level numbers.
- Later reports are linked to it through shared registration numbers.
- Merging duplicate primary publications of the same trial into one trial record is planned before release 1.0;
  until then, duplicates are flagged by shared registration number.

## 12. Releases
- The dataset is updated continuously on the website.
- Citable releases are frozen snapshots (dataset JSON and CSV, this protocol, the code version and an audit summary),
  numbered vMAJOR.MINOR and archived with a DOI (Zenodo, from the GitHub repository).
- Each release states its search date, its counts and its known limitations.
- The licence for data and code is to be decided by the maintainer before release 1.0, after checking whether the
  verbatim abstract sentences may be redistributed.

## 13. Known limitations
- Only abstracts are read: results reported only in full texts or supplements are missing.
- PubMed only: trials published only in other databases or as conference abstracts are not found.
- Language models extract the numbers; code checks, audits and human validation bound their errors but cannot
  eliminate them.

## Change log
- 1.0 (2026-10-22): first registered version.
