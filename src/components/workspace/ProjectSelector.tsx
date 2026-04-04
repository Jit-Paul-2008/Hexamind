"use client";

import { useMemo } from "react";
import type { ChangeEvent } from "react";
import { useRouter } from "next/navigation";
import { useWorkspaceStore } from "@/store/workspaceStore";

export default function ProjectSelector() {
  const router = useRouter();
  const { projects, selectedProjectId, selectProject } = useWorkspaceStore();

  const selected = useMemo(
    () => projects.find((project) => project.id === selectedProjectId),
    [projects, selectedProjectId]
  );

  return (
    <div className="rounded-lg border border-white/10 bg-white/5 p-3">
      <label
        htmlFor="project-selector"
        className="mb-1 block text-[11px] uppercase tracking-[0.16em] text-white/45"
      >
        Project
      </label>
      <select
        id="project-selector"
        value={selectedProjectId}
        onChange={(event: ChangeEvent<HTMLSelectElement>) => {
          const projectId = event.target.value;
          selectProject(projectId);
          router.push(`/workspace/${projectId}`);
        }}
        className="w-full rounded-md border border-white/15 bg-[#0d1119] px-2 py-2 text-sm text-white outline-none"
      >
        {projects.map((project) => (
          <option key={project.id} value={project.id}>
            {project.name}
          </option>
        ))}
      </select>
      <p className="mt-2 text-xs text-white/60">{selected?.description ?? ""}</p>
    </div>
  );
}
