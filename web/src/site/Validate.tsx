import { useEffect, useMemo, useState } from "react";
import { SITE } from "./config";
import { DATA, fmtValue, useData, type Dataset, type OutcomeRecord } from "./data";
import { href } from "./router";

// Blind human validation (dataset protocol section 10): find each number in the abstract yourself, then see Ada's.
// Answers stay in this browser and can be downloaded as a file to send back.

interface Item {
  id: string; pmid: string; trial: string | null; title: string; arm: string; comparator: string | null;
  measure: string; label: string; population: string; detail: string | null; unit: string;
}
interface Sample { name: string; seed: string; drawn: string; pool: number; items: Item[]; results: { agree: number; answered: number } | null }
interface Answer { value: number | null; not_stated: boolean; note: string }

const KEY = (s: string) => `ada-validation:${s}`;
const load = (s: string): Record<string, Answer> => { try { return JSON.parse(localStorage.getItem(KEY(s)) ?? "{}"); } catch { return {}; } };
const save = (s: string, a: Record<string, Answer>) => { try { localStorage.setItem(KEY(s), JSON.stringify(a)); } catch { /* private mode */ } };

export function ValidatePage() {
  const samples = useData<Sample[]>(DATA.validation);
  const dataset = useData<Dataset>(DATA.dataset);
  const sample = samples?.[samples.length - 1];
  const [answers, setAnswers] = useState<Record<string, Answer>>({});
  const [i, setI] = useState(0);
  const [value, setValue] = useState("");
  const [notStated, setNotStated] = useState(false);
  const [note, setNote] = useState("");
  const [who, setWho] = useState(() => { try { return localStorage.getItem("ada-validation:name") ?? ""; } catch { return ""; } });

  useEffect(() => { if (sample) setAnswers(load(sample.name)); }, [sample?.name]);
  const records = useMemo(() => {
    const m = new Map<string, OutcomeRecord>();
    dataset?.trials.forEach((t) => t.records.forEach((r) => m.set(r.id, r)));
    return m;
  }, [dataset]);

  if (samples === undefined) return <p className="muted">Loading…</p>;
  if (!sample) return (
    <article className="prose"><h1>Validate</h1>
      <p>No validation sample has been drawn yet. It is drawn at random from the published numbers before a release
        (see the <a href={href("paper")}>paper page</a>).</p></article>);

  const item = sample.items[i];
  const done = answers[item.id];
  const ada = records.get(item.id);
  const answered = sample.items.filter((it) => answers[it.id]).length;
  const agree = sample.items.filter((it) => {
    const a = answers[it.id], r = records.get(it.id);
    return a && r && !a.not_stated && a.value != null && Math.abs(a.value - r.value) < 1e-6;
  }).length;

  function submit() {
    const v = parseFloat(value.replace(",", "."));
    if (!notStated && Number.isNaN(v)) return;
    const next = { ...answers, [item.id]: { value: notStated ? null : v, not_stated: notStated, note } };
    setAnswers(next);
    save(sample!.name, next);
  }
  function go(k: number) {
    setI(Math.max(0, Math.min(sample!.items.length - 1, k)));
    setValue(""); setNotStated(false); setNote("");
  }
  function download() {
    const blob = new Blob([JSON.stringify({ sample: sample!.name, validator: who, saved: new Date().toISOString(), answers }, null, 1)],
      { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `ada-validation-${sample!.name}.json`;
    a.click();
  }
  const where = `${item.label}${item.detail ? ` (${item.detail})` : ""}`;
  return (
    <article className="prose wide">
      <h1>Validate</h1>
      <p className="lede">
        Help check Ada's work, blind. For each number, open the paper's abstract on PubMed, find the value yourself, and
        enter it. Only then will you see what Ada recorded. Use only the abstract, and the definitions in the{" "}
        {SITE.repo ? <a href={`${SITE.repo}/blob/main/research/protocol/dataset-protocol-v1.md#5-data-items`} target="_blank"
          rel="noreferrer">protocol</a> : "protocol"}.
      </p>
      <p className="muted small">
        Sample "{sample.name}": {sample.items.length} numbers drawn at random (seed {sample.seed}) on {sample.drawn} from
        {" "}{sample.pool.toLocaleString()} published ones. Your answers stay in this browser until you download them.
      </p>
      <label className="small">Your name (for the record):{" "}
        <input value={who} onChange={(e) => { setWho(e.target.value); try { localStorage.setItem("ada-validation:name", e.target.value); } catch { /* */ } }} />
      </label>
      <div className="meter-bar"><span style={{ width: `${(100 * answered) / sample.items.length}%` }} /></div>
      <p className="muted small">{answered} of {sample.items.length} answered{answered ? ` · ${agree} agree with Ada` : ""}</p>

      <section className="val-card">
        <p className="muted small">Number {i + 1} of {sample.items.length}</p>
        <h2>{item.trial ? `${item.trial}: ` : ""}{item.title}</h2>
        <p><a href={`https://pubmed.ncbi.nlm.nih.gov/${item.pmid}/`} target="_blank" rel="noreferrer">Open the abstract
          on PubMed (PMID {item.pmid}) ↗</a></p>
        <p className="val-ask">Find: <strong>{where}</strong> for the arm <strong>“{item.arm}”</strong>
          {item.comparator ? <> versus <strong>“{item.comparator}”</strong></> : null}
          {item.population !== "overall" ? <>, in the <strong>{item.population}</strong> subgroup</> : <>, in the whole trial population</>}.
          {" "}Unit: {item.unit}.</p>
        {!done ? (
          <div className="val-form">
            <input type="text" inputMode="decimal" placeholder="value" value={value} disabled={notStated}
              onChange={(e) => setValue(e.target.value)} onKeyDown={(e) => e.key === "Enter" && submit()} />
            <label className="small"><input type="checkbox" checked={notStated} onChange={(e) => setNotStated(e.target.checked)} />
              {" "}Not stated in the abstract</label>
            <input type="text" placeholder="note (optional)" value={note} onChange={(e) => setNote(e.target.value)} />
            <button className="btn primary" onClick={submit}>Save my answer</button>
          </div>
        ) : (
          <div className="val-reveal">
            <p>You: <strong>{done.not_stated ? "not stated" : done.value}</strong>{done.note ? ` (${done.note})` : ""}</p>
            {ada ? <>
              <p>Ada: <strong>{fmtValue(ada)}</strong>{" "}
                {(!done.not_stated && done.value != null && Math.abs(done.value - ada.value) < 1e-6)
                  ? <span className="badge-st verified">agree</span> : <span className="badge-st needs_review">differ</span>}</p>
              <p className="muted small">Her source sentence: “{ada.quote}”</p>
            </> : <p className="muted small">Ada's record is no longer in the published dataset (it may have been corrected or removed).</p>}
          </div>
        )}
        <div className="val-nav">
          <button className="btn" onClick={() => go(i - 1)} disabled={i === 0}>← Previous</button>
          <button className="btn" onClick={() => go(i + 1)} disabled={i === sample.items.length - 1}>Next →</button>
        </div>
      </section>
      <p>
        <button className="btn primary" onClick={download} disabled={!answered}>Download my answers</button>{" "}
        <span className="muted small">Send the file to the maintainer; the disagreements are then checked against the source.</span>
      </p>
    </article>
  );
}
