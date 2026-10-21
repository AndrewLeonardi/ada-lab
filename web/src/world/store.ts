import { create } from "zustand";
import type {
  Activity, Book, Hypothesis, LogEntry, Mood, ScreenContent, ScreenId, StationId, WorldEvent,
} from "./protocol";

export type Inspectable =
  | { kind: "screen"; screen: ScreenId }
  | { kind: "library" }
  | { kind: "board" }
  | { kind: "researcher" }
  | null;

export interface WorldState {
  researcher: { name: string; title: string };
  station: StationId;          // where she is going / is
  arrived: StationId | null;   // set by the character when she reaches her station
  activity: Activity;          // what she does once there
  mood: Mood;
  thought: string | null;
  status: string;
  screens: Record<ScreenId, ScreenContent>;
  library: Book[];
  board: Hypothesis[];
  log: LogEntry[];
  inspected: Inspectable;
  mode: "scripted" | "replay" | "live";
  follow: boolean;             // camera follows the researcher
  followZoom: number;          // how close the follow camera gets (x the whole-lab zoom)
  setFollow: (f: boolean) => void;
  dispatch: (e: WorldEvent) => void;
  inspect: (i: Inspectable) => void;
}

export const useWorld = create<WorldState>((set) => ({
  researcher: { name: "Ada", title: "Research scientist, colorectal cancer" },
  station: "center",
  arrived: "center",
  activity: "idle",
  mood: "neutral",
  thought: null,
  status: "Arriving at the lab",
  screens: {
    computer: { app: "idle", title: "Locked" },
    simulator: { app: "idle", title: "Patient simulator ready" },
    microscope: { app: "idle", title: "Microscope idle" },
  },
  library: [],
  board: [],
  log: [],
  inspected: null,
  mode: "scripted",
  follow: false,
  followZoom: 3.2,
  setFollow: (follow) => set({ follow }),
  inspect: (inspected) => set({ inspected }),
  dispatch: (e) =>
    set((s) => {
      switch (e.type) {
        case "goto":
          return { station: e.station, activity: e.activity };
        case "activity":
          return { activity: e.activity };
        case "mood":
          return { mood: e.mood };
        case "thought":
          return { thought: e.text };
        case "status":
          return { status: e.text };
        case "screen":
          return { screens: { ...s.screens, [e.screen]: e.content } };
        case "book":
          return { library: [...s.library.filter((b) => b.id !== e.book.id), e.book] };
        case "hypothesis":
          return {
            board: s.board.some((h) => h.id === e.hypothesis.id)
              ? s.board.map((h) => (h.id === e.hypothesis.id ? e.hypothesis : h))
              : [...s.board, e.hypothesis],
          };
        case "log":
          return { log: [...s.log.slice(-199), e.entry] };
        default:
          return {};
      }
    }),
}));
