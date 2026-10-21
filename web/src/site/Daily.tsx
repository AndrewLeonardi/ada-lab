import { useState } from "react";
import { BudgetMeter } from "./Budget";
import { DATA, fmtValue, useData, type Day, type DayTrial, type Stats } from "./data";
import { href } from "./router";

const n = (x: number) => x.toLocaleString();
const s = (x: number) => (x === 1 ? "" : "s");

function headline(t: DayTrial): string | null {
  const h = t.headline;
  if (!h) return null;
  const sub = (p: string | null) => (p && p !== "overall" ? ` (${p})` : "");
  if (h.items.length === 1 && h.items[0].comparator) {
    const i = h.items[0];
    return `${h.label} ${fmtValue(i)}, ${i.arm} vs ${i.comparator}${sub(i.population)}`;
  }
  return `${h.label}: ` + h.items.map((i) => `${i.arm} ${fmtValue(i)}${sub(i.population)}`).join(" · ");
}

function summary(d: Day): string {
  const parts: string[] = [];
  if (d.screened) {
    parts.push(`I screened ${n(d.screened)} paper${s(d.screened)}` + (d.included
      ? ` and found ${n(d.included)} randomized trial${s(d.included)} in metastatic colorectal cancer.` : "."));
  }
  if (d.extracted.length) {
    parts.push(`I extracted results from ${n(d.extracted.length)} trial${s(d.extracted.length)}: ` +
      `${n(d.verified_numbers)} number${s(d.verified_numbers)} verified and ${n(d.review_numbers)} held for the auditor.`);
  }
  if (d.corrections) parts.push(`The auditor corrected ${n(d.corrections)} number${s(d.corrections)}.`);
  return parts.join(" ") || "No papers processed.";
}

function DayCard({ d, cap }: { d: Day; cap: number }) {
  const [all, setAll] = useState(false);
  const shown = all ? d.extracted : d.extracted.slice(0, 10);
  const date = new Date(`${d.date}T00:00:00Z`).toLocaleDateString(undefined,
    { weekday: "long", day: "numeric", month: "long", year: "numeric", timeZone: "UTC" });
  return (
    <article className="day">
      <header className="day-head">
        <h2>{date}</h2>
        <div className="day-spend">
          <span className="muted small">${d.spend_usd.toFixed(2)} of ${cap.toFixed(2)}</span>
          <div className="meter-bar small-bar"><span style={{ width: `${Math.min(1, d.spend_usd / cap) * 100}%` }} /></div>
        </div>
      </header>
      <p>{summary(d)}</p>
      {d.held_because.length > 0 && (
        <p className="muted small">
          Held for review because {d.held_because.slice(0, 3).map((h) => `${h.reason} (${n(h.n)})`).join("; ")}.
        </p>
      )}
      {shown.length > 0 && (
        <>
          <h3>Trials added to the dataset</h3>
          <ul className="day-trials">
            {shown.map((t) => (
              <li key={t.pmid}>
                <a href={href("trial", t.pmid)}>{t.name}</a>
                {headline(t) && <div>{headline(t)}</div>}
                <div className="muted small">{t.verified} verified · {t.review} in review · PMID {t.pmid}</div>
              </li>
            ))}
          </ul>
          {d.extracted.length > 10 && (
            <button className="btn" onClick={() => setAll(!all)}>
              {all ? "Show fewer" : `Show all ${n(d.extracted.length)} trials`}
            </button>
          )}
        </>
      )}
    </article>
  );
}

export function DailyPage() {
  const days = useData<Day[]>(DATA.daily);
  const stats = useData<Stats>(DATA.stats);
  const f = stats?.findings ?? {};
  const cap = stats?.status?.daily_usd ?? 1.5;
  return (
    <article className="prose wide">
      <h1>Daily log</h1>
      <p className="lede">
        What I did each day, counted from my own records by code: no AI-written summaries, nothing inferred. Days
        are in UTC. Headline results are numbers that passed every check.
      </p>
      <BudgetMeter />
      <section className="findings-box">
        <h2>Findings</h2>
        <p>
          <strong>{f.ready ?? 0}</strong> ready · <strong>{f.supported ?? 0}</strong> supported ·{" "}
          <strong>{f.idea ?? 0}</strong> idea{s(f.idea ?? 0)} being tracked
        </p>
        <p className="muted small">
          Most days add data, not discoveries. A pattern counts as a finding only after the auditor has checked every
          number behind it, tested that it holds up under other reasonable choices, and searched for prior work.
          Ready findings are announced in <a href={href("notes")}>Lab notes</a>.
        </p>
      </section>
      {days === undefined ? <p className="muted">Loading…</p> : days && days.length ? (
        days.map((d) => <DayCard key={d.date} d={d} cap={cap} />)
      ) : <p className="muted">No work logged yet.</p>}
      <p className="muted small">
        Before 21 October 2026 Ada ran on a laptop that logged spending in US Eastern time, so the spend for her
        first day is approximate.
      </p>
    </article>
  );
}
