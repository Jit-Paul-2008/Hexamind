"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

type HealthPayload = {
  status?: string;
  activeProvider?: string;
  circuitState?: string;
  fallbackCount?: number;
  promptRegistryVersion?: string;
  promptRegistrySize?: number;
  maxConcurrentStreams?: number;
  activeStreams?: number;
  queueWaitTimeoutSeconds?: number;
  retrievalTimeoutSeconds?: number;
  agentTimeoutSeconds?: number;
  finalTimeoutSeconds?: number;
};

export default function TelemetryPanel() {
  const [payload, setPayload] = useState<HealthPayload | null>(null);

  useEffect(() => {
    let active = true;

    const load = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/health`);
        const json = response.ok ? ((await response.json()) as HealthPayload) : null;
        if (active) {
          setPayload(json);
        }
      } catch {
        if (active) {
          setPayload(null);
        }
      }
    };

    void load();
    const timer = setInterval(load, 15000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, []);

  if (!payload) {
    return null;
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay: 0.15 }}
      className="fixed bottom-24 left-6 z-40 w-[320px] rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 backdrop-blur-xl shadow-[0_18px_48px_rgba(0,0,0,0.26)]"
    >
      <div className="flex items-center justify-between gap-3 mb-2">
        <div className="text-[10px] uppercase tracking-[0.28em] text-white/40">Telemetry</div>
        <div className="text-[10px] text-white/30">{payload.status || "unknown"}</div>
      </div>
      <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-[10px] text-white/62">
        <div>Provider: {payload.activeProvider || "unknown"}</div>
        <div>Circuit: {payload.circuitState || "closed"}</div>
        <div>Streams: {payload.activeStreams ?? 0}/{payload.maxConcurrentStreams ?? 0}</div>
        <div>Fallbacks: {payload.fallbackCount ?? 0}</div>
        <div>Prompt registry: {payload.promptRegistryVersion || "n/a"}</div>
        <div>Prompt count: {payload.promptRegistrySize ?? 0}</div>
        <div>Queue wait: {payload.queueWaitTimeoutSeconds ?? 0}s</div>
        <div>Final timeout: {payload.finalTimeoutSeconds ?? 0}s</div>
      </div>
    </motion.div>
  );
}