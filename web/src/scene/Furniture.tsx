import { useMemo, useRef, type ReactNode } from "react";
import { useFrame, type ThreeEvent } from "@react-three/fiber";
import { RoundedBox } from "@react-three/drei";
import * as THREE from "three";
import { C } from "./palette";
import { ScreenMesh } from "./ScreenMesh";
import { useWorld, type Inspectable } from "../world/store";
import type { Hypothesis } from "../world/protocol";

type V3 = [number, number, number];

function Clickable({ target, children }: { target: Inspectable; children: ReactNode }) {
  const inspect = useWorld((s) => s.inspect);
  return (
    <group
      onClick={(e: ThreeEvent<MouseEvent>) => { e.stopPropagation(); inspect(target); }}
      onPointerOver={(e) => { e.stopPropagation(); document.body.style.cursor = "pointer"; }}
      onPointerOut={() => { document.body.style.cursor = "auto"; }}
    >
      {children}
    </group>
  );
}

function Box({ args, position, color, radius = 0.03, rough = 0.6, rotation }: {
  args: V3; position: V3; color: string; radius?: number; rough?: number; rotation?: V3;
}) {
  return (
    <RoundedBox args={args} radius={Math.min(radius, Math.min(...args) / 2.01)} position={position} rotation={rotation}
      castShadow receiveShadow smoothness={3}>
      <meshStandardMaterial color={color} roughness={rough} />
    </RoundedBox>
  );
}

// ------------------------------------------------------------------ desk + computer
function Desk() {
  return (
    <group position={[1.0, 0, -3.45]}>
      <Box args={[2.1, 0.08, 1.0]} position={[0, 0.78, 0]} color={C.pink} />
      <Box args={[0.6, 0.72, 0.9]} position={[0.65, 0.37, 0]} color={C.white} />
      {[0.12, 0.36, 0.58].map((y) => (
        <Box key={y} args={[0.5, 0.02, 0.02]} position={[0.65, y, 0.46]} color={C.steel} radius={0.01} />
      ))}
      <Box args={[0.06, 0.74, 0.06]} position={[-0.98, 0.37, 0.42]} color={C.white} />
      <Box args={[0.06, 0.74, 0.06]} position={[-0.98, 0.37, -0.42]} color={C.white} />
      {/* monitor */}
      <Clickable target={{ kind: "screen", screen: "computer" }}>
        <group position={[-0.15, 0.82, -0.25]}>
          <Box args={[0.08, 0.28, 0.06]} position={[0, 0.14, -0.02]} color={C.ink} />
          <Box args={[0.36, 0.03, 0.22]} position={[0, 0.015, 0]} color={C.ink} />
          <Box args={[1.26, 0.8, 0.06]} position={[0, 0.66, 0]} color={C.ink} radius={0.04} />
          <group position={[0, 0.66, 0.032]}>
            <ScreenMesh screen="computer" size={[1.16, 0.7]} px={640} />
          </group>
        </group>
      </Clickable>
      {/* keyboard, mouse, mug, notebook */}
      <Box args={[0.62, 0.03, 0.2]} position={[-0.15, 0.835, 0.15]} color={C.offWhite} radius={0.012} />
      <Box args={[0.08, 0.03, 0.12]} position={[0.32, 0.835, 0.15]} color={C.offWhite} radius={0.015} />
      <mesh position={[0.78, 0.89, -0.1]} castShadow>
        <cylinderGeometry args={[0.06, 0.055, 0.14, 20]} />
        <meshStandardMaterial color={C.coral} />
      </mesh>
      <Box args={[0.34, 0.025, 0.26]} position={[0.62, 0.83, 0.22]} color={C.white} rotation={[0, 0.25, 0]} radius={0.01} />
    </group>
  );
}

function Chair() {
  // sits at the desk station; the researcher's seated pose matches its height
  return (
    <group position={[1.0, 0, -2.55]} rotation={[0, Math.PI, 0]}>
      <Box args={[0.55, 0.08, 0.52]} position={[0, 0.48, 0]} color={C.teal} radius={0.04} />
      <Box args={[0.5, 0.42, 0.06]} position={[0, 0.74, 0.27]} color={C.teal} radius={0.04} />
      <mesh position={[0, 0.25, 0]}>
        <cylinderGeometry args={[0.03, 0.03, 0.42, 10]} />
        <meshStandardMaterial color={C.ink} />
      </mesh>
      {[0, 1, 2, 3, 4].map((i) => (
        <mesh key={i} position={[Math.sin((i / 5) * Math.PI * 2) * 0.22, 0.04, Math.cos((i / 5) * Math.PI * 2) * 0.22]}>
          <sphereGeometry args={[0.04, 10, 8]} />
          <meshStandardMaterial color={C.ink} />
        </mesh>
      ))}
    </group>
  );
}

