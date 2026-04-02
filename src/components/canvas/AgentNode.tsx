"use client";

import { useEffect, useState } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import { motion } from "framer-motion";
import { usePipelineStore } from "@/lib/store";
import type { NodeStatus } from "@/types/pipeline";

// Visual config per status
const STATUS_STYLES: Record<
  NodeStatus,
  { borderOpacity: number; glow: boolean; pulseClass: string }
> = {
  idle: { borderOpacity: 0.08, glow: false, pulseClass: "" },
  active: { borderOpacity: 0.5, glow: true, pulseClass: "animate-pulse" },
  done: { borderOpacity: 0.25, glow: false, pulseClass: "" },
  error: { borderOpacity: 0.6, glow: true, pulseClass: "animate-pulse" },
};

export default function AgentNode({ data }: NodeProps) {
  const agentId = (data as Record<string, unknown>).agentId as string;
  const label = (data as Record<string, unknown>).label as string;
  const role = (data as Record<string, unknown>).role as string;
  const accentColor = (data as Record<string, unknown>).accentColor as string;
  const panelSide =
    ((data as Record<string, unknown>).panelSide as "left" | "right") ||
    "right";

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

  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    if (status !== "active") {
      return;
    }
    const id = setInterval(() => setNow(Date.now()), 250);
    return () => clearInterval(id);
  }, [status]);

  const styles = STATUS_STYLES[status];
  const elapsedMs = startedAt
    ? (completedAt || now) - startedAt
    : 0;
  const elapsedSeconds = Math.max(0, elapsedMs / 1000);
  const wordCount = content.trim() ? content.trim().split(/\s+/).length : 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6 }}
      className="relative"
      style={{ width: 260 }}
    >
      {/* Side processing window */}
      <div
        className="absolute top-0 w-[260px] rounded-2xl border backdrop-blur-xl px-4 py-3 transition-all duration-300"
        style={{
          left: panelSide === "right" ? "calc(100% + 14px)" : "auto",
          right: panelSide === "left" ? "calc(100% + 14px)" : "auto",
          borderColor: `${accentColor}33`,
          background:
            status === "active"
              ? `linear-gradient(180deg, rgba(${hexToRgb(accentColor)}, 0.12) 0%, rgba(10,11,15,0.78) 100%)`
              : "rgba(10,11,15,0.72)",
          boxShadow:
            status === "active"
              ? `0 0 18px ${accentColor}22`
              : "none",
        }}
      >
        <div className="flex items-center justify-between mb-2">
          <span
            className="text-[8px] font-sans tracking-[0.22em] uppercase"
            style={{ color: `${accentColor}bb` }}
          >
            {label} Window
          </span>
          <span className="text-[9px] text-white/45 font-mono">
            {elapsedSeconds.toFixed(1)}s
          </span>
        </div>

        <div className="grid grid-cols-2 gap-2 mb-2 text-[10px] font-sans text-white/60">
          <div className="rounded-lg bg-white/5 px-2 py-1">
            Status: {status}
          </div>
          <div className="rounded-lg bg-white/5 px-2 py-1 text-right">
            {wordCount} words
          </div>
        </div>

        <div className="min-h-[56px] max-h-[130px] overflow-y-auto rounded-lg bg-black/25 border border-white/10 px-2.5 py-2">
          {status === "idle" ? (
            <p className="text-[10px] text-white/35 italic font-sans">
              Queueing input...
            </p>
          ) : (
            <p className="text-[10px] text-white/75 font-sans leading-relaxed whitespace-pre-wrap">
              {content || "Preparing response..."}
              {status === "active" && (
                <span className="inline-block w-1.5 h-3 ml-0.5 bg-white/50 animate-pulse" />
              )}
            </p>
          )}
        </div>
      </div>

      {/* Glow layer — only visible when active */}
      {styles.glow && (
        <div
          className="absolute -inset-1 rounded-2xl blur-xl pointer-events-none"
          style={{
            background: `radial-gradient(circle, ${accentColor}30 0%, transparent 70%)`,
          }}
        />
      )}

      <div
        className={`relative rounded-2xl border px-5 py-4 backdrop-blur-xl transition-all duration-500 ${styles.pulseClass}`}
        style={{
          background:
            status === "active"
              ? `rgba(${hexToRgb(accentColor)}, 0.06)`
              : "rgba(255,255,255,0.03)",
          borderColor:
            status === "error"
              ? "#f87171"
              : `${accentColor}${Math.round(styles.borderOpacity * 255)
                  .toString(16)
                  .padStart(2, "0")}`,
          boxShadow: styles.glow
            ? `0 0 24px ${accentColor}22, inset 0 1px 0 ${accentColor}11`
            : "none",
        }}
      >
        {/* Header row */}
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <div
              className="w-2 h-2 rounded-full transition-all duration-500"
              style={{
                backgroundColor:
                  status === "idle" ? "#525a6e" : accentColor,
                boxShadow:
                  status === "active"
                    ? `0 0 10px ${accentColor}`
                    : "none",
              }}
            />
            <span
              className="font-serif text-sm tracking-tight transition-colors duration-300"
              style={{
                color:
                  status === "idle" ? "rgba(255,255,255,0.35)" : "#fff",
              }}
            >
              {label}
            </span>
          </div>
          <span
            className="text-[8px] font-sans tracking-[0.25em] uppercase"
            style={{ color: `${accentColor}88` }}
          >
            {status === "idle" ? "standby" : status}
          </span>
        </div>

        {/* Role subtitle */}
        <p
          className="text-[9px] font-sans tracking-[0.2em] uppercase mb-3"
          style={{ color: `${accentColor}55` }}
        >
          {role}
        </p>

        {/* Content area */}
        <div className="min-h-[40px] max-h-[100px] overflow-hidden">
          {status === "idle" ? (
            <p className="text-[11px] text-white/15 italic font-sans">
              Waiting for data...
            </p>
          ) : (
            <p className="text-[11px] text-white/75 font-sans leading-relaxed">
              {content}
              {status === "active" && (
                <span className="inline-block w-1.5 h-3 ml-0.5 bg-white/50 animate-pulse" />
              )}
            </p>
          )}
        </div>
      </div>

      {/* Handles */}
      <Handle
        type="target"
        position={Position.Top}
        className="!w-2.5 !h-2.5 !rounded-full !border-2 !bg-transparent"
        style={{ borderColor: `${accentColor}44` }}
      />
      <Handle
        type="source"
        position={Position.Bottom}
        className="!w-2.5 !h-2.5 !rounded-full !border-2 !bg-transparent"
        style={{ borderColor: `${accentColor}44` }}
      />
    </motion.div>
  );
}

// Util — hex to rgb string
function hexToRgb(hex: string): string {
  const h = hex.replace("#", "");
  return [
    parseInt(h.slice(0, 2), 16),
    parseInt(h.slice(2, 4), 16),
    parseInt(h.slice(4, 6), 16),
  ].join(",");
}
