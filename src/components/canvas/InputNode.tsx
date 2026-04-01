"use client";

import { Handle, Position, type NodeProps } from "@xyflow/react";
import { motion } from "framer-motion";
import { usePipelineStore } from "@/lib/store";

export default function InputNode({ data }: NodeProps) {
  const session = usePipelineStore((s) => s.session);
  const status = usePipelineStore((s) => s.nodeStatuses["input"]);

  const hasQuery = !!session?.query;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      className="relative"
      style={{ width: 240 }}
    >
      <div
        className="rounded-2xl border px-5 py-4 backdrop-blur-xl transition-all duration-500"
        style={{
          background: hasQuery
            ? "rgba(255,255,255,0.06)"
            : "rgba(255,255,255,0.03)",
          borderColor: hasQuery
            ? "rgba(255,255,255,0.20)"
            : "rgba(255,255,255,0.08)",
          boxShadow: hasQuery
            ? "0 0 30px rgba(255,255,255,0.06), inset 0 1px 0 rgba(255,255,255,0.06)"
            : "none",
        }}
      >
        {/* Header */}
        <div className="flex items-center gap-2 mb-3">
          <div
            className="w-2 h-2 rounded-full transition-colors duration-500"
            style={{
              backgroundColor: hasQuery ? "#e2e8f0" : "#525a6e",
              boxShadow: hasQuery ? "0 0 8px #e2e8f0" : "none",
            }}
          />
          <span className="text-[10px] font-sans tracking-[0.3em] uppercase text-white/50">
            Query
          </span>
        </div>

        {/* Content */}
        {hasQuery ? (
          <p className="font-sans text-sm text-white/90 leading-relaxed">
            {session?.query}
          </p>
        ) : (
          <p className="font-sans text-xs text-white/25 italic">
            Awaiting input...
          </p>
        )}
      </div>

      {/* Output handle — bottom centre */}
      <Handle
        type="source"
        position={Position.Bottom}
        className="!w-2.5 !h-2.5 !rounded-full !border-2 !border-white/20 !bg-white/10"
      />
    </motion.div>
  );
}
