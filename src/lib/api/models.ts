import { publicApiBaseUrl } from "@/lib/publicApiBaseUrl";

const API_BASE_URL = publicApiBaseUrl;

export type ModelStatus = {
  baseUrl?: string;
  configuredProvider?: string;
  activeProvider?: string;
  modelName?: string;
  isFallback?: boolean;
  ready?: boolean;
  installedCount?: number;
  [key: string]: string | number | boolean | string[] | undefined;
};

export async function fetchModelStatus(): Promise<ModelStatus> {
  const response = await fetch(`${API_BASE_URL}/api/models/status`);
  if (!response.ok) {
    throw new Error(`Failed to load model status (${response.status})`);
  }
  return (await response.json()) as ModelStatus;
}
