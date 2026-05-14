import { useQuery } from "@tanstack/react-query";
import { getSummary, getPolicyComparison, type Window } from "../api/telemetry";

export function useTelemetrySummary(window: Window = "24h") {
  return useQuery({
    queryKey: ["telemetry", "summary", window],
    queryFn: () => getSummary(window),
    refetchInterval: 30_000, // poll every 30s
    staleTime: 25_000,
  });
}

export function usePolicyComparison(window: Window = "24h") {
  return useQuery({
    queryKey: ["telemetry", "comparison", window],
    queryFn: () => getPolicyComparison(window),
    refetchInterval: 30_000,
    staleTime: 25_000,
  });
}
