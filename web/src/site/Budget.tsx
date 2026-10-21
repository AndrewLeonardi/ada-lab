import { useEffect, useState } from "react";
import { liveBase } from "../world/live";
import { DATA, useData, type Stats } from "./data";

// Ada's spending and state, as of her server's last update (it publishes when she starts or stops working,
// and every 6 hours). Used on the website and in the lab.

const STALE_HOURS = 7;

function useMinuteClock() {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 30_000);
    return () => clearInterval(id);
  }, []);
  return now;
}

interface LiveState {
  state: "working" | "free_work" | "resting" | "idle" | null; daily_usd: number | null; total_usd: number | null;
  spend_today: number; spend_total: number; budget_day: string; resets_at: number; now: number;
}

/** Her state straight from her server, refreshed every 30 seconds (null if it can't be reached). */
function useLiveState(): LiveState | null {
  const [s, setS] = useState<LiveState | null>(null);
  useEffect(() => {
    const base = liveBase();
    if (!base) return;
    let alive = true;
    const poll = () => fetch(`${base}/live/state`, { cache: "no-store" }).then((r) => (r.ok ? r.json() : null))
      .catch(() => null).then((v) => alive && setS(v));
    poll();
    const id = setInterval(poll, 30_000);
    return () => { alive = false; clearInterval(id); };
  }, []);
  return s;
}

export function ago(seconds: number): string {
  if (seconds < 90) return "just now";
  if (seconds < 3600) return `${Math.round(seconds / 60)} min ago`;
  if (seconds < 48 * 3600) return `${Math.round(seconds / 3600)} h ago`;
  return `${Math.round(seconds / 86400)} days ago`;
}

function until(ts: number, now: number): string {
  const min = Math.max(0, Math.round((ts * 1000 - now) / 60000));
  return min >= 60 ? `${Math.floor(min / 60)} h ${min % 60} min` : `${min} min`;
}

// Her working day runs 9:00 to 9:00 US Eastern; it's named after the date it starts.
const workingDay = (now: number) => new Date(now - 9 * 3600_000).toLocaleDateString("en-CA", { timeZone: "America/New_York" });

export interface BudgetView {
  tone: "working" | "free" | "resting" | "idle" | "quiet";
  short: string; // for the lab's header
  headline: string;
  detail: string;
  spend: number;
  cap: number;
  frac: number;
  totalSpend: number;
  totalCap: number;
  updated: string;
}

export function useBudget(): BudgetView | null {
  const published = useData<Stats>(DATA.stats);
  const live = useLiveState();
  const now = useMinuteClock();
  // the live state, when her server answers, in the same shape as the published stats
  const stats: Stats | null | undefined = live ? {
    ...(published ?? {} as Stats), version: live.budget_day, budget_day: live.budget_day, budget_resets_at: live.resets_at,
    updated_at: live.now, spend_usd_today: live.spend_today, spend_usd_total: live.spend_total,
    status: live.state ? { state: live.state, since: 0, profile: "", daily_usd: live.daily_usd ?? 1.5, total_usd: live.total_usd ?? 30 } : null,
  } : published;
  if (!stats) return null;
  const cap = stats.status?.daily_usd ?? 1.5;
  const age = stats.updated_at ? now / 1000 - stats.updated_at : Infinity;
  const sameDay = (stats.budget_day ?? stats.version) === workingDay(now);
  const spend = stats.spend_usd_today;
  const state = stats.status?.state;
  let tone: BudgetView["tone"], headline: string, detail: string;
  if (age > STALE_HOURS * 3600) {
    tone = "quiet";
    headline = "No recent update";
    detail = `Her server hasn't reported for ${ago(age).replace(" ago", "")}.`;
  } else if (state === "free_work") {
    tone = "free";
    headline = "Free night shift";
    detail = "Today's paid budget is used; she's checking trial registries and her own numbers, at no cost.";
  } else if (state === "resting" && sameDay) {
    tone = "resting";
    headline = "Resting: today's budget is used";
    detail = stats.budget_resets_at
      ? `Back at work in ${until(stats.budget_resets_at, now)} (9:00 AM Eastern).` : "Back at work at 9:00 AM Eastern.";
  } else if (state === "resting") {
    tone = "working";
    headline = "New day, new budget";
    detail = "Her budget reset at 9:00 AM Eastern; she resumes on her own.";
  } else if (state === "idle") {
    tone = "idle";
    headline = "Caught up";
    detail = "Every paper is processed; she checks PubMed daily for new ones.";
  } else {
    tone = "working";
    headline = "Working";
    detail = "Screening and extracting papers.";
  }
  const short = { working: "Now: working", free: "Now: free shift", resting: "Now: resting", idle: "Now: caught up",
    quiet: "No recent update" }[tone];
  return {
    tone, short, headline, detail, cap,
    spend: sameDay ? spend : 0,
    frac: Math.min(1, (sameDay ? spend : 0) / cap),
    totalSpend: stats.spend_usd_total,
    totalCap: stats.status?.total_usd ?? 30,
    updated: live ? "live" : stats.updated_at ? ago(age) : stats.updated,
  };
}

const usd = (x: number) => `$${x.toFixed(2)}`;

/** Full meter for the website. */
export function BudgetMeter() {
  const b = useBudget();
  if (!b) return null;
  return (
    <div className={`meter ${b.tone}`}>
      <div className="meter-top">
        <span className="meter-dot" />
        <strong>{b.headline}</strong>
        <span className="muted">· {b.detail}</span>
      </div>
      <div className="meter-bar"><span style={{ width: `${b.frac * 100}%` }} /></div>
      <div className="meter-foot muted small">
        Today (from 9 AM Eastern): {usd(b.spend)} of {usd(b.cap)} · all time: {usd(b.totalSpend)} of {usd(b.totalCap)} ·{" "}
        {b.updated === "live" ? "live from her server" : `updated ${b.updated}`}
      </div>
    </div>
  );
}
