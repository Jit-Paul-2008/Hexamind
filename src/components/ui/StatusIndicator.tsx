"use client";

import { motion } from "framer-motion";
import { usePipelineStore } from "@/lib/store";

export default function StatusIndicator() {
  const pipelineStatus = usePipelineStore((s) => s.session?.status);

  const statusText = (() => {
    switch (pipelineStatus) {
      case "running":
        return "Processing";
      case "complete":
        return "Complete";
      case "error":
        return "Error";
      default:
        return "Ready";
    }
  })();

  const dotColor = (() => {
    switch (pipelineStatus) {
      case "running":
        return "#818cf8";
      case "complete":
        return "#34d399";
      case "error":
        return "#f87171";
      default:
        return "#525a6e";
    }
  })();

  return (
    <motion.div
      initial={{ opacity: 0, x: 10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.6, delay: 0.2 }}
      className="fixed top-5 right-6 z-50 flex items-center gap-2.5"
    >
      {/* TODO(backend): WebSocket connection status indicator */}
      <div className="px-3.5 py-1.5 rounded-full bg-white/5 border border-white/8 backdrop-blur-xl flex items-center gap-2">
        <div
          className={`w-1.5 h-1.5 rounded-full transition-colors duration-500 ${
            pipelineStatus === "running" ? "animate-pulse" : ""
          }`}
          style={{ backgroundColor: dotColor, boxShadow: `0 0 6px ${dotColor}` }}
        />
        <span className="font-sans text-[10px] tracking-[0.25em] uppercase text-white/40">
          {statusText}
        </span>
      </div>
    </motion.div>
  );
}
