"use client";

import { useMemo, useState } from "react";
import type { ChangeEvent } from "react";
import { useCaseStore } from "@/store/caseStore";
import { useRunStore } from "@/store/runStore";
import RunDiff from "@/components/compare/RunDiff";

type Props = {
  projectId: string;
};

export default function CompareView({ projectId }: Props) {
  const { getCasesByProject } = useCaseStore();
  const { getRunsByCase } = useRunStore();

  const projectCases = getCasesByProject(projectId);
  const defaultCaseId = projectCases[0]?.id ?? "";
  const [caseId, setCaseId] = useState(defaultCaseId);

  const caseRuns = useMemo(() => getRunsByCase(caseId), [caseId, getRunsByCase]);
  const [leftRunId, setLeftRunId] = useState(caseRuns[0]?.id ?? "");
  const [rightRunId, setRightRunId] = useState(caseRuns[1]?.id ?? caseRuns[0]?.id ?? "");

  const leftRun = caseRuns.find((item) => item.id === leftRunId) ?? caseRuns[0];
  const rightRun = caseRuns.find((item) => item.id === rightRunId) ?? caseRuns[1] ?? caseRuns[0];

  return (
    <div className="flex h-full flex-col gap-4">
      <header>
        <p className="text-xs uppercase tracking-[0.12em] text-white/45">Comparison</p>
        <h1 className="text-2xl font-semibold">Run Compare</h1>
      </header>

      <div className="grid gap-3 md:grid-cols-3">
        <select
          value={caseId}
          onChange={(event: ChangeEvent<HTMLSelectElement>) => {
            const nextCaseId = event.target.value;
            const nextRuns = getRunsByCase(nextCaseId);
            setCaseId(nextCaseId);
            setLeftRunId(nextRuns[0]?.id ?? "");
            setRightRunId(nextRuns[1]?.id ?? nextRuns[0]?.id ?? "");
          }}
          className="rounded-md border border-white/20 bg-[#0d1119] px-2 py-2 text-sm"
        >
          {projectCases.map((item) => (
            <option key={item.id} value={item.id}>
              {item.title}
            </option>
          ))}
        </select>

        <select
          value={leftRunId}
          onChange={(event: ChangeEvent<HTMLSelectElement>) =>
            setLeftRunId(event.target.value)
          }
          className="rounded-md border border-white/20 bg-[#0d1119] px-2 py-2 text-sm"
        >
          {caseRuns.map((run) => (
            <option key={run.id} value={run.id}>
              {run.id}
            </option>
          ))}
        </select>

        <select
          value={rightRunId}
          onChange={(event: ChangeEvent<HTMLSelectElement>) =>
            setRightRunId(event.target.value)
          }
          className="rounded-md border border-white/20 bg-[#0d1119] px-2 py-2 text-sm"
        >
          {caseRuns.map((run) => (
            <option key={run.id} value={run.id}>
              {run.id}
            </option>
          ))}
        </select>
      </div>

      {leftRun && rightRun ? (
        <RunDiff leftRun={leftRun} rightRun={rightRun} />
      ) : (
        <p className="text-sm text-white/65">Need at least one run to compare.</p>
      )}
    </div>
  );
}
