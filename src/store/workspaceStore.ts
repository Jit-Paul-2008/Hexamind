import { create } from "zustand";
import { projects, type Project } from "@/lib/mock-data";

type WorkspaceState = {
  projects: Project[];
  selectedProjectId: string;
  selectProject: (projectId: string) => void;
};

export const useWorkspaceStore = create<WorkspaceState>((set) => ({
  projects,
  selectedProjectId: projects[0]?.id ?? "",
  selectProject: (selectedProjectId) => set({ selectedProjectId }),
}));
