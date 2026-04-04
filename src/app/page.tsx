"use client";

import dynamic from "next/dynamic";
import { motion } from "framer-motion";
import InputBar from "@/components/ui/InputBar";
import StatusIndicator from "@/components/ui/StatusIndicator";
import TelemetryPanel from "@/components/ui/TelemetryPanel";

// CSR-only — ReactFlow uses browser APIs
const HexamindCanvas = dynamic(
  () => import("@/components/canvas/HexamindCanvas"),
  {
    ssr: false,
    loading: () => (
      <div className="w-full h-full flex items-center justify-center">
        <div className="animate-pulse w-3 h-3 rounded-full bg-white/10" />
      </div>
    ),
  }
);

export default function Home() {
  return (
    <main className="relative w-full h-screen overflow-hidden bg-[#0a0b0f]">
      <a
        href="#query-input"
        className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 z-[120] rounded-md border border-white/20 bg-black/90 px-3 py-2 text-xs text-white"
      >
        Skip to prompt input
      </a>

      <div className="absolute inset-0 z-0 pointer-events-none hex-grid-overlay" />
      <div className="absolute inset-0 z-0 pointer-events-none aurora-bg" />

      {/* ── Top-left: System label ── */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, delay: 0.1 }}
        className="fixed top-5 left-6 z-50 flex items-center gap-2.5"
      >
        <div className="w-1.5 h-1.5 rounded-full bg-lavender-gray/60" />
        <span className="font-sans text-[10px] tracking-[0.3em] uppercase text-white/30">
          Hexamind · ARIA
        </span>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: -6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, delay: 0.18 }}
        className="fixed top-10 left-6 z-50 hidden md:flex items-center gap-2 text-[10px] text-white/40"
      >
        <span className="rounded-full border border-white/10 px-2 py-1 tracking-[0.12em] uppercase">
          live orchestration
        </span>
        <span className="rounded-full border border-white/10 px-2 py-1 tracking-[0.12em] uppercase">
          adversarial agents
        </span>
        <span className="rounded-full border border-white/10 px-2 py-1 tracking-[0.12em] uppercase">
          quality gates
        </span>
      </motion.div>

      {/* ── Status indicator (top-right) ── */}
      <StatusIndicator />

      {/* ── Telemetry panel (bottom-left) ── */}
      <TelemetryPanel />

      {/* ── Centre vignette — subtle radial glow ── */}
      <div className="absolute inset-0 z-0 pointer-events-none flex items-center justify-center">
        <div
          className="w-[80vw] h-[80vw] max-w-[900px] max-h-[900px] rounded-full"
          style={{
            background:
              "radial-gradient(circle, rgba(67,189,146,0.08) 0%, rgba(52,93,129,0.04) 45%, transparent 72%)",
            filter: "blur(60px)",
          }}
        />
      </div>

      {/* ── Node graph canvas ── */}
      <div className="absolute inset-0 z-10">
        <HexamindCanvas />
      </div>

      {/* ── Input bar — fixed at bottom ── */}
      <InputBar />
    </main>
  );
}
