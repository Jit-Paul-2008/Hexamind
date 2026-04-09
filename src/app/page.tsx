"use client";

import React from 'react';
import ResearchConsole from '@/components/ResearchConsole';

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center bg-[#FFFFFF] px-6 md:px-12 py-12">
      {/* Minimal Header */}
      <div className="max-w-6xl w-full mb-16 flex flex-col items-center text-center">
        <h1 className="text-4xl md:text-5xl text-[#1D1D1F] font-semibold mb-2 tracking-tight">
          Hexamind <span className="serif italic font-normal">Aurora</span>
        </h1>
        <p className="text-[11px] tracking-[0.2em] text-[#86868B] uppercase font-bold">
          High-Fidelity Research Pipeline
        </p>
        <div className="mt-6 h-px w-10 bg-[#E5E5E7]"></div>
      </div>

      <div className="max-w-6xl w-full">
        <ResearchConsole />
      </div>

      <footer className="mt-32 pb-16 w-full flex flex-col items-center border-t border-[#F2F2F7] pt-12">
        <div className="flex items-center space-x-6 text-[#86868B] text-[10px] uppercase font-bold tracking-widest">
          <span>Ollama v0.5</span>
          <span className="w-1 h-1 rounded-full bg-[#D2D2D7]"></span>
          <span>2CPU 1.5B-7B Tiered</span>
          <span className="w-1 h-1 rounded-full bg-[#D2D2D7]"></span>
          <span>Stateful Persistence</span>
        </div>
      </footer>
    </main>
  );
}
