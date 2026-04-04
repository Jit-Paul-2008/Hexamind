"use client";

import { useMemo } from "react";
import { useRunStore } from "@/store/runStore";

export default function CostTracker() {
  const { runs } = useRunStore();

  const estimate = useMemo(() => {
    const base = runs.length * 0.002;
    return Math.max(0.0, base).toFixed(3);
  }, [runs.length]);

  return (
    <div className="rounded-md border border-white/10 bg-black/20 px-3 py-2 text-xs text-white/70">
      Estimated Session Cost: ${estimate}
    </div>
  );
}
