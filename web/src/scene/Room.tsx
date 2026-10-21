import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { RoundedBox } from "@react-three/drei";
import * as THREE from "three";
import { C } from "./palette";

/** A canvas texture of square tiles with grout lines. */
function tileTexture(color: string, line: string, tiles: [number, number], px = 64): THREE.CanvasTexture {
  const [tx, ty] = tiles;
  const cv = document.createElement("canvas");
  cv.width = tx * px;
  cv.height = ty * px;
  const g = cv.getContext("2d")!;
  g.fillStyle = color;
  g.fillRect(0, 0, cv.width, cv.height);
  g.strokeStyle = line;
  g.lineWidth = 3;
  for (let i = 0; i <= tx; i++) {
    g.beginPath(); g.moveTo(i * px, 0); g.lineTo(i * px, cv.height); g.stroke();
  }
  for (let j = 0; j <= ty; j++) {
    g.beginPath(); g.moveTo(0, j * px); g.lineTo(cv.width, j * px); g.stroke();
  }
  // a soft highlight on each tile so the floor reads as glazed ceramic
  for (let i = 0; i < tx; i++)
    for (let j = 0; j < ty; j++) {
      const grd = g.createLinearGradient(i * px, j * px, (i + 1) * px, (j + 1) * px);
      grd.addColorStop(0, "rgba(255,255,255,0.10)");
      grd.addColorStop(1, "rgba(0,0,0,0.06)");
      g.fillStyle = grd;
      g.fillRect(i * px + 2, j * px + 2, px - 4, px - 4);
    }
  const t = new THREE.CanvasTexture(cv);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 8;
  return t;
}

function Floor() {
  const tex = useMemo(() => tileTexture(C.tile, C.tileDark, [8, 8], 96), []);
  return (
    <group>
      {/* diorama base */}
      <RoundedBox args={[8.9, 0.7, 8.9]} radius={0.12} position={[0.05, -0.36, 0.05]} receiveShadow>
        <meshStandardMaterial color={C.base} roughness={0.5} />
      </RoundedBox>
      <mesh position={[0, 0.001, 0]} rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
        <planeGeometry args={[8, 8]} />
        <meshStandardMaterial map={tex} roughness={0.22} metalness={0.05} />
      </mesh>
      {/* skirting edge where the tiles meet the base */}
      <mesh position={[0.05, -0.02, 4.02]}>
        <boxGeometry args={[8.1, 0.06, 0.06]} />
        <meshStandardMaterial color={C.baseRim} />
      </mesh>
      <mesh position={[4.02, -0.02, 0.05]}>
        <boxGeometry args={[0.06, 0.06, 8.1]} />
        <meshStandardMaterial color={C.baseRim} />
      </mesh>
    </group>
  );
}

function Wall({ side }: { side: "left" | "back" }) {
  const H = 4.6;
  const wTex = useMemo(() => tileTexture(C.wainscot, C.wainscotLine, [16, 3], 64), []);
  const left = side === "left";
  const pos: [number, number, number] = left ? [-4.12, H / 2, -0.06] : [-0.06, H / 2, -4.12];
  const size: [number, number, number] = left ? [0.24, H, 8.24] : [8.24, H, 0.24];
  return (
    <group>
      <mesh position={pos} castShadow receiveShadow>
        <boxGeometry args={size} />
        <meshStandardMaterial color={C.wall} roughness={0.9} />
      </mesh>
      {/* tiled lower half */}
      <mesh
        position={left ? [-3.995, 0.8, 0] : [0, 0.8, -3.995]}
        rotation={left ? [0, Math.PI / 2, 0] : [0, 0, 0]}
        receiveShadow
      >
        <planeGeometry args={[8, 1.6]} />
        <meshStandardMaterial map={wTex} roughness={0.3} />
      </mesh>
      {/* chair rail */}
      <mesh position={left ? [-3.97, 1.62, 0] : [0, 1.62, -3.97]}>
        <boxGeometry args={left ? [0.06, 0.06, 8] : [8, 0.06, 0.06]} />
        <meshStandardMaterial color={C.trim} />
      </mesh>
      {/* top cap: the cut-away edge of the diorama */}
      <mesh position={left ? [-4.12, H + 0.04, -0.06] : [-0.06, H + 0.04, -4.12]}>
        <boxGeometry args={left ? [0.3, 0.08, 8.3] : [8.3, 0.08, 0.3]} />
        <meshStandardMaterial color={C.trim} />
      </mesh>
    </group>
  );
}

