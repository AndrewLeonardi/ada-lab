import { useEffect, useState } from "react";

// Static data files written by `ada export` into web/public/data/.

export interface OutcomeRecord {
  id: string;
  arm: string;
  measure: string;
  label: string;
  value: number;
  unit: string;
  ci_low: number | null;
  ci_high: number | null;
  comparator: string | null;
  population: string | null;
  detail: string | null;
  quote: string;
  status: "verified" | "corrected" | "needs_review" | "rejected";
  failed_checks: string[];
  audit_note?: string | null;
}

export interface Trial {
  pmid: string;
  title: string;
  journal: string;
  year: number | null;
  authors: string;
  doi: string;
  nct_ids: string[];
  acronym: string | null;
  phase: string | null;
  line: string | null;
  biomarker: string | null;
  n_randomized: number | null;
  primary_endpoint: string | null;
  arms: { label: string; regimen: string }[];
  records: OutcomeRecord[];
}

export interface Dataset {
  name: string;
  version: string;
  generated: string;
  counts: Counts;
  trials: Trial[];
}

export interface Counts {
  candidates: number;
  screened: number;
  included: number;
  trials: number;
  verified_numbers: number;
  pending_numbers: number;
  corrected_numbers: number;
}

export interface Stats {
  version: string;
  updated: string;
  counts: Counts;
  spend_usd_total: number;
  spend_usd_today: number;
  updated_at?: number; // epoch seconds of this export
  status?: { state: "working" | "resting" | "idle"; since: number; profile: string; daily_usd: number; total_usd: number } | null;
  findings?: Partial<Record<"idea" | "supported" | "ready", number>>;
  benchmark?: { date: string; gold_numbers_in_abstracts: number; recall_verified: number; recall_any: number };
  audit_scoreboard?: { audits: { date: string; sampled: number; correct: number; notes?: string }[] };
}

export interface DayTrial {
  pmid: string;
  name: string;
  verified: number;
  review: number;
  headline: { label: string; items: (Pick<OutcomeRecord, "arm" | "comparator" | "value" | "unit" | "ci_low" | "ci_high" | "population">)[] } | null;
}

export interface Day {
  date: string; // UTC
  spend_usd: number;
  screened: number;
  included: number;
  secondary: number;
  excluded: number;
  extracted: DayTrial[];
  verified_numbers: number;
  review_numbers: number;
  held_because: { reason: string; n: number }[];
  corrections: number;
}

export interface Note {
  slug: string;
  title: string;
  date: string;
  author: string;
  summary: string;
  body: string;
}

const cache = new Map<string, Promise<unknown>>();

function load<T>(path: string): Promise<T> {
  if (!cache.has(path)) {
    cache.set(path, fetch(path, { cache: "no-cache" }).then((r) => (r.ok ? r.json() : Promise.reject(r.status))));
  }
  return cache.get(path) as Promise<T>;
}

export function useData<T>(path: string): T | null | undefined {
  // undefined = loading, null = missing
  const [v, setV] = useState<T | null | undefined>(undefined);
  useEffect(() => {
    let alive = true;
    load<T>(path).then((d) => alive && setV(d)).catch(() => alive && setV(null));
    return () => { alive = false; };
  }, [path]);
  return v;
}

export const DATA = {
  dataset: "data/dataset.json",
  stats: "data/stats.json",
  notes: "data/notes.json",
  events: "data/events.json",
  daily: "data/daily.json",
  csv: "data/dataset.csv",
};

export const LINE_NAMES: Record<string, string> = {
  first: "First line", second: "Second line", third_or_later: "Third line or later", maintenance: "Maintenance",
  mixed: "Mixed lines", unclear: "Line unclear",
};

export function fmtValue(r: Pick<OutcomeRecord, "value" | "unit" | "ci_low" | "ci_high">): string {
  const u = r.unit === "percent" ? "%" : r.unit === "months" ? " mo" : r.unit === "weeks" ? " wk" : "";
  const ci = r.ci_low != null && r.ci_high != null ? ` (95% CI ${r.ci_low}–${r.ci_high})` : "";
  return `${r.value}${u}${ci}`;
}
