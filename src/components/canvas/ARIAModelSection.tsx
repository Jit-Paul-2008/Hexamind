"use client";

import { Canvas, useFrame, extend } from "@react-three/fiber";
import { Environment, MeshTransmissionMaterial } from "@react-three/drei";
import { useRef, useEffect, useState, useMemo } from "react";
import * as THREE from "three";
import { motion, useInView } from "framer-motion";

// ─────────────────────────────────────────────────────────────────────────────
// Build the custom bipyramid geometry that matches the reference image.
// Shape: an elongated double-ended crystal (bipyramid) with a 4-sided square
// waist, tilted ~30° along the Z-axis so the apices read upper-right / lower-left.
// ─────────────────────────────────────────────────────────────────────────────
function buildCrystalGeometry(): THREE.BufferGeometry {
  //   v0  — upper apex  (primary spike, upper-right direction)
  //   v1  — lower apex  (primary spike, lower-left direction)
  //   v2–v5 — belt ring (square cross-section at the crystal waist)
  const v0 = new THREE.Vector3(2.0, 0.0, 0.0);   // upper apex (pre-tilt)
  const v1 = new THREE.Vector3(-2.0, 0.0, 0.0);   // lower apex (pre-tilt)
  // Offset the belt slightly from centre to give the shape its irregular
  // "crystal" look rather than a perfectly symmetric diamond.
  const v2 = new THREE.Vector3(-0.1, 0.75, 0.65);  // belt front-top
  const v3 = new THREE.Vector3(0.45, 0.35, -0.65); // belt back-top
  const v4 = new THREE.Vector3(0.1, -0.75, 0.65);  // belt front-bottom
  const v5 = new THREE.Vector3(-0.45, -0.35, -0.65); // belt back-bottom

  const positions = new Float32Array([
    ...v0.toArray(),
    ...v1.toArray(),
    ...v2.toArray(),
    ...v3.toArray(),
    ...v4.toArray(),
    ...v5.toArray(),
  ]);

  // 8 triangular faces — 4 on each pyramid half
  // Winding is ordered so computed normals face outward.
  const indices = new Uint16Array([
    // Upper pyramid (apex = v0)
    0, 2, 3,
    0, 3, 4,
    0, 4, 5,
    0, 5, 2,
    // Lower pyramid (apex = v1)
    1, 3, 2,
    1, 4, 3,
    1, 5, 4,
    1, 2, 5,
  ]);

  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geo.setIndex(new THREE.BufferAttribute(indices, 1));
  geo.computeVertexNormals();
  return geo;
}

