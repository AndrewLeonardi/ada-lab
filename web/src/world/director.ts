// The scripted director: a demo "day in the lab" that drives the researcher through the same
// events the real AI brain will send in phase 2. Papers shown are real and PubMed-verified;
// their on-screen text is our own paraphrase, not the abstract. Simulator curves are
// ILLUSTRATIVE and labelled as such.

import type { Activity, Mood, ScreenContent, ScreenId, StationId, WorldEvent } from "./protocol";
import { useWorld } from "./store";

const PAPERS = {
  parseghian: {
    id: "pmid-30462160",
    title: "Anti-EGFR-resistant clones decay exponentially after progression: implications for anti-EGFR re-challenge",
    authors: "Parseghian CM, Loree JM, Morris VK, et al.",
    journal: "Ann Oncol 2019;30:243-249 · PMID 30462160",
    url: "pubmed.ncbi.nlm.nih.gov/30462160",
    notes:
      "Reading notes (my paraphrase).\n\nQuestion: once anti-EGFR antibodies stop, what happens to the tumor cells that " +
      "became resistant (RAS or EGFR mutations)?\n\nApproach: serial blood tests (circulating tumor DNA) in patients " +
      "after progression on anti-EGFR therapy, fitting an exponential decay to the mutant fraction.\n\nKey number: the " +
      "resistant clones fade with a cumulative half-life of about 4.4 months, and the result held in an independent " +
      "validation cohort.\n\nWhy it matters to me: if resistance fades on a clock, the timing of a rechallenge is a " +
      "question about dynamics, and my simulator is built for exactly that.",
  },
  cricket: {
    id: "pmid-30476968",
    title: "Rechallenge for Patients With RAS and BRAF Wild-Type mCRC With Acquired Resistance to First-line Cetuximab and Irinotecan (CRICKET)",
    authors: "Cremolini C, et al.",
    journal: "JAMA Oncol 2019;5:343-350 · PMID 30476968",
  },
  chronos: {
    id: "pmid-35915157",
    title: "Circulating tumor DNA to guide rechallenge with panitumumab in metastatic colorectal cancer: the phase 2 CHRONOS trial",
    authors: "Sartore-Bianchi A, et al.",
    journal: "Nat Med 2022;28:1612-1618 · PMID 35915157",
  },
  diaz: {
    id: "pmid-22722843",
    title: "The molecular evolution of acquired resistance to targeted EGFR blockade in colorectal cancers",
    authors: "Diaz LA Jr, et al.",
    journal: "Nature 2012;486:537-540 · PMID 22722843",
  },
};

interface Step {
  at: StationId;
  act: Activity;
  mood: Mood;
  hold: number; // seconds to stay after arriving
  status: string;
  thought?: string | null;
  screen?: [ScreenId, ScreenContent];
  extra?: WorldEvent[];
  log?: string;
  kind?: "action" | "finding" | "thought";
}

function km(points: number, half: number, floor = 0.04): [number, number][] {
  const out: [number, number][] = [];
  for (let i = 0; i <= points; i++) {
    const m = (i / points) * 14;
    out.push([m, Math.max(floor, Math.exp((-Math.LN2 * m) / half))]);
  }
  return out;
}

