"use client";

import Link from "next/link";
import { useMemo } from "react";
import { usePathname } from "next/navigation";
import { useWorkspaceStore } from "@/store/workspaceStore";
import { useCaseStore } from "@/store/caseStore";
import { useRunStore } from "@/store/runStore";

export default function NavigationTree() {
  const pathname = usePathname();
  const { selectedProjectId } = useWorkspaceStore();
  const { getCasesByProject, selectCase } = useCaseStore();
  const { getRunsByCase, selectRun } = useRunStore();

  const projectCases = useMemo(
    () => getCasesByProject(selectedProjectId),
    [getCasesByProject, selectedProjectId]
  );

  return (
    <nav className="rounded-lg border border-white/10 bg-white/5 p-3">
      <p className="mb-2 text-[11px] uppercase tracking-[0.18em] text-white/45">Cases</p>
      <ul className="space-y-2">
        {projectCases.map((caseItem) => {
          const caseActive = pathname.includes(`/case/${caseItem.id}`);
          const runs = getRunsByCase(caseItem.id).slice(0, 3);
          return (
            <li key={caseItem.id} className="rounded-md border border-white/10 bg-black/20 p-2">
              <Link
                href={`/workspace/${selectedProjectId}/case/${caseItem.id}`}
                onClick={() => selectCase(caseItem.id)}
                className={`block text-sm ${caseActive ? "text-white" : "text-white/70"}`}
              >
                {caseItem.title}
              </Link>
              <ul className="mt-2 space-y-1">
                {runs.map((run) => (
                  <li key={run.id}>
                    <button
                      type="button"
                      onClick={() => selectRun(run.id)}
                      className="w-full rounded px-2 py-1 text-left text-xs text-white/55 hover:bg-white/5 hover:text-white/80"
                    >
                      {new Date(run.createdAt).toLocaleDateString()} · {run.id}
                    </button>
                  </li>
                ))}
              </ul>
            </li>
          );
        })}
      </ul>

      <Link
        href={`/workspace/${selectedProjectId}/compare`}
        className="mt-3 inline-flex rounded-md border border-white/20 px-2 py-1 text-xs text-white/80 hover:bg-white/10"
      >
        Compare Runs
      </Link>
    </nav>
  );
}