// ─────────────────────────────────────────────────────────────────────────────
// The rotating ARIA Crystal
// ─────────────────────────────────────────────────────────────────────────────
function ARIACrystal({ visible }: { visible: boolean }) {
  const groupRef = useRef<THREE.Group>(null);
  const meshRef = useRef<THREE.Mesh>(null);
  const edgesRef = useRef<THREE.LineSegments>(null);

  // Build geometry once
  const crystalGeo = useMemo(() => buildCrystalGeometry(), []);

  // Edge geometry for the wireframe overlay
  const edgesGeo = useMemo(() => new THREE.EdgesGeometry(crystalGeo, 1), [crystalGeo]);

  useFrame((state, delta) => {
    if (!visible || !groupRef.current) return;
    // Slow continuous rotation — matches the constant-motion requirement
    groupRef.current.rotation.y += delta * 0.22;
    groupRef.current.rotation.x += delta * 0.08;
    // Gentle vertical float
    groupRef.current.position.y = Math.sin(state.clock.elapsedTime * 0.7) * 0.14;
    // Subtle breathing pulse on the edge opacity
    if (edgesRef.current) {
      const mat = edgesRef.current.material as THREE.LineBasicMaterial;
      mat.opacity = 0.25 + Math.sin(state.clock.elapsedTime * 1.2) * 0.1;
    }
  });

  if (!visible) return null;

  return (
    // Tilt the whole crystal ~30° so it reads upper-right / lower-left (matching reference)
    <group ref={groupRef} rotation={[0, 0, Math.PI / 6]}>
      {/* ── Dark glass solid ── */}
      <mesh ref={meshRef} geometry={crystalGeo} castShadow receiveShadow>
        <MeshTransmissionMaterial
          backside
          backsideThickness={0.5}
          thickness={0.6}
          roughness={0.08}
          transmission={0.92}
          ior={1.5}
          chromaticAberration={0.04}
          anisotropy={0.15}
          distortionScale={0.05}
          temporalDistortion={0.02}
          // Nearly-black dark tinted glass — the key to the dark glassmorphic look
          color="#0d0f13"
          attenuationColor="#383e4e"
          attenuationDistance={1.5}
        />
      </mesh>

      {/* ── Wire edge overlay — thin, subtly glowing ── */}
      <lineSegments ref={edgesRef} geometry={edgesGeo}>
        <lineBasicMaterial
          color="#b6bac5"
          opacity={0.3}
          transparent
          linewidth={1}
        />
      </lineSegments>
    </group>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Section wrapper — scroll-triggered entrance, used as Viewport 2 in /aria
// ─────────────────────────────────────────────────────────────────────────────
export default function ARIAModelSection() {
  const sectionRef = useRef<HTMLDivElement>(null);
  const isInView = useInView(sectionRef, { once: false, amount: 0.35 });
  const [crystalVisible, setCrystalVisible] = useState(false);

  useEffect(() => {
    setCrystalVisible(isInView);
  }, [isInView]);

  return (
    <div ref={sectionRef} className="relative w-full h-full bg-background overflow-hidden">

      {/* ── Ambient radial glow ── */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-0">
        <motion.div
          initial={{ opacity: 0, scale: 0.4 }}
          animate={isInView ? { opacity: 1, scale: 1 } : { opacity: 0, scale: 0.4 }}
          transition={{ duration: 1.8, ease: "easeOut" }}
          className="w-[600px] h-[600px] rounded-full"
          style={{
            background:
              "radial-gradient(circle, rgba(56,62,78,0.45) 0%, rgba(13,15,19,0) 65%)",
            filter: "blur(50px)",
          }}
        />
      </div>

      {/* ── 3D Canvas ── */}
      <motion.div
        initial={{ opacity: 0, y: 80, filter: "blur(24px)" }}
        animate={
          isInView
            ? { opacity: 1, y: 0, filter: "blur(0px)" }
            : { opacity: 0, y: 80, filter: "blur(24px)" }
        }
        transition={{ duration: 1.6, ease: [0.16, 1, 0.3, 1] }}
        className="absolute inset-0 z-10 bg-background"
      >
        <Canvas
          shadows
          gl={{ antialias: true, alpha: true }}
          camera={{ position: [0, 0, 7], fov: 38 }}
        >
          {/* Very dim ambient — dark scene */}
          <ambientLight intensity={0.15} />
          {/* Main key light — cold white from upper-right (matching crystal orientation) */}
          <directionalLight
            position={[5, 5, 3]}
            intensity={1.0}
            color="#c8ccd6"
          />
          {/* Rim light — warm-indigo from lower-left to catch the waist edges */}
          <directionalLight
            position={[-5, -4, -2]}
            intensity={0.6}
            color="#383e4e"
          />
          {/* Subtle fill from the front */}
          <pointLight position={[0, 0, 6]} intensity={0.3} color="#b6bac5" />

          <ARIACrystal visible={crystalVisible} />

          <Environment preset="night" />
        </Canvas>
      </motion.div>

      {/* ── Label overlay — bottom ── */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 20 }}
        transition={{ duration: 1, delay: 0.7 }}
        className="absolute bottom-10 left-0 right-0 z-20 flex flex-col items-center gap-2 text-center pointer-events-none"
      >
        <p className="font-sans text-[9px] tracking-[0.45em] uppercase text-lavender-gray/35">
          ARIA // Intelligence Core
        </p>
        <h2 className="font-serif text-3xl md:text-4xl text-white/90 tracking-tight">
          The <span className="italic text-lavender-gray">Prism</span> of Thought
        </h2>
        <p className="font-sans text-xs text-lavender-gray/45 max-w-xs leading-relaxed font-light mt-1">
          Refracting every question through dual perspectives — Advocate&nbsp;&&nbsp;Skeptic — until truth crystallises.
        </p>
      </motion.div>
    </div>
  );
}
