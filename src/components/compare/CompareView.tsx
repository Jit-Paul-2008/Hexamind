"use client";

import React from "react";
import { cases } from "@/lib/mock-data";
import Link from "next/link";

interface CompareViewProps {
  projectId: string;
}

export default function CompareView({ projectId }: CompareViewProps) {
  const projectCases = cases.filter((c) => c.projectId === projectId);

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <p className="text-xs uppercase tracking-[0.14em] text-white/45">Compare</p>
        <h1 className="text-2xl font-semibold text-white">Case Comparison</h1>
        <p className="text-sm text-white/60">Side-by-side view of research cases in this project.</p>
      </header>

      {projectCases.length === 0 ? (
        <div className="rounded-md border border-white/10 bg-white/5 p-6 text-sm text-white/40 italic">
          No cases found for this project.
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {projectCases.map((caseItem) => (
            <Link
              key={caseItem.id}
              href={`/workspace/${projectId}/case/${caseItem.id}`}
              className="rounded-md border border-white/10 bg-white/5 p-4 transition hover:bg-white/10"
            >
              <p className="text-sm font-medium text-white">{caseItem.title}</p>
              <p className="mt-1 text-xs text-white/60">{caseItem.question}</p>
            </Link>
          ))}
        </div>
      )}

      <Link
        href="/"
        className="inline-block text-xs text-white/30 hover:text-white/60 transition"
      >
        ← Back to Aurora Console
      </Link>
    </div>
  );
}
