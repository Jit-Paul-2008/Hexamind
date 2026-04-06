"use client";

import React from 'react';

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8 bg-[#F8F9FF] text-[#1A1A1A] font-[family-name:var(--font-space-grotesk)]">
      <div className="max-w-3xl w-full text-center space-y-8 animate-in fade-in duration-700">
        <header className="space-y-4">
          <div className="inline-block px-4 py-1 rounded-full bg-indigo-50 text-indigo-600 text-sm font-semibold tracking-wide border border-indigo-100 uppercase">
            Fresh Start - Phase 1 Complete
          </div>
          <h1 className="text-5xl md:text-7xl font-bold font-[family-name:var(--font-playfair)] text-[#0F172A] tracking-tight">
            Hexamind <span className="text-indigo-600 italic">Research</span> Console
          </h1>
          <p className="text-xl text-slate-600 max-w-2xl mx-auto leading-relaxed">
            Workspace reset and infrastructure stabilized. Ready for the **70B Model Redesign** and advanced multi-agent orchestration.
          </p>
        </header>

        <section className="grid grid-cols-1 md:grid-cols-3 gap-6 text-left">
          <div className="p-6 rounded-2xl bg-white border border-slate-100 shadow-sm transition-all hover:shadow-md hover:border-indigo-200 group">
            <h3 className="font-bold text-lg mb-2 text-[#0F172A] group-hover:text-indigo-600 transition-colors">Backend Ready</h3>
            <p className="text-slate-500 text-sm">FastAPI service stabilized with core model providers and research engines preserved.</p>
          </div>
          <div className="p-6 rounded-2xl bg-white border border-slate-100 shadow-sm transition-all hover:shadow-md hover:border-indigo-200 group">
            <h3 className="font-bold text-lg mb-2 text-[#0F172A] group-hover:text-indigo-600 transition-colors">Clean Frontend</h3>
            <p className="text-slate-500 text-sm">Legacy UI components stripped. Workspace initialized with a lean Next.js boilerplate.</p>
          </div>
          <div className="p-6 rounded-2xl bg-white border border-slate-100 shadow-sm transition-all hover:shadow-md hover:border-indigo-200 group">
            <h3 className="font-bold text-lg mb-2 text-[#0F172A] group-hover:text-indigo-600 transition-colors">Deployment Ready</h3>
            <p className="text-slate-500 text-sm">Render and Docker configurations verified. All environment variables preserved.</p>
          </div>
        </section>

        <footer className="pt-12">
          <div className="text-slate-400 text-sm font-mono flex items-center justify-center space-x-4">
            <span>Status: Operational (70B Redesign)</span>
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
          </div>
        </footer>
      </div>
    </main>
  );
}
