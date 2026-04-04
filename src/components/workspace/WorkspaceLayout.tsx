"use client";

import { useEffect } from "react";
import type { ReactNode } from "react";
import { useWorkspaceStore } from "@/store/workspaceStore";
import ProjectSelector from "@/components/workspace/ProjectSelector";
import NavigationTree from "@/components/workspace/NavigationTree";
import EvidencePanel from "@/components/evidence/EvidencePanel";

type Props = {
  projectId: string;
  children: ReactNode;
};

export default function WorkspaceLayout({ projectId, children }: Props) {
  const { selectProject } = useWorkspaceStore();

  useEffect(() => {
    selectProject(projectId);
  }, [projectId, selectProject]);

  return (
    <main className="h-screen w-full bg-[#090d14] text-white">
      <div className="grid h-full grid-cols-12 gap-3 p-3">
        <aside className="col-span-12 flex min-h-0 flex-col gap-3 lg:col-span-3">
          <ProjectSelector />
          <div className="min-h-0 flex-1 overflow-auto">
            <NavigationTree />
          </div>
        </aside>

        <section className="col-span-12 min-h-0 overflow-auto rounded-lg border border-white/10 bg-[#0c1220] p-4 lg:col-span-6">
          {children}
        </section>

        <aside className="col-span-12 min-h-0 overflow-auto rounded-lg border border-white/10 bg-[#0b1322] p-3 lg:col-span-3">
          <EvidencePanel />
        </aside>
      </div>
    </main>
  );
}
