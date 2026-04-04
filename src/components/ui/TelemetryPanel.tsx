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

type CompetitiveSummary = {
  status?: string;
  batchName?: string;
  topicCount?: number;
  providerStats?: Record<
    string,
    {
      wins?: number;
      topics?: number;
      averageScore?: number;
      averageTrust?: number;
    }
  >;
  notes?: string[];
};

export default function TelemetryPanel() {
  const [payload, setPayload] = useState<HealthPayload | null>(null);
  const [competitiveSummary, setCompetitiveSummary] = useState<CompetitiveSummary | null>(null);
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  const loadTelemetry = async () => {
    try {
      const [healthResponse, competitiveResponse] = await Promise.all([
        fetch(`${API_BASE_URL}/health`),
        fetch(`${API_BASE_URL}/api/benchmark/competitive`),
      ]);
      const json = healthResponse.ok ? ((await healthResponse.json()) as HealthPayload) : null;
      const competitiveJson = competitiveResponse.ok
        ? ((await competitiveResponse.json()) as CompetitiveSummary)
        : null;
      setPayload(json);
      setCompetitiveSummary(competitiveJson);
    } catch {
      setPayload(null);
      setCompetitiveSummary(null);
    }
  };

  useEffect(() => {
    let active = true;

    const load = async () => {
      try {
        const [healthResponse, competitiveResponse] = await Promise.all([
          fetch(`${API_BASE_URL}/health`),
          fetch(`${API_BASE_URL}/api/benchmark/competitive`),
        ]);
        const json = healthResponse.ok ? ((await healthResponse.json()) as HealthPayload) : null;
        const competitiveJson = competitiveResponse.ok
          ? ((await competitiveResponse.json()) as CompetitiveSummary)
          : null;
        if (active) {
          setPayload(json);
          setCompetitiveSummary(competitiveJson);
        }
      } catch {
        if (active) {
          setPayload(null);
          setCompetitiveSummary(null);
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

  const providerEntries = Object.entries(competitiveSummary?.providerStats || {}).sort(
    (a, b) => (b[1].averageScore ?? 0) - (a[1].averageScore ?? 0)
  );

  const onCopyTelemetry = async () => {
    if (!payload) {
      return;
    }

    try {
      await navigator.clipboard.writeText(
        JSON.stringify(
          {
            health: payload,
            competitiveSummary,
            copiedAt: new Date().toISOString(),
          },
          null,
          2
        )
      );
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay: 0.15 }}
      className="fixed bottom-24 left-6 z-40 w-[min(360px,calc(100vw-3rem))] rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 backdrop-blur-xl shadow-[0_18px_48px_rgba(0,0,0,0.26)]"
    >
      <div className="flex items-center justify-between gap-3 mb-2">
        <div className="text-[10px] uppercase tracking-[0.28em] text-white/40">Telemetry</div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => void loadTelemetry()}
            className="rounded-md border border-white/10 px-2 py-1 text-[9px] uppercase tracking-[0.2em] text-white/40 hover:text-white/75 hover:border-white/20 transition"
          >
            Refresh
          </button>
          <div className="text-[10px] text-white/30">{payload.status || "unknown"}</div>
        </div>
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
      {competitiveSummary?.status === "ready" ? (
        <div className="mt-3 rounded-xl border border-white/8 bg-black/20 p-3 text-[10px] text-white/62 space-y-1">
          <div className="uppercase tracking-[0.2em] text-white/35">Competitive batch</div>
          <div>{competitiveSummary.batchName || "latest batch"} • {competitiveSummary.topicCount ?? 0} topics</div>
          <div className="grid grid-cols-1 gap-1.5">
            {providerEntries.map(([providerName, stats]) => (
              <div
                key={providerName}
                className="flex items-center justify-between rounded-lg border border-white/8 bg-white/[0.02] px-2 py-1"
              >
                <span className="text-white/55">{providerName}</span>
                <span className="text-white/75">
                  Score {stats.averageScore?.toFixed(1) ?? "n/a"} · Trust {stats.averageTrust?.toFixed(2) ?? "n/a"} · Wins {stats.wins ?? 0}
                </span>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      <div className="mt-3 flex items-center gap-2">
        <button
          type="button"
          onClick={() => setExpanded((value) => !value)}
          className="rounded-md border border-white/10 px-2 py-1 text-[9px] uppercase tracking-[0.2em] text-white/40 hover:text-white/75 hover:border-white/20 transition"
        >
          {expanded ? "Hide details" : "Show details"}
        </button>
        <button
          type="button"
          onClick={() => void onCopyTelemetry()}
          className="rounded-md border border-white/10 px-2 py-1 text-[9px] uppercase tracking-[0.2em] text-white/40 hover:text-white/75 hover:border-white/20 transition"
        >
          {copied ? "Copied" : "Copy JSON"}
        </button>
      </div>

      {expanded ? (
        <pre className="mt-2 max-h-[180px] overflow-auto rounded-lg border border-white/8 bg-black/30 p-2 text-[9px] text-white/45">
          {JSON.stringify({ health: payload, competitiveSummary }, null, 2)}
        </pre>
      ) : null}
    </motion.div>
  );
}