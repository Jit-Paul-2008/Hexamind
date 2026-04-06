"use client";

import React from 'react';
import ResearchConsole from '@/components/ResearchConsole';

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center p-4 lg:p-12 overflow-x-hidden">
      {/* Aurora Background Glows */}
      <div className="fixed top-0 left-1/4 w-[500px] h-[500px] bg-indigo-600/10 blur-[120px] rounded-full -z-10 animate-pulse"></div>
      <div className="fixed bottom-0 right-1/4 w-[400px] h-[400px] bg-cyan-600/10 blur-[100px] rounded-full -z-10"></div>

      {/* Global Header */}
      <div className="max-w-6xl w-full mb-12 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-cyan-400 flex items-center justify-center font-bold text-white shadow-lg shadow-indigo-500/20">
            H
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight">Hexamind <span className="text-indigo-400">Aurora</span></h1>
            <p className="text-[10px] text-slate-500 uppercase tracking-widest font-bold">Research Intelligence V4</p>
          </div>
        </div>
        
        <div className="hidden md:flex items-center space-x-6 text-sm">
          <div className="flex items-center space-x-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]"></span>
            <span className="text-slate-400 font-mono text-xs">Ollama: DeepSeek-R1-14B</span>
          </div>
          <div className="px-3 py-1 rounded-full bg-white/5 border border-white/10 text-xs text-slate-400">
            Zero Cost Mode
          </div>
        </div>
      </div>

      <ResearchConsole />

      <footer className="mt-24 pb-12 text-center space-y-4">
        <p className="text-slate-600 text-xs font-medium uppercase tracking-[0.2em]"> Powered by Local Inference & Stateful Reasoning Graphs </p>
        <div className="h-px w-12 bg-indigo-500/20 mx-auto"></div>
      </footer>
    </main>
  );
}
