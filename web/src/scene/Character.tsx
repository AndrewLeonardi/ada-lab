import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { RoundedBox } from "@react-three/drei";
import * as THREE from "three";
import { C } from "./palette";
import { STATIONS, planPath } from "../world/stations";
import { useWorld } from "../world/store";
import type { Activity, Mood } from "../world/protocol";
import { anchors } from "../world/anchors";

// ------------------------------------------------------------------ expressions
type MouthShape = "smile" | "grin" | "flat" | "frown" | "o";
interface Face {
  browAngle: number; // + = inner ends up (worried/sad), - = inner ends down (focused/angry)
  browY: number;
  browAsym: number; // raises the left brow relative to the right
  eyeOpen: number;
  mouth: MouthShape;
  blush: number;
  tilt: number;
}
const FACES: Record<Mood, Face> = {
  neutral: { browAngle: 0, browY: 0, browAsym: 0, eyeOpen: 1, mouth: "smile", blush: 0, tilt: 0 },
  focused: { browAngle: -0.25, browY: -0.01, browAsym: 0, eyeOpen: 0.82, mouth: "flat", blush: 0, tilt: 0 },
  curious: { browAngle: 0.05, browY: 0.012, browAsym: 0.02, eyeOpen: 1.1, mouth: "o", blush: 0.1, tilt: 0.14 },
  happy: { browAngle: 0.1, browY: 0.012, browAsym: 0, eyeOpen: 0.75, mouth: "smile", blush: 0.55, tilt: 0.06 },
  excited: { browAngle: 0.15, browY: 0.025, browAsym: 0, eyeOpen: 1.18, mouth: "grin", blush: 0.85, tilt: 0 },
  puzzled: { browAngle: 0.1, browY: 0.0, browAsym: 0.035, eyeOpen: 1.0, mouth: "flat", blush: 0, tilt: -0.18 },
  frustrated: { browAngle: -0.45, browY: -0.012, browAsym: 0, eyeOpen: 0.85, mouth: "frown", blush: 0.25, tilt: 0 },
  tired: { browAngle: 0.25, browY: -0.015, browAsym: 0, eyeOpen: 0.42, mouth: "flat", blush: 0, tilt: 0.08 },
};

export const EMOTE: Partial<Record<Mood, string>> = { excited: "!", puzzled: "?", curious: "…", frustrated: "#", tired: "z" };

const lerp = THREE.MathUtils.lerp;
const damp = (cur: number, target: number, rate: number, dt: number) => lerp(cur, target, 1 - Math.exp(-rate * dt));

function mat(color: string, rough = 0.55) {
  return new THREE.MeshStandardMaterial({ color, roughness: rough });
}

