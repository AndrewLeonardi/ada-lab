# Feedback 2026-10-20: screening spot check 1

Auditor: Claude (Opus 5.5) via Claude Code. Checked the first 250 screening decisions (screen-v1, Haiku).

## Result
- Exclusions were good: screening and colonoscopy trials, protocols, single-arm studies and non-metastatic
  disease were all correctly excluded.
- Inclusions were not. About 8 of 39 did not belong:
  - locally advanced rectal or colon cancer treated before surgery (5);
  - a phase 1 study;
  - a pooled safety report of four trials in several cancers;
  - a protocol with no results.
- Several of her own reasons said "the population is non-metastatic" next to the decision "include".

## Cause
The answer format asked for the decision before the reason, so she committed first and explained after.

## Changes (screen-v2)
1. A checklist is answered before the decision: `randomized`, `metastatic`, `per_arm_efficacy`, `primary_report`.
2. "Metastatic" is defined precisely. Locally advanced disease without distant metastases is not metastatic,
   even when called "advanced", "high-risk" or "unresectable". Resected or resectable liver or lung metastases
   count as metastatic.
3. Code enforces it (`screen.enforce`). "Include" requires all four checks. A failed check downgrades the
   decision to secondary or exclude and marks the reason "[downgraded by checklist]".
4. `ada rescreen` re-screens papers last screened with an older prompt. All 250 were re-screened for $0.08:
   - 31 decisions changed; includes went from 39 to 26;
   - all 26 remaining includes were checked by title and are randomized metastatic colorectal cancer trials.

## Watch next time
- BREAKWATER Cohort 3 (PMID 42219860) is now "secondary". It is a separately randomized cohort with its own
  primary results. I would include it; decide at the next audit.
- How often the checklist downgrades her: count `[downgraded by checklist]` reasons.
- Trials that were extracted before being re-screened out are hidden from the public dataset by export,
  not deleted.
