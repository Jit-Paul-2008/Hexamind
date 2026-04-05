"use client";

import {
  useState,
  useCallback,
  useEffect,
  type FormEvent,
  type KeyboardEvent,
} from "react";
import { motion } from "framer-motion";
import { useProcessPipeline } from "@/hooks/useProcessPipeline";
import { usePipelineStore } from "@/lib/store";

const QUICK_PROMPTS = [
  "Summarize key healthcare AI safety risks for the next 12 months",
  "Compare local model architectures for reliability and cost",
  "Generate an executive brief with citations and actionable recommendations",
];

const MAX_CHARS = 1800;

export default function InputBar() {
  const [query, setQuery] = useState("");
  const { runPipeline } = useProcessPipeline();
  const pipelineStatus = usePipelineStore((s) => s.session?.status);
  const pipelineError = usePipelineStore((s) => s.session?.errorMessage);
  const isRunning = pipelineStatus === "running";

  const setPrompt = useCallback(
    (prompt: string) => {
      if (isRunning) {
        return;
      }
      setQuery(prompt.slice(0, MAX_CHARS));
      requestAnimationFrame(() => {
        const input = document.getElementById("query-input") as HTMLTextAreaElement | null;
        input?.focus();
        input?.setSelectionRange(input.value.length, input.value.length);
      });
    },
    [isRunning]
  );

  const handleSubmit = useCallback(
    (e?: FormEvent) => {
      e?.preventDefault();
      const trimmed = query.trim();
      if (!trimmed || isRunning) return;
      runPipeline(trimmed);
      setQuery("");
    },
    [query, isRunning, runPipeline]
  );

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit]
  );

  const handleGlobalShortcut = useCallback((e: globalThis.KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      const input = document.getElementById("query-input") as HTMLTextAreaElement | null;
      input?.focus();
    }
  }, []);

  useEffect(() => {
    window.addEventListener("keydown", handleGlobalShortcut);
    return () => {
      window.removeEventListener("keydown", handleGlobalShortcut);
    };
  }, [handleGlobalShortcut]);

  const remainingChars = MAX_CHARS - query.length;
  const isNearLimit = remainingChars <= 160;

  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.8, delay: 0.3 }}
      className="fixed bottom-0 left-0 right-0 z-50 pointer-events-none"
    >
      <div className="bg-background px-4 pb-6 pt-4 pointer-events-auto border-t-8 border-border-dark">
        {pipelineStatus === "error" && pipelineError ? (
          <div className="max-w-2xl mx-auto mb-4 retro-input bg-[#ffb3b3] p-4 text-xs text-foreground font-black uppercase tracking-wider">
            Pipeline error: {pipelineError}
          </div>
        ) : null}

        <div className="max-w-2xl mx-auto mb-3 flex flex-wrap items-center gap-2">
          {QUICK_PROMPTS.map((prompt) => (
            <button
              key={prompt}
              type="button"
              disabled={isRunning}
              onClick={() => setPrompt(prompt)}
              className="retro-button px-4 py-2 text-[11px] font-black bg-pastel-yellow hover:bg-pastel-peach transition disabled:opacity-50"
            >
              {prompt.split(" ").slice(0, 4).join(" ")}
            </button>
          ))}
        </div>
        <form
          onSubmit={handleSubmit}
          className="max-w-2xl mx-auto flex items-end gap-3"
        >
          {/* Text input */}
          <div className="flex-1 relative">
            <textarea
              id="query-input"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask ARIA anything..."
              disabled={isRunning}
              rows={1}
              maxLength={MAX_CHARS}
              aria-label="Pipeline prompt input"
              className="w-full resize-none retro-input px-5 py-4 font-sans text-sm text-foreground placeholder:text-foreground/30 font-bold
                         focus:outline-none transition-all duration-200 shadow-[4px_4px_0px_0px_var(--border-color)]"
              style={{ minHeight: 56, maxHeight: 120 }}
            />
          </div>

          {/* Send button */}
          <button
            type="submit"
            disabled={!query.trim() || isRunning}
            id="send-query-btn"
            aria-label="Run pipeline"
            className="flex-shrink-0 retro-button px-6 py-4 bg-[#7dd3fc] hover:bg-[#38bdf8] text-foreground transition-all duration-200 group h-[56px]"
          >
            {isRunning ? (
              <div className="flex items-center gap-3">
                <div className="w-4 h-4 border-4 border-border-dark border-t-transparent rounded-full animate-spin" />
                <span className="text-sm font-sans font-black uppercase tracking-widest">Wait</span>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 14 14"
                  fill="none"
                  className="group-hover:translate-x-0.5 transition-transform"
                >
                  <path
                    d="M1 7h12M13 7L8 2M13 7L8 12"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
                <span className="text-xs font-sans font-bold uppercase tracking-wide">Run</span>
              </div>
            )}
          </button>

          <button
            type="button"
            disabled={!query || isRunning}
            onClick={() => setQuery("")}
            aria-label="Clear query"
            className="flex-shrink-0 retro-button bg-white px-5 py-4 text-[11px] font-black h-[56px] hover:bg-[#ffb3b3] transition"
          >
            Clear
          </button>
        </form>

        {/* System info */}
        <div className="max-w-2xl mx-auto mt-4 flex items-center justify-between">
          <p className="text-[11px] font-sans font-black tracking-[0.2em] uppercase text-foreground/40">
            Hexamind · ARIA 1.0
          </p>
          <div className="flex items-center gap-4">
            <p className="text-[11px] font-sans font-black text-foreground/40 border-r-4 border-border-dark/10 pr-4">
              Enter to send · Shift+Enter new line
            </p>
            <p className={`text-[11px] font-sans font-black ${isNearLimit ? "text-rose-600" : "text-foreground/40"}`}>
              {remainingChars} chars
            </p>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
