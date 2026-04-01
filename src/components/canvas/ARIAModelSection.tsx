"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import { Environment, Float, MeshTransmissionMaterial, Text } from "@react-three/drei";
import { useRef, useEffect, useState } from "react";
import * as THREE from "three";
import { motion, useInView } from "framer-motion";

// The 3D prism — only animates in once visible
function ARIAPrism({ visible }: { visible: boolean }) {
  const groupRef = useRef<THREE.Group>(null);
  const outerRef = useRef<THREE.Mesh>(null);
  const innerRef = useRef<THREE.Mesh>(null);

  useFrame((state, delta) => {
    if (!visible) return;
    if (outerRef.current) {
      outerRef.current.rotation.x += delta * 0.15;
      outerRef.current.rotation.y += delta * 0.25;
    }
    if (innerRef.current) {
      innerRef.current.rotation.x -= delta * 0.1;
      innerRef.current.rotation.y -= delta * 0.2;
    }
    // Hover gently using time
    if (groupRef.current) {
      groupRef.current.position.y = Math.sin(state.clock.elapsedTime * 0.6) * 0.15;
    }
  });

  if (!visible) return null;

  return (
    <group ref={groupRef}>
      {/* Outer glass octahedron */}
      <mesh ref={outerRef} castShadow receiveShadow>
        <octahedronGeometry args={[2.2, 0]} />
        <MeshTransmissionMaterial
          backside
          backsideThickness={2}
          thickness={1}
          roughness={0.03}
          transmission={1}
          ior={1.35}
          chromaticAberration={0.08}
          anisotropy={0.2}
          color="#c8ccd6"
          distortionScale={0.2}
          temporalDistortion={0.05}
        />
      </mesh>
      {/* Inner wireframe structure */}
      <mesh ref={innerRef} scale={0.65}>
        <icosahedronGeometry args={[2, 1]} />
        <meshStandardMaterial color="#b6bac5" wireframe opacity={0.4} transparent />
      </mesh>
    </group>
  );
}

export default function ARIAModelSection() {
  const sectionRef = useRef<HTMLDivElement>(null);
  const isInView = useInView(sectionRef, { once: false, amount: 0.4 });
  const [prismVisible, setPrismVisible] = useState(false);

  useEffect(() => {
    if (isInView) setPrismVisible(true);
    else setPrismVisible(false);
  }, [isInView]);

  return (
    <div ref={sectionRef} className="relative w-full h-full bg-background overflow-hidden">
      {/* Ambient glow at the center */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-0">
        <motion.div
          initial={{ opacity: 0, scale: 0.5 }}
          animate={isInView ? { opacity: 1, scale: 1 } : { opacity: 0, scale: 0.5 }}
          transition={{ duration: 1.5, ease: "easeOut" }}
          className="w-[500px] h-[500px] rounded-full"
          style={{
            background: "radial-gradient(circle, rgba(56,62,78,0.5) 0%, rgba(17,18,22,0) 70%)",
            filter: "blur(40px)",
          }}
        />
      </div>

      {/* 3D Canvas — centered prism */}
      <motion.div
        initial={{ opacity: 0, y: 60, filter: "blur(20px)" }}
        animate={isInView ? { opacity: 1, y: 0, filter: "blur(0px)" } : { opacity: 0, y: 60, filter: "blur(20px)" }}
        transition={{ duration: 1.4, ease: [0.16, 1, 0.3, 1] }}
        className="absolute inset-0 z-10 bg-background"
      >
        <Canvas shadows camera={{ position: [0, 0, 7], fov: 40 }}>
          <ambientLight intensity={0.3} />
          <directionalLight position={[8, 8, 5]} intensity={1.2} castShadow color="#ffffff" />
          <directionalLight position={[-8, -8, -5]} intensity={1.5} color="#383e4e" />
          <Float speed={1} rotationIntensity={0} floatIntensity={0}>
            <ARIAPrism visible={prismVisible} />
          </Float>
          <Environment preset="night" />
        </Canvas>
      </motion.div>

      {/* Text overlay — bottom of section */}
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={isInView ? { opacity: 1, y: 0 } : { opacity: 0, y: 30 }}
        transition={{ duration: 1, delay: 0.6 }}
        className="absolute bottom-12 left-0 right-0 z-20 flex flex-col items-center gap-3 text-center pointer-events-none"
      >
        <p className="font-sans text-[10px] tracking-[0.4em] uppercase text-lavender-gray/40">
          ARIA // Intelligence Core
        </p>
        <h2 className="font-serif text-4xl md:text-5xl text-white tracking-tight">
          The <span className="italic text-lavender-gray">Prism</span> of Thought
        </h2>
        <p className="font-sans text-sm text-lavender-gray/50 max-w-xs leading-relaxed font-light">
          Refracting every question through dual perspectives — Advocate and Skeptic — until truth crystallises.
        </p>
      </motion.div>
    </div>
  );
}
