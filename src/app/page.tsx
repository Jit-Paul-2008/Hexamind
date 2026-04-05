"use client";

import { useState } from "react";
import { AGENTS } from "@/lib/agents";
import { usePipelineStore } from "@/lib/store";
import { useRunStore } from "@/store/runStore";
import { startPipelineRun } from "@/lib/pipelineClient";

export default function Home() {
  const [query, setQuery] = useState("");
  const [isRunning, setIsRunning] = useState(false);
  const session = usePipelineStore((s) => s.session);
  const statuses = usePipelineStore((s) => s.nodeStatuses);
  const { runs } = useRunStore();
  
  const previousRun = runs.find(run => run.answer && run.answer !== session?.finalAnswer);

  const handleRun = async () => {
    if (!query.trim() || isRunning) return;
    
    setIsRunning(true);
    await startPipelineRun(query, {
      startPipeline: () => {},
      setBackendSessionId: () => {},
      setNodeStatus: () => {},
      appendChunk: () => {},
      setFinalAnswer: () => {},
      setQualityLoading: () => {},
      setQualityReport: () => {},
      setQualityError: () => {},
      setPipelineError: () => {},
    });
    setIsRunning(false);
  };

  const getAgentStatusClass = (status: string) => {
    switch (status) {
      case "active": return "agent-card active";
      case "done": return "agent-card done";
      default: return "agent-card";
    }
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="container">
        {/* Header */}
        <header className="text-center mb-8">
          <h1 className="text-3xl font-light text-slate-800 mb-2">Hexamind</h1>
          <p className="text-slate-600">Research Pipeline with Multi-Agent Analysis</p>
        </header>

        {/* Query Input */}
        <div className="card mb-8">
          <label className="block text-sm font-medium text-slate-700 mb-2">
            Research Query
          </label>
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="What would you like to research today?"
            className="input mb-4 resize-none"
            rows={4}
          />
          <button
            onClick={handleRun}
            disabled={!query.trim() || isRunning}
            className="button"
          >
            {isRunning ? "Processing..." : "Start Research"}
          </button>
        </div>

        {/* Agent Status */}
        <div className="card mb-8">
          <h2 className="text-lg font-medium text-slate-800 mb-4">Agent Status</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
            {AGENTS.map((agent) => {
              const status = statuses[agent.id] || "idle";
              return (
                <div key={agent.id} className={getAgentStatusClass(status)}>
                  <div className="font-medium text-slate-800 mb-1">{agent.codename}</div>
                  <div className="text-xs text-slate-600 uppercase">{status}</div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Output Windows */}
        <div className="grid lg:grid-cols-2 gap-6">
          {/* Technical Output */}
          <div className="output-window">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-medium text-blue-600">Technical Output</h2>
              <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded-full">
                {statuses.output || "idle"}
              </span>
            </div>
            <div className="output-content text-slate-700">
              {session?.finalAnswer || "Technical analysis will appear here..."}
            </div>
            {session?.qualityReport && (
              <div className="grid grid-cols-4 gap-2 mt-4">
                <div className="metric">
                  <div className="font-medium text-slate-800">Score</div>
                  <div className="text-slate-600">{session.qualityReport.overallScore.toFixed(1)}</div>
                </div>
                <div className="metric">
                  <div className="font-medium text-slate-800">Sources</div>
                  <div className="text-slate-600">{session.qualityReport.metrics.sourceCount}</div>
                </div>
                <div className="metric">
                  <div className="font-medium text-slate-800">Trust</div>
                  <div className="text-slate-600">{session.qualityReport.trustScore?.toFixed(1) || "N/A"}</div>
                </div>
                <div className="metric">
                  <div className="font-medium text-slate-800">Issues</div>
                  <div className="text-slate-600">{session.qualityReport.metrics.contradictionCount}</div>
                </div>
              </div>
            )}
          </div>

          {/* Final Report */}
          <div className="output-window">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-medium text-emerald-600">Final Report</h2>
              <span className="text-xs bg-emerald-100 text-emerald-700 px-2 py-1 rounded-full">
                {previousRun ? `Previous: ${previousRun.id}` : "No previous"}
              </span>
            </div>
            <div className="output-content text-slate-700">
              {previousRun?.answer || "Previous reports will appear here for comparison..."}
            </div>
            {previousRun?.quality && (
              <div className="grid grid-cols-4 gap-2 mt-4">
                <div className="metric">
                  <div className="font-medium text-slate-800">Score</div>
                  <div className="text-slate-600">{previousRun.quality.overallScore}</div>
                </div>
                <div className="metric">
                  <div className="font-medium text-slate-800">Sources</div>
                  <div className="text-slate-600">{previousRun.quality.sourceCount}</div>
                </div>
                <div className="metric">
                  <div className="font-medium text-slate-800">Trust</div>
                  <div className="text-slate-600">{previousRun.quality.trustScore || "N/A"}</div>
                </div>
                <div className="metric">
                  <div className="font-medium text-slate-800">Issues</div>
                  <div className="text-slate-600">{previousRun.quality.contradictionCount}</div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <footer className="text-center mt-12 text-sm text-slate-500">
          <p>Powered by Local AI Models • Multi-Agent Reasoning</p>
        </footer>
      </div>
    </div>
  );
}
