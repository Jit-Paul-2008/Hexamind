"use client";

import dynamic from "next/dynamic";

// CSR-only — the section contains React Three Fiber canvases
const ARIADashboard = dynamic(
  () => import("@/components/canvas/ARIAModelSection"),
  {
    ssr: false,
    loading: () => (
      <div className="w-full h-screen flex items-center justify-center bg-background">
        <div className="animate-pulse w-4 h-4 rounded-full bg-lavender-gray/20" />
      </div>
    ),
  }
);

export default function ARIAPage() {
  return (
    // No height constraint, no overflow-hidden — the 400vh scroll section must breathe
    <main className="w-full bg-background">
      <ARIADashboard />
    </main>
  );
}
