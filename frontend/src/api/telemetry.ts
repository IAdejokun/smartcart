import { apiClient } from "./client";
import type { PolicyComparison, TelemetrySummary } from "../types/api";

export type Window = "1h" | "24h" | "7d" | "all";

export async function getSummary(
  window: Window = "24h",
): Promise<TelemetrySummary> {
  const response = await apiClient.get<TelemetrySummary>("/telemetry/summary", {
    params: { window },
  });
  return response.data;
}

export async function getPolicyComparison(
  window: Window = "24h",
): Promise<PolicyComparison> {
  const response = await apiClient.get<PolicyComparison>(
    "/telemetry/policy-comparison",
    {
      params: { window },
    },
  );
  return response.data;
}
