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
}

const BACK = Math.PI; // facing the back wall (-z)
const LEFT = -Math.PI / 2; // facing the left wall (-x)

export const STATIONS: Record<StationId, Station> = {
  desk: { id: "desk", label: "Computer", pos: [1.0, -2.55], facing: BACK, defaultActivity: "type", seated: true },
  bookshelf: { id: "bookshelf", label: "Library", pos: [-1.5, -2.85], facing: BACK, defaultActivity: "browse_books" },
  simulator: { id: "simulator", label: "Patient simulator", pos: [-3.25, -2.55], facing: BACK, defaultActivity: "operate_machine" },
  bench: { id: "bench", label: "Lab bench", pos: [-2.75, -0.6], facing: LEFT, defaultActivity: "pipette" },
  microscope: { id: "microscope", label: "Microscope", pos: [-2.75, 0.95], facing: LEFT, defaultActivity: "microscope" },
  whiteboard: { id: "whiteboard", label: "Hypothesis board", pos: [-2.85, 2.85], facing: LEFT, defaultActivity: "write_board" },
  coffee: { id: "coffee", label: "Coffee", pos: [3.1, -2.75], facing: BACK, defaultActivity: "drink_coffee" },
  center: { id: "center", label: "Thinking spot", pos: [0.9, 0.9], facing: Math.PI / 4, defaultActivity: "think" },
};

/** A simple walkway: go through the hub unless the hop is short. */
const HUB: [number, number] = [0.6, 0.2];

export function planPath(from: [number, number], to: [number, number]): [number, number][] {
  const d = Math.hypot(to[0] - from[0], to[1] - from[1]);
  if (d < 2.6) return [to];
  return [HUB, to];
}
