# Hypothesis ledger

Ada's research questions, each written down **before** it is tested, with the exact test and what result would
disprove it. The commit history of this folder is the public record of what was predicted, and when.

## Rules

1. **Register before testing.** A hypothesis file states the claim, the data, the prespecified test and the decision
   rule, and is committed before the test runs on the full data. Anything already seen is disclosed in `disclosure`.
2. **Never edit a registered hypothesis.** A change is a new amendment appended at the bottom (`amendments:`, with
   date and reason) or a new hypothesis. Each result records the hash of the file it was tested against.
3. **Tests are code, not opinions.** Each hypothesis names a test function in `ada/hypotheses.py`. A language model
   never decides whether a hypothesis is supported.
4. **Human checks are sampled, not chosen.** When a test needs hand verification (`verification/`), the sample is drawn
   by code with a fixed seed (`ada hypothesis-sample <id>`), and every sampled item must be judged.
5. **Failures are published too.** Supported, refuted, inconclusive and withdrawn hypotheses all stay on the website.
6. **A supported hypothesis is a candidate finding, not a discovery.** It still needs a search for prior work and an
   expert's review before it is presented as anything more.

Statuses: `waiting` (data or verification not ready), `supported`, `refuted`, `not_supported` (the test did not reach
its threshold), `inconclusive` (the interval spans the threshold), `withdrawn`.
