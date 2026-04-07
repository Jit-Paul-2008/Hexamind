"use client";

import React from "react";
import { cases } from "@/lib/mock-data";
import Link from "next/link";

interface CaseViewProps {
  caseId: string;
}

export default function CaseView({ caseId }: CaseViewProps) {
  const caseItem = cases.find((c) => c.id === caseId);

  if (!caseItem) {
    return (
      <div className="flex h-full items-center justify-center text-white/40">
        <p>Case not found.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <p className="text-xs uppercase tracking-[0.14em] text-white/45">Case</p>
        <h1 className="text-2xl font-semibold text-white">{caseItem.title}</h1>
        <p className="text-sm text-white/60">{caseItem.question}</p>
      </header>

      <div className="rounded-md border border-white/10 bg-white/5 p-6">
        <p className="text-sm text-white/50 italic">
          Open the Aurora console to run a research pipeline for this case.
        </p>
        <Link
          href="/"
          className="mt-4 inline-block rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500 transition"
        >
          Go to Aurora Console
        </Link>
      </div>
    </div>
  );
}
