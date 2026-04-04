"use client";

import type { SourceItem } from "@/lib/mock-data";

type Props = {
  sources: SourceItem[];
};

export default function SourcesList({ sources }: Props) {
  if (!sources.length) {
    return <p className="text-sm text-white/55">No sources captured for this run.</p>;
  }

  return (
    <ul className="space-y-2">
      {sources.map((source) => (
        <li key={source.id} className="rounded-md border border-white/10 bg-black/20 p-2">
          <p className="text-xs font-medium text-white">{source.title}</p>
          <a href={source.url} target="_blank" rel="noreferrer" className="text-[11px] text-cyan-300/85 hover:text-cyan-200">
            {source.domain}
          </a>
          <p className="mt-1 text-[11px] text-white/55">Relevance: {Math.round(source.relevance * 100)}%</p>
        </li>
      ))}
    </ul>
  );
}
