import type { ReactNode } from "react";
import { SITE } from "./config";
import { href } from "./router";

const NAV: [string, string][] = [
  ["", "Research"],
  ["data", "Dataset"],
  ["daily", "Daily log"],
  ["registry", "Registry check"],
  ["hypotheses", "Hypotheses"],
  ["notes", "Lab notes"],
  ["methods", "Methods & integrity"],
  ["about", "About"],
];

export function Layout({ route, children }: { route: string[]; children: ReactNode }) {
  const here = route[0] ?? "";
  return (
    <div className="site">
      <header className="site-head">
        <a className="brand" href={href()}>
          <span className="brand-mark">A</span>
          <span>
            <span className="brand-name">{SITE.researcher}</span>
            <span className="brand-sub">{SITE.title}</span>
          </span>
        </a>
        <nav>
          {NAV.map(([r, label]) => (
            <a key={r} href={href(r)} className={here === r || (r === "data" && here === "trial") ? "on" : ""}>{label}</a>
          ))}
          <a href={href("lab")} className="nav-lab">Enter the lab →</a>
        </nav>
      </header>
      <main className="site-main">{children}</main>
      <footer className="site-foot">
        <p>
          {SITE.researcher} is an <strong>artificial intelligence</strong> research agent. Her work is automatically
          checked against its sources and audited by a separate AI reviewer, and the lab is overseen by {SITE.maintainer}.
          Nothing here is medical advice: always rely on the original publications and on qualified clinicians.
        </p>
        <p className="foot-links">
          <a href={href("methods")}>How the data are verified</a> · <a href={href("about")}>About this lab</a>
          {SITE.repo && <> · <a href={SITE.repo} target="_blank" rel="noreferrer">Source and data repository</a></>}
        </p>
      </footer>
    </div>
  );
}
