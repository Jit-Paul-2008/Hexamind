import type { NodeStatus, PipelineEvent } from "../types/pipeline";

export interface PipelineRunHandlers {
  startPipeline: (query: string) => void;
  setNodeStatus: (agentId: string, status: NodeStatus) => void;
  appendChunk: (agentId: string, chunk: string) => void;
  setFinalAnswer: (answer: string) => void;
}

export interface PipelineClientOptions {
  apiBaseUrl?: string;
  fetchImpl?: typeof fetch;
  eventSourceImpl?: new (url: string) => EventSource;
}

export async function startPipelineRun(
  query: string,
  handlers: PipelineRunHandlers,
  options: PipelineClientOptions = {}
): Promise<EventSource | null> {
  const apiBaseUrl =
    options.apiBaseUrl ??
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    "http://localhost:8000";
  const fetchImpl = options.fetchImpl ?? fetch;
  const eventSourceImpl = options.eventSourceImpl ?? EventSource;

  handlers.startPipeline(query);

  try {
    const startResponse = await fetchImpl(`${apiBaseUrl}/api/pipeline/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });

    if (!startResponse.ok) {
      throw new Error(`Failed to start pipeline (${startResponse.status})`);
    }

    const { sessionId } = (await startResponse.json()) as { sessionId: string };
    const source = new eventSourceImpl(
      `${apiBaseUrl}/api/pipeline/${sessionId}/stream`
    );

    const onMessage = (raw: MessageEvent) => {
      try {
        const event = JSON.parse(raw.data) as PipelineEvent;

        if (event.type === "agent_start") {
          handlers.setNodeStatus(event.agentId, "active");
          return;
        }

        if (event.type === "agent_chunk" && event.chunk) {
          handlers.appendChunk(event.agentId, event.chunk);
          return;
        }

        if (event.type === "agent_done") {
          handlers.setNodeStatus(event.agentId, "done");
          return;
        }

        if (event.type === "pipeline_done") {
          handlers.setNodeStatus("output", "active");
          handlers.setFinalAnswer(event.fullContent || "");
          source.close();
          return;
        }

        if (event.type === "error") {
          handlers.setNodeStatus(event.agentId || "output", "error");
          source.close();
        }
      } catch {
        handlers.setNodeStatus("output", "error");
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
      handlers.setNodeStatus("output", "error");
      source.close();
    };

    return source;
  } catch {
    handlers.setNodeStatus("output", "error");
    return null;
  }
}