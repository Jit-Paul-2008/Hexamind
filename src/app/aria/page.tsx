"use client";

import dynamic from "next/dynamic";
import OverlayList from "@/components/ui/OverlayList";

// Dynamically import the 3D scene to prevent SSR issues with canvas/webgl
const Scene = dynamic(() => import("@/components/canvas/Scene"), {
  ssr: false,
  loading: () => (
    <div className="absolute inset-0 bg-background flex items-center justify-center">
      <div className="animate-pulse w-8 h-8 rounded-full bg-lavender-gray/20"></div>
    </div>
  ),
});

export default function Home() {
  return (
    <main className="relative min-h-screen w-full overflow-hidden bg-background">
      <Scene />
      <OverlayList />
    </main>
  );
}
