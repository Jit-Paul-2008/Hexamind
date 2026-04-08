"use client";

import React, { useState, useEffect, useRef, useMemo } from 'react';
import { PipelineEvent, PipelineEventType } from '@/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

// List of available agents in the Aurora pipeline
const AURORA_AGENTS = [
  { id: 'orchestrator', name: 'Orchestrator' },
  { id: 'historian', name: 'Historian' },
  { id: 'researcher', name: 'Researcher' },
  { id: 'critic', name: 'Critic' },
  { id: 'advocate', name: 'Advocate' },
  { id: 'skeptic', name: 'Skeptic' },
  { id: 'synthesiser', name: 'Synthesiser' },
  { id: 'oracle', name: 'Oracle' },
  { id: 'verifier', name: 'Verifier' },
  { id: 'auditor', name: 'Auditor' },
  { id: 'analyst', name: 'Analyst' },
];

export default function ResearchConsole() {
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState<'idle' | 'researching' | 'completed' | 'error'>('idle');
  const [activeAgentId, setActiveAgentId] = useState<string | null>(null);
  const [agentLogs, setAgentLogs] = useState<Record<string, string[]>>({});
  const [finalReport, setFinalReport] = useState<string>('');
  const [error, setError] = useState<string | null>(null);

  // Auto-scroll logic for terminal streams
  const logRefs = useRef<Record<string, HTMLDivElement | null>>({});

  useEffect(() => {
    Object.values(logRefs.current).forEach(ref => {
      if (ref) ref.scrollTop = ref.scrollHeight;
    });
  }, [agentLogs]);

  const startResearch = async () => {
    if (!query.trim()) return;

    // Reset local state
    setAgentLogs({});
    setFinalReport('');
    setError(null);
    setStatus('researching');
    setActiveAgentId('orchestrator');

    try {
      const startRes = await fetch(`${API_BASE}/api/pipeline/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, agaMode: false, mathMode: false }),
      });

      if (!startRes.ok) throw new Error(`Failed to start pipeline: ${startRes.statusText}`);
      const { sessionId } = await startRes.json();

      const eventSource = new EventSource(`${API_BASE}/api/pipeline/${sessionId}/stream`);

      eventSource.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data);
          const data = JSON.parse(parsed.data) as PipelineEvent;
          const agentId = data.agentId || 'orchestrator';

          if (parsed.event === PipelineEventType.AGENT_START) {
            setActiveAgentId(agentId);
          }

          const content = data.chunk || data.fullContent || '';
          if (content) {
            setAgentLogs(prev => ({
              ...prev,
              [agentId]: [...(prev[agentId] || []), content.trim()]
            }));
          }

          if (parsed.event === PipelineEventType.PIPELINE_DONE) {
            setFinalReport(data.fullContent || '');
            setStatus('completed');
            setActiveAgentId(null);
            eventSource.close();
          }

          if (parsed.event === PipelineEventType.PIPELINE_ERROR) {
            setError(data.error || 'Research interrupted.');
            setStatus('error');
            setActiveAgentId(null);
            eventSource.close();
          }
        } catch (err) {
          console.error('SSE Error:', err);
        }
      };

      eventSource.onerror = () => {
        setError("Connection lost, but local inference may still be active.");
        setStatus('error');
        eventSource.close();
      };
    } catch (err: any) {
      setError(err.message);
      setStatus('error');
    }
  };

  const [activeTab, setActiveTab] = useState<'research' | 'technical'>('research');

  return (
    <div className="w-full flex flex-col space-y-12 animate-in fade-in duration-500">
      {/* 1. Search Bar */}
      <div className="w-full flex justify-center">
        <div className="relative w-full max-w-3xl">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && startResearch()}
            placeholder="Describe your research inquiry..."
            disabled={status === 'researching'}
            className="mac-input w-full py-4 px-6 text-lg outline-none font-medium placeholder:font-light"
          />
          <div className="absolute right-3 top-1/2 -translate-y-1/2">
            {status === 'researching' ? (
              <div className="busy-indicator"></div>
            ) : (
              <button 
                onClick={startResearch}
                disabled={!query.trim()}
                className="bg-[#1D1D1F] text-white text-[12px] font-bold px-4 py-2 rounded-lg hover:opacity-90 disabled:opacity-30 transition-all uppercase tracking-wider"
              >
                Start
              </button>
            )}
          </div>
        </div>
      </div>

      {/* 2. Flow Visualization */}
      <div className="w-full py-4 px-2 overflow-x-auto">
        <div className="min-w-[800px] flex items-center justify-between px-10 relative">
           {/* Background connecting line */}
           <div className="absolute top-1/2 left-20 right-20 h-[0.5px] bg-[#E5E5E7] -z-10"></div>
           
           {AURORA_AGENTS.map((agent, i) => {
             const isActive = activeAgentId === agent.id;
             const isDone = !!agentLogs[agent.id] && !isActive && status !== 'idle';
             return (
               <div key={agent.id} className="flex flex-col items-center space-y-2">
                 <div className={`w-3 h-3 rounded-full border border-white transition-all duration-500 shadow-sm ${
                   isActive ? 'bg-[#0066CC] scale-125 pulsing-node shadow-[0_0_10px_rgba(0,102,204,0.4)]' : 
                   isDone ? 'bg-[#34C759]' : 'bg-[#D2D2D7]'
                 }`}></div>
                 <span className={`text-[9px] uppercase font-bold tracking-widest ${isActive ? 'text-[#1D1D1F]' : 'text-[#86868B]'}`}>
                   {agent.name.slice(0, 3)}
                 </span>
               </div>
             );
           })}
        </div>
      </div>

      {/* 3. Agent Mission Control (Horizontal Scroller for 'Keep Clean' look) */}
      <div className="w-full flex space-x-4 overflow-x-auto pb-6 px-2 scrollbar-thin">
        {AURORA_AGENTS.map((agent) => {
          const isActive = activeAgentId === agent.id;
          const logs = agentLogs[agent.id] || [];
          return (
            <div 
              key={agent.id} 
              className={`agent-card min-w-[180px] max-w-[180px] p-3 h-32 flex flex-col shrink-0 ${isActive ? 'agent-card-active' : ''}`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className={`text-[9px] font-black uppercase tracking-widest ${isActive ? 'text-[#0066CC]' : 'text-[#86868B]'}`}>
                  {agent.name}
                </span>
                {isActive && <div className="busy-indicator !m-0 !w-1.5 !h-1.5"></div>}
              </div>
              <div 
                ref={el => { logRefs.current[agent.id] = el; }}
                className="terminal-stream flex-1 scrollbar-hide text-[9px]"
              >
                {logs.length > 0 ? (
                  logs.slice(-5).map((line, idx) => (
                    <div key={idx} className="mb-0.5 border-l border-[#E5E5E7] pl-1.5 ml-0.5">• {line}</div>
                  ))
                ) : (
                  <div className="opacity-10 italic">idle_state</div>
                )}
                {isActive && <div className="animate-pulse pl-1.5 ml-0.5">_</div>}
              </div>
            </div>
          );
        })}
      </div>

      {/* 4. Output / Execution Status */}
      <div className="border-t border-[#F2F2F7] pt-12">
        {status === 'idle' && (
          <div className="py-20 flex flex-col items-center opacity-10">
            <h2 className="serif text-5xl mb-4 italic">Waiting to synthesize...</h2>
            <div className="h-0.5 w-12 bg-[#1D1D1F]"></div>
          </div>
        )}

        {error && (
          <div className="max-w-2xl mx-auto p-4 bg-[#FEFBFA] border border-[#F5E8E2] rounded-xl text-[#B3261E] text-sm font-medium">
             ⚠️ {error}
          </div>
        )}

        {finalReport && (
          <div className="animate-in fade-in slide-in-from-top-6 duration-1000 max-w-2xl mx-auto">
            {/* Tabbed Switcher (macOS style) */}
            {finalReport.includes('## Technical report') && (
              <div className="flex justify-center mb-10">
                <div className="bg-[#F2F2F7] p-1 rounded-lg flex space-x-1">
                  <button 
                    onClick={() => setActiveTab('research')}
                    className={`px-4 py-1.5 text-[12px] font-bold rounded-md transition-all ${activeTab === 'research' ? 'bg-white shadow-sm text-[#1D1D1F]' : 'text-[#86868B] hover:text-[#1D1D1F]'}`}
                  >
                    Research Report
                  </button>
                  <button 
                    onClick={() => setActiveTab('technical')}
                    className={`px-4 py-1.5 text-[12px] font-bold rounded-md transition-all ${activeTab === 'technical' ? 'bg-white shadow-sm text-[#1D1D1F]' : 'text-[#86868B] hover:text-[#1D1D1F]'}`}
                  >
                    Technical Assessment
                  </button>
                </div>
              </div>
            )}

            <article className="space-y-8">
              <div className="flex items-center space-x-4 mb-4">
                <span className="text-[10px] font-black uppercase tracking-[0.3em] text-[#34C759] border border-[#34C759] px-2 py-0.5 rounded">
                  {activeTab === 'research' ? 'Synthesis Output' : 'Technical Analysis'}
                </span>
                <div className="h-px flex-1 bg-[#F2F2F7]"></div>
              </div>

              {(() => {
                const parts = finalReport.split(/## (?:Technical report|Report on Topic)/i);
                let content = finalReport;
                
                if (parts.length >= 3) {
                  // Index 1 is technical, index 2 is research
                  content = activeTab === 'technical' ? parts[1] : parts[2];
                }

                return (
                  <div className={`leading-relaxed text-[#1D1D1F] whitespace-pre-wrap ${activeTab === 'research' ? 'serif text-lg md:text-xl first-letter:text-6xl first-letter:float-left first-letter:mr-4 first-letter:font-black' : 'font-mono text-[13px] text-[#424245]'}`}>
                    {content.trim()}
                  </div>
                );
              })()}
            </article>
          </div>
        )}
      </div>
    </div>
  );
}
