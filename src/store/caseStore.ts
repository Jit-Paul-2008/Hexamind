import { create } from "zustand";
import { cases, type CaseItem } from "@/lib/mock-data";

type CaseState = {
  cases: CaseItem[];
  selectedCaseId: string;
  selectCase: (caseId: string) => void;
  getCasesByProject: (projectId: string) => CaseItem[];
};

export const useCaseStore = create<CaseState>((set, get) => ({
  cases,
  selectedCaseId: cases[0]?.id ?? "",
  selectCase: (selectedCaseId: string) => set({ selectedCaseId }),
  getCasesByProject: (projectId: string) =>
    get().cases.filter((item) => item.projectId === projectId),
}));
