"""ada <command>

  status                         dataset size, review queue, spend
  sync [--limit N]               find new candidate papers on PubMed (free)
  run --profile P [--hours H]    work: screen, extract, verify, publish (loops; respects the caps)
  benchmark --profile P          accuracy against hand-verified trials (costs cents)
  export                         rebuild the website data files
  approve <slug>                 publish a drafted lab note
  reverify                       re-run the code checks on all stored extractions (free; after checks improve)
  rescreen --profile P           re-screen papers last screened with an older screening prompt (fractions of a cent each)
  publish [-m MESSAGE]           export, commit and push to GitHub (the website updates in ~1 minute)
  audit-sample [--n 20]          draw an audit sample (for /audit-ada in Claude Code)
  apply-audit <file.yaml>        apply an audit's verdicts and corrections
  profiles                       list run profiles
  recheck-registry               redo every paper-vs-registry comparison (free; after the comparison improves)
  hypotheses                     run the registered hypothesis tests now (free; research/hypotheses/)
  hypothesis-sample ID [--n 30]  draw the fixed-seed sample to verify by hand (prints YAML)
  live [--port 8787]             stream her activity to the 3D lab as it happens (read-only; runs on the server)
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
    sub.add_parser("reverify")
    sub.add_parser("recheck-registry")
    sub.add_parser("hypotheses")
    hs = sub.add_parser("hypothesis-sample")
    hs.add_argument("id")
    hs.add_argument("--n", type=int, default=30)
    lv = sub.add_parser("live")
    lv.add_argument("--port", type=int, default=8787)
    rs = sub.add_parser("rescreen")
    rs.add_argument("--profile", default="balanced", choices=list(PROFILES))
    rs.add_argument("--rules-only", action="store_true", help="re-apply the code rules to current inclusions (free)")
    pub = sub.add_parser("publish")
    pub.add_argument("-m", "--message", default=None)
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
        print(f"spent today ${db.spent(con, db.budget_day()):.4f} (day starts 9:00 Eastern), total ${db.spent(con):.4f}")
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
    elif args.cmd == "recheck-registry":
        con.execute("DELETE FROM registry_checks")  # derived data: the night shift compares every trial again (free)
        con.commit()
        print("registry comparisons cleared; the night shift will redo them")
    elif args.cmd == "hypotheses":
        from .hypotheses import run_all
        for r in run_all(con):
            print(f"{r['id']}  {r['status']:13s} {r['summary']}")
        export(con)
    elif args.cmd == "hypothesis-sample":
        from .hypotheses import sample_yaml
        print(sample_yaml(con, args.id.upper(), args.n))
    elif args.cmd == "live":
        from .live import serve
        serve(args.port)
    elif args.cmd == "rescreen" and args.rules_only:
        from .screen import apply_rules
        changed = apply_rules(con)
        print(f"{len(changed)} inclusions changed by the rules: {', '.join(changed)}")
        export(con)
    elif args.cmd == "rescreen":
        from .llm import Budget, Claude
        from .pipeline import _paper
        from .screen import PROMPT_VERSION, screen_paper
        prof = PROFILES[args.profile]
        claude = Claude(con, Budget(prof["daily_usd"], prof["total_usd"]))
        rows = con.execute("SELECT p.* FROM papers p JOIN screenings s ON s.pmid = p.pmid AND s.id = (SELECT MAX(id) "
                           "FROM screenings WHERE pmid = p.pmid) WHERE s.prompt_version != ?", (PROMPT_VERSION,)).fetchall()
        changed = []
        for row in rows:
            old = con.execute("SELECT decision FROM screenings WHERE pmid=? ORDER BY id DESC LIMIT 1", (row["pmid"],)).fetchone()[0]
            new = screen_paper(con, claude, prof["screen_model"], _paper(row))["decision"]
            if new != old:
                changed.append(f"{row['pmid']} {old} -> {new}: {row['title'][:90]}")
        print(f"re-screened {len(rows)} papers with {PROMPT_VERSION}; {len(changed)} decisions changed")
        print("\n".join(changed))
        export(con)
    elif args.cmd == "reverify":
        from .pipeline import _paper
        from .verify import verify_paper
        tot = {"verified": 0, "needs_review": 0}
        for row in con.execute("SELECT DISTINCT pmid FROM extractions").fetchall():
            ex = {r["pass"]: json.loads(r["result"]) for r in con.execute(
                "SELECT pass, result FROM extractions WHERE pmid=? AND id IN (SELECT MAX(id) FROM extractions "
                "WHERE pmid=? GROUP BY pass)", (row["pmid"], row["pmid"]))}
            if 1 not in ex:
                continue
            paper = _paper(con.execute("SELECT * FROM papers WHERE pmid=?", (row["pmid"],)).fetchone())
            for k, v in verify_paper(con, paper, ex[1], ex.get(2)).items():
                tot[k] += v
        print(json.dumps(tot))
        export(con)
    elif args.cmd == "publish":
        from .publish import publish
        msg = publish(con, args.message)
        print(f"published: {msg}" if msg else "nothing new to publish")
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
