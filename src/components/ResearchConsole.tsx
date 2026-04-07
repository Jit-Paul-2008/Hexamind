"use client";

import React, { useState, useEffect, useRef } from 'react';
import ReasoningGraph from './ReasoningGraph';
import DynamicChart from './DynamicChart';
import { PipelineEvent, PipelineEventType } from '@/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';


export default function ResearchConsole() {
  const [query, setQuery] = useState('');
  const [agaMode, setAgaMode] = useState(false);
  const [mathMode, setMathMode] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [status, setStatus] = useState<'idle' | 'researching' | 'completed' | 'error'>('idle');
  const [events, setEvents] = useState<any[]>([]);
  const [activeAgent, setActiveAgent] = useState<string | null>(null);
  const [finalReport, setFinalReport] = useState<string>('');
  const [error, setError] = useState<string | null>(null);

  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events]);

  const startResearch = async () => {
    if (!query.trim()) return;

    // Reset state
    setEvents([]);
    setFinalReport('');
    setError(null);
    setStatus('researching');
    setActiveAgent('planner');

    try {
      // 1. Create session
      const startRes = await fetch(`${API_BASE}/api/pipeline/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, agaMode: false, mathMode: false }),
      });

      if (!startRes.ok) throw new Error(`Failed to start research session: ${startRes.statusText}`);
      const { sessionId } = await startRes.json();

      // 2. Connect to SSE
      const eventSource = new EventSource(`${API_BASE}/api/pipeline/${sessionId}/stream`);



      eventSource.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data);
          const data = JSON.parse(parsed.data) as PipelineEvent;

          const content = data.chunk || data.fullContent || '';
          setEvents(prev => [...prev, { type: parsed.event, agent: data.agentId, content }]);

          if (parsed.event === PipelineEventType.AGENT_START) {
            setActiveAgent(data.agentId);
          }

          if (parsed.event === PipelineEventType.PIPELINE_DONE) {
            setFinalReport(data.fullContent || '');
            setStatus('completed');
            setActiveAgent(null);
            eventSource.close();
          }

          if (parsed.event === PipelineEventType.PIPELINE_ERROR) {
            setError(data.fullContent || data.error || 'Pipeline encountered an internal error.');
            setStatus('error');
            setActiveAgent(null);
            eventSource.close();
          }
        } catch (parseErr) {
          console.error('Failed to parse SSE frame:', parseErr);
        }
      };


      eventSource.onerror = (err) => {
        console.error("SSE Error:", err);
        setError("Connection lost. The research might still be running locally.");
        setStatus('error');
        eventSource.close();
      };

    } catch (err: any) {
      setError(err.message);
      setStatus('error');
    }
  };

  return (
    <div className="w-full max-w-6xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-1000">
      {/* Search Header */}
      <div className="glass-card p-8 space-y-6">
        <div className="space-y-2">
          <h2 className="text-3xl font-bold aurora-gradient">Aurora Reasoning Engine</h2>
          <p className="text-slate-400">Professional-grade research orchestrated by a stateful multi-agent graph.</p>
        </div>

        <div className="relative group">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && startResearch()}
            placeholder="Describe your research objective..."
            disabled={status === 'researching'}
            className="w-full bg-white/5 border border-white/10 rounded-2xl py-4 px-6 text-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all placeholder:text-slate-600"
          />
          <button
            onClick={startResearch}
            disabled={status === 'researching' || !query.trim()}
            className="absolute right-2 top-2 bottom-2 px-6 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 rounded-xl font-semibold transition-all flex items-center space-x-2"
          >
            {status === 'researching' ? (
              <><span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span><span>Thinking...</span></>
            ) : (
              <span>Initiate Research</span>
            )}
          </button>
        </div>

        <div className="flex flex-wrap gap-4 px-2">
          <div className="flex items-center space-x-3">
            <button
              onClick={() => {
                setToast("Under Development: Strict Fact Mode is disabled for this public demo.");
                setTimeout(() => setToast(null), 4000);
              }}
              className={`w-12 h-6 rounded-full transition-colors relative bg-slate-700 opacity-50 cursor-not-allowed`}
            >
              <div className={`w-4 h-4 bg-white rounded-full absolute top-1 transition-transform translate-x-1`} />
            </button>
            <div className="flex flex-col">
              <span className="text-sm font-semibold text-slate-200">Strict Fact Mode (AGA)</span>
              <span className="text-xs text-slate-500">Eliminates hallucination by enforcing atomic grounding.</span>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={() => {
                setToast("Under Development: Math Engine is disabled for this public demo.");
                setTimeout(() => setToast(null), 4000);
              }}
              className={`w-12 h-6 rounded-full transition-colors relative bg-slate-700 opacity-50 cursor-not-allowed`}
            >
              <div className={`w-4 h-4 bg-white rounded-full absolute top-1 transition-transform translate-x-1`} />
            </button>
            <div className="flex flex-col">
              <span className="text-sm font-semibold text-blue-300">Math Engine (Supercomputer)</span>
              <span className="text-xs text-slate-500">Quantitative Python simulation & forecasting charts.</span>
            </div>
          </div>
        </div>

        {toast && (
          <div className="animate-in fade-in slide-in-from-top-2 text-sm font-bold bg-blue-500/20 text-blue-300 px-4 py-3 mt-4 rounded-xl border border-blue-500/30 flex items-center shadow-[0_0_15px_rgba(59,130,246,0.2)]">
            <span className="material-icons text-xl mr-2">science</span>
            {toast}
          </div>
        )}
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left: Graph & Logs */}
        <div className="lg:col-span-4 space-y-8">
          <ReasoningGraph activeAgent={activeAgent} status={status} />

          <div className="glass-card flex flex-col h-[400px]">
            <div className="px-4 py-3 border-b border-white/10 flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-widest text-slate-500">Thinking Process</span>
              <span className="flex h-2 w-2 rounded-full bg-indigo-500 pulsar"></span>
            </div>
            <div
              ref={scrollRef}
              className="flex-1 overflow-y-auto p-4 font-mono text-xs space-y-2 scrollbar-thin scrollbar-thumb-white/10"
            >
              {events.map((ev, i) => (
                <div key={i} className="animate-in fade-in duration-300">
                  <span className="text-indigo-400 mr-2">[{ev.agent}]</span>
                  <span className="text-slate-300">{ev.content}</span>
                </div>
              ))}
              {status === 'researching' && (
                <div className="text-indigo-500 animate-pulse">_</div>
              )}
              {status === 'idle' && (
                <div className="h-full flex items-center justify-center text-slate-600 italic">
                  Awaiting instruction...
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right: Output */}
        <div className="lg:col-span-8">
          <div className="glass-card flex flex-col h-full min-h-[600px] relative overflow-hidden">
            {status === 'researching' && <div className="scanning-line" />}

            <div className="px-6 py-4 border-b border-white/10 flex items-center justify-between bg-white/[0.02]">
              <span className="font-bold text-indigo-300">Research Report</span>
              {status === 'completed' && <span className="text-xs bg-emerald-500/20 text-emerald-400 px-2 py-1 rounded">Verified Output</span>}
            </div>

            <div className="flex-1 p-8 prose prose-invert prose-indigo max-w-none overflow-y-auto">
              {!finalReport && status === 'idle' && (
                <div className="h-full flex flex-col items-center justify-center space-y-4 text-slate-500">
                  <div className="w-16 h-16 border-2 border-white/5 rounded-full flex items-center justify-center text-3xl opacity-20">
                    <span className="material-icons">description</span>
                  </div>
                  <p>Your research report will appear here.</p>
                </div>
              )}

              {finalReport ? (
                <div className="animate-in fade-in slide-in-from-top-4 duration-1000">
                  {/* Extract and render chart data if present */}
                  {(() => {
                    const chartMatch = finalReport.match(/\[CHART_DATA\]([\s\S]*?)\[\/CHART_DATA\]/);
                    let cleanText = finalReport.replace(/\[CHART_DATA\][\s\S]*?\[\/CHART_DATA\]/g, '');
                    let chartDataArray: any[] = [];
                    if (chartMatch && chartMatch[1]) {
                      try {
                        const parsed = JSON.parse(chartMatch[1]);
                        if (Array.isArray(parsed)) {
                          chartDataArray = parsed;
                        } else {
                          chartDataArray = [parsed];
                        }
                      } catch (e) {
                        console.error("Failed to parse chart JSON from text");
                      }
                    }
                    return (
                      <>
                        {chartDataArray.length > 0 && (
                          <div className={`grid grid-cols-1 ${chartDataArray.length > 1 ? 'xl:grid-cols-2' : ''} gap-6 mt-4 mb-8`}>
                            {chartDataArray.map((chart, idx) => (
                              <DynamicChart key={idx} data={chart} />
                            ))}
                          </div>
                        )}
                        <div className="whitespace-pre-wrap font-sans leading-relaxed">
                          {cleanText}
                        </div>
                      </>
                    );
                  })()}
                </div>
              ) : status === 'researching' && (
                <div className="space-y-4 py-8">
                  <div className="h-4 bg-white/5 rounded w-3/4 animate-pulse"></div>
                  <div className="h-4 bg-white/5 rounded w-1/2 animate-pulse delay-75"></div>
                  <div className="h-4 bg-white/5 rounded w-5/6 animate-pulse delay-150"></div>
                </div>
              )}

              {error && (
                <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-sm">
                  <strong>Error</strong>: {error}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