// ------------------------------------------------------------------ bookshelf (the library)
const SPINE_COLORS = [C.coral, C.pink, C.teal, C.rose, "#e3c46a", "#7aa6c2", C.offWhite, "#9fc58f"];

function Bookshelf() {
  const library = useWorld((s) => s.library);
  const books = useMemo(() => {
    const out: { pos: V3; h: number; w: number; color: string; mine: boolean }[] = [];
    const shelves = [0.28, 0.9, 1.52, 2.14];
    let li = 0;
    shelves.forEach((y, si) => {
      let x = -0.9;
      let k = 0;
      while (x < 0.85) {
        const w = 0.07 + ((si * 7 + k * 13) % 5) * 0.012;
        const h = 0.36 + ((si * 3 + k * 5) % 4) * 0.04;
        const mine = li < library.length && si >= 2;
        const color = mine ? library[li].color : SPINE_COLORS[(si * 5 + k * 3) % SPINE_COLORS.length];
        if (mine) li++;
        if (!(si === 1 && k > 9 && k < 13)) out.push({ pos: [x + w / 2, y + h / 2, 0], h, w, color, mine });
        x += w + 0.012;
        k++;
      }
    });
    return out;
  }, [library]);
  return (
    <Clickable target={{ kind: "library" }}>
      <group position={[-1.5, 0, -3.72]}>
        <Box args={[2.0, 2.66, 0.08]} position={[0, 1.33, -0.21]} color={C.tealDark} radius={0.02} />
        <Box args={[0.08, 2.66, 0.5]} position={[-0.98, 1.33, 0]} color={C.tealDark} radius={0.02} />
        <Box args={[0.08, 2.66, 0.5]} position={[0.98, 1.33, 0]} color={C.tealDark} radius={0.02} />
        {[0.04, 0.86, 1.48, 2.1, 2.66].map((y) => (
          <Box key={y} args={[2.0, 0.06, 0.5]} position={[0, y - 0.02, 0]} color={C.tealDark} radius={0.02} />
        ))}
        {books.map((b, i) => (
          <mesh key={i} position={b.pos} castShadow>
            <boxGeometry args={[b.w, b.h, 0.34]} />
            <meshStandardMaterial color={b.color} roughness={0.7}
              emissive={b.mine ? b.color : "#000"} emissiveIntensity={b.mine ? 0.25 : 0} />
          </mesh>
        ))}
        {/* a small globe and a skull model on the shelf, like a real lab */}
        <mesh position={[0.55, 1.08, 0.02]} castShadow>
          <sphereGeometry args={[0.13, 24, 16]} />
          <meshStandardMaterial color="#7aa6c2" roughness={0.4} />
        </mesh>
      </group>
    </Clickable>
  );
}

// ------------------------------------------------------------------ patient simulator
function Simulator() {
  const leds = useRef<THREE.Group>(null);
  useFrame(({ clock }) => {
    leds.current?.children.forEach((c, i) => {
      const m = (c as THREE.Mesh).material as THREE.MeshStandardMaterial;
      m.emissiveIntensity = 0.5 + 1.5 * Math.max(0, Math.sin(clock.elapsedTime * (2 + i) + i));
    });
  });
  return (
    <Clickable target={{ kind: "screen", screen: "simulator" }}>
      <group position={[-3.3, 0, -3.5]}>
        <Box args={[1.15, 2.2, 0.85]} position={[0, 1.1, 0]} color={C.white} radius={0.06} />
        <Box args={[1.17, 0.3, 0.87]} position={[0, 0.15, 0]} color={C.tealDark} radius={0.05} />
        <Box args={[0.98, 0.66, 0.04]} position={[0, 1.5, 0.42]} color={C.ink} radius={0.03} />
        <group position={[0, 1.5, 0.445]}>
          <ScreenMesh screen="simulator" size={[0.9, 0.58]} px={512} />
        </group>
        <group ref={leds} position={[-0.35, 0.95, 0.43]}>
          {[0, 1, 2, 3].map((i) => (
            <mesh key={i} position={[i * 0.12, 0, 0]}>
              <sphereGeometry args={[0.03, 10, 8]} />
              <meshStandardMaterial color={["#5fd3a5", "#ffbd3e", "#5fd3a5", "#ff6b5e"][i]}
                emissive={["#5fd3a5", "#ffbd3e", "#5fd3a5", "#ff6b5e"][i]} toneMapped={false} />
            </mesh>
          ))}
        </group>
        <Box args={[0.6, 0.12, 0.02]} position={[0.2, 0.95, 0.43]} color={C.tealDark} radius={0.01} />
        {[0.55, 0.62, 0.69].map((y) => (
          <Box key={y} args={[0.8, 0.025, 0.02]} position={[0, y, 0.43]} color={C.offWhite} radius={0.01} />
        ))}
      </group>
    </Clickable>
  );
}

