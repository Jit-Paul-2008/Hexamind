import type {
  NodeStatus,
  PipelineEvent,
  PipelineQualityReport,
} from "../types/pipeline";
import { publicApiBaseUrl } from "@/lib/publicApiBaseUrl";

export interface PipelineRunHandlers {
  startPipeline: (query: string) => void;
  setBackendSessionId: (sessionId: string) => void;
  setNodeStatus: (agentId: string, status: NodeStatus) => void;
  appendChunk: (agentId: string, chunk: string) => void;
  setFinalAnswer: (answer: string) => void;
  setQualityLoading: () => void;
  setQualityReport: (report: PipelineQualityReport) => void;
  setQualityError: () => void;
  setPipelineError: (message: string) => void;
}

export interface PipelineClientOptions {
  apiBaseUrl?: string;
  fetchImpl?: typeof fetch;
  eventSourceImpl?: new (url: string) => EventSource;
}

export interface SarvamTransformPayload {
  targetLanguageCode: string;
  instruction?: string;
}

export interface SarvamTransformResponse {
  sessionId: string;
  text: string;
  languageCode: string;
  instructionApplied: boolean;
  provider: string;
  fallback: boolean;
  notes: string[];
}

export async function startPipelineRun(
  query: string,
  handlers: PipelineRunHandlers,
  options: PipelineClientOptions = {}
): Promise<EventSource | null> {
  const apiBaseUrl = options.apiBaseUrl ?? publicApiBaseUrl;
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
    handlers.setBackendSessionId(sessionId);
    const source = new eventSourceImpl(
      `${apiBaseUrl}/api/pipeline/${sessionId}/stream`
    );
    let pipelineCompleted = false;

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
          if (pipelineCompleted) {
            return;
          }
          pipelineCompleted = true;
          handlers.setNodeStatus("output", "active");
          handlers.setFinalAnswer(event.fullContent || "");
          handlers.setQualityLoading();
          void fetchQualityReport(apiBaseUrl, sessionId, fetchImpl, handlers);
          source.close();
          return;
        }

        if (event.type === "error") {
          handlers.setPipelineError(event.error || "Pipeline stream returned an error.");
          handlers.setNodeStatus(event.agentId || "output", "error");
          source.close();
        }
      } catch {
        handlers.setPipelineError("Could not parse pipeline stream event.");
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
      if (pipelineCompleted) {
        return;
      }
      handlers.setPipelineError("Lost connection to pipeline stream. Please retry.");
      handlers.setNodeStatus("output", "error");
      source.close();
    };

    return source;
  } catch (error) {
    const message =
      error instanceof Error
        ? error.message
        : "Unable to start pipeline. Check backend availability.";
    handlers.setPipelineError(message);
    handlers.setNodeStatus("output", "error");
    return null;
  }
}

async function fetchQualityReport(
  apiBaseUrl: string,
  sessionId: string,
  fetchImpl: typeof fetch,
  handlers: Pick<
    PipelineRunHandlers,
    "setQualityReport" | "setQualityError"
  >
): Promise<void> {
  try {
    let attempts = 0;
    let payload: PipelineQualityReport | null = null;

    while (attempts < 3 && !payload) {
      attempts += 1;
      const response = await fetchImpl(`${apiBaseUrl}/api/pipeline/${sessionId}/quality`);
      if (!response.ok) {
        throw new Error(`Failed to fetch quality report (${response.status})`);
      }
      const candidate = (await response.json()) as PipelineQualityReport;
      if (candidate.status === "ready" || attempts >= 3) {
        payload = candidate;
        break;
      }
      await new Promise((resolve) => setTimeout(resolve, 300));
    }

    if (!payload) {
      throw new Error("Quality report did not become ready");
    }

    handlers.setQualityReport(payload);
  } catch {
    handlers.setQualityError();
  }
}

export async function transformReportWithSarvam(
  sessionId: string,
  payload: SarvamTransformPayload,
  options: Omit<PipelineClientOptions, "eventSourceImpl"> = {}
): Promise<SarvamTransformResponse> {
  const apiBaseUrl = options.apiBaseUrl ?? publicApiBaseUrl;
  const fetchImpl = options.fetchImpl ?? fetch;

  const response = await fetchImpl(
    `${apiBaseUrl}/api/pipeline/${sessionId}/sarvam-transform`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }
  );

  if (!response.ok) {
    throw new Error(`Sarvam transform failed (${response.status})`);
  }

  return (await response.json()) as SarvamTransformResponse;
}

export async function exportReportDocx(
  sessionId: string,
  payload: SarvamTransformPayload,
  options: Omit<PipelineClientOptions, "eventSourceImpl"> = {}
): Promise<{ blob: Blob; filename: string }> {
  const apiBaseUrl = options.apiBaseUrl ?? publicApiBaseUrl;
  const fetchImpl = options.fetchImpl ?? fetch;

  const response = await fetchImpl(`${apiBaseUrl}/api/pipeline/${sessionId}/export-docx`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`DOCX export failed (${response.status})`);
  }

  const blob = await response.blob();
  const disposition = response.headers.get("content-disposition") || "";
  const filenameMatch = disposition.match(/filename="?([^";]+)"?/i);
  const filename = filenameMatch?.[1] || `hexamind-${sessionId}.docx`;
  return { blob, filename };
}