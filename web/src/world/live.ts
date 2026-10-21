// Ada, live: her real activity as it happens, streamed from her server (ada/live.py). The lab first sets the
// scene from her latest events, then plays each new one in order, letting her walk before the next begins.

import { SITE } from "../site/config";
import type { StationId, WorldEvent } from "./protocol";
import { useWorld } from "./store";

type Stamped = WorldEvent & { id?: number; at?: number };

/** Where her live service is (?live=<url> overrides it, for testing), or null if there is none. */
export function liveBase(): string | null {
  const q = new URLSearchParams(location.search).get("live");
  return q || SITE.live || null;
}

export async function fetchRecent(base: string, n = 60, timeoutMs = 4000): Promise<Stamped[] | null> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const r = await fetch(`${base}/live/recent?n=${n}`, { signal: ctrl.signal, cache: "no-store" });
    return r.ok ? await r.json() : null;
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}

const strip = ({ id: _id, at: _at, ...e }: Stamped) => e as WorldEvent;

const sleep = (ms: number, signal: AbortSignal) =>
  new Promise<void>((res, rej) => {
    const id = setTimeout(res, ms);
    signal.addEventListener("abort", () => { clearTimeout(id); rej(new Error("aborted")); }, { once: true });
  });

async function waitArrived(st: StationId, signal: AbortSignal, maxMs: number) {
  for (let i = 0; i < maxMs / 100; i++) {
    if (useWorld.getState().arrived === st) return;
    await sleep(100, signal);
  }
}

// Pauses after each event so a burst plays as a sequence; skipped when she gets far ahead of the viewer.
const HOLD: Partial<Record<WorldEvent["type"], number>> = {
  screen: 2500, book: 800, log: 500, thought: 1500, activity: 800, status: 150, mood: 100, hypothesis: 200,
};

export function startLive(base: string, recent: Stamped[]): () => void {
  const ctrl = new AbortController();
  const { signal } = ctrl;
  const dispatch = (e: WorldEvent) => useWorld.getState().dispatch(e);
  useWorld.setState({ mode: "live", log: [] });
  // set the scene: applying recent events in order leaves her latest place, screens, board and notebook
  recent.forEach((e) => dispatch(strip(e)));
  const lastId = recent.length ? recent[recent.length - 1].id ?? 0 : 0;

  const queue: WorldEvent[] = [];
  let wake: (() => void) | null = null;
  const es = new EventSource(`${base}/live/stream?after=${lastId}`);
  es.onmessage = (m) => {
    queue.push(strip(JSON.parse(m.data)));
    wake?.();
  };
  (async () => {
    try {
      for (;;) {
        if (!queue.length) await new Promise<void>((r) => { wake = r; signal.addEventListener("abort", () => r(), { once: true }); });
        wake = null;
        if (signal.aborted) return;
        const e = queue.shift();
        if (!e) continue;
        dispatch(e);
        const behind = queue.length > 12;
        if (e.type === "goto") await waitArrived(e.station, signal, behind ? 0 : 12000);
        await sleep(behind ? 0 : HOLD[e.type] ?? 300, signal);
      }
    } catch {
      /* stopped */
    }
  })();
  return () => { ctrl.abort(); es.close(); };
}