// ------------------------------------------------------------------ the character
export function Character() {
  const station = useWorld((s) => s.station);
  const activity = useWorld((s) => s.activity);
  const mood = useWorld((s) => s.mood);
  const inspect = useWorld((s) => s.inspect);

  const m = useMemo(() => ({
    skin: mat(C.skin, 0.65), hair: mat(C.hair, 0.5), coat: mat(C.coat, 0.7), shirt: mat(C.shirt, 0.7),
    pants: mat(C.pants, 0.8), shoes: mat(C.shoes, 0.5), dark: mat("#1d1a1f", 0.3), white: mat("#ffffff", 0.2),
    brow: mat("#2b2124", 0.6), mouth: mat("#7a2f35", 0.6), glasses: mat("#3a3036", 0.3),
    blush: new THREE.MeshBasicMaterial({ color: "#ff8f8f", transparent: true, opacity: 0 }),
    tie: mat(C.coral, 0.5), book: mat(C.coral, 0.6), page: mat("#fbf6ea", 0.8), mug: mat(C.teal, 0.5),
    marker: mat(C.coral, 0.5),
  }), []);

  // refs for animated parts
  const root = useRef<THREE.Group>(null!);
  const body = useRef<THREE.Group>(null!);
  const torso = useRef<THREE.Group>(null!);
  const head = useRef<THREE.Group>(null!);
  const legL = useRef<THREE.Group>(null!);
  const legR = useRef<THREE.Group>(null!);
  const armL = useRef<THREE.Group>(null!);
  const armR = useRef<THREE.Group>(null!);
  const foreL = useRef<THREE.Group>(null!);
  const foreR = useRef<THREE.Group>(null!);
  const pony = useRef<THREE.Group>(null!);
  const eyeL = useRef<THREE.Group>(null!);
  const eyeR = useRef<THREE.Group>(null!);
  const pupils = useRef<THREE.Group>(null!);
  const browL = useRef<THREE.Mesh>(null!);
  const browR = useRef<THREE.Mesh>(null!);
  const mouths = useRef<Record<MouthShape, THREE.Object3D | null>>({ smile: null, grin: null, flat: null, frown: null, o: null });
  const blushL = useRef<THREE.Mesh>(null!);
  const blushR = useRef<THREE.Mesh>(null!);
  const props = useRef<Record<string, THREE.Object3D | null>>({});

  // locomotion state (kept outside React state: updated every frame)
  const nav = useRef({
    pos: new THREE.Vector2(...STATIONS.center.pos),
    yaw: STATIONS.center.facing,
    path: [] as THREE.Vector2[],
    target: "center" as string,
    arrived: true,
    face: { ...FACES.neutral, mouthW: { smile: 1, grin: 0, flat: 0, frown: 0, o: 0 } as Record<MouthShape, number> },
    blinkT: 2,
    seat: 0,
    lie: 0, // 1 = lying on the couch
    bodyY: 0,
    bodyZ: 0,
  });

  const tmp = useMemo(() => new THREE.Vector3(), []);
  useFrame((state, dtRaw) => {
    const dt = Math.min(dtRaw, 0.05);
    // where her head is on screen, for the DOM overlay (thought bubble, name tag)
    head.current.getWorldPosition(tmp);
    anchors.headWorld.x = tmp.x; anchors.headWorld.y = tmp.y; anchors.headWorld.z = tmp.z;
    tmp.y += 0.45;
    tmp.project(state.camera);
    const el = state.gl.domElement;
    anchors.head.x = ((tmp.x + 1) / 2) * el.clientWidth;
    anchors.head.y = ((1 - tmp.y) / 2) * el.clientHeight;
    anchors.head.visible = tmp.z < 1;
    const t = state.clock.elapsedTime;
    const n = nav.current;
    const st = STATIONS[station];

    // ---- path planning when the target station changes
    if (n.target !== station) {
      // leave a station by its route only if she was actually there (not when redirected mid-walk)
      const leave = n.arrived ? STATIONS[n.target as keyof typeof STATIONS]?.route : undefined;
      n.target = station;
      n.arrived = false;
      n.path = planPath([n.pos.x, n.pos.y], st.pos, leave, st.route).map((p) => new THREE.Vector2(p[0], p[1]));
      useWorld.setState({ arrived: null });
    }
    let act: Activity = n.arrived ? activity : "walk";
    if (!n.arrived && (n.seat > 0.02 || n.lie > 0.02)) act = "idle"; // get up before walking

    // ---- walking
    if (act === "walk" && n.path.length) {
      const goal = n.path[0];
      const d = goal.clone().sub(n.pos);
      const dist = d.length();
      const speed = 1.35;
      if (dist < 0.05) {
        n.path.shift();
        if (!n.path.length) {
          n.arrived = true;
          useWorld.setState({ arrived: station });
        }
      } else {
        n.pos.add(d.multiplyScalar(Math.min(1, (speed * dt) / dist)));
        const want = Math.atan2(goal.x - n.pos.x, goal.y - n.pos.y);
        n.yaw = angleDamp(n.yaw, want, 10, dt);
      }
    } else if (n.arrived) {
      // emotional moments are played toward the viewer so the face is visible
      const toViewer = activity === "think" || activity === "celebrate" || station === "center";
      n.yaw = angleDamp(n.yaw, toViewer && !st.seated ? Math.PI / 4 : st.facing, 6, dt);
    }
    root.current.position.set(n.pos.x, 0, n.pos.y);
    root.current.rotation.y = n.yaw;

    // ---- pose targets for the current activity
    const lying = n.arrived && act === "nap";
    const seated = n.arrived && !!st.seated && !lying;
    n.seat = damp(n.seat, seated ? 1 : 0, 6, dt);
    n.lie = damp(n.lie, lying ? 1 : 0, 3, dt);
    const P = pose(act, t, n.seat);
    const k = 12;
    legL.current.rotation.x = damp(legL.current.rotation.x, P.legL, k, dt);
    legR.current.rotation.x = damp(legR.current.rotation.x, P.legR, k, dt);
    armL.current.rotation.x = damp(armL.current.rotation.x, P.armL, k, dt);
    armR.current.rotation.x = damp(armR.current.rotation.x, P.armR, k, dt);
    armL.current.rotation.z = damp(armL.current.rotation.z, P.armLz, k, dt);
    armR.current.rotation.z = damp(armR.current.rotation.z, P.armRz, k, dt);
    foreL.current.rotation.x = damp(foreL.current.rotation.x, P.foreL, k, dt);
    foreR.current.rotation.x = damp(foreR.current.rotation.x, P.foreR, k, dt);
    torso.current.rotation.x = damp(torso.current.rotation.x, P.lean, 8, dt);
    head.current.rotation.x = damp(head.current.rotation.x, P.headPitch, 8, dt);
    head.current.rotation.y = damp(head.current.rotation.y, P.headYaw, 6, dt);
    n.bodyY = damp(n.bodyY, P.bodyY + n.seat * 0.02, 14, dt);
    n.bodyZ = damp(n.bodyZ, n.seat * 0.08, 8, dt);
    // lying: on her side along the couch, head on the pillow at its left end, face toward the viewer
    body.current.position.set(n.lie * 0.8, n.bodyY * (1 - n.lie) + n.lie * 0.74, n.bodyZ * (1 - n.lie));
    body.current.rotation.z = n.lie * (Math.PI / 2);

    // ---- face
    const F = FACES[mood];
    const f = n.face;
    f.browAngle = damp(f.browAngle, F.browAngle, 8, dt);
    f.browY = damp(f.browY, F.browY, 8, dt);
    f.browAsym = damp(f.browAsym, F.browAsym, 8, dt);
    f.blush = damp(f.blush, F.blush, 4, dt);
    f.tilt = damp(f.tilt, F.tilt + (act === "think" ? 0.12 : 0), 5, dt);
    head.current.rotation.z = f.tilt;
    for (const s of Object.keys(f.mouthW) as MouthShape[]) {
      f.mouthW[s] = damp(f.mouthW[s], s === F.mouth ? 1 : 0, 10, dt);
      const o = mouths.current[s];
      if (o) { o.scale.setScalar(Math.max(0.001, f.mouthW[s])); o.visible = f.mouthW[s] > 0.02; }
    }
    browL.current.position.y = 0.1 + f.browY + f.browAsym;
    browR.current.position.y = 0.1 + f.browY;
    browL.current.rotation.z = -f.browAngle;
    browR.current.rotation.z = f.browAngle;
    (blushL.current.material as THREE.MeshBasicMaterial).opacity = f.blush * 0.55;

    // blinking (and closed eyes when asleep)
    n.blinkT -= dt;
    if (n.blinkT < -0.12) n.blinkT = 2 + Math.random() * 3;
    const blink = n.blinkT < 0 ? 0.1 : 1;
    const open = act === "sleep" || act === "nap" ? 0.06 : act === "listen_music" ? 0.3 : F.eyeOpen * blink * (act === "drink_coffee" && Math.sin(t * 0.9) > 0.7 ? 0.2 : 1);
    eyeL.current.scale.y = damp(eyeL.current.scale.y, open, 25, dt);
    eyeR.current.scale.y = eyeL.current.scale.y;
    // eyes scan text when reading
    const scan = act === "read_screen" || act === "read_book" || act === "type" ? Math.sin(t * 2.2) * 0.012 : 0;
    const lookUp = act === "think" ? 0.012 : act === "browse_books" ? 0.01 : 0;
    pupils.current.position.x = damp(pupils.current.position.x, scan, 10, dt);
    pupils.current.position.y = damp(pupils.current.position.y, lookUp, 10, dt);

    // ponytail sway (more when walking)
    pony.current.rotation.x = 0.35 + Math.sin(t * (act === "walk" ? 9 : 1.6)) * (act === "walk" ? 0.18 : 0.05);
    pony.current.rotation.z = Math.sin(t * (act === "walk" ? 4.5 : 0.9)) * 0.08;

    // hand props
    const show = (k: string, v: boolean) => { const o = props.current[k]; if (o) o.visible = v; };
    show("book", act === "read_book");
    show("mug", act === "drink_coffee");
    show("marker", act === "write_board");
    show("pipette", act === "pipette");
    show("headphones", act === "listen_music");
  });

  return (
    <group ref={root} onClick={(e) => { e.stopPropagation(); inspect({ kind: "researcher" }); }}
      onPointerOver={() => (document.body.style.cursor = "pointer")} onPointerOut={() => (document.body.style.cursor = "auto")}>
      <group ref={body}>
        {/* legs */}
        {[[legL, 0.1], [legR, -0.1]].map(([ref, x], i) => (
          <group key={i} ref={ref as React.RefObject<THREE.Group>} position={[x as number, 0.58, 0]}>
            <mesh position={[0, -0.26, 0]} material={m.pants} castShadow>
              <capsuleGeometry args={[0.075, 0.32, 6, 12]} />
            </mesh>
            <RoundedBox args={[0.13, 0.08, 0.22]} radius={0.035} position={[0, -0.53, 0.04]} material={m.shoes} castShadow />
          </group>
        ))}
        <group ref={torso} position={[0, 0.58, 0]}>
          {/* hips + shirt */}
          <mesh position={[0, 0.02, 0]} material={m.pants} castShadow>
            <sphereGeometry args={[0.16, 20, 14]} />
          </mesh>
          <mesh position={[0, 0.27, 0]} material={m.shirt} castShadow>
            <capsuleGeometry args={[0.155, 0.24, 8, 16]} />
          </mesh>
          {/* open lab coat (a gap at the front shows the shirt) */}
          <mesh position={[0, 0.2, 0]} material={m.coat} castShadow>
            <cylinderGeometry args={[0.175, 0.24, 0.62, 28, 1, true, Math.PI * 0.2, Math.PI * 1.6]} />
          </mesh>
          <mesh position={[0, 0.2, 0]} material={m.coat}>
            <cylinderGeometry args={[0.17, 0.235, 0.62, 28, 1, true, Math.PI * 0.2, Math.PI * 1.6]} />
          </mesh>
          <mesh position={[0, 0.45, 0]} material={m.coat}>
            <sphereGeometry args={[0.178, 24, 10, 0, Math.PI * 2, 0, Math.PI / 2.2]} />
          </mesh>
          {/* collar flaps + pocket with a pen */}
          {[-1, 1].map((s) => (
            <mesh key={s} position={[0.07 * s, 0.47, 0.13]} rotation={[0.3, 0, s * 0.5]} material={m.coat}>
              <boxGeometry args={[0.07, 0.12, 0.015]} />
            </mesh>
          ))}
          <mesh position={[-0.11, 0.3, 0.16]} rotation={[0, -0.45, 0]} material={m.coat}>
            <boxGeometry args={[0.08, 0.07, 0.01]} />
          </mesh>
          <mesh position={[-0.12, 0.35, 0.165]} material={m.tie}>
            <cylinderGeometry args={[0.008, 0.008, 0.07, 6]} />
          </mesh>
          {/* arms: shoulder -> elbow -> hand */}
          {[[armL, foreL, 0.22, "L"], [armR, foreR, -0.22, "R"]].map(([arm, fore, x, side]) => (
            <group key={side as string} ref={arm as React.RefObject<THREE.Group>} position={[x as number, 0.44, 0]}>
              <mesh position={[0, -0.12, 0]} material={m.coat} castShadow>
                <capsuleGeometry args={[0.062, 0.14, 6, 12]} />
              </mesh>
              <group ref={fore as React.RefObject<THREE.Group>} position={[0, -0.24, 0]}>
                <mesh position={[0, -0.09, 0]} material={m.coat} castShadow>
                  <capsuleGeometry args={[0.057, 0.12, 6, 12]} />
                </mesh>
                <mesh position={[0, -0.21, 0]} material={m.skin} castShadow>
                  <sphereGeometry args={[0.055, 14, 10]} />
                </mesh>
                {side === "R" && (
                  <>
                    <group ref={(o) => { props.current.mug = o; }} position={[0, -0.24, 0.05]} visible={false}>
                      <mesh material={m.mug}><cylinderGeometry args={[0.05, 0.045, 0.1, 14]} /></mesh>
                    </group>
                    <group ref={(o) => { props.current.marker = o; }} position={[0, -0.25, 0.03]} rotation={[1.2, 0, 0]} visible={false}>
                      <mesh material={m.marker}><cylinderGeometry args={[0.012, 0.012, 0.12, 8]} /></mesh>
                    </group>
                    <group ref={(o) => { props.current.pipette = o; }} position={[0, -0.28, 0.02]} visible={false}>
                      <mesh material={m.white}><cylinderGeometry args={[0.014, 0.004, 0.18, 8]} /></mesh>
                    </group>
                  </>
                )}
                {side === "L" && (
                  <group ref={(o) => { props.current.book = o; }} position={[-0.12, -0.24, 0.1]} rotation={[-1.1, 0, 0]} visible={false}>
                    <mesh material={m.book}><boxGeometry args={[0.3, 0.03, 0.22]} /></mesh>
                    <mesh position={[0, 0.018, 0]} material={m.page}><boxGeometry args={[0.28, 0.012, 0.2]} /></mesh>
                  </group>
                )}
              </group>
            </group>
          ))}
          {/* neck + head */}
          <mesh position={[0, 0.54, 0]} material={m.skin}>
            <cylinderGeometry args={[0.055, 0.06, 0.12, 12]} />
          </mesh>
          <group ref={head} position={[0, 0.81, 0]}>
            <mesh material={m.skin} scale={[1, 0.95, 0.96]} castShadow>
              <sphereGeometry args={[0.27, 32, 24]} />
            </mesh>
            {/* hair: crown, back and sides (leaving the face open), side-swept fringe, ponytail */}
            <mesh material={m.hair} position={[0, 0.012, -0.005]} castShadow>
              <sphereGeometry args={[0.288, 36, 18, 0, Math.PI * 2, 0, Math.PI * 0.36]} />
            </mesh>
            <mesh material={m.hair} position={[0, 0.0, -0.01]} castShadow>
              <sphereGeometry args={[0.286, 36, 22, Math.PI * 0.93, Math.PI * 1.14, Math.PI * 0.3, Math.PI * 0.38]} />
            </mesh>
            <mesh material={m.hair} position={[0.0, 0.006, 0.004]} rotation={[0.06, 0, 0.16]}>
              <sphereGeometry args={[0.292, 36, 12, Math.PI * 0.1, Math.PI * 0.8, Math.PI * 0.18, Math.PI * 0.2]} />
            </mesh>
            {[-1, 1].map((s) => (
              <mesh key={s} material={m.hair} position={[0.215 * s, -0.07, 0.05]} rotation={[0.1, 0, s * 0.12]}>
                <capsuleGeometry args={[0.042, 0.17, 6, 10]} />
              </mesh>
            ))}
            <group ref={pony} position={[0, 0.1, -0.24]}>
              <mesh material={m.tie}><torusGeometry args={[0.04, 0.018, 8, 16]} /></mesh>
              <mesh material={m.hair} position={[0, -0.18, -0.04]} castShadow>
                <capsuleGeometry args={[0.07, 0.26, 8, 12]} />
              </mesh>
            </group>
            {/* headphones (for music on the couch) */}
            <group ref={(o) => { props.current.headphones = o; }} visible={false}>
              <mesh material={m.dark} position={[0, -0.02, -0.01]}>
                <torusGeometry args={[0.315, 0.022, 8, 28, Math.PI]} />
              </mesh>
              {[-1, 1].map((s) => (
                <mesh key={s} material={m.tie} position={[0.3 * s, -0.03, 0]} rotation={[0, 0, Math.PI / 2]}>
                  <cylinderGeometry args={[0.075, 0.075, 0.07, 18]} />
                </mesh>
              ))}
            </group>
            {/* ears + nose */}
            {[-1, 1].map((s) => (
              <mesh key={s} material={m.skin} position={[0.265 * s, -0.02, 0]}>
                <sphereGeometry args={[0.045, 12, 10]} />
              </mesh>
            ))}
            <mesh material={m.skin} position={[0, -0.045, 0.262]}>
              <sphereGeometry args={[0.022, 12, 10]} />
            </mesh>
            {/* eyes */}
            <group ref={pupils}>
              {[[eyeL, 0.095], [eyeR, -0.095]].map(([ref, x], i) => (
                <group key={i} ref={ref as React.RefObject<THREE.Group>} position={[x as number, -0.005, 0.247]}>
                  <mesh material={m.dark} scale={[0.78, 1, 0.45]}><sphereGeometry args={[0.056, 18, 14]} /></mesh>
                  <mesh material={m.white} position={[0.016, 0.022, 0.024]}><sphereGeometry args={[0.014, 8, 6]} /></mesh>
                </group>
              ))}
            </group>
            {/* glasses */}
            {[0.095, -0.095].map((x) => (
              <mesh key={x} material={m.glasses} position={[x, 0.0, 0.258]}>
                <torusGeometry args={[0.07, 0.008, 8, 28]} />
              </mesh>
            ))}
            <mesh material={m.glasses} position={[0, 0.012, 0.262]}><boxGeometry args={[0.05, 0.01, 0.01]} /></mesh>
            {/* eyebrows */}
            <mesh ref={browL} material={m.brow} position={[0.095, 0.1, 0.276]}><boxGeometry args={[0.085, 0.018, 0.02]} /></mesh>
            <mesh ref={browR} material={m.brow} position={[-0.095, 0.1, 0.276]}><boxGeometry args={[0.085, 0.018, 0.02]} /></mesh>
            {/* mouths (blended by mood) */}
            <group position={[0, -0.088, 0.252]}>
              <mesh ref={(o) => { mouths.current.smile = o; }} material={m.mouth} rotation={[0, 0, Math.PI]}>
                <torusGeometry args={[0.045, 0.011, 8, 20, Math.PI]} />
              </mesh>
              <mesh ref={(o) => { mouths.current.frown = o; }} material={m.mouth} position={[0, -0.035, 0]}>
                <torusGeometry args={[0.04, 0.011, 8, 20, Math.PI]} />
              </mesh>
              <mesh ref={(o) => { mouths.current.flat = o; }} material={m.mouth} rotation={[0, 0, Math.PI / 2]}>
                <capsuleGeometry args={[0.01, 0.05, 4, 8]} />
              </mesh>
              <mesh ref={(o) => { mouths.current.o = o; }} material={m.mouth} scale={[0.8, 1, 0.5]}>
                <sphereGeometry args={[0.028, 12, 10]} />
              </mesh>
              <group ref={(o) => { mouths.current.grin = o; }}>
                <mesh material={m.mouth} rotation={[0, 0, Math.PI]} scale={[1, 1, 0.4]}>
                  <circleGeometry args={[0.055, 20, 0, Math.PI]} />
                </mesh>
              </group>
            </group>
            {/* blush */}
            {[[blushL, 0.165], [blushR, -0.165]].map(([ref, x], i) => (
              <mesh key={i} ref={ref as React.RefObject<THREE.Mesh>} material={m.blush}
                position={[x as number, -0.06, 0.218]} rotation={[0, (x as number) > 0 ? 0.6 : -0.6, 0]}>
                <circleGeometry args={[0.045, 16]} />
              </mesh>
            ))}
          </group>
        </group>
      </group>
    </group>
  );
}

