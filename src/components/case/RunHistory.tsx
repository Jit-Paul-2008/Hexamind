"use client";

import { useRunStore } from "@/store/runStore";

type Props = {
  caseId: string;
};

export default function RunHistory({ caseId }: Props) {
  const { getRunsByCase, selectedRunId, selectRun } = useRunStore();
  const runs = getRunsByCase(caseId);

  return (
    <div className="rounded-md border border-white/10 bg-black/20 p-3">
      <p className="mb-2 text-xs uppercase tracking-[0.13em] text-white/55">Run History</p>
      <ul className="space-y-1">
        {runs.map((run) => (
          <li key={run.id}>
            <button
              type="button"
              onClick={() => selectRun(run.id)}
              className={`w-full rounded-md px-2 py-2 text-left text-xs ${
                selectedRunId === run.id
                  ? "bg-white/12 text-white"
                  : "bg-white/5 text-white/65 hover:bg-white/10 hover:text-white"
              }`}
            >
              <span className="block font-medium">{run.id}</span>
              <span className="block text-[11px] opacity-80">
                {new Date(run.createdAt).toLocaleString()}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
