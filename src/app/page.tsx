"use client";

import { useState } from "react";
import { V1_AGENTS } from "@/lib/v1Agents";
import { usePipelineStore } from "@/lib/store";
import { useRunStore } from "@/store/runStore";
import { startPipelineRun } from "@/lib/pipelineClient";
import { ResearchPaperFormatter } from "@/lib/researchPaperFormatter";

export default function Home() {
  const [query, setQuery] = useState("");
  const [isRunning, setIsRunning] = useState(false);
  const [activeTab, setActiveTab] = useState("technical");
  const session = usePipelineStore((s) => s.session);
  const statuses = usePipelineStore((s) => s.nodeStatuses);
  const { runs } = useRunStore();

  const currentAgents = V1_AGENTS;
  
  // Get research paper from actual technical output
  const researchPaper = session?.finalAnswer && query 
    ? ResearchPaperFormatter.formatTechnicalOutputToPaper(session.finalAnswer, query)
    : null;

  const handleRun = async () => {
    if (!query.trim() || isRunning) return;
    
    setIsRunning(true);
    
    const handlers = {
      startPipeline: (q: string) => usePipelineStore.getState().startPipeline(q),
      setBackendSessionId: (id: string) => usePipelineStore.getState().setBackendSessionId(id),
      setNodeStatus: (id: string, status: any) => usePipelineStore.getState().setNodeStatus(id, status),
      appendChunk: (id: string, chunk: string) => usePipelineStore.getState().appendChunk(id, chunk),
      setFinalAnswer: (answer: string) => usePipelineStore.getState().setFinalAnswer(answer),
      setQualityLoading: () => usePipelineStore.getState().setQualityLoading(),
      setQualityReport: (report: any) => usePipelineStore.getState().setQualityReport(report),
      setQualityError: () => usePipelineStore.getState().setQualityError(),
      setPipelineError: (message: string) => usePipelineStore.getState().setPipelineError(message),
    };
    
    await startPipelineRun(query, handlers);
    setIsRunning(false);
  };

  const getAgentStatusClass = (status: string) => {
    switch (status) {
      case "active": return "agent-card active";
      case "done": return "agent-card done";
      default: return "agent-card";
    }
  };

  const downloadReport = (content: string, filename: string) => {
    const blob = new Blob([content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <div className="container mx-auto px-4 py-8 max-w-6xl">
        {/* Header */}
        <header className="text-center mb-10">
          <h1 className="text-4xl font-bold text-slate-800 mb-3">Hexamind</h1>
          <p className="text-slate-600 text-lg">AI-Powered Research & Analysis Platform</p>
          <div className="mt-4 flex items-center justify-center gap-4 text-sm text-slate-500">
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 bg-emerald-500 rounded-full"></span>
              V1 Optimized Mode
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 bg-blue-500 rounded-full"></span>
              Local 70B Model
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 bg-purple-500 rounded-full"></span>
              Live Web Research
            </span>
          </div>
        </header>

        {/* Query Input */}
        <div className="bg-white rounded-xl shadow-lg p-6 mb-8">
          <label className="block text-sm font-semibold text-slate-700 mb-3">
            Research Topic
          </label>
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Enter your research topic (e.g., 'quantum computing applications in drug discovery')..."
            className="w-full p-4 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none text-slate-700"
            rows={4}
            disabled={isRunning}
          />
          <div className="mt-4 flex items-center justify-between">
            <div className="text-sm text-slate-500">
              {isRunning ? "Research in progress..." : "Ready to analyze"}
            </div>
            <button
              onClick={handleRun}
              disabled={!query.trim() || isRunning}
              className={`px-6 py-3 rounded-lg font-semibold transition-all ${
                isRunning 
                  ? 'bg-slate-300 text-slate-500 cursor-not-allowed' 
                  : 'bg-blue-600 text-white hover:bg-blue-700 shadow-lg hover:shadow-xl'
              }`}
            >
              {isRunning ? (
                <span className="flex items-center gap-2">
                  <span className="animate-spin">⏳</span>
                  Processing...
                </span>
              ) : (
                'Start Research'
              )}
            </button>
          </div>
        </div>

        {/* Agent Status */}
        {isRunning && (
          <div className="bg-white rounded-xl shadow-lg p-6 mb-8">
            <h2 className="text-lg font-semibold text-slate-800 mb-4 flex items-center gap-2">
              <span className="animate-pulse">🤖</span>
              Agent Progress
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {currentAgents.map((agent) => (
                <div
                  key={agent.id}
                  className={`p-4 rounded-lg border-2 transition-all ${
                    statuses[agent.id] === 'active' 
                      ? 'border-blue-500 bg-blue-50 animate-pulse' 
                      : statuses[agent.id] === 'done'
                      ? 'border-emerald-500 bg-emerald-50'
                      : 'border-slate-200 bg-slate-50'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-semibold text-slate-800">{agent.codename}</span>
                    <span className={`text-xs px-2 py-1 rounded-full ${
                      statuses[agent.id] === 'active' 
                        ? 'bg-blue-100 text-blue-700' 
                        : statuses[agent.id] === 'done'
                        ? 'bg-emerald-100 text-emerald-700'
                        : 'bg-slate-100 text-slate-600'
                    }`}>
                      {statuses[agent.id] || 'waiting'}
                    </span>
                  </div>
                  <div className="text-sm text-slate-600">{agent.role}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Quality Metrics */}
        {session?.qualityReport && (
          <div className="bg-white rounded-xl shadow-lg p-6 mb-8">
            <h2 className="text-lg font-semibold text-slate-800 mb-4">Research Quality</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center p-4 bg-slate-50 rounded-lg">
                <div className="text-2xl font-bold text-blue-600">
                  {session.qualityReport.overallScore.toFixed(1)}
                </div>
                <div className="text-sm text-slate-600">Quality Score</div>
              </div>
              <div className="text-center p-4 bg-slate-50 rounded-lg">
                <div className="text-2xl font-bold text-emerald-600">
                  {session.qualityReport.metrics.sourceCount}
                </div>
                <div className="text-sm text-slate-600">Sources Found</div>
              </div>
              <div className="text-center p-4 bg-slate-50 rounded-lg">
                <div className="text-2xl font-bold text-purple-600">
                  {session.qualityReport.trustScore?.toFixed(1) || "N/A"}
                </div>
                <div className="text-sm text-slate-600">Trust Score</div>
              </div>
              <div className="text-center p-4 bg-slate-50 rounded-lg">
                <div className="text-2xl font-bold text-amber-600">
                  {session.qualityReport.metrics.contradictionCount}
                </div>
                <div className="text-sm text-slate-600">Issues Found</div>
              </div>
            </div>
          </div>
        )}

        {/* Results Section */}
        {session?.finalAnswer && (
          <div className="bg-white rounded-xl shadow-lg p-6 mb-8">
            {/* Tab Navigation */}
            <div className="flex items-center justify-between mb-6 border-b border-slate-200">
              <div className="flex gap-4">
                <button
                  onClick={() => setActiveTab('technical')}
                  className={`pb-3 px-4 font-semibold transition-colors ${
                    activeTab === 'technical' 
                      ? 'text-blue-600 border-b-2 border-blue-600' 
                      : 'text-slate-500 hover:text-slate-700'
                  }`}
                >
                  Technical Analysis
                </button>
                <button
                  onClick={() => setActiveTab('paper')}
                  className={`pb-3 px-4 font-semibold transition-colors ${
                    activeTab === 'paper' 
                      ? 'text-emerald-600 border-b-2 border-emerald-600' 
                      : 'text-slate-500 hover:text-slate-700'
                  }`}
                >
                  Research Paper
                </button>
              </div>
              <div className="flex gap-2">
                {activeTab === 'technical' && (
                  <button
                    onClick={() => downloadReport(session.finalAnswer || '', `${query.replace(/\s+/g, '_')}_technical.md`)}
                    className="px-4 py-2 bg-slate-100 text-slate-700 rounded-lg hover:bg-slate-200 transition-colors text-sm font-medium"
                  >
                    Download Technical
                  </button>
                )}
                {activeTab === 'paper' && researchPaper && (
                  <button
                    onClick={() => downloadReport(researchPaper, `${query.replace(/\s+/g, '_')}_research_paper.md`)}
                    className="px-4 py-2 bg-emerald-100 text-emerald-700 rounded-lg hover:bg-emerald-200 transition-colors text-sm font-medium"
                  >
                    Download Paper
                  </button>
                )}
              </div>
            </div>

            {/* Tab Content */}
            {activeTab === 'technical' ? (
              <div className="prose prose-slate max-w-none">
                <div className="bg-slate-50 rounded-lg p-6 font-mono text-sm text-slate-700 whitespace-pre-wrap">
                  {session.finalAnswer}
                </div>
              </div>
            ) : (
              <div className="prose prose-slate max-w-none">
                {researchPaper ? (
                  <div className="bg-emerald-50 rounded-lg p-6 border-2 border-emerald-100">
                    <div className="prose-headings:text-emerald-800 prose-p:text-slate-700 whitespace-pre-wrap">
                      {researchPaper}
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-12 text-slate-500">
                    Research paper will be generated from technical analysis
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Previous Research */}
        {runs.length > 1 && (
          <div className="bg-white rounded-xl shadow-lg p-6 mb-8">
            <h2 className="text-lg font-semibold text-slate-800 mb-4">Research History</h2>
            <div className="space-y-3">
              {runs.slice(0, 5).map((run) => (
                <div key={run.id} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                  <div>
                    <div className="font-medium text-slate-800 truncate max-w-md">
                      {run.answer ? run.answer.substring(0, 50) + '...' : 'Untitled Research'}
                    </div>
                    <div className="text-sm text-slate-500">
                      {new Date(run.createdAt).toLocaleString()}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {run.quality && (
                      <span className="text-sm px-2 py-1 bg-blue-100 text-blue-700 rounded">
                        Score: {run.quality.overallScore?.toFixed(1) || 'N/A'}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Footer */}
        <footer className="text-center mt-12 text-sm text-slate-500">
          <p>Powered by Multi-Agent AI • Local 70B Model • Zero API Costs</p>
        </footer>
      </div>
    </div>
  );
}
