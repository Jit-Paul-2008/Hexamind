"use client";

import React from "react";
import Link from "next/link";

interface WorkspaceLayoutProps {
  projectId: string;
  children: React.ReactNode;
}

export default function WorkspaceLayout({ projectId, children }: WorkspaceLayoutProps) {
  return (
    <div className="flex min-h-screen bg-background text-foreground">
      <aside className="w-56 shrink-0 border-r border-white/10 bg-white/[0.02] p-4 flex flex-col gap-2">
        <p className="text-[10px] uppercase tracking-widest text-white/30 mb-2">Navigation</p>
        <Link
          href={`/workspace/${projectId}`}
          className="rounded px-3 py-2 text-sm text-white/70 hover:bg-white/5 hover:text-white transition"
        >
          Overview
        </Link>
        <Link
          href={`/workspace/${projectId}/compare`}
          className="rounded px-3 py-2 text-sm text-white/70 hover:bg-white/5 hover:text-white transition"
        >
          Compare
        </Link>
        <div className="mt-auto pt-4 border-t border-white/10">
          <Link href="/" className="rounded px-3 py-2 text-xs text-white/30 hover:text-white/60 transition block">
            ← Aurora Console
          </Link>
        </div>
      </aside>
      <main className="flex-1 p-8">{children}</main>
    </div>
  );
}