// ------------------------------------------------------------------ bench, microscope, wall shelf
function Flask({ position, color, scale = 1 }: { position: V3; color: string; scale?: number }) {
  return (
    <group position={position} scale={scale}>
      <mesh position={[0, 0.11, 0]}>
        <coneGeometry args={[0.12, 0.22, 24, 1, true]} />
        <meshPhysicalMaterial color="#e8fbff" transparent opacity={0.35} roughness={0.05} side={THREE.DoubleSide} />
      </mesh>
      <mesh position={[0, 0.07, 0]}>
        <coneGeometry args={[0.1, 0.14, 24]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.9} toneMapped={false} />
      </mesh>
      <mesh position={[0, 0.27, 0]}>
        <cylinderGeometry args={[0.03, 0.03, 0.12, 12, 1, true]} />
        <meshPhysicalMaterial color="#e8fbff" transparent opacity={0.4} side={THREE.DoubleSide} />
      </mesh>
    </group>
  );
}

function Microscope({ position }: { position: V3 }) {
  return (
    <group position={position} rotation={[0, Math.PI / 2, 0]}>
      <Box args={[0.34, 0.06, 0.26]} position={[0, 0.03, 0]} color={C.teal} />
      <Box args={[0.08, 0.38, 0.1]} position={[0, 0.25, -0.08]} color={C.teal} />
      <Box args={[0.24, 0.03, 0.18]} position={[0, 0.17, 0.02]} color={C.ink} />
      <mesh position={[0, 0.38, 0.03]} rotation={[0.5, 0, 0]}>
        <cylinderGeometry args={[0.035, 0.045, 0.3, 14]} />
        <meshStandardMaterial color={C.white} />
      </mesh>
      <mesh position={[0, 0.25, 0.04]}>
        <cylinderGeometry args={[0.025, 0.02, 0.1, 10]} />
        <meshStandardMaterial color={C.ink} />
      </mesh>
    </group>
  );
}

