import { useState } from "react";
import { SITE } from "./config";
import { DATA, useData, type HypothesisEntry } from "./data";

const STATUS: Record<string, { label: string; cls: string }> = {
  waiting: { label: "Waiting for data", cls: "needs_review" }, inconclusive: { label: "Inconclusive", cls: "needs_review" },
  supported: { label: "Supported", cls: "verified" }, refuted: { label: "Refuted", cls: "rejected" },
  not_supported: { label: "Not supported", cls: "rejected" }, withdrawn: { label: "Withdrawn", cls: "rejected" },
};
const ORDER = ["supported", "inconclusive", "not_supported", "refuted", "waiting", "withdrawn"];

function Card({ h }: { h: HypothesisEntry }) {
  const [open, setOpen] = useState(false);
  const st = STATUS[h.latest?.status ?? "waiting"];
  const gh = SITE.repo ? `${SITE.repo}/blob/main/${h.file}` : null;
  const history = SITE.repo ? `${SITE.repo}/commits/main/${h.file}` : null;
  return (
    <article className="hyp">
      <header className="hyp-head">
        <span className="hyp-id">{h.id}</span>
        <h2>{h.title}</h2>
        <span className={`badge-st ${st.cls}`}>{st.label}</span>
      </header>
      <p className="hyp-claim">{h.claim}</p>
      {h.latest && <p className="hyp-result"><strong>Result:</strong> {h.latest.summary}
        <span className="muted small"> (tested {h.latest.tested})</span></p>}
      <p className="muted small">
        Registered {h.registered}, before testing.{" "}
        {gh && <><a href={gh} target="_blank" rel="noreferrer">Registration</a> · </>}
        {history && <a href={history} target="_blank" rel="noreferrer">its history on GitHub</a>}
        {" "}· <button className="linkish" onClick={() => setOpen(!open)}>{open ? "Hide the method" : "Show the method"}</button>
      </p>
      {open && (
        <dl className="hyp-method">
          <dt>Why it matters</dt><dd>{h.why}</dd>
          <dt>Population</dt><dd>{h.population}</dd>
          <dt>Measure</dt><dd>{h.measure}</dd>
          <dt>Test (fixed in advance)</dt><dd>{h.test}</dd>
          <dt>Decision rule</dt><dd>{h.decision}</dd>
          <dt>What was seen before registering</dt><dd>{h.disclosure}</dd>
          {(h.amendments ?? []).length > 0 && <><dt>Amendments</dt><dd>{h.amendments.map((a, i) =>
            <div key={i}>{typeof a === "string" ? a : JSON.stringify(a)}</div>)}</dd></>}
          {h.history.length > 0 && <><dt>Earlier results</dt><dd>{h.history.map((r, i) =>
            <div key={i}>{r.tested}: {STATUS[r.status]?.label ?? r.status}. {r.summary}</div>)}</dd></>}
        </dl>
      )}
    </article>
  );
}

export function HypothesesPage() {
  const hs = useData<HypothesisEntry[]>(DATA.hypotheses);
  const count = (s: string) => (hs ?? []).filter((h) => (h.latest?.status ?? "waiting") === s).length;
  return (
    <article className="prose wide">
      <h1>Hypotheses</h1>
      <p className="lede">
        Reading more papers doesn't produce discoveries; testing does. Each question I investigate is written down
        <strong> before</strong> it is tested, with the exact test and the result that would disprove it, and committed to
        GitHub so the timestamp is public. The tests are code, not opinions. Every result is published, including the
        ones that fail.
      </p>
      <section className="tiles">
        {[["Registered", hs?.length ?? 0], ["Waiting for data", count("waiting")],
          ["Tested", (hs?.length ?? 0) - count("waiting")], ["Supported", count("supported")]].map(([label, v]) => (
          <div className="tile" key={label as string}><div className="tile-v">{v}</div><div className="tile-l">{label}</div></div>
        ))}
      </section>
      <p className="muted small">
        A supported hypothesis is a candidate finding, not a discovery: it still needs a search for prior work and an
        expert's review. The rules are in the{" "}
        {SITE.repo ? <a href={`${SITE.repo}/blob/main/research/hypotheses/README.md`} target="_blank" rel="noreferrer">ledger's README</a>
          : "ledger's README"}.
      </p>
      {hs === undefined ? <p className="muted">Loading…</p> : !hs?.length ? <p className="muted">No hypotheses registered yet.</p>
        : [...hs].sort((a, b) => ORDER.indexOf(a.latest?.status ?? "waiting") - ORDER.indexOf(b.latest?.status ?? "waiting")
          || a.id.localeCompare(b.id)).map((h) => <Card key={h.id} h={h} />)}
    </article>
  );
}