/** Round window on the left wall; the sky follows the real time of day. */
function Window() {
  const sky = useRef<THREE.MeshBasicMaterial>(null);
  useFrame(() => {
    if (!sky.current) return;
    const h = new Date().getHours() + new Date().getMinutes() / 60;
    const day = Math.max(0, Math.sin(((h - 6) / 12) * Math.PI)); // 0 at night, 1 at noon
    const night = new THREE.Color("#1b2547");
    const dusk = new THREE.Color("#f1a37a");
    const noon = new THREE.Color("#8fd0f2");
    const c = day < 0.35 ? night.clone().lerp(dusk, day / 0.35) : dusk.clone().lerp(noon, (day - 0.35) / 0.65);
    sky.current.color.copy(c);
  });
  return (
    <group position={[-3.99, 3.35, -0.4]} rotation={[0, Math.PI / 2, 0]}>
      <mesh>
        <circleGeometry args={[0.62, 48]} />
        <meshBasicMaterial ref={sky} color="#8fd0f2" toneMapped={false} />
      </mesh>
      <mesh position={[0, 0, 0.02]}>
        <torusGeometry args={[0.64, 0.07, 12, 48]} />
        <meshStandardMaterial color={C.trim} />
      </mesh>
      <mesh position={[0, 0, 0.02]}>
        <boxGeometry args={[1.25, 0.05, 0.04]} />
        <meshStandardMaterial color={C.trim} />
      </mesh>
      <mesh position={[0, 0, 0.02]}>
        <boxGeometry args={[0.05, 1.25, 0.04]} />
        <meshStandardMaterial color={C.trim} />
      </mesh>
    </group>
  );
}

/** Wall clock showing the real local time. */
function Clock() {
  const hour = useRef<THREE.Group>(null);
  const minute = useRef<THREE.Group>(null);
  const second = useRef<THREE.Group>(null);
  useFrame(() => {
    const d = new Date();
    const s = d.getSeconds() + d.getMilliseconds() / 1000;
    const m = d.getMinutes() + s / 60;
    const h = (d.getHours() % 12) + m / 60;
    if (second.current) second.current.rotation.z = -(s / 60) * Math.PI * 2;
    if (minute.current) minute.current.rotation.z = -(m / 60) * Math.PI * 2;
    if (hour.current) hour.current.rotation.z = -(h / 12) * Math.PI * 2;
  });
  return (
    <group position={[1.0, 3.85, -3.96]}>
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <cylinderGeometry args={[0.36, 0.36, 0.06, 40]} />
        <meshStandardMaterial color={C.trim} />
      </mesh>
      <mesh position={[0, 0, 0.035]} rotation={[Math.PI / 2, 0, 0]}>
        <cylinderGeometry args={[0.31, 0.31, 0.02, 40]} />
        <meshStandardMaterial color={C.white} />
      </mesh>
      {[...Array(12)].map((_, i) => (
        <mesh key={i} position={[Math.sin((i / 12) * Math.PI * 2) * 0.25, Math.cos((i / 12) * Math.PI * 2) * 0.25, 0.05]}>
          <boxGeometry args={[0.025, 0.025, 0.01]} />
          <meshStandardMaterial color={C.ink} />
        </mesh>
      ))}
      <group ref={hour} position={[0, 0, 0.06]}>
        <mesh position={[0, 0.07, 0]}><boxGeometry args={[0.035, 0.15, 0.01]} /><meshStandardMaterial color={C.ink} /></mesh>
      </group>
      <group ref={minute} position={[0, 0, 0.065]}>
        <mesh position={[0, 0.1, 0]}><boxGeometry args={[0.022, 0.21, 0.01]} /><meshStandardMaterial color={C.ink} /></mesh>
      </group>
      <group ref={second} position={[0, 0, 0.07]}>
        <mesh position={[0, 0.1, 0]}><boxGeometry args={[0.008, 0.22, 0.01]} /><meshStandardMaterial color={C.coral} /></mesh>
      </group>
    </group>
  );
}

function WallLight({ position, rotation }: { position: [number, number, number]; rotation?: [number, number, number] }) {
  return (
    <group position={position} rotation={rotation}>
      <RoundedBox args={[0.9, 0.16, 0.12]} radius={0.04}>
        <meshStandardMaterial color={C.white} emissive="#fff3d6" emissiveIntensity={2.2} toneMapped={false} />
      </RoundedBox>
    </group>
  );
}

export function Room() {
  return (
    <group>
      <Floor />
      <Wall side="left" />
      <Wall side="back" />
      <Window />
      <Clock />
      <WallLight position={[3.0, 4.1, -3.95]} />
      <WallLight position={[-3.95, 4.1, 2.4]} rotation={[0, Math.PI / 2, 0]} />
    </group>
  );
}