function Bench() {
  return (
    <group>
      {/* base cabinets along the left wall */}
      <Box args={[1.0, 0.86, 3.8]} position={[-3.5, 0.43, -0.2]} color={C.tealDark} radius={0.04} />
      {[-1.6, -0.65, 0.3, 1.25].map((z) => (
        <group key={z}>
          <Box args={[0.02, 0.7, 0.86]} position={[-2.995, 0.45, z]} color={C.teal} radius={0.01} />
          <Box args={[0.03, 0.03, 0.22]} position={[-2.975, 0.72, z]} color={C.steel} radius={0.01} />
        </group>
      ))}
      <Box args={[1.08, 0.07, 3.9]} position={[-3.48, 0.895, -0.2]} color={C.white} radius={0.03} />
      {/* sink + faucet */}
      <mesh position={[-3.5, 0.9, -1.45]}>
        <boxGeometry args={[0.6, 0.02, 0.55]} />
        <meshStandardMaterial color="#cdd7da" roughness={0.2} metalness={0.4} />
      </mesh>
      <mesh position={[-3.85, 1.1, -1.45]}>
        <cylinderGeometry args={[0.025, 0.025, 0.4, 10]} />
        <meshStandardMaterial color={C.steel} metalness={0.6} roughness={0.3} />
      </mesh>
      <mesh position={[-3.72, 1.29, -1.45]} rotation={[0, 0, Math.PI / 2]}>
        <cylinderGeometry args={[0.022, 0.022, 0.28, 10]} />
        <meshStandardMaterial color={C.steel} metalness={0.6} roughness={0.3} />
      </mesh>
      {/* glassware, rack, pipette, sample box */}
      <Flask position={[-3.4, 0.93, -0.75]} color={C.glow} />
      <Flask position={[-3.65, 0.93, -0.45]} color="#7fd9ff" scale={0.8} />
      <Flask position={[-3.3, 0.93, -0.2]} color="#ff9f8a" scale={0.7} />
      <group position={[-3.6, 0.93, 0.25]}>
        <Box args={[0.36, 0.08, 0.14]} position={[0, 0.1, 0]} color={C.coral} radius={0.01} />
        {[0, 1, 2, 3, 4].map((i) => (
          <mesh key={i} position={[-0.14 + i * 0.07, 0.15, 0]}>
            <cylinderGeometry args={[0.018, 0.018, 0.24, 8]} />
            <meshStandardMaterial color={["#ff9f8a", "#9cf06b", "#7fd9ff", "#ffd36b", "#c7a2ff"][i]} transparent opacity={0.85} />
          </mesh>
        ))}
      </group>
      <Microscope position={[-3.45, 0.93, 0.95]} />
      {/* digital display for the microscope */}
      <Clickable target={{ kind: "screen", screen: "microscope" }}>
        <group position={[-3.96, 2.0, 0.95]} rotation={[0, Math.PI / 2, 0]}>
          <Box args={[0.98, 0.64, 0.05]} position={[0, 0, 0]} color={C.ink} radius={0.03} />
          <group position={[0, 0, 0.028]}>
            <ScreenMesh screen="microscope" size={[0.9, 0.56]} px={512} />
          </group>
        </group>
      </Clickable>
      {/* wall shelf with jars and binders */}
      <group position={[-3.82, 2.55, -1.1]}>
        <Box args={[0.34, 0.05, 1.7]} position={[0, 0, 0]} color={C.tealDark} radius={0.02} />
        {[-0.65, -0.35, -0.05].map((z, i) => (
          <mesh key={z} position={[0.02, 0.15, z]} castShadow>
            <cylinderGeometry args={[0.09, 0.09, 0.26, 18]} />
            <meshPhysicalMaterial color={["#bfe8c9", "#f5d0b5", "#cde3f7"][i]} transparent opacity={0.75} roughness={0.1} />
          </mesh>
        ))}
        {[0.25, 0.36, 0.47, 0.58].map((z, i) => (
          <mesh key={z} position={[0.02, 0.2, z]} castShadow>
            <boxGeometry args={[0.24, 0.36, 0.09]} />
            <meshStandardMaterial color={SPINE_COLORS[i + 1]} />
          </mesh>
        ))}
      </group>
    </group>
  );
}

// ------------------------------------------------------------------ whiteboard of hypotheses
const STATUS_COLOR: Record<Hypothesis["status"], string> = {
  open: "#ffe08a", testing: "#9fd4ff", supported: "#a8e6a1", refuted: "#f4a7a0",
};

function Whiteboard() {
  const board = useWorld((s) => s.board);
  const tex = useMemo(() => {
    const W = 760, H = 520;
    const cv = document.createElement("canvas");
    cv.width = W; cv.height = H;
    const g = cv.getContext("2d")!;
    g.fillStyle = "#fbfbf8";
    g.fillRect(0, 0, W, H);
    g.fillStyle = "#3a4a52";
    g.font = "800 30px Nunito, sans-serif";
    g.fillText("Hypotheses", 24, 46);
    board.slice(-6).forEach((h, i) => {
      const x = 24 + (i % 3) * 244, y = 72 + Math.floor(i / 3) * 216;
      g.save();
      g.translate(x + 110, y + 95);
      g.rotate(((i * 37) % 7 - 3) * 0.012);
      g.fillStyle = STATUS_COLOR[h.status];
      g.shadowColor = "rgba(0,0,0,0.15)";
      g.shadowBlur = 8;
      g.fillRect(-110, -95, 220, 190);
      g.shadowBlur = 0;
      g.fillStyle = "#2b3a40";
      g.font = "600 19px Nunito, sans-serif";
      const words = h.text.split(" ");
      let line = "", ly = -64;
      for (const w of words) {
        const t = line ? line + " " + w : w;
        if (g.measureText(t).width > 190) { g.fillText(line, -98, ly); ly += 23; line = w; }
        else line = t;
        if (ly > 60) break;
      }
      if (ly <= 60) g.fillText(line, -98, ly);
      g.font = "800 15px Nunito, sans-serif";
      g.fillStyle = "#4b5d64";
      g.fillText(h.status.toUpperCase(), -98, 84);
      g.restore();
    });
    const t = new THREE.CanvasTexture(cv);
    t.colorSpace = THREE.SRGBColorSpace;
    t.anisotropy = 8;
    return t;
  }, [board]);
  return (
    <Clickable target={{ kind: "board" }}>
      <group position={[-3.96, 2.2, 2.85]} rotation={[0, Math.PI / 2, 0]}>
        <Box args={[2.05, 1.42, 0.05]} position={[0, 0, 0]} color={C.steel} radius={0.03} />
        <mesh position={[0, 0, 0.03]}>
          <planeGeometry args={[1.94, 1.32]} />
          <meshStandardMaterial map={tex} roughness={0.5} />
        </mesh>
        <Box args={[1.6, 0.05, 0.12]} position={[0, -0.74, 0.06]} color={C.steel} radius={0.02} />
      </group>
    </Clickable>
  );
}

