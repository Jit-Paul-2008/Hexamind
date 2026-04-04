"use client";

import type { RunItem } from "@/lib/mock-data";

type Props = {
  leftRun: RunItem;
  rightRun: RunItem;
};

export default function RunDiff({ leftRun, rightRun }: Props) {
  return (
    <div className="grid gap-3 lg:grid-cols-2">
      <DiffCard title="Run A" run={leftRun} />
      <DiffCard title="Run B" run={rightRun} />
      <div className="rounded-md border border-white/10 bg-white/5 p-3 lg:col-span-2">
        <p className="text-xs uppercase tracking-[0.12em] text-white/45">Delta Summary</p>
        <ul className="mt-2 list-disc space-y-1 pl-4 text-sm text-white/80">
          <li>Trust score delta: {leftRun.quality.trustScore - rightRun.quality.trustScore}</li>
          <li>Overall score delta: {leftRun.quality.overallScore - rightRun.quality.overallScore}</li>
          <li>Contradiction delta: {leftRun.quality.contradictionCount - rightRun.quality.contradictionCount}</li>
        </ul>
      </div>
    </div>
  );
}

function DiffCard({ title, run }: { title: string; run: RunItem }) {
  return (
    <article className="rounded-md border border-white/10 bg-black/20 p-3">
      <p className="text-xs uppercase tracking-[0.12em] text-white/45">{title}</p>
      <p className="mt-1 text-sm text-white/70">{run.id}</p>
      <p className="mt-3 text-sm text-white/85">{run.answer}</p>
    </article>
  );
}
