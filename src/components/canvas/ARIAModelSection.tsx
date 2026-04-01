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

const AgentShapeCanvas = dynamic(() => import("./AgentShape"), { ssr: false });

// ─────────────────────────────────────────────────────────────────────────────
// ARIA Octahedron
// FIX: Y-axis ONLY rotation — vertical apex stays pointing up/down at all times.
// No X or Z rotation so the prism never tilts sideways.
// ─────────────────────────────────────────────────────────────────────────────
function ARIAOctahedron() {
  const outerRef = useRef<THREE.Mesh>(null);
  const innerRef = useRef<THREE.Mesh>(null);

  useFrame((state, delta) => {
    if (outerRef.current) {
      // ONLY Y rotation — keeps the vertical orientation locked
      outerRef.current.rotation.y += delta * 0.32;
      // Gentle float stays purely vertical (Y position only)
      outerRef.current.position.y = Math.sin(state.clock.elapsedTime * 0.7) * 0.14;
    }
    if (innerRef.current) {
      // Counter-rotate inner wireframe on Y only for depth — no tilt
      innerRef.current.rotation.y -= delta * 0.48;
    }
  });

  return (
    <group>
      {/* Outer glass shell */}
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
      {/* Counter-rotating inner wireframe — Y only */}
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
// Single agent card — scroll-animated entrance, permanently stays visible
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
  // useTransform clamps at boundaries by default — once opacity hits 1 it STAYS at 1
  const opacity = useTransform(scrollYProgress, [range[0], range[1]], [0, 1]);
  // Y: slides up into position then stays. Spring gives smooth entry.
  const rawY = useTransform(scrollYProgress, [range[0], range[1]], [36, 0]);
  const y    = useSpring(rawY, { damping: 38, stiffness: 130 });

  return (
    <motion.div
      className="flex items-start gap-4 group cursor-pointer pointer-events-auto select-none"
      style={{ opacity, y }}
      whileHover={{ x: 4 }}
      transition={{ duration: 0.15 }}
      // TODO(backend): onClick → POST /api/session/start { agentId: agent.id, processingOrder: agent.processingOrder }
    >
      {/* ── Timeline dot (sits on the vertical connector line) */}
      <div className="relative flex flex-col items-center flex-shrink-0" style={{ width: 14, paddingTop: 6 }}>
        <div
          className="w-2.5 h-2.5 rounded-full flex-shrink-0"
          style={{
            background: agent.accentColor,
            boxShadow: `0 0 8px ${agent.accentColor}, 0 0 18px ${agent.accentColor}55`,
          }}
        />
        {/* Segment of vertical line below this dot — gradient toward next color */}
        {!isLast && (
          <div
            style={{
              width: 1,
              height: 64,
              marginTop: 4,
              background: `linear-gradient(to bottom, ${agent.accentColor}60, transparent)`,
            }}
          />
        )}
      </div>

      {/* ── 3D polygon shape */}
      <div
        className="flex-shrink-0 rounded-xl overflow-hidden"
        style={{
          width: 64,
          height: 64,
          background: `radial-gradient(circle, ${agent.glowColor} 0%, rgba(0,0,0,0) 70%)`,
          border: `1px solid ${agent.accentColor}28`,
          boxShadow: `0 0 16px ${agent.glowColor}`,
        }}
      >
        <AgentShapeCanvas shape={agent.shape} accentColor={agent.accentColor} />
      </div>

      {/* ── Text */}
      <div className="flex flex-col gap-0.5 pt-1">
        <span
          className="font-sans text-[8px] tracking-[0.36em] uppercase leading-none mb-0.5"
          style={{ color: agent.accentColor }}
        >
          {String(agent.processingOrder).padStart(2, "0")} · {agent.role}
        </span>
        <h3
          className="font-serif text-[1.1rem] leading-snug text-white tracking-tight 
                     group-hover:text-lavender-gray transition-colors duration-300"
          style={{ textShadow: `0 0 24px ${agent.accentColor}33` }}
        >
          {agent.codename}
        </h3>
        <p className="font-sans text-[10.5px] text-lavender-gray/55 leading-relaxed font-light max-w-[230px]">
          {agent.purpose}
        </p>
      </div>
    </motion.div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Main Section — 500vh tall scroll container, sticky 100vh viewport inside.
// Layout contract (scroll progress vs. events):
//
//  0.00–0.12  Static hero — ARIA wordmark + prism centred, dot-grid bg
//  0.08–0.35  Background fades to near-black, grid disappears
//  0.00–0.30  ARIA wordmark fully fades to 0 (complete before agents)
//  0.28–0.55  Prism moves DOWN slightly (+45px), scales to 0.68 (zoom-out)
//  0.32–0.88  4 agents reveal sequentially — each has a wide 0.14 dwell window
//             and STAYS visible once reached (useTransform clamp)
//  0.88–1.00  Stable rest state — all agents visible, prism steady
// ─────────────────────────────────────────────────────────────────────────────
export default function ARIAModelSection() {
  const sectionRef = useRef<HTMLDivElement>(null);

  const { scrollYProgress } = useScroll({
    target: sectionRef,
    offset: ["start start", "end end"],
  });

  // ── Background
  const gridOpacity   = useTransform(scrollYProgress, [0, 0.18, 0.34], [1, 0.4, 0]);
  const blackOpacity  = useTransform(scrollYProgress, [0.08, 0.35], [0, 0.94]);
  const glowIntensity = useTransform(scrollYProgress, [0.10, 0.52], [0.30, 0.88]);

  // ── ARIA wordmark — fades to 0 COMPLETELY before agents ever appear
  const wordmarkOpacity = useTransform(scrollYProgress, [0, 0.16, 0.30], [1, 0.85, 0]);
  const wordmarkScale   = useTransform(scrollYProgress, [0, 0.30], [1, 0.91]);
  // Wordmark does NOT move — stays centred, only fades
  const wordmarkY       = useTransform(scrollYProgress, [0, 0.30], [0, 0]);

  // ── Prism: stays horizontally centred (absolute inset-0 + flex never drifts X).
  // FIX: moves DOWN slightly (+45px) — positive Y = downward in CSS.
  // FIX: no upward/-185 movement that pushed it off-screen.
  const prismYRaw     = useTransform(scrollYProgress, [0.28, 0.56], [0, 45]);
  const prismScaleRaw = useTransform(scrollYProgress, [0, 0.12, 0.56], [1, 1.04, 0.68]);
  const prismY        = useSpring(prismYRaw,     { damping: 32, stiffness: 92 });
  const prismScale    = useSpring(prismScaleRaw, { damping: 32, stiffness: 92 });

  // ── Scroll hint at bottom of hero state
  const hintOpacity = useTransform(scrollYProgress, [0, 0.10, 0.20], [1, 0.5, 0]);

  // ── Agent container — fades in once, stays
  const agentContainerOpacity = useTransform(scrollYProgress, [0.28, 0.38], [0, 1]);

  // Each agent: wide dwell window so it stays visible long enough with scroll.
  // Ranges are non-overlapping so each card appears in sequence.
  // Framer-motion clamps at the final value → once visible, always visible.
  const agentRanges: [number, number][] = [
    [0.32, 0.44],   // Advocate
    [0.47, 0.59],   // Skeptic
    [0.62, 0.74],   // Synthesiser
    [0.77, 0.89],   // Oracle
  ];

  return (
    // 500vh — gives 400vh of scroll travel (400/500 × viewport per step)
    <div ref={sectionRef} className="relative" style={{ height: "500vh" }}>

      {/* ── Sticky viewport — 100vh, all layers absolutely positioned inside */}
      <div className="sticky top-0 w-full h-screen overflow-hidden">

        {/* Z0 — darkest base */}
        <div className="absolute inset-0 bg-background z-0" />

        {/* Z1 — dot grid, fades to 0 early */}
        <motion.div
          className="absolute inset-0 z-[1]"
          style={{
            opacity: gridOpacity,
            backgroundImage: `radial-gradient(circle at 1px 1px, rgba(182,186,197,0.04) 1px, transparent 0)`,
            backgroundSize: "40px 40px",
          }}
        />

        {/* Z2 — deep black overlay, fades in */}
        <motion.div
          className="absolute inset-0 z-[2]"
          style={{
            opacity: blackOpacity,
            background: "radial-gradient(ellipse at 50% 45%, #05050a 0%, #000000 100%)",
          }}
        />

        {/* Z3 — indigo ambient glow, intensifies as prism becomes the hero */}
        <div className="absolute inset-0 z-[3] flex items-center justify-center pointer-events-none">
          <motion.div
            className="rounded-full"
            style={{
              width: "65vw",
              height: "65vw",
              maxWidth: 820,
              maxHeight: 820,
              opacity: glowIntensity,
              background:
                "radial-gradient(circle, rgba(99,102,241,0.16) 0%, rgba(79,70,229,0.06) 45%, transparent 70%)",
              filter: "blur(80px)",
            }}
          />
        </div>

        {/* ──────────────────────────────────────────────────────────────────
            Z10 — ARIA wordmark
            Entire text sits BELOW the prism canvas in z-order.
            Stays centred (no X/Y drift on its own wrapper).
            Fades to opacity:0 before agents appear — no overlap.
        ────────────────────────────────────────────────────────────────── */}
        <motion.div
          className="absolute inset-0 z-10 flex items-center justify-center pointer-events-none select-none"
          style={{ opacity: wordmarkOpacity, scale: wordmarkScale, y: wordmarkY }}
        >
          {/* TODO(backend): aria-live="polite" — display real-time ARIA system status from WebSocket */}
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

        {/* ──────────────────────────────────────────────────────────────────
            Z20 — Prism canvas
            Above wordmark. Uses `absolute inset-0 + flex items-center justify-center`
            so the prism ONLY moves vertically (y transform) — zero horizontal drift.
            Positive y = moves DOWN from its centred position.
        ────────────────────────────────────────────────────────────────── */}
        <motion.div
          className="absolute inset-0 z-20 flex items-center justify-center pointer-events-none"
          style={{ y: prismY, scale: prismScale }}
        >
          <div style={{ width: "min(44vw, 44vh)", height: "min(44vw, 44vh)" }}>
            <Canvas
              shadows
              gl={{ antialias: true, alpha: true }}
              camera={{ position: [0, 0, 8], fov: 36 }}
            >
              <ambientLight intensity={0.10} />
              <directionalLight position={[5, 7, 3]}    intensity={1.3} color="#c8ccd6" />
              <directionalLight position={[-5, -5, -3]} intensity={0.9} color="#4f46e5" />
              <pointLight       position={[0, 0, 7]}    intensity={0.5} color="#a5b4fc" />
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

        {/* Z25 — scroll hint, fades out early */}
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

        {/* ──────────────────────────────────────────────────────────────────
            Z30 — Agent pipeline
            Appears only AFTER wordmark is fully gone (opaque from 0.28+).
            Anchored to the bottom of the viewport.
            All 4 agents share one parent container with a SINGLE continuous
            gradient line running through all their dots — they look connected.
        ────────────────────────────────────────────────────────────────── */}
        <motion.div
          className="absolute bottom-6 left-0 right-0 z-30 flex justify-center pointer-events-none"
          style={{ opacity: agentContainerOpacity }}
        >
          <div className="relative w-full max-w-md px-6">

            {/* Single continuous pipeline line that runs through ALL 4 agent dots.
                Positioned absolutely behind the cards.
                left: 17px aligns with the centre of each 14px-wide dot column. */}
            <div
              className="absolute"
              style={{
                left: 17,
                top: 6,
                bottom: 6,
                width: 1,
                background:
                  "linear-gradient(to bottom, #818cf8 0%, #f87171 33%, #34d399 66%, #fbbf24 100%)",
                opacity: 0.42,
              }}
            />

            {/* Agent cards stacked with gap-0 so the per-card connector lines
                between dots form a seamless visual chain */}
            <div className="flex flex-col gap-0">
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
          </div>
        </motion.div>

      </div>
    </div>
  );
}