// ------------------------------------------------------------------ coffee corner, plants, stool
function Plant({ position, scale = 1 }: { position: V3; scale?: number }) {
  return (
    <group position={position} scale={scale}>
      <mesh position={[0, 0.18, 0]} castShadow>
        <cylinderGeometry args={[0.2, 0.15, 0.36, 20]} />
        <meshStandardMaterial color={C.rose} />
      </mesh>
      {[...Array(9)].map((_, i) => (
        <mesh key={i} position={[Math.sin(i * 2.4) * 0.08, 0.55 + (i % 3) * 0.06, Math.cos(i * 2.4) * 0.08]}
          rotation={[Math.cos(i * 2.4) * 0.5, 0, -Math.sin(i * 2.4) * 0.5]} castShadow>
          <coneGeometry args={[0.07, 0.55, 6]} />
          <meshStandardMaterial color={i % 2 ? "#8bc34a" : "#a6d65c"} roughness={0.6} />
        </mesh>
      ))}
    </group>
  );
}

function CoffeeCorner() {
  return (
    <group position={[3.1, 0, -3.6]}>
      <Box args={[1.4, 0.9, 0.7]} position={[0, 0.45, 0]} color={C.white} />
      <Box args={[1.46, 0.06, 0.76]} position={[0, 0.92, 0]} color={C.pink} />
      <Box args={[0.42, 0.55, 0.38]} position={[-0.25, 1.22, -0.05]} color={C.ink} radius={0.05} />
      <Box args={[0.3, 0.06, 0.12]} position={[-0.25, 1.32, 0.17]} color={C.steel} radius={0.02} />
      <mesh position={[-0.25, 0.99, 0.12]}>
        <cylinderGeometry args={[0.05, 0.045, 0.1, 16]} />
        <meshStandardMaterial color={C.white} />
      </mesh>
      {[0.2, 0.36].map((x, i) => (
        <mesh key={x} position={[x, 1.0, 0.05]} castShadow>
          <cylinderGeometry args={[0.055, 0.05, 0.12, 16]} />
          <meshStandardMaterial color={i ? C.teal : C.coral} />
        </mesh>
      ))}
    </group>
  );
}

function Stool({ position }: { position: V3 }) {
  return (
    <group position={position}>
      <mesh position={[0, 0.62, 0]} castShadow>
        <cylinderGeometry args={[0.24, 0.24, 0.08, 24]} />
        <meshStandardMaterial color={C.pink} />
      </mesh>
      {[0, 1, 2].map((i) => (
        <mesh key={i} position={[Math.sin(i * 2.09) * 0.14, 0.3, Math.cos(i * 2.09) * 0.14]}
          rotation={[Math.cos(i * 2.09) * 0.18, 0, -Math.sin(i * 2.09) * 0.18]}>
          <cylinderGeometry args={[0.018, 0.018, 0.62, 8]} />
          <meshStandardMaterial color={C.steel} metalness={0.5} roughness={0.3} />
        </mesh>
      ))}
      <mesh position={[0, 0.25, 0]} rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[0.15, 0.012, 8, 24]} />
        <meshStandardMaterial color={C.steel} metalness={0.5} />
      </mesh>
    </group>
  );
}

export function Furniture() {
  return (
    <group>
      <Desk />
      <Chair />
      <Bookshelf />
      <Simulator />
      <Bench />
      <Whiteboard />
      <CoffeeCorner />
      <Plant position={[3.55, 0, 3.4]} scale={1.3} />
      <Plant position={[3.8, 0.92, -3.85]} scale={0.6} />
      <Stool position={[2.0, 0, 1.6]} />
    </group>
  );
}
