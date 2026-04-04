import { create } from "zustand";
import {
  modeLabels,
  runs as mockRuns,
  type AriaMode,
  type RunItem,
} from "@/lib/mock-data";

type RunState = {
  runs: RunItem[];
  selectedRunId: string;
  selectedMode: AriaMode;
  selectRun: (runId: string) => void;
  selectMode: (mode: AriaMode) => void;
  getRunsByCase: (caseId: string) => RunItem[];
  createMockRun: (caseId: string, prompt: string) => RunItem;
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
}));
