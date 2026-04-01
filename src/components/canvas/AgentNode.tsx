"use client";

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

  const status = usePipelineStore((s) => s.nodeStatuses[agentId] || "idle");
  const content = usePipelineStore(
    (s) => s.session?.outputs[agentId]?.content || ""
  );

  const styles = STATUS_STYLES[status];

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6 }}
      className="relative"
      style={{ width: 260 }}
    >
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
