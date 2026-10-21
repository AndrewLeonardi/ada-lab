"""ada <command>

  status                         dataset size, review queue, spend
  sync [--limit N]               find new candidate papers on PubMed (free)
  run --profile P [--hours H]    work: screen, extract, verify, publish (loops; respects the caps)
  benchmark --profile P          accuracy against hand-verified trials (costs cents)
  export                         rebuild the website data files
  approve <slug>                 publish a drafted lab note
  audit-sample [--n 20]          draw an audit sample (for /audit-ada in Claude Code)
  apply-audit <file.yaml>        apply an audit's verdicts and corrections
  profiles                       list run profiles
  (add --mock to run or benchmark for a free offline test)
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys

from . import db
from .export import NOTES, export
from .pipeline import PROFILES, extract_one, run, sync


def main(argv=None):
    ap = argparse.ArgumentParser(prog="ada", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    sub.add_parser("profiles")
    s = sub.add_parser("sync")
    s.add_argument("--limit", type=int, default=None)
    r = sub.add_parser("run")
    r.add_argument("--profile", default="balanced", choices=list(PROFILES))
    r.add_argument("--hours", type=float, default=None)
    r.add_argument("--mock", action="store_true")
    b = sub.add_parser("benchmark")
    b.add_argument("--profile", default="balanced", choices=list(PROFILES))
    b.add_argument("--mock", action="store_true")
    sub.add_parser("export")
    a = sub.add_parser("approve")
    a.add_argument("slug")
    asm = sub.add_parser("audit-sample")
    asm.add_argument("--n", type=int, default=20)
    asm.add_argument("--review", type=int, default=30)
    apa = sub.add_parser("apply-audit")
    apa.add_argument("file")
    args = ap.parse_args(argv)
    con = db.connect()

    if args.cmd == "profiles":
        for k, v in PROFILES.items():
            print(f"{k:12s} daily ${v['daily_usd']:.2f}, total ${v['total_usd']:.0f} - {v['description']}")
    elif args.cmd == "status":
        print(json.dumps(export(con), indent=1))
        print(f"spent today ${db.spent(con, __import__('time').strftime('%Y-%m-%d')):.4f}, total ${db.spent(con):.4f}")
    elif args.cmd == "sync":
        print(f"{sync(con, args.limit)} new papers")
    elif args.cmd == "run":
        from .mock import mock
        run(args.profile, args.hours, mock=mock if args.mock else None)
    elif args.cmd == "benchmark":
        from .benchmark import run_benchmark
        from .llm import Budget, Claude
        from .mock import mock
        prof = PROFILES[args.profile]
        claude = Claude(con, Budget(prof["daily_usd"], prof["total_usd"]), mock=mock if args.mock else None)
        res = run_benchmark(con, lambda pmid: extract_one(con, claude, prof["extract_models"], pmid))
        print(json.dumps({k: v for k, v in res.items() if k != "missed"}, indent=1))
        export(con)
    elif args.cmd == "export":
        print(json.dumps(export(con), indent=1))
    elif args.cmd == "audit-sample":
        from .audit import sample
        print(sample(con, args.n, args.review))
    elif args.cmd == "apply-audit":
        import pathlib
        from .audit import apply
        print(json.dumps(apply(con, pathlib.Path(args.file)), indent=1))
        export(con)
    elif args.cmd == "approve":
        src = NOTES / "drafts" / f"{args.slug}.md"
        if not src.exists():
            sys.exit(f"no draft {src}")
        (NOTES / "published").mkdir(parents=True, exist_ok=True)
        shutil.move(src, NOTES / "published" / src.name)
        export(con)
        print(f"published {args.slug}")


if __name__ == "__main__":
    main()
