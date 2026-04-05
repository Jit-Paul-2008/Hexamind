"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { usePipelineStore } from "@/lib/store";
import { fetchHealthCached } from "@/lib/api/cachedBackend";

export default function StatusIndicator() {
  const pipelineStatus = usePipelineStore((s) => s.session?.status);
  const sessionCreatedAt = usePipelineStore((s) => s.session?.createdAt || 0);
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);
  const [modelLabel, setModelLabel] = useState("Model ...");
  const [circuitLabel, setCircuitLabel] = useState("Circuit unknown");
  const [clockLabel, setClockLabel] = useState(() =>
    new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
  );
  const [elapsedLabel, setElapsedLabel] = useState("0m 00s");

  useEffect(() => {
    let active = true;

    const checkBackend = async () => {
      try {
        const { ok, data: payload } = await fetchHealthCached();
        if (active) {
          setBackendOnline(ok);
          if (payload && typeof payload === "object") {
            const activeProvider =
              typeof payload.activeProvider === "string"
                ? payload.activeProvider
                : "unknown";
            const isFallback = payload.isFallback === true;
            const circuitState =
              typeof payload.circuitState === "string"
                ? payload.circuitState
                : "closed";
            setModelLabel(
              isFallback
                ? `${activeProvider} fallback`
                : `${activeProvider} live`
            );
            setCircuitLabel(`Circuit ${circuitState}`);
          } else {
            setModelLabel("Model unknown");
            setCircuitLabel("Circuit unknown");
          }
        }
      } catch {
        if (active) {
          setBackendOnline(false);
          setModelLabel("Model offline");
          setCircuitLabel("Circuit offline");
        }
      }
    };

    checkBackend();
    const timer = setInterval(checkBackend, 12_000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    const id = setInterval(() => {
      setClockLabel(new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }));
      if (!sessionCreatedAt) {
        setElapsedLabel("0m 00s");
        return;
      }
      const elapsedSeconds = Math.max(0, Math.floor((Date.now() - sessionCreatedAt) / 1000));
      const minutes = Math.floor(elapsedSeconds / 60);
      const seconds = elapsedSeconds % 60;
      setElapsedLabel(`${minutes}m ${String(seconds).padStart(2, "0")}s`);
    }, 1000);

    return () => clearInterval(id);
  }, [sessionCreatedAt]);

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
      className="fixed top-5 right-6 z-50 flex max-w-[calc(100vw-2rem)] flex-wrap justify-end items-center gap-2"
    >
      <div className="px-3.5 py-1.5 rounded-full border-3 border-border-dark bg-white shadow-[2px_2px_0px_0px_var(--border-color)] flex items-center gap-2">
        <div
          className={`w-2 h-2 rounded-full border border-border-dark transition-colors duration-500 ${
            pipelineStatus === "running" ? "animate-pulse" : ""
          }`}
          style={{ backgroundColor: dotColor }}
        />
        <span className="font-sans text-[10px] tracking-[0.1em] font-extrabold uppercase text-foreground">
          {statusText}
        </span>
      </div>
      <div className="px-3.5 py-1.5 rounded-full border-3 border-border-dark bg-white shadow-[2px_2px_0px_0px_var(--border-color)] flex items-center gap-2">
        <div
          className="w-2 h-2 rounded-full border border-border-dark transition-colors duration-500"
          style={{ backgroundColor: backendColor }}
        />
        <span className="font-sans text-[10px] tracking-[0.1em] font-extrabold uppercase text-foreground">
          API {backendText}
        </span>
      </div>
      <div className="px-3.5 py-1.5 rounded-full border-3 border-border-dark bg-white shadow-[2px_2px_0px_0px_var(--border-color)] flex items-center gap-2">
        <div className="w-2 h-2 rounded-full border border-border-dark bg-[#93c5fd]" />
        <span className="font-sans text-[10px] tracking-[0.05em] font-extrabold uppercase text-foreground/80">
          {modelLabel}
        </span>
      </div>
      <div className="px-3.5 py-1.5 rounded-full border-3 border-border-dark bg-white shadow-[2px_2px_0px_0px_var(--border-color)] flex items-center gap-2">
        <div className="w-2 h-2 rounded-full border border-border-dark bg-[#fcd34d]" />
        <span className="font-sans text-[10px] tracking-[0.05em] font-extrabold uppercase text-foreground/80">
          {circuitLabel}
        </span>
      </div>
      <div className="px-3.5 py-1.5 rounded-full border-3 border-border-dark bg-white shadow-[2px_2px_0px_0px_var(--border-color)] flex items-center gap-2">
        <div className="w-2 h-2 rounded-full border border-border-dark bg-[#c4b5fd]" />
        <span className="font-sans text-[10px] tracking-[0.05em] font-extrabold uppercase text-foreground/80">
          Uptime {elapsedLabel}
        </span>
      </div>
      <div className="px-3.5 py-1.5 rounded-full border-3 border-border-dark bg-white shadow-[2px_2px_0px_0px_var(--border-color)] flex items-center gap-2">
        <div className="w-2 h-2 rounded-full border border-border-dark bg-[#7dd3fc]" />
        <span className="font-sans text-[10px] tracking-[0.05em] font-extrabold uppercase text-foreground/80">
          {clockLabel}
        </span>
      </div>
    </motion.div>
  );
}
