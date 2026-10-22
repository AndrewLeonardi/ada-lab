# Candidate findings register

Things the dataset might support beyond the dataset itself. A candidate is marked "ready for the user"
only when all four checks pass:
- **verification:** every underlying number is audited correct;
- **robustness:** it survives reasonable alternative analysis choices;
- **novelty:** prior work has been searched on PubMed, with PMIDs;
- **analysis:** the analysis is re-runnable code.

## Status on 2026-10-20 (audit 1)
**No candidates yet.** The public dataset is still empty, because the real screening run has not started. The 19 benchmark trials
are a hand-picked test set, not a sample to draw conclusions from.

## Ideas to test once the dataset is large (about 100+ trials)
1. **Endpoint drift.** How often do trial abstracts report non-standard time endpoints (PFS2, PFS on
   treatment, failure-free survival, duration of disease control), and has this changed over time?
   4 of the 19 benchmark trials did. That is a strategy-trial-heavy set, so this is a hint, not a rate.
   - status: idea
2. **Surrogate relationship.** Relationship between arm-level PFS and OS hazard ratios, and between PFS
   and OS medians, by line and biomarker. This is well studied, so the novelty check must find the prior
   meta-analyses. It would only be new as a continuously updated, sentence-sourced version.
   - status: idea
3. **Registry cross-check.** Abstract results against ClinicalTrials.gov (AACT) results for the same NCT
   number: missing or different numbers.
   - status: idea; needs the AACT step.

## Status on 2026-10-22 (audit 2)
The dataset now has 310 trials. Candidates are tested through the hypothesis ledger (`research/hypotheses/`,
website "Hypotheses"); this register records the auditor's view.

4. **Missing results** (H001-H003).
   - Of 355 registered randomized metastatic colorectal cancer trials that finished 2+ years ago, the
     automated search found no results for 60 so far; 37 candidate papers still await a model check.
   - H001 needs a hand-checked random sample of 30 (seed H001-v1), drawn once nothing is pending.
   - Prior work exists on non-publication of cancer trials in general, so the novelty check must cite it. A
     colorectal-specific, continuously updated tracker would be the contribution.
   - status: under test.
5. **Primary endpoint switching** (H004). 0 of 32 compared trials, so inconclusive (95% CI 0% to 10.7%). The
   comparison is being redone with a fairer matching rule; the primary-endpoint logic is unchanged.
   - status: under test (likely inconclusive until the dataset grows).
6. **Number differences between paper and registry.**
   - Audit 2 reviewed all 38. Most are explained: registries count every enrolled patient across cohorts,
     abstracts round, and some registry tables are for a subgroup.
   - The real problems were Ada's own extraction errors (ACCRU), not errors in the papers.
   - status: idea (low).
7. **Errors in published papers.**
   - The 27 consistency contradictions were all extraction errors once checked against the abstracts
     (reversed hazard ratios, totals under each arm, rates misfiled). No inconsistency within a paper was
     confirmed.
   - status: idea.
