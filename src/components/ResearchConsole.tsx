"use client";

import React, { useState, useEffect, useRef } from 'react';
import { PipelineEvent, PipelineEventType, TaxonomyNode } from '@/types';
import ReportPlanner from './ReportPlanner';

interface RuntimeConfig {
  apiUrl?: string;
}

interface AgentDescriptor {
  id: string;
  name: string;
}

interface QualityReport {
  status?: 'pending' | 'ready';
  overallScore?: number;
  deliveryMode?: string;
  notes?: string[];
  metrics?: {
    sourceCount?: number;
    stepsTaken?: number;
    citationCount?: number;
    uniqueDomains?: number;
    averageCredibility?: number;
  };
}

const toErrorMessage = (error: unknown): string => {
  if (error instanceof Error) {
    return error.message;
  }
  return String(error);
};

// List of available agents in the Aurora pipeline
// List of core agents in the Aurora Diamond pipeline
const INITIAL_AGENTS = [
  { id: 'orchestrator', name: 'Orchestrator' },
  { id: 'historian', name: 'Historian' },
  { id: 'researcher', name: 'Researcher' },
  { id: 'auditor', name: 'Auditor' },
  { id: 'analyst', name: 'Analyst' },
  { id: 'synthesiser', name: 'Synthesiser' },
];

