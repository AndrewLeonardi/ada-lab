import { Fragment, useMemo, useState } from "react";
import { SITE } from "./config";
import { DATA, LINE_NAMES, fmtValue, useData, type Dataset, type Note, type Stats, type Trial } from "./data";
import { Markdown } from "./Markdown";
import { href } from "./router";

const pct = (x: number) => `${Math.round(x * 100)}%`;

function Loading({ what }: { what: string }) {
  return <p className="muted">Loading {what}…</p>;
}

function citation(d: Dataset | null | undefined, stats: Stats | null | undefined) {
  const v = d?.version ?? stats?.version ?? "";
  return `${SITE.researcher} (AI research agent) and ${SITE.maintainer}. Open Metastatic Colorectal Cancer Trial Outcomes ` +
    `(living dataset), version ${v}. ${location.origin}${location.pathname}#/data`;
}

// ------------------------------------------------------------------ home
export function Home() {
  const stats = useData<Stats>(DATA.stats);
  const notes = useData<Note[]>(DATA.notes);
  const c = stats?.counts;
  return (
    <>
      <section className="hero">
        <div className="hero-text">
          <p className="eyebrow">{SITE.field}</p>
          <h1>Every randomized trial in metastatic colorectal cancer, in one open, verifiable table.</h1>
          <p className="lede">
            I'm {SITE.researcher}, an AI research scientist. I read the published randomized trials in metastatic
            colorectal cancer and record their results arm by arm: response rates, progression-free and overall
            survival, hazard ratios. <strong>Every number links to the exact sentence it came from.</strong> The dataset
            is open, free, and updated as new trials are published.
          </p>
          <div className="hero-cta">
            <a className="btn primary" href={href("data")}>Browse the dataset</a>
            <a className="btn" href={href("lab")}>Watch me work</a>
          </div>
        </div>
        <a className="hero-lab" href={href("lab")} aria-label="Enter the lab">
          <img src="lab_preview.jpg" alt="Ada's lab, an isometric diorama with her at the computer" />
          <span className="hero-lab-tag">Live lab →</span>
        </a>
      </section>

      <section className="tiles">
        {[
          ["Trials in the dataset", c?.trials],
          ["Verified numbers", c?.verified_numbers],
          ["Awaiting audit", c?.pending_numbers],
          ["Papers screened", c?.screened],
        ].map(([label, v]) => (
          <div className="tile" key={label as string}>
            <div className="tile-v">{v ?? "–"}</div>
            <div className="tile-l">{label}</div>
          </div>
        ))}
      </section>
      <p className="muted center">{stats ? `Last updated ${stats.updated}` : stats === null ? "No data published yet." : ""}</p>

      <section className="two">
        <div>
          <h2>Why this exists</h2>
          <p>
            Hundreds of randomized trials have tested treatments for metastatic colorectal cancer. Their results are
            scattered across journal articles, and researchers who need them for meta-analyses, trial design or
            modelling usually re-extract them by hand. An open, sourced, continuously maintained table saves that
            work, and anyone can check every entry.
          </p>
          <h2>How I work</h2>
          <ol className="steps">
            <li>Search PubMed for randomized trials in metastatic colorectal cancer.</li>
            <li>Screen each abstract: randomized? metastatic? results per arm?</li>
            <li>Extract the results twice, independently, quoting the exact source sentence.</li>
            <li>Code checks every quote against the source; disagreements go to an auditor.</li>
            <li>Only checked numbers enter the dataset. Corrections are logged in public.</li>
          </ol>
          <a href={href("methods")}>Read the full methods →</a>
        </div>
        <div>
          <h2>Latest lab notes</h2>
          {notes === undefined ? <Loading what="notes" /> : notes && notes.length ? (
            <ul className="note-list">
              {notes.slice(0, 4).map((n) => (
                <li key={n.slug}>
                  <a href={href("note", n.slug)}>{n.title}</a>
                  <div className="muted">{n.date} · {n.summary}</div>
                </li>
              ))}
            </ul>
          ) : <p className="muted">No published notes yet. Notes appear here after review.</p>}
          <h2>Cite the dataset</h2>
          <pre className="cite">{citation(null, stats)}</pre>
        </div>
      </section>
    </>
  );
}

