"use client";

import { Handle, Position, type NodeProps } from "@xyflow/react";
import { motion } from "framer-motion";
import { usePipelineStore } from "@/lib/store";

export default function OutputNode({}: NodeProps) {
  const status = usePipelineStore((s) => s.nodeStatuses["output"]);
  const finalAnswer = usePipelineStore((s) => s.session?.finalAnswer || "");
  const isDone = status === "done";

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      className="relative"
      style={{ width: 780 }}
    >
      {/* Glow when result is ready */}
      {isDone && (
        <div
          className="absolute -inset-2 rounded-3xl blur-2xl pointer-events-none"
          style={{
            background:
              "radial-gradient(circle, rgba(226,232,240,0.12) 0%, transparent 70%)",
          }}
        />
      )}

      <div
        className="relative rounded-[28px] border px-7 py-7 backdrop-blur-xl transition-all duration-500"
        style={{
          minHeight: 1123,
          background: isDone
            ? "linear-gradient(180deg, rgba(255,255,255,0.08) 0%, rgba(9,10,14,0.94) 100%)"
            : "linear-gradient(180deg, rgba(255,255,255,0.03) 0%, rgba(9,10,14,0.92) 100%)",
          borderColor: isDone
            ? "rgba(255,255,255,0.24)"
            : "rgba(255,255,255,0.06)",
          boxShadow: isDone
            ? "0 30px 90px rgba(0,0,0,0.55), inset 0 1px 0 rgba(255,255,255,0.10)"
            : "0 20px 60px rgba(0,0,0,0.28)",
        }}
      >
        {/* Header */}
        <div className="flex items-center justify-between gap-4 mb-6">
          <div className="flex items-center gap-1.5">
            {isDone ? (
              <svg
                width="14"
                height="14"
                viewBox="0 0 14 14"
                fill="none"
                className="text-emerald-400"
              >
                <path
                  d="M3 7.5L6 10.5L11 4"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            ) : (
              <div className="w-2 h-2 rounded-full bg-white/15" />
            )}
            <span className="text-[10px] font-sans tracking-[0.3em] uppercase text-white/50">
              Research Synthesis Report
            </span>
          </div>
          <div className="text-right">
            <div className="text-[9px] uppercase tracking-[0.28em] text-white/35">
              A4 Report View
            </div>
            <div className="text-[9px] text-white/25 font-mono">Thesis-style output</div>
          </div>
        </div>

        {/* Content */}
        {isDone ? (
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.8 }}
            className="font-sans text-[13px] text-white/88 leading-7 whitespace-pre-wrap max-h-[980px] overflow-y-auto pr-2"
          >
            {finalAnswer}
          </motion.p>
        ) : status === "active" ? (
          <div className="flex items-center gap-2 min-h-[220px]">
            <div className="flex gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-white/30 animate-bounce" style={{ animationDelay: "0ms" }} />
              <span className="w-1.5 h-1.5 rounded-full bg-white/30 animate-bounce" style={{ animationDelay: "150ms" }} />
              <span className="w-1.5 h-1.5 rounded-full bg-white/30 animate-bounce" style={{ animationDelay: "300ms" }} />
            </div>
            <span className="text-xs text-white/30 font-sans">
              Compiling structured report...
            </span>
          </div>
        ) : (
          <p className="font-sans text-xs text-white/20 italic min-h-[220px]">
            Pipeline output will appear here as a full research report
          </p>
        )}
      </div>

      {/* Input handle — top */}
      <Handle
        type="target"
        position={Position.Top}
        className="!w-2.5 !h-2.5 !rounded-full !border-2 !border-white/20 !bg-white/10"
      />
    </motion.div>
  );
}
