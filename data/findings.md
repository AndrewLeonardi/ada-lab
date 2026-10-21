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
