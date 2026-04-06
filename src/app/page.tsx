"use client";

import { useState, useEffect, useRef } from "react";
import { AGENTS } from "@/lib/agents";
import { usePipelineStore } from "@/lib/store";
import { startPipelineRun, type ReportLength } from "@/lib/pipelineClient";
import { publicApiBaseUrl } from "@/lib/publicApiBaseUrl";

// ── Inline markdown renderer ─────────────────────────────────────────────────
function inlineFormat(line: string): React.ReactNode {
  const parts = line.split(/(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g);
  return (
    <>
      {parts.map((part, i) => {
        if (part.startsWith("**") && part.endsWith("**"))
          return <strong key={i}>{part.slice(2, -2)}</strong>;
        if (part.startsWith("*") && part.endsWith("*"))
          return <em key={i}>{part.slice(1, -1)}</em>;
        if (part.startsWith("`") && part.endsWith("`"))
          return <code key={i} className="bg-slate-100 text-rose-600 px-1 rounded text-[0.8em] font-mono">{part.slice(1, -1)}</code>;
        return <span key={i}>{part}</span>;
      })}
    </>
  );
}

function MarkdownReport({ text }: { text: string }) {
  const lines = text.split("\n");
  const nodes: React.ReactNode[] = [];
  let i = 0;
  let key = 0;

  while (i < lines.length) {
    const line = lines[i];

    if (line.startsWith("```")) {
      const block: string[] = [];
      i++;
      while (i < lines.length && !lines[i].startsWith("```")) { block.push(lines[i]); i++; }
      nodes.push(
        <pre key={key++} className="bg-slate-900 text-emerald-300 rounded-lg p-4 overflow-x-auto text-sm font-mono my-4">
          <code>{block.join("\n")}</code>
        </pre>
      );
      i++; continue;
    }
    if (line.startsWith("# ")) {
      nodes.push(<h1 key={key++} className="text-2xl font-bold text-slate-900 mt-6 mb-2">{inlineFormat(line.slice(2))}</h1>);
      i++; continue;
    }
    if (line.startsWith("## ")) {
      nodes.push(<h2 key={key++} className="text-xl font-bold text-slate-800 mt-5 mb-2 border-b border-slate-200 pb-1">{inlineFormat(line.slice(3))}</h2>);
      i++; continue;
    }
    if (line.startsWith("### ")) {
      nodes.push(<h3 key={key++} className="text-base font-semibold text-slate-800 mt-4 mb-1">{inlineFormat(line.slice(4))}</h3>);
      i++; continue;
    }
    if (line.match(/^[-*]{3,}$/) || line.match(/^_{3,}$/)) {
      nodes.push(<hr key={key++} className="border-slate-200 my-4" />);
      i++; continue;
    }
    if (line.startsWith("> ")) {
      nodes.push(
        <blockquote key={key++} className="border-l-4 border-blue-400 pl-4 py-1 my-2 bg-blue-50 rounded-r text-slate-600 italic text-sm">
          {inlineFormat(line.slice(2))}
        </blockquote>
      );
      i++; continue;
    }
    if (line.startsWith("- ") || line.startsWith("* ")) {
      const items: string[] = [];
      while (i < lines.length && (lines[i].startsWith("- ") || lines[i].startsWith("* "))) {
        items.push(lines[i].slice(2)); i++;
      }
      nodes.push(
        <ul key={key++} className="list-disc list-inside space-y-1 my-2 text-slate-700">
          {items.map((it, ii) => <li key={ii} className="text-sm leading-relaxed">{inlineFormat(it)}</li>)}
        </ul>
      );
      continue;
    }
    if (line.match(/^\d+\. /)) {
      const items: string[] = [];
      while (i < lines.length && lines[i].match(/^\d+\. /)) {
        items.push(lines[i].replace(/^\d+\. /, "")); i++;
      }
      nodes.push(
        <ol key={key++} className="list-decimal list-inside space-y-1 my-2 text-slate-700">
          {items.map((it, ii) => <li key={ii} className="text-sm leading-relaxed">{inlineFormat(it)}</li>)}
        </ol>
      );
      continue;
    }
    if (line.trim() === "") { i++; continue; }

    nodes.push(
      <p key={key++} className="text-slate-700 text-sm leading-relaxed my-1.5">{inlineFormat(line)}</p>
    );
    i++;
  }

  return <div className="space-y-0.5">{nodes}</div>;
}

// ── Backend health hook ───────────────────────────────────────────────────────
function useBackendHealth() {
  const [status, setStatus] = useState<"checking" | "online" | "offline">("checking");
  useEffect(() => {
    fetch(`${publicApiBaseUrl}/health`, { signal: AbortSignal.timeout(4000) })
      .then((r) => setStatus(r.ok ? "online" : "offline"))
      .catch(() => setStatus("offline"));
  }, []);
  return status;
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function Home() {
  const [query, setQuery] = useState("");
  const [reportLength, setReportLength] = useState<ReportLength>("moderate");
  const [isRunning, setIsRunning] = useState(false);
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null);
  const reportRef = useRef<HTMLDivElement>(null);

  const session = usePipelineStore((s) => s.session);
  const statuses = usePipelineStore((s) => s.nodeStatuses);
  const resetPipeline = usePipelineStore((s) => s.resetPipeline);
  const backendHealth = useBackendHealth();

  const handleRun = async () => {
    if (!query.trim() || isRunning) return;
    resetPipeline();
    setExpandedAgent(null);
    setIsRunning(true);

    const store = usePipelineStore.getState();
    await startPipelineRun(query, {
      startPipeline: (q) => store.startPipeline(q),
      setBackendSessionId: (id) => usePipelineStore.getState().setBackendSessionId(id),
      setNodeStatus: (id, st) => usePipelineStore.getState().setNodeStatus(id, st),
      appendChunk: (id, chunk) => usePipelineStore.getState().appendChunk(id, chunk),
      setFinalAnswer: (ans) => usePipelineStore.getState().setFinalAnswer(ans),
      setQualityLoading: () => usePipelineStore.getState().setQualityLoading(),
      setQualityReport: (r) => usePipelineStore.getState().setQualityReport(r),
      setQualityError: () => usePipelineStore.getState().setQualityError(),
      setPipelineError: (msg) => usePipelineStore.getState().setPipelineError(msg),
    }, { reportLength });

    setIsRunning(false);
    setTimeout(() => reportRef.current?.scrollIntoView({ behavior: "smooth" }), 200);
  };

  const downloadReport = () => {
    if (!session?.finalAnswer) return;
    const blob = new Blob([session.finalAnswer], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${query.slice(0, 40).replace(/\s+/g, "_")}_report.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const hasReport = !!session?.finalAnswer;
  const hasError = session?.status === "error";

  return (
    <div className="min-h-screen bg-[#f8fafc]">
      {/* ── Top bar ── */}
      <header className="sticky top-0 z-50 bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between shadow-sm">
        <div className="flex items-center gap-3">
          <span className="text-xl font-bold tracking-tight text-slate-900">Hexamind</span>
          <span className="text-xs text-slate-400 hidden sm:inline">Multi-Agent Research Intelligence</span>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <span className={`w-2 h-2 rounded-full flex-shrink-0 ${
            backendHealth === "online" ? "bg-emerald-500" :
            backendHealth === "offline" ? "bg-red-500" :
            "bg-amber-400 animate-pulse"
          }`} />
          <span className="text-slate-500">
            {backendHealth === "online" ? "Backend live · llama3.1:70b" :
             backendHealth === "offline" ? "Backend offline — start with: sudo systemctl start hexamind-backend" :
             "Connecting…"}
          </span>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8 space-y-5">

        {/* ── Query ── */}
        <section className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
          <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-3">Research Query</h2>
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) handleRun(); }}
            placeholder="What do you want to research? (Ctrl+Enter to run)"
            rows={3}
            disabled={isRunning}
            className="w-full px-4 py-3 rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none text-slate-800 placeholder-slate-400 disabled:opacity-60 text-sm"
          />
          <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500">Depth:</span>
              {(["brief", "moderate", "huge"] as ReportLength[]).map((l) => (
                <button
                  key={l}
                  onClick={() => setReportLength(l)}
                  disabled={isRunning}
                  className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                    reportLength === l ? "bg-blue-600 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                  }`}
                >
                  {l.charAt(0).toUpperCase() + l.slice(1)}
                </button>
              ))}
            </div>
            <button
              onClick={handleRun}
              disabled={!query.trim() || isRunning || backendHealth !== "online"}
              className="px-6 py-2.5 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm flex items-center gap-2"
            >
              {isRunning ? (
                <>
                  <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                  </svg>
                  Running…
                </>
              ) : "Run Research"}
            </button>
          </div>
        </section>

        {/* ── Agent pipeline ── */}
        {session && (
          <section className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
            <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-4">Agent Pipeline</h2>
            <div className="space-y-2">
              {AGENTS.map((agent) => {
                const st = statuses[agent.id] ?? "idle";
                const output = session.outputs[agent.id];
                const hasContent = (output?.content?.length ?? 0) > 0;
                const isExpanded = expandedAgent === agent.id;

                return (
                  <div key={agent.id} className={`rounded-lg border overflow-hidden transition-colors ${
                    st === "active" ? "border-blue-300 bg-blue-50" :
                    st === "done"   ? "border-emerald-300 bg-emerald-50" :
                    st === "error"  ? "border-red-300 bg-red-50" :
                    "border-slate-200 bg-slate-50"
                  }`}>
                    <div
                      className={`flex items-center gap-3 px-4 py-3 ${hasContent ? "cursor-pointer select-none" : ""}`}
                      onClick={() => hasContent && setExpandedAgent(isExpanded ? null : agent.id)}
                    >
                      <span className={`w-2 h-2 rounded-full flex-shrink-0 ${
                        st === "active" ? "bg-blue-500 animate-pulse" :
                        st === "done"   ? "bg-emerald-500" :
                        st === "error"  ? "bg-red-500" : "bg-slate-300"
                      }`} />
                      <span className="font-medium text-sm text-slate-800 w-24 flex-shrink-0">{agent.codename}</span>
                      <span className="text-xs text-slate-500 flex-1 truncate hidden sm:block">{agent.role}</span>
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium flex-shrink-0 ${
                        st === "active" ? "bg-blue-100 text-blue-700" :
                        st === "done"   ? "bg-emerald-100 text-emerald-700" :
                        st === "error"  ? "bg-red-100 text-red-700" :
                        "bg-slate-100 text-slate-500"
                      }`}>{st}</span>
                      {hasContent && (
                        <svg className={`w-4 h-4 text-slate-400 flex-shrink-0 transition-transform ${isExpanded ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                        </svg>
                      )}
                    </div>
                    {isExpanded && hasContent && (
                      <div className="px-4 pb-4">
                        <div className="bg-white rounded border border-slate-200 p-3 max-h-52 overflow-y-auto text-xs text-slate-600 font-mono whitespace-pre-wrap leading-relaxed">
                          {output.content}
                          {st === "active" && <span className="inline-block w-1.5 h-3 bg-blue-500 animate-pulse ml-0.5 align-middle" />}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {/* ── Error ── */}
        {hasError && (
          <section className="bg-red-50 border border-red-300 rounded-xl p-5 flex items-start gap-3">
            <svg className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
            <div>
              <p className="font-semibold text-red-800 text-sm">Pipeline Error</p>
              <p className="text-red-700 text-sm mt-1">{session?.errorMessage || "An unknown error occurred."}</p>
            </div>
          </section>
        )}

        {/* ── Report ── */}
        {hasReport && (
          <section ref={reportRef} className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-widest">Research Report</h2>
              <button
                onClick={downloadReport}
                className="flex items-center gap-2 px-4 py-2 text-xs font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
              >
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                Download .md
              </button>
            </div>
            <MarkdownReport text={session.finalAnswer} />
          </section>
        )}

        {/* ── Quality metrics ── */}
        {session?.qualityReport && session.qualityStatus === "ready" && (
          <section className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
            <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-4">Quality Analysis</h2>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
              {[
                { label: "Overall Score", value: session.qualityReport.overallScore?.toFixed(1), color: "text-blue-600" },
                { label: "Trust Score",   value: session.qualityReport.trustScore?.toFixed(1) ?? "—", color: "text-emerald-600" },
                { label: "Sources",       value: String(session.qualityReport.metrics.sourceCount), color: "text-purple-600" },
                { label: "Citations",     value: String(session.qualityReport.metrics.citationCount), color: "text-amber-600" },
              ].map((m) => (
                <div key={m.label} className="bg-slate-50 rounded-lg p-4 text-center border border-slate-100">
                  <div className={`text-2xl font-bold ${m.color}`}>{m.value}</div>
                  <div className="text-xs text-slate-500 mt-1">{m.label}</div>
                </div>
              ))}
            </div>

            {session.qualityReport.claimVerifications?.length > 0 && (
              <div className="mb-4">
                <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-2">Claim Verifications</h3>
                <div className="space-y-1.5">
                  {session.qualityReport.claimVerifications.slice(0, 6).map((cv, i) => (
                    <div key={i} className={`flex items-start gap-2 p-2.5 rounded-lg text-xs border ${
                      cv.status === "verified"   ? "bg-emerald-50 border-emerald-200" :
                      cv.status === "contested"  ? "bg-amber-50 border-amber-200" :
                      "bg-slate-50 border-slate-200"
                    }`}>
                      <span className={`font-semibold flex-shrink-0 ${
                        cv.status === "verified"  ? "text-emerald-700" :
                        cv.status === "contested" ? "text-amber-700" : "text-slate-500"
                      }`}>{cv.status}</span>
                      <span className="text-slate-700">{cv.claim}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {session.qualityReport.contradictionFindings?.length > 0 && (
              <div>
                <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-2">Contradictions</h3>
                <div className="space-y-1.5">
                  {session.qualityReport.contradictionFindings.slice(0, 3).map((c, i) => (
                    <div key={i} className="text-xs p-2.5 bg-rose-50 border border-rose-200 rounded-lg text-rose-700">{c.reason}</div>
                  ))}
                </div>
              </div>
            )}
          </section>
        )}

        {session?.qualityStatus === "loading" && (
          <section className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 flex items-center gap-3 text-sm text-slate-500">
            <svg className="animate-spin w-4 h-4 text-blue-500" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
            </svg>
            Analysing report quality…
          </section>
        )}

      </main>

      <footer className="text-center py-8 text-xs text-slate-400">
        Hexamind · Multi-agent AI · llama3.1:70b · Zero cost
      </footer>
    </div>
  );
}
