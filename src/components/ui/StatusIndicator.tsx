"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { usePipelineStore } from "@/lib/store";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export default function StatusIndicator() {
  const pipelineStatus = usePipelineStore((s) => s.session?.status);
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);

  useEffect(() => {
    let active = true;

    const checkBackend = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/health`);
        if (active) {
          setBackendOnline(response.ok);
        }
      } catch {
        if (active) {
          setBackendOnline(false);
        }
      }
    };

    checkBackend();
    const timer = setInterval(checkBackend, 7000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, []);

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

  const backendText = backendOnline === null ? "Checking" : backendOnline ? "Online" : "Offline";
  const backendColor = backendOnline === null ? "#9ca3af" : backendOnline ? "#34d399" : "#f87171";

  return (
    <motion.div
      initial={{ opacity: 0, x: 10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.6, delay: 0.2 }}
      className="fixed top-5 right-6 z-50 flex items-center gap-2.5"
    >
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
      <div className="px-3.5 py-1.5 rounded-full bg-white/5 border border-white/8 backdrop-blur-xl flex items-center gap-2">
        <div
          className="w-1.5 h-1.5 rounded-full transition-colors duration-500"
          style={{ backgroundColor: backendColor, boxShadow: `0 0 6px ${backendColor}` }}
        />
        <span className="font-sans text-[10px] tracking-[0.25em] uppercase text-white/40">
          API {backendText}
        </span>
      </div>
    </motion.div>
  );
}
