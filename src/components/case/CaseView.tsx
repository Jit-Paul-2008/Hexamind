"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { ChangeEvent } from "react";
import { useCaseStore } from "@/store/caseStore";
import { useRunStore } from "@/store/runStore";
import { modeLabels } from "@/lib/mock-data";
import { usePipeline } from "@/hooks/usePipeline";
import { exportDocx } from "@/lib/api/export";
import type { ReportLength } from "@/lib/pipelineClient";
import ModeSelector from "@/components/case/ModeSelector";
import RunHistory from "@/components/case/RunHistory";

type Props = {
  caseId: string;
};

export default function CaseView({ caseId }: Props) {
  const [prompt, setPrompt] = useState("");
  const [reportLength, setReportLength] = useState<ReportLength>("moderate");
  const { cases } = useCaseStore();
  const {
    selectedRunId,
    selectedMode,
    getRunsByCase,
    createMockRun,
    addLiveRun,
    updateRunQuality,
  } = useRunStore();
  const { run, sessionId, isRunning, finalAnswer, liveOutput, qualityReport, error } =
    usePipeline();
  const createdFromSessionRef = useRef<string>("");

  const currentCase = useMemo(
    () => cases.find((item) => item.id === caseId),
    [caseId, cases]
  );

  const runs = getRunsByCase(caseId);
  const selectedRun = runs.find((run) => run.id === selectedRunId) ?? runs[0];

  useEffect(() => {
    if (!sessionId || !finalAnswer.trim()) {
      return;
    }
    if (createdFromSessionRef.current === sessionId) {
      return;
    }

    const liveRunId = `live-${sessionId.slice(-8)}`;
    addLiveRun({
      id: liveRunId,
      backendSessionId: sessionId,
      caseId,
      mode: selectedMode,
      createdAt: new Date().toISOString(),
      answer: finalAnswer,
      sources: [],
      quality: {
        trustScore: 0,
        overallScore: 0,
        contradictionCount: 0,
        sourceCount: 0,
      },
      contradictions: [],
    });
    createdFromSessionRef.current = sessionId;
  }, [addLiveRun, caseId, finalAnswer, selectedMode, sessionId]);

  useEffect(() => {
    if (!qualityReport || !sessionId) {
      return;
    }
    const liveRunId = `live-${sessionId.slice(-8)}`;
    updateRunQuality(liveRunId, qualityReport);
  }, [qualityReport, sessionId, updateRunQuality]);

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
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <span className="text-[11px] uppercase tracking-[0.12em] text-white/50">Report length</span>
            {(["brief", "moderate", "huge"] as ReportLength[]).map((lengthMode) => {
              const active = reportLength === lengthMode;
              return (
                <button
                  key={lengthMode}
                  type="button"
                  onClick={() => setReportLength(lengthMode)}
                  className={`rounded-md border px-2.5 py-1 text-[11px] uppercase tracking-[0.08em] transition ${
                    active
                      ? "border-cyan-300/60 bg-cyan-300/20 text-cyan-100"
                      : "border-white/20 bg-white/5 text-white/70 hover:bg-white/10"
                  }`}
                >
                  {lengthMode}
                </button>
              );
            })}
          </div>
          <button
            type="button"
            onClick={async () => {
              const activePrompt = prompt || currentCase?.question || "Untitled";
              try {
                await run(activePrompt, reportLength);
              } catch {
                createMockRun(caseId, activePrompt);
              }
            }}
            className="mt-2 rounded-md border border-emerald-300/40 bg-emerald-300/15 px-3 py-2 text-xs uppercase tracking-[0.12em] text-emerald-100 hover:bg-emerald-300/20"
          >
            {isRunning ? "Running..." : `Run ARIA (${modeLabels[selectedMode]})`}
          </button>
          {sessionId && (
            <button
              type="button"
              onClick={async () => {
                const doc = await exportDocx(sessionId, {
                  targetLanguageCode: "en-IN",
                  instruction: "keep concise and structured",
                });
                const url = URL.createObjectURL(doc.blob);
                const anchor = document.createElement("a");
                anchor.href = url;
                anchor.download = doc.filename;
                anchor.click();
                URL.revokeObjectURL(url);
              }}
              className="ml-2 mt-2 rounded-md border border-white/30 bg-white/10 px-3 py-2 text-xs uppercase tracking-[0.12em] text-white/80 hover:bg-white/20"
            >
              Export DOCX
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="rounded-md border border-red-300/30 bg-red-300/10 px-3 py-2 text-xs text-red-100">
          {error}
        </div>
      )}

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
                {isRunning && liveOutput ? liveOutput : selectedRun.answer}
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
