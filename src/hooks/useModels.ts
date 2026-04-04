"use client";

import { useCallback, useEffect, useState } from "react";
import { fetchModelStatus, type ModelStatus } from "@/lib/api/models";

export function useModels() {
  const [status, setStatus] = useState<ModelStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const payload = await fetchModelStatus();
      setStatus(payload);
      return payload;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load model status.");
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return { status, loading, error, reload: load };
}
