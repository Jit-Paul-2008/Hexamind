"use client";

import { useCallback, useState } from "react";
import type { PipelineQualityReport } from "@/types/pipeline";
import { fetchQualityReport } from "@/lib/api/quality";

export function useQuality() {
  const [report, setReport] = useState<PipelineQualityReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async (sessionId: string) => {
    setLoading(true);
    setError("");
    try {
      const payload = await fetchQualityReport(sessionId);
      setReport(payload);
      return payload;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load quality.");
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  return { report, loading, error, load };
}
