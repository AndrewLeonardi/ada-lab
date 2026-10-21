// Positions written by the 3D scene every frame and read by DOM overlays and the camera rig.
// Kept outside React state on purpose: they change 60 times a second.
export const anchors = {
  head: { x: -9999, y: -9999, visible: false }, // screen pixels
  headWorld: { x: 0, y: 1.4, z: 0 },             // world units
};
