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
      {/* Gradient fade above the bar */}
      <div className="h-12 bg-gradient-to-t from-[#0a0b0f] to-transparent" />

      <div className="bg-[#0a0b0f]/90 backdrop-blur-2xl border-t border-white/5 px-4 pb-4 pt-3 pointer-events-auto">
        <div className="max-w-2xl mx-auto mb-3 flex flex-wrap items-center gap-2">
          {QUICK_PROMPTS.map((prompt) => (
            <button
              key={prompt}
              type="button"
              disabled={isRunning}
              onClick={() => setPrompt(prompt)}
              className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1 text-[10px] tracking-[0.12em] uppercase text-white/45 hover:text-white/80 hover:bg-white/[0.09] hover:border-white/20 disabled:opacity-30 disabled:cursor-not-allowed transition"
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
              className="w-full resize-none rounded-xl border border-white/10 bg-white/5 px-4 py-3 
                         font-sans text-sm text-white/90 placeholder:text-white/20
                         focus:outline-none focus:border-white/25 focus:bg-white/[0.07]
                         disabled:opacity-40 disabled:cursor-not-allowed
                         transition-all duration-300"
              style={{ minHeight: 44, maxHeight: 120 }}
            />
          </div>

          {/* Send button */}
          <button
            type="submit"
            disabled={!query.trim() || isRunning}
            id="send-query-btn"
            aria-label="Run pipeline"
            className="flex-shrink-0 rounded-xl border border-white/10 bg-white/5 px-4 py-3
                       text-white/50 hover:text-white hover:bg-white/10 hover:border-white/20
                       disabled:opacity-25 disabled:cursor-not-allowed
                       transition-all duration-300 group"
          >
            {isRunning ? (
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 border-2 border-white/30 border-t-white/80 rounded-full animate-spin" />
                <span className="text-xs font-sans tracking-wider uppercase">Processing</span>
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
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
                <span className="text-xs font-sans tracking-wider uppercase">Run</span>
              </div>
            )}
          </button>

          <button
            type="button"
            disabled={!query || isRunning}
            onClick={() => setQuery("")}
            aria-label="Clear query"
            className="flex-shrink-0 rounded-xl border border-white/10 bg-transparent px-3 py-3 text-[10px] uppercase tracking-[0.2em] text-white/40 hover:text-white/75 hover:border-white/20 disabled:opacity-25 disabled:cursor-not-allowed transition"
          >
            Clear
          </button>
        </form>

        {/* System info */}
        <div className="max-w-2xl mx-auto mt-2 flex items-center justify-between">
          <p className="text-[9px] font-sans tracking-[0.3em] uppercase text-white/15">
            Hexamind · ARIA Pipeline v1.0
          </p>
          <div className="flex items-center gap-3">
            <p className="text-[9px] font-sans text-white/15">
              Enter to send · Shift+Enter for new line · Ctrl/Cmd+K focus
            </p>
            <p className={`text-[9px] font-sans ${isNearLimit ? "text-amber-200/60" : "text-white/15"}`}>
              {remainingChars} chars
            </p>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