export default function ResearchConsole() {
  const [apiBase, setApiBase] = useState(process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000');
  const [query, setQuery] = useState('');
  const [agents, setAgents] = useState(INITIAL_AGENTS);
  const [activeTab, setActiveTab] = useState<'research' | 'technical'>('research');
  
  // Dynamic API discovery for public users
  useEffect(() => {
    const discoverApi = async () => {
      try {
        // 1. Discover API Endpoint from canonical path, then legacy fallback.
        const configPaths = ['/Hexamind/config.json', '/config.json'];
        let discoveredApi: string | null = null;
        for (const path of configPaths) {
          const configRes = await fetch(path);
          if (!configRes.ok) {
            continue;
          }
          const cfg = (await configRes.json()) as RuntimeConfig;
          if (cfg.apiUrl) {
            console.log("🛰️ Aurora API Discovered:", cfg.apiUrl, `(${path})`);
            discoveredApi = cfg.apiUrl;
            break;
          }
        }
        if (discoveredApi) {
          setApiBase(discoveredApi);
        }
        
        // 2. Discover Agent Roles (Singular Source of Truth)
        const agentRes = await fetch('/Hexamind/agents.json');
        if (agentRes.ok) {
          const agentData = (await agentRes.json()) as AgentDescriptor[];
          setAgents(agentData.map((a) => ({ id: a.id, name: a.name })));
        }
      } catch (e) {
        console.warn("Discovery failed, using defaults:", e);
      }
    };
    discoverApi();
  }, []);
  const [status, setStatus] = useState<'idle' | 'planning' | 'researching' | 'completed' | 'error'>('idle');
  const [activeAgentId, setActiveAgentId] = useState<string | null>(null);
  const [agentLogs, setAgentLogs] = useState<Record<string, string[]>>({});
  const [finalReport, setFinalReport] = useState<string>('');
  const [technicalReport, setTechnicalReport] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [proposedTaxonomy, setProposedTaxonomy] = useState<TaxonomyNode[] | null>(null);

  // Auto-scroll logic for terminal streams
  const logRefs = useRef<Record<string, HTMLDivElement | null>>({});

  useEffect(() => {
    Object.values(logRefs.current).forEach(ref => {
      if (ref) ref.scrollTop = ref.scrollHeight;
    });
  }, [agentLogs]);

  const apiUrl = (path: string): string => {
    const base = apiBase.trim().replace(/\/$/, '');
    if (!base) {
      return path;
    }
    return `${base}${path}`;
  };

  const buildTechnicalReport = (quality: QualityReport | null, logs: Record<string, string[]>, currentSessionId: string | null): string => {
    const lines: string[] = [];
    lines.push('### Technical Output');
    lines.push('');
    lines.push(`- Session: ${currentSessionId || 'n/a'}`);
    lines.push(`- Backend: ${apiBase}`);
    lines.push(`- Quality Status: ${quality?.status || 'pending'}`);
    if (typeof quality?.overallScore === 'number') {
      lines.push(`- Confidence Score: ${quality.overallScore.toFixed(1)}`);
    }
    if (quality?.deliveryMode) {
      lines.push(`- Delivery Mode: ${quality.deliveryMode}`);
    }
    lines.push('');
    lines.push('### Metrics');
    lines.push(`- Sources: ${quality?.metrics?.sourceCount ?? 0}`);
    lines.push(`- Steps: ${quality?.metrics?.stepsTaken ?? 0}`);
    if (typeof quality?.metrics?.citationCount === 'number') {
      lines.push(`- Citations: ${quality.metrics.citationCount}`);
    }
    if (typeof quality?.metrics?.uniqueDomains === 'number') {
      lines.push(`- Domains: ${quality.metrics.uniqueDomains}`);
    }
    if (typeof quality?.metrics?.averageCredibility === 'number') {
      lines.push(`- Avg Credibility: ${quality.metrics.averageCredibility.toFixed(2)}`);
    }
    lines.push('');
    if (quality?.notes?.length) {
      lines.push('### Quality Notes');
      for (const note of quality.notes) {
        lines.push(`- ${note}`);
      }
      lines.push('');
    }
    lines.push('### Agent Execution Logs');
    for (const agent of agents) {
      const agentLines = logs[agent.id] || [];
      lines.push(`- ${agent.name}: ${agentLines.length} updates`);
    }
    return lines.join('\n');
  };

  const proposePlan = async () => {
    if (!query.trim()) return;
    setStatus('planning');
    setError(null);
    setProposedTaxonomy(null);

    try {
      const res = await fetch(apiUrl('/api/pipeline/propose'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      });
      if (!res.ok) throw new Error('Failed to generate research plan.');
      const data = await res.json();
      setProposedTaxonomy(data.taxonomy);
    } catch (err: unknown) {
      setError(toErrorMessage(err));
      setStatus('error');
    }
  };

  const startResearch = async (customTaxonomy?: TaxonomyNode[]) => {
    if (!query.trim()) return;

    // Reset local state
    setAgentLogs({});
    setFinalReport('');
    setTechnicalReport('');
    setError(null);
    setStatus('researching');
    setActiveAgentId('orchestrator');
    setActiveTab('research');

    try {
      const startRes = await fetch(apiUrl('/api/pipeline/start'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          query, 
          agaMode: false, 
          mathMode: false,
          taxonomy: customTaxonomy
        }),
      });

      if (!startRes.ok) throw new Error(`Failed to start pipeline: ${startRes.statusText}`);
      const { sessionId: createdSessionId } = await startRes.json();

      let runtimeLogs: Record<string, string[]> = {};

      const eventSource = new EventSource(apiUrl(`/api/pipeline/${createdSessionId}/stream`));

      eventSource.onmessage = async (event) => {
        try {
          const data = JSON.parse(event.data) as PipelineEvent;
          const eventType = data.type;
          const agentId = data.agentId || 'orchestrator';

          if (eventType === PipelineEventType.AGENT_START) {
            setActiveAgentId(agentId);
          }

          const content = data.chunk || data.fullContent || '';
          if (content) {
            runtimeLogs = {
              ...runtimeLogs,
              [agentId]: [...(runtimeLogs[agentId] || []), content.trim()]
            };
            setAgentLogs(prev => ({
              ...prev,
              [agentId]: [...(prev[agentId] || []), content.trim()]
            }));
          }

          if (eventType === PipelineEventType.PIPELINE_DONE) {
            setFinalReport(data.fullContent || '');
            try {
              const qualityRes = await fetch(apiUrl(`/api/pipeline/${createdSessionId}/quality`));
              if (qualityRes.ok) {
                const quality = (await qualityRes.json()) as QualityReport;
                  setTechnicalReport(buildTechnicalReport(quality, runtimeLogs, createdSessionId));
              } else {
                  setTechnicalReport(buildTechnicalReport(null, runtimeLogs, createdSessionId));
              }
            } catch {
                setTechnicalReport(buildTechnicalReport(null, runtimeLogs, createdSessionId));
            }
            setStatus('completed');
            setActiveAgentId(null);
            eventSource.close();
          }

          if (eventType === PipelineEventType.PIPELINE_ERROR || eventType === PipelineEventType.ERROR) {
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
    } catch (err: unknown) {
      setError(toErrorMessage(err));
      setStatus('error');
    }
  };

  return (
    <div className="w-full flex flex-col space-y-12 animate-in fade-in duration-500">
      {/* 1. Search Bar */}
      <div className="w-full flex justify-center">
        <div className="relative w-full max-w-3xl">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && proposePlan()}
            placeholder="Describe your research inquiry..."
            disabled={status !== 'idle' && status !== 'error'}
            className="mac-input w-full py-4 px-6 text-lg outline-none font-medium placeholder:font-light"
          />
          <div className="absolute right-3 top-1/2 -translate-y-1/2">
            {status === 'researching' || (status === 'planning' && !proposedTaxonomy) ? (
              <div className="busy-indicator"></div>
            ) : (
              <button 
                onClick={proposePlan}
                disabled={!query.trim() || status === 'planning'}
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
        <div className="min-w-200 flex items-center justify-between px-10 relative">
           {/* Background connecting line */}
           <div className="absolute top-1/2 left-20 right-20 h-[0.5px] bg-[#E5E5E7] -z-10"></div>
           
           {agents.map((agent) => {
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
        {agents.map((agent) => {
          const isActive = activeAgentId === agent.id;
          const logs = agentLogs[agent.id] || [];
          return (
            <div 
              key={agent.id} 
              className={`agent-card min-w-45 max-w-45 p-3 h-32 flex flex-col shrink-0 ${isActive ? 'agent-card-active' : ''}`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className={`text-[9px] font-black uppercase tracking-widest ${isActive ? 'text-[#0066CC]' : 'text-[#86868B]'}`}>
                  {agent.name}
                </span>
                {isActive && <div className="busy-indicator m-0! w-1.5! h-1.5!"></div>}
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

        {status === 'planning' && proposedTaxonomy && (
          <div className="py-10">
            <ReportPlanner 
              key={query}
              query={query}
              initialTaxonomy={proposedTaxonomy} 
              onConfirm={(finalTaxonomy) => startResearch(finalTaxonomy)}
              onCancel={() => setStatus('idle')}
            />
          </div>
        )}

        {status === 'planning' && !proposedTaxonomy && (
          <div className="py-20 flex flex-col items-center">
            <div className="busy-indicator w-8! h-8! mb-6"></div>
            <h2 className="serif text-2xl italic text-[#86868B]">Orchestrating Strategic Roadmap...</h2>
          </div>
        )}

        {error && (
          <div className="max-w-2xl mx-auto p-4 bg-[#FEFBFA] border border-[#F5E8E2] rounded-xl text-[#B3261E] text-sm font-medium">
             ⚠️ {error}
          </div>
        )}

        {finalReport && (
          <div className="animate-in fade-in slide-in-from-top-6 duration-1000 max-w-2xl mx-auto">
            <div className="flex justify-center mb-10">
              <div className="bg-[#F2F2F7] p-1 rounded-lg flex space-x-1">
                <button 
                  onClick={() => setActiveTab('research')}
                  className={`px-4 py-1.5 text-[12px] font-bold rounded-md transition-all ${activeTab === 'research' ? 'bg-white shadow-sm text-[#1D1D1F]' : 'text-[#86868B] hover:text-[#1D1D1F]'}`}
                >
                  Real Output
                </button>
                <button 
                  onClick={() => setActiveTab('technical')}
                  className={`px-4 py-1.5 text-[12px] font-bold rounded-md transition-all ${activeTab === 'technical' ? 'bg-white shadow-sm text-[#1D1D1F]' : 'text-[#86868B] hover:text-[#1D1D1F]'}`}
                >
                  Technical Output
                </button>
              </div>
            </div>

            <article className="space-y-8">
              <div className="flex items-center space-x-4 mb-4">
                <span className="text-[10px] font-black uppercase tracking-[0.3em] text-[#34C759] border border-[#34C759] px-2 py-0.5 rounded">
                  {activeTab === 'research' ? 'Synthesis Output' : 'Technical Analysis'}
                </span>
                <div className="h-px flex-1 bg-[#F2F2F7]"></div>
              </div>

              <div className={`leading-relaxed text-[#1D1D1F] whitespace-pre-wrap ${activeTab === 'research' ? 'serif text-lg md:text-xl first-letter:text-6xl first-letter:float-left first-letter:mr-4 first-letter:font-black' : 'font-mono text-[13px] text-[#424245]'}`}>
                {(activeTab === 'technical' ? technicalReport : finalReport).trim()}
              </div>
            </article>
          </div>
        )}
      </div>
    </div>
  );
}
