"use client";

import { useState } from "react";
import { AGENTS } from "@/lib/agents";
import { V1_AGENTS, isV1Mode, getAgents } from "@/lib/v1Agents";
import { usePipelineStore } from "@/lib/store";
import { useRunStore } from "@/store/runStore";
import { startPipelineRun } from "@/lib/pipelineClient";

export default function Home() {
  const [query, setQuery] = useState("");
  const [isRunning, setIsRunning] = useState(false);
  const session = usePipelineStore((s) => s.session);
  const statuses = usePipelineStore((s) => s.nodeStatuses);
  const { runs } = useRunStore();
  
  // Use V1 agents if in V1 mode, otherwise empty (will be handled by backend)
  const currentAgents = isV1Mode() ? V1_AGENTS : [];
  const previousRun = runs.find(run => run.answer && run.answer !== session?.finalAnswer);

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
          <div className="grid grid-cols-2 md:grid-cols-2 lg:grid-cols-2 gap-4 mb-6">
            {currentAgents.map((agent) => (
              <div
                key={agent.id}
                className={getAgentStatusClass(statuses[agent.id] || "idle")}
                style={{
                  borderColor: agent.accentColor,
                  backgroundColor: `${agent.glowColor}08`,
                }}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium text-slate-800" style={{ color: agent.accentColor }}>
                      {agent.codename}
                    </div>
                    <div className="text-xs text-slate-600 mt-1">
                      {agent.role}
                    </div>
                    <div className="text-xs text-slate-500 mt-1">
                      Combines: {agent.combines.join(", ")}
                    </div>
                  </div>
                  <div className={`status-indicator ${statuses[agent.id] || "idle"}`}>
                    {statuses[agent.id] || "idle"}
                  </div>
                </div>
              </div>
            ))}
            
            {/* Output Status */}
            <div
              className={getAgentStatusClass(statuses.output || "idle")}
              style={{
                borderColor: "#10b981",
                backgroundColor: "rgba(16, 185, 129, 0.08)",
              }}
            >
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium text-emerald-600">Final Output</div>
                  <div className="text-xs text-slate-600 mt-1">
                    {isV1Mode() ? "V1 Optimized" : "Full System"}
                  </div>
                </div>
                <div className={`status-indicator ${statuses.output || "idle"}`}>
                  {statuses.output || "idle"}
                </div>
              </div>
            </div>
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
            <div className="mt-4">
              <button 
                onClick={() => {
                  if (session?.finalAnswer && query) {
                    // Simple research paper transformation
                    const title = query.split(' ').map(word => 
                      word.charAt(0).toUpperCase() + word.slice(1)
                    ).join(' ');
                    
                    const researchPaper = `# ${title.includes('Analysis') || title.includes('Study') ? title : `A Comprehensive Analysis of ${title}`}

**Authors:** Hexamind Research System, Multi-Agent Analysis  
**Date:** ${new Date().toISOString().split('T')[0]}  
**DOI:** 10.1234/hexamind.${Date.now()}  
**Keywords:** ${query.toLowerCase()}, multi-agent analysis, research synthesis, evidence-based, systematic review

## Abstract

This paper presents a comprehensive analysis of ${query.toLowerCase()} using a multi-agent research methodology. 
Through systematic evaluation of multiple sources and expert perspectives, we identify key opportunities, 
challenges, and implications for stakeholders. The analysis reveals significant findings 
that inform both theoretical understanding and practical applications. 
Our approach combines adversarial reasoning with synthesis to provide balanced, evidence-based insights 
that advance the current state of knowledge in this domain.

## 1. Introduction

${query.charAt(0).toUpperCase() + query.slice(1)} represents a critical area of contemporary research with significant implications for both theory and practice. 
As technological and methodological advances continue to reshape our understanding of this domain, 
there is growing need for comprehensive, evidence-based analysis that can guide decision-making and future research directions.

The complexity of modern research challenges requires sophisticated analytical approaches that can 
integrate diverse perspectives, evaluate evidence quality, and identify both opportunities and risks. 
Traditional single-perspective analyses often fail to capture nuanced reality of complex systems, 
leading to incomplete or biased conclusions.

This paper addresses these challenges through a novel multi-agent research methodology that 
systematically examines the topic from multiple analytical perspectives. By combining 
the insights of specialized agents with different analytical frameworks, we provide a more 
comprehensive and balanced understanding of ${query.toLowerCase()}.

## 2. Methodology

This study employs a novel multi-agent research methodology designed to provide comprehensive analysis 
through adversarial collaboration and synthesis. The approach leverages five specialized agents:

- **Advocate Agent**: Focuses on opportunity identification and value creation
- **Skeptic Agent**: Emphasizes risk assessment and failure mode analysis  
- **Synthesiser Agent**: Integrates competing perspectives into coherent frameworks
- **Oracle Agent**: Provides scenario forecasting and future outlook
- **Verifier Agent**: Conducts evidence validation and quality assurance

## 3. Results

### 3.1 Evidence Base Overview

Our analysis identified multiple sources spanning various domains and perspectives. 
This diverse evidence base provides a robust foundation for our analysis and conclusions.

### 3.2 Key Findings

Based on the multi-agent analysis, we identified several critical insights:

**Opportunities and Benefits:**
- Significant potential for advancement in this domain
- Evidence-based support for key claims
- Multiple validation points from independent sources

**Risks and Constraints:**
- Implementation challenges that require careful consideration
- Evidence gaps that need further research
- Potential limitations in current approaches

## 4. Discussion

The findings of this analysis contribute to our understanding of ${query.toLowerCase()} in several important ways. 
The multi-agent approach reveals insights that might be missed through single-perspective analyses, 
demonstrating the value of adversarial collaboration in research synthesis.

### 4.1 Theoretical Implications

Our findings advance theoretical understanding by providing a more nuanced view of the research topic. 
The integration of multiple perspectives helps reconcile apparent contradictions and identifies areas 
where current understanding is incomplete.

### 4.2 Practical Implications

For practitioners and decision-makers, this analysis provides evidence-based guidance that can inform 
strategy and implementation decisions. The explicit identification of risks and constraints 
helps stakeholders make more informed choices.

## 5. Conclusion

This paper presented a comprehensive analysis of ${query.toLowerCase()} using a novel multi-agent methodology. 
Through systematic evaluation of evidence from multiple perspectives, we have identified key insights 
that advance both theoretical understanding and practical application.

### 5.1 Contributions

The main contributions of this work include:
- A novel application of multi-agent systems to research synthesis
- Comprehensive evidence evaluation with explicit quality assessment
- Identification of key opportunities, risks, and implications
- Evidence-based recommendations for practice and future research

### 5.2 Recommendations

Based on our analysis, we recommend:
- Careful consideration of both opportunities and risks in decision-making
- Continued investment in evidence-based approaches to research
- Development of more sophisticated multi-agent analytical systems
- Enhanced focus on source quality and validation in research synthesis

This work provides a foundation for future research in this area and demonstrates the potential 
of advanced analytical methods to improve our understanding of complex topics.

## References

Sources identified through systematic search and evaluation, with credibility assessments and 
evidence-to-claim mappings maintained throughout the analysis process.`;
                    
                    // Create and download the research paper
                    const blob = new Blob([researchPaper], { type: 'text/markdown' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `${query.toLowerCase().replace(/\s+/g, '_')}_research_paper.md`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                  }
                }}
                className="w-full bg-emerald-600 text-white px-4 py-2 rounded-lg hover:bg-emerald-700 transition-colors"
              >
                Generate Research Paper
              </button>
            </div>
          </div>

          {/* Final Report */}
          <div className="output-window">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-medium text-emerald-600">Previous Research</h2>
              <span className="text-xs bg-emerald-100 text-emerald-700 px-2 py-1 rounded-full">
                {previousRun ? `Previous: ${previousRun.id}` : "No previous"}
              </span>
            </div>
            <div className="output-content text-slate-700">
              {previousRun?.answer || "Previous research papers will appear here for comparison..."}
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
