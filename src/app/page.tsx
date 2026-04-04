"use client";

import { motion } from "framer-motion";
import InputBar from "@/components/ui/InputBar";
import StatusIndicator from "@/components/ui/StatusIndicator";
import { AGENTS } from "@/lib/agents";
import { usePipelineStore } from "@/lib/store";

function statusClass(status: string) {
  if (status === "done") return "text-emerald-200 border-emerald-300/30 bg-emerald-300/10";
  if (status === "active") return "text-amber-100 border-amber-300/30 bg-amber-300/10";
  if (status === "error") return "text-rose-100 border-rose-300/30 bg-rose-300/10";
  return "text-white/60 border-white/10 bg-white/5";
}

export default function Home() {
  const session = usePipelineStore((s) => s.session);
  const statuses = usePipelineStore((s) => s.nodeStatuses);

  return (
    <main className="relative min-h-screen w-full bg-[#0f1116] pb-48">
      <a
        href="#query-input"
        className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 z-[120] rounded-md border border-white/20 bg-black/90 px-3 py-2 text-xs text-white"
      >
        Skip to prompt input
      </a>

      <div className="absolute inset-0 z-0 pointer-events-none aurora-bg" />
      <StatusIndicator />

      <section className="relative z-10 mx-auto max-w-6xl px-4 pt-24 md:px-6">
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="mb-5"
        >
          <p className="text-[11px] uppercase tracking-[0.24em] text-amber-100/60">ARIA Workspace</p>
          <h1 className="mt-1 text-2xl font-semibold text-white">Practical Research Console</h1>
          <p className="mt-2 max-w-2xl text-sm text-white/70">
            Write a prompt, run the pipeline, and read each agent output with quality signals in one place.
          </p>
        </motion.div>

        <div className="grid gap-4 lg:grid-cols-3">
          <article className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 lg:col-span-1">
            <p className="text-[11px] uppercase tracking-[0.2em] text-white/50">Current Prompt</p>
            <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-white/85">
              {session?.query || "No query yet. Use the prompt box below to start."}
            </p>
            {session?.status === "error" && session.errorMessage ? (
              <div className="mt-4 rounded-xl border border-rose-300/30 bg-rose-300/10 px-3 py-2 text-xs text-rose-100">
                {session.errorMessage}
              </div>
            ) : null}
          </article>

          <article className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 lg:col-span-2">
            <div className="flex items-center justify-between gap-2">
              <p className="text-[11px] uppercase tracking-[0.2em] text-white/50">Agent Progress</p>
              <span className="text-xs text-white/50">{session?.status || "ready"}</span>
            </div>
            <div className="mt-3 grid gap-3 md:grid-cols-2">
              {AGENTS.map((agent) => {
                const status = statuses[agent.id] || "idle";
                const content = session?.outputs?.[agent.id]?.content || "";
                return (
                  <div
                    key={agent.id}
                    className={`rounded-xl border px-3 py-3 ${statusClass(status)}`}
                  >
                    <div className="mb-2 flex items-center justify-between gap-2">
                      <p className="text-sm font-medium">{agent.codename}</p>
                      <span className="text-[10px] uppercase tracking-[0.18em]">{status}</span>
                    </div>
                    <p className="line-clamp-4 text-xs leading-5 text-white/75">
                      {content || "Waiting for output..."}
                    </p>
                  </div>
                );
              })}
            </div>
          </article>
        </div>

        <article className="mt-4 rounded-2xl border border-white/10 bg-white/[0.03] p-4">
          <div className="flex items-center justify-between gap-2">
            <p className="text-[11px] uppercase tracking-[0.2em] text-white/50">Final Report</p>
            <span className={`rounded-full border px-2 py-0.5 text-[10px] uppercase tracking-[0.16em] ${statusClass(statuses.output || "idle")}`}>
              {statuses.output || "idle"}
            </span>
          </div>
          <div className="mt-3 max-h-[42vh] overflow-auto rounded-xl border border-white/10 bg-black/25 p-3">
            <p className="whitespace-pre-wrap text-sm leading-6 text-white/85">
              {session?.finalAnswer || "Final answer will appear here after pipeline completion."}
            </p>
          </div>
          {session?.qualityReport ? (
            <div className="mt-3 grid gap-2 text-xs text-white/70 md:grid-cols-3">
              <div className="rounded-lg border border-white/10 bg-white/5 px-3 py-2">
                Score: {session.qualityReport.overallScore.toFixed(1)}
              </div>
              <div className="rounded-lg border border-white/10 bg-white/5 px-3 py-2">
                Sources: {session.qualityReport.metrics.sourceCount}
              </div>
              <div className="rounded-lg border border-white/10 bg-white/5 px-3 py-2">
                Contradictions: {session.qualityReport.metrics.contradictionCount}
              </div>
            </div>
          ) : null}
        </article>
      </section>

      <InputBar />
    </main>
  );
}
