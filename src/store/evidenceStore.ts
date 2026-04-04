import { create } from "zustand";

export type EvidenceTab = "sources" | "quality" | "contradictions";

type EvidenceState = {
  activeTab: EvidenceTab;
  setActiveTab: (tab: EvidenceTab) => void;
};

export const useEvidenceStore = create<EvidenceState>((set) => ({
  activeTab: "sources",
  setActiveTab: (activeTab) => set({ activeTab }),
}));
