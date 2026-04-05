"use client";

import { motion } from "framer-motion";
import InputBar from "@/components/ui/InputBar";
import StatusIndicator from "@/components/ui/StatusIndicator";
import { AGENTS } from "@/lib/agents";
import { usePipelineStore } from "@/lib/store";

function statusClass(status: string) {
  if (status === "done") return "bg-[#b8e8c6] border-border-dark text-foreground border-2 font-medium";
  if (status === "active") return "bg-pastel-yellow border-border-dark text-foreground border-2 font-medium";
  if (status === "error") return "bg-[#ffb3b3] border-border-dark text-foreground border-2 font-medium";
  return "bg-white border-border-dark text-foreground border-2 opacity-80";
}

export default function Home() {
  const session = usePipelineStore((s) => s.session);
  const statuses = usePipelineStore((s) => s.nodeStatuses);

  return (
    <main className="relative min-h-screen w-full bg-background pb-48 font-bold">
      <a
        href="#query-input"
        className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 z-[120] rounded-md border-3 border-border-dark bg-white px-3 py-2 text-xs text-foreground shadow-[2px_2px_0px_0px_var(--border-color)]"
      >
        Skip to prompt input
      </a>
      <StatusIndicator />

      <section className="relative z-10 mx-auto max-w-6xl px-4 pt-24 md:px-6">
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="mb-5"
        >
          <p className="text-[11px] uppercase tracking-[0.24em] text-foreground/60 font-bold">ARIA Workspace</p>
          <h1 className="mt-1 text-3xl font-extrabold text-foreground tracking-tight">Practical Research Console</h1>
          <p className="mt-2 max-w-2xl text-sm text-foreground/80 font-medium">
            Write a prompt, run the pipeline, and read each agent output with quality signals in one place.
          </p>
        </motion.div>

        <div className="grid gap-6 lg:grid-cols-3">
          <article className="retro-card p-5 lg:col-span-1">
            <p className="text-[12px] uppercase tracking-[0.1em] text-foreground/60 font-bold">Current Prompt</p>
            <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-foreground font-medium">
              {session?.query || "No query yet. Use the prompt box below to start."}
            </p>
            {session?.status === "error" && session.errorMessage ? (
              <div className="mt-4 retro-input bg-[#ffb3b3] px-3 py-2 text-xs text-foreground font-bold">
                {session.errorMessage}
              </div>
            ) : null}
          </article>

          <article className="retro-card p-5 lg:col-span-2">
            <div className="flex items-center justify-between gap-2 border-b-2 border-border-dark/20 pb-2">
              <p className="text-[12px] uppercase tracking-[0.1em] text-foreground/60 font-bold">Agent Progress</p>
              <span className="text-xs text-foreground/70 font-bold uppercase">{session?.status || "ready"}</span>
            </div>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              {AGENTS.map((agent) => {
                const status = statuses[agent.id] || "idle";
                const content = session?.outputs?.[agent.id]?.content || "";
                return (
                  <div
                    key={agent.id}
                    className={`rounded-xl px-4 py-3 border-3 shadow-[2px_2px_0px_0px_var(--border-color)] transition-all ${statusClass(status)}`}
                  >
                    <div className="mb-2 flex items-center justify-between gap-2 border-b-2 border-border-dark/20 pb-2">
                      <p className="text-sm font-bold">{agent.codename}</p>
                      <span className="text-[10px] uppercase font-extrabold tracking-[0.1em]">{status}</span>
                    </div>
                    <p className="line-clamp-4 text-xs leading-5 text-foreground/90 font-medium">
                      {content || "Waiting for output..."}
                    </p>
                  </div>
                );
              })}
            </div>
          </article>
        </div>

        <article className="mt-6 retro-card-peach p-5">
          <div className="flex items-center justify-between gap-2 border-b-2 border-border-dark/20 pb-2">
            <p className="text-[12px] uppercase tracking-[0.1em] text-foreground/60 font-bold">Final Report</p>
            <span className={`rounded-full px-3 py-1 text-[10px] font-extrabold uppercase tracking-[0.1em] shadow-[2px_2px_0px_0px_var(--border-color)] ${statusClass(statuses.output || "idle")}`}>
              {statuses.output || "idle"}
            </span>
          </div>
          <div className="mt-4 max-h-[42vh] overflow-auto retro-input p-4">
            <p className="whitespace-pre-wrap text-sm leading-6 text-foreground font-medium">
              {session?.finalAnswer || "Final answer will appear here after pipeline completion."}
            </p>
          </div>
          {session?.qualityReport ? (
            <div className="mt-4 grid gap-3 text-xs text-foreground md:grid-cols-3">
              <div className="retro-input p-3 font-bold text-center">
                Score: {session.qualityReport.overallScore.toFixed(1)}
              </div>
              <div className="retro-input p-3 font-bold text-center">
                Sources: {session.qualityReport.metrics.sourceCount}
              </div>
              <div className="retro-input p-3 font-bold text-center">
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
