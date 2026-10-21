import { useEffect, useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import type { ScreenId } from "../world/protocol";
import { useWorld } from "../world/store";
import { drawScreen } from "./drawScreen";

/** A glowing monitor face that shows a live screen from the world state. */
export function ScreenMesh({ screen, size, px = 512 }: { screen: ScreenId; size: [number, number]; px?: number }) {
  const content = useWorld((s) => s.screens[screen]);
  const W = px;
  const H = Math.round((px * size[1]) / size[0]);
  const { canvas, tex } = useMemo(() => {
    const canvas = document.createElement("canvas");
    canvas.width = W;
    canvas.height = H;
    const tex = new THREE.CanvasTexture(canvas);
    tex.colorSpace = THREE.SRGBColorSpace;
    tex.anisotropy = 8;
    return { canvas, tex };
  }, [W, H]);
  const since = useRef(performance.now());
  const last = useRef(0);
  useEffect(() => {
    since.current = performance.now();
  }, [content]);
  useFrame(() => {
    const now = performance.now();
    if (now - last.current < 80) return; // ~12 fps is plenty for a screen
    last.current = now;
    const g = canvas.getContext("2d")!;
    drawScreen(g, W, H, content, (now - since.current) / 1000);
    tex.needsUpdate = true;
  });
  return (
    <mesh>
      <planeGeometry args={size} />
      <meshBasicMaterial map={tex} toneMapped={false} />
    </mesh>
  );
}
