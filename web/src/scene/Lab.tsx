import { useEffect, useRef } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { ContactShadows, OrbitControls, OrthographicCamera } from "@react-three/drei";
import { Bloom, EffectComposer, N8AO, Vignette } from "@react-three/postprocessing";
import * as THREE from "three";
import { Room } from "./Room";
import { Furniture } from "./Furniture";
import { Character } from "./Character";
import { useWorld } from "../world/store";
import { anchors } from "../world/anchors";

const ROOM_TARGET = new THREE.Vector3(0, 1.4, 0);
const ISO_OFFSET = new THREE.Vector3(13, 10.1, 13); // camera position relative to its target

/** Fits the whole diorama to the window; in follow mode, glides in close to the researcher. */
function CameraRig() {
  const camera = useThree((s) => s.camera) as THREE.OrthographicCamera;
  const size = useThree((s) => s.size);
  const controls = useThree((s) => s.controls) as unknown as { target: THREE.Vector3; update: () => void } | null;
  const follow = useWorld((s) => s.follow);
  const followZoom = useWorld((s) => s.followZoom);
  const fit = Math.max(28, Math.min(size.width / 13.5, size.height / 12.5));
  const goal = useRef(new THREE.Vector3());
  const moving = useRef(0);
  useEffect(() => {
    camera.zoom = fit;
    camera.updateProjectionMatrix();
  }, [camera, fit]);
  useEffect(() => {
    moving.current = 2.5; // seconds of easing after a mode switch
  }, [follow]);
  useFrame((_, dt) => {
    if (!controls) return;
    if (follow) {
      goal.current.set(anchors.headWorld.x, anchors.headWorld.y - 0.2 * (3.2 / followZoom), anchors.headWorld.z);
    } else if (moving.current > 0) {
      goal.current.copy(ROOM_TARGET);
    } else return; // room view: leave the camera to the user's own orbiting and zooming
    moving.current -= dt;
    const k = 1 - Math.exp(-4 * dt);
    const offset = camera.position.clone().sub(controls.target);
    controls.target.lerp(goal.current, k);
    camera.position.copy(controls.target).add(follow ? offset.lerp(ISO_OFFSET, k) : offset);
    const wantZoom = follow ? fit * followZoom : fit;
    camera.zoom += (wantZoom - camera.zoom) * k;
    camera.updateProjectionMatrix();
    controls.update();
  });
  return null;
}

export function Lab() {
  const inspect = useWorld((s) => s.inspect);
  return (
    <Canvas
      shadows
      dpr={[1, 2]}
      gl={{ antialias: true, toneMapping: THREE.ACESFilmicToneMapping }}
      onPointerMissed={() => inspect(null)}
    >
      <color attach="background" args={["#0d2f3a"]} />
      <fog attach="fog" args={["#0d2f3a", 40, 70]} />
      <OrthographicCamera makeDefault position={[13, 11.5, 13]} zoom={62} near={0.1} far={200} />
      <CameraRig />
      <OrbitControls
        makeDefault
        target={[0, 1.4, 0]}
        enablePan={false}
        minZoom={25}
        maxZoom={220}
        minAzimuthAngle={Math.PI / 4 - 0.5}
        maxAzimuthAngle={Math.PI / 4 + 0.5}
        minPolarAngle={0.75}
        maxPolarAngle={1.15}
        enableDamping
      />

      <hemisphereLight args={["#fff6e8", "#1d5560", 0.85]} />
      <directionalLight
        position={[7, 12, 6]}
        intensity={2.1}
        color="#fff1dd"
        castShadow
        shadow-mapSize={[2048, 2048]}
        shadow-camera-left={-8}
        shadow-camera-right={8}
        shadow-camera-top={8}
        shadow-camera-bottom={-8}
        shadow-bias={-0.0004}
        shadow-normalBias={0.02}
      />
      <pointLight position={[-2, 3.6, 1]} intensity={6} distance={9} color="#d8f3ff" />
      <pointLight position={[2.5, 3.6, -2.5]} intensity={5} distance={8} color="#ffe9c9" />

      <Room />
      <Furniture />
      <Character />
      <ContactShadows position={[0, 0.005, 0]} scale={9} blur={2.4} opacity={0.35} far={2} />

      <EffectComposer multisampling={4}>
        <N8AO aoRadius={0.6} intensity={2.2} distanceFalloff={0.8} />
        <Bloom intensity={0.55} luminanceThreshold={0.85} luminanceSmoothing={0.2} mipmapBlur />
        <Vignette darkness={0.45} offset={0.3} />
      </EffectComposer>
    </Canvas>
  );
}
