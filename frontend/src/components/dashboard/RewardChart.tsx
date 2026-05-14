import type { AvgRewardRow } from "../../types/api";

interface RewardChartProps {
  data: AvgRewardRow[];
}

export function RewardChart({ data }: RewardChartProps) {
  const drl = data.find((r) => r.policy === "drl");
  const cf = data.find((r) => r.policy === "collab_filter");

  return (
    <div className="bg-white rounded-2xl border border-gray-200 p-6">
      <h2 className="text-base font-semibold mb-1">
        Average reward per episode
      </h2>
      <p className="text-xs text-gray-500 mb-6">
        Mean of non-zero reward signals · indicates intent quality
      </p>

      <div className="grid grid-cols-2 gap-4">
        <RewardCell
          label="DRL"
          value={drl?.avg_reward ?? 0}
          count={drl?.n_episodes ?? 0}
        />
        <RewardCell
          label="CF Baseline"
          value={cf?.avg_reward ?? 0}
          count={cf?.n_episodes ?? 0}
        />
      </div>
    </div>
  );
}

function RewardCell({
  label,
  value,
  count,
}: {
  label: string;
  value: number;
  count: number;
}) {
  const positive = value >= 0;
  return (
    <div className="rounded-xl border border-gray-100 p-4">
      <span className="text-xs text-gray-500 uppercase tracking-wide">
        {label}
      </span>
      <div
        className={`text-3xl font-semibold mt-1 ${positive ? "text-brand-600" : "text-red-600"}`}
      >
        {value >= 0 ? "+" : ""}
        {value.toFixed(3)}
      </div>
      <p className="text-xs text-gray-500 mt-1">over {count} episodes</p>
    </div>
  );
}
