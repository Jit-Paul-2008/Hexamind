// ─────────────────────────────────────────────────────────────────────────────
// useProcessPipeline — orchestrates the agent processing flow
//
// MOCK VERSION: simulates streaming text with timeouts.
// TODO(backend): replace with SSE/WebSocket connection to:
//   POST /api/pipeline/start   → { sessionId }
//   GET  /api/pipeline/:id/stream → SSE stream of PipelineEvent
// ─────────────────────────────────────────────────────────────────────────────

import { useCallback } from "react";
import { usePipelineStore } from "@/lib/store";
import { AGENTS } from "@/lib/agents";

// Simulated agent responses — replace with real backend data
const MOCK_RESPONSES: Record<string, string> = {
  advocate:
    "Analysing from a constructive perspective... The hypothesis holds merit when considering the available evidence. Key supporting factors include the correlation between input variables and the positive trend in recent data. The logical framework remains internally consistent across multiple validation passes.",
  skeptic:
    "Challenging assumptions... Several potential weaknesses identified: the sample size may be insufficient for broad generalisation, there's a possible confirmation bias in the data collection methodology, and the causal mechanism hasn't been isolated from confounding variables.",
  synthesiser:
    "Integrating perspectives... Both the constructive and adversarial analyses reveal a more nuanced picture. The core hypothesis is partially supported but requires qualification — the relationship holds under specific conditions but breaks down at the boundaries identified by the Skeptic.",
  oracle:
    "Projecting implications... Based on the synthesised analysis, there is a 73% probability of the primary outcome materialising within the specified timeframe. Two key risk factors could alter this trajectory. Recommended action: proceed with a monitored pilot phase.",
};

function streamText(
  agentId: string,
  text: string,
  onChunk: (chunk: string) => void,
  onDone: () => void,
): NodeJS.Timeout[] {
  const words = text.split(" ");
  const timers: NodeJS.Timeout[] = [];
  words.forEach((word, i) => {
    const t = setTimeout(() => {
      onChunk(word + (i < words.length - 1 ? " " : ""));
      if (i === words.length - 1) onDone();
    }, i * 55 + Math.random() * 30); // ~55ms per word, slight jitter
    timers.push(t);
  });
  return timers;
}

export function useProcessPipeline() {
  const { startPipeline, setNodeStatus, appendChunk, setFinalAnswer } =
    usePipelineStore();

  const runPipeline = useCallback(
    (query: string) => {
      startPipeline(query);

      // TODO(backend): POST /api/pipeline/start { query }
      // Then open SSE: GET /api/pipeline/{sessionId}/stream
      // For now, we simulate the sequential agent processing:

      const agentOrder = AGENTS.sort(
        (a, b) => a.processingOrder - b.processingOrder
      );
      let delay = 600; // initial delay after input

      agentOrder.forEach((agent, _idx) => {
        const text = MOCK_RESPONSES[agent.id] || "Processing...";
        const agentStartDelay = delay;

        // Start agent
        setTimeout(() => {
          setNodeStatus(agent.id, "active");
        }, agentStartDelay);

        // Stream text
        const streamStartDelay = agentStartDelay + 400;
        setTimeout(() => {
          streamText(
            agent.id,
            text,
            (chunk) => appendChunk(agent.id, chunk),
            () => {
              setNodeStatus(agent.id, "done");
            }
          );
        }, streamStartDelay);

        // Calculate when this agent finishes
        const wordCount = text.split(" ").length;
        const streamDuration = wordCount * 60 + 200;
        delay = streamStartDelay + streamDuration + 300; // gap before next agent
      });

      // Final answer after all agents complete
      setTimeout(() => {
        setNodeStatus("output", "active");
        setTimeout(() => {
          setFinalAnswer(
            "Based on the multi-agent analysis, the hypothesis is partially validated with a 73% confidence interval. A monitored pilot is recommended before full commitment."
          );
        }, 800);
      }, delay);
    },
    [startPipeline, setNodeStatus, appendChunk, setFinalAnswer]
  );

  return { runPipeline };
}
