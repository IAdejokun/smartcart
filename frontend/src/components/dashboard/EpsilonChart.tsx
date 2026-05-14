import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { EpsilonPoint } from "../../types/api";

interface EpsilonChartProps {
  data: EpsilonPoint[];
}

function formatEpsilonValue(value: unknown): string {
  return typeof value === "number" ? value.toFixed(3) : "—";
}

export function EpsilonChart({ data }: EpsilonChartProps) {
  return (
    <div className="bg-white rounded-2xl border border-gray-200 p-6">
      <h2 className="text-base font-semibold mb-1">
        Exploration rate (ε) decay
      </h2>
      <p className="text-xs text-gray-500 mb-4">
        Probability of a random recommendation · grounded in real training
        history
      </p>

      {data.length === 0 ? (
        <div className="text-center text-sm text-gray-400 py-8">
          Trainer has not run yet
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
            <XAxis
              dataKey="steps_done"
              tick={{ fontSize: 11 }}
              label={{
                value: "training steps",
                position: "insideBottom",
                offset: -2,
                fontSize: 11,
              }}
            />
            <YAxis tick={{ fontSize: 11 }} domain={[0, 0.35]} />
            <Tooltip
              formatter={formatEpsilonValue}
              contentStyle={{
                borderRadius: 8,
                border: "1px solid #e5e7eb",
                fontSize: 12,
              }}
            />
            <Line
              type="monotone"
              dataKey="epsilon"
              stroke="#f59e0b"
              strokeWidth={2}
              dot={{ r: 3 }}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
