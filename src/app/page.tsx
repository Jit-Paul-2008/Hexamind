"use client";

import { motion } from "framer-motion";
import InputBar from "@/components/ui/InputBar";
import StatusIndicator from "@/components/ui/StatusIndicator";
import { AGENTS } from "@/lib/agents";
import { usePipelineStore } from "@/lib/store";

function statusClass(status: string) {
  if (status === "done") return "bg-[#b8e8c6] border-border-dark text-foreground border-4 font-bold shadow-[2px_2px_0px_0px_var(--border-color)]";
  if (status === "active") return "bg-pastel-yellow border-border-dark text-foreground border-4 font-bold shadow-[2px_2px_0px_0px_var(--border-color)]";
  if (status === "error") return "bg-[#ffb3b3] border-border-dark text-foreground border-4 font-bold shadow-[2px_2px_0px_0px_var(--border-color)]";
  return "bg-white border-border-dark text-foreground border-4 font-bold shadow-[2px_2px_0px_0px_var(--border-color)]";
}

export default function Home() {
  const session = usePipelineStore((s) => s.session);
  const statuses = usePipelineStore((s) => s.nodeStatuses);

  return (
    <main className="relative min-h-screen w-full bg-background pb-48">
      <a
        href="#query-input"
        className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 z-[120] rounded-md border-4 border-border-dark bg-white px-3 py-2 text-xs text-foreground shadow-[4px_4px_0px_0px_var(--border-color)] font-bold uppercase tracking-wider"
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
          <p className="text-[12px] uppercase tracking-[0.3em] text-foreground/80 font-black">ARIA Workspace</p>
          <h1 className="mt-1 text-4xl font-black text-foreground tracking-tight uppercase">Practical Research Console</h1>
          <p className="mt-2 max-w-2xl text-base text-foreground font-bold italic">
            Write a prompt, run the pipeline, and read each agent output with quality signals in one place.
          </p>
        </motion.div>

        <div className="grid gap-8 lg:grid-cols-3">
          <article className="retro-card p-6 lg:col-span-1">
            <p className="text-[13px] uppercase tracking-[0.2em] text-foreground/70 font-black border-b-4 border-border-dark/10 pb-2 mb-4">Current Prompt</p>
            <p className="whitespace-pre-wrap text-sm leading-7 text-foreground font-bold">
              {session?.query || "No query yet. Use the prompt box below to start."}
            </p>
            {session?.status === "error" && session.errorMessage ? (
              <div className="mt-6 retro-input bg-[#ffb3b3] p-4 text-xs text-foreground font-black uppercase">
                {session.errorMessage}
              </div>
            ) : null}
          </article>

          <article className="retro-card p-6 lg:col-span-2">
            <div className="flex items-center justify-between gap-2 border-b-4 border-border-dark/10 pb-2 mb-4">
              <p className="text-[13px] uppercase tracking-[0.2em] text-foreground/70 font-black">Agent Progress</p>
              <span className="text-xs text-foreground/70 font-black uppercase tracking-widest">{session?.status || "ready"}</span>
            </div>
            <div className="grid gap-6 md:grid-cols-2">
              {AGENTS.map((agent) => {
                const status = statuses[agent.id] || "idle";
                const content = session?.outputs?.[agent.id]?.content || "";
                return (
                  <div
                    key={agent.id}
                    className={`rounded-2xl px-5 py-4 border-4 shadow-[4px_4px_0px_0px_var(--border-color)] transition-all ${statusClass(status)}`}
                  >
                    <div className="mb-3 flex items-center justify-between gap-2 border-b-4 border-border-dark/10 pb-2">
                      <p className="text-sm font-black uppercase tracking-tight">{agent.codename}</p>
                      <span className="text-[10px] uppercase font-black tracking-widest">{status}</span>
                    </div>
                    <p className="line-clamp-4 text-xs leading-6 text-foreground font-bold italic">
                      {content || "Waiting for output..."}
                    </p>
                  </div>
                );
              })}
            </div>
          </article>
        </div>

        <article className="mt-8 retro-card-peach p-6">
          <div className="flex items-center justify-between gap-2 border-b-4 border-border-dark/10 pb-2 mb-4">
            <p className="text-[13px] uppercase tracking-[0.2em] text-foreground/70 font-black">Final Report</p>
            <span className={`rounded-full px-4 py-1.5 text-[10px] font-black uppercase tracking-widest shadow-[4px_4px_0px_0px_var(--border-color)] ${statusClass(statuses.output || "idle")}`}>
              {statuses.output || "idle"}
            </span>
          </div>
          <div className="mt-4 max-h-[45vh] overflow-auto retro-input p-6">
            <p className="whitespace-pre-wrap text-base leading-8 text-foreground font-bold">
              {session?.finalAnswer || "Final answer will appear here after pipeline completion."}
            </p>
          </div>
          {session?.qualityReport ? (
            <div className="mt-6 grid gap-4 text-xs text-foreground md:grid-cols-3">
              <div className="retro-input p-4 font-black text-center uppercase tracking-wider">
                Score: {session.qualityReport.overallScore.toFixed(1)}
              </div>
              <div className="retro-input p-4 font-black text-center uppercase tracking-wider">
                Sources: {session.qualityReport.metrics.sourceCount}
              </div>
              <div className="retro-input p-4 font-black text-center uppercase tracking-wider">
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