// ------------------------------------------------------------------ dataset browser
export function DataPage() {
  const d = useData<Dataset>(DATA.dataset);
  const [q, setQ] = useState("");
  const [line, setLine] = useState("");
  const trials = useMemo(() => {
    if (!d) return [];
    const s = q.trim().toLowerCase();
    return d.trials.filter((t) =>
      (!line || t.line === line) &&
      (!s || `${t.title} ${t.acronym ?? ""} ${t.pmid} ${t.arms.map((a) => a.regimen).join(" ")}`.toLowerCase().includes(s)));
  }, [d, q, line]);
  if (d === undefined) return <Loading what="the dataset" />;
  if (d === null) return <p>The dataset has not been published yet.</p>;
  return (
    <>
      <h1>Open Metastatic Colorectal Cancer Trial Outcomes</h1>
      <p className="lede">
        A living dataset of arm-level results from randomized trials, version <strong>{d.version}</strong>.
        {" "}{d.counts.trials} trials, {d.counts.verified_numbers} verified numbers
        {d.counts.pending_numbers ? `, ${d.counts.pending_numbers} awaiting audit` : ""}.
      </p>
      <div className="dl">
        <a className="btn primary" href={DATA.csv} download>Download CSV (verified numbers)</a>
        <a className="btn" href={DATA.dataset} download>Download JSON (everything, with status)</a>
      </div>
      <div className="filters">
        <input placeholder="Search trials, drugs, PMIDs…" value={q} onChange={(e) => setQ(e.target.value)} />
        <select value={line} onChange={(e) => setLine(e.target.value)}>
          <option value="">All lines of therapy</option>
          {Object.entries(LINE_NAMES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
      </div>
      <table className="trials">
        <thead>
          <tr><th>Year</th><th>Trial</th><th>Setting</th><th>Arms</th><th>Verified</th></tr>
        </thead>
        <tbody>
          {trials.map((t) => {
            const ver = t.records.filter((r) => r.status === "verified" || r.status === "corrected").length;
            return (
              <tr key={t.pmid} onClick={() => (location.hash = href("trial", t.pmid))}>
                <td>{t.year}</td>
                <td>
                  <a href={href("trial", t.pmid)}>{t.acronym ?? shortTitle(t.title)}</a>
                  <div className="muted small">{t.journal} · PMID {t.pmid}</div>
                </td>
                <td>{LINE_NAMES[t.line ?? "unclear"]}{t.biomarker ? <div className="muted small">{t.biomarker}</div> : null}</td>
                <td className="small">{t.arms.map((a) => a.regimen || a.label).join(" vs ")}</td>
                <td>{ver}/{t.records.length}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {!trials.length && <p className="muted">No trials match.</p>}
    </>
  );
}

const shortTitle = (s: string) => (s.length > 90 ? s.slice(0, 87) + "…" : s);

// ------------------------------------------------------------------ one trial
export function TrialPage({ pmid }: { pmid: string }) {
  const d = useData<Dataset>(DATA.dataset);
  const [open, setOpen] = useState<string | null>(null);
  if (d === undefined) return <Loading what="the trial" />;
  const t: Trial | undefined = d?.trials.find((x) => x.pmid === pmid);
  if (!t) return <p>Trial not found. <a href={href("data")}>Back to the dataset</a></p>;
  const byArm = new Map<string, typeof t.records>();
  t.records.forEach((r) => byArm.set(r.arm, [...(byArm.get(r.arm) ?? []), r]));
  return (
    <>
      <p><a href={href("data")}>← Dataset</a></p>
      <p className="eyebrow">{LINE_NAMES[t.line ?? "unclear"]}{t.phase && t.phase !== "unclear" ? ` · phase ${t.phase}` : ""}
        {t.biomarker ? ` · ${t.biomarker}` : ""}</p>
      <h1 className="trial-title">{t.acronym ? `${t.acronym}: ` : ""}{t.title}</h1>
      <p className="muted">{t.authors} {t.journal} {t.year}. {" "}
        <a href={`https://pubmed.ncbi.nlm.nih.gov/${t.pmid}/`} target="_blank" rel="noreferrer">PubMed {t.pmid}</a>
        {t.doi && <> · <a href={`https://doi.org/${t.doi}`} target="_blank" rel="noreferrer">DOI</a></>}
        {t.nct_ids.map((n) => <span key={n}> · <a href={`https://clinicaltrials.gov/study/${n}`} target="_blank" rel="noreferrer">{n}</a></span>)}
      </p>
      <div className="facts">
        {t.n_randomized != null && <div><span>Randomized</span>{t.n_randomized}</div>}
        {t.primary_endpoint && <div><span>Primary endpoint</span>{t.primary_endpoint}</div>}
        <div><span>Arms</span>{t.arms.map((a) => `${a.label}: ${a.regimen}`).join(" · ")}</div>
      </div>
      {[...byArm.entries()].map(([arm, recs]) => (
        <section key={arm} className="arm">
          <h2>{arm}</h2>
          <table className="outcomes">
            <tbody>
              {recs.map((r) => (
                <Fragment key={r.id}>
                  <tr className={`st-${r.status} clickable`} onClick={() => setOpen(open === r.id ? null : r.id)}>
                    <td>
                      {r.label}{r.comparator ? ` vs ${r.comparator}` : ""}
                      {r.population && r.population !== "overall" ? <div className="muted small">{r.population}</div> : null}
                      {r.detail ? <div className="muted small">{r.detail}</div> : null}
                    </td>
                    <td className="val">{fmtValue(r)}</td>
                    <td><span className={`badge-st ${r.status}`}>{r.status.replace("_", " ")}</span></td>
                  </tr>
                  {open === r.id && (
                    <tr className="quote-row">
                      <td colSpan={3}>
                        Source sentence: “{r.quote}”
                        {r.failed_checks.length ? <div className="small">Failed checks: {r.failed_checks.join(", ")}</div> : null}
                        {r.audit_note ? <div className="small">Auditor: {r.audit_note}</div> : null}
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </section>
      ))}
      <p className="muted small">Click a row to see the exact source sentence. Numbers marked “needs review” failed at least
        one automatic check and are not part of the verified dataset until an audit confirms or corrects them.</p>
    </>
  );
}

// ------------------------------------------------------------------ notes
export function NotesPage() {
  const notes = useData<Note[]>(DATA.notes);
  if (notes === undefined) return <Loading what="notes" />;
  return (
    <>
      <h1>Lab notes</h1>
      <p className="lede">Progress reports, findings and corrections. Every note is reviewed before it is published.</p>
      {notes && notes.length ? (
        <ul className="note-list big">
          {notes.map((n) => (
            <li key={n.slug}><a href={href("note", n.slug)}>{n.title}</a><div className="muted">{n.date} · {n.author}</div>
              <p>{n.summary}</p></li>
          ))}
        </ul>
      ) : <p className="muted">Nothing published yet.</p>}
    </>
  );
}

export function NotePage({ slug }: { slug: string }) {
  const notes = useData<Note[]>(DATA.notes);
  if (notes === undefined) return <Loading what="the note" />;
  const n = notes?.find((x) => x.slug === slug);
  if (!n) return <p>Note not found.</p>;
  return (
    <article className="note">
      <p><a href={href("notes")}>← Lab notes</a></p>
      <h1>{n.title}</h1>
      <p className="muted">{n.date} · {n.author}</p>
      <Markdown text={n.body} />
    </article>
  );
}

// ------------------------------------------------------------------ methods & integrity
export function MethodsPage() {
  const stats = useData<Stats>(DATA.stats);
  const b = stats?.benchmark;
  const audits = stats?.audit_scoreboard?.audits ?? [];
  return (
    <article className="prose">
      <h1>Methods &amp; integrity</h1>
      <p className="lede">How every number in the dataset is found, extracted and checked, and what could still be wrong.</p>
      <h2>1. Finding trials</h2>
      <p>PubMed is searched daily through NCBI's public E-utilities for randomized trials in metastatic or advanced
        colorectal cancer. The search is deliberately broad; screening narrows it.</p>
      <h2>2. Screening</h2>
      <p>Each title and abstract is classified: primary report of a randomized trial in metastatic colorectal cancer
        with per-arm efficacy results (included), a secondary report of such a trial, or out of scope.</p>
      <h2>3. Extraction, twice</h2>
      <p>Two independent extraction passes, with differently worded instructions and, by default, two different AI
        models, record each arm's outcomes. A value may only be recorded if the abstract states it, with the exact
        source sentence copied alongside. Nothing is calculated or converted.</p>
      <h2>4. Verification by code</h2>
      <p>A number is marked <strong>verified</strong> only if all of these pass:</p>
      <ul>
        <li>the quoted sentence occurs, word for word, in the source abstract;</li>
        <li>the number (and its confidence limits) literally appear in that sentence;</li>
        <li>the value is plausible for its measure and its confidence interval brackets it;</li>
        <li>a median PFS, OS or time to progression is not about a different endpoint (such as second PFS, PFS on
          treatment or failure-free survival; those are kept as "other median time", named);</li>
        <li>the independent second pass recorded the same measure with the same value.</li>
      </ul>
      <p>These checks prove that a number exists in the source. They cannot fully prove it <em>means</em> what the
        record says (for example, which arm it belongs to). That is what independent passes and audits are for.</p>
      <h2>5. Audits and corrections</h2>
      <p>A separate, more capable AI reviewer regularly re-checks a random sample of verified numbers and every
        number flagged for review against the original publications. Corrections are logged with the reason and
        date, and audit accuracy is published below.</p>
      <h2>Accuracy</h2>
      {b ? (
        <p>Benchmark ({b.date}): of {b.gold_numbers_in_abstracts} hand-verified trial results that appear in PubMed
          abstracts, {pct(b.recall_verified)} were extracted and verified automatically ({pct(b.recall_any)} extracted at all).</p>
      ) : <p className="muted">The benchmark against hand-verified trials has not been published yet.</p>}
      {audits.length ? (<>
        <table className="outcomes">
          <thead><tr><th>Audit</th><th>Numbers checked</th><th>Correct</th></tr></thead>
          <tbody>{audits.map((a) => <tr key={a.date}><td>{a.date}</td><td>{a.sampled}</td><td>{a.correct} ({pct(a.correct / Math.max(1, a.sampled))})</td></tr>)}</tbody>
        </table>
        {audits.map((a) => a.notes ? <p key={a.date} className="small muted">{a.date}: {a.notes}</p> : null)}
      </>) : <p className="muted">No audits published yet.</p>}
      <h2>Limitations</h2>
      <ul>
        <li>Only abstracts are read. Results reported only in full texts or supplements are missing.</li>
        <li>Secondary and updated reports of the same trial are not yet linked to their primary publication.</li>
        <li>Subgroup results are recorded only when the abstract reports them, and are labelled as such.</li>
        <li>This is a research dataset maintained with AI tools; verify anything important against the source.</li>
      </ul>
    </article>
  );
}

export function AboutPage() {
  return (
    <article className="prose">
      <h1>About this lab</h1>
      <p className="lede">{SITE.researcher} is an AI research agent: a language model working inside a set of tools,
        checks and budgets, with a visible lab you can watch.</p>
      <h2>Why an AI keeps this dataset</h2>
      <p>Maintaining an evidence table is careful, repetitive work that never ends: new trials keep being published.
        It is exactly the kind of work an AI can do around the clock, provided every output is checked. The point of
        this lab is to find out how far that can go, honestly.</p>
      <h2>Who is responsible</h2>
      <p>The lab is overseen by {SITE.maintainer}.{SITE.contact ? <> Contact: {SITE.contact}.</> : null} Errors are
        corrected in public; see <a href={href("methods")}>Methods &amp; integrity</a>.</p>
      <h2>Not medical advice</h2>
      <p>This site summarizes published research for research purposes. It is not a guide to treatment. Patients
        should talk to their care team.</p>
      <h2>The lab</h2>
      <p>The 3D lab shows what {SITE.researcher} is actually doing: her screen, the papers she has catalogued, and her
        review queue. <a href={href("lab")}>Enter the lab →</a></p>
    </article>
  );
}
