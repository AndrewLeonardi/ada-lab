"""Publish Ada's work: rebuild the website data, commit it and push to GitHub (Pages rebuilds the site).

On the server this runs once a day from the work loop (ADA_PUBLISH_HOURS); anywhere, `ada publish` runs it now.
"""

from __future__ import annotations

import subprocess
import time

from .export import ROOT, export

PATHS = ["web/public/data", "data/notes/published", "data/audits", "data/feedback", "data/audit_scoreboard.json",
         "data/benchmark.json", "data/findings.md", "data/hypotheses.json"]


def _git(*args: str) -> subprocess.CompletedProcess:
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"git {args[0]}: {(r.stderr or r.stdout).strip()[:300]}")
    return r


def publish(con, message: str | None = None) -> str | None:
    """Return the commit message, or None when nothing changed."""
    counts = export(con)
    _git("add", *[p for p in PATHS if (ROOT / p).exists()])
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode == 0:
        return None
    msg = message or (f"Dataset update {time.strftime('%Y-%m-%d')}: {counts['trials']} trials, "
                      f"{counts['verified_numbers']} verified numbers")
    _git("commit", "-q", "-m", msg)
    # Code changes arrive from elsewhere (pushed from the Mac); take them first. On a conflict in a data
    # file, this commit's version wins ("theirs" is the commit being replayed during a rebase).
    _git("pull", "-q", "--rebase", "--autostash", "-X", "theirs")
    _git("push", "-q")
    return msg
