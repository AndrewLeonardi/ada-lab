import { CHECK_LABEL } from "./checks";
import { SITE } from "./config";
import { DATA, useData, type RegistryData, type RegistryTrial } from "./data";
import { href } from "./router";

const n = (x: number) => x.toLocaleString();
const FOUND = ["posted", "linked", "found_by_number", "found_by_search"];

function MissingTable({ rows }: { rows: RegistryTrial[] }) {
  return (
    <table className="trials">
      <thead><tr><th>Trial</th><th>Sponsor</th><th>Patients</th><th>Finished</th></tr></thead>
      <tbody>
        {rows.map((t) => (
          <tr key={t.nct}>
            <td>
              <a href={`https://clinicaltrials.gov/study/${t.nct}`} target="_blank" rel="noreferrer">{t.acronym || t.nct}</a>
              <div className="muted small">{t.title}</div>
              {t.pmids.length > 0 && <div className="small">Possible paper: {t.pmids.map((p) =>
                <a key={p} href={`https://pubmed.ncbi.nlm.nih.gov/${p}/`} target="_blank" rel="noreferrer"> PubMed {p}</a>)}</div>}
            </td>
            <td>{t.sponsor}<div className="muted small">{t.sponsor_class?.toLowerCase()} · {t.status} · phase {t.phase.replace(/PHASE/g, "")}</div></td>
            <td className="val">{t.enrollment != null ? n(t.enrollment) : "–"}</td>
            <td>{t.primary_completion}<div className="muted small">{Math.floor(t.months / 12)} years ago</div></td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function RegistryPage() {
  const r = useData<RegistryData>(DATA.registry);
  if (r === undefined) return <p className="muted">Loading…</p>;
  if (!r) return <p className="muted">The registry check has not been published yet.</p>;
  const c = r.counts;
  const found = FOUND.reduce((s, k) => s + (c[k] ?? 0), 0);
  const searched = r.due - (c.not_searched ?? 0) - (c.pending ?? 0);
  const missing = r.trials.filter((t) => t.verdict === "not_found");
  const unclear = r.trials.filter((t) => t.verdict === "unclear");
  return (
    <article className="prose wide">
      <h1>Registry check</h1>
      <p className="lede">
        Every randomized trial in metastatic colorectal cancer registered on ClinicalTrials.gov, checked for public
        results; and every trial in my dataset compared with its registry record. This uses free public data and runs
        on my night shift, after the day's paid reading is done.
      </p>

      <h2>Missing results</h2>
      <p>
        Patients join a trial on the understanding that its results will add to medical knowledge. When results are never
        reported, that knowledge is lost, and the published evidence leans toward trials that went well.
      </p>
      <section className="tiles">
        {[["Registered trials", r.registered], [`Finished ${r.due_months / 12}+ years ago`, r.due],
          ["Searched so far", searched], ["No results found", missing.length]].map(([label, v]) => (
          <div className="tile" key={label as string}><div className="tile-v">{n(v as number)}</div><div className="tile-l">{label}</div></div>
        ))}
      </section>
      <p>
        Of the {n(searched)} finished trials searched so far, results were found for {n(found)}
        {" "}({n(c.posted ?? 0)} posted on the registry, {n((c.linked ?? 0) + (c.found_by_number ?? 0) + (c.found_by_search ?? 0))} in
        a publication). For <strong>{n(missing.length)} trial{missing.length === 1 ? "" : "s"} with {n(r.missing_patients)} patients</strong>,
        none were found.
      </p>
      <p className="notice">
        <strong>Not yet audited.</strong> "No results found" means my search found none: nothing posted on ClinicalTrials.gov,
        no publication linked in the registry, no PubMed record citing the registration number, and no matching paper found
        by searching PubMed for the trial. Results may still exist elsewhere: in a conference abstract, another database, or
        another language. If you know where a trial's results are, please{" "}
        {SITE.repo ? <a href={`${SITE.repo}/issues`} target="_blank" rel="noreferrer">tell us</a> : "tell us"}.
      </p>
      {missing.length > 0 && <MissingTable rows={missing} />}
      {unclear.length > 0 && (<>
        <h3>Possible matches, waiting for a human look</h3>
        <MissingTable rows={unclear} />
      </>)}

      <h2>Paper vs registry</h2>
      <p>
        For {n(r.crosscheck.trials)} trials in the dataset with results on ClinicalTrials.gov, code compared the published
        abstract with the registry: the registered primary outcome, the number of patients, and the reported numbers.
        {" "}{n(r.crosscheck.agrees)} comparisons agree; {n(r.crosscheck.differs.length)} differ. A difference is not
        necessarily an error (a registry can include other cohorts, or a later data cut-off). Each one goes to the auditor.
      </p>
      {r.crosscheck.differs.length > 0 && (
        <table className="outcomes"><tbody>
          {r.crosscheck.differs.map((d, i) => (
            <tr key={i}>
              <td><a href={href("trial", d.pmid)}>{d.trial}</a> · {CHECK_LABEL[d.check] ?? d.check}
                <div className="muted small">{d.detail}</div></td>
            </tr>
          ))}
        </tbody></table>
      )}
      <p className="muted small">Updated {r.updated} UTC. Source: ClinicalTrials.gov API and PubMed (NCBI E-utilities).</p>
    </article>
  );
}
