// The event protocol between "the brain" and the room.
//
// Phase 1: a scripted director (director.ts) emits these events in the browser.
// Phase 2: the real AI backend streams the same events over a WebSocket.
// The room never knows which one is driving it.

export type StationId =
  | "desk"
  | "bookshelf"
  | "whiteboard"
  | "bench"
  | "microscope"
  | "simulator"
  | "coffee"
  | "center"
  | "couch";

export type Activity =
  | "idle"
  | "walk"
  | "type"
  | "read_screen"
  | "browse_books"
  | "read_book"
  | "write_board"
  | "pipette"
  | "microscope"
  | "operate_machine"
  | "drink_coffee"
  | "think"
  | "celebrate"
  | "sleep"
  | "nap" // lying on the couch
  | "listen_music";

export type Mood =
  | "neutral"
  | "focused"
  | "curious"
  | "happy"
  | "excited"
  | "puzzled"
  | "frustrated"
  | "tired";

/** What a screen in the room is showing. */
export type ScreenContent =
  | { app: "idle"; title?: string }
  | { app: "search"; source: string; query: string; url: string; results: SearchResult[] }
  | { app: "paper"; source: string; url: string; title: string; authors: string; journal: string; body: string }
  | { app: "notebook"; title: string; cells: { kind: "code" | "output" | "note"; text: string }[] }
  | { app: "trial"; title: string; status: string; progress: number; arms?: TrialArm[] }
  | { app: "tissue"; title: string; image: string; caption: string };

export interface SearchResult {
  title: string;
  meta: string;
  id?: string;
}

export interface TrialArm {
  name: string;
  color: string;
  /** survival curve points: [month, probability] */
  curve: [number, number][];
  median?: string;
}

export type ScreenId = "computer" | "simulator" | "microscope";

export interface Book {
  id: string;
  title: string;
  kind: "paper" | "notes" | "dataset";
  source: string;
  note: string;
  color: string;
}

export type HypothesisStatus = "open" | "testing" | "supported" | "refuted";

export interface Hypothesis {
  id: string;
  text: string;
  status: HypothesisStatus;
  evidence?: string;
}

export interface LogEntry {
  t: number; // epoch ms
  text: string;
  kind?: "action" | "finding" | "thought" | "system";
}

export type WorldEvent =
  | { type: "goto"; station: StationId; activity: Activity }
  | { type: "activity"; activity: Activity }
  | { type: "mood"; mood: Mood }
  | { type: "thought"; text: string | null }
  | { type: "screen"; screen: ScreenId; content: ScreenContent }
  | { type: "book"; book: Book }
  | { type: "hypothesis"; hypothesis: Hypothesis }
  | { type: "log"; entry: LogEntry }
  | { type: "status"; text: string };
