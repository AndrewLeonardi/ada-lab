import { SITE } from "./config";
import { DATA, useData } from "./data";
import { href } from "./router";

interface Step { name: string; status: "done" | "doing" | "todo"; detail: string; progress: number | null }
interface Readiness { steps: Step[]; done: number; total: number }

const BADGE: Record<Step["status"], { label: string; cls: string }> = {
  done: { label: "Done", cls: "verified" }, doing: { label: "In progress", cls: "needs_review" }, todo: { label: "To do", cls: "rejected" },
};

export function PaperPage() {
  const r = useData<Readiness>(DATA.paper);
  return (
    <article className="prose wide">
      <h1>Toward a paper</h1>
      <p className="lede">
        The goal: a peer-reviewed <strong>data descriptor</strong>, a paper whose contribution is this dataset: what is
        in it, how it was built, how accurate it is, and how others can use it. This page tracks what it still needs.
      </p>
      <p>
        The rules were fixed in advance in the{" "}
        {SITE.repo ? <a href={`${SITE.repo}/blob/main/research/protocol/dataset-protocol-v1.md`} target="_blank" rel="noreferrer">
          dataset protocol</a> : "dataset protocol"}, registered on GitHub before the first release. Before submission, a
        person re-checks a random sample of the numbers without seeing Ada's answers (<a href={href("validate")}>the
        validation form</a>). AI cannot be an author; the paper's authors would be people, with Ada's and the auditor's
        roles disclosed in the methods.
      </p>
      {r === undefined ? <p className="muted">Loading…</p> : !r ? <p className="muted">Not published yet.</p> : (
        <>
          <div className="meter-bar"><span style={{ width: `${(100 * r.done) / r.total}%` }} /></div>
          <p className="muted small">{r.done} of {r.total} steps done</p>
          <ol className="steps-list">
            {r.steps.map((s) => (
              <li key={s.name}>
                <div className="step-head"><strong>{s.name}</strong>
                  <span className={`badge-st ${BADGE[s.status].cls}`}>{BADGE[s.status].label}</span></div>
                <div className="muted small">{s.detail}</div>
                {s.progress != null && s.status !== "done" &&
                  <div className="meter-bar small-bar"><span style={{ width: `${100 * s.progress}%` }} /></div>}
              </li>
            ))}
          </ol>
        </>
      )}
    </article>
  );
}
