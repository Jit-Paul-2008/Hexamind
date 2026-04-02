"use client";

import { useEffect, useState } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import { usePipelineStore } from "@/lib/store";

export default function ProcessingNode({ data }: NodeProps) {
  const agentId = (data as Record<string, unknown>).agentId as string;
  const label = (data as Record<string, unknown>).label as string;
  const accentColor = (data as Record<string, unknown>).accentColor as string;

  const status = usePipelineStore((s) => s.nodeStatuses[agentId] || "idle");
  const content = usePipelineStore(
    (s) => s.session?.outputs[agentId]?.content || ""
  );
  const startedAt = usePipelineStore(
    (s) => s.session?.outputs[agentId]?.startedAt || 0
  );
  const completedAt = usePipelineStore(
    (s) => s.session?.outputs[agentId]?.completedAt || 0
  );

  const [now, setNow] = useState(0);

  useEffect(() => {
    if (status !== "active") {
      return;
    }
    const id = setInterval(() => setNow(Date.now()), 250);
    return () => clearInterval(id);
  }, [status]);

  const elapsedMs = startedAt ? (completedAt || now) - startedAt : 0;
  const elapsedSeconds = Math.max(0, elapsedMs / 1000);
  const wordCount = content.trim() ? content.trim().split(/\s+/).length : 0;

  return (
    <div
      className="relative rounded-2xl border backdrop-blur-xl px-4 py-3 transition-all duration-300"
      style={{
        width: 270,
        borderColor: `${accentColor}33`,
        background:
          status === "active"
            ? `linear-gradient(180deg, rgba(${hexToRgb(accentColor)}, 0.12) 0%, rgba(10,11,15,0.78) 100%)`
            : "rgba(10,11,15,0.72)",
        boxShadow: status === "active" ? `0 0 18px ${accentColor}22` : "none",
      }}
    >
      <div className="flex items-center justify-between mb-2">
        <span
          className="text-[8px] font-sans tracking-[0.22em] uppercase"
          style={{ color: `${accentColor}bb` }}
        >
          {label} Process
        </span>
        <span className="text-[9px] text-white/45 font-mono">
          {elapsedSeconds.toFixed(1)}s
        </span>
      </div>

      <div className="grid grid-cols-2 gap-2 mb-2 text-[10px] font-sans text-white/60">
        <div className="rounded-lg bg-white/5 px-2 py-1">Status: {status}</div>
        <div className="rounded-lg bg-white/5 px-2 py-1 text-right">{wordCount} words</div>
      </div>

      <div className="min-h-[56px] max-h-[130px] overflow-y-auto rounded-lg bg-black/25 border border-white/10 px-2.5 py-2">
        {status === "idle" ? (
          <p className="text-[10px] text-white/35 italic font-sans">Queueing input...</p>
        ) : (
          <p className="text-[10px] text-white/75 font-sans leading-relaxed whitespace-pre-wrap">
            {content || "Preparing response..."}
            {status === "active" && (
              <span className="inline-block w-1.5 h-3 ml-0.5 bg-white/50 animate-pulse" />
            )}
          </p>
        )}
      </div>

      <Handle
        type="target"
        position={Position.Left}
        className="!w-2.5 !h-2.5 !rounded-full !border-2 !bg-transparent"
        style={{ borderColor: `${accentColor}44` }}
      />
    </div>
  );
}

function hexToRgb(hex: string): string {
  const h = hex.replace("#", "");
  return [
    parseInt(h.slice(0, 2), 16),
    parseInt(h.slice(2, 4), 16),
    parseInt(h.slice(4, 6), 16),
  ].join(",");
}
