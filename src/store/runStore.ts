import { create } from "zustand";
import {
  modeLabels,
  runs as mockRuns,
  type AriaMode,
  type RunItem,
} from "@/lib/mock-data";
import type { PipelineQualityReport } from "@/types/pipeline";

type RunState = {
  runs: RunItem[];
  selectedRunId: string;
  selectedMode: AriaMode;
  selectRun: (runId: string) => void;
  selectMode: (mode: AriaMode) => void;
  getRunsByCase: (caseId: string) => RunItem[];
  createMockRun: (caseId: string, prompt: string) => RunItem;
  addLiveRun: (run: RunItem) => void;
  updateRunQuality: (runId: string, report: PipelineQualityReport) => void;
};

const modeKeys = Object.keys(modeLabels) as AriaMode[];

export const useRunStore = create<RunState>((set, get) => ({
  runs: mockRuns,
  selectedRunId: mockRuns[0]?.id ?? "",
  selectedMode: "deep_research",
  selectRun: (selectedRunId: string) => set({ selectedRunId }),
  selectMode: (selectedMode: AriaMode) => set({ selectedMode }),
  getRunsByCase: (caseId: string) =>
    get()
      .runs.filter((item) => item.caseId === caseId)
      .sort((a, b) =>
        new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
      ),
  createMockRun: (caseId: string, prompt: string) => {
    const currentRuns = get().runs;
    const runNumber = currentRuns.length + 1;
    const mode = get().selectedMode;
    const nextRun: RunItem = {
      id: `run-${String(runNumber).padStart(3, "0")}`,
      caseId,
      mode,
      createdAt: new Date().toISOString(),
      answer: `Mock ${modeLabels[mode]} output generated for: ${prompt}`,
      sources: [
        {
          id: "S1",
          title: "Mock Source Record",
          url: "https://example.com/mock-source",
          domain: "example.com",
          relevance: 0.75,
        },
      ],
      quality: {
        trustScore: 65 + (modeKeys.indexOf(mode) % 5),
        overallScore: 72 + (modeKeys.indexOf(mode) % 5),
        contradictionCount: mode === "scenario_test" ? 2 : 1,
        sourceCount: 1,
      },
      contradictions:
        mode === "scenario_test"
          ? ["Scenario A and Scenario B diverge under low-resource assumptions."]
          : ["Evidence is mixed for impact outside pilot conditions."],
    };

    set({ runs: [nextRun, ...currentRuns], selectedRunId: nextRun.id });
    return nextRun;
  },
  addLiveRun: (run: RunItem) => {
    set((state) => ({
      runs: [run, ...state.runs],
      selectedRunId: run.id,
    }));
  },
  updateRunQuality: (runId: string, report: PipelineQualityReport) => {
    set((state) => ({
      runs: state.runs.map((run) => {
        if (run.id !== runId) {
          return run;
        }
        return {
          ...run,
          quality: {
            trustScore: Math.round(Number(report.trustScore ?? report.overallScore ?? 0)),
            overallScore: Math.round(report.overallScore ?? 0),
            contradictionCount: Number(report.metrics?.contradictionCount ?? 0),
            sourceCount: Number(report.metrics?.sourceCount ?? 0),
          },
          contradictions: (report.contradictionFindings ?? []).map((finding) => finding.reason),
        };
      }),
    }));
  },
}));
