"use client";

import dynamic from "next/dynamic";
import OverlayList from "@/components/ui/OverlayList";

// Dynamically import (CSR-only) the full prism model section
const ARIAModel = dynamic(() => import("@/components/canvas/ARIAModelSection"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-screen flex items-center justify-center bg-background">
      <div className="animate-pulse w-4 h-4 rounded-full bg-lavender-gray/20" />
    </div>
  ),
});

export default function ARIAPage() {
  return (
    // Full-height scroll container (no snap — natural scroll)
    <div className="relative w-full bg-background">

      {/* ── Viewport 1: Dashboard Overlay (no 3D canvas here) ── */}
      <section className="relative w-full h-screen overflow-hidden">
        {/* Pure dark background with subtle grid texture */}
        <div
          className="absolute inset-0 z-0 bg-background"
          style={{
            backgroundImage: `radial-gradient(circle at 1px 1px, rgba(182,186,197,0.04) 1px, transparent 0)`,
            backgroundSize: "40px 40px",
          }}
        />
        {/* Top ambient glow */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] rounded-full bg-indigo-charcoal/30 blur-[120px] -translate-y-1/2 z-0" />
        <OverlayList />
      </section>

      {/* ── Scroll indicator between sections ── */}
      <div className="relative z-10 flex items-center justify-center py-6 gap-3">
        <div className="h-[1px] flex-1 max-w-xs bg-gradient-to-r from-transparent to-white/10" />
        <span className="font-sans text-[10px] tracking-[0.3em] uppercase text-lavender-gray/30">
          ARIA Model
        </span>
        <div className="h-[1px] flex-1 max-w-xs bg-gradient-to-l from-transparent to-white/10" />
      </div>

      {/* ── Viewport 2: ARIA Prism Reveal (3D model lives here) ── */}
      <section className="relative w-full h-screen overflow-hidden">
        <ARIAModel />
      </section>
    </div>
  );
}