function day(): Step[] {
  return [
    { at: "coffee", act: "drink_coffee", mood: "happy", hold: 9, status: "Morning coffee",
      thought: "Morning! Where did I leave off yesterday...", log: "Arrived at the lab", kind: "action" },
    { at: "desk", act: "type", mood: "focused", hold: 10, status: "Searching PubMed",
      thought: "What is known about restarting anti-EGFR drugs?",
      screen: ["computer", { app: "search", source: "PubMed", url: "pubmed.ncbi.nlm.nih.gov/?term=anti-EGFR+rechallenge+ctDNA",
        query: "anti-EGFR rechallenge ctDNA colorectal", results: [
          { title: PAPERS.cricket.title, meta: PAPERS.cricket.journal },
          { title: PAPERS.chronos.title, meta: PAPERS.chronos.journal },
          { title: PAPERS.parseghian.title, meta: PAPERS.parseghian.journal },
          { title: PAPERS.diaz.title, meta: PAPERS.diaz.journal },
        ] }],
      log: "Searched PubMed: anti-EGFR rechallenge ctDNA colorectal", kind: "action" },
    { at: "desk", act: "read_screen", mood: "curious", hold: 14, status: "Reading Parseghian et al. 2019",
      thought: "Resistant clones fade with a ~4.4-month half-life once the drug stops...",
      screen: ["computer", { app: "paper", source: "PubMed", url: PAPERS.parseghian.url, title: PAPERS.parseghian.title,
        authors: PAPERS.parseghian.authors, journal: PAPERS.parseghian.journal, body: PAPERS.parseghian.notes }],
      extra: [{ type: "book", book: { id: PAPERS.parseghian.id, title: PAPERS.parseghian.title, kind: "paper",
        source: PAPERS.parseghian.journal, note: "Resistant clones decay with a ~4.4-month half-life after anti-EGFR stops.",
        color: "#e07a6a" } }],
      log: "Saved to library: Parseghian 2019 (resistant clones decay, half-life ~4.4 months)", kind: "finding" },
    { at: "center", act: "think", mood: "curious", hold: 8, status: "Thinking",
      thought: "If resistance fades on a clock... is there a best moment to restart?" },
    { at: "whiteboard", act: "write_board", mood: "excited", hold: 9, status: "Writing a hypothesis",
      thought: null,
      extra: [{ type: "hypothesis", hypothesis: { id: "h1", status: "open",
        text: "Restarting anti-EGFR when blood RAS falls below detection beats a fixed 4-month break" } }],
      log: "New hypothesis: ctDNA-timed rechallenge beats a fixed break", kind: "thought" },
    { at: "bookshelf", act: "browse_books", mood: "focused", hold: 6, status: "Looking for the CRICKET trial" },
    { at: "bookshelf", act: "read_book", mood: "focused", hold: 9, status: "Reading CRICKET (Cremolini 2019)",
      thought: "21% responded to a rechallenge... and blood RAS status predicted who.",
      extra: [{ type: "book", book: { id: PAPERS.cricket.id, title: PAPERS.cricket.title, kind: "paper",
        source: PAPERS.cricket.journal, note: "Rechallenge response 21%; patients with RAS-negative ctDNA did better.",
        color: "#3f9a96" } }],
      log: "Saved to library: CRICKET 2019 rechallenge trial", kind: "finding" },
    { at: "simulator", act: "operate_machine", mood: "focused", hold: 12, status: "Running a virtual trial",
      thought: "Pilot: ctDNA-timed versus fixed-break rechallenge.",
      screen: ["simulator", { app: "trial", title: "Virtual trial (ILLUSTRATIVE DEMO)", status: "Simulating 200 patients...",
        progress: 0.35, arms: [
          { name: "fixed 4-month break", color: "#ffbd3e", curve: km(28, 3.2), median: "3.2 mo" },
          { name: "ctDNA-timed", color: "#5fd3a5", curve: km(28, 3.9), median: "3.9 mo" },
        ] }],
      extra: [{ type: "hypothesis", hypothesis: { id: "h1", status: "testing",
        text: "Restarting anti-EGFR when blood RAS falls below detection beats a fixed 4-month break" } }],
      log: "Started virtual pilot trial (demo)", kind: "action" },
    { at: "simulator", act: "operate_machine", mood: "puzzled", hold: 7, status: "Reading the results",
      thought: "Hmm. A small difference... probably underpowered. Need a bigger trial.",
      screen: ["simulator", { app: "trial", title: "Virtual trial (ILLUSTRATIVE DEMO)", status: "Done - difference not significant (demo)",
        progress: 1, arms: [
          { name: "fixed 4-month break", color: "#ffbd3e", curve: km(28, 3.2), median: "3.2 mo" },
          { name: "ctDNA-timed", color: "#5fd3a5", curve: km(28, 3.9), median: "3.9 mo" },
        ] }] },
    { at: "bench", act: "pipette", mood: "neutral", hold: 8, status: "Preparing a tissue sample",
      thought: "Meanwhile: does the antibody even reach the tumor core?" },
    { at: "microscope", act: "microscope", mood: "focused", hold: 9, status: "Looking at virtual colon tissue",
      screen: ["microscope", { app: "tissue", title: "Virtual colon - implanted tumor", image: "/tissue_demo.png",
        caption: "Necrosis begins ~120-150 um from capillaries (Thomlinson & Gray 1955 saw 145-200 um)" }],
      log: "Imaged virtual tissue: necrotic core where diffusion predicts", kind: "action" },
    { at: "microscope", act: "celebrate", mood: "excited", hold: 5, status: "A nice match!",
      thought: "The necrotic core sits right where the physics says it should!" },
    { at: "desk", act: "type", mood: "focused", hold: 12, status: "Planning a bigger trial",
      screen: ["computer", { app: "notebook", title: "rechallenge_power.ipynb", cells: [
        { kind: "note", text: "Pilot gave a small difference. How many patients per arm to detect HR 0.75?" },
        { kind: "code", text: "events = (1.96 + 0.84)**2 * 4 / log(0.75)**2\nprint(round(events))" },
        { kind: "output", text: "379  # events needed (Schoenfeld formula)" },
        { kind: "note", text: "Next: request a 500-per-arm virtual trial when the yearly budget allows." },
      ] }],
      log: "Power calculation: ~379 events needed to detect HR 0.75", kind: "action" },
  ];
}

