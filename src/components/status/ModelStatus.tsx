"use client";

import { useModels } from "@/hooks/useModels";

export default function ModelStatus() {
  const { status, loading, error } = useModels();

  if (loading) {
    return <p className="text-xs text-white/55">Model status: loading...</p>;
  }

  if (error) {
    return <p className="text-xs text-red-300/90">Model status error: {error}</p>;
  }

  return (
    <div className="rounded-md border border-white/10 bg-black/20 px-3 py-2 text-xs text-white/75">
      <span className="mr-3">Provider: {String(status?.activeProvider ?? status?.configuredProvider ?? "unknown")}</span>
      <span className="mr-3">Model: {String(status?.modelName ?? "n/a")}</span>
      <span className={status?.isFallback ? "text-amber-200" : "text-emerald-200"}>
        {status?.isFallback ? "Fallback" : "Primary"}
      </span>
    </div>
  );
}
