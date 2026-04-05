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
      <div className="bg-background px-4 pb-4 pt-3 pointer-events-auto border-t-4 border-border-dark">
        {pipelineStatus === "error" && pipelineError ? (
          <div className="max-w-2xl mx-auto mb-3 retro-input bg-[#ffb3b3] px-3 py-2 text-[11px] text-foreground font-bold">
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
              className="retro-button px-3 py-1 text-[10px] tracking-[0.1em] uppercase font-bold bg-pastel-yellow hover:bg-pastel-peach transition disabled:opacity-40"
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
              className="w-full resize-none retro-input px-4 py-3 font-sans text-sm text-foreground placeholder:text-foreground/40 font-medium
                         focus:outline-none transition-all duration-200"
              style={{ minHeight: 48, maxHeight: 120 }}
            />
          </div>

          {/* Send button */}
          <button
            type="submit"
            disabled={!query.trim() || isRunning}
            id="send-query-btn"
            aria-label="Run pipeline"
            className="flex-shrink-0 retro-button px-4 py-3 bg-pastel-yellow hover:bg-pastel-peach text-foreground transition-all duration-200 group"
          >
            {isRunning ? (
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 border-2 border-border-dark border-t-foreground/40 rounded-full animate-spin" />
                <span className="text-xs font-sans font-bold uppercase tracking-wide">Processing</span>
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
            className="flex-shrink-0 retro-button bg-white px-3 py-3 text-[10px] uppercase font-bold tracking-[0.1em] text-foreground hover:bg-pastel-yellow transition"
          >
            Clear
          </button>
        </form>

        {/* System info */}
        <div className="max-w-2xl mx-auto mt-3 flex items-center justify-between">
          <p className="text-[10px] font-sans font-bold tracking-[0.1em] uppercase text-foreground/50">
            Hexamind · ARIA Pipeline v1.0
          </p>
          <div className="flex items-center gap-3">
            <p className="text-[10px] font-sans font-bold text-foreground/50">
              Enter to send · Shift+Enter for new line · Ctrl/Cmd+K focus
            </p>
            <p className={`text-[10px] font-sans font-bold ${isNearLimit ? "text-[#ffb3b3]" : "text-foreground/50"}`}>
              {remainingChars} chars
            </p>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
