"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import { Environment, MeshTransmissionMaterial } from "@react-three/drei";
import { useRef } from "react";
import * as THREE from "three";
import {
  motion,
  useScroll,
  useTransform,
  useSpring,
  type MotionValue,
} from "framer-motion";
import dynamic from "next/dynamic";
import { AGENTS, type Agent } from "@/lib/agents";

// Dynamically import the agent shape canvas to keep it CSR-only
const AgentShapeCanvas = dynamic(() => import("./AgentShape"), { ssr: false });

// ─────────────────────────────────────────────────────────────────────────────
// ARIA Octahedron — symmetric glass prism with inner wireframe
// ─────────────────────────────────────────────────────────────────────────────
function ARIAOctahedron() {
  const outerRef = useRef<THREE.Mesh>(null);
  const innerRef = useRef<THREE.Mesh>(null);

  useFrame((state, delta) => {
    if (outerRef.current) {
      outerRef.current.rotation.y += delta * 0.28;
      outerRef.current.rotation.x += delta * 0.1;
      outerRef.current.position.y = Math.sin(state.clock.elapsedTime * 0.75) * 0.18;
    }
    if (innerRef.current) {
      innerRef.current.rotation.y -= delta * 0.42;
      innerRef.current.rotation.z += delta * 0.14;
    }
  });

  return (
    <group>
      {/* Glass outer shell */}
      <mesh ref={outerRef} castShadow>
        <octahedronGeometry args={[2.2, 0]} />
        <MeshTransmissionMaterial
          backside
          backsideThickness={0.6}
          thickness={0.8}
          roughness={0.04}
          transmission={0.96}
          ior={1.6}
          chromaticAberration={0.09}
          anisotropy={0.22}
          distortionScale={0.05}
          temporalDistortion={0.03}
          color="#090b10"
          attenuationColor="#4f46e5"
          attenuationDistance={2.0}
        />
      </mesh>
      {/* Counter-rotating inner wireframe for depth */}
      <mesh ref={innerRef} scale={0.54}>
        <icosahedronGeometry args={[2.2, 1]} />
        <meshStandardMaterial
          color="#818cf8"
          wireframe
          transparent
          opacity={0.18}
          emissive="#818cf8"
          emissiveIntensity={0.5}
        />
      </mesh>
    </group>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Animated Agent Card — each one has its own scroll-triggered entrance
// ─────────────────────────────────────────────────────────────────────────────
function AnimatedAgentCard({
  agent,
  scrollYProgress,
  range,
  isLast,
}: {
  agent: Agent;
  scrollYProgress: MotionValue<number>;
  range: [number, number];
  isLast: boolean;
}) {
  const opacity = useTransform(scrollYProgress, [range[0], range[1]], [0, 1]);
  const y = useTransform(scrollYProgress, [range[0], range[1]], [48, 0]);
  const ySpring = useSpring(y, { damping: 32, stiffness: 110 });

  return (
    <motion.div
      className="flex items-center gap-5 group cursor-pointer pointer-events-auto select-none"
      style={{ opacity, y: ySpring }}
      whileHover={{ x: 6 }}
      transition={{ duration: 0.18 }}
      // TODO(backend): onClick → POST /api/session/start { agentId: agent.id }
    >
      {/* Order pip + connector line */}
      <div className="flex flex-col items-center flex-shrink-0 self-stretch">
        <span
          className="font-sans text-[9px] font-semibold tabular-nums leading-none mb-1"
          style={{ color: agent.accentColor }}
        >
          {String(agent.processingOrder).padStart(2, "0")}
        </span>
        {!isLast && (
          <div
            className="flex-1 w-px mt-1"
            style={{
              background: `linear-gradient(to bottom, ${agent.accentColor}40, transparent)`,
            }}
          />
        )}
      </div>

      {/* 3D polygon */}
      <div
        className="flex-shrink-0 rounded-xl overflow-hidden"
        style={{
          width: 72,
          height: 72,
          background: `radial-gradient(circle, ${agent.glowColor} 0%, rgba(0,0,0,0) 70%)`,
          border: `1px solid ${agent.accentColor}28`,
          boxShadow: `0 0 22px ${agent.glowColor}`,
        }}
      >
        <AgentShapeCanvas shape={agent.shape} accentColor={agent.accentColor} />
      </div>

      {/* Text block */}
      <div className="flex flex-col gap-0.5">
        <span
          className="font-sans text-[8px] tracking-[0.38em] uppercase leading-none"
          style={{ color: agent.accentColor }}
        >
          {agent.role}
        </span>
        <h3
          className="font-serif text-lg text-white tracking-tight group-hover:text-lavender-gray transition-colors duration-300"
          style={{ textShadow: `0 0 30px ${agent.accentColor}33` }}
        >
          {agent.codename}
        </h3>
        <p className="font-sans text-[11px] text-lavender-gray/55 leading-relaxed font-light max-w-[260px]">
          {agent.purpose}
        </p>
      </div>
    </motion.div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Main Section — 400vh scroll container, sticky viewport inside
// ─────────────────────────────────────────────────────────────────────────────
export default function ARIAModelSection() {
  const sectionRef = useRef<HTMLDivElement>(null);

  const { scrollYProgress } = useScroll({
    target: sectionRef,
    offset: ["start start", "end end"],
  });

  // ── Background transitions
  const gridOpacity    = useTransform(scrollYProgress, [0, 0.18, 0.34], [1, 0.4, 0]);
  const blackOpacity   = useTransform(scrollYProgress, [0.08, 0.36], [0, 0.93]);
  const glowIntensity  = useTransform(scrollYProgress, [0.1, 0.5], [0.32, 0.85]);

  // ── ARIA wordmark (behind prism, fades as agents emerge)
  const wordmarkOpacity = useTransform(scrollYProgress, [0, 0.14, 0.28], [1, 0.9, 0]);
  const wordmarkScale   = useTransform(scrollYProgress, [0, 0.28], [1, 0.93]);
  const wordmarkY       = useTransform(scrollYProgress, [0, 0.28], [0, -12]);

  // ── Prism: centres → lifts to upper third, slightly smaller
  const prismYRaw    = useTransform(scrollYProgress, [0.25, 0.54], [0, -185]);
  const prismScaleRaw = useTransform(scrollYProgress, [0, 0.12, 0.54], [1, 1.05, 0.68]);
  const prismY       = useSpring(prismYRaw,    { damping: 28, stiffness: 88 });
  const prismScale   = useSpring(prismScaleRaw, { damping: 28, stiffness: 88 });

  // ── Bottom hint fades
  const hintOpacity = useTransform(scrollYProgress, [0, 0.11, 0.22], [1, 0.5, 0]);

  // ── Agents container: overall fade-in, then individual starters
  const agentContainerOpacity = useTransform(scrollYProgress, [0.26, 0.36], [0, 1]);

  const agentRanges: [number, number][] = [
    [0.30, 0.40],
    [0.42, 0.52],
    [0.55, 0.64],
    [0.67, 0.76],
  ];

  return (
    // 400vh tall — gives 300vh of scroll distance on a 100vh viewport
    <div ref={sectionRef} className="relative" style={{ height: "400vh" }}>

      {/* ── Sticky viewport ─────────────────────────────────────── */}
      <div className="sticky top-0 w-full h-screen overflow-hidden">

        {/* Z0 — dark base */}
        <div className="absolute inset-0 bg-background z-0" />

        {/* Z1 — dot grid (fades out) */}
        <motion.div
          className="absolute inset-0 z-[1]"
          style={{
            opacity: gridOpacity,
            backgroundImage: `radial-gradient(circle at 1px 1px, rgba(182,186,197,0.04) 1px, transparent 0)`,
            backgroundSize: "40px 40px",
          }}
        />

        {/* Z2 — deep-black overlay (fades in) */}
        <motion.div
          className="absolute inset-0 z-[2]"
          style={{
            opacity: blackOpacity,
            background: "radial-gradient(ellipse at 50% 40%, #06060c 0%, #000000 100%)",
          }}
        />

        {/* Z3 — indigo ambient glow (intensifies) */}
        <div className="absolute inset-0 z-[3] flex items-center justify-center pointer-events-none">
          <motion.div
            className="rounded-full"
            style={{
              width: "70vw",
              height: "70vw",
              maxWidth: 860,
              maxHeight: 860,
              opacity: glowIntensity,
              background:
                "radial-gradient(circle, rgba(99,102,241,0.16) 0%, rgba(79,70,229,0.06) 45%, transparent 70%)",
              filter: "blur(80px)",
            }}
          />
        </div>

        {/* Z10 — ARIA wordmark — ENTIRE wordmark behind the prism canvas */}
        <motion.div
          className="absolute inset-0 z-10 flex items-center justify-center pointer-events-none select-none"
          style={{ opacity: wordmarkOpacity, scale: wordmarkScale, y: wordmarkY }}
        >
          {/* TODO(backend): aria-live="polite" for real-time ARIA status from WebSocket */}
          <span
            className="font-serif font-bold leading-none"
            aria-label="ARIA Intelligence System"
            style={{
              fontSize: "clamp(7rem, 20vw, 20rem)",
              letterSpacing: "-0.04em",
              background:
                "linear-gradient(135deg, #b6bac5 0%, #818cf8 18%, #ffffff 32%, #a5b4fc 48%, #60a5fa 62%, #c7d2fe 78%, #b6bac5 100%)",
              backgroundSize: "300% 300%",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              backgroundClip: "text",
              animation: "aria-refraction 6s ease-in-out infinite",
            }}
          >
            ARIA
          </span>
        </motion.div>

        {/* Z20 — Prism canvas — ABOVE wordmark, floats without covering much of it */}
        <motion.div
          className="absolute inset-0 z-20 flex items-center justify-center pointer-events-none"
          style={{ y: prismY, scale: prismScale }}
        >
          <div style={{ width: "min(46vw, 46vh)", height: "min(46vw, 46vh)" }}>
            <Canvas
              shadows
              gl={{ antialias: true, alpha: true }}
              camera={{ position: [0, 0, 8], fov: 36 }}
            >
              <ambientLight intensity={0.1} />
              <directionalLight position={[5, 6, 3]}  intensity={1.3} color="#c8ccd6" />
              <directionalLight position={[-5, -4, -3]} intensity={0.9} color="#4f46e5" />
              <pointLight position={[0, 0, 7]} intensity={0.5} color="#a5b4fc" />
              <spotLight
                position={[0, 10, 5]}
                intensity={0.8}
                angle={0.3}
                penumbra={1}
                color="#ffffff"
              />
              <ARIAOctahedron />
              <Environment preset="night" />
            </Canvas>
          </div>
        </motion.div>

        {/* Z25 — "Intelligence Core" subtitle + scroll hint — fades out */}
        <motion.div
          className="absolute bottom-10 left-0 right-0 z-[25] flex flex-col items-center gap-2 pointer-events-none text-center"
          style={{ opacity: hintOpacity }}
        >
          <p className="font-sans text-[9px] tracking-[0.45em] uppercase text-lavender-gray/35">
            ARIA // Intelligence Core
          </p>
          <p className="font-sans text-[10px] text-lavender-gray/20 tracking-[0.2em]">
            Scroll to reveal the pipeline
          </p>
          <motion.div
            animate={{ y: [0, 5, 0] }}
            transition={{ duration: 1.8, repeat: Infinity }}
            className="mt-3"
          >
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
              <path
                d="M6 1v10M6 11L2 7M6 11L10 7"
                stroke="rgba(182,186,197,0.28)"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </motion.div>
        </motion.div>

        {/* Z30 — Agent cards — appear sequentially below the rising prism */}
        <motion.div
          className="absolute inset-0 z-30 flex flex-col items-center justify-end pb-10 pointer-events-none"
          style={{ opacity: agentContainerOpacity }}
        >
          <div className="flex flex-col gap-6 w-full max-w-xl px-8">
            {AGENTS.map((agent, i) => (
              <AnimatedAgentCard
                key={agent.id}
                agent={agent}
                scrollYProgress={scrollYProgress}
                range={agentRanges[i]}
                isLast={i === AGENTS.length - 1}
              />
            ))}
          </div>
        </motion.div>

      </div>
    </div>
  );
}
