// Replays Ada's real recorded activity (data/events.json, written by `ada export`) in the room.
// Timing is compressed so a long work session plays back in minutes; screens stay up long
// enough to read. When the replay ends it starts over.

import type { StationId, WorldEvent } from "./protocol";
import { useWorld } from "./store";

type Stamped = WorldEvent & { at?: number };

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

const HOLD: Partial<Record<WorldEvent["type"], number>> = {
  screen: 6500, book: 1500, hypothesis: 400, log: 1400, thought: 2500, status: 200, mood: 150, activity: 3000,
};

export function startReplay(events: Stamped[]): () => void {
  const ctrl = new AbortController();
  const { signal } = ctrl;
  const st = useWorld.getState;
  useWorld.setState({ mode: "replay" });
  (async () => {
    try {
      for (;;) {
        useWorld.setState({ log: [] });
        for (const e of events) {
          const { at: _at, ...ev } = e;
          st().dispatch(ev as WorldEvent);
          if (ev.type === "goto") await waitArrived(ev.station, signal);
          await sleep(HOLD[ev.type] ?? 300, signal);
        }
        await sleep(8000, signal);
      }
    } catch {
      /* stopped */
    }
  })();
  return () => ctrl.abort();
}
