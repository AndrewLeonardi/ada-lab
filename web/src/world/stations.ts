import type { Activity, StationId } from "./protocol";

// Floor coordinates: the room spans x, z in [-4, 4]; walls stand at x = -4 (left) and z = -4 (back).
// Each station is where the researcher stands (or sits) to use something, and which way she faces.

export interface Station {
  id: StationId;
  label: string;
  pos: [number, number]; // x, z on the floor
  facing: number; // yaw in radians (0 = facing +z, toward the viewer)
  defaultActivity: Activity;
  seated?: boolean;
  route?: [number, number][]; // waypoints from the walkway to the spot (walked in reverse when leaving)
}

const BACK = Math.PI; // facing the back wall (-z)
const LEFT = -Math.PI / 2; // facing the left wall (-x)
const VIEWER = Math.PI / 4; // facing the viewer

// The lounge: a couch in the front-right of the room, facing the viewer. The walkway is behind it, so she
// walks around its right end and sits down from the front. COUCH is the seat; W runs along it, F out of it.
export const COUCH: [number, number] = [2.1, 2.4];
const W: [number, number] = [Math.SQRT1_2, -Math.SQRT1_2];
const F: [number, number] = [Math.SQRT1_2, Math.SQRT1_2];
export const atCouch = (w: number, f: number): [number, number] => [COUCH[0] + W[0] * w + F[0] * f, COUCH[1] + W[1] * w + F[1] * f];

export const STATIONS: Record<StationId, Station> = {
  desk: { id: "desk", label: "Computer", pos: [1.0, -2.55], facing: BACK, defaultActivity: "type", seated: true },
  bookshelf: { id: "bookshelf", label: "Library", pos: [-1.5, -2.85], facing: BACK, defaultActivity: "browse_books" },
  simulator: { id: "simulator", label: "Patient simulator", pos: [-3.25, -2.55], facing: BACK, defaultActivity: "operate_machine" },
  bench: { id: "bench", label: "Lab bench", pos: [-2.75, -0.6], facing: LEFT, defaultActivity: "pipette" },
  microscope: { id: "microscope", label: "Microscope", pos: [-2.75, 0.95], facing: LEFT, defaultActivity: "microscope" },
  whiteboard: { id: "whiteboard", label: "Hypothesis board", pos: [-2.85, 2.85], facing: LEFT, defaultActivity: "write_board" },
  coffee: { id: "coffee", label: "Coffee", pos: [3.1, -2.75], facing: BACK, defaultActivity: "drink_coffee" },
  center: { id: "center", label: "Thinking spot", pos: [0.9, 0.9], facing: Math.PI / 4, defaultActivity: "think" },
  couch: { id: "couch", label: "Lounge", pos: COUCH, facing: VIEWER, defaultActivity: "listen_music", seated: true,
    route: [atCouch(1.6, -0.7), atCouch(1.5, 0.75), atCouch(0, 0.75)] },
};

/** A simple walkway: go through the hub unless the hop is short. */
const HUB: [number, number] = [0.6, 0.2];

export function planPath(from: [number, number], to: [number, number], leave: [number, number][] = [],
  enter: [number, number][] = []): [number, number][] {
  const out = [...leave].reverse();
  const a = out.length ? out[out.length - 1] : from;
  const b = enter.length ? enter[0] : to;
  if (Math.hypot(b[0] - a[0], b[1] - a[1]) >= 2.6) out.push(HUB);
  return [...out, ...enter, to];
}
