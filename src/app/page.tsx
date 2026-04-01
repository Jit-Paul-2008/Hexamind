"use client";

import { motion, useMotionValue, useSpring } from "framer-motion";
import Image from "next/image";
import Link from "next/link";
import { useCallback } from "react";

export default function LandingPage() {
  // Mouse position for spotlight glow
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);
  const springX = useSpring(mouseX, { damping: 30, stiffness: 150 });
  const springY = useSpring(mouseY, { damping: 30, stiffness: 150 });

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      mouseX.set(e.clientX - 200);
      mouseY.set(e.clientY - 200);
    },
    [mouseX, mouseY]
  );

  return (
    <main
      className="relative min-h-screen w-full overflow-hidden bg-background cursor-default"
      onMouseMove={handleMouseMove}
    >
      {/* ── Background Image ── */}
      <div className="absolute inset-0 z-0">
        <Image
          src="/images/flow-bg.png"
          alt="Abstract Flow Background"
          fill
          priority
          className="object-cover opacity-60"
        />
        {/* Base vignette */}
        <div className="absolute inset-0 bg-gradient-to-b from-background/70 via-background/30 to-background/90" />
      </div>

      {/* ── Mouse-tracking spotlight blur ── */}
      <motion.div
        className="pointer-events-none absolute z-10 w-[400px] h-[400px] rounded-full"
        style={{
          x: springX,
          y: springY,
          background:
            "radial-gradient(circle, rgba(182,186,197,0.12) 0%, rgba(56,62,78,0.08) 50%, transparent 70%)",
          filter: "blur(60px)",
        }}
      />

      {/* ── Top-left: System label ── */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, delay: 0.2 }}
        className="absolute top-8 left-8 z-20 flex items-center gap-3"
      >
        <div className="w-2 h-2 rounded-full bg-lavender-gray animate-pulse" />
        <span className="font-sans text-xs tracking-[0.25em] uppercase text-lavender-gray/60">
          Hexamind // System v1.0
        </span>
      </motion.div>

      {/* ── Top-right: Status pill ── */}
      <motion.div
        initial={{ opacity: 0, x: 10 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.8, delay: 0.4 }}
        className="absolute top-8 right-8 z-20"
      >
        <div className="px-4 py-1.5 rounded-full bg-white/5 border border-white/10 backdrop-blur-md">
          <span className="font-sans text-xs tracking-widest uppercase text-lavender-gray/50">
            ARIA Offline
          </span>
        </div>
      </motion.div>

      {/* ── Center: Hero headline (NOT in a glass box) ── */}
      <div className="absolute inset-0 z-20 flex flex-col items-center justify-center text-center px-6">
        {/* Tagline above */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.9, delay: 0.5 }}
          className="font-sans text-xs tracking-[0.4em] uppercase text-lavender-gray/50 mb-6"
        >
          Dual-Agent Cognitive Intelligence
        </motion.p>

        {/* Main title – split into two independent lines, different sizes */}
        <motion.h1
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1, delay: 0.7, ease: [0.16, 1, 0.3, 1] }}
          className="font-serif text-[clamp(3.5rem,10vw,9rem)] leading-[0.9] text-white tracking-tighter"
        >
          Think
        </motion.h1>
        <motion.h1
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1, delay: 0.85, ease: [0.16, 1, 0.3, 1] }}
          className="font-serif italic text-[clamp(3rem,9vw,8rem)] leading-[0.9] text-lavender-gray tracking-tighter mb-10"
        >
          Beyond Limits.
        </motion.h1>

        {/* Sub-description – smaller, lighter, separate from title */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1, delay: 1.1 }}
          className="font-sans font-light text-base md:text-lg text-lavender-gray/60 max-w-md leading-relaxed mb-12"
        >
          Meet ARIA — an adversarial reasoning intelligence that challenges every assumption, explores every angle, and surfaces what others miss.
        </motion.p>

        {/* CTA Button */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.8, delay: 1.3 }}
        >
          <Link href="/aria" id="initiate-aria-btn" className="group relative inline-flex items-center justify-center gap-4">
            {/* Ambient glow */}
            <div className="absolute inset-0 rounded-full bg-white/10 blur-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-700 scale-125" />
            <div className="relative px-10 py-4 rounded-full border border-white/15 bg-white/5 backdrop-blur-xl flex items-center gap-4 group-hover:border-white/30 group-hover:bg-white/10 transition-all duration-500">
              <span className="font-sans font-medium text-sm tracking-[0.25em] uppercase text-white">
                Initiate ARIA
              </span>
              <motion.div
                className="w-4 h-[1px] bg-white/60 origin-left"
                animate={{ scaleX: [1, 1.5, 1] }}
                transition={{ duration: 2.5, repeat: Infinity, ease: "easeInOut" }}
              />
              <svg width="10" height="10" viewBox="0 0 10 10" fill="none" className="text-white/60 group-hover:text-white transition-colors duration-300 group-hover:translate-x-0.5 transition-transform">
                <path d="M1 5H9M9 5L5 1M9 5L5 9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
          </Link>
        </motion.div>
      </div>

      {/* ── Bottom-left: Floating metadata text ── */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 1, delay: 1.5 }}
        className="absolute bottom-8 left-8 z-20"
      >
        <p className="font-sans text-xs text-lavender-gray/30 tracking-widest uppercase">
          Est. 2026 — Hexamind Labs
        </p>
      </motion.div>

      {/* ── Bottom-right: Down hint ── */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 1, delay: 1.6 }}
        className="absolute bottom-8 right-8 z-20 flex items-center gap-2"
      >
        <span className="font-sans text-xs text-lavender-gray/30 tracking-widest uppercase">Scroll after entry</span>
        <motion.div
          animate={{ y: [0, 4, 0] }}
          transition={{ duration: 1.5, repeat: Infinity }}
        >
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <path d="M6 1v10M6 11L2 7M6 11L10 7" stroke="rgba(182,186,197,0.3)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </motion.div>
      </motion.div>
    </main>
  );
}
