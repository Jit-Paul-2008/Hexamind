"use client";

import { useMemo } from "react";
import { useRunStore } from "@/store/runStore";
import { useEvidenceStore, type EvidenceTab } from "@/store/evidenceStore";
import SourcesList from "@/components/evidence/SourcesList";
import QualityMetrics from "@/components/evidence/QualityMetrics";
import ContradictionView from "@/components/evidence/ContradictionView";

const tabs: { key: EvidenceTab; label: string }[] = [
  { key: "sources", label: "Sources" },
  { key: "quality", label: "Quality" },
  { key: "contradictions", label: "Contradictions" },
];

export default function EvidencePanel() {
  const { runs, selectedRunId } = useRunStore();
  const { activeTab, setActiveTab } = useEvidenceStore();

  const run = useMemo(
    () => runs.find((item) => item.id === selectedRunId) ?? runs[0],
    [runs, selectedRunId]
  );

  return (
    <section className="h-full">
      <p className="mb-3 text-xs uppercase tracking-[0.15em] text-white/45">Evidence</p>
      <div className="mb-3 flex flex-wrap gap-2">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setActiveTab(tab.key)}
            className={`rounded-md border px-2 py-1 text-xs ${
              activeTab === tab.key
                ? "border-white/40 bg-white/15 text-white"
                : "border-white/15 bg-white/5 text-white/60"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="min-h-[180px] rounded-md border border-white/10 bg-black/20 p-2">
        {!run && <p className="text-sm text-white/60">No selected run.</p>}
        {run && activeTab === "sources" && <SourcesList sources={run.sources} />}
        {run && activeTab === "quality" && <QualityMetrics quality={run.quality} />}
        {run && activeTab === "contradictions" && <ContradictionView items={run.contradictions} />}
      </div>
    </section>
  );
}
