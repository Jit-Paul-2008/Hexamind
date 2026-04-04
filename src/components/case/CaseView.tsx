"use client";

import { useMemo, useState } from "react";
import type { ChangeEvent } from "react";
import { useCaseStore } from "@/store/caseStore";
import { useRunStore } from "@/store/runStore";
import ModeSelector from "@/components/case/ModeSelector";
import RunHistory from "@/components/case/RunHistory";

type Props = {
  caseId: string;
};

export default function CaseView({ caseId }: Props) {
  const [prompt, setPrompt] = useState("");
  const { cases } = useCaseStore();
  const { selectedRunId, getRunsByCase, createMockRun } = useRunStore();

  const currentCase = useMemo(
    () => cases.find((item) => item.id === caseId),
    [caseId, cases]
  );

  const runs = getRunsByCase(caseId);
  const selectedRun = runs.find((run) => run.id === selectedRunId) ?? runs[0];

  return (
    <div className="flex h-full flex-col gap-4">
      <div>
        <p className="text-xs uppercase tracking-[0.15em] text-white/45">Case</p>
        <h1 className="mt-1 text-2xl font-semibold text-white">{currentCase?.title ?? "Unknown Case"}</h1>
        <p className="mt-2 text-sm text-white/70">{currentCase?.question}</p>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <ModeSelector />
        <div className="rounded-md border border-white/10 bg-white/5 p-3">
          <label htmlFor="case-prompt" className="mb-1 block text-xs text-white/60">
            Prompt
          </label>
          <textarea
            id="case-prompt"
            value={prompt}
            onChange={(event: ChangeEvent<HTMLTextAreaElement>) =>
              setPrompt(event.target.value)
            }
            rows={3}
            className="w-full rounded-md border border-white/20 bg-[#0d1119] px-2 py-2 text-sm"
            placeholder="Ask ARIA to run a focused analysis..."
          />
          <button
            type="button"
            onClick={() => createMockRun(caseId, prompt || currentCase?.question || "Untitled")}
            className="mt-2 rounded-md border border-emerald-300/40 bg-emerald-300/15 px-3 py-2 text-xs uppercase tracking-[0.12em] text-emerald-100 hover:bg-emerald-300/20"
          >
            Run ARIA
          </button>
        </div>
      </div>

      <div className="grid min-h-0 flex-1 gap-3 lg:grid-cols-3">
        <div className="lg:col-span-1">
          <RunHistory caseId={caseId} />
        </div>
        <article className="min-h-0 overflow-auto rounded-md border border-white/10 bg-white/5 p-3 lg:col-span-2">
          <p className="mb-2 text-xs uppercase tracking-[0.12em] text-white/45">Latest Output</p>
          {selectedRun ? (
            <>
              <p className="mb-3 text-xs text-white/55">
                {selectedRun.id} · {new Date(selectedRun.createdAt).toLocaleString()}
              </p>
              <p className="whitespace-pre-wrap text-sm leading-6 text-white/85">
                {selectedRun.answer}
              </p>
            </>
          ) : (
            <p className="text-sm text-white/60">No runs yet.</p>
          )}
        </article>
      </div>
    </div>
  );
}
