import { useState } from "react";
import {
  useTelemetrySummary,
  usePolicyComparison,
} from "../hooks/useTelemetry";
import { ConversionChart } from "../components/dashboard/ConversionChart";
import { RewardChart } from "../components/dashboard/RewardChart";
import { EntropyChart } from "../components/dashboard/EntropyChart";
import { EpsilonChart } from "../components/dashboard/EpsilonChart";
import type { Window } from "../api/telemetry";
import { cn } from "../lib/cn";

const WINDOWS: { value: Window; label: string }[] = [
  { value: "1h", label: "Last hour" },
  { value: "24h", label: "Last 24h" },
  { value: "7d", label: "Last 7 days" },
  { value: "all", label: "All time" },
];

export default function DashboardPage() {
  const [window, setWindow] = useState<Window>("24h");
  const { data: summary, isLoading } = useTelemetrySummary(window);
  const { data: comparison } = usePolicyComparison(window);

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-6 gap-4">
        <div>
          <h1 className="text-2xl font-semibold">
            Policy comparison dashboard
          </h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Live A/B telemetry · DRL agent vs collaborative-filtering baseline
          </p>
        </div>

        <div className="flex gap-1 bg-white border border-gray-200 rounded-lg p-1">
          {WINDOWS.map((w) => (
            <button
              key={w.value}
              onClick={() => setWindow(w.value)}
              className={cn(
                "px-3 py-1.5 text-xs font-medium rounded transition",
                window === w.value
                  ? "bg-brand-600 text-white"
                  : "text-gray-600 hover:bg-gray-50",
              )}
            >
              {w.label}
            </button>
          ))}
        </div>
      </div>

      {isLoading || !summary || !comparison ? (
        <div className="grid md:grid-cols-2 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div
              key={i}
              className="bg-white rounded-2xl h-64 border border-gray-200 animate-pulse"
            />
          ))}
        </div>
      ) : (
        <div className="grid md:grid-cols-2 gap-4">
          <ConversionChart data={comparison} />
          <RewardChart data={summary.avg_reward_by_policy} />
          <EntropyChart data={summary.q_value_entropy_timeline} />
          <EpsilonChart data={summary.epsilon_curve} />
        </div>
      )}
    </div>
  );
}
