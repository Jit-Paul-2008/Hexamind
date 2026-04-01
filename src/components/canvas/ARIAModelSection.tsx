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
// ARIA Octahedron — vertical orientation, Y-axis rotation ONLY.
// No X or Z rotation so the two apices always point straight up and down.
// ─────────────────────────────────────────────────────────────────────────────
function ARIAOctahedron() {
  const outerRef = useRef<THREE.Mesh>(null);
  const innerRef = useRef<THREE.Mesh>(null);

  useFrame((state, delta) => {
    if (outerRef.current) {
      outerRef.current.rotation.y += delta * 0.32;           // spin around vertical axis only
      outerRef.current.position.y = Math.sin(state.clock.elapsedTime * 0.7) * 0.14; // float
    }
    if (innerRef.current) {
      innerRef.current.rotation.y -= delta * 0.50;           // counter-spin inner cage
    }
  });

  return (
    <group>
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
// Agent card — each one enters with a fade+rise and then STAYS permanently.
// useTransform clamps at its last output value by default.
// No Y spring here — avoids flicker and "appear/disappear" behaviour.
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
  // Clamps at 1 once past range[1] — card is permanently visible after appearing
  const opacity = useTransform(scrollYProgress, [range[0], range[1]], [0, 1]);
  // Slide in from below with NO spring so it doesn't re-animate on re-entry
  const y       = useTransform(scrollYProgress, [range[0], range[1]], [32, 0]);

  return (
    <motion.div
      className="flex items-start gap-4 group cursor-pointer pointer-events-auto select-none"
      style={{ opacity, y }}
      whileHover={{ x: 5 }}
      transition={{ duration: 0.15 }}
      // TODO(backend): onClick → POST /api/session/start { agentId: agent.id }
    >
      {/* ── Timeline column: dot + connector segment to next agent ── */}
      <div
        className="relative flex flex-col items-center flex-shrink-0"
        style={{ width: 14, paddingTop: 5 }}
      >
        {/* The coloured dot sits exactly on the continuous vertical line */}
        <div
          className="w-2.5 h-2.5 rounded-full flex-shrink-0 z-10 relative"
          style={{
            background: agent.accentColor,
            boxShadow: `0 0 8px ${agent.accentColor}, 0 0 16px ${agent.accentColor}66`,
          }}
        />
        {/* Per-segment connector — provides gradients between agents */}
        {!isLast && (
          <div
            style={{
              width: 1,
              height: 62,
              marginTop: 3,
              background: `linear-gradient(to bottom, ${agent.accentColor}70, transparent)`,
              flexShrink: 0,
            }}
          />
        )}
      </div>

      {/* ── 3D polygon shape ── */}
      <div
        className="flex-shrink-0 rounded-xl overflow-hidden"
        style={{
          width: 66,
          height: 66,
          background: `radial-gradient(circle, ${agent.glowColor} 0%, rgba(0,0,0,0) 70%)`,
          border: `1px solid ${agent.accentColor}28`,
          boxShadow: `0 0 18px ${agent.glowColor}`,
        }}
      >
        <AgentShapeCanvas shape={agent.shape} accentColor={agent.accentColor} />
      </div>

      {/* ── Text content ── */}
      <div className="flex flex-col gap-1 pt-1">
        <span
          className="font-sans text-[8px] tracking-[0.36em] uppercase leading-none"
          style={{ color: agent.accentColor }}
        >
          {String(agent.processingOrder).padStart(2, "0")} · {agent.role}
        </span>
        <h3
          className="font-serif text-xl leading-snug text-white tracking-tight
                     group-hover:text-lavender-gray/80 transition-colors duration-300"
          style={{ textShadow: `0 0 24px ${agent.accentColor}44` }}
        >
          {agent.codename}
        </h3>
        <p className="font-sans text-xs text-lavender-gray/65 leading-relaxed font-light max-w-[240px]">
          {agent.purpose}
        </p>
      </div>
    </motion.div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
//  Main component — 500vh scroll, sticky 100vh inner viewport.
//
//  SCROLL TIMELINE (progress → screen scrolled at ~1000px viewport height):
//
//  0.00 – 0.07   Hero static                         (0 – 28px per vh unit)
//  0.05 – 0.18   ① Background darkens, grid vanishes
//  0.00 – 0.18   ② ARIA wordmark fades to 0           ← GONE by 18% scroll
//  0.00 – 0.14   ③ Scroll-hint fades to 0
//  0.14 – 0.42   ④ Prism drifts DOWN +45px, zooms to 0.68
//  0.18 – 0.22   ⑤ Agent container fades in (fully visible at 22%)
//  0.22 – 0.36   ⑥ Agent 1 (Advocate) enters, STAYS
//  0.40 – 0.54   ⑦ Agent 2 (Skeptic)  enters, STAYS
//  0.58 – 0.72   ⑧ Agent 3 (Synthesiser) enters, STAYS
//  0.76 – 0.90   ⑨ Agent 4 (Oracle) enters, STAYS
//  0.90 – 1.00   Rest state — all 4 visible, prism centred at bottom
// ─────────────────────────────────────────────────────────────────────────────
export default function ARIAModelSection() {
  const sectionRef = useRef<HTMLDivElement>(null);

  const { scrollYProgress } = useScroll({
    target: sectionRef,
    offset: ["start start", "end end"],
  });

  // ── Background ──────────────────────────────────────────────────────────────
  const gridOpacity   = useTransform(scrollYProgress, [0,    0.06, 0.16], [1,    0.4, 0]);
  const blackOpacity  = useTransform(scrollYProgress, [0.05, 0.18        ], [0,    0.95]);
  const glowIntensity = useTransform(scrollYProgress, [0.08, 0.45        ], [0.28, 0.92]);

  // ── ARIA wordmark — fades COMPLETELY by 18% scroll (well before first agent) ──
  const wordmarkOpacity = useTransform(scrollYProgress, [0, 0.07, 0.18], [1, 0.75, 0]);
  const wordmarkScale   = useTransform(scrollYProgress, [0, 0.18       ], [1, 0.88  ]);

  // ── Scroll-hint at bottom — gone earlier than wordmark ──────────────────────
  const hintOpacity = useTransform(scrollYProgress, [0, 0.05, 0.13], [1, 0.5, 0]);

  // ── Prism: moves DOWN and zooms out as agents enter.
  //    Positive y = downward shift. Stays horizontally centred via flex. ──────
  const prismYRaw     = useTransform(scrollYProgress, [0.14, 0.42], [0,   45]);
  const prismScaleRaw = useTransform(scrollYProgress, [0,    0.10, 0.42], [1, 1.04, 0.68]);
  const prismY        = useSpring(prismYRaw,     { damping: 32, stiffness: 90 });
  const prismScale    = useSpring(prismScaleRaw, { damping: 32, stiffness: 90 });

  // ── Agent container — fades in BEFORE any individual card starts appearing ──
  const agentContainerOpacity = useTransform(scrollYProgress, [0.18, 0.23], [0, 1]);

  // Per-agent ranges — 0.14 wide each, well separated, generous dwell time.
  // Each range ends at a higher value than agents start, and since useTransform
  // clamps, once a card hits opacity:1 it NEVER goes back to 0.
  const agentRanges: [number, number][] = [
    [0.22, 0.36],   // 01 Advocate
    [0.40, 0.54],   // 02 Skeptic
    [0.58, 0.72],   // 03 Synthesiser
    [0.76, 0.90],   // 04 Oracle
  ];

  return (
    <div ref={sectionRef} className="relative" style={{ height: "500vh" }}>

      {/* ─── Sticky 100vh viewport, all layers stack via absolute + z-index ─── */}
      <div className="sticky top-0 w-full h-screen overflow-hidden">

        {/* Z0 — base dark background */}
        <div className="absolute inset-0 bg-background z-0" />

        {/* Z1 — dot grid, fades early */}
        <motion.div
          className="absolute inset-0 z-[1]"
          style={{
            opacity: gridOpacity,
            backgroundImage: `radial-gradient(circle at 1px 1px, rgba(182,186,197,0.04) 1px, transparent 0)`,
            backgroundSize: "40px 40px",
          }}
        />

        {/* Z2 — deep black overlay, fades in during transition */}
        <motion.div
          className="absolute inset-0 z-[2]"
          style={{
            opacity: blackOpacity,
            background: "radial-gradient(ellipse at 50% 45%, #05050a 0%, #000000 100%)",
          }}
        />

        {/* Z3 — indigo glow, strengthens as prism becomes the focus */}
        <div className="absolute inset-0 z-[3] flex items-center justify-center pointer-events-none">
          <motion.div
            className="rounded-full"
            style={{
              width: "65vw",
              height: "65vw",
              maxWidth: 840,
              maxHeight: 840,
              opacity: glowIntensity,
              background:
                "radial-gradient(circle, rgba(99,102,241,0.16) 0%, rgba(79,70,229,0.06) 45%, transparent 70%)",
              filter: "blur(80px)",
            }}
          />
        </div>

        {/* ─────────────────────────────────────────────────────────────────────
            Z10 — ARIA wordmark
            - Entire wordmark is BEHIND the prism (z-10 < z-20)
            - Fades to opacity:0 by scrollYProgress=0.18 — completely gone
              before the first agent card ever appears at 0.22
            - No horizontal movement — stays centred until gone
        ───────────────────────────────────────────────────────────────────── */}
        <motion.div
          className="absolute inset-0 z-10 flex items-center justify-center pointer-events-none select-none"
          style={{ opacity: wordmarkOpacity, scale: wordmarkScale }}
        >
          {/* TODO(backend): aria-live="polite" for WebSocket ARIA system status */}
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

        {/* ─────────────────────────────────────────────────────────────────────
            Z20 — Prism canvas
            - Sits above wordmark
            - ONLY moves vertically (y-transform on flex-centered container)
            - Positive y → moves DOWN from centre  (no horizontal drift possible)
        ───────────────────────────────────────────────────────────────────── */}
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

        {/* ─────────────────────────────────────────────────────────────────────
            Z25 — scroll-hint label
            Completely hidden by 0.13 progress — NO overlap with agent layer
        ───────────────────────────────────────────────────────────────────── */}
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

        {/* ─────────────────────────────────────────────────────────────────────
            Z30 — Agent pipeline
            - Container appears AFTER wordmark is already 0
            - Single continuous gradient line runs through ALL 4 dot positions,
              aligned to x=7px (the centre of the 14px-wide dot column, 0px left-padding)
            - Cards are ordered 1→4 top-to-bottom, container anchored to bottom-right
            - backdrop-blur on each card makes text crisp over the dark background
        ───────────────────────────────────────────────────────────────────── */}
        <motion.div
          className="absolute bottom-8 right-8 z-30 pointer-events-none"
          style={{ opacity: agentContainerOpacity }}
        >
          {/* Container: no horizontal padding so dot alignment maths are simple */}
          <div className="relative w-80">
            {/*
              The single continuous pipeline line.
              left: 7px = centre of dot column (dot is w-2.5=10px, column is 14px → offset 2px + radius 5px = 7px)
              top: 5px = paddingTop of first dot column
              bottom: 0
            */}
            <div
              className="absolute pointer-events-none"
              style={{
                left: 7,
                top: 5,
                bottom: 0,
                width: 1,
                background:
                  "linear-gradient(to bottom, #818cf8, #f87171 33%, #34d399 66%, #fbbf24)",
                opacity: 0.5,
              }}
            />

            {/* Agent cards — gap-0 so per-card connector lines form an unbroken chain */}
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
