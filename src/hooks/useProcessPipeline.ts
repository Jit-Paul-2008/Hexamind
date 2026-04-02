import { useCallback } from "react";
import { usePipelineStore } from "@/lib/store";
import type { PipelineEvent } from "@/types/pipeline";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export function useProcessPipeline() {
  const { startPipeline, setNodeStatus, appendChunk, setFinalAnswer } =
    usePipelineStore();

  const runPipeline = useCallback(
    async (query: string) => {
      startPipeline(query);

      try {
        const startResponse = await fetch(`${API_BASE_URL}/api/pipeline/start`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query }),
        });

        if (!startResponse.ok) {
          throw new Error(`Failed to start pipeline (${startResponse.status})`);
        }

        const { sessionId } = (await startResponse.json()) as { sessionId: string };

        const source = new EventSource(
          `${API_BASE_URL}/api/pipeline/${sessionId}/stream`
        );

        const onMessage = (raw: MessageEvent) => {
          try {
            const event = JSON.parse(raw.data) as PipelineEvent;
            if (event.type === "agent_start") {
              setNodeStatus(event.agentId, "active");
              return;
            }

            if (event.type === "agent_chunk" && event.chunk) {
              appendChunk(event.agentId, event.chunk);
              return;
            }

            if (event.type === "agent_done") {
              setNodeStatus(event.agentId, "done");
              return;
            }

            if (event.type === "pipeline_done") {
              setNodeStatus("output", "active");
              setFinalAnswer(event.fullContent || "");
              source.close();
              return;
            }

            if (event.type === "error") {
              setNodeStatus(event.agentId || "output", "error");
              source.close();
            }
          } catch {
            setNodeStatus("output", "error");
            source.close();
          }
        };

        source.onmessage = onMessage;
        source.addEventListener("agent_start", onMessage as EventListener);
        source.addEventListener("agent_chunk", onMessage as EventListener);
        source.addEventListener("agent_done", onMessage as EventListener);
        source.addEventListener("pipeline_done", onMessage as EventListener);
        source.addEventListener("error", onMessage as EventListener);

        source.onerror = () => {
          setNodeStatus("output", "error");
          source.close();
        };
      } catch {
        setNodeStatus("output", "error");
      }
    },
    [startPipeline, setNodeStatus, appendChunk, setFinalAnswer]
  );

  return { runPipeline };
}
