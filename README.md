# The Living Lab

**Ada** is an AI research scientist with a visible lab and a real job: she maintains an open, source-verified dataset of arm-level results from every published randomized trial in metastatic colorectal cancer. Every number links to the exact sentence it came from, and an independent AI auditor checks her work.

| Part | Where | What it does |
|---|---|---|
| Ada's pipeline | `ada/` (Python) | PubMed search → screening → two independent extractions → code verification → export |
| Her website | `web/` (React) | Research homepage, dataset browser, trial pages with source quotes, lab notes, methods & accuracy, and the 3D lab |
| The lab | `web/src/scene` | Isometric diorama where Ada acts out her real recorded work (replay), or a scripted demo day |
| Audits | `../.claude/skills/audit-ada` | `/audit-ada` in Claude Code: re-check a sample against sources, correct, score, improve her prompts, flag findings |
| Data | `data/` | `ada.sqlite` (private: contains full abstracts), audits, scoreboard, feedback, lab-note drafts |

## Ada's commands

Run from the project root (`~/Desktop/Science`):

```bash
.venv/bin/ada profiles
```

```bash
.venv/bin/ada benchmark --profile balanced
```

```bash
.venv/bin/ada run --profile balanced
```

```bash
.venv/bin/ada status
```

- `ada profiles`: lists the run profiles, i.e. which model does which job and the daily and total spending caps (`ada/profiles.yaml`).
- `ada benchmark --profile balanced`: measures her accuracy against our hand-verified trials. It costs cents and should be run first.
- `ada run --profile balanced`: work, in a loop: screen, extract, verify and publish, then check PubMed daily. It stops at the caps.
- `ada status`: dataset size, review queue and spend.
- `ada audit-sample` and `ada apply-audit <file>`: used by `/audit-ada`.
- `ada approve <slug>`: publishes a drafted lab note. Notes are never published without approval.
- Add `--mock` to `run` or `benchmark` for a free offline test.

The API key goes in `../.env` (or `livinglab/.env`) as `ANTHROPIC_API_KEY=...`. It is never committed.

## How a number gets into the dataset

1. **Search:** PubMed (free) for randomized trials in metastatic or advanced colorectal cancer, about 3,750 candidates.
2. **Screen:** the cheapest model decides from the abstract whether the paper is the primary report of an RCT with per-arm results.
3. **Extract twice:** two independent passes, with differently worded instructions and, in the `balanced` profile, two different models. Every value must come with a verbatim quote.
4. **Verify by code (free):**
   - the quote is in the abstract;
   - the number is in the quote;
   - the value is plausible;
   - its confidence interval brackets it;
   - both passes agree.

   Only then is the record `verified`; otherwise it is `needs_review`.
5. **Audit:** `/audit-ada` samples published numbers and the review queue, and corrects, rejects or confirms them. Accuracy is published on the website.

Planning costs: screening all candidates costs well under $1 with Haiku, and extracting a few hundred trials twice costs a few dollars to roughly $20, depending on the profile. Ongoing updates cost cents per week.

## The website

```bash
cd web && ~/.bun/bin/bun install && ~/.bun/bin/bun run dev
```

Then open http://127.0.0.1:5180. Bun is used because Homebrew Node is broken on this Mac. `ada export` writes the site's data into `web/public/data/`.

Edit `web/src/site/config.ts` (maintainer name, contact, repository link) before publishing.

**Free hosting:** this folder is ready to be its own GitHub repository. On every push, `.github/workflows/pages.yml` builds the site and publishes it to GitHub Pages (`https://<user>.github.io/<repo>/`). `.gitignore` keeps the private database (full abstracts) and the API key out. A GitHub release can be archived by Zenodo to get a citable DOI for the dataset.

## The lab

`web/src/world/protocol.ts` defines the events between Ada and the room. Her pipeline emits them as she works (`ada/pipeline.py`); `ada export` publishes the latest 400. The lab replays them, compressed: her real screens, real papers on the shelf, and the review queue on the whiteboard. With no recorded activity, it plays a scripted demo day. To check expressions, use photo mode: `#/lab?photo=excited&act=celebrate`.
