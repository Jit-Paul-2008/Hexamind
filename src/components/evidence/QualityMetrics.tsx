"use client";

import type { QualityItem } from "@/lib/mock-data";

type Props = {
  quality: QualityItem;
};

export default function QualityMetrics({ quality }: Props) {
  return (
    <div className="grid gap-2 sm:grid-cols-2">
      <MetricCard label="Trust Score" value={quality.trustScore} suffix="/100" />
      <MetricCard label="Overall Score" value={quality.overallScore} suffix="/100" />
      <MetricCard label="Contradictions" value={quality.contradictionCount} />
      <MetricCard label="Sources" value={quality.sourceCount} />
    </div>
  );
}

function MetricCard({ label, value, suffix = "" }: { label: string; value: number; suffix?: string }) {
  return (
    <div className="rounded-md border border-white/10 bg-black/20 p-3">
      <p className="text-[11px] uppercase tracking-[0.12em] text-white/45">{label}</p>
      <p className="mt-1 text-lg font-semibold text-white">
        {value}
        <span className="text-sm text-white/60">{suffix}</span>
      </p>
    </div>
  );
}
