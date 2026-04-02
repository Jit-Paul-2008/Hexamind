"use client";

import { useEffect, useState } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import { motion } from "framer-motion";
import { usePipelineStore } from "@/lib/store";
import { exportReportDocx, transformReportWithSarvam } from "@/lib/pipelineClient";

const LANGUAGE_OPTIONS: Array<{ value: string; label: string }> = [
  { value: "en-IN", label: "English (India)" },
  { value: "hi-IN", label: "Hindi" },
  { value: "bn-IN", label: "Bengali" },
  { value: "ta-IN", label: "Tamil" },
  { value: "te-IN", label: "Telugu" },
  { value: "gu-IN", label: "Gujarati" },
  { value: "kn-IN", label: "Kannada" },
  { value: "ml-IN", label: "Malayalam" },
  { value: "mr-IN", label: "Marathi" },
  { value: "pa-IN", label: "Punjabi" },
  { value: "od-IN", label: "Odia" },
];

export default function OutputNode({}: NodeProps) {
  const status = usePipelineStore((s) => s.nodeStatuses["output"]);
  const finalAnswer = usePipelineStore((s) => s.session?.finalAnswer || "");
  const backendSessionId = usePipelineStore((s) => s.session?.backendSessionId || "");
  const qualityStatus = usePipelineStore((s) => s.session?.qualityStatus || "idle");
  const qualityReport = usePipelineStore((s) => s.session?.qualityReport);
  const [displayAnswer, setDisplayAnswer] = useState("");
  const [targetLanguageCode, setTargetLanguageCode] = useState("hi-IN");
  const [instruction, setInstruction] = useState("");
  const [transforming, setTransforming] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [transformStatus, setTransformStatus] = useState("");
  const isDone = status === "done";

  useEffect(() => {
    setDisplayAnswer(finalAnswer);
    setTransformStatus("");
  }, [finalAnswer]);

  const canTransform = isDone && Boolean(backendSessionId) && Boolean(finalAnswer.trim());

  const onTransformWithSarvam = async () => {
    if (!canTransform || transforming) {
      return;
    }
    setTransforming(true);
    setTransformStatus("Applying Sarvam transformation...");
    try {
      const response = await transformReportWithSarvam(backendSessionId, {
        targetLanguageCode,
        instruction,
      });
      setDisplayAnswer(response.text);
      setTransformStatus(
        response.fallback
          ? "Sarvam fallback used. Report updated with best-effort transformation."
          : `Sarvam transformation applied (${response.languageCode}).`
      );
    } catch {
      setTransformStatus("Sarvam transformation failed. Showing original report.");
    } finally {
      setTransforming(false);
    }
  };

  const onDownloadDocx = async () => {
    if (!canTransform || exporting) {
      return;
    }
    setExporting(true);
    setTransformStatus("Preparing DOCX download...");
    try {
      const { blob, filename } = await exportReportDocx(backendSessionId, {
        targetLanguageCode,
        instruction,
      });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      setTransformStatus(`DOCX downloaded: ${filename}`);
    } catch {
      setTransformStatus("DOCX export failed. Try running the report again.");
    } finally {
      setExporting(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      className="relative"
      style={{ width: 780 }}
    >
      {/* Glow when result is ready */}
      {isDone && (
        <div
          className="absolute -inset-2 rounded-3xl blur-2xl pointer-events-none"
          style={{
            background:
              "radial-gradient(circle, rgba(226,232,240,0.12) 0%, transparent 70%)",
          }}
        />
      )}

      <div
        className="relative rounded-[28px] border px-7 py-7 backdrop-blur-xl transition-all duration-500"
        style={{
          minHeight: 1123,
          background: isDone
            ? "linear-gradient(180deg, rgba(255,255,255,0.08) 0%, rgba(9,10,14,0.94) 100%)"
            : "linear-gradient(180deg, rgba(255,255,255,0.03) 0%, rgba(9,10,14,0.92) 100%)",
          borderColor: isDone
            ? "rgba(255,255,255,0.24)"
            : "rgba(255,255,255,0.06)",
          boxShadow: isDone
            ? "0 30px 90px rgba(0,0,0,0.55), inset 0 1px 0 rgba(255,255,255,0.10)"
            : "0 20px 60px rgba(0,0,0,0.28)",
        }}
      >
        {/* Header */}
        <div className="flex items-center justify-between gap-4 mb-6">
          <div className="flex items-center gap-1.5">
            {isDone ? (
              <svg
                width="14"
                height="14"
                viewBox="0 0 14 14"
                fill="none"
                className="text-emerald-400"
              >
                <path
                  d="M3 7.5L6 10.5L11 4"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            ) : (
              <div className="w-2 h-2 rounded-full bg-white/15" />
            )}
            <span className="text-[10px] font-sans tracking-[0.3em] uppercase text-white/50">
              Research Synthesis Report
            </span>
          </div>
          <div className="text-right">
            <div className="text-[9px] uppercase tracking-[0.28em] text-white/35">
              A4 Report View
            </div>
            <div className="text-[9px] text-white/25 font-mono">Thesis-style output</div>
          </div>
        </div>

        {/* Content */}
        {isDone ? (
          <div className="space-y-4">
            <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
              <div className="flex items-center justify-between gap-3 mb-3">
                <div className="text-[10px] uppercase tracking-[0.22em] text-white/45">
                  Research Quality Gate
                </div>
                {qualityStatus === "loading" ? (
                  <span className="text-[10px] text-amber-300/90">Scoring...</span>
                ) : qualityStatus === "error" ? (
                  <span className="text-[10px] text-rose-300/90">Quality check unavailable</span>
                ) : qualityReport ? (
                  <span
                    className="text-[10px]"
                    style={{ color: qualityReport.passing ? "#6ee7b7" : "#fca5a5" }}
                  >
                    {qualityReport.passing ? "Pass" : "Fail"} • Score {qualityReport.overallScore.toFixed(1)}
                  </span>
                ) : (
                  <span className="text-[10px] text-white/35">Pending</span>
                )}
              </div>

              {qualityReport && (
                <div className="space-y-2">
                  <div className="grid grid-cols-2 gap-2 text-[11px] text-white/70">
                    <div>Citations: {qualityReport.metrics.citationCount}</div>
                    <div>Sources: {qualityReport.metrics.sourceCount}</div>
                    <div>Domains: {qualityReport.metrics.uniqueDomains}</div>
                    <div>Contradictions: {qualityReport.metrics.contradictionCount}</div>
                    <div>Verified claims: {qualityReport.metrics.verifiedClaimCount}</div>
                    <div>
                      Verification rate: {(qualityReport.metrics.claimVerificationRate * 100).toFixed(0)}%
                    </div>
                  </div>
                  {qualityReport.regenerated ? (
                    <div className="text-[10px] text-cyan-300/90">
                      Auto-regenerated once due to failed first quality pass.
                    </div>
                  ) : null}
                  {qualityReport.contradictionFindings.length > 0 ? (
                    <div className="text-[10px] text-amber-200/90">
                      Top contradiction: {qualityReport.contradictionFindings[0]?.sourceA} vs {qualityReport.contradictionFindings[0]?.sourceB}
                    </div>
                  ) : null}
                  {qualityReport.claimVerifications?.length > 0 ? (
                    <div className="text-[10px] text-white/60">
                      Claim check: {qualityReport.claimVerifications[0]?.status.toUpperCase()} - {qualityReport.claimVerifications[0]?.rationale}
                    </div>
                  ) : null}
                </div>
              )}
            </div>

            <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 space-y-3">
              <div className="text-[10px] uppercase tracking-[0.22em] text-white/45">
                Sarvam Export and Language Transform
              </div>
              <div className="grid grid-cols-2 gap-2">
                <label className="text-[10px] text-white/55">
                  Target language
                  <select
                    value={targetLanguageCode}
                    onChange={(event) => setTargetLanguageCode(event.target.value)}
                    className="mt-1 w-full rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-[11px] text-white/80"
                    disabled={!canTransform || transforming || exporting}
                  >
                    {LANGUAGE_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value} className="bg-[#11131a]">
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
                <div className="flex items-end gap-2">
                  <button
                    type="button"
                    onClick={onTransformWithSarvam}
                    disabled={!canTransform || transforming || exporting}
                    className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-[10px] uppercase tracking-[0.2em] text-white/70 disabled:opacity-40"
                  >
                    {transforming ? "Transforming" : "Transform"}
                  </button>
                  <button
                    type="button"
                    onClick={onDownloadDocx}
                    disabled={!canTransform || transforming || exporting}
                    className="rounded-lg border border-cyan-200/20 bg-cyan-200/10 px-3 py-2 text-[10px] uppercase tracking-[0.2em] text-cyan-100 disabled:opacity-40"
                  >
                    {exporting ? "Exporting" : "Download DOCX"}
                  </button>
                </div>
              </div>
              <label className="text-[10px] text-white/55 block">
                Optional prompt to modify output before download
                <textarea
                  value={instruction}
                  onChange={(event) => setInstruction(event.target.value)}
                  placeholder="Example: Make it concise for executives and keep bullet points only"
                  disabled={!canTransform || transforming || exporting}
                  className="mt-1 w-full min-h-[72px] rounded-lg border border-white/10 bg-white/5 px-2 py-2 text-[11px] text-white/80 placeholder:text-white/30"
                />
              </label>
              {transformStatus ? (
                <div className="text-[10px] text-cyan-100/90">{transformStatus}</div>
              ) : null}
            </div>

            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.8 }}
              className="font-sans text-[13px] text-white/88 leading-7 whitespace-pre-wrap max-h-[920px] overflow-y-auto pr-2"
            >
              {displayAnswer}
            </motion.p>
          </div>
        ) : status === "active" ? (
          <div className="flex items-center gap-2 min-h-[220px]">
            <div className="flex gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-white/30 animate-bounce" style={{ animationDelay: "0ms" }} />
              <span className="w-1.5 h-1.5 rounded-full bg-white/30 animate-bounce" style={{ animationDelay: "150ms" }} />
              <span className="w-1.5 h-1.5 rounded-full bg-white/30 animate-bounce" style={{ animationDelay: "300ms" }} />
            </div>
            <span className="text-xs text-white/30 font-sans">
              Compiling structured report...
            </span>
          </div>
        ) : (
          <p className="font-sans text-xs text-white/20 italic min-h-[220px]">
            Pipeline output will appear here as a full research report
          </p>
        )}
      </div>

      {/* Input handle — top */}
      <Handle
        type="target"
        position={Position.Top}
        className="!w-2.5 !h-2.5 !rounded-full !border-2 !border-white/20 !bg-white/10"
      />
    </motion.div>
  );
}
