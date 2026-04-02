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
      style={{ width: 280 }}
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
        className="relative rounded-2xl border px-5 py-5 backdrop-blur-xl transition-all duration-500"
        style={{
          background: isDone
            ? "rgba(255,255,255,0.07)"
            : "rgba(255,255,255,0.02)",
          borderColor: isDone
            ? "rgba(255,255,255,0.22)"
            : "rgba(255,255,255,0.06)",
          boxShadow: isDone
            ? "0 0 40px rgba(255,255,255,0.05), inset 0 1px 0 rgba(255,255,255,0.08)"
            : "none",
        }}
      >
        {/* Header */}
        <div className="flex items-center gap-2 mb-3">
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
              Synthesis Complete
            </span>
          </div>
        </div>

        {/* Content */}
        {isDone ? (
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.8 }}
            className="font-sans text-sm text-white/90 leading-relaxed"
          >
            {finalAnswer}
          </motion.p>
        ) : status === "active" ? (
          <div className="flex items-center gap-2">
            <div className="flex gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-white/30 animate-bounce" style={{ animationDelay: "0ms" }} />
              <span className="w-1.5 h-1.5 rounded-full bg-white/30 animate-bounce" style={{ animationDelay: "150ms" }} />
              <span className="w-1.5 h-1.5 rounded-full bg-white/30 animate-bounce" style={{ animationDelay: "300ms" }} />
            </div>
            <span className="text-xs text-white/30 font-sans">
              Compiling final answer...
            </span>
          </div>
        ) : (
          <p className="font-sans text-xs text-white/20 italic">
            Pipeline output will appear here
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