const sleep = (ms: number, signal: AbortSignal) =>
  new Promise<void>((res, rej) => {
    const id = setTimeout(res, ms);
    signal.addEventListener("abort", () => { clearTimeout(id); rej(new Error("aborted")); }, { once: true });
  });

async function waitArrived(st: StationId, signal: AbortSignal) {
  for (let i = 0; i < 300; i++) {
    if (useWorld.getState().arrived === st) return;
    await sleep(100, signal);
  }
}

export function startDirector(): () => void {
  const ctrl = new AbortController();
  const { signal } = ctrl;
  const emit = (e: WorldEvent) => useWorld.getState().dispatch(e);
  useWorld.setState({ mode: "scripted" });
  (async () => {
    try {
      emit({ type: "log", entry: { t: Date.now(), text: "Scripted demo day started (the AI brain arrives in phase 2)", kind: "system" } });
      for (;;) {
        const hour = new Date().getHours();
        if (hour >= 1 && hour < 6) {
          // night: she naps at her desk (in the live version this is when the daily budget resets)
          emit({ type: "goto", station: "desk", activity: "sleep" });
          emit({ type: "mood", mood: "tired" });
          emit({ type: "thought", text: null });
          emit({ type: "status", text: "Napping until morning" });
          await sleep(60_000, signal);
          continue;
        }
        for (const s of day()) {
          emit({ type: "goto", station: s.at, activity: s.act });
          emit({ type: "status", text: `Walking to the ${s.at}` });
          await waitArrived(s.at, signal);
          emit({ type: "mood", mood: s.mood });
          emit({ type: "status", text: s.status });
          if (s.thought !== undefined) emit({ type: "thought", text: s.thought });
          if (s.screen) emit({ type: "screen", screen: s.screen[0], content: s.screen[1] });
          for (const e of s.extra ?? []) emit(e);
          if (s.log) emit({ type: "log", entry: { t: Date.now(), text: s.log, kind: s.kind } });
          await sleep(s.hold * 1000, signal);
        }
        emit({ type: "thought", text: null });
      }
    } catch {
      /* stopped */
    }
  })();
  return () => ctrl.abort();
}