function angleDamp(cur: number, target: number, rate: number, dt: number) {
  let d = target - cur;
  while (d > Math.PI) d -= Math.PI * 2;
  while (d < -Math.PI) d += Math.PI * 2;
  return cur + d * (1 - Math.exp(-rate * dt));
}

// ------------------------------------------------------------------ poses
interface Pose {
  legL: number; legR: number; armL: number; armR: number; armLz: number; armRz: number;
  foreL: number; foreR: number; lean: number; headPitch: number; headYaw: number; bodyY: number;
}

function pose(a: Activity, t: number, seat: number): Pose {
  const base: Pose = { legL: 0, legR: 0, armL: 0, armR: 0, armLz: 0.08, armRz: -0.08, foreL: -0.15, foreR: -0.15,
    lean: 0, headPitch: 0, headYaw: 0, bodyY: Math.sin(t * 1.8) * 0.006 };
  // seated: thighs forward, body lowered onto the chair
  const sitLegs = -1.45 * seat;
  const p = { ...base, legL: sitLegs, legR: sitLegs, bodyY: base.bodyY - 0.06 * seat };
  switch (a) {
    case "walk": {
      const s = Math.sin(t * 9);
      return { ...p, legL: s * 0.55, legR: -s * 0.55, armL: -s * 0.45, armR: s * 0.45, foreL: -0.35, foreR: -0.35,
        bodyY: Math.abs(Math.cos(t * 9)) * 0.035, lean: 0.06 };
    }
    case "type":
      return { ...p, armL: -0.95, armR: -0.95, foreL: -0.55 + Math.sin(t * 14) * 0.08, foreR: -0.55 + Math.sin(t * 14 + 2) * 0.08,
        armLz: 0.2, armRz: -0.2, lean: 0.08, headPitch: 0.12 + Math.sin(t * 0.7) * 0.03 };
    case "read_screen":
      return { ...p, armL: -0.7, armR: -0.7, foreL: -0.8, foreR: -0.8, armLz: 0.25, armRz: -0.25, lean: 0.12,
        headPitch: 0.05, headYaw: Math.sin(t * 0.4) * 0.05 };
    case "browse_books":
      return { ...p, armR: -2.0 + Math.sin(t * 1.2) * 0.2, foreR: -0.4, headPitch: -0.25 + Math.sin(t * 0.8) * 0.15,
        headYaw: Math.sin(t * 0.6) * 0.35 };
    case "read_book":
      return { ...p, armL: -0.95, armR: -0.95, foreL: -0.75, foreR: -0.75, armLz: 0.35, armRz: -0.35, headPitch: 0.35,
        headYaw: Math.sin(t * 0.5) * 0.06 };
    case "write_board":
      return { ...p, armR: -2.3 + Math.sin(t * 6) * 0.15, armRz: -0.2 + Math.cos(t * 6) * 0.15, foreR: -0.3,
        headPitch: -0.15, headYaw: Math.sin(t * 3) * 0.08 };
    case "pipette":
      return { ...p, armL: -1.0, armR: -1.1, foreL: -0.6, foreR: -0.7 + Math.max(0, Math.sin(t * 3)) * 0.25,
        armLz: 0.2, armRz: -0.2, lean: 0.12, headPitch: 0.35 };
    case "microscope":
      return { ...p, armL: -0.9, armR: -0.9, foreL: -0.4, foreR: -0.4 + Math.sin(t * 2) * 0.05, armLz: 0.3, armRz: -0.3,
        lean: 0.38, headPitch: 0.45 };
    case "operate_machine":
      return { ...p, armR: -1.3 + Math.max(0, Math.sin(t * 4)) * 0.2, foreR: -0.4, armL: -0.3, headPitch: -0.12,
        headYaw: Math.sin(t * 0.7) * 0.1 };
    case "drink_coffee": {
      const sip = Math.sin(t * 0.9) > 0.7 ? 1 : 0;
      return { ...p, armR: -0.8 - sip * 0.8, foreR: -1.2 - sip * 0.5, armRz: -0.15, headPitch: -0.1 * sip };
    }
    case "think":
      return { ...p, armR: -0.6, foreR: -2.0, armRz: 0.35, armL: -0.25, foreL: -1.2, armLz: 0.5,
        headPitch: -0.22, headYaw: Math.sin(t * 0.5) * 0.15 };
    case "celebrate": {
      const j = Math.abs(Math.sin(t * 6));
      return { ...p, armL: -2.8, armR: -2.8, armLz: 0.5 + Math.sin(t * 12) * 0.2, armRz: -0.5 - Math.sin(t * 12) * 0.2,
        foreL: 0, foreR: 0, bodyY: j * 0.18, headPitch: -0.2 };
    }
    case "sleep":
      return { ...p, armL: -1.3, armR: -1.3, foreL: -1.3, foreR: -1.3, armLz: 0.5, armRz: -0.5,
        lean: 0.75 + Math.sin(t * 1.2) * 0.02, headPitch: 0.3 };
    case "nap": // lying on her side (the body is rotated by the caller): knees drawn up a little, hands together
      return { ...base, legL: -0.45, legR: -0.35, armL: -0.9, armR: -0.75, foreL: -1.1, foreR: -1.2, armLz: 0.1,
        armRz: -0.1, lean: 0.05 + Math.sin(t * 1.1) * 0.015, headPitch: 0.15, bodyY: 0 };
    case "listen_music": { // leaning back, head bobbing, a foot tapping
      const beat = Math.sin(t * 4.2);
      return { ...p, legR: p.legR + Math.max(0, beat) * 0.12, armL: -0.45, armR: -0.45, foreL: -0.7, foreR: -0.7,
        armLz: 0.3, armRz: -0.3, lean: -0.12, headPitch: -0.05 + beat * 0.07, headYaw: Math.sin(t * 2.1) * 0.08 };
    }
    default:
      return p;
  }
}
