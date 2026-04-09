"use client";

import React from 'react';

interface ReasoningGraphProps {
  activeAgent: string | null;
  status: 'idle' | 'researching' | 'completed' | 'error';
}

const STAGES = [
  { id: 'orchestrator', label: 'Orchestrator', icon: '🛰️', color: 'indigo' },
  { id: 'historian', label: 'Historian', icon: '📜', color: 'violet' },
  { id: 'researcher', label: 'Researcher', icon: '📡', color: 'cyan' },
  { id: 'auditor', label: 'Auditor', icon: '�️', color: 'red' },
  { id: 'analyst', label: 'Analyst', icon: '�', color: 'blue' },
  { id: 'synthesizer', label: 'Synthesizer', icon: '✨', color: 'emerald' },
];

export default function ReasoningGraph({ activeAgent, status }: ReasoningGraphProps) {
  return (
    <div className="glass-card p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-bold uppercase tracking-widest text-slate-500">Reasoning Graph</h3>
        <div className="flex space-x-1">
          {[1, 2, 3].map(i => (
            <div key={i} className={`w-1 h-1 rounded-full ${status === 'researching' ? 'bg-indigo-500 animate-bounce' : 'bg-slate-700'}`} style={{ animationDelay: `${i * 0.2}s` }}></div>
          ))}
        </div>
      </div>

      <div className="relative flex flex-col space-y-4">
        {STAGES.map((stage, index) => {
          const isActive = activeAgent === stage.id;
          const isDone = status === 'completed' || (activeAgent && STAGES.findIndex(s => s.id === activeAgent) > index);
          
          return (
            <div key={stage.id} className="relative flex items-center group">
              {/* Connector Line */}
              {index < STAGES.length - 1 && (
                <div className={`absolute left-5 top-10 bottom-0 w-0.5 transition-colors duration-500 ${isDone ? 'bg-emerald-500/50' : 'bg-white/5'}`}></div>
              )}

              {/* Node */}
              <div className={`
                z-10 w-10 h-10 rounded-full flex items-center justify-center text-lg transition-all duration-500 border
                ${isActive ? 'node-active scale-110 pulsar' : ''}
                ${isDone ? 'node-done scale-100' : 'bg-white/5 border-white/10 opacity-40'}
              `}>
                {stage.icon}
              </div>

              {/* Label */}
              <div className="ml-4 flex flex-col">
                <span className={`font-bold transition-colors ${isActive ? 'text-indigo-400' : isDone ? 'text-emerald-400' : 'text-slate-500'}`}>
                  {stage.label}
                </span>
                {isActive && (
                  <span className="text-[10px] text-indigo-500/80 animate-pulse uppercase tracking-tighter">
                    Processing Context...
                  </span>
                )}
              </div>

              {/* Status Glow */}
              {isActive && (
                <div className="absolute -inset-2 bg-indigo-500/10 blur-xl rounded-full -z-10 animate-pulse"></div>
              )}
            </div>
          );
        })}
      </div>

      {status === 'completed' && (
        <div className="pt-4 border-t border-white/10 text-center animate-in fade-in slide-in-from-top-2 duration-700">
          <p className="text-[10px] text-emerald-500 font-mono uppercase tracking-widest">
            Reasoning Cycle Complete (2CPU Tiered)
          </p>
        </div>
      )}
    </div>
  );
}
