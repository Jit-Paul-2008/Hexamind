import {
  exportReportDocx,
  transformReportWithSarvam,
  type SarvamTransformPayload,
  type SarvamTransformResponse,
} from "@/lib/pipelineClient";

export async function transformReport(
  sessionId: string,
  payload: SarvamTransformPayload
): Promise<SarvamTransformResponse> {
  return transformReportWithSarvam(sessionId, payload);
}

export async function exportDocx(sessionId: string, payload: SarvamTransformPayload) {
  return exportReportDocx(sessionId, payload);
}
